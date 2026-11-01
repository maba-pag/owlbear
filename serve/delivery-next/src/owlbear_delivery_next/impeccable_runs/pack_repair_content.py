"""An agent's CI repair of the Impeccable pull request: the pack's protected content it changes (``pack_repair``).

The detector's glue, the pins, the golden pages and the pinned skills are protected. A repair that changes them is
checked again as the update was (``pack_activation``): its whole protected content is read from its commit, never from
what an earlier repair left in the candidate, laid into the updater's folder, and compared with what was checked. The
blobs it changed are kept for the owner's approval before the merge. A ``Kind`` says what a kind of update protects and
refuses; a PDS update's is ``pds_runs.repair``'s.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.impeccable import pack_files, pack_git
from owlbear_delivery_next.impeccable_runs import pack_gates, pack_updater
from owlbear_delivery_next.impeccable_runs.pack_candidate import MANIFEST, NOTICE
from owlbear_delivery_next.impeccable_runs.pack_state import RUNS

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.impeccable_runs.pack_candidate import Candidate
    from owlbear_delivery_next.impeccable_runs.pack_job import Job
    from owlbear_delivery_next.impeccable_runs.pack_repair import Repair
    from owlbear_delivery_next.impeccable_runs.pack_run import Context
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run

REGULAR = frozenset({"100644", "100755"})
CHECKS = (
    "The folder is a copy of the whole repository at the pull request's head. Change what makes the failed checks "
    "fail, and only that. Never weaken a check: do not skip, xfail or delete a test, loosen an assertion, lower a "
    "threshold or add a suppression (`noqa`, `type: ignore`, `biome-ignore`, `pragma: no cover` and the like). Do not "
    "change lint, format, CI workflow, hook or security configuration (`.github/`, `pyproject.toml`, `biome.json`, "
    "`.pre-commit-config.yaml`, `conftest.py` and the like): if the fix needs that, change nothing and say so in your "
    "summary."
)
PUSH = "You cannot run commands or push: Delivery commits and pushes what you changed, and CI runs again."


@dataclass(frozen=True)
class Kind:
    """What a kind of update's CI repair checks again or never pushes, how its session runs, and its words."""

    rules: str  # the session's rules, after the CI stop
    label: str  # the role whose settings its session takes
    content: str  # what its protected paths are, in the owner's words
    changes: str  # the words before the protected paths a repair changes
    refusal: str  # why a refused path is never pushed
    protected: Callable[[str, str], bool]  # (package, path): checked again before the push, approved before the merge
    refused: Callable[[str, str, bool, list[str]], bool]  # (package, path, kept, pinned skills): only an update may
    recheck: str  # the run's next action while a repair is checked
    publish: str  # its next action otherwise
    run: Callable[[Any, Session], Run]  # (job, session): the session's runner
    job: str = ""  # the session's job, when it needs other skills than its role's
    skills: Callable[[Path], Path | None] = lambda _at: None  # the skills folder in the copy, for its knowledge
    pinned: Callable[[Any], list[str]] = lambda _ctx: []  # (context): the skills its run pinned, for ``refused``


def _refused(package: str, path: str, kept: bool, skills: list[str]) -> bool:  # noqa: FBT001 - Kind.refused's shape
    return protected(package, path) and not pack_gates.allowed(updater_path(package, path), kept, skills)


def package_at(job: Job, src: pack_git.Source) -> str:
    """The package's path in the checkout *src*."""
    return job.live.package.resolve().relative_to(src.root.resolve()).as_posix()


def protected(package: str, path: str) -> bool:
    """Whether the repository *path* is the pack's protected content: the detector's glue, pins, golden or skills."""
    files = {f"{package}/{p}" for p in (*pack_gates.GLUE.values(), "impeccable.json")}
    return path in files or path.startswith((f"{package}/golden/", f"{package}/skills/"))


def updater_path(package: str, path: str) -> str:
    """The updater's path of the repository *path* in the package (``pack_gates``), or empty when it has none."""
    if not path.startswith(f"{package}/"):
        return ""
    inner = path.removeprefix(f"{package}/")
    glue = {theirs: ours for ours, theirs in pack_gates.GLUE.items()}
    return glue.get(inner, inner if inner.startswith(("golden/", "skills/")) else "")


def snapshot(job: Job, ctx: Context, c: Candidate) -> dict[str, bytes]:
    """The committed repair's whole protected content, by updater path: its golden pages, glue and pinned skills.

    Read from the commit itself, never from what an earlier repair left in the candidate.

    Raises:
        pack_files.PackError: Git could not read it, a file is missing or no regular file, or its pins or notice are
            not the run's.
    """
    r, pub, run = ctx.repair, ctx.publication, job.live.git
    assert pub is not None  # noqa: S101 - a repair follows publication
    src = pack_git.Source(Path(pub.root), pub.repository, pub.base)
    package = package_at(job, src)
    wanted = {f"{package}/{theirs}": ours for ours, theirs in pack_gates.GLUE.items()}
    wanted |= {f"{package}/skills/{n}/SKILL.md": f"skills/{n}/SKILL.md" for n in c.pins["skills"]}
    for entry in filter(None, run(src.root, ["ls-tree", "-z", r.commit, "--", f"{package}/golden/"]).split("\0")):
        meta, path = entry.split("\t", 1)
        mode, kind, _ = meta.split()
        if kind == "blob" and mode not in REGULAR:
            msg = f"{path} in the repair {r.commit[:12]} is no regular file"
            raise pack_files.PackError(msg)
        if kind == "blob":
            wanted[path] = f"golden/{PurePosixPath(path).name}"
    pins = {f"{package}/{MANIFEST}": c.manifest, f"{package}/{NOTICE}": c.notice}
    at = job.store.root / RUNS / f"{job.state['run']}-ci-repair"
    shutil.rmtree(at, ignore_errors=True)
    quiet(run, src.root, ["worktree", "prune"])
    at.parent.mkdir(parents=True, exist_ok=True)
    run(src.root, ["worktree", "add", "--quiet", "--detach", "--no-checkout", str(at), r.commit])
    try:  # the bytes as committed, never git's text output; a missing path fails the checkout
        run(at, ["checkout", r.commit, "--", *sorted(wanted), *sorted(pins)])
        moved = [p for p, text in pins.items() if (at / p).read_bytes() != text.encode("utf-8")]
        if moved:
            msg = f"the repair {r.commit[:12]} holds pins or a notice the run did not make: {', '.join(moved)}"
            raise pack_files.PackError(msg)
        return {ours: (at / p).read_bytes() for p, ours in wanted.items()}
    finally:
        quiet(run, src.root, ["worktree", "remove", "--force", str(at)])
        shutil.rmtree(at, ignore_errors=True)


def lay(at: Path, snap: dict[str, bytes]) -> None:
    """Make the updater's folder hold exactly *snap*'s golden pages, glue and skills, whatever it held before."""
    golden = at / pack_gates.GOLDEN
    if golden.is_symlink():
        golden.unlink()
    shutil.rmtree(golden, ignore_errors=True)
    for path, data in snap.items():
        (at / path).unlink(missing_ok=True)  # a link at the file is replaced, never written through
        (at / path).parent.mkdir(parents=True, exist_ok=True)
        (at / path).write_bytes(data)


def unlike(at: Path, c: Candidate, snap: dict[str, bytes]) -> list[str]:
    """The protected paths whose bytes in the updater's folder or the candidate are not *snap*'s; empty when alike."""
    golden = {f"{pack_gates.GOLDEN}{p.name}" for p in (at / pack_gates.GOLDEN).glob("*") if p.is_file()}
    differ = sorted(golden ^ {p for p in snap if p.startswith(pack_gates.GOLDEN)})
    for path, data in snap.items():
        here = at / path
        if here.is_symlink() or not here.is_file() or here.read_bytes() != data:
            differ.append(path)
    for name in c.pins["skills"]:
        if pack_updater.skill(c, name).read_bytes() != snap[f"skills/{name}/SKILL.md"]:
            differ.append(f"the candidate's {name}")
    return sorted(set(differ))


def guarded(
    run: pack_git.Git, src: pack_git.Source, r: Repair, package: str, rule: Callable[[str, str], bool] = protected
) -> tuple[dict[str, str], str, bool]:
    """The protected paths the repair changes with their blobs in its commit, their diff, and whether it is binary."""
    picked = [p for p in r.paths if rule(package, p)]
    if not picked:
        return {}, "", False
    listed = run(src.root, ["ls-tree", r.commit, "--", *picked]).splitlines()
    blobs = dict.fromkeys(picked, "deleted") | {line.split("\t", 1)[1]: line.split()[2] for line in listed}
    changed = [f"{r.commit}~1", r.commit, "--", *picked]
    return blobs, run(src.root, ["diff", *changed]), binary(run, src.root, changed)


def binary(run: pack_git.Git, cwd: Path, changed: list[str]) -> bool:
    """Whether the diff of *changed* (git diff's arguments) holds a binary change, which Git does not render."""
    return any(line.startswith("-\t-\t") for line in run(cwd, ["diff", "--numstat", *changed]).splitlines())


def quiet(run: pack_git.Git, cwd: Path, args: list[str]) -> None:
    """Run git, ignoring its failure: a cleanup."""
    try:
        run(cwd, args)
    except pack_files.PackError:
        return


IMPECCABLE = Kind(
    rules=(
        "This session is not a pack update: the updater's rules on `skills/`, `golden/` and `code/` do not apply. "
        f"{CHECKS} A change to the detector's glue, the golden pages or the skills is checked again as the update was "
        "and needs the owner's approval; never change `impeccable.json`, the notice or other files of the pack. "
        f"{PUSH}"
    ),
    label=pack_updater.LABEL, content="the pack's protected content", changes="the pack's",
    refusal="pack content only an update may change",
    protected=protected, refused=_refused, recheck="golden", publish="activate",
    run=lambda job, cfg: job.live.update(job.store, cfg), pinned=lambda ctx: ctx.pins["skills"],
)  # fmt: skip
