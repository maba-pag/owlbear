"""Status-view HTTP API of the host app: Changes, answers, check results and brief approval (D4 §3.2, §3.6)."""

from __future__ import annotations

import hashlib
import re
import secrets
import shlex
import shutil
import time
from datetime import UTC, datetime
from importlib.resources import files
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next import backlog_routes, config_routes, evidence, held, loop, memory_routes, pages, profile
from owlbear_delivery_next.briefs import save_brief, save_visual
from owlbear_delivery_next.inbox import (
    AnswerItem,
    BriefApproval,
    CheckResult,
    ConsentItem,
    IntentItem,
    PullItem,
    WithdrawItem,
)
from owlbear_delivery_next.launches import Launches, Refused
from owlbear_delivery_next.models import Change, Exit, PersonCheck, Waiting
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.status import card, status, unloadable
from owlbear_delivery_next.steps import check, decision, visual
from owlbear_delivery_next.store import StoreError
from owlbear_delivery_next.vscode_adapter import open_chat

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from owlbear_delivery_next.config import Effective
    from owlbear_delivery_next.host import Host, HostRecord
    from owlbear_delivery_next.inbox import InboxItem
    from owlbear_delivery_next.launches import Ended
    from owlbear_delivery_next.models import Inputs, VisualResult
    from owlbear_delivery_next.status import Activity
    from owlbear_delivery_next.store import Store
    from owlbear_delivery_next.vscode_contract import Outcome

SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
PDS = {"index.css": "text/css", "load.mjs": "text/javascript"}  # the vendored Porsche Design System 4.8.0 files
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
T6 = "This is a recovery decision; make it in the Changes page"
START_PROMPT = "Start a new Delivery Change: use the delivery skill to shape a brief with me."
LAUNCH_GAP = 5.0  # seconds after a new-Change launch ends before the next may start


class Body(BaseModel):
    """Strict request body."""

    model_config = ConfigDict(extra="forbid")


class AnswerBody(Body):
    """Answer one open question; a visual decision names the round, capture and pack the page showed (TD-79)."""

    question: str = Field(max_length=16)
    option: str | None = Field(default=None, max_length=64)
    text: str = Field(default="", max_length=2000)
    channel: Literal["status-view", "chat"] = "status-view"
    round: int | None = Field(default=None, ge=1)
    head: str = Field(default="", max_length=40)
    pack: str = Field(default="", max_length=200)
    findings: list[Annotated[str, Field(max_length=40)]] = Field(default_factory=list, max_length=60)


def decision_refused(c: Change, body: AnswerBody) -> tuple[int, str] | None:
    """Why a Pass or Fail is refused: its round, capture or pack changed since the page showed them, or it is empty."""
    kept = c.visual_rounds[-1] if c.visual_rounds else None
    shown = (body.round, body.head, body.pack)
    if kept is None or kept.outcome != "ask" or kept.decision or shown != (kept.number, kept.head, kept.pack):
        return 409, "the capture or the design pack changed since the page was shown; reload"
    if unknown := sorted(set(body.findings) - {f.id for v in kept.verdicts for f in v.findings}):
        return 422, f"findings {unknown} are not in round {kept.number}"
    if body.option == "fail" and not body.findings and not body.text.strip():
        return 422, "a Fail ticks a finding or says what is wrong"
    return None


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


def fixed_page(html: str) -> Callable[[], HTMLResponse]:
    """A page handler without parameters, so no request can change what it serves."""

    def page() -> HTMLResponse:
        return HTMLResponse(html)

    return page


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
        options = [o.model_dump(include={"id", "label"}) for o in held.offered(store, c, q)]
        where = "chat" if loop.ordinary(q) else "changes-page"
        out["question"] = {"id": f"{c.handle or slug}.{q.id}", "text": q.text, "options": options, "answer_in": where}
    return out


def new_chat(
    repo: Path,
    shaper: Effective,
    prompt: str = START_PROMPT,
    start: Callable[[Path, Effective, str], tuple[Outcome, str]] = open_chat,
) -> dict[str, str]:
    """Open the shaping chat in *repo*'s window on the shaper role (TD-83): its launch's ending state."""
    out, warning = start(repo, shaper, prompt)
    if out.end == "started":
        ending = {"state": "open"}
    else:
        why = f"the Copilot chat did not start ({out.end}: {out.detail})"
        ending = {"state": "failed", "reason": f"{why}; run this in {repo}"}
    return ending | ({"warning": warning} if warning else {})


def create_app(  # noqa: C901, PLR0915 - one closure per route
    store: Store,
    token: str,
    host: Host,
    *,
    launch: Callable[[Path, Effective, str], dict[str, str]] = new_chat,
    which: Callable[[str], str | None] = shutil.which,
) -> FastAPI:
    """Return the host's app: its pages without data, and a guarded API under ``/api/next``."""
    app = FastAPI(title="OwlBear Delivery", docs_url=None, redoc_url=None, openapi_url=None)
    expected = f"Bearer {token}".encode()
    launches = Launches(LAUNCH_GAP, time.monotonic)

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

    def save(
        body: object, write: Callable[[Store, object], tuple[int, dict[str, Any]]] = save_brief
    ) -> tuple[int, dict[str, Any]]:
        code, out = write(store, body)
        if code == 200:  # noqa: PLR2004 - HTTP OK
            out["next"] = f"Approve brief v{out['version']} of {out['change']} in the Changes page: {link(host.record)}"
        return code, out

    @app.get("/assets/pds/{name}")
    def pds(name: str) -> Response:
        if name not in PDS:
            raise HTTPException(404, "no such asset")
        body = files("owlbear_delivery_next").joinpath("web", "pds", name).read_bytes()
        return Response(body, media_type=PDS[name], headers={"Cache-Control": "max-age=3600"})

    for path, html in pages.pages().items():
        app.add_api_route(path, fixed_page(html), methods=["GET"], response_class=HTMLResponse)

    def start_chat(prompt: str, done: Ended | None = None) -> dict[str, Any]:
        """Open the shaping chat with ``prompt`` in the background, or say why not and give the command by hand."""
        command = shlex.join(["code", "chat", "-m", "agent", prompt])
        if not which("code"):
            return {"started": False, "command": command, "reason": f"`code` is not on PATH; run this in {host.repo}"}
        try:
            shaper = store.settings().agents["shaper"]
        except StoreError as exc:
            return {"started": False, "command": command, "reason": f"the settings are unreadable ({exc})"}
        try:
            return {"started": True, "launch": launches.start(lambda: launch(host.repo, shaper, prompt), command, done)}
        except Refused as exc:
            raise HTTPException(exc.status, exc.text) from exc

    router = APIRouter(prefix="/api/next", dependencies=[Depends(auth)])

    @router.post("/briefs")
    async def brief(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except ValueError:
            body = ""
        code, out = save(body)
        return JSONResponse(out, status_code=code)

    @router.post("/briefs/visual")
    async def brief_visual(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except ValueError:
            body = ""
        code, out = save(body, save_visual)
        return JSONResponse(out, status_code=code)

    @router.get("/changes")
    def changes() -> list[dict[str, Any]]:
        return [summary_of(slug) for slug in store.slugs()]

    @router.get("/project")
    def project() -> dict[str, list[str]]:
        return {"notes": profile.notes(store.read_profile() or Profile())}

    @router.post("/new-change")
    def new_change() -> dict[str, Any]:
        return start_chat(START_PROMPT)

    @router.get("/new-change/{launch_id}")
    def new_change_state(launch_id: str) -> dict[str, Any]:
        if (state := launches.state(launch_id)) is None:
            raise HTTPException(404, "no such launch")
        return state

    @router.get("/changes/{slug}")
    def detail(slug: str) -> dict[str, Any]:
        c = read(slug)
        o = c.outcome
        events = store.events(slug)
        merge = offer(c, events)
        q = next((q for q in c.questions if o and o.exit == Exit.ASK and q.id == o.question and not merge), None)
        q = q.model_copy(update={"options": held.offered(store, c, q)}) if q else None
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
                "ui": c.brief.ui,
                "visual": [s.model_dump() for s in c.brief.visual],
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
            "visual_existing_errors": [
                f"{e.state} at {e.width}px, {e.kind} error: {e.text}"
                for e in visual.classify(c.visual.errors if c.visual else [], c.before)[1]
            ],
            "before": c.before.model_dump(mode="json") if c.before else None,
            "visual_round": c.visual_rounds[-1].model_dump(mode="json")
            | {"proposed": decision.proposed(c.visual_rounds[-1])}
            if c.visual_rounds
            else None,
            "owner_criteria": [k.model_dump(mode="json") for k in c.owner_criteria if k.withdrawn_at is None],
            "activity": events[-20:],
        }

    def png(shots: VisualResult | None, folder_of: Callable[[str], Path], name: str) -> FileResponse:
        if not (shots and visual.FILE.fullmatch(name) and name in shots.files):
            raise HTTPException(404, "no such screenshot")
        folder = folder_of(shots.head).resolve()
        path = (folder / name).resolve()
        if path.parent != folder or not path.is_file():
            raise HTTPException(404, "no such screenshot")
        return FileResponse(path, media_type="image/png")

    @router.get("/changes/{slug}/visual/{name}")
    def screenshot(slug: str, name: str) -> FileResponse:
        return png(read(slug).visual, lambda head: store.visual_dir(slug, head), name)

    @router.get("/changes/{slug}/before/{name}")
    def before_screenshot(slug: str, name: str) -> FileResponse:
        return png(read(slug).before, lambda base: store.before_dir(slug, base), name)

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
        if body.option is not None and body.option not in {o.id for o in held.offered(store, c, q)}:
            if body.option in {o.id for o in q.options}:  # an accept its hold no longer supports
                raise HTTPException(409, "the held result no longer matches its step, brief or commit; run it again")
            raise HTTPException(422, f"option {body.option} is not one of {[o.id for o in q.options]}")
        if body.option is None and {o.next for o in q.options} & loop.DECISIONS - {"retry"}:
            raise HTTPException(422, f"choose one of {[o.label for o in q.options]}")
        if q.cause == decision.CAUSE and body.option in {"pass", "fail"} and (why := decision_refused(c, body)):
            raise HTTPException(*why)
        item = AnswerItem(
            at=datetime.now(UTC), channel=body.channel, question=q.id, option=body.option, text=body.text,
            round=body.round, findings=body.findings,
        )  # fmt: skip
        return put(slug, item)

    @router.post("/changes/{slug}/criteria/{criterion}/withdraw")
    def withdraw(slug: str, criterion: str) -> dict[str, str]:
        if not any(k.id == criterion and k.withdrawn_at is None for k in read(slug).owner_criteria):
            raise HTTPException(404, f"no criterion {criterion} is in force")
        return put(slug, WithdrawItem(at=datetime.now(UTC), criterion=criterion))

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
        brief = read(slug).brief
        if body.version != brief.version:
            raise HTTPException(409, f"brief version {body.version} is not the current draft")
        if (stepped := [s.name for s in brief.visual if s.steps]) and not store.settings().seed:
            raise HTTPException(
                409,
                f"The visual states {', '.join(stepped)} have clicks or typing, which run only on seeded test data "
                "(TD-60); set the project's seed command in Settings first, or revise the brief without those steps",
            )
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

    router.include_router(config_routes.router(store))
    router.include_router(backlog_routes.router(store, start_chat))
    router.include_router(memory_routes.router(store))
    app.include_router(router)
    return app
