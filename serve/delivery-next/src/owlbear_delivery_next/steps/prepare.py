"""TD-96, TD-107: run a check's chosen test preparation and keep the preparer's setup edits as a patch.

Per check, a live copy is exported and masked once into a frozen snapshot outside every repository. Before the
"before" capture and again before the host launches the check, that same snapshot is restored into the isolated test
environment, test data is seeded and the preparer's setup patch applied. The end of the check discards the patch,
runs the cleanup command and deletes the snapshot unless the owner keeps it. Restore, seed, cleanup and the launch
run with the option's isolation; only export and masking see Delivery's own environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field

from owlbear_delivery_next import loop, preparation, tools
from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.models import VISUAL, ErrorKind, Exit, Option, Record, StepKind, Stop, Waiting
from owlbear_delivery_next.preparation import LIVE, SNAPSHOT, Preparation
from owlbear_delivery_next.steps import before, check, engine, worktree
from owlbear_delivery_next.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from owlbear_delivery_next.config import Settings
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.store import Lock, Store

type Log = Callable[[dict[str, Any]], None]
SESSION = "session.open"  # a running preparer session's root and the edits it found (JSON)


class Prepared(Record):
    """One check's chosen preparation and the preparer's setup edits, kept with its recipe; and its current run."""

    check: str
    option: Preparation  # as validated when chosen; it runs as chosen while it is still declared so
    reason: str = ""
    paths: list[str] = Field(default_factory=list)  # the setup files the patch changes (TD-107)
    snapshot: str = ""  # this run's frozen snapshot, outside the repository
    digest: str = ""  # the snapshot's content once masked; every restore checks it
    applied: str = ""  # the worktree the patch is applied to now
    ready: bool = False  # restored into the Change worktree for this launch
    open: bool = False  # this run may have left what the end of the check removes


class PrepareError(Exception):
    """The check cannot start on a test copy; its result says why."""

    def __init__(self, result: loop.StepResult) -> None:
        super().__init__(result.reason)
        self.result = result


def snapshots() -> Path:
    """Delivery's snapshot folder, beside its worktrees and outside every repository."""
    return worktree.data_root().parent / "snapshots"


def _dir(store: Store, slug: str) -> Path:
    return store.root / "changes" / slug / "prepare"


def _file(store: Store, slug: str, check_id: str, suffix: str) -> Path:
    return _dir(store, slug) / f"{hashlib.sha256(check_id.encode()).hexdigest()[:16]}{suffix}"


def read(store: Store, slug: str, check_id: str) -> Prepared | None:
    """The preparation the check *check_id* last chose, if any."""
    path = _file(store, slug, check_id, ".json")
    return Prepared.model_validate_json(path.read_text()) if path.is_file() else None


def _records(store: Store, slug: str) -> list[Prepared]:
    folder = _dir(store, slug)
    found = sorted(folder.glob("*.json")) if folder.is_dir() else []
    return [Prepared.model_validate_json(p.read_text()) for p in found]


def _write(store: Store, slug: str, rec: Prepared, patch: bytes | None = None) -> None:
    _dir(store, slug).mkdir(mode=0o700, parents=True, exist_ok=True)
    if patch is not None:
        path = _file(store, slug, rec.check, ".patch")
        path.with_suffix(".tmp").write_bytes(patch)
        path.with_suffix(".tmp").replace(path)
    atomic_write(_file(store, slug, rec.check, ".json"), rec.model_dump_json())


def _git(root: Path, *args: str, env: Mapping[str, str] | None = None) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=root, capture_output=True, check=True, timeout=60, env=env
    ).stdout


def edits(root: Path) -> list[str]:
    """Every uncommitted path of the worktree, both ends of a staged rename, each name as Git wrote it."""
    fields = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").decode().split("\0")
    paths, i = [], 0
    while i < len(fields) and fields[i]:
        paths.append(fields[i][3:])
        if fields[i][0] in {"R", "C"}:
            i += 1
            paths.append(fields[i])
        i += 1
    return paths


def capture(root: Path, paths: Sequence[str]) -> bytes:
    """The edits of *paths* against HEAD as one binary patch, staged in a private index; the worktree's is untouched."""
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ | {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        _git(root, "read-tree", "HEAD", env=env)
        _git(root, "--literal-pathspecs", "add", "--all", "--", *paths, env=env)
        return _git(root, "diff", "--cached", "--binary", "HEAD", env=env)


def discard(root: Path, paths: Sequence[str]) -> None:
    """Return *paths* to HEAD: tracked ones checked out, new ones removed; nothing else is touched."""
    if not paths:
        return
    _git(root, "--literal-pathspecs", "reset", "-q", "HEAD", "--", *paths)
    tracked = set(_git(root, "--literal-pathspecs", "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", *paths)
                  .decode().split("\0")) - {""}  # fmt: skip
    if tracked:
        _git(root, "--literal-pathspecs", "checkout", "HEAD", "--", *sorted(tracked))
    for p in set(paths) - tracked:
        (root / p).unlink(missing_ok=True)


def context(store: Store, c: Change, settings: Settings, root: Path) -> preparation.Preparing:
    """What a preparer's recipe is validated against, with the HEAD and the edits its session starts from.

    The edits are kept on disk too, so the preparer's own are discarded even when its runner dies (``stray``).
    """
    found = edits(root)
    _dir(store, c.slug).mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write(_dir(store, c.slug) / SESSION, json.dumps({"root": str(root), "found": found}))
    return preparation.Preparing(tuple(settings.preparations), settings.data, worktree.head(root), tuple(found))


def stray(store: Store, slug: str, log: Log) -> None:
    """Discard the edits of a preparer session whose runner ended before ``chosen`` (TD-107)."""
    marker = _dir(store, slug) / SESSION
    if not marker.is_file():
        return
    started = json.loads(marker.read_text())
    if (root := Path(started["root"])).is_dir():
        made = [p for p in edits(root) if p not in set(started["found"])]
        discard(root, made)
        log({"event": "prepared-stray", "at": datetime.now(UTC).isoformat(), "discarded": made[:20]})
    marker.unlink()


def chosen(  # noqa: PLR0913, PLR0917 - the session's end, its worktree and what it started from
    store: Store, c: Change, root: Path, payload: tools.Args | None, ctx: preparation.Preparing, result: loop.StepResult
) -> loop.StepResult:
    """End a preparer session: keep an accepted recipe's option and setup edits as its patch, then discard every edit.

    The preparer's edits never stay in the worktree, accepted or not (TD-107); edits it found there stay.
    """
    made = [p for p in edits(root) if p not in set(ctx.found)]
    try:
        if result.exit == Exit.PENDING and isinstance(payload, tools.CheckRecipe):
            if option := ctx.option(payload.preparation):
                patch = capture(root, made) if made else b""
                _write(store, c.slug, Prepared(check=c.step.task or "", option=option, reason=payload.reason,
                                               paths=made), patch)  # fmt: skip
            else:
                for suffix in (".json", ".patch"):
                    _file(store, c.slug, c.step.task or "", suffix).unlink(missing_ok=True)
    except (OSError, subprocess.SubprocessError) as exc:
        result = check.failed(f"the preparer's setup edits could not be kept: {exc}"[:300])
    finally:
        discard(root, made)
        (_dir(store, c.slug) / SESSION).unlink(missing_ok=True)
    return result


def unsafe(settings: Settings, live: Mapping[str, str] | None = None) -> loop.StepResult | None:
    """No declared option is permitted, so a check would run on live data: the owner decides; nothing runs."""
    live = dict(os.environ) if live is None else live
    if not settings.preparations or preparation.safe(settings.preparations, settings.data, live):
        return None
    why = "; ".join(f"{o.id}: {', '.join(preparation.refusals(o, settings.data, live))}" for o in settings.preparations)
    text = (
        f"No declared test preparation is permitted ({why}), and a check never runs on live data (TD-96). Change "
        "the project's preparation options or data permissions in its settings, then continue."
    )
    cause = cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "preparation-unsafe")
    return engine.ask(StepKind.CHECK, text[:1500], cause, engine.continue_or_pause(StepKind.CHECK))


def refused(store: Store, lock: Lock, c: Change) -> bool:
    """A check step with no permitted preparation asks the owner instead of starting a preparer."""
    asked = unsafe(store.settings()) if c.step.kind == StepKind.CHECK else None
    if asked:
        store.write(lock, loop.apply(c, asked, datetime.now(UTC)))
    return asked is not None


def stepped(c: Change, *, prepared: bool) -> None:
    """Clicks and typing run only on a prepared test copy (TD-96); without one the owner decides.

    Raises:
        PrepareError: a state has steps and the check has no preparation.
    """
    if prepared or not any(s.steps for s in c.brief.visual):
        return
    text = (
        "The visual check has states with clicks or typing, which run only on a prepared test copy (TD-96), and "
        "this check has none. Declare a preparation option in the project settings, or revise the brief's states."
    )
    options = [
        Option(id="done", label="Preparation declared, prepare again", next=StepKind.CHECK),
        Option(id="brief", label="Revise the brief", next=StepKind.SHAPE),
        Option(id="pause", label="Pause", next="pause"),
    ]
    cause = cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "preparation")
    raise PrepareError(engine.ask(StepKind.CHECK, text, cause, options))


def reusable(store: Store, c: Change, settings: Settings, live: Mapping[str, str] | None = None) -> bool:
    """Whether the recipe's preparation still holds: the option it chose is declared as it was, and permitted."""
    rec = read(store, c.slug, c.step.task or "")
    if rec is None:
        return not settings.preparations
    now = next((o for o in settings.preparations if o.id == rec.option.id), None)
    live = dict(os.environ) if live is None else live
    return now == rec.option and not preparation.refusals(rec.option, settings.data, live)


def isolated(rec: Prepared) -> dict[str, str]:
    """The environment of restore, seed, cleanup and the launch: the option's isolation and the snapshot."""
    return dict(os.environ) | rec.option.isolation | ({SNAPSHOT: rec.snapshot} if rec.snapshot else {})


def environ(store: Store, c: Change) -> dict[str, str] | None:
    """The launch environment of the check's test copy; None when it runs without a preparation."""
    rec = read(store, c.slug, c.env.check) if c.env else None
    return isolated(rec) if rec else None


def due(store: Store, c: Change) -> bool:
    """The check's environment runs on a test copy not yet restored into the Change worktree."""
    e = c.env
    if e is None or e.launched_at is not None or (c.step.kind, c.step.task) != (StepKind.CHECK, e.check):
        return False
    rec = read(store, c.slug, e.check)
    return rec is not None and not rec.ready


def _digest(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        h.update(str(p.relative_to(folder)).encode() + b"\0")
        if p.is_symlink():
            h.update(str(p.readlink()).encode())
        elif p.is_file():
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def _command(rec: Prepared, name: str, root: Path, log: Log, env: Mapping[str, str]) -> str:
    cmd = getattr(rec.option, name)
    return f"the {name} command {note}" if cmd and (note := check.run(shlex.split(cmd), root, log, env)) else ""


def _snapshot(store: Store, slug: str, rec: Prepared, home: Path, log: Log) -> str:
    """Export and mask the live copy once per check; the frozen snapshot's digest is kept."""
    if rec.option.kind not in LIVE or rec.digest:
        return ""
    folder = snapshots() / hashlib.sha256(f"{store.root}\0{slug}\0{rec.check}".encode()).hexdigest()[:16]
    shutil.rmtree(folder, ignore_errors=True)  # a kept snapshot of an earlier run
    folder.mkdir(mode=0o700, parents=True)
    rec.snapshot = str(folder)
    _write(store, slug, rec)  # before the export: the end of the check removes even a partial snapshot
    live = dict(os.environ) | {SNAPSHOT: str(folder)}  # export reads live; it is the copy the owner permitted
    if note := _command(rec, "export", home, log, live) or _command(rec, "masking", home, log, live):
        return note
    if not any(folder.iterdir()):
        return f"the export wrote nothing into ${SNAPSHOT}"
    rec.digest = _digest(folder)
    _write(store, slug, rec)
    log({"event": "snapshot", "at": datetime.now(UTC).isoformat(), "check": rec.check, "option": rec.option.id})
    return ""


def _into(  # noqa: PLR0913 - the run, its two worktrees and the permissions in force
    store: Store, c: Change, rec: Prepared, root: Path, *, settings: Settings, log: Log, keep: bool
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
    rec.open = True
    _write(store, c.slug, rec)
    if note := _snapshot(store, c.slug, rec, Path(c.names.worktree), log):
        return note
    if rec.snapshot and _digest(Path(rec.snapshot)) != rec.digest:
        return "the snapshot changed after it was frozen"
    patch = _file(store, c.slug, rec.check, ".patch")
    if rec.paths and patch.is_file():
        if keep:
            rec.applied = str(root)
            _write(store, c.slug, rec)  # before applying: the end of the check discards even a partial patch
        try:
            _git(root, "apply", "--binary", str(patch))
        except subprocess.CalledProcessError as exc:
            return f"the setup patch did not apply: {exc.stderr.decode(errors='replace').strip()[:200]}"
    env = isolated(rec)
    return _command(rec, "restore", root, log, env) or _command(rec, "seed", root, log, env)


def merge_base(store: Store, c: Change, settings: Settings, log: Log) -> Callable[[Path], dict[str, str]] | None:
    """The "before" capture's preparation of its merge-base worktree; it returns the launch environment."""
    rec = read(store, c.slug, VISUAL)
    if rec is None:
        return None

    def go(root: Path) -> dict[str, str]:
        if note := _into(store, c, rec, root, settings=settings, log=log, keep=False):
            raise PrepareError(check.failed(note))
        return isolated(rec)

    return go


def launch(store: Store, c: Change, settings: Settings, log: Log) -> loop.StepResult:
    """Prepare the test copy in the Change worktree before the host launches the check there."""
    rec = read(store, c.slug, c.env.check if c.env else "")
    if rec is None:
        return check.failed("the check's preparation is missing")
    try:
        note = _into(store, c, rec, Path(c.names.worktree), settings=settings, log=log, keep=True)
    except (PrepareError, OSError, subprocess.SubprocessError) as exc:
        return exc.result if isinstance(exc, PrepareError) else check.failed(f"test preparation failed: {exc}"[:300])
    if note:
        return check.failed(f"test preparation failed: {note}"[:300])
    _write(store, c.slug, rec.model_copy(update={"ready": True}))
    reason = f"test copy {rec.option.id} prepared; starting the check"
    return loop.StepResult(exit=Exit.PENDING, waiting=Waiting.CHECK_START, reason=reason)


def left(store: Store, c: Change) -> list[Prepared]:
    """Runs whose check environment is gone: the end of their check is still to run."""
    current = c.env.check if c.env else None
    return [r for r in _records(store, c.slug) if r.open and r.check != current]


def end(store: Store, c: Change, repo: Path, settings: Settings, log: Log) -> loop.StepResult | None:
    """End every check whose environment is gone: discard its patch, clean up, delete its snapshot.

    Cleanup and deletion always run. A patch that cannot be discarded stops the Change, so no setup edit can
    reach a commit (TD-107).
    """
    for rec in left(store, c):
        stuck = ""
        if rec.applied and Path(rec.applied).is_dir():
            try:
                discard(Path(rec.applied), rec.paths)
            except (OSError, subprocess.SubprocessError) as exc:
                stuck = f"the check's setup edits ({', '.join(rec.paths[:5])}) could not be discarded: {exc}"[:300]
        home = Path(c.names.worktree) if c.names.worktree and Path(c.names.worktree).is_dir() else repo
        note = _command(rec, "cleanup", home, log, isolated(rec))
        keep = settings.data.retention == "keep"
        if rec.snapshot and not keep:
            shutil.rmtree(rec.snapshot, ignore_errors=True)
        at = datetime.now(UTC)
        log({"event": "prepared-end", "at": at.isoformat(), "check": rec.check, "cleanup": note or "ok"})
        if stuck:
            stop = Stop(kind=ErrorKind.STATE, reason=stuck, action=f"Discard those edits in {rec.applied}",
                        resume="The worktree holds none of them", at=at)  # fmt: skip
            return loop.StepResult(exit=Exit.STOP, reason=stuck, stop=stop)
        update = {"snapshot": rec.snapshot if keep else "", "digest": "", "applied": "", "ready": False, "open": False}
        _write(store, c.slug, rec.model_copy(update=update))
    return None


def ran(store: Store, lock: Lock, c: Change, repo: Path, *, runnable: bool) -> bool:
    """What preparation owes before any step: a gone check's end, then a due test copy; whether it decided the run."""
    log = partial(store.log, lock, c.slug)
    stray(store, c.slug, log)
    if left(store, c) and (stop := end(store, c, repo, store.settings(), log)):
        store.write(lock, loop.apply(c, stop, datetime.now(UTC)))
        return True
    if not runnable or before.due(c) or not due(store, c):  # the "before" capture exports and restores first
        return False
    result = launch(store, c, store.settings(), log)
    if result.exit != Exit.PENDING:
        c.env = c.recipe = None
    store.write(lock, loop.apply(c, result, datetime.now(UTC)))
    return True
