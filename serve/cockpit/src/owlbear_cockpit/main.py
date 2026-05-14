"""Cockpit FastAPI application."""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from owlbear_cockpit.deps import get_engine  # noqa: F401 — re-exported for test DI
from owlbear_cockpit.routes.decisions import router as decisions_router
from owlbear_cockpit.routes.events import router as events_router
from owlbear_cockpit.routes.mutation import router as mutation_router
from owlbear_cockpit.routes.read import router as read_router
from owlbear_kanban.errors import (
    ConcurrencyError,
    ConfigError,
    KanbanError,
    NotFoundError,
    ValidationError,
)

_DEFAULT_PORT = 8420
_MAX_PORT = 65535

app = FastAPI(title="OwlBear Cockpit")
app.include_router(read_router, prefix="/api")
app.include_router(mutation_router, prefix="/api")
app.include_router(decisions_router, prefix="/api")
app.include_router(events_router, prefix="/api")


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


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}


def run() -> None:
    """Start the Cockpit server — entry point for `uv run cockpit`."""
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    # --- port resolution and validation ---
    port_str = os.environ.get("COCKPIT_PORT", str(_DEFAULT_PORT))
    try:
        port = int(port_str)
    except ValueError:
        sys.stderr.write(f"Error: COCKPIT_PORT={port_str!r} is not a valid integer.\n")
        sys.exit(1)
    if not (1 <= port <= _MAX_PORT):
        sys.stderr.write(
            f"Error: COCKPIT_PORT={port} is out of range (1-{_MAX_PORT}).\n"
        )
        sys.exit(1)

    # --- kanban directory ---
    kanban_dir_str = os.environ.get("KANBAN_DIR")
    kanban_dir = (
        Path(kanban_dir_str) if kanban_dir_str else Path.cwd() / ".owlbear" / "kanban"
    )
    if not kanban_dir.is_dir():
        sys.stderr.write(f"Error: kanban directory not found: {kanban_dir}\n")
        sys.exit(1)

    # --- dist/ directory ---
    dist_dir = Path(__file__).parent.parent.parent / "dist"
    if not dist_dir.is_dir():
        sys.stderr.write(
            f"Error: dist/ directory not found at {dist_dir}. Run `npm run build` first.\n"
        )
        sys.exit(1)

    # --- engine init (before uvicorn starts) ---
    engine = KanbanEngine(kanban_dir)
    app.state.engine = engine

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
