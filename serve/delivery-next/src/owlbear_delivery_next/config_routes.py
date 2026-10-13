"""The settings page's API (§3.13 item 5, TD-52): read both layers and the resolved values, save one layer.

A save names the revision it was based on, so a page opened earlier never overwrites a newer save. Both layers live
where the store says: in the shared repository once its pointer exists (TD-57), where each save is committed and
pushed (TD-64); without it, only the project layer, in the clone. Only model, effort and widths are applied.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from owlbear_delivery_next.catalogue import CATALOGUE
from owlbear_delivery_next.config import GlobalLayer, Layer, resolve
from owlbear_delivery_next.store import StoreError, read_layer_bytes

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.store import Store

APPLIED = ["agents.*.effort", "agents.*.model", "widths", "seed", "design_failures"]  # the settings Delivery uses today


class Save(BaseModel):
    """One layer as the page edited it, and the revision of the layer it started from."""

    rev: str
    layer: dict[str, Any]


def _rev(path: Path | None) -> str:
    """The layer file's content hash; an absent file has the hash of nothing."""
    data = path.read_bytes() if path and path.exists() else b""
    return hashlib.sha256(data).hexdigest()


def _state(store: Store, notice: str = "") -> dict[str, Any]:
    """Both layers with their revisions, the resolved settings with their sources, and what is applied."""
    global_path = store.global_path
    try:
        glob, glob_raw = read_layer_bytes(global_path, GlobalLayer) if global_path else (None, b"")
        project, project_raw = read_layer_bytes(store.config_path, Layer)
    except StoreError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {
        "project": project.model_dump(mode="json"),
        "project_rev": hashlib.sha256(project_raw).hexdigest(),
        "global": glob.model_dump(mode="json") if glob else None,
        "global_rev": hashlib.sha256(glob_raw).hexdigest(),
        "global_location": global_path is not None,
        "notice": notice or (store.shared.pending() if store.shared else ""),
        "settings": resolve(glob, project).model_dump(mode="json"),
        "inherited": {  # what a blank field in each layer resolves to: the layers below it only
            "project": resolve(glob, Layer()).model_dump(mode="json"),
            "global": resolve(None, Layer()).model_dump(mode="json"),
        },
        "applied": APPLIED,
        "catalogue": CATALOGUE,
    }


def _save[T: Layer](store: Store, path: Path, model: type[T], body: Save, what: str) -> str:
    """Validate the edited layer, write it if its file is still at ``body.rev``, publish it; return the notice."""
    try:
        new = model.model_validate(body.layer)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False, include_context=False)) from exc

    def change(_current: T) -> T:
        if _rev(path) != body.rev:
            raise HTTPException(409, "the settings changed since this page loaded them")
        return new

    try:
        return store.save(path, model, change, what)
    except StoreError as exc:
        raise HTTPException(409, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(503, f"the settings could not be saved: {exc.strerror or exc}") from exc


def router(store: Store) -> APIRouter:
    """The settings routes; the caller adds the token check."""
    routes = APIRouter()

    @routes.get("/config")
    def read() -> dict[str, Any]:
        return _state(store)

    @routes.put("/config/project")
    def put_project(body: Save) -> dict[str, Any]:
        notice = _save(store, store.config_path, Layer, body, f"{store.name or 'the project'}: from the settings page")
        return _state(store, notice)

    @routes.put("/config/global")
    def put_global(body: Save) -> dict[str, Any]:
        if store.global_path is None:
            raise HTTPException(409, "no shared settings location is set up; run `owlbear-next common PATH`")
        return _state(store, _save(store, store.global_path, GlobalLayer, body, "global: from the settings page"))

    return routes
