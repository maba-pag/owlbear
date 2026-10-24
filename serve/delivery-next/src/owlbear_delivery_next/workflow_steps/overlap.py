"""Paths shared between Changes: recorded as information when planning; asked about only on a collision (D7)."""

from __future__ import annotations

import fnmatch
import hashlib
import itertools
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, NamedTuple

from owlbear_delivery_next.change_contracts import evidence
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Overlap, StepKind, Stop
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.change_flow.worktree import GIT, git
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import engine

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change, Plan, Task
    from owlbear_delivery_next.state_store.store import Store

RECENT = timedelta(days=14)  # a merged Change's scope still explains a collision this long
LOCKS = frozenset({"uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"})
LOCKS |= {"Cargo.lock", "go.sum", "Gemfile.lock", "composer.lock"}
DOCS = (".md", ".rst", ".txt")
GENERATED = (".min.js", ".map")
FOLDERS = frozenset({"docs", "dist", "build"})


class Neighbour(NamedTuple):
    """Another open or recently merged Change of this clone."""

    handle: str
    scope: list[str]
    outcome: str
    merged: bool


class _Merge(NamedTuple):
    sides: tuple[str, str]
    pending: bool = False


def neighbours(store: Store, slug: str, now: datetime) -> list[Neighbour]:
    """The other open or recently merged Changes with their plan's task scopes, else their brief's."""
    out = []
    for other in store.slugs():
        try:
            o = store.read(other)
        except StoreError:
            continue
        scope = sorted({p for t in o.plan.tasks for p in t.scope} if o.plan else set(o.brief.scope))
        live = not o.finished_at or now - o.finished_at <= RECENT
        if other != slug and scope and live and not o.intent.abandoned_at:
            out.append(Neighbour(o.handle or other, scope, o.brief.outcome or o.brief.title, bool(o.finished_at)))
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


def _merges(path: Path, since: str | None) -> list[_Merge]:
    """The Change's merge history since its durable base, oldest first, then any unfinished merge."""
    if since and _quiet(path, "merge-base", "--is-ancestor", since, "HEAD", missing=True) is None:
        msg = "The integration start head is not an ancestor of the current work"
        raise ValueError(msg)
    commits = (
        _quiet(
            path,
            "rev-list",
            "--first-parent",
            "--merges",
            "--reverse",
            *([f"{since}..HEAD"] if since else ["--no-walk", "HEAD"]),
        )
        or ""
    )
    found = []
    for commit in commits.splitlines():
        parents = (_quiet(path, "show", "--no-patch", "--format=%P", commit) or "").split()
        if len(parents) != 2:  # noqa: PLR2004 - one target update has exactly two parents
            msg = "Git did not return exactly two integration parents"
            raise ValueError(msg)
        found.append(_Merge((parents[0], parents[1])))
    if theirs := _quiet(path, "rev-parse", "--verify", "--quiet", "MERGE_HEAD", missing=True):
        if not (ours := _quiet(path, "rev-parse", "--verify", "HEAD")):
            msg = "Git did not identify the unfinished integration's start head"
            raise ValueError(msg)
        found.append(_Merge((ours, theirs), pending=True))
    return found


def collided(path: Path, since: str | None, *, resolved: bool) -> list[str]:
    """Paths in every update since the task base; unfinished updates use both sides' changed paths."""
    return sorted({p for merge in _merges(path, since)
                   for p in _collision_paths(path, merge.sides, resolved=resolved and not merge.pending)})  # fmt: skip


def _collision_paths(path: Path, sides: tuple[str, str] | None, *, resolved: bool) -> list[str]:
    if not sides:
        return []
    if resolved:
        tree = [GIT, "merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", *sides]
        run = subprocess.run(tree, cwd=path, capture_output=True, text=True, check=False, timeout=60)  # noqa: S603
        if run.returncode == 0:
            return []
        if run.returncode != 1:
            run.check_returncode()
        paths = list(itertools.takewhile(bool, run.stdout.split("\0")[1:]))
        if not paths:
            msg = "Git reported an integration conflict without identifying its paths"
            raise ValueError(msg)
        return paths
    base = git(path, "merge-base", *sides).strip()
    ours, theirs = ({p for p in git(path, "diff", "--name-only", "-z", base, s).split("\0") if p} for s in sides)
    return sorted(ours & theirs)


def _hits(
    paths: Iterable[str], near: Iterable[Neighbour], patterns: Iterable[str]
) -> list[tuple[Neighbour, list[str]]]:
    paths = list(paths)
    hits = [
        (n, sorted({p for p in paths if not incidental(p, patterns) and any(evidence.within(p, s) for s in n.scope)}))
        for n in near
    ]
    return [(n, ps) for n, ps in hits if ps]


def _cause(c: Change, hits: list[tuple[Neighbour, list[str]]], merge: tuple[str, str] | None) -> str:
    material = [merge, c.brief.outcome, sorted((n.handle, n.outcome, ps) for n, ps in hits)]
    binding = hashlib.sha256(json.dumps(material, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    # Task numbers restart on replanning; the adopted plan version advances even on an owner's replan.
    subject = (
        [f"brief-{c.brief.version}", f"plan-{c.plan.version}", c.step.task]
        if c.step.kind == StepKind.BUILD and c.step.task and c.plan
        else []
    )
    return cause_key(ErrorKind.CONFLICT, c.step.kind, ["collision", binding, *subject, *(n.handle for n, _ in hits)])


def collision(  # noqa: PLR0913 - collision context, path policy and the pending/completed merge proof
    c: Change,
    paths: Iterable[str],
    near: Iterable[Neighbour],
    said: str = "",
    patterns: Iterable[str] = (),
    *,
    merge: tuple[str, str] | None = None,
    pending_paths: Iterable[str] | None = None,
) -> StepResult | None:
    """Ask for a collision once; completing an approved pending merge may narrow its affected paths."""
    near, patterns = list(near), list(patterns)
    hits = _hits(paths, near, patterns)
    if not hits:
        return None
    cause = _cause(c, hits, merge)
    consent = {cause}
    if pending_paths is not None:
        pending = _hits(pending_paths, near, patterns)
        covered = {n.handle: set(ps) for n, ps in pending}
        if all(set(ps) <= covered.get(n.handle, set()) for n, ps in hits):
            consent.add(_cause(c, pending, merge))
    if any(q.cause in consent and q.answer and q.answer.option in {"keep", "adopt"} for q in c.questions):
        return None
    others = ", ".join(n.handle for n, _ in hits)
    wants = " ".join(f"{n.handle} ({'merged' if n.merged else 'open'}) wants: {n.outcome or '?'}." for n, _ in hits)
    on = "; ".join(f"{n.handle} on {', '.join(ps[:5])}" for n, ps in hits)
    text = f"Updating with the target collided with {on}. This Change wants: {c.brief.outcome or '?'}. {wants}"
    text += f" The Builder said: {said}" if said else ""
    options = [
        Option(id="keep", label="Keep this Change's behaviour", next=c.step.kind),
        Option(id="adopt", label=f"Adopt {others}'s behaviour", next=c.step.kind),
        Option(id="pause", label="Pause this Change", next="pause"),
    ]
    return engine.ask(c.step.kind, text, cause, options)


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


def integrated(store: Store, c: Change, path: Path, session: tuple[str | None, str], result: StepResult) -> StepResult:
    """An integration's result, or the collision question when it touched another Change's scope.

    *session* is the durable integration base and how the session ended. A resolved update collides on the paths the
    Builder resolved; one the Builder could not finish (it asked or reported a wrong premise, e.g. failing
    checks) collides on the paths both sides changed.
    """
    start, ending = session
    resolved = result.exit == Exit.DONE
    if result.exit == Exit.STOP or not integrates(c) or not (resolved or ending in {"ask", "premise"}):
        return result
    if start is None:
        return _unverified("The integration start head is missing, so collisions cannot be checked")
    said = "" if resolved else result.reason or (result.question.text if result.question else "")
    near = neighbours(store, c.slug, datetime.now(UTC))
    try:
        merges = _merges(path, start)
        if resolved and any(m.pending for m in merges):
            return _unverified("The integration reported completion while a merge is still unfinished")
        patterns = generated(path)
        for merge in merges:
            paths = _collision_paths(path, merge.sides, resolved=resolved)
            pending = _collision_paths(path, merge.sides, resolved=False) if resolved and paths else None
            hit = collision(c, paths, near, said, patterns, merge=merge.sides, pending_paths=pending)
            if hit:
                return hit
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return _unverified(f"Integration collisions could not be checked: {exc}"[:300])
    return result
