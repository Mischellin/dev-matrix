# Observability & Security: Redact Query String Secrets in Logs

## Context
Web servers (such as Uvicorn, Gunicorn, Starlette, or FastAPI) frequently log incoming request URIs with full query strings into access logs. Consequently, temporary credentials, single-use signed download tokens (`?dl=<jwt>`), OAuth authorization codes (`?code=...&state=...`), and presigned cloud object storage URLs (`?X-Amz-Signature=...`) leak into centralized log aggregation (e.g. Loki, Datadog, CloudWatch) in plain text.

## Requirements
Implement `RedactQuerySecretsFilter` as a standard `logging.Filter` in `src/logging_filter/filters.py`:
1. Replaces the values of the following sensitive query parameters (including URL percent-encoded names such as `%74oken` or `%64l`) with `<redacted>`:
   - `dl`
   - `token`
   - `access_token`
   - `refresh_token`
   - `id_token`
   - `code`
   - `state`
   - `signature`
   - Any parameter starting with `X-Amz-` (e.g. `X-Amz-Credential`, `X-Amz-Signature`, `X-Amz-Security-Token`).
2. Harmless parameters (e.g. `page=`, `limit=`, `download=`, `status=`, `code_type=`, `dlx=`) must remain untouched.
3. Path structure, parameter names, and order must be preserved.
4. Filter contract:
   - `filter(record: logging.LogRecord) -> bool` must always return `True` (never drop logs).
   - Must handle records formatted via template `msg % args` (such as standard Uvicorn access log lines `%s - "%s %s HTTP/%s" %d`).
   - Must be idempotent (repeated filtering must not corrupt or double-redact).
   - Must never raise exceptions on malformed URLs or unexpected formats.

## Definition of Done
All existing tests pass and all acceptance tests verifying token scrubbing pass.
