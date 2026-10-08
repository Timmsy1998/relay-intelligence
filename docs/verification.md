# Verification record

Checked locally on 8 October 2026 with Python 3.12 and Node 24. CI targets Node 22.

| Check | Result |
| --- | --- |
| Python behavioural tests | 32 passed, including DynamoDB conditional writes through Moto |
| Python lint and formatting | Ruff checks passed |
| Frontend API tests | 3 passed |
| TypeScript and production bundle | Vue type check and Vite build passed |
| Frontend formatting | Prettier check passed |
| Dependency audit | npm audit reported zero vulnerabilities |
| Browser demo | Chromium verified selection, evidence, review, filters, abstention, failed connection and mobile overflow |
| Live browser | Connected, submitted, awaited analysis, reviewed, reloaded and verified persistence |
| Native pipeline | Real MongoDB 8.0.16, Redis 7.0.15, Gunicorn, Celery worker and beat processed an HTTP submission through review |
| JavaScript producer | Submitted an alert to the running API |
| Synthetic model regression | 12 of 12 held-out examples classified correctly; see the model card for limits |
| Infrastructure | YAML checks, delivery invariants and AWS cfn-lint passed |

The native integration used temporary binaries and local processes. Docker was unavailable in the development environment, so Compose images, the Lambda image and SAM builds have not been executed locally. GitHub Actions defines those checks; a successful hosted CI run is still required. Cloud deployment, IAM behaviour against actual cloud services, GCP delivery, Kubernetes rollout, Datadog ingestion and load testing remain unverified.

The workbench screenshot is captured from the browser demo. Its incident data is synthetic; the analysis is produced by the same Python pipeline as connected mode.
