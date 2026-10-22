"""The machine host's HTTP surface (TD-242): pages, machine routes and each project's API by its id.

Pages are at ``/``, machine routes under ``/api/next/`` (OwlBear's own decisions under ``/api/next/owlbear/``, TD-435)
and each project's own API, unchanged, under ``/p/{id}/api/next/``, chosen by a small ASGI dispatcher. One token and
the Host-header check guard everything; the token is no project boundary (one owner, loopback).
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import secrets
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import Field

from owlbear_delivery_next.local_system import data_repo, leases, local_home
from owlbear_delivery_next.machine_host import control, registry, versions
from owlbear_delivery_next.machine_host.machine import Machine, MachineError
from owlbear_delivery_next.project_host import api, decision_routes, impact_routes, pages
from owlbear_delivery_next.state_store import decision_impact

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from starlette.responses import Response
    from starlette.types import ASGIApp, Receive, Scope, Send

PROJECT = re.compile(r"^/p/([0-9a-f]{16})(?=/|$)")


class RegisterBody(api.Body):
    """The folder of a clone to serve."""

    path: str = Field(min_length=1, max_length=4096)


class SettingsBody(api.Body):
    """The machine's settings as the page edited them, and the revision it read."""

    rev: str = Field(min_length=1, max_length=64)
    settings: registry.Settings


class CurateBody(api.Body):
    """Which memory folder of the shared repository to curate now, or ``all``."""

    folder: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _local(host: str) -> bool:
    return host.rsplit(":", 1)[0] in api.LOCAL_HOSTS


class Dispatcher:
    """Send ``/p/{id}/…`` to that project's app, admitted by its gate; everything else to the machine's app."""

    def __init__(self, app: ASGIApp, machine: Machine, expected: bytes) -> None:
        """Wrap the machine's app."""
        self.app, self.machine, self.expected = app, machine, expected

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Route one connection; one that changes anything, or a chat's call, is the owner's use (§7)."""
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            asked = scope.get("method") != "GET" or b"x-owlbear-use" in headers
            if asked and secrets.compare_digest(headers.get(b"authorization", b""), self.expected):
                self.machine.auto.use()
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
        if self.machine.stopping.is_set() or (self.machine.updating and scope.get("method") != "GET"):
            said = (
                "OwlBear is stopping" if self.machine.stopping.is_set() else self.machine.updating
            )  # reads only (§5.3)
            await JSONResponse({"detail": said}, 503)(scope, receive, send)
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


def create(machine: Machine, ended: Callable[[], None] = lambda: None) -> ASGIApp:
    """The machine host's app: pages, the machine routes and every project's API.

    Its shutdown stops every project, then calls *ended*, inside Uvicorn's own shutdown: a stop signal is
    replayed once Uvicorn returns, so nothing after ``server.run`` may be relied on.
    """

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await asyncio.to_thread(machine.stop_all)
        ended()

    app = FastAPI(title="OwlBear", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
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
        return {
            "paused": machine.paused, "waiting": machine.waiting(), "projects": listed, "ending": machine.ending,
            "left": machine.left() if machine.ending else [],
            "update_while_paused": registry.load().settings.update_while_paused,
            "update": machine.updater.read(), "updated": machine.updated or versions.running(),
            "announce": machine.auto.read(),
        }  # fmt: skip

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

    @routes.get("/decisions/{decision_id}/changes")
    def pinned(decision_id: str) -> dict[str, Any]:
        """The Changes of every loaded project whose decision baseline pins the decision (TD-419 slice 5a)."""
        listed = [
            c | {"project": p.name, "pid": p.entry.id}
            for p in list(machine.projects.values())
            if p.store is not None and p.state == "loaded"
            for c in decision_impact.pinning(p.store, decision_id)
        ]
        return {"changes": listed}

    routes.include_router(impact_routes.router(_shared, lambda: _places(machine), [Depends(decision_routes.owner)]))

    def fenced(request: Request) -> None:
        """Fenced as a project's API is: nothing while stopping, reads only while an update runs (§5.3)."""
        if machine.stopping.is_set() or (machine.updating and request.method != "GET"):
            raise HTTPException(503, "OwlBear is stopping" if machine.stopping.is_set() else machine.updating)

    owlbear = decision_routes.router(_shared, lambda: decision_routes.OWLBEAR, lambda: _places(machine))
    routes.include_router(owlbear, prefix="/owlbear", dependencies=[Depends(fenced)])  # chats in OwlBear's workspace
    _machine_routes(routes, machine)
    _curation_routes(routes, machine)
    _update_routes(routes, machine)
    return routes


def _shared() -> data_repo.DataRepo | None:
    try:
        return data_repo.locate()
    except data_repo.DataRepoError:
        return None


def _places(machine: Machine) -> list[decision_impact.Place]:
    """Every project the machine serves, for a decision's impact; one not loaded says why (TD-428)."""
    return [
        decision_impact.Place(p.name, Path(p.entry.path), p.store)
        if p.store is not None and p.state == "loaded"
        else decision_impact.Place(p.name, why=f"{p.name} is {p.state}" + (f": {p.reason}" if p.reason else ""))
        for p in list(machine.projects.values())
    ]


def _machine_routes(routes: APIRouter, machine: Machine) -> None:
    """The machine's own values and its Resume and stop."""

    @routes.get("/machine")
    def values() -> dict[str, Any]:
        return machine_values(machine)

    @routes.put("/machine/settings")
    def configure(body: SettingsBody) -> dict[str, Any]:
        try:
            registry.configure(body.settings, body.rev)
        except registry.RegistryError as exc:
            raise HTTPException(409, str(exc)) from exc
        return values()

    @routes.post("/resume")
    def resume() -> dict[str, bool]:
        machine.resume()
        return {"paused": machine.paused}

    @routes.post("/pause")
    def pause() -> dict[str, bool]:
        machine.pause()
        return {"paused": machine.paused}

    @routes.post("/pause-stop")
    def pause_stop() -> dict[str, bool]:
        machine.pause_stop()
        return {"paused": machine.paused, "ending": machine.ending}

    @routes.post("/stop")
    def stop() -> dict[str, bool]:
        machine.say("stopping: asked through the stop route")
        machine.on_stop()
        return {"stopping": True}


def _curation_routes(routes: APIRouter, machine: Machine) -> None:
    """Automatic memory curation: each folder's last run, and the Maintenance page's button."""

    @routes.get("/curation")
    def curation() -> dict[str, Any]:
        """Each memory folder's last automatic curation, and what waits (item 5 slice 4)."""
        return machine.curation.read()

    @routes.post("/curation")
    def curate(body: CurateBody) -> dict[str, Any]:
        """The Maintenance page's button: curate one folder, or all, now; also while paused (the owner, 2026-10-22)."""
        if why := machine.updating or ("OwlBear is stopping" if machine.stopping.is_set() else ""):
            raise HTTPException(503, why)
        try:
            started = machine.curation.start(body.folder)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return machine.curation.read() | {"started": started}


def machine_values(machine: Machine) -> dict[str, Any]:
    """The machine's own values (TD-243): its settings, Resume, the login item and a kept legacy runtime."""
    login = control.autostarts() if sys.platform == "darwin" else "not available on this system"
    saved = registry.load()
    return {
        "paused": machine.paused, "resumed_at": saved.resumed_at, "login_item": login,
        "settings": saved.settings.model_dump(), "settings_rev": registry.revision(saved.settings),
        "legacy": [str(p) for p in versions.legacy()],
    }  # fmt: skip


def _update_routes(routes: APIRouter, machine: Machine) -> None:
    """Run updates now, its state, and the removal of the runtime the first update put away (self-update §3, §5)."""

    @routes.get("/update")
    def update_state() -> dict[str, Any]:
        return machine.updater.read()

    @routes.post("/update")
    def update_now() -> dict[str, Any]:
        """Run updates now (TD-352, TD-353): no waiting for idle time; it still waits for running steps."""
        return machine.updater.run_now()

    @routes.post("/seen")
    def seen() -> dict[str, bool]:
        """A page's word that the owner is at it, and Postpone: use, counted where every request comes in (§7)."""
        return {"seen": True}

    @routes.post("/machine/legacy/remove")
    def remove_legacy() -> dict[str, Any]:
        """Remove the runtime folders the first update put away; never a running one (§3)."""
        for path in versions.legacy():
            if path.resolve() == (local_home.root() / local_home.RUNTIME).resolve():
                raise HTTPException(409, f"{path} is the running version")
            if users := leases.unpinned():  # it holds no leases: processes started through the alias before
                pids = ", ".join(map(str, users[:5]))
                raise HTTPException(409, f"processes {pids} still run it: reload the VS Code windows, then try again")
            shutil.rmtree(path)
        return machine_values(machine)
