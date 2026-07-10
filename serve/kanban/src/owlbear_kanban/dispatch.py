"""Dispatch logic for the owlbear kanban engine.

Provides pick_dispatchable() — a gate-filtered, priority/status-sorted list of
tasks ready for agent dispatch.

Rank maps use *execution priority* order, which is intentionally the inverse of
the config.yml display order:
    - PRIORITY_RANK: high=0 (highest) → low=2 (lowest)
        Config display order: low first, high last (opposite).
    - STATUS_RANK: collect=0 (highest) → shape=3 (lowest)
    Config display order: shape first, collect last (opposite).
"""

from __future__ import annotations

import re
import warnings
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_kanban.engine import KanbanEngine
    from owlbear_kanban.models import Task

from owlbear_kanban.topology import PRODUCT_TOPOLOGY

# ---------------------------------------------------------------------------
# Rank maps — execution priority (intentionally ≠ config display order)
# ---------------------------------------------------------------------------

PRIORITY_RANK: dict[str, int] = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

STATUS_RANK: dict[str, int] = {
    "collect": 0,
    "verify": 1,
    "build": 2,
    "shape": 3,
}

# ---------------------------------------------------------------------------
# Gate constants
# ---------------------------------------------------------------------------

_AC_PATTERN = re.compile(r"(?m)^\s*(-\s|\d+\.\s)")

_CLARITY_STATUSES = frozenset({"build", "verify", "collect"})

_NON_IMPL_TAGS = PRODUCT_TOPOLOGY.non_impl_tags

_MAX_PRIORITY_RANK = max(PRIORITY_RANK.values())
_MAX_STATUS_RANK = max(STATUS_RANK.values())

_TERMINAL_STATUSES = frozenset({"archived"})


# ---------------------------------------------------------------------------
# Gate predicates
# ---------------------------------------------------------------------------


def _claim_is_active(task: Task, timeout: timedelta) -> bool:
    """Return True if the task's claim has not expired."""
    if not task.claimed_at:
        return False
    claimed_dt = datetime.fromisoformat(task.claimed_at)
    if claimed_dt.tzinfo is None:
        claimed_dt = claimed_dt.replace(tzinfo=UTC)
    return datetime.now(tz=UTC) < claimed_dt + timeout


def _passes_clarity_gate(task: Task) -> bool:
    """Return True if the task passes the clarity gate.

    Gate applies to build/verify/collect tasks:
    - PASS if the structured ac field has entries
    - PASS if body contains a bullet or numbered list item
    - FAIL if body is empty or prose-only with no structured AC
    """
    if task.status not in _CLARITY_STATUSES:
        return True
    if task.ac:
        return True
    body: str = task.body or ""
    return bool(_AC_PATTERN.search(body))


def _passes_dependency_gate(task: Task, active_ids: frozenset[int]) -> bool:
    """Return True if all depends_on IDs are resolved (not in active tasks).

    A dependency is met when its task ID is absent from the active task set
    (i.e. archived or purged).  Any dependency still present in the tasks
    directory — regardless of status, including ``done`` — is considered unmet.
    """
    deps: list[int] = task.depends_on or []
    if not deps:
        return True
    return not any(dep_id in active_ids for dep_id in deps)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def pick_dispatchable(engine: KanbanEngine, *, limit: int = 25, tag: str = "") -> list[Task]:
    """Return a gate-filtered, sorted list of dispatchable tasks.

    Reads full Task objects (including body) directly from the filesystem so
    that gate predicates execute against the actual task body, not the
    body-stripped TaskSummary returned by engine.list_tasks().

    Gates applied (in order):
    1. Terminal status exclusion — archived/done tasks are excluded.
    2. Blocked exclusion — blocked=True tasks are excluded.
    3. Dependency gate — tasks whose depends_on IDs are still active are excluded.
    4. Claimed exclusion — tasks with an active (non-expired) claim are excluded.
    5. Tag filter — when tag is non-empty, only tasks carrying that tag pass.
    6. Clarity gate — build/verify/collect tasks need at least one bullet/numbered AC line.

    Results are sorted by (PRIORITY_RANK, STATUS_RANK) ascending and capped at limit.

    Args:
        engine: KanbanEngine instance providing filesystem access.
        limit:  Maximum number of tasks to return. Defaults to 25.
        tag:    If non-empty, only include tasks tagged with this value.

    Returns:
        Sorted, capped list of Task instances.
    """
    warnings.warn(
        "pick_dispatchable() is deprecated; use AgentView.pick_tasks() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    tasks: list[Task] = []
    for path in sorted(engine._tasks_dir.glob("*.md")):  # noqa: SLF001
        task_id = path.stem.split("-", 1)[0]
        if not task_id.isdigit():
            continue
        tasks.append(engine.show_task(task_id))

    active_ids: frozenset[int] = frozenset(t.id for t in tasks if t.id is not None)
    claim_timeout = engine._parse_claim_timeout()  # noqa: SLF001

    passing: list[Task] = []
    for task in tasks:
        if task.status in _TERMINAL_STATUSES:
            continue
        if task.blocked:
            continue
        if not _passes_dependency_gate(task, active_ids):
            continue
        if _claim_is_active(task, claim_timeout):
            continue
        if tag and tag not in (task.tags or []):
            continue
        if not _passes_clarity_gate(task):
            continue
        passing.append(task)

    passing.sort(
        key=lambda t: (
            PRIORITY_RANK.get(t.priority or "", _MAX_PRIORITY_RANK + 1),
            STATUS_RANK.get(t.status or "", _MAX_STATUS_RANK + 1),
        )
    )

    return passing[:limit]
