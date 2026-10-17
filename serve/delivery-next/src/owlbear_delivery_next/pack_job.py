"""The Settings page's design pack update (TD-101, TD-220, TD-256): one host job at a time, its stages, its last run.

Stages run in order and the first that fails stops the run with its reason: notice, candidate, diff, golden pages, then
the updater's and the challenger's rounds with the calibration replay (``pack_run``), activate (one commit in the
package's checkout) and push. Until activation nothing in the package changes. A run whose rounds need the owner waits
for his answers on the Settings page; its state is kept under the store, so a waiting run survives a host restart,
while a run the host stopped during reads as failed.
"""

from __future__ import annotations

import json
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import (
    design_pack,
    pack_candidate,
    pack_git,
    pack_replay,
    pack_rounds,
    pack_run,
    pack_update,
    sessions,
)
from owlbear_delivery_next.pack_run import CANDIDATE, UPDATER, Stopped
from owlbear_delivery_next.round_records import RoundLoop
from owlbear_delivery_next.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.calibration import Replay
    from owlbear_delivery_next.session_result import Run
    from owlbear_delivery_next.store import Store

__all__ = ["CANDIDATE", "FILE", "STAGES", "Busy", "Job", "Live", "Refused", "Stale", "Stopped", "last"]
FILE = "design-pack-update.json"  # the last run, under the store
STAGES = (
    ("notice", "Notice: newer upstream release"),
    ("candidate", "Candidate: detector pins and skills"),
    ("diff", "Diff: rules and skill files"),
    ("golden", "Golden pages"),
    ("update", "Updater: skills against upstream and the findings"),
    ("replay", "Calibration replay"),
    ("challenger", "Challenger on the whole pack"),
    ("activate", "Activate: one commit in the package"),
    ("push", "Push the branch"),
)
LOG = 200  # lines kept of the last run's log
OPEN = frozenset({"pending", "running", "waiting"})


class Busy(Exception):  # noqa: N818 - the route's answer, not a fault
    """An update is already running, or waits for the owner."""


class Stale(Exception):  # noqa: N818 - the route's answer, not a fault
    """The answer is to no open question of a waiting run."""


class Refused(Exception):  # noqa: N818 - the route's answer, not a fault
    """The answer cannot be carried out as given."""


def _upstream() -> Path:
    return design_pack.folder().parent / "upstream"  # beside the packs, outside every project


@dataclass
class Live:
    """What reaches outside: upstream, downloads, the browser, model sessions and git. Tests replace each."""

    package: Path = field(default_factory=lambda: Path(str(files("owlbear_delivery_next"))))
    clone: Path = field(default_factory=_upstream)
    releases: Callable[[str], bytes] | None = None  # the notice's release list; None reads GitHub
    sync: Callable[[Path, str], None] = pack_candidate.sync
    download: Callable[[str], bytes] = design_pack.fetch
    golden: Callable[[design_pack.Installed], dict[str, dict[str, list[str]]]] = pack_update.golden
    replay: Callable[[Store, pack_candidate.Candidate | None], Replay] = pack_replay.replay
    challenge: Callable[[Store, Any], Run] = sessions.run
    update: Callable[[Store, Any], Run] = sessions.run  # the writing updater (TD-125)
    git: pack_git.Git = pack_git.git


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _blank() -> dict[str, Any]:
    stages = [{"name": n, "label": label, "result": "pending", "detail": ""} for n, label in STAGES]
    return {"state": "idle", "stage": "", "stages": stages, "started_at": None, "ended_at": None, "reason": "",
            "log": [], "pushed": None, "run": "", "loop": None, "questions": [], "context": None}  # fmt: skip


class Job:
    """The project's design pack update: start one, answer it, read its state."""

    def __init__(self, store: Store, live: Live | None = None) -> None:
        """Read the last run; one the host stopped during reads as failed, one waiting for the owner still waits."""
        self.store, self.live, self.lock = store, live or Live(), threading.Lock()
        self.thread: threading.Thread | None = None
        self.state = self._read()
        if self.state["state"] == "running":
            self._end("failed", "the host stopped during this run; check the package checkout before running again")

    @property
    def path(self) -> Path:
        """Where the last run is kept."""
        return self.store.root / FILE

    def _read(self) -> dict[str, Any]:
        try:
            kept = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            return _blank()
        return _blank() | kept if isinstance(kept, dict) and {"state", "stages", "log"} <= kept.keys() else _blank()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.path, json.dumps(self.state, indent=1) + "\n")

    def read(self) -> dict[str, Any]:
        """The current or last run, as the page shows it: without the run's context."""
        with self.lock:
            return self._copy()

    def _copy(self) -> dict[str, Any]:
        return json.loads(json.dumps({k: v for k, v in self.state.items() if k != "context"}))

    def _busy(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self) -> dict[str, Any]:
        """Start a run on its own thread and return its first state.

        Raises:
            Busy: A run is in progress, or waits for the owner's answers.
        """
        with self.lock:
            if self.state["state"] == "running" or self._busy():
                msg = "a design pack update is already running"
                raise Busy(msg)
            if self.state["state"] == "waiting":
                msg = "a design pack update waits for your answers; answer or discard it first"
                raise Busy(msg)
            self.state = _blank() | {"state": "running", "started_at": _now(), "run": uuid.uuid4().hex}
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
            asked = self.state["questions"] if self.state["state"] == "waiting" and not self._busy() else []
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
            self._log(
                f"you answered {q['kind']} {q.get('finding', '')}: {pack_rounds.LABELS[option]}".replace("  ", " ")
            )
            if option == pack_rounds.DISCARD:
                self._finish("discarded", "discarded by you; nothing changed")
                return self._copy()
            ctx = pack_run.Context.model_validate(self.state["context"])
            lp = RoundLoop.model_validate(self.state["loop"])
            left = _decided(self.state["questions"], q, option, note=note, ctx=ctx, lp=lp)
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
            if self.state["state"] != "waiting" or self._busy():
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

    def wait(self, ctx: pack_run.Context, lp: RoundLoop, questions: list[dict[str, Any]]) -> None:
        """Stop the run for the owner's answers; it goes on when he has answered every question."""
        with self.lock:
            ctx.next = "wait"
            self.state |= {"state": "waiting", "stage": "", "questions": questions}
            self.state |= {"context": ctx.model_dump(mode="json"), "loop": lp.model_dump(mode="json")}
            stage = next(s for s in self.state["stages"] if s["name"] == "challenger")
            stage["result"] = "waiting"
            self._log(f"waiting for you: {len(questions)} question(s)")
            self._save()

    def pushed(self, commit: str, co: pack_git.Checkout, changed: list[str]) -> None:
        """Record the pushed commit."""
        with self.lock:
            self.state["pushed"] = {"commit": commit, "remote": co.remote, "branch": co.merge, "files": changed}
            self._save()

    def _end(self, state: str, reason: str) -> None:
        with self.lock:
            self._finish(state, reason)

    def _finish(self, state: str, reason: str) -> None:
        for s in self.state["stages"]:
            if s["result"] in OPEN:
                s["result"] = "failed" if s["result"] == "running" and state == "failed" else "skipped"
        self.state |= {"state": state, "stage": "", "ended_at": _now(), "reason": reason, "questions": []}
        self.state["context"] = None
        shutil.rmtree(self.store.root / UPDATER, ignore_errors=True)
        self._save()

    def _run(self, work: Callable[[], str | None]) -> None:
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

    def do[T](self, name: str, work: Callable[[], T], said: Callable[[T], str] = str) -> T:
        """Run one stage's work: its result shown, any failure ending the run with the stage named."""
        self.stage(name, "running")
        try:
            out = work()
        except Stopped as exc:
            self.stage(name, "passed" if exc.current else "failed", exc.reason)
            raise
        except Exception as exc:
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

        def candidate() -> tuple[pack_git.Checkout, pack_candidate.Candidate]:
            co = pack_git.checkout(package, live.git)  # before any download: a checkout that cannot commit stops
            live.sync(live.clone, old["upstream"]["repository"])
            folder = store.root / CANDIDATE  # kept after the run, so the owner can read what was judged
            shutil.rmtree(folder, ignore_errors=True)
            return co, pack_candidate.prepare(live.clone, package, tag, live.download, folder)

        co, c = self.do("candidate", candidate, lambda out: _pack(*out))
        diff = self.do("diff", lambda: pack_update.diff(live.clone, tag))
        golden = self.do("golden", lambda: _golden(live.golden(c.installed)))
        why = f"design pack: {old['pack']} to {c.pins['pack']} (upstream {old['upstream']['tag']} to {tag})"
        return pack_run.begin(self, c, co, diff=diff, golden=golden, why=why)

    def _resume(self) -> str | None:
        with self.lock:
            ctx = pack_run.Context.model_validate(self.state["context"])
            lp = RoundLoop.model_validate(self.state["loop"])
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
    if option == pack_rounds.ANOTHER:
        lp.extra, lp.ended, ctx.next = lp.extra + 1, "", "challenge"
    else:
        lp.ended, ctx.accepted, ctx.next = lp.ended, q["identity"], "activate"
    return []


def _pack(co: pack_git.Checkout, c: pack_candidate.Candidate) -> str:
    up = c.pins["upstream"]
    return f"{c.pins['pack']}: upstream {c.tag} at {up['commit'][:12]}, engine {up['engine']}; commits on {co.branch}"


def _golden(wrong: dict[str, dict[str, list[str]]]) -> str:
    if wrong:
        pages = "; ".join(f"{p}: missing {', '.join(w['missing']) or 'none'}, unexpected "
                          f"{', '.join(w['unexpected']) or 'none'}" for p, w in wrong.items())  # fmt: skip
        msg = f"golden pages differ: {pages}"
        raise Stopped(msg)
    return "as expected"


def last(store: Store) -> dict[str, Any] | None:
    """The last run's state, ending and times, for the Maintenance page; None when it never ran."""
    try:
        kept = json.loads((store.root / FILE).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(kept, dict) or not kept.get("started_at"):
        return None
    return {k: kept.get(k) for k in ("state", "started_at", "ended_at", "reason")}
