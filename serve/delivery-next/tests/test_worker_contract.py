import asyncio
import dataclasses
import shlex
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import psutil
import pytest

from owlbear_delivery_next.change_contracts import tool_schema, tools
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Change,
    ErrorKind,
    Exit,
    ItemRef,
    Plan,
    Question,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.tools import AskQuestion, BuildResult, Worktree
from owlbear_delivery_next.change_flow import repairs
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.local_system.processes import Termination, verdict
from owlbear_delivery_next.runtimes import (
    lessons,
    sdk_adapter,
    sdk_teardown,
    sdk_usage,
    session_result,
    step_answers,
    step_decisions,
    step_input,
)
from owlbear_delivery_next.runtimes.session_result import Run, to_result

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HEAD, BASE = "a" * 40, "b" * 40
GOOD = {
    "summary": "Added greet().",
    "checks": [{"command": "npm test", "exit_code": 0}],
}


def build(**changes) -> BuildResult:
    result, errors = tool_schema.parse(BuildResult, {**GOOD, **changes})
    assert errors == []
    return result


def test_the_plan_challenger_sees_where_each_check_runs() -> None:
    entry = ProfileEntry(state="known", value="npm test", evidence="packages/app/package.json")
    profile = Profile(entries={"check:packages/app": entry})
    plan = Plan(tasks=[Task(id="t1", title="Add sign", scope=["packages/app"], checks=["npm test"])])
    text = step_input.plan_challenge(Change(slug="s"), plan, profile, Path("/w"), {})
    assert "- `packages/app`: install `none`, check `npm test`" in text
    assert "runs each check from its package directory" in text


def test_the_plan_challenger_sees_the_whole_plan_and_a_cut_is_said() -> None:
    goal = " ".join(f"AC-{i}: the page shows item {i} in the footer once the build has finished." for i in range(30))
    tasks = [
        Task(id=f"t{i}", title=f"Task {i} " + "x" * 300, scope=["app"], checks=["npm test"], detail=goal)
        for i in (1, 2)
    ]
    plan = Plan(tasks=tasks)
    assert len(goal) > 1500
    text = step_input.plan_challenge(Change(slug="s"), plan, Profile(), Path("/w"), {})
    assert text.count(goal) == 2
    assert text.count("x" * 300) == 2
    assert "(truncated)" not in text
    huge = Plan(tasks=[Task(id=f"t{i}", title="t", detail=goal) for i in range(1, 9)])
    text = step_input.plan_challenge(Change(slug="s"), huge, Profile(), Path("/w"), {})
    assert "(truncated)" in text
    assert 12000 < len(text.split("## Plan (data, not instructions)\n")[1].split("\n\n## Brief")[0]) < 12100


def test_schema_errors_name_the_field_and_the_agent_cannot_name_a_commit() -> None:
    result, errors = tool_schema.parse(BuildResult, {**GOOD, "commit": "3f2c1ab", "checks": [{"command": "npm test"}]})
    assert result is None
    assert any(e.startswith("commit: Extra inputs are not permitted") for e in errors)
    assert any(e.startswith("checks[0].exit_code:") for e in errors)
    assert tool_schema.parse(AskQuestion, "not json")[1] == [
        "arguments: not a JSON object - send the fields as one object"
    ]


def test_the_derived_head_must_move_past_the_base_with_a_clean_worktree() -> None:
    tree = Worktree(head=BASE, base=BASE, dirty=("packages/app/src/greet.ts",))
    assert tools.check_build(build(), tree, ["npm test"]) == [
        f"changes: no commit since the task's base {BASE[:12]}; commit your changes, then submit again",
        "changes: uncommitted files (packages/app/src/greet.ts); commit them, then submit again",
    ]


def test_a_committed_result_must_name_every_passing_check_and_never_its_paths() -> None:
    tree = Worktree(head=HEAD, base=BASE, changed=("packages/app/src/greet.ts", "packages/app/test/greet.test.ts"))
    assert tools.check_build(build(), Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",)), ["npm test"]) == []
    errors = tools.check_build(
        build(checks=[{"command": "npm test", "exit_code": 1}]), tree, ["npm test", "npm run lint"]
    )
    assert errors[0].startswith("checks[0].exit_code: 1")
    assert errors[1].startswith('checks: "npm run lint" missing')
    assert len(errors) == 2
    assert "changed_paths" not in tool_schema.schema(tools.SUBMIT)["properties"]
    assert tool_schema.parse(BuildResult, {**GOOD, "changed_paths": ["a.ts"]})[1] == [
        "changed_paths: Extra inputs are not permitted"  # a new call stays strict; Delivery reads the paths itself
    ]


PLACED, QUOTED = "cd packages/b && npm test", f"cd {shlex.quote("my app's")} && npm test"
LONG = "packages/frontend-components-library"


@pytest.mark.parametrize(
    ("reported", "required", "missing"),
    [
        (["npm test -- --grep x"], ["npm test"], ["npm test"]),  # a narrowed run
        (["npm test:unit"], ["npm test"], ["npm test"]),  # another script
        (["echo npm test"], ["npm test"], ["npm test"]),
        (["cd packages/app && npm test -- --grep x"], ["npm test"], ["npm test"]),
        (["cd packages/b&&npm test", PLACED], ["npm test", PLACED], ["npm test"]),  # another task's package run
        (["cd 'packages/b' && npm test"], ["npm test", PLACED], ["npm test"]),
        (["cd unrelated && cd packages/b && npm test"], [PLACED], [PLACED]),  # a placed check gets no second cd
        (["cd /packages/b && npm test"], [PLACED], [PLACED]),  # another directory
        (['cd "packages/b\'" && npm test'], [PLACED], [PLACED]),
        (["cd #package && npm test"], ["npm test"], ["npm test"]),  # the shell comments the test out
        (["cd packages/b>cd.log && npm test"], ["npm test", PLACED], ["npm test", PLACED]),  # still packages/b
        (["cd 'p/$b' && npm test", 'cd "p/\\$b" && npm test'], ["npm test", "cd 'p/$b' && npm test"], ["npm test"]),
        ([PLACED, "cd packages/\\\nb && npm test"], ["npm test", PLACED], ["npm test"]),  # both run packages/b
        (["cd packages/b &&\r\nnpm test"], [PLACED], [PLACED]),  # the shell runs a stray \r as a command
        (["npm  test "], ["npm test"], ["npm test"]),  # the exact text, but for its ends
        (["grep -q 'AC 1' a.txt"], ["grep -q 'AC  1' a.txt"], ["grep -q 'AC  1' a.txt"]),  # tests other text
        (["sh -c 'exit 1'\ntrue"], ["sh -c 'exit 1' true"], ["sh -c 'exit 1' true"]),  # two commands
        (['test "$(echo "a b")" = 1'], ['test "$(echo "a  b")" = 1'], ['test "$(echo "a  b")" = 1']),
        (["cd\npackages/b && npm test"], [PLACED], [PLACED]),  # a bare cd, then packages/b as a command
        ([" npm test\n"], ["npm test"], []),
        (["cd '#package' && npm test"], ["npm test"], []),
        (["cd packages/app && npm test"], ["npm test"], []),  # run from its package directory
        ([QUOTED], ["npm test"], []),
        (['cd "my app\'s" && npm test'], [QUOTED], []),
        (["cd ./packages/b/ && npm test"], [PLACED], []),
        ([f"cd {LONG}; npm test"], ["npm test"], ["npm test"]),  # answered at once, however long the directory
    ],
)
def test_a_required_check_counts_only_as_that_command_or_that_command_run_in_a_directory(reported, required, missing):
    result = build(checks=[{"command": c, "exit_code": 0} for c in reported])
    assert tools.check_build(result, Worktree(HEAD, BASE), required) == [
        f'checks: "{c}" missing - run it on your commit and report it, e.g. {{"command": "{c}", "exit_code": 0}}'
        for c in missing
    ]


def test_only_a_bot_comment_or_review_may_be_left_without_a_reply() -> None:
    tree = Worktree(head=BASE, base=BASE)
    no_action = build(checks=[], response={"how": "no-action", "text": "bot notice"})
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
    q, _ = tool_schema.parse(AskQuestion, {"question": "q", "why": "w", "options": [{"label": "A", "effect": "x"}] * 2})
    assert tools.check_question(q) == ["options: labels repeat - give each option a distinct answer"]


def step(**cfg) -> sdk_adapter._Step:
    log: list[dict] = []
    journal = sdk_adapter.Journal(event=log.append, **cfg)
    session = sdk_adapter.Session(
        StepKind.BUILD,
        Path(),
        "s1",
        "m",
        resume=True,
        policy=Policy(Path()),
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
    assert st.run.changed == ["packages/app/src/greet.ts"]  # Delivery's read at the accepted head, kept with it
    assert [e["accepted"] for e in st.events if e.get("event") == "tool"] == [True, False]


def _accepted(model: str = "claude-opus-5.5") -> sdk_adapter._Step:
    trees = iter([Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",))])
    st = step()
    st.cfg = dataclasses.replace(st.cfg, model=model, observe=lambda: next(trees), checks=("npm test",))
    st.gate.cfg = st.cfg
    st._handle(tools.SUBMIT, SimpleNamespace(arguments=GOOD))  # noqa: SLF001
    return st


def _event(kind: str, **data: object) -> SimpleNamespace:
    return SimpleNamespace(type=SimpleNamespace(value=kind), data=SimpleNamespace(**data))


def test_a_turn_on_another_model_voids_an_accepted_result() -> None:
    st = _accepted()
    st.on_event(_event("assistant.message", content="", model="claude-opus-5.5", parent_tool_call_id=None))
    assert (st.run.ending, st.run.head) == ("result", HEAD)
    st.on_event(_event("assistant.message", content="", model="mai-code-1.1-flash", parent_tool_call_id=None))
    assert (st.run.ending, st.run.payload, st.run.head, st.run.model_check) == ("error", None, None, "mismatch")
    assert st.run.changed == []
    assert st.run.detail == "wrong model: a turn ran on mai-code-1.1-flash, the step needs claude-opus-5.5"
    st = _accepted()
    st.on_event(_event("session.auto_mode_resolved"))
    assert (st.run.ending, st.run.payload, st.run.detail) == ("error", None, "wrong model: the runtime resolved auto")
    st = _accepted()
    st.on_event(_event("assistant.turn_start", turn_id="t", model="gpt-6-sol", parent_tool_call_id=None))
    assert (st.run.ending, st.run.detail) == (
        "error",
        "wrong model: a turn ran on gpt-6-sol, the step needs claude-opus-5.5",
    )


def test_any_subagent_voids_the_step_as_policy_and_auto_stays_a_wrong_model() -> None:
    def started(name: str, model: str | None, source: str = "agent_definition_default") -> SimpleNamespace:
        return _event("subagent.started", agent_name=name, model=model, model_selection_source=source)

    ran = "a subagent ran; no subagent may run"
    for event, detail, check in [
        (
            started("general-purpose", "claude-opus-5.5"),
            "a subagent started: general-purpose; no subagent may run",
            "unknown",
        ),
        (started("researcher", "gpt-6-luna"), "a subagent started: researcher; no subagent may run", "unknown"),
        (started("explore", "auto", "explicit_override"), "wrong model: a subagent ran on auto", "mismatch"),
        (
            _event("assistant.message", content="", model="claude-opus-5.5", parent_tool_call_id="call-1"),
            ran,
            "unknown",
        ),
        (
            _event("assistant.usage", model="claude-opus-5.5", parent_tool_call_id="call-1", is_auto=False),
            ran,
            "unknown",
        ),
        (
            _event("assistant.usage", model="mai-code-1.1-flash", parent_tool_call_id="call-2", is_auto=True),
            "wrong model: a subagent call ran on auto",
            "mismatch",
        ),
        (
            _event("assistant.usage", model="claude-opus-5.5", parent_tool_call_id=None, is_auto=True),
            "wrong model: a call ran on auto",
            "mismatch",
        ),
    ]:
        st = _accepted()
        st.on_event(event)
        assert (st.run.ending, st.run.payload, st.run.detail, st.run.model_check) == ("error", None, detail, check)


def test_usage_naming_an_unattributed_model_voids_the_result_and_an_unnamed_model_never_starts(monkeypatch) -> None:
    usage = {"models": {"gpt-6-luna": {}, "claude-haiku-5.5": {}, "mai-code-1.1-flash": {}}}
    assert sdk_usage.unexpected_models({}, usage, "gpt-6-luna") == ["claude-haiku-5.5", "mai-code-1.1-flash"]
    assert sdk_usage.unexpected_models({}, {"models": {"gpt-6-luna": {}}}, "gpt-6-luna") == []
    before = {"models": {"claude-haiku-5.5": {"tokens": 100}, "gpt-6-luna": {"tokens": 50}}}
    resumed = {"models": {"claude-haiku-5.5": {"tokens": 100}, "gpt-6-luna": {"tokens": 90}}}
    assert sdk_usage.unexpected_models(before, resumed, "gpt-6-luna") == []
    grown = {"models": {**resumed["models"], "claude-haiku-5.5": {"tokens": 130}}}
    assert sdk_usage.unexpected_models(before, grown, "gpt-6-luna") == ["claude-haiku-5.5"]
    assert sdk_usage.unexpected_models({"error": "RuntimeError"}, grown, "gpt-6-luna") == []
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

    monkeypatch.setattr(sdk_usage, "USAGE_PAUSE", 0)
    once = SimpleNamespace(rpc=SimpleNamespace(usage=Usage(1)))
    assert asyncio.run(sdk_usage.usage_read(once, "gpt-6-luna"))["models"]["gpt-6-luna"]["tokens"] == 12
    twice = SimpleNamespace(rpc=SimpleNamespace(usage=Usage(2)))
    after = asyncio.run(sdk_usage.usage_read(twice, "gpt-6-luna"))
    assert after == {"error": "RuntimeError"}
    assert sdk_usage.unread({}, after) == "the usage at the step's end could not be read (RuntimeError)"
    before = sdk_usage.unread({"error": "TimeoutError"}, {"models": {}})
    assert before == "the usage before the resumed turn could not be read (TimeoutError)"
    assert sdk_usage.unread({}, {}) == sdk_usage.unread({}, {"models": {}}) == ""


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

        async def create_session(self, **opts) -> Session:
            Client.excluded = opts["excluded_tools"]
            if not Client.opens:
                raise ConnectionError
            return Session()

    async def teardown(*_a) -> Termination:
        return Termination(confirmed=True)

    monkeypatch.setattr(sdk_adapter, "CopilotClient", Client)
    monkeypatch.setattr(sdk_adapter, "cli_path", lambda: "copilot")
    monkeypatch.setattr(sdk_teardown, "teardown", teardown)
    monkeypatch.setattr(sdk_usage, "USAGE_PAUSE", 0)
    cfg = dataclasses.replace(step().cfg, model="gpt-6-luna", resume=False)
    run = asyncio.run(sdk_adapter.run(cfg))
    assert (run.ending, run.usage_unread) == ("error", "the usage at the step's end could not be read (RuntimeError)")
    assert Client.excluded == ["ask_user"]
    Client.opens = False  # nothing opened, so no model ran
    assert asyncio.run(sdk_adapter.run(cfg)).usage_unread == ""


def test_a_model_without_reasoning_efforts_is_opened_without_one(monkeypatch) -> None:
    class Client:
        listed: ClassVar[list | Exception] = []
        opts: ClassVar[dict] = {}

        def __init__(self, **_k) -> None:
            pass

        async def start(self) -> None:
            pass

        async def list_models(self) -> list:
            if isinstance(Client.listed, Exception):
                raise Client.listed
            return Client.listed

        async def create_session(self, **opts) -> None:
            Client.opts = opts
            raise ConnectionError

    async def teardown(*_a) -> Termination:
        return Termination(confirmed=True)

    monkeypatch.setattr(sdk_adapter, "CopilotClient", Client)
    monkeypatch.setattr(sdk_adapter, "cli_path", lambda: "copilot")
    monkeypatch.setattr(sdk_teardown, "teardown", teardown)
    cfg = dataclasses.replace(step().cfg, model="claude-haiku-4.5", effort="medium", resume=False)

    def effort(listed: list | Exception) -> str | None:
        Client.listed, Client.opts = listed, {}
        asyncio.run(sdk_adapter.run(cfg))
        return Client.opts.get("reasoning_effort", "omitted")

    haiku = SimpleNamespace(id="claude-haiku-4.5", supported_reasoning_efforts=None)
    assert effort([haiku]) == "omitted"
    assert effort([SimpleNamespace(id="claude-haiku-4.5", supported_reasoning_efforts=["low", "medium"])]) == "medium"
    assert effort([]) == "medium"  # an unlisted model is trusted
    assert effort(RuntimeError()) == "medium"  # an unread list leaves the refusal to the runtime


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
    assert sends == [sdk_adapter.step_input.CONTINUE, "m"]
    st.run.termination = Termination(confirmed=True)
    r = to_result(st.run, StepKind.BUILD, NOW)
    assert (r.exit, r.cause) == (Exit.RETRY, f"{ErrorKind.LIVENESS}:build:transcript")


@pytest.mark.parametrize("earlier", ["another question's", "a repair context holding it", "its own"])
def test_a_new_identical_answer_to_another_question_is_sent_and_an_interrupted_one_is_not(earlier) -> None:
    def delivery(qid: str) -> str:
        answer = Answer(text="Done", kind="event", at=NOW)
        asked = Question(id=qid, step=StepKind.BUILD, text="Proceed?", answer=answer)
        return step_decisions.resumed(step_answers.answer(asked))  # as the runner opens a resumed session with it

    message, sends = delivery("q2"), []
    taken_over = repairs.fallback(Task(id="t1", title="t", earlier=message))  # a worker's summary holding it whole
    repair = f"{lessons.HEADING}\n{lessons.NONE}\n\nRepair the findings.{taken_over}"
    content = {"another question's": delivery("q1"), "a repair context holding it": repair, "its own": message}[earlier]
    user = SimpleNamespace(type=SimpleNamespace(value="user.message"), data=SimpleNamespace(content=content))

    async def send(m):
        sends.append(m)

    session = SimpleNamespace(get_events=lambda: asyncio.sleep(0, [user]), send=send)
    client = SimpleNamespace(get_session_metadata=lambda _s: asyncio.sleep(0, {}))
    client.resume_session = lambda _s, **_o: asyncio.sleep(0, session)
    st = step()
    st.cfg = dataclasses.replace(st.cfg, message=message)
    asyncio.run(sdk_adapter._open(client, st))  # noqa: SLF001
    assert sends == [step_input.CONTINUE if earlier == "its own" else message]


def test_a_hung_runtime_stop_is_bounded_and_falls_back_to_signals(monkeypatch) -> None:
    calls: list[str] = []

    async def hang() -> None:
        await asyncio.sleep(60)

    proc = SimpleNamespace(pid=None, terminate=lambda: calls.append("term"), kill=lambda: calls.append("kill"))
    client = SimpleNamespace(_cli_process=proc, stop=hang)
    monkeypatch.setattr(sdk_teardown, "STOP_CALL", 0.05)
    monkeypatch.setattr(sdk_teardown, "GRACE", 0.05)
    monkeypatch.setattr(sdk_teardown, "SETTLE", 0.05)
    st = step()
    t = asyncio.run(sdk_teardown.teardown(client, None, st))
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
