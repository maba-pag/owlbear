"""The design pack's writing updater (TD-125, TD-177): it edits the candidate's skills, then the challenger's findings.

It brings the skills in line with upstream and implements the findings after judging them; Delivery takes only its
skill edits, and it may write only in its own folder and run no shell (TD-194). Adapter repairs (TD-177) are not built:
an adapter that cannot read upstream still stops the update at the candidate or diff stage, for the owner.
"""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from typing import TYPE_CHECKING

from pydantic import Field

from owlbear_delivery_next import design_pack, pack_candidate, roles, sdk_adapter, tools
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.session_result import Run
    from owlbear_delivery_next.store import Store

LABEL = "pack-update"
FINISH = (
    "Call `submit_result` once with `summary`, skill by skill, and `rejected` for each finding you judge wrong. If the "
    "golden pages or the calibration rounds would have to change, call `report_wrong_premise`."
)


class UpdateResult(tools.Args):
    """``submit_result`` for the design pack updater."""

    summary: str = tools.bounded(
        2000, "What you changed and why, skill by skill", "owlbear-design-review: checks glow."
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
    found = (p for p in sorted(at.rglob("*")) if p.is_file() and ".git" not in p.relative_to(at).parts)
    return {p.relative_to(at).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in found}


def lay_out(at: Path, c: pack_candidate.Candidate, clone: Path) -> dict[str, str]:
    """The updater's repository: the candidate's skills to edit and upstream's new skill text to read; its files."""
    subprocess.run(["git", "init", "-q", str(at)], check=True, capture_output=True)  # noqa: S603, S607 - fixed argv
    for name in c.pins["skills"]:
        (at / "skills" / name).mkdir(parents=True, exist_ok=True)
        (at / "skills" / name / "SKILL.md").write_bytes(skill(c, name).read_bytes())
    pack_candidate.upstream_skill(clone, c.pins["upstream"]["commit"], at / "upstream")
    return _files(at)


def skill(c: pack_candidate.Candidate, name: str) -> Path:
    """One of the candidate's own skill files."""
    if c.skills is None:
        msg = "the candidate has no skill folder of its own"
        raise design_pack.PackError(msg)
    return c.skills / name / "SKILL.md"


def taken(at: Path, start: dict[str, str], c: pack_candidate.Candidate) -> list[str]:
    """Copy the updater's skills into the candidate; any other change stops the update. The skills that changed."""
    now = _files(at)
    changed = sorted(p for p in start.keys() | now.keys() if start.get(p) != now.get(p))
    allowed = {f"skills/{n}/SKILL.md" for n in c.pins["skills"]}
    if bad := [p for p in changed if p not in allowed or p not in now]:
        msg = f"the updater changed {', '.join(bad[:5])}, which it may not change"
        raise design_pack.PackError(msg)
    moved = []
    for name in c.pins["skills"]:  # every skill, so one restored to its start replaces an earlier edit too
        data = (at / "skills" / name / "SKILL.md").read_bytes()
        if skill(c, name).read_bytes() != data:
            skill(c, name).write_bytes(data)
            moved.append(name)
    return moved


def prompt(c: pack_candidate.Candidate, diff: str, lines: list[str], earlier: str = "") -> str:
    """The updater's whole first message: the update, the challenger's findings, an earlier session's work."""
    head = f"You update Delivery's design pack to `{c.pins['pack']}` (upstream `{c.tag}`). Edit the skills under "
    out = [f"{head}`skills/`; upstream's new skill text is under `upstream/`.", "", "## Rule and skill diff", diff]
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
    )  # fmt: skip


def ended(done: Run) -> UpdateResult:
    """The updater's result; any other ending stops the update with its reason, for the owner.

    Raises:
        design_pack.PackError: Its processes are not confirmed gone, it reported a premise, or it gave no result.
    """
    p = done.payload
    if not (done.termination and done.termination.confirmed):
        msg = f"the updater {done.session_id} may still be running; stop it before updating again"
        raise design_pack.PackError(msg)
    if done.ending == "premise" and isinstance(p, tools.WrongPremise):
        msg = f"the updater asks the owner: {p.reason} ({'; '.join(p.evidence)})"
        raise design_pack.PackError(msg[:2000])
    if done.ending != "result" or not isinstance(p, UpdateResult):
        msg = f"the updater ended with {done.ending}: {done.detail or 'no result'}"
        raise design_pack.PackError(msg[:600])
    return p
