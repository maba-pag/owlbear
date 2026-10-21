"""The read-back queue as this host keeps it (TD-427, §8): what waits, and the owner's "ignore for now".

A decision waits when a chat or the owner queued its read-back (`decision_actions.queue_read_back`) or it is flagged
`conflict` (derived, never written). "Ignore for now" writes nothing to the decision and leaves its rule in force:
this host's database keeps the revision ignored, which moves the item to the bottom of the queue until the decision
changes. The reason a read-back was answered on stays in the decision's own file, shared by every host.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from owlbear_decisions import ReadBackKind, queue, queued
from owlbear_delivery_next.state_store import decision_actions, decision_store
from owlbear_delivery_next.state_store.decision_actions import Refused

if TYPE_CHECKING:
    from owlbear_decisions import Queued
    from owlbear_delivery_next.state_store.decision_store import DataView, Receipt
    from owlbear_delivery_next.state_store.store import Store

KEY = "read-backs"  # the `meta` row holding {"ignored": {id: revision}}
MARKS = ("ignored",)


def _parsed(row: tuple[str] | None) -> dict[str, dict[str, str]]:
    try:
        found = json.loads(row[0]) if row else {}
    except ValueError:
        found = {}
    found = found if isinstance(found, dict) else {}
    return {k: dict(v) if isinstance(v := found.get(k), dict) else {} for k in MARKS}


def marks(store: Store) -> dict[str, dict[str, str]]:
    """This host's ignored revisions by decision id."""
    with store.db.read() as db:
        return _parsed(db.execute("SELECT value FROM meta WHERE key = ?", (KEY,)).fetchone())


def _mark(store: Store, mark: str, decision_id: str, value: str) -> None:
    with store.db.write() as db:
        found = _parsed(db.execute("SELECT value FROM meta WHERE key = ?", (KEY,)).fetchone())
        found[mark][decision_id] = value
        db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (KEY, json.dumps(found)))


def waiting(store: Store, view: DataView) -> list[Queued]:
    """The view's read-backs in queue order, the ones ignored at their current revision last."""
    decisions = [e.decision for e in view.snapshot.entries]
    ignored = marks(store)["ignored"]
    return queue(decisions, {d.id for d in decisions if ignored.get(d.id) == d.revision})


def item(q: Queued, ignored: dict[str, str]) -> dict[str, Any]:
    """One queue item as the page and the checkpoints show it."""
    d = q.decision
    said = d.model_dump(mode="json", include={"id", "title", "statement", "scope", "project", "origin", "state"})
    return said | {"revision": d.revision, "kind": str(q.kind), "why": q.why, "derived": q.derived,
                   "ignored": ignored.get(d.id) == d.revision}  # fmt: skip


def ask(  # noqa: PLR0913 - why, how urgent and the revision the caller read
    store: Store, project: str, decision_id: str, *, why: str, kind: str, revision: str
) -> list[Receipt]:
    """Queue a read-back for a new reason, against the revision the caller read."""
    return decision_actions.queue_read_back(
        store.shared, project, decision_id, why=why, kind=ReadBackKind(kind), revision=revision
    )


def answer(  # noqa: PLR0913 - who answered, his words and the revision read
    store: Store, project: str, decision_id: str, revision: str, *, said: str, by: str
) -> list[Receipt]:
    """Record the owner's read-back ("still right"); the reason it waited on stays in the decision as settled."""
    return decision_actions.read_back(store.shared, project, decision_id, revision, answer=said, by=by)


def ignore(store: Store, project: str, decision_id: str, revision: str) -> dict[str, Any]:
    """Ignore a waiting read-back for now: nothing is written to the decision, its rule stays in force."""
    found = decision_store.load(store.shared, project).snapshot.get(decision_id)
    if found is None:
        msg = f"there is no decision {decision_id} in this view"
        raise Refused(msg, 404)
    if found.decision.revision != revision:
        msg = f"{decision_id} changed since it was read; reload and decide again"
        raise Refused(msg)
    if queued(found.decision) is None:
        msg = f"{decision_id} does not wait to be read back"
        raise Refused(msg)
    _mark(store, "ignored", decision_id, revision)
    notice = "Ignored for now: the rule stays in force as recorded; it waits at the bottom of the queue."
    return {"ignored": decision_id, "notice": notice}
