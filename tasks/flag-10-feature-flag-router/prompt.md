# Feature Task: Mount the Signing Sub-API Only When `SIGNING_ENABLED` Is On

## Context
`src/gateway/` is a tiny in-process request router (no web framework). `create_app(env)` builds an `App` with the core routes (`GET /health`, `GET /version`) and the signing sub-API from `signing.py` (`POST /signing/sign`, `GET /signing/signatures/{signature_id}`, `POST /signing/verify`). Requests are made with `app.handle(method, path, body)` which returns a `Response(status, body)`; `app.routes()` lists `(METHOD, template)` pairs and `app.describe()` returns an OpenAPI-like dict whose `paths` maps each path template to a sorted list of lowercase methods.

## Problem
The signing sub-API is always mounted, so it is reachable (and advertised) in deployments where it must not exist. Its handlers are also sloppy: they do not validate input and use loose status codes.

## Requirements
1. Mount the signing routes only when the environment flag `SIGNING_ENABLED` is on. The flag is read from the `env` mapping passed to `create_app`; when `env` is `None`, `os.environ` is used.
2. The flag is on only for the values `1`, `true`, `yes`, `on`, compared case-insensitively with surrounding whitespace ignored. A missing flag, any other value (`0`, `false`, empty, `enabled`, `2`, ...) means disabled.
3. When disabled, every request under `/signing/` (any method) returns 404, and no `/signing/...` path appears in `app.routes()` or `app.describe()["paths"]`.
4. The flag is evaluated when the app is constructed, not at import time and not per request: two apps built with different envs coexist in one process, and mutating the env mapping (or `os.environ`) after construction does not change an existing app. Signature storage is per app.
5. Core routes (`/health`, `/version`) behave identically whether the flag is on or off, including `405` for a wrong method on a known path and `404` for an unknown path.
6. When enabled, `POST /signing/sign` (body `{"document_id": str, "signer": str}`) returns `201` with the record (`signature_id`, `document_id`, `signer`, `digest`). A non-object body returns `400`; a missing, non-string or blank (empty / whitespace-only) field returns `422`.
7. When enabled, `GET /signing/signatures/{signature_id}` returns `200` with the record, or `404` for an unknown id.
8. When enabled, `POST /signing/verify` (body `{"signature_id": str}`) returns `200` with `{"valid": True}` for a known id, `404` for an unknown id, `422` for a missing or non-string id, and `400` for a non-object body.

## Definition of Done
All existing tests pass, and the signing sub-API is absent (404, not listed) unless the flag is on, with the enabled handlers returning the status codes above.
