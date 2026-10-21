"""A brief's project decisions published from its approval (TD-453; decision-intent-build §5, slice 3).

At the first step boundary after the owner approves a brief, its project decisions are saved in force to the shared
data repository in one commit and pushed, and each save's receipt is recorded on the Change. One not yet on the remote
is shown on the Change and saved again at every later boundary; a retry, or a restart after a save whose receipt was
never recorded, writes the same file at its own revision, so nothing is published twice. The Change's pin takes them
in, so its own gate never asks about them; other Changes meet them at their next boundary, through their gate. Its
end never demotes them (`decision_archive`): abandonment revokes nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionError, State, applies, decision_path, read
from owlbear_delivery_next.change_contracts.decision_records import Published, Said
from owlbear_delivery_next.state_store import decision_archive, decision_store
from owlbear_delivery_next.workflow_steps import decisions_gate

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_decisions import Decision
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.decision_store import Receipt
    from owlbear_delivery_next.state_store.store import Lock, Store

    type Item = tuple[Decision, str | None]  # what to save and the revision its file is expected at

MOVED = "its file changed in the shared data repository since; that change stands"


def publish(store: Store, lock: Lock, c: Change) -> Change:
    """Publish what *c*'s approval still owes, record each receipt and pin what it saved; *c* as it goes on."""
    if store.shared is None or c.brief.approved_at is None or c.finished_at:
        return c
    held = {p.id: p for p in c.decisions_published}
    due = [d for d in decision_archive.lasting(store.name, c, decisions_gate.stem(c)) if _due(d, held.get(d.id))]
    if not due:
        return c
    c, now = c.model_copy(deep=True), datetime.now(UTC)
    try:
        found = [(d, _target(store.shared.root, d, held.get(d.id))) for d in due]
    except (DecisionError, OSError) as exc:
        found, why = [], f"not saved: {exc}"[:300]
        held |= {d.id: _merged(held.get(d.id), d, now, why) for d in due}
    held |= {d.id: _merged(held.get(d.id), d, now, moved=True) for d, item in found if item is None}
    items = [item for _, item in found if item is not None]
    receipts = _saved(store, c, items)
    held |= {d.id: _merged(held.get(d.id), d, now, receipts[d.id]) for d, _ in items}
    c.decisions_published = list(held.values())
    _pinned(c, [d for d, _ in items if not isinstance(r := receipts[d.id], str) and r.saved])
    store.write(lock, c)
    return c


def _due(d: Decision, p: Published | None) -> bool:
    """Whether *d* is still to be published in its state: never saved, not yet on the remote, or since retired."""
    return p is None or not p.settled or p.state != d.state


def _target(root: Path, d: Decision, p: Published | None) -> Item | None:
    """What to save for *d* and the file's revision it expects; None when the file changed without this Change.

    A file this Change wrote keeps its wording and only moves on in state; an identical save publishes it again.
    """
    path = decision_path(d, root / d.project)
    current = read(path) if path.exists() else None
    if current is None:
        return d, None
    if current.revision in {d.revision, p.revision if p and p.saved else d.revision}:
        return current.model_copy(update={"state": d.state}), current.revision
    return None


def _saved(store: Store, c: Change, items: list[Item]) -> dict[str, Receipt | str]:
    """Each item's receipt, or why none was saved; every file of one approval goes in one commit."""
    if not items:
        return {}
    version = c.brief.approved[-1].version if c.brief.approved else c.brief.version
    message = f"decisions: {store.name}: {c.slug} brief v{version} approved"
    try:
        return {r.id: r for r in decision_store.save_all(store.shared, items, message=message)}
    except decision_store.DecisionsUnavailable as exc:
        return {d.id: f"not saved: {exc}"[:300] for d, _ in items}


def _merged(
    p: Published | None, d: Decision, now: datetime, said: Receipt | str = "", *, moved: bool = False
) -> Published:
    """The record after one attempt; a failed one keeps what an earlier save wrote."""
    record = Published(id=d.id, title=d.title, state=d.state.value, moved=moved, notice=MOVED if moved else "", at=now)
    if isinstance(said, str):
        kept = {"revision": p.revision, "saved": p.saved, "committed": p.committed} if p else {}
        return record.model_copy(update=kept | ({"notice": said} if said else {}))
    fields = {"revision": said.revision, "saved": said.saved, "committed": said.committed}
    return record.model_copy(update=fields | {"published": said.published, "notice": said.notice})


def _pinned(c: Change, saved: list[Decision]) -> None:
    """The Change's pin takes its own published decisions in: its gate asks only about others' changes."""
    pin = c.decisions_baseline
    if pin is None:
        return
    paths, own = decisions_gate.scope(c), decisions_gate.stem(c)
    for d in saved:
        if d.state is not State.IN_FORCE:
            pin.revisions.pop(d.id, None)
            pin.said.pop(d.id, None)
            continue
        pin.revisions[d.id] = d.rule_revision
        if applies(d, paths=paths, role=None, step=None, change=own) is not False:
            pin.said[d.id] = Said(title=d.title, statement=d.statement)
