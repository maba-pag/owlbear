"""Dispatch logic for the owlbear kanban engine.

Provides pick_dispatchable() — a gate-filtered, priority/status-sorted list of
tasks ready for agent dispatch.

Rank maps use *execution priority* order, which is intentionally the inverse of
the config.yml display order:
  - PRIORITY_RANK: critical=0 (highest) → someday=4 (lowest)
    Config display order: someday first, critical last (opposite).
    - STATUS_RANK: released=0 (highest) → research=7 (lowest)
    Config display order: research first, done last (opposite).
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
    "critical": 0,
    "needed": 1,
    "important": 2,
    "nice-to-have": 3,
    "someday": 4,
}

STATUS_RANK: dict[str, int] = {
    "released": 0,
    "done": 1,
    "docs": 2,
    "review": 3,
    "in-progress": 4,
    "todo": 5,
    "backlog": 6,
    "research": 7,
}

# ---------------------------------------------------------------------------
# Gate constants
# ---------------------------------------------------------------------------

_AC_PATTERN = re.compile(r"(?m)^\s*(-\s|\d+\.\s)")

_CLARITY_STATUSES = frozenset({"todo", "in-progress", "review", "docs", "done"})

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


def _passes_tdd_gate(task: Task) -> bool:
    """Return True if the task passes the TDD gate.

    Gate applies only to in-progress tasks:
    - PASS if body contains '## Test-Writer Notes'
    - PASS if body contains '## Builder Notes' or '## Review Evidence'
      (task re-entered in-progress after a review cycle)
    - PASS if any tag is a non-impl tag (exempt from TDD requirement)
    - FAIL otherwise
    """
    if task.status != "in-progress":
        return True
    body: str = task.body or ""
    if "## Test-Writer Notes" in body:
        return True
    if "## Builder Notes" in body or "## Review Evidence" in body:
        return True
    tags: list[str] = task.tags or []
    return bool(_NON_IMPL_TAGS.intersection(tags))


def _passes_clarity_gate(task: Task) -> bool:
    """Return True if the task passes the clarity gate.

    Gate applies to active statuses (todo, in-progress, review, docs, done):
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


def pick_dispatchable(  # noqa: C901
    engine: KanbanEngine, *, limit: int = 25, tag: str = ""
) -> list[Task]:
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
    6. TDD gate — in-progress tasks need ## Test-Writer Notes or a non-impl tag.
    7. Clarity gate — active-status tasks need at least one bullet/numbered AC line.

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
        if not _passes_tdd_gate(task):
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
