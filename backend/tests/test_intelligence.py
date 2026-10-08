import json

import pytest
from relay.intelligence import DATA, engine
from sklearn.metrics import accuracy_score


@pytest.mark.parametrize("example", json.loads((DATA / "evaluation.json").read_text()))
def test_held_out_classification(example):
    assert engine().analyse(example["text"])["suggested_category"] == example["label"]


def test_unknown_input_abstains_without_inventing_evidence():
    result = engine().analyse("A violet bicycle with silver wheels, marigolds and a paper kite.")
    assert result["abstained"] and result["category"] == "unclassified"
    assert result["recommendation"] is None and result["checks"] == []


def test_evidence_is_a_versioned_source_not_generated_text():
    source = json.loads((DATA / "runbooks.json").read_text())
    result = engine().analyse(
        "SQS queue backlog oldest message age consumer worker throughput broker"
    )
    assert not result["abstained"]
    for item in result["evidence"]:
        original = next(r for r in source if r["id"] == item["id"])
        assert item["action"] == original["action"] and item["revision"] == original["revision"]


def test_training_and_evaluation_do_not_overlap():
    train = {r["text"] for r in json.loads((DATA / "training.json").read_text())}
    evaluation = json.loads((DATA / "evaluation.json").read_text())
    assert not train.intersection(r["text"] for r in evaluation)
    predicted = [engine().analyse(r["text"])["suggested_category"] for r in evaluation]
    assert accuracy_score([r["label"] for r in evaluation], predicted) >= 0.8
