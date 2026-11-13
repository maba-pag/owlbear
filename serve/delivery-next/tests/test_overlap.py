import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    ErrorKind,
    Exit,
    Overlap,
    Plan,
    Step,
    StepKind,
    Stop,
    Task,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import FINAL, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import loop, round_flow
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.change_flow.status import Activity, card
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import overlap, plan_round

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
K = StepKind
C1 = Lock("c1")  # the integrating Change's writer lock


def git(cwd, *args, check=True):
    done = subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


def plan(*scope: str) -> Plan:
    return Plan(tasks=[Task(id="t1", title="one", scope=list(scope))])


def integrating(**fields) -> Change:
    brief = Brief(title="Speed", outcome="pages load in 1 s")
    return Change(**{"slug": "c1", "brief": brief, "plan": plan("src"), "step": Step(kind=K.INTEGRATE)} | fields)


def building(origin: str = "integration") -> Change:
    t1 = Task(id="t1", title="one", scope=["src"], done=True)
    t2 = Task(id="t2", title="two", scope=["src"], origin=origin)
    return integrating(plan=Plan(tasks=[t1, t2]), step=Step(kind=K.BUILD, task="t2"))


def shared_store(tmp_path, scope="src/app.ts") -> Store:
    store = Store(tmp_path / "store")
    with store.lock("c3") as lock:
        store.write(lock, Change(slug="c3", handle="c3", brief=Brief(outcome="cache pages"), plan=plan(scope)))
    return store


def replace_plan(c, store, path, monkeypatch):
    """Adopt a real planner result without launching its SDK challenge."""
    monkeypatch.setattr(plan_round.plan_rounds, "revised", lambda *_: "accepted")
    events: list[dict[str, object]] = []  # the challenge's step events, logged once its settlement is written
    with store.lock(c.slug) as lock:
        result = plan_round.planned(
            store, lock, c, path, None, StepResult(exit=Exit.DONE, plan=plan("src")), Profile(), {}, events
        )
        c = loop.apply(c, result, NOW)
        store.write(lock, c)
    assert events == []  # accepted unchallenged: no paid challenge ran
    c.plan.tasks[0].done = True
    c.plan.tasks.append(Task(id="t2", title="new integration", scope=["src"], origin="integration"))
    c.step = Step(kind=K.BUILD, task="t2")
    with store.lock(c.slug) as lock:
        store.write(lock, c)
    return store.read(c.slug)


@pytest.fixture
def merged_cleanly(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "src").mkdir()
    lines = [f"line {i}\n" for i in range(20)]
    (repo / "src/app.ts").write_text("".join(lines))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    git(repo, "switch", "-qc", "change")
    ours = ["ours\n", *lines[1:]]
    (repo / "src/app.ts").write_text("".join(ours))
    git(repo, "commit", "-qam", "mine")
    start = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-q", "main")
    (repo / "src/app.ts").write_text("".join([*lines[:-1], "theirs\n"]))
    git(repo, "commit", "-qam", "theirs")
    git(repo, "switch", "-q", "change")
    git(repo, "merge", "-q", "--no-edit", "main")
    return repo, start


def conflicting_repository(tmp_path, filename="src/app.ts"):
    """A Change branch whose update with main conflicts on src/app.ts (and also changes a lockfile)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "src").mkdir()
    for text, msg in [("a", "base")]:
        (repo / filename).write_text(text)
        (repo / "uv.lock").write_text(text)
        git(repo, "add", ".")
        git(repo, "commit", "-qm", msg)
    git(repo, "switch", "-qc", "change")
    (repo / filename).write_text("mine")
    (repo / "uv.lock").write_text("mine")
    git(repo, "commit", "-qam", "mine")
    git(repo, "switch", "-q", "main")
    (repo / filename).write_text("theirs")
    (repo / "uv.lock").write_text("theirs")
    git(repo, "commit", "-qam", "theirs")
    git(repo, "switch", "-q", "change")
    start = git(repo, "rev-parse", "HEAD")
    git(repo, "merge", "-q", "main", check=False)
    return repo, start


@pytest.fixture
def conflicted(tmp_path):
    return conflicting_repository(tmp_path)


def test_overlapping_plans_are_recorded_as_information_on_the_card():
    others = {"c2": ["packages/app"], "c3": ["packages/web"], "c4": ["."]}
    assert overlap.found(plan("packages/app/src"), others) == [
        Overlap(other="c2", paths=["packages/app/src"]),
        Overlap(other="c4", paths=["packages/app/src"]),
    ]
    c = loop.apply(integrating(step=Step(kind=K.PLAN), plan=None), StepResult(exit=Exit.DONE, plan=plan("x")), NOW)
    assert (c.step.kind, loop.open_question(c)) == (K.BUILD, None)  # planning continues
    c.overlaps = [Overlap(other="c3", paths=["src/app.ts"])]
    alive = Activity(host_up=True, runner_alive=True, last_event_at=NOW)
    assert card(c, alive, [], NOW)["overlaps"] == ["overlaps with c3: src/app.ts"]


@pytest.mark.parametrize(
    "shared", [["README.md"], ["docs/guide"], ["uv.lock"], ["web/package-lock.json"], ["dist"], ["a/app.min.js"]]
)
def test_docs_lockfiles_and_generated_output_are_no_overlap(shared):
    assert overlap.found(plan(*shared), {"c2": shared}) == []


def test_linguist_generated_paths_are_no_overlap(tmp_path):
    (tmp_path / ".gitattributes").write_text("# x\napi/gen/** linguist-generated\n*.pb.go linguist-generated=true\n")
    patterns = overlap.generated(tmp_path)
    assert overlap.found(plan("api/gen/client.ts", "x/y.pb.go"), {"c2": ["api", "x"]}, patterns) == []


SHOWS, HIDES = "On a day without values, the page shows an empty chart.", "On such a day, the page hides the chart."
SIDES = [("a" * 40, "b" * 40)]


def told(this: str = SHOWS, other: str = HIDES) -> tools.MergedResult:
    return tools.MergedResult(summary="merged", checks=[], merge={"this": this, "other": other})


def answered(c: Change, asked: StepResult, option: str = "keep") -> Change:
    c = loop.apply(c, asked, NOW)
    return loop.schedule(c, [AnswerItem(at=NOW, question=loop.open_question(c).id, option=option)], NOW)[0]


def test_a_reported_difference_asks_which_behaviour_to_keep_and_no_difference_asks_nothing(conflicted, tmp_path):
    repo, start = conflicted
    (repo / "src/app.ts").write_text("both")
    (repo / "uv.lock").write_text("both")
    git(repo, "commit", "-qam", "merge main")
    store, c, done = Store(tmp_path / "store"), building(), StepResult(exit=Exit.DONE)
    c.names.target = "main"
    asked = overlap.integrated(store, C1, c, repo, start, done, told())
    q = asked.question
    assert (asked.exit, q.step, q.subject) == (Exit.ASK, K.BUILD, "product")
    assert [(o.id, o.next) for o in q.options] == [("keep", K.BUILD), ("adopt", K.BUILD), ("pause", "pause")]
    assert q.text == (
        "The combined work cannot keep both behaviours in one situation.\n\n"
        f"This Change: {SHOWS}\nThe latest work on main: {HIDES}\n\nKeep this Change's behaviour there?"
    )
    assert overlap.integrated(store, C1, c, repo, start, done, told("", "")) is done  # nothing is left for him
    kept = answered(c, asked)
    assert overlap.integrated(store, C1, kept, repo, start, done, told()) is done  # answered: not asked again
    assert overlap.collision(integrating(), told().merge, SIDES).question.step == K.INTEGRATE


def test_an_integration_that_asks_or_steps_back_passes_through_to_its_completion(conflicted, tmp_path):
    repo, start = conflicted
    store = Store(tmp_path / "store")
    for exit_ in (Exit.ASK, Exit.BACK, Exit.RETRY):
        unfinished = StepResult(exit=exit_, reason="checks fail after the update")
        assert overlap.integrated(store, C1, building(), repo, start, unfinished) is unfinished


def test_an_integration_result_without_its_merge_report_stops(merged_cleanly, tmp_path):
    repo, start = merged_cleanly
    old = tools.BuildResult(summary="merged", checks=[])  # a result held from before the report existed
    stopped = overlap.integrated(
        Store(tmp_path / "store"), C1, building(), repo, start, StepResult(exit=Exit.DONE), old
    )
    assert (stopped.exit, stopped.stop.kind) == (Exit.STOP, ErrorKind.STATE)
    assert "does not say what the merge did to behaviour" in stopped.reason


def test_an_integration_build_without_its_start_head_stops_instead_of_passing(tmp_path):
    stopped = overlap.integrated(Store(tmp_path / "store"), C1, building(), tmp_path, None,
                                 StepResult(exit=Exit.DONE), told())  # fmt: skip
    assert (stopped.exit, stopped.stop.kind) == (Exit.STOP, ErrorKind.STATE)


def test_a_build_that_is_not_an_integration_is_not_checked_for_collisions(tmp_path):
    done = StepResult(exit=Exit.DONE)
    assert overlap.integrated(Store(tmp_path / "store"), C1, building("plan"), tmp_path, None, done) is done


def test_a_new_integration_task_or_a_new_merge_does_not_reuse_an_earlier_collision_answer():
    c, report = building(), told().merge
    first = overlap.collision(c, report, SIDES)
    c = answered(c, first)
    assert overlap.collision(c, report, SIDES) is None
    later = overlap.collision(c, report, [*SIDES, ("c" * 40, "d" * 40)])  # the target moved and was merged again
    assert (later.exit, later.cause != first.cause) == (Exit.ASK, True)
    c.plan.tasks.append(Task(id="t3", title="another integration", scope=["src"], origin="integration"))
    c.step = Step(kind=K.BUILD, task="t3")
    asked = overlap.collision(c, report, SIDES)
    assert asked.exit == Exit.ASK
    assert asked.cause != first.cause


def test_replanning_with_reused_task_numbers_requires_fresh_collision_consent(tmp_path, monkeypatch):
    c, report = building(), told().merge
    first = overlap.collision(c, report, SIDES)
    c = answered(c, first)
    c = loop.apply(c, StepResult(exit=Exit.BACK, back_to=K.PLAN, cause="conflict:build:replan", reason="replan"), NOW)
    assert c.budgets.replans == 1
    store = Store(tmp_path / "store")
    c = replace_plan(c, store, tmp_path, monkeypatch)

    asked = overlap.collision(c, report, SIDES)

    assert asked is not None
    assert asked.cause != first.cause
    assert c.questions[0].answer.option == "keep"


def test_owner_final_review_replan_with_unchanged_retry_budget_requires_new_consent(tmp_path, monkeypatch):
    c, report = building(), told().merge
    first = overlap.collision(c, report, SIDES)
    c = answered(c, first)
    before = c.brief.version, c.budgets.replans
    final = RoundLoop(subject=FINAL, policy=RoundPolicy())
    round_flow.replan(c, final, "Owner selected Plan again from the brief", NOW)
    assert c.step.kind == K.PLAN
    assert (c.brief.version, c.budgets.replans) == before
    c = replace_plan(c, Store(tmp_path / "store"), tmp_path, monkeypatch)

    asked = overlap.collision(c, report, SIDES)

    assert asked is not None
    assert asked.cause != first.cause
    assert c.plan.version == 2


def test_a_report_in_other_words_is_asked_again_but_reaches_the_owner_at_most_twice():
    c = building()
    c.brief.approved_version = c.brief.version
    first = overlap.collision(c, told().merge, SIDES)
    c = answered(c, first)
    second = overlap.collision(c, told("The page keeps an empty chart on such days.").merge, SIDES)
    assert (second.cause != first.cause, second.question.follows == first.question.follows) == (True, True)
    c = answered(c, second)
    assert c.questions[-1].text.startswith(f'You answered {c.questions[0].id} with "Yes: keep this Change')
    third = overlap.collision(c, told("An empty chart stays visible then.").merge, SIDES)
    c = loop.apply(c, third, NOW)
    assert (len(c.questions), c.repairs.current is not None) == (2, True)  # Delivery handles it now


def test_a_completed_result_with_an_unfinished_merge_stays_stopped(conflicted, tmp_path):
    repo, start = conflicted
    stopped = overlap.integrated(
        Store(tmp_path / "store"), C1, building(), repo, start, StepResult(exit=Exit.DONE), told()
    )
    assert stopped.exit == Exit.STOP
    assert stopped.stop.kind == ErrorKind.STATE


@pytest.mark.parametrize("choice", ["keep", "adopt"])
def test_pause_then_resume_does_not_authorize_collision_resolution(choice):
    c, report = building(), told().merge
    c = loop.apply(c, overlap.collision(c, report, SIDES), NOW)
    question = loop.open_question(c)
    paused, step = loop.schedule(c, [AnswerItem(at=NOW, question=question.id, option="pause")], NOW)
    assert step is None
    resumed, step = loop.schedule(paused, [IntentItem(at=NOW, intent="resume")], NOW)
    assert step.kind == K.BUILD

    asked = overlap.collision(resumed, report, SIDES)

    assert asked is not None
    resumed = loop.apply(resumed, asked, NOW)
    fresh = loop.open_question(resumed)
    assert fresh.id != question.id
    done, step = loop.schedule(resumed, [AnswerItem(at=NOW, question=fresh.id, option=choice)], NOW)
    assert step.kind == K.BUILD
    assert overlap.collision(done, report, SIDES) is None


def test_unverified_integration_termination_keeps_its_stop_and_recovery(conflicted, tmp_path):
    repo, start = conflicted
    stop = Stop(
        kind=ErrorKind.CAPACITY, reason="runtime termination is unverified", action="Stop the old worker",
        resume="The old worker is confirmed stopped", at=NOW,
    )  # fmt: skip
    stopped = StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)

    observed = overlap.integrated(Store(tmp_path / "store"), C1, building(), repo, start, stopped)

    assert observed is stopped
    assert observed.stop == stop


def test_a_failed_git_collision_probe_stops_instead_of_passing(tmp_path, monkeypatch):
    store = Store(tmp_path / "store")

    def failed(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 128, "", "object database unreadable")

    monkeypatch.setattr(overlap.subprocess, "run", failed)
    stopped = overlap.integrated(store, C1, building(), tmp_path, "a" * 40, StepResult(exit=Exit.DONE), told())
    assert (stopped.exit, stopped.stop.kind) == (Exit.STOP, ErrorKind.STATE)
    assert "collision" in stopped.reason.lower()


def test_neighbours_are_other_open_or_recently_merged_changes(tmp_path):
    store = Store(tmp_path / "store")
    old, recent = NOW - overlap.RECENT - timedelta(seconds=1), NOW - timedelta(days=1)
    for slug, finished in [("c1", None), ("c2", None), ("c3", recent), ("c4", old)]:
        with store.lock(slug) as lock:
            store.write(lock, Change(slug=slug, plan=plan(f"{slug}/x"), finished_at=finished))
    near = overlap.neighbours(store, "c1", NOW)
    assert [(n.handle, n.scope, n.merged) for n in near] == [("c2", ["c2/x"], False), ("c3", ["c3/x"], True)]


def test_a_collision_check_that_fails_stops_and_logs_its_whole_reason(
    merged_cleanly, tmp_path, monkeypatch, whole_error
):
    repo, start = merged_cleanly
    store = shared_store(tmp_path)
    c = building()
    c.plan.tasks[1].base, c.names.worktree = start, str(repo)
    store.write(C1, c)
    probe = ["git", "rev-list", "--first-parent"]

    def unreadable(*_a):
        raise subprocess.CalledProcessError(128, probe, stderr=whole_error)

    async def built(cfg):
        head = git(repo, "rev-parse", "HEAD")
        return Run(cfg.session_id, "result", tools.BuildResult(summary="merged", checks=[]), head=head,
                   termination=Termination(confirmed=True))  # fmt: skip

    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: repo)
    monkeypatch.setattr(runner.sdk_adapter, "run", built)
    monkeypatch.setattr(overlap, "_merges", unreadable)
    runner._agent(store, C1, store.read("c1"), repo)  # noqa: SLF001
    expected = (
        "Integration collisions could not be checked: CalledProcessError: "
        f"Command '{probe}' returned non-zero exit status 128.\n{whole_error}"
    )
    assert store.read("c1").outcome.reason == expected
    assert [e["reason"] for e in store.events("c1") if e.get("event") == "collisions-unchecked"] == [expected]
