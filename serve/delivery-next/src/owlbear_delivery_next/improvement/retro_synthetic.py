"""Retro's synthetic units (#715 gate G2, Improvement design §5): invented work for kinds no real unit shows.

Each unit in ``retro_synthetic.json`` is one short builder session with the Spotter's records of it. ``install``
writes its capture to Retro's own folder, never the chatlogs, and takes its revision in ``units.json`` marked
``synthetic``; a button run (``owlbear improvement retro run --synthetic``) then judges it through the same phases as
a real unit (``retro_judge.run``). Everything it yields carries provenance ``synthetic`` and the assumption
``retro-synthetic-1``: the real reads never return it, and no read returns it once that assumption is retired.

The ``demo`` set shows two lessons' worth of findings (a hand-off claiming tests never run) and two agent changes'
worth (a skill silent that a file is generated), plus a finding resting on a removed output. ``large`` is sized for
two judging batches at least, for the credit-stop check. A text too long for one line of the file is a list of pieces,
joined as read.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions, retro_segments
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.retro_calls import Ask, Work

if TYPE_CHECKING:
    from collections.abc import Mapping

DATA = Path(__file__).with_name("retro_synthetic.json")
PREFIX = "syn:"  # a synthetic unit's id
DEMO = "demo"
NEEDS = (assumptions.RETRO_SYNTHETIC,)
RECENT = 3  # turns a record's card shows before its moment


def specs(name: str = "") -> list[dict[str, Any]]:
    """The synthetic units: the demonstration set, or the one *name*d.

    Raises:
        RetroError: No synthetic unit has that name.
    """
    found = [_joined(s) for s in json.loads(DATA.read_text())]
    picked = [s for s in found if s["name"] == name] if name else [s for s in found if s["set"] == DEMO]
    if not picked:
        msg = f"no synthetic unit is named {name!r}"
        raise store.RetroError(msg)
    return picked


def _joined(spec: dict[str, Any]) -> dict[str, Any]:
    """*spec* with each text split into pieces in the file joined: its outcome, its turns' parts and records' fields."""

    def text(v: object) -> object:
        return "".join(v) if isinstance(v, list) else v

    turns = [[text(v) for v in t] for t in spec["turns"]]
    records = [{k: text(v) for k, v in r.items()} for r in spec["records"]]
    return {**spec, "outcome": text(spec["outcome"]), "turns": turns, "records": records}


def unit_id(spec: Mapping[str, Any]) -> str:
    """The unit id of *spec*."""
    return f"{PREFIX}{spec['name']}"


def session(spec: Mapping[str, Any]) -> str:
    """The session id of *spec*'s capture."""
    return f"{units.SYNTHETIC}{spec['name']}"


def _turn(turn: list[Any], n: int) -> list[dict[str, Any]]:
    kind, *rest = turn
    if kind in {"user", "agent"}:
        return [{"type": "user.message" if kind == "user" else "assistant.message", "data": {"content": rest[0]}}]
    tool, args, result, ok = rest
    call = f"call-{n + 1}"
    arguments = {"command": args} if tool == "bash" else {"input": args}
    return [
        {"type": "tool.execution_start", "data": {"toolName": tool, "toolCallId": call, "arguments": arguments}},
        {"type": "tool.execution_complete", "data": {"toolCallId": call, "success": ok, "result": {"content": result}}},
    ]


def _log(n: int, chars: int) -> str:
    line = (
        f"[{n:3}%] Building CXX object src/core/CMakeFiles/core.dir/module_{n:04}.cpp.o\n"
        f"warning: implicit conversion loses integer precision in module_{n:04}.cpp:{n * 7 + 3}\n"
    )
    return (line * (chars // len(line) + 1))[:chars]


def events(spec: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[int, int]]:
    """*spec*'s log events, and by turn (from 1) the number of the event that ends it."""
    out: list[dict[str, Any]] = []
    ends: dict[int, int] = {}
    fill = spec.get("filler") or {}
    for i, turn in enumerate(spec["turns"], 1):
        out += _turn(turn, len(out))
        ends[i] = len(out)
        for k in range(fill.get("calls", 0) if i == fill.get("after") else 0):
            out += _turn(["call", "bash", f"make -j8 module_{k:04}", _log(k, fill["chars"]), True], len(out))
    return out, ends


def records(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The Spotter's records of *spec*, each with its card."""
    _, ends = events(spec)
    turns = spec["turns"]
    found = []
    for r in spec["records"]:
        recent = [
            {"what": t[0], "text": " ".join(map(str, t[1:4]))} for t in turns[max(0, r["turn"] - RECENT) : r["turn"]]
        ]
        card = {"step": "build", "intent": {"task": turns[0][1]}, "moment": {"look": r["look"]}, "recent": recent}
        found.append(
            {
                "id": r["id"],
                "look": r["look"],
                "category": r["category"],
                "note": r["note"],
                "cutoff": ends[r["turn"]],
                "session": session(spec),
                "step": "synthetic",
                "provenance": "synthetic",
                "card": card,
            }
        )
    return found


def install(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Write *spec*'s capture and take its revision: the one already taken while the unit is unchanged."""
    sid, uid = session(spec), unit_id(spec)
    log, _ = events(spec)
    folder = units.folder(sid)
    store.ready()
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    body = gzip.compress("".join(json.dumps(d) + "\n" for d in log).encode(), mtime=0)
    outputs = [{"path": p, "state": s, "bytes": 0} for p, s in (spec.get("outputs") or {}).items()]
    said = {"session": sid, "size": len(body), "mtime": 0, "provisional": False, "outputs": outputs}
    for name, data in (("log.jsonl.gz", body), ("sidecar.json", json.dumps(said).encode())):
        (folder / name).write_bytes(data)
        (folder / name).chmod(0o600)
    rev = f"s-{store.digest(spec)}"
    graded = store.graded()
    described = {
        "kind": "change",
        "family": uid,
        "sessions": [sid],
        "exposure": sorted(spec["exposure"]),
        "gaps": units.session_gaps(sid, {"provisional": False}),
        "provenance": "synthetic",
        "assumptions": list(NEEDS),
    }

    def put(table: dict[str, Any]) -> None:
        unit = table["units"].setdefault(uid, {"revisions": []})
        unit |= described
        if all(r["rev"] != rev for r in unit["revisions"]):
            ids = [r["id"] for r in records(spec) if r["id"] not in graded]
            unit["revisions"].append(
                {"rev": rev, "from_events": 0, "cutoff_events": len(log), "frozen_at": store.now()}
                | {"records": ids, "state": "open", "run": ""}
            )

    found = store.update(put)["units"][uid]
    return next(r for r in found["revisions"] if r["rev"] == rev)


def work(spec: Mapping[str, Any], rev: Mapping[str, Any], run: str, ask: Ask) -> Work:
    """Run *run*'s work over *spec*'s revision *rev*, asking with *ask*."""
    held = set(rev.get("records") or ())
    unit = store.units()[unit_id(spec)]
    prepared = retro_segments.prepare([session(spec)], spec["outcome"])
    mine = [r for r in records(spec) if r["id"] in held]
    return Work(run, unit_id(spec), rev, unit, mine, prepared, ask, provenance="synthetic")
