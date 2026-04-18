"""Cockpit FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from owlbear_cockpit.deps import get_engine  # noqa: F401 — re-exported for test DI
from owlbear_cockpit.routes.mutation import router as mutation_router
from owlbear_cockpit.routes.read import router as read_router

app = FastAPI(title="OwlBear Cockpit")
app.include_router(read_router, prefix="/api")
app.include_router(mutation_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
