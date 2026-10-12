import asyncio
import base64
import dataclasses
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

from owlbear_delivery_next import api, briefs, host, loop, permissions, processes, runner, sdk_adapter, tools
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.models import (
    VISUAL,
    Brief,
    Change,
    Criterion,
    Environment,
    ErrorKind,
    Exit,
    Names,
    PageError,
    PersonCheck,
    Plan,
    Step,
    StepKind,
    Stop,
    Task,
    VisualResult,
    VisualState,
)
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.session_result import Run
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


def err(text, width=1280, kind="console", state="home"):
    return PageError(state=state, version=1, width=width, kind=kind, text=text)


def test_an_error_is_existing_only_if_a_good_before_shot_of_that_state_version_and_width_had_it():
    seen = [err("TypeError: x is undefined", kind="page"), err("404 /a.png", 1920)]
    before = VisualResult(head="b", tree="t", files=["home-1280.png"], errors=seen, at=NOW)
    after = [err("TypeError: x is undefined", kind="page"), err("404 /a.png"), err("404 /b.png")]
    new, old = visual.classify(after, before)
    assert old == [after[0]]  # same state, version, width, kind and text
    assert new == after[1:]  # seen only at another width; never seen
    assert visual.classify(after, None) == (after, [])  # no before: never a clean baseline
    failed = before.model_copy(update={"files": []})  # the before shot of that width failed
    assert visual.classify(after, failed) == (after, [])


def test_new_errors_fail_with_the_reviewers_findings_and_existing_ones_never_fail(clone):
    head = commit(clone, "web/app.css")
    shots = [visual.Shot("home", 1280, "home-1280.png", errors=(err("old"),))]
    before = VisualResult(head="b", tree="t", files=["home-1280.png"], errors=[err("old")], at=NOW)
    c, result = visual.judged(change(clone, before=before), head, "t", shots, verdict=rv("pass"), now=NOW)
    assert (result.exit, c.visual.passed, c.visual.errors) == (Exit.DONE, True, [err("old")])
    shots = [visual.Shot("home", 1280, "home-1280.png", errors=(err("old"), err("boom", kind="page")))]
    verdict = rv("fix", [tools.Finding(place="home-1280.png", problem="text overflows", fix="wrap it")])
    c, result = visual.judged(change(clone, before=before), head, "t", shots, verdict=verdict, now=NOW)
    assert (result.exit, c.visual.passed) == (Exit.BACK, False)
    assert c.visual.findings == [
        "home at 1280px: new page error: boom",
        "home-1280.png: text overflows - fix: wrap it",
    ]
    assert "new page error: boom" in result.fix_task.detail
    assert "text overflows" in result.fix_task.detail


def test_the_review_cap_keeps_each_shots_errors(tmp_path):
    (tmp_path / "home-1280.png").write_bytes(PNG)
    shot = visual.Shot("home", 1280, "home-1280.png", errors=(err("boom"),))
    assert visual.capped(tmp_path, [shot])[0].errors == (err("boom"),)


def test_doubt_is_only_offered_when_nothing_is_definitely_wrong(clone):
    head = commit(clone, "web/app.css")
    good = [visual.Shot("home", 1280, "home-1280.png")]
    c, result = visual.judged(change(clone), head, "t", good, verdict=unsure(), now=NOW)
    assert (result.exit, c.visual.passed, result.question.options[0].next) == (Exit.ASK, False, "accept")
    noisy = [visual.Shot("home", 1280, "home-1280.png", errors=(err("boom", kind="page"),))]
    c, result = visual.judged(change(clone), head, "t", noisy, verdict=unsure(), now=NOW)
    assert (result.exit, c.visual.findings) == (Exit.BACK, ["home at 1280px: new page error: boom"])
    broken = [visual.Shot("home", 1280, error="/ answered 500")]
    assert visual.judged(change(clone), head, "t", broken, verdict=unsure(), now=NOW)[1].exit == Exit.BACK


def test_only_the_visual_review_may_be_unsure_and_it_must_say_why():
    tree = tools.Worktree("h", "b", changed=("home-1280.png",))
    bare = tools.VisualReviewResult(verdict="unsure", covered_paths=["home-1280.png"])
    assert tools.check_review(bare, tree, visual=True) == [
        "doubts: empty - an unsure verdict names each screenshot and what you cannot decide"
    ]
    assert tools.check_review(unsure(), tree, visual=True) == []
    with pytest.raises(ValidationError):
        tools.ReviewResult(verdict="unsure")


def test_a_failed_shot_keeps_the_new_errors_in_the_findings_and_long_details_split_not_cut(clone):
    head = commit(clone, "web/app.css")
    shots = [visual.Shot("home", 1280, error="/ answered 500", errors=(err("boom", kind="page"),))]
    c, _ = visual.judged(change(clone), head, "t", shots, verdict=None, now=NOW)
    assert c.visual.findings == ["home at 1280px: / answered 500", "home at 1280px: new page error: boom"]
    noisy = [visual.Shot("home", 1280, "home-1280.png", errors=tuple(err(f"e{i} " + "x" * 250) for i in range(30)))]
    verdict = rv("fix", [tools.Finding(place="home-1280.png", problem="text overflows", fix="wrap it")])
    c, result = visual.judged(change(clone), head, "t", noisy, verdict=verdict, now=NOW)
    details = [result.fix_task.detail, *(t.detail for t in result.more_fixes)]
    assert all(len(d) <= 4000 for d in details)
    assert "text overflows" in details[-1]  # the reviewer's finding survives the error noise


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
        self.calls, self.verdict, self.termination = [], verdict, processes.Termination(confirmed=True)

    async def __call__(self, cfg):
        self.calls.append(cfg)
        payload = unsure() if self.verdict == "unsure" else rv(self.verdict)
        return Run(cfg.session_id, ending="result", payload=payload, termination=self.termination)


def unsure():
    doubt = {"place": "home-1280.png", "question": "Is the greeting meant to wrap at 1280px?"}
    return tools.VisualReviewResult(verdict="unsure", doubts=[doubt], covered_paths=["home-1280.png"])


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

    def fake(base, states, out, widths):
        seen.append(base)
        flow.widths.append(list(widths))
        out.mkdir(parents=True, exist_ok=True)
        shots = []
        for s in states:
            for w in widths:
                (out / f"{s.name}-{w}.png").write_bytes(PNG)
                shots.append(visual.Shot(s.name, w, f"{s.name}-{w}.png"))
        return shots

    monkeypatch.setattr(visual, "CAPTURE", fake)
    flow = SimpleNamespace(store=store, review=review, clone=clone, seen=seen, mp=monkeypatch, widths=[])
    return flow


def test_the_reviewer_is_told_each_new_and_existing_error_as_data(flow):
    c = checking(flow.store, flow.clone)
    c.before = VisualResult(head="b", tree="t", files=["home-1280.png"], widths=[1280], errors=[err("old")], at=NOW)
    flow.store.write(Lock("c1"), c)
    plain = visual.CAPTURE

    def noisy(base, states, out, widths):
        return [
            dataclasses.replace(s, errors=(err("old"), err("boom", kind="page")))
            for s in plain(base, states, out, widths)
        ]

    flow.mp.setattr(visual, "CAPTURE", noisy)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    message = flow.review.calls[0].message
    assert "- new, home at 1280px, page error: boom" in message
    assert "- existing, home at 1280px, console error: old" in message


def test_the_capture_uses_the_widths_the_settings_name(flow):
    flow.store.update_config(lambda cur: cur.model_copy(update={"widths": [1600]}))
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    assert (flow.widths, flow.store.read("c1").visual.files) == ([[1600]], ["home-1600.png"])


def test_a_changes_before_screenshots_fix_its_widths_so_every_after_shot_has_its_pair(flow):
    c = checking(flow.store, flow.clone)
    c.before = VisualResult(head="b", tree="t", files=["home-1280.png"], widths=[1280], at=NOW)
    flow.store.write(Lock("c1"), c)
    flow.store.update_config(lambda cur: cur.model_copy(update={"widths": [1600]}))
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    assert (flow.widths, flow.store.read("c1").visual.files) == ([[1280]], ["home-1280.png"])


def test_a_capture_is_judged_from_png_blob_attachments_and_passes(flow):
    c = checking(flow.store, flow.clone)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert flow.seen == ["http://127.0.0.1:4173"]
    assert (after.visual.passed, after.visual.files) == (True, ["home-1280.png", "home-1920.png", "home-2400.png"])
    cfg = flow.review.calls[0]
    assert [(a["type"], a["mimeType"], a["displayName"]) for a in cfg.attachments] == [
        ("blob", "image/png", "home-1280.png"),
        ("blob", "image/png", "home-1920.png"),
        ("blob", "image/png", "home-2400.png"),
    ]
    assert base64.b64decode(cfg.attachments[0]["data"]) == PNG
    assert "The greeting is centred" in cfg.message
    head = git(flow.clone, "rev-parse", "HEAD")
    assert (flow.store.visual_dir("c1", head) / "home-2400.png").read_bytes() == PNG
    assert merge.visual_ok(after, head, [])


def test_an_unsure_reviewer_makes_the_owner_decide_and_acceptance_holds_only_for_that_capture(flow):
    flow.review.verdict = "unsure"
    c = checking(flow.store, flow.clone)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    asked = flow.store.read("c1")
    q = loop.open_question(asked)
    assert (asked.visual.passed, asked.visual.doubts, [o.next for o in q.options]) == (
        False,
        ["home-1280.png: Is the greeting meant to wrap at 1280px?"],
        ["accept", "repair", "pause"],
    )
    assert not loop.ordinary(q)  # a Changes-page decision (T6)
    assert check.action(asked, live=False, paths={}) == "dispose"  # nothing relaunches before the owner answers
    for empty in (AnswerItem(at=NOW, question=q.id), AnswerItem(at=NOW, question=q.id, text="hmm")):
        still, step = loop.schedule(asked, [empty], NOW)
        assert (step, loop.open_question(still).id, still.visual.decision) == (None, q.id, None)
    client = TestClient(
        api.create_app(flow.store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    refused = client.post("/api/next/changes/c1/answers", json={"question": q.id, "text": "hmm"})
    assert (refused.status_code, "choose one of" in refused.json()["detail"]) == (422, True)
    accepted, step = loop.schedule(asked, [AnswerItem(at=NOW, question=q.id, option="accept")], NOW)
    assert (accepted.visual.decision, step) == ("accept", accepted.step)
    flow.store.write(Lock("c1"), accepted)
    runner._visual(flow.store, Lock("c1"), accepted, flow.clone)  # noqa: SLF001
    done = flow.store.read("c1")
    head = git(flow.clone, "rev-parse", "HEAD")
    assert (len(flow.review.calls), done.visual.passed, done.step.kind) == (1, True, StepKind.MERGE)
    assert merge.visual_ok(done, head, [])


def test_an_acceptance_never_passes_a_capture_of_another_head(flow):
    flow.review.verdict = "unsure"
    c = checking(flow.store, flow.clone)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    asked = flow.store.read("c1")
    accepted, _ = loop.schedule(asked, [AnswerItem(at=NOW, question=asked.outcome.question, option="accept")], NOW)
    flow.store.write(Lock("c1"), accepted)
    commit(flow.clone, "web/app.css", "moved\n")
    flow.review.verdict = "pass"
    runner._visual(flow.store, Lock("c1"), accepted, flow.clone)  # noqa: SLF001
    assert len(flow.review.calls) == 2  # captured and judged again at the new head


def test_a_verdict_whose_usage_stayed_unread_is_never_recorded_and_the_owner_reruns_the_check(flow):
    c = checking(flow.store, flow.clone)
    plain = flow.review.__call__

    async def unread(cfg):
        run = await plain(cfg)
        run.usage_unread = "the usage at the step's end could not be read (RuntimeError)"
        return run

    flow.mp.setattr(runner.sdk_adapter, "run", unread)
    flow.mp.setattr(flow.store, "log", lambda *_a: (_ for _ in ()).throw(OSError(28, "No space left on device")))
    with pytest.raises(OSError, match="No space"):  # the gate is written before anything that can fail
        runner._step(flow.store, Lock("c1"), c, c.step, flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    q = loop.open_question(after)
    assert (after.visual, after.outcome.exit, [o.next for o in q.options]) == (c.visual, Exit.ASK, ["retry"])
    assert "could not be read (RuntimeError)" in q.text
    assert check.action(after, live=True, paths={}) == "dispose"  # no capture resumes before the owner answers


def test_a_session_whose_processes_remain_stops_on_them_even_with_its_usage_unread(flow):
    c = checking(flow.store, flow.clone)
    flow.review.termination = processes.Termination(confirmed=False, survivors=(7,))
    plain = flow.review.__call__

    async def unread(cfg):
        run = await plain(cfg)
        run.usage_unread = "the usage at the step's end could not be read (RuntimeError)"
        return run

    flow.mp.setattr(runner.sdk_adapter, "run", unread)
    runner._step(flow.store, Lock("c1"), c, c.step, flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert (after.outcome.exit, after.stop.reason) == (Exit.STOP, "termination unverified: processes 7 still present")


def test_the_reviewer_must_cover_every_screenshot(flow):
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    st = sdk_adapter._Step(flow.review.calls[0], SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    args = {"verdict": "pass", "findings": [], "covered_paths": ["home-1280.png"]}
    reply = st._handle(st.cfg.submit, SimpleNamespace(arguments=args))  # noqa: SLF001
    assert "home-1920.png" in str(reply)
    assert st.run.payload is None


def test_an_unconfirmed_termination_wins_over_a_passing_verdict(flow):
    flow.review.termination = processes.Termination(confirmed=False, survivors=(123,))
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


def test_screenshots_past_the_measured_count_are_findings(tmp_path):
    (tmp_path / "s.png").write_bytes(PNG)
    shots = visual.capped(tmp_path, [visual.Shot(f"s{n}", 1280, "s.png") for n in range(visual.MAX_SHOTS + 1)])
    assert [s.file for s in shots[:-1]] == ["s.png"] * visual.MAX_SHOTS
    last = f"state s{visual.MAX_SHOTS} takes the screenshots over the {visual.MAX_SHOTS} images one review takes"
    assert (shots[-1].file, shots[-1].error) == ("", last)


def test_the_launch_recipe_follows_the_worker_path_policy(tmp_path):
    def errors(command):
        fields = {"directory": ".", "command": command, "ready_url": "http://127.0.0.1:4173/", "summary": "ran"}
        recipe = tools.CheckRecipe(**fields)
        return tools.check_recipe(recipe, tools.Worktree("h", "h"), ["npm run preview"], tmp_path)

    assert any("/outside is outside the worktree" in e for e in errors("npm run preview --prefix /outside"))
    assert errors("npm run preview -- --port 4173") == []


@pytest.mark.parametrize("command", ["npm run preview", "npm  run preview --port 1", "npm run previews", "npm run"])
def test_the_launch_allow_list_and_the_permission_policy_share_one_rule(tmp_path, command, monkeypatch):
    fields = {"directory": ".", "command": command, "ready_url": "http://127.0.0.1:4173/", "summary": "ran"}
    errs = tools.check_recipe(tools.CheckRecipe(**fields), tools.Worktree("h", "h"), ["npm run preview"], tmp_path)
    assert (not any(e.startswith("command: not an allowed") for e in errs)) is permissions.allowed(
        command, ["npm run preview"]
    )
    monkeypatch.setattr(permissions, "allowed", lambda *_a: False)
    errs = tools.check_recipe(tools.CheckRecipe(**fields), tools.Worktree("h", "h"), ["npm run preview"], tmp_path)
    assert any(e.startswith("command: not an allowed") for e in errs)  # the recipe check asks the policy's rule


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


def test_the_change_detail_reports_the_errors_that_existed_before_the_change(tmp_path):
    store = Store(tmp_path / "store")
    c = change()
    c.before = VisualResult(head="b", tree="t", files=["home-1280.png"], errors=[err("old")], at=NOW)
    errors = [err("old"), err("boom", kind="page")]
    c.visual = VisualResult(head="a" * 40, tree="t", files=["home-1280.png"], errors=errors, at=NOW)
    store.write(Lock("c1"), c)
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    existing = client.get("/api/next/changes/c1").json()["visual_existing_errors"]
    assert existing == ["home at 1280px, console error: old"]


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


class _Missing:
    """Playwright stand-in whose launch fails per channel with the given errors."""

    def __init__(self, errors):
        self.errors, self.tried = errors, []
        self.chromium = SimpleNamespace(launch=self.launch)

    def launch(self, *, headless, channel):
        from playwright.sync_api import Error  # noqa: PLC0415 - the optional runtime's error type

        assert headless
        self.tried.append(channel)
        raise Error(self.errors[channel])

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def test_the_installed_browser_is_tried_first_and_only_missing_browsers_fall_through(tmp_path, monkeypatch):
    import playwright.sync_api  # noqa: PLC0415 - patched where capture imports it

    gone = {"chrome": "Chromium distribution 'chrome' is not found at /x", "msedge": "… is not found at /y"}
    pw = _Missing(gone | {None: "Executable doesn't exist at /z; run playwright install"})
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: pw)
    with pytest.raises(visual.BrowserMissingError):
        visual.capture("http://127.0.0.1:1", [HOME], tmp_path, (1280,))
    assert pw.tried == ["chrome", "msedge", None]
    pw = _Missing({"chrome": "Target page, context or browser has been closed"})
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: pw)
    with pytest.raises(playwright.sync_api.Error):  # another launch failure is not a missing browser
        visual.capture("http://127.0.0.1:1", [HOME], tmp_path, (1280,))
    assert pw.tried == ["chrome"]


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
        shots = visual.capture(
            f"http://127.0.0.1:{server.server_port}", states, tmp_path / "out", (1280, 1920), timeout_ms=5000
        )
    except visual.BrowserMissingError as exc:
        pytest.skip(f"no Chrome, Edge or Playwright Chromium: {exc}")
    finally:
        server.shutdown()
    assert [(s.state, s.width, bool(s.file)) for s in shots] == [
        ("home", 1280, True),
        ("home", 1920, True),
        ("gone", 1280, False),
        ("gone", 1920, False),
    ]
    assert (tmp_path / "out" / "home-1920.png").read_bytes().startswith(b"\x89PNG")
    assert shots[2].error == "/missing answered 404"


@pytest.mark.browser
def test_a_real_capture_records_console_and_page_errors_and_only_new_ones_fail(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    script = "<script>console.error('old warning'); {}</script>"
    (site / "index.html").write_text("<!doctype html><title>t</title><h1>Hi</h1>" + script.format(""))
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        before = visual.capture(url, [HOME], tmp_path / "before", (1280,), timeout_ms=5000)
        (site / "index.html").write_text(
            "<!doctype html><title>t</title><h1>Hi</h1>" + script.format("undefined_call();")
        )
        after = visual.capture(url, [HOME], tmp_path / "after", (1280,), timeout_ms=5000)
    except visual.BrowserMissingError as exc:
        pytest.skip(f"no Chrome, Edge or Playwright Chromium: {exc}")
    finally:
        server.shutdown()
    base = VisualResult(head="b", tree="t", files=["home-1280.png"], errors=list(before[0].errors), at=NOW)
    new, old = visual.classify(list(after[0].errors), base)
    assert [(e.kind, e.text) for e in old] == [("console", "old warning")]
    assert [e.kind for e in new] == ["page"]
    assert "undefined_call" in new[0].text


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
        shots = visual.capture(
            f"http://127.0.0.1:{preview.server_port}", [HOME], tmp_path / "out", (1280,), timeout_ms=5000
        )
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
        shots = visual.capture(
            f"http://127.0.0.1:{server.server_port}", [HOME], tmp_path / "out", (1280,), timeout_ms=5000
        )
    except visual.BrowserMissingError as exc:
        pytest.skip(f"Chromium is not installed: {exc}")
    finally:
        server.shutdown()
    assert all(not s.file and "over the 6000px cap" in s.error for s in shots), shots
