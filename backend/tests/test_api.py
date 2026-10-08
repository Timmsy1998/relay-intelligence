from uuid import uuid4

from relay.worker import process


def test_authenticated_submission_analysis_and_review(client, repo, jobs, payload):
    key = str(uuid4())
    created = client.post("/api/incidents/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert created.status_code == 202
    incident_id = created.data["id"]
    retried = client.post("/api/incidents/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert retried.status_code == 200 and retried.data["id"] == incident_id
    process(repo.pending_events()[0]["outbox"]["event"], repo, jobs)
    detail = client.get(f"/api/incidents/{incident_id}/")
    assert detail.data["analysis"]["category"] == "queue"
    reviewed = client.post(
        f"/api/incidents/{incident_id}/review/",
        {"decision": "accepted", "version": detail.data["version"], "note": "Restored consumers"},
        format="json",
    )
    assert reviewed.status_code == 200 and reviewed.data["status"] == "reviewed"
    stale = client.post(
        f"/api/incidents/{incident_id}/review/",
        {"decision": "rejected", "version": detail.data["version"]},
        format="json",
    )
    assert stale.status_code == 409
    listed = client.get("/api/incidents/")
    assert len(listed.data["items"]) == 1
    assert "outbox" not in listed.data["items"][0]


def test_auth_fails_closed(client, monkeypatch):
    client.credentials()
    assert client.get("/api/incidents/").status_code == 401
    assert client.get("/health/").status_code == 200
    monkeypatch.delenv("RELAY_API_TOKEN")
    client.credentials(HTTP_AUTHORIZATION="Bearer test-token")
    assert client.get("/api/incidents/").status_code == 401


def test_validation_and_idempotency_conflict(client, payload):
    assert client.post("/api/incidents/", payload, format="json").status_code == 400
    key = str(uuid4())
    assert (
        client.post(
            "/api/incidents/",
            {**payload, "severity": "P9"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        ).status_code
        == 400
    )
    client.post("/api/incidents/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert (
        client.post(
            "/api/incidents/",
            {**payload, "title": "Changed request body"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        ).status_code
        == 409
    )


def test_unknown_incident_returns_404(client):
    path = f"/api/incidents/{uuid4()}/"
    assert client.get(path).status_code == 404
    assert (
        client.post(
            path + "review/", {"decision": "accepted", "version": 2}, format="json"
        ).status_code
        == 404
    )
