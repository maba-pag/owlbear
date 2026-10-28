"""The spend the runtime's own log of an OwlBear session holds: what ``spend_reconcile`` imports from it.

The log is ``~/.copilot/session-state/<id>/events.jsonl``, else Retro's copy. It completes a run the ledger left open
for ``OPEN`` (killed), a run that ended with its usage unread, unknown or a lower bound, and a session only Retro's
chatlogs manifest names (curator, design pack and lookup runs before the ledger, and a Spotter look whose own lines
and record a crash lost). Every new high of the session's
cumulative credits counts, at the time it was first reached, the highest of each quarter hour (``QUARTER``), so a
day's total never depends on when the log was first read and known spend never moves to a later day. Its usage stays
provisional until the log shows the session shut down at no less than its high, and the log is read again whenever it
changes.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.improvement import cases
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.runtimes import chatlogs
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.state_store import spend_shares
from owlbear_delivery_next.state_store.spend_ledger import Where

if TYPE_CHECKING:
    from collections.abc import Callable

OPEN = timedelta(hours=3)  # a run still open after this was killed: its runtime's log says what it spent
EPS = 1e-9
QUARTER = 15 * 60  # seconds: every time zone's midnight is a quarter hour's start in UTC, so no day loses a checkpoint
LOOKUP = "decision-lookup"
UNKNOWN_PROJECT = Where(project="(unknown)", name="Project unknown")


def agent(kind: str) -> str:
    """The agent a session of *kind* ran: a Delivery step's role, or the picker for a decision lookup."""
    return "picker" if kind == LOOKUP else roles.SESSIONS.get(kind, "")


def base(place: Where, slug: str, **more: object) -> dict[str, Any]:
    """An imported line's place and Change, with *more*."""
    return {"project": place.project, "name": place.name, "clone": place.clone, "change": slug} | more


def ident(*parts: object) -> str:
    """A deterministic id of *parts*: a line imported again gets the same."""
    return hashlib.sha256(json.dumps(parts, default=str, sort_keys=True).encode()).hexdigest()[:20]


def found(
    known: list[dict[str, Any]], places: dict[str, Where], checked: dict[str, Any], pending: dict[str, str]
) -> list[dict[str, Any]]:
    """What the runtime's log adds: killed runs, runs whose usage was unread or not final, sessions it alone saw.

    A killed run, an ended run or a Change's mark whose usage is unread, unknown or a lower bound, and an OwlBear
    session no other record names get the log's checkpoints as more ``end`` lines of their own run (``log:<session>``
    for the last): a killed run those since it started, the others every one. Each line's id is its content's, so a
    later, larger checkpoint is a new line, and ``spend_shares`` keeps a run's largest usage, or, for a run whose
    ending is itself a checkpoint, dates each one's growth between it and the one before.
    Until the log shows the session shut down, its usage stays provisional (``incomplete``) and the log is read again
    whenever it changes. Each log read is noted in *pending*; it counts as read (*checked*) only once its lines are
    written. A Spotter look's session (``_look``) carries its look's id, and its owner when known (``Owners``); an
    owner known only later moves it with an ``owner`` line (``_owned``).
    """
    now, later = datetime.now(UTC), _resumed(known)
    found = list({r["run"]: r for r in spend_shares.runs(known)}.values())  # each run as its latest entry says
    out = _unfinished(found, later, checked, pending)
    for run in found:
        if run.get("ended") or not run.get("started") or later(run):
            continue  # ended, or a later run of its session accounts for what it spent
        with contextlib.suppress(ValueError, TypeError):
            if now - datetime.fromisoformat(run["started"]) < OPEN:
                continue
        for at, usage, final in _since(_checkpoints(str(run["session"]), checked, pending), run["started"]):
            out.append({k: run.get(k) for k in ("project", "name", "clone", "change", "step")}
                       | _correction(run["run"], str(run["session"]), at, usage, final)
                       | {"ending": "unconfirmed"})  # fmt: skip
    sessions = {line.get("session") for line in known}
    owners = Owners(places)
    for sid, who in _manifest().items():
        if sid in sessions:
            continue  # its runs say it
        if who.get("kind") == "spotter":
            out += _look(sid, who, owners, checked, pending)
            continue
        place, change = _owner(sid, who, places)
        job = str(who.get("job") or "")
        role = str(who.get("role") or agent(job or str(who.get("kind"))))
        for at, usage, final in _checkpoints(sid, checked, pending):
            out.append(base(place, change, agent=role, job=job, step="" if job else str(who.get("kind") or ""),
                             ending="") | _correction(f"log:{sid}", sid, at, usage, final))  # fmt: skip
    return out + _owned(found, owners)


type Owner = tuple[Where, str, str, str, str, dict[str, Any]]
STOP = ("limit", "stopped", "stopped_by")  # a look meter's limit and stop, as its record or cases run keeps them


def _stop(said: dict[str, Any]) -> dict[str, Any]:
    return {"limit": said.get("limit"), "stopped": str(said.get("stopped") or ""),
            "stopped_by": str(said.get("stopped_by") or "")}  # fmt: skip


class Owners:
    """Who owns each Spotter look, by its id: its Spotter record, else the Spotter cases run that replayed it.

    Read once, when first asked: the place, Change, step and job its spend counts under, the source that said so, and
    its meter's limit and stop (``STOP``), which no other line of a look whose own lines were lost keeps.
    """

    def __init__(self, places: dict[str, Where]) -> None:
        self.places = places
        self.found: dict[str, Owner] | None = None

    def of(self, look: str) -> Owner | None:
        """The owner of *look*, or None while neither its record nor its cases run is written."""
        if self.found is None:
            self.found = self._read()
        return self.found.get(look)

    def _read(self) -> dict[str, Owner]:
        out: dict[str, Owner] = {}
        for run in _lines(cases.place() / "runs.jsonl"):  # a replay is machine-wide work, as its own lines say
            for report in run.get("looks") or ():
                if isinstance(report, dict) and report.get("id"):
                    out[str(report["id"])] = (Where(), "", "", "look", "import:cases", _stop(report))
        folder = local_home.root() / "spotter"
        for path in sorted(folder.glob("records-*.jsonl")) if folder.is_dir() else ():
            for rec in _lines(path):
                if rec.get("id"):
                    project = str(rec.get("project") or "")
                    place = self.places.get(project, UNKNOWN_PROJECT if project else Where())
                    out[str(rec["id"])] = (place, str(rec.get("change") or ""), str(rec.get("step") or ""),
                                           f"{rec.get('look') or ''} look".strip(), "import:spotter",
                                           _stop(rec))  # fmt: skip
        return out


def _lines(path: Path) -> list[dict[str, Any]]:
    """Each readable JSON object line of *path*; none when it cannot be read."""
    out = []
    with contextlib.suppress(OSError):
        for raw in path.read_text(encoding="utf-8").splitlines():
            with contextlib.suppress(ValueError):
                if isinstance(line := json.loads(raw), dict):
                    out.append(line)
    return out


def _look(
    sid: str, who: dict[str, Any], owners: Owners, checked: dict[str, Any], pending: dict[str, str]
) -> list[dict[str, Any]]:
    """A Spotter look's session only the manifest names: its own run, ``log:<session>``, carrying its look's id.

    A legacy look, whose manifest line names no look, is its Spotter record's. Its place is its owner's when known,
    else the unknown project, never this machine's: a crash may have kept its record or cases run from being written.
    Its own lines, when they come after all, join this run (``spend_shares.runs``).
    """
    look = str(who.get("look") or "")
    if not look or not (read := _checkpoints(sid, checked, pending)):
        return []
    place, change, step, job, _, stop = owners.of(look) or (UNKNOWN_PROJECT, "", "", "look", "", {})
    role = str(who.get("role") or "spotter")
    return [base(place, change, agent=role, job=job, step=step, ending="", look=look) | stop
            | _correction(f"log:{sid}", sid, at, usage, final) for at, usage, final in read]  # fmt: skip


def _owned(found: list[dict[str, Any]], owners: Owners) -> list[dict[str, Any]]:
    """An ``owner`` line for each recovered look session still under the unknown project whose owner is now known.

    Its run moves to its owner, and takes its meter's stop, whether or not its log changed since: ``spend_shares.runs``
    applies the line.
    """
    out = []
    for run in found:
        look, sid = str(run.get("look") or ""), str(run.get("session") or "")
        if not look or run["run"] != f"log:{sid}" or run.get("project") != UNKNOWN_PROJECT.project:
            continue
        owner = owners.of(look)
        if owner is None or owner[0] == UNKNOWN_PROJECT:
            continue
        place, change, step, job, source, stop = owner
        fields = base(place, change, step=step, job=job) | stop
        out.append({"id": f"owner:{run['run']}:{ident(fields)}", "type": spend_shares.OWNER, "run": run["run"],
                    "session": sid, "look": look, "source": source} | fields)  # fmt: skip
    return out


def _correction(run: str, session: str, at: str, usage: dict[str, Any], final: bool) -> dict[str, Any]:  # noqa: FBT001
    """Another ``end`` of *run*: its session's usage at *at* as the runtime's log has it; provisional unless *final*.

    *at* is the checkpoint's own time: ``spend_shares`` keeps a run's recorded ending time, and dates a run whose
    ending is itself a checkpoint by each checkpoint.
    """
    usage = usage if final else usage | {"incomplete": "checkpoint"}
    return {"id": f"end:{run}:log:{ident(at, usage)}", "type": "end", "run": run, "at": at, "session": session,
            "usage": usage, "source": "import:runtime-log"}  # fmt: skip


def _resumed(known: list[dict[str, Any]]) -> Callable[[dict[str, Any]], bool]:
    """Whether a later run of a run's session started: its ``before`` accounts for what the run spent."""
    starts: dict[str, list[tuple[str, str]]] = {}
    for line in known:
        if line.get("type") == "start" and isinstance(at := line.get("at"), str):
            starts.setdefault(str(line.get("session")), []).append((at, str(line.get("run"))))

    def later(run: dict[str, Any]) -> bool:
        began = run.get("started") or run.get("at") or ""
        return any(at > began and rid != run["run"] for at, rid in starts.get(str(run.get("session")), ()))

    return later


def _unfinished(
    found: list[dict[str, Any]],
    later: Callable[[dict[str, Any]], bool],
    checked: dict[str, Any],
    pending: dict[str, str],
) -> list[dict[str, Any]]:
    """Ended runs and Change marks whose usage is unread, unknown or a lower bound, completed from their session's log.

    Not when a later run of the session accounts for what it spent; a lower bound is replaced only by at least as much.
    """
    out = []
    for run in found:
        usage = run.get("usage")
        if not run.get("ended") or run.get("line") not in {"end", "mark"} or usage is None:
            continue
        unread = spend_shares.unread(usage)
        if not unread and not usage.get("incomplete"):
            continue
        if later(run):
            continue
        for at, got, final in _checkpoints(str(run["session"]), checked, pending):
            if unread or got["credits"] >= (usage.get("credits") or 0.0):
                out.append(_correction(run["run"], str(run["session"]), at, got, final))
    return out


def _since(read: list[tuple[str, dict[str, Any], bool]], started: str) -> list[tuple[str, dict[str, Any], bool]]:
    """The checkpoints from *started* on (those before are an earlier run's), else the latest: its total then."""
    with contextlib.suppress(ValueError, TypeError):
        began = datetime.fromisoformat(started)
        return [x for x in read if datetime.fromisoformat(x[0]) >= began] or read[-1:]
    return read[-1:]


def _manifest() -> dict[str, dict[str, Any]]:
    """Each OwlBear session Retro's manifest names, with its first owner line."""
    out: dict[str, dict[str, Any]] = {}
    with contextlib.suppress(OSError):
        for raw in (chatlogs.root() / "manifest.jsonl").read_text().splitlines():
            with contextlib.suppress(ValueError, TypeError, AttributeError):
                line = json.loads(raw)
                if line.get("event") == "started" and line.get("session"):
                    out.setdefault(str(line["session"]), line)
    return out


def _owner(sid: str, who: dict[str, Any], places: dict[str, Where]) -> tuple[Where, str]:
    """A logged session's project and Change: its Delivery worktree, else a curator's folder, else unknown."""
    path = str(who.get("worktree") or "")
    with contextlib.suppress(ValueError):
        parts = Path(path).relative_to(worktree.data_root()).parts
        if len(parts) > 1 and parts[0] in places:  # <clone folder>/<Change>
            return places[parts[0]], parts[1]
    if who.get("job") == "memory-curation" and sid.startswith("memory-curation-"):
        name = sid.removeprefix("memory-curation-").rsplit("-", 1)[0]
        return next((p for p in places.values() if p.project == name), Where(project=name, name=name)), ""
    return UNKNOWN_PROJECT, ""


def _checkpoints(sid: str, checked: dict[str, Any], pending: dict[str, str]) -> list[tuple[str, dict[str, Any], bool]]:
    """The session's usage highs in the runtime's log, oldest first: when first reached, the usage, whether final.

    The latest is final when the session shut down, was not resumed since, and reported no less than its high.
    A log read and written before, and unchanged since, is not read again; this read is noted in *pending*.
    """
    for path in (chatlogs.state() / sid / "events.jsonl", chatlogs.root() / "chatlogs" / sid / "log.jsonl.gz"):
        try:
            seen = path.stat()
        except OSError:
            continue
        mark = f"{seen.st_size}:{seen.st_mtime_ns}"
        if checked.get(sid) == mark:
            return []
        pending[sid] = mark
        read: list[tuple[str, dict[str, Any]]] = []  # every checkpoint, as written
        final = False
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[operator]
            for raw in f:
                kind = _kind(raw)
                if kind in {"session.usage_checkpoint", "session.shutdown"}:
                    got = _read(raw)
                    if got is not None:
                        read.append(got)
                    final = kind == "session.shutdown" and got is not None
                elif kind in {"session.start", "session.resume"}:
                    final = False
        return _highs(read, final=final)
    return []


def _read(raw: str) -> tuple[str, dict[str, Any]] | None:
    with contextlib.suppress(ValueError, TypeError, KeyError):
        return _usage(json.loads(raw))
    return None


def _highs(read: list[tuple[str, dict[str, Any]]], *, final: bool) -> list[tuple[str, dict[str, Any], bool]]:
    """Each new high of the cumulative credits at the time it was first reached, the highest of each quarter hour.

    A reading at or below the high adds nothing and never moves it later; a quarter hour lies within one day in every
    time zone. The last high is final only when the log's last reading, its shutdown (*final*), reached it: then it
    takes that reading's usage, at the high's time. A shutdown lower than the high leaves it a lower bound.
    """
    quarters: dict[int, tuple[str, dict[str, Any]]] = {}
    top = -1.0
    for at, usage in read:
        if usage["credits"] > top + EPS:
            top = usage["credits"]
            quarters[int(datetime.fromisoformat(at).timestamp()) // QUARTER] = (at, usage)
    highs = list(quarters.values())
    if not highs:
        return []
    done = final and read[-1][1]["credits"] >= top - EPS
    last = (highs[-1][0], read[-1][1]) if done else highs[-1]
    return [(at, usage, False) for at, usage in highs[:-1]] + [(*last, done)]


def _kind(raw: str) -> str:
    """A log line's event type, read without parsing the line when it comes first, as the runtime writes it."""
    head = raw[:80]
    if '"type"' not in head:
        return ""
    with contextlib.suppress(IndexError):
        return head.split('"type"', 1)[1].split('"', 2)[1]
    return ""


def _usage(event: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """A checkpoint or shutdown event as a cumulative usage, in the ledger's form (``sdk_usage``)."""
    data = event["data"]
    snap = data.get("accountingSnapshot") or {}
    nano = snap.get("totalNanoAiu", data.get("totalNanoAiu"))
    if nano is None:
        return None
    usage: dict[str, Any] = {"credits": float(nano) / 1e9, "models": _models(snap.get("modelMetrics") or {})}
    if agents := snap.get("agentMetrics"):
        usage["agents"] = {
            key: {"agent": a.get("agentName") or ("main" if key == "main" else ""),
                  "models": _models(a.get("modelMetrics") or {})}
            for key, a in agents.items()
        }  # fmt: skip
    at = datetime.fromisoformat(str(event["timestamp"])).astimezone(UTC).isoformat(timespec="seconds")
    return at, usage


def _models(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for name, m in metrics.items():
        u, nano = m.get("usage") or {}, m.get("totalNanoAiu")
        inp, outp = int(u.get("inputTokens") or 0), int(u.get("outputTokens") or 0)
        out[name] = {"credits": None if nano is None else float(nano) / 1e9, "tokens": inp + outp, "input": inp,
                     "output": outp, "cache_read": int(u.get("cacheReadTokens") or 0),
                     "cache_write": int(u.get("cacheWriteTokens") or 0)}  # fmt: skip
    return out
