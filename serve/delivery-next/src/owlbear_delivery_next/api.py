"""Status-view HTTP API of the host app: Changes, answers, check results and brief approval (D4 §3.2, §3.6)."""

from __future__ import annotations

import contextlib
import hashlib
import re
import secrets
from datetime import UTC, datetime
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next import loop, profile, tools
from owlbear_delivery_next.models import (
    AnswerItem,
    BriefApproval,
    Change,
    CheckResult,
    ConsentItem,
    Criterion,
    Exit,
    IntentItem,
    Names,
    Outcome,
    PersonCheck,
    Profile,
    StepKind,
    Waiting,
)
from owlbear_delivery_next.status import status, unloadable
from owlbear_delivery_next.steps import check
from owlbear_delivery_next.store import LockHeldError, StoreError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.responses import Response

    from owlbear_delivery_next.host import Host, HostRecord
    from owlbear_delivery_next.models import InboxItem, Inputs
    from owlbear_delivery_next.status import Activity
    from owlbear_delivery_next.store import Store

SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
T6 = "This is a recovery decision; make it in the Changes page"


class Body(BaseModel):
    """Strict request body."""

    model_config = ConfigDict(extra="forbid")


class AnswerBody(Body):
    """Answer one open question."""

    question: str = Field(max_length=16)
    option: str | None = Field(default=None, max_length=64)
    text: str = Field(default="", max_length=2000)
    channel: Literal["status-view", "chat"] = "status-view"


class CheckBody(Body):
    """Pass or fail of the person-only check that is waiting, with a note."""

    check: str = Field(max_length=64)
    passed: bool
    note: str = Field(default="", max_length=2000)
    inputs: str = Field(pattern=r"^[0-9a-f]{64}$")  # the snapshot of the check the page showed


class ApproveBody(Body):
    """Approve one brief version."""

    version: int = Field(ge=1)


class ConsentBody(Body):
    """Consent to merge one exact head; void once the PR head differs."""

    head: str = Field(pattern=r"^[0-9a-f]{40}$")


class IntentBody(Body):
    """Pause, resume or abandon the Change."""

    intent: Literal["pause", "resume", "abandon"]
    text: str = Field(default="", max_length=500)


def link(rec: HostRecord | None) -> str | None:
    """The Changes-page URL with its token, as the host prints it; None until the host has one."""
    return f"{rec.url}#token={rec.token}" if rec and rec.token else None


def snapshot(inputs: Inputs, person: PersonCheck) -> str:
    """Opaque fingerprint of one check's inputs and shown instructions; a relaunch leaves it unchanged."""
    shown = inputs.model_dump_json() + person.model_dump_json(include={"steps", "expect"})
    return hashlib.sha256(shown.encode()).hexdigest()


def offer(c: Change, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The merge dialog: the latest offer while the Change waits for consent to merge its exact head."""
    o = c.outcome
    if not (o and o.exit == Exit.ASK and o.cause == loop.CONSENT):
        return None
    last = next((e for e in reversed(events) if e.get("event") == "merge-offer"), None)
    return last and last | {"diff": f"{last['url']}/files"}


def summary(store: Store, slug: str, act: Activity, now: datetime) -> dict[str, Any]:
    """One Change's status line, next action, chat handle and open question; shared with the chat fallback."""
    try:
        c = store.read(slug)
    except StoreError as exc:
        s = unloadable(exc.stop(now))
        return {"slug": slug, "line": s.line, "action": s.action, "actor": s.actor}
    s = status(c, act, now)
    out = {"slug": slug, "handle": c.handle, "step": c.step.kind, "line": s.line, "action": s.action, "actor": s.actor}
    out["spend"] = c.spend.model_dump()
    if q := loop.open_question(c):
        options = [o.model_dump(include={"id", "label"}) for o in q.options]
        where = "chat" if loop.ordinary(q) else "changes-page"
        out["question"] = {"id": f"{c.handle or slug}.{q.id}", "text": q.text, "options": options, "answer_in": where}
    return out


def drafted(old: Change | None, d: tools.BriefDraft, slug: str, handle: str, prof: Profile) -> Change:
    """The Change with its new brief draft version, waiting for the owner's approval; criteria and checks versioned."""
    names = Names(branch=f"owlbear/{slug}", target=profile.value(prof, profile.DEFAULT, "main"))
    c = old or Change(slug=slug, handle=handle, profile_version=prof.version, names=names)
    before = {k.id: k for k in c.brief.criteria}
    criteria = []
    for i, text in enumerate(d.criteria, 1):
        prev = before.get(f"AC-{i}")
        criteria.append(Criterion(id=f"AC-{i}", text=text, version=prev.version + (prev.text != text) if prev else 1))
    v = c.brief.version + 1
    fields = {"version": v, "title": d.title, "outcome": d.outcome, "scope": d.scope, "criteria": criteria}
    c.brief = c.brief.model_copy(update=fields)
    ids, paths, shown = [k.id for k in criteria], loop.coverage(c), {p.id: p for p in c.checks}
    c.checks = []
    for p in d.person_checks:
        prev = shown.get(p.name)
        procedure = prev.procedure + ((prev.steps, prev.expect) != (p.steps, p.expect)) if prev else 1
        c.checks.append(
            PersonCheck(id=p.name, criteria=ids, steps=p.steps, expect=p.expect, paths=paths, procedure=procedure)
        )
    c.outcome = Outcome(
        exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", reason=f"approve brief v{v}", at=datetime.now(UTC)
    )
    return c


def new_slug(title: str, taken: list[str]) -> str:
    """A free slug from the title."""
    base = "-".join(re.findall(r"[a-z0-9]+", title.lower()))[:40].strip("-") or "change"
    return next(s for n in range(1, 1000) if (s := base if n == 1 else f"{base}-{n}") not in taken)


def create_app(store: Store, token: str, host: Host) -> FastAPI:  # noqa: C901, PLR0915 - one closure per route
    """Return the host's app: the Changes page without data, and a token-guarded API under ``/api/next``."""
    app = FastAPI(title="OwlBear Delivery", docs_url=None, redoc_url=None, openapi_url=None)
    page = files("owlbear_delivery_next").joinpath("web", "changes.html").read_text(encoding="utf-8")
    expected = f"Bearer {token}".encode()

    @app.middleware("http")
    async def local_only(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.headers.get("host", "").rsplit(":", 1)[0] not in LOCAL_HOSTS:  # DNS rebinding
            return JSONResponse({"detail": "host not allowed"}, status_code=403)
        return await call_next(request)

    def auth(request: Request) -> None:
        if not secrets.compare_digest(request.headers.get("authorization", "").encode(), expected):
            raise HTTPException(401, "token required")

    def read(slug: str) -> Change:
        if not SLUG.fullmatch(slug) or slug not in store.slugs():
            raise HTTPException(404, "no such Change")
        try:
            return store.read(slug)
        except StoreError as exc:
            raise HTTPException(409, str(exc)) from exc

    def summary_of(slug: str) -> dict[str, Any]:
        return summary(store, slug, host.activity(slug), datetime.now(UTC))

    def put(slug: str, item: InboxItem) -> dict[str, str]:
        store.put_inbox(slug, item)
        host.wake.set()
        return {"accepted": item.kind}

    def save(body: object) -> tuple[int, dict[str, Any]]:
        draft, errors = tools.parse(tools.BriefDraft, body)
        errors = tools.check_brief(draft) if draft else errors
        if draft is None or errors:
            return 422, {"errors": errors}
        handles = {}
        for s in (slugs := store.slugs()):
            with contextlib.suppress(StoreError):
                handles[store.read(s).handle] = s
        slug = handles.get(draft.change) if draft.change else new_slug(draft.title, slugs)
        if slug is None:
            return 422, {"errors": [f"change: {draft.change} is not a Change here - leave it empty for a new one"]}
        number = max((int(h[1:]) for h in handles if h[1:].isdigit()), default=0) + 1
        try:
            with store.lock(slug) as lock:
                old = store.read(slug) if draft.change else None
                if old and (old.step.kind != StepKind.SHAPE or old.finished_at):
                    return 409, {"errors": [f"change: {draft.change} is approved; ask for changes in the Changes page"]}
                c = drafted(old, draft, slug, f"c{number}", store.read_profile() or Profile())
                store.write(lock, c)
        except (LockHeldError, StoreError) as exc:
            return 409, {"errors": [f"change: {exc}; try again"]}
        approve = f"Approve brief v{c.brief.version} of {c.handle} in the Changes page: {link(host.record)}"
        return 200, {"change": c.handle, "version": c.brief.version, "next": approve}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return page

    router = APIRouter(prefix="/api/next", dependencies=[Depends(auth)])

    @router.post("/briefs")
    async def brief(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except ValueError:
            body = ""
        code, out = save(body)
        return JSONResponse(out, status_code=code)

    @router.get("/changes")
    def changes() -> list[dict[str, Any]]:
        return [summary_of(slug) for slug in store.slugs()]

    @router.get("/changes/{slug}")
    def detail(slug: str) -> dict[str, Any]:
        c = read(slug)
        o = c.outcome
        events = store.events(slug)
        merge = offer(c, events)
        q = next((q for q in c.questions if o and o.exit == Exit.ASK and q.id == o.question and not merge), None)
        waiting = o and o.exit == Exit.PENDING and o.waiting == Waiting.PERSON_CHECK and o.who == "you"
        checks = [
            {
                "id": p.id,
                "steps": p.steps,
                "expect": p.expect,
                "passed": p.answer.passed if p.answer else None,
                "waiting": bool(waiting and c.step.task == p.id),
                "url": c.env.ready_url if c.env and c.env.check == p.id and c.env.ready_at else None,
                "inputs": snapshot(loop.check_inputs(c, p, check.fingerprints(c, p)), p),
            }
            for p in c.checks
        ]
        return summary_of(slug) | {
            "brief": {
                "version": c.brief.version,
                "approved": c.brief.approved_version,
                "title": c.brief.title,
                "outcome": c.brief.outcome,
            },
            "criteria": [k.model_dump() for k in c.brief.criteria],
            "plan": [t.model_dump() for t in c.plan.tasks] if c.plan else [],
            "handled": [
                h.model_dump(mode="json", include={"item", "kind", "url", "how", "text", "resolved", "at"})
                for h in c.handled
            ],
            "question": q.model_dump(mode="json", include={"id", "text", "options"}) if q else None,
            "checks": checks,
            "pr": c.names.pr,
            "paused": c.intent.paused_at is not None,
            "merge": merge,
            "consent": c.consent.model_dump(mode="json") if c.consent else None,
            "activity": events[-20:],
        }

    @router.post("/changes/{slug}/answers")
    def answer(slug: str, body: AnswerBody) -> dict[str, str]:
        c = read(slug)
        q = next((q for q in c.questions if q.id == body.question and q.answer is None), None)
        if q is None:
            raise HTTPException(409, f"question {body.question} is not open")
        if q.cause == loop.CONSENT:
            raise HTTPException(409, "consent to merge goes through merge-consent with the exact head")
        if body.channel == "chat" and not loop.ordinary(q):
            raise HTTPException(403, T6)
        if body.option is not None and body.option not in {o.id for o in q.options}:
            raise HTTPException(422, f"option {body.option} is not one of {[o.id for o in q.options]}")
        item = AnswerItem(at=datetime.now(UTC), channel=body.channel, question=q.id, option=body.option, text=body.text)
        return put(slug, item)

    @router.post("/changes/{slug}/check-results")
    def check_result(slug: str, body: CheckBody) -> dict[str, str]:
        c = read(slug)
        person = next((p for p in c.checks if p.id == body.check), None)
        if person is None or not (c.env and c.env.check == body.check and c.env.ready_at):
            raise HTTPException(409, f"check {body.check} is not waiting for a result")
        inputs = loop.check_inputs(c, person, check.fingerprints(c, person))
        if snapshot(inputs, person) != body.inputs:
            raise HTTPException(409, "This check changed since you opened it; reload")
        item = CheckResult(at=datetime.now(UTC), check=person.id, passed=body.passed, note=body.note, inputs=inputs)
        return put(slug, item)

    @router.post("/changes/{slug}/approve-brief")
    def approve(slug: str, body: ApproveBody) -> dict[str, str]:
        if body.version != read(slug).brief.version:
            raise HTTPException(409, f"brief version {body.version} is not the current draft")
        return put(slug, BriefApproval(at=datetime.now(UTC), version=body.version))

    @router.post("/changes/{slug}/merge-consent")
    def consent(slug: str, body: ConsentBody) -> dict[str, str]:
        merge = offer(read(slug), store.events(slug))
        if merge is None or merge["head"] != body.head:
            shown = merge["head"] if merge else "none"
            raise HTTPException(409, f"head {body.head[:7]} is not the head waiting for consent ({shown[:7]})")
        return put(slug, ConsentItem(at=datetime.now(UTC), head=body.head, delta=merge.get("delta") or ""))

    @router.post("/changes/{slug}/intent")
    def intent(slug: str, body: IntentBody) -> dict[str, str]:
        read(slug)
        return put(slug, IntentItem(at=datetime.now(UTC), intent=body.intent, text=body.text))

    app.include_router(router)
    return app
