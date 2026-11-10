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
# square brackets (e.g. ids[]=1, filter[name]=a), quoted values with spaces/symbols (e.g. %r), Unicode/IRIs,
# spaces inside query values not ending the URL, internal single quotes, and <> for idempotent passes,
# while respecting boundaries between multiple URLs/data structures).
_CHARS = r"a-zA-Z0-9_\-.~%!$&+=:;@/?,<>()*!\[\]\u0080-\uffff"
_QUERY_PATTERN = re.compile(
    rf"(\?(?:=\x27[^\x27]*\x27|=\x22[^\x22]*\x22|[{_CHARS}]| (?!HTTP/|[0-9]{{3}}|\x27|\"|\)|\]|$)|(?!\x27(?:\s|$|,[\s\x27]|\]|\)|\"))[\x27])*)"
)


def _is_sensitive_key(key: str) -> bool:
    prev = key
    while True:
        unquoted = urllib.parse.unquote(prev)
        if unquoted == prev:
            break
        prev = unquoted
    lk = prev.lower()
    return lk in SENSITIVE_KEYS or lk.startswith("x-amz-")


def redact_query_string(query_str: str) -> str:
    """Scrub sensitive parameter values from '?key=val&key2=val2'."""
    if not query_str or not query_str.startswith("?"):
        return query_str

    raw_query = query_str[1:]
    tokens = re.split(r"([&;])", raw_query)
    new_tokens = []
    for token in tokens:
        if token in ("&", ";"):
            new_tokens.append(token)
            continue
        if not token:
            new_tokens.append("")
            continue
        if "=" in token:
            k, _v = token.split("=", 1)
            if _is_sensitive_key(k):
                new_tokens.append(f"{k}=<redacted>")
            else:
                new_tokens.append(token)
        else:
            new_tokens.append(token)

    return "?" + "".join(new_tokens)


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
            # 1. Always scrub record.args first so sensitive values never leak
            _scrub_args_in_place(record)

            # 2. Process record.msg
            if isinstance(record.msg, str):
                if "?" in record.msg and record.args:
                    # If query string contains placeholders, merge them via getMessage()
                    try:
                        formatted = record.getMessage()
                        record.msg = redact_text(formatted)
                        record.args = () if isinstance(record.args, tuple) else {}
                    except TypeError:
                        # Collision between literal URL percent encodings (e.g. %20) and printf width specs
                        try:
                            tmp_msg = re.sub(r"%(?=[0-9a-fA-F]{2})", "%%", record.msg)
                            formatted = tmp_msg % record.args
                            record.msg = redact_text(formatted)
                            record.args = () if isinstance(record.args, tuple) else {}
                        except Exception:  # noqa: BLE001
                            record.msg = redact_text(record.msg)
                            record.args = () if isinstance(record.args, tuple) else {}
                    except Exception:  # noqa: BLE001
                        record.msg = redact_text(record.msg)
                        record.args = () if isinstance(record.args, tuple) else {}
                else:
                    record.msg = redact_text(record.msg)
        except Exception:  # noqa: BLE001, S110
            # Filter contract: never raise, never drop record
            pass

        return True
