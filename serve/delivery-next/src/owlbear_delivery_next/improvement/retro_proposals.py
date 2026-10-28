"""Retro's proposals (#715, Improvement design §5): an event log folded into snapshots.

``proposals.jsonl`` in Retro's judged folder, under ``retro_store``'s lock, holds ``opened``, ``grown``, ``reviewed``
and ``state`` events, each with its own id, so a replay appends nothing twice. A proposal's open key is its
provenance, kind and what it is about (``open_key``); at most one proposal per key is open (not accepted, rejected or
redirected). New evidence for an open one grows it and makes its review stale (back to ``drafted``) until the new
evidence is reviewed; new evidence after it closed opens another with ``prior`` naming it. Real and synthetic
proposals never share a key, because the key starts with the provenance.

Retro writes ``drafted``, ``waiting`` and ``rejected``; the Improvement page (#716) writes the owner's states with
``transition`` and acts on an accepted one itself.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import retro_store as store

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

FILE = "proposals.jsonl"
KINDS = ("lesson", "agent-change", "delivery-change", "look-reconsider", "spotter-case")
CLOSED = frozenset({"accepted", "rejected", "redirected"})
OWNER_STATES = frozenset({"shown", "accepted", "rejected", "redirected", "later"})


def open_key(provenance: str, kind: str, *about: str) -> str:
    """A proposal's open key: *provenance*, *kind*, then what it is about.

    That is the cause, target and mechanism id of a lesson or agent change, the cause and target of a Delivery change,
    or the record id of a Spotter case.
    """
    return "|".join((provenance, kind, *about))


def evidence(snap: Mapping[str, Any]) -> str:
    """The digest of a proposal's evidence: its findings and counterexample count. A review is bound to it."""
    return store.digest([sorted(snap["findings"]), snap["counterexamples"].get("count", 0)])


def _event(event: Mapping[str, Any]) -> bool:
    with store.locked():
        if any(line.get("eid") == event["eid"] for line in store.lines(FILE)):
            return False
        store.append(FILE, {**event, "at": event.get("at") or store.now()})
        return True


def _opened(line: Mapping[str, Any]) -> dict[str, Any]:
    snap = {
        "prior": "",
        "verdict": "",
        "why": "",
        "risks": [],
        "publishable": {},
        "review_digest": "",
        "counterexamples": {"count": 0, "sample": []},
        "assumptions": [],
    }
    snap |= {k: v for k, v in line.items() if k not in {"eid", "proposal", "type", "at"}}
    return snap | {
        "id": line["proposal"],
        "state": "drafted",
        "history": [{"state": "drafted", "by": "retro", "at": line["at"]}],
    }


def folded() -> dict[str, dict[str, Any]]:
    """Every proposal's snapshot by id, in the order they opened, hidden ones included."""
    found: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for line in store.lines(FILE):
        if line["eid"] in seen:
            continue
        seen.add(line["eid"])
        kind, snap = line["type"], found.get(line["proposal"])
        if kind == "opened":
            found[line["proposal"]] = _opened(line)
        elif snap is None:
            continue
        elif kind == "grown":
            snap["findings"] = [*snap["findings"], *(f for f in line["findings"] if f not in snap["findings"])]
            snap["counterexamples"] = line.get("counterexamples") or snap["counterexamples"]
            if snap["state"] not in CLOSED and snap["state"] != "drafted":
                snap["state"] = "drafted"
                snap["history"].append({"state": "drafted", "by": "retro", "at": line["at"]})
        elif kind == "reviewed":
            snap |= {k: line.get(k) for k in ("verdict", "why", "risks", "publishable")}
            snap["review_digest"] = line["digest"]
        elif kind == "state":
            snap["state"] = line["state"]
            snap["history"].append({"state": line["state"], "by": line.get("by", ""), "at": line["at"]})
    for snap in found.values():
        snap["evidence"] = evidence(snap)
    return found


def proposals(state: str | None = None, *, synthetic: bool = False) -> list[dict[str, Any]]:
    """The proposals, in one *state* when named; for the Improvement page (#716)."""
    gone = store.retired_ids()
    return [
        p
        for p in folded().values()
        if store.visible(p, gone, synthetic=synthetic) and (state is None or p["state"] == state)
    ]


def file(
    key: str, findings: Iterable[str], counterexamples: Mapping[str, Any] | None = None, **fields: object
) -> str | None:
    """File evidence under *key*: grow its open proposal, or open one; the proposal's id, None when nothing is new.

    *fields* (kind, cause, target, mechanism, bar, provenance, assumptions, ...) describe a proposal it opens. One
    opened after another with the same key closed names it as ``prior``, and only on evidence that one did not hold.
    """
    findings = list(dict.fromkeys(findings))
    with store.locked():
        same = [p for p in folded().values() if p["key"] == key]
        live = next((p for p in same if p["state"] not in CLOSED), None)
        if live is not None:
            new = [f for f in findings if f not in live["findings"]]
            moved = counterexamples is not None and dict(counterexamples) != live["counterexamples"]
            if not new and not moved:
                return live["id"]
            grown = {"findings": new} | ({"counterexamples": dict(counterexamples)} if moved else {})
            eid = f"gr-{live['id']}-{store.digest(grown)}"
            _event({"eid": eid, "proposal": live["id"], "type": "grown", **grown})
            return live["id"]
        held = {f for p in same for f in p["findings"]}
        if same and not any(f not in held for f in findings):
            return None
        pid = f"rp-{store.digest([key, sorted(findings)])}"
        _event(
            {
                "eid": f"op-{pid}",
                "proposal": pid,
                "type": "opened",
                "key": key,
                "findings": findings,
                "counterexamples": dict(counterexamples or {"count": 0, "sample": []}),
                "prior": same[-1]["id"] if same else "",
                **fields,
            }
        )
        return pid


def due_reviews() -> list[dict[str, Any]]:
    """The open proposals whose evidence has no review yet, synthetic ones included.

    None that rests on a retired assumption is listed.
    """
    gone = store.retired_ids()
    return [
        p
        for p in folded().values()
        if p["state"] == "drafted" and p["review_digest"] != p["evidence"] and store.visible(p, gone, synthetic=True)
    ]


def reviewed(proposal: str, digest: str, answer: Mapping[str, Any]) -> None:
    """Keep ``retro-review``'s *answer* for the evidence *digest*.

    A verdict on evidence still current moves the proposal to ``waiting`` (survive) or ``rejected``, in the same write.
    """
    with store.locked():
        snap = folded().get(proposal)
        rows = [
            {
                "eid": f"rev-{proposal}-{digest}",
                "proposal": proposal,
                "type": "reviewed",
                "digest": digest,
                "verdict": answer.get("verdict", ""),
                "why": answer.get("why", ""),
                "risks": list(answer.get("risks") or []),
                "publishable": dict(answer.get("publishable") or {}),
            }
        ]
        if snap is not None and snap["state"] == "drafted" and snap["evidence"] == digest:
            state = "waiting" if answer.get("verdict") == "survive" else "rejected"
            rows.append(
                {
                    "eid": f"st-{proposal}-{digest}",
                    "proposal": proposal,
                    "type": "state",
                    "state": state,
                    "by": "retro-review",
                }
            )
        have, at = {line.get("eid") for line in store.lines(FILE)}, store.now()
        if new := [{**row, "at": at} for row in rows if row["eid"] not in have]:
            store.append(FILE, *new)


def transition(proposal: str, state: str, by: str) -> None:
    """The page's move of *proposal* to *state* (shown, accepted, rejected, redirected, later), by the owner *by*.

    Raises:
        RetroError: The state is not one the owner gives, or the proposal is unknown or closed.
    """
    if state not in OWNER_STATES:
        msg = f"{state!r} is not a state the owner gives a proposal"
        raise store.RetroError(msg)
    with store.locked():
        snap = folded().get(proposal)
        if snap is None or snap["state"] in CLOSED:
            msg = f"proposal {proposal} is {'unknown' if snap is None else snap['state']}"
            raise store.RetroError(msg)
        _event({"eid": f"st-{uuid.uuid4().hex[:12]}", "proposal": proposal, "type": "state", "state": state, "by": by})
