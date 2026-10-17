"""Status-view HTTP API of the host app: Changes, answers, check results and brief approval (D4 §3.2, §3.6)."""

from __future__ import annotations

import hashlib
import re
import secrets
import shlex
import shutil
import time
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.resources import files
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts import evidence
from owlbear_delivery_next.change_contracts.inbox import (
    AnswerItem,
    CheckResult,
    ConsentItem,
    IntentItem,
    PullItem,
    RestartItem,
    WithdrawItem,
)
from owlbear_delivery_next.change_contracts.models import Change, Exit, PersonCheck, Waiting
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import brief_rounds, loop, rebuilds, round_flow, round_marks
from owlbear_delivery_next.change_flow.progress import progress
from owlbear_delivery_next.change_flow.status import card, status, unloadable
from owlbear_delivery_next.pack_runs import pack_job
from owlbear_delivery_next.project_host import (
    answers,
    backlog_routes,
    brief_routes,
    config_routes,
    memory_routes,
    pack_routes,
    pages,
)
from owlbear_delivery_next.project_host.launches import Launches, Refused
from owlbear_delivery_next.runtimes.vscode_adapter import open_chat
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.briefs import save_brief, save_visual
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import check, decision, held, visual

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.inbox import InboxItem
    from owlbear_delivery_next.change_contracts.models import Inputs
    from owlbear_delivery_next.change_contracts.visual_records import VisualResult
    from owlbear_delivery_next.change_flow.status import Activity
    from owlbear_delivery_next.project_host.host import Host, HostRecord
    from owlbear_delivery_next.project_host.launches import Ended
    from owlbear_delivery_next.runtimes.vscode_contract import Outcome
    from owlbear_delivery_next.settings.config import Effective
    from owlbear_delivery_next.state_store.store import Store

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
    """Answer one open question; a visual decision names the round, capture and pack the page showed (TD-79).

    A final retry names the plan tasks to rebuild and the loop attempt and head the page showed (TD-217).
    """

    question: str = Field(max_length=16)
    option: str | None = Field(default=None, max_length=64)
    text: str = Field(default="", max_length=2000)
    channel: Literal["status-view", "chat"] = "status-view"
    round: int | None = Field(default=None, ge=1)
    head: str = Field(default="", max_length=40)
    pack: str = Field(default="", max_length=200)
    findings: list[Annotated[str, Field(max_length=40)]] = Field(default_factory=list, max_length=60)
    tasks: list[Annotated[str, Field(max_length=16)]] = Field(default_factory=list, max_length=200)
    attempt: int | None = Field(default=None, ge=1)


class CheckBody(Body):
    """Pass or fail of the person-only check that is waiting, with a note."""

    check: str = Field(max_length=64)
    passed: bool
    note: str = Field(default="", max_length=2000)
    inputs: str = Field(pattern=r"^[0-9a-f]{64}$")  # the snapshot of the check the page showed


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


def person_check(c: Change, p: PersonCheck, *, inputs: Inputs, waiting: bool) -> dict[str, Any]:
    """One person-only check as the page shows it; a pass its inputs no longer match counts as open (None)."""
    a = p.answer
    held = bool(a and a.passed and a.inputs and evidence.check_valid(a.inputs, inputs))
    return {
        "id": p.id,
        "steps": p.steps,
        "expect": p.expect,
        "passed": True if held else (False if a and a.passed is False else None),
        "waiting": waiting,
        "url": c.env.ready_url if c.env and c.env.check == p.id and c.env.ready_at else None,
        "inputs": snapshot(inputs, p),
    }


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
    out["progress"] = asdict(progress(c))
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


def create_app(  # noqa: C901, PLR0913, PLR0915 - one closure per route; seams the tests replace
    store: Store,
    token: str,
    host: Host,
    *,
    launch: Callable[[Path, Effective, str], dict[str, str]] = new_chat,
    which: Callable[[str], str | None] = shutil.which,
    pack: pack_job.Job | None = None,
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
            out["next"] = (
                f"Once the draft is ready, ask for its challenge with challenge_brief (change {out['change']}, "
                f"version {out['version']}); the owner approves it in the Changes page after: {link(host.record)}"
            )
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
        o, prof = c.outcome, store.read_profile() or Profile()
        events = store.events(slug)
        merge = offer(c, events)
        q = next((q for q in c.questions if o and o.exit == Exit.ASK and q.id == o.question and not merge), None)
        q = q.model_copy(update={"options": held.offered(store, c, q)}) if q else None
        waiting = o and o.exit == Exit.PENDING and o.waiting == Waiting.PERSON_CHECK and o.who == "you"
        checks = [person_check(c, p, inputs=evidence.check_inputs(c, p, check.fingerprints(c, p)), waiting=bool(
            waiting and c.step.task == p.id)) for p in c.checks]  # fmt: skip
        return (
            summary_of(slug)
            | {
                "brief": {
                    "version": c.brief.version,
                    "approved": c.brief.approved_version,
                    "title": c.brief.title,
                    "outcome": c.brief.outcome,
                    "scope": c.brief.scope,
                    "non_goals": c.brief.non_goals,
                    "decisions": [x.model_dump() for x in c.brief.decisions],
                    "specified": c.brief.specified,
                    "approved_at": c.brief.approved_at.isoformat() if c.brief.approved_at else None,
                    "ui": c.brief.ui,
                    "visual": [s.model_dump() for s in c.brief.visual],
                    "unapprovable": brief_rounds.approvable(c),  # TD-249: why the approve button is off
                    "unreviewed": brief_rounds.unreviewed(c),  # TD-255: approving needs the owner's tick
                },
                "criteria": [k.model_dump() for k in c.brief.criteria],
                "plan": [t.model_dump() for t in c.plan.tasks] if c.plan else [],
                "handled": [
                    h.model_dump(mode="json", include={"item", "kind", "url", "how", "text", "resolved", "at"})
                    for h in c.handled
                ],
                "question": q.model_dump(mode="json", include={"id", "text", "options"}) if q else None,
                "retry": rebuilds.shown(c, q),  # TD-217: the plan tasks beside the final review's retry question
                "rounds": round_marks.shown(c),  # TD-217: each loop's round markers, details and what is left
                "checks": checks,
                "pr": c.names.pr,
                "target": c.names.target,
                "asks_merge": profile.value(prof, profile.ASK) == "yes",
                "deletes_branch": profile.value(prof, profile.DELETE) == "yes",
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
                "amendments": [a.model_dump(mode="json") for a in c.amendments],  # TD-179: proposed, never applied here
                "restartable": not round_flow.restartable(c),
                "activity": events[-20:],
            }
        )

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
        if q.repair and ((now_open := loop.open_question(c)) is None or now_open.id != q.id):
            raise HTTPException(409, "the Change moved on since this round gate asked; reload")
        if body.option is None and ({o.next for o in q.options} & loop.DECISIONS - {"retry"} or q.repair):
            raise HTTPException(422, f"choose one of {[o.label for o in q.options]}")
        if any(o.id == body.option and o.next == "reconsider" for o in q.options) and not body.text.strip():
            raise HTTPException(422, "a reconsideration needs your note: what the reviewer should weigh")
        if why := answers.refused(c, q, body):
            raise HTTPException(*why)
        item = AnswerItem(
            at=datetime.now(UTC), channel=body.channel, question=q.id, option=body.option, text=body.text,
            round=body.round, findings=body.findings, tasks=body.tasks, attempt=body.attempt, head=body.head,
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
        if not (body.passed or body.note.strip()):
            raise HTTPException(422, "a failed check says what failed: the note becomes the builder's fix task")
        inputs = evidence.check_inputs(c, person, check.fingerprints(c, person))
        if snapshot(inputs, person) != body.inputs:
            raise HTTPException(409, "This check changed since you opened it; reload")
        item = CheckResult(at=datetime.now(UTC), check=person.id, passed=body.passed, note=body.note, inputs=inputs)
        return put(slug, item)

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

    @router.post("/changes/{slug}/restart-review")
    def restart_review(slug: str) -> dict[str, str]:
        if why := round_flow.restartable(read(slug)):
            raise HTTPException(409, f"the review loop cannot restart: {why}")
        if host.activity(slug).runner_alive:
            raise HTTPException(409, "a step is running; restart the review loop once it has ended")
        return put(slug, RestartItem(at=datetime.now(UTC)))

    router.include_router(config_routes.router(store, host))
    router.include_router(brief_routes.router(store, read, put, lambda: host.wake.set()))  # noqa: PLW0108 - read late
    router.include_router(backlog_routes.router(store, start_chat))
    router.include_router(memory_routes.router(store))
    router.include_router(pack_routes.router(store, pack or pack_job.Job(store)))
    app.include_router(router)
    return app
