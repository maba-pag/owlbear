"""The Change page's screenshots: the check's "after" and "before", and the shaping capture's and the reference's.

Each is served only when its capture lists it, from that capture's own folder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from owlbear_delivery_next.workflow_steps import captures, visual

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.visual_records import ShapingCapture, VisualResult
    from owlbear_delivery_next.state_store.store import Store


def png(shots: VisualResult | None, folder_of: Callable[[str], Path], name: str) -> FileResponse:
    """The screenshot *name* of *shots*, from the folder its head names; 404 when it lists none such."""
    if not (shots and visual.FILE.fullmatch(name) and name in shots.files):
        raise HTTPException(404, "no such screenshot")
    folder = folder_of(shots.head).resolve()
    path = (folder / name).resolve()
    if path.parent != folder or not path.is_file():
        raise HTTPException(404, "no such screenshot")
    return FileResponse(path, media_type="image/png")


def router(store: Store, read: Callable[[str], Change]) -> APIRouter:
    """GET /changes/{slug}/visual|before|shaped|reference/{name}."""
    routes = APIRouter()

    def shaping(s: ShapingCapture | None, slug: str, name: str) -> FileResponse:
        return png(s and s.result, lambda _head: captures.folder(store, slug, s), name)

    @routes.get("/changes/{slug}/visual/{name}")
    def screenshot(slug: str, name: str) -> FileResponse:
        return png(read(slug).visual, lambda head: store.visual_dir(slug, head), name)

    @routes.get("/changes/{slug}/before/{name}")
    def before_screenshot(slug: str, name: str) -> FileResponse:
        return png(read(slug).before, lambda base: store.before_dir(slug, base), name)

    @routes.get("/changes/{slug}/shaped/{name}")
    def shaped_screenshot(slug: str, name: str) -> FileResponse:
        return shaping(read(slug).shaped, slug, name)

    @routes.get("/changes/{slug}/reference/{name}")
    def reference_screenshot(slug: str, name: str) -> FileResponse:
        return shaping(read(slug).reference, slug, name)

    return routes
