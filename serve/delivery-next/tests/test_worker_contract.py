import asyncio
import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import psutil

from owlbear_delivery_next import processes, sdk_adapter, session_result, tools
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind
from owlbear_delivery_next.permissions import Policy, Request, decide
from owlbear_delivery_next.processes import Termination, verdict
from owlbear_delivery_next.session_result import Run, to_result
from owlbear_delivery_next.tools import AskQuestion, BuildResult, Worktree

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HEAD, BASE = "a" * 40, "b" * 40
GOOD = {
    "summary": "Added greet().",
    "changed_paths": ["packages/app/src/greet.ts"],
    "checks": [{"command": "npm test", "exit_code": 0}],
}


def build(**changes) -> BuildResult:
    result, errors = tools.parse(BuildResult, {**GOOD, **changes})
    assert errors == []
    return result


def test_schema_errors_name_the_field_and_the_agent_cannot_name_a_commit() -> None:
    result, errors = tools.parse(BuildResult, {**GOOD, "commit": "3f2c1ab", "checks": [{"command": "npm test"}]})
    assert result is None
    assert any(e.startswith("commit: Extra inputs are not permitted") for e in errors)
    assert any(e.startswith("checks[0].exit_code:") for e in errors)
    assert tools.parse(AskQuestion, "not json")[1] == ["arguments: not a JSON object - send the fields as one object"]


def test_the_derived_head_must_move_past_the_base_with_a_clean_worktree() -> None:
    tree = Worktree(head=BASE, base=BASE, dirty=("packages/app/src/greet.ts",))
    assert tools.check_build(build(), tree, ["npm test"]) == [
        f"changes: no commit since the task's base {BASE[:12]}; commit your changes, then submit again",
        "changes: uncommitted files (packages/app/src/greet.ts); commit them, then submit again",
    ]


def test_a_committed_result_must_name_paths_and_every_passing_check() -> None:
    tree = Worktree(head=HEAD, base=BASE, changed=("packages/app/src/greet.ts", "packages/app/test/greet.test.ts"))
    assert tools.check_build(build(), Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",)), ["npm test"]) == []
    errors = tools.check_build(
        build(checks=[{"command": "npm test", "exit_code": 1}]), tree, ["npm test", "npm run lint"]
    )
    assert errors[0] == "changed_paths: missing packages/app/test/greet.test.ts - list every path your commit changes"
    assert errors[1].startswith("checks[0].exit_code: 1")
    assert errors[2].startswith('checks: "npm run lint" missing')


def test_a_conversation_response_is_validated_against_the_item_kind() -> None:
    tree = Worktree(head=BASE, base=BASE)
    no_action = {"changed_paths": [], "checks": [], "response": {"how": "no-action", "text": "bot notice"}}
    assert tools.check_build(build(**no_action), tree, [], "comment") == []
    assert tools.check_build(build(**no_action), tree, [], "thread") == [
        "response.how: no-action is not allowed for a review thread - fix it or answer it"
    ]
    assert tools.check_build(build(**no_action), tree, [], None)[0].startswith("response: only for")
    assert tools.check_build(build(), Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",)), [], "review")[
        0
    ].startswith("response: required")


def test_question_options_must_differ() -> None:
    q, _ = tools.parse(AskQuestion, {"question": "q", "why": "w", "options": [{"label": "A", "effect": "x"}] * 2})
    assert tools.check_question(q) == ["options: labels repeat - give each option a distinct answer"]


def shell(*texts: str, read_only: bool = False, **kw) -> Request:
    return Request("shell", tuple((t, read_only) for t in texts), **kw)


def test_permission_allows_listed_commands_and_worktree_paths_only(tmp_path: Path) -> None:
    policy = Policy(tmp_path, ("git add", "git commit", "npm test", "cd"))
    (tmp_path / "pkg").mkdir()
    assert decide(policy, shell("cd pkg", "npm test -- --x", f"cd '{tmp_path}/pkg'", "cd ..", "npm test")) is None
    assert decide(policy, shell("git push origin x")) == "`git push origin x` is denied"
    assert decide(policy, shell("npm test", "rm -rf src")) == "`rm -rf src` is not in this step's allow list"
    assert decide(policy, shell("ls", read_only=True, paths=("src",))) is None
    assert decide(policy, shell("cat", read_only=True, paths=("/etc/passwd",))) is not None
    assert decide(policy, shell("npm test", urls=True)) is not None
    assert decide(policy, Request("write", paths=(str(tmp_path / "a.ts"),))) is None
    assert decide(policy, Request("write", paths=("../escape.ts",))) == "write outside the worktree: ../escape.ts"
    assert decide(Policy(tmp_path, (), write=False), Request("write", paths=("a.ts",))) is not None
    assert decide(policy, Request("url")) == "url requests are not allowed in this step"
    assert decide(policy, Request("custom-tool", tool="submit_result")) is None


def test_commands_reaching_outside_the_worktree_are_denied_before_the_allow_list(tmp_path: Path) -> None:
    policy = Policy(tmp_path, ("git add", "git commit", "npm test", "cd"))
    for text, target in [
        ("cd /opt", "/opt"),
        ("cd ../other", "../other"),
        ("git -C /elsewhere commit -m x", "/elsewhere"),
        ("npm test --prefix=../x", "../x"),
        ("git add ~/notes.txt", "~/notes.txt"),
        ("npm test >/srv/out", "/srv/out"),
    ]:
        assert decide(policy, shell(text)) == f"`{text}` reaches {target}, outside the worktree"
    assert decide(policy, shell("cd pkg", "cd ../..")) == "`cd ../..` reaches ../.., outside the worktree"
    assert decide(policy, shell("npm test 2>/dev/null")) is None


def test_patterns_messages_and_comments_are_not_paths(tmp_path: Path) -> None:
    policy = Policy(tmp_path, ("git commit", "git -C", "grep", "sed"))
    for text in [
        "grep -qxF '// keep in sync' src/a.ts",
        "grep -c /api/ src/a.ts",
        "grep -e /x -e /y src",
        "git commit -m '/api: fix'",
        "sed -i '/^debug/d' src/a.ts",
    ]:
        assert decide(policy, shell(text)) is None, text
    for text, target in [
        ("grep -e x /etc/passwd", "/etc/passwd"),
        ("sed -i s/a/b/ /etc/hosts", "/etc/hosts"),
        ("grep -qxF '// x' //etc/hosts", "//etc/hosts"),
        ("git -C /elsewhere commit -m '// x'", "/elsewhere"),
    ]:
        assert decide(policy, shell(text)) == f"`{text}` reaches {target}, outside the worktree"


def test_hook_signing_and_force_bypasses_are_denied(tmp_path: Path) -> None:
    policy = Policy(tmp_path, ("git add", "git commit", "git merge", "git push"))
    for text, flag in [
        ("git commit --no-verify -m x", "--no-verify"),
        ("git commit -n -m x", "-n"),
        ("git commit -anm x", "-anm"),
        ("git commit --no-gpg-sign -m x", "--no-gpg-sign"),
        ("git merge --no-verify main", "--no-verify"),
    ]:
        assert decide(policy, shell(text)) == f"`{text}` uses {flag}, which skips hooks or signing or forces history"
    assert "uses --force-with-lease" in decide(policy, shell("git push --force-with-lease"))
    assert "uses -f" in decide(policy, shell("git push -f origin x"))
    assert decide(policy, shell("git commit -m 'fix -n handling'", "git commit -mn")) is None


def step(**cfg) -> sdk_adapter._Step:
    log: list[dict] = []
    journal = sdk_adapter.Journal(event=log.append, **cfg)
    session = sdk_adapter.Session(
        StepKind.BUILD,
        Path(),
        "s1",
        "m",
        resume=True,
        policy=Policy(Path(), ()),
        observe=Worktree,
        checks=(),
        journal=journal,
    )
    st = sdk_adapter._Step(session, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    st.events = log
    return st


def test_pids_are_kept_with_unknown_start_times_and_persisted_as_seen(monkeypatch) -> None:
    def started(pid: int) -> float:
        if pid == 2:
            raise psutil.AccessDenied(pid)
        if pid == 3:
            raise psutil.NoSuchProcess(pid)
        return 100.0

    monkeypatch.setattr(processes, "started", started)
    st = step()
    st.record(1, 2, 3, None)
    st.record(3, keep=True)
    assert st.run.pids == {1: 100.0, 2: None, 3: None}
    assert [e["pids"] for e in st.events] == [{"1": 100.0, "2": None}, {"3": None}]
    live, groups = processes.targets({1: 100.0, 2: None, 4: 50.0, 5: 60.0}, lambda *_: True, {1: 1, 4: 9, 5: 5}.get, 5)
    assert (live, groups) == ([1, 4, 5], [1])


def test_a_missing_session_is_replaced_only_once_earlier_processes_are_gone(monkeypatch) -> None:
    monkeypatch.setattr(processes, "alive", lambda pid, _c: pid == 7)
    st = step(replaced=lambda: "s2")
    st.cfg = dataclasses.replace(st.cfg, previous={7: 1.0})
    assert (st.replace(), st.run.ending, st.run.pids) == (None, "missing", {7: 1.0})
    st = step(replaced=lambda: "s2")
    assert st.replace() == "s2"
    st = step(replaced=lambda: None)
    assert (st.replace(), st.run.ending, st.run.detail) == (None, "missing", "session missing again")


def test_delivery_is_not_effect_and_a_delivered_answer_is_found_in_the_transcript() -> None:
    def ev(kind: str, content: str) -> SimpleNamespace:
        return SimpleNamespace(type=SimpleNamespace(value=kind), data=SimpleNamespace(content=content))

    events = [ev("assistant.message", "The owner answered"), ev("user.message", "The owner answered: German\n")]
    assert sdk_adapter.sent(events, "The owner answered: German")
    assert not sdk_adapter.sent(events[:1], "The owner answered: German")
    assert [session_result.effect_seen(Run("s", ending=e, payload=build())) for e in ("result", "ask", "deadline")] == [
        True,
        True,
        False,
    ]
    assert not session_result.effect_seen(Run("s", ending="result"))


def test_a_resumed_answer_is_read_back_before_any_send_and_an_unread_transcript_sends_nothing() -> None:
    sends: list[str] = []
    user = SimpleNamespace(type=SimpleNamespace(value="user.message"), data=SimpleNamespace(content="m"))

    async def events(found):
        if found is None:
            raise TimeoutError
        return found

    async def send(message):
        sends.append(message)

    for found in ([user], [], None):
        session = SimpleNamespace(get_events=lambda f=found: events(f), send=send)
        client = SimpleNamespace(get_session_metadata=lambda _s: asyncio.sleep(0, {}))
        client.resume_session = lambda _s, s=session, **_o: asyncio.sleep(0, s)
        st = step()
        asyncio.run(sdk_adapter._open(client, st))  # noqa: SLF001
    assert sends == [sdk_adapter.prompts.CONTINUE, "m"]
    st.run.termination = Termination(confirmed=True)
    r = to_result(st.run, StepKind.BUILD, NOW)
    assert (r.exit, r.cause) == (Exit.RETRY, f"{ErrorKind.LIVENESS}:build:transcript")


def test_a_hung_runtime_stop_is_bounded_and_falls_back_to_signals(monkeypatch) -> None:
    calls: list[str] = []

    async def hang() -> None:
        await asyncio.sleep(60)

    proc = SimpleNamespace(pid=None, terminate=lambda: calls.append("term"), kill=lambda: calls.append("kill"))
    client = SimpleNamespace(_cli_process=proc, stop=hang)
    monkeypatch.setattr(sdk_adapter, "STOP_CALL", 0.05)
    monkeypatch.setattr(sdk_adapter, "GRACE", 0.05)
    monkeypatch.setattr(sdk_adapter, "SETTLE", 0.05)
    st = step()
    t = asyncio.run(sdk_adapter._teardown(client, None, st))  # noqa: SLF001
    assert (t.confirmed, t.problems, calls) == (False, ("runtime PID unknown",), ["term", "kill"])
    assert st.events[-1]["reason"] == "runtime stop failed (TimeoutError)"


def test_deadline_retries_unless_termination_is_unverified_and_carries_the_last_denial() -> None:
    run = Run(
        "s1", ending="deadline", detail="send did not answer within 30 s", termination=Termination(confirmed=True)
    )
    run.denials.append("`git commit --no-verify` uses --no-verify")
    r = to_result(run, StepKind.BUILD, NOW)
    assert (r.exit, r.cause, r.reason, r.denial) == (
        Exit.RETRY,
        f"{ErrorKind.LIVENESS}:build:deadline",
        "send did not answer within 30 s",
        "`git commit --no-verify` uses --no-verify",
    )
    run.termination = Termination(confirmed=False, unknown=(9,), problems=("disconnect failed (OSError)",))
    assert to_result(run, StepKind.BUILD, NOW).stop.reason == (
        "termination unverified: processes 9 still present; disconnect failed (OSError)"
    )


def test_an_exhausted_quota_observation_maps_its_reset_to_wake_at() -> None:
    run = Run("s1", ending="error", detail="request failed", termination=Termination(confirmed=True))
    budget = SimpleNamespace(reset_at_epoch_ms=int(datetime(2026, 10, 10, 15, tzinfo=UTC).timestamp() * 1000))
    seen = SimpleNamespace(observation=SimpleNamespace(capacity_state="exhausted", budget_metadata=budget))
    session_result.note_quota(run, "session.quota_observation", seen)
    r = to_result(run, StepKind.BUILD, NOW)
    assert (r.exit, r.cause, r.wake_at) == (Exit.RETRY, "capacity:build:quota", datetime(2026, 10, 10, 15, tzinfo=UTC))
    error = SimpleNamespace(error_type="rate_limit", error_code="quota_exceeded", message="premium requests used up")
    other = Run("s2", ending="error", termination=Termination(confirmed=True))
    session_result.note_quota(other, "session.error", error)
    assert (other.quota, to_result(other, StepKind.BUILD, NOW).cause) == (True, "capacity:build:quota")


def test_termination_is_confirmed_only_when_every_recorded_pid_is_observed_gone() -> None:
    states = {1: False, 2: False}
    assert verdict({1: 10.0, 2: None}, lambda pid, _: states[pid]).confirmed
    t = verdict({1: 10.0, 2: None, 3: 5.0}, lambda pid, _: {1: False, 2: True, 3: None}[pid])
    assert (t.confirmed, t.survivors, t.unknown) == (False, (2,), (3,))


def test_a_valid_result_still_stops_while_a_step_process_survives() -> None:
    run = Run("s1", ending="result", payload=build(), termination=Termination(confirmed=True))
    assert to_result(run, StepKind.BUILD, NOW).exit == Exit.DONE
    run.termination = Termination(confirmed=False, survivors=(17494,))
    stopped = to_result(run, StepKind.BUILD, NOW)
    assert (stopped.exit, stopped.stop.action) == (Exit.STOP, "End processes 17494")
