"""Where Spotter cases come from (Improvement design §4): session families' sides, and Spotter records.

A case's session family (a Delivery Change, or a chat's session) is on one side of the split for good: ``dev`` or
the ``reserve``. The pilot's own splits are kept; any other family is assigned once by the pilot's rule (ordered by
sha256(seed + family), the first 60% dev) and persisted in ``families.json``. A Spotter record becomes a candidate
with its card frozen anew; its provenance keeps the record's own fields, an old record's as it has them.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
from typing import TYPE_CHECKING

from owlbear_delivery_next.improvement.cases import CALLS, CaseError, commit, current, freeze, locked, place, ready

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
            path = ready() / "families.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(found, indent=1, sort_keys=True) + "\n")
            tmp.chmod(0o600)
            tmp.replace(path)
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


def from_record(record: str, call: str, why: str, by: str) -> str:
    """A candidate case from the Spotter's record *record* (its card frozen anew); its id.

    Raises:
        CaseError: The record or its card cannot be found.
    """
    if call not in CALLS:
        msg = f"the call is one of {', '.join(CALLS)}"
        raise CaseError(msg)
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
    with locked():
        cur = current()
        commit(
            cur["n"],
            {cid: {"stage": "candidate", "call": call, "why": why, "example": "", "review": None}},
            by,
            f"from Spotter record {record}",
        )
    return cid
