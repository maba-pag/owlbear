"""Cockpit FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="OwlBear Cockpit")


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
