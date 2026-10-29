"""The Settings page's Impeccable update (TD-101, TD-220, TD-256): one host job at a time, its stages, its last run.

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
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.round_records import RoundLoop
from owlbear_delivery_next.impeccable import pack_files, pack_git, pack_update
from owlbear_delivery_next.impeccable_runs import (
    pack_activation,
    pack_admission,
    pack_candidate,
    pack_gates,
    pack_progress,
    pack_publish,
    pack_repair,
    pack_rounds,
    pack_run,
)
from owlbear_delivery_next.impeccable_runs.machine_lock import HeldError, take
from owlbear_delivery_next.impeccable_runs.pack_live import Live
from owlbear_delivery_next.impeccable_runs.pack_run import CANDIDATE, UPDATER, Stopped
from owlbear_delivery_next.impeccable_runs.pack_state import (
    FILE,
    HOST_STOPPED,
    MACHINE_LOCK,
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
from owlbear_delivery_next.impeccable_runs.pack_state import (
    blank as _blank,
)
from owlbear_delivery_next.impeccable_runs.pack_state import (
    describe as _pack,
)
from owlbear_delivery_next.impeccable_runs.pack_state import (
    ended as _ended,
)
from owlbear_delivery_next.impeccable_runs.pack_state import (
    interrupted as _interrupted,
)
from owlbear_delivery_next.impeccable_runs.pack_state import (
    now as _now,
)
from owlbear_delivery_next.impeccable_runs.pack_steps import Steps
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.state_store import spend_ledger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from owlbear_delivery_next.local_system.maintenance import Maintenance
    from owlbear_delivery_next.state_store.store import Store

__all__ = ["CANDIDATE", "FILE", "STAGES", "Busy", "Job", "Live", "Refused", "Stale", "Stopped", "last", "running_for"]


class Busy(Exception):  # noqa: N818 - the route's answer, not a fault
    """An update is already running, or waits for the owner."""


class Stale(Exception):  # noqa: N818 - the route's answer, not a fault
    """The answer is to no open question of a waiting run."""


class Refused(Exception):  # noqa: N818 - the route's answer, not a fault
    """The answer cannot be carried out as given."""


class Job(Steps):
    """The project's Impeccable update: start one, answer it, read its state."""

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
            ctx = pack_run.Context.model_validate(self.state["context"])
            reason = pack_repair.interrupted(ctx) or "the host stopped while the update was being published"
            self._hold(ctx, reason)
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
        shown = {k: v for k, v in self.state.items() if k != "context"} | {
            "progress": pack_progress.progress(self.state),  # from the context, which the page never gets
            "repair": pack_repair.view(self.state.get("context")),
        }
        return json.loads(json.dumps(shown))

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
            Busy: A run is in progress or waits for the owner's answers, here or in another project on this machine,
                or an Impeccable pull request is open or cannot be ruled out.
        """
        with self.lock:
            if self.state["state"] == "running" or self.busy():
                msg = "an Impeccable update is already running"
                raise Busy(msg)
            if self.state["state"] == "waiting":
                msg = "an Impeccable update waits for your answers; answer or discard it first"
                raise Busy(msg)
            self._claim(self._fresh)
            run = uuid.uuid4().hex
            self.state = _blank() | {
                "state": "running", "started_at": _now(), "run": run,
                "workspace": str(self.store.root / RUNS / run), "invocations": [],
            }  # fmt: skip
            self._save()
            self.thread = threading.Thread(
                target=self._run, args=(self._stages,), name="impeccable-update", daemon=True
            )
        self.thread.start()
        return self.read()

    def answer(self, question: str, option: str, note: str = "") -> dict[str, Any]:
        """Carry out the owner's answer to one open question; once none is open, the run goes on.

        Raises:
            Stale: No waiting run asks this question, or the run is still settling.
            Refused: The option is not one of the question's, or a reconsideration lacks its note.
            Busy: The last answer would resume the run, but it is no longer itself or alone (``pack_admission``).
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
            left = pack_run.decided(self.state["questions"], q, option, note=note, ctx=ctx, lp=lp)
            if not left:
                self._claim(self._resumed)  # before anything changes: a refusal leaves the question open
            self._log(said)
            self.state |= {"loop": lp.model_dump(mode="json"), "context": ctx.model_dump(mode="json")}
            self.state["questions"] = left
            if self.state.get("invocations") is not None:
                pack_progress.answered(self.state["invocations"], said, last=not left)
            if not left:
                self.state["state"] = "running"
                for s in self.state["stages"]:  # the stop he answered holds nothing any more
                    s["result"] = "answered" if s["result"] == "waiting" else s["result"]
                self.thread = threading.Thread(
                    target=self._run, args=(self._resume,), name="impeccable-update", daemon=True
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
                msg = "no Impeccable update waits for you"
                raise Stale(msg)
            self._log("you discarded the update")
            self._finish("discarded", "discarded by you; nothing changed")
            return self._copy()

    def keep(self, ctx: pack_run.Context, lp: RoundLoop | None = None) -> None:
        """Keep the run's context and loop (as kept when None), so it goes on from here."""
        with self.lock:
            self.state["context"] = ctx.model_dump(mode="json")
            if lp is not None:
                self.state["loop"] = lp.model_dump(mode="json")
            self._save()

    def wait(
        self, ctx: pack_run.Context, lp: RoundLoop | None, questions: list[dict[str, Any]], stage: str = "challenger"
    ) -> None:
        """Stop the run for the owner's answers; it goes on when he has answered every question."""
        with self.lock:
            ctx.next = "wait"
            self.state |= {"state": "waiting", "stage": "", "questions": questions}
            self.state["context"] = ctx.model_dump(mode="json")
            if lp is not None:
                self.state["loop"] = lp.model_dump(mode="json")
            next(s for s in self.state["stages"] if s["name"] == stage)["result"] = "waiting"
            if self.state.get("invocations") is not None:
                pack_progress.asked(self.state["invocations"], stage, questions)
            self._log(f"waiting for you: {len(questions)} question(s)")
            self._save()

    def hold(self, ctx: pack_run.Context, reason: str) -> None:
        """Publication stopped: the owner tries again once he fixed what stopped it, or discards the update."""
        with self.lock:
            self._hold(ctx, reason)

    def _hold(self, ctx: pack_run.Context, reason: str) -> None:
        pub = ctx.publication
        link = f" ({pub.url})" if pub and pub.url else ""
        repair = [pack_rounds.REPAIR] if pack_repair.offered(ctx) else []  # CI failed on its own pull request
        options = [pack_rounds.RETRY, *repair, pack_rounds.DISCARD]
        question = {"id": f"{self.state['run']}-publish", "kind": "publish", "text": f"{reason}{link}",
                    "options": pack_rounds.published(options, opened=bool(pub and pub.number))}  # fmt: skip
        ctx.next = "wait"
        stage = next((s for s in self.state["stages"] if s["result"] in {"running", "failed"}), None)
        if stage is not None:
            stage["result"], stage["detail"] = "waiting", reason[:4000]
        if self.state.get("invocations") is not None:
            pack_progress.stopped(self.state["invocations"], reason)
            pack_progress.asked(self.state["invocations"], stage["name"] if stage else "merge", [question])
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
        _ended(self.state, state, reason)
        if not keep and self._removable(self.workspace):
            shutil.rmtree(self.workspace, ignore_errors=True)
        self._save()

    def _removable(self, workspace: Path) -> bool:
        """A workspace goes unless the ledger keeps it; without a ledger only the legacy shared root is kept."""
        if self.maintenance is None:
            return workspace != self.store.root / UPDATER
        return not self.maintenance.retained(str(workspace))

    def _claim(self, admits: Callable[[], None]) -> None:
        """Take the machine's one pack lock for the run's thread, if the caller's policy *admits* it under the lock.

        The lock stays held from the policy's reading through the caller's saved claim, so no other project's claim
        comes between them; the pack is shared by every project.

        Raises:
            Busy: Another project's update runs now, an earlier pack session is still unproven, or *admits* refuses.
        """
        self._unproven()
        try:
            # Verified again while the lock is held: an earlier updater may have released it unconfirmed before this.
            self.held = take(local_home.root() / MACHINE_LOCK, self._name, lambda: self._admitted(admits))
        except HeldError as exc:
            msg = f"an Impeccable update runs for {exc.who}; one runs at a time on this machine"
            raise Busy(msg) from None

    @property
    def _name(self) -> str:
        return self.store.name or self.store.root.parent.parent.name

    def _admitted(self, admits: Callable[[], None]) -> None:
        self._unproven()
        try:
            admits()
        except pack_admission.Refused as exc:
            raise Busy(str(exc)) from None

    def _fresh(self) -> None:
        """A new update's policy: no run open on this machine and no pack pull request open (``pack_admission``)."""
        pack_admission.fresh(self.store.root, self._name, self.live.github(self.live.package))

    def _resumed(self) -> None:
        """A waiting run's policy, for an answer and a publication retry: it goes on only as itself, with its own PR."""
        publication = (self.state.get("context") or {}).get("publication") or {}
        pack_admission.resumed(
            self.store.root, self._name, run=self.state["run"], version=self.version,
            branch=str(publication.get("branch") or ""), github=self.live.github(self.live.package),
        )  # fmt: skip

    def _alone(self) -> None:
        """A manual replay's policy: the lock alone. It writes no run record and no pull request (TD-177)."""

    def _unproven(self) -> None:
        if self.maintenance is not None and self.maintenance.pending(kind="pack"):
            msg = "an earlier Impeccable session is unproven; recover it on the Maintenance page first"
            raise Busy(msg)

    def _run(self, work: Callable[[], str | None]) -> None:
        try:
            with spend_ledger.at(spend_ledger.Where.of(self.store, job="Impeccable update")):  # its project's spend
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
                msg = "an Impeccable update is running or waits for answers: finish it before a replay"
                raise Busy(msg)
            self._claim(self._alone)
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
        golden = self.do(  # the updater's evidence, never a verdict on the candidate
            "golden", lambda: pack_gates.checked(live.golden(c.installed)), op="initial-golden",
            judged=lambda _o: "completed",
        )  # fmt: skip
        why = f"Impeccable: {old['pack']} to {c.pins['pack']} (upstream {old['upstream']['tag']} to {tag})"
        return pack_run.begin(self, c, src, diff=diff, golden=golden, why=why)

    def _resume(self) -> str | None:
        with self.lock:
            ctx = pack_run.Context.model_validate(self.state["context"])
            lp = RoundLoop.model_validate(self.state["loop"])
        checking = ctx.repair.phase == "checking"  # an agent's repair of pack content, checked before it is pushed
        if ctx.publication and ctx.publication.commit and not checking:  # GitHub first: the package may have moved on
            return pack_activation.republish(self, ctx, lp)
        return pack_run.advance(self, pack_run.rebuilt(self, ctx), ctx, lp)

    def _notice(self) -> str:
        found = pack_update.newer(self.live.releases)
        if found is None:
            msg = "upstream's releases could not be read; try again when online"
            raise Stopped(msg)
        if not found:
            msg = f"up to date: no skill release newer than {pack_files.manifest()['upstream']['tag']}"
            raise Stopped(msg, current=True)
        return found[-1]
