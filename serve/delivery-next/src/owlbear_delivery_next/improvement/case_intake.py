"""Where Spotter cases come from (Improvement design §4): session families' sides, and Spotter records.

A case's session family (a Delivery Change, or a chat's session) is on one side of the split for good: ``dev`` or
the ``reserve``. The pilot's own splits are kept; any other family is assigned once by the pilot's rule (ordered by
sha256(seed + family), the first 60% dev) and persisted in ``families.json``. A Spotter record becomes a candidate
with its card frozen anew; its provenance keeps the record's own fields, an old record's as it has them. A synthetic
unit's record (Retro's demonstration) becomes one resting on Retro's synthetic assumption, so a reset leaves it out.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
from typing import TYPE_CHECKING

from owlbear_delivery_next.improvement import assumptions, retro_synthetic
from owlbear_delivery_next.improvement.cases import (
    CALLS,
    CaseError,
    commit,
    current,
    fact,
    freeze,
    locked,
    place,
    ready,
)
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Mapping

# Families: which side of the split a case's session family is on, fixed once


SPLIT_SEED = "owlbear-watcher-replay-pilot-2026-10-25"  # the pilot's seed; its 60% dev, 40% reserve
DEV = 0.6


def families() -> dict[str, dict[str, str]]:
    """Every family assigned so far: its side (``dev`` or ``reserve``) and how it was assigned."""
    try:
        return json.loads((place() / "families.json").read_text())
    except FileNotFoundError:
        return {}
    except ValueError as exc:
        msg = f"families.json cannot be read: {exc}"
        raise CaseError(msg) from exc


def assign(given: Mapping[str, tuple[str, str]]) -> dict[str, str]:
    """Persist *given* sides (family -> side, how) for families not yet assigned; every family's side afterwards.

    An assigned family keeps its side for good.
    """
    with locked():
        found = families()
        added = {f: {"side": side, "how": how} for f, (side, how) in given.items() if f not in found}
        if added:
            found |= added
            atomic_write(ready() / "families.json", json.dumps(found, indent=1, sort_keys=True) + "\n")
        return {f: v["side"] for f, v in found.items()}


def hashed(names: list[str]) -> dict[str, tuple[str, str]]:
    """New families' sides by the pilot's rule: ordered by sha256(seed + family), the first 60% (rounded) dev."""
    ranked = sorted(names, key=lambda f: hashlib.sha256((SPLIT_SEED + f).encode()).hexdigest())
    n_dev = round(DEV * len(ranked))
    return {f: ("dev" if i < n_dev else "reserve", "hashed once") for i, f in enumerate(ranked)}


def side(family: str) -> str:
    """The side of *family*: as assigned, else assigned now on its own by its hash."""
    known = families()
    if family in known:
        return known[family]["side"]
    one = "dev" if int(hashlib.sha256((SPLIT_SEED + family).encode()).hexdigest()[:8], 16) / 2**32 < DEV else "reserve"
    return assign({family: (one, "hashed once")})[family]


def _call(call: str) -> None:
    if call not in CALLS:
        msg = f"the call is one of {', '.join(CALLS)}"
        raise CaseError(msg)


def _candidate(cid: str, call: str, why: str, by: str, reason: str) -> str:
    with locked():
        cur = current()
        entry = {"stage": "candidate", "call": call, "why": why, "example": "", "review": None}
        commit(cur["n"], {cid: entry}, by, reason)
    return cid


def of_record(record: str, call: str) -> str:
    """The current candidate made from the Spotter's record *record* with *call*, else nothing.

    One with another call, or checked already, is another case of that record.
    """
    cur = current()["cases"]
    return next(
        (
            cid
            for cid in sorted(cur)
            if (cur[cid]["stage"], cur[cid].get("call")) == ("candidate", call)
            and fact(cid)["provenance"].get("record", {}).get("id") == record
        ),
        "",
    )


def from_record(record: str, call: str, why: str, by: str) -> str:
    """A candidate case from the Spotter's record *record* (its card frozen anew); its id.

    Raises:
        CaseError: The record or its card cannot be found.
    """
    _call(call)
    spot = place().parent
    found = None
    for path in sorted(spot.glob("records-*.jsonl"), reverse=True):
        for line in path.read_text().splitlines():
            with contextlib.suppress(ValueError):
                r = json.loads(line)
                if r.get("id") == record:
                    found = r
        if found:
            break
    if found is None:
        msg = f"there is no Spotter record {record}"
        raise CaseError(msg)
    try:
        with gzip.open(spot / "cards" / f"{record}.json.gz", "rt") as fh:
            the_card = json.load(fh)
    except (OSError, ValueError) as exc:
        msg = f"the card of record {record} cannot be read: {exc}"
        raise CaseError(msg) from exc
    family = f"change:{found['change']}" if found.get("change") else f"session:{found.get('session', '')}"
    keep = ("id", "at", "session", "change", "step", "look", "call", "category", "prompt", "cases", "turn")
    provenance = {"record": {k: found[k] for k in keep if k in found}}
    cid = freeze(
        the_card, {"source": "record", "provenance": provenance, "family": family, "reserve": side(family) == "reserve"}
    )
    return _candidate(cid, call, why, by, f"from Spotter record {record}")


def from_synthetic(record: str, call: str, why: str, by: str) -> str:
    """A candidate case from synthetic unit's record *record*, resting on Retro's synthetic assumption; its id.

    Raises:
        CaseError: No synthetic unit has that record, or the assumption was reset.
    """
    _call(call)
    if not assumptions.ensure(assumptions.RETRO_SYNTHETIC):
        msg = "Retro's synthetic assumption was reset: its records make no cases"
        raise CaseError(msg)
    names = [s["name"] for s in json.loads(retro_synthetic.DATA.read_text())]
    every = (r for n in names for r in retro_synthetic.records(retro_synthetic.specs(n)[0]))
    found = next((r for r in every if r["id"] == record), None)
    if found is None:
        msg = f"no synthetic unit has the record {record}"
        raise CaseError(msg)
    the_card = {**found["card"], "gaps": [*found["card"].get("gaps", []), "synthetic: an invented moment"]}
    keep = ("id", "session", "look", "category", "note")
    cid = freeze(
        the_card,
        {
            "source": "synthetic",
            "provenance": {"record": {k: found[k] for k in keep}},
            "family": f"session:{found['session']}",
            "reserve": False,
            "assumption": assumptions.RETRO_SYNTHETIC,
        },
    )
    return _candidate(cid, call, why, by, f"from synthetic record {record}")
