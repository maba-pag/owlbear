"""The Settings page's design pack update (TD-101, TD-220, TD-256): one host job at a time, its stages, its last run.

Stages run in order and the first that fails stops the run with its reason: notice, candidate, diff, golden pages, then
the updater's and the challenger's rounds with the calibration replay (``pack_run``), then the way into ``main``
(``pack_publish``): commit, push, pull request, CI and merge. Until the merge nothing in ``main`` changes, and the
running checkout never does. A run whose rounds or publication need the owner waits for his answers on the Settings
page; its state is kept under the store, so a waiting run survives a host restart. A run the host stopped during
reads as failed, except during publication: it waits for the owner, and trying again reconciles with GitHub first.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from owlbear_delivery_next.change_contracts.round_records import RoundLoop
from owlbear_delivery_next.design_packs import design_pack, pack_git, pack_update
from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.pack_runs import pack_candidate, pack_gates, pack_publish, pack_replay, pack_rounds, pack_run
from owlbear_delivery_next.pack_runs.machine_lock import HeldError, take
from owlbear_delivery_next.pack_runs.pack_run import CANDIDATE, UPDATER, Stopped
from owlbear_delivery_next.pack_runs.pack_state import (
    FILE,
    HOST_STOPPED,
    LOG,
    MACHINE_LOCK,
    OPEN,
    RUNS,
    STAGES,
    last,
    legacy_uncertain,  # noqa: F401 - retain the existing pack_job ownership-reader API
    observed,  # noqa: F401 - the unloaded ownership reader session_slots shares with Job
    read_only,  # noqa: F401 - retain the existing pack_job ownership-reader API
    read_version,
    running_for,
    version_of,
)
from owlbear_delivery_next.pack_runs.pack_state import (
    blank as _blank,
)
from owlbear_delivery_next.pack_runs.pack_state import (
    describe as _pack,
)
from owlbear_delivery_next.pack_runs.pack_state import (
    interrupted as _interrupted,
)
from owlbear_delivery_next.pack_runs.pack_state import (
    now as _now,
)
from owlbear_delivery_next.workflow_steps import sessions

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from owlbear_delivery_next.design_packs.calibration import Replay
    from owlbear_delivery_next.github.provider import Provider
    from owlbear_delivery_next.local_system.maintenance import Maintenance
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store

__all__ = ["CANDIDATE", "FILE", "STAGES", "Busy", "Job", "Live", "Refused", "Stale", "Stopped", "last", "running_for"]


class Busy(Exception):  # noqa: N818 - the route's answer, not a fault
    """An update is already running, or waits for the owner."""


class Stale(Exception):  # noqa: N818 - the route's answer, not a fault
    """The answer is to no open question of a waiting run."""


class Refused(Exception):  # noqa: N818 - the route's answer, not a fault
    """The answer cannot be carried out as given."""


def _upstream() -> Path:
    return design_pack.folder().parent / "upstream"  # beside the packs, outside every project


class Replays(Protocol):
    """The calibration replay: its candidate's session runs under *run*, and *keep* holds its scratch directory."""

    def __call__(
        self,
        store: Store,
        candidate: pack_candidate.Candidate | None,
        run: Callable[[Session], Run] | None = None,
        *,
        keep: Callable[[Path], bool] | None = None,
    ) -> Replay: ...


@dataclass
class Live:
    """What reaches outside: upstream, downloads, the browser, model sessions and git. Tests replace each."""

    package: Path = field(default_factory=lambda: Path(str(files("owlbear_delivery_next"))))
    clone: Path = field(default_factory=_upstream)
    releases: Callable[[str], bytes] | None = None  # the notice's release list; None reads GitHub
    sync: Callable[[Path, str], None] = pack_candidate.sync
    download: Callable[[str], bytes] = design_pack.fetch
    golden: Callable[..., dict[str, dict[str, list[str]]]] = pack_update.golden  # (installed, folder=None)
    replay: Replays = pack_replay.replay
    challenge: Callable[[Store, Session], Run] = sessions.run
    update: Callable[[Store, Session], Run] = sessions.run  # the writing updater (TD-125)
    git: pack_git.Git = pack_git.git
    github: Callable[[Path], Provider] = GhProvider
    sleep: Callable[[float], None] = time.sleep
    poll: float = 30.0  # seconds between looks at the pull request's checks
    ci_wait: float = 3600.0  # seconds CI may take at one head before the owner is asked


class Job:
    """The project's design pack update: start one, answer it, read its state."""

    def __init__(self, store: Store, live: Live | None = None) -> None:
        """Read the last run; one the host stopped during reads as failed, one waiting for the owner still waits."""
        self.store, self.live, self.lock = store, live or Live(), threading.Lock()
        self.thread: threading.Thread | None = None
        self.held: int | None = None
        self.maintenance: Maintenance | None = None  # bound by session_slots.packed; without it nothing is removed
        self.interrupted: dict[str, str] | None = None  # a run the last host left running; its SDK stage may still work
        self.replays = 0
        self.version = ""  # the run file's identity as read; see _read
        self.state = self._read()
        if self.state["state"] == "running" and (self.state.get("context") or {}).get("publication"):
            reason = "the host stopped while the update was being published"
            self._hold(pack_run.Context.model_validate(self.state["context"]), reason)
        elif self.state["state"] == "running":
            self.interrupted = _interrupted(self.state, self.version)  # its identity before this rewrite, carried in it
            # keeps the workspace: nothing is bound to say whether an uncertain session still uses it
            self._finish("failed", HOST_STOPPED, keep=True)  # records the rewrite's own identity as self.version

    @property
    def path(self) -> Path:
        """Where the last run is kept."""
        return self.store.root / FILE

    @property
    def workspace(self) -> Path:
        """The current run's updater repository; a run from before per-run workspaces keeps the shared root."""
        kept = self.state.get("workspace")
        return Path(kept) if kept else self.store.root / UPDATER

    def keeps(self, path: Path) -> bool:
        """Whether the ledger holds *path*'s session, so its scratch directory must outlive the call."""
        return self.maintenance is not None and self.maintenance.retained(str(path))

    def _read(self) -> dict[str, Any]:
        """The last run, and its file version from the same descriptor: "absent", "" when unreadable."""
        state, self.version = read_version(self.path)
        return state

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.version = version_of(atomic_write(self.path, json.dumps(self.state, indent=1) + "\n"))

    def read(self) -> dict[str, Any]:
        """The current or last run, as the page shows it: without the run's context."""
        with self.lock:
            return self._copy()

    def _copy(self) -> dict[str, Any]:
        return json.loads(json.dumps({k: v for k, v in self.state.items() if k != "context"}))

    def busy(self) -> bool:
        """Whether an update's thread or a tracked calibration replay runs now."""
        return self.replays > 0 or (self.thread is not None and self.thread.is_alive())

    def count_replay(self, delta: int) -> None:
        """Count a calibration replay in (+1) or out (-1), so a stop waits for it and no update starts beside it."""
        with self.lock:
            self.replays += delta

    def start(self) -> dict[str, Any]:
        """Start a run on its own thread and return its first state.

        Raises:
            Busy: A run is in progress, or waits for the owner's answers.
        """
        with self.lock:
            if self.state["state"] == "running" or self.busy():
                msg = "a design pack update is already running"
                raise Busy(msg)
            if self.state["state"] == "waiting":
                msg = "a design pack update waits for your answers; answer or discard it first"
                raise Busy(msg)
            self._claim()
            run = uuid.uuid4().hex
            self.state = _blank() | {
                "state": "running", "started_at": _now(), "run": run,
                "workspace": str(self.store.root / RUNS / run),
            }  # fmt: skip
            self._save()
            self.thread = threading.Thread(
                target=self._run, args=(self._stages,), name="design-pack-update", daemon=True
            )
        self.thread.start()
        return self.read()

    def answer(self, question: str, option: str, note: str = "") -> dict[str, Any]:
        """Carry out the owner's answer to one open question; once none is open, the run goes on.

        Raises:
            Stale: No waiting run asks this question, or the run is still settling.
            Refused: The option is not one of the question's, or a reconsideration lacks its note.
        """
        with self.lock:
            asked = self.state["questions"] if self.state["state"] == "waiting" and not self.busy() else []
            q = next((q for q in asked if q["id"] == question), None)
            if q is None:
                msg = "this question is no longer open; reload the page"
                raise Stale(msg)
            if option not in {o["id"] for o in q["options"]}:
                msg = f"{option!r} is no answer to this question"
                raise Refused(msg)
            if option == pack_rounds.RECONSIDER and not note.strip():
                msg = "asking the challenger to reconsider needs your note"
                raise Refused(msg)
            said = f"you answered {q['kind']} {q.get('finding', '')}: {pack_rounds.LABELS[option]}".replace("  ", " ")
            if option == pack_rounds.DISCARD:
                self._log(said)
                self._finish("discarded", "discarded by you; nothing changed")
                return self._copy()
            ctx = pack_run.Context.model_validate(self.state["context"])
            lp = RoundLoop.model_validate(self.state["loop"])
            left = _decided(self.state["questions"], q, option, note=note, ctx=ctx, lp=lp)
            if not left:
                self._claim()  # before anything changes: a refusal leaves the question open
            self._log(said)
            self.state |= {"loop": lp.model_dump(mode="json"), "context": ctx.model_dump(mode="json")}
            self.state["questions"] = left
            if not left:
                self.state["state"] = "running"
                self.thread = threading.Thread(
                    target=self._run, args=(self._resume,), name="design-pack-update", daemon=True
                )
            self._save()
            resumed = self.thread if not left else None
        if resumed is not None:
            resumed.start()
        return self.read()

    def discard(self) -> dict[str, Any]:
        """End a waiting run without activating anything.

        Raises:
            Stale: No run waits for the owner.
        """
        with self.lock:
            if self.state["state"] != "waiting" or self.busy():
                msg = "no design pack update waits for you"
                raise Stale(msg)
            self._log("you discarded the update")
            self._finish("discarded", "discarded by you; nothing changed")
            return self._copy()

    def log(self, line: str) -> None:
        """One line of the run's log, kept with its state."""
        with self.lock:
            self._log(line)
            self._save()

    def _log(self, line: str) -> None:
        self.state["log"] = [*self.state["log"], f"{_now()} {line}"][-LOG:]

    def stage(self, name: str, result: str, detail: str = "") -> None:
        """One stage's result, shown on the page and logged."""
        with self.lock:
            stage = next(s for s in self.state["stages"] if s["name"] == name)
            stage["result"], stage["detail"] = result, detail[:4000]
            self.state["stage"] = name if result == "running" else self.state["stage"]
            self._save()
        self.log(f"{name}: {result}{f': {detail.splitlines()[0][:300]}' if detail else ''}")

    def keep(self, ctx: pack_run.Context, lp: RoundLoop) -> None:
        """Keep the run's context and loop, so it goes on from here."""
        with self.lock:
            self.state |= {"context": ctx.model_dump(mode="json"), "loop": lp.model_dump(mode="json")}
            self._save()

    def wait(
        self, ctx: pack_run.Context, lp: RoundLoop, questions: list[dict[str, Any]], stage: str = "challenger"
    ) -> None:
        """Stop the run for the owner's answers; it goes on when he has answered every question."""
        with self.lock:
            ctx.next = "wait"
            self.state |= {"state": "waiting", "stage": "", "questions": questions}
            self.state |= {"context": ctx.model_dump(mode="json"), "loop": lp.model_dump(mode="json")}
            next(s for s in self.state["stages"] if s["name"] == stage)["result"] = "waiting"
            self._log(f"waiting for you: {len(questions)} question(s)")
            self._save()

    def hold(self, ctx: pack_run.Context, reason: str) -> None:
        """Publication stopped: the owner tries again once he fixed what stopped it, or discards the update."""
        with self.lock:
            self._hold(ctx, reason)

    def _hold(self, ctx: pack_run.Context, reason: str) -> None:
        pub = ctx.publication
        link = f" ({pub.url})" if pub and pub.url else ""
        question = {"id": f"{self.state['run']}-publish", "kind": "publish", "text": f"{reason}{link}",
                    "options": [{"id": o, "label": pack_rounds.LABELS[o]} for o in pack_rounds.PUBLISH]}  # fmt: skip
        ctx.next = "wait"
        stage = next((s for s in self.state["stages"] if s["result"] in {"running", "failed"}), None)
        if stage is not None:
            stage["result"], stage["detail"] = "waiting", reason[:4000]
        self.state |= {"state": "waiting", "stage": "", "questions": [question], "reason": reason}
        self.state["context"] = ctx.model_dump(mode="json")
        self._log(f"waiting for you: {reason}")
        self._save()

    def published(self, pub: pack_publish.Publication) -> None:
        """Record how far the update got on its way into ``main``, with the run's context, so a retry goes on."""
        with self.lock:
            self.state["published"] = pub.model_dump(exclude={"root", "body"})
            if self.state.get("context"):
                self.state["context"]["publication"] = pub.model_dump(mode="json")
            self._save()

    def _end(self, state: str, reason: str) -> None:
        with self.lock:
            self._finish(state, reason)

    def _finish(self, state: str, reason: str, *, keep: bool = False) -> None:
        for s in self.state["stages"]:
            if s["result"] in OPEN:
                s["result"] = "failed" if s["result"] == "running" and state == "failed" else "skipped"
        self.state |= {"state": state, "stage": "", "ended_at": _now(), "reason": reason, "questions": []}
        self.state["context"] = None
        if not keep and self._removable(self.workspace):
            shutil.rmtree(self.workspace, ignore_errors=True)
        self._save()

    def _removable(self, workspace: Path) -> bool:
        """A workspace goes unless the ledger keeps it; without a ledger only the legacy shared root is kept."""
        if self.maintenance is None:
            return workspace != self.store.root / UPDATER
        return not self.maintenance.retained(str(workspace))

    def _claim(self) -> None:
        """Take the machine's one pack lock for the run's thread; the pack is shared by every project.

        Raises:
            Busy: Another project's update runs now, or an earlier pack session is still unproven.
        """
        self._unproven()
        try:
            # Verified again while the lock is held: an earlier updater may have released it unconfirmed before this.
            self.held = take(
                local_home.root() / MACHINE_LOCK, self.store.name or self.store.root.parent.parent.name, self._unproven,
            )  # fmt: skip
        except HeldError as exc:
            msg = f"a design pack update runs for {exc.who}; one runs at a time on this machine"
            raise Busy(msg) from None

    def _unproven(self) -> None:
        if self.maintenance is not None and self.maintenance.pending(kind="pack"):
            msg = "an earlier design pack session is unproven; recover it on the Maintenance page first"
            raise Busy(msg)

    def _run(self, work: Callable[[], str | None]) -> None:
        try:
            self._steps(work)
        finally:
            self._release()

    def _release(self) -> None:
        with self.lock:  # the close and the clear are one step, so a successor's claim is never erased
            if self.held is not None:
                os.close(self.held)
                self.held = None

    @contextlib.contextmanager
    def exclusive(self) -> Iterator[None]:
        """Hold the machine's pack claim while a manual replay runs, as an update does; uncertain pack work refuses it.

        Raises:
            Busy: An update runs or waits, another project holds the machine's claim, or a pack session is unproven.
        """
        with self.lock:
            if self.busy() or self.state["state"] in ("running", "waiting"):
                msg = "a design pack update is running or waits for answers: finish it before a replay"
                raise Busy(msg)
            self._claim()
        try:
            yield
        finally:
            self._release()

    def _steps(self, work: Callable[[], str | None]) -> None:
        try:
            reason = work()
        except Stopped as exc:
            self.log(exc.reason)
            self._end("up-to-date" if exc.current else "failed", exc.reason)
        except Exception as exc:  # noqa: BLE001 - the page must learn how the run ended
            reason = f"{type(exc).__name__}: {exc}"[:600]
            self.log(reason)
            self._end("failed", reason)
        else:
            if reason is not None:  # None: the run waits for the owner
                self._end("passed", reason)

    def do[T](
        self, name: str, work: Callable[[], T], said: Callable[[T], str] = str, hold: type[Exception] | None = None
    ) -> T:
        """Run one stage's work: its result shown, any failure ending the run with the stage named.

        A failure of the *hold* kind is raised as it is, for the owner to decide.
        """
        self.stage(name, "running")
        try:
            out = work()
        except Stopped as exc:
            self.stage(name, "passed" if exc.current else "failed", exc.reason)
            raise
        except Exception as exc:
            if hold is not None and isinstance(exc, hold):
                self.stage(name, "failed", str(exc))
                raise
            reason = f"{name}: {type(exc).__name__}: {exc}"[:2000]  # any failure stops the run, its stage named
            self.stage(name, "failed", reason)
            raise Stopped(reason) from exc
        self.stage(name, "passed", said(out))
        return out

    def _stages(self) -> str | None:
        live, store = self.live, self.store
        package = live.package.resolve()
        old = json.loads((package / pack_candidate.MANIFEST).read_text(encoding="utf-8"))
        tag = self.do("notice", self._notice)

        def candidate() -> tuple[pack_git.Source, pack_candidate.Candidate]:
            src = pack_git.source(package, live.git)  # before any download: a checkout that cannot publish stops
            pack_publish.preflight(live.github(src.root), src.repository)
            live.sync(live.clone, old["upstream"]["repository"])
            folder = store.root / CANDIDATE  # kept after the run, so the owner can read what was judged
            shutil.rmtree(folder, ignore_errors=True)
            return src, pack_candidate.prepare(live.clone, package, tag, live.download, folder)

        src, c = self.do("candidate", candidate, lambda out: _pack(*out))
        diff = self.do("diff", lambda: pack_update.diff(live.clone, tag))
        golden = self.do("golden", lambda: pack_gates.checked(live.golden(c.installed)))  # the updater's evidence
        why = f"design pack: {old['pack']} to {c.pins['pack']} (upstream {old['upstream']['tag']} to {tag})"
        return pack_run.begin(self, c, src, diff=diff, golden=golden, why=why)

    def _resume(self) -> str | None:
        with self.lock:
            ctx = pack_run.Context.model_validate(self.state["context"])
            lp = RoundLoop.model_validate(self.state["loop"])
        if ctx.publication and ctx.publication.commit:  # GitHub first: the package may have moved on meanwhile
            return pack_run.republish(self, ctx)
        return pack_run.advance(self, pack_run.rebuilt(self, ctx), ctx, lp)

    def _notice(self) -> str:
        found = pack_update.newer(self.live.releases)
        if found is None:
            msg = "upstream's releases could not be read; try again when online"
            raise Stopped(msg)
        if not found:
            msg = f"up to date: no skill release newer than {design_pack.manifest()['upstream']['tag']}"
            raise Stopped(msg, current=True)
        return found[-1]


def _decided(  # noqa: PLR0913 - the open questions, the answered one, the answer and what it changes
    asked: list[dict[str, Any]], q: dict[str, Any], option: str, *, note: str, ctx: pack_run.Context, lp: RoundLoop
) -> list[dict[str, Any]]:
    """Record one answer; the questions still open. The last dispute answer sets what the run does next."""
    if q["kind"] == "dispute":
        pack_rounds.decided(lp, q["finding"], option, note)
        left = [x for x in asked if x["id"] != q["id"]]
        if not left:  # TD-193: the answers are carried out together
            ctx.next = pack_run.NEXT[pack_rounds.after(lp)]
        return left
    if q["kind"] == "publish":  # trying again reconciles with GitHub before anything is repeated
        ctx.next = "activate"
        return []
    if q["kind"] in pack_gates.KINDS:
        return pack_run.gated(asked, q, option, ctx, lp)
    if option == pack_rounds.ANOTHER:
        lp.extra, lp.ended, ctx.next = lp.extra + 1, "", "challenge"
    else:
        lp.ended, ctx.accepted, ctx.next = lp.ended, q["identity"], "activate"
    return []
