"""Status-view HTTP API of the host app: Changes, answers, check results and brief approval (D4 §3.2, §3.6)."""

from __future__ import annotations

import hashlib
import re
import secrets
import shlex
import shutil
import subprocess
import threading
import time
from datetime import UTC, datetime
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next import evidence, loop
from owlbear_delivery_next.briefs import save_brief
from owlbear_delivery_next.models import (
    AnswerItem,
    BriefApproval,
    Change,
    CheckResult,
    ConsentItem,
    Exit,
    IntentItem,
    PersonCheck,
    PullItem,
    Waiting,
)
from owlbear_delivery_next.status import card, status, unloadable
from owlbear_delivery_next.steps import check, visual
from owlbear_delivery_next.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from starlette.responses import Response

    from owlbear_delivery_next.host import Host, HostRecord
    from owlbear_delivery_next.models import InboxItem, Inputs
    from owlbear_delivery_next.status import Activity
    from owlbear_delivery_next.store import Store

SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
T6 = "This is a recovery decision; make it in the Changes page"
START_PROMPT = "Start a new Delivery Change: use the delivery skill to shape a brief with me."
LAUNCH_GAP = 5.0  # seconds between two new-Change launches


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
    tool = store.now(slug)
    s = status(c, act, now, tool)
    out = {"slug": slug, "handle": c.handle, "step": c.step.kind, "line": s.line, "action": s.action, "actor": s.actor}
    out |= card(c, act, store.events(slug), now, tool)
    out["spend"] = c.spend.model_dump()
    out["pullback"] = c.pullback.model_dump(mode="json") if c.pullback else None
    if q := loop.open_question(c):
        options = [o.model_dump(include={"id", "label"}) for o in q.options]
        where = "chat" if loop.ordinary(q) else "changes-page"
        out["question"] = {"id": f"{c.handle or slug}.{q.id}", "text": q.text, "options": options, "answer_in": where}
    return out


def new_chat(
    repo: Path, which: Callable[[str], str | None] = shutil.which, popen: Callable[..., object] = subprocess.Popen
) -> dict[str, Any]:
    """Open a VS Code agent chat with the fixed start prompt in *repo*; on failure, the command to run there."""
    argv = ["code", "chat", "-m", "agent", START_PROMPT]
    command = shlex.join(argv)
    if not (code := which("code")):
        return {"started": False, "command": command, "reason": f"`code` is not on PATH; run this in {repo}"}
    try:
        popen(
            [code, *argv[1:]],
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return {"started": False, "command": command, "reason": f"could not start `code` ({exc}); run this in {repo}"}
    return {"started": True, "command": command}


def create_app(  # noqa: C901, PLR0915 - one closure per route
    store: Store, token: str, host: Host, *, launch: Callable[[], dict[str, Any]] | None = None
) -> FastAPI:
    """Return the host's app: the Changes page without data, and a token-guarded API under ``/api/next``."""
    app = FastAPI(title="OwlBear Delivery", docs_url=None, redoc_url=None, openapi_url=None)
    page = files("owlbear_delivery_next").joinpath("web", "changes.html").read_text(encoding="utf-8")
    expected = f"Bearer {token}".encode()
    launched, launching = [-LAUNCH_GAP], threading.Lock()

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
        code, out = save_brief(store, body)
        if code == 200:  # noqa: PLR2004 - HTTP OK
            out["next"] = f"Approve brief v{out['version']} of {out['change']} in the Changes page: {link(host.record)}"
        return code, out

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

    @router.post("/new-change")
    def new_change() -> dict[str, Any]:
        with launching:  # FastAPI runs sync routes on a thread pool; check and set as one step
            if (now := time.monotonic()) - launched[0] < LAUNCH_GAP:
                raise HTTPException(429, "A new Change chat was just opened; wait a few seconds")
            launched[0] = now
        return launch() if launch else new_chat(host.repo)

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
                "inputs": snapshot(evidence.check_inputs(c, p, check.fingerprints(c, p)), p),
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
            "fixes": [f"fix Change {e['fix']} drafted" for e in events if e.get("event") == "fix-drafted"],
            "visual": c.visual.model_dump(mode="json") if c.visual else None,
            "activity": events[-20:],
        }

    @router.get("/changes/{slug}/visual/{name}")
    def screenshot(slug: str, name: str) -> FileResponse:
        c = read(slug)
        if not (c.visual and visual.FILE.fullmatch(name) and name in c.visual.files):
            raise HTTPException(404, "no such screenshot")
        folder = store.visual_dir(slug, c.visual.head).resolve()
        path = (folder / name).resolve()
        if path.parent != folder or not path.is_file():
            raise HTTPException(404, "no such screenshot")
        return FileResponse(path, media_type="image/png")

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
        inputs = evidence.check_inputs(c, person, check.fingerprints(c, person))
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

    @router.post("/changes/{slug}/pull")
    def pull(slug: str) -> dict[str, str]:
        read(slug)
        return put(slug, PullItem(at=datetime.now(UTC)))

    app.include_router(router)
    return app
