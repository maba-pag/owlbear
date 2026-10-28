"""Retro's units (#715, Improvement design §5): which Changes and chats are due, what a revision covers, and its gaps.

A Change is one unit (``chg:<project id>:<slug>``) judged once, in revision ``r1``, after it finished. An enrolled chat
(``chat:<session>``) is judged each time it fell quiet with a grown log: revision ``rN`` covers the log's events after
the last judged revision's cutoff, counted the way the Spotter's chat intake counts them (every readable event, a
subagent's included), so a record's ``cutoff`` places it in exactly one revision. A record is graded once, ever; one
written after its revision was judged makes a grade-only run of that revision due, and a gap record (``cutoff`` 0) is
graded not-assessable whenever it is seen. Only work finished after Retro first started (its watermark) is taken on
its own; an older Change or chat only by the button.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import sqlite3
import subprocess
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.improvement import chatlogs, retro_store, spotter
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import ACTIVITY_LIMIT

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable, Iterator, Mapping

    from owlbear_delivery_next.state_store.store import Store

    type Projects = Mapping[str, tuple[Store, Path | None]]  # each loaded project's store and clone, by project id

LINE = 8 << 20  # bytes: a longer event is left out, as the chat intake leaves it out (``chats.LINE``)
OPEN = frozenset({"open", "waiting"})  # a revision whose run has not ended
SHAPING = "the chat that shaped the brief is not attributable to the Change"
SYNTHETIC = "syn-"  # a synthetic unit's session (``retro_synthetic``)
UNREADABLE = (StoreError, sqlite3.Error, OSError, ValueError)  # a Change or its activity cannot be read


def change_id(project: str, slug: str) -> str:
    """A Change's unit id."""
    return f"chg:{project}:{slug}"


def chat_id(session: str) -> str:
    """A chat's unit id."""
    return f"chat:{session}"


def _when(text: str) -> datetime:
    at = datetime.fromisoformat(text)
    return at if at.tzinfo else at.replace(tzinfo=UTC)


# What Retro reads: the Spotter's records, Retro's manifest and its captures


def records() -> list[dict[str, Any]]:
    """Every Spotter record on this machine; an unreadable line is left out, as case intake leaves it."""
    found = []
    for path in sorted(spotter.place().glob("records-*.jsonl")):
        with contextlib.suppress(OSError):
            for line in path.read_text().splitlines():
                with contextlib.suppress(ValueError):
                    if isinstance(r := json.loads(line), dict) and r.get("id"):
                        found.append(r)
    return found


def manifest() -> list[dict[str, Any]] | None:
    """Retro's manifest lines; None when it exists but cannot be read."""
    try:
        text = (chatlogs.root() / "manifest.jsonl").read_text()
    except FileNotFoundError:
        return []
    except OSError:
        return None
    found = []
    for line in text.splitlines():
        with contextlib.suppress(ValueError):
            if isinstance(d := json.loads(line), dict) and d.get("session"):
                found.append(d)
    return found


def folder(session: str) -> Path:
    """Where *session*'s capture is kept; a synthetic one's in Retro's own folder, apart from the chatlogs."""
    if session.startswith(SYNTHETIC):
        return retro_store.place() / "synthetic" / session
    return chatlogs.root() / "chatlogs" / session


def sidecar(session: str) -> dict[str, Any]:
    """The capture's sidecar; empty when there is none or it cannot be read."""
    with contextlib.suppress(OSError, ValueError):
        said = json.loads((folder(session) / "sidecar.json").read_text())
        return said if isinstance(said, dict) else {}
    return {}


def events(session: str) -> Iterator[dict[str, Any]]:
    """The captured log's events, counted as the chat intake counts them.

    Raises:
        OSError: The capture cannot be read (``EOFError`` and ``zlib.error`` come as it).
    """
    try:
        with gzip.open(folder(session) / "log.jsonl.gz", "rb") as fh:
            for raw in fh:
                if len(raw) > LINE + 1:
                    continue
                with contextlib.suppress(ValueError):
                    if isinstance(d := json.loads(raw), dict):
                        yield d
    except (EOFError, zlib.error) as exc:
        raise OSError(str(exc)) from exc


def fingerprint(session: str) -> dict[str, Any]:
    """The capture's size and time as its log had them, and the hash of the copy."""
    said, digest = sidecar(session), hashlib.sha256()
    with contextlib.suppress(OSError), (folder(session) / "log.jsonl.gz").open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return {"size": said.get("size"), "mtime": said.get("mtime"), "sha256": digest.hexdigest()}


def exposure(session: str) -> tuple[set[str], int]:
    """The agents, skills and tools that ran in *session*'s capture, and its events.

    Raises:
        OSError: The capture cannot be read.
    """
    seen: set[str] = set()
    n = 0
    for d in events(session):
        n += 1
        kind, data = d.get("type"), d.get("data") or {}
        if not isinstance(data, dict):
            continue
        if kind == "subagent.started" and data.get("agentName"):
            seen.add(f"agent:{data['agentName']}")
        elif kind == "skill.invoked" and data.get("name"):
            seen.add(f"skill:{data['name']}")
        elif kind == "tool.execution_start" and data.get("toolName"):
            seen.add(f"tool:{data['toolName']}")
    return seen, n


def session_gaps(session: str, ended: Mapping[str, Any] | None) -> list[str]:
    """What is missing from *session*'s evidence, each named."""
    said = sidecar(session)
    if not said:
        return [f"session {session} has no capture"]
    if said.get("missing"):
        return [f"session {session}'s log was missing when it was captured"]
    gaps = []
    if said.get("provisional") and (ended is None or ended.get("provisional", True)):
        gaps.append(f"session {session}'s end was not confirmed; its capture may be incomplete")
    gaps += [
        f"output {Path(o.get('path', '')).name} of session {session}: {o.get('state')}"
        for o in said.get("outputs") or ()
        if o.get("state") != "kept"
    ]
    return gaps


# A Change's sessions


def change_sessions(lines: list[dict[str, Any]], place: str) -> list[str]:
    """The sessions that ran in the Change's worktree *place* or its reviewers' read-only copy, with replacements."""
    places = {place, f"{place}.ro"}
    found = [d["session"] for d in lines if d.get("event") == "started" and d.get("worktree") in places]
    grew = True
    while grew:
        more = [d["session"] for d in lines if d.get("replaces") in found and d["session"] not in found]
        found += more
        grew = bool(more)
    return list(dict.fromkeys(found))


def change_place(st: Store, repo: Path | None, slug: str) -> str:
    """The Change's worktree as its sessions named it; "" when it cannot be known."""
    try:
        change = st.read(slug)
    except UNREADABLE:
        return ""
    if change.names.worktree:
        return change.names.worktree
    if repo is None:
        return ""
    with contextlib.suppress(OSError, subprocess.CalledProcessError):
        return str(worktree.path_for(git_common_dir(repo), slug))
    return ""


def describe_change(uid: str, st: Store, repo: Path | None) -> dict[str, Any]:
    """A Change unit's sessions, exposure and gaps as known now.

    Raises:
        RetroError: Retro's manifest cannot be read.
    """
    slug = uid.split(":", 2)[2]
    lines = manifest()
    if lines is None:
        msg = "Retro's manifest cannot be read"
        raise retro_store.RetroError(msg)
    place, gaps, seen = change_place(st, repo, slug), [SHAPING], set()
    sessions = change_sessions(lines, place) if place else []
    if not place:
        gaps.append("the Change's worktree cannot be known, so none of its sessions is")
    ended = {d["session"]: d for d in lines if d.get("event") == "ended"}
    roles = {d["session"]: d.get("role", "") for d in lines if d.get("event") == "started"}
    seen |= {f"agent:{roles[s]}" for s in sessions if roles.get(s)}
    for session in sessions:
        gaps += session_gaps(session, ended.get(session))
        if not (said := sidecar(session)) or said.get("missing"):
            continue
        try:
            seen |= exposure(session)[0]
        except OSError as exc:
            gaps.append(f"session {session}'s capture cannot be read ({type(exc).__name__})")
    with contextlib.suppress(*UNREADABLE):
        if len(st.events(slug)) >= ACTIVITY_LIMIT:
            gaps.append(f"the Change's activity keeps only its last {ACTIVITY_LIMIT} events")
    return {
        "kind": "change",
        "family": uid,
        "project": st.root.name,
        "slug": slug,
        "sessions": sessions,
        "exposure": sorted(seen),
        "gaps": list(dict.fromkeys(gaps)),
    }


# Which records a unit holds


def unit_of(record: Mapping[str, Any]) -> str:
    """The unit a Spotter record belongs to; "" for one of neither (a replay)."""
    if record.get("step") == "chat" and record.get("session"):
        return chat_id(record["session"])
    if record.get("project") and record.get("change"):
        return change_id(record["project"], record["change"])
    return ""


def card_gaps(ids: Iterable[str]) -> list[str]:
    """Each record whose card is missing."""
    return [f"record {r}'s card is missing" for r in ids if not (spotter.place() / "cards" / f"{r}.json.gz").exists()]


def grade(record: Mapping[str, Any], rev: str, value: str, reason: str = "", **more: object) -> dict[str, Any]:
    """A grade of *record* in revision *rev*: what live delivery's gate (#717) and the page (#716) read."""
    uid = unit_of(record)
    keep = ("look", "category", "preliminary", "prompt", "cases", "session", "call", "cutoff")
    return {
        "id": f"rg-{record['id']}",
        "record": record["id"],
        "grade": value,
        "reason": reason,
        "unit": uid,
        "family": uid,
        "rev": rev,
        "provenance": "real",
        "assumptions": ["retro-grades-1"],
        "at": retro_store.now(),
        **{k: record.get(k) for k in keep},
        **more,
    }


def gap_grades(found: Iterable[Mapping[str, Any]], known: Mapping[str, Any], graded: set[str]) -> list[dict[str, Any]]:
    """A not-assessable grade for each ungraded gap record (``cutoff`` 0) of a unit Retro knows: no call needed."""
    return [
        grade(r, "", "not-assessable", r.get("skipped") or "a gap in what the Spotter could see")
        for r in found
        if not r.get("cutoff") and r["id"] not in graded and unit_of(r) in known
    ]


def _bounds(rev: Mapping[str, Any]) -> tuple[int, int]:
    return int(rev.get("from_events") or 0), int(rev.get("cutoff_events") or 0)


def late(found: Iterable[Mapping[str, Any]], known: Mapping[str, Any], graded: set[str]) -> list[dict[str, Any]]:
    """Grade-only work: records written after the judged revision they belong to was taken, by unit and revision."""
    work: dict[tuple[str, str], list[str]] = {}
    for r in found:
        uid = unit_of(r)
        if not r.get("cutoff") or r["id"] in graded or (unit := known.get(uid)) is None:
            continue
        for rev in unit.get("revisions") or ():
            low, high = _bounds(rev)
            inside = unit["kind"] == "change" or low < r["cutoff"] <= high
            if inside and rev.get("state") == "judged" and r["id"] not in rev.get("records", ()):
                work.setdefault((uid, rev["rev"]), []).append(r["id"])
                break
    return [{"unit": u, "rev": rv, "mode": "grade-only", "records": ids} for (u, rv), ids in work.items()]


# What is due


def due_changes(projects: Projects, *, change: str = "") -> list[dict[str, Any]]:
    """Changes finished after the watermark and never taken; with *change* (``project:slug``), that one, if finished."""
    mark, known = _when(retro_store.watermark()), retro_store.known()
    work = []
    for pid, (st, _repo) in projects.items():
        for slug in st.slugs():
            uid = change_id(pid, slug)
            if (change and change != f"{pid}:{slug}") or (not change and known.get(uid, {}).get("revisions")):
                continue
            with contextlib.suppress(*UNREADABLE):
                finished = st.read(slug).finished_at
                if finished is not None and (change or _when(finished.isoformat()) >= mark):
                    revs = known.get(uid, {}).get("revisions") or []
                    work.append({"unit": uid, "rev": revs[-1]["rev"] if revs else "", "mode": "judge"})
    return work


def due_chats(enrolled: list[str], now: datetime, *, chat: str = "", logs: Path | None = None) -> list[dict[str, Any]]:
    """Enrolled chats quiet for a day whose log grew after the watermark and since their last, judged, revision.

    A chat whose last revision did not end judged waits for the button, which takes it again in that revision, its
    later growth left to the next; with *chat*, that one despite the watermark, still only when enrolled and quiet. One
    whose log is shorter than a revision took was replaced: only the button offers it, and its admission refuses it.
    """
    logs = logs or chatlogs.state()
    mark, known = _when(retro_store.watermark()), retro_store.known()
    work = []
    for sid in chatlogs.finished_chats(enrolled, now, logs):
        if chat and sid != chat:
            continue
        try:
            st = (logs / sid / "events.jsonl").stat()
        except OSError:
            continue
        revs = known.get(chat_id(sid), {}).get("revisions") or []
        last = revs[-1] if revs else {}
        unfinished = bool(last) and last.get("state") != "judged"
        if not chat and (datetime.fromtimestamp(st.st_mtime, UTC) < mark or unfinished or replaced(sid, st.st_size)):
            continue
        if not unfinished and (last.get("size"), last.get("mtime")) == (st.st_size, st.st_mtime):
            continue
        work.append({"unit": chat_id(sid), "rev": last["rev"] if unfinished else "", "mode": "judge"})
    return work


def eligible(
    uid: str, enrolled: list[str], projects: Projects, logs: Path | None = None, *, fresh: bool = False
) -> str:
    """Why *uid* may not be read now; "" when it may. Checked before anything of it is read or sent.

    A chat whose revision is not yet taken (*fresh*) must still be quiet: one active again is taken once it is quiet.
    """
    kind, _, rest = uid.partition(":")
    if kind == "chat":
        return _chat_refusal(rest, enrolled, logs or chatlogs.state(), fresh=fresh)
    if kind == "chg":
        pid, _, slug = rest.partition(":")
        if pid not in projects:
            return "its project is not loaded"
        try:
            return "" if projects[pid][0].read(slug).finished_at is not None else "it is not finished"
        except UNREADABLE as exc:
            return f"it cannot be read ({type(exc).__name__})"
    return "it is no unit Retro knows"


def _chat_refusal(session: str, enrolled: list[str], logs: Path, *, fresh: bool) -> str:
    ours = chatlogs.own()
    if ours is None:
        return "Retro's manifest cannot be read, so no chat is told from OwlBear's own sessions"
    if session in ours:
        return "it is one of OwlBear's own sessions"
    if not chatlogs.chat(logs / session, enrolled, ours):
        return "it is not an enrolled chat"
    try:
        st = (logs / session / "events.jsonl").stat()
    except OSError as exc:
        return f"its log cannot be read ({type(exc).__name__})"
    return _fresh_refusal(session, st) if fresh else ""


def _fresh_refusal(session: str, st: os.stat_result) -> str:
    """Why a new revision of chat *session*, its log at *st*, may not be taken: it is active again, or was replaced."""
    if datetime.now(UTC) - datetime.fromtimestamp(st.st_mtime, UTC) < chatlogs.QUIET:
        return "it is active again; it is taken once it is quiet"
    if rev := replaced(session, st.st_size):
        return f"its log is shorter than revision {rev} took: it was replaced, and a replaced chat is not read again"
    return ""


def replaced(session: str, size: int) -> str:
    """The revision of chat *session* that took more of its log than its *size* now; "" when none did."""
    revs = (retro_store.known().get(chat_id(session)) or {}).get("revisions") or []
    return next((r["rev"] for r in reversed(revs) if int(r.get("size") or 0) > size), "")


# Taking a revision


def freeze(item: Mapping[str, Any], projects: Projects, found: list[dict[str, Any]]) -> dict[str, Any]:
    """Take *item*'s revision: a chat captured as final first; its records frozen. The revision as stored.

    Raises:
        RetroError: The unit cannot be described (its manifest is unreadable).
    """
    uid, graded = item["unit"], retro_store.graded()
    kind, _, rest = uid.partition(":")
    known = retro_store.known().get(uid) or {}
    revs = list(known.get("revisions") or [])
    if item.get("rev"):
        return next(r for r in revs if r["rev"] == item["rev"])
    if kind == "chat":
        chatlogs.capture(rest, provisional=False)
        described = {"kind": "chat", "family": uid, "sessions": [rest], "gaps": session_gaps(rest, {})}
        try:
            seen, n = exposure(rest)
        except OSError as exc:
            seen, n = set(), 0
            described["gaps"].append(f"the chat's capture cannot be read ({type(exc).__name__})")
        low = max((int(r.get("cutoff_events") or 0) for r in revs if r.get("state") == "judged"), default=0)
        mine = [r for r in found if unit_of(r) == uid and low < int(r.get("cutoff") or 0) <= n]
        rev = {"from_events": low, "cutoff_events": n, **fingerprint(rest)}
    else:
        pid = rest.split(":", 1)[0]
        described = describe_change(uid, *projects[pid])
        seen = set(described.pop("exposure"))
        mine = [r for r in found if unit_of(r) == uid and r.get("cutoff")]
        rev = {"from_events": 0, "cutoff_events": 0}
    ids = [r["id"] for r in mine if r["id"] not in graded]
    rev |= {"rev": f"r{len(revs) + 1}", "frozen_at": retro_store.now(), "records": ids, "state": "open", "run": ""}
    described["gaps"] += card_gaps(ids)

    def put(table: dict[str, Any]) -> None:
        unit = table["units"].setdefault(uid, {"revisions": [], "provenance": "real"})
        unit |= described | {"exposure": sorted(set(unit.get("exposure") or ()) | seen)}
        unit["revisions"].append(rev)

    retro_store.update(put)
    return rev


def settle(uid: str, rev: str, state: str, **fields: object) -> None:
    """Record how revision *rev* of *uid* ended (``judged``, ``stopped``, ``failed``, ``refused``) and by which run."""

    def put(table: dict[str, Any]) -> None:
        unit = table["units"][uid]
        for r in unit["revisions"]:
            if r["rev"] == rev:
                r |= {"state": state, **fields}
        if state == "judged":
            unit["judged_at"] = retro_store.now()

    retro_store.update(put)
