"""The Decisions page's API (TD-419 slice 5a): the project's and Global decisions, one entry, and the owner's actions.

Reads come from the data repository's files (`decision_store.load`), text through the index. Every action is a
`decision_store.save` and answers with its receipts; the owner's actions refuse a chat's call (its ``X-OwlBear-Use``
header): a chat proposes and reads back, only the page activates, replaces, withdraws, promotes, records an
exception or resolves a conflict.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from owlbear_decisions import State
from owlbear_decisions.models import ID_PATTERN
from owlbear_delivery_next.state_store import decision_actions, decision_index, decision_store
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_decisions import Entry
    from owlbear_delivery_next.state_store.decision_actions import Receipt
    from owlbear_delivery_next.state_store.decision_store import DataView
    from owlbear_delivery_next.state_store.store import Store

NO_SHARED = "No shared repository is set up, so there are no decisions; set one with `owlbear-next data PATH`"
OWNER_ONLY = "Only the owner does this, on the Decisions page; a chat proposes with record_decision"
Revision = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Statement = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
type Where = Literal["project", "global", "all"]
type ReadBack = Literal["", "none", "pending", "done"]


class Shown(BaseModel):
    """The revision of the decision the page or chat read; a later change refuses the action."""

    model_config = ConfigDict(extra="forbid")

    revision: Revision


class Redecide(Shown):
    """``redecide``: the owner confirmed he re-decides a `decided` decision; ``reason``: why the rule changes."""

    redecide: bool = False
    reason: Text = ""


class WithdrawBody(Redecide):
    """Why it no longer applies (``reason``, required); said in the commit and its rationale."""


class Promotion(Shown):
    """Why the decision widens."""

    reason: Text = ""


class SuccessorBody(Redecide):
    """The owner's new rule: a successor that replaces the decision, or an exception to a Global one."""

    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    statement: Statement
    rationale: Text = ""
    words: Text = ""


class KeepBody(BaseModel):
    """The revisions the page showed of the decision kept and of each competing successor, and why it stays."""

    model_config = ConfigDict(extra="forbid")

    revisions: dict[Annotated[str, StringConstraints(pattern=ID_PATTERN)], Revision] = Field(max_length=20)
    reason: Text = ""


class ReadBackBody(Shown):
    """The owner's answer when the decision was read back to him."""

    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ProposalBody(BaseModel):
    """A chat's proposed decision: always a draft the owner activates."""

    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    topic: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] = ""
    statement: Statement
    rationale: Text = ""
    words: Text = ""
    replaces: Annotated[str, StringConstraints(pattern=f"{ID_PATTERN}|^$")] = ""
    reason: Text = ""


def owner(request: Request) -> None:
    """Refuse a chat tool's call: these writes are the owner's, made on the page."""
    if request.headers.get("x-owlbear-use", "").lower() == "chat":
        raise HTTPException(403, OWNER_ONLY)


def _row(view: DataView, entry: Entry) -> dict[str, Any]:
    d = entry.decision
    out = d.model_dump(mode="json", include={"id", "aliases", "title", "topic", "statement", "scope", "project"})
    out |= d.model_dump(mode="json", include={"change", "origin", "state", "conflict", "read_back", "created_at"})
    found = view.snapshot.findings_for(d.id)
    return out | {"revision": d.revision, "active": view.snapshot.active(d.id), "findings": len(found)}


def _linked(view: DataView, entry: Entry) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Its links, then the links to it, each with the other decision's title and state when it is in view."""

    def named(link_type: str, other: str) -> dict[str, str]:
        found = view.snapshot.get(other)
        d = found.decision if found else None
        title, state, origin = (d.title, str(d.state), str(d.origin)) if d else ("not in this view", "", "")
        return {"type": link_type, "id": other, "title": title, "state": state, "origin": origin}

    out = [named(str(link.type), link.target) for link in entry.decision.links]
    into = [
        named(str(link.type), e.decision.id)
        for e in view.snapshot.entries
        for link in e.decision.links
        if link.target == entry.decision.id
    ]
    return out, into


def _history(store: Store, entry: Entry) -> list[dict[str, str]]:
    """The data repository's commits of the decision's file, newest first."""
    shared = store.shared
    if shared is None:
        return []
    rel = entry.path.relative_to(shared.root).as_posix()
    said = shared.git("log", "-n", "30", "--format=%H%x1f%cI%x1f%s", "--", rel)
    if said.returncode:
        return []
    rows = (line.split("\x1f", 2) for line in said.stdout.splitlines() if line.count("\x1f") == 2)  # noqa: PLR2004
    return [{"commit": commit[:12], "at": at, "subject": subject} for commit, at, subject in rows]


def pinning(store: Store, decision_id: str) -> list[dict[str, Any]]:
    """The Changes of *store* whose decision baseline pins *decision_id*, and whether it applied to them."""
    found = []
    for slug in store.slugs():
        try:
            c = store.read(slug)
        except StoreError:
            continue
        pin = c.decisions_baseline
        if pin and decision_id in pin.revisions:
            found.append({
                "slug": slug, "handle": c.handle, "title": c.brief.title, "step": str(c.step.kind),
                "applies": decision_id in pin.said, "revision": pin.revisions[decision_id],
            })  # fmt: skip
    return found


def _shown(d: dict[str, Any], where: Where, state: str, read_back: ReadBack, *, retired: bool) -> bool:
    """Within the scope filter, and in the state asked for: by default every one but the retired ones."""
    scope = where == "all" or (d["scope"] == "global") == (where == "global")
    kept = d["state"] == state if state else retired or d["state"] not in {str(s) for s in decision_actions.RETIRED}
    back = read_back in {"", d["read_back"]} or (read_back == "done" and d["read_back"] not in {"none", "pending"})
    return scope and kept and back


def _receipts(work: Callable[[], list[Receipt]]) -> dict[str, Any]:
    try:
        done = work()
    except decision_actions.Refused as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except decision_store.DecisionsUnavailable as exc:
        raise HTTPException(409, f"{exc} ({exc.action})") from exc
    return {"receipts": [asdict(r) for r in done], "saved": bool(done) and all(r.saved for r in done)}


def _view(store: Store) -> DataView:
    try:
        return decision_store.load(store.shared, store.name)
    except decision_store.DecisionsUnavailable as exc:
        raise HTTPException(409, f"{exc} ({exc.action})") from exc


def router(store: Store) -> APIRouter:
    """The decision routes; the caller adds the token check."""
    routes = APIRouter()
    mine: list[Any] = [Depends(owner)]

    @routes.get("/decisions")
    def listed(  # noqa: PLR0913 - the page's filters
        *,
        where: Where = "all",
        text: Annotated[str, Query(max_length=200)] = "",
        topic: Annotated[str, Query(max_length=80)] = "",
        origin: Annotated[str, Query(max_length=16)] = "",
        state: Annotated[str, Query(max_length=16)] = "",
        read_back: ReadBack = "",
        retired: bool = False,
    ) -> dict[str, Any]:
        if store.shared is None:
            return {"available": False, "reason": NO_SHARED, "decisions": []}
        try:
            view = decision_store.load(store.shared, store.name)
            ids = None
            if text.strip():
                hits = decision_index.search(text, store.name, include_retired=True, limit=1000, view=view)
                ids = {h.id for h in hits}
        except StoreError as exc:
            return {"available": False, "reason": f"{exc} ({exc.action})", "decisions": []}
        rows = [_row(view, e) for e in view.snapshot.entries if ids is None or e.decision.id in ids]
        topics = sorted({e.decision.topic for e in view.snapshot.entries if e.decision.topic})
        kept = [
            r
            for r in rows
            if _shown(r, where, state, read_back, retired=retired) and topic in {"", r["topic"]}
            and origin in {"", r["origin"]}
        ]  # fmt: skip
        return {
            "available": True, "project": store.name, "commit": view.commit, "topics": topics,
            "states": [str(s) for s in State], "total": len(view.snapshot.entries), "decisions": kept,
        }  # fmt: skip

    @routes.get("/decisions/{decision_id}")
    def one(decision_id: str) -> dict[str, Any]:
        view = _view(store)
        entry = view.snapshot.get(decision_id)
        if entry is None:
            raise HTTPException(404, "no such decision in this project's view")
        d, (links, linked_from) = entry.decision, _linked(view, entry)
        more = d.model_dump(mode="json", include={"rationale", "consequences", "applies_to", "actor", "source"})
        problems = [{"rule": f.rule, "message": f.message} for f in view.snapshot.findings_for(d.id)]
        rivals = [r.model_dump(mode="json", include={"id", "title"}) | {"revision": r.revision}
                  for r in decision_actions.rivals(view, d, store.shared)]  # fmt: skip
        try:
            redecide = d.state is State.DRAFT and decision_actions.redecision(store.shared, view, d)
        except decision_store.DecisionsUnavailable as exc:
            raise HTTPException(409, f"{exc} ({exc.action})") from exc
        return _row(view, entry) | more | {
            "owner_words": [w.model_dump(mode="json") for w in d.owner_words], "links": links,
            "linked_from": linked_from, "problems": problems, "history": _history(store, entry),
            "changes": pinning(store, d.id), "rivals": rivals, "redecide": redecide,
        }  # fmt: skip

    _owner_routes(routes, store, mine)
    _shared_routes(routes, store)
    return routes


def _owner_routes(routes: APIRouter, store: Store, mine: list[Any]) -> None:
    """The owner's actions; a chat's call is refused."""
    shared, name, act = store.shared, store.name, decision_actions

    @routes.post("/decisions/{decision_id}/replace", dependencies=mine)
    def replace(decision_id: str, body: SuccessorBody) -> dict[str, Any]:
        return _receipts(lambda: act.replace(
            shared, name, decision_id, body.revision, title=body.title, statement=body.statement,
            rationale=body.rationale, words=body.words, reason=body.reason, redecided=body.redecide,
        ))  # fmt: skip

    @routes.post("/decisions/{decision_id}/withdraw", dependencies=mine)
    def withdraw(decision_id: str, body: WithdrawBody) -> dict[str, Any]:
        return _receipts(lambda: act.withdraw(
            shared, name, decision_id, body.revision, reason=body.reason, redecided=body.redecide))  # fmt: skip

    @routes.post("/decisions/{decision_id}/activate", dependencies=mine)
    def activate(decision_id: str, body: Redecide) -> dict[str, Any]:
        return _receipts(lambda: act.activate(
            shared, name, decision_id, body.revision, reason=body.reason, redecided=body.redecide))  # fmt: skip

    @routes.post("/decisions/{decision_id}/promote", dependencies=mine)
    def promote(decision_id: str, body: Promotion) -> dict[str, Any]:
        return _receipts(lambda: act.promote(shared, name, decision_id, body.revision, reason=body.reason))

    @routes.post("/decisions/{decision_id}/exception", dependencies=mine)
    def exception(decision_id: str, body: SuccessorBody) -> dict[str, Any]:
        return _receipts(lambda: act.exception(
            shared, name, decision_id, body.revision, title=body.title, statement=body.statement,
            rationale=body.rationale, words=body.words,
        ))  # fmt: skip

    @routes.post("/decisions/{decision_id}/keep", dependencies=mine)
    def keep(decision_id: str, body: KeepBody) -> dict[str, Any]:
        return _receipts(lambda: act.keep(shared, name, decision_id, body.revisions, reason=body.reason))


def _shared_routes(routes: APIRouter, store: Store) -> None:
    """What a chat may do as well as the page: propose a draft, record a read-back."""

    @routes.post("/decisions/propose")
    def propose(body: ProposalBody) -> dict[str, Any]:
        return _receipts(lambda: decision_actions.propose(
            store.shared, store.name, title=body.title, topic=body.topic, statement=body.statement,
            rationale=body.rationale, words=body.words, replaces=body.replaces, reason=body.reason,
        ))  # fmt: skip

    @routes.post("/decisions/{decision_id}/read-back")
    def read_back(decision_id: str, body: ReadBackBody, request: Request) -> dict[str, Any]:
        by = "chat" if request.headers.get("x-owlbear-use", "").lower() == "chat" else "owner"
        return _receipts(lambda: decision_actions.read_back(
            store.shared, store.name, decision_id, body.revision, answer=body.answer, by=by))  # fmt: skip
