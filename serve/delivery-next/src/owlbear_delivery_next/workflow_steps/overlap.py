"""Paths shared between Changes are recorded as information when planning; a merge asks only about behaviour (D7)."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import evidence
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Overlap, Question, StepKind, Stop
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.change_flow.worktree import GIT, failure
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change, Plan, Task
    from owlbear_delivery_next.change_contracts.tools import MergeReport
    from owlbear_delivery_next.state_store.store import Lock, Store

LOCKS = frozenset({"uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"})
LOCKS |= {"Cargo.lock", "go.sum", "Gemfile.lock", "composer.lock"}
DOCS = (".md", ".rst", ".txt")
GENERATED = (".min.js", ".map")
FOLDERS = frozenset({"docs", "dist", "build"})


def scopes(store: Store, slug: str) -> dict[str, list[str]]:
    """Scopes of the other open Changes of this clone: their plan's task scopes, else their brief's."""
    out = {}
    for other in store.slugs():
        try:
            o = store.read(other)
        except StoreError:
            continue
        scope = sorted({p for t in o.plan.tasks for p in t.scope} if o.plan else set(o.brief.scope))
        if other != slug and scope and not o.finished_at and not o.intent.abandoned_at:
            out[o.handle or other] = scope
    return out


def generated(repo: Path) -> list[str]:
    """The ``linguist-generated`` patterns of the repository's root ``.gitattributes``."""
    try:
        lines = (repo / ".gitattributes").read_text(encoding="utf-8").splitlines()
    except OSError, UnicodeDecodeError:
        return []
    marked = {"linguist-generated", "linguist-generated=true"}
    return [w[0] for line in lines if (w := line.split()) and not w[0].startswith("#") and marked & set(w[1:])]


def incidental(path: str, patterns: Iterable[str] = ()) -> bool:
    """Docs, lockfiles and generated output: sharing them is no overlap."""
    p = PurePosixPath(path)
    if p.name in LOCKS or p.suffix in DOCS or path.endswith(GENERATED) or FOLDERS & set(p.parts):
        return True
    return any(fnmatch.fnmatch(path, g.lstrip("/")) or ("/" not in g and fnmatch.fnmatch(p.name, g)) for g in patterns)


def _deeper(a: str, b: str) -> str:
    return max(a, b, key=lambda x: len(PurePosixPath(x).parts))


def found(plan: Plan, others: Mapping[str, Iterable[str]], patterns: Iterable[str] = ()) -> list[Overlap]:
    """Each other Change whose scope shares a path or directory with the plan's task scopes, incidental paths aside."""
    mine, patterns = [p for t in plan.tasks for p in t.scope], list(patterns)
    out = []
    for handle, scope in sorted(others.items()):
        shared = {_deeper(p, m) for p in scope for m in mine if evidence.within(p, m)}
        if paths := sorted(p for p in shared if not incidental(p, patterns)):
            out.append(Overlap(other=handle, paths=paths))
    return out


def record(c: Change, result: StepResult, others: Mapping[str, Iterable[str]], repo: Path) -> None:
    """Record the overlaps of the plan the step keeps: shown, never asked about (D7).

    A plan its challenge sent back is kept too, so the owner's "accept as it is" finds its overlaps recorded.
    """
    if result.plan and result.exit in {Exit.DONE, Exit.RETRY}:
        c.overlaps = found(result.plan, others, generated(repo))


def _quiet(path: Path, *args: str, missing: bool = False) -> str | None:
    run = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [GIT, *args], cwd=path, capture_output=True, text=True, check=False, timeout=60
    )
    if run.returncode == 0:
        return run.stdout.strip()
    if missing and run.returncode == 1:
        return None
    run.check_returncode()
    return None


def _merges(path: Path, since: str) -> list[tuple[str, str]]:
    """Both parents of each merge on the Change's branch since the integration's durable base, oldest first."""
    if _quiet(path, "merge-base", "--is-ancestor", since, "HEAD", missing=True) is None:
        msg = "The integration start head is not an ancestor of the current work"
        raise ValueError(msg)
    listed = _quiet(path, "log", "--first-parent", "--merges", "--reverse", "--format=%P", f"{since}..HEAD") or ""
    found = []
    for line in listed.splitlines():
        parents = line.split()
        if len(parents) != 2:  # noqa: PLR2004 - one target update has exactly two parents
            msg = "Git did not return exactly two integration parents"
            raise ValueError(msg)
        found.append((parents[0], parents[1]))
    return found


def _cause(c: Change, sides: list[tuple[str, str]], told: tuple[str, str] | None = None) -> str:
    """The collision's cause: its merges and task, and with *told* the reported behaviours a consent holds for."""
    material = [sides, c.brief.outcome, told]
    binding = hashlib.sha256(json.dumps(material, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    # Task numbers restart on replanning; the adopted plan version advances even on an owner's replan.
    subject = (
        [f"brief-{c.brief.version}", f"plan-{c.plan.version}", c.step.task]
        if c.step.kind == StepKind.BUILD and c.step.task and c.plan
        else []
    )
    return cause_key(ErrorKind.CONFLICT, c.step.kind, ["collision", binding, *subject])


def collision(c: Change, told: MergeReport, sides: list[tuple[str, str]]) -> StepResult | None:
    """Ask which behaviour to keep when the builder reports one that only one side can have (#1189).

    The owner's answer holds for exactly the reported behaviours of these merges in this task; a report in other
    words is asked again, and counts as the same cause for the limit of two (``follows``).
    """
    if not told.this:
        return None
    cause = _cause(c, sides, (told.this, told.other))
    if any(q.cause == cause and q.answer and q.answer.option in {"keep", "adopt"} for q in c.questions):
        return None
    text = (
        "This Change and the work merged into it need the product to behave differently in one situation. "
        "Keep this Change's behaviour there?"
    )
    options = [  # each label carries its behaviour whole: the answer's label is what the next builder is told
        Option(id="keep", label=f"Yes: {told.this}", next=c.step.kind),
        Option(id="adopt", label=f"No, the merged-in work's: {told.other}", next=c.step.kind),
        Option(id="pause", label="Pause this Change", next="pause"),
    ]
    q = Question(step=c.step.kind, text=text, cause=cause, options=options, subject="product", follows=_cause(c, sides))
    return StepResult(exit=Exit.ASK, reason=text, cause=cause, question=q)


def integrates(c: Change) -> bool:
    """Recognize the supported integration BUILD as well as the legacy INTEGRATE step."""
    if c.step.kind == StepKind.INTEGRATE:
        return True
    tasks = c.plan.tasks if c.plan and c.step.kind == StepKind.BUILD else []
    return any(task.id == c.step.task and task.origin == "integration" for task in tasks)


def _unverified(reason: str) -> StepResult:
    stop = Stop(
        kind=ErrorKind.STATE, reason=reason, action="Restore Git access or redo the integration task",
        resume="The integration collision check completes", at=datetime.now(UTC),
    )  # fmt: skip
    return StepResult(exit=Exit.STOP, reason=reason, stop=stop)


def starting(c: Change, task: Task | None) -> StepResult | None:
    """Refuse a resumed integration with no durable base instead of inventing a base from its current HEAD."""
    resumed = (
        c.step.session is not None
        or c.step.started_at is not None
        or bool(task and (task.spans or task.built_by or task.done))
    )
    if c.step.kind == StepKind.BUILD and task and task.origin == "integration" and task.base is None and resumed:
        return _unverified("The resumed integration start head is missing, so collisions cannot be checked")
    return None


def integrated(  # noqa: PLR0913, PLR0917 - the runner's writer and lock, the Change, its worktree and session
    store: Store, lock: Lock, c: Change, path: Path, start: str | None, result: StepResult, payload: object = None
) -> StepResult:
    """A finished integration's result, or the question when its builder reports a behaviour only one side can have.

    *start* is the durable integration base. An integration that asked or stepped back passes through: it reaches
    this gate when it completes.
    """
    if result.exit != Exit.DONE or not integrates(c):
        return result
    if start is None:
        return _unverified("The integration start head is missing, so collisions cannot be checked")
    try:
        pending = _quiet(path, "rev-parse", "--verify", "--quiet", "MERGE_HEAD", missing=True)
        sides = _merges(path, start)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        reason = f"Integration collisions could not be checked: {failure(exc)}"
        store.log(
            lock, c.slug, {"event": "collisions-unchecked", "at": datetime.now(UTC).isoformat(), "reason": reason}
        )
        return _unverified(reason)
    if pending:
        return _unverified("The integration reported completion while a merge is still unfinished")
    if (told := getattr(payload, "merge", None)) is None:
        return _unverified("The integration result does not say what the merge did to behaviour")
    return collision(c, told, sides) or result
