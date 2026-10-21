"""A brief's project decisions published by its approval (TD-453; decision-intent-build §5, slice 3).

The approve route, under the Change's lock, records the approval with these saves planned, saves the approved
version's project decisions in force to the shared data repository in one commit, then records their receipts; a save
that is refused or fails refuses the approval. A push that fails leaves
them committed in this checkout, where this machine's other Changes read them at their next step, and the data
repository's next save pushes them. A file an earlier approval wrote keeps its content: a retried approval rewrites it
unchanged, and a later version that replaces, drops or narrows it to the Change retires it in the same commit, never
deleting it (TD-430). The approval's pin takes them in, so the Change's own gate never asks about them; its end never
demotes them (`decision_archive`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_decisions import DecisionError, State, applies, decision_path, read
from owlbear_delivery_next.change_contracts.decision_records import Published, Said
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Stop
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.state_store import decision_archive, decision_store
from owlbear_delivery_next.workflow_steps import decisions_gate

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_decisions import Decision
    from owlbear_delivery_next.change_contracts.decision_records import DecisionBaseline
    from owlbear_delivery_next.change_contracts.inbox import BriefApproval
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.decision_store import Receipt
    from owlbear_delivery_next.state_store.store import Lock, Store

    type Item = tuple[Decision, str | None]  # what to save and the revision its file is expected at

REFUSED = "the brief's project decisions were not saved, so it is not approved; approve it again"
UNSAVED = "the approved brief's project decisions were not saved"
SAVE = "Let the shared data repository save and commit again (see the reason), then resume"


def approve(store: Store, lock: Lock, c: Change, approval: BriefApproval) -> str:
    """Record *approval* on *c*, which the caller read under *lock*, and publish its project decisions; or why not.

    The approval is written with its saves planned before Git is touched, then their receipts: an interruption
    between them leaves an approved Change whose next step saves them again (`resume`), files being rebuilt the same.
    A save that is refused or fails writes *c* back as it was.
    """
    after = loop.fold(c, [approval], approval.at)
    try:
        items = _items(store, after)
    except (DecisionError, OSError) as exc:
        return f"{REFUSED}: {exc}"[:600]
    if items:
        planned = [_record(d, None, approval.at) for d, _ in items]
        after = loop.fold(c, [approval.model_copy(update={"published": planned})], approval.at)
    store.write(lock, after)
    if not items:
        return ""
    done, why = _published(store, after, items)
    store.write(lock, c if why else done)
    return f"{REFUSED}: {why}"[:600] if why else ""


def resume(store: Store, lock: Lock, c: Change, now: datetime) -> Change | None:
    """*c* with an interrupted approval's saves done again before its next step, or None once that stopped it."""
    if all(p.committed for p in c.decisions_published):
        return c
    try:
        done, why = _published(store, c, _items(store, c))
    except (DecisionError, OSError) as exc:
        done, why = c, str(exc)
    if not why:
        store.write(lock, done)
        return done
    reason = f"{UNSAVED}: {why}"[:600]
    stop = Stop(kind=ErrorKind.STATE, reason=reason, action=SAVE, resume="They are saved", at=now)
    store.write(lock, loop.apply(c, StepResult(exit=Exit.STOP, reason=reason, stop=stop), now))
    return None


def _items(store: Store, c: Change) -> list[Item]:
    """What the approved *c*'s project decisions save: rebuilt from its approvals, so the same on every retry."""
    if store.shared is None:
        return []
    found = decision_archive.lasting(store.name, c, decisions_gate.stem(c))
    return [item for d in found if (item := _item(store.shared.root, c, d)) is not None]


def _published(store: Store, c: Change, items: list[Item]) -> tuple[Change, str]:
    """*c* with the receipts of saving *items* in one commit and its pin taking them in, or why they were not saved."""
    done = c.model_copy(deep=True)
    saved: dict[str, Published] = {}
    if items:
        message = f"decisions: {store.name}: {c.slug} brief v{c.brief.approved_version} approved"
        try:
            receipts = decision_store.save_all(store.shared, items, message=message)
        except (decision_store.DecisionsUnavailable, DecisionError, OSError) as exc:
            return c, str(exc)
        if failed := [r for r in receipts if not r.committed]:
            return c, "; ".join(_failed(r) for r in failed)
        at = c.brief.approved_at or datetime.now(UTC)
        saved = {d.id: _record(d, r, at) for (d, _), r in zip(items, receipts, strict=True)}
        done.decisions_baseline = _pinned(c.decisions_baseline, c, [d for d, _ in items])
    kept = [p for p in c.decisions_published if p.committed and p.id not in saved]  # planned ones not saved go
    done.decisions_published = [*kept, *saved.values()]
    return done, ""


def _item(root: Path, c: Change, d: Decision) -> Item | None:
    """What to save for *d*: new, its file as an earlier approval wrote it, or that file retired; None to leave it."""
    path = decision_path(d, root / d.project)
    current = read(path) if path.exists() else None
    if current is None:
        return d, None
    if current.state is d.state:  # a retried approval rewrites it unchanged
        return current, current.revision
    if current.state is State.IN_FORCE:
        rationale = "\n\n".join(filter(None, [current.rationale, _retired(c, d)]))
        return current.model_copy(update={"state": d.state, "rationale": rationale}), current.revision
    return None  # retired since without this Change: that stands


def _retired(c: Change, d: Decision) -> str:
    """Why the approved version retires *d*: replaced, moved into the Change, or dropped."""
    by = f"brief v{c.brief.approved[-1].version} of Change {c.slug}"
    if d.state is State.REPLACED:
        return f"Replaced by {by}."
    narrowed = {x.replaces for b in c.brief.approved for x in b.decisions if x.replaces and x.scope != "project"}
    if d.id in narrowed:
        return f"Withdrawn by {by}: it moved into that Change's own decisions."
    return f"Withdrawn by {by}, which dropped it."


def _failed(r: Receipt) -> str:
    return f"{r.id}: {r.notice or 'not committed'}"


def _record(d: Decision, r: Receipt | None, at: datetime) -> Published:
    """*d*'s save with its receipt; without one, planned and not yet saved."""
    if r is None:
        return Published(id=d.id, title=d.title, state=d.state.value, at=at)
    fields = {"revision": r.revision, "saved": r.saved, "committed": r.committed, "published": r.published}
    return Published(id=d.id, title=d.title, state=d.state.value, notice=r.notice, at=at, **fields)


def _pinned(baseline: DecisionBaseline | None, c: Change, saved: list[Decision]) -> DecisionBaseline | None:
    """The approval's pin with *c*'s own saves taken in: its gate asks only about others' changes."""
    if baseline is None:
        return None
    pin = baseline.model_copy(deep=True)
    paths, own = decisions_gate.scope(c), decisions_gate.stem(c)
    for d in saved:
        if d.state is not State.IN_FORCE:
            pin.revisions.pop(d.id, None)
            pin.said.pop(d.id, None)
            continue
        pin.revisions[d.id] = d.rule_revision
        if applies(d, paths=paths, role=None, step=None, change=own) is not False:
            pin.said[d.id] = Said(title=d.title, statement=d.statement)
    return pin
