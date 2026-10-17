"""Rebuilding rejected work (TD-210, TD-217): the owner's task list, which commits an undo takes, the fresh attempts.

After the final review's last round the owner ticks plan tasks to rebuild: a task with an open finding starts
ticked, and a kept task that shares changed files with a ticked one may depend on it. The undo takes the ticked tasks'
own commits (what their build sessions made), their task-loop repairs' and those of each final repair whose fixed
findings name only ticked tasks of the current plan. Undone work belongs to no task afterwards, so no later undo
reverts it twice.
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.round_records import FINAL, RoundLoop
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.change_flow.moves import go, open_task, subject_of
from owlbear_delivery_next.change_flow.round_flow import PREFIX
from owlbear_delivery_next.change_flow.round_marks import kind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.change_contracts.models import Change, Question, Task
    from owlbear_delivery_next.change_contracts.profile_record import Profile


def asking(c: Change, q: Question | None) -> RoundLoop | None:
    """The final loop while *q* is its open last-round question offering a rebuild."""
    final = q is not None and q.answer is None and (q.cause or "").startswith(f"{PREFIX}{FINAL} ")
    return c.loops.get(FINAL) if final and any(o.id == "rebuild" for o in q.options) else None


def head(lp: RoundLoop) -> str:
    """The commit the owner's question was asked at: the last repair's, else the last reviewed one."""
    return lp.completion.head if lp.completion else lp.head


def shown(c: Change, q: Question | None) -> dict[str, object] | None:
    """The task list beside the final retry question, and the attempt and head its answer is bound to."""
    if (lp := asking(c, q)) is None:
        return None
    plan = [t for t in c.plan.tasks if t.origin == "plan"] if c.plan else []
    red, files = _red(c, lp), _files(c)
    tasks = [
        {
            "id": t.id,
            "title": t.title,
            "ticked": t.id in red,
            "shares": [u.id for u in plan if u.id != t.id and files.get(t.id, set()) & files.get(u.id, set())],
        }
        for t in plan
    ]
    return {"attempt": lp.attempt, "head": head(lp), "tasks": tasks}


def refused(
    c: Change, q: Question, option: str | None, tasks: list[str], at: tuple[int | None, str]
) -> tuple[int, str] | None:
    """Why a final retry's answer is refused: a stale page, no ticked task, or a task the plan does not have.

    The host checks it before accepting the answer, and the fold again, so a stale or crafted one settles nothing.
    """
    lp = asking(c, q)
    if option != "rebuild" or lp is None:
        return (422, "only Rebuild names tasks; untick them to accept as done") if tasks else None
    if at != (lp.attempt, head(lp)):
        return 409, "the final review moved on since the page was shown; reload"
    if not tasks:
        return 422, "tick the tasks to rebuild, or accept as done"
    plan = {t.id for t in c.plan.tasks if t.origin == "plan"} if c.plan else set()
    if unknown := sorted(set(tasks) - plan):
        return 422, f"tasks {unknown} are not plan tasks"
    return None


def _red(c: Change, lp: RoundLoop) -> set[str]:
    """Plan tasks with an open finding: one the final loop names, or one of the task's own loop."""
    named = {t for f in lp.findings if kind(lp, f) == "open" for t in f.tasks}
    own = {k for k, x in c.loops.items() if k != FINAL and any(kind(x, f) == "open" for f in x.findings)}
    return named | own


def _files(c: Change) -> dict[str, set[str]]:
    """The files each plan task's reviews covered, its repairs' included: what it changed."""
    tasks = {t.id: t for t in c.plan.tasks} if c.plan else {}
    out: dict[str, set[str]] = {}
    for v in c.reviews:
        if v.task in tasks:
            out.setdefault(subject_of(c, tasks[v.task]), set()).update(v.inputs.paths)
    return out


def undoing(c: Change, lp: RoundLoop) -> tuple[list[Task], str]:
    """The tasks whose commits a rebuild of the ticked tasks undoes, else why they cannot be told apart."""
    picked, named, out = set(lp.rebuild), _named(lp), []
    for t in c.plan.tasks if c.plan else []:
        if t.base is None:
            continue
        root = subject_of(c, t)
        names = named.get(t.id, set()) if root == FINAL else {root}
        if names & picked and not names <= picked:
            return [], f"final repair {t.id} fixed findings of both rebuilt and kept work: its commits cannot be split"
        if not names & picked:
            continue
        if not t.spans or any(s.endswith("..") for s in t.spans):
            return [], f"the commits of task {t.id} are not recorded"
        out.append(t)
    return out, ""


def _named(lp: RoundLoop) -> dict[str, set[str]]:
    """Per final repair of the current plan, the plan tasks its fixed findings name; "" for one that names none."""
    out: dict[str, set[str]] = {}
    for x in (lp, *reversed(lp.history)):
        if x.subject == FINAL and x.ended == "replanned":
            break  # an earlier plan's repairs: their task ids may be the current plan's
        for f in x.findings if x.subject == FINAL else []:
            if f.repair:
                out.setdefault(f.repair, set()).update(f.tasks or [""])
    return out


def fresh(c: Change, task: Task) -> None:
    """A rejected task starts a new attempt of its loop; its repairs retire, and their commits are no one's now."""
    tasks = c.plan.tasks if c.plan else []
    if (lp := c.loops.get(task.id)) is not None:
        old = lp.model_copy(update={"history": [], "ended": "retried", "undo": ""})
        c.loops[task.id] = RoundLoop(
            subject=task.id, attempt=lp.attempt + 1, since=len(tasks), policy=lp.policy, history=[*lp.history, old]
        )
    for t in tasks:
        if t.fixes and subject_of(c, t) == task.id:
            t.done, t.base, t.spans = True, None, []
    task.done, task.base, task.spans, task.built_by, task.earlier = False, None, [], "", ""


def rotated(c: Change, lp: RoundLoop, undone: list[Task], profile: Profile) -> None:
    """After the undo the ticked tasks are built again in plan order, then the final loop goes on (TD-235).

    The last rebuilt task then runs its own and every other plan task's checks on the rebuilt code, each placed in its
    own task's package by that task's planned scope, which no rebuild widens, so a later retry places them the same
    way; its builder fixes what they find before its result is accepted, and that task's rounds review the fix
    (TD-246). The final loop's completion and any merge consent no longer count.
    """
    tasks = c.plan.tasks if c.plan else []
    picked = [t for t in tasks if t.id in lp.rebuild]
    for t in undone:
        t.base, t.spans = None, []
    for t in picked:
        fresh(c, t)
    if picked:
        last, others = picked[-1], [t for t in tasks if t.origin == "plan" and t is not picked[-1] and t.checks]
        last.checks = list(dict.fromkeys([*_placed(profile, [last]), *_placed(profile, others)]))
    lp.ended, lp.rebuild, lp.completion, c.consent = "retried", [], None, None
    if nxt := open_task(c):
        go(c, StepKind.BUILD, nxt.id)
    else:
        go(c, StepKind.REVIEW, mode="final")


def _placed(profile: Profile, tasks: Sequence[Task]) -> list[str]:
    """Each task's checks as `cd <package> && <check>` for every package of its scope the profile runs it in.

    A check the profile runs at the repository root, or in no package of the scope, stays as it is.
    """
    known, out = worktree.checks(profile), []
    for t in tasks:
        for check in t.checks:
            homes = sorted(p for p, k in known if k == check and _holds(p, t.scope))
            out += [f"cd {shlex.quote(p.strip('/'))} && {check}" for p in homes] or [check]
    return out


def _holds(package: str, scope: Sequence[str]) -> bool:
    root = package.strip("/")
    return any(p.strip("/") == root or p.startswith(f"{root}/") for p in scope)
