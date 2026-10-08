import json

from mangum import Mangum

from relay.asgi import application
from relay.telemetry import emit
from relay.transport import dispatch
from relay.worker import process

api = Mangum(application, lifespan="off")


def outbox(event, context):
    return {"published": dispatch()}


def worker(event, context):
    failures = []
    for record in event["Records"]:
        try:
            envelope = json.loads(record["body"])
            process(envelope["detail"])
        except Exception as exc:
            emit("analysis.failed", message_id=record["messageId"], error_type=type(exc).__name__)
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
