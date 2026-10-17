"""A visual round the owner settled: decided on the Changes page (TD-79) or accepted without the model check (TD-94)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.design_packs import calibration
from owlbear_delivery_next.workflow_steps import decision, sessions

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Lock, Store


def settled(store: Store, lock: Lock, change: Change, capture: tuple[str, str, list[int]], out: Path) -> bool:
    """Apply the owner's settlement of the last round to this exact capture; whether the step ended uncaptured."""
    head, tree, widths = capture
    if owned := decision.decided(change, head, tree):
        store.write(lock, loop.apply(owned[0], owned[1], datetime.now(UTC)))
        calibrated(store, owned[0], out)  # after the decision is saved: it never waits on the shared repository
        return True
    if taken := decision.waived(change, head, tree, widths):
        store.write(lock, loop.apply(taken[0], taken[1], datetime.now(UTC)))
        return True
    return False


def calibrated(store: Store, change: Change, out: Path) -> None:
    """Keep a decided round for calibration in the shared repository; the decision never waits on it."""
    v, b = change.visual, change.before
    if store.shared is None or v is None or not change.visual_rounds:
        return
    before = store.before_dir(change.slug, b.head) if b else None
    images = {f"after-{f}": out / f for f in v.files}
    images |= {f"before-{f}": before / f for f in v.files if before and (before / f).is_file()}
    try:
        if notice := calibration.keep(store.shared, store.name, change.slug, change.visual_rounds[-1], images):
            sessions.out(f"calibration: {notice}")
    except Exception as exc:  # noqa: BLE001 - calibration is evidence; the decision stands without it
        sessions.out(f"calibration: {type(exc).__name__}: {exc}"[:300])
