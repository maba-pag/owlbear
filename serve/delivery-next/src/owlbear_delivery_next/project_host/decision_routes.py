"""The Decisions page's API (TD-419 slice 5a): the project's and Global decisions, one entry, and the owner's actions.

Reads come from the data repository's files (`decision_store.load`), text through the index. Every action is a
`decision_store.save` and answers with its receipts; the owner's actions refuse a chat's call (its ``X-OwlBear-Use``
header): a chat records what the owner confirmed (in force at once, TD-450) or proposes a draft, retires what he
confirmed retiring, queues and records read-backs; only the page activates, promotes, records an exception, resolves
a conflict or ignores a read-back for now. ``where=owlbear`` reads and acts on OwlBear's own decisions
(owlbear-data's ``owlbear/`` folder) and Global, though OwlBear's repository is not a registered project (TD-435);
the machine host mounts the same routes for them, the folder fixed, for chats in OwlBear's workspace. The list
leads with the read-back queue of its scope (TD-427).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from owlbear_decisions import Origin, ReadBackKind, Scope, State
from owlbear_decisions.models import ID_PATTERN
from owlbear_delivery_next.project_host import impact_routes
from owlbear_delivery_next.state_store import (
    decision_actions,
    decision_impact,
    decision_index,
    decision_origin,
    decision_store,
    read_backs,
)
from owlbear_delivery_next.state_store.decision_actions import Effect
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from owlbear_decisions import Entry
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.decision_actions import Receipt
    from owlbear_delivery_next.state_store.decision_store import DataView
    from owlbear_delivery_next.state_store.store import Store

NO_SHARED = "No shared repository is set up, so there are no decisions; set one with `owlbear-next data PATH`"
OWNER_ONLY = "Only the owner does this, on the Decisions page; a chat proposes with record_decision"
UNCONFIRMED = "only the owner retires a decision: read the retirement back to him, then pass confirmed=true"
Revision = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Statement = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
type Where = Literal["project", "global", "all", "owlbear"]
type ReadBack = Literal["", "none", "pending", "done"]
OWLBEAR = "owlbear"  # OwlBear's own folder in owlbear-data, shown beside Global without registering it (TD-435)
ACTIONS = {  # a commit subject's first word after "decisions: " -> the action shown; older subjects' words included
    **{a: a for a in ("replace", "withdraw", "activate", "promote", "exception", "keep", "read-back",
                      "queue-read-back", "propose", "record", "accept-existing", "conflict", "correct-origin")},
    "proposed": "propose", "queue": "queue-read-back",
}  # fmt: skip


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


class RetireBody(WithdrawBody):
    """A chat's withdrawal: ``confirmed`` says the owner confirmed retiring it there."""

    confirmed: bool = False


class Promotion(Shown):
    """Why the decision widens."""

    reason: Text = ""


class SuccessorBody(Redecide):
    """The owner's new rule: a successor that replaces the decision, or an exception to a Global one.

    Made on the page, it is his and confirmed today; ``confirmed`` says so and carries no words (TD-449).
    """

    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    statement: Statement
    rationale: Text = ""
    confirmed: bool = False


class ReplaceBody(SuccessorBody):
    """``effect``: the owner's mark, forbids existing behaviour or wording only; empty is unknown (TD-428)."""

    effect: Effect = ""


class ActivateBody(Redecide):
    """Activating a draft; ``effect`` marks a replacement as for `ReplaceBody`."""

    effect: Effect = ""


class KeepBody(BaseModel):
    """The revisions the page showed of the decision kept and of each competing successor, and why it stays."""

    model_config = ConfigDict(extra="forbid")

    revisions: dict[Annotated[str, StringConstraints(pattern=ID_PATTERN)], Revision] = Field(max_length=20)
    reason: Text = ""


class ReadBackBody(Shown):
    """``confirmed``: the owner confirmed the statement as it stands, read back to him; no answer is sent."""

    confirmed: bool = False


class CorrectBody(ReadBackBody):
    """``origin``: the lower origin the owner stated; ``reason``: why, in the shaper's words, never his."""

    origin: Literal["approved", "autonomous"]
    reason: Text = ""


class QueueBody(BaseModel):
    """Why the decision is read back again and how urgent, against the revision the caller read."""

    model_config = ConfigDict(extra="forbid")

    why: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]
    kind: ReadBackKind
    revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class LookupBody(BaseModel):
    """A lead chat's question: which decisions govern it."""

    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ProposalBody(BaseModel):
    """A chat's decision: in force at once when the owner confirmed it (``confirmed``), else a draft he activates.

    ``scope``: the view's own folder or Global. A replacement names the ``revision`` of what it replaces as read,
    whether the owner re-decided a `decided` one (``redecide``) and his ``effect`` mark (TD-428).
    """

    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    topic: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] = ""
    statement: Statement
    rationale: Text = ""
    confirmed: bool = False
    scope: Literal["here", "global"] = "here"
    replaces: Annotated[str, StringConstraints(pattern=f"{ID_PATTERN}|^$")] = ""
    revision: Annotated[str, StringConstraints(pattern=r"^([0-9a-f]{64})?$")] = ""
    reason: Text = ""
    redecide: bool = False
    effect: Effect = ""


def owner(request: Request) -> None:
    """Refuse a chat tool's call: these writes are the owner's, made on the page."""
    if request.headers.get("x-owlbear-use", "").lower() == "chat":
        raise HTTPException(403, OWNER_ONLY)


def _row(view: DataView, entry: Entry) -> dict[str, Any]:
    d = entry.decision
    out = d.model_dump(mode="json", include={"id", "aliases", "title", "topic", "statement", "scope", "project"})
    out |= d.model_dump(mode="json", include={"change", "origin", "state", "conflict", "read_back", "inherited"})
    out |= d.model_dump(mode="json", include={"created_at"})
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


def _history(shared: DataRepo | None, entry: Entry) -> list[dict[str, str]]:
    """The data repository's commits of the decision's file, newest first, each by its action word only."""
    if shared is None:
        return []
    rel = entry.path.relative_to(shared.root).as_posix()
    said = shared.git("log", "-n", "30", "--format=%H%x1f%cI%x1f%s", "--", rel)
    if said.returncode:
        return []
    rows = (line.split("\x1f", 2) for line in said.stdout.splitlines() if line.count("\x1f") == 2)  # noqa: PLR2004
    return [{"commit": commit[:12], "at": at, "action": _action(subject)} for commit, at, subject in rows]


def _action(subject: str) -> str:
    """A commit's known action word, else "changed": an older subject may hold words a person typed (TD-449)."""
    if not subject.startswith(prefix := "decisions: "):
        return "changed"
    rest = subject.removeprefix(prefix)
    word = "read-back" if rest.startswith("read back ") else rest.split(" ", 1)[0]
    return ACTIONS.get(word, "changed")


def _shown(d: dict[str, Any], where: Where, state: str, read_back: ReadBack, *, retired: bool) -> bool:
    """Within the scope filter, and in the state asked for: by default every one but the retired ones."""
    scope = _within(d, where)
    kept = d["state"] == state if state else retired or d["state"] not in {str(s) for s in decision_actions.RETIRED}
    back = read_back in {"", d["read_back"]} or (read_back == "done" and d["read_back"] not in {"none", "pending"})
    return scope and kept and back


def _within(d: dict[str, Any], where: Where) -> bool:
    """Whether the decision lies in the scope filter; OwlBear's view holds OwlBear's decisions and Global ones."""
    return where in {"all", OWLBEAR} or (d["scope"] == "global") == (where == "global")


def _receipts(work: Callable[[], list[Receipt]]) -> dict[str, Any]:
    try:
        done = work()
    except decision_actions.Refused as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except decision_store.DecisionsUnavailable as exc:
        raise HTTPException(409, f"{exc} ({exc.action})") from exc
    return {"receipts": [asdict(r) for r in done], "saved": bool(done) and all(r.saved for r in done)}


def _view(shared: DataRepo | None, project: str) -> DataView:
    try:
        return decision_store.load(shared, project)
    except decision_store.DecisionsUnavailable as exc:
        raise HTTPException(409, f"{exc} ({exc.action})") from exc


def _queue(store: Store | None, view: DataView, where: Where) -> list[dict[str, Any]]:
    """The read-backs waiting in the scope filter, in queue order."""
    ignored = read_backs.marks(store)["ignored"]
    items = [read_backs.item(q, ignored) for q in read_backs.waiting(store, view)]
    return [i for i in items if _within(i, where)]


def scoped(where: Where = "all") -> str:
    """OwlBear's folder for ``where=owlbear`` (TD-435), else empty: the host's own project."""
    return OWLBEAR if where == OWLBEAR else ""


In = Annotated[str, Depends(scoped)]  # the project folder a call reads and acts in


type Shared = Callable[[], DataRepo | None]
type Places = Callable[[], Sequence[decision_impact.Place]]  # the projects a change of mind's impact report covers
type At = Callable[[str], str]  # the folder a call acts in: OwlBear's for ``where=owlbear``, else the router's own


def project(store: Store, repo: Callable[[], Path] | None = None) -> APIRouter:
    """A project host's routes over its store's folder; *repo* is the project's clone, for the impact report."""

    def here() -> list[decision_impact.Place]:
        known = repo() if repo else None
        return [decision_impact.Place(store.name, known, store, "" if known else "this host does not know its clone")]

    return router(lambda: store.shared, lambda: store.name, here, store)  # Settings may rename the folder


def router(shared: Shared, folder: Callable[[], str], places: Places, store: Store | None = None) -> APIRouter:
    """The decision routes over the view of the folder *folder* names at each call; the caller adds the token check.

    Without a project *store* (OwlBear's own decisions on the machine host) ignored read-backs and the Changes
    pinning a decision are left out.
    """
    routes = APIRouter(route_class=impact_routes.Quiet)
    mine: list[Any] = [Depends(owner)]

    def at(scope: str) -> str:
        return scope or folder()

    routes.include_router(impact_routes.router(shared, places, mine))

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
        if (data := shared()) is None:
            return {"available": False, "reason": NO_SHARED, "decisions": []}
        project = at(scoped(where))
        try:
            view = decision_store.load(data, project)
            ids = None
            if text.strip():
                hits = decision_index.search(text, project, include_retired=True, limit=1000, view=view)
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
            "available": True, "project": project, "commit": view.commit, "topics": topics,
            "states": [str(s) for s in State], "total": len(view.snapshot.entries), "decisions": kept,
            "queue": _queue(store, view, where),
        }  # fmt: skip

    @routes.get("/decisions/{decision_id}")
    def one(decision_id: str, project: In) -> dict[str, Any]:
        data = shared()
        view = _view(data, at(project))
        entry = view.snapshot.get(decision_id)
        if entry is None:
            raise HTTPException(404, "no such decision in this project's view")
        d, (links, linked_from) = entry.decision, _linked(view, entry)
        more = d.model_dump(mode="json", include={"rationale", "consequences", "actor", "source"})
        problems = [{"rule": f.rule, "message": f.message} for f in view.snapshot.findings_for(d.id)]
        rivals = [r.model_dump(mode="json", include={"id", "title"}) | {"revision": r.revision}
                  for r in decision_actions.rivals(view, d, data)]  # fmt: skip
        try:
            redecide = d.state is State.DRAFT and decision_actions.redecision(data, view, d)
        except decision_store.DecisionsUnavailable as exc:
            raise HTTPException(409, f"{exc} ({exc.action})") from exc
        return _row(view, entry) | more | {
            "links": links,
            "linked_from": linked_from, "problems": problems, "history": _history(data, entry),
            "changes": decision_impact.pinning(store, d.id) if store else [], "rivals": rivals, "redecide": redecide,
        }  # fmt: skip

    _owner_routes(routes, shared, at, mine)
    if store is not None:
        _ignore_route(routes, store, at, mine)
    _shared_routes(routes, shared, at, places)
    _lookup_route(routes, shared, folder, store)
    return routes


def _lookup_route(routes: APIRouter, shared: Shared, folder: Callable[[], str], store: Store | None) -> None:
    """A lead chat's lookup: the picker over the folder's and Global decisions in force (TD-456, TD-459)."""
    chats = lookup.Chats()  # this host's: one lookup at a time (TD-336)

    @routes.post("/decisions/lookup")
    def look_up(body: LookupBody) -> dict[str, Any]:
        return chats(shared(), folder(), body.question, store.settings if store else None)


def _confirmed(body: SuccessorBody) -> None:
    """A successor is the owner's confirmed rule (`decided`, read back today); an unconfirmed one is refused."""
    if not body.confirmed:
        raise HTTPException(422, decision_actions.NOT_CONFIRMED)


def _owner_routes(routes: APIRouter, shared: Shared, at: At, mine: list[Any]) -> None:
    """The owner's actions; a chat's call is refused."""
    act = decision_actions

    @routes.post("/decisions/{decision_id}/replace", dependencies=mine)
    def replace(decision_id: str, body: ReplaceBody, project: In) -> dict[str, Any]:
        _confirmed(body)
        return _receipts(lambda: act.replace(
            shared(), at(project), decision_id, body.revision, title=body.title, statement=body.statement,
            rationale=body.rationale, reason=body.reason, redecided=body.redecide,
            effect=body.effect,
        ))  # fmt: skip

    @routes.post("/decisions/{decision_id}/withdraw", dependencies=mine)
    def withdraw(decision_id: str, body: WithdrawBody, project: In) -> dict[str, Any]:
        return _receipts(lambda: act.withdraw(
            shared(), at(project), decision_id, body.revision, reason=body.reason,
            redecided=body.redecide))  # fmt: skip

    @routes.post("/decisions/{decision_id}/activate", dependencies=mine)
    def activate(decision_id: str, body: ActivateBody, project: In) -> dict[str, Any]:
        return _receipts(lambda: act.activate(
            shared(), at(project), decision_id, body.revision, reason=body.reason,
            redecided=body.redecide, effect=body.effect))  # fmt: skip

    @routes.post("/decisions/{decision_id}/promote", dependencies=mine)
    def promote(decision_id: str, body: Promotion, project: In) -> dict[str, Any]:
        return _receipts(lambda: act.promote(
            shared(), at(project), decision_id, body.revision, reason=body.reason))  # fmt: skip

    @routes.post("/decisions/{decision_id}/exception", dependencies=mine)
    def exception(decision_id: str, body: SuccessorBody, project: In) -> dict[str, Any]:
        _confirmed(body)
        return _receipts(lambda: act.exception(
            shared(), at(project), decision_id, body.revision, title=body.title, statement=body.statement,
            rationale=body.rationale,
        ))  # fmt: skip

    @routes.post("/decisions/{decision_id}/keep", dependencies=mine)
    def keep(decision_id: str, body: KeepBody, project: In) -> dict[str, Any]:
        return _receipts(lambda: act.keep(
            shared(), at(project), decision_id, body.revisions, reason=body.reason))  # fmt: skip


def _ignore_route(routes: APIRouter, store: Store, at: At, mine: list[Any]) -> None:
    """The owner's "ignore for now", marked in the project's store (TD-427)."""

    @routes.post("/decisions/{decision_id}/ignore-read-back", dependencies=mine)
    def ignore(decision_id: str, body: Shown, project: In) -> dict[str, Any]:
        try:
            return read_backs.ignore(store, at(project), decision_id, body.revision)
        except decision_actions.Refused as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        except decision_store.DecisionsUnavailable as exc:
            raise HTTPException(409, f"{exc} ({exc.action})") from exc


def _impact(shared: DataRepo | None, folder: str, decision_id: str, places: Places) -> dict[str, Any]:
    """A replacement's impact report as the page shows it (TD-428), or why it cannot be made."""
    try:
        return decision_impact.shown(decision_impact.report(shared, folder, decision_id, places()))
    except (decision_actions.Refused, decision_store.DecisionsUnavailable) as exc:
        return {"error": str(exc)}


def _shared_routes(routes: APIRouter, shared: Shared, at: At, places: Places) -> None:
    """What a chat may do as well as the page: record or propose, retire, queue a read-back and record one."""

    @routes.post("/decisions/propose")
    def propose(body: ProposalBody, project: In) -> dict[str, Any]:
        scope = Scope.GLOBAL if body.scope == "global" else Scope.PROJECT
        out = _receipts(lambda: decision_actions.propose(
            shared(), at(project), title=body.title, topic=body.topic, statement=body.statement,
            rationale=body.rationale, confirmed=body.confirmed, replaces=body.replaces, reason=body.reason,
            scope=scope, revision=body.revision, redecided=body.redecide, effect=body.effect,
        ))  # fmt: skip
        if body.confirmed and body.replaces and out["saved"] and body.effect != "wording":
            out["impact"] = _impact(shared(), at(project), out["receipts"][0]["id"], places)
        return out

    @routes.post("/decisions/{decision_id}/retire")
    def retire(decision_id: str, body: RetireBody, project: In) -> dict[str, Any]:
        if not body.confirmed:
            raise HTTPException(422, UNCONFIRMED)
        out = _receipts(lambda: decision_actions.withdraw(
            shared(), at(project), decision_id, body.revision, reason=body.reason, redecided=body.redecide,
        ))  # fmt: skip
        if out["saved"]:
            out["impact"] = _impact(shared(), at(project), decision_id, places)
        return out

    @routes.post("/decisions/{decision_id}/queue-read-back")
    def queue_read_back(decision_id: str, body: QueueBody, project: In) -> dict[str, Any]:
        return _receipts(lambda: decision_actions.queue_read_back(
            shared(), at(project), decision_id, why=body.why, kind=body.kind, revision=body.revision))  # fmt: skip

    @routes.post("/decisions/{decision_id}/read-back")
    def read_back(decision_id: str, body: ReadBackBody, request: Request, project: In) -> dict[str, Any]:
        by = "chat" if request.headers.get("x-owlbear-use", "").lower() == "chat" else "owner"
        return _receipts(lambda: decision_actions.read_back(
            shared(), at(project), decision_id, body.revision, confirmed=body.confirmed, by=by))  # fmt: skip

    @routes.post("/decisions/{decision_id}/correct-origin")
    def correct_origin(decision_id: str, body: CorrectBody, request: Request, project: In) -> dict[str, Any]:
        by = "chat" if request.headers.get("x-owlbear-use", "").lower() == "chat" else "owner"
        return _receipts(lambda: decision_origin.correct_origin(
            shared(), at(project), decision_id, body.revision, origin=Origin(body.origin), reason=body.reason,
            confirmed=body.confirmed, by=by))  # fmt: skip
