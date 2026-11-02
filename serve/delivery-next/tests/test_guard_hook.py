"""The shell guard's warnings in a step's session (#864): the pre-tool hook, its records, and the level it judges at.

D-01M6DX04FRP680Z4GGHK5B9VRC: a warning adds context and lets the command run; the permission callback alone refuses.
"""

import json

import pytest

from owlbear_delivery_next.change_contracts import git_reading, shell_walk
from owlbear_delivery_next.change_contracts.permissions import BYPASS
from owlbear_delivery_next.change_flow import status
from owlbear_delivery_next.local_system import shell_parse
from owlbear_delivery_next.runtimes import guard_hook
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, resolve

COMMIT = "git commit --no-verify -m x"
FOUND = f"`{COMMIT}` uses --no-verify, {BYPASS}"


def test_a_warned_command_gets_only_added_context_one_warned_record_and_runs(through_step) -> None:
    got = through_step(COMMIT, "lenient")
    assert (got.outcome, got.out) == ("warned", {"additionalContext": guard_hook.WARNING.format(reason=FOUND)})
    assert "fix the cause or ask" in got.said
    assert "guard_level" not in got.said
    assert "lenient" not in got.said
    assert [{k: v for k, v in e.items() if k != "at"} for e in got.events] == [
        {"event": "warned", "kind": "shell", "request": [COMMIT], "reason": FOUND}
    ]
    assert (got.run.denials, got.run.denied, got.run.wrong) == ([], {}, {})  # no wrong tool choice either
    assert status._SAID["warned"](got.events[0]) == f'warned "{COMMIT}"'  # noqa: SLF001


def test_a_refused_command_is_left_to_the_callback_and_nothing_is_warned(through_step) -> None:
    got = through_step(COMMIT, "strict")
    assert (got.outcome, got.said, got.out) == ("refused", f"Denied: {FOUND}", None)
    assert [e["event"] for e in got.events] == ["denied"]
    assert got.run.wrong == {}  # a refused bypass is still no wrong tool choice


def test_an_allowed_command_and_other_tools_get_nothing_from_the_hook(through_step) -> None:
    got = through_step("git status", "lenient")
    assert (got.outcome, got.out, got.events) == ("allowed", None, [])
    assert got.step.pre_tool({"toolName": "view", "toolArgs": {"path": "x"}}, {}) is None
    assert got.events == []


def test_a_warned_command_holding_a_token_is_masked_in_every_record(through_step) -> None:
    token = "ghp_" + "Z9" * 18
    got = through_step(f"GH_TOKEN={token} {COMMIT}", "lenient")
    assert got.outcome == "warned"
    assert token not in json.dumps(got.events)
    assert token not in got.said


def test_a_failing_hook_records_its_error_and_stops_the_step_and_the_callback_still_decides(
    through_step, monkeypatch
) -> None:
    def broken(*_a: object, **_k: object) -> None:
        msg = "the reader broke"
        raise RuntimeError(msg)

    monkeypatch.setattr(guard_hook, "judge", broken)
    got = through_step(COMMIT, "lenient")
    assert (got.outcome, got.out) == ("allowed", None)  # the callback judged it at lenient: a warning, so it runs
    failed = [e for e in got.events if e["event"] == "hook-failed"]
    assert len(failed) == 1
    assert "Traceback" in failed[0]["error"]
    assert "RuntimeError: the reader broke" in failed[0]["error"]
    assert got.step.gate.done
    assert got.run.ending == "error"
    assert "the shell guard's warning hook failed" in got.run.detail
    assert "the reader broke" in got.run.detail


@pytest.mark.parametrize("level", ["lenient", "off"])
@pytest.mark.parametrize(
    ("text", "counted"), [("docker compose up > log", True), (COMMIT, False), (f"{COMMIT}; touch x", False)]
)
def test_a_read_only_steps_writes_stay_refused_through_the_session_at_lowered_levels(
    through_step, text: str, *, counted: bool, level: str
) -> None:
    got = through_step(text, level, write=False)
    assert (got.outcome, got.out) == ("refused", None)
    assert "read-only step" in got.said
    assert got.run.wrong == ({"denied": 1} if counted else {})  # a bypass it names is no wrong tool choice


def test_off_reads_no_command_in_a_write_steps_session(through_step, monkeypatch) -> None:
    def fail(*_a: object, **_k: object) -> None:
        raise AssertionError

    monkeypatch.setattr(shell_parse, "parse", fail)
    monkeypatch.setattr(git_reading, "bypass", fail)
    monkeypatch.setattr(shell_walk.Walk, "commands", fail)
    got = through_step(COMMIT, "off")
    assert (got.outcome, got.out, got.events, got.run.denials) == ("allowed", None, [], [])


def test_the_level_stays_the_one_the_worker_was_built_with(through_step, monkeypatch) -> None:
    switches = {"load_user_instructions": False, "load_user_skills": False, "load_user_memory": False}
    built = roles.user_config(resolve(GlobalLayer(**switches, guard_level="strict"), Layer()))
    lowered = roles.user_config(resolve(GlobalLayer(**switches, guard_level="strict"), Layer(guard_level="off")))
    assert lowered.guard == "off"
    monkeypatch.setattr(roles, "user_config", lambda *_a: lowered)  # the owner lowers it while the step runs
    got = through_step(COMMIT, user=built)
    assert (got.outcome, got.out) == ("refused", None)
