from __future__ import annotations

import logging
import re
import urllib.parse

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

# Regex to find URI query string in a string (allows internal single quotes per RFC 3986 sub-delims)
_QUERY_PATTERN = re.compile(r"(\?[^ \t\r\n\"`\\]*)")


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
        qs = match.group(1)
        suffix = ""
        # If the query string was enclosed in quotes like 'GET /path?x=y', strip trailing quote
        if qs.endswith("'") and text[:match.start()].count("'") % 2 == 1:
            qs = qs[:-1]
            suffix = "'"
        return redact_query_string(qs) + suffix

    return _QUERY_PATTERN.sub(_replace, text)


class RedactQuerySecretsFilter(logging.Filter):
    """Filter that replaces sensitive query parameters with <redacted>."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Format message with args first to prevent placeholder stripping collisions
            formatted = record.getMessage()
            record.msg = redact_text(formatted)
            record.args = None
        except Exception:  # noqa: BLE001, S110
            # Filter contract: never raise, never drop record
            pass

        return True
