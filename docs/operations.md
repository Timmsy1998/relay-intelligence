# Operations

## Signals that matter

The worker emits JSON events with event/incident IDs and analysis duration. Outbox errors include the event ID and exception type. Alert bodies, tokens and connection strings are excluded from these application log records. Broker/framework error logs still need review before forwarding to external tooling.

Track API error/latency rates, queued incident age, pending outbox count, worker failures, abstention rate, queue age, DLQ count and review disagreements. Only the two SQS alarms are provisioned in the AWS template; the remaining signals require log queries or instrumentation in the target environment.

| Symptom | First check |
| --- | --- |
| Queued incident, empty queue | Pending Mongo outbox and publisher errors |
| Growing queue age | Worker errors, concurrency, Mongo connectivity and active leases |
| DLQ nonempty | Preserve envelope; identify poison input vs transient failure |
| Repeated 409 reviews | Stale browser version or concurrent reviewer |
| All predictions abstain | Input quality, training/runbook changes and source digest |
| Readiness fails | Mongo reachability and credentials; health alone proves only process liveness |

## Replay

Investigate before redriving DLQ messages. Preserve the original `event_id` and envelope: generating a new event identity conceals duplicate history. A live lease must expire or be released before retry can proceed. A completed or reviewed incident stays intact even if its event is replayed.

For queued records whose local Celery retries are exhausted, inspect the embedded outbox event and its ledger. Republish the original event after resolving the failure and lease expiry. There is no automatic local poison-message store. Do not delete incident documents to make replay work.

Completed leases and incidents have no automatic retention policy in this version. Establish privacy, audit and replay retention requirements before real data is admitted. Mongo backup/PITR belongs to the external database configuration. Dynamo PITR is enabled in SAM. Test restoration and duplicate replay together.

## Datadog

The optional `observability` extra installs the official Python tracer:

```bash
pip install '.[observability]'
DD_SERVICE=relay-api DD_ENV=staging DD_VERSION=0.1.0 \
  DD_TRACE_AGENT_URL=http://localhost:8126 DD_LOGS_INJECTION=true \
  ddtrace-run gunicorn relay.wsgi:application --bind 0.0.0.0:8000
```

For Celery use the same prefix with `DD_SERVICE=relay-worker` and the existing worker command. Add the optional dependency in your derived container image, run a Datadog Agent/collector with a reachable trace endpoint, and enable `DD_TRACE_ENABLED=true` (the local example disables it). Use unified service/env/version tags on application containers. The Kubernetes API manifest includes the service label as a starting point.

For AWS Lambda use Datadog's documented Lambda extension/container instrumentation; `ddtrace-run` alone does not establish Lambda telemetry. Enable the AWS integration for SQS and Lambda metrics. Build monitors for queue age, DLQ count, worker errors and p95 API latency, and correlate with the application's event IDs. Do not put bearer tokens or incident descriptions in span tags. Datadog credentials, agents, dashboards and monitors are not provisioned here.

References: [Python tracing setup](https://docs.datadoghq.com/tracing/trace_collection/automatic_instrumentation/dd_libraries/python/), [Lambda container instrumentation](https://docs.datadoghq.com/serverless/aws_lambda/installation/python/?tab=containerimage).

## Kubernetes

`infra/k8s/workspace.yaml` provides two API replicas, two Celery worker replicas, a Service, and a minute outbox CronJob with overlapping jobs forbidden. It defines non-root execution, resource limits and API probes. MongoDB and Redis are external dependencies.

Publish the backend image to your registry and replace all `relay:0.1.0` image references. Create a `relay-runtime` Secret with the variables from `.env.example`, adapting Mongo/Redis addresses and secrets to your environment. Set `EVENT_TRANSPORT=celery`, `LEDGER_BACKEND=mongo` and the actual allowed API hostnames. Apply the manifest, inspect rollout status, then use `kubectl port-forward service/api 8000:8000` for an initial smoke test.

Do not run Celery beat alongside this CronJob. A public ingress, TLS, NetworkPolicies, autoscaling, external secret synchronization, frontend deployment and Datadog Agent installation remain environment-specific work. These manifests are a deployment starting point; no cluster rollout was performed here.
