"""Gate predicate functions for the OwlBear dispatch planner.

Gates 1 (status), 2 (dependency), and 6 (claim) are handled upstream by CLI
flags passed to read_board(). The two predicates here cover:
  - Gate 4: TDD readiness (in-progress tasks without a non-impl tag must have
    Test-Writer Notes; non-impl pass-through tasks are exempt)
  - Gate 5: clarity (active tasks must have bullet or numbered AC)

Atomicity (single-concern) is evaluated by the architect during review, not
as a hard dispatch gate.  Multi-concern tasks get routed to the planner via
the existing ``Needs decomposition:`` body marker.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.planner.models import Task

_AC_PATTERN = re.compile(r"(?m)^\s*(-\s|\d+\.\s)")
_CLARITY_STATUSES = frozenset({"todo", "in-progress", "review", "docs", "done"})
_NON_IMPL_TAGS = frozenset(
    {
        "research",
        "docs",
        "type:config",
        "type:docs",
        "test",
        "type:test",
        "agent",
        "quality",
        "type:user-action",
    }
)


def check_tdd(task: Task) -> bool:
    """Return True unless the task is in-progress without Test-Writer Notes.

    An in-progress task signals that the builder must implement; it must have
    the Test-Writer Notes marker confirming the RED phase is complete.
    Non-implementation pass-through tasks (tagged with a non-impl tag) are
    exempt — they pass through without Test-Writer Notes.
    All other statuses pass this gate unconditionally.
    """
    if task.status == "in-progress":
        if _NON_IMPL_TAGS.intersection(task.tags):
            return True
        return "## Test-Writer Notes" in task.body
    return True


def check_clarity(task: Task) -> bool:
    """Return True if the task has bullet or numbered acceptance criteria.

    Active statuses (todo, in-progress, review, docs, done) require at least
    one bullet (- item) or numbered list item (1. item) in the body.
    Pre-pipeline statuses (research, backlog) are exempt — AC not required yet.
    """
    if task.status in _CLARITY_STATUSES:
        return bool(_AC_PATTERN.search(task.body))
    return True


def check_gates(task: Task) -> bool:
    """Composite gate: returns True only if TDD and clarity gates pass.

    Gates 1, 2, and 6 are handled by CLI flags in read_board() before this
    function is called.  Atomicity is evaluated by the architect during
    review, not as a dispatch gate.
    """
    return check_tdd(task) and check_clarity(task)
