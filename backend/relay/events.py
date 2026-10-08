from datetime import UTC, datetime
from uuid import UUID, uuid4

EVENT_TYPE = "incident.submitted.v1"


def utcnow():
    return datetime.now(UTC).isoformat()


def submitted(incident_id):
    return {
        "event_id": str(uuid4()),
        "event_type": EVENT_TYPE,
        "schema_version": 1,
        "occurred_at": utcnow(),
        "incident_id": incident_id,
    }


def validate_event(event):
    if not isinstance(event, dict) or event.get("event_type") != EVENT_TYPE:
        raise ValueError("Unsupported event type")
    if type(event.get("schema_version")) is not int or event["schema_version"] != 1:
        raise ValueError("Unsupported schema version")
    UUID(event["event_id"])
    UUID(event["incident_id"])
    datetime.fromisoformat(event["occurred_at"])
    return event
