"""Held-out synthetic benchmark. Run from the repository root."""

import json

from relay.intelligence import DATA, engine
from sklearn.metrics import accuracy_score, classification_report


def evaluate():
    examples = json.loads((DATA / "evaluation.json").read_text())
    model = engine()
    results = [model.analyse(row["text"]) for row in examples]
    labels = [row["label"] for row in examples]
    predictions = [row["suggested_category"] for row in results]
    return {
        "model_version": "tfidf-logreg-v1",
        "training_digest": model.training_digest,
        "dataset": "12 curated synthetic held-out alerts; not production validation",
        "classification_accuracy": accuracy_score(labels, predictions),
        "coverage": sum(not r["abstained"] for r in results) / len(results),
        "report": classification_report(labels, predictions, output_dict=True, zero_division=0),
        "results": [
            {
                "expected": row["label"],
                "predicted": result["suggested_category"],
                "abstained": result["abstained"],
                "score": result["score"],
            }
            for row, result in zip(examples, results, strict=True)
        ],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
