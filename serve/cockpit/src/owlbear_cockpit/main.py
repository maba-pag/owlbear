"""Cockpit FastAPI application."""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Request
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

from owlbear_cockpit.deps import get_engine, get_ideas_path, get_memory_engine
from owlbear_cockpit.models import HealthModule, IdeasHealth, WorkspaceHealth
from owlbear_cockpit.routes.events import router as events_router
from owlbear_cockpit.routes.ideas import router as ideas_router
from owlbear_cockpit.routes.memory import router as memory_router
from owlbear_cockpit.routes.mutation import router as mutation_router
from owlbear_cockpit.routes.read import router as read_router
from owlbear_cockpit.routes.requests import router as requests_router
from owlbear_kanban.errors import (
    ConcurrencyError,
    ConfigError,
    KanbanError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import DeterministicRepairResult, RepairOutcome, TaskHealthResult

_DEFAULT_PORT = 8420
_MAX_PORT = 65535

app = FastAPI(title="OwlBear Cockpit")
app.include_router(read_router, prefix="/api")
app.include_router(mutation_router, prefix="/api")
app.include_router(requests_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(ideas_router, prefix="/api")
app.include_router(memory_router, prefix="/api")

_Engine = Annotated[object, Depends(get_engine)]
_MemoryEngine = Annotated[object, Depends(get_memory_engine)]
_IdeasPath = Annotated[Path, Depends(get_ideas_path)]


def _get_health_engine() -> object | None:
    try:
        return get_engine()
    except AttributeError:
        return None


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


_HealthEngine = Annotated[object | None, Depends(_get_health_engine)]
_HealthMemoryEngine = Annotated[object | None, Depends(_get_health_memory_engine)]
_HealthIdeasPath = Annotated[Path, Depends(_get_health_ideas_path)]


def _error_envelope(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _kanban_status(exc: KanbanError) -> int:
    if isinstance(exc, NotFoundError):
        return 404
    if isinstance(exc, ConcurrencyError):
        return 409
    if isinstance(exc, ValidationError):
        return 422
    if isinstance(exc, ConfigError):
        return 500
    return 500


@app.exception_handler(KanbanError)
def handle_kanban_error(_request: Request, exc: KanbanError) -> JSONResponse:
    """Return stable cockpit error envelope for domain errors."""
    return JSONResponse(
        status_code=_kanban_status(exc),
        content=_error_envelope(exc.code, exc.user_message),
    )


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
        else:
            findings = [
                {"path": path, "detail": "unreadable"}
                for path in result.unreadable_paths
            ] + [
                {"path": path, "detail": "duplicate"}
                for paths in result.duplicate_paths.values()
                for path in paths
            ]
            checked_paths = result.unreadable_paths + [
                path for paths in result.duplicate_paths.values() for path in paths
            ]
        return HealthModule(
            status="healthy" if not findings else "unhealthy",
            findings=findings,
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


def _workspace_health(engine: object | None, memory_engine: object | None, ideas_path: Path) -> WorkspaceHealth:
    modules = {
        "tasks": _module_health(engine.task_health if engine else None),
        "requests": _module_health(engine.request_health if engine else None),
        "memory": _module_health(memory_engine.health if memory_engine else None),
        "ideas": _ideas_health(ideas_path),
    }
    return WorkspaceHealth(
        status="healthy" if all(module.status == "healthy" for module in modules.values()) else "unhealthy",
        modules=modules,
    )


@app.get("/health/live")
def health_live() -> dict[str, str]:
    """Return liveness without touching workspace storage."""
    return {"status": "ok"}


@app.get("/health", response_model=WorkspaceHealth)
def health(engine: _HealthEngine, memory_engine: _HealthMemoryEngine, ideas_path: _HealthIdeasPath) -> WorkspaceHealth:
    return _workspace_health(engine, memory_engine, ideas_path)


@app.get("/health/tasks", response_model=HealthModule)
def task_health(engine: _HealthEngine) -> HealthModule:
    return _module_health(engine.task_health if engine else None)


@app.get("/health/requests", response_model=HealthModule)
def request_health(engine: _HealthEngine) -> HealthModule:
    return _module_health(engine.request_health if engine else None)


@app.get("/health/memory", response_model=HealthModule)
def memory_health(memory_engine: _HealthMemoryEngine) -> HealthModule:
    return _module_health(memory_engine.health if memory_engine else None)


@app.get("/health/ideas", response_model=IdeasHealth)
def ideas_health(ideas_path: _IdeasPath) -> IdeasHealth:
    return _ideas_health(ideas_path)


@app.post("/health/tasks/repair", response_model=DeterministicRepairResult)
def repair_task_health(engine: _Engine) -> DeterministicRepairResult:
    started_at = datetime.now().astimezone()
    outcomes = engine.repair_storage()
    if isinstance(outcomes, DeterministicRepairResult):
        return outcomes
    if hasattr(outcomes, "status") and hasattr(outcomes, "removed_count"):
        return DeterministicRepairResult.model_validate(outcomes, from_attributes=True)

    typed_outcomes = [
        item if isinstance(item, RepairOutcome) else RepairOutcome.model_validate(item)
        for item in outcomes
    ]
    task_health_result: TaskHealthResult | None = None
    if hasattr(engine, "task_health"):
        result = engine.task_health()
        task_health_result = (
            result
            if isinstance(result, TaskHealthResult)
            else TaskHealthResult.model_validate(result, from_attributes=True)
        )
    counts = {
        "removed": sum(item.action == "removed" for item in typed_outcomes),
        "moved": sum(item.action == "moved" for item in typed_outcomes),
        "quarantined": sum(item.action == "quarantined" for item in typed_outcomes),
        "skipped": sum(item.action == "skipped" for item in typed_outcomes),
        "failed": sum(item.action == "failed" for item in typed_outcomes),
        "unresolved": sum(item.action == "unresolved" for item in typed_outcomes),
    }
    return DeterministicRepairResult(
        started_at=started_at,
        completed_at=datetime.now().astimezone(),
        removed_count=counts["removed"],
        moved_count=counts["moved"],
        quarantined_count=counts["quarantined"],
        skipped_count=counts["skipped"],
        failed_count=counts["failed"],
        unresolved_count=counts["unresolved"],
        outcomes=typed_outcomes,
        unresolved_findings=task_health_result.findings if task_health_result else [],
        task_health_result=task_health_result,
    )


def run() -> None:
    """Start the Cockpit server — entry point for `uv run cockpit`."""
    from owlbear_memory.engine import MemoryEngine  # noqa: PLC0415

    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    # --- port resolution and validation ---
    port_str = os.environ.get("COCKPIT_PORT", str(_DEFAULT_PORT))
    try:
        port = int(port_str)
    except ValueError:
        sys.stderr.write(f"Error: COCKPIT_PORT={port_str!r} is not a valid integer.\n")
        sys.exit(1)
    if not (1 <= port <= _MAX_PORT):
        sys.stderr.write(f"Error: COCKPIT_PORT={port} is out of range (1-{_MAX_PORT}).\n")
        sys.exit(1)

    # --- kanban directory ---
    kanban_dir_str = os.environ.get("KANBAN_DIR")
    kanban_dir = Path(kanban_dir_str) if kanban_dir_str else Path.cwd() / ".owlbear" / "kanban"
    if not kanban_dir.is_dir():
        sys.stderr.write(f"Error: kanban directory not found: {kanban_dir}\n")
        sys.exit(1)

    # --- dist/ directory ---
    dist_dir = Path(__file__).parent.parent.parent / "dist"
    if not dist_dir.is_dir():
        sys.stderr.write(f"Error: dist/ directory not found at {dist_dir}. Run `npm run build` first.\n")
        sys.exit(1)

    # --- engine init (before uvicorn starts) ---
    engine = KanbanEngine(kanban_dir)
    memory_dir_str = os.environ.get("MEMORY_DIR")
    memory_dir = Path(memory_dir_str) if memory_dir_str else Path.cwd() / ".owlbear" / "memory"
    memory_engine = MemoryEngine(memory_dir)
    app.state.engine = engine
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
