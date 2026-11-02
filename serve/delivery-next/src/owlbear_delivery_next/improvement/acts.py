"""What a Spotter finding does (design §4, "Modes and settings" and "Live delivery"), and the act lines that say so.

A finding acts as its category's setting says, in the setting's own words: ``steer``, ``refuse-hand-off``,
``stop-and-resume``, ``stop-and-ask`` or ``show-owner``; ``record`` and every rule below that holds it back give
``none``. Irreversible harm acts by its setting in both arms of the steered-versus-silent test, from any look, and is
never capped (D-01M5W68MMV8JCVKNKH4VJQ9V14). Otherwise:

- sample and state-change looks are record-only until Retro shows their class is worth it;
- the discretionary actions (steer, refuse the hand-off, stop and resume) act only in the ``steered`` arm, while
  showing the owner and stopping to ask him act in both: they never steer the agent;
- a finding of the same category at the same look kind after a delivered act in the same scope (the step, or the
  chat's requester turn) becomes one ``ask`` to the owner, then ``none``: never a loop;
- steering notes (steer, stop and resume) beyond the intervention cap in one scope become ``none``; hand-off refusals
  are never capped.

``show-owner`` is never sent to the agent: the record shows it. Each act is one line in the Spotter's
``outcomes-<date>.jsonl`` (kind ``act``) written before it is dispatched; later lines add its delivery, error and the
decision-conflict check's answer, and ``acts`` folds them, the last line per field winning. The counters a decision
reads are folded from the same lines, so a Spotter rebuilt within a turn (a host or follower restart) keeps them.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement.events import NOTE
from owlbear_delivery_next.improvement.spotter_store import Worker, _append

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from owlbear_delivery_next.improvement.spotter import Context, Record

TOKEN = NOTE + "{id}]"  # every note the Spotter sends into a chat starts with it, *id* its record's
HARM = "irreversible-harm"
DISCRETIONARY = frozenset({"steer", "refuse-hand-off", "stop-and-resume"})  # the steer share's actions
NOTES = frozenset({"steer", "stop-and-resume"})  # steering notes: what the intervention cap counts
UNSENT = frozenset({"none", "show-owner"})  # acts never dispatched to the agent
RECORD_ONLY = frozenset({"sample", "state-change"})
CHECKS = Worker(1)  # the decision-conflict checks: a slow one never holds the Spotter's writes


@dataclass
class Act:
    """What one record's finding did; the first line holds every field up to ``token``."""

    record: str
    at: str
    unit: str  # ``chg:<project>/<slug>`` or ``chat:<session>``, as its arm is kept
    arm: str
    session: str
    scope: str  # the step, or the chat's requester turn: the counters' key
    look: str
    category: str  # with the look kind, the repeat's key
    act: str  # the setting's own words, ``ask`` for a repeat's escalation, or ``none``
    why: str  # ``setting``, ``arm``, ``cap``, ``record-only look``, ``repeat`` or ``asked``
    harm: bool = False
    note: str = ""
    token: str = ""
    delivery: str = ""  # "" when nothing is sent; else pending, delivered, failed, unconfirmed or expired
    error: str = ""  # a failed delivery's whole error
    conflict: str = ""  # the decision-conflict check's answer as text, or why there is none


FIRST = frozenset(f.name for f in fields(Act) if f.name not in {"harm", "note", "token", "delivery", "error",
                                                                 "conflict"})  # fmt: skip


def scope(record: Record, ctx: Context) -> str:
    """The scope a record's act counts in: a chat's requester turn, or the step."""
    return record.turn if ctx.step == "chat" else ctx.step


def unit(record: Record, ctx: Context) -> str:
    """The unit whose arm the act follows."""
    return f"chat:{record.session}" if ctx.step == "chat" else f"chg:{ctx.project}/{ctx.change}"


def decide(record: Record, look: str, ctx: Context, sent: int, unresolved: Mapping[tuple[str, str], str]) -> Act:
    """What *record*'s finding does, given the steering notes already *sent* in its scope and its *unresolved* findings.

    *unresolved* maps a (category, look kind) of the scope to ``delivered`` (an act of it was) or ``asked`` (the owner
    was asked about it).
    """
    category, harm = record.category, record.category == HARM
    setting, was = ctx.actions.get(category, "record"), unresolved.get((category, look))
    rules = (  # the first that holds decides; else the setting acts
        (setting == "record", "none", "setting"),
        (look in RECORD_ONLY and not harm, "none", "record-only look"),
        (setting == "show-owner", "show-owner", "setting"),
        (was == "delivered", "ask", "repeat"),
        (was is not None, "none", "asked"),
        (not harm and setting in DISCRETIONARY and ctx.arm != "steered", "none", "arm"),
        (not harm and setting in NOTES and sent >= (ctx.cap or 0), "none", "cap"),
    )
    act, why = next(((a, w) for hit, a, w in rules if hit), (setting, "setting"))
    return Act(record=record.id, at=datetime.now(UTC).isoformat(timespec="seconds"), unit=unit(record, ctx),
               arm=str(ctx.arm), session=record.session, scope=scope(record, ctx), look=look, category=category,
               act=act, why=why, harm=harm, note=record.note, token=TOKEN.format(id=record.id),
               delivery="" if act in UNSENT else "pending")  # fmt: skip


def could_act(ctx: Context) -> bool:
    """Whether a hand-off look could answer the hand-off itself, so its submit waits for the look.

    It could when any category's setting acts in this arm: a discretionary action only in the steered arm, a stop to
    ask in either, irreversible harm by any acting setting in either; recording and showing the owner never do.
    """
    if ctx.act is None or "hand-off" not in ctx.looks:
        return False
    steered = ctx.arm == "steered"
    return any(
        setting not in {*UNSENT, "record"} and (category == HARM or setting not in DISCRETIONARY or steered)
        for category, setting in ctx.actions.items()
    )


def held_back(record: Record, ctx: Context, why: str) -> Act:
    """The act of a look that could have acted and found nothing to act on, a failed or timed-out one: *why*."""
    return Act(record=record.id, at=datetime.now(UTC).isoformat(timespec="seconds"), unit=unit(record, ctx),
               arm=str(ctx.arm), session=record.session, scope=scope(record, ctx), look=record.look,
               category=record.category, act="none", why=why)  # fmt: skip


def write(folder: Path, act: Act) -> None:
    """*act*'s first line, in *folder*'s outcomes of the day."""
    _append(folder, "outcomes", {"kind": "act", **asdict(act)})


def update(folder: Path, record: str, **changed: object) -> None:
    """A later line for *record*'s act: its delivery, error or conflict answer."""
    _append(folder, "outcomes", {"kind": "act", "record": record, **changed})


def acts(folder: Path) -> dict[str, Act]:
    """Every act in *folder*, by record, its lines folded in order; outcome lines of other kinds are left out.

    An unreadable line is left out, as the records' readers leave it; so is an act whose first line was never written.
    """
    merged: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("outcomes-*.jsonl")):
        try:
            text = path.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("kind") == "act" and d.get("record"):
                merged.setdefault(d["record"], {}).update(d)
    names = {f.name for f in fields(Act)}
    return {r: Act(**{k: v for k, v in d.items() if k in names}) for r, d in merged.items() if d.keys() >= FIRST}


def counts(folder: Path, session: str, scope_: str) -> tuple[int, dict[tuple[str, str], str]]:
    """The steering notes sent in *session*'s *scope_* and its unresolved findings, from its act lines."""
    sent, unresolved = 0, {}
    for a in acts(folder).values():
        if (a.session, a.scope) != (session, scope_):
            continue
        sent += a.act in NOTES and not a.harm and a.delivery != "failed"
        key = (a.category, a.look)
        if a.act == "ask":
            unresolved[key] = "asked"
        elif a.delivery == "delivered" and unresolved.get(key) != "asked":
            unresolved[key] = "delivered"
    return sent, unresolved


def checked(folder: Path, record: str, conflicts: Callable[[str], str] | None, change: str) -> str:
    """Ask the decision-conflict check about the state *change* and add its answer to *record*'s act; the answer.

    A check that raises or none given is kept as a ``failed`` answer with why: the record stays preliminary.
    """
    if conflicts is None:
        answer = json.dumps({"failed": "no decision-conflict check was given to this Spotter"})
    else:
        try:
            answer = conflicts(change)
        except Exception as exc:  # noqa: BLE001 - kept as the answer, whole
            answer = json.dumps({"failed": f"{type(exc).__name__}: {exc}"})
    update(folder, record, conflict=answer)
    return answer


def answered(conflict: object) -> bool:
    """Whether *conflict* is a completed check's answer: a JSON object without ``failed``."""
    try:
        said = json.loads(str(conflict or ""))
    except ValueError:
        return False
    return isinstance(said, dict) and "failed" not in said


def joined(act: Act) -> dict[str, Any]:
    """What a record shows of its act; ``acted`` is the act once delivered, ``stopped`` for a harm stop to ask.

    ``question`` is a stop to ask's note, the owner's question as the act line keeps it.
    """
    acted = act.act if act.delivery == "delivered" else ""
    if acted == "stop-and-ask" and act.harm:
        acted = "stopped"
    return {"act": act.act, "why": act.why, "arm": act.arm, "delivery": act.delivery, "error": act.error,
            "conflict": act.conflict, "acted": acted,
            "question": act.note if act.act in {"stop-and-ask", "ask"} else ""}  # fmt: skip
