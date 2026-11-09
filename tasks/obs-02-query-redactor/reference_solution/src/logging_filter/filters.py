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

# Regex to find URI query string in a string (allows RFC 3986 sub-delims including *, !, parentheses, commas,
# internal single quotes, and <> for idempotent passes, while respecting boundaries between multiple URLs/data structures).
_QUERY_PATTERN = re.compile(
    r"(\?[a-zA-Z0-9_\-.~%!$&+=:;@/?,<>()*!]*(?:\x27[a-zA-Z0-9_\-.~%!$&+=:;@?<>()*!][a-zA-Z0-9_\-.~%!$&+=:;@/?,<>()*!]*)*)"
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
            new_parts.append("")
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


def _scrub_args_in_place(record: logging.LogRecord) -> None:
    """Sanitize secrets inside record.args while strictly preserving collection structure."""
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


class RedactQuerySecretsFilter(logging.Filter):
    """Filter that replaces sensitive query parameters with <redacted>."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # 1. Always scrub record.args first so secrets never leak even if template formatting fails
            _scrub_args_in_place(record)

            # 2. If record.msg contains placeholders within query string, format and redact
            if isinstance(record.msg, str) and "?" in record.msg:
                # Protect literal URL percent-encodings like %20, %74, %2F from crashing printf formatters
                escaped_msg = re.sub(r"%(?=[0-9a-fA-F]{2})", "%%", record.msg)
                if "%" in escaped_msg.split("?", 1)[1]:
                    try:
                        formatted = escaped_msg % record.args if record.args else escaped_msg
                        record.msg = redact_text(formatted)
                        record.args = () if isinstance(record.args, tuple) else {}
                    except Exception:  # noqa: BLE001
                        # If printf formatting fails, still redact raw record.msg
                        record.msg = redact_text(record.msg)
                else:
                    record.msg = redact_text(record.msg)
            elif isinstance(record.msg, str):
                record.msg = redact_text(record.msg)
        except Exception:  # noqa: BLE001, S110
            # Filter contract: never raise, never drop record
            pass

        return True
