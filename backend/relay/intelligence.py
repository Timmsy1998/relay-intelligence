"""Small, inspectable ML baseline. No generated diagnosis or automated remediation."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

DATA = Path(__file__).parent / "data"
MODEL_VERSION = "tfidf-logreg-v1"
MIN_SCORE = 0.32
MIN_MARGIN = 0.08
MIN_EVIDENCE = 0.08


class Intelligence:
    def __init__(self):
        raw = (DATA / "training.json").read_bytes()
        training = json.loads(raw)
        self.training_digest = hashlib.sha256(raw).hexdigest()[:12]
        self.classifier = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode"),
            LogisticRegression(C=12, max_iter=1000, random_state=42),
        )
        self.classifier.fit([r["text"] for r in training], [r["label"] for r in training])
        self.runbooks = json.loads((DATA / "runbooks.json").read_text())
        self.retriever = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.index = self.retriever.fit_transform(
            [
                f"{r['title']} {r['symptoms']} {' '.join(r['checks'])} {r['action']}"
                for r in self.runbooks
            ]
        )

    def analyse(self, text):
        probabilities = self.classifier.predict_proba([text])[0]
        order = np.argsort(probabilities)[::-1]
        score = float(probabilities[order[0]])
        margin = score - float(probabilities[order[1]])
        category = str(self.classifier.classes_[order[0]])
        similarities = (self.index @ self.retriever.transform([text]).T).toarray().ravel()
        evidence = [
            {**self.runbooks[int(i)], "similarity": round(float(similarities[i]), 3)}
            for i in np.argsort(similarities)[::-1][:3]
            if similarities[i] >= MIN_EVIDENCE
        ]
        abstained = score < MIN_SCORE or margin < MIN_MARGIN or not evidence
        primary = next((r for r in evidence if r["category"] == category), None)
        if primary is None:
            abstained = True
        return {
            "model_version": MODEL_VERSION,
            "training_digest": self.training_digest,
            "category": "unclassified" if abstained else category,
            "suggested_category": category,
            "score": round(score, 3),
            "margin": round(margin, 3),
            "abstained": abstained,
            "summary": "Insufficient matching evidence. Ask an engineer to investigate."
            if abstained
            else f"Signals most closely match {category}. Start with ‘{primary['title']}’.",
            "recommendation": None if abstained else primary["action"],
            "checks": [] if abstained else primary["checks"],
            "evidence": evidence,
            "score_note": "Model score is uncalibrated; it is not a probability that the diagnosis is correct.",
        }


@lru_cache
def engine():
    return Intelligence()
