"""Item 7 (TD-36, TD-63): the missing-tool report, its five cases in order, and how each one moves the Change."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import permissions, tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    Exit,
    ItemRef,
    Names,
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
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import missing, sdk_adapter, step_input
from owlbear_delivery_next.runtimes.session_result import Run, to_result
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import brief_round, conversation, held, plan_round

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


@pytest.mark.parametrize("tool", ["browser", "open_browser_page", "get_task_output"])
def test_a_window_only_tool_asks_the_owner_by_name_and_no_other_runtime_runs_the_step(tool) -> None:
    r = to_result(run(report(tool, "unknown tool")), K.BUILD, NOW)
    assert (r.exit, r.cause, r.operational) == (Exit.ASK, f"project-env:build:tool-{missing.slug(tool)}", True)
    assert r.question.text == (
        f"{tool} exists only in a VS Code window; Delivery steps run only through the SDK. "
        f"The step needs {tool} for run the integration tests: unknown tool"
    )
    assert options(r) == [("replan", K.PLAN), ("pause", "pause")]  # no switch to another runtime


def test_a_window_only_tool_changes_the_plan_or_the_brief_only_where_they_can_change() -> None:
    plan = to_result(run(report("openBrowserPage", "unknown tool")), K.PLAN, NOW)
    assert options(plan) == [("revise", K.SHAPE), ("pause", "pause")]
    brief = to_result(run(report("open_browser_page", "unknown tool")), K.REVIEW, NOW, K.SHAPE)
    assert options(brief) == [("pause", "pause")]  # the brief changes only in chat


@pytest.mark.parametrize(
    ("enclosing", "exit_", "target"),
    [
        (K.BUILD, Exit.BACK, K.PLAN),
        (K.REVIEW, Exit.BACK, K.PLAN),
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
    premise = StepResult(exit=Exit.BACK, back_to=K.SHAPE, cause="scope:review:brief", reason="AC-1 cannot hold")
    kept = plan_round.judged(c, premise, said)
    assert (kept.exit, kept.plan, kept.challenged) == (Exit.RETRY, c.plan, True)
    assert [f.text for f in c.loops["plan"].findings] == ["premise: AC-1 cannot hold (a.txt:1)"]


# c1 (#1061): the check its builder reported, its resolved form, and pytest's session timeout as observed on OwlBear
C1_CHECK = "cd . && {\nuv run test --changed && uv run lint --no-fix\n}"
C1_TIMEOUT = (  # nodes naming a connection or a quota are no network or capacity failure
    "PASSED tests/test_vscode_step.py::test_connection_speaks_websocket_json_rpc_over_the_local_socket\n"
    "PASSED tests/test_missing.py::test_the_quota_never_overrides_a_report\n"
    "PASSED tests/test_api.py::test_a_rate_limit_waits[ECONNRESET]\n"
    "tests/test_status.py::test_a_line[request failed: connection refused] PASSED\n"
    "10 workers [429 items]\ncollected 429 items\n"
    "========= 429 passed in 900.12s =========\n"
    "xdist.dsession.Interrupted: session-timeout: 900.0 sec exceeded"
)


@pytest.mark.parametrize("check", [C1_CHECK, "cd . && {\nuv run test --changed;uv run lint --no-fix\n}"])
def test_a_check_that_cannot_finish_is_repaired_and_a_network_failure_of_it_still_waits(check) -> None:
    timed_out = run(report("uv run test --changed", C1_TIMEOUT, "run the task's check"), checks=(check,))
    r = to_result(timed_out, K.BUILD, NOW)  # c1 case 1: retried as "failed temporarily" three times
    assert (r.exit, r.setup, r.cause) == (Exit.RETRY, True, "project-env:build:check-uv-run-test-changed")
    c = loop.apply(change(), r, NOW)
    assert (c.repairs.current.cause, c.step.kind, loop.next_step(c, NOW)) == (r.cause, K.BUILD, c.step)  # repaired
    for error in ("npm ERR! request to https://registry.npmjs.org failed, reason: connect ETIMEDOUT 104.16.1.35:443",
                  "Error: read ECONNRESET",
                  "socket.gaierror: [Errno -3] Temporary failure in name resolution",
                  "Error: connect ECONNREFUSED ::1:443",
                  "FAILED tests/test_api.py::test_fetch - ConnectionError: connection refused"):  # fmt: skip
        offline = to_result(run(report("uv run test --changed", error), checks=(check,)), K.BUILD, NOW)
        assert (offline.cause, offline.exit, offline.setup) == (
            "network:build:tool-uv-run-test-changed",
            Exit.RETRY,
            False,
        )
    kept = held.load_run(held.dump_run(timed_out))  # a held result keeps its checks
    assert to_result(kept, K.BUILD, NOW) == r


def test_a_plan_missing_a_profile_entry_is_repaired_never_sent_back_to_the_brief() -> None:
    said = "The project profile must hold a package at the repository root, checked with `uv run test --changed`"
    r = to_result(run(report("project profile packages (check commands)", said)), K.PLAN, NOW)  # c1 case 2
    c = loop.apply(change(K.PLAN), r, NOW)
    assert (r.setup, c.repairs.current.step, c.step.kind) == (True, K.PLAN, K.PLAN)
    assert said in c.repairs.current.evidence


@pytest.mark.parametrize("stage", ["setup", "target"])
def test_a_plan_missing_an_outside_pr_is_repaired_never_sent_back_to_the_brief(stage) -> None:
    said = tools.WrongPremise(  # c1 case 3, recorded as scope:plan:target and sent to shaping
        stage=stage,
        reason="The owner chose to land the exclusion on main in its own PR before re-planning. That has not happened.",
        evidence=["main (054e2edf6) has no exclusion and no PR"],
    )
    c = change(K.PLAN)
    plan_rounds.loop(c, RoundPolicy(), NOW)
    c.step.mode = plan_rounds.CHALLENGE
    r = to_result(Run("s1", ending="premise", payload=said, termination=Termination(confirmed=True)), K.PLAN, NOW)
    assert plan_round.judged(c, r, said) is r  # the plan challenge counts no finding for it
    c = loop.apply(c, r, NOW)
    assert (r.setup, c.repairs.current.step, c.step.kind, c.loops["plan"].round) == (True, K.PLAN, K.PLAN, 0)
    assert "054e2edf6" in c.repairs.current.evidence
    share = Run("s2", "premise", said.model_copy(update={"stage": "setup"}), termination=Termination(confirmed=True))
    assert to_result(share, K.TESTS, NOW).setup  # a test review's share too


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


def test_a_conversation_task_missing_a_tool_asks_instead_of_replanning() -> None:
    ref = ItemRef(id="t1", kind="thread", version="v", task="pr-t1-v", url="https://x/pull/7#r1")
    task = Task(id="pr-t1-v", title="answer", item=ref, detail="boecht: add a docker test\n\nhttps://x/pull/7#r1")
    p = report("matlab", "matlab: license server unknown")
    asked = conversation.disputed(task, p, to_result(run(p), K.BUILD, NOW))
    assert (asked.exit, [o.next for o in asked.question.options]) == (Exit.ASK, [K.BUILD, K.BUILD, "pause"])
    assert "needs matlab" in asked.question.text
    other = report("browser", "no browser tool in this session")
    window = conversation.disputed(task, other, to_result(run(other), K.BUILD, NOW))
    assert options(window) == [("decline", K.BUILD), ("pause", "pause")]


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
    asked = runner._unshelved(failure(caught.value))  # noqa: SLF001
    assert (asked.exit, asked.cause, options(asked)) == (
        Exit.ASK,
        "state:plan:dirty-worktree",
        [("done", K.PLAN), ("pause", "pause")],
    )
    loop.apply(change(K.PLAN), asked, NOW)


def test_prompts_name_the_report() -> None:
    assert "report_missing_tool" in step_input.FINISH
    assert "report_missing_tool" in step_input.reminder("builder")


@pytest.mark.parametrize("how", ["refused", "left"])
def test_a_shelve_failure_is_asked_and_logged_whole(  # noqa: PLR0913, PLR0917 - fixtures
    repo, tmp_path, whole_error, monkeypatch, how, checks_settled
) -> None:
    store = Store(tmp_path / "store")
    checks_settled(store)
    c = change(K.PLAN).model_copy(update={"names": Names(branch="owlbear/c1", target="main")})
    store.write(Lock("c1"), c)
    left = [f"new-{i:02d}-{'x' * 12}.txt" for i in range(30)]
    for name in left:
        (repo / name).write_text("new\n")
    real = worktree.git

    def stash(cwd, *args):
        if args[0] != "stash":
            return real(cwd, *args)
        if how == "refused":
            raise subprocess.CalledProcessError(1, "git stash push", stderr=whole_error)
        return ""  # Git reported success yet kept the files

    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: repo)
    monkeypatch.setattr(worktree, "git", stash)
    runner._step(store, Lock("c1"), store.read("c1"), Step(kind=K.PLAN), repo)  # noqa: SLF001
    why = (
        f"git stash failed in {repo}: CalledProcessError: Command 'git stash push' returned non-zero exit status 1.\n"
        f"{whole_error}"
        if how == "refused"
        else f"files stay uncommitted in {repo} after git stash: " + "\n".join(f"?? {n}" for n in left)
    )
    q = loop.open_question(store.read("c1"))
    assert q.text == (
        "Delivery could not set aside the uncommitted edits before planning "
        f"(ShelveError: {why}). Commit, stash or discard them."
    )
    assert [e["reason"] for e in store.events("c1") if e["event"] == "not-shelved"] == [f"ShelveError: {why}"]


@pytest.mark.parametrize("where", ["report", "session"])
def test_a_denial_keeps_its_whole_text(whole_error, where) -> None:
    if where == "report":
        r = to_result(run(report("docker"), denied={"docker": whole_error}), K.BUILD, NOW)
        reason = f"docker was denied by Delivery's guard, which grants nothing: {whole_error}"
        assert (r.reason, r.denial) == (reason, whole_error)
    else:
        failed = Run("s1", ending="error", detail="stopped", termination=Termination(confirmed=True))
        failed.denials = [f"earlier: {whole_error}"]
        assert to_result(failed, K.BUILD, NOW).denial == f"earlier: {whole_error}"
