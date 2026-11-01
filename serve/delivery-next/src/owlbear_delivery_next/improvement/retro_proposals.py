"""Retro's proposals (#715, Improvement design §5): an event log folded into snapshots.

``proposals.jsonl`` in Retro's judged folder, under ``retro_store``'s lock, holds ``opened``, ``grown``, ``reviewed``
and ``state`` events, each with its own id, so a replay appends nothing twice. A proposal's open key is its
provenance, kind and what it is about (``open_key``); at most one proposal per key is open (not accepted, rejected or
redirected). New evidence for an open one grows it and makes its review stale (back to ``drafted``) until the new
evidence is reviewed; new evidence after it closed opens another with ``prior`` naming it. Real and synthetic
proposals never share a key, because the key starts with the provenance.

Retro writes ``drafted``, ``waiting`` and ``rejected``; the Improvement page (#716) writes the owner's states with
``transition``, checked against the ``token`` of what the owner saw. An accepted proposal keeps the snapshot it was
accepted on; acting on it appends ``applied`` (one artefact made, or a step of it) and ``failed`` events. A redirected
one is redrafted by ``retro-review`` into a new proposal (``redrafted``) naming it as ``prior``.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement.cases import CALLS
from owlbear_delivery_next.local_system import mask

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

FILE = "proposals.jsonl"
KINDS = ("lesson", "agent-change", "delivery-change", "look-reconsider", "spotter-case")
CLOSED = frozenset({"accepted", "rejected", "redirected"})
OWNER_STATES = frozenset({"shown", "accepted", "rejected", "redirected", "later"})
ERROR = 2_000  # characters of a failure's message kept


def steps(destination: Mapping[str, Any]) -> tuple[str, ...]:
    """The steps acting on an accepted proposal takes for *destination*: an artefact made, then what follows it."""
    if destination.get("kind") == "case":
        return ("created", "done")  # the case, then its paid check queued
    if destination.get("kind") == "issue" and destination.get("synthetic"):
        return ("created", "closed")
    return ("created",)


def token(snap: Mapping[str, Any], destination: Mapping[str, Any]) -> str:
    """What the owner saw of *snap*: its evidence, review, publishable text and *destination*; a decision names it."""
    review = [snap.get("review_digest", ""), snap.get("verdict", ""), snap.get("why", ""), snap.get("risks") or []]
    shown = [snap["id"], snap["evidence"], review, snap.get("publishable") or {}, destination]
    return store.digest(shown, 16)


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
        "direction": "",
        "redraft_of": "",
    }
    snap |= {k: v for k, v in line.items() if k not in {"eid", "proposal", "type", "at"}}
    return snap | {
        "id": line["proposal"],
        "state": "drafted",
        "history": [{"state": "drafted", "by": "retro", "at": line["at"]}],
        "accepted": {},
        "applied": [],
        "failures": [],
        "last": "",
        "redraft": "",
        "redraft_state": "",
    }


def _grown(snap: dict[str, Any], line: Mapping[str, Any]) -> None:
    snap["findings"] = [*snap["findings"], *(f for f in line["findings"] if f not in snap["findings"])]
    snap["counterexamples"] = line.get("counterexamples") or snap["counterexamples"]
    if snap["state"] not in CLOSED and snap["state"] != "drafted":
        snap["state"] = "drafted"
        snap["history"].append({"state": "drafted", "by": "retro", "at": line["at"]})


def _reviewed(snap: dict[str, Any], line: Mapping[str, Any]) -> None:
    snap |= {k: line.get(k) for k in ("verdict", "why", "risks", "publishable")}
    snap["review_digest"] = line["digest"]


def _moved(snap: dict[str, Any], line: Mapping[str, Any]) -> None:
    snap["state"] = line["state"]
    snap["history"].append({"state": line["state"], "by": line.get("by", ""), "at": line["at"]})
    snap["accepted"] = line.get("snapshot") or snap["accepted"]
    snap["direction"] = line.get("direction") or snap["direction"]


def _acted(snap: dict[str, Any], line: Mapping[str, Any]) -> None:
    if line["type"] == "applied":
        snap["applied"].append({"step": line["step"], "artefact": line["artefact"], "at": line["at"]})
    else:
        snap["failures"].insert(0, {"step": line.get("step", ""), "error": line["error"], "at": line["at"]})
    snap["last"] = line["type"]


FOLDS = {"grown": _grown, "reviewed": _reviewed, "state": _moved, "applied": _acted, "failed": _acted}


def _apply_state(snap: Mapping[str, Any]) -> str:
    if snap["state"] != "accepted":
        return ""
    if set(steps(snap["accepted"].get("destination") or {})) <= {a["step"] for a in snap["applied"]}:
        return "done"
    if snap["last"] == "failed":
        return "failed"
    return "partly" if snap["applied"] else "pending"


def folded() -> dict[str, dict[str, Any]]:
    """Every proposal's snapshot by id, in the order they opened, hidden ones included.

    Besides Retro's fields, a snapshot holds what the owner did: ``accepted`` (the snapshot he accepted),
    ``direction`` (a redirect's), ``applied`` (the artefacts made, by step), ``failures`` (newest first),
    ``apply_state`` (``""``, ``pending``, ``partly``, ``done`` or ``failed``), ``redraft`` (a redirected one's) and
    ``redraft_state`` (that redraft's state).
    """
    found: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for line in store.lines(FILE):
        if line["eid"] in seen:
            continue
        seen.add(line["eid"])
        kind, snap = line["type"], found.get(line["proposal"])
        if kind == "opened":
            found[line["proposal"]] = _opened(line)
        elif snap is not None and kind in FOLDS:
            FOLDS[kind](snap, line)
    for snap in found.values():
        snap["evidence"] = evidence(snap)
        snap["apply_state"] = _apply_state(snap)
        if (prior := found.get(snap["redraft_of"])) is not None:
            prior["redraft"], prior["redraft_state"] = snap["id"], snap["state"]
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
            n = sum(line.get("proposal") == live["id"] for line in store.lines(FILE))  # growth back to an earlier
            eid = f"gr-{live['id']}-{n}-{store.digest(grown)}"  # state is a new event, never a replay of the old
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
    """The drafted proposals, synthetic ones included: their current evidence has no review yet.

    That holds too for evidence grown back to a digest reviewed before, since growth made that review stale. None that
    rests on a retired assumption is listed.
    """
    gone = store.retired_ids()
    return [p for p in folded().values() if p["state"] == "drafted" and store.visible(p, gone, synthetic=True)]


def reviewed(proposal: str, digest: str, answer: Mapping[str, Any]) -> None:
    """Keep ``retro-review``'s *answer* for the evidence *digest*.

    A verdict on evidence still current moves the proposal to ``waiting`` (survive) or ``rejected``, in the same write.
    Its events are keyed by the proposal's growth too: evidence grown back to a digest reviewed before is reviewed anew.
    """
    with store.locked():
        snap = folded().get(proposal)
        grew = sum(line.get("proposal") == proposal and line["type"] == "grown" for line in store.lines(FILE))
        rows = [
            {
                "eid": f"rev-{proposal}-{grew}-{digest}",
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
                    "eid": f"st-{proposal}-{grew}-{digest}",
                    "proposal": proposal,
                    "type": "state",
                    "state": state,
                    "by": "retro-review",
                }
            )
        have, at = {line.get("eid") for line in store.lines(FILE)}, store.now()
        if new := [{**row, "at": at} for row in rows if row["eid"] not in have]:
            store.append(FILE, *new)


def transition(
    proposal: str,
    state: str,
    by: str,
    *,
    check: Callable[[dict[str, Any]], Mapping[str, Any] | None] | None = None,
    **fields: object,
) -> dict[str, Any]:
    """The page's move of *proposal* to *state* (shown, accepted, rejected, redirected, later), by the owner *by*.

    *check* sees the snapshot under the lock and may refuse it (the page checks the token of what the owner saw); what
    it returns goes on the ``state`` event with *fields*: ``snapshot`` on an accept, ``direction`` on a redirect. The
    new snapshot.

    Raises:
        RetroError: The state is not one the owner gives, the proposal is unknown, closed or hidden (it rests on a
            retired assumption), its evidence (first or grown) waits for its review, or *check* refused it.
    """
    if state not in OWNER_STATES:
        msg = f"{state!r} is not a state the owner gives a proposal"
        raise store.RetroError(msg)
    with store.locked():
        snap = folded().get(proposal)
        if snap is None or snap["state"] in CLOSED:
            msg = f"proposal {proposal} is {'unknown' if snap is None else snap['state']}"
            raise store.RetroError(msg)
        if not store.visible(snap, store.retired_ids(), synthetic=True):
            msg = f"proposal {proposal} is hidden: it rests on a retired assumption"
            raise store.RetroError(msg)
        if snap["state"] == "drafted" or snap.get("review_digest") != snap["evidence"]:
            msg = f"proposal {proposal}'s evidence waits for its review"
            raise store.RetroError(msg)
        taken = (check(snap) if check is not None else None) or {}
        event = {"eid": f"st-{uuid.uuid4().hex[:12]}", "proposal": proposal, "type": "state", "state": state, "by": by}
        _event(event | fields | taken)
        return folded()[proposal]


def outcome(proposal: str, kind: str, **fields: object) -> None:
    """Keep what acting on an accepted *proposal* did: ``applied`` (``artefact``, ``step``) or ``failed`` (``error``).

    An artefact applied again at the same step is a replay and adds nothing; each failure is kept, its error masked.
    """
    if kind == "applied":
        eid = f"ap-{proposal}-{fields['step']}-{store.digest(fields['artefact'])}"
    else:
        error = mask.redact(str(fields.get("error", "")))[:ERROR]
        eid, fields = f"fa-{uuid.uuid4().hex[:12]}", fields | {"error": error}
    _event({"eid": eid, "proposal": proposal, "type": kind, **fields})


def redrafted(prior: str, answer: Mapping[str, Any], direction: str) -> str:
    """Open the redraft of the redirected *prior* that ``retro-review`` gave as *answer* for *direction*; its id.

    It keeps the prior's findings, counterexamples, kind, bar, provenance, assumptions and record; its cause, target
    and mechanism are the answer's, and so is a Spotter case's call when it is one of ``cases.CALLS``. A second
    redraft of the same prior is a replay: the first one's id.

    Raises:
        RetroError: *prior* is unknown or not redirected.
    """
    with store.locked():
        snap = folded().get(prior)
        if snap is None or snap["state"] != "redirected":
            msg = f"proposal {prior} is {'unknown' if snap is None else snap['state']}, not redirected"
            raise store.RetroError(msg)
        if snap["redraft"]:
            return snap["redraft"]
        about = {k: str(answer.get(k) or "") for k in ("cause", "target", "mechanism")}
        pid = f"rp-{store.digest([prior, 'redraft'])}"
        kept = {k: snap[k] for k in ("kind", "bar", "provenance", "assumptions", "record") if k in snap}
        given = answer.get("call")
        call = {"call": given if given in CALLS else snap.get("call", "")} if snap.get("kind") == "spotter-case" else {}
        _event(
            {
                "eid": f"op-rd-{prior}",
                "proposal": pid,
                "type": "opened",
                "key": open_key(snap["provenance"], snap["kind"], about["cause"], about["target"], f"redraft:{prior}"),
                "findings": list(snap["findings"]),
                "counterexamples": dict(snap["counterexamples"]),
                "prior": prior,
                "redraft_of": prior,
                "direction": direction,
                **kept,
                **call,
                **about,
            }
        )
        return pid


def synthetic_artefacts() -> list[dict[str, Any]]:
    """Every artefact acting on synthetic proposals made, once each: what the reset lists."""
    found: dict[str, dict[str, Any]] = {}
    for snap in folded().values():
        if snap.get("provenance") == "synthetic":
            for done in snap["applied"]:
                art = done["artefact"]
                found.setdefault(store.digest([art.get("kind"), art.get("where"), art.get("ref")]), art)
    return list(found.values())
