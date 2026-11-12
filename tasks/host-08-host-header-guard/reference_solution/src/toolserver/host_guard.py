"""Host header validation for the tool-server HTTP transport (DNS-rebinding guard)."""

import ipaddress
import re
from collections.abc import Iterable, Mapping

OK = (200, "ok")

_NAME_RE = re.compile(r"[a-z0-9_]([a-z0-9_.-]*[a-z0-9_])?")
_LOOPBACK = ("localhost", "127.0.0.1", "[::1]")


def _parse(value: str, *, pattern: bool = False) -> tuple[str, int | None]:
    """Split ``host[:port]`` into a canonical host and an optional port."""
    value = value.strip().lower() if pattern else value.lower()
    if value.startswith("["):
        end = value.find("]")
        if end < 0:
            raise ValueError("unbalanced bracket")
        inner, rest = value[1:end], value[end + 1 :]
        host = f"[{ipaddress.IPv6Address(inner)}]"
        if rest and not rest.startswith(":"):
            raise ValueError("garbage after IPv6 literal")
        port_text = rest[1:] if rest else None
    else:
        if value.count(":") > 1:
            raise ValueError("bare IPv6 literal")
        host, sep, port_text = value.partition(":")
        port_text = port_text if sep else None
        body = host[2:] if pattern and host.startswith("*.") else host
        if not _NAME_RE.fullmatch(body):
            raise ValueError("invalid host name")
    if port_text is None:
        return host, None
    if not (port_text.isascii() and port_text.isdigit()) or not 0 < int(port_text) < 65536:
        raise ValueError("invalid port")
    return host, int(port_text)


def _matches(host: str, port: int, pattern: tuple[str, int | None]) -> bool:
    p_host, p_port = pattern
    if p_port is not None and p_port != port:
        return False
    if p_host.startswith("*."):
        suffix = p_host[1:]
        return host.endswith(suffix) and len(host) > len(suffix)
    return host == p_host


def check_host(
    host_header: str | None,
    allowed_hosts: Iterable[str] = (),
    *,
    port: int = 8080,
    default_port: int = 80,
) -> tuple[int, str]:
    """Validate a ``Host`` header value and return ``(status, reason)``."""
    if host_header is None or not host_header.strip():
        return 400, "missing host header"
    try:
        host, req_port = _parse(host_header)
    except ValueError:
        return 400, "malformed host header"
    patterns_raw = list(allowed_hosts)
    if patterns_raw:
        patterns = [_parse(p, pattern=True) for p in patterns_raw]
    else:
        patterns = [_parse(f"{name}:{port}") for name in _LOOPBACK]
    effective = default_port if req_port is None else req_port
    if any(_matches(host, effective, p) for p in patterns):
        return OK
    return 421, "host not allowed"


def guard_request(
    headers: Mapping[str, str],
    allowed_hosts: Iterable[str] = (),
    *,
    port: int = 8080,
    default_port: int = 80,
) -> tuple[int, str]:
    """Validate the ``Host`` header found in a request header mapping."""
    host = None
    for name, value in headers.items():
        if name.lower() == "host":
            host = value
            break
    return check_host(host, allowed_hosts, port=port, default_port=default_port)
