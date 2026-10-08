import mongomock
import pytest
from relay.ledger import MongoLedger
from relay.repository import IncidentRepository
from rest_framework.test import APIClient


@pytest.fixture
def repo():
    return IncidentRepository(mongomock.MongoClient().relay)


@pytest.fixture
def jobs(repo):
    return MongoLedger(repo.collection.database)


@pytest.fixture
def client(repo, monkeypatch):
    monkeypatch.setenv("RELAY_API_TOKEN", "test-token")
    monkeypatch.setattr("relay.views.repository", lambda: repo)
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION="Bearer test-token")
    return api


@pytest.fixture
def payload():
    return {
        "title": "Queue backlog keeps growing",
        "service": "orders",
        "severity": "P2",
        "description": "SQS oldest message age is increasing. Consumer throughput is zero and the worker broker disconnected.",
    }
