"""The "Decisions in force" section of a step's input (TD-452, TD-456, TD-457): the Change's pinned set, whole.

The runner's gate loads the decisions once per step and holds the section while the step runs, so every input built
for that step (the worker's, a judge's, any role's) carries the same pinned set: the decisions picked for the Change
and its own, or every one in force when it was approved without a pick. A challenger's input (`held(complete=True)`)
adds the complete list of the others in force to check the pinned set against. Binding text is never cut and has no
size limit. One runner process runs one step.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store.decision_archive import WHOLE, whole

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Sequence

    from owlbear_decisions import Decision
    from owlbear_delivery_next.change_contracts.decision_records import BriefDecision
    from owlbear_delivery_next.change_contracts.decision_records import Decision as ChangeDecision

SHAPED = 30  # the brief's own decisions listed; brief_tools.DecisionDraft bounds each question and answer
HEAD = "## Decisions in force (the lasting rules this Change follows: follow them; a conflict goes to the owner)"
NONE = "- none recorded: this project has no shared data repository"
COMPLETE = (
    "## The complete list: every other decision in force (check the decisions above against it: one here that "
    "governs this work but is missing above is a finding)"
)
_HELD: list[tuple[list[str], list[str]]] = []


def shaped(decisions: Sequence[BriefDecision]) -> list[str]:
    """The brief's own decisions as the shaper recorded them, each whole on one line."""
    if not (kept := list(decisions)[:SHAPED]):
        return []
    head = "Decisions while shaping (origin: decided by the owner, approved with the brief, or autonomous):"
    return ["", head, *(f"- {' '.join(d.question.split())} -> {' '.join(d.answer.split())} ({d.origin})" for d in kept)]


def entry(decision: Decision, *, replaced: bool = False) -> str:
    """One decision in full: id and aliases, scope, origin, title and statement, a cut one's whole wording too."""
    names = ", ".join([decision.id, *decision.aliases])
    note = " [this Change's brief replaces it]" if replaced else ""
    statement = " ".join(decision.statement.split())
    expanded = " ".join(whole(decision).split())
    if expanded != statement:
        statement += f" ({WHOLE}{expanded})"  # the archive cut a long answer and kept it whole in the rationale
    return f"- {names} ({decision.scope}, {decision.origin}): {' '.join(decision.title.split())}: {statement}{note}"


def section(pinned: Sequence[Decision], replaced: Collection[str] = ()) -> list[str]:
    """The section every role of a step reads: each pinned decision whole."""
    return [HEAD, *(entry(d, replaced=d.id in replaced) for d in pinned)] if pinned else [HEAD, "- none in force"]


def own(lines: list[str] | None, recorded: Sequence[ChangeDecision]) -> list[str] | None:
    """*lines* with the decisions recorded on the Change during its work, such as a confirmed clarification (TD-461).

    They hold for this Change alone, in force from when they were recorded, whole like every other.
    """
    if lines is None or not recorded:
        return lines
    mine = [f"- {d.id or 'this Change'} (change, {d.origin}): {_titled(d)}" for d in recorded]
    return [lines[0], *mine, *(x for x in lines[1:] if x != "- none in force")]


def _titled(d: ChangeDecision) -> str:
    text = " ".join(d.text.split())
    return f"{' '.join(d.title.split())}: {text}" if d.title else text


def complete(others: Sequence[Decision]) -> list[str]:
    """What a challenger reads besides the section: every other decision in force, whole."""
    return ["", COMPLETE, *(entry(d) for d in others)] if others else ["", COMPLETE, "- none: the list above is all"]


@contextmanager
def using(lines: list[str] | None, others: list[str] | None = None) -> Iterator[None]:
    """Hold *lines* as the section of every input built until the block ends, *others* for challengers too."""
    _HELD.append((lines or [], others or []))
    try:
        yield
    finally:
        _HELD.pop()


def held(*, complete: bool = False) -> list[str]:
    """The section held for the running step after a blank line, a challenger's (*complete*) with the complete list."""
    if not (_HELD and _HELD[-1][0]):
        return []
    lines, others = _HELD[-1]
    return ["", *lines, *(others if complete else [])]


def resumed(message: str) -> str:
    """A message to a resumed session with the held section, so decisions accepted since it started reach it."""
    return "\n".join([message, *held()])
