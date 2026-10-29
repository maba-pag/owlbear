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
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts import chat_contract, evidence
from owlbear_delivery_next.change_contracts.inbox import (
    CheckResult,
    ConsentItem,
    IntentItem,
    PullItem,
    RestartItem,
    WithdrawItem,
)
from owlbear_delivery_next.change_contracts.models import Change, Exit, PersonCheck, Waiting
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import brief_rounds, loop, picks, rebuilds, round_flow, round_marks
from owlbear_delivery_next.change_flow.progress import progress
from owlbear_delivery_next.change_flow.status import card, status, unloadable
from owlbear_delivery_next.impeccable_runs import pack_job
from owlbear_delivery_next.project_host import (
    answers,
    backlog_routes,
    brief_routes,
    chat_routes,
    config_routes,
    decision_routes,
    memory_routes,
    pack_routes,
    pages,
    session_slots,
)
from owlbear_delivery_next.project_host.admission import admitted
from owlbear_delivery_next.project_host.launches import Launches, Refused
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.runtimes.vscode_adapter import open_chat
from owlbear_delivery_next.runtimes.window_files import HARNESS
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import spend_ledger, tool_metrics, watch_reports
from owlbear_delivery_next.state_store.briefs import save_brief, save_visual
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import check, decision, decisions_gate, held, visual

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
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
START_PROMPT = "Start a new Delivery Change: use the owlbear-change-shaping skill to shape a brief with me."
PICKER_NOTE = (  # the owner's typed messages run on the picker, not on the role's model (TD-277)
    '\n\nBegin your first message or question to the owner with this line: "Messages you type here run on this '
    "chat's model picker: set it to {model} at {effort} effort.\""
)
SHAPER_MODE = readiness.SHAPER.removesuffix(".agent.md")  # `code chat -m` keeps the shaper for typed messages
LAUNCH_GAP = 5.0  # seconds after a new-Change launch ends before the next may start


class Body(BaseModel):
    """Strict request body."""

    model_config = ConfigDict(extra="forbid")


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
    """The Changes-page URL with its token, on the record's project under the machine host (TD-242); else None."""
    if not (rec and rec.token):
        return None
    return f"{rec.url}{f'?project={rec.project}' if rec.project else ''}#token={rec.token}"


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
    out |= card(c, act, store.events(slug), now, tool, pending=store.shared.pending if store.shared else None)
    out["progress"] = asdict(progress(c))
    out["spend"] = c.spend.model_dump()
    out["tool_use"] = tool_metrics.of_change(spend_ledger.Where.of(store).clone, slug).model_dump()
    out["pullback"] = c.pullback.model_dump(mode="json") if c.pullback else None
    out["watcher"] = watch_reports.counts(store.db, slug)  # observed calls writing outside, unresolved ones apart
    if q := loop.open_question(c):
        options = [o.model_dump(include={"id", "label"}) for o in held.offered(store, c, q)]
        where = "chat" if loop.ordinary(q) else "changes-page"
        out["question"] = {"id": f"{c.handle or slug}.{q.id}", "text": q.text, "options": options, "answer_in": where}
    return out


def display_prefs(store: Store) -> tuple[dict[str, bool | None], str | None]:
    """The merge and branch preferences the page shows, None where unset; an unreadable layer is a reported fault."""
    try:
        prefs = store.settings().prefs
    except StoreError as exc:
        return {"asks_merge": None, "deletes_branch": None}, str(exc)
    return {"asks_merge": prefs.ask_before_merge, "deletes_branch": prefs.delete_remote_branch}, None


def watcher(store: Store, slug: str) -> dict[str, Any]:
    """The Change's watcher list: its newest reports, their counts and whether the Spotter watches (None: unknown)."""
    try:
        switch = store.settings().spotter.switch
    except StoreError:
        switch = None
    on = None if switch is None else switch == "on"
    return {"on": on, "reports": watch_reports.reports(store.db, slug)} | watch_reports.counts(store.db, slug)


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
        if out.end == "unbound":  # the window opened a Local chat: it reads the harness key only when it starts
            why += (
                f"; if a Local chat opened, set {HARNESS} to true in .vscode/settings.json (`owlbear-next setup` "
                "offers it), reload the window (Developer: Reload Window) and try again"
            )
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
        if not chat_contract.served(sent := request.headers.get(chat_contract.HEADER)):  # before any route runs
            return JSONResponse(chat_contract.refusal(sent or ""), status_code=409)
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

    pages.assets(app)
    for path, html in pages.pages().items():
        app.add_api_route(path, fixed_page(html), methods=["GET"], response_class=HTMLResponse)

    def start_chat(prompt: str, done: Ended | None = None) -> dict[str, Any]:
        """Open the shaping chat with ``prompt`` in the background, or say why not and give the command by hand."""
        try:
            shaper = store.settings().agent("shaper")
        except SettingsUnset as exc:
            command = shlex.join(["code", "chat", "-m", SHAPER_MODE, prompt])
            return {"started": False, "command": command, "reason": str(exc)}
        except StoreError as exc:
            command = shlex.join(["code", "chat", "-m", SHAPER_MODE, prompt])
            return {"started": False, "command": command, "reason": f"the settings are unreadable ({exc})"}
        prompt += PICKER_NOTE.format(model=shaper.model, effort=shaper.effort)
        command = shlex.join(["code", "chat", "-m", SHAPER_MODE, prompt])
        if not which("code"):
            return {"started": False, "command": command, "reason": f"`code` is not on PATH; run this in {host.repo}"}

        def work() -> dict[str, str]:
            return launch(host.repo, shaper, prompt)

        try:
            with admitted(host):
                return {"started": True, "launch": launches.start(work, command, done)}
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
        q = loop.open_question(c) if not merge else None
        q = q.model_copy(update={"options": held.offered(store, c, q)}) if q else None
        shown = q and q.model_dump(mode="json", include={"id", "text", "options"}) | {"ordinary": loop.ordinary(q)}
        waiting = o and o.exit == Exit.PENDING and o.waiting == Waiting.PERSON_CHECK and o.who == "you"
        checks = [person_check(c, p, inputs=evidence.check_inputs(c, p, check.fingerprints(c, p)), waiting=bool(
            waiting and c.step.task == p.id)) for p in c.checks]  # fmt: skip
        prefs, fault = display_prefs(store)
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
                    "decisions": [x.model_dump(exclude={"id", "replaces"}) for x in c.brief.decisions],  # as drafted
                    "specified": c.brief.specified,
                    "approved_at": c.brief.approved_at.isoformat() if c.brief.approved_at else None,
                    "ui": c.brief.ui,
                    "visual": [s.model_dump() for s in c.brief.visual],
                    "unapprovable": brief_rounds.approvable(c),  # TD-249: why the approve button is off
                    "unreviewed": brief_rounds.unreviewed(c),  # TD-255: approving needs the owner's tick
                    "read_backs": decisions_gate.checkpoint(store, c),  # TD-427: at most three, never blocking
                    "picked": picks.shown(c),  # TD-459: the decisions this version's work follows, by title
                },
                "criteria": [k.model_dump() for k in c.brief.criteria],
                "plan": [t.model_dump() for t in c.plan.tasks] if c.plan else [],
                "handled": [
                    h.model_dump(mode="json", include={"item", "kind", "url", "how", "text", "resolved", "at"})
                    for h in c.handled
                ],
                "question": shown,
                "retry": rebuilds.shown(c, q),  # TD-217: the plan tasks beside the final review's retry question
                "rounds": round_marks.shown(c),  # TD-217: each loop's round markers, details and what is left
                "checks": checks,
                "pr": c.names.pr,
                "target": c.names.target,
                "asks_merge": prefs["asks_merge"],  # None while unset: the page asks the owner
                "deletes_branch": prefs["deletes_branch"],
                "settings_fault": fault,  # set while a layer is unreadable: the page says so, nothing is assumed
                "paused": c.intent.paused_at is not None,
                "finished": c.finished_at is not None,
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
                "watcher": watcher(store, slug),
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
    router.include_router(answers.router(store, read, put))
    router.include_router(chat_routes.router(read))
    wake, ending = lambda: host.wake.set(), lambda: host.draining()  # noqa: PLW0108 - read late
    router.include_router(brief_routes.router(store, read, wake, ending))
    router.include_router(backlog_routes.router(store, start_chat, lambda: host.record.project))
    router.include_router(memory_routes.router(store))
    router.include_router(decision_routes.project(store, lambda: host.repo))
    job = session_slots.packed(host, pack or pack_job.Job(store))  # its sessions count as the project's (TD-336)
    router.include_router(pack_routes.router(store, job, lambda: admitted(host), host))
    app.include_router(router)
    app.state.busy = lambda: [  # work admitted outside a request, which a project's stop waits for (TD-242)
        *(["a shaping chat opening"] if launches.opening else []),
        *(["an Impeccable update"] if job.busy() else []),
    ]
    return app
