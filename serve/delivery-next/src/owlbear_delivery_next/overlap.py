"""Paths shared between Changes: recorded as information when planning; asked about only on a collision (D7)."""

from __future__ import annotations

import fnmatch
import itertools
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, NamedTuple

from owlbear_delivery_next import evidence
from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.models import ErrorKind, Exit, Option, Overlap, StepKind
from owlbear_delivery_next.steps import engine
from owlbear_delivery_next.steps.worktree import GIT, git
from owlbear_delivery_next.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change, Plan
    from owlbear_delivery_next.store import Store

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


def _quiet(path: Path, *args: str) -> str | None:
    run = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [GIT, *args], cwd=path, capture_output=True, text=True, check=False, timeout=60
    )
    return run.stdout.strip() if run.returncode == 0 else None


def _sides(path: Path, since: str | None) -> tuple[str, str] | None:
    """Both sides of the unfinished update, else of the latest merge commit since *since* (or of HEAD)."""
    if theirs := _quiet(path, "rev-parse", "--verify", "--quiet", "MERGE_HEAD"):
        return "HEAD", theirs
    merge = _quiet(
        path, "rev-list", "--merges", "--max-count=1", *([f"{since}..HEAD"] if since else ["--no-walk", "HEAD"])
    )
    parents = _quiet(path, "rev-parse", f"{merge}^1", f"{merge}^2") if merge else None
    return tuple(parents.split()) if parents else None  # type: ignore[return-value]


def collided(path: Path, since: str | None, *, resolved: bool) -> list[str]:
    """Paths the Builder resolved in the update's merge; while it cannot finish, paths both sides changed."""
    sides = _sides(path, since)
    if not sides:
        return []
    if resolved:
        tree = [GIT, "merge-tree", "--write-tree", "--name-only", "--no-messages", *sides]
        run = subprocess.run(tree, cwd=path, capture_output=True, text=True, check=False, timeout=60)  # noqa: S603
        return list(itertools.takewhile(bool, run.stdout.splitlines()[1:])) if run.returncode == 1 else []
    base = git(path, "merge-base", *sides).strip()
    ours, theirs = ({p for p in git(path, "diff", "--name-only", base, s).splitlines() if p} for s in sides)
    return sorted(ours & theirs)


def collision(
    c: Change, paths: Iterable[str], near: Iterable[Neighbour], said: str = "", patterns: Iterable[str] = ()
) -> StepResult | None:
    """Ask which behaviour to keep when an update collided on paths of another Change's scope; once per collision."""
    patterns = list(patterns)
    hits = [
        (n, sorted({p for p in paths if not incidental(p, patterns) and any(evidence.within(p, s) for s in n.scope)}))
        for n in near
    ]
    hits = [(n, ps) for n, ps in hits if ps]
    cause = cause_key(ErrorKind.CONFLICT, StepKind.INTEGRATE, ["collision", *(n.handle for n, _ in hits)])
    if not hits or any(q.cause == cause and q.answer for q in c.questions):
        return None
    others = ", ".join(n.handle for n, _ in hits)
    wants = " ".join(f"{n.handle} ({'merged' if n.merged else 'open'}) wants: {n.outcome or '?'}." for n, _ in hits)
    on = "; ".join(f"{n.handle} on {', '.join(ps[:5])}" for n, ps in hits)
    text = f"Updating with the target collided with {on}. This Change wants: {c.brief.outcome or '?'}. {wants}"
    text += f" The Builder said: {said}" if said else ""
    options = [
        Option(id="keep", label="Keep this Change's behaviour", next=StepKind.INTEGRATE),
        Option(id="adopt", label=f"Adopt {others}'s behaviour", next=StepKind.INTEGRATE),
        Option(id="pause", label="Pause this Change", next="pause"),
    ]
    return engine.ask(StepKind.INTEGRATE, text, cause, options)


def integrated(store: Store, c: Change, path: Path, session: tuple[str | None, str], result: StepResult) -> StepResult:
    """An integration's result, or the collision question when it touched another Change's scope.

    *session* is the head before the session and how it ended. A resolved update collides on the paths the
    Builder resolved; one the Builder could not finish (it asked or reported a wrong premise, e.g. failing
    checks) collides on the paths both sides changed.
    """
    start, ending = session
    resolved = result.exit == Exit.DONE
    if c.step.kind != StepKind.INTEGRATE or not (resolved or ending in {"ask", "premise"}):
        return result
    said = "" if resolved else result.reason or (result.question.text if result.question else "")
    near = neighbours(store, c.slug, datetime.now(UTC))
    hit = collision(c, collided(path, start, resolved=resolved), near, said, generated(path))
    return hit or result
