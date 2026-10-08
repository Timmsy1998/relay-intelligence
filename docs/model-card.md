# Model card: tfidf-logreg-v1

## Purpose

Suggest an operational incident category and an initial runbook to inspect. Output is advisory. The model does not establish a root cause, estimate business impact or execute a fix.

## Data and method

Training: 48 synthetic alert descriptions across saturation, deployment, database, network, queue and authentication. Evaluation: 12 separate synthetic alerts, two per class. Runbooks: six synthetic, versioned operational guides. All fixtures are checked into `backend/relay/data`; no customer data was used.

A TF-IDF word unigram/bigram vectorizer feeds logistic regression. A separate TF-IDF index compares the alert to runbooks using cosine similarity. The model trains once per process from bundled fixtures. A training-data digest accompanies each analysis so changes are visible.

A recommendation requires a classifier score of at least 0.32, a top-two margin of at least 0.08, and same-category runbook evidence with similarity at least 0.08. Those are demonstration thresholds, not statistically calibrated production cutoffs. The interface calls the value a model score, not confidence.

The output includes a suggested category even when abstaining for audit/debugging, but the visible assessment asks for more context. Evidence retains its source ID, revision and owner. The model never rewrites a runbook into an invented diagnosis.

## Evaluation

`python scripts/evaluate.py` regenerates the benchmark report. The committed [report](evaluation.json) records 12/12 correct class predictions and 100% non-abstained coverage on the current in-domain examples. Separate tests cover empty, irrelevant and mixed-signal inputs and lack of supporting evidence.

This tiny synthetic result is easy to overfit. It does not measure real alert quality, unseen services, data drift, noisy logs, multilabel incidents, adversarial input or how often a useful first check actually resolves an incident. No accuracy claim should extend beyond this fixture set.

## Before real use

Collect consented, redacted historical incidents with engineer-reviewed outcomes. Split by time and incident family to avoid leakage. Compare to keyword and majority-class baselines. Report per-class precision/recall, abstention coverage, error rate on accepted predictions, calibration and engineer usefulness ratings. Choose thresholds on a validation set and preserve a final test set.

Human reviews are stored as feedback, but they are not automatically used as labels or training data. A review accepts a direction, not proof that the diagnosis was correct. An LLM adapter would need the same evidence and abstention contract plus a separate evaluation of unsupported claims and sensitive-data handling.
