"""TD-96, TD-107: run a check's chosen test preparation and keep the preparer's setup edits as a patch.

Per check, a live copy is exported and masked once into a frozen snapshot outside every repository. Before the
"before" capture and again before the host launches the check, that same snapshot is restored into the isolated test
environment, test data is seeded and the preparer's setup patch applied. The end of the check runs the cleanup command
with the patch still applied, then discards it and deletes the snapshot unless the owner keeps a masked one; a failed
cleanup or deletion is ended again by the next runner. Restore, seed, cleanup and the launch run with an explicit
environment: the process essentials (``preparation.BASE``) and the option's isolation, never Delivery's own; only
export and masking see that, and they run only the project's committed scripts, never one the preparer edited.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import preparation, tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import (
    VISUAL,
    ErrorKind,
    Exit,
    Outcome,
    StepKind,
    Stop,
    Waiting,
)
from owlbear_delivery_next.change_contracts.preparation import LIVE, SNAPSHOT, Preparing
from owlbear_delivery_next.change_flow import budgets, loop, worktree
from owlbear_delivery_next.change_flow.worktree import failure
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.state_store.prepared import (
    Prepared,
    cleanup_record,
    cleanup_records,
    left,
    read,
    snapshot_owner,
)
from owlbear_delivery_next.state_store.prepared import (
    file as _file,
)
from owlbear_delivery_next.state_store.prepared import (
    folder as _dir,
)
from owlbear_delivery_next.state_store.prepared import (
    write as _write,
)
from owlbear_delivery_next.workflow_steps import before, check, engine, preparer, repair_copy, snapshot_files
from owlbear_delivery_next.workflow_steps.check import PrepareError
from owlbear_delivery_next.workflow_steps.snapshot_files import snapshots

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store

type Log = Callable[[dict[str, Any]], None]
SESSION = "session.open"  # a running preparer session's root and the edits it found (JSON)
SHAPING = "shaping"  # the shaping capture's own test copy (D-01M6Q56RXK85C5T4AG7R051X6N)


def _git(root: Path, *args: str, env: Mapping[str, str] | None = None) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=root, capture_output=True, check=True, timeout=60, env=env
    ).stdout


def edits(root: Path) -> list[str]:
    """Every uncommitted path of the worktree, both ends of a rename or copy in either column, each once."""
    out = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return worktree.status_paths(out.decode().split("\0"))


def _in_head(root: Path, paths: Sequence[str]) -> set[str]:
    out = _git(root, "--literal-pathspecs", "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", *paths)
    return set(out.decode().split("\0")) - {""}


def capture(root: Path, paths: Sequence[str]) -> bytes:
    """The edits of *paths* against HEAD as one binary patch, staged in a private index; the worktree's is untouched.

    A path in neither HEAD nor the worktree, such as a rename's middle name, has no edit and is left out (#744).
    """
    head = _in_head(root, paths) if paths else set()
    kept = [p for p in paths if p in head or os.path.lexists(root / p)]
    if not kept:
        return b""  # a pathless ``add --all`` would take every other edit too
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ | {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        _git(root, "read-tree", "HEAD", env=env)
        _git(root, "--literal-pathspecs", "add", "--all", "--", *kept, env=env)
        return _git(root, "diff", "--cached", "--binary", "HEAD", env=env)


def discard(root: Path, paths: Sequence[str]) -> None:
    """Return *paths* to HEAD: tracked ones checked out, new ones removed; nothing else is touched."""
    if not paths:
        return
    _git(root, "--literal-pathspecs", "reset", "-q", "HEAD", "--", *paths)
    tracked = _in_head(root, paths)
    if tracked:
        _git(root, "--literal-pathspecs", "checkout", "HEAD", "--", *sorted(tracked))
    for p in set(paths) - tracked:
        (root / p).unlink(missing_ok=True)


def context(store: Store, c: Change, settings: Settings, root: Path) -> preparation.Preparing:
    """What a preparer's recipe is validated against, with the HEAD and the edits its session starts from.

    The edits, HEAD and ignored setup files are kept on disk too, so the preparer's own are undone even when its
    runner dies (``stray``).
    """
    found, folder = edits(root), _dir(store, c.slug)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    globs = sorted({g for o in settings.preparations for g in o.setup_globs})
    started = {"root": str(root), "found": found} | preparer.start(root, folder, globs)
    atomic_write(folder / SESSION, json.dumps(started))
    return preparation.Preparing(tuple(settings.preparations), settings.data, started["head"], tuple(found))


def stray(store: Store, slug: str, log: Log) -> None:
    """Discard the edits of a preparer session whose runner ended before ``chosen`` (TD-107)."""
    marker = _dir(store, slug) / SESSION
    if not marker.is_file():
        return
    started = json.loads(marker.read_text())
    if (root := Path(started["root"])).is_dir():
        undone = preparer.end(root, _dir(store, slug), started)
        made = [p for p in edits(root) if p not in set(started["found"])]
        discard(root, made)
        log({"event": "prepared-stray", "at": datetime.now(UTC).isoformat(), "discarded": made[:20], **undone})
    marker.unlink()


def chosen(  # noqa: PLR0913, PLR0917 - the session's end, its worktree and what it started from
    store: Store, lock: Lock, c: Change, root: Path, payload: tools.Args | None, ctx: Preparing, result: loop.StepResult
) -> loop.StepResult:
    """End a preparer session: keep an accepted recipe's option and setup edits as its patch, then discard every edit.

    The preparer's edits, commits and ignored setup files never stay in the worktree, accepted or not (TD-107);
    edits it found there stay. A preparer that moved HEAD keeps nothing.
    """
    marker = _dir(store, c.slug) / SESSION
    started = json.loads(marker.read_text()) if marker.is_file() else {"head": ctx.head}
    moved = preparer.end(root, _dir(store, c.slug), started).get("reset")  # if this fails, ``stray`` ends it
    made = [p for p in edits(root) if p not in set(ctx.found)]
    try:
        if moved and result.exit != Exit.STOP:
            result = check.failed(f"the preparer committed (HEAD was {moved[:12]}); its commits were undone")
        elif result.exit == Exit.PENDING and isinstance(payload, tools.CheckRecipe):
            if option := ctx.option(payload.preparation):
                patch = capture(root, made)
                # git apply refuses an empty patch, so one without edits keeps no paths to apply
                _write(store, c.slug, Prepared(check=c.step.task or "", option=option, reason=payload.reason,
                                               paths=made if patch else []), patch)  # fmt: skip
            else:
                for suffix in (".json", ".patch"):
                    _file(store, c.slug, c.step.task or "", suffix).unlink(missing_ok=True)
    except (OSError, subprocess.SubprocessError) as exc:
        result = check.failed(why := f"the preparer's setup edits could not be kept: {failure(exc)}")
        store.log(lock, c.slug, {"event": "setup-edits-not-kept", "at": datetime.now(UTC).isoformat(), "reason": why})
    finally:
        discard(root, made)
        marker.unlink(missing_ok=True)
    return result


def unsafe(settings: Settings, live: Mapping[str, str] | None = None) -> loop.StepResult | None:
    """A missing or refused test copy goes to repair before any check or preparer starts."""
    live = dict(os.environ) if live is None else live
    lead = "Checks cannot run: this project has no safe test copy set up, and Delivery never runs a check on live data"
    if not settings.preparations:
        cause = cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "preparation-missing")
        said = f"{lead}. No test preparation option is declared (TD-96). Delivery will propose one for your approval"
        return loop.StepResult(exit=Exit.RETRY, cause=cause, reason=said, setup=True, operational=True)
    if preparation.safe(settings.preparations, settings.data, live):
        return None
    why = "; ".join(f"{o.id}: {', '.join(preparation.refusals(o, settings.data, live))}" for o in settings.preparations)
    cause = cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "preparation-unsafe")
    said = f"{lead}. No declared test preparation is permitted ({why}) (TD-96). Delivery will propose a permitted one"
    return loop.StepResult(exit=Exit.RETRY, cause=cause, reason=said, setup=True, operational=True)


def refused(store: Store, lock: Lock, c: Change) -> bool:
    """A check with no permitted preparation enters repair instead of starting a preparer."""
    asked = unsafe(store.settings()) if c.step.kind == StepKind.CHECK else None
    if asked:
        store.write(lock, loop.apply(c, asked, datetime.now(UTC)))
    return asked is not None


def stepped(c: Change, *, prepared: bool) -> None:
    """Clicks and typing run only on a prepared test copy (TD-96); without one the step stops.

    Raises:
        PrepareError: a state has steps and the check has no preparation.
    """
    if prepared or not any(s.steps for s in c.brief.visual):
        return
    said = (
        "The visual check has pages it must click or type on, which it does only on a prepared test copy, and this "
        "check has none. Have a test preparation declared for this project, then run the step again"
    )
    detail = "A brief state has steps and the check has no preparation (TD-96): `preparations` in the project settings"
    cause = cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "preparation")
    raise PrepareError(engine.blocked(cause, said, detail))


def reusable(store: Store, c: Change, settings: Settings, live: Mapping[str, str] | None = None) -> bool:
    """Whether the recipe's preparation still holds: the option it chose is declared as it was, and permitted."""
    rec = read(store, c.slug, c.step.task or "")
    if rec is None:
        return False
    now = next((o for o in settings.preparations if o.id == rec.option.id), None)
    live = dict(os.environ) if live is None else live
    return now == rec.option and not preparation.refusals(rec.option, settings.data, live)


def isolated(rec: Prepared, root: Path | None = None) -> dict[str, str]:
    """The explicit environment of restore, seed, cleanup and the launch: the essentials, isolation and snapshot."""
    base = {k: v for k in preparation.BASE if (v := os.environ.get(k)) is not None}
    env = base | rec.option.isolation | ({SNAPSHOT: rec.snapshot} if rec.snapshot else {})
    if root is not None and (home := rec.option.isolation.get("HOME")) and not Path(home).is_absolute():
        at = (root / home).resolve()
        if not at.is_relative_to(root.resolve()):
            raise PrepareError(check.failed(f"preparation HOME {root / home} resolves outside {root} to {at}"))
        if at != root.resolve() / home:
            raise PrepareError(check.failed(f"preparation HOME {root / home} redirects to source directory {at}"))
        env["HOME"] = str(at)
    return env


def environ(store: Store, c: Change) -> dict[str, str] | None:
    """The launch environment of the check's test copy; None when it runs without a preparation."""
    rec = read(store, c.slug, c.env.check) if c.env else None
    return isolated(rec, Path(c.names.worktree)) if rec else None


def due(store: Store, c: Change) -> bool:
    """The check's environment runs on a test copy not yet restored into the Change worktree."""
    e = c.env
    if e is None or e.launched_at is not None or (c.step.kind, c.step.task) != (StepKind.CHECK, e.check):
        return False
    rec = read(store, c.slug, e.check)
    return rec is not None and not rec.ready


def _snapshot(store: Store, slug: str, rec: Prepared, home: Path, log: Log) -> str:
    """Export and mask the live copy once per check; the frozen snapshot's digest is kept, a failed one deleted."""
    if rec.option.kind not in LIVE or rec.digest:
        return ""
    if edited := preparation.named(f"{rec.option.export} {rec.option.masking}", rec.paths, home):
        return f"the export or masking runs {', '.join(edited)}, which the preparer edited; they read live"
    folder = snapshots() / hashlib.sha256(f"{store.root}\0{slug}\0{rec.check}".encode()).hexdigest()[:16]
    shutil.rmtree(folder, ignore_errors=True)  # a kept snapshot of an earlier run
    folder.mkdir(mode=0o700, parents=True)
    rec.snapshot = str(folder)
    _write(store, slug, rec)  # before the export: the end of the check removes even a partial snapshot
    live = dict(os.environ) | {SNAPSHOT: str(folder)}  # export reads live; it is the copy the owner permitted
    note = snapshot_files.command(rec, "export", home, log, live) or snapshot_files.plain(folder)
    note = note or snapshot_files.command(rec, "masking", home, log, live) or snapshot_files.plain(folder)
    if not note and not any(folder.iterdir()):
        note = f"the export wrote nothing into ${SNAPSHOT}"
    if note:  # only a masked snapshot may be kept
        if not snapshot_files.gone(rec.snapshot):
            return f"the unmasked snapshot {folder} could not be deleted; {note}"
        rec.snapshot = ""
        _write(store, slug, rec)
        return note
    rec.digest = snapshot_files.digest(folder)
    _write(store, slug, rec)
    log({"event": "snapshot", "at": datetime.now(UTC).isoformat(), "check": rec.check, "option": rec.option.id})
    return ""


def _into(  # noqa: PLR0913 - the run, its two worktrees and the permissions in force
    store: Store,
    c: Change,
    rec: Prepared,
    root: Path,
    *,
    settings: Settings,
    log: Log,
    keep: bool,
    home: Path | None = None,
) -> str:
    """Restore the frozen snapshot into the test environment, seed it and apply the setup patch in *root*.

    Raises:
        PrepareError: the option is no longer declared as chosen or no longer permitted.
    """
    now = next((o for o in settings.preparations if o.id == rec.option.id), None)
    if now != rec.option:
        raise PrepareError(check.failed(f"the preparation option {rec.option.id} changed since it was chosen"))
    if (why := preparation.refusals(rec.option, settings.data, os.environ)) and (asked := unsafe(settings)):
        raise PrepareError(asked)
    if why:
        raise PrepareError(check.failed(f"the preparation option {rec.option.id} is no longer permitted"))
    rec.open, rec.snapshot_only = True, True
    _write(store, c.slug, rec)
    source = snapshot_owner(store, c.slug, rec)
    if note := _snapshot(store, c.slug, source, home or Path(c.names.worktree), log):
        return note
    if source.snapshot and snapshot_files.digest(Path(source.snapshot)) != source.digest:
        return "the snapshot changed after it was frozen"
    patch = _file(store, c.slug, source.check, ".patch")
    if source.paths and patch.is_file():
        if keep:
            rec.applied = str(root)
            _write(store, c.slug, rec)  # before applying: the end of the check discards even a partial patch
        try:  # before restore and seed, so setup scripts the preparer repaired are the ones they run
            _git(root, "apply", "--binary", str(patch))
        except subprocess.CalledProcessError as exc:
            return f"the setup patch did not apply: {exc.stderr.decode(errors='replace').strip()}"
    env = isolated(source, root)
    rec.snapshot_only = False
    _write(store, c.slug, rec)
    return snapshot_files.command(rec, "restore", root, log, env) or snapshot_files.command(rec, "seed", root, log, env)


def merge_base(store: Store, c: Change, settings: Settings, log: Log) -> Callable[[Path], dict[str, str]]:
    """The "before" capture's preparation of its merge-base worktree; it returns the launch environment."""
    rec = read(store, c.slug, VISUAL)

    def go(root: Path) -> dict[str, str]:
        if rec is None:
            raise PrepareError(check.failed("the check has no test preparation; nothing launches without one"))
        owned = Prepared(
            check=f"before-{VISUAL}",
            option=rec.option,
            home=str(root),
            open=True,
            trial=True,
            snapshot_from=rec.check,
            snapshot_only=True,
        )
        _write(store, c.slug, owned)
        if note := _into(store, c, owned, root, settings=settings, log=log, keep=False):
            raise PrepareError(check.failed(note))
        return isolated(cleanup_record(store, c.slug, owned), root)

    return go


def shaping(store: Store, c: Change, settings: Settings, log: Log) -> Callable[[Path], dict[str, str]]:
    """The shaping capture's test copy in its own checkout, under a check's permissions; a refusal is its reason."""

    def go(root: Path) -> dict[str, str]:
        option = next((o for o in settings.preparations if o.id == c.brief.preparation), None)
        if option is None:
            asked = unsafe(settings)
            said = asked.reason if asked else f"the preparation option {c.brief.preparation} is not declared"
            raise PrepareError(check.failed(said))
        rec = Prepared(check=SHAPING, option=option, home=str(root), trial=True)
        _write(store, c.slug, rec)  # before the export: the next runner ends even a cut-short copy
        if note := _into(store, c, rec, root, settings=settings, log=log, keep=False, home=root):
            raise PrepareError(check.failed(note))
        return isolated(rec, root)

    return go


def launch(store: Store, c: Change, settings: Settings, log: Log) -> loop.StepResult:
    """Prepare the test copy in the Change worktree before the host launches the check there."""
    rec = read(store, c.slug, c.env.check if c.env else "")
    if rec is None:
        return check.failed("the check's preparation is missing")
    try:
        note = _into(store, c, rec, Path(c.names.worktree), settings=settings, log=log, keep=True)
    except (PrepareError, OSError, subprocess.SubprocessError) as exc:
        return exc.result if isinstance(exc, PrepareError) else check.failed(f"test preparation failed: {failure(exc)}")
    if note:
        return check.failed(f"test preparation failed: {note}")
    _write(store, c.slug, rec.model_copy(update={"ready": True}))
    reason = f"test copy {rec.option.id} prepared; starting the check"
    return loop.StepResult(exit=Exit.PENDING, waiting=Waiting.CHECK_START, reason=reason)


def _reapply(store: Store, c: Change, rec: Prepared, home: Path) -> None:
    """Apply the setup patch again for a cleanup that runs without it, unless the worktree edited its paths since."""
    patch = _file(store, c.slug, rec.check, ".patch")
    if rec.applied or not rec.paths or not patch.is_file() or str(home) != c.names.worktree:
        return
    if set(edits(home)) & set(rec.paths):
        return
    rec.applied = str(home)
    _write(store, c.slug, rec)  # before applying: the patch is discarded even when the end is cut short
    try:
        _git(home, "apply", "--binary", str(patch))
    except subprocess.CalledProcessError:
        rec.applied = ""  # Git applies all of a patch or none of it
        _write(store, c.slug, rec)


def _cleanup(rec: Prepared, home: Path, log: Log) -> str:
    try:
        note = snapshot_files.command(rec, "cleanup", home, log, isolated(rec, home))
    except PrepareError as exc:
        return exc.result.reason
    return note


def _dispose_trial(store: Store, slug: str, rec: Prepared, repo: Path) -> bool:
    if not (rec.trial and not rec.open and rec.home):
        return False
    home = Path(rec.home)
    repair_copy.drop(repo, home)
    if home.exists():
        msg = f"the cleaned preparation trial checkout {home} could not be removed"
        raise OSError(msg)
    _write(store, slug, rec.model_copy(update={"home": ""}))
    return True


def end(store: Store, c: Change, repo: Path, settings: Settings, log: Log) -> loop.StepResult | None:
    """End every check whose environment is gone: clean up with its patch applied, discard it, delete its snapshot.

    Cleanup and deletion always run. A patch that cannot be discarded stops the Change, so no setup edit can
    reach a commit (TD-107). A failed cleanup or deletion leaves the run outstanding: the next runner ends it again.
    """
    for rec in cleanup_records(store, c, datetime.now(UTC)):
        if _dispose_trial(store, c.slug, rec, repo):
            continue
        stuck = note = ""
        if rec.home and not Path(rec.home).is_dir() and not rec.trial:
            note = f"its checkout {rec.home} is gone, so its cleanup did not run"
            if not (gone := snapshot_files.gone(rec.snapshot)):  # outstanding: the next end deletes it again
                note += f"; the snapshot {rec.snapshot} could not be deleted"
            log({"event": "prepared-end", "at": datetime.now(UTC).isoformat(), "check": rec.check, "cleanup": note}
                | ({} if gone else {"outstanding": True}))  # fmt: skip
            _write(store, c.slug, rec.model_copy(update={"snapshot": "", "digest": "", "open": False}) if gone else rec)
            continue
        worked = Path(c.names.worktree) if c.names.worktree and Path(c.names.worktree).is_dir() else repo
        home = Path(rec.home) if rec.home else worked
        keep = settings.data.retention == "keep" and bool(rec.digest) and rec.check != SHAPING  # never a shaping copy
        try:
            _reapply(store, c, rec, home)
            note = "" if rec.snapshot_only else _cleanup(cleanup_record(store, c.slug, rec), home, log)
            if not (gone := keep or snapshot_files.gone(rec.snapshot)):
                note = "; ".join(filter(None, [note, f"the snapshot {rec.snapshot} could not be deleted"]))
        finally:
            if rec.applied and Path(rec.applied).is_dir():
                try:
                    discard(Path(rec.applied), rec.paths)
                except (OSError, subprocess.SubprocessError) as exc:
                    stuck = f"the check's setup edits ({', '.join(rec.paths)}) could not be discarded: {failure(exc)}"
        at = datetime.now(UTC)
        log({"event": "prepared-end", "at": at.isoformat(), "check": rec.check, "cleanup": note or "ok"}
            | ({"outstanding": True} if note else {}) | ({"reason": note} if rec.trial and note else {})
            | ({"stuck": stuck} if stuck else {}))  # fmt: skip
        if stuck:
            stop = Stop(kind=ErrorKind.STATE, reason=stuck, action=f"Discard those edits in {rec.applied}",
                        resume="The worktree holds none of them", at=at)  # fmt: skip
            return loop.StepResult(exit=Exit.STOP, reason=stuck, stop=stop)
        update = {"snapshot": rec.snapshot if keep or not gone else "", "applied": "", "ready": False}
        ended = rec.model_copy(update=update | ({} if note else {"digest": "", "open": False}))
        _write(store, c.slug, ended)
        _dispose_trial(store, c.slug, ended, repo)
    return None


def ran(store: Store, lock: Lock, c: Change, repo: Path, *, runnable: bool) -> bool:
    """What preparation owes before any step: a gone check's end, then a due test copy; whether it decided the run."""
    log = partial(store.log, lock, c.slug)
    stray(store, c.slug, log)
    if left(store, c) and not cleanup_records(store, c, datetime.now(UTC)):
        return True
    if left(store, c) and (stop := end(store, c, repo, store.settings(), log)):
        store.write(lock, loop.apply(c, stop, datetime.now(UTC)))
        return True
    if any(rec.trial or rec.snapshot_only for rec in left(store, c)):
        if c.outcome is None or c.outcome.exit == Exit.PENDING:
            c.outcome = Outcome(exit=Exit.RETRY, reason="test-copy cleanup is pending; see its recorded error",
                                at=datetime.now(UTC))  # fmt: skip
        c.outcome.wake_at = datetime.now(UTC) + budgets.PAUSE
        store.write(lock, c)
        return True
    if not runnable or before.due(c) or not due(store, c):  # the "before" capture exports and restores first
        return False
    result, at = launch(store, c, store.settings(), log), datetime.now(UTC)
    if result.exit != Exit.PENDING:  # every such result says why
        c.env = c.recipe = None
        log({"event": "step", "at": at.isoformat(), "kind": c.step.kind, "exit": result.exit, "reason": result.reason})
    store.write(lock, loop.apply(c, result, at))
    return True
