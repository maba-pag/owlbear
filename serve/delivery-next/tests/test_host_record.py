import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from owlbear_delivery_next.runtimes import host_record

SINCE = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)
TOOLS = ["bash", "view", "task", "owlbear-step-ab/submit_result"]


def _write(  # noqa: PLR0913
    state: Path, sid: str, folder: Path, *, at: datetime = SINCE, agent: str = "owlbear-builder", extra=()
):
    events = [
        {"type": "session.start", "data": {"startTime": at.isoformat(), "context": {"cwd": str(folder)}}},
        {"type": "subagent.selected", "data": {"agentName": agent, "tools": TOOLS}},
        *extra,
    ]
    path = state / sid / "events.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events) + '{"type": "assistant.mess')
    os.utime(path, (at.timestamp() + 60, at.timestamp() + 60))
    return path


def test_the_steps_record_is_the_one_in_its_folder_after_launch_that_selected_its_agent(tmp_path: Path) -> None:
    state, folder = tmp_path / "state", tmp_path / "wt"
    folder.mkdir()
    started = {"toolCallId": "call_1", "agentName": "explore", "model": "gpt-5.6-luna"}
    done = started | {"totalTokens": 6958, "totalToolCalls": 1, "durationMs": 2929}
    _write(
        state,
        "a",
        folder,
        extra=[{"type": "subagent.started", "data": started}, {"type": "subagent.completed", "data": done}],
    )
    _write(state, "old", folder, at=SINCE - timedelta(hours=1))
    _write(state, "other-folder", tmp_path)
    _write(state, "other-agent", folder, agent="owlbear-reviewer")

    record = host_record.read(folder, SINCE, "owlbear-builder", state)

    assert (record.found, record.tools) == (True, TOOLS)
    (k1, s1), (k2, s2) = record.subagents
    assert (k1, s1.tool_call_id, s1.agent_name, s1.model) == ("subagent.started", "call_1", "explore", "gpt-5.6-luna")
    assert (k2, s2.total_tokens, s2.total_tool_calls, s2.duration) == (
        "subagent.completed",
        6958,
        1,
        timedelta(milliseconds=2929),
    )


def test_no_record_or_two_records_are_no_answer(tmp_path: Path) -> None:
    state, folder = tmp_path / "state", tmp_path / "wt"
    folder.mkdir()
    assert host_record.read(folder, SINCE, "owlbear-builder", state).why == "no host record"
    _write(state, "a", folder)
    _write(state, "b", folder)
    record = host_record.read(folder, SINCE, "owlbear-builder", state)
    assert (record.found, record.why) == (False, "2 host records match the step")


def test_only_tools_beyond_the_allowlist_and_the_runtimes_own_are_unexpected() -> None:
    given = ["bash", "skill", "sql", "task_complete", "parallel", "uv-init", "owlbear-browser-pilot/navigate"]
    assert host_record.unexpected(given, ["bash"]) == ["owlbear-browser-pilot/navigate", "uv-init"]
