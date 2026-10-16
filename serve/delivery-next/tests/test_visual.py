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

from owlbear_delivery_next import (
    api,
    brief_tools,
    briefs,
    design_pack,
    design_tools,
    detector,
    held,
    host,
    loop,
    processes,
    prompts,
    runner,
    sdk_adapter,
    tools,
)
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
    PersonCheck,
    Plan,
    Step,
    StepKind,
    Stop,
    Task,
    VisualState,
)
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import check, decision, judges, merge, visual
from owlbear_delivery_next.store import Lock, Store
from owlbear_delivery_next.visual_records import (
    DetectorFinding,
    DetectorScan,
    JudgeFinding,
    JudgeVerdict,
    PageError,
    VisualResult,
    VisualRound,
)

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
    return brief_tools.BriefDraft(**(base | {"scope": ["web"]} | fields))


# Brief


def test_a_ui_brief_needs_states_or_a_person_check_and_states_stay_under_the_preview_root():
    check_brief = brief_tools.check_brief
    assert any("empty for a UI Change" in e for e in check_brief(draft(ui=True)))
    person = {"name": "look", "steps": ["Open the page"], "expect": "Hallo"}
    assert any("visual: true" in e for e in check_brief(draft(ui=True, person_checks=[person])))
    assert check_brief(draft(ui=True, person_checks=[person | {"visual": True}])) == []
    assert check_brief(draft(ui=True, visual=[HOME.model_dump(exclude={"version", "steps"})])) == []
    bad = [{"name": "a", "path": "/../x", "expect": "e"}, {"name": "a", "path": "//evil", "expect": "e"}]
    errors = check_brief(draft(visual=bad))
    assert sum("must stay under the preview root" in e for e in errors) == 2
    assert "visual: names repeat - give each state its own name" in errors
    reserved = check_brief(draft(person_checks=[person | {"name": VISUAL}]))
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
    tree = visual.tree(clone, head)
    c, result = visual.judged(c, head, tree, shots, verdict=rv("pass"), now=NOW, kept=rounded(c, head, tree))
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
    tree = visual.tree(clone, head)
    c, result = visual.judged(
        c, head, tree, shots, verdict=verdict, now=NOW, kept=rounded(c, head, tree, correct="fail")
    )
    assert (result.exit, result.back_to, c.visual.passed) == (Exit.BACK, StepKind.BUILD, False)
    assert c.visual.findings == ["home 390px: text overflows - fix: wrap it"]
    after = loop.apply(c, result, NOW)
    assert (after.step.kind, after.step.task) == (StepKind.BUILD, result.fix_task.id)
    assert any(t.id == result.fix_task.id for t in after.plan.tasks)


def err(text, width=1280, kind="console", state="home"):
    return PageError(state=state, version=1, width=width, kind=kind, text=text)


def rounded(c, head, tree="t", *, correct="pass", design="pass", setting="ask", found=()):  # noqa: PLR0913
    """The round both judges recorded, each with a verified verdict."""
    verdicts = [
        JudgeVerdict(lens="correctness", verdict=correct, usage_verified=True),
        JudgeVerdict(lens="design", verdict=design, findings=list(found), usage_verified=True),
    ]
    states = {s.name: s.version for s in c.brief.visual}
    number = len(c.visual_rounds) + 1
    kept = VisualRound(
        number=number, head=head, tree=tree, states=states, design_failures=setting, verdicts=verdicts, at=NOW
    )
    c.visual_rounds.append(kept)
    return kept


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
    c = change(clone, before=before)
    c, result = visual.judged(c, head, "t", shots, verdict=rv("pass"), now=NOW, kept=rounded(c, head))
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


def test_an_oversize_screenshot_keeps_its_errors(tmp_path):
    (tmp_path / "home-1280.png").write_bytes(b"x" * (visual.MAX_BYTES + 1))
    shot = visual.Shot("home", 1280, "home-1280.png", errors=(err("boom"),))
    assert visual.oversize(tmp_path, [shot])[0].errors == (err("boom"),)


def test_doubt_is_only_offered_when_nothing_is_definitely_wrong(clone):
    head = commit(clone, "web/app.css")
    good = [visual.Shot("home", 1280, "home-1280.png")]
    c = change(clone)
    c, result = visual.judged(c, head, "t", good, verdict=unsure(), now=NOW, kept=rounded(c, head))
    assert (result.exit, c.visual.passed, result.question.options[0].next) == (Exit.ASK, False, "accept")
    assert (result.question.cause, c.visual_rounds[-1].outcome) == (decision.CAUSE, "ask")
    seen = tools.Finding(place="home-1280.png", problem="maybe wraps", fix="decide")
    c = change(clone)
    doubtful = unsure().model_copy(update={"findings": [seen]})
    c, result = visual.judged(c, head, "t", good, verdict=doubtful, now=NOW, kept=rounded(c, head, correct="unsure"))
    assert result.exit == Exit.ASK  # an unsure judge's findings are for the owner, never an automatic repair
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
    for shots, verdict in (([], rv("pass")), ([visual.Shot("home", 1280, error="/ answered 500")], None)):
        c, result = visual.judged(change(clone), head, "t", shots, verdict=verdict, now=NOW)
        assert (result.exit, c.visual.passed) == (Exit.BACK, False)
    c, result = visual.judged(change(clone), head, "t", [visual.Shot("home", 1280, "f.png")], verdict=None, now=NOW)
    assert (result.exit, result.cause, c.visual.passed) == (Exit.RETRY, decision.AGAIN, False)  # judged again


# Runner flow with a fake capturer and reviewer


class FakeReview:
    def __init__(self, verdict="pass"):
        self.calls, self.verdict, self.termination = [], verdict, processes.Termination(confirmed=True)
        self.designs, self.design = [], designed  # the design judge's sessions, and how each ends

    async def __call__(self, cfg):
        if cfg.role == "designer":
            self.designs.append(cfg)
            return self.design(cfg)
        self.calls.append(cfg)
        payload = unsure() if self.verdict == "unsure" else rv(self.verdict)
        return Run(cfg.session_id, ending="result", payload=payload, termination=self.termination)


def designed(cfg, verdict="pass", findings=()):
    """A verified two-phase design verdict over the session's images."""
    names = list(cfg.observe().changed)
    pairs = [{"pair": p, "better": "equal", "why": "same"} for p in design_tools.pairs(names)]
    look = design_tools.DesignLook(verdict=verdict, findings=list(findings), preferences=pairs, covered_paths=names)
    final = design_tools.DesignResult(**look.model_dump())
    done = processes.Termination(confirmed=True)
    return Run(cfg.session_id, ending="result", payload=final, first=look, termination=done)


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

    def fake(base, states, out, widths, **_k):
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
    monkeypatch.setattr(runner.design, "pack", lambda: None)  # never this machine's design pack
    flow = SimpleNamespace(store=store, review=review, clone=clone, seen=seen, mp=monkeypatch, widths=[])
    return flow


def test_the_reviewer_is_told_each_new_and_existing_error_as_data(flow):
    c = checking(flow.store, flow.clone)
    c.before = VisualResult(head="b", tree="t", files=["home-1280.png"], widths=[1280], errors=[err("old")], at=NOW)
    flow.store.write(Lock("c1"), c)
    plain = visual.CAPTURE

    def noisy(base, states, out, widths, **k):
        return [
            dataclasses.replace(s, errors=(err("old"), err("boom", kind="page")))
            for s in plain(base, states, out, widths, **k)
        ]

    flow.mp.setattr(visual, "CAPTURE", noisy)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    message = flow.review.calls[0].message
    assert "- new, home at 1280px, page error: boom" in message
    assert "- existing, home at 1280px, console error: old" in message


def test_the_detectors_findings_are_recorded_as_evidence_and_never_fail_the_check(flow):
    def scan(*rules):
        found = [DetectorFinding(rule=r, category="quality", advisory=False, where=".card") for r in rules]
        return DetectorScan(state="home", width=1280, kind="page", scanned=True, findings=found)

    c = checking(flow.store, flow.clone)
    sources = DetectorScan(state="sources", kind="source", scanned=True, covered=["web/app.css"])  # absent there
    c.before = VisualResult(
        head="b",
        tree="t",
        states={"home": 1},
        files=["home-1280.png"],
        widths=[1280],
        design=[scan("old"), sources],
        at=NOW,
    )
    flow.store.write(Lock("c1"), c)
    plain = visual.CAPTURE

    def scanned(base, states, out, widths, **k):
        assert k["pack"] is pack
        return [dataclasses.replace(s, design=scan("old", "fresh")) for s in plain(base, states, out, widths)]

    pack = design_pack.Installed(Path("/nowhere"), "0" * 64, "")
    flow.mp.setattr(visual, "CAPTURE", scanned)
    flow.mp.setattr(runner.design, "pack", lambda: pack)
    flow.mp.setattr(
        detector,
        "scan_source",
        lambda _p, paths, _cwd: [
            detector.Finding("tiny-text", "quality", advisory=False, name="Tiny text", where=f"{p}:1", detail="")
            for p in paths
        ],
    )
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    after = flow.store.read("c1").visual
    assert after.passed  # evidence only: the reviewer's pass stands (TD-77)
    assert [(s.state, s.kind, [(f.rule, f.where, f.freshness) for f in s.findings]) for s in after.design] == [
        ("home", "page", [("old", ".card", "existing"), ("fresh", ".card", "new")]),
        ("sources", "source", [("tiny-text", "web/app.css:1", "new")]),  # the file is new on the Change
    ]


def test_both_judges_run_and_the_round_keeps_the_design_judges_blind_two_phase_verdict(flow):
    c = checking(flow.store, flow.clone)
    old = flow.store.before_dir("c1", "b" * 40)
    old.mkdir(parents=True)
    (old / "home-1280.png").write_bytes(PNG + b"before")
    c.before = VisualResult(head="b" * 40, tree="t", states={"home": 1}, files=["home-1280.png"], widths=[1280], at=NOW)
    flow.store.write(Lock("c1"), c)
    flow.mp.setattr(judges, "SHUFFLE", SimpleNamespace(random=lambda: 0.9))  # "before" comes first, as A
    seen = {"image": "home-1280-B.png", "problem": "cramped", "rule": "Layout & Space", "severity": "P1"}
    first = design_tools.DesignLook(
        verdict="fail",
        findings=[seen],
        preferences=[{"pair": "home-1280", "better": "A", "why": "B crowds the card"}],
        covered_paths=["home-1280-A.png", "home-1280-B.png"],
    )
    final = design_tools.DesignResult(**first.model_dump(), false_positives=["side-tab"])
    done = processes.Termination(confirmed=True)
    flow.review.design = lambda cfg: Run(cfg.session_id, ending="result", payload=final, first=first, termination=done)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    [cfg] = flow.review.designs
    assert (cfg.role, cfg.first_look, cfg.submit) == ("designer", design_tools.FIRST, design_tools.FINAL)
    assert [(a["displayName"], base64.b64decode(a["data"])) for a in cfg.attachments] == [
        ("home-1280-A.png", PNG + b"before"),
        ("home-1280-B.png", PNG),
    ]
    assert "detector" not in cfg.message.lower().split("## judge")[0]  # held back until the first look
    assert "design detector's findings" in cfg.reveal
    [kept] = after.visual_rounds
    assert kept.blind == {"home-1280-A.png": "before", "home-1280-B.png": "after"}
    assert [(i.message, i.reveal, i.images) for i in kept.design_inputs] == [
        (cfg.message, cfg.reveal, ["home-1280-A.png", "home-1280-B.png"])
    ]  # what a calibration replay sends again
    correct, design_verdict = kept.verdicts
    assert (correct.lens, correct.verdict, correct.usage_verified) == ("correctness", "pass", True)
    assert (design_verdict.verdict, design_verdict.unanchored, design_verdict.preferences) == (
        "fail",
        "fail",
        {"home-1280": "before"},
    )
    assert design_verdict.false_positives == ["side-tab"]
    assert [(f.state, f.width, f.severity, f.introduced) for f in design_verdict.findings] == [
        ("home", 1280, "P1", True)
    ]
    assert (design_verdict.model, design_verdict.effort) == ("claude-opus-5.5", "high")
    q = loop.open_question(after)  # a design fail with the default setting: the owner decides
    assert (after.visual.passed, kept.outcome, q.cause, after.step.kind) == (
        False,
        "ask",
        decision.CAUSE,
        StepKind.CHECK,
    )


def test_a_judge_without_a_verified_verdict_runs_again_with_the_capture(flow):
    done = processes.Termination(confirmed=True)
    flow.review.design = lambda cfg: Run(cfg.session_id, ending="error", termination=done)
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    [kept] = after.visual_rounds
    assert (kept.verdicts[1].verdict, kept.verdicts[1].usage_verified, kept.outcome) == (None, False, None)
    assert kept.blind == {"home-1280-A.png": "after", "home-1920-A.png": "after", "home-2400-A.png": "after"}
    assert (after.visual, after.outcome.exit) == (None, Exit.RETRY)  # the outage's own retry, under its budget
    flow.review.design = lambda cfg: designed(cfg).__class__(**{**vars(designed(cfg)), "first": None})
    runner._visual(flow.store, Lock("c1"), after, flow.clone)  # noqa: SLF001
    again = flow.store.read("c1")
    assert (again.visual.passed, again.outcome.exit, again.outcome.cause) == (False, Exit.RETRY, decision.AGAIN)


@pytest.mark.parametrize(
    ("correct", "setting", "step", "sent"),
    [
        ("pass", "back", StepKind.BUILD, ["design"]),  # back by the setting, with the design findings
        ("pass", "ask", StepKind.CHECK, []),  # the owner decides
        ("fix", "back", StepKind.BUILD, ["correctness", "design"]),
        ("fix", "ask", StepKind.BUILD, ["correctness"]),  # the design fail waits for the next round
    ],
)
def test_the_verdict_matrix_routes_a_design_fail_by_the_setting(flow, correct, setting, step, sent):
    flow.store.update_config(lambda cur: cur.model_copy(update={"design_failures": setting}))
    flow.review.verdict = correct
    problem = {"image": "home-1280-A.png", "problem": "cramped card", "rule": "Layout & Space", "severity": "P1"}
    flow.review.design = lambda cfg: designed(
        cfg, "fail", [problem] if "home-1280-A.png" in cfg.observe().changed else []
    )
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert (after.step.kind, after.visual_rounds[-1].outcome) == (step, "back" if step == StepKind.BUILD else "ask")
    detail = next((t.detail for t in after.plan.tasks if t.origin == "review"), "")
    has = {"correctness": "did not accept the screenshots" in detail, "design": "cramped card" in detail}
    assert [lens for lens, seen in has.items() if seen] == sent


def test_a_fail_proposes_only_what_a_failing_judge_found_the_change_introduced_worth_a_fix() -> None:
    def found(n: int, severity: str | None, *, introduced: bool | None) -> JudgeFinding:
        return JudgeFinding(
            id=f"design-{n}", state="home", width=1280, text=f"problem {n}", severity=severity, introduced=introduced
        )

    made = [
        found(1, "P1", introduced=True),
        found(2, "P3", introduced=True),
        found(3, "P0", introduced=False),
        found(4, "P2", introduced=None),
        found(5, "P3", introduced=True).model_copy(update={"rule": "owner-1"}),
    ]
    design = JudgeVerdict(lens="design", verdict="fail", usage_verified=True, findings=made)
    note = JudgeFinding(id="correctness-1", state="home", text="wraps late")
    correct = JudgeVerdict(lens="correctness", verdict="pass", usage_verified=True, findings=[note])
    kept = VisualRound(
        number=1, head="a" * 40, tree="b" * 40, states={"home": 1}, widths=[1280], pack="p",
        design_failures="back", verdicts=[correct, design], at=NOW,
    )  # fmt: skip
    assert decision.proposed(kept) == ["design-1", "design-4", "design-5"]  # an owner's criterion, never polish
    passed = tools.ReviewResult.model_construct(verdict="pass", findings=[])
    route, sent = decision.route(kept, [], passed, broken=False)
    assert (route, [line.rsplit(": ", 1)[1] for line in sent]) == ("back", ["problem 1", "problem 4", "problem 5"])
    polish = kept.model_copy(update={"verdicts": [correct, design.model_copy(update={"findings": made[1:3]})]})
    assert decision.route(polish, [], passed, broken=False) == ("ask", [])  # nothing to fix: the owner looks


def test_the_owner_decides_a_round_with_pass_or_fail_bound_to_its_capture(flow):
    flow.review.verdict = "unsure"
    c = checking(flow.store, flow.clone)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    asked = flow.store.read("c1")
    q, kept = loop.open_question(asked), asked.visual_rounds[-1]
    assert (asked.visual.passed, asked.visual.doubts, [o.id for o in q.options]) == (
        False,
        ["home-1280.png: Is the greeting meant to wrap at 1280px?"],
        ["pass", "fail", "pause"],
    )
    assert not loop.ordinary(q)  # a Changes-page decision (T6)
    assert check.action(asked, live=False, paths={}) == "dispose"  # nothing relaunches before the owner answers
    client = TestClient(
        api.create_app(flow.store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    shown = {"question": q.id, "round": kept.number, "head": kept.head, "pack": kept.pack}
    refused = client.post("/api/next/changes/c1/answers", json={"question": q.id, "text": "hmm"})
    assert (refused.status_code, "choose one of" in refused.json()["detail"]) == (422, True)
    empty = client.post("/api/next/changes/c1/answers", json=shown | {"option": "fail"})
    assert (empty.status_code, "ticks a finding or says what is wrong" in empty.json()["detail"]) == (422, True)
    stale = client.post("/api/next/changes/c1/answers", json=shown | {"option": "pass", "pack": "older"})
    assert (stale.status_code, "changed since the page was shown" in stale.json()["detail"]) == (409, True)
    unknown = client.post("/api/next/changes/c1/answers", json=shown | {"option": "fail", "findings": ["design-9"]})
    assert (unknown.status_code, "design-9" in unknown.json()["detail"]) == (422, True)
    detail = client.get("/api/next/changes/c1").json()
    assert (detail["visual_round"]["number"], detail["owner_criteria"]) == (kept.number, [])
    assert detail["visual_round"]["proposed"] == decision.proposed(kept)  # what the page ticks for the owner
    passed, step = loop.schedule(asked, [AnswerItem(at=NOW, question=q.id, option="pass", round=kept.number)], NOW)
    assert (passed.visual_rounds[-1].decision.outcome, step) == ("pass", passed.step)
    flow.store.write(Lock("c1"), passed)
    runner._visual(flow.store, Lock("c1"), passed, flow.clone)  # noqa: SLF001
    done = flow.store.read("c1")
    head = git(flow.clone, "rev-parse", "HEAD")
    assert (len(flow.review.calls), done.visual.passed, done.step.kind) == (1, True, StepKind.MERGE)
    assert (done.visual_rounds[-1].outcome, done.owner_criteria) == ("merge", [])  # a Pass comment is a note only
    assert merge.visual_ok(done, head, [])


def test_a_fail_sends_the_ticked_findings_back_and_its_comment_becomes_a_criterion_until_withdrawn(flow):
    flow.review.verdict = "unsure"
    problem = {"image": "home-1280-A.png", "problem": "cramped card", "rule": "Layout & Space", "severity": "P2"}
    flow.review.design = lambda cfg: designed(
        cfg, "unsure", [problem] if "home-1280-A.png" in cfg.observe().changed else []
    )
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    asked = flow.store.read("c1")
    q, kept = loop.open_question(asked), asked.visual_rounds[-1]
    [ticked] = [f.id for v in kept.verdicts for f in v.findings]
    item = AnswerItem(at=NOW, question=q.id, option="fail", round=kept.number, findings=[ticked], text="More air")
    failed, _ = loop.schedule(asked, [item], NOW)
    flow.store.write(Lock("c1"), failed)
    runner._visual(flow.store, Lock("c1"), failed, flow.clone)  # noqa: SLF001
    back = flow.store.read("c1")
    fix = next(t for t in back.plan.tasks if t.origin == "review")
    assert (back.step.kind, back.visual_rounds[-1].outcome) == (StepKind.BUILD, "back")
    assert (back.visual.doubts, "owner: More air" in back.visual.findings) == ([], True)  # decided: nothing open
    assert ("cramped card" in fix.detail, "owner: More air" in fix.detail) == (True, True)
    [criterion] = back.owner_criteria
    assert (criterion.id, criterion.text, criterion.round) == ("owner-1", "More air", kept.number)
    assert "owner-1: More air" in prompts.visual(
        back, [("home", 1280, "home-1280.png")]
    )  # every later review checks it
    client = TestClient(
        api.create_app(flow.store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    assert client.post("/api/next/changes/c1/criteria/owner-1/withdraw").status_code == 200
    withdrawn, _ = flow.store.fold(Lock("c1"), "c1", NOW)
    assert withdrawn.owner_criteria[0].withdrawn_at is not None
    assert "owner-1" not in prompts.visual(withdrawn, [("home", 1280, "home-1280.png")])
    assert client.post("/api/next/changes/c1/criteria/owner-9/withdraw").status_code == 404


def test_a_decision_never_passes_a_capture_of_another_head(flow):
    flow.review.verdict = "unsure"
    c = checking(flow.store, flow.clone)
    runner._visual(flow.store, Lock("c1"), c, flow.clone)  # noqa: SLF001
    asked = flow.store.read("c1")
    kept = asked.visual_rounds[-1]
    item = AnswerItem(at=NOW, question=asked.outcome.question, option="pass", round=kept.number)
    passed, _ = loop.schedule(asked, [item], NOW)
    flow.store.write(Lock("c1"), passed)
    commit(flow.clone, "web/app.css", "moved\n")
    flow.review.verdict = "pass"
    runner._visual(flow.store, Lock("c1"), passed, flow.clone)  # noqa: SLF001
    assert len(flow.review.calls) == 2  # captured and judged again at the new head
    assert flow.store.read("c1").visual_rounds[-1].number == kept.number + 1


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


def test_a_round_whose_judge_model_is_unknown_is_accepted_whole_or_run_again(flow):
    c = checking(flow.store, flow.clone)
    plain = flow.review.__call__

    async def unread(cfg):
        run = await plain(cfg)
        if cfg.role != "designer":  # only the correctness judge's model stays unproven
            run.usage_unread = "the usage at the step's end could not be read (RuntimeError)"
        return run

    flow.mp.setattr(runner.sdk_adapter, "run", unread)
    runner._step(flow.store, Lock("c1"), c, c.step, flow.clone)  # noqa: SLF001
    asked = flow.store.read("c1")
    q, kept = loop.open_question(asked), asked.visual_rounds[-1]
    assert (asked.outcome.exit, [o.id for o in q.options], kept.outcome, kept.waivable) == (
        Exit.ASK,
        ["accept", "retry"],
        "model",
        "merge",
    )
    assert "could not be read (RuntimeError)" in q.text
    assert (asked.visual.passed, asked.visual.doubts[0].startswith("correctness: model unknown")) == (False, True)
    assert check.action(asked, live=True, paths={}) == "dispose"  # no capture resumes before the owner answers
    assert [o.id for o in held.offered(flow.store, asked, q)] == ["accept", "retry"]
    accepted, _ = loop.schedule(asked, [AnswerItem(at=NOW, question=q.id, option="accept")], NOW)
    assert accepted.visual_rounds[-1].model_waived
    flow.store.write(Lock("c1"), accepted)
    runner._visual(flow.store, Lock("c1"), accepted, flow.clone)  # noqa: SLF001
    done = flow.store.read("c1")
    assert (len(flow.review.calls), done.visual.passed, done.visual_rounds[-1].outcome) == (1, True, "merge")


def test_a_visual_accept_without_the_model_check_is_withdrawn_once_the_capture_moves(flow):
    c = checking(flow.store, flow.clone)
    plain = flow.review.__call__

    async def unread(cfg):
        run = await plain(cfg)
        run.usage_unread = "no usage report of the window named the step's model gpt-6-luna"
        return run

    flow.mp.setattr(runner.sdk_adapter, "run", unread)
    log = flow.store.log
    flow.mp.setattr(flow.store, "log", lambda *_a: (_ for _ in ()).throw(OSError(28, "No space left on device")))
    with pytest.raises(OSError, match="No space"):  # the gate is written before the held runs are logged
        runner._step(flow.store, Lock("c1"), c, c.step, flow.clone)  # noqa: SLF001
    flow.mp.setattr(flow.store, "log", log)
    asked = flow.store.read("c1")
    q = loop.open_question(asked)
    assert (asked.visual_rounds[-1].outcome, [o.id for o in q.options]) == ("model", ["accept", "retry"])
    flow.store.update_config(lambda cur: cur.model_copy(update={"widths": [1600]}))
    assert [o.id for o in held.offered(flow.store, asked, q)] == ["retry"]  # other widths: no accept
    flow.store.update_config(lambda cur: cur.model_copy(update={"widths": asked.visual_rounds[-1].widths}))
    assert [o.id for o in held.offered(flow.store, asked, q)] == ["accept", "retry"]
    commit(flow.clone, "web/app.css", "moved\n")
    assert [o.id for o in held.offered(flow.store, asked, q)] == ["retry"]
    accepted, _ = loop.schedule(asked, [AnswerItem(at=NOW, question=q.id, option="accept")], NOW)
    flow.store.write(Lock("c1"), accepted)
    flow.mp.setattr(runner.sdk_adapter, "run", plain)
    runner._visual(flow.store, Lock("c1"), accepted, flow.clone)  # noqa: SLF001
    again = flow.store.read("c1")
    assert (len(flow.review.calls), again.visual_rounds[-1].number) == (2, 2)  # captured and judged again


def test_damaged_settings_stop_the_change_once_instead_of_crashing_each_runner(flow):
    c = checking(flow.store, flow.clone)
    flow.store.config_path.parent.mkdir(parents=True, exist_ok=True)
    flow.store.config_path.write_text("{not json")
    runner._step(flow.store, Lock("c1"), c, c.step, flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert (after.outcome.exit, after.stop.kind) == (Exit.STOP, ErrorKind.STATE)
    assert flow.review.calls == []


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


def test_only_a_screenshot_larger_than_one_review_takes_is_a_finding(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x" * (visual.MAX_BYTES + 1))
    (tmp_path / "b.png").write_bytes(b"x" * (visual.MAX_BYTES - 1))
    shots = visual.oversize(tmp_path, [visual.Shot("home", 1280, "a.png"), visual.Shot("about", 1280, "b.png")])
    assert [(s.file, s.error) for s in shots] == [
        ("", "state home at 1280px is over the 12 MB one review takes"),
        ("b.png", ""),
    ]


def test_a_capture_over_one_reviews_budget_is_judged_in_batches_by_both_judges(flow):
    flow.mp.setattr(judges, "batches", lambda images, **_k: [[i] for i in images])  # one image per session
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert [[a["displayName"] for a in c.attachments] for c in flow.review.calls] == [
        ["home-1280.png"],
        ["home-1920.png"],
        ["home-2400.png"],
    ]
    assert len(flow.review.designs) == 3
    assert (after.visual.passed, after.visual.files) == (True, ["home-1280.png", "home-1920.png", "home-2400.png"])


def test_the_launch_recipe_needs_a_clean_worktree_directory_and_a_local_url(tmp_path):
    def errors(dirty=(), **fields):
        base = {"directory": ".", "command": "npm run x", "ready_url": "http://127.0.0.1:4173/", "summary": "ran"}
        return tools.check_recipe(tools.CheckRecipe(**base | fields), tools.Worktree("h", "h", dirty), tmp_path)

    assert errors(command="npm run preview --prefix /outside") == []
    assert errors(("a",))[0].startswith("changes: a edited; you may edit nothing without")
    assert errors(directory="../")[0].startswith("directory: ../ is not a directory in the worktree")
    assert errors(ready_url="https://example.com/")[0].startswith("ready_url: must be local")


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
    def missing(*_a, **_k):
        raise visual.BrowserMissingError(MISSING)

    flow.mp.setattr(visual, "CAPTURE", missing)
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    question = next(q for q in after.questions if q.id == after.outcome.question)
    assert after.outcome.exit == Exit.ASK
    assert "uv run playwright install chromium" in question.text
    assert (after.visual, flow.review.calls) == (None, [])


def test_a_capture_error_is_never_a_pass(flow):
    def crash(*_a, **_k):
        raise RuntimeError(CRASHED)

    flow.mp.setattr(visual, "CAPTURE", crash)
    runner._visual(flow.store, Lock("c1"), checking(flow.store, flow.clone), flow.clone)  # noqa: SLF001
    after = flow.store.read("c1")
    assert after.outcome.exit == Exit.RETRY
    assert CRASHED in after.outcome.reason
    assert (after.visual, flow.review.calls) == (None, [])


def test_a_failed_shot_skips_the_reviewer_and_becomes_a_repair_task(flow):
    flow.mp.setattr(visual, "CAPTURE", lambda *_a, **_k: [visual.Shot("home", 1280, error="/ answered 500")])
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
            policy=Policy(Path(), write=False),
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
