# Security Task: Redact Sensitive Values at Any Depth in Event Metadata

## Context
`src/pipeline/scrub.py` is the last step of a fictional analytics pipeline. Every event carries a free-form `metadata` dict supplied by client SDKs, and `scrub_event` / `scrub_metadata` must remove credentials from it before the event is stored or forwarded. A redacted value is replaced with the constant `REDACTED` (`"[REDACTED]"`). The list of sensitive key patterns is `SENSITIVE_PATTERNS`.

## Problem
`scrub_metadata` only inspects the top level of the dict and only matches keys that are exactly equal (case-sensitive) to a pattern. Credentials nested in dicts, lists or tuples (`{"request": {"headers": {"Authorization": "Bearer ..."}}}`) or stored under keys such as `"User_Password"` or `"X-Api_Key"` leak into storage.

## Requirements
Public API: `scrub_metadata(metadata, *, patterns=SENSITIVE_PATTERNS, max_depth=8)` and `scrub_event(event, *, patterns=SENSITIVE_PATTERNS, max_depth=8)`. Keep the signatures and the `REDACTED` / `SENSITIVE_PATTERNS` names.

1. A key is sensitive if it is a `str` that contains any pattern as a substring, compared case-insensitively (`"X-Authorization"`, `"DB_PASSWORD"`, `"refresh_token_v2"` are sensitive). Keys that are not strings (ints, tuples, `None`, ...) are never sensitive themselves, but their values must still be traversed and scrubbed.
2. The value of a sensitive key is replaced entirely with `REDACTED`, whatever its type (string, number, `None`, dict, list).
3. Scrubbing is recursive through dicts, lists and tuples at any depth, including dicts inside lists and lists inside tuples. Plain string items of a list are never redacted by themselves.
4. The input is never mutated, at any depth. The result must not share any mutable dict or list with the input.
5. Types are preserved: dicts stay dicts, lists stay lists, tuples stay tuples; non-sensitive scalars (str, int, float, bool, `None`) and all non-sensitive keys, including non-string keys, are returned unchanged.
6. Cycles must not cause an exception or infinite recursion. A container that refers back to one of its own ancestors is replaced at that position with `REDACTED`. The same object appearing several times without forming a cycle (a shared reference) is scrubbed normally everywhere.
7. `max_depth` limits traversal. The top-level `metadata` mapping is at depth 0, its values are at depth 1, their children at depth 2, and so on (list and tuple items count as one level deeper than the list). Any value located deeper than `max_depth` is replaced with `REDACTED`, whether it is a container or a scalar. With a large enough `max_depth` nothing is cut off.
8. The `patterns` argument replaces the default patterns when given and uses the same case-insensitive substring matching. `scrub_event` passes `patterns` and `max_depth` to `scrub_metadata`, returns a new dict, leaves all other event fields as they are, and returns an event without a dict `metadata` unchanged in content.

## Definition of Done
All existing tests pass, and new tests demonstrate that nested, mixed-case and substring-matching keys are redacted, that the input is never mutated, and that cycles and the depth limit are handled.
