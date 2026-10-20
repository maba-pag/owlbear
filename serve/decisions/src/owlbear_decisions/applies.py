"""Whether a decision applies to a Change's work: its state, its scope and its typed selectors (§7)."""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_decisions.models import Scope, State

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_decisions.models import Decision

_MAGIC = frozenset("*?[")


def applies(
    decision: Decision, *, paths: Sequence[str], role: str | None, step: str | None, change: str = ""
) -> bool | None:
    """True or False, or None when the Change's scope cannot tell yet; None counts as applying, marked so.

    Only an in-force decision applies; a Change decision only to its own Change (*change*, its record stem).
    """
    if decision.state is not State.IN_FORCE:
        return False
    return matches(decision, paths=paths, role=role, step=step, change=change)


def matches(
    decision: Decision, *, paths: Sequence[str], role: str | None, step: str | None, change: str = ""
) -> bool | None:
    """`applies` without the state: whether its scope and selectors reach this work. None role or step: any."""
    if decision.scope is Scope.CHANGE and decision.change != change:
        return False
    selectors = decision.applies_to
    if role is not None and selectors.roles and role not in selectors.roles:
        return False
    if step is not None and selectors.steps and step not in selectors.steps:
        return False
    if not selectors.paths:
        return True
    scope = [p for p in paths if p.strip()]
    if not scope:
        return None
    return any(overlap(glob, path) for glob in selectors.paths for path in scope)


def _parts(path: str) -> tuple[str, ...]:
    return tuple(p for p in PurePosixPath(path.strip()).parts if p not in {".", "/"})


def _opened(scope: str, parts: tuple[str, ...]) -> bool:
    """Whether a scope entry may hold paths under it: a directory, or a last name without a file extension."""
    return scope.strip().endswith("/") or not parts or "." not in parts[-1].lstrip(".")


def overlap(glob: str, scope: str) -> bool:
    """Whether a decision's *glob* and a Change's *scope* entry can name a common path.

    Segment by segment: `**` spans any number of segments and the rest of the glob still has to match. The glob
    covers what lies under it, and so does a scope entry that may be a directory (`web` means `web/**`). Generous:
    a wildcard in the scope entry matches any segment, and `**` in it any number of them.
    """
    have = _parts(scope)
    return _meet(_parts(glob), have, opened=_opened(scope, have))


def _meet(want: tuple[str, ...], have: tuple[str, ...], *, opened: bool) -> bool:
    if not want:
        return True
    if not have:
        return opened or all(w == "**" for w in want)
    if "**" in have[0]:
        return True
    if want[0] == "**":
        return _meet(want[1:], have, opened=opened) or _meet(want, have[1:], opened=opened)
    if not (_MAGIC.intersection(have[0]) or fnmatchcase(have[0], want[0])):
        return False
    return _meet(want[1:], have[1:], opened=opened)
