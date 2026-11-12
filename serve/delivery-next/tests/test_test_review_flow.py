"""A test review's start and its TESTS step (TD-373, TD-390): shares, waves, the end, and a fixed brief and plan."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import check_hint, curation_tools, tools
from owlbear_delivery_next.change_contracts.curation_records import TestReview
from owlbear_delivery_next.change_contracts.curation_tools import TEST_CURATION, TestCurationResult, TestReviewResult
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    Exit,
    Names,
    Plan,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import loop, stuck, worktree
from owlbear_delivery_next.change_flow.brief_rounds import ready
from owlbear_delivery_next.change_flow.curation_flow import CURATE
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.change_flow.status import Activity, status
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import api, session_slots
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import identities
from owlbear_delivery_next.state_store.briefs import new_slug
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import (
    curation,
    curation_build,
    curation_shares,
    repair_copy,
    sessions,
    step_repair,
)

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)
AUTH = {"authorization": "Bearer tok"}


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@t"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A project with two packages of tests, a fixture's data file, and code; ``main`` holds them."""
    work = tmp_path / "work"
    files = {
        "pyproject.toml": "", "src/app.py": "x = 1\n", "tests/test_a.py": "a\n" * 3, "tests/data.json": "{}\n",
        "tests/helpers.py": "h\n", "web/package.json": "{}", "web/src/b.test.ts": "b\n" * 2, "web/src/b.ts": "b\n",
    }  # fmt: skip
    for name, text in files.items():
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text(text)
    git(tmp_path, "init", "-q", "-b", "main", str(work))
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    return work


def test_a_project_s_tests_are_found_by_package_and_split_into_whole_file_shares(repo, monkeypatch):
    found = curation_shares.packages(repo, git(repo, "rev-parse", "HEAD"))
    assert [(p.path, p.files) for p in found] == [(".", {"tests/helpers.py": 1, "tests/test_a.py": 3}),
                                                  ("web", {"web/src/b.test.ts": 2})]  # fmt: skip
    monkeypatch.setattr(curation_shares, "SHARE", 3)
    shares = curation_shares.split(found)
    assert [(s.paths, s.lines) for s in shares] == [
        (["tests/helpers.py"], 1), (["tests/test_a.py"], 3), (["web/src/b.test.ts"], 2)
    ]  # fmt: skip
    assert curation_shares.split(found) == shares  # deterministic


def test_the_start_approves_the_fixed_brief_and_plan_and_pins_the_commit(repo):
    store = Store.open(repo)
    with pytest.raises(curation.StartError, match="at least one package"):
        curation.start(store, repo, ["nowhere"], NOW)
    c = curation.start(store, repo, ["web"], NOW)
    assert (c.step.kind, c.tests.packages, c.brief.scope, [t.id for t in c.plan.tasks]) == (
        StepKind.TESTS, ["web"], ["web"], ["t1"]
    )  # fmt: skip
    assert ready(c)
    assert (c.brief.approved_at, len(c.brief.criteria)) == (NOW, 4)
    assert c.tests.commit == git(repo, "rev-parse", "main") == git(c.names.worktree, "rev-parse", "HEAD")
    assert [s.paths for s in c.tests.shares] == [["web/src/b.test.ts"]]
    assert session_slots.wanted(c, c.step) == session_slots.ALL  # its shares run together
    with pytest.raises(curation.StartError, match="has not finished"):
        curation.start(store, repo, ["."], NOW)


def test_the_maintenance_routes_offer_the_packages_and_start_once(repo):
    store = Store.open(repo)
    host = Host(store, repo)
    client = TestClient(api.create_app(store, "tok", host), base_url="http://127.0.0.1", headers=AUTH)
    offer = client.get("/api/next/maintenance/test-review").json()
    assert ([p["path"] for p in offer["packages"]], offer["open"], offer["sessions"]) == ([".", "web"], None, 2)
    assert offer["roles"]["test-curator"] == {"model": "claude-opus-5.5", "effort": "high", "context": "long"}
    assert client.post("/api/next/maintenance/test-review", json={"packages": []}).status_code == 422
    started = client.post("/api/next/maintenance/test-review", json={"packages": [".", "web"]}).json()
    assert client.get("/api/next/maintenance/test-review").json()["open"]["handle"] == started["handle"]
    assert client.post("/api/next/maintenance/test-review", json={"packages": ["web"]}).status_code == 409


def reviewed(cfg) -> Run:
    paths = [line[2:] for line in cfg.message.splitlines() if line.startswith("- ")][:1]
    payload = TestReviewResult(verdicts=[], kept=1, covered_paths=paths)
    return Run(cfg.session_id, "result", payload=payload, termination=Termination(confirmed=True))


@pytest.fixture
def review(repo, monkeypatch):
    """A started review of both packages, its sessions faked; ``ran`` holds each wave's shares."""
    store = Store.open(repo)
    store.write_profile(profile.confirm(Profile(), "check:.", "uv run pytest", NOW))
    c = curation.start(store, repo, [".", "web"], NOW)
    ends, ran = {}, []

    async def session(cfg):
        ran.append(cfg.message.splitlines()[0])
        return ends.get(cfg.message.splitlines()[0], reviewed)(cfg)

    monkeypatch.setattr(sessions.sdk_adapter, "run", session)
    monkeypatch.setattr(sessions, "GRANT", 1)
    return SimpleNamespace(store=store, slug=c.slug, ends=ends, ran=ran, repo=repo)


@pytest.fixture
def started(tmp_path: Path) -> SimpleNamespace:
    """The Change ``review``'s start writes, built as the start builds it but without Git: its commit is a fixed one."""
    store = Store(tmp_path / "store")
    number, slug = identities.reserve(store, lambda n, taken: new_slug(f"{curation.TITLE} {n}", taken))
    found = [
        curation_shares.Package(".", {"tests/helpers.py": 1, "tests/test_a.py": 3}),
        curation_shares.Package("web", {"web/src/b.test.ts": 2}),
    ]
    scope = [p.path for p in found]
    criteria = [Criterion(id=f"AC-{i}", text=t) for i, t in enumerate(curation.CRITERIA, 1)]
    brief = Brief(
        version=1, title=curation.TITLE, outcome=curation.OUTCOME, scope=scope, criteria=criteria, challenged=1
    )
    brief.approved_version, brief.approved_at = 1, NOW
    brief.approved = [brief.model_copy(deep=True)]
    branch = f"owlbear/{slug}"
    c = Change(
        slug=slug,
        handle=f"c{number}",
        profile_version=(store.read_profile() or Profile()).version,
        brief=brief,
        plan=Plan(tasks=[Task(id=CURATE, title="Curate the tests", scope=scope, detail=curation.RULES)]),
        step=Step(kind=StepKind.TESTS),
        names=Names(branch=branch, target="main", worktree=str(tmp_path / slug)),
        tests=TestReview(commit="c" * 40, packages=scope, shares=curation_shares.split(found)),
    )
    with store.lock(slug) as lock:
        identities.publish_reserved(store, lock, c)
    return SimpleNamespace(store=store, slug=slug, repo=tmp_path)


def step(r) -> None:
    c = r.store.read(r.slug)
    with r.store.lock(r.slug) as lock:
        runner._step(r.store, lock, c, c.step, r.repo)  # noqa: SLF001


def test_every_share_s_reviewer_runs_in_waves_and_the_curator_builds_next(review):
    step(review)
    c = review.store.read(review.slug)
    assert review.ran == ["# Test review: share 1 of 2", "# Test review: share 2 of 2"]  # one at a time: grant 1
    assert [s.ended for s in c.tests.shares] == ["reviewed", "reviewed"]
    assert (c.step.kind, c.step.task, c.tests.shares[0].review.kept) == (StepKind.BUILD, "t1", 1)


def test_a_failed_share_retries_alone_and_the_owner_may_go_on_without_it(review):
    second = "# Test review: share 2 of 2"
    review.ends[second] = lambda cfg: Run(cfg.session_id, "premise", termination=Termination(confirmed=True))
    step(review)
    c = review.store.read(review.slug)
    assert ([s.ended for s in c.tests.shares], c.step.kind, c.outcome.exit) == (["reviewed", None], StepKind.TESTS,
                                                                                 Exit.RETRY)  # fmt: skip
    review.ran.clear()
    for _ in range(3):  # its budget runs out: only it reruns, and it never goes to the planner
        step(review)
    c = review.store.read(review.slug)
    assert (set(review.ran), c.step.kind) == ({second}, StepKind.TESTS)
    q = loop.open_question(c)
    assert [o.id for o in q.options] == ["retry", "without", "pause", "abandon"]
    review.store.put_inbox(review.slug, AnswerItem(at=NOW, question=q.id, option="without"))
    with review.store.lock(review.slug) as lock:
        c, _ = review.store.fold(lock, review.slug, NOW, None)
    assert ([s.ended for s in c.tests.shares], c.step.kind) == (["reviewed", "not-reviewed"], StepKind.BUILD)


def test_a_wave_left_running_stops_the_review_and_no_further_share_starts(review):
    first = "# Test review: share 1 of 2"
    review.ends[first] = lambda cfg: Run(cfg.session_id, "error", termination=Termination(confirmed=False))
    step(review)
    c = review.store.read(review.slug)
    assert (review.ran, c.outcome.exit, c.step.kind) == ([first], Exit.STOP, StepKind.TESTS)


def test_a_moved_worktree_stops_the_review_before_any_share(review):
    c = review.store.read(review.slug)
    (review.repo.parent / "x").write_text("x")
    git(c.names.worktree, "commit", "-q", "--allow-empty", "-m", "moved")
    step(review)
    c = review.store.read(review.slug)
    assert (review.ran, c.outcome.exit, "not at the commit it reviews" in c.stop.reason) == ([], Exit.STOP, True)


def test_a_test_review_never_shapes_or_plans_and_its_status_counts_shares_and_the_owner_reruns_its_stopped_step(
    started, whole_error
):
    c = started.store.read(started.slug)
    line = status(c, Activity(host_up=True, runner_alive=True), NOW).line
    assert "starting: Review the tests · 0 of 2 shares done" in line  # no share has started yet (#718)
    c = c.model_copy(update={"step": Step(kind=StepKind.BUILD, task="t1")})
    back = StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause="scope:build:premise", reason="the plan is wrong")
    c = apply(c, back, NOW)
    assert (c.step.kind, c.outcome.exit, c.stop.reason) == (
        StepKind.BUILD, Exit.STOP, "a test review keeps its fixed brief and plan: the plan is wrong"
    )  # fmt: skip
    assert (c.stop.action, c.stop.resume) == (
        'Abandon the test review, or press "Done: run the step again" on the Changes page to run its step again',
        'You pressed "Done: run the step again"',
    )  # not Resume, which clears only a pause (#754)
    again = started.store.read(started.slug).model_copy(update={"step": Step(kind=StepKind.BUILD, task="t1")})
    sent = StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause="scope:build:premise", reason="the plan is wrong")
    for _ in range(4):  # REPLAN_LIMIT and RETRY_LIMIT never reached: nothing is counted
        again = apply(again.model_copy(update={"outcome": None, "stop": None}), sent, NOW)
    assert (again.step.kind, again.outcome.exit, again.budgets.replans, again.budgets.causes) == (
        StepKind.BUILD,
        Exit.STOP,
        0,
        {},
    )
    again, step_ = loop.schedule(again.model_copy(update={"outcome": None, "stop": None}),
                                 [IntentItem(at=NOW, intent="change", text="also docs")], NOW)  # fmt: skip
    assert (again.step.kind, again.outcome.exit, step_) == (StepKind.BUILD, Exit.STOP, None)  # a change request too
    whole = started.store.read(started.slug).model_copy(update={"step": Step(kind=StepKind.BUILD, task="t1")})
    long = StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause="scope:build:premise", reason=whole_error)
    whole = apply(whole, long, NOW)
    expected = f"a test review keeps its fixed brief and plan: {whole_error}"
    assert (whole.stop.reason, whole.outcome.reason) == (expected, expected)  # the whole reason, never cut
    done = c.model_copy(update={"finished_at": NOW, "tests": c.tests.model_copy(update={"unchanged": True})})
    assert status(done, Activity(host_up=True), NOW).line == "Done · no test changed"
    with started.store.lock(started.slug) as lock:
        started.store.write(lock, c)
    client = TestClient(api.create_app(started.store, "tok", Host(started.store, started.repo)),
                        base_url="http://127.0.0.1", headers=AUTH)  # fmt: skip
    shown = c.stop.model_dump(mode="json", include={"action", "at"})
    assert client.post(f"/api/next/changes/{started.slug}/recovery", json=shown).status_code == 200
    with started.store.lock(started.slug) as lock:
        after, _ = started.store.fold(lock, started.slug, NOW, None)
    assert (after.stop, loop.next_step(after, NOW), after.brief, after.plan) == (None, c.step, c.brief, c.plan)


def test_an_unchanged_curation_goes_straight_to_cleanup_and_a_changed_one_to_its_review(started):
    c = started.store.read(started.slug)
    c = c.model_copy(update={"step": Step(kind=StepKind.BUILD, task="t1")})
    changed = apply(c, StepResult(exit=Exit.DONE, reason="applied 3"), NOW)
    assert (changed.step.kind, changed.step.task) == (StepKind.REVIEW, "t1")
    c.tests.unchanged = True
    assert apply(c, StepResult(exit=Exit.DONE, reason="nothing held"), NOW).step.kind == StepKind.CLEANUP


def test_shares_wait_for_the_project_s_slots_like_any_step(started):
    c = started.store.read(started.slug)
    host = SimpleNamespace(
        wants={c.slug: session_slots.wanted(c, c.step)}, slots=Slots(lambda: 4), asked=set(),
        record=SimpleNamespace(project="p"), store=started.store,
    )  # fmt: skip
    assert session_slots.reserve(host, c.slug) == 2  # the project's limit: two shares at once


MEASURE = {"command": "uv run pytest -q", "commit": "", "tests": 4, "seconds": 2.0}


def verdict(test: str, action: str = "retire") -> dict:
    return {"test": test, "action": action, "behaviour": "b", "bug": "x", "caught_by": "tests/test_a.py::k"}


@pytest.fixture
def curating(review, monkeypatch):
    """The review's shares ended with one retire and one rewrite-lower verdict; its curator's session is faked."""
    review.ends["# Test review: share 1 of 2"] = lambda cfg: Run(
        cfg.session_id, "result", termination=Termination(confirmed=True),
        payload=TestReviewResult(verdicts=[verdict("tests/test_a.py::old"), verdict("tests/test_a.py::slow",
                                 "rewrite-lower")], kept=1, covered_paths=["tests/test_a.py"]),
    )  # fmt: skip
    step(review)
    seen = []

    async def curator(cfg):
        seen.append(cfg)
        return review.curate(cfg)

    monkeypatch.setattr(sessions.sdk_adapter, "run", curator)
    review.seen = seen
    return review


def curated(applied: bool):  # noqa: FBT001 - one switch per test
    def done(cfg) -> Run:
        wt = cfg.worktree
        head = git(wt, "rev-parse", "HEAD")
        after = None
        if applied:
            (wt / "tests" / "test_a.py").write_text("a\n")
            git(wt, "commit", "-qam", "test review: retire old")
            head = git(wt, "rev-parse", "HEAD")
            after = MEASURE | {"commit": head, "tests": 3}
        payload = TestCurationResult.model_validate({
            "applied": [{"test": "tests/test_a.py::old", "action": "retire", "change": "removed"}] if applied else [],
            "refused": [] if applied else [{"test": "tests/test_a.py::old", "reason": "only it covers empty names"}],
            "before": MEASURE | {"commit": head}, "after": after, "summary": "s",
        })  # fmt: skip
        return Run(cfg.session_id, "result", payload=payload, head=head, termination=Termination(confirmed=True))

    return done


def test_the_curator_builds_with_its_role_and_every_retire_or_merge_verdict(curating, monkeypatch, user_on):
    prof = profile.confirm(Profile(), "check:.", "uv run pytest", NOW)
    prof = profile.confirm(prof, "check:api", "npm test", NOW)
    prof = profile.confirm(prof, "check:web", "npm test", NOW)
    curating.store.write_profile(prof)
    curating.curate = curated(applied=True)
    base = config.BASE  # the builder's own session values unset: the curator's build never needs them
    builder = base.agents["builder"].model_copy(update={"model": None, "effort": None, "minutes": None})
    monkeypatch.setattr(config, "BASE", base.model_copy(update={"agents": base.agents | {"builder": builder}}))
    step(curating)
    [cfg] = curating.seen
    c = curating.store.read(curating.slug)
    assert (cfg.role, cfg.model, cfg.effort, cfg.context, cfg.submit) == (
        "test-curator", "claude-opus-5.5", "high", "long", TEST_CURATION
    )  # fmt: skip
    assert cfg.user == user_on
    assert cfg.checks == (
        check_hint.qualified(".", "uv run pytest"),
        check_hint.qualified("web", "npm test"),
    )
    assert cfg.checks[0] in cfg.message
    repair = c.model_copy(update={"step": Step(kind=StepKind.BUILD, task=CURATE)}, deep=True)
    stuck.start(repair, "project-env:build:measurement", "the suite measurement cannot finish", NOW)
    witness = step_repair._witness  # noqa: SLF001
    assert witness(repair, prof, cfg.worktree) == cfg.checks
    partial = profile.confirm(Profile(), "check:web", "npm test", NOW)
    with pytest.raises(ValueError, match="lack confirmed checks"):
        witness(repair, partial, cfg.worktree)
    follow = repair.model_copy(deep=True)
    follow.plan.tasks.append(Task(id="r1", title="Fix the review", scope=["."]))
    follow.step.task = follow.repairs.current.task = "r1"
    with monkeypatch.context() as ordinary:
        ordinary.setattr(worktree, "owns_changed_runner", lambda *_: False)
        confirmed = profile.confirm(Profile(), "check:.", "uv run pytest", NOW)
        assert witness(follow, confirmed, cfg.worktree) == (check_hint.qualified(".", "uv run pytest"),)
    assert "tests/test_a.py::old: retire" in cfg.message
    assert "share 2 (web/src/b.test.ts" not in cfg.message  # every share ended
    assert "::slow" not in cfg.message  # rewrite-lower waits (TD-312)
    assert (c.tests.report.applied[0].test, c.tests.unchanged, c.step.kind) == (
        "tests/test_a.py::old", False, StepKind.REVIEW
    )  # fmt: skip
    text = curation_build.body(c)
    assert "Before: `uv run pytest -q`" in text
    assert "- tests/test_a.py::old: retire, removed" in text
    assert "Rewrite lower, for later (1):\n- tests/test_a.py::slow: b" in text


def test_curator_measurements_refuse_a_mixed_changed_runner(curating, monkeypatch):
    c = curating.store.read(curating.slug)
    c.step = Step(kind=StepKind.BUILD, task=CURATE)
    prof = profile.confirm(Profile(), "check:.", "uv run test --changed", NOW)
    prof = profile.confirm(prof, "check:api", "uv run pytest", NOW)
    prof = profile.confirm(prof, "check:web", "npm test", NOW)
    owns_runner = worktree.owns_changed_runner
    monkeypatch.setattr(worktree, "owns_changed_runner", lambda *_: True)
    stuck.start(c, "project-env:build:measurement", "the suite measurement cannot finish", NOW)
    witness = step_repair._witness  # noqa: SLF001
    with pytest.raises(ValueError, match=r"cannot measure selected suites: \."):
        witness(c, prof, curating.repo)
    python = c.model_copy(deep=True)
    python.tests.packages = ["."]
    python.tests.shares = python.tests.shares[:1]
    assert witness(python, prof, curating.repo) == (
        check_hint.task_command(
            check_hint.qualified(".", "uv run test --changed -m tests"), c.tests.commit, c.tests.commit
        ),
    )
    mixed = python.model_copy(deep=True)
    mixed.tests.shares[0].paths.append("tests/client.test.ts")
    with pytest.raises(ValueError, match=r"cannot measure selected suites: \."):
        witness(mixed, prof, curating.repo)
    mixed.tests.shares[0].paths[-1] = "tests/client_test.py"
    with pytest.raises(ValueError, match=r"cannot measure selected suites: \."):
        witness(mixed, prof, curating.repo)
    owned = c.model_copy(deep=True)
    owned.tests.packages = ["api", "web"]
    owned.tests.shares[0].paths = ["api/tests/test_a.py"]
    assert witness(owned, prof, curating.repo) == (
        check_hint.qualified("api", "uv run pytest"),
        check_hint.qualified("web", "npm test"),
    )
    manifest = curating.repo / "serve/tools/pyproject.toml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("[project\n")
    monkeypatch.setattr(worktree, "owns_changed_runner", owns_runner)
    with pytest.raises(repair_copy.RepairError, match="cannot resolve the curator's unchanged measurement"):
        witness(python, prof, curating.repo)


def test_a_curation_that_applies_nothing_ends_without_review_or_pr(curating):
    curating.curate = curated(applied=False)
    step(curating)
    c = curating.store.read(curating.slug)
    assert (c.tests.unchanged, c.step.kind, c.tests.report.refused[0].reason) == (
        True, StepKind.CLEANUP, "only it covers empty names"
    )  # fmt: skip


def test_a_curation_result_must_match_what_its_commits_show():
    payload = TestCurationResult.model_validate({"before": MEASURE | {"commit": "a" * 40}, "summary": "s"})
    assert curation_tools.check(payload, tools.Worktree("b" * 40, "a" * 40, changed=("tests/test_a.py",))) == [
        "applied: your commits change files; list each verdict you applied, or undo them"
    ]
    applied = TestCurationResult.model_validate({
        "applied": [{"test": "t", "action": "retire", "change": "c"}], "before": MEASURE | {"commit": "a" * 40},
        "after": MEASURE | {"commit": "c" * 12}, "summary": "s",
    })  # fmt: skip
    tree = tools.Worktree("b" * 40, "a" * 40, dirty=("x.txt",), changed=("src/app.py",))
    assert curation_tools.check(applied, tree) == [
        "changes: uncommitted files (x.txt); commit or undo them",
        "changes: src/app.py is not a test; edit only tests",
        f"after.commit: measure on your last commit, {'b' * 12}",
    ]
    assert curation_tools.check(applied, tools.Worktree("c" * 40, "a" * 40, changed=("tests/data.json",))) == []
    broke = applied.model_copy(update={"after": applied.after.model_copy(update={"failures": ["t.py::new"]})})
    assert curation_tools.check(broke, tools.Worktree("c" * 40, "a" * 40)) == [
        "after.failures: t.py::new passed before; restore what breaks them"
    ]
    elsewhere = applied.model_copy(update={"before": applied.before.model_copy(update={"commit": "d" * 40})})
    assert curation_tools.check(elsewhere, tools.Worktree("c" * 40, "a" * 40)) == [
        f"before.commit: measure on the commit you started from, {'a' * 12}"
    ]


def test_a_round_gated_on_one_share_keeps_the_others_reviews(review, monkeypatch):
    first = "# Test review: share 1 of 2"
    review.ends[first] = lambda cfg: Run(
        cfg.session_id, "error", usage_unread="model unknown", termination=Termination(confirmed=True)
    )
    monkeypatch.setattr(sessions, "GRANT", 2)
    step(review)
    c = review.store.read(review.slug)
    assert [s.ended for s in c.tests.shares] == [None, "reviewed"]  # the gated share reruns; the other stays done
    assert loop.usage_gated(c)


def test_a_held_review_s_usage_is_logged_when_another_share_gates_the_round(review, monkeypatch):
    unread, done = "model unknown", Termination(confirmed=True)
    review.ends["# Test review: share 1 of 2"] = lambda cfg: Run(cfg.session_id, "error", usage_unread=unread,
                                                                 termination=done)  # fmt: skip
    review.ends["# Test review: share 2 of 2"] = lambda cfg: Run(
        cfg.session_id, "result", usage_unread=unread, termination=done,
        payload=TestReviewResult(verdicts=[], kept=1, covered_paths=["web/src/b.test.ts"]),
    )  # fmt: skip
    monkeypatch.setattr(sessions, "GRANT", 2)
    step(review)
    c = review.store.read(review.slug)
    held = [e for e in review.store.events(review.slug) if e.get("exit") == "held"]
    assert (len(held), [s.ended for s in c.tests.shares], loop.usage_gated(c)) == (1, [None, None], True)


def test_only_the_curation_task_is_the_curator_s_and_its_pr_text_fits(curating):
    c = curating.store.read(curating.slug)
    c.plan.tasks.append(Task(id="r1", title="fix the review's finding", scope=["."], origin="review", fixes="t1"))
    c.step = Step(kind=StepKind.BUILD, task="r1")
    with curating.store.lock(curating.slug) as lock:
        curating.store.write(lock, c)
    curating.curate = lambda cfg: Run(cfg.session_id, "error", termination=Termination(confirmed=True))
    step(curating)
    [cfg] = curating.seen
    assert (cfg.role, cfg.submit) == ("", tools.SUBMIT)  # a repair is an ordinary build; the report stays t1's
    many = [{"test": f"tests/test_{i}.py::" + "x" * 280, "action": "retire", "change": "y" * 480} for i in range(100)]
    head = "a" * 40
    c.tests.report = TestCurationResult.model_validate({
        "applied": many, "before": MEASURE | {"commit": head}, "after": MEASURE | {"commit": head}, "summary": "s"
    })  # fmt: skip
    text = curation_build.body(c)
    assert len(text) <= curation_build.BODY
    assert text.endswith("- \u2026 the rest is in the Change's record")
