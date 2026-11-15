"""A repair's proposal for a project check command: add one, replace a confirmed one or remove it, by the owner's yes.

The owner confirms every project check (#968). A repair adds a check the profile lacks (#1066), replaces a confirmed
one that cannot pass with a command it proved in its copy (D-01M7FV79CK8TJVQMWQZY0M3RSE), or, when nothing a check
could run on exists until the Change has built the project, has the confirmed one removed, so the Change plans without
a check and gets a proven one after its first task (D-01M7FW1WD4W53C76BSF35KSWW4, #1275). Delivery never runs a
proposed command before his yes. The Change that asked then plans again what its plan built on the old check.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import check_hint
from owlbear_delivery_next.change_contracts.models import Exit, Outcome, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import moves, worktree
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.workflow_steps import project_checks

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.repair_records import Repair
    from owlbear_delivery_next.state_store.store import Lock, Store

LATER = project_checks.LATER
MEANS = (  # what the answers mean once a confirmed check changes; {0}: what yes does to the project's check
    "Yes {0}; a later repair can change it again the same way. "
    "This Change's open work that used the old check is planned again on the existing code, then Delivery continues. "
    "No leaves the check as it is and stops this Change; running the step again repeats this repair."
)


def _current(change: Change) -> Repair:
    if (r := change.repairs.current) is None:
        msg = "only a running repair proposes or applies a project check"
        raise ValueError(msg)
    return r


def _confirmed(prof: Profile, package: str) -> str:
    entry = prof.entries.get(f"check:{package}")
    return entry.value if entry is not None and profile.is_confirmed(entry) else ""


def offer(change: Change, at: Path, changed: list[tuple[str, str]], prof: Profile) -> str:
    """Why the repair's check proposal can't be put to the owner, else "" with its reason and what it replaces set."""
    r = _current(change)
    where, old = PurePosixPath(r.package), _confirmed(prof, r.package)
    inside = not where.is_absolute() and ".." not in where.parts and (at / where).resolve().is_relative_to(at.resolve())
    if not inside or not (at / where).is_dir():
        return f"its proposed check names the package {r.package}, which is not a folder of this repository"
    if changed:
        edits = ", ".join(p for p, _ in changed)
        return f"its proposed check also needs files it changed ({edits}), which a project check cannot carry"
    if r.fix == LATER:
        if project_checks.deferred(change) or project_checks.has_built(change) or not old:
            return (
                f"it asked to remove {r.package}'s check until the project is built, which needs a confirmed check "
                "and a Change that has built no task and deferred no check yet"
            )
        said = f"removes {r.package}'s confirmed check `{old}` from the project profile until this Change has built"
        r.replaces, r.held = old, [f"{said} the project, which you confirm"]
        return ""
    if old == r.command:
        return f"it proposed {r.package}'s check `{old}`, which is already confirmed"
    r.replaces = old
    replaces = f"replaces {r.package}'s confirmed check `{old}` with `{r.command}` in the project profile"
    adds = f"adds the check `{r.command}` for {r.package} to the project profile"
    r.held = [f"{replaces if old else adds}, which you confirm"]
    return ""


def question(r: Repair, defect: str) -> str:
    """The owner's yes or no on the proposal, with what each answer means when a confirmed check changes."""
    last = r.tried[-1].outcome if r.tried else "nothing"
    proof = f"With its fix, the repairer reports it passed ({last}); Delivery runs it only once you confirm it"
    if r.fix == LATER:
        lead = f"Delivery found what stopped the work: the project's check for {r.package} cannot pass, and no check"
        lead += " can until this Change has built the project"
        ask, yes = "Remove it and continue this Change?", "leaves every Change of this project without that check"
        proof = "After the first task, Delivery proposes a check proven on the built project"
    elif r.replaces:
        lead = f"Delivery found a fix for what stopped the work: another check command for {r.package}"
        ask, yes = "Replace the project's check and continue this Change?", "changes the check for every later Change"
    else:
        lead = f"Delivery found a fix for what stopped the work: `{r.command}` for {r.package}"
        ask, yes = "Add this check to the project profile and run the step again?", ""
    means = f" {MEANS.format(yes)}" if r.replaces else ""
    return (
        f"{lead}. It needs your yes because it {'; '.join(r.held)}. {ask}{means}\n\n"
        f"Details: the step was stopped by: {r.evidence}\nDelivery's repair found: {r.found}\n{proof}.{defect}"
    )


def apply(store: Store, lock: Lock, change: Change, prof: Profile, path: Path) -> tuple[str, str]:
    """Write the approved proposal to the profile; (what was made, "") or ("", why the profile no longer fits it)."""
    r = _current(change)
    key, now = f"check:{r.package}", datetime.now(UTC)
    if (held := _confirmed(prof, r.package)) != r.replaces:  # changed while the question waited
        said = f"`{held}` was confirmed" if held else "was removed"
        return "", f"{r.package}'s check {said} meanwhile; nothing changed"
    if r.fix == LATER:
        store.write_profile(profile.withdraw(prof, key, profile.package_entries(path).get(key)))
        at = now.isoformat(timespec="seconds")
        store.log(lock, change.slug, {"event": "profile-withdrawn", "at": at, "key": key, "value": r.replaces})
        return "check deferred", ""
    store.write_profile(profile.confirm(prof, key, r.command, now))
    return f"profile {key}", ""


def adopt(store: Store, change: Change, repair: Repair, repo: Path) -> None:
    """After a confirmed check changed: the asking Change plans its open tasks that name the old one again."""
    if not repair.replaces or change.plan is None:
        return
    prof = profile.vouched(store.read_profile() or Profile())
    offered = [check_hint.qualified(p, c) for p, c in worktree.plan_checks(prof, Path(change.names.worktree or repo))]

    def stale(check: str) -> bool:
        return check_hint.body(check)[0] == repair.package and not check_hint.offered(check, offered)

    tasks = [t for t in change.plan.tasks if any(stale(c) for c in t.checks)]
    for t in tasks:
        if t.done:  # the repair tasks that copy it get the current checks whole
            t.checks = list(offered)
    if any(not t.done for t in tasks):
        new = f"`{repair.command}` replaces it" if repair.fix != LATER else "no check exists until the project is built"
        why = f"The project's check for {repair.package}, `{repair.replaces}`, cannot pass: {new}."
        moves.go(change, StepKind.PLAN)
        change.outcome = Outcome(
            exit=Exit.BACK,
            reason=f"{why} Plan the work that is still open again, on the existing code.",
            at=datetime.now(UTC),
        )
