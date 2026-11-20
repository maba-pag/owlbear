"""The inline reminder for an approved look once the serving OwlBear release contains its Change."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request

from owlbear_delivery_next.change_contracts import owner_look
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.local_system.git_files import probe_in
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store

WAITING = "The look is due once an OwlBear release containing this Change is installed."
LOG = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _contains(root: Path, tag: str, commit: str) -> bool:
    """A release's immutable commit pair; errors are not cached."""
    run = probe_in(root)

    def git(*args: str) -> str:
        code, said = run(["git", *args])
        if code:
            msg = f"Installed OwlBear release in {root}: {said}"
            raise RuntimeError(msg)
        return said

    if git("rev-parse", "HEAD") != git("rev-parse", f"refs/tags/{tag}^{{commit}}"):
        msg = f"Installed OwlBear release in {root}: HEAD does not match {tag}"
        raise RuntimeError(msg)
    code, said = run(["git", "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"])
    if code == 1:  # an older installation need not hold a future merge object
        return False
    if code:
        msg = f"Installed OwlBear release in {root}: {said}"
        raise RuntimeError(msg)
    code, said = run(["git", "merge-base", "--is-ancestor", commit, "HEAD"])
    if code not in {0, 1}:
        msg = f"Installed OwlBear release in {root}: {said}"
        raise RuntimeError(msg)
    return code == 0


def shown(store: Store, c: Change) -> dict[str, str | bool] | None:
    """The pending look, or none; installation failures stay visible without permitting acknowledgement."""
    look = c.release_look
    if (
        c.step.mode == "abandon"
        or c.intent.abandoned_at
        or not c.finished_at
        or look is None
        or look.done_at
        or not owner_look.approved(c)
    ):
        return None
    try:
        prof = store.read_profile()
        if prof is None or profile.value(prof, profile.REPO).lower() != owner_look.REPOSITORY:
            return None
        if look.version != c.brief.version:
            return {
                "ready": False,
                "error": True,
                "text": "The release look's receipt does not match this brief version.",
            }
        root = codebase.ROOT.resolve().parents[3]
        if root.parent != (local_home.root() / local_home.VERSIONS).resolve() or not re.fullmatch(
            r"v\d+(?:\.\d+)?", root.name
        ):
            return {"ready": False, "text": WAITING}
        ready = _contains(root, root.name, look.commit)
    except (RuntimeError, StoreError) as exc:
        LOG.exception("The release look for %s could not check its installation", c.slug)
        return {"ready": False, "error": True, "text": f"The release look could not be checked: {failure(exc)}"}
    return {"ready": ready, "text": f"{root.name} is installed. Take your look at this Change." if ready else WAITING}


def router(store: Store, read: Callable[[str], Change]) -> APIRouter:
    """A local acknowledgement starts no work and never changes merge or check evidence."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/release-look")
    def done(slug: str, request: Request) -> dict[str, str]:
        if request.headers.get("x-owlbear-use", "").lower() == "chat":
            raise HTTPException(403, "Only the owner marks a release look done, on the Changes page")
        read(slug)
        try:
            with store.lock(slug) as lock:
                c = store.read(slug)
                if c.release_look and c.release_look.done_at:
                    return {"accepted": "release-look"}
                state = shown(store, c)
                if c.release_look is None or state is None or not state["ready"]:
                    raise HTTPException(409, str(state["text"]) if state else "No release look is due")
                c.release_look.done_at = datetime.now(UTC)
                store.write(lock, c)
        except (LockHeldError, StoreError) as exc:
            raise HTTPException(409, f"change: {exc}; try again") from exc
        return {"accepted": "release-look"}

    return routes
