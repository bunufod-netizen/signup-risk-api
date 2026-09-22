# Signup Risk API

A self-hosted FastAPI service that provides non-intrusive email risk signals at signup. It validates syntax, resolves domain DNS and MX records, and checks local lists for disposable providers, common providers, role accounts, and common domain typos. It does **not** assert mailbox existence or perform SMTP verification.

## Install and run locally

Requires Python 3.11+. Create a virtual environment, install dependencies, then run the app:

```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The interactive OpenAPI documentation is at `http://127.0.0.1:8000/docs`.

## API

`GET /health` returns `{"status":"ok"}`.

`POST /check` accepts `{"email":"john@example.com"}` and returns syntax, DNS/MX, list-based signals, an explainable score (0–100), risk classification, and reasons.

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d '{"email":"admin@mailinator.com"}'
curl -X POST http://127.0.0.1:8000/bulk-check -H "Content-Type: application/json" -d '{"emails":["john@example.com","test@mailinator.com"]}'
```

Example response (DNS values vary by resolver):

```json
{"email":"admin@mailinator.com","valid_format":true,"domain":"mailinator.com","domain_exists":true,"mx_exists":true,"disposable":true,"role_account":true,"free_provider":false,"typo_suggestion":null,"risk":"high","risk_score":100,"reasons":["Disposable email provider","Role-based email address"]}
```

Bulk requests contain 1–100 emails and return one object per input. Each DNS operation has a configurable timeout and retry count. DNS timeouts, transient resolver failures, and network errors return `null` for unknown DNS fields plus a `DNS verification temporarily unavailable` reason; they are never treated as proof that a domain is nonexistent. Configure `DNS_TIMEOUT_SECONDS`, `DNS_RETRIES`, `MAX_BULK_EMAILS`, `CORS_ORIGINS`, and `LOG_LEVEL` in `.env` (see `.env.example`). CORS is disabled unless origins are explicitly configured.

## Docker

```bash
docker build -t signup-risk-api .
docker run -p 8000:8000 signup-risk-api
```

For production, set configuration with environment variables rather than committing a `.env` file:

```bash
docker run --rm -p 8000:8000 -e PORT=8000 -e RAPIDAPI_PROXY_SECRET="replace-with-provider-secret" signup-risk-api
```

`PORT` controls the production listener (default `8000`). `DNS_TIMEOUT_SECONDS`, `DNS_RETRIES`, `MAX_BULK_EMAILS`, `MAX_REQUEST_BODY_BYTES`, `CORS_ORIGINS`, and `LOG_LEVEL` are also configurable. The image uses a non-root account and production-only dependencies.

## RapidAPI and security

Set `RAPIDAPI_PROXY_SECRET` to the value configured for `X-RapidAPI-Proxy-Secret` in the RapidAPI provider dashboard. When it is set, `/check` and `/bulk-check` return `401` unless that header has the exact value; `/`, `/health`, and documentation remain available. This guards the origin against direct requests but does not replace network controls—also restrict origin ingress to RapidAPI/gateway infrastructure where the deployment platform supports it. RapidAPI remains responsible for customer keys, subscriptions, quotas, and billing.

Use `GET /health` for platform health checks; it intentionally requires no proxy secret and returns `{"status":"ok"}`. Request bodies over `MAX_REQUEST_BODY_BYTES` are rejected with HTTP 413 before parsing.

## Tests

```bash
pytest
```

## RapidAPI deployment

Deploy this container to a HTTPS-capable service, put authentication and per-client rate limiting at the gateway, and map RapidAPI plans/quotas there. Keep `data/disposable_domains.txt` refreshed from a vetted source and make DNS resolver behavior observable with metrics before broad rollout.
