"""A test review's start and its TESTS step (TD-373, TD-390): shares, waves, the end, and a fixed brief and plan."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.curation_tools import TestReviewResult
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import Exit, Step, StepKind
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.loop import StepResult, apply, brief_ready
from owlbear_delivery_next.change_flow.status import Activity, status
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import api, session_slots
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import curation, curation_shares, sessions

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
    assert brief_ready(c)
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
    c = curation.start(store, repo, [".", "web"], NOW)
    ends, ran = {}, []

    async def session(cfg):
        ran.append(cfg.message.splitlines()[0])
        return ends.get(cfg.message.splitlines()[0], reviewed)(cfg)

    monkeypatch.setattr(sessions.sdk_adapter, "run", session)
    monkeypatch.setattr(sessions, "GRANT", 1)
    return SimpleNamespace(store=store, slug=c.slug, ends=ends, ran=ran, repo=repo)


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


def test_a_test_review_never_shapes_or_plans_and_its_status_counts_shares(review):
    c = review.store.read(review.slug)
    line = status(c, Activity(host_up=True, runner_alive=True), NOW).line
    assert "reviewing tests: Review the tests · 0 of 2 shares done" in line
    c = c.model_copy(update={"step": Step(kind=StepKind.BUILD, task="t1")})
    back = StepResult(exit=Exit.BACK, back_to=StepKind.PLAN, cause="scope:build:premise", reason="the plan is wrong")
    c = apply(c, back, NOW)
    assert (c.step.kind, c.outcome.exit, c.stop.reason) == (
        StepKind.BUILD, Exit.STOP, "a test review keeps its fixed brief and plan: the plan is wrong"
    )  # fmt: skip
    done = c.model_copy(update={"finished_at": NOW, "tests": c.tests.model_copy(update={"unchanged": True})})
    assert status(done, Activity(host_up=True), NOW).line == "Done · no test changed"


def test_an_unchanged_curation_goes_straight_to_cleanup_and_a_changed_one_to_its_review(review):
    c = review.store.read(review.slug)
    c = c.model_copy(update={"step": Step(kind=StepKind.BUILD, task="t1")})
    changed = apply(c, StepResult(exit=Exit.DONE, reason="applied 3"), NOW)
    assert (changed.step.kind, changed.step.task) == (StepKind.REVIEW, "t1")
    c.tests.unchanged = True
    assert apply(c, StepResult(exit=Exit.DONE, reason="nothing held"), NOW).step.kind == StepKind.CLEANUP


def test_shares_wait_for_the_project_s_slots_like_any_step(review):
    c = review.store.read(review.slug)
    host = SimpleNamespace(
        wants={c.slug: session_slots.wanted(c, c.step)}, slots=Slots(lambda: 4), asked=set(),
        record=SimpleNamespace(project="p"), store=review.store,
    )  # fmt: skip
    assert session_slots.reserve(host, c.slug) == 2  # the project's limit: two shares at once
