"""The Settings page's design pack update (TD-101): one host job at a time, its stages, and its last run on disk.

Stages run in order and the first that fails stops the run with its reason: notice, candidate, diff, golden pages,
calibration replay, challenger, activate (one commit in the package's checkout) and push. Until activation nothing in
the package changes; a candidate's files may stay installed in their own pack folder, as any pack's do. The last run
is kept under the store, so it survives a host restart; a run the host stopped during reads as failed.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
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
    pack_update,
    pack_updater,
    preload,
    sessions,
)
from owlbear_delivery_next.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next import sdk_adapter
    from owlbear_delivery_next.calibration import Replay
    from owlbear_delivery_next.session_result import Run
    from owlbear_delivery_next.store import Store

FILE = "design-pack-update.json"  # the last run, under the store
CANDIDATE = "design-pack-candidate"  # the last run's candidate skills, under the store
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


class Busy(Exception):  # noqa: N818 - the route's answer, not a fault
    """An update is already running."""


class Stopped(Exception):  # noqa: N818 - how a stage ends the run
    """A stage ended the run: up to date, or failed with a reason."""

    def __init__(self, reason: str, *, current: bool = False) -> None:
        """Keep the reason; *current* ends the run as up to date rather than failed."""
        super().__init__(reason)
        self.reason, self.current = reason, current


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
            "log": [], "pushed": None}  # fmt: skip


class Job:
    """The project's design pack update: start one, read its state."""

    def __init__(self, store: Store, live: Live | None = None) -> None:
        """Read the last run; one the host stopped during reads as failed."""
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
        return kept if isinstance(kept, dict) and {"state", "stages", "log"} <= kept.keys() else _blank()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.path, json.dumps(self.state, indent=1) + "\n")

    def read(self) -> dict[str, Any]:
        """The current or last run, as the page shows it."""
        with self.lock:
            return json.loads(json.dumps(self.state))

    def start(self) -> dict[str, Any]:
        """Start a run on its own thread and return its first state.

        Raises:
            Busy: A run is in progress.
        """
        with self.lock:
            if self.state["state"] == "running":
                msg = "a design pack update is already running"
                raise Busy(msg)
            self.state = _blank() | {"state": "running", "started_at": _now()}
            self._save()
            self.thread = threading.Thread(target=self._run, name="design-pack-update", daemon=True)
        self.thread.start()
        return self.read()

    def log(self, line: str) -> None:
        """One line of the run's log, kept with its state."""
        with self.lock:
            self.state["log"] = [*self.state["log"], f"{_now()} {line}"][-LOG:]
            self._save()

    def _stage(self, name: str, result: str, detail: str = "") -> None:
        with self.lock:
            stage = next(s for s in self.state["stages"] if s["name"] == name)
            stage["result"], stage["detail"] = result, detail[:4000]
            self.state["stage"] = name if result == "running" else self.state["stage"]
            self._save()
        self.log(f"{name}: {result}{f': {detail.splitlines()[0][:300]}' if detail else ''}")

    def _end(self, state: str, reason: str) -> None:
        with self.lock:
            for s in self.state["stages"]:
                if s["result"] in {"pending", "running"}:
                    s["result"] = "failed" if s["result"] == "running" and state == "failed" else "skipped"
            self.state |= {"state": state, "stage": "", "ended_at": _now(), "reason": reason}
            self._save()

    def _run(self) -> None:
        try:
            self._stages()
        except Stopped as exc:
            self.log(exc.reason)
            self._end("up-to-date" if exc.current else "failed", exc.reason)
        except Exception as exc:  # noqa: BLE001 - the page must learn how the run ended
            reason = f"{type(exc).__name__}: {exc}"[:600]
            self.log(reason)
            self._end("failed", reason)
        else:
            self._end("passed", "activated, committed and pushed")

    def _do[T](self, name: str, work: Callable[[], T], said: Callable[[T], str] = str) -> T:
        self._stage(name, "running")
        try:
            out = work()
        except Stopped as exc:
            self._stage(name, "passed" if exc.current else "failed", exc.reason)
            raise
        except Exception as exc:
            reason = f"{name}: {type(exc).__name__}: {exc}"[:2000]  # any failure stops the run, its stage named
            self._stage(name, "failed", reason)
            raise Stopped(reason) from exc
        self._stage(name, "passed", said(out))
        return out

    def _stages(self) -> None:
        live, store = self.live, self.store
        package = live.package.resolve()
        old = json.loads((package / pack_candidate.MANIFEST).read_text(encoding="utf-8"))
        tag = self._do("notice", self._notice)

        def candidate() -> tuple[pack_git.Checkout, pack_candidate.Candidate]:
            co = pack_git.checkout(package, live.git)  # before any download: a checkout that cannot commit stops
            live.sync(live.clone, old["upstream"]["repository"])
            folder = store.root / CANDIDATE  # kept after the run, so the owner can read what was judged
            shutil.rmtree(folder, ignore_errors=True)
            return co, pack_candidate.prepare(live.clone, package, tag, live.download, folder)

        co, c = self._do("candidate", candidate, lambda out: _pack(*out))
        diff = self._do("diff", lambda: pack_update.diff(live.clone, tag))
        golden = self._do("golden", lambda: _golden(live.golden(c.installed)))
        replayed = self._rounds(c, diff, golden, package)
        edited = [n for n in c.pins["skills"] if pack_updater.skill(c, n).read_bytes() != c.baseline[n]]
        why = f"design pack: {old['pack']} to {c.pins['pack']} (upstream {old['upstream']['tag']} to {tag})"
        said = f"The updater changed {', '.join(edited)}." if edited else "The updater changed no skill."
        body = f"{why}\n\nGolden pages as expected. Calibration replay: {replayed}. {said} The challenger passed."
        changed = {package / pack_candidate.MANIFEST: c.manifest, package / pack_candidate.NOTICE: c.notice}

        def activate() -> str:  # the edited skills join the one commit, checked against the package just before
            changed.update(_skills(package, c, edited))
            return pack_git.activate(co, changed, body, live.git)

        commit = self._do("activate", activate)
        self._do("push", lambda: pack_git.push(co, commit, live.git), lambda _o: f"{commit} to {co.remote} {co.merge}")
        with self.lock:
            files_ = sorted(str(p.relative_to(co.root)) for p in changed)
            self.state["pushed"] = {"commit": commit, "remote": co.remote, "branch": co.merge, "files": files_}

    def _rounds(self, c: pack_candidate.Candidate, diff: str, golden: str, package: Path) -> str:
        """Updater, replay and challenger until the challenger passes (TD-125); the last replay in words.

        The producing updater repairs once, then a fresh one; the replay reruns only on changed skills.
        """
        live, store = self.live, self.store
        with tempfile.TemporaryDirectory(prefix="owlbear-pack-update-") as tmp:
            at = Path(tmp)
            start = pack_updater.lay_out(at, c, live.clone)
            sid, findings, summary, replayed, judged = pack_updater.new_id(), {}, "", "", ""
            for n in range(pack_updater.ROUNDS):
                sid = pack_updater.new_id() if n == pack_updater.ROUNDS - 1 else sid
                whole = pack_updater.prompt(c, diff, findings, summary if n else "")
                ask = pack_updater.repair(findings) if n == 1 else whole
                cfg = pack_updater.config(store, at, sid, ask, resume=n == 1, fresh=whole, replaced=self._replaced)

                def update(cfg: sdk_adapter.Session = cfg) -> pack_updater.UpdateResult:
                    result = pack_updater.ended(live.update(store, cfg))
                    pack_updater.taken(at, start, c)
                    return result

                result = self._do("update", update, lambda r: r.summary)
                rejected = {r.finding: r.reason for r in result.rejected if r.finding in findings}
                summary, now = result.summary, design_pack.identity(c.manifest, c.skills)
                if now != judged:  # the affected check reruns after the updater's edits (TD-177)
                    replayed, judged = self._do("replay", lambda: _replayed(live.replay(store, c))), now
                text = pack_candidate.message(
                    c, diff, golden, replayed, package, updated=summary,
                    rechecks=pack_updater.rechecks(findings, rejected),
                )  # fmt: skip

                def challenge(text: str = text, rejected: dict[str, str] = rejected, findings: dict = findings) -> dict:
                    done = pack_candidate.challenge(
                        store, c, live.clone, text, live.challenge, rechecks=tuple(rejected)
                    )
                    return pack_updater.judged(done, findings, rejected)

                findings = self._do("challenger", challenge, lambda f: "passed" if not f else f"{len(f)} finding(s)")
                if not findings:
                    return replayed
                said = "; ".join(f"{k}: {v}" for k, v in findings.items())
                last = n == pack_updater.ROUNDS - 1
                self._stage("challenger", "failed" if last else "returned", said)
        msg = f"findings remain after {pack_updater.ROUNDS} challenger rounds; the owner decides: {said}"
        raise Stopped(msg[:2000])

    def _replaced(self) -> str:
        """The resumed updater is gone: a fresh one takes its repair, told the earlier work (TD-175)."""
        self.log("update: the updater's session could not be resumed; a fresh one takes its repair")
        return pack_updater.new_id()

    def _notice(self) -> str:
        found = pack_update.newer(self.live.releases)
        if found is None:
            msg = "upstream's releases could not be read; try again when online"
            raise Stopped(msg)
        if not found:
            msg = f"up to date: no skill release newer than {design_pack.manifest()['upstream']['tag']}"
            raise Stopped(msg, current=True)
        return found[-1]


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


def _replayed(r: Replay) -> str:
    said = pack_candidate.said_replay(r)
    if not r.ok:
        msg = f"calibration replay: {said}"
        raise Stopped(msg)
    return said


def _passed(out: tuple[bool, str]) -> str:
    ok, why = out
    if not ok:
        msg = f"challenger: {why}"
        raise Stopped(msg)
    return why


def _skills(package: Path, c: pack_candidate.Candidate, edited: list[str]) -> dict[Path, str]:
    """The edited skills' exact text; every skill in the package must still be what the candidate started from."""
    for name, start in c.baseline.items():
        if (package / preload.ROOT / name / "SKILL.md").read_bytes() != start:
            msg = f"{name} changed in the package during the update; run the update again"
            raise Stopped(msg)
    return {
        package / preload.ROOT / n / "SKILL.md": pack_updater.skill(c, n).read_text(encoding="utf-8") for n in edited
    }


def last(store: Store) -> dict[str, Any] | None:
    """The last run's state, ending and times, for the Maintenance page; None when it never ran."""
    try:
        kept = json.loads((store.root / FILE).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(kept, dict) or not kept.get("started_at"):
        return None
    return {k: kept.get(k) for k in ("state", "started_at", "ended_at", "reason")}
