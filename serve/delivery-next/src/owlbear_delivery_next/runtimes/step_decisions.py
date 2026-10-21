"""The "Decisions in force" section of a step's input (TD-419 slice 4, §7): every applicable decision, whole.

The runner's gate loads the decisions once per step and holds the section while the step runs, so every input built
for that step (the worker's, a challenger's, a judge's) carries the same text. One runner process runs one step.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Sequence

    from owlbear_decisions import Decision
    from owlbear_delivery_next.change_contracts.decision_records import BriefDecision

BUDGET = 12_000  # characters of mandatory decision text, apart from every other limit; never cut
SHAPED = 30  # the brief's own decisions listed; brief_tools.DecisionDraft bounds each question and answer
UNRESOLVED = " [unresolved applicability]"
HEAD = "## Decisions in force (the project's and Global lasting rules: follow them; a conflict goes to the owner)"
NONE = "- none recorded: this project has no shared data repository"
_HELD: list[list[str]] = []


def shaped(decisions: Sequence[BriefDecision]) -> list[str]:
    """The brief's own decisions as the shaper recorded them, each whole on one line."""
    if not (kept := list(decisions)[:SHAPED]):
        return []
    head = "Decisions while shaping (origin: decided by the owner, approved with the brief, or autonomous):"
    return ["", head, *(f"- {' '.join(d.question.split())} -> {' '.join(d.answer.split())} ({d.origin})" for d in kept)]


def entry(decision: Decision, *, resolved: bool, replaced: bool = False) -> str:
    """One decision in full: id and aliases, scope, origin, title and statement."""
    names = ", ".join([decision.id, *decision.aliases])
    note = (UNRESOLVED if not resolved else "") + (" [this Change's brief replaces it]" if replaced else "")
    statement = " ".join(decision.statement.split())
    return f"- {names} ({decision.scope}, {decision.origin}): {' '.join(decision.title.split())}: {statement}{note}"


def section(applying: Sequence[tuple[Decision, bool]], others: int, replaced: Collection[str] = ()) -> list[str]:
    """The section: each applying decision with whether its applicability resolved, then the count of the rest."""
    lines = [HEAD, *(entry(d, resolved=r, replaced=d.id in replaced) for d, r in applying)]
    if not applying:
        lines.append("- none applies to this step")
    if others:
        lines.append(f"{others} other decision(s) in force do not apply to this step and are not listed.")
    return lines


def size(lines: Sequence[str]) -> int:
    """The characters of the section's decision entries, measured against `BUDGET`."""
    return sum(len(line) + 1 for line in lines if line.startswith("- D-"))


@contextmanager
def using(lines: list[str] | None) -> Iterator[None]:
    """Hold *lines* as the section of every input built until the block ends; None holds none."""
    _HELD.append(lines or [])
    try:
        yield
    finally:
        _HELD.pop()


def held() -> list[str]:
    """The section held for the running step, with a blank line before it; nothing outside a gated step."""
    return ["", *_HELD[-1]] if _HELD and _HELD[-1] else []


def resumed(message: str) -> str:
    """A message to a resumed session with the held section, so decisions accepted since it started reach it."""
    return "\n".join([message, *held()])
