"""Cockpit FastAPI application."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
import threading
import webbrowser
from datetime import UTC, datetime
from http.client import HTTPConnection
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from owlbear_memory.errors import (
    ConcurrencyError as MemoryConcurrencyError,
)
from owlbear_memory.errors import (
    NotFoundError as MemoryNotFoundError,
)
from owlbear_memory.errors import (
    TransitionError as MemoryTransitionError,
)

from owlbear_cockpit.deps import get_ideas_path, get_memory_engine
from owlbear_cockpit.models import CockpitInstance, HealthModule, IdeasHealth
from owlbear_cockpit.routes.ideas import router as ideas_router
from owlbear_cockpit.routes.memory import router as memory_router
from owlbear_cockpit.routes.target_work import (
    handle_target_http_error,
    handle_target_validation_error,
)
from owlbear_cockpit.routes.target_work import router as target_work_router
from owlbear_cockpit.target_context import load_target_context
from owlbear_delivery.storage_io import atomic_write

_DEFAULT_PORT = 8420
_MAX_PORT = 65535
_HTTP_OK = 200
_DIST_DIR = Path(__file__).parent.parent.parent / "dist"
_HOST = "127.0.0.1"
_MEMORY_DIR = Path(".owlbear/memory")
_NO_OPEN_ENV = "COCKPIT_NO_OPEN"
_PORT_ENV = "COCKPIT_PORT"
_REGISTRY_ENV = "OWLBEAR_COCKPIT_REGISTRY"

app = FastAPI(title="OwlBear Cockpit")
app.add_exception_handler(HTTPException, handle_target_http_error)
app.add_exception_handler(RequestValidationError, handle_target_validation_error)
app.include_router(target_work_router, prefix="/api")
app.include_router(ideas_router, prefix="/api")
app.include_router(memory_router, prefix="/api")

_MemoryEngine = Annotated[object, Depends(get_memory_engine)]
_IdeasPath = Annotated[Path, Depends(get_ideas_path)]


def _get_health_memory_engine() -> object | None:
    try:
        return get_memory_engine()
    except AttributeError:
        return None


def _get_health_ideas_path() -> Path:
    try:
        return get_ideas_path()
    except AttributeError:
        return Path("ideas.md")


_HealthMemoryEngine = Annotated[object | None, Depends(_get_health_memory_engine)]
_HealthIdeasPath = Annotated[Path, Depends(_get_health_ideas_path)]


def _error_envelope(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


@app.exception_handler(MemoryNotFoundError)
def handle_memory_not_found(_request: Request, exc: MemoryNotFoundError) -> JSONResponse:
    """Map memory missing-entry errors to cockpit envelope."""
    return JSONResponse(
        status_code=404,
        content=_error_envelope("MEM_NOT_FOUND", str(exc)),
    )


@app.exception_handler(MemoryConcurrencyError)
def handle_memory_concurrency(_request: Request, exc: MemoryConcurrencyError) -> JSONResponse:
    """Map memory OCC mismatches to cockpit envelope."""
    return JSONResponse(
        status_code=409,
        content=_error_envelope("MEM_CONFLICT", str(exc)),
    )


@app.exception_handler(MemoryTransitionError)
def handle_memory_transition(_request: Request, exc: MemoryTransitionError) -> JSONResponse:
    """Map invalid memory state transitions to cockpit envelope."""
    return JSONResponse(
        status_code=422,
        content=_error_envelope("MEM_INVALID_TRANSITION", str(exc)),
    )


@app.exception_handler(Exception)
def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
    """Normalize unexpected failures to a stable machine-readable envelope."""
    return JSONResponse(
        status_code=500,
        content=_error_envelope(
            "COCKPIT_INTERNAL_ERROR",
            "An unexpected error occurred.",
        ),
    )


def _module_health(checker: object) -> HealthModule:
    """Run one checker without preventing sibling module results."""
    try:
        if checker is None:
            return HealthModule(status="check-failed", findings=[{"detail": "engine unavailable"}])
        result = checker()
        if hasattr(result, "findings"):
            findings = [item.model_dump() for item in result.findings]
            checked_paths = result.checked_paths
            repairable_count = getattr(
                result,
                "repairable_count",
                sum(bool(finding.get("repairable")) for finding in findings),
            )
        else:
            findings = [{"path": path, "detail": "unreadable"} for path in result.unreadable_paths] + [
                {"path": path, "detail": "duplicate"} for paths in result.duplicate_paths.values() for path in paths
            ]
            checked_paths = result.unreadable_paths + [
                path for paths in result.duplicate_paths.values() for path in paths
            ]
            repairable_count = 0
        status = "healthy"
        if findings:
            status = "attention" if repairable_count == len(findings) else "unhealthy"
        return HealthModule(
            status=status,
            findings=findings,
            repairable_count=repairable_count,
            checked_paths=checked_paths,
        )
    except Exception as exc:  # noqa: BLE001
        return HealthModule(status="check-failed", findings=[{"detail": str(exc)}])


def _ideas_health(ideas_path: Path) -> IdeasHealth:
    try:
        ideas_path.read_bytes().decode("utf-8")
    except FileNotFoundError:
        return IdeasHealth(status="healthy", path=str(ideas_path))
    except (OSError, UnicodeDecodeError) as exc:
        return IdeasHealth(status="unhealthy", path=str(ideas_path), detail=str(exc))
    return IdeasHealth(status="healthy", path=str(ideas_path))


@app.get("/health/live")
def health_live() -> dict[str, int | str | None]:
    """Return liveness without touching workspace storage."""
    workspace = getattr(app.state, "workspace_root", None)
    return {
        "status": "ok",
        "pid": os.getpid(),
        "port": getattr(app.state, "port", None),
        "workspace": str(workspace) if workspace is not None else None,
    }


@app.get("/health/memory", response_model=HealthModule)
def memory_health(memory_engine: _HealthMemoryEngine) -> HealthModule:
    """Return the memory-storage health projection."""
    return _module_health(memory_engine.health if memory_engine else None)


@app.get("/health/ideas", response_model=IdeasHealth)
def ideas_health(ideas_path: _IdeasPath) -> IdeasHealth:
    """Return the ideas-file health projection."""
    return _ideas_health(ideas_path)


def _resolve_port(override: int | None = None) -> int:
    port_str = str(override) if override is not None else os.environ.get(_PORT_ENV, str(_DEFAULT_PORT))
    try:
        port = int(port_str)
    except ValueError:
        sys.stderr.write(f"Error: COCKPIT_PORT={port_str!r} is not a valid integer.\n")
        sys.exit(1)
    if not (1 <= port <= _MAX_PORT):
        sys.stderr.write(f"Error: COCKPIT_PORT={port} is out of range (1-{_MAX_PORT}).\n")
        sys.exit(1)
    return port


def _registry_dir() -> Path:
    configured = os.environ.get(_REGISTRY_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    user = str(os.getuid()) if hasattr(os, "getuid") else os.environ.get("USERNAME", "user")
    return Path(tempfile.gettempdir()) / f"owlbear-cockpit-{user}"


def _instance_path(pid: int) -> Path:
    return _registry_dir() / f"{pid}.json"


def _register_instance(instance: CockpitInstance) -> Path:
    registry = _registry_dir()
    registry.mkdir(parents=True, exist_ok=True)
    path = _instance_path(instance.pid)
    atomic_write(path, instance.model_dump_json(indent=2) + "\n")
    return path


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _probe_instance(instance: CockpitInstance) -> bool:
    if not _process_exists(instance.pid):
        return False
    connection = HTTPConnection(_HOST, instance.port, timeout=0.5)
    try:
        connection.request("GET", "/health/live")
        response = connection.getresponse()
        if response.status != _HTTP_OK:
            return False
        body = json.loads(response.read())
    except OSError, json.JSONDecodeError:
        return False
    finally:
        connection.close()
    return (
        body.get("status") == "ok"
        and body.get("pid") == instance.pid
        and body.get("port") == instance.port
        and body.get("workspace") == instance.workspace
    )


def _running_instances() -> list[CockpitInstance]:
    instances: list[CockpitInstance] = []
    registry = _registry_dir()
    if not registry.is_dir():
        return instances
    for path in sorted(registry.glob("*.json")):
        try:
            instance = CockpitInstance.model_validate_json(path.read_bytes())
        except OSError, ValueError:
            path.unlink(missing_ok=True)
            continue
        if _probe_instance(instance):
            instances.append(instance)
        else:
            path.unlink(missing_ok=True)
    return instances


def list_instances() -> None:
    """Print verified running Cockpit instances and clean stale records."""
    instances = _running_instances()
    if not instances:
        print("No running Cockpit instances.")  # noqa: T201
        return
    print(f"{'PID':>7}  {'PORT':>5}  {'STARTED':<20}  WORKSPACE")  # noqa: T201
    for instance in instances:
        started = instance.started_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{instance.pid:>7}  {instance.port:>5}  {started:<20}  {instance.workspace}")  # noqa: T201


def _load_target_runtime() -> tuple[Path, object]:
    workspace_root = Path.cwd().resolve()
    try:
        target_context = load_target_context(workspace_root)
    except RuntimeError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)
    return workspace_root, target_context


def _resolve_dist_dir() -> Path:
    dist_dir = _DIST_DIR.resolve()
    if not dist_dir.is_dir():
        sys.stderr.write(f"Error: dist/ directory not found at {dist_dir}. Run `npm run build` first.\n")
        sys.exit(1)
    return dist_dir


def run(*, port_override: int | None = None, no_open: bool = False) -> None:
    """Start the Cockpit server — entry point for `uv run cockpit`."""
    from owlbear_memory.engine import MemoryEngine  # noqa: PLC0415

    port = _resolve_port(port_override)
    workspace_root, target_context = _load_target_runtime()
    dist_dir = _resolve_dist_dir()

    # --- runtime init (before uvicorn starts) ---
    memory_engine = MemoryEngine(workspace_root / _MEMORY_DIR)
    app.state.workspace_root = workspace_root
    app.state.target_context = target_context
    app.state.memory_engine = memory_engine
    app.state.port = port

    # --- static file mount and SPA catch-all (inside run() for test isolation) ---
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")
    pds_dir = dist_dir / "porsche-design-system"
    if pds_dir.is_dir():
        app.mount(
            "/porsche-design-system",
            StaticFiles(directory=pds_dir),
            name="porsche-design-system",
        )

    @app.get("/theme-bootstrap.js")
    def _theme_bootstrap() -> FileResponse:
        return FileResponse(
            dist_dir / "theme-bootstrap.js",
            media_type="application/javascript",
        )

    @app.get("/{path:path}")
    def _spa_catchall(path: str) -> HTMLResponse:  # noqa: ARG001
        return HTMLResponse((dist_dir / "index.html").read_text(encoding="utf-8"))

    # --- browser auto-open ---
    if not no_open and not os.environ.get(_NO_OPEN_ENV):

        def _open_browser() -> None:
            with contextlib.suppress(Exception):
                webbrowser.open(f"http://{_HOST}:{port}/")

        timer = threading.Timer(0.5, _open_browser)
        timer.start()

    instance = CockpitInstance(
        pid=os.getpid(),
        port=port,
        workspace=str(workspace_root),
        started_at=datetime.now(UTC),
    )
    record = _register_instance(instance)
    try:
        uvicorn.run(app, host=_HOST, port=port)
    finally:
        record.unlink(missing_ok=True)


def main() -> None:
    """Dispatch Cockpit start and discovery commands."""
    parser = argparse.ArgumentParser(prog="cockpit")
    parser.add_argument("command", nargs="?", choices=("list",))
    parser.add_argument("--port", type=int, metavar="PORT")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if args.command == "list":
        if args.port is not None or args.no_open:
            parser.error("list does not accept start options")
        list_instances()
        return
    run(port_override=args.port, no_open=args.no_open)
