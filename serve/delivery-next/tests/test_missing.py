"""Item 7 (TD-36, TD-63): the missing-tool report, its five cases in order, and how each one moves the Change."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import permissions, profile_record, tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    Exit,
    ItemRef,
    Plan,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import brief_rounds, budgets, loop, plan_rounds, worktree
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import missing, sdk_adapter, step_input, window_files
from owlbear_delivery_next.runtimes.session_result import Run, to_result
from owlbear_delivery_next.workflow_steps import brief_round, conversation, plan_round

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
K = StepKind


def report(tool="docker", error="exit status 1", need="run the integration tests") -> tools.MissingTool:
    return tools.MissingTool(tool=tool, need=need, error=error)


def run(payload: tools.MissingTool, **fields) -> Run:
    return Run("s1", ending="missing-tool", payload=payload, termination=Termination(confirmed=True), **fields)


def change(kind=K.BUILD, task="t1") -> Change:
    return Change(
        slug="c1",
        brief=Brief(version=1, approved_version=1, challenged=1, criteria=[Criterion(id="AC-1", text="works")]),
        plan=Plan(tasks=[Task(id="t1", title="one", scope=["a"])]),
        step=Step(kind=kind, task=task if kind in {K.BUILD, K.REVIEW} else None),
    )


def options(r: StepResult) -> list[tuple[str, object]]:
    return [(o.id, o.next) for o in r.question.options]


def test_the_report_is_one_small_described_tool_every_step_offers() -> None:
    assert tools.MISSING in tools.SPECS
    assert (tools.MISSING.name, tools.MISSING.ending) == ("report_missing_tool", "missing-tool")
    assert tools.MISSING.description


def test_a_denied_tool_stays_denied_and_is_retried_within_its_budget() -> None:
    r = to_result(run(report("docker compose"), denied={"docker": "docker is not allowed"}), K.BUILD, NOW)
    assert (r.exit, r.cause, r.denial) == (Exit.RETRY, "policy:build:tool-docker-compose", "docker is not allowed")
    assert "grants nothing" in r.reason
    later = run(report("docker"), denied={"docker": "docker is not allowed"}, denials=["later: gh is denied"])
    assert to_result(later, K.BUILD, NOW).denial == "docker is not allowed"  # the report's own denial wins


@pytest.mark.parametrize(
    ("tool", "error"),
    [
        ("docker", "zsh: command not found: docker"),
        ("docker", "bash: docker: command not found"),
        ("pnpm", "sh: 1: pnpm: not found"),
        ("playwright", "Error: spawn playwright ENOENT"),
        ("terraform", "FileNotFoundError: [Errno 2] No such file or directory: '/usr/bin/terraform'"),
        ("chromium", "Executable doesn't exist at /Users/a/Library/Caches/ms-playwright/chromium-1187/chrome-mac"),
        ("Docker Desktop", "docker is not installed on this machine"),
        ("docker", "Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?"),
        ("pytest", "error: Failed to spawn: `pytest`\n  Caused by: No such file or directory (os error 2)"),
        ("postgres", "postgres is not running on port 5432"),
    ],
)
def test_an_absent_tool_asks_the_owner_to_set_it_up_and_rerun(tool, error) -> None:
    r = to_result(run(report(tool, error)), K.BUILD, NOW)
    assert (r.exit, r.cause, r.operational) == (Exit.ASK, f"project-env:build:tool-{missing.slug(tool)}", True)
    assert r.question.text.startswith(f"Set up {tool} on this machine (install or start it)")
    assert error in r.question.text
    assert options(r) == [("done", "retry"), ("pause", "pause")]


@pytest.mark.parametrize(
    ("tool", "error"),
    [
        ("npm", "npm ERR! enoent ENOENT: no such file or directory, open '/w/web/package.json'"),
        ("go", "zsh: command not found: golangci-lint"),
        ("npm", "npm ran, but vitest is not installed"),
        ("docker", "docker-compose: command not found"),
    ],
)
def test_an_absent_file_or_another_program_is_not_this_tool_missing(tool, error) -> None:
    assert not missing.absent(tool, error)


def test_an_unset_package_goes_back_to_planning() -> None:
    error = "npm ERR! enoent ENOENT: no such file or directory, open '/w/web/package.json'"
    r = to_result(run(report("npm", error, "install the web package")), K.BUILD, NOW)
    assert (r.exit, r.back_to) == (Exit.BACK, K.PLAN)  # no runtime here can install a package that is not set up


def test_a_temporary_failure_retries_at_once_then_after_growing_pauses() -> None:
    error = "npm ERR! network request to https://registry.npmjs.org failed, reason: connect ETIMEDOUT 104.16.1.35:443"
    r = to_result(run(report("npm", error)), K.BUILD, NOW)
    assert (r.exit, r.cause, r.reason, r.detail, r.wake_at) == (
        Exit.RETRY,
        "network:build:tool-npm",
        "npm failed temporarily",
        error,
        NOW,
    )
    c = loop.apply(change(), r, NOW)
    assert (c.outcome.exit, c.outcome.wake_at, loop.next_step(c, NOW)) == (Exit.PENDING, NOW, c.step)
    c = loop.apply(c, r, NOW)
    assert c.outcome.wake_at == NOW + 2 * budgets.PAUSE
    late = NOW + budgets.EPISODE_ASK
    c = loop.apply(c, r.model_copy(update={"wake_at": late}), late)
    assert error in c.questions[-1].text  # the owner sees the real error, not the stable reason


def test_a_tool_of_another_runtime_asks_since_delivery_does_not_rerun_there_yet(monkeypatch) -> None:
    monkeypatch.setattr(profile_record, "WINDOW_PAUSED", False)
    r = to_result(run(report("browser", "no browser tool in this session")), K.BUILD, NOW)
    assert (r.exit, r.cause) == (Exit.ASK, "project-env:build:tool-browser")
    assert "only in the window runtime; this step ran in the sdk runtime" in r.question.text
    assert options(r) == [("switched", "retry"), ("replan", K.PLAN), ("pause", "pause")]
    plan = to_result(run(report("openBrowserPage", "unknown tool")), K.PLAN, NOW)
    assert options(plan)[1] == ("revise", K.SHAPE)
    brief = to_result(run(report("open_browser_page", "unknown tool")), K.REVIEW, NOW, K.SHAPE)
    assert options(brief) == [("switched", "retry"), ("pause", "pause")]  # the brief changes only in chat
    task = to_result(run(report("get_task_output", "unknown tool")), K.BUILD, NOW)
    assert (task.exit, task.cause) == (Exit.ASK, "project-env:build:tool-get-task-output")


def test_a_window_tool_offers_no_switch_while_window_steps_are_paused() -> None:
    r = to_result(run(report("browser", "no browser tool in this session")), K.BUILD, NOW)
    assert (r.exit, r.cause) == (Exit.ASK, "project-env:build:tool-browser")
    assert profile_record.PAUSED_NOTE in r.question.text
    assert options(r) == [("replan", K.PLAN), ("pause", "pause")]
    brief = to_result(run(report("open_browser_page", "unknown tool")), K.REVIEW, NOW, K.SHAPE)
    assert options(brief) == [("pause", "pause")]
    there = to_result(run(report("get_errors", "the tool failed"), runtime="window"), K.BUILD, NOW)
    assert there.exit == Exit.BACK  # the window runtime has it; it is still missing, so nowhere fits


@pytest.mark.parametrize(
    ("enclosing", "exit_", "target"),
    [
        (K.BUILD, Exit.BACK, K.PLAN),
        (K.REVIEW, Exit.BACK, K.PLAN),
        (K.PLAN, Exit.BACK, K.SHAPE),
        (K.CHECK, Exit.ASK, K.PLAN),
        (K.FOLLOW, Exit.ASK, K.PLAN),
    ],
)
def test_a_tool_no_runtime_has_changes_the_work_that_asked_for_it(enclosing, exit_, target) -> None:
    p = report("matlab", "matlab: license server unknown")
    r = to_result(run(p), K.REVIEW, NOW, enclosing)
    assert (r.exit, r.cause) == (exit_, f"scope:{enclosing}:tool-matlab")
    assert "needs matlab for run the integration tests: matlab: license server unknown" in r.reason
    if exit_ == Exit.BACK:
        assert r.back_to == target
    else:
        assert options(r) == [("replan", target), ("pause", "pause")]
    loop.apply(change(enclosing), r, NOW)  # every case is an exit its step defines


def test_a_brief_challenge_without_the_tool_makes_it_the_rounds_finding_for_the_shaper() -> None:
    r = to_result(run(report("matlab", "matlab: license server unknown")), K.REVIEW, NOW, K.SHAPE)
    due = change(K.SHAPE).model_copy(update={"brief": Brief(version=1, requested=1)})
    due.step.mode = brief_rounds.CHALLENGE
    due.loops["brief"] = RoundLoop(subject="brief", policy=RoundPolicy())
    assert brief_round.judged(due, r, r.model_copy(), NOW) is None
    assert (due.loops["brief"].findings[0].text.startswith("the brief needs matlab"), due.outcome.waiting) == (
        True, Waiting.CHAT
    )  # fmt: skip


def test_the_quota_never_overrides_a_report() -> None:
    r = to_result(run(report("matlab", "license server unknown"), quota=True), K.BUILD, NOW)
    assert (r.exit, r.back_to) == (Exit.BACK, K.PLAN)


def test_the_plan_challenge_passes_an_operational_step_back_on_and_keeps_a_premise_its_own() -> None:
    c = change(K.PLAN)
    plan_rounds.loop(c, RoundPolicy(), NOW)
    c.step.mode = plan_rounds.CHALLENGE
    nowhere = to_result(run(report("matlab", "license server unknown")), K.REVIEW, NOW, K.PLAN)
    assert plan_round.judged(c, nowhere, nowhere) is nowhere  # counted no round: the same plan is challenged again
    assert (c.loops["plan"].round, c.step.mode) == (0, plan_rounds.CHALLENGE)
    said = tools.WrongPremise(stage="brief", reason="AC-1 cannot hold", evidence=["a.txt:1"])
    premise = nowhere.model_copy(update={"operational": False})
    kept = plan_round.judged(c, premise, said)
    assert (kept.exit, kept.plan, kept.challenged) == (Exit.RETRY, c.plan, True)
    assert [f.text for f in c.loops["plan"].findings] == ["premise: AC-1 cannot hold (a.txt:1)"]


def test_the_planner_reads_why_the_change_is_planned_again() -> None:
    c = loop.apply(change(), to_result(run(report("matlab", "license server unknown")), K.BUILD, NOW), NOW)
    assert c.step.kind == K.PLAN
    text = step_input.plan(c, Profile(), Path("/w"), {})
    assert "## Why the Change is planned again" in text
    assert "needs matlab for run the integration tests" in text


def test_installed_and_rerun_resumes_the_same_task() -> None:
    r = to_result(run(report("docker", "zsh: command not found: docker")), K.BUILD, NOW)
    c = loop.apply(change(), r, NOW)
    q = c.questions[-1]
    assert loop.owner_gated(c)
    c = loop.fold(c, [AnswerItem(at=NOW, channel="status-view", question=q.id, option="done")], NOW)
    assert (c.step.kind, c.step.task, loop.next_step(c, NOW)) == (K.BUILD, "t1", c.step)


def test_pause_is_never_delivered_to_the_session_after_resume() -> None:
    r = to_result(run(report("docker", "zsh: command not found: docker")), K.BUILD, NOW)
    c = loop.apply(change(), r, NOW)
    q = c.questions[-1]
    c = loop.fold(c, [AnswerItem(at=NOW, channel="status-view", question=q.id, option="pause")], NOW)
    assert (c.intent.paused_at, loop.next_step(c, NOW)) == (NOW, None)
    c = loop.fold(c, [IntentItem(at=NOW, intent="resume")], NOW)
    assert (c.step.kind, c.step.task, loop.next_step(c, NOW)) == (K.BUILD, "t1", c.step)
    assert [p.id for p in c.questions if p.answer and not p.effect_observed_at] == []  # the runner resumes with these


def shell(text: str) -> SimpleNamespace:
    """One SDK shell permission request for *text*."""
    command = SimpleNamespace(identifier=text.split(maxsplit=1)[0])
    segment = SimpleNamespace(full_command_text=text)
    return SimpleNamespace(
        kind="shell",
        commands=[command],
        command_segments=[segment],
        full_command_text=text,
        possible_paths=(),
        possible_urls=(),
    )


def test_denials_record_the_programs_they_name() -> None:
    piped = permissions.Request("shell", ("cd web && /usr/local/bin/docker ps | grep api",))
    assert permissions.identities(piped) == {"docker", "grep"}
    assert permissions.identities(permissions.Request("mcp", tool="Fetch")) == {"fetch"}
    assert permissions.identities(permissions.Request("url")) == {"url"}
    cfg = sdk_adapter.Session(
        K.BUILD,
        Path(),
        "s1",
        "m",
        resume=False,
        policy=Policy(Path(), write=False),
        observe=tools.Worktree,
        checks=(),
        journal=sdk_adapter.Journal(event=lambda _e: None),
    )
    st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    st.permission(shell("docker compose up > log"), None)
    assert list(st.run.denied) == ["docker"]
    assert st.run.denied["docker"] == st.run.denials[-1]
    st.permission(shell("docker ps"), None)
    assert st.run.denied == {}  # a later allowed use of the program supersedes its denial


def test_a_conversation_task_missing_a_tool_asks_instead_of_replanning(monkeypatch) -> None:
    monkeypatch.setattr(profile_record, "WINDOW_PAUSED", False)
    ref = ItemRef(id="t1", kind="thread", version="v", task="pr-t1-v", url="https://x/pull/7#r1")
    task = Task(id="pr-t1-v", title="answer", item=ref, detail="boecht: add a docker test\n\nhttps://x/pull/7#r1")
    p = report("matlab", "matlab: license server unknown")
    asked = conversation.disputed(task, p, to_result(run(p), K.BUILD, NOW))
    assert (asked.exit, [o.next for o in asked.question.options]) == (Exit.ASK, [K.BUILD, K.BUILD, "pause"])
    assert "needs matlab" in asked.question.text
    other = report("browser", "no browser tool in this session")
    switch = conversation.disputed(task, other, to_result(run(other), K.BUILD, NOW))
    assert options(switch) == [("switched", "retry"), ("decline", K.BUILD), ("pause", "pause")]


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    work = tmp_path / "work"
    work.mkdir()
    worktree.git(work, "init", "-q")
    (work / "a.txt").write_text("a\n")
    worktree.git(work, "add", "a.txt")
    worktree.git(work, "commit", "-q", "-m", "base")
    return work


def test_planning_starts_on_a_clean_tree_whatever_step_left_edits(repo, monkeypatch) -> None:
    events: list[dict] = []
    store = SimpleNamespace(log=lambda _lock, _slug, e: events.append(e))
    monkeypatch.setattr(runner.plan_round, "scopes", lambda *_: {"c2": ["b"]})
    assert runner._planning(store, None, "c1", repo) == {"c2": ["b"]}  # noqa: SLF001 - a clean tree keeps nothing
    assert (events, worktree.git(repo, "stash", "list")) == ([], "")
    (repo / "a.txt").write_text("edited\n")
    (repo / "new.txt").write_text("new\n")
    runner._planning(store, None, "c1", repo)  # noqa: SLF001
    assert worktree.git(repo, "status", "--porcelain") == ""
    assert "owlbear c1: uncommitted edits before planning" in worktree.git(repo, "stash", "list")
    assert worktree.git(repo, "stash", "show", "--include-untracked", "--name-only").split() == ["a.txt", "new.txt"]
    assert [e["event"] for e in events] == ["shelved"]


def test_a_failed_shelve_asks_the_owner_before_any_planner_runs(tmp_path) -> None:
    with pytest.raises(worktree.ShelveError, match="git stash failed") as caught:
        worktree.shelve(tmp_path, "owlbear c1")  # not a repository: Git fails
    asked = runner._unshelved(caught.value)  # noqa: SLF001
    assert (asked.exit, asked.cause, options(asked)) == (
        Exit.ASK,
        "state:plan:dirty-worktree",
        [("done", K.PLAN), ("pause", "pause")],
    )
    loop.apply(change(K.PLAN), asked, NOW)


def test_prompts_and_window_note_name_the_report() -> None:
    assert "report_missing_tool" in step_input.FINISH
    assert "report_missing_tool" in step_input.reminder("builder")
    assert "report_missing_tool" in window_files.tools_note("builder")
