"""Application factory: wires the core routes and the signing sub-API."""

import os
from collections.abc import Mapping
from typing import Any

from .router import Request, Response, Router
from .signing import mount_signing


def _health(request: Request) -> Response:
    return Response(200, {"status": "ok"})


def _version(request: Request) -> Response:
    return Response(200, {"version": "1.0"})


class App:
    def __init__(self, env: Mapping[str, str]) -> None:
        self.env = env
        self.router = Router()
        self.router.add("GET", "/health", _health)
        self.router.add("GET", "/version", _version)
        mount_signing(self.router)

    def handle(self, method: str, path: str, body: Any = None) -> Response:
        return self.router.dispatch(Request(method, path, body))

    def routes(self) -> list[tuple[str, str]]:
        """Sorted (METHOD, path template) pairs of all mounted routes."""
        return self.router.routes()

    def describe(self) -> dict[str, Any]:
        """OpenAPI-like description: `paths` maps template -> sorted lowercase methods."""
        paths: dict[str, list[str]] = {}
        for method, template in self.routes():
            paths.setdefault(template, []).append(method.lower())
        return {"title": "gateway", "paths": paths}


def create_app(env: Mapping[str, str] | None = None) -> App:
    return App(os.environ if env is None else env)
