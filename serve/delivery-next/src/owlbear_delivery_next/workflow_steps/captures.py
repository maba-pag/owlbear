"""The runner's captures of the brief's states outside a check's own preview, each returning the line it prints.

"before" renders the merge-base once the visual check's recipe is known (TD-24). The shaping capture
(D-01M61V2GR0C6JV2R6KJ0WR4PNB, D-01M6Q56RXK85C5T4AG7R051X6N) fetches the target, renders the brief's states there with
its recipe on its declared test copy, ends that copy in the throwaway checkout and writes the result; earlier sets the
design reference does not use are deleted.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.visual_records import ShapingCapture
from owlbear_delivery_next.change_flow import shaping_capture
from owlbear_delivery_next.state_store import github_writer
from owlbear_delivery_next.workflow_steps import before, engine, prepare

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Lock, Store


def folder(store: Store, slug: str, key: str) -> Path:
    """Where the capture of *key* keeps its pictures."""
    return store.root / "changes" / slug / "shaped" / key[:16]


def at_merge_base(store: Store, lock: Lock, change: Change, repo: Path) -> str:
    """TD-24: render the brief's states at the merge-base once, before the visual check's own preview starts."""
    settings, log = store.settings(), lambda e: store.log(lock, change.slug, e)
    settings.need("widths")
    change.before = shots = before.capture(
        change,
        repo,
        lambda base: store.before_dir(change.slug, base),
        store.read_profile() or Profile(),
        log,
        widths=settings.widths,
        prepare=prepare.merge_base(store, change, settings, log),
    )
    store.write(lock, change)
    return "; ".join([f"before: {len(shots.files)} screenshots at {shots.head[:7]}", *shots.findings])


def at_target(store: Store, lock: Lock, change: Change, repo: Path) -> str:
    """Capture the draft's pages and record them. The runner's lock holds the draft unchanged meanwhile."""
    settings, log, key = store.settings(), lambda e: store.log(lock, change.slug, e), shaping_capture.key(change.brief)
    settings.need("widths")
    writer = github_writer.of(store, repo)

    def finish(_tmp: Path, notes: list[str]) -> None:
        """End the test copy in its checkout; a cleanup that failed is the capture's finding, whole.

        Its checkout goes with the capture, so it is not run again: the next test copy of the option runs it on the
        same resources.
        """

        def told(e: dict[str, Any]) -> None:
            log(e)
            if e.get("event") == "prepared-end" and e.get("outstanding"):
                notes.append(f"the test copy's cleanup did not finish: {e['cleanup']}")

        if (r := prepare.end(store, change, repo, settings, told)) is not None:
            notes.append(r.reason)

    out = folder(store, change.slug, key)
    result = before.at_target(
        change, repo, out, store.read_profile() or Profile(), log, widths=settings.widths,
        fetch=lambda path, target: engine.fetch(path, target, writer.access()),
        prepare=prepare.shaping(store, change, settings, log), finish=finish,
    )  # fmt: skip
    change.shaped = ShapingCapture(key=key, result=result)
    store.write(lock, change)
    kept = {folder(store, change.slug, s.key).name for s in (change.shaped, change.reference) if s}
    for old in out.parent.iterdir() if out.parent.is_dir() else ():  # a failed fetch made none
        if old.name not in kept:
            shutil.rmtree(old, ignore_errors=True)
    return "; ".join([f"shaping capture: {len(result.files)} screenshots at {result.head[:7]}", *result.findings])
