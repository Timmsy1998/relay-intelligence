import os
import time
from functools import lru_cache
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from relay.repository import database

LEASE_SECONDS = 120  # Longer than the 60-second Lambda worker timeout.


class Busy(Exception):
    """Retry a concurrent delivery; acknowledging it could lose a failed first attempt."""


class MongoLedger:
    def __init__(self, db):
        self.collection = db.jobs

    def claim(self, event_id):
        now, owner = time.time(), str(uuid4())
        try:
            self.collection.insert_one(
                {
                    "_id": event_id,
                    "state": "running",
                    "lease_until": now + LEASE_SECONDS,
                    "owner": owner,
                }
            )
            return owner
        except DuplicateKeyError:
            pass
        existing = self.collection.find_one({"_id": event_id})
        if existing["state"] == "done":
            return None
        result = self.collection.find_one_and_update(
            {"_id": event_id, "state": "running", "lease_until": {"$lte": now}},
            {"$set": {"owner": owner, "lease_until": now + LEASE_SECONDS}},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            raise Busy(event_id)
        return owner

    def finish(self, event_id, owner):
        self.collection.update_one({"_id": event_id, "owner": owner}, {"$set": {"state": "done"}})

    def release(self, event_id, owner):
        self.collection.update_one(
            {"_id": event_id, "owner": owner, "state": "running"}, {"$set": {"lease_until": 0}}
        )


class DynamoLedger:
    def __init__(self, table):
        self.table = table

    def claim(self, event_id):
        now, owner = int(time.time()), str(uuid4())
        try:
            self.table.update_item(
                Key={"event_id": event_id},
                UpdateExpression="SET #s = :running, lease_until = :until, #o = :owner",
                ConditionExpression="attribute_not_exists(event_id) OR (#s = :running AND lease_until <= :now)",
                ExpressionAttributeNames={"#s": "state", "#o": "owner"},
                ExpressionAttributeValues={
                    ":running": "running",
                    ":until": now + LEASE_SECONDS,
                    ":owner": owner,
                    ":now": now,
                },
            )
            return owner
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            existing = self.table.get_item(Key={"event_id": event_id}, ConsistentRead=True).get(
                "Item", {}
            )
            if existing.get("state") == "done":
                return None
            raise Busy(event_id) from exc

    def finish(self, event_id, owner):
        self._update(event_id, owner, "SET #s = :done", {":done": "done"})

    def release(self, event_id, owner):
        self._update(event_id, owner, "SET lease_until = :zero", {":zero": 0})

    def _update(self, event_id, owner, expression, values):
        names = {"#o": "owner"}
        if "#s" in expression:
            names["#s"] = "state"
        try:
            self.table.update_item(
                Key={"event_id": event_id},
                UpdateExpression=expression,
                ConditionExpression="#o = :owner",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues={":owner": owner, **values},
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise


@lru_cache
def ledger():
    if os.environ.get("LEDGER_BACKEND", "mongo") == "dynamo":
        return DynamoLedger(boto3.resource("dynamodb").Table(os.environ["JOBS_TABLE"]))
    return MongoLedger(database())
