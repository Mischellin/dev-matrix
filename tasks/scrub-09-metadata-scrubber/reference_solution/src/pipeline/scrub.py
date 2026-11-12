"""Scrubbing of free-form event metadata before events leave the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_PATTERNS = ("password", "token", "secret", "api_key", "authorization")


def _is_sensitive(key: Any, patterns: tuple[str, ...]) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(p.lower() in lowered for p in patterns)


def _scrub(
    value: Any,
    patterns: tuple[str, ...],
    max_depth: int,
    depth: int,
    path: frozenset[int],
) -> Any:
    if depth > max_depth:
        return REDACTED
    if not isinstance(value, (Mapping, list, tuple)):
        return value
    if id(value) in path:
        return REDACTED
    path = path | {id(value)}
    if isinstance(value, Mapping):
        return {
            k: REDACTED
            if _is_sensitive(k, patterns)
            else _scrub(v, patterns, max_depth, depth + 1, path)
            for k, v in value.items()
        }
    items = [_scrub(v, patterns, max_depth, depth + 1, path) for v in value]
    return items if isinstance(value, list) else tuple(items)


def scrub_metadata(
    metadata: Mapping[Any, Any],
    *,
    patterns: tuple[str, ...] = SENSITIVE_PATTERNS,
    max_depth: int = 8,
) -> dict[Any, Any]:
    """Return a copy of ``metadata`` with sensitive values replaced by ``REDACTED``."""
    return _scrub(metadata, patterns, max_depth, 0, frozenset())


def scrub_event(
    event: Mapping[str, Any],
    *,
    patterns: tuple[str, ...] = SENSITIVE_PATTERNS,
    max_depth: int = 8,
) -> dict[str, Any]:
    """Return a shallow copy of ``event`` whose ``metadata`` dict is scrubbed."""
    scrubbed = dict(event)
    metadata = scrubbed.get("metadata")
    if isinstance(metadata, Mapping):
        scrubbed["metadata"] = scrub_metadata(metadata, patterns=patterns, max_depth=max_depth)
    return scrubbed
