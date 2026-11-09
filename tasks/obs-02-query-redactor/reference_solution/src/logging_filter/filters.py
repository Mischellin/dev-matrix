from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any

SENSITIVE_KEYS = {
    "dl",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "code",
    "state",
    "signature",
}

# Regex to find URI query string in a string
_QUERY_PATTERN = re.compile(r"(\?[^ \t\r\n\"'\\]*)")


def _is_sensitive_key(key: str) -> bool:
    lk = key.lower()
    return lk in SENSITIVE_KEYS or lk.startswith("x-amz-")


def redact_query_string(query_str: str) -> str:
    """Scrub sensitive parameter values from '?key=val&key2=val2'."""
    if not query_str or not query_str.startswith("?"):
        return query_str

    raw_query = query_str[1:]
    parts = raw_query.split("&")
    new_parts = []
    for part in parts:
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            if _is_sensitive_key(k):
                new_parts.append(f"{k}=<redacted>")
            else:
                new_parts.append(part)
        else:
            new_parts.append(part)

    return "?" + "&".join(new_parts)


def redact_text(text: str) -> str:
    """Find query strings inside text and redact them."""
    def _replace(match: re.Match) -> str:
        return redact_query_string(match.group(1))

    return _QUERY_PATTERN.sub(_replace, text)


class RedactQuerySecretsFilter(logging.Filter):
    """Filter that replaces sensitive query parameters with <redacted>."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # If record.args is a tuple/list (e.g. uvicorn access log)
            if record.args:
                new_args: list[Any] = []
                for arg in record.args:
                    if isinstance(arg, str):
                        new_args.append(redact_text(arg))
                    else:
                        new_args.append(arg)
                record.args = tuple(new_args) if isinstance(record.args, tuple) else new_args

            # Also check record.msg if it's a string
            if isinstance(record.msg, str):
                record.msg = redact_text(record.msg)
        except Exception:
            # Filter contract: never raise, never drop record
            pass

        return True
