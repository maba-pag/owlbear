import asyncio
import base64
import functools
import http.server
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from owlbear_delivery_next import api, briefs, host, loop, runner, sdk_adapter, tools
from owlbear_delivery_next.models import (
    VISUAL,
    AnswerItem,
    Brief,
    Change,
    Criterion,
    Environment,
    ErrorKind,
    Exit,
    Names,
    PersonCheck,
    Plan,
    Profile,
    Step,
    StepKind,
    Stop,
    Task,
    VisualResult,
    VisualState,
)
from owlbear_delivery_next.sdk_adapter import Policy, Run
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import check, merge, visual
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
MISSING, CRASHED = "Executable doesn't exist", "browser crashed"
HOME = VisualState(name="home", path="/", expect="The greeting is centred")


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


@pytest.fixture
def clone(tmp_path):
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(work, "switch", "-q", "-c", "owlbear/c1")
    return work


def commit(work, name, text="x\n"):
    (work / name).parent.mkdir(parents=True, exist_ok=True)
    (work / name).write_text(text)
    git(work, "add", name)
    git(work, "commit", "-q", "-m", f"edit {name}")
    return git(work, "rev-parse", "HEAD")


def change(worktree="", states=(HOME,), slug="c1", **fields):
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["web"], checks=["npm test"])])
    names = Names(branch=f"owlbear/{slug}", target="main", worktree=str(worktree))
    brief = Brief(version=1, ui=bool(states), visual=list(states))
    return Change(slug=slug, brief=brief, plan=plan, step=Step(kind=StepKind.MERGE), names=names, **fields)


def rv(verdict, findings=()):
    return tools.ReviewResult(verdict=verdict, findings=list(findings), covered_paths=["home-1280.png"])


def draft(**fields):
    base = {"title": "Greet", "outcome": "The page greets the owner.", "criteria": ["The page greets Ada"]}
    return tools.BriefDraft(**(base | {"scope": ["web"]} | fields))


# Brief


def test_a_ui_brief_needs_states_or_a_person_check_and_states_stay_under_the_preview_root():
    assert any("empty for a UI Change" in e for e in tools.check_brief(draft(ui=True)))
    person = {"name": "look", "steps": ["Open the page"], "expect": "Hallo"}
    assert any("visual: true" in e for e in tools.check_brief(draft(ui=True, person_checks=[person])))
    assert tools.check_brief(draft(ui=True, person_checks=[person | {"visual": True}])) == []
    assert tools.check_brief(draft(ui=True, visual=[HOME.model_dump(exclude={"version"})])) == []
    bad = [{"name": "a", "path": "/../x", "expect": "e"}, {"name": "a", "path": "//evil", "expect": "e"}]
    errors = tools.check_brief(draft(visual=bad))
    assert sum("must stay under the preview root" in e for e in errors) == 2
    assert "visual: names repeat - give each state its own name" in errors
    reserved = tools.check_brief(draft(person_checks=[person | {"name": VISUAL}]))
    assert any("reserved for the visual check" in e for e in reserved)
    with pytest.raises(ValidationError):
        draft(visual=[{"name": f"s{i}", "path": "/", "expect": "e"} for i in range(7)])
    with pytest.raises(ValidationError):
        draft(visual=[{"name": "s", "path": "/", "expect": "e" * 301}])


def test_revising_a_state_raises_only_its_version():
    home, about = {"name": "home", "path": "/", "expect": "Hallo"}, {"name": "about", "path": "/about", "expect": "Us"}
    first = briefs.drafted(None, draft(ui=True, visual=[home, about]), "c1", "c1", Profile())
    second = briefs.drafted(
        first, draft(ui=True, visual=[home | {"expect": "Hallo, Ada"}, about]), "c1", "c1", Profile()
    )
    assert [(s.name, s.version) for s in second.brief.visual] == [("home", 2), ("about", 1)]


def test_marking_a_person_check_visual_is_a_new_procedure():
    look = {"name": "look", "steps": ["Open the page"], "expect": "Hallo"}
    first = briefs.drafted(None, draft(person_checks=[look]), "c1", "c1", Profile())
    second = briefs.drafted(first, draft(person_checks=[look | {"visual": True}]), "c1", "c1", Profile())
    assert [(p.visual, p.procedure) for p in second.checks] == [(True, 2)]


# UI detection by diff


def test_a_ui_diff_without_a_visual_check_asks_once_and_not_ui_is_a_decided_decision(clone):
    head = commit(clone, "web/app.css")
    c = change(clone, states=())
    ui = visual.ui_paths(c, head)
    assert ui == ["web/app.css"]
    assert not merge.visual_ok(c, head, ui)
    result = visual.held(c, head, ui)
    assert result.exit == Exit.ASK
    assert result.question.text == "This Change touches UI files (web/app.css) but its brief has no visual check"
    assert [o.label for o in result.question.options] == ["Revise the brief", "Not a UI change", "Pause"]
    c = loop.apply(c, result, NOW)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question=c.outcome.question, option=visual.NOT_UI)], NOW)
    c = visual.decide(visual.decide(c, ui, NOW), ui, NOW)
    text = f"Not a UI change (brief v1, UI paths {visual.digest(ui)})"
    assert [(d.text, d.origin, d.paths) for d in c.decisions] == [(text, "decided", ui)]
    assert merge.visual_ok(c, head, ui)
    assert merge.visual_ok(c, head, [])  # fewer UI paths stay covered
    more = [*ui, "web/new.tsx"]
    assert not merge.visual_ok(c, head, more)  # a new UI path asks again
    assert visual.held(c, head, more).exit == Exit.ASK
    c.brief.version = 2  # the decision holds for its brief version only
    assert not merge.visual_ok(c, head, ui)


def test_revise_the_brief_returns_to_shaping(clone):
    head = commit(clone, "web/index.html")
    c = change(clone, states=())
    c = loop.apply(c, visual.held(c, head, visual.ui_paths(c, head)), NOW)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question=c.outcome.question, option="brief")], NOW)
    assert c.step.kind == StepKind.SHAPE
    assert not visual.not_ui(c, ["web/index.html"])


def test_renames_ui_directories_and_template_suffixes_count_as_ui(clone):
    commit(clone, "web/a.css")
    git(clone, "push", "-q", "origin", "HEAD:refs/heads/main")  # the stylesheet exists on the target
    git(clone, "mv", "web/a.css", "notes.txt")
    git(clone, "commit", "-q", "-m", "move")
    commit(clone, "src/components/Button.ts")
    head = commit(clone, "site/page.njk")
    c = change(clone, states=())
    assert visual.ui_paths(c, head) == ["site/page.njk", "src/components/Button.ts", "web/a.css"]
    assert not visual.is_ui("src/a.py")


def test_a_non_ui_diff_and_a_person_check_pass_without_states(clone):
    head = commit(clone, "src/a.py")
    c = change(clone, states=())
    assert visual.ui_paths(c, head) == []
    assert merge.visual_ok(c, head, [])
    c.brief.ui = True
    assert not merge.visual_ok(c, head, [])
    c.checks = [PersonCheck(id="look", criteria=["AC-1"])]
    assert not merge.visual_ok(c, head, [])  # a person check must be marked visual
    c.checks = [PersonCheck(id="look", criteria=["AC-1"], visual=True)]
    assert merge.visual_ok(c, head, [])


def test_an_unreadable_diff_counts_as_ui(tmp_path):
    assert visual.ui_paths(change(tmp_path, states=()), "b" * 40) == ["(the diff could not be read)"]


# Gate


def test_a_passed_visual_check_holds_only_for_its_exact_head_tree_and_state_versions(clone):
    head = commit(clone, "web/app.css")
    c = change(clone)
    assert not merge.visual_ok(c, head, [])  # fail-closed without a result
    shots = [visual.Shot("home", 1280, "home-1280.png"), visual.Shot("home", 390, "home-390.png")]
    c, result = visual.judged(c, head, visual.tree(clone, head), shots, verdict=rv("pass"), now=NOW)
    assert (result.exit, c.visual.passed, c.visual.states) == (Exit.DONE, True, {"home": 1})
    assert merge.visual_ok(c, head, [])
    newer = commit(clone, "web/app.css", "y\n")
    assert not merge.visual_ok(c, newer, [])
    held = visual.held(c, newer, [])
    assert (held.exit, held.back_to) == (Exit.BACK, StepKind.FOLLOW)
    c.brief.visual[0].version = 2
    assert not merge.visual_ok(c, head, [])
    c.brief.visual[0].version = 1
    c.brief.criteria = [Criterion(id="AC-1", text="The page greets Ada", version=2)]
    assert not merge.visual_ok(c, head, [])  # a revised criterion voids the judgement
    assert not merge.visual_ok(c, "c" * 40, [])  # an unreadable head tree is never accepted


def test_a_fix_verdict_becomes_a_builder_repair_task(clone):
    head = commit(clone, "web/app.css")
    c = change(clone)
    verdict = rv("fix", [tools.Finding(place="home 390px", problem="text overflows", fix="wrap it")])
    shots = [visual.Shot("home", 1280, "home-1280.png"), visual.Shot("home", 390, "home-390.png")]
    c, result = visual.judged(c, head, visual.tree(clone, head), shots, verdict=verdict, now=NOW)
    assert (result.exit, result.back_to, c.visual.passed) == (Exit.BACK, StepKind.BUILD, False)
    assert c.visual.findings == ["home 390px: text overflows - fix: wrap it"]
    after = loop.apply(c, result, NOW)
    assert (after.step.kind, after.step.task) == (StepKind.BUILD, result.fix_task.id)
    assert any(t.id == result.fix_task.id for t in after.plan.tasks)


def test_an_unanswered_url_is_a_finding_and_a_capture_without_judgement_never_passes(clone):
    head = commit(clone, "web/app.css")
    c = change(clone)
    shots = [visual.Shot("home", 1280, error="/ did not answer: net::ERR_CONNECTION_REFUSED")]
    c, result = visual.judged(c, head, "t", shots, verdict=rv("pass"), now=NOW)
    assert (result.exit, c.visual.passed) == (Exit.BACK, False)
    assert c.visual.findings == ["home at 1280px: / did not answer: net::ERR_CONNECTION_REFUSED"]
    for shots, verdict in (([], rv("pass")), ([visual.Shot("home", 1280, "f.png")], None)):
        c, result = visual.judged(change(clone), head, "t", shots, verdict=verdict, now=NOW)
        assert (result.exit, c.visual.passed) == (Exit.BACK, False)


# Runner flow with a fake capturer and reviewer


class FakeReview:
    def __init__(self, verdict="pass"):
        self.calls, self.verdict, self.termination = [], verdict, sdk_adapter.Termination(confirmed=True)

    async def __call__(self, cfg):
        self.calls.append(cfg)
        return Run(cfg.session_id, ending="result", payload=rv(self.verdict), termination=self.termination)


def checking(store, clone):
    env = Environment(check=VISUAL, command="npm run preview", directory=".", ready_url="http://127.0.0.1:4173/x")
    c = change(clone, env=env.model_copy(update={"ready_at": NOW}))
    c.step = Step(kind=StepKind.CHECK, task=VISUAL)
    store.write(Lock("c1"), c)
    return c


@pytest.fixture
def flow(tmp_path, clone, monkeypatch):
    commit(clone, "web/app.css")
    store, review = Store(tmp_path / "store"), FakeReview()
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: clone)
    monkeypatch.setattr(runner.sdk_adapter, "run", review)
    seen = []

    def fake(base, states, out):
        seen.append(base)
        out.mkdir(parents=True, exist_ok=True)
        shots = []
        for s in states:
            for w, _h in visual.VIEWPORTS:
                (out / f"{s.name}-{w}.png").write_bytes(PNG)
                shots.append(visual.Shot(s.name, w, f"{s.name}-{w}.png"))
        return shots

    monkeypatch.setattr(visual, "CAPTURE", fake)
    return SimpleNamespace(store=store, review=review, clone=clone, seen=seen, mp=monkeypatch)


def test_a_capture_is_judged_from_png_blob_attachments_and_passes(flow):
    c = checking(flow.store, flow.clone)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert flow.seen == ["http://127.0.0.1:4173"]
    assert (after.visual.passed, after.visual.files) == (True, ["home-1280.png", "home-390.png"])
    cfg = flow.review.calls[0]
    assert [(a["type"], a["mimeType"], a["displayName"]) for a in cfg.attachments] == [
        ("blob", "image/png", "home-1280.png"),
        ("blob", "image/png", "home-390.png"),
    ]
    assert base64.b64decode(cfg.attachments[0]["data"]) == PNG
    assert "The greeting is centred" in cfg.message
    head = git(flow.clone, "rev-parse", "HEAD")
    assert (flow.store.visual_dir("c1", head) / "home-390.png").read_bytes() == PNG
    assert merge.visual_ok(after, head, [])


def test_the_reviewer_must_cover_every_screenshot(flow):
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    st = sdk_adapter._Step(flow.review.calls[0], SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    args = {"verdict": "pass", "findings": [], "covered_paths": ["home-1280.png"]}
    reply = st._handle(tools.REVIEW, SimpleNamespace(arguments=args))  # noqa: SLF001
    assert "home-390.png" in str(reply)
    assert st.run.payload is None


def test_an_unconfirmed_termination_wins_over_a_passing_verdict(flow):
    flow.review.termination = sdk_adapter.Termination(confirmed=False, survivors=(123,))
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert (after.outcome.exit, after.visual) == (Exit.STOP, None)


def test_screenshots_over_the_review_budget_are_findings(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x" * (visual.MAX_BYTES - 10))
    (tmp_path / "b.png").write_bytes(b"x" * 20)
    shots = visual.capped(tmp_path, [visual.Shot("home", 1280, "a.png"), visual.Shot("about", 1280, "b.png")])
    assert [(s.file, s.error) for s in shots] == [
        ("a.png", ""),
        ("", "state about takes the screenshots over the 12 MB review cap"),
    ]


def test_the_launch_recipe_follows_the_worker_path_policy(tmp_path):
    def errors(command):
        fields = {"directory": ".", "command": command, "ready_url": "http://127.0.0.1:4173/", "summary": "ran"}
        recipe = tools.CheckRecipe(**fields)
        return tools.check_recipe(recipe, tools.Worktree("h", "h"), ["npm run preview"], tmp_path)

    assert any("/outside is outside the worktree" in e for e in errors("npm run preview --prefix /outside"))
    assert errors("npm run preview -- --port 4173") == []


def test_a_visual_environment_is_disposed_on_stop_or_abandon_and_its_runner_crash_is_charged(flow):
    c = checking(flow.store, flow.clone)
    assert check.action(c, live=True, paths={}) == "keep"
    stopped = c.model_copy(update={"stop": Stop(kind=ErrorKind.LIVENESS, reason="r", action="a", resume="r", at=NOW)})
    assert check.action(stopped, live=True, paths={}) == "dispose"
    abandoned = c.model_copy(deep=True)
    abandoned.intent.abandoned_at = NOW
    assert check.action(abandoned, live=True, paths={}) == "dispose"
    rec = SimpleNamespace(started_at=NOW)
    assert host.disappeared(c, rec, NOW)
    person = c.model_copy(update={"env": c.env.model_copy(update={"check": "look"})})
    assert not host.disappeared(person, rec, NOW)


def test_a_missing_chromium_asks_with_the_install_command(flow):
    def missing(*_a):
        raise visual.BrowserMissingError(MISSING)

    flow.mp.setattr(visual, "CAPTURE", missing)
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    question = next(q for q in after.questions if q.id == after.outcome.question)
    assert after.outcome.exit == Exit.ASK
    assert "uv run playwright install chromium" in question.text
    assert (after.visual, flow.review.calls) == (None, [])


def test_a_capture_error_is_never_a_pass(flow):
    def crash(*_a):
        raise RuntimeError(CRASHED)

    flow.mp.setattr(visual, "CAPTURE", crash)
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert after.outcome.exit == Exit.RETRY
    assert CRASHED in after.outcome.reason
    assert (after.visual, flow.review.calls) == (None, [])


def test_a_failed_shot_skips_the_reviewer_and_becomes_a_repair_task(flow):
    flow.mp.setattr(visual, "CAPTURE", lambda *_a: [visual.Shot("home", 1280, error="/ answered 500")])
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert flow.review.calls == []
    assert (after.step.kind, after.visual.passed, after.visual.findings) == (
        StepKind.BUILD,
        False,
        ["home at 1280px: / answered 500"],
    )


def test_attachments_are_sent_with_the_first_message_only_when_present():
    sends = []

    async def send(message, **extra):
        sends.append((message, extra))

    for attached in ((), ({"type": "blob", "data": "eA==", "mimeType": "image/png", "displayName": "a.png"},)):
        session = SimpleNamespace(send=send)
        client = SimpleNamespace(create_session=lambda s=session, **_o: asyncio.sleep(0, s))
        cfg = sdk_adapter.Session(
            StepKind.REVIEW,
            Path(),
            "s1",
            "look",
            resume=False,
            policy=Policy(Path(), (), write=False),
            observe=tools.Worktree,
            checks=(),
            journal=sdk_adapter.Journal(event=lambda _e: None),
            attachments=attached,
        )
        st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
        asyncio.run(sdk_adapter._open(client, st))  # noqa: SLF001
    assert sends == [("look", {}), ("look", {"attachments": [attached[0]]})]


# Visibility


class Host:
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

    def activity(self, _slug):
        return Activity(host_up=True)


def test_the_screenshot_endpoint_serves_only_this_changes_recorded_files(tmp_path):
    store, head = Store(tmp_path / "store"), "a" * 40
    for slug, files in (("c1", ["home-1280.png"]), ("c2", ["home-1280.png", "other-1280.png"])):
        c = change(slug=slug)
        c.visual = VisualResult(head=head, tree="t", states={"home": 1}, files=files, passed=True, at=NOW)
        store.write(Lock(slug), c)
        folder = store.visual_dir(slug, head)
        folder.mkdir(parents=True)
        for f in files:
            (folder / f).write_bytes(PNG + slug.encode())
    (store.visual_dir("c1", head).parent / "secret-1280.png").write_bytes(b"secret")
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    ok = client.get("/api/next/changes/c1/visual/home-1280.png")
    assert (ok.status_code, ok.headers["content-type"], ok.content) == (200, "image/png", PNG + b"c1")
    assert client.get("/api/next/changes/c1").json()["visual"]["files"] == ["home-1280.png"]
    for name in ("other-1280.png", "..%2Fsecret-1280.png", "%2E%2E%2Fsecret-1280.png", "..%2F..%2Fc2%2Fx.png"):
        assert client.get(f"/api/next/changes/c1/visual/{name}").status_code == 404
    assert client.get(
        "/api/next/changes/c1/visual/home-1280.png", headers={"authorization": "Bearer x"}
    ).status_code in {
        401,
        403,
    }


# One real capture


@pytest.mark.browser
def test_a_real_capture_of_a_local_page(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><title>t</title><h1>Hallo, Ada!</h1>")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    states = [HOME, VisualState(name="gone", path="/missing", expect="nothing")]
    try:
        shots = visual.capture(f"http://127.0.0.1:{server.server_port}", states, tmp_path / "out", timeout_ms=5000)
    except visual.BrowserMissingError as exc:
        pytest.skip(f"Chromium is not installed: {exc}")
    finally:
        server.shutdown()
    assert [(s.state, s.width, bool(s.file)) for s in shots] == [
        ("home", 1280, True),
        ("home", 390, True),
        ("gone", 1280, False),
        ("gone", 390, False),
    ]
    assert (tmp_path / "out" / "home-390.png").read_bytes().startswith(b"\x89PNG")
    assert shots[2].error == "/missing answered 404"


class Redirect(http.server.BaseHTTPRequestHandler):
    target = ""

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", self.target)
        self.end_headers()

    def log_message(self, *_a):
        pass


@pytest.mark.browser
def test_a_state_that_leaves_the_preview_is_a_finding(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><h1>elsewhere</h1>")
    other = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    )
    handler = type("R", (Redirect,), {"target": f"http://127.0.0.1:{other.server_port}/"})
    preview = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    for server in (other, preview):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        shots = visual.capture(f"http://127.0.0.1:{preview.server_port}", [HOME], tmp_path / "out", timeout_ms=5000)
    except visual.BrowserMissingError as exc:
        pytest.skip(f"Chromium is not installed: {exc}")
    finally:
        preview.shutdown()
        other.shutdown()
    assert {s.error for s in shots} == {f"state home left the preview (http://127.0.0.1:{other.server_port})"}


@pytest.mark.browser
def test_a_page_over_the_height_cap_is_a_finding(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text('<!doctype html><div style="height:7000px">long</div>')
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        shots = visual.capture(f"http://127.0.0.1:{server.server_port}", [HOME], tmp_path / "out", timeout_ms=5000)
    except visual.BrowserMissingError as exc:
        pytest.skip(f"Chromium is not installed: {exc}")
    finally:
        server.shutdown()
    assert all(not s.file and "over the 6000px cap" in s.error for s in shots), shots
