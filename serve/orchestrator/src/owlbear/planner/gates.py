"""Gate predicate functions for the OwlBear dispatch planner.

Gates 1 (status), 2 (dependency), and 6 (claim) are handled upstream by CLI
flags passed to read_board(). The three predicates here cover:
  - Gate 3: atomicity (single-concern title heuristic)
  - Gate 4: TDD readiness (in-progress tasks must have Test-Writer Notes)
  - Gate 5: clarity (active tasks must have bullet or numbered AC)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.planner.models import Task

_AND_PATTERN = re.compile(r"\band\b", re.IGNORECASE)
_AC_PATTERN = re.compile(r"(?m)^\s*(-\s|\d+\.\s)")
_CLARITY_STATUSES = frozenset({"todo", "in-progress", "review", "docs", "done"})


def check_atomicity(task: Task) -> bool:
    """Return True if the task title has no word-boundary 'and'.

    This is a heuristic approximation for single-concern scope.
    False positives (e.g. 'sandwich') are prevented by word boundaries.
    Tasks that fail re-enter the next dispatch cycle automatically.
    """
    return not bool(_AND_PATTERN.search(task.title))


def check_tdd(task: Task) -> bool:
    """Return True unless the task is in-progress without Test-Writer Notes.

    An in-progress task signals that the builder must implement; it must have
    the Test-Writer Notes marker confirming the RED phase is complete.
    All other statuses pass this gate unconditionally.
    """
    if task.status == "in-progress":
        return "## Test-Writer Notes" in task.body
    return True


def check_clarity(task: Task) -> bool:
    """Return True if the task has bullet or numbered acceptance criteria.

    Active statuses (todo, in-progress, review, docs, done) require at least
    one bullet (- item) or numbered list item (1. item) in the body.
    Pre-pipeline statuses (ideation, backlog) are exempt — AC not required yet.
    """
    if task.status in _CLARITY_STATUSES:
        return bool(_AC_PATTERN.search(task.body))
    return True


def check_gates(task: Task) -> bool:
    """Composite gate: returns True only if atomicity, TDD, and clarity all pass.

    Gates 1, 2, and 6 are handled by CLI flags in read_board() before this
    function is called.
    """
    return check_atomicity(task) and check_tdd(task) and check_clarity(task)
