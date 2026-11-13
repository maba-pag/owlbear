"""Run a stuck step's repair (#1066, D-01M6RT5QHXFM58C9BPQXEK3QFB): find the cause, prove a fix, apply, ask or stop.

A Repairer session (D-01M6SY11CY5SN5ZKYJNM0K6BDM) works in a throwaway copy of the step worktree's whole state. Delivery
then reruns the step's own checks there itself, with the confirmed install commands first: only exit 0 is proof. A
fix that weakens a check is never applied. One inside the brief's scope that touches no configuration reserved for the
owner (lint, format, CI, hooks, security) is applied and the step runs again; any other proven fix, and every new
project check, is his yes or no with the proof and the diff. Unchanged checks independently verified rerun the real
step; a failed diagnosis keeps repairing. Exhausted remedies stop listing their tries and spend; OwlBear defects get
an issue (``defect_issue``).
"""

from __future__ import annotations

import os
import shlex
import tomllib
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from traceback import format_exception_only
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import check_hint, evidence, repair_tools
from owlbear_delivery_next.change_contracts.failures import ENVIRONMENT, WRONG_MODEL, kind_of
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Outcome, StepKind, Stop
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.repair_records import KEPT, Tried, Witness
from owlbear_delivery_next.change_flow import budgets, curation_flow, loop, rebuilds, stuck, worktree
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.runtimes import session_result
from owlbear_delivery_next.settings import profile, roles
from owlbear_delivery_next.workflow_steps import (
    check,
    check_weakening,
    defect_issue,
    engine,
    lookup,
    preparation_repair,
    repair_copy,
    repair_messages,
    sessions,
)
from owlbear_delivery_next.workflow_steps.check_sources import console_script as _console_script

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.repair_records import Repair
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store

LABEL = repair_messages.LABEL


def run(store: Store, lock: Lock, change: Change, repo: Path) -> None:
    """The repair's next phase: its session and proof, or the fix the owner approved."""
    r = change.repairs.current
    assert r is not None  # noqa: S101 - the runner dispatches here only while a repair runs
    settings = store.settings()
    settings.need(f"agents.{roles.SESSIONS[LABEL]}")  # unset, it holds only this repair (D-01M6SY11CY5SN5ZKYJNM0K6BDM)
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    prof = store.read_profile() or Profile()
    try:
        if r.phase == "approved":
            _apply(store, lock, change, path, prof)
        else:
            _repair(store, lock, change, path, (settings, prof))
    except preparation_repair.CleanupPending as exc:
        now = datetime.now(UTC)
        reason = f"cleaning up the preparation trial: {exc}"
        _log(store, lock, change, reason)
        change.outcome = Outcome(exit=Exit.RETRY, cause=r.cause, reason=reason, wake_at=now + budgets.PAUSE, at=now)
        store.write(lock, change)
    except repair_copy.RepairError as exc:
        if r.fix == "preparation" and r.phase == "approved":
            now, reason = datetime.now(UTC), str(exc)
            _log(store, lock, change, reason)
            change.stop = Stop(kind=ErrorKind.PROJECT_ENV, reason=reason, action=stuck.RERUN,
                               resume="Retry publishing the approved preparation", at=now)  # fmt: skip
            change.outcome = Outcome(exit=Exit.STOP, cause=r.cause, reason=reason, who="you", at=now)
            store.write(lock, change)
        else:
            _stopped(store, lock, change, str(exc))


def _repair(store: Store, lock: Lock, change: Change, path: Path, given: tuple[Settings, Profile]) -> None:
    settings, prof = given
    r = change.repairs.current
    assert r is not None  # noqa: S101 - run() checked it
    at = store.root / "runs" / f"{change.slug}-repair-{len(change.repairs.done) + 1}"
    r.base = repair_copy.copy(path, at)
    r.target = repair_copy.git(path, ["rev-parse", f"{worktree.tracking(path, change.names.target)}^{{commit}}"])
    store.write(lock, change)
    done: Run | None = None
    try:
        preparing = r.cause in preparation_repair.CAUSES
        if preparing:
            r.preparations_before = store.read_config().preparations
        witness = () if preparing else _witness(change, prof, path)
        asked = lookup.Asked(store, lock, lambda: change)  # the repairer's and its Spotter's lookups (TD-456)
        try:
            cfg = repair_messages.session(store, lock, change, (at, asked), (settings, witness))
            done = asked.settled(lambda: sessions.run(store, cfg))
        except sessions.UsageUnreadError as exc:  # the owner's gate decides its result; its spend is the repair's
            done = exc.run
            _spent(r, done)
            store.write(lock, change)
            raise
        sessions.logged(store, lock, change, done, {"kind": LABEL, "exit": done.ending})
        _spent(r, done)
        if _gated(store, lock, change, done):
            return
        p = done.payload
        if not isinstance(p, repair_tools.RepairResult):
            _stopped(store, lock, change, f"its session ended without a result ({done.ending}: {done.detail})")
            return
        r.found, r.fix = p.cause, p.fix
        r.preparation = p.preparation
        r.tried.extend(Tried(fix=t.fix, outcome=t.outcome) for t in p.tried)
        if p.defect is not None:
            r.defect = defect_issue.file(store, path, p.defect)
        if p.fix == "none":
            _stopped(store, lock, change, "nothing it tried worked")
            return
        if preparing or p.fix == "preparation":
            _preparation(
                store,
                lock,
                change,
                (path, at, bool(done.termination and done.termination.confirmed)),
                (roles.limit(settings, LABEL), _installs(change, prof)),
            )
            return
        if p.fix == "retry":
            _unchanged(store, lock, change, (path, at), (witness, roles.limit(settings, LABEL), prof))
            return
        r.package, r.command = p.package.strip(), p.command.strip()
        _proven(store, lock, change, (path, at), witness, roles.limit(settings, LABEL), prof)
    finally:
        if done is not None and done.termination is not None and done.termination.confirmed:
            repair_copy.drop(path, at)
        else:  # its processes may still use it: the next repair's copy replaces it
            _log(store, lock, change, f"kept its copy {at}: its session's processes are not confirmed gone")


def _preparation(
    store: Store, lock: Lock, change: Change, trees: tuple[Path, Path, bool], trial: tuple[float, tuple[str, ...]]
) -> None:
    _, at, _ = trees
    r = change.repairs.current
    if r is None or r.fix != "preparation" or r.cause not in preparation_repair.CAUSES:
        _stopped(store, lock, change, "missing or unsafe preparation needs a concrete setup proposal")
        return
    if repair_copy.changed(at, r.base):
        _stopped(store, lock, change, "a preparation proposal must repair setup without source edits")
        return
    preparation_repair.prove(store, lock, change, trees, trial)
    stuck.asked(change, repair_messages.question(r), datetime.now(UTC))
    store.write(lock, change)


def _unchanged(
    store: Store,
    lock: Lock,
    change: Change,
    trees: tuple[Path, Path],
    given: tuple[tuple[str, ...], float, Profile],
) -> None:
    path, at = trees
    r = change.repairs.current
    assert r is not None  # noqa: S101 - _repair checked it
    if repair_copy.changed(at, r.base):
        _stopped(store, lock, change, "it reported no change needed but left edits; none were applied")
        return
    if r.step == StepKind.BUILD and not engine.contains(at, r.target):
        _log(store, lock, change, f"target {r.target} is not integrated; scheduling integration, not accepting a fix")
        stuck.unchanged(change, "the missing target needs integration", datetime.now(UTC))
        store.write(
            lock,
            loop.apply(
                change,
                engine.integrate(change, StepKind.BUILD, worktree.tracking(path, change.names.target)),
                datetime.now(UTC),
            ),
        )
        return
    witness, within, prof = given
    if why := _witnessed(store, lock, change, at, (witness, within, prof)):
        r.evidence += f"\nDelivery's unchanged diagnostic failed: {why}"
        _log(store, lock, change, f"the unchanged diagnosis failed; trying remedies: {why}")
        change.outcome = Outcome(exit=Exit.RETRY, cause=r.cause, reason=f"repairing: {why}", at=datetime.now(UTC))
        store.write(lock, change)
        return
    said = f"no change was needed; the unchanged checks passed; the step runs again.{repair_messages.defect(r)}"
    _log(store, lock, change, said)
    stuck.unchanged(change, f"Delivery's repair: {said}", datetime.now(UTC))
    store.write(lock, change)


def _proven(  # noqa: PLR0913, PLR0917 - the Change, its two trees, the proof and its limit, the profile
    store: Store, lock: Lock, change: Change, trees: tuple[Path, Path], witness: tuple[str, ...], within: float,
    prof: Profile,
) -> None:  # fmt: skip
    """Check the fix, run the witness in the copy, then apply it, ask the owner or stop."""
    path, at = trees
    r = change.repairs.current
    assert r is not None  # noqa: S101 - _repair() checked it
    changed = repair_copy.changed(at, r.base)
    if r.fix == "profile-check":  # Delivery never runs a proposed command before the owner confirms it (#1066)
        _offered(store, lock, change, at, changed, prof)
        return
    if not changed:
        _stopped(store, lock, change, "it reported a fix but changed nothing")
        return
    weak = [
        f"{p} ({w})" for p, how in changed if (w := check_weakening.weakened(repair_copy.git, at, r.base, p, how)[0])
    ]
    if weak:
        _stopped(store, lock, change, f"its fix weakens a check, which Delivery never applies: {', '.join(weak)}")
        return
    if why := _witnessed(store, lock, change, at, (witness, within, prof)):
        _stopped(store, lock, change, why)
        return
    r.paths = [p for p, _ in changed]
    said = f"fix: {stuck.obstruction(r.found)}\n\nRepaired by an agent; committed by Delivery."
    r.commit = repair_copy.commit(at, said)
    repair_copy.git(path, ["update-ref", f"{KEPT}{change.slug}", r.commit])
    r.held = [f"changes {p}, configuration that is yours" for p in r.paths if check_weakening.configured(p)]
    r.held += [f"makes {p} a link or submodule" for p, how in changed if how.split()[0] in check_weakening.LINKS]
    r.held += [
        f"{edit} the test {p}"
        for p, how in changed
        if (edit := check_weakening.weakened(repair_copy.git, at, r.base, p, how)[1])
    ]
    r.held += [reason for p in r.paths if (reason := _check_hold(p, witness, path))]
    r.held += [f"changes {p}, outside the brief's scope" for p in r.paths if not _in_scope(change, p)]
    if not r.held:
        _apply(store, lock, change, path, prof)
        return
    r.diff, cut = repair_copy.shown(path, r.base, r.commit, r.paths)
    if cut:
        _stopped(store, lock, change, "its proven fix is too long or binary to show you whole: not applied")
        return
    stuck.asked(change, repair_messages.question(r), datetime.now(UTC))
    store.write(lock, change)


def _witnessed(
    store: Store, lock: Lock, change: Change, at: Path, given: tuple[tuple[str, ...], float, Profile]
) -> str:
    """Delivery's run of the witness on the staged fix; why it proves nothing, or empty when it proves the fix."""
    (witness, within, prof), r = given, change.repairs.current
    assert r is not None  # noqa: S101 - _proven() checked it
    tree = repair_copy.git(at, ["write-tree"])
    r.witness = _ran(at, (*_installs(change, prof), *witness), within, store, lock)
    if not witness or r.witness.exit != 0:
        return f"Delivery's run of {', '.join(witness) or 'no check'} with the fix failed: {r.witness.output}"
    repair_copy.changed(at, r.base)  # stages what the run left, its bytecode aside
    if wrote := repair_copy.git(at, ["diff", "--cached", "--name-only", tree]).splitlines():
        return f"its proof changed {', '.join(wrote)}, so it proved other bytes than the fix"
    return ""


def _offered(  # noqa: PLR0913, PLR0917 - the Change, its copy, what changed there and the profile
    store: Store, lock: Lock, change: Change, at: Path, changed: list[tuple[str, str]], prof: Profile
) -> None:
    """A proposed project check is the owner's to confirm, unless it can't be offered."""
    r = change.repairs.current
    assert r is not None  # noqa: S101 - _proven() checked it
    if why := _unfit(at, r.package, changed, prof):
        _stopped(store, lock, change, why)
        return
    r.held = [f"adds the check `{r.command}` for {r.package} to the project profile, which you confirm"]
    stuck.asked(change, repair_messages.question(r), datetime.now(UTC))
    store.write(lock, change)


def _apply(store: Store, lock: Lock, change: Change, path: Path, prof: Profile) -> None:
    r = change.repairs.current
    assert r is not None  # noqa: S101 - run() checked it
    if r.fix == "preparation":
        made = preparation_repair.apply(store, change)
    elif r.fix == "profile-check":
        key = f"check:{r.package}"
        if (entry := prof.entries.get(key)) is not None and profile.is_confirmed(entry):  # confirmed while it waited
            _stopped(store, lock, change, f"{r.package}'s check `{entry.value}` was confirmed meanwhile; nothing added")
            return
        store.write_profile(profile.confirm(prof, key, r.command, datetime.now(UTC)))
        made = f"profile {key}"
    else:
        message = f"fix: {stuck.obstruction(r.found)}\n\nRepaired by an agent; applied by Delivery (#1066)."
        made = repair_copy.apply(path, change.names.branch, r.base, r.commit, message)
        repair_copy.git(path, ["update-ref", "-d", f"{KEPT}{change.slug}"])
    _log(store, lock, change, f"applied {made}; the step runs again.{repair_messages.defect(r)}")
    stuck.applied(change, made)
    store.write(lock, change)


def _stopped(store: Store, lock: Lock, change: Change, why: str) -> None:
    r = change.repairs.current
    said = f"{why}.{repair_messages.defect(r)}".rstrip(".") if r else why
    _log(store, lock, change, f"stopped: {said}")
    stuck.stopped(change, said, datetime.now(UTC))
    store.write(lock, change)


def _witness(change: Change, prof: Profile, source: Path) -> tuple[str, ...]:
    """The commands that must pass: the task's resolved checks, else the confirmed checks of the brief's packages."""
    try:
        return _resolved_witness(change, prof, source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        r = change.repairs.current
        if r is None:
            raise
        detail = "".join(format_exception_only(error)).strip()
        r.evidence += f"\nUnchanged runner ownership in {source}/serve/tools/pyproject.toml: {detail}"
        if change.tests is not None and r.task == curation_flow.CURATE:
            msg = f"cannot resolve the curator's unchanged measurement in {source}: {detail}"
            raise repair_copy.RepairError(msg) from error
        task = next((t for t in change.plan.tasks if t.id == r.task), None) if change.plan else None
        pairs = worktree.checks(profile.vouched(prof))
        selected = (
            check_hint.resolve(task.checks, pairs)
            if task and task.checks
            else [check_hint.qualified(p, c) for p, c in pairs if _in_scope(change, p)]
        )
        target = worktree.git(
            source, "rev-parse", f"{worktree.tracking(source, change.names.target)}^{{commit}}"
        ).strip()
        base = task.base if task and task.base is not None else r.base
        return tuple(check_hint.task_command(command, base, target) for command in selected)


def _resolved_witness(change: Change, prof: Profile, source: Path) -> tuple[str, ...]:
    tasks = change.plan.tasks if change.plan else []
    r = change.repairs.current
    task = next((t for t in tasks if r and t.id == r.task), None)
    if task:
        rebuilds.refresh(change, task)
    pairs = worktree.checks(profile.vouched(prof))
    if task and r is not None and (task.checks or (change.tests is not None and r.task == curation_flow.CURATE)):
        bound = task if task.base is not None else task.model_copy(update={"base": r.base})
        return tuple(worktree.build_checks(profile.vouched(prof), change, bound, source))
    selected = [check_hint.qualified(p, c) for p, c in pairs if _in_scope(change, p)]
    if r is None or not worktree.owns_changed_runner(source):
        return tuple(selected)
    target = worktree.git(source, "rev-parse", f"{worktree.tracking(source, change.names.target)}^{{commit}}").strip()
    return tuple(check_hint.task_command(command, r.base, target) for command in selected)


def _installs(change: Change, prof: Profile) -> tuple[str, ...]:
    return tuple(check_hint.qualified(p, c) for p, c in worktree.installs(prof, change.brief.scope or ["."]))


def _check_hold(path: str, witness: tuple[str, ...], source: Path) -> str:
    """Incomplete original-source discovery holds the fix with the whole error, never applies it."""
    try:
        named = _named(path, witness, source)
    except (OSError, SyntaxError, tomllib.TOMLDecodeError) as error:
        detail = "".join(format_exception_only(error)).strip()
        return f"cannot inspect the unchanged check for {path}: {detail}; its altered witness proves nothing alone"
    return f"changes {path}, which the step's check runs, so it proves nothing alone" if named else ""


def _named(path: str, witness: tuple[str, ...], source: Path | None = None) -> bool:
    """Whether a check command names *path*: a fix to the check it is proven by needs the owner (never weakened).

    A script by its path, a Python module run with ``-m`` by its file, or the root selector's imported machinery;
    a command that can't be parsed names every path.
    """
    for one in witness:
        where, command = _split(one)
        try:
            words = list(shlex.shlex(command, posix=True, punctuation_chars=True))
        except ValueError:
            return True
        if source is not None and _console_script(path, words, source):
            return True
        for before, word in zip(["", *words], words, strict=False):
            found = [word.strip("{}")]
            if before == "-m":
                module = word.replace(".", "/")
                found = [f"{module}.py", f"{module}/__main__.py", f"{module}/__init__.py"]
            for name in found:
                named = os.path.normpath(PurePosixPath(where or ".", name))
                if named == os.path.normpath(path):
                    return True
                if before == "-m" and path.endswith(f"/{name}") and (not where or evidence.within(where, path)):
                    return True  # a module found on the path, as a src/ layout puts it
                if not where and PurePosixPath(name).name == path:
                    return True
    return False


def _split(check: str) -> tuple[str | None, str]:
    """A resolved check as (its directory, the command run there), as ``check_hint`` writes it: `cd <dir> && {…}`."""
    found = check_hint.CD_CHECK.fullmatch(check.strip())
    if not found:
        return None, check
    body = found[2].strip()
    return shlex.split(found[1])[0], body[1:-1] if body.startswith("{") and body.endswith("}") else body


def _in_scope(change: Change, path: str) -> bool:
    return not change.brief.scope or any(evidence.within(s, path) for s in change.brief.scope)


def _ran(at: Path, commands: tuple[str, ...], within: float, store: Store, lock: Lock) -> Witness:
    """Delivery's own run of *commands* in the copy, one after another, within *within* seconds together."""
    seconds, out = 0.0, []
    for command in commands:
        done = check.execute(["/bin/sh", "-c", command], at, lambda e: store.log(lock, lock.slug, e), within - seconds)
        seconds += done.seconds
        out.append(f"$ {command}\n{done.output}{done.why}")
        if done.exit != 0:
            return Witness(commands=list(commands), exit=done.exit, seconds=seconds, output="\n".join(out))
    return Witness(commands=list(commands), exit=0, seconds=seconds, output="\n".join(out))


def _spent(r: Repair, run: Run) -> None:
    """Add *run*'s credits to the repair's: unknown once any session's spend is unknown."""
    found = run.usage.get("credits")
    spent = float(found) if isinstance(found, int | float) else None
    r.credits = spent if not r.session else None if r.credits is None or spent is None else r.credits + spent
    r.session = run.session_id


def _gated(store: Store, lock: Lock, change: Change, done: Run) -> bool:
    """The gates every session's result passes first; True when they settled the repair for now.

    Processes not confirmed gone or a credit limit stop it; a wrong model reruns it once after the wait
    (D-01M5DW3X003TZZRSDCY027SP3C); a network or quota failure is temporary: the repair runs again later
    (D-01M6RT5QHWHB0ZHBBY0BE34FBE).
    """
    r, now = change.repairs.current, datetime.now(UTC)
    assert r is not None  # noqa: S101 - _repair() checked it
    seen = session_result.to_result(done, StepKind(r.step), now)
    wrong = (seen.cause or "").endswith(f":{WRONG_MODEL}")
    if seen.exit == Exit.STOP or (wrong and r.rerun):
        _stopped(store, lock, change, f"its session's result was voided: {seen.reason}")
        return True
    temporary = kind_of(seen.cause) in ENVIRONMENT and not isinstance(done.payload, repair_tools.RepairResult)
    if not (wrong or temporary):
        return False
    r.rerun = r.rerun or wrong
    wake = seen.wake_at if seen.wake_at and seen.wake_at > now else now + budgets.PAUSE
    change.outcome = Outcome(
        exit=Exit.RETRY, cause=r.cause, reason=f"repairing again: {seen.reason}", wake_at=wake, at=now
    )
    _log(store, lock, change, f"runs again at {wake:%H:%M}: {seen.reason}")
    store.write(lock, change)
    return True


def _unfit(at: Path, package: str, changed: list[tuple[str, str]], prof: Profile) -> str:
    """Why a proposed project check can't be offered: its package lies outside the repository, or it needs edits."""
    where = PurePosixPath(package)
    inside = not where.is_absolute() and ".." not in where.parts and (at / where).resolve().is_relative_to(at.resolve())
    if not inside or not (at / where).is_dir():
        return f"its proposed check names the package {package}, which is not a folder of this repository"
    if (entry := prof.entries.get(f"check:{package}")) is not None and profile.is_confirmed(entry):
        return f"its proposed check would replace {package}'s confirmed check `{entry.value}`, which only you change"
    if changed:
        edits = ", ".join(p for p, _ in changed)
        return f"its proposed check also needs files it changed ({edits}), which a project check cannot carry"
    return ""


def _log(store: Store, lock: Lock, change: Change, said: str) -> None:
    r = change.repairs.current
    at = datetime.now(UTC).isoformat(timespec="seconds")
    store.log(lock, change.slug, {"event": "repair", "at": at, "cause": r.cause if r else "", "reason": said})
