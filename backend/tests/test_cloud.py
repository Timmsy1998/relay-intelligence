import json
from uuid import uuid4

import boto3
import pytest
from moto import mock_aws
from relay.events import submitted
from relay.ledger import Busy, DynamoLedger


@mock_aws
def test_dynamo_claim_retry_completion_and_fencing():
    table = boto3.resource("dynamodb", region_name="eu-west-2").create_table(
        TableName="jobs",
        KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "event_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    jobs, key = DynamoLedger(table), str(uuid4())
    owner = jobs.claim(key)
    with pytest.raises(Busy):
        jobs.claim(key)
    jobs.release(key, owner)
    next_owner = jobs.claim(key)
    jobs.finish(key, owner)
    with pytest.raises(Busy):
        jobs.claim(key)
    jobs.finish(key, next_owner)
    assert jobs.claim(key) is None


def test_sqs_partial_batch_failure(monkeypatch):
    from relay import lambda_handlers

    good, bad = submitted(str(uuid4())), submitted(str(uuid4()))

    def process(event):
        if event == bad:
            raise RuntimeError("transient")

    monkeypatch.setattr(lambda_handlers, "process", process)
    result = lambda_handlers.worker(
        {
            "Records": [
                {"messageId": "good", "body": json.dumps({"detail": good})},
                {"messageId": "bad", "body": json.dumps({"detail": bad})},
                {"messageId": "malformed", "body": "invalid"},
            ]
        },
        None,
    )
    assert result == {
        "batchItemFailures": [{"itemIdentifier": "bad"}, {"itemIdentifier": "malformed"}]
    }


def test_eventbridge_rejection_is_not_acknowledged(monkeypatch):
    from relay import transport

    class Events:
        def put_events(self, **kwargs):
            return {"FailedEntryCount": 1}

    monkeypatch.setenv("EVENT_TRANSPORT", "eventbridge")
    monkeypatch.setenv("EVENT_BUS_NAME", "relay")
    monkeypatch.setattr(transport.boto3, "client", lambda name: Events())
    with pytest.raises(RuntimeError):
        transport.publish(submitted(str(uuid4())))


def test_pubsub_receiver_acknowledges_success_and_retries_busy(monkeypatch, client):
    import base64

    from django.test import override_settings
    from relay import gcp
    from relay.ledger import Busy

    payload = {
        "message": {"data": base64.b64encode(json.dumps(submitted(str(uuid4()))).encode()).decode()}
    }
    with override_settings(ROOT_URLCONF="relay.gcp"):
        monkeypatch.setattr(gcp, "process", lambda event: "completed")
        assert client.post("/pubsub/", payload, format="json").status_code == 204

        def busy(event):
            raise Busy("held")

        monkeypatch.setattr(gcp, "process", busy)
        assert client.post("/pubsub/", payload, format="json").status_code == 503
        assert (
            client.post("/pubsub/", {"message": {"data": "bad!"}}, format="json").status_code == 400
        )


def test_event_matches_published_contract():
    from pathlib import Path

    from jsonschema import Draft202012Validator, FormatChecker

    schema = json.loads(Path("docs/event.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(submitted(str(uuid4())))
