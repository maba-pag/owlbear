"""The fresh read-only challenge of a worker's proposed amendment, run after the step that proposed it (TD-179)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next import amendments, sdk_adapter, sessions
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.session_result import Run
    from owlbear_delivery_next.store import Lock, Store


def challenge(store: Store, lock: Lock, change: Change, path: Path, run: Run) -> None:
    """Record the exact candidate first, then judge it; the proposing step's own result keeps its route."""
    made = amendments.prepared(change, run, datetime.now(UTC))
    if made is None:
        return
    store.write(lock, change)  # durable before its challenge runs: a lost challenge leaves it unjudged

    def config(at: Path) -> sdk_adapter.Session:
        return sdk_adapter.Session(
            kind=StepKind.REVIEW,
            worktree=at,
            session_id="",
            message=amendments.prompt(change, made, at),
            resume=False,
            policy=Policy(at, write=False),
            observe=lambda: worktree.observe(at, change.names.target),
            checks=(),
            journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)),
            memory=sessions.memory(store),
        )

    _, done = sessions.review_run(store, lock, change, path, config, amendments.LABEL, submit=amendments.SUBMIT)
    amendments.judged(made, done)
    store.write(lock, change)
