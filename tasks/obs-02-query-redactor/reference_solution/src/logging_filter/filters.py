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

# Regex to find URI query string in a string (allows internal commas, parentheses, internal single quotes,
# includes <> for idempotent passes over <redacted>, but stops at boundaries between multiple URLs/data structures).
_QUERY_PATTERN = re.compile(
    r"(\?[a-zA-Z0-9_\-.~%!$&+=:;@/?,<>()]*(?:\x27[a-zA-Z0-9_\-.~%!$&+=:;@?<>()][a-zA-Z0-9_\-.~%!$&+=:;@/?,<>()]*)*)"
)


def _is_sensitive_key(key: str) -> bool:
    unquoted = urllib.parse.unquote(key).lower()
    return unquoted in SENSITIVE_KEYS or unquoted.startswith("x-amz-")


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
            k, _v = part.split("=", 1)
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
            # Case A: If record.msg contains a query string with any format placeholders (e.g. %s, %d, %r, %(key)s),
            # we format message first so that stripping/replacing placeholders does not desync arguments.
            if (
                isinstance(record.msg, str)
                and "?" in record.msg
                and "%" in record.msg.split("?", 1)[1]
            ):
                formatted = record.getMessage()
                record.msg = redact_text(formatted)
                record.args = () if isinstance(record.args, tuple) else {}
            else:
                # Case B: Standard logging and access logs (e.g. Uvicorn):
                # 1. Redact args preserving exact tuple/list/dict structure so custom formatters
                # (like Uvicorn's AccessFormatter) can unpack args.
                if isinstance(record.args, tuple):
                    record.args = tuple(
                        redact_text(a) if isinstance(a, str) else a for a in record.args
                    )
                elif isinstance(record.args, list):
                    record.args = [
                        redact_text(a) if isinstance(a, str) else a for a in record.args
                    ]
                elif isinstance(record.args, dict):
                    new_dict: dict[str, Any] = {}
                    for k, v in record.args.items():
                        new_dict[k] = redact_text(v) if isinstance(v, str) else v
                    record.args = new_dict

                # 2. Redact record.msg if it is a string
                if isinstance(record.msg, str):
                    record.msg = redact_text(record.msg)
        except Exception:  # noqa: BLE001, S110
            # Filter contract: never raise, never drop record
            pass

        return True
