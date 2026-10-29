"""Impeccable's writing updater (TD-125, TD-177): it edits the candidate, then the challenger's findings.

It brings the skills, the golden pages and the detector's glue in line with upstream and implements the findings after
judging them; Delivery takes only changes within the pack (``pack_gates``), and it may write only in its own folder
and run no shell (TD-194). An adapter that cannot read upstream still stops the update at the candidate or diff
stage, for the owner.
"""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from typing import TYPE_CHECKING

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.impeccable_runs import pack_candidate, pack_gates
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.workflow_steps import sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store

LABEL = "pack-update"
UPSTREAM_DIFF = "upstream/skill.diff"  # upstream's skill text from the pinned tag, laid out for the updater
FINISH = (
    "Call `submit_result` once with `summary`, file by file, `evidence` when you changed `golden/`, and `rejected` for "
    "each finding you judge wrong. If the calibration rounds would have to change, call `report_wrong_premise`."
)
RULES = (
    "Change only what the upgrade needs. You may edit the skills' `SKILL.md`, add, edit or remove golden pages and "
    "`golden/expected.json`, and edit the two files under `code/`; any other change is refused. A change under "
    "`golden/` changes the pack's expected evidence: the owner accepts it before the checks go on. A change under "
    "`code/` is not run by this update's checks, which use the running code: the owner approves its diff before the "
    "pull request, and CI's unit tests must pass."
)


class UpdateResult(tools.Args):
    """``submit_result`` for the Impeccable updater."""

    summary: str = tools.bounded(2000, "What you changed and why, file by file", "owlbear-design-review: checks glow.")
    evidence: str = Field(
        default="",
        max_length=1000,
        description="Only when you changed `golden/`: why the upgrade needs each changed expectation or page",
    )
    rejected: list[tools.Rejection] = Field(
        default_factory=list,
        max_length=20,
        description="Only when your message lists challenger findings: those you judge wrong, by key, with evidence; "
        "the next challenger judges each",
    )


UPDATE = tools.Spec("submit_result", "Submit once, after editing the skills.", UpdateResult, "result")


def new_id() -> str:
    """A fresh updater session id."""
    return f"{LABEL}-{uuid.uuid4().hex[:8]}"


def _files(at: Path) -> dict[str, str]:
    found = (
        p for p in sorted(at.rglob("*")) if p.is_file() and not p.is_symlink() and ".git" not in p.relative_to(at).parts
    )
    return {p.relative_to(at).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in found}


def lay_out(at: Path, c: pack_candidate.Candidate, clone: Path, package: Path) -> dict[str, str]:
    """The updater's repository: the candidate's skills, golden pages and glue to edit, upstream's skills to read."""
    subprocess.run(["git", "init", "-q", str(at)], check=True, capture_output=True)  # noqa: S603, S607 - fixed argv
    for name in c.pins["skills"]:
        (at / "skills" / name).mkdir(parents=True, exist_ok=True)
        (at / "skills" / name / "SKILL.md").write_bytes(skill(c, name).read_bytes())
    pack_gates.lay_out(at, package)
    upstream(at, c, clone)
    return _files(at)


def upstream(at: Path, c: pack_candidate.Candidate, clone: Path) -> None:
    """Upstream's new skill text and its diff from the pinned tag, for the updater to read: it runs no shell."""
    commit = c.pins["upstream"]["commit"]
    pack_candidate.upstream_skill(clone, commit, at / "upstream")
    (at / UPSTREAM_DIFF).write_text(pack_update.skill_diff(clone, commit), encoding="utf-8")


def skill(c: pack_candidate.Candidate, name: str) -> Path:
    """One of the candidate's own skill files."""
    if c.skills is None:
        msg = "the candidate has no skill folder of its own"
        raise pack_files.PackError(msg)
    return c.skills / name / "SKILL.md"


def outside(at: Path, start: dict[str, str], skills: list[str]) -> list[str]:
    """The paths the updater changed that it may not change, and every link it made (TD-194)."""
    now = _files(at)
    changed = sorted(p for p in start.keys() | now.keys() if start.get(p) != now.get(p))
    return sorted({*(p for p in changed if not pack_gates.allowed(p, p in now, skills)), *pack_gates.links(at)})


def taken(at: Path, c: pack_candidate.Candidate) -> list[str]:
    """Copy the updater's skills into the candidate; the skills that changed."""
    moved = []
    for name in c.pins["skills"]:  # every skill, so one restored to its start replaces an earlier edit too
        data = (at / "skills" / name / "SKILL.md").read_bytes()
        if skill(c, name).read_bytes() != data:
            skill(c, name).write_bytes(data)
            moved.append(name)
    return moved


def prompt(c: pack_candidate.Candidate, diff: str, lines: list[str], earlier: str = "", golden: str = "") -> str:
    """The updater's whole first message: the update, the challenger's findings, an earlier session's work."""
    kept = [n for n in diff.splitlines() if not n.startswith(pack_update.SKILL_TEXT)]  # a command it cannot run
    shown = "\n".join([*kept, f"{pack_update.SKILL_TEXT}`{UPSTREAM_DIFF}`"])
    head = f"You update Delivery's Impeccable to `{c.pins['pack']}` (upstream `{c.tag}`). Edit the skills under "
    out = [
        (
            f"{head}`skills/`, the golden pages and their expectations under `golden/` and the detector's glue under "
            "`code/` (`detector.py` calls the engine and reads its findings; `pack_update.py` reads upstream's "
            f"registry and skills). Upstream's new skill text is under `upstream/{pack_update.SKILL}/`, and "
            f"`{UPSTREAM_DIFF}` is its diff from the pinned tag. You have no shell: read these files."
        ),
        "", "## What you may change", RULES, "", "## Rule and skill diff", shown,
    ]  # fmt: skip
    out += ["", "## Golden pages with the package's expectations", golden] if golden else []
    out += lines
    out += ["", "## The earlier updater session's work (it could not be resumed)", earlier] if earlier else []
    return "\n".join([*out, "", "## Finish", FINISH])


def repair(lines: list[str]) -> str:
    """The challenger's findings, by key: what a resumed updater is sent."""
    return "\n".join([*lines, "", "## Finish", FINISH])


def config(  # noqa: PLR0913 - one session: its worktree, id, message, resume, fallback, replacement and keys
    store: Store,
    at: Path,
    sid: str,
    message: str,
    *,
    resume: bool,
    fresh: str,
    replaced: Callable[[], str | None],
    keys: tuple[tuple[str, ...], tuple[str, ...]] = ((), ()),
) -> sdk_adapter.Session:
    """The writing updater's session in its own repository; *keys* are the findings it may reject and the owner's."""
    role = roles.chosen(store.settings(), LABEL)
    return sdk_adapter.Session(
        kind=StepKind.BUILD, worktree=at, session_id=sid, message=message, resume=resume,
        policy=Policy(at, write=True, confined=True), observe=lambda: tools.Worktree("", ""), checks=(),
        submit=UPDATE, rejectable=keys[0], settled=keys[1], model=role.model, effort=role.effort,
        context=role.context, role="updater", fresh=fresh, journal=sdk_adapter.Journal(replaced=replaced),
        limit=roles.limit(store.settings(), LABEL), subagents=roles.subagents(store.settings(), LABEL),
        memory=sessions.memory(store),  # TD-399: it recalls and saves like the other producing roles
        user=roles.user_config(store.settings()),
    )  # fmt: skip


def ended(done: Run) -> UpdateResult:
    """The updater's result; any other ending stops the update with its reason, for the owner.

    Raises:
        pack_files.PackError: Its processes are not confirmed gone, it reported a premise or a missing tool, or it
            gave no result.
    """
    p = done.payload
    if not (done.termination and done.termination.confirmed):
        msg = f"the updater {done.session_id} may still be running; stop it before updating again"
        raise pack_files.PackError(msg)
    if done.ending == "premise" and isinstance(p, tools.WrongPremise):
        msg = f"the updater asks the owner: {p.reason} ({'; '.join(p.evidence)})"
        raise pack_files.PackError(msg[:2000])
    if done.ending == "missing-tool" and isinstance(p, tools.MissingTool):
        msg = f"the updater lacks {p.tool}: {p.need} ({p.error})"
        raise pack_files.PackError(msg[:2000])
    if done.ending != "result" or not isinstance(p, UpdateResult):
        msg = f"the updater ended with {done.ending}: {done.detail or 'no result'}"
        raise pack_files.PackError(msg[:600])
    return p
