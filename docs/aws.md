# AWS: the primary deployment

The SAM template builds three Python container Lambdas: DRF through Mangum, a scheduled outbox sweep, and the analysis worker. EventBridge routes the submitted event to SQS; DynamoDB stores conditional execution leases. MongoDB remains the canonical store and must be provided separately, for example by an Atlas cluster.

## Prepare and deploy

Install AWS CLI v2, SAM CLI and Docker. Select an account and region, set a budget alert, and provide a MongoDB deployment with TLS and scoped database credentials. Store a Secrets Manager JSON object containing `mongo_uri`, `api_token` and `django_secret_key`. Use generated secrets; do not use `.env.example` values remotely. Do not commit the secret or pass it in shell command history.

```bash
sam validate --lint --template-file infra/aws/template.yaml
sam build --template-file infra/aws/template.yaml
sam deploy --guided --resolve-image-repos
```

Use `eu-west-2` or override `AllowedHost` to the matching API Gateway hostname suffix. Supply the secret **name** as `RuntimeSecret`, choose a stack name, and review IAM changes before deployment. The secret values resolve into Lambda configuration at deployment; secret rotation requires refreshing the deployed function configuration.

The template supplies EventBridge publishing permission to the sweep and DynamoDB permissions to the worker; SAM adds the SQS polling permissions. Review generated IAM policies before operational deployment. CloudWatch alarms track a nonempty DLQ and queue age over five minutes. Alarm actions are intentionally unset: connect them to your incident channel.

## Mongo networking

This template does not create a VPC or open an Atlas access list. Choose a private networking arrangement and add Lambda VPC configuration, routing and endpoints/NAT as required, or a tightly scoped approved public connectivity arrangement. A Mongo connection string does not establish network reachability. Test all three functions' connectivity before exercising the pipeline. Private Lambdas also need routes to EventBridge, DynamoDB and SQS as applicable.

## Connect and verify

The `ApiUrl` output is the backend endpoint. For local UI testing:

```bash
cd frontend
API_PROXY_TARGET=https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com npm run dev
```

Enter the deployed workspace token, submit a non-sensitive alert, and confirm queued → ready → reviewed. The scheduled sweep runs once a minute. Retry the original POST with its original key and verify there is only one record. Inspect the worker's structured logs and the queue alarms.

For hosted frontend use, build the Vue app and serve it behind a same-origin `/api` reverse proxy to API Gateway. The supplied nginx configuration is for Compose's `api` service; adapt its upstream and TLS/server-name handling before deploying it to cloud hosting. This repository does not provision a public frontend CDN, domain or certificate.

The API has gateway request throttles and bounded Lambda concurrency. Those are guardrails, not user-level quotas. This single shared bearer token must be replaced by user identity, tenant-aware authorization and audit identity before opening the workspace to a team.

## Failure exercises

Stop publication or point the sweep at an unavailable broker: a successfully accepted record should remain queued and pending. Restore publication and check recovery. Inject a malformed message into a test queue; five receives should send it to the DLQ. Redrive a duplicate completed event; the worker should leave the incident and any review intact.

Use `sam delete` to remove the application when finished. Inspect retained/external resources, image repositories, secrets and MongoDB separately. No AWS deployment was performed while building this repository; CI validation/build is not a live deployment test.

References: [MongoDB atomicity](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/), [Lambda SQS error handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html), [SAM HTTP API](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-httpapi.html).
