import hashlib
import json
import os
from functools import lru_cache
from uuid import uuid4

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

from relay.events import submitted, utcnow


class Conflict(Exception):
    pass


class IncidentRepository:
    def __init__(self, database):
        self.collection = database.incidents
        self.collection.create_index("id", unique=True)
        self.collection.create_index("created_at")
        self.collection.create_index("outbox.published_at")

    def create(self, payload, request_key):
        # Unique _id makes concurrent retries converge without a preflight read.
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        incident_id = str(uuid4())
        document = {
            "_id": request_key,
            "id": incident_id,
            **payload,
            "fingerprint": fingerprint,
            "created_at": utcnow(),
            "status": "queued",
            "analysis": None,
            "review": None,
            "version": 1,
            "outbox": {"event": submitted(incident_id), "published_at": None},
            "timeline": [{"at": utcnow(), "label": "Incident received"}],
        }
        try:
            self.collection.insert_one(document)
            return self.public(document), True
        except DuplicateKeyError:
            existing = self.collection.find_one({"_id": request_key})
            if existing["fingerprint"] != fingerprint:
                raise Conflict("Idempotency key already belongs to another request") from None
            return self.public(existing), False

    @staticmethod
    def public(document):
        if document is None:
            return None
        return {
            key: value
            for key, value in document.items()
            if key not in {"_id", "fingerprint", "outbox"}
        }

    def list(self):
        return [self.public(d) for d in self.collection.find().sort("created_at", -1).limit(100)]

    def get(self, incident_id):
        return self.public(self.collection.find_one({"id": incident_id}))

    def pending_events(self):
        return list(self.collection.find({"outbox.published_at": None}).limit(100))

    def mark_published(self, key):
        self.collection.update_one({"_id": key}, {"$set": {"outbox.published_at": utcnow()}})

    def complete(self, incident_id, analysis):
        # Analysis can never overwrite a completed or reviewed incident, even after lease expiry.
        document = self.collection.find_one_and_update(
            {"id": incident_id, "status": "queued"},
            {
                "$set": {"analysis": analysis, "status": "ready"},
                "$inc": {"version": 1},
                "$push": {
                    "timeline": {"at": utcnow(), "label": "Evidence and classification ready"}
                },
            },
            return_document=ReturnDocument.AFTER,
        )
        return self.public(document)

    def review(self, incident_id, decision, note, version):
        document = self.collection.find_one_and_update(
            {"id": incident_id, "status": "ready", "version": version},
            {
                "$set": {
                    "status": "reviewed",
                    "review": {"decision": decision, "note": note, "at": utcnow()},
                },
                "$inc": {"version": 1},
                "$push": {
                    "timeline": {"at": utcnow(), "label": f"Engineer {decision} recommendation"}
                },
            },
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise Conflict("Incident changed or is not ready for review. Refresh and retry.")
        return self.public(document)


@lru_cache
def database():
    client = MongoClient(
        os.environ.get("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=5000
    )
    return client[os.environ.get("MONGO_DATABASE", "relay")]


@lru_cache
def repository():
    return IncidentRepository(database())
