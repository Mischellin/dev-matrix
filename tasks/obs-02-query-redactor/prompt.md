# Observability & Security: Redact Query String Secrets in Logs

## Context
Web servers (such as Uvicorn, Gunicorn, Starlette, or FastAPI) frequently log incoming request URIs with full query strings into access logs. Consequently, temporary credentials, single-use signed download tokens (`?dl=<jwt>`), OAuth authorization codes (`?code=...&state=...`), and presigned cloud object storage URLs (`?X-Amz-Signature=...`) leak into centralized log aggregation (e.g. Loki, Datadog, CloudWatch) in plain text.

## Requirements
Implement `RedactQuerySecretsFilter` as a standard `logging.Filter` in `src/logging_filter/filters.py`:
1. Replaces the values of the following sensitive query parameters with `<redacted>`:
   - `dl`
   - `token`
   - `access_token`
   - `refresh_token`
   - `id_token`
   - `code`
   - `state`
   - `signature`
   - Any parameter starting with `X-Amz-` (e.g. `X-Amz-Credential`, `X-Amz-Signature`, `X-Amz-Security-Token`).
2. Parameter names may be single or recursively percent-encoded (e.g. `%74oken` or `%2564l` -> `%64l` -> `dl`). They must be unquoted recursively until stable before evaluating sensitivity.
3. Harmless parameters (e.g. `page=`, `limit=`, `download=`, `status=`, `code_type=`, `dlx=`) must remain untouched.
4. Path structure, parameter names, and order must be preserved.
5. Filter contract:
   - `filter(record: logging.LogRecord) -> bool` must always return `True` (never drop logs).
   - Preserving `record.args` collection structure: when query parameters or URIs are passed inside `record.args` (e.g. Uvicorn 5-tuple `(client_addr, method, full_path, http_version, status_code)`), strings inside `record.args` must be sanitized in-place, preserving collection type and length for downstream formatters.
   - When `record.msg` contains query string formatting placeholders (e.g. `?code=%d` or `?token=%s`), format via `record.getMessage()`, redact the resulting query string into `record.msg`, and clear `record.args` (handling potential collisions between literal URL percent-encodings like `%20` and printf specifiers).
   - Must be idempotent (repeated filtering must not corrupt or double-redact).
   - Must never raise exceptions on malformed URLs or unexpected formats.

## Definition of Done
All existing tests pass and all acceptance tests verifying token scrubbing pass.
