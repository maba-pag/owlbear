"""Calibration replay before a design pack update (design skill research §3.5, step 4 of ``pack_update``).

The design judge reruns with the candidate pack an update would activate, with the project's design model, on each
decided round kept whole, and ``calibration.replayed`` compares its agreement with the owner to the recorded one. The
replay records the candidate's identity; the candidate must name the skills the judge's session loads.

Fixed are the messages, detector reveals and screenshots the round was judged on. Not fixed: the judge's worktree is
empty, and the project memory it reads is today's.
"""

from __future__ import annotations

import dataclasses
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.design_packs import calibration, design_pack
from owlbear_delivery_next.local_system import git_files
from owlbear_delivery_next.runtimes import loop_owner, sdk_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.workflow_steps import judges, sessions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.profile_record import RoleModel
    from owlbear_delivery_next.change_contracts.visual_records import VisualRound
    from owlbear_delivery_next.pack_runs.pack_candidate import Candidate
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store


NAME = re.compile(r"(?P<stem>(?P<state>[a-z0-9][a-z0-9-]{0,39})-(?P<width>\d{3,4}))-[AB]\.png")  # home-1280-A.png


class ReplayError(RuntimeError):
    """A replay judge may still be running, so no further one starts."""


def replay(
    store: Store, candidate: Candidate | None = None, run: Callable[[sdk_adapter.Session], Run] | None = None
) -> calibration.Replay:
    """The design judge, with *candidate* (else the installed pack) and the project's model, on each decided round.

    A round is replayed with the messages and screenshots it was judged on, and only if its design verdict came from
    the model and effort the replay runs; any other round is left out and counted.

    Raises:
        design_pack.PackError: No shared repository holds the rounds, the judge's worktree cannot be a repository, or
            the candidate names skills the judge does not load.
        ReplayError: A judge's processes were not confirmed gone.
    """
    if store.shared is None:
        msg = "the calibration replay reads the shared repository: set it with `owlbear-next data PATH`"
        raise design_pack.PackError(msg)
    pack = _pack(candidate)
    role, memory = roles.chosen(store.settings(), "design-review"), sessions.memory(store)
    run = run or (lambda cfg: loop_owner.run(sdk_adapter.run(cfg)))
    root, pairs, left_out = calibration.folder(store.shared, store.name).resolve(), [], 0
    if not root.is_relative_to(store.shared.root.resolve()):
        msg = f"the calibration folder leads outside the shared repository, to {root}"
        raise design_pack.PackError(msg)
    with tempfile.TemporaryDirectory(prefix="owlbear-replay-") as tmp:
        code, text = git_files.probe_in(Path(tmp))(["git", "init", "-q"])  # the window places its files only in a repo
        if code:
            msg = f"the replay's worktree could not be made a git repository: {text[:200] or f'exit {code}'}"
            raise design_pack.PackError(msg)
        base = sdk_adapter.Session(
            kind=StepKind.REVIEW, worktree=Path(tmp), session_id="", message="", resume=False,
            policy=Policy(Path(tmp), write=False), observe=lambda: tools.Worktree("", ""), checks=(),
            model=role.model, effort=role.effort, context=role.context, memory=memory,
            limit=roles.limit(store.settings(), "design-review"),
            subagents=roles.subagents(store.settings(), "design-review"),
            skills=candidate.skills if candidate else None,  # the judge loads the candidate's skills, as edited
        )  # fmt: skip
        for kept, kept_files in calibration.cases(store.shared, store.name):
            images = _images(kept, {f.name: f for f in kept_files if _inside(f, root)})
            try:
                cfgs = judges.replayed(base, kept, images) if images and _same(kept, role) else None
            except ValueError:
                cfgs = None
            if cfgs is None:
                left_out += 1
                continue
            pairs.append((kept, judges.design(_ran(run, cfgs), images, role, datetime.now(UTC)).verdict))
    return dataclasses.replace(calibration.replayed(pairs), left_out=left_out, pack=pack)


def _pack(candidate: Candidate | None) -> str:
    """The identity of the pack replayed; a candidate's skills must be the ones the judge's session loads."""
    if candidate is None:
        return design_pack.identity()
    if candidate.pins["skills"] != design_pack.manifest()["skills"]:
        msg = f"the candidate pack {candidate.pins['pack']} names skills the judge does not load; it cannot be replayed"
        raise design_pack.PackError(msg)
    return design_pack.identity(candidate.manifest, candidate.skills)


def _ran(run: Callable[[sdk_adapter.Session], Run], cfgs: list[sdk_adapter.Session]) -> list[Run]:
    runs = []
    for cfg in cfgs:
        cfg = dataclasses.replace(cfg, session_id=f"replay-{uuid.uuid4().hex[:8]}", fresh=cfg.message)  # noqa: PLW2901
        done = run(cfg)
        if not (done.termination and done.termination.confirmed):
            msg = f"the replay judge {cfg.session_id} may still be running; stop it before replaying again"
            raise ReplayError(msg)
        runs.append(done)
    return runs


def _same(kept: VisualRound, role: RoleModel) -> bool:
    """The round was judged with inputs kept and the replay's model, effort and tier, so only the pack differs."""
    design = next((v for v in kept.verdicts if v.lens == "design"), None)
    return (
        bool(kept.design_inputs)
        and design is not None
        and (design.model, design.effort, design.context) == (role.model, role.effort, role.context)
    )


def _inside(path: Path, root: Path) -> bool:
    """A real screenshot file in the calibration folder: no link, nothing reached through one."""
    return not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(root)


def _images(kept: VisualRound, kept_files: dict[str, Path]) -> list[judges.Image] | None:
    """The round's images under the names its judge saw, from the screenshots kept as ``after-home-1280.png``."""
    made = []
    for name, side in kept.blind.items():
        if not (m := NAME.fullmatch(name)) or (path := kept_files.get(f"{side}-{m['stem']}.png")) is None:
            return None
        made.append(judges.Image(name, path, side, m["state"], int(m["width"])))
    return made
