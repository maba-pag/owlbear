"""Evidence validity: when a recorded review, check or visual answer holds, and what a Change must show (P5, F3)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.models import Inputs

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from owlbear_delivery_next.models import Change, PersonCheck, Review

TREE = ":tree"  # the fingerprint key of a check without declared paths
type Need = Literal["none", "states", "person", "unmet"]


def need(*, ui: bool, states: bool, person: bool) -> Need:
    """The one visual rule: states are captured; else a UI Change needs a person check with ``visual: true``."""
    if states:
        return "states"
    if not ui:
        return "none"
    return "person" if person else "unmet"


def within(a: str, b: str) -> bool:
    """One path contains the other; an empty or root scope contains every path."""
    pa, pb = (tuple(x for x in PurePosixPath(p).parts if x != "/") for p in (a, b))
    n = min(len(pa), len(pb))
    return pa[:n] == pb[:n]


def inputs_valid(recorded: Inputs, current: Inputs) -> bool:
    """A review or check answer stays valid while every input it recorded is unchanged (P5)."""
    return (
        all(current.criteria.get(k) == v for k, v in recorded.criteria.items())
        and all(current.paths.get(p) == f for p, f in recorded.paths.items())
        and (recorded.procedure, recorded.environment) == (current.procedure, current.environment)
    )


def check_valid(recorded: Inputs, current: Inputs) -> bool:
    """A person-only check answer holds only while its covered paths are exactly as recorded, added ones included."""
    return recorded.paths == current.paths and inputs_valid(recorded, current)


def changed(recorded: Inputs, current: Inputs) -> list[str]:
    """Name each check input that no longer holds: a criterion, a path, the check's steps or its environment."""
    names = [k for k, v in recorded.criteria.items() if current.criteria.get(k) != v]
    paths = [p for p, f in recorded.paths.items() if current.paths.get(p) != f]
    names += ["the worktree" if p == TREE else p for p in paths + [p for p in current.paths if p not in recorded.paths]]
    names += ["the check's steps"] if recorded.procedure != current.procedure else []
    return names + (["the environment"] if recorded.environment != current.environment else [])


def coverage(c: Change) -> list[str]:
    """Conservative paths of a person-only check: the brief's scope and every task's scope."""
    tasks = c.plan.tasks if c.plan else []
    return sorted({*c.brief.scope, *(p for t in tasks for p in t.scope)})


def cover(c: Change) -> None:
    """Set every person-only check's paths to the Change's current coverage."""
    for check in c.checks:
        check.paths = coverage(c)


def criteria(c: Change) -> dict[str, int]:
    """The current version of each brief criterion."""
    return {k.id: k.version for k in c.brief.criteria}


def review_valid(c: Change, review: Review, paths: Mapping[str, str], changed: Iterable[str] | None = None) -> bool:
    """Return whether a passing review still holds for the observed fingerprints and, given, the changed paths.

    Every path changed against the base must lie in the review's engine-computed coverage (F3).
    """
    if changed is not None and not set(changed) <= review.inputs.paths.keys():
        return False
    return review.verdict == "pass" and inputs_valid(review.inputs, Inputs(criteria=criteria(c), paths=dict(paths)))


def check_inputs(c: Change, check: PersonCheck, paths: Mapping[str, str]) -> Inputs:
    """Return the current inputs of one person-only check from the brief and observed paths.

    A check without declared paths depends on the whole tree (``TREE``), so any tree change voids it (F3).
    """
    crit = criteria(c)
    return Inputs(
        criteria={k: crit[k] for k in check.criteria if k in crit},
        paths={
            k: f
            for k, f in paths.items()
            if (k != TREE and any(within(k, p) for p in check.paths)) or (k == TREE and not check.paths)
        },
        procedure=check.procedure,
        environment=check.environment,
    )


def visual_valid(c: Change, head: str | None, tree: str | None = None) -> bool:
    """A passed visual result holds only for its exact head (and tree, when given) and the current state versions."""
    r = c.visual
    if r is None or not r.passed or r.head != head or (tree is not None and r.tree != tree):
        return False
    return r.states == {s.name: s.version for s in c.brief.visual} and r.criteria == criteria(c)


def next_check(c: Change, paths: Mapping[str, str]) -> PersonCheck | None:
    """Return the first declared person-only check without a valid passing answer."""
    for check in c.checks:
        answer = check.answer
        if not (answer and answer.passed and answer.inputs):
            return check
        if not check_valid(answer.inputs, check_inputs(c, check, paths)):
            return check
    return None
