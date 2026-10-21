"""The impact of a change of mind with built effect (TD-428; decision system §9, slice 5b part 2).

For a decision that replaced another, or was withdrawn, each project the old rule reached is `confirmed` (merge
history shows work built under it: a merged finished-Change record whose brief made it or whose baseline applied it,
or a Change in the project's store whose baseline applied it), `unaffected` (its path selectors match no file in the
working tree, at `HEAD` or at the freshly fetched remote default branch, and every merged record rules it out) or
`unknown`, with why. Records alone miss chat-built code, so a rule without path selectors stays unknown, and so does a
project whose remote cannot be confirmed or whose history holds records that cannot rule it out (older ones without
`decisions_applied`, or unreadable ones). A Global rule reaches every project the host knows and OwlBear's own folder;
a project whose repository the host cannot read stays unknown. Nothing here writes, apart from the bounded fetch
updating the project checkout's remote-tracking branches.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Literal

from owlbear_decisions import LinkType, Scope, State
from owlbear_decisions.applies import overlap
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.state_store import decision_actions, decision_store
from owlbear_delivery_next.state_store.decision_actions import EFFECT, EFFECTS, Refused
from owlbear_delivery_next.state_store.decision_archive import CHANGES
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from owlbear_decisions import Decision
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store

type Status = Literal["confirmed", "unaffected", "unknown"]
OWLBEAR = "owlbear"  # OwlBear's own folder in owlbear-data (TD-435)
SHOWN = 50  # evidence paths listed per project; the rest are counted
GIT_SECONDS = 20
FETCH_SECONDS = 10
REMOTE = "could not confirm against the remote"
WHOLE = "a whole-project rule: code and tests cannot tell"
ACCEPTED = "the Decisions page: existing code accepted"  # the source of the owner's grandfathering decision
DIVERGENCE = {
    "forbids": "The new rule forbids existing behaviour: affected work, publication and merge pause until compliance "
    "is settled (a running Change it applies to stops at its next step and asks); keeping existing code is the "
    "owner's choice per project.",
    "unknown": "Not said whether the new rule forbids existing behaviour, so it is treated as forbidding it: affected "
    "work pauses until compliance is settled.",
    "wording": "Wording only: existing behaviour stays compliant, so no fixes are scheduled.",
    "withdrawn": "Withdrawn without a successor: no rule replaces it, so existing code needs no fix for it.",
}


class Unreadable(Exception):  # noqa: N818 - says what happened
    """The project's repository cannot be listed."""


@dataclass(frozen=True)
class Place:
    """A project the host knows: its data folder, its repository and store when it can read them, else why not."""

    name: str
    repo: Path | None = None
    store: Store | None = None
    why: str = ""


@dataclass(frozen=True)
class Impact:
    """One project's verdict, the Changes, files and incomplete records behind it, and the owner's acceptance."""

    project: str
    status: Status
    why: str
    changes: tuple[dict[str, str], ...] = ()
    paths: tuple[str, ...] = ()
    accepted: str = ""  # the id of the decision keeping its existing code
    incomplete: tuple[str, ...] = ()  # the finished-Change records that cannot rule the old rule out


@dataclass(frozen=True)
class Report:
    """The old rule, the new one (None: withdrawn), the owner's mark on the change and each project's impact."""

    old: Decision
    new: Decision | None
    effect: str  # forbids, wording, unknown or withdrawn
    projects: tuple[Impact, ...]


def _listed(record: dict[str, Any]) -> list[Any] | None:
    listed = record.get("decisions_applied")
    if not isinstance(listed, list | None):
        raise TypeError(listed)
    return listed


def pinning(store: Store, decision_id: str) -> list[dict[str, Any]]:
    """The Changes of *store* whose decision baseline pins *decision_id*, and whether it applied to them."""
    found = []
    for slug in store.slugs():
        try:
            c = store.read(slug)
        except StoreError:
            continue
        pin = c.decisions_baseline
        if pin and decision_id in pin.revisions:
            found.append({
                "slug": slug, "handle": c.handle, "title": c.brief.title, "step": str(c.step.kind),
                "applies": decision_id in pin.said, "revision": pin.revisions[decision_id],
            })  # fmt: skip
    return found


def built(root: Path, project: str, old: Decision) -> tuple[list[dict[str, str]], list[str]]:
    """The merged records of *project* that made or applied *old*, and the records that cannot rule it out.

    Those are unreadable records and merged ones that do not list the decisions they applied (older Changes).
    """
    found, incomplete = [], []
    for path in sorted((root / project / CHANGES).glob("*.json")):
        try:
            record = json.loads(path.read_text())
            brief = record.get("brief") or {}
            listed = _listed(record)
            made = {d.get("id") for d in brief.get("decisions", [])} | set(listed or [])
            merged, pr = record.get("outcome") == "merged", (record.get("pr") or {}).get("url") or ""
            slug, title = str(record.get("slug", path.stem)), str(brief.get("title", ""))
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            incomplete.append(f"{path.name}: cannot be read ({type(exc).__name__})")
            continue
        if merged and (old.id in made or path.stem == old.change):
            found.append({"slug": slug, "title": title, "pr": str(pr), "from": "merged"})
        elif merged and listed is None:
            incomplete.append(f"{path.name}: merged, but records no decisions it applied")
    return found, incomplete


def applied(store: Store | None, decision_id: str) -> list[dict[str, str]]:
    """The Changes in *store* whose baseline applied the decision: built, or being built, under it."""
    if store is None:
        return []
    return [
        {"slug": c["slug"], "title": c["title"], "pr": "", "from": f"pinned, at {c['step']}"}
        for c in pinning(store, decision_id)
        if c["applies"]
    ]


def _git(git: str, repo: Path, *args: str, seconds: float = GIT_SECONDS) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [git, "-C", str(repo), *args], capture_output=True, text=True, timeout=seconds, check=False,
        stdin=subprocess.DEVNULL, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )  # fmt: skip


def _names(listed: subprocess.CompletedProcess[str], repo: Path) -> list[str]:
    if listed.returncode:
        msg = f"git cannot list the files of {repo}: {' '.join(listed.stderr.split())[:200]}"
        raise Unreadable(msg)
    return [p for p in listed.stdout.split("\0") if p]


def _remote_head(git: str, repo: Path) -> str:
    """The remote default branch's commit after a bounded fetch; nothing when it cannot be resolved."""
    quiet = ("-c", "gc.auto=0", "-c", "maintenance.auto=false")
    fetched = _git(git, repo, *quiet, "fetch", "-q", "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules",
                   "origin", seconds=FETCH_SECONDS)  # fmt: skip
    if fetched.returncode:
        return ""
    branch = "HEAD"
    if _git(git, repo, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/HEAD").returncode:
        said = _git(git, repo, "ls-remote", "--symref", "origin", "HEAD", seconds=FETCH_SECONDS).stdout.split()
        if len(said) < 2 or said[0] != "ref:" or not said[1].startswith("refs/heads/"):  # noqa: PLR2004 - ref: NAME
            return ""
        branch = said[1].removeprefix("refs/heads/")
    head = _git(git, repo, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}^{{commit}}")
    return "" if head.returncode else head.stdout.strip()


def tracked(repo: Path) -> tuple[list[str], str]:
    """The files of the working tree (untracked ones too), `HEAD` and the remote default branch, and a doubt.

    The remote is fetched first, bounded; the doubt says why it could not be confirmed, else it is empty.
    """
    try:
        git = resolve_git_executable()
        files = _names(_git(git, repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard"), repo)
        files += _names(_git(git, repo, "ls-tree", "-r", "-z", "--name-only", "HEAD"), repo)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        msg = f"its repository {repo} cannot be read: {exc}"
        raise Unreadable(msg) from exc
    try:
        remote = _remote_head(git, repo)
        files += _names(_git(git, repo, "ls-tree", "-r", "-z", "--name-only", remote), repo) if remote else []
    except OSError, subprocess.TimeoutExpired, Unreadable:
        remote = ""
    doubt = "" if remote else f"{REMOTE}: its default branch could not be fetched and resolved"
    return sorted(set(files)), doubt


def classify(
    old: Decision, changes: Sequence[dict[str, str]], files: Iterable[str], unreadable: str = "", doubt: str = ""
) -> tuple[Status, str, tuple[str, ...]]:
    """One project's verdict on *old*, why, and the files its path selectors match.

    A *doubt* (an unconfirmed remote, records that cannot rule it out) keeps it from `unaffected`.
    """
    globs = old.applies_to.paths
    paths = tuple(f for f in files if any(overlap(g, f) for g in globs)) if globs else ()
    if unreadable:
        return "unknown", unreadable, paths
    if changes:
        return "confirmed", f"{len(changes)} Change(s) built or are building work under the old rule", paths
    if not globs:
        return "unknown", WHOLE, paths
    if paths:
        return "unknown", f"{len(paths)} files match its paths: whether they follow it needs a look", paths
    if doubt:
        return "unknown", doubt, paths
    return "unaffected", "no file matches its paths here, at HEAD or on the remote, and no Change applied it", paths


def _impact(root: Path, place: Place, old: Decision, accepted: dict[str, str]) -> Impact:
    merged, incomplete = built(root, place.name, old)
    changes = [*merged, *applied(place.store, old.id)]
    files: list[str] = []
    unreadable = place.why or ("" if place.repo else f"{place.name}'s repository is not served by this host")
    doubt = f"{len(incomplete)} finished-Change record(s) cannot rule out that it was applied" if incomplete else ""
    if not unreadable and place.repo and old.applies_to.paths:
        try:
            files, remote = tracked(place.repo)
            doubt = "; ".join(filter(None, (doubt, remote)))
        except Unreadable as exc:
            unreadable = str(exc)
    status, why, paths = classify(old, changes, files, unreadable, doubt)
    return Impact(place.name, status, why, tuple(changes), paths, accepted.get(place.name, ""), tuple(incomplete))


def _reached(root: Path, old: Decision, places: Sequence[Place]) -> list[Place]:
    """The projects *old* reached: its own, or for a Global rule every known one and OwlBear's folder."""
    by_name = {p.name: p for p in places if p.name}
    if old.scope is Scope.GLOBAL:
        names = [*by_name, *([OWLBEAR] if (root / OWLBEAR).is_dir() and OWLBEAR not in by_name else [])]
    else:
        names = [old.project]
    absent = "is not a project this host serves"
    return [by_name.get(n) or Place(n, why=f"{'OwlBear' if n == OWLBEAR else n}'s repository {absent}") for n in names]


def effect(new: Decision | None) -> str:
    """The owner's mark on the replacement in its rationale: forbids, wording or unknown; withdrawn without one."""
    if new is None:
        return "withdrawn"
    marks = [p.removeprefix(EFFECT) for p in new.rationale.split("\n\n") if p.startswith(EFFECT)]
    named = {said: key for key, said in EFFECTS.items()}
    return named.get(marks[-1], "unknown") if marks else "unknown"


def _accepted(decisions: Iterable[Decision], new: Decision | None) -> dict[str, str]:
    """The projects whose existing code the owner kept under *new*, with the decision recording it."""
    if new is None:
        return {}
    return {
        d.project: d.id
        for d in decisions
        if d.source == ACCEPTED and d.state is State.IN_FORCE and any(link.target == new.id for link in d.links)
    }


def report(shared: DataRepo | None, folder: str, decision_id: str, places: Sequence[Place]) -> Report:
    """The impact of *decision_id* (in *folder*'s view): the rule it replaced, or itself when withdrawn."""
    view = decision_store.load(shared, folder)
    if shared is None or (entry := view.snapshot.get(decision_id)) is None:
        msg = f"there is no decision {decision_id} in this view"
        raise Refused(msg, 404)
    chosen, every = entry.decision, decision_actions.every(shared)
    target = next((link.target for link in chosen.links if link.type is LinkType.REPLACES), "")
    if target:
        old, new = every.get(target), chosen
        if old is None:
            msg = f"{target}, which {chosen.id} replaces, cannot be found"
            raise Refused(msg, 404)
    elif chosen.state is State.WITHDRAWN:
        old, new = chosen, None
    else:
        msg = f"{chosen.id} replaced no decision and is not withdrawn: it has no impact report"
        raise Refused(msg, 422)
    accepted = _accepted(every.values(), new)
    found = tuple(_impact(shared.root, p, old, accepted) for p in _reached(shared.root, old, places))
    return Report(old, new, effect(new), found)


def due(report: Report) -> list[Impact]:
    """The projects whose code may still follow the old rule: confirmed or unknown, and not kept by the owner."""
    if report.new is None or report.effect == "wording":
        return []
    return [i for i in report.projects if i.status != "unaffected" and not i.accepted]


def is_test(path: str) -> bool:
    """A test file: under a ``tests`` folder, or named ``test_*``."""
    parts = PurePosixPath(path).parts
    return "tests" in parts[:-1] or parts[-1].startswith("test_")


def _rule(d: Decision) -> dict[str, Any]:
    out = d.model_dump(mode="json", include={"id", "title", "statement", "scope", "project", "state", "origin"})
    return out | {"revision": d.revision, "paths": list(d.applies_to.paths)}


def _project(i: Impact) -> dict[str, Any]:
    tests = [p for p in i.paths if is_test(p)]
    return {
        "project": i.project, "status": i.status, "why": i.why, "changes": list(i.changes), "accepted": i.accepted,
        "paths": list(i.paths[:SHOWN]), "more": max(0, len(i.paths) - SHOWN),
        "tests": tests[:SHOWN], "more_tests": max(0, len(tests) - SHOWN),
        "incomplete": list(i.incomplete[:SHOWN]), "more_incomplete": max(0, len(i.incomplete) - SHOWN),
    }  # fmt: skip


def shown(report: Report) -> dict[str, Any]:
    """The report as the page shows it, evidence paths capped."""
    return {
        "old": _rule(report.old), "new": _rule(report.new) if report.new else None, "effect": report.effect,
        "divergence": DIVERGENCE[report.effect], "projects": [_project(i) for i in report.projects],
        "fixes": bool(due(report)) and report.new is not None and report.new.state is State.IN_FORCE,
    }  # fmt: skip
