"""The spend the runtime's own log of an OwlBear session holds: what ``spend_reconcile`` imports from it.

The log is ``~/.copilot/session-state/<id>/events.jsonl``, else Retro's copy. It completes a run the ledger left open
for ``OPEN`` (killed), a run that ended with its usage unread, unknown or a lower bound, and a session only Retro's
chatlogs manifest names (curator, design pack and lookup runs before the ledger). Its usage stays provisional until
the log shows the session shut down, and the log is read again whenever it changes.
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
from owlbear_delivery_next.runtimes import chatlogs
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.state_store import spend_shares
from owlbear_delivery_next.state_store.spend_ledger import Where

if TYPE_CHECKING:
    from collections.abc import Callable

OPEN = timedelta(hours=3)  # a run still open after this was killed: its runtime's log says what it spent
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

    A killed run, an ended run whose usage is unread, unknown or a lower bound, and an OwlBear session no other record
    names get the log's latest usage as another ``end`` of their own run (``log:<session>`` for the last). Each line's
    id is its content's, so a later, larger checkpoint is a new line, and ``spend_shares`` keeps a run's largest usage.
    Until the log shows the session shut down, its usage stays provisional (``incomplete``) and the log is read again
    whenever it changes. Each log read is noted in *pending*; it counts as read (*checked*) only once its lines are
    written.
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
        if (read := _checkpoint(str(run["session"]), checked, pending)) is not None:
            at, usage, final = read
            out.append({k: run.get(k) for k in ("project", "name", "clone", "change", "step")}
                       | _correction(run["run"], str(run["session"]), at, usage, final)
                       | {"ending": "unconfirmed"})  # fmt: skip
    sessions = {line.get("session") for line in known}
    for sid, who in _manifest().items():
        if sid in sessions or who.get("kind") == "spotter":  # its runs say it; a legacy look is its Spotter record's
            continue
        if (read := _checkpoint(sid, checked, pending)) is not None:
            at, usage, final = read
            place, change = _owner(sid, who, places)
            job = str(who.get("job") or "")
            role = str(who.get("role") or agent(job or str(who.get("kind"))))
            out.append(base(place, change, agent=role, job=job, step="" if job else str(who.get("kind") or ""),
                             ending="") | _correction(f"log:{sid}", sid, at, usage, final))  # fmt: skip
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
    """Ended runs whose usage is unread, unknown or a lower bound, completed from their session's log.

    Not when a later run of the session accounts for what it spent; a lower bound is replaced only by at least as much.
    """
    out = []
    for run in found:
        usage = run.get("usage")
        if not run.get("ended") or run.get("line") != "end" or usage is None:
            continue
        unread = spend_shares.unread(usage)
        if not unread and not usage.get("incomplete"):
            continue
        if later(run):
            continue
        if (read := _checkpoint(str(run["session"]), checked, pending)) is None:
            continue
        at, got, final = read
        if unread or got["credits"] >= (usage.get("credits") or 0.0):
            out.append(_correction(run["run"], str(run["session"]), at, got, final))
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


def _checkpoint(sid: str, checked: dict[str, Any], pending: dict[str, str]) -> tuple[str, dict[str, Any], bool] | None:
    """The session's latest usage in the runtime's log: its time, cumulative usage and whether it is final.

    It is final when the session shut down and was not resumed since; None without one.
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
        last, final = None, False
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[operator]
            for raw in f:
                kind = _kind(raw)
                if kind in {"session.usage_checkpoint", "session.shutdown"}:
                    last, final = raw, kind == "session.shutdown"
                elif kind in {"session.start", "session.resume"}:
                    final = False
        if last is None:
            return None
        with contextlib.suppress(ValueError, TypeError, KeyError):
            if (got := _usage(json.loads(last))) is not None:
                return (*got, final)
        return None
    return None


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
