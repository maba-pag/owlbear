"""Status-view HTTP API of the host app: Changes, answers, check results and brief approval (D4 §3.2, §3.6)."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from importlib.resources import files
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next import loop
from owlbear_delivery_next.models import AnswerItem, BriefApproval, CheckResult, ConsentItem, Exit, Waiting
from owlbear_delivery_next.status import status, unloadable
from owlbear_delivery_next.steps import check
from owlbear_delivery_next.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.responses import Response

    from owlbear_delivery_next.host import Host
    from owlbear_delivery_next.models import Change, InboxItem
    from owlbear_delivery_next.store import Store

SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})


class Body(BaseModel):
    """Strict request body."""

    model_config = ConfigDict(extra="forbid")


class AnswerBody(Body):
    """Answer one open question."""

    question: str = Field(max_length=16)
    option: str | None = Field(default=None, max_length=64)
    text: str = Field(default="", max_length=2000)


class CheckBody(Body):
    """Pass or fail of the person-only check that is waiting, with a note."""

    check: str = Field(max_length=64)
    passed: bool
    note: str = Field(default="", max_length=2000)


class ApproveBody(Body):
    """Approve one brief version."""

    version: int = Field(ge=1)


class ConsentBody(Body):
    """Consent to merge one exact head; void once the PR head differs."""

    head: str = Field(pattern=r"^[0-9a-f]{40}$")


def offer(c: Change, events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The merge dialog: the latest offer while the Change waits for consent to merge its exact head."""
    o = c.outcome
    if not (o and o.exit == Exit.ASK and o.cause == loop.CONSENT):
        return None
    last = next((e for e in reversed(events) if e.get("event") == "merge-offer"), None)
    return last and last | {"diff": f"{last['url']}/files"}


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

    def summary(slug: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        try:
            c = store.read(slug)
        except StoreError as exc:
            s = unloadable(exc.stop(now))
            return {"slug": slug, "line": s.line, "action": s.action, "actor": s.actor}
        s = status(c, host.activity(slug), now)
        return {"slug": slug, "step": c.step.kind, "line": s.line, "action": s.action, "actor": s.actor}

    def put(slug: str, item: InboxItem) -> dict[str, str]:
        store.put_inbox(slug, item)
        host.wake.set()
        return {"accepted": item.kind}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return page

    router = APIRouter(prefix="/api/next", dependencies=[Depends(auth)])

    @router.get("/changes")
    def changes() -> list[dict[str, Any]]:
        return [summary(slug) for slug in store.slugs()]

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
            }
            for p in c.checks
        ]
        return summary(slug) | {
            "brief": {"version": c.brief.version, "approved": c.brief.approved_version, "outcome": c.brief.outcome},
            "criteria": [k.model_dump() for k in c.brief.criteria],
            "plan": [t.model_dump() for t in c.plan.tasks] if c.plan else [],
            "question": q.model_dump(mode="json", include={"id", "text", "options"}) if q else None,
            "checks": checks,
            "pr": c.names.pr,
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
        if body.option is not None and body.option not in {o.id for o in q.options}:
            raise HTTPException(422, f"option {body.option} is not one of {[o.id for o in q.options]}")
        return put(slug, AnswerItem(at=datetime.now(UTC), question=q.id, option=body.option, text=body.text))

    @router.post("/changes/{slug}/check-results")
    def check_result(slug: str, body: CheckBody) -> dict[str, str]:
        c = read(slug)
        person = next((p for p in c.checks if p.id == body.check), None)
        if person is None or not (c.env and c.env.check == body.check and c.env.ready_at):
            raise HTTPException(409, f"check {body.check} is not waiting for a result")
        inputs = loop.check_inputs(c, person, check.fingerprints(c, person))
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

    app.include_router(router)
    return app
