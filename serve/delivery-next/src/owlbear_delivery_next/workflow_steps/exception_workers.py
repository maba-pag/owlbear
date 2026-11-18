"""The builder's and test curator's nonterminal, committed-only exception helper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_quality import ledger
from owlbear_quality.inspect import added

from owlbear_delivery_next.change_contracts import exception_tools
from owlbear_delivery_next.change_flow import exception_gate, quality, worktree
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.workflow_steps import exceptions, lookup

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts import tools
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Lock, Store


def worker(store: Store, c: Change, root: Path, where: spend_ledger.Where) -> tuple[dict[str, Any], Run | None]:
    """Judge up to 60 unjudged added copies; a dirty tree must be committed before calling again."""
    if worktree.git(root, "status", "--porcelain").strip():
        msg = "Commit first, then call judge_exceptions: the worktree is dirty; only commits are read."
        return {"failed": msg}, None
    base, head, _ = quality.current(c, root)
    items = exception_gate.pending(c, root, store.root, (base, head))
    items = exception_gate.approved(c, store.root, head, items)
    waiting = [item for item in items if not item["refusal"]]
    done = None
    if waiting:
        context = exceptions.authority(store, c) | {"for": c.slug, "commit": head}
        said, done = exceptions.judge(store, root, waiting[: exceptions.LIMIT], where, context)
        if "failed" in said:
            return said, done
    verdicts = []
    for addition in added(quality.git, root, base, head):
        rows = exception_gate.ordered(ledger.counting(store.root, addition.identity, scope=c.slug))
        verdicts.extend(
            {"place": row["place"], "verdict": row["verdict"], "reason": row["reason"]}
            for row in rows[: addition.count]
        )
    reply: dict[str, Any] = {"verdicts": verdicts}
    if len(waiting) > exceptions.LIMIT:
        reply["note"] = "More unjudged copies remain. Call judge_exceptions again before submitting."
    return reply, done


class Asked(lookup.Asked):
    """Use lookup's admission, teardown and caller-owned spend accounting for the exception judge."""

    def __init__(self, store: Store, lock: Lock, current: Callable[[], Change], root: Path) -> None:
        """Bind host-owned Change, checkout and spend location, never agent-supplied identity."""
        place = spend_ledger.where()
        if not place.project:
            change = current()
            place = spend_ledger.Where.of(store, change=change.slug, step=str(change.step.kind), job=exceptions.JOB)
        super().__init__(store, lock, current, answer=lambda _: worker(store, current(), root, place))
        self.label = exceptions.JOB

    def helper(self) -> tuple[tools.Spec, Callable[[tools.Args], str]]:
        """No arguments: all items and identities come from committed Git trees."""
        return exception_tools.HELPER, self
