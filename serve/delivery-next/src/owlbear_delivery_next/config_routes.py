"""The settings page's API (§3.13 item 5, TD-52): read both layers and the resolved values, save one layer.

A save names the revision it was based on, so a page opened earlier never overwrites a newer save. Both layers live
where the store says: in the shared repository once its pointer exists (TD-57), where each save is committed and
pushed (TD-64); without it, only the project layer, in the clone. Only model, effort and widths are applied. The
project's folder there can be renamed (TD-98) while none of its runners runs.
"""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from owlbear_delivery_next import calibration, data_repo, model_choices, pack_update
from owlbear_delivery_next.catalogue import CATALOGUE
from owlbear_delivery_next.config import GlobalLayer, Layer, resolve
from owlbear_delivery_next.data_repo import DataRepoError
from owlbear_delivery_next.store import StoreError, read_layer_bytes

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.host import Host
    from owlbear_delivery_next.store import Store

APPLIED = [
    "agents.*.context",
    "agents.*.effort",
    "agents.*.model",
    "widths",
    "preparations",
    "data",
    "design_failures",
]  # the settings Delivery uses today
STARTING = 5.0  # seconds a folder rename waits for a runner launch or the host's folder check to end


class Save(BaseModel):
    """One layer as the page edited it, and the revision of the layer it started from."""

    rev: str
    layer: dict[str, Any]


class Folder(BaseModel):
    """The new name of the project's folder in the shared repository."""

    name: str


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
        "folder": store.name or None,
        "notice": notice or (store.shared.pending() if store.shared else ""),
        "settings": resolve(glob, project).model_dump(mode="json"),
        "inherited": {  # what a blank field in each layer resolves to: the layers below it only
            "project": resolve(glob, Layer()).model_dump(mode="json"),
            "global": resolve(None, Layer()).model_dump(mode="json"),
        },
        "applied": APPLIED,
        "catalogue": CATALOGUE,
        "agreement": _agreement(store),
        "design_pack": pack_update.said(pack_update.notice(refresh=False)),  # never online; setup refreshes it
    }


def _agreement(store: Store) -> list[dict[str, Any]]:
    """Each judge's agreement with the owner's visual decisions; none without a shared repository, or while busy."""
    if store.shared is None:
        return []
    try:
        return calibration.agreement([r for r, _ in calibration.cases(store.shared, store.name, wait=2.0)])
    except DataRepoError, OSError, ValueError:
        return []


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


def _working(store: Store, host: Host) -> list[str]:
    """The Changes whose runner may still run, or whose lock another process holds: they may use the old folder."""
    out = []
    for slug in store.slugs():
        rec, holder = host.runner(slug), store.holder(slug)
        if (rec and host.alive(rec.pid, rec.created) is not False) or (holder and holder.pid != host.record.pid):
            out.append(slug)
    return out


def _rename(store: Store, host: Host, name: str) -> str:
    """Move the project's folder while no runner can start or run, then use it here; the publication notice."""
    if store.shared is None:
        raise HTTPException(409, "no shared settings location is set up; run `owlbear-next data PATH`")
    if not host.launching.acquire(timeout=STARTING):
        raise HTTPException(409, "a runner is starting; try again")
    try:
        if busy := _working(store, host):
            raise HTTPException(409, f"steps of {', '.join(busy)} are running; rename once they have finished")
        until = time.monotonic() + data_repo.SAVE_SECONDS
        with store.shared.locked():
            notice = store.shared.rename(store.name, name, until)
            store.name = name
    except DataRepoError as exc:
        raise HTTPException(409, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(503, f"the folder could not be renamed: {exc.strerror or exc}") from exc
    finally:
        host.launching.release()
    return notice


def router(store: Store, host: Host) -> APIRouter:
    """The settings routes; the caller adds the token check."""
    routes, offered = APIRouter(), model_choices.Offered()

    @routes.get("/config")
    def read() -> dict[str, Any]:
        return _state(store)

    @routes.get("/config/models")
    def models() -> dict[str, Any]:
        return offered()

    @routes.put("/config/project")
    def put_project(body: Save) -> dict[str, Any]:
        notice = _save(store, store.config_path, Layer, body, f"{store.name or 'the project'}: from the settings page")
        return _state(store, notice)

    @routes.put("/config/global")
    def put_global(body: Save) -> dict[str, Any]:
        if store.global_path is None:
            raise HTTPException(409, "no shared settings location is set up; run `owlbear-next data PATH`")
        return _state(store, _save(store, store.global_path, GlobalLayer, body, "global: from the settings page"))

    @routes.put("/config/folder")
    def put_folder(body: Folder) -> dict[str, Any]:
        return _state(store, "" if body.name == store.name else _rename(store, host, body.name))

    return routes
