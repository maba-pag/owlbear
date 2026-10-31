"""Edits of the Spotter cases the owner makes (Improvement design §4), shared by ``owlbear cases`` and the page (#716).

A stage move or a rollback is written as a new version when it leaves the active examples as they are; one that
changes them is queued as a paid regression for the machine host's job, which commits it only if it passes. A check
of candidates is queued the same way. Every edit is made of the version it names, refused once a newer one exists.
"""

from __future__ import annotations

from typing import Any

from owlbear_delivery_next.improvement import case_replay, cases
from owlbear_delivery_next.improvement.cases import CaseError, Stale


def change(edits: dict[str, Any], reason: str, parent: int, by: str) -> dict[str, Any]:
    """Write *edits*, made of version *parent*: ``{"version": n}``; or queue their regression: ``{"queued": id}``.

    Raises:
        Stale: The newest version is no longer *parent*: nothing is written or queued.
    """
    with cases.locked():
        cur = cases.current()
        if cur["n"] != parent:
            msg = f"the Spotter cases are at version {cur['n']} now, not {parent}: look again and retry"
            raise Stale(msg)
        after = cases.applied(cur["cases"], edits)
        if cases.shown(after) == cases.shown(cur["cases"]):
            return {"version": cases.commit(cur["n"], edits, by, reason)}
        request = case_replay.regression(edits, by, reason)
    return {"queued": case_replay.ask(request)}


def move(cid: str, stage: str, by: str, parent: int | None = None, **fields: str) -> dict[str, Any]:
    """Move case *cid* to *stage* (``removed`` leaves it out), with *fields* (call, why, example, reviewed_by, note).

    *parent* is the version the owner saw; the newest when not given.

    Raises:
        CaseError: The case is not in the version, or the move is not one a case can make.
        Stale: The newest version is no longer *parent*.
    """
    with cases.locked():  # the edit is made of the version it is written onto
        cur = cases.current()
        parent = cur["n"] if parent is None else parent
        if cid not in cur["cases"]:
            msg = f"case {cid} is not in version {cur['n']}"
            raise CaseError(msg)
        if stage == "removed":
            return change({cid: None}, f"{cid} removed", parent, by)
        entry = cases.edited(cid, cur["cases"][cid], stage=stage, **fields)
        return change({cid: entry}, f"{cid} to {stage}", parent, by)


def check_request(ids: list[str], by: str) -> str:
    """Queue the paid check of candidates *ids* (every candidate with a call when none is named); its request id.

    Raises:
        CaseError: A case named is not a candidate with a call, or there is none to check.
    """
    cur = cases.current()["cases"]
    chosen = ids or [cid for cid, e in sorted(cur.items()) if e["stage"] == "candidate" and e.get("call")]
    if bad := [cid for cid in chosen if cur.get(cid, {}).get("stage") != "candidate" or not cur[cid].get("call")]:
        msg = f"only candidates with a call are checked: {', '.join(bad)}"
        raise CaseError(msg)
    if not chosen:
        msg = "no candidate to check"
        raise CaseError(msg)
    request = {
        "id": f"r-{cases.digest([chosen, cases.now()])[:10]}",
        "kind": "check",
        "at": cases.now(),
        "by": by,
        "ids": {cid: cases.content(cid, cur[cid]) for cid in chosen},
    }
    return case_replay.ask(request)
