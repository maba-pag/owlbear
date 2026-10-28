"""Retro's judged state (#715, Improvement design §5): runs, saved answers, findings, grades and proposals.

Kept owner-only in ``~/.owlbear/retro/judged/`` beside the chatlogs, under one writer lock: ``units.json`` (what Retro
knows of each Change and chat and each revision it took; written whole), and append-only ``runs.jsonl``,
``batches.jsonl``, ``findings.jsonl``, ``grades.jsonl``, ``proposals.jsonl`` and ``requests.jsonl``. Every line has an
id; reading folds the lines by it, so a line written twice changes nothing, and a write that finds its id already kept
adds nothing (a retry or a replay reconciles by id). A paid call's raw answer is saved before anything is derived from
it; an answer that is empty, cut off or invalid is kept only as an attempt and is never reused.

Proposals, kept in the same folder under the same lock, are ``retro_proposals``. The read functions here and there are
what the Improvement page (#716) and live delivery's gate (#717) use; what rests on a retired assumption is never
returned, and synthetic work only when asked for.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping
    from pathlib import Path

LOCK = 10.0  # seconds the writer lock is waited for
GRADES = ("worth-it", "correct-not-worth-it", "wrong", "missed", "not-assessable")
UNITS = "units.json"


class RetroError(Exception):
    """Retro's state cannot be read or written as asked."""


def place() -> Path:
    """Where Retro's judged state is kept; nothing is created."""
    return local_home.root() / "retro" / "judged"


def ready() -> Path:
    """The folder, created owner-only if needed."""
    folder = place()
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    return folder


_held = threading.local()
_thread_lock = threading.RLock()


@contextlib.contextmanager
def locked() -> Iterator[None]:
    """The one writer across threads and processes; re-entrant within a thread.

    Raises:
        RetroError: Another writer holds it past ``LOCK``.
    """
    if getattr(_held, "depth", 0):
        _held.depth += 1
        try:
            yield
        finally:
            _held.depth -= 1
        return
    with _thread_lock:
        fd = os.open(ready() / "judged.lock", os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            until = time.monotonic() + LOCK
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > until:
                        msg = "another writer of Retro's state is still running"
                        raise RetroError(msg) from None
                    time.sleep(0.05)
            _held.depth = 1
            try:
                yield
            finally:
                _held.depth = 0
        finally:
            os.close(fd)


def now() -> str:
    """The time, as every file here writes it."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def digest(value: object, n: int = 12) -> str:
    """The start of the hash of *value*'s canonical JSON."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:n]


def append(name: str, *rows: Mapping[str, Any]) -> None:
    """Append *rows* to the file *name* in one write, owner-only; the caller holds ``locked``."""
    fd = os.open(ready() / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "ab") as out:
        out.write("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode())


def lines(name: str) -> list[dict[str, Any]]:
    """Every line of *name*; none when it is missing.

    Raises:
        RetroError: A line cannot be read: the file is unreadable, never taken as shorter.
    """
    try:
        text = (place() / name).read_text()
    except FileNotFoundError:
        return []
    try:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except ValueError as exc:
        msg = f"Retro's {name} cannot be read: {exc}"
        raise RetroError(msg) from exc


def retired_ids() -> set[str]:
    """The marked assumptions retired now, or whose entry cannot be read: nothing resting on those is shown."""
    gone = set()
    for name in assumptions.listed():
        try:
            live = assumptions.active(name)
        except ValueError:
            live = False
        if not live:
            gone.add(name)
    return gone


def visible(item: Mapping[str, Any], gone: set[str], *, synthetic: bool) -> bool:
    """Whether a read returns *item*: nothing resting on a retired assumption; synthetic work only when asked for."""
    if gone.intersection(item.get("assumptions") or ()):
        return False
    return synthetic or item.get("provenance", "real") != "synthetic"


# Units: what Retro knows of each Change and chat, and the time it first started (its watermark)


def table() -> dict[str, Any]:
    """``units.json``; an empty table with no watermark when it is missing.

    Raises:
        RetroError: It cannot be read.
    """
    try:
        found = json.loads((place() / UNITS).read_text())
    except FileNotFoundError:
        return {"watermark": "", "units": {}}
    except ValueError as exc:
        msg = f"Retro's {UNITS} cannot be read: {exc}"
        raise RetroError(msg) from exc
    if not isinstance(found, dict) or not isinstance(found.get("units"), dict):
        msg = f"Retro's {UNITS} is not a table of units"
        raise RetroError(msg)
    return found


def update(change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """Apply *change* to the units table under the lock and write it whole; the table as written."""
    with locked():
        found = table()
        found["watermark"] = found.get("watermark") or now()
        change(found)
        atomic_write(place() / UNITS, json.dumps(found, indent=1, ensure_ascii=False) + "\n")
        (place() / UNITS).chmod(0o600)
        return found


def watermark() -> str:
    """When Retro first started on this machine: only work finished after it is judged on its own."""
    found = table()
    return found["watermark"] or update(lambda _t: None)["watermark"]


def known() -> dict[str, dict[str, Any]]:
    """Every unit Retro knows, by id, synthetic and retired ones too: what the job itself works from."""
    return table()["units"]


def units(state: str | None = None, *, synthetic: bool = False) -> dict[str, dict[str, Any]]:
    """The units, by id, as a reader sees them; with *state*, those whose latest revision is in it."""
    gone = retired_ids()
    return {
        k: u
        for k, u in known().items()
        if visible(u, gone, synthetic=synthetic)
        and (state is None or (u.get("revisions") or [{}])[-1].get("state") == state)
    }


# Button requests (the Improvement page's, or ``owlbear improvement retro run``)


def request(by: str, change: str | None = None, chat: str | None = None, *, synthetic: str = "") -> str:
    """Queue a run of one Change (``project:slug``), one chat, or one synthetic unit (by its name); its id.

    A request is taken before its run opens, so a host that stops in between loses it and never pays twice; the
    synthetic set is queued one unit per request, so a stop loses none of its units still queued.

    Raises:
        RetroError: Not exactly one of them is named.
    """
    if sum(map(bool, (change, chat, synthetic))) != 1:
        msg = "a Retro request names exactly one Change, one chat, or the synthetic units"
        raise RetroError(msg)
    rid = f"rq-{uuid.uuid4().hex[:12]}"
    with locked():
        append(
            "requests.jsonl",
            {"id": rid, "by": by, "change": change or "", "chat": chat or "", "synthetic": synthetic, "at": now()},
        )
    return rid


def queued() -> list[dict[str, Any]]:
    """The requests not taken yet, oldest first."""
    found, taken = {}, set()
    for line in lines("requests.jsonl"):
        if line.get("taken"):
            taken.add(line["id"])
        else:
            found.setdefault(line["id"], line)
    return [r for rid, r in found.items() if rid not in taken]


def take(rid: str) -> bool:
    """Take request *rid* off the queue before it runs; whether this call took it."""
    with locked():
        if all(r["id"] != rid for r in queued()):
            return False
        append("requests.jsonl", {"id": rid, "taken": True, "at": now()})
        return True


# Runs: one unit revision each, an event log folded by run id


def run_event(run: str, event: str, **fields: object) -> None:
    """One event of *run*: ``opened``, ``frozen``, ``inflight``, ``settled``, ``waiting``, ``resumed`` or ``ended``."""
    with locked():
        append("runs.jsonl", {"run": run, "event": event, "at": now(), **fields})


def run_states() -> dict[str, dict[str, Any]]:
    """Every run's snapshot by id, in the order they opened.

    A line identical to one read before is a replay and changes nothing; an ended run stays ended; spend only grows,
    and once unknown it stays unknown.
    """
    found: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for line in lines("runs.jsonl"):
        if (mark := digest(line, 32)) in seen:
            continue
        seen.add(mark)
        run, event = line.get("run"), line.get("event")
        if event == "opened":
            fresh = {"id": run, "state": "open", "spent": 0.0, "known": True, "unsettled": [], "calls": 0, "why": ""}
            found.setdefault(run, fresh | {"result": ""} | {k: v for k, v in line.items() if k not in {"run", "event"}})
            continue
        snap = found.get(run)
        if snap is None or snap["state"] == "ended":
            continue
        snap["spent"] = max(snap["spent"], line.get("spent", 0.0))
        snap["known"] = snap["known"] and line.get("known", True)
        if event == "inflight" and line["batch"] not in snap["unsettled"]:
            snap["unsettled"].append(line["batch"])
        elif event == "settled" and line["batch"] in snap["unsettled"]:
            snap["unsettled"].remove(line["batch"])
            snap["calls"] += 1
        elif event == "frozen":
            snap["rev"] = line.get("rev", "")
        elif event in {"waiting", "resumed"}:
            snap["state"], snap["why"] = ("waiting", line.get("why", "")) if event == "waiting" else ("open", "")
            snap |= {k: line[k] for k in ("trigger", "by") if k in line}  # the button took it over
        elif event == "ended":
            snap |= {"state": "ended", "result": line.get("result", ""), "ended": line["at"]}
            snap["credits"] = line.get("credits")
    return found


def runs(limit: int = 50, *, synthetic: bool = False) -> list[dict[str, Any]]:
    """The latest *limit* runs, newest first."""
    gone = retired_ids()
    found = [r for r in run_states().values() if visible(r, gone, synthetic=synthetic)]
    return found[::-1][:limit]


# Saved answers: one per batch key; attempts are kept apart and never reused


def saved(key: str) -> dict[str, Any] | None:
    """The batch *key*'s saved answer, if a valid one was kept."""
    for line in lines("batches.jsonl"):
        if line.get("key") == key and not line.get("attempt"):
            return line
    return None


def keep(key: str, run: str, answer: object, spent: float, *, attempt: str = "", **fields: object) -> None:
    """Keep a paid call's raw answer under its batch *key* before anything is derived from it.

    An *attempt* (why the answer is unusable: empty, cut off, invalid) is kept for its spend only; a second valid
    answer for a key already kept adds nothing.
    """
    with locked():
        if not attempt and saved(key) is not None:
            return
        line = {"key": key, "run": run, "answer": answer, "spent": spent, "at": now(), **fields}
        append("batches.jsonl", line | ({"attempt": attempt} if attempt else {}))


def attempts(key: str) -> list[dict[str, Any]]:
    """The unusable answers kept for batch *key*."""
    return [line for line in lines("batches.jsonl") if line.get("key") == key and line.get("attempt")]


# Findings and grades: each kept once by its id


def _first(name: str) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for line in lines(name):
        found.setdefault(line["id"], line)
    return found


def _add(name: str, items: Iterable[Mapping[str, Any]]) -> list[str]:
    with locked():
        have, new = set(_first(name)), []
        for item in items:
            if item["id"] not in have:
                append(name, item)
                have.add(item["id"])
                new.append(item["id"])
        return new


def add_findings(items: Iterable[Mapping[str, Any]]) -> list[str]:
    """Keep each finding not kept before; the ids added."""
    return _add("findings.jsonl", items)


def add_grades(items: Iterable[Mapping[str, Any]]) -> list[str]:
    """Keep each grade not kept before (a record is graded once, ever); the ids added."""
    return _add("grades.jsonl", items)


def all_findings() -> list[dict[str, Any]]:
    """Every finding kept, hidden ones included: what proposals and pruning work from."""
    return list(_first("findings.jsonl").values())


def graded() -> set[str]:
    """Every Spotter record id graded, whatever the grade rests on."""
    return {g["record"] for g in _first("grades.jsonl").values()}


def findings(
    change: str | None = None, session: str | None = None, *, synthetic: bool = False, unit: str | None = None
) -> list[dict[str, Any]]:
    """The findings, of one Change (``project:slug``), one session or one unit when named."""
    gone = retired_ids()
    return [
        f
        for f in all_findings()
        if visible(f, gone, synthetic=synthetic)
        and (change is None or f.get("change") == change)
        and (unit is None or f.get("unit") == unit)
        and (session is None or session in (f.get("sessions") or ()))
    ]


def grades(record: str | None = None, unit: str | None = None, *, synthetic: bool = False) -> list[dict[str, Any]]:
    """The grades, of one Spotter record or one unit when named."""
    gone = retired_ids()
    return [
        g
        for g in _first("grades.jsonl").values()
        if visible(g, gone, synthetic=synthetic)
        and (record is None or g["record"] == record)
        and (unit is None or g.get("unit") == unit)
    ]


def class_grades() -> dict[tuple[str, str], dict[str, int]]:
    """For live delivery's gate (#717): each (look, category)'s real grades; preliminary ones counted apart.

    Synthetic grades are never counted; not-assessable ones are counted apart from the four assessable grades.
    """
    found: dict[tuple[str, str], dict[str, int]] = {}
    for g in grades():
        counts = found.setdefault(
            (g.get("look", ""), g.get("category", "")), dict.fromkeys((*GRADES, "preliminary"), 0)
        )
        if g.get("preliminary"):
            counts["preliminary"] += 1
        elif g["grade"] in counts:
            counts[g["grade"]] += 1
    return found
