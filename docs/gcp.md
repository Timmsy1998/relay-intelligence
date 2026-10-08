# Google Cloud alternative

The same Python API and worker run in containers on Cloud Run. Pub/Sub replaces EventBridge/SQS, and the worker uses MongoDB leases rather than DynamoDB. This path includes a real publishing adapter and push receiver; provisioning is an operator-led recipe rather than a second infrastructure template.

## Resources

Create an Artifact Registry repository, a Pub/Sub topic, a dead-letter topic, a push subscription and dedicated service accounts for API, outbox job, worker and push delivery. Provide a TLS-enabled MongoDB deployment and Secret Manager entries for its URI, the Django secret and workspace token. Grant the runtime identities access only to their needed secrets.

Build and publish `infra/gcp/Dockerfile` from the repository root. It installs `requirements-gcp.lock` and listens on port 8000. Deploy the API image with `--port 8000`, bounded maximum instances, `DJANGO_ALLOWED_HOSTS` set to its Cloud Run hostname and `RELAY_URLCONF=relay.urls`. Supply secrets through Secret Manager bindings. The API can be externally reachable; incident endpoints still require the workspace token.

Deploy **a separate private worker service** with:

```text
--no-allow-unauthenticated
--port 8000
--timeout 60
--concurrency 1
RELAY_URLCONF=relay.gcp
LEDGER_BACKEND=mongo
```

Bind its Mongo and Django secrets. Its sole endpoint is `/pubsub/`; it is never mounted on the normal API. Cloud Run IAM must authenticate the Google-signed OIDC push token before Django. Do not make this receiver public: it intentionally relies on that infrastructure authentication boundary.

Give the push service account `roles/run.invoker` on the worker only. Configure the subscription with push URL `https://WORKER_HOST/pubsub/`, that service account as the OIDC identity and the worker service URL as audience. Allow the Pub/Sub service agent to mint the required token. Give the service agent the documented subscriber/publisher permissions for dead-letter forwarding. Configure a 60-second acknowledgement deadline, exponential retry and a finite dead-letter delivery threshold.

## Outbox job

Create a Cloud Run Job using the same image with command `python` and arguments `-c`, `from relay.transport import dispatch; print(dispatch())`. Configure:

```text
EVENT_TRANSPORT=pubsub
PUBSUB_TOPIC=projects/PROJECT_ID/topics/relay-incidents
MONGO_DATABASE=relay
```

Supply Mongo credentials and grant the job identity `roles/pubsub.publisher` on that topic. Schedule one execution per minute with Cloud Scheduler calling the Cloud Run Jobs API using an **OAuth** service-account token. Give the scheduler identity permission to run this job. Job overlap may duplicate publication; the worker contract tolerates duplicates. Monitor pending outbox count because transport failures are logged and retained for the next sweep, rather than making the job exit nonzero.

The publisher waits for the publish acknowledgement before marking the outbox. The receiver returns 204 on successful or duplicate processing and 503 on transient failure. Malformed payloads return 400 and will retry under Pub/Sub's policy until dead-letter handling applies.

## Verify and operate

Check secret access, Mongo networking, OIDC audience and private worker IAM first. Submit an alert to the API, wait for the scheduled job, then inspect the analysis and saved review. Disable worker invocation temporarily and confirm retries/queue-age monitoring; restore it and confirm recovery. Configure Pub/Sub backlog, oldest unacknowledged message and dead-letter alerts. Use the same-origin frontend proxy approach described in the AWS guide.

Cloud Run, Pub/Sub and Scheduler resources were not deployed in this build. Validate this recipe in a test project before using it remotely. GCP IAM/networking and frontend hosting are explicitly outside the supplied manifests.

References: [Cloud Run Pub/Sub integration](https://cloud.google.com/run/docs/tutorials/pubsub), [authenticated push](https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions), [dead-letter topics](https://cloud.google.com/pubsub/docs/dead-letter-topics).
