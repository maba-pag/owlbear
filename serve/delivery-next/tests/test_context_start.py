"""A real context attribution answer mapped to the seven parts of a session's context at start."""

from __future__ import annotations

import json
from pathlib import Path

from copilot.generated.rpc import SessionContextAttribution

from owlbear_delivery_next.runtimes import context_start
from owlbear_delivery_next.state_store import spend_ledger, spend_shares

ANSWER = json.loads((Path(__file__).parent / "fixtures" / "context_attribution.json").read_text())


def test_a_real_answer_maps_to_seven_parts_that_add_up_to_its_total_and_is_written_as_no_run() -> None:
    found = context_start.mapped(SessionContextAttribution.from_dict(ANSWER["contextAttribution"]))
    assert (found.measured, found.window, found.total, found.kept) == (True, 272000, 11029, "")
    assert found.parts == {"system_prompt": 4210, "custom_instructions": 6137, "skills": 0, "subagents": 0,
                           "built_in_tools": 581, "mcp_tools": 0, "messages": 101}  # fmt: skip
    assert sum(found.parts.values()) == ANSWER["contextAttribution"]["totalTokens"]
    assert context_start.mapped(None).fields() == {"measured": False, "error": "no context attribution"}

    spend_ledger.context("r1", "s1", agent="builder", model="gpt-6-luna", tier="standard", measurement=found.fields())
    assert spend_ledger.WRITER.settled(5)
    (line,) = spend_ledger.lines()
    assert (line["type"], line["parts"]["messages"], line["measured"]) == ("context", 101, True)
    assert spend_shares.runs([line]) == []
