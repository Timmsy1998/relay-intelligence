from uuid import uuid4

import pytest
from relay.ledger import Busy
from relay.repository import Conflict
from relay.transport import dispatch
from relay.worker import process


def create(repo, payload):
    incident, _ = repo.create(payload, str(uuid4()))
    event = repo.collection.find_one({"id": incident["id"]})["outbox"]["event"]
    return incident, event


def test_create_is_atomic_and_retries_converge(repo, payload):
    key = str(uuid4())
    first, created = repo.create(payload, key)
    second, retried = repo.create(payload, key)
    assert created and not retried and first == second
    assert len(repo.pending_events()) == 1
    with pytest.raises(Conflict):
        repo.create({**payload, "title": "Different submission"}, key)


def test_publish_failure_does_not_lose_outbox(repo, payload):
    create(repo, payload)

    def fail(event):
        raise OSError("broker unavailable")

    assert dispatch(repo, fail) == 0
    assert len(repo.pending_events()) == 1
    seen = []
    assert dispatch(repo, seen.append) == 1
    assert len(repo.pending_events()) == 0
    assert len(seen) == 1


def test_worker_duplicate_delivery_is_safe(repo, jobs, payload):
    incident, event = create(repo, payload)
    assert process(event, repo, jobs) == "completed"
    first = repo.get(incident["id"])
    assert first["analysis"]["category"] == "queue"
    assert process(event, repo, jobs) == "duplicate"
    assert repo.get(incident["id"]) == first


def test_retry_releases_failed_lease(repo, jobs, payload):
    incident, event = create(repo, payload)

    class BrokenModel:
        def analyse(self, text):
            raise RuntimeError("transient failure")

    with pytest.raises(RuntimeError):
        process(event, repo, jobs, BrokenModel())
    assert repo.get(incident["id"])["status"] == "queued"
    assert process(event, repo, jobs) == "completed"


def test_concurrent_delivery_is_retried_and_stale_owner_is_fenced(jobs):
    event_id = str(uuid4())
    first = jobs.claim(event_id)
    with pytest.raises(Busy):
        jobs.claim(event_id)
    jobs.collection.update_one({"_id": event_id}, {"$set": {"lease_until": 0}})
    second = jobs.claim(event_id)
    jobs.finish(event_id, first)
    assert jobs.collection.find_one({"_id": event_id})["state"] == "running"
    jobs.finish(event_id, second)
    assert jobs.claim(event_id) is None


def test_stale_review_and_redelivered_analysis_cannot_overwrite_decision(repo, jobs, payload):
    incident, event = create(repo, payload)
    process(event, repo, jobs)
    ready = repo.get(incident["id"])
    reviewed = repo.review(incident["id"], "accepted", "Confirmed worker outage", ready["version"])
    with pytest.raises(Conflict):
        repo.review(incident["id"], "rejected", "", ready["version"])
    assert repo.complete(incident["id"], {"wrong": "replacement"}) is None
    assert repo.get(incident["id"]) == reviewed


def test_review_before_analysis_is_rejected(repo, payload):
    incident, _ = create(repo, payload)
    with pytest.raises(Conflict):
        repo.review(incident["id"], "accepted", "", 1)


def test_duplicate_publish_after_crash_keeps_event_id(repo, jobs, payload):
    incident, _ = create(repo, payload)
    deliveries = []
    # Simulate successful delivery followed by a dispatcher crash before marking published.
    event = repo.pending_events()[0]["outbox"]["event"]
    deliveries.append(event)
    dispatch(repo, deliveries.append)
    assert deliveries[0] == deliveries[1]
    for delivery in deliveries:
        process(delivery, repo, jobs)
    assert len(repo.get(incident["id"])["timeline"]) == 2
