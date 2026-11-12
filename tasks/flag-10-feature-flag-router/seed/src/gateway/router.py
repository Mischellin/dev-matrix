"""Minimal method + path-template router (no web framework)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    body: Any = None
    params: dict[str, str] | None = None


@dataclass(frozen=True)
class Response:
    status: int
    body: Any = None


Handler = Callable[[Request], Response]


def _split(path: str) -> list[str]:
    return [part for part in path.split("/") if part]


def _match(template: str, path: str) -> dict[str, str] | None:
    t_parts, p_parts = _split(template), _split(path)
    if len(t_parts) != len(p_parts):
        return None
    params: dict[str, str] = {}
    for t_part, p_part in zip(t_parts, p_parts):
        if t_part.startswith("{") and t_part.endswith("}"):
            params[t_part[1:-1]] = p_part
        elif t_part != p_part:
            return None
    return params


class Router:
    """Holds (method, path template, handler) entries; `{name}` segments capture params."""

    def __init__(self) -> None:
        self._routes: list[tuple[str, str, Handler]] = []

    def add(self, method: str, template: str, handler: Handler) -> None:
        self._routes.append((method.upper(), template, handler))

    def routes(self) -> list[tuple[str, str]]:
        return sorted((m, t) for m, t, _ in self._routes)

    def dispatch(self, request: Request) -> Response:
        path_matched = False
        for method, template, handler in self._routes:
            params = _match(template, request.path)
            if params is None:
                continue
            path_matched = True
            if method == request.method.upper():
                return handler(Request(request.method, request.path, request.body, params))
        if path_matched:
            return Response(405, {"error": "method not allowed"})
        return Response(404, {"error": "not found"})
