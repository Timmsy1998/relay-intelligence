import json
import os

import boto3

from relay.repository import repository
from relay.telemetry import emit


def publish(event):
    if os.environ.get("EVENT_TRANSPORT", "celery") == "eventbridge":
        response = boto3.client("events").put_events(
            Entries=[
                {
                    "Source": "relay.incidents",
                    "DetailType": event["event_type"],
                    "Detail": json.dumps(event),
                    "EventBusName": os.environ["EVENT_BUS_NAME"],
                }
            ]
        )
        if response["FailedEntryCount"]:
            raise RuntimeError("EventBridge rejected event")
    elif os.environ.get("EVENT_TRANSPORT") == "pubsub":
        from google.cloud import pubsub_v1

        publisher = pubsub_v1.PublisherClient()
        publisher.publish(os.environ["PUBSUB_TOPIC"], json.dumps(event).encode()).result(timeout=20)
    else:
        from relay.tasks import analyse_incident

        analyse_incident.delay(event)


def dispatch(repo=None, publisher=None):
    repo, publisher = repo or repository(), publisher or publish
    count = 0
    for document in repo.pending_events():
        try:
            publisher(document["outbox"]["event"])
            repo.mark_published(document["_id"])
            count += 1
        except Exception as exc:
            # Continue independent events; leave this document pending for the next sweep.
            emit(
                "outbox.failed",
                event_id=document["outbox"]["event"]["event_id"],
                error_type=type(exc).__name__,
            )
    return count
