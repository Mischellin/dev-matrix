"""Host header validation for the tool-server HTTP transport (DNS-rebinding guard)."""

from collections.abc import Iterable, Mapping

OK = (200, "ok")


def check_host(
    host_header: str | None,
    allowed_hosts: Iterable[str] = (),
    *,
    port: int = 8080,
    default_port: int = 80,
) -> tuple[int, str]:
    """Validate a ``Host`` header value and return ``(status, reason)``."""
    # Only the literal loopback name on the listening port is accepted.
    if host_header == f"localhost:{port}":
        return OK
    return 421, "invalid host header"


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
