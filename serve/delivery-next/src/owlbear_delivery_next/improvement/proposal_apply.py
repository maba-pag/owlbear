"""The owner's decision on a Retro proposal, and acting on an accepted one (#716, Improvement design §6).

A decision names the token of what the owner saw (the proposal's evidence, review, text and destination); a proposal
changed since is refused under the lock, with nothing written. An accept keeps a snapshot of what was accepted, and
acting reads only that snapshot: a proposal grown since makes no difference. Each artefact is found again before it
is made (a marker in a backlog entry's evidence or an issue's body, the same memory, the case of the same record), so
a retry after a lost response makes no second one. The reviewed text is checked for credentials, emails and home
paths before anything leaves the machine; a failure is kept on the proposal, masked, and acting can be retried.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_memory.errors import ConcurrencyError, DuplicateEntryError, ValidationError
from owlbear_memory.models import MemoryCategory

from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.improvement import case_intake, case_replay, case_review, cases
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.state_store.backlog import BacklogError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping
    from contextlib import AbstractContextManager

    from owlbear_memory.engine import MemoryEngine

    from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
    from owlbear_delivery_next.state_store.backlog import Backlog

BY = "owner (page)"
DIRECTION = 1_000  # characters of the owner's direction for a redraft
FAILURES = (ProviderError, BacklogError, ConcurrencyError, DuplicateEntryError, ValidationError, OSError, ValueError)
_acting = threading.Lock()  # one proposal acted on at a time: two clicks never make two artefacts
_writing: list[str] = []  # the owner's writes admitted and not yet ended


def working() -> list[str]:
    """The owner's writes admitted and not yet ended: what a stop when idle and an update wait for."""
    return [f"Improvement: {w}" for w in list(_writing)]


@contextmanager
def admitted(what: str, barrier: AbstractContextManager[object], gate: Callable[[], None]) -> Iterator[None]:
    """The owner's write *what*, admitted under the machine's stop *barrier* once *gate* lets it; counted till it ends.

    A stop or an update's fence takes the barrier too: either it sees this write in ``working`` and waits for it, or
    *gate* sees it and refuses the write.
    """
    with barrier:
        gate()
        _writing.append(what)
    try:
        yield
    finally:
        _writing.remove(what)


class Refused(store.RetroError):
    """A decision that is not one to make: an unknown state, or a redirect without a direction."""


@dataclass(frozen=True)
class Seams:
    """Where artefacts are made: the backlog seen from a folder ("" none), memory folders, OwlBear's issues, cases."""

    backlog: Callable[[str], Backlog]
    memory: Callable[[Path], MemoryEngine]
    issues: Callable[[], OwlbearIssues]
    case: Callable[[Mapping[str, Any]], str]  # the intake of an accepted Spotter case -> its case id
    check: Callable[[str], str]  # the paid check of one case queued -> the request id
    live: Callable[[], str] = lambda: ""  # the request this host's cases job runs now, "" none


def intake(accepted: Mapping[str, Any]) -> str:
    """The candidate case an accepted Spotter case makes: of its record, real or synthetic, with its call."""
    dest = accepted["destination"]
    make = case_intake.from_synthetic if dest.get("synthetic") else case_intake.from_record
    why = str((accepted.get("publishable") or {}).get("title") or "")[: cases.WHY]
    return make(dest["record"], dest["call"], why, BY)


def destination(
    snap: Mapping[str, Any], places: Mapping[str, targets.Place], shared_root: Path, units: Mapping[str, str]
) -> dict[str, Any]:
    """Where *snap* lands, or ``{"error": why}`` when it cannot be accepted; what the page shows and the token names."""
    try:
        return targets.resolve(snap, places, shared_root, units)
    except store.RetroError as exc:
        return {"error": str(exc)}


def decide(  # noqa: PLR0913 - the decision, what the owner saw, and where it may land
    pid: str,
    state: str,
    token: str,
    by: str,
    *,
    places: Mapping[str, targets.Place],
    shared_root: Path,
    direction: str = "",
) -> dict[str, Any]:
    """The owner's *state* for proposal *pid*, given the *token* of what he saw; the proposal after it.

    An accept keeps what was accepted; acting on it is ``apply``. A redirect keeps the *direction* and queues the
    redraft.

    Raises:
        Refused: Not a state the owner gives, or a redirect without a direction or with one too long.
        RetroError: The proposal changed since it was shown, cannot be accepted, or is closed, hidden or waiting.
    """
    if state not in props.OWNER_STATES:
        msg = f"{state!r} is not a state the owner gives a proposal"
        raise Refused(msg)
    direction = direction.strip()
    if state == "redirected" and not 0 < len(direction) <= DIRECTION:
        msg = f"a redirect says what to change, in 1 to {DIRECTION} characters"
        raise Refused(msg)
    units = targets.units_of()

    def seen(snap: dict[str, Any]) -> dict[str, Any]:
        dest = destination(snap, places, shared_root, units)
        if props.token(snap, dest) != token:
            msg = f"proposal {pid} changed since it was shown: look again"
            raise store.RetroError(msg)
        if state != "accepted":
            return {}
        if "error" in dest:
            raise store.RetroError(dest["error"])
        kept = ("kind", "target", "record", "call", "findings", "provenance", "publishable")
        return {"snapshot": {"destination": dest, **{k: snap.get(k) for k in kept}}}

    fields = {"direction": direction} if state == "redirected" else {}
    after = props.transition(pid, state, by, check=seen, **fields)
    if state == "redirected":
        store.request(by, redraft=pid)
    return after


def closing(snap: Mapping[str, Any]) -> bool:
    """Whether all that is left of accepted *snap* is closing the synthetic issue it made; a reset never stops that."""
    made = any(a["step"] == "created" for a in snap["applied"])
    issue = (snap.get("accepted") or {}).get("destination", {}).get("kind") == "issue"
    return snap["state"] == "accepted" and snap["apply_state"] != "done" and issue and made


def apply(pid: str, seams: Seams, gate: Callable[[], None] = lambda: None) -> dict[str, Any]:
    """Act on the accepted proposal *pid* from what was accepted; the proposal after it, applied or failed.

    One resting on an assumption a reset retired since makes nothing more, except closing a synthetic issue it made.
    *gate* is asked again once the proposal before it is done: a stop or a fence begun meanwhile refuses this one.

    Raises:
        RetroError: The proposal is unknown, not accepted, or rests on a retired assumption.
    """
    with _acting:
        gate()
        snap = props.folded().get(pid)
        if snap is None or snap["state"] != "accepted":
            msg = f"proposal {pid} is {'unknown' if snap is None else snap['state']}, not accepted"
            raise store.RetroError(msg)
        if snap["apply_state"] == "done":
            return snap
        accepted = snap["accepted"]
        done = {a["step"]: a["artefact"] for a in snap["applied"]}
        if not closing(snap) and not store.visible(snap, store.retired_ids(), synthetic=True):
            msg = f"proposal {pid} rests on a retired assumption: nothing more is made of it"
            raise store.RetroError(msg)
        text = accepted.get("publishable") or {}
        title, body = str(text.get("title") or "").strip(), str(text.get("body") or "").strip()
        problem = "" if title and body else "the accepted text has no title or body"
        if leaked := case_review.leaks([title, body]):
            problem = f"the accepted text holds {', '.join(leaked)}: nothing was written; redirect it"
        if problem:
            props.outcome(pid, "failed", step="", error=problem)
            return props.folded()[pid]
        act = ACTS[accepted["destination"]["kind"]]
        try:
            act(pid, accepted, (title, body), done, seams)
        except (*FAILURES, store.RetroError, cases.CaseError) as exc:
            props.outcome(pid, "failed", step="", error=f"{type(exc).__name__}: {exc}")
        return props.folded()[pid]


type Text = tuple[str, str]  # the accepted title and body
type Done = dict[str, dict[str, Any]]  # the artefact made at each step so far


def _backlog(pid: str, accepted: Mapping[str, Any], text: Text, _done: Done, seams: Seams) -> None:
    marker, (title, body) = f"retro-proposal:{pid}", text
    view = seams.backlog(accepted["destination"]["folder"])
    entry = next((e for e in view.read(fresh=True)[0].values() if marker in e.evidence), None)
    if entry is None:  # the marker last, as the newest refs are kept; a synthetic title never matches a real entry
        title = f"[synthetic] {title}" if accepted["destination"].get("synthetic") else title
        entry, _ = view.add(title, body, "retro", evidence=[*accepted["findings"], marker])
    link = f"https://github.com/{view.repository}/issues/{entry.id}"
    props.outcome(pid, "applied", step="created", artefact=_artefact("backlog", view.repository, f"#{entry.id}", link))


def _memory(pid: str, accepted: Mapping[str, Any], text: Text, _done: Done, seams: Seams) -> None:
    dest, (title, body) = accepted["destination"], text
    engine = seams.memory(Path(dest["folder"]))
    made = next(
        (e for e in engine.get_entries() if (e.title, e.source_agent, e.content) == (title, "retro", body)), None
    ) or engine.save(
        title=title,
        content=body,
        categories=[MemoryCategory.BEHAVIOUR],
        confidence=0.7,
        source_agent="retro",
        scope_agents=list(dest["roles"]),
        recommended=dest["recommended"],
    )
    props.outcome(pid, "applied", step="created", artefact=_artefact("memory", dest["folder"], made.id))


def _issue(pid: str, accepted: Mapping[str, Any], text: Text, done: Done, seams: Seams) -> None:
    gh, (title, body) = seams.issues(), text
    if "created" in done:  # only a synthetic one's closing is left: the issue made is closed, not looked for again
        made = done["created"]
        gh.close(int(made["ref"].lstrip("#")))
        props.outcome(pid, "applied", step="closed", artefact=made)
        return
    synthetic, marker = bool(accepted["destination"].get("synthetic")), f"<!-- retro-proposal:{pid} -->"
    issue = gh.find(marker)
    if issue is None:
        issue = gh.create(f"[synthetic] {title}" if synthetic else title, f"{body}\n\n{marker}")
    made = _artefact("issue", gh.repository, f"#{issue.number}", issue.url)
    props.outcome(pid, "applied", step="created", artefact=made)
    if synthetic:
        if issue.state != "closed":
            gh.close(issue.number)
        props.outcome(pid, "applied", step="closed", artefact=made)


def _case(pid: str, accepted: Mapping[str, Any], _text: Text, done: Done, seams: Seams) -> None:
    if "created" in done:
        cid = done["created"]["ref"]
    else:
        dest = accepted["destination"]
        cid = case_intake.of_record(dest["record"], dest["call"]) or seams.case(accepted)
        props.outcome(pid, "applied", step="created", artefact=_artefact("case", "Spotter cases", cid))
    rid = _checked(cid, seams.live()) or seams.check(cid)
    props.outcome(pid, "applied", step="done", artefact=_artefact("case", "Spotter cases", cid) | {"check": rid})


def _checked(cid: str, live: str) -> str:
    """The check already asked of case *cid*, else nothing.

    The host may stop between asking for it and recording it: one still queued counts, so does the *live* one this
    host's job runs now (not one an ended host left taken), and so does one that ran (or was stopped by the host's
    end) once the case has left the candidates.
    """
    asked = case_replay.queued() + [r for r in case_replay.running() if live and r.get("id") == live]
    if mine := [q["id"] for q in asked if q.get("kind") == "check" and cid in (q.get("ids") or {})]:
        return mine[-1]
    if cases.current()["cases"].get(cid, {}).get("stage") == "candidate":
        return ""
    ran = [r for r in case_replay.results() if r.get("kind") == "check"]
    return next((r["id"] for r in reversed(ran) if cid in (r.get("reviews") or r.get("ids") or {})), "")


def _artefact(kind: str, where: str, ref: str, link: str = "") -> dict[str, Any]:
    return {"kind": kind, "where": where, "ref": ref, "link": link}


ACTS: dict[str, Callable[[str, Mapping[str, Any], Text, Done, Seams], None]] = {
    "backlog": _backlog,
    "memory": _memory,
    "issue": _issue,
    "case": _case,
}
