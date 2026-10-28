"""Retro's prepared evidence (#715 gate H3): what the judge reads reaches it, bounded, masked and checkable."""

import gzip
import json

from owlbear_delivery_next.improvement import retro_evidence, retro_units
from owlbear_delivery_next.improvement import retro_segments as seg

SECRET = "ghp_" + "a" * 36


def _captured(session, events, outputs=(), **kept):
    folder = retro_units.folder(session)
    (folder / "outputs").mkdir(parents=True, exist_ok=True)
    (folder / "log.jsonl.gz").write_bytes(gzip.compress("".join(json.dumps(e) + "\n" for e in events).encode()))
    (folder / "sidecar.json").write_text(json.dumps({"session": session, "outputs": list(outputs)}))
    for name, body in kept.items():
        (folder / "outputs" / f"{name}.gz").write_bytes(gzip.compress(body.encode()))


def _event(kind, **data):
    return {"type": kind, "data": data}


def _turn(ask, call_id, saved, answer):
    return [
        _event("user.message", content=ask),
        _event("tool.execution_start", toolName="bash", toolCallId=call_id, arguments={"command": "uv run test"}),
        _event("tool.execution_complete", toolCallId=call_id, success=True, result={"content": f"Saved to: {saved}"}),
        _event("assistant.message", content=answer),
    ]


def test_a_kept_outputs_decisive_result_and_a_later_recovery_reach_the_judge_and_a_missing_one_is_marked(tmp_path):
    kept, gone = str(tmp_path / "copilot-tool-output-1.txt"), str(tmp_path / "copilot-tool-output-2.txt")
    events = [
        *_turn("make the tests pass", "c1", kept, "all green, done"),
        *_turn("are you sure?", "c2", gone, "I recovered: the parser now handles empty input"),
    ]
    outputs = [{"path": kept, "state": "kept"}, {"path": gone, "state": "missing"}]
    _captured("s1", events, outputs, **{"copilot-tool-output-1.txt": "...\n3 failed, 9 passed\n"})

    got = seg.prepare(["s1"], "the chat ended", per_turn=True)

    first, second = got.parts
    assert (first.ref, second.ref) == ("s1.p1", "s2.p1")
    assert "3 failed, 9 passed" in first.text
    assert "I recovered" in first.later
    assert first.later.endswith("outcome: the chat ended")
    assert "[output copilot-tool-output-2.txt: missing]" in second.text
    rests = seg.verify(
        {"refs": ["s2.e7"], "quotes": ["copilot-tool-output-2.txt: missing"], "rests_on_gap": True}, got.parts
    )
    assert rests["status"] == "unknown"


def test_a_later_turns_kept_test_result_reaches_an_earlier_turns_later_course(tmp_path):
    early, late = str(tmp_path / "copilot-tool-output-1.txt"), str(tmp_path / "copilot-tool-output-2.txt")
    events = [*_turn("make the tests pass", "c1", early, "done"), *_turn("ship it", "c2", late, "shipped")]
    outputs = [{"path": early, "state": "kept"}, {"path": late, "state": "kept"}]
    bodies = {"copilot-tool-output-1.txt": "12 passed\n", "copilot-tool-output-2.txt": "...\n5 failed, 400 passed\n"}
    _captured("s1", events, outputs, **bodies)

    first, _ = seg.prepare(["s1"], "the chat ended", per_turn=True).parts

    assert "bash test result: 5 failed, 400 passed; Saved to:" in first.later


def test_a_changes_first_session_sees_what_its_shorter_second_session_did_later_and_not_the_reverse():
    _captured("s-a", [_event("assistant.message", content=f"step {i}") for i in range(5)])
    found = [_event("assistant.message", content="the reviewer found the build broken")]
    _captured("s-b", [*found, _event("assistant.message", content="fixed")])

    first, second = seg.prepare(["s-a", "s-b"], "the Change ended done").parts

    assert "the reviewer found the build broken" in first.later
    assert "step 4" not in second.later


def test_a_chats_outcome_is_its_main_agents_last_word_never_a_subagents():
    events = [
        _event("assistant.message", content="the main agent is done"),
        {"type": "assistant.message", "agentId": "sub-1", "data": {"content": "a subagent's report"}},
        _event("assistant.message", content="a nested reply", parentToolCallId="t1"),
    ]
    _captured("s1", events)
    assert retro_evidence.last_said("s1") == "the main agent is done"


def test_parts_are_bounded_and_masked_and_only_quotes_found_in_the_cited_text_survive():
    events = [_event("user.message", content="go")]
    for i in range(40):
        events += [
            _event("tool.execution_start", toolName="bash", toolCallId=f"c{i}", arguments={"command": SECRET}),
            _event("tool.execution_complete", toolCallId=f"c{i}", success=False, result={"content": "x" * 9000}),
        ]
    _captured("s1", events)

    got = seg.prepare(["s1"], "merged", low=3)

    assert len(got.parts) > 1
    assert all(len(p.text) <= seg.PART and len(p.later) <= seg.LATER for p in got.parts)
    assert all(SECRET not in p.text + p.later for p in got.parts)
    assert got.parts[0].first == 4
    assert "chars omitted]" in got.parts[0].text
    finding = {"refs": ["s1.e4"], "quotes": ["result bash failed", "never said"]}
    checked = seg.verify(finding, got.parts)
    assert (checked["quotes"], checked["status"]) == (["result bash failed"], "known")
    assert seg.verify({"refs": ["s1.e4"], "quotes": ["never said"]}, got.parts)["status"] == "unknown"
