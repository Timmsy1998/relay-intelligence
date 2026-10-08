"""Exercise real HTTP -> Mongo outbox -> Redis/Celery -> Mongo review in Compose."""

import json
import time
import urllib.request
from uuid import uuid4

BASE = "http://localhost:8000"


def request(path, data=None, headers=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={
            "Authorization": "Bearer local-review-token",
            "Content-Type": "application/json",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


if __name__ == "__main__":
    with open("docs/sample-alert.json") as file:
        payload = json.load(file)
    incident = request("/api/incidents/", payload, {"Idempotency-Key": str(uuid4())})
    path = f"/api/incidents/{incident['id']}/"
    for _ in range(40):
        incident = request(path)
        if incident["status"] == "ready":
            break
        time.sleep(1)
    else:
        raise RuntimeError("Worker did not complete within 40 seconds")
    assert incident["analysis"]["category"] == "queue"
    reviewed = request(
        path + "review/",
        {"decision": "accepted", "version": incident["version"], "note": "Container smoke test"},
    )
    assert reviewed["status"] == "reviewed"
    print("Real HTTP/outbox/worker pipeline smoke passed")
