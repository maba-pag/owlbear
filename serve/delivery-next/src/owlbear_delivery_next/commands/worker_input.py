"""Within-turn helpers, planning scopes and pre-worker tree preservation."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.impeccable import design_tools
from owlbear_delivery_next.workflow_steps import design, overlap, sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts import tools
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Lock, Store
    from owlbear_delivery_next.workflow_steps.lookup import Asked


def helpers(change: Change, at: Path, asked: Asked) -> tuple[tuple[tools.Spec, Callable[[tools.Args], str]], ...]:
    """The tools that answer within the turn: the builder's design detector on a UI Change (slice 7), the lookup."""
    ui = change.step.kind == StepKind.BUILD and change.brief.ui
    return (*(((design_tools.SCAN, partial(design.builder_scan, at)),) if ui else ()), asked.helper())


def planning(store: Store, lock: Lock, slug: str, path: Path) -> dict[str, list[str]]:
    """The read-only planner needs a clean tree: edits an earlier step left are kept in a stash first.

    Returns:
        The other open Changes' scopes the planner avoids.
    """
    message = f"owlbear {slug}: uncommitted edits before planning"
    if worktree.shelve(path, message):
        store.log(lock, slug, {"event": "shelved", "at": datetime.now(UTC).isoformat(timespec="seconds")})
        sessions.out(f"{slug}: uncommitted edits kept in `git stash list` as '{message}'")
    return overlap.scopes(store, slug)
