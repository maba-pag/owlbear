"""Cockpit FastAPI application."""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import webbrowser
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
from owlbear_cockpit.models import HealthModule, IdeasHealth
from owlbear_cockpit.routes.ideas import router as ideas_router
from owlbear_cockpit.routes.memory import router as memory_router
from owlbear_cockpit.routes.target_work import (
    handle_target_http_error,
    handle_target_validation_error,
)
from owlbear_cockpit.routes.target_work import router as target_work_router
from owlbear_cockpit.target_context import load_target_context

_DEFAULT_PORT = 8420
_MAX_PORT = 65535

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
def health_live() -> dict[str, str]:
    """Return liveness without touching workspace storage."""
    return {"status": "ok"}


@app.get("/health/memory", response_model=HealthModule)
def memory_health(memory_engine: _HealthMemoryEngine) -> HealthModule:
    """Return the memory-storage health projection."""
    return _module_health(memory_engine.health if memory_engine else None)


@app.get("/health/ideas", response_model=IdeasHealth)
def ideas_health(ideas_path: _IdeasPath) -> IdeasHealth:
    """Return the ideas-file health projection."""
    return _ideas_health(ideas_path)


def _resolve_port() -> int:
    port_str = os.environ.get("COCKPIT_PORT", str(_DEFAULT_PORT))
    try:
        port = int(port_str)
    except ValueError:
        sys.stderr.write(f"Error: COCKPIT_PORT={port_str!r} is not a valid integer.\n")
        sys.exit(1)
    if not (1 <= port <= _MAX_PORT):
        sys.stderr.write(f"Error: COCKPIT_PORT={port} is out of range (1-{_MAX_PORT}).\n")
        sys.exit(1)
    return port


def _load_target_runtime() -> tuple[Path, object]:
    configured_root = os.environ.get("OWLBEAR_WORKSPACE_ROOT", "").strip()
    workspace_root = (Path(configured_root) if configured_root else Path.cwd()).resolve()
    configured_request = os.environ.get("OWLBEAR_TARGET_CUTOVER_REQUEST", "").strip()
    request_path = Path(configured_request) if configured_request else Path(".owlbear/target-cutover-request.json")
    if not request_path.is_absolute():
        request_path = workspace_root / request_path
    try:
        target_context = load_target_context(workspace_root, request_path.resolve())
    except RuntimeError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)
    return workspace_root, target_context


def _resolve_dist_dir() -> Path:
    configured_dist = os.environ.get("COCKPIT_DIST_DIR", "").strip()
    dist_dir = Path(configured_dist).resolve() if configured_dist else Path(__file__).parent.parent.parent / "dist"
    if not dist_dir.is_dir():
        sys.stderr.write(f"Error: dist/ directory not found at {dist_dir}. Run `npm run build` first.\n")
        sys.exit(1)
    return dist_dir


def run() -> None:
    """Start the Cockpit server — entry point for `uv run cockpit`."""
    from owlbear_memory.engine import MemoryEngine  # noqa: PLC0415

    port = _resolve_port()
    workspace_root, target_context = _load_target_runtime()
    dist_dir = _resolve_dist_dir()

    # --- runtime init (before uvicorn starts) ---
    memory_dir_str = os.environ.get("MEMORY_DIR")
    memory_dir = Path(memory_dir_str) if memory_dir_str else workspace_root / ".owlbear" / "memory"
    memory_engine = MemoryEngine(memory_dir)
    app.state.workspace_root = workspace_root
    app.state.target_context = target_context
    app.state.memory_engine = memory_engine

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
    if not os.environ.get("COCKPIT_NO_OPEN"):

        def _open_browser() -> None:
            with contextlib.suppress(Exception):
                webbrowser.open(f"http://127.0.0.1:{port}/")

        timer = threading.Timer(0.5, _open_browser)
        timer.start()

    uvicorn.run(app, host="127.0.0.1", port=port)
