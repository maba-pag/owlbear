import asyncio
import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest

from owlbear_delivery_next import processes, prompts, sdk_adapter, session_result, tools
from owlbear_delivery_next.models import Change, ErrorKind, Exit, ItemRef, Plan, StepKind, Task
from owlbear_delivery_next.permissions import Policy, Request, decide
from owlbear_delivery_next.processes import Termination, verdict
from owlbear_delivery_next.profile_record import Profile, ProfileEntry
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


def test_the_plan_reviewer_sees_where_each_check_runs() -> None:
    entry = ProfileEntry(state="known", value="npm test", evidence="packages/app/package.json")
    profile = Profile(entries={"check:packages/app": entry})
    plan = Plan(tasks=[Task(id="t1", title="Add sign", scope=["packages/app"], checks=["npm test"])])
    text = prompts.plan_review(Change(slug="s"), plan, profile, Path("/w"), {})
    assert "- `packages/app`: install `none`, check `npm test`" in text
    assert "runs each check from its package directory" in text


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


def test_only_a_bot_comment_or_review_may_be_left_without_a_reply() -> None:
    tree = Worktree(head=BASE, base=BASE)
    no_action = build(changed_paths=[], checks=[], response={"how": "no-action", "text": "bot notice"})
    refused = "response.how: no-action is only for a bot's comment or review - fix it or answer it"

    def ref(kind, *, bot):
        return ItemRef(id="i", kind=kind, version="v", task="t", bot=bot)

    assert tools.check_build(no_action, tree, [], ref("comment", bot=True)) == []
    assert tools.check_build(no_action, tree, [], ref("review", bot=True)) == []
    for kind, bot in (("comment", False), ("review", False), ("thread", False), ("thread", True)):
        assert tools.check_build(no_action, tree, [], ref(kind, bot=bot)) == [refused], (kind, bot)
    assert tools.check_build(no_action, tree, [], None)[0].startswith("response: only for")
    assert tools.check_build(
        build(), Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",)), [], ref("review", bot=False)
    )[0].startswith("response: required")


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


def test_allowed_commands_cannot_write_through_a_symlink_or_output_option(tmp_path: Path) -> None:
    root, away = tmp_path / "wt", tmp_path / "away"
    root.mkdir()
    away.mkdir()
    (root / "link").symlink_to(away)
    text = "git --no-pager diff --output=link/out"
    for write in (True, False):
        policy = Policy(root, ("git diff", "git add"), write=write)
        assert decide(policy, shell(text, read_only=True)) == f"`{text}` reaches link/out, outside the worktree"
        assert decide(policy, shell("git diff", read_only=True, paths=(str(away / "x"),))) is not None
    assert (
        decide(Policy(root, ("git add",)), shell("git add link/x"))
        == "`git add link/x` reaches link/x, outside the worktree"
    )
    read = Policy(root, ("git diff", "git log"), write=False)
    assert decide(read, shell("git diff --output=x", read_only=True)) == (
        "`git diff --output=x` uses --output=x, which writes in a read-only step"
    )
    assert "uses -o" in decide(read, shell("git log -o x", read_only=True))
    assert "uses --ext-diff" in decide(read, shell("git diff --ext-diff", read_only=True))
    assert "uses a redirect" in decide(read, shell("git log >> notes", read_only=True))
    assert decide(read, shell("git diff --textconv HEAD", read_only=True)) is None


def test_a_prefix_cannot_smuggle_a_second_command(tmp_path: Path) -> None:
    policy = Policy(tmp_path, ("npm test", "git commit"))
    for text in [
        "npm test; rm -rf src",
        "npm test || rm x",
        "npm test | sh",
        "npm test & rm x",
        "npm test > x",
        "npm test < x",
        "npm test $(rm x)",
        "npm test `rm x`",
        'npm test "$(rm x)"',
    ]:
        assert decide(policy, shell(text)) == f"`{text}` is not in this step's allow list", text
    for text in ["npm test 2>/dev/null", "npm test 2>&1", "git commit -m 'a; b | `c` $(d)'"]:
        assert decide(policy, shell(text)) is None, text


def test_a_package_check_runs_only_in_its_package_and_alone(tmp_path: Path) -> None:
    root, away = tmp_path / "wt", tmp_path / "away"
    (root / "packages" / "app").mkdir(parents=True)
    away.mkdir()
    (root / "escape").symlink_to(away)
    checks = (("packages/app", "npm test"), ("escape", "npm test"))
    policy = Policy(root, ("git add",), checks=checks)
    assert decide(policy, shell("cd packages/app && npm test")) is None
    assert decide(policy, shell("cd packages/app/ && npm test -- --run")) is None
    for text in [
        "cd packages/app && npm test && rm x",
        "cd packages/app && npm test; rm x",
        "cd packages/app && npm test | sh",
        "cd packages/app && npm test > x",
        "cd packages/app && FOO=1 npm test",
        "cd packages/app && npm test $(rm x)",
        "cd packages && npm test",
        "cd . && npm test",
    ]:
        assert decide(policy, shell(text)) == f"`{text}` is not in this step's allow list", text
    assert "outside the worktree" in decide(policy, shell("cd escape && npm test"))
    assert decide(Policy(root, ("git add",)), shell("cd packages/app && npm test")) is not None


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


def test_a_late_call_never_changes_the_accepted_result_or_its_head() -> None:
    trees = iter([Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",)), Worktree(BASE, BASE)])
    st = step()
    st.cfg = dataclasses.replace(st.cfg, observe=lambda: next(trees), checks=("npm test",))
    st.gate.cfg = st.cfg
    accepted = st._handle(tools.SUBMIT, SimpleNamespace(arguments=GOOD))  # noqa: SLF001
    late = st._handle(tools.SUBMIT, SimpleNamespace(arguments={**GOOD, "summary": "Other."}))  # noqa: SLF001
    assert (accepted.result_type, late.result_type) == ("success", "rejected")
    assert (st.run.ending, st.run.head, st.run.payload.summary) == ("result", HEAD, "Added greet().")
    assert [e["accepted"] for e in st.events if e.get("event") == "tool"] == [True, False]


def test_a_turn_on_another_model_voids_even_an_accepted_result_but_a_subagent_model_is_only_logged() -> None:
    def message(model: str, parent: str | None = None) -> SimpleNamespace:
        data = SimpleNamespace(content="", model=model, parent_tool_call_id=parent)
        return SimpleNamespace(type=SimpleNamespace(value="assistant.message"), data=data)

    def accepted() -> sdk_adapter._Step:
        trees = iter([Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",))])
        st = step()
        st.cfg = dataclasses.replace(st.cfg, model="gpt-6-luna", observe=lambda: next(trees), checks=("npm test",))
        st.gate.cfg = st.cfg
        st._handle(tools.SUBMIT, SimpleNamespace(arguments=GOOD))  # noqa: SLF001
        return st

    st = accepted()
    st.on_event(message("gpt-6-luna"))
    st.on_event(message("claude-haiku-5.5", parent="call-1"))
    assert (st.run.ending, st.run.head) == ("result", HEAD)
    assert [e["model"] for e in st.events if e.get("event") == "subagent-model"] == ["claude-haiku-5.5"]
    st.on_event(message("mai-code-1.1-flash"))
    assert (st.run.ending, st.run.payload, st.run.head) == ("error", None, None)
    assert st.run.detail == "wrong model: a turn ran on mai-code-1.1-flash, the step needs gpt-6-luna"
    st = accepted()
    st.on_event(SimpleNamespace(type=SimpleNamespace(value="session.auto_mode_resolved"), data=SimpleNamespace()))
    assert (st.run.ending, st.run.payload, st.run.detail) == ("error", None, "wrong model: the runtime resolved auto")
    st = accepted()
    turn = SimpleNamespace(turn_id="t", model="gpt-6-sol", parent_tool_call_id=None)
    st.on_event(SimpleNamespace(type=SimpleNamespace(value="assistant.turn_start"), data=turn))
    assert (st.run.ending, st.run.detail) == (
        "error",
        "wrong model: a turn ran on gpt-6-sol, the step needs gpt-6-luna",
    )


def test_a_subagent_on_auto_voids_the_step_and_a_runtime_chosen_subagent_model_is_logged() -> None:
    def started(model: str | None, source: str) -> SimpleNamespace:
        data = SimpleNamespace(agent_name="general-purpose", model=model, model_selection_source=source)
        return SimpleNamespace(type=SimpleNamespace(value="subagent.started"), data=data)

    def usage(model: str, parent: str | None = None, *, auto: bool | None = False) -> SimpleNamespace:
        data = SimpleNamespace(model=model, parent_tool_call_id=parent, is_auto=auto)
        return SimpleNamespace(type=SimpleNamespace(value="assistant.usage"), data=data)

    def accepted() -> sdk_adapter._Step:
        trees = iter([Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",))])
        st = step()
        st.cfg = dataclasses.replace(st.cfg, model="gpt-6-luna", observe=lambda: next(trees), checks=("npm test",))
        st.gate.cfg = st.cfg
        st._handle(tools.SUBMIT, SimpleNamespace(arguments=GOOD))  # noqa: SLF001
        return st

    st = accepted()
    st.on_event(started("claude-haiku-5.5", "agent_definition_default"))
    st.on_event(started("mai-code-1.1-flash", "runtime_policy"))  # "runtime policy, Auto mode, or an experiment"
    st.on_event(usage("gpt-6-luna", auto=None))
    st.on_event(usage("claude-haiku-5.5", parent="call-1"))
    assert (st.run.ending, st.run.head) == ("result", HEAD)
    assert [(e["model"], e["source"]) for e in st.events if e.get("event") == "subagent-start"] == [
        ("claude-haiku-5.5", "agent_definition_default"),
        ("mai-code-1.1-flash", "runtime_policy"),
    ]
    assert st.subagent_models == {"claude-haiku-5.5"}  # a start alone never excuses a model in the final usage
    st.on_event(started("auto", "explicit_override"))
    assert (st.run.ending, st.run.payload, st.run.detail) == ("error", None, "wrong model: a subagent ran on auto")

    for event, detail in [
        (usage("mai-code-1.1-flash", parent="call-2", auto=True), "wrong model: a subagent call ran on auto"),
        (usage("gpt-6-luna", auto=True), "wrong model: a call ran on auto"),
        (usage("mai-code-1.1-flash"), "wrong model: a turn ran on mai-code-1.1-flash, the step needs gpt-6-luna"),
    ]:
        st = accepted()
        st.on_event(event)
        assert (st.run.ending, st.run.payload, st.run.detail) == ("error", None, detail)
    st = accepted()
    message = SimpleNamespace(content="", model="auto", parent_tool_call_id="call-1")
    st.on_event(SimpleNamespace(type=SimpleNamespace(value="assistant.message"), data=message))
    assert (st.run.ending, st.run.detail) == ("error", "wrong model: a subagent ran on auto")


def test_usage_naming_an_unattributed_model_voids_the_result_and_an_unnamed_model_never_starts(monkeypatch) -> None:
    usage = {"models": {"gpt-6-luna": {}, "claude-haiku-5.5": {}, "mai-code-1.1-flash": {}}}
    assert sdk_adapter.unexpected_models({}, usage, "gpt-6-luna", {"claude-haiku-5.5"}) == ["mai-code-1.1-flash"]
    assert sdk_adapter.unexpected_models({}, {"models": {"gpt-6-luna": {}}}, "gpt-6-luna", set()) == []
    before = {"models": {"claude-haiku-5.5": {"tokens": 100}, "gpt-6-luna": {"tokens": 50}}}
    resumed = {"models": {"claude-haiku-5.5": {"tokens": 100}, "gpt-6-luna": {"tokens": 90}}}
    assert sdk_adapter.unexpected_models(before, resumed, "gpt-6-luna", set()) == []
    grown = {"models": {**resumed["models"], "claude-haiku-5.5": {"tokens": 130}}}
    assert sdk_adapter.unexpected_models(before, grown, "gpt-6-luna", set()) == ["claude-haiku-5.5"]
    assert sdk_adapter.unexpected_models({"error": "RuntimeError"}, grown, "gpt-6-luna", set()) == []
    monkeypatch.setattr(sdk_adapter, "CopilotClient", lambda **_: pytest.fail("no runtime may start"))
    run = asyncio.run(sdk_adapter.run(step().cfg))
    assert (run.ending, run.detail) == ("error", "wrong model: the step names no model (TD-32)")


def test_usage_is_read_once_more_and_a_still_unread_read_names_why_the_check_cannot_run(monkeypatch) -> None:
    class Usage:
        def __init__(self, fails: int) -> None:
            self.fails = fails

        async def get_metrics(self) -> SimpleNamespace:
            if self.fails:
                self.fails -= 1
                raise RuntimeError
            tokens = SimpleNamespace(input_tokens=5, output_tokens=7)
            luna = SimpleNamespace(total_nano_aiu=2e9, usage=tokens)
            return SimpleNamespace(total_nano_aiu=2e9, model_metrics={"gpt-6-luna": luna})

    monkeypatch.setattr(sdk_adapter, "USAGE_PAUSE", 0)
    once = SimpleNamespace(rpc=SimpleNamespace(usage=Usage(1)))
    assert asyncio.run(sdk_adapter._usage_read(once, "gpt-6-luna"))["models"]["gpt-6-luna"]["tokens"] == 12  # noqa: SLF001
    twice = SimpleNamespace(rpc=SimpleNamespace(usage=Usage(2)))
    after = asyncio.run(sdk_adapter._usage_read(twice, "gpt-6-luna"))  # noqa: SLF001
    assert after == {"error": "RuntimeError"}
    assert sdk_adapter.unread({}, after) == "the usage at the step's end could not be read (RuntimeError)"
    before = sdk_adapter.unread({"error": "TimeoutError"}, {"models": {}})
    assert before == "the usage before the resumed turn could not be read (TimeoutError)"
    assert sdk_adapter.unread({}, {}) == sdk_adapter.unread({}, {"models": {}}) == ""


def test_a_session_that_opened_but_could_not_send_still_needs_its_usage_read(monkeypatch) -> None:
    class Session:
        def __init__(self) -> None:
            self.rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=self.metrics))

        async def metrics(self) -> None:
            raise RuntimeError

        async def send(self, *_a, **_k) -> None:
            raise ConnectionError

    class Client:
        opens = True

        def __init__(self, **_k) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **_k) -> Session:
            if not Client.opens:
                raise ConnectionError
            return Session()

    async def teardown(*_a) -> Termination:
        return Termination(confirmed=True)

    monkeypatch.setattr(sdk_adapter, "CopilotClient", Client)
    monkeypatch.setattr(sdk_adapter, "cli_path", lambda: "copilot")
    monkeypatch.setattr(sdk_adapter, "_teardown", teardown)
    monkeypatch.setattr(sdk_adapter, "USAGE_PAUSE", 0)
    cfg = dataclasses.replace(step().cfg, model="gpt-6-luna", resume=False)
    run = asyncio.run(sdk_adapter.run(cfg))
    assert (run.ending, run.usage_unread) == ("error", "the usage at the step's end could not be read (RuntimeError)")
    Client.opens = False  # nothing opened, so no model ran
    assert asyncio.run(sdk_adapter.run(cfg)).usage_unread == ""


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
