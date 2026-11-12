"""Scrubbing of free-form event metadata before events leave the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_PATTERNS = ("password", "token", "secret", "api_key", "authorization")


def scrub_metadata(
    metadata: Mapping[Any, Any],
    *,
    patterns: tuple[str, ...] = SENSITIVE_PATTERNS,
    max_depth: int = 8,
) -> dict[Any, Any]:
    """Return a copy of ``metadata`` with sensitive values replaced by ``REDACTED``."""
    result: dict[Any, Any] = {}
    for key, value in metadata.items():
        if key in patterns:
            result[key] = REDACTED
        else:
            result[key] = value
    return result


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
