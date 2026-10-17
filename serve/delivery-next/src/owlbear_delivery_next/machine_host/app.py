"""The machine host's HTTP surface (TD-242): pages, machine routes and each project's API by its id.

Pages are at ``/``, machine routes under ``/api/next/`` and each project's own API, unchanged, under
``/p/{id}/api/next/``, chosen by a small ASGI dispatcher. One token and the Host-header check guard everything;
the token is no project boundary (one owner, loopback).
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import Field

from owlbear_delivery_next.machine_host.machine import Machine, MachineError
from owlbear_delivery_next.project_host import api, pages

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.responses import Response
    from starlette.types import ASGIApp, Receive, Scope, Send

PROJECT = re.compile(r"^/p/([0-9a-f]{16})(?=/|$)")


class RegisterBody(api.Body):
    """The folder of a clone to serve."""

    path: str = Field(min_length=1, max_length=4096)


def _local(host: str) -> bool:
    return host.rsplit(":", 1)[0] in api.LOCAL_HOSTS


class Dispatcher:
    """Send ``/p/{id}/…`` to that project's app, admitted by its gate; everything else to the machine's app."""

    def __init__(self, app: ASGIApp, machine: Machine, expected: bytes) -> None:
        """Wrap the machine's app."""
        self.app, self.machine, self.expected = app, machine, expected

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Route one connection."""
        found = PROJECT.match(scope.get("path", "")) if scope["type"] == "http" else None
        if found is None:
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        if not _local(headers.get(b"host", b"").decode("latin-1")):  # DNS rebinding
            await JSONResponse({"detail": "host not allowed"}, 403)(scope, receive, send)
            return
        if not secrets.compare_digest(headers.get(b"authorization", b""), self.expected):
            await JSONResponse({"detail": "token required"}, 401)(scope, receive, send)
            return
        p = self.machine.projects.get(found[1])
        if p is None or p.app is None or p.state != "loaded":
            said = f"{p.name} is {p.state}" + (f": {p.reason}" if p.reason else "") if p else "no such project"
            await JSONResponse({"detail": said}, 404)(scope, receive, send)
            return
        if not p.gate.enter():
            await JSONResponse({"detail": f"{p.name} is stopping"}, 503)(scope, receive, send)
            return
        try:
            await p.app({**scope, "root_path": scope.get("root_path", "") + found[0]}, receive, send)
        finally:
            p.gate.leave()


def create(machine: Machine) -> ASGIApp:
    """The machine host's app: pages, the machine routes and every project's API."""
    app = FastAPI(title="OwlBear", docs_url=None, redoc_url=None, openapi_url=None)
    expected = f"Bearer {machine.record.token}".encode()

    @app.middleware("http")
    async def local_only(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not _local(request.headers.get("host", "")):  # DNS rebinding
            return JSONResponse({"detail": "host not allowed"}, status_code=403)
        return await call_next(request)

    def auth(request: Request) -> None:
        if not secrets.compare_digest(request.headers.get("authorization", "").encode(), expected):
            raise HTTPException(401, "token required")

    pages.assets(app)
    for path, html in pages.pages().items():
        app.add_api_route(path, api.fixed_page(html), methods=["GET"], response_class=HTMLResponse)
    app.include_router(_routes(machine), dependencies=[Depends(auth)])
    return Dispatcher(app, machine, expected)


def _routes(machine: Machine) -> APIRouter:
    routes = APIRouter(prefix="/api/next")

    def answer(work: Callable[[], Any]) -> Any:  # noqa: ANN401 - each route's own answer
        try:
            return work()
        except MachineError as exc:
            raise HTTPException(exc.status, exc.text) from exc

    @routes.get("/projects")
    def projects() -> dict[str, Any]:
        listed = [p.info() for p in list(machine.projects.values())]
        return {"paused": machine.paused, "waiting": machine.waiting(), "projects": listed}

    @routes.post("/projects")
    def register(body: RegisterBody) -> dict[str, Any]:
        return answer(lambda: machine.register(Path(body.path).expanduser()).info())

    @routes.delete("/projects/{pid}")
    def remove(pid: str) -> dict[str, str]:
        answer(lambda: machine.remove(pid))
        return {"removed": pid}

    @routes.post("/projects/{pid}/adopt")
    def adopt(pid: str) -> dict[str, Any]:
        return answer(lambda: machine.adopt(pid).info())

    @routes.post("/resume")
    def resume() -> dict[str, bool]:
        machine.resume()
        return {"paused": machine.paused}

    @routes.post("/stop")
    def stop() -> dict[str, bool]:
        machine.on_stop()
        return {"stopping": True}

    return routes
