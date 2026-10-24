import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    ErrorKind,
    Exit,
    Overlap,
    Plan,
    Question,
    Step,
    StepKind,
    Stop,
    Task,
)
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.change_flow.status import Activity, card
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import overlap

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
K = StepKind


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


def shared_store(tmp_path) -> Store:
    store = Store(tmp_path / "store")
    with store.lock("c3") as lock:
        store.write(lock, Change(slug="c3", handle="c3", brief=Brief(outcome="cache pages"), plan=plan("src/app.ts")))
    return store


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


def test_a_resolved_conflict_on_another_changes_scope_asks_naming_both_outcomes(conflicted):
    repo, start = conflicted
    (repo / "src/app.ts").write_text("both")
    (repo / "uv.lock").write_text("both")
    git(repo, "commit", "-qam", "merge main")
    paths = overlap.collided(repo, start, resolved=True)
    assert paths == ["src/app.ts", "uv.lock"]
    near = [overlap.Neighbour("c3", ["src", "uv.lock"], "cache pages", merged=True)]
    asked = overlap.collision(integrating(), paths, near)
    q = asked.question
    assert (asked.exit, q.step, [o.id for o in q.options]) == (Exit.ASK, K.INTEGRATE, ["keep", "adopt", "pause"])
    assert "c3 on src/app.ts." in q.text  # the lockfile is incidental
    assert ("pages load in 1 s" in q.text, "c3 (merged) wants: cache pages" in q.text) == (True, True)
    assert overlap.collision(integrating(), paths, [overlap.Neighbour("c4", ["lib"], "x", merged=False)]) is None


def test_an_unfinished_update_on_another_changes_scope_asks_once_and_the_answer_continues(conflicted, tmp_path):
    repo, start = conflicted
    store = Store(tmp_path / "store")
    other = Change(slug="c3", handle="c3", brief=Brief(outcome="cache pages"), plan=plan("src/app.ts"))
    with store.lock("c3") as lock:
        store.write(lock, other)
    said = StepResult(exit=Exit.ASK, question=Question(step=K.INTEGRATE, text="checks fail after the update"))
    c = integrating()
    asked = overlap.integrated(store, c, repo, (start, "ask"), said)
    assert "The Builder said: checks fail after the update" in asked.question.text
    assert overlap.integrated(store, c, repo, (start, "timeout"), said) is said
    c = loop.apply(c, asked, NOW)
    q = loop.open_question(c)
    keep, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="keep")], NOW)
    assert step.kind == K.INTEGRATE
    assert overlap.integrated(store, keep, repo, (start, "ask"), said) is said  # answered: not asked again
    paused, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="pause")], NOW)
    assert (step, paused.intent.paused_at) == (None, NOW)


def test_an_integration_build_whose_update_collides_asks_on_its_own_step(conflicted, tmp_path):
    repo, start = conflicted
    (repo / "src/app.ts").write_text("both")
    (repo / "uv.lock").write_text("both")
    git(repo, "commit", "-qam", "merge main")
    asked = overlap.integrated(shared_store(tmp_path), building(), repo, (start, "result"), StepResult(exit=Exit.DONE))
    q = asked.question
    assert (asked.exit, q.step) == (Exit.ASK, K.BUILD)
    assert [(o.id, o.next) for o in q.options] == [("keep", K.BUILD), ("adopt", K.BUILD), ("pause", "pause")]
    assert "c3 on src/app.ts." in q.text


def test_a_plain_overlap_that_merges_cleanly_is_recorded_not_asked(merged_cleanly, tmp_path):
    repo, start = merged_cleanly
    done = StepResult(exit=Exit.DONE)
    assert overlap.collided(repo, start, resolved=True) == []
    assert overlap.integrated(shared_store(tmp_path), building(), repo, (start, "result"), done) is done


def test_an_integration_build_without_its_start_head_stops_instead_of_passing(tmp_path):
    stopped = overlap.integrated(shared_store(tmp_path), building(), tmp_path, (None, "result"),
                                 StepResult(exit=Exit.DONE))  # fmt: skip
    assert (stopped.exit, stopped.stop.kind) == (Exit.STOP, ErrorKind.STATE)


def test_a_build_that_is_not_an_integration_is_not_checked_for_collisions(tmp_path):
    done = StepResult(exit=Exit.DONE)
    assert overlap.integrated(shared_store(tmp_path), building("plan"), tmp_path, (None, "result"), done) is done


def test_a_new_integration_task_does_not_reuse_an_earlier_collision_answer():
    c = building()
    near = [overlap.Neighbour("c3", ["src"], "cache pages", merged=False)]
    first = overlap.collision(c, ["src/app.ts"], near)
    c = loop.apply(c, first, NOW)
    question = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question=question.id, option="keep")], NOW)
    assert overlap.collision(c, ["src/app.ts"], near) is None
    c.plan.tasks.append(Task(id="t3", title="another integration", scope=["src"], origin="integration"))
    c.step = Step(kind=K.BUILD, task="t3")
    asked = overlap.collision(c, ["src/app.ts"], near)
    assert asked.exit == Exit.ASK
    assert asked.cause != first.cause


def test_replanning_with_reused_task_numbers_requires_fresh_collision_consent(tmp_path):
    c = building()
    near = [overlap.Neighbour("c3", ["src"], "cache pages", merged=False)]
    first = overlap.collision(c, ["src/app.ts"], near)
    c = loop.apply(c, first, NOW)
    question = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question=question.id, option="keep")], NOW)
    c = loop.apply(c, StepResult(exit=Exit.BACK, back_to=K.PLAN, cause="conflict:build:replan", reason="replan"), NOW)
    assert c.budgets.replans == 1
    c = loop.apply(c, StepResult(exit=Exit.DONE, plan=plan("src")), NOW)
    c.plan.tasks[0].done = True
    c.plan.tasks.append(Task(id="t2", title="new integration", scope=["src"], origin="integration"))
    c.step = Step(kind=K.BUILD, task="t2")
    store = Store(tmp_path / "store")
    with store.lock(c.slug) as lock:
        store.write(lock, c)
    c = store.read(c.slug)

    asked = overlap.collision(c, ["src/app.ts"], near)

    assert asked is not None
    assert asked.cause != first.cause
    assert c.questions[0].answer.option == "keep"


@pytest.mark.parametrize("choice", ["keep", "adopt"])
def test_pause_then_resume_does_not_authorize_collision_resolution(choice):
    c = building()
    near = [overlap.Neighbour("c3", ["src"], "cache pages", merged=False)]
    c = loop.apply(c, overlap.collision(c, ["src/app.ts"], near), NOW)
    question = loop.open_question(c)
    paused, step = loop.schedule(c, [AnswerItem(at=NOW, question=question.id, option="pause")], NOW)
    assert step is None
    resumed, step = loop.schedule(paused, [IntentItem(at=NOW, intent="resume")], NOW)
    assert step.kind == K.BUILD

    asked = overlap.collision(resumed, ["src/app.ts"], near)

    assert asked is not None
    resumed = loop.apply(resumed, asked, NOW)
    fresh = loop.open_question(resumed)
    assert fresh.id != question.id
    answered, step = loop.schedule(resumed, [AnswerItem(at=NOW, question=fresh.id, option=choice)], NOW)
    assert step.kind == K.BUILD
    assert overlap.collision(answered, ["src/app.ts"], near) is None


@pytest.mark.parametrize("ending", ["ask", "premise"])
def test_unverified_integration_termination_keeps_its_stop_and_recovery(conflicted, tmp_path, ending):
    repo, start = conflicted
    stop = Stop(
        kind=ErrorKind.CAPACITY, reason="runtime termination is unverified", action="Stop the old worker",
        resume="The old worker is confirmed stopped", at=NOW,
    )  # fmt: skip
    stopped = StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)

    observed = overlap.integrated(shared_store(tmp_path), building(), repo, (start, ending), stopped)

    assert observed is stopped
    assert observed.stop == stop


def test_a_failed_git_collision_probe_stops_instead_of_passing(tmp_path, monkeypatch):
    store = shared_store(tmp_path)

    def failed(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 128, "", "object database unreadable")

    monkeypatch.setattr(overlap.subprocess, "run", failed)
    stopped = overlap.integrated(store, building(), tmp_path, ("a" * 40, "result"), StepResult(exit=Exit.DONE))
    assert (stopped.exit, stopped.stop.kind) == (Exit.STOP, ErrorKind.STATE)
    assert "collision" in stopped.reason.lower()


@pytest.mark.parametrize("filename", ["src/app with spaces.ts", "src/app\nwith\nlines.ts"])
def test_collision_paths_keep_whitespace_in_both_pending_and_resolved_merges(tmp_path, filename):
    repo, start = conflicting_repository(tmp_path, filename)
    near = [overlap.Neighbour("c3", ["src"], "cache pages", merged=False)]
    pending = overlap.collided(repo, start, resolved=False)
    assert filename in pending
    assert filename in overlap.collision(building(), pending, near).question.text
    (repo / filename).write_text("both")
    (repo / "uv.lock").write_text("both")
    git(repo, "commit", "-qam", "merge main")
    resolved = overlap.collided(repo, start, resolved=True)
    assert filename in resolved
    assert filename in overlap.collision(building(), resolved, near).question.text


def test_neighbours_are_other_open_or_recently_merged_changes(tmp_path):
    store = Store(tmp_path / "store")
    old, recent = NOW - overlap.RECENT - timedelta(seconds=1), NOW - timedelta(days=1)
    for slug, finished in [("c1", None), ("c2", None), ("c3", recent), ("c4", old)]:
        with store.lock(slug) as lock:
            store.write(lock, Change(slug=slug, plan=plan(f"{slug}/x"), finished_at=finished))
    near = overlap.neighbours(store, "c1", NOW)
    assert [(n.handle, n.scope, n.merged) for n in near] == [("c2", ["c2/x"], False), ("c3", ["c3/x"], True)]
