# Bugfix Task: Host Header Guard Rejects Every Real Deployment Host

## Context
`src/toolserver/host_guard.py` protects the HTTP transport of a tool server against DNS-rebinding attacks by validating the `Host` header of each request. It exposes two pure functions:

- `check_host(host_header, allowed_hosts=(), *, port=8080, default_port=80) -> tuple[int, str]`
- `guard_request(headers, allowed_hosts=(), *, port=8080, default_port=80) -> tuple[int, str]`, which looks up the `Host` header in a `Mapping[str, str]` (header names are case-insensitive) and delegates to `check_host`.

Both return `(status, reason)`: `(200, "ok")` when the request may proceed, otherwise an HTTP error status and a short non-empty human-readable reason.

## Problem
`check_host` ignores `allowed_hosts` and only accepts the literal `localhost:<port>`. Any server deployed behind a real name (`tools.example.test`, a load balancer, an IPv6 listener, ...) answers 421 to every request.

## Requirements
1. `allowed_hosts` is an iterable of patterns. Matching is case-insensitive for both the pattern and the `Host` header.
2. A pattern is one of: an exact host name (`tools.example.test`), a host with a port (`tools.example.test:8443`), a wildcard (`*.example.test`, optionally with a port), or a bracketed IPv6 literal (`[::1]`, `[::1]:8080`). A wildcard matches hosts with one or more extra labels below the suffix (`a.example.test`, `a.b.example.test`), but never the bare apex `example.test` and never look-alikes such as `evil-example.test`.
3. A pattern without a port accepts any port. A pattern with a port accepts only that port.
4. Default-port normalisation: a `Host` header without a port is treated as using `default_port`; a pattern port equal to `default_port` therefore matches a header without a port, and a header such as `tools.example.test:80` matches a pattern `tools.example.test:80` (with the default `default_port=80`).
5. IPv6 literals must be written in brackets in the `Host` header; the comparison uses the canonical address, so `[0:0:0:0:0:0:0:1]:8080` matches the pattern `[::1]:8080`. A bare `::1` (no brackets) is malformed.
6. When `allowed_hosts` is empty, the loopback names `localhost`, `127.0.0.1` and `[::1]` are accepted, but only on the listening `port` (as today, `localhost:8080` is accepted and `localhost:9999` is not).
7. When `allowed_hosts` is non-empty it fully replaces that loopback default: unlisted hosts, including `localhost`, are rejected.
8. A missing header (`None`) or an empty/whitespace-only value is rejected with status 400, as is any malformed value: userinfo (`user@host`), a path/query/fragment (`/`, `?`, `#`), embedded whitespace, an empty or non-numeric port, a port above 65535, or an unbalanced bracket. Malformed input is never allowed, even if a pattern would otherwise match its host part.
9. A well-formed `Host` that matches no pattern is rejected with status 421 (this is the DNS-rebinding case, e.g. `tools.example.test.evil.test` or `localhost.evil.test`).
10. `guard_request` finds `Host` regardless of the header-name case and returns the 400 rejection when it is absent.
11. A syntactically invalid pattern in `allowed_hosts` raises `ValueError`.
12. The functions stay pure: standard library only, no I/O.

## Definition of Done
Existing tests pass, and requests for every allowed form above succeed while rebinding and malformed hosts are rejected with the stated statuses.
