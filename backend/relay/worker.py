import time

from relay.events import validate_event
from relay.intelligence import engine
from relay.ledger import ledger
from relay.repository import repository
from relay.telemetry import emit


def process(event, repo=None, jobs=None, model=None):
    validate_event(event)
    repo, jobs, model = repo or repository(), jobs or ledger(), model or engine()
    owner = jobs.claim(event["event_id"])
    if owner is None:
        return "duplicate"
    started = time.monotonic()
    try:
        incident = repo.get(event["incident_id"])
        if incident is None:
            raise ValueError("Incident does not exist")
        if incident["status"] == "queued":
            analysis = model.analyse(f"{incident['title']}\n{incident['description']}")
            repo.complete(incident["id"], analysis)
        jobs.finish(event["event_id"], owner)
        emit(
            "analysis.completed",
            event_id=event["event_id"],
            incident_id=incident["id"],
            duration_ms=round((time.monotonic() - started) * 1000),
        )
        return "completed"
    except Exception:
        jobs.release(event["event_id"], owner)
        raise
