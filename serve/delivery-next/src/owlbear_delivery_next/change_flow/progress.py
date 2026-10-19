"""Where a Change stands: its stages in order, the current task and sub-step, and the round of its loop (TD-97).

A round counts one loop of the normal process, from Delivery's own records, never reset: a plan challenge or a
re-plan (``budgets.loops["plan"]``, ``budgets.replans``), a review that sends its task or the final review back
to fixing (``budgets.loops`` by ``round_key``), and a visual check that fails back to the build (a visual round
that ended ``back``). Retries after a crash or a network wait (``budgets.causes``) are never a round.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.change_contracts.models import VISUAL, StepKind
from owlbear_delivery_next.change_contracts.round_records import BRIEF, FINAL
from owlbear_delivery_next.change_flow.brief_rounds import MODES as CHALLENGING
from owlbear_delivery_next.change_flow.budgets import review_round

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Task

type State = Literal["done", "current", "upcoming", "skipped"]

STAGES = {
    "shape": "Shape",
    "plan": "Plan",
    "build": "Build",
    "final": "Final review",
    "publish": "Publish",
    "visual": "Visual check",
    "checks": "Your checks",
    "merge": "Merge",
}
_STAGE = {
    StepKind.SHAPE: "shape",
    StepKind.PLAN: "plan",
    StepKind.TESTS: "build",  # a test review's reviewers come before its curator's build (TD-373)
    StepKind.BUILD: "build",
    StepKind.REVIEW: "build",
    StepKind.INTEGRATE: "build",
    StepKind.PUBLISH: "publish",
    StepKind.FOLLOW: "publish",
    StepKind.CHECK: "checks",
    StepKind.MERGE: "merge",
    StepKind.CLEANUP: "merge",
}
_OWN = frozenset({"shape", "plan", "final"})  # the round keys that are not a task's scope
_VISUAL_FIX = ("Fix: the visual check of", "Fix: the owner failed the visual review of")  # decision.repair titles
_FINAL_FIX = "of the final review"  # in the title of a final review's repair task (steps/review.py)
_ORIGIN = {
    "ci": "Fixing CI",
    "pr-feedback": "Answering PR feedback",
    "person-check": "Fixing your check's findings",
    "integration": "Integration task",
}
_SUB = {
    StepKind.INTEGRATE: "Updating with the target",
    StepKind.FOLLOW: "Following the pull request",
    StepKind.CLEANUP: "Cleaning up",
}


@dataclass(frozen=True)
class Stage:
    """One workflow stage; ``rounds`` is 1 until the stage loops."""

    key: str
    label: str
    state: State
    rounds: int


@dataclass(frozen=True)
class Progress:
    """The stages, the current one with its task position and sub-step, and the round of the current loop."""

    stages: list[Stage]
    current: str | None
    task: int | None
    tasks: int | None
    sub: str | None
    round: int
    line: str | None


def _kind(c: Change) -> StepKind:
    return StepKind(c.step.mode) if c.step.kind == StepKind.INTEGRATE and c.step.mode else c.step.kind


def _current(c: Change) -> str:
    kind, task = _kind(c), c.step.task
    if kind == StepKind.REVIEW and task is None:
        return "final"
    return "visual" if kind == StepKind.CHECK and task == VISUAL else _STAGE[kind]


def _rounds(c: Change) -> dict[str, int]:
    r = c.budgets.loops  # never reset, so a round shown never goes down and a finished stage keeps its badge
    return {
        "shape": (c.loops[BRIEF].round if BRIEF in c.loops else 0) + 1,  # the brief challenge's rounds (TD-221)
        "plan": r.get("plan", 0) + c.budgets.replans + 1,
        "build": max((n for k, n in r.items() if k not in _OWN), default=0) + 1,
        "final": r.get("final", 0) + 1,
        "visual": sum(v.outcome == "back" for v in c.visual_rounds) + 1,
    }


def _task(c: Change) -> Task | None:
    return next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None


def _root(c: Change, task: Task | None) -> Task | None:
    """The task whose review findings *task* repairs, through every repair of a repair."""
    tasks = {t.id: t for t in c.plan.tasks} if c.plan else {}
    seen: set[str] = set()
    while task and task.fixes in tasks and task.id not in seen:
        seen.add(task.id)
        task = tasks[task.fixes]
    return task


def _position(c: Change) -> tuple[int | None, int | None]:
    """The planned task being worked on, as its place among the planned tasks."""
    planned = [t.id for t in c.plan.tasks if t.origin == "plan"] if c.plan else []
    root = _root(c, _task(c)) if c.step.task and c.step.kind != StepKind.CHECK else None
    return (planned.index(root.id) + 1, len(planned)) if root and root.id in planned else (None, None)


def _work(c: Change, rounds: dict[str, int]) -> tuple[str | None, int]:  # noqa: C901, PLR0911 - one case per step
    """The sub-step and the round of its loop."""
    s, kind, task = c.step, _kind(c), _task(c)
    own = review_round(c)
    if s.kind == StepKind.INTEGRATE and kind != StepKind.INTEGRATE:  # the round of the loop it interrupted
        return _SUB[s.kind], _work(c.model_copy(update={"step": s.model_copy(update={"kind": kind})}), rounds)[1]
    if s.kind in _SUB:
        return _SUB[s.kind], 1
    if kind == StepKind.SHAPE:
        return ("Brief challenge" if c.step.mode in CHALLENGING else None), rounds["shape"]
    if kind == StepKind.PLAN:
        again = "Re-planning after the plan challenge" if c.budgets.loops.get("plan") else "Re-planning"
        return (again if rounds["plan"] > 1 else None), rounds["plan"]
    if kind == StepKind.REVIEW:
        return ("Task review", own) if s.task else (None, rounds["final"])
    if kind == StepKind.CHECK:
        return ("Visual review", rounds["visual"]) if s.task == VISUAL else (f"Check {s.task}", 1)
    if kind != StepKind.BUILD or task is None:
        return None, 1
    if task.fixes == FINAL:
        return "Fixing final review findings", rounds["final"]
    if task.origin == "review" and task.fixes is None:  # a repair of no task: the visual check's or the final review's
        if task.title.startswith(_VISUAL_FIX):
            return "Fixing visual findings", rounds["visual"]
        if _FINAL_FIX in task.title:
            return "Fixing final review findings", rounds["final"]
        return "Fixing findings", 1
    return ("Fixing review findings" if task.fixes else _ORIGIN.get(task.origin)), own


def _state(at: int, i: int, *, skipped: bool, finished: bool) -> State:
    if skipped:
        return "skipped"
    if finished or i < at:
        return "done"
    return "current" if i == at else "upcoming"


def progress(c: Change) -> Progress:
    """Derive the progress display of *c* from its records alone."""
    rounds = _rounds(c)
    keys = list(STAGES)
    unused = {"visual"} if not c.brief.visual else set()
    unused |= {"checks"} if not c.checks else set()
    gone = bool(c.intent.abandoned_at) or c.step.mode == "abandon"
    if gone:
        unused = set(keys)
    finished = c.finished_at is not None and not gone
    current = None if gone or finished else _current(c)
    at = keys.index(current) if current else len(keys)
    stages = [
        Stage(k, STAGES[k], _state(at, i, skipped=k in unused, finished=finished), rounds.get(k, 1))
        for i, k in enumerate(keys)
    ]
    if current is None:
        return Progress(stages, None, None, None, None, 1, None)
    task, tasks = _position(c)
    sub, n = _work(c, rounds)
    parts = [STAGES[current], f"Task {task} of {tasks}" if task else None, sub, f"round {n}" if n > 1 else None]
    return Progress(stages, current, task, tasks, sub, n, " · ".join(p for p in parts if p))
