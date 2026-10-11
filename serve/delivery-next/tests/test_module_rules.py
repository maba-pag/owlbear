"""Code-shape rules (TD-33): agents aim for 400 lines per module, the test fails at 500 raw lines."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from owlbear_delivery_next import mcp_server, tools
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind

SRC = Path(__file__).resolve().parents[1] / "src" / "owlbear_delivery_next"
LIMIT = 500
SUBMITS = (tools.SUBMIT, tools.REVIEW, tools.RECIPE, tools.PLAN)  # one per worker role and step


@pytest.mark.parametrize("path", sorted(SRC.rglob("*.py")), ids=lambda p: str(p.relative_to(SRC)))
def test_module_within_limit(path: Path) -> None:
    count = len(path.read_text(encoding="utf-8").splitlines())
    assert count <= LIMIT, f"{path.relative_to(SRC)} has {count} lines; split it by use case"


def test_vocabularies_stay_small() -> None:
    assert len(StepKind) <= 10
    assert len(ErrorKind) <= 15
    assert {e for e in Exit if e is not Exit.PENDING} == {Exit.DONE, Exit.RETRY, Exit.ASK, Exit.BACK, Exit.STOP}
    assert len(Exit) == 6


def test_agent_tools_stay_few() -> None:
    per_role = [{s.name for s in (submit, tools.ASK, tools.PREMISE)} for submit in SUBMITS]
    chat = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert len(set().union(*per_role) | chat) <= 6
    assert all(len(names) <= 3 for names in [*per_role, chat])
