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
4. Supports standard `&` as well as matrix/semicolon `;` query parameter delimiters (e.g. `?page=1;token=SECRET`), Unicode (IRIs), and parameter values containing spaces or quotes.
   - A URL inside a quoted string ends at a closing quote followed by whitespace, `]`, `)`, `"`, the end of the message, or a comma that is itself followed by whitespace or a quote (`', ` or `','`). Several URLs in one message or in a list representation are therefore each redacted: `urls=['/a?page=1','/b?token=demo_secret']` becomes `urls=['/a?page=1','/b?token=<redacted>']`.
   - Any other apostrophe, bracket, parenthesis, asterisk, comma or slash inside a query value is part of the value and never ends the URL, so later secrets are still redacted: `/docs?token=first'SECOND&state=THIRD` -> `?token=<redacted>&state=<redacted>`; `/search?filter=john's&token=x` -> `?filter=john's&token=<redacted>`; `?filter=a',b&token=x` -> `?filter=a',b&token=<redacted>`; `?filter=a'[0]&token=x`, `?filter=(a)&token=x`, `?filter=*&token=x`, `?ids[]=1&token=x`, `?filter[name]=a&X-Amz-Signature=x` keep the harmless parameter and redact the secret; `?token=prefix(suffix)` and `?token=abc[0]` are redacted completely. Empty segments and delimiters are preserved (`?page=1&&limit=2&` is unchanged).
5. Path structure, parameter names, and order must be preserved.
6. Filter contract:
   - `filter(record: logging.LogRecord) -> bool` must always return `True` (never drop logs).
   - Preserving `record.args` collection structure: when query parameters or URIs are passed inside `record.args` (e.g. Uvicorn 5-tuple `(client_addr, method, full_path, http_version, status_code)`), strings inside `record.args` must be sanitized in-place, preserving collection type and length for downstream formatters.
   - The same applies to any printf placeholder type inside a query: `"/docs?code=%d"` with `(123,)` and `"/docs?token=%r"` with `("secret_token",)` both become `/docs?...=<redacted>`; a value with spaces or Unicode passed through `%s` (`"/docs?token=%s"` with `("ab SECRET",)`) becomes `/docs?token=<redacted>`. For a Uvicorn-style tuple whose path contains an apostrophe (`"/search?filter=a',b&token=SECRET"`), `record.args[2]` becomes `"/search?filter=a',b&token=<redacted>"` and the tuple type and length are preserved.
   - When `record.msg` contains query string formatting placeholders (e.g. `?code=%d` or `?token=%s`), format via `record.getMessage()`, redact the resulting query string into `record.msg`, and clear `record.args` (handling potential collisions between literal URL percent-encodings like `%20` and printf specifiers). A literal `%` that is not a valid printf specifier must not break formatting or corrupt the arguments: for `msg="100%? done %s"` with `args=("yes",)` `record.getMessage()` is still `100%? done yes` after filtering.
   - Must be idempotent (repeated filtering must not corrupt or double-redact).
   - Must never raise exceptions on malformed URLs or unexpected formats.

## Definition of Done
All existing tests pass and all acceptance tests verifying token scrubbing pass.
