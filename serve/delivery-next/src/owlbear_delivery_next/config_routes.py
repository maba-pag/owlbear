"""The settings page's API (§3.13 item 5, TD-52): read both layers and the resolved values, save one layer.

A save names the revision it was based on, so a page opened earlier never overwrites a newer save. The global
layer is saved only where the caller configured a location, which is the owner's decision; until then it is
absent and the page shows it as such. Only model and effort are applied (TD-27); the page marks the rest.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from owlbear_delivery_next.config import GlobalLayer, Layer, resolve
from owlbear_delivery_next.store import CONFIG, StoreError, read_layer_bytes, update_layer

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.store import Store

APPLIED = ["agents.*.effort", "agents.*.model"]  # the settings Delivery uses today; the page marks the rest
# What each runtime offers beyond the shared baseline (runtime research P15 to P19); shown, not used for routing yet.
CATALOGUE: dict[str, Any] = {
    "baseline": "the runtime's own tools (files, edit, shell) and Delivery's result tools",
    "runtimes": [
        {
            "runtime": "sdk",
            "adds": "nothing beyond the baseline",
            "mcp": "only servers Delivery passes",
            "live_view": "no (VS Code shows a snapshot at most)",
            "outside_writes": "Delivery's hard guard (TD-45)",
        },
        {
            "runtime": "window",
            "adds": "the VS Code window's tools: browser, tasks, problems",
            "mcp": "your VS Code mcp.json",
            "live_view": "yes",
            "outside_writes": "the watcher, once it exists (D6)",
        },
    ],
    "categories": {
        "browser": {
            "runtime": "window",
            "tools": [
                "openBrowserPage",
                "readPage",
                "screenshotPage",
                "navigatePage",
                "clickElement",
                "typeInPage",
                "hoverElement",
                "dragElement",
                "handleDialog",
                "runPlaywrightCode",
            ],
        },
    },
}


class Save(BaseModel):
    """One layer as the page edited it, and the revision of the layer it started from."""

    rev: str
    layer: dict[str, Any]


def _rev(path: Path | None) -> str:
    """The layer file's content hash; an absent file has the hash of nothing."""
    data = path.read_bytes() if path and path.exists() else b""
    return hashlib.sha256(data).hexdigest()


def _state(store: Store, global_path: Path | None) -> dict[str, Any]:
    """Both layers with their revisions, the resolved settings with their sources, and what is applied."""
    try:
        glob, glob_raw = read_layer_bytes(global_path, GlobalLayer) if global_path else (None, b"")
        project, project_raw = read_layer_bytes(store.root / CONFIG, Layer)
    except StoreError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {
        "project": project.model_dump(mode="json"),
        "project_rev": hashlib.sha256(project_raw).hexdigest(),
        "global": glob.model_dump(mode="json") if glob else None,
        "global_rev": hashlib.sha256(glob_raw).hexdigest(),
        "global_location": global_path is not None,
        "settings": resolve(glob, project).model_dump(mode="json"),
        "inherited": {  # what a blank field in each layer resolves to: the layers below it only
            "project": resolve(glob, Layer()).model_dump(mode="json"),
            "global": resolve(None, Layer()).model_dump(mode="json"),
        },
        "applied": APPLIED,
        "catalogue": CATALOGUE,
    }


def _save[T: Layer](path: Path, model: type[T], body: Save) -> None:
    """Validate the edited layer, then write it under the layer's lock if its file is still at ``body.rev``."""
    try:
        new = model.model_validate(body.layer)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False, include_context=False)) from exc

    def change(_current: T) -> T:
        if _rev(path) != body.rev:
            raise HTTPException(409, "the settings changed since this page loaded them")
        return new

    try:
        update_layer(path, model, change)
    except StoreError as exc:
        raise HTTPException(409, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(503, f"the settings could not be saved: {exc.strerror or exc}") from exc


def router(store: Store, global_path: Path | None) -> APIRouter:
    """The settings routes; the caller adds the token check."""
    routes = APIRouter()

    @routes.get("/config")
    def read() -> dict[str, Any]:
        return _state(store, global_path)

    @routes.put("/config/project")
    def put_project(body: Save) -> dict[str, Any]:
        _save(store.root / CONFIG, Layer, body)
        return _state(store, global_path)

    @routes.put("/config/global")
    def put_global(body: Save) -> dict[str, Any]:
        if global_path is None:
            raise HTTPException(409, "no global settings location is configured yet; the owner decides where it lives")
        _save(global_path, GlobalLayer, body)
        return _state(store, global_path)

    return routes
