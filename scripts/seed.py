import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from relay.intelligence import engine
from relay.repository import repository
from relay.worker import process

ALERTS = [
    {
        "title": "Checkout latency climbs during the evening peak",
        "service": "checkout-api",
        "severity": "P1",
        "description": "P95 response time rose from 240ms to 3.8s. CPU utilisation is 97% across all pods with sustained CPU throttling. Traffic is twice the normal request rate and the autoscaler is at maximum replicas. Error rate remains below 1%.",
    },
    {
        "title": "Order events waiting for a consumer",
        "service": "order-pipeline",
        "severity": "P2",
        "description": "SQS queue backlog has reached 12,400 messages. Oldest message age is 18 minutes and rising. Consumer throughput dropped to zero after the worker disconnected from the broker. Incoming publish rate is unchanged.",
    },
    {
        "title": "MongoDB reads wait on connection capacity",
        "service": "catalogue",
        "severity": "P2",
        "description": "Database read latency is elevated. Mongo queries wait up to 4 seconds for a connection pool slot. Slow query logs show a collection scan and missing index on the product lookup. Replication lag is stable.",
    },
    {
        "title": "New canary fails its readiness checks",
        "service": "account-service",
        "severity": "P2",
        "description": "The new deployment image fails readiness probes and returns HTTP 500 errors on startup. The previous release is healthy. Errors began immediately after the configuration rollout changed a required environment variable.",
    },
    {
        "title": "Unusual support report needs investigation",
        "service": "customer-portal",
        "severity": "P3",
        "description": "A customer reports that their saved preferences appear different from yesterday. We do not have logs, reproduction steps or a clear time window yet.",
    },
]


def fixtures():
    items = []
    for i, alert in enumerate(ALERTS):
        analysis = engine().analyse(f"{alert['title']}\n{alert['description']}")
        items.append(
            {
                "id": str(uuid5(NAMESPACE_URL, alert["title"])),
                **alert,
                "created_at": f"2026-10-08T{14 - i:02d}:24:00+00:00",
                "status": "ready",
                "version": 2,
                "analysis": analysis,
                "review": None,
                "timeline": [
                    {"at": f"2026-10-08T{14 - i:02d}:24:00+00:00", "label": "Incident received"},
                    {
                        "at": f"2026-10-08T{14 - i:02d}:24:02+00:00",
                        "label": "Evidence and classification ready",
                    },
                ],
            }
        )
    return items


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--export", action="store_true", help="Generate the browser's labelled demo fixtures"
    )
    args = parser.parse_args()
    if args.export:
        Path("frontend/src/demo.json").write_text(json.dumps(fixtures(), indent=2) + "\n")
    else:
        repo = repository()
        for alert in ALERTS:
            incident, _ = repo.create(alert, str(uuid5(NAMESPACE_URL, alert["title"])))
            document = repo.collection.find_one({"id": incident["id"]})
            process(document["outbox"]["event"])
            repo.mark_published(document["_id"])
        print("Seeded five incidents. Existing seeds are preserved.")
