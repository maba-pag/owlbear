"""The settings page's API (§3.13 item 5, TD-52): read both layers and the resolved values, save one layer.

A save names the revision it was based on, so a page opened earlier never overwrites a newer save. Both layers live
where the store says: in the shared repository once its pointer exists (TD-57), where each save is committed and
pushed (TD-64); without it, only the project layer, in the clone. Only model, effort and widths are applied. The
project's folder there can be renamed (TD-98) while none of its runners runs.
"""

from __future__ import annotations

import contextlib
import hashlib
import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
from owlbear_delivery_next.design_packs import calibration, pack_update
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.runtimes.catalogue import CATALOGUE
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, resolve
from owlbear_delivery_next.state_store.store import StoreError, read_layer_bytes

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Store

APPLIED = [
    "agents.*.context",
    "agents.*.effort",
    "agents.*.model",
    "widths",
    "preparations",
    "data",
    "design_failures",
    "agents.builder.max_rounds",
    "agents.builder.max_findings",
    "agents.builder.last_round_at",
    "agents.builder.ask_owner_at",
    "agents.planner.max_rounds",
    "agents.planner.max_findings",
    "agents.planner.last_round_at",
    "agents.planner.ask_owner_at",
    "agents.shaper.max_rounds",
    "agents.shaper.max_findings",
    "agents.shaper.last_round_at",
    "agents.shaper.ask_owner_at",
    "final_review",
    *(f"agents.{role}.minutes" for role in ("planner", "builder", "reviewer", "challenger", "design-judge")),
    "agents.preparer.minutes",
    "agents.updater.minutes",
    "pr_labels",
    "pr_marker",
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
    here, alone = list[str](), list[str]()
    settings, below = _resolved(glob, project, here), _resolved(glob, Layer(), alone)
    if here:
        notice = (
            f"The challenge-round values in use here do not fit together ({here[0]}); steps stop until you fix them"
        )
    elif alone:
        notice = (
            f"The global challenge-round values do not fit together on their own ({alone[0]}); a project without its "
            "own values stops until you fix them in the global layer"
        )
    return {
        "project": project.model_dump(mode="json"),
        "project_rev": hashlib.sha256(project_raw).hexdigest(),
        "global": glob.model_dump(mode="json") if glob else None,
        "global_rev": hashlib.sha256(glob_raw).hexdigest(),
        "global_location": global_path is not None,
        "folder": store.name or None,
        "notice": notice or (store.shared.pending() if store.shared else ""),
        "settings": settings.model_dump(mode="json"),
        "inherited": {  # what a blank field in each layer resolves to: the layers below it only
            "project": below.model_dump(mode="json"),
            "global": resolve(None, Layer()).model_dump(mode="json"),
        },
        "applied": APPLIED,
        "catalogue": CATALOGUE,
        "agreement": _agreement(store),
        "design_pack": pack_update.said(pack_update.notice(refresh=False)),  # never online; setup refreshes it
    }


def _resolved(glob: GlobalLayer | None, project: Layer, misfit: list[str]) -> Settings:
    """The settings; when stored round values do not fit together, those without them, the problem in *misfit*.

    A hand edit, two saves at once or another machine's save can store such a combination; the page shows it so the
    owner can fix it, while runners stop on it.
    """
    try:
        return resolve(glob, project)
    except ValidationError as exc:
        misfit.append("; ".join(e["msg"] for e in exc.errors(include_url=False)))
        return resolve(_unrounded(glob), _unrounded(project))


def _unrounded[T: Layer](layer: T | None) -> T | None:
    if layer is None:
        return None
    agents = {role: a.model_copy(update=dict.fromkeys(RoundPolicy.model_fields)) for role, a in layer.agents.items()}
    return layer.model_copy(update={"agents": agents, "final_review": None})


def _agreement(store: Store) -> list[dict[str, Any]]:
    """Each judge's agreement with the owner's visual decisions; none without a shared repository, or while busy."""
    if store.shared is None:
        return []
    try:
        return calibration.agreement([r for r, _ in calibration.cases(store.shared, store.name, wait=2.0)])
    except DataRepoError, OSError, ValueError:
        return []


def _others(store: Store) -> list[Layer]:
    """The other projects' layers in the shared repository; one that does not read is that project's to fix."""
    layers = []
    for path in sorted(store.shared.root.glob(f"*/{data_repo.CONFIG}")) if store.shared else []:
        if path != store.config_path:
            with contextlib.suppress(StoreError):
                layers.append(read_layer_bytes(path, Layer)[0])
    return layers


def _save[T: Layer](store: Store, path: Path, model: type[T], body: Save, what: str) -> str:
    """Validate the edited layer, write it if its file is still at ``body.rev``, publish it; return the notice."""
    try:
        new = model.model_validate(body.layer)
        if isinstance(new, GlobalLayer):
            for layer in [store.read_config(), *_others(store), Layer()]:  # every project it applies to (TD-209)
                resolve(new, layer)
        else:
            resolve(read_layer_bytes(store.global_path, GlobalLayer)[0] if store.global_path else None, new)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False, include_context=False)) from exc
    except StoreError as exc:
        raise HTTPException(409, str(exc)) from exc

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
    for slug in store.db.legacy_slugs() if store.db.waiting() else store.slugs():  # a clone not yet imported too
        rec, holder = host.runner(slug), store.holder(slug)
        if (rec and host.alive(rec.pid, rec.created) is not False) or (holder and holder.pid != host.record.pid):
            out.append(slug)
    return out


def _rename(store: Store, host: Host, name: str) -> str:
    """Move the project's folder while no runner of any clone using it can start or run; the publication notice.

    The machine's other clones of the project share the folder (TD-242): each one's launch mutex is held too.
    """
    if store.shared is None:
        raise HTTPException(409, "no shared settings location is set up; run `owlbear-next data PATH`")
    held: list[Host] = []
    try:
        for h in sorted([host, *host.peers()], key=id):  # one order, so two renames never wait for each other
            if not h.launching.acquire(timeout=STARTING):
                raise HTTPException(409, "a runner is starting; try again")
            held.append(h)
        if busy := [s for h in held for s in _working(h.store, h)]:
            raise HTTPException(409, f"steps of {', '.join(busy)} are running; rename once they have finished")
        until = time.monotonic() + data_repo.SAVE_SECONDS
        with store.shared.locked():
            notice = store.shared.rename(store.name, name, until)
            for h in held:
                h.store.name = name
    except DataRepoError as exc:
        raise HTTPException(409, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(503, f"the folder could not be renamed: {exc.strerror or exc}") from exc
    finally:
        for h in held:
            h.launching.release()
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
