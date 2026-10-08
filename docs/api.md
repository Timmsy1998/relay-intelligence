# API

All incident endpoints require `Authorization: Bearer <RELAY_API_TOKEN>`. An unset token fails closed. This is a single-workspace secret, not user identity. Health and readiness endpoints are public and disclose only a status.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health/` | Process alive |
| GET | `/ready/` | Mongo reachable; 503 on failure |
| GET | `/api/incidents/` | Latest 100 incidents, newest first |
| POST | `/api/incidents/` | 202 new incident; 200 matching retry |
| GET | `/api/incidents/{uuid}/` | One incident, or 404 |
| POST | `/api/incidents/{uuid}/review/` | Reviewed incident; 409 stale version/state |

Submission requires a UUID `Idempotency-Key` header and JSON fields `title` (8–160 characters), `description` (20–12,000), `service` (1–80) and `severity` (`P1`, `P2`, `P3`). Reusing a key with different content returns 409. Keep the key on timeout/retry; create a new key for a different alert.

```bash
curl http://localhost:8000/api/incidents/ \
  -H 'Authorization: Bearer local-review-token' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 893b4db2-660a-4f66-8f45-d1b334177b24' \
  --data-binary @docs/sample-alert.json
```

Review body:

```json
{"decision":"accepted","note":"Confirmed backlog; consumer restored.","version":2}
```

Decision is `accepted` or `rejected`; the note is optional and capped at 2,000 characters. Read the returned incident version before reviewing. The backend never executes the suggested checks.

The browser uses a same-origin `/api` proxy; there is no permissive CORS policy. Vite proxies to localhost:8000 by default (`API_PROXY_TARGET` can change it). The nginx container proxies to the Compose API service. Tokens stay in browser memory, are never persisted to local storage and clear on reload/disconnect. Use TLS for any remote workspace.

The event envelope is defined in [event.schema.json](event.schema.json). It carries `event_id`, `incident_id`, `event_type`, `schema_version` and `occurred_at`; the worker loads alert content from MongoDB.
