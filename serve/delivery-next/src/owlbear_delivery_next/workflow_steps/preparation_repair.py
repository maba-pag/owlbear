"""A stuck check's synthetic preparation: prove the exact option, ask, then publish only what was approved."""

from __future__ import annotations

import json
import os
import shlex
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import preparation
from owlbear_delivery_next.change_contracts.repair_records import Witness
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import check, prepare, repair_copy

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.preparation import Preparation
    from owlbear_delivery_next.change_contracts.repair_records import PreparationProposal, Repair
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store

CAUSES = frozenset({"project-env:check:preparation-missing", "project-env:check:preparation-unsafe"})


def options(r: Repair) -> list[Preparation]:
    """The shown value: replace only the proposed id, or append it; leave every other option unchanged."""
    if r.preparation is None:
        msg = "the repair supplied no preparation proposal"
        raise repair_copy.RepairError(msg)
    option = r.preparation.option
    before = r.preparations_before or []
    return [option if o.id == option.id else o for o in before] + (
        [] if any(o.id == option.id for o in before) else [option]
    )


def shown(r: Repair) -> str:
    """The complete value the owner approves, kept after either answer."""
    return json.dumps({"preparations": [o.model_dump(mode="json") for o in options(r)]}, indent=2)


def context(change: Change, settings: Settings) -> str:
    """The actual project setup and requested states, not a generic no-data recipe."""
    r = change.repairs.current
    return "\n".join(
        [
            "## Missing or unsafe test preparation",
            "Propose fix=preparation, not a code patch or a no-change retry. Do not edit the project settings.",
            "Inspect what this check reads. Use committed fixtures or self-contained commands; leave no source edits.",
            "Propose synthetic data only, within the current permissions. Never copy live data or relax permissions.",
            "Declare HOME as a directory relative to the worktree root. Delivery anchors it there for every command.",
            "Describe the source, seeded content, cleanup and isolation. Supply verify: one command that checks the",
            "seeded state the check needs. Exercise it here, not only an unrelated unit test or the seed's exit.",
            "Delivery runs restore, seed, verify and cleanup in this copy before showing your exact option.",
            "If a fixture preview seeds itself, explain its separate dataset; do not claim it reads this preparation.",
            "Current preparations:",
            json.dumps(
                [o.model_dump(mode="json") for o in r.preparations_before]
                if r and r.preparations_before is not None
                else None
            ),
            "Standing data permissions:",
            settings.data.model_dump_json(),
            "Required visual states:",
            json.dumps([s.model_dump(mode="json") for s in change.brief.visual]),
        ]
    )


def _permitted(proposal: PreparationProposal, settings: Settings) -> None:
    why = preparation.refusals(proposal.option, settings.data, os.environ)
    if why:
        msg = f"the proposed preparation {proposal.option.id} is not permitted: {'; '.join(why)}"
        raise repair_copy.RepairError(msg)


def prove(store: Store, lock: Lock, change: Change, root: Path, trial: tuple[float, tuple[str, ...]]) -> None:
    """Run the exact option and seeded-state check, always clean it, and keep the host's whole trial."""
    r = change.repairs.current
    if r is None or r.preparation is None:
        msg = "the repair supplied no preparation proposal"
        raise repair_copy.RepairError(msg)
    p = r.preparation
    _permitted(p, store.settings())
    clean = root.with_name(f"{root.name}-preparation-proof")
    repair_copy.drop(root, clean)
    repair_copy.git(root, ["worktree", "add", "--quiet", "--detach", str(clean), r.base])
    try:
        if not (clean / p.option.isolation["HOME"]).resolve().is_relative_to(clean.resolve()):
            msg = "the preparation HOME resolves outside its execution worktree"
            raise repair_copy.RepairError(msg)
        r.witness = _trial(store, lock, change, clean, trial)
        if repair_copy.changed(clean, r.base):
            msg = "the preparation trial left source edits; a settings-only proposal must use unchanged project code"
            raise repair_copy.RepairError(msg)
    finally:
        repair_copy.drop(root, clean)
    store.write(lock, change)
    if r.witness.exit != 0:
        msg = f"the preparation trial failed in {clean}:\n{r.witness.output}"
        raise repair_copy.RepairError(msg)
    r.diff = shown(r)


def _trial(store: Store, lock: Lock, change: Change, root: Path, trial: tuple[float, tuple[str, ...]]) -> Witness:
    within, installs = trial
    r = change.repairs.current
    if r is None or r.preparation is None:
        msg = "a preparation trial needs its proposal"
        raise repair_copy.RepairError(msg)
    p = r.preparation
    env = prepare.isolated(prepare.Prepared(check=change.step.task or "", option=p.option), root)
    commands, output, seconds, failed = [], [], 0.0, False
    exit_code: int | None = 0

    def run(command: str, *, install: bool = False, cleanup: bool = False) -> None:
        nonlocal seconds, failed, exit_code
        commands.append(command)
        done = check.execute(
            ["/bin/sh", "-c", command] if install else shlex.split(command),
            root,
            lambda e: store.log(lock, change.slug, e),
            max(30.0 if cleanup else 0.1, within - seconds),
            None if install else env,
        )
        seconds += done.seconds
        output.append(f"$ {command}\n{done.output}{done.why}")
        if done.exit != 0:
            failed, exit_code = True, done.exit

    try:
        for command in installs:
            run(command, install=True)
            if failed:
                break
        for command in filter(None, (p.option.restore, p.option.seed, p.verify)):
            if failed:
                break
            run(command)
    finally:
        run(p.option.cleanup, cleanup=True)
    return Witness(commands=commands, exit=exit_code, seconds=seconds, output="\n".join(output))


def question(r: Repair) -> str:
    """One exact yes/no, its consequence, and the host-run proof."""
    p, w = r.preparation, r.witness
    if p is None or w is None:
        msg = "a preparation question needs its exact proposal and host-run trial"
        raise repair_copy.RepairError(msg)
    return (
        f"Save this test preparation and run the step again? {p.description}\n\n"
        "Yes saves the exact preparations entry below in this project's settings, commits and pushes it when "
        "settings are shared, then reruns this step. No changes no settings and stops with this proposal kept. "
        "Data permissions do not change. A chat can later remove or replace this saved project option; "
        "removing it does not undo checks or their effects that already ran.\n\n"
        f"The setup problem this changes: {r.evidence}\nDelivery found: {r.found}\n\n"
        f"The exact settings value:\n{r.diff}\n\n"
        f"Delivery's trial passed in the throwaway copy (exit 0 in {w.seconds:.0f} s):\n{w.output}"
    )


def apply(store: Store, change: Change) -> str:
    """Publish the approved edit, without replacing another setup or reporting a failed push as success."""
    r = change.repairs.current
    if r is None or r.preparation is None:
        msg = "the approved repair has no preparation proposal"
        raise repair_copy.RepairError(msg)
    _permitted(r.preparation, store.settings())
    after = options(r)

    def changed(layer: Layer) -> Layer:
        if layer.preparations not in (r.preparations_before, after):
            msg = "the project's preparations changed after this proposal was shown; nothing was overwritten"
            raise repair_copy.RepairError(msg)
        return layer.model_copy(update={"preparations": after})

    try:
        notice = store.save(
            store.config_path, Layer, changed, f"{store.name or 'the project'}: approved test preparation", owner=True
        )
    except StoreError as exc:
        msg = f"the approved preparation could not be published: {exc}"
        raise repair_copy.RepairError(msg) from exc
    if notice:
        msg = f"the approved preparation is not published: {notice}"
        raise repair_copy.RepairError(msg)
    return f"preparation {r.preparation.option.id}"
