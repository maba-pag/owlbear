"""The Change page's status row and current committed exception verdicts."""

from __future__ import annotations

import functools
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_quality import ledger
from owlbear_quality.inspect import added

from owlbear_delivery_next.change_flow import exception_gate, loop, quality, worktree
from owlbear_delivery_next.change_flow.progress import progress
from owlbear_delivery_next.change_flow.status import card, status, unloadable
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.project_host import release_look
from owlbear_delivery_next.state_store import spend_ledger, tool_metrics, watch_reports
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import held

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_quality.inspect import Addition

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_flow.status import Activity
    from owlbear_delivery_next.state_store.store import Store


def summary(store: Store, slug: str, act: Activity, now: datetime) -> dict[str, Any]:
    """One Change's status line, next action, chat handle and open question; shared with the chat fallback."""
    try:
        c = store.read(slug)
    except StoreError as exc:
        s = unloadable(exc.stop(now).model_copy(update={"reason": failure(exc)}))
        return {"slug": slug, **asdict(s)}
    tool = store.now(slug)
    s = status(c, act, now, tool)
    out = {"slug": slug, "handle": c.handle, "step": c.step.kind, **asdict(s)}
    out["title"] = c.brief.title
    out |= card(c, act, store.events(slug), now, tool, pending=store.shared.pending if store.shared else None)
    out["progress"] = asdict(progress(c))
    out["spend"] = c.spend.model_dump()
    out["tool_use"] = tool_metrics.of_change(spend_ledger.Where.of(store).clone, slug).model_dump()
    try:
        out["suppressions"] = suppressions(store, c)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        out["suppressions_fault"] = failure(exc)
    out["pullback"] = c.pullback.model_dump(mode="json") if c.pullback else None
    out["release_look"] = release_look.shown(store, c)
    out["watcher"] = watch_reports.counts(store.db, slug)  # observed calls writing outside, unresolved ones apart
    if q := loop.open_question(c):
        options = [o.model_dump(include={"id", "label"}) for o in held.offered(store, c, q)]
        where = "chat" if loop.ordinary(q) else "changes-page"
        out["question"] = {
            "id": f"{c.handle or slug}.{q.id}",
            "text": q.text,
            "cause": q.cause,
            "options": options,
            "answer_in": where,
        }
    return out


@functools.lru_cache(maxsize=32)
def _added(root: Path, base: str, head: str) -> list[Addition]:
    """What two commits add never changes, and the page asks every few seconds: read each pair once."""
    return added(quality.git, root, base, head)


def suppressions(store: Store, c: Change) -> list[dict[str, str]]:
    """Current added copies or the recorded verdicts when the worktree is gone."""
    if not c.names.worktree or not (root := Path(c.names.worktree)).exists():
        return [
            {key: row.get(key, "") for key in ("place", "directive", "verdict", "reason", "by")}
            for row in ledger.counting_scope(store.root, c.slug)
        ]
    if not c.names.target:
        return []
    head = worktree.head(root)
    target = worktree.tracking(root, c.names.target)
    base = worktree.git(root, "merge-base", target, head).strip()
    found = []
    for addition in _added(root, base, head):
        rows = exception_gate.ordered(ledger.counting(store.root, addition.identity, scope=c.slug))
        for n, place in enumerate(addition.places[: addition.count]):
            row = rows[n] if n < len(rows) else {}
            found.append(
                {
                    "place": f"{place.path}:{place.line}",
                    "directive": place.directive,
                    "verdict": row.get("verdict", "not judged"),
                    "reason": row.get("reason", "No verdict has been given for this Change."),
                    "by": row.get("by", ""),
                }
            )
    return found
