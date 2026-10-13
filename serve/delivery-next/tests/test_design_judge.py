"""Visual review slice 5: the design judge's role and its two-phase result tools (TD-78)."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next import design_tools, preload, roles, sdk_adapter, sessions, tools, window_files
from owlbear_delivery_next.config import Layer, resolve
from owlbear_delivery_next.models import Brief, Change, Exit, Step, StepKind, VisualState
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.results import ACCEPTED, Gate
from owlbear_delivery_next.session_result import Run, to_result
from owlbear_delivery_next.steps import judges
from owlbear_delivery_next.store import Lock, Store
from owlbear_delivery_next.visual_records import DetectorFinding, DetectorScan

IMAGES = ("home-1280-A.png", "home-1280-B.png", "about-1280-A.png")


def session(**fields):
    base = {
        "kind": StepKind.REVIEW,
        "worktree": Path(),
        "session_id": "s1",
        "message": "judge",
        "resume": False,
        "policy": Policy(Path(), write=False),
        "observe": lambda: tools.Worktree("h", "h", changed=IMAGES),
        "checks": (),
        "role": "designer",
        "submit": design_tools.FINAL,
        "first_look": design_tools.FIRST,
        "reveal": "The detector found: side-tab on home at 1280px (new).",
        "attachments": ({"type": "blob", "data": "eA==", "mimeType": "image/png", "displayName": IMAGES[0]},),
    }
    return sdk_adapter.Session(**(base | fields))


def look(verdict="pass", **fields):
    base = {
        "verdict": verdict,
        "preferences": [{"pair": "home-1280", "better": "equal", "why": "Same layout"}],
        "covered_paths": list(IMAGES),
    }
    return base | fields


def test_the_designer_is_its_own_role_with_its_skills_and_first_look_in_both_runtimes(tmp_path) -> None:
    chosen = roles.chosen(resolve(None, Layer()), "design-review")
    assert (chosen.model, chosen.effort) == ("claude-opus-5.5", "high")  # TD-27: Opus high as designer
    agent = sdk_adapter.agent(StepKind.REVIEW, role="designer")
    assert (agent["name"], agent["skills"]) == ("designer", ["owlbear-ui-design", "owlbear-ui-review"])
    assert tools.FIRST_LOOK in agent["tools"]
    assert tools.FIRST_LOOK not in sdk_adapter.agent(StepKind.REVIEW)["tools"]  # the reviewer has none
    assert preload.missing("designer") == []
    text = window_files.agent("designer", tmp_path / "inbox.json")(None)
    relay, _ = window_files.names(tmp_path / "inbox.json")
    assert f"{relay}/{tools.FIRST_LOOK}" in text
    assert "skills: [owlbear-ui-design, owlbear-ui-review]" in text


def test_a_first_look_comes_once_before_the_final_verdict_and_releases_the_detectors_findings() -> None:
    run, cfg = Run("s1"), session()
    gate = Gate(cfg, run, lambda **_e: None, lambda: None)
    assert design_tools.FIRST in gate.specs
    text, ok = gate.call(design_tools.FINAL, look())
    assert (ok, "first submit your own verdict with submit_first_look" in text) == (False, True)
    text, ok = gate.call(design_tools.FIRST, look("fail", findings=[finding()]))
    assert (ok, text, gate.done) == (True, f"Recorded. {cfg.reveal}", False)
    assert run.first.verdict == "fail"
    text, ok = gate.call(design_tools.FIRST, look())
    assert (ok, "already recorded" in text) == (False, True)
    text, ok = gate.call(design_tools.FINAL, look(false_positives=["side-tab"]))
    assert (ok, text, gate.done, run.payload.false_positives) == (True, ACCEPTED, True, ["side-tab"])


def finding(**fields):
    base = {"image": "home-1280-B.png", "problem": "cramped", "rule": "Layout & Space", "severity": "P2"}
    return base | fields


@pytest.mark.parametrize(
    ("args", "error"),
    [
        (look("fail"), "findings: empty"),
        (look("pass", findings=[finding(severity="P1")]), "use fail"),
        (look("unsure"), "doubt: empty"),
        (look(covered_paths=list(IMAGES[:2])), "covered_paths: missing about-1280-A.png"),
        (look("fail", findings=[finding(image="x.png")]), "x.png is not one of your images"),
        (look(preferences=[]), "preferences: name each pair once - home-1280"),
    ],
)
def test_a_design_verdict_must_match_its_findings_and_judge_every_image_and_pair(args, error) -> None:
    gate = Gate(session(), Run("s1"), lambda **_e: None, lambda: None)
    text, ok = gate.call(design_tools.FIRST, args)
    assert (ok, error in text) == (False, True), text


def test_only_the_first_look_lets_the_sdk_turn_go_on() -> None:
    st = sdk_adapter._Step(session(), SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    assert {t.name: t.is_terminal for t in st.tools()} == {
        "submit_result": True,
        tools.FIRST_LOOK: False,
        "ask_question": True,
        "report_wrong_premise": True,
        "report_missing_tool": True,
    }
    plain = sdk_adapter._Step(session(role="", first_look=None, submit=tools.VISUAL_REVIEW), asyncio.new_event_loop())  # noqa: SLF001
    assert all(t.is_terminal for t in plain.tools())


def test_images_over_the_budget_are_judged_in_batches_by_state_and_none_is_dropped(tmp_path) -> None:
    def image(state, width, side):
        (path := tmp_path / f"{state}-{width}-{side}.png").write_bytes(b"x" * 10)
        return judges.Image(f"{state}-{width}-{'A' if side == 'after' else 'B'}.png", path, side, state, width)

    images = [image(s, w, side) for s in ("home", "about", "big") for w in (1280, 1920) for side in ("after", "before")]
    by_count = judges.batches(images, shots=4, size=1000)
    assert [{i.state for i in b} for b in by_count] == [{"home"}, {"about"}, {"big"}]
    alone = judges.batches(images[:4], shots=2, size=1000)  # one state over the budget goes by width
    assert [[(i.width, i.side) for i in b] for b in alone] == [
        [(1280, "after"), (1280, "before")],
        [(1920, "after"), (1920, "before")],
    ]
    by_size = judges.batches(images, shots=24, size=50)
    assert ([len(b) for b in by_size], [i for b in by_size for i in b] == images) == ([4, 4, 4], True)
    assert judges.batches(images, shots=24, size=10_000) == [images]


def test_each_batch_is_its_own_two_phase_session_with_its_states_evidence(tmp_path) -> None:
    def image(state):
        (path := tmp_path / f"{state}.png").write_bytes(b"x" * 10)
        return judges.Image(f"{state}-1280-A.png", path, "after", state, 1280)

    found = [DetectorFinding(rule="side-tab", category="slop", advisory=False, where=".card")]
    scans = [
        DetectorScan(state="home", width=1280, kind="page", scanned=True, findings=found),
        DetectorScan(state="about", width=1280, kind="page", scanned=True),
        DetectorScan(state="sources", kind="source", scanned=True, findings=found),
    ]
    states = [VisualState(name=n, path=f"/{n}", expect="e") for n in ("home", "about")]
    c = Change(slug="c1", brief=Brief(version=1, ui=True, visual=states))
    cfgs = judges.sessions(session(), c, "h", [image("home"), image("about")], errors=((), ()), scans=scans)
    assert len(cfgs) == 1  # within the budget, one session
    split = judges.batches([image("home"), image("about")], shots=1)
    assert len(split) == 2
    reveal = judges._reveal(scans, {"about"})  # noqa: SLF001
    assert ("about at 1280px" not in reveal, "sources: side-tab" in reveal) == (True, True)
    assert "home at 1280px" not in reveal
    assert "no comparable before" in cfgs[0].message
    assert cfgs[0].observe().changed == ("home-1280-A.png", "about-1280-A.png")


NAMED = {
    "home-1280-A.png": judges.Image("home-1280-A.png", Path("a"), "before", "home", 1280),
    "home-1280-B.png": judges.Image("home-1280-B.png", Path("b"), "after", "home", 1280),
    "new-1280-A.png": judges.Image("new-1280-A.png", Path("n"), "after", "new", 1280),
}


def judged(verdict="pass", findings=(), better="equal"):
    names = list(NAMED)
    return design_tools.DesignLook(
        verdict=verdict,
        findings=list(findings),
        preferences=[{"pair": "home-1280", "better": better, "why": "hierarchy"}],
        covered_paths=names,
    )


def problem(image, severity="P1", rule="Contrast"):
    return {"image": image, "problem": "hard to read", "rule": rule, "severity": severity}


@pytest.mark.parametrize(
    ("look", "verdict", "why"),
    [
        (judged("pass", better="A"), "fail", "after is worse than before, whatever the judge said"),
        (judged("fail", [problem("home-1280-A.png")]), "pass", "the serious problem is only in before"),
        (judged("fail", [problem("home-1280-A.png"), problem("home-1280-B.png")]), "pass", "both had it: existing"),
        (judged("fail", [problem("home-1280-B.png")]), "fail", "after has a serious problem before did not"),
        (judged("pass", [problem("home-1280-B.png", "P3", "owner-1")]), "fail", "after misses an owner's criterion"),
        (judged("fail", [problem("new-1280-A.png")]), "fail", "a new state's serious problem counts"),
        (judged("unsure", [problem("home-1280-B.png", "P3")]), "unsure", "the judge's doubt stands"),
    ],
)
def test_delivery_decides_what_the_change_did_from_the_blind_evidence_mapped_back(look, verdict, why) -> None:
    assert judges._derived(look, NAMED) == verdict, why  # noqa: SLF001


@pytest.mark.parametrize("verdict", ["pass", "fail", "unsure"])
def test_a_design_verdict_is_logged_as_a_finished_judge_not_a_retry(verdict) -> None:
    findings = [] if verdict == "pass" else [problem("home-1280-B.png")]
    final = design_tools.DesignResult(**judged(verdict, findings).model_dump())
    done = Run("d", ending="result", payload=final, termination=Termination(confirmed=True))
    r = to_result(done, StepKind.REVIEW, datetime.now(UTC))
    assert (r.exit, r.reason.split(":")[0]) == (Exit.DONE, f"design {verdict}")  # the round's matrix decides


def test_findings_keep_their_image_and_delivery_marks_what_the_change_introduced() -> None:
    look = judged("fail", [problem("home-1280-A.png"), problem("home-1280-B.png"), problem("new-1280-A.png", rule="x")])
    final = design_tools.DesignResult(**look.model_dump())
    done = Run("d", ending="result", payload=final, first=look, termination=Termination(confirmed=True))
    record = judges.design([done], list(NAMED.values()), roles.DEFAULTS["designer"], datetime.now(UTC))
    assert [(f.image, f.introduced) for f in record.findings] == [
        ("home-1280-A.png", False),
        ("home-1280-B.png", False),  # before had it too
        ("new-1280-A.png", None),  # no before to tell
    ]
    assert (record.verdict, record.reason) == ("fail", "")  # the new state's P1


def test_a_judge_left_running_outranks_another_judges_unread_usage(tmp_path, monkeypatch) -> None:
    store = Store(tmp_path / "store")
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=StepKind.CHECK))
    store.write(Lock("c1"), change)
    unread = Run("u", ending="result", usage_unread="unread", termination=Termination(confirmed=True))
    left = Run("l", ending="error", termination=Termination(confirmed=False, survivors=(7,)))

    async def fake(cfg):
        return unread if cfg.role != "designer" else left

    monkeypatch.setattr(sessions.sdk_adapter, "run", fake)
    ran = sessions.judges(
        store, Lock("c1"), change, [("visual-review", session(role="")), ("design-review", session())]
    )
    assert [r.exit for r, _ in ran][1] == Exit.STOP  # returned, so the stop is applied
    monkeypatch.setattr(sessions.sdk_adapter, "run", lambda cfg: fake(cfg) if cfg.role != "designer" else _ok(cfg))
    with pytest.raises(sessions.UsageUnreadError):
        sessions.judges(store, Lock("c1"), change, [("visual-review", session(role="")), ("design-review", session())])


async def _ok(cfg):
    return Run(cfg.session_id, ending="error", termination=Termination(confirmed=True))


def test_a_judge_never_runs_the_judged_steps_callbacks(tmp_path, monkeypatch) -> None:
    """The plan challenge took the plan step's journal; its delivery swapped the runner's Change, losing its credits."""
    store, touched = Store(tmp_path / "store"), []
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=StepKind.PLAN))
    step = sdk_adapter.Journal(delivered=lambda: touched.append("delivered"), replaced=lambda: touched.append("new"))

    async def fake(cfg):
        cfg.journal.delivered()  # both runtimes call it once the first message is acknowledged
        usage = {"credits": 4.37, "models": {"gpt-6.1-sol": {"credits": 4.37, "tokens": 65556}}}
        return Run(cfg.session_id, ending="result", usage=usage, termination=Termination(confirmed=True))

    monkeypatch.setattr(sessions.sdk_adapter, "run", fake)
    sessions.reviewer(store, Lock("c1"), change, session(role="", journal=step), "plan-challenge")
    assert touched == []
    assert change.spend.credits == 4.37


def test_a_correctness_finding_or_doubt_names_one_of_its_screenshots() -> None:
    tree = tools.Worktree("h", "h", changed=("home-1280.png",))
    loose = tools.Finding(place="home at 1280px", problem="cut off", fix="wrap it")
    review = tools.VisualReviewResult(verdict="fix", findings=[loose], covered_paths=["home-1280.png"])
    assert any("place: home at 1280px is not a screenshot" in e for e in tools.check_review(review, tree, visual=True))
    anchored = review.model_copy(update={"findings": [loose.model_copy(update={"place": "home-1280.png"})]})
    assert tools.check_review(anchored, tree, visual=True) == []


def test_every_judge_ends_before_an_error_of_another_goes_on(tmp_path, monkeypatch) -> None:
    store, ended = Store(tmp_path / "store"), []
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=StepKind.CHECK))

    async def fake(cfg):
        if cfg.role == "designer":
            msg = "disk full"
            raise OSError(msg)
        await asyncio.sleep(0.05)
        ended.append(cfg.session_id)
        return Run(cfg.session_id, termination=Termination(confirmed=True))

    monkeypatch.setattr(sessions.sdk_adapter, "run", fake)
    with pytest.raises(OSError, match="disk full"):
        sessions.judges(store, Lock("c1"), change, [("visual-review", session(role="")), ("design-review", session())])
    assert len(ended) == 1  # the other judge was not cancelled half-way
