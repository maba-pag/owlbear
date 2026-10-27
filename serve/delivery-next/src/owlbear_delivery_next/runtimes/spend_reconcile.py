"""Spend the ledger lacks, taken from OwlBear's other records: earlier work, lost lines and killed runs.

One pass, on the machine host's own thread, never under the ledger's lock while it reads; it appends what it found
per source, each line with a deterministic id, so a pass cut short and run again adds nothing twice, and
``spend_shares`` takes a session's highest totals, so a line that repeats what the ledger holds adds nothing either.
Its progress and what it could not read are in ``reconcile.json`` beside the ledger, which the Metrics page shows.

What it reads, for each project this machine serves and for this machine:
- each Change's step events (their session, kind, time and cumulative usage; the activity log keeps the last 200);
- each Change's per-session marks (``Spend.last``: a session's highest totals, time unknown) where they exceed what
  the ledger has for that session, and the Change's credits no session holds (``residual``: time and agent unknown);
- Spotter records written before looks wrote the ledger: one session each; a legacy look whose spend was not
  reported carries the 0.5 estimate it was booked at, which is imported as unknown, never as measured;
- the runtime's own log of an OwlBear session (``~/.copilot/session-state/<id>/events.jsonl``, else Retro's copy)
  whose run the ledger left open for ``OPEN`` or which the ledger never saw, from Retro's chatlogs manifest: curator,
  design pack and lookup runs before the ledger, and a killed run's last usage checkpoint.
Spend that none of these kept is not recoverable: a session OwlBear ran before Retro's manifest (2026-10-25) and
outside any Change, such as a curator or design pack run, and the events a Change's activity log dropped beyond its
marks' totals.
"""

from __future__ import annotations

import contextlib
import fcntl
import gzip
import hashlib
import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.runtimes import chatlogs
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.state_store.spend_ledger import Where

if TYPE_CHECKING:
    from collections.abc import Iterable

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store

OPEN = timedelta(hours=3)  # a run still open after this was killed: its runtime's log says what it spent
AGAIN = timedelta(minutes=10)  # a page read starts another pass at most this often
ESTIMATE = 0.5  # what a legacy Spotter look booked when its spend was not reported
LOOKUP = "decision-lookup"
UNKNOWN_PROJECT = Where(project="(unknown)", name="Project unknown")
EPS = 1e-6
_running = threading.Lock()


def state_path() -> Path:
    """The pass's progress and findings."""
    return spend_ledger.folder() / "reconcile.json"


def state() -> dict[str, Any]:
    """The last pass's progress, or none yet."""
    try:
        found = json.loads(state_path().read_text())
    except OSError, ValueError:
        return {"state": "never"}
    return found if isinstance(found, dict) else {"state": "never"}


def _save(said: dict[str, Any]) -> None:
    with contextlib.suppress(OSError):
        spend_ledger.folder().mkdir(parents=True, exist_ok=True, mode=0o700)
        atomic_write(state_path(), json.dumps(said, indent=1))


def _now() -> datetime:
    return datetime.now(UTC)


def due(now: datetime | None = None) -> bool:
    """Whether a page read should start a pass: none ran, or the last ended ``AGAIN`` ago."""
    said, now = state(), now or _now()
    if said.get("state") == "running" and _running.locked():
        return False
    try:
        return now - datetime.fromisoformat(said["finished"]) >= AGAIN
    except KeyError, TypeError, ValueError:
        return True


def start(projects: Iterable[tuple[Store, Path | None]]) -> bool:
    """Run a pass on a daemon thread unless one runs; whether one started."""
    if not _running.acquire(blocking=False):
        return False
    listed = list(projects)

    def work() -> None:
        try:
            run(listed)
        finally:
            _running.release()

    threading.Thread(target=work, name="spend-reconcile", daemon=True).start()
    return True


def settled(seconds: float) -> bool:
    """Wait at most *seconds* until no pass runs in this process; whether none does."""
    if not _running.acquire(timeout=seconds):
        return False
    _running.release()
    return True


def _id(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, default=str, sort_keys=True).encode()).hexdigest()[:20]


def _high(lines: list[dict[str, Any]]) -> dict[str, float]:
    """Each session's highest known credits in the ledger."""
    out: dict[str, float] = {}
    for line in lines:
        usage = line.get("usage") or {}
        if (c := usage.get("credits")) is not None and (s := line.get("session")):
            out[s] = max(out.get(s, 0.0), float(c))
    return out


def run(projects: list[tuple[Store, Path | None]]) -> dict[str, Any]:
    """One pass over every source; its final state.

    The machine's own lock file keeps two hosts from passing at once; the second ends at once, having done nothing.
    """
    spend_ledger.folder().mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(spend_ledger.folder() / "reconcile.lock", os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return state()
        return _pass(projects)
    finally:
        os.close(fd)


def _pass(projects: list[tuple[Store, Path | None]]) -> dict[str, Any]:
    said = state()
    checked = said.get("checked") if isinstance(said.get("checked"), dict) else {}
    said = {"state": "running", "started": _now().isoformat(timespec="seconds"), "finished": said.get("finished"),
            "sources": len(projects) + 2, "done": 0, "imported": {}, "errors": [], "checked": checked}  # fmt: skip
    _save(said)
    known = spend_ledger.lines()
    ids, high = {line["id"] for line in known}, _high(known)
    places = _places(projects)

    pending: dict[str, str] = {}  # the runtime logs read in this pass: kept as read only once what they gave is written

    def commit(source: str, found: list[dict[str, Any]]) -> None:
        new = [line for line in found if line["id"] not in ids]
        said["done"] += 1
        if new and spend_ledger.append(new):  # nothing counts as read: the next pass reads it all again
            said["errors"].append(f"{source}: {len(new)} line(s) not written")
            _save(said)
            return
        ids.update(line["id"] for line in new)
        for line in new:
            if (c := (line.get("usage") or {}).get("credits")) is not None:
                high[line["session"]] = max(high.get(line["session"], 0.0), float(c))
        said["imported"][source] = said["imported"].get(source, 0) + len(new)
        if source == "logs":
            checked.update(pending)
        _save(said)

    for store, repo in projects:
        try:
            commit("changes", _changes(store, repo, high))
        except Exception as exc:  # noqa: BLE001 - one project's records never stop the others'
            said["errors"].append(f"{store.name or store.root.name}: {type(exc).__name__}: {exc}"[:300])
            said["done"] += 1
    for source, read in (
        ("spotter", lambda: _looks(known, places)),
        ("logs", lambda: _logs(known, places, checked, pending)),
    ):
        try:
            commit(source, read())
        except Exception as exc:  # noqa: BLE001 - a source that cannot be read is said, never fatal
            said["errors"].append(f"{source}: {type(exc).__name__}: {exc}"[:300])
            said["done"] += 1
    said |= {"state": "done", "finished": _now().isoformat(timespec="seconds")}
    _save(said)
    return said


def _places(projects: list[tuple[Store, Path | None]]) -> dict[str, Where]:
    """Each project's place by its clone id and by its worktrees' folder name."""
    out: dict[str, Where] = {}
    for store, repo in projects:
        place = Where.of(store, repo)
        out[place.clone] = place
        if repo is not None:
            with contextlib.suppress(Exception):
                out[worktree.path_for(git_common_dir(repo), "x").parent.name] = place
    return out


def _agent(kind: str) -> str:
    return "picker" if kind == LOOKUP else roles.SESSIONS.get(kind, "")


def _steps() -> set[str]:
    return {k.value for k in StepKind}


def _changes(store: Store, repo: Path | None, high: dict[str, float]) -> list[dict[str, Any]]:
    """The step events, marks and residuals of every Change of *store*."""
    place, out, seen = Where.of(store, repo), [], dict(high)
    for slug in store.slugs():
        c = store.read(slug)
        events = [e for e in store.events(slug) if e.get("event") == "step" and e.get("session")]
        found = _events(place, slug, events)
        for line in found:  # a mark these events already reach adds nothing
            seen[line["session"]] = max(seen.get(line["session"], 0.0), float(line["usage"].get("credits") or 0.0))
        agents = {e["session"]: _agent(str(e.get("kind") or "")) for e in events}
        out += found + _marks(place, c, agents, seen)
    return out


def _base(place: Where, slug: str, **more: object) -> dict[str, Any]:
    return {"project": place.project, "name": place.name, "clone": place.clone, "change": slug} | more


def _events(place: Where, slug: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for e in events:
        usage = e.get("usage")
        unread = not isinstance(usage, dict) or "error" in usage
        if unread or (usage.get("credits") is None and not usage.get("models")):
            continue  # a held run's or an unread usage: its mark or a later report counts it
        kind = str(e.get("kind") or "")
        subagents = sum(1 for s in e.get("subagents") or [] if isinstance(s, dict) and s.get("allowed"))
        out.append(_base(place, slug, id=f"event:{_id(place.clone, slug, e)}", type="event", at=e.get("at"),
                         session=e["session"], usage=usage, agent=_agent(kind), job="" if kind in _steps() else kind,
                         step=kind if kind in _steps() else "", ending=str(e.get("ending") or ""),
                         subagents=subagents, source="import:activity"))  # fmt: skip
    return out


def _marks(place: Where, c: Change, agents: dict[str, str], high: dict[str, float]) -> list[dict[str, Any]]:
    out = []
    held = 0.0
    for session, mark in c.spend.last.items():
        held += mark.credits
        if mark.credits <= high.get(session, -1.0) + EPS and session in high:
            continue
        usage = {"credits": mark.credits, "models": {m: s.model_dump() for m, s in mark.models.items()}}
        ident = f"mark:{_id(place.clone, c.slug, session, usage)}"
        out.append(_base(place, c.slug, id=ident, type="mark", session=session, usage=usage,
                         agent=agents.get(session, ""), source="import:change"))  # fmt: skip
    if (rest := c.spend.credits - held) > EPS:
        session = f"residual:{place.clone}:{c.slug}"
        out.append(_base(place, c.slug, id=f"residual:{_id(session, round(rest, 6))}", type="residual",
                         session=session, usage={"credits": rest}, source="import:change"))  # fmt: skip
    return out


def _looks(known: list[dict[str, Any]], places: dict[str, Where]) -> list[dict[str, Any]]:
    """Spotter looks whose own lines the ledger lacks: those recorded before looks wrote it.

    A look and its Spotter record share one id, its meter's (``credit_meter.Meter.id``, the record's ``id``); time
    never decides it, since the record is made before its look's runtime starts. A record the ledger has lines for
    is still imported when its ``sdk_sessions`` name one the ledger lacks: ``spend_shares`` then counts only what the
    record holds beyond the ledger's own lines.
    """
    seen: dict[str, set[str]] = {}
    for line in known:
        if line.get("look") and line.get("type") in {"start", "end"}:
            seen.setdefault(str(line["look"]), set()).add(str(line.get("session") or ""))
    folder, out = local_home.root() / "spotter", []
    for path in sorted(folder.glob("records-*.jsonl")) if folder.is_dir() else ():
        for raw in path.read_text(encoding="utf-8").splitlines():
            with contextlib.suppress(ValueError, TypeError, KeyError, AttributeError):
                rec = json.loads(raw)
                covered = str(rec["id"]) in seen and set(rec.get("sdk_sessions") or ()) <= seen[str(rec["id"])]
                if not covered and (line := _look(rec, places)) is not None:
                    out.append(line)
    return out


def _look(rec: dict[str, Any], places: dict[str, Where]) -> dict[str, Any] | None:
    """A Spotter record as one ``look`` line; None when no look ran.

    The credit meter's record says whether its ``credits`` are known (``credits_known``); a legacy record, without
    that key, booked the 0.5 estimate when its spend was not reported, so that amount is unknown, never measured.
    """
    spent, legacy = rec.get("credits"), "credits_known" not in rec
    if rec.get("credits_known") is False:  # the credit meter's record: its spend is not known
        known = False
    elif not spent and not rec.get("sdk_sessions"):
        return None  # no look ran: skipped, or refused by its limit, before any session
    else:
        known = spent != ESTIMATE if legacy else bool(rec["credits_known"])
    place = places.get(str(rec.get("project") or ""), UNKNOWN_PROJECT if rec.get("project") else Where())
    model = str(rec.get("model") or "")
    usage = ({"credits": float(spent), "models": {model: {"credits": float(spent)}}} if known
             else {"error": "estimate" if legacy else "unknown"})  # fmt: skip
    job = f"{rec.get('look') or ''} look".strip()
    return _base(place, str(rec.get("change") or ""), id=f"look:{rec['id']}", type="look", at=rec["at"],
                 session=f"look:{rec['id']}", usage=usage, agent="spotter", job=job,
                 step=str(rec.get("step") or ""), model=model, limit=rec.get("limit"),
                 stopped=str(rec.get("stopped") or ""), stopped_by=str(rec.get("stopped_by") or ""), ending="look",
                 look=str(rec["id"]), sdk_sessions=list(rec.get("sdk_sessions") or ()),
                 source="import:spotter")  # fmt: skip


def _logs(
    known: list[dict[str, Any]], places: dict[str, Where], checked: dict[str, Any], pending: dict[str, str]
) -> list[dict[str, Any]]:
    """What the runtime's log adds: killed runs, runs whose final read failed, sessions the ledger never saw.

    A killed run gets its last usage checkpoint, a run whose final read failed the rest of its spend, and an OwlBear
    session the ledger never saw its own line. Each log read is noted in *pending*; it counts as read (*checked*)
    only once its lines are written.
    """
    now, sessions, ended = _now(), {line.get("session") for line in known}, {line.get("run") for line in known
                                                                              if line.get("type") == "end"}  # fmt: skip
    latest = _latest(known)
    out = _incomplete(known, latest, checked, pending)
    for line in known:
        if line.get("type") != "start" or line["run"] in ended or latest.get(line["session"], "") > line["at"]:
            continue  # ended, or a later run of its session accounts for what it spent
        with contextlib.suppress(ValueError, TypeError):
            if now - datetime.fromisoformat(line["at"]) < OPEN:
                continue
        if (found := _checkpoint(str(line["session"]), checked, pending)) is not None:
            at, usage = found
            out.append({k: line.get(k) for k in ("project", "name", "clone", "change", "step")}
                       | {"id": f"end:{line['run']}", "type": "end", "run": line["run"], "at": at,
                          "session": line["session"], "usage": usage, "ending": "unconfirmed",
                          "source": "import:runtime-log"})  # fmt: skip
    for sid, who in _manifest().items():
        if sid in sessions or who.get("kind") == "spotter":  # a legacy look is its Spotter record's
            continue
        if (found := _checkpoint(sid, checked, pending)) is not None:
            at, usage = found
            place, change = _owner(sid, who, places)
            job = str(who.get("job") or "")
            agent = str(who.get("role") or _agent(job or str(who.get("kind"))))
            out.append(_base(place, change, id=f"log:{_id(sid, at, usage.get('credits'))}", type="event", at=at,
                             session=sid, usage=usage, agent=agent,
                             job=job, step="" if job else str(who.get("kind") or ""), ending="",
                             source="import:runtime-log"))  # fmt: skip
    return out


def _latest(known: list[dict[str, Any]]) -> dict[str, str]:
    """Each session's latest line time in the ledger."""
    latest: dict[str, str] = {}
    for line in known:
        if (sid := line.get("session")) and isinstance(at := line.get("at"), str):
            latest[sid] = max(latest.get(sid, ""), at)
    return latest


def _incomplete(
    known: list[dict[str, Any]], latest: dict[str, str], checked: dict[str, Any], pending: dict[str, str]
) -> list[dict[str, Any]]:
    """Runs whose final read failed, completed from their session's last checkpoint when no later run covers it.

    The completing line is another ``end`` of the same run: its usage replaces the sample, its time stays.
    """
    out = []
    for line in known:
        sample = line.get("usage") or {}
        if line.get("type") != "end" or not sample.get("incomplete") or latest.get(line["session"], "") > line["at"]:
            continue
        if (found := _checkpoint(str(line["session"]), checked, pending)) is None:
            continue
        usage = found[1]
        if (usage.get("credits") or 0.0) >= (sample.get("credits") or 0.0):
            out.append({"id": f"end:{line['run']}:log", "type": "end", "run": line["run"], "session": line["session"],
                        "usage": usage, "source": "import:runtime-log"})  # fmt: skip
    return out


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


def _checkpoint(sid: str, checked: dict[str, Any], pending: dict[str, str]) -> tuple[str, dict[str, Any]] | None:
    """The session's last usage checkpoint in the runtime's log: its time and cumulative usage; None without one.

    A log read and written before, and unchanged since, is not read again; this read is noted in *pending*.
    """
    for path in (chatlogs.state() / sid / "events.jsonl", chatlogs.root() / "chatlogs" / sid / "log.jsonl.gz"):
        try:
            seen = path.stat()
        except OSError:
            continue
        mark = f"{seen.st_size}:{seen.st_mtime_ns}"
        if checked.get(sid) == mark:
            return None
        pending[sid] = mark
        last = None
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[operator]
            for raw in f:
                if '"session.usage_checkpoint"' in raw or '"session.shutdown"' in raw:
                    last = raw
        if last is None:
            return None
        with contextlib.suppress(ValueError, TypeError, KeyError):
            return _usage(json.loads(last))
        return None
    return None


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
