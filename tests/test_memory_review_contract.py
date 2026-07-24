"""Contract tests for memory review lifecycle coverage and loading."""

from __future__ import annotations

import re
from pathlib import Path

from owlbear_mcp_memory.models import MemoryState

_REPO_ROOT = Path(__file__).parent.parent
_PROMPT = _REPO_ROOT / "share/prompts/memory-audit.prompt.md"
_STRUCTURE = _REPO_ROOT / "share/skills/h-memory-structure/SKILL.md"


def _quoted_values(text: str) -> set[str]:
    return set(re.findall(r'"([a-z]+)"', text))


def test_memory_review_preflight_covers_every_live_runtime_state() -> None:
    """Review preflight cannot silently omit a non-deleted lifecycle state."""
    prompt = _PROMPT.read_text(encoding="utf-8")
    preflight = prompt.split("## 2. Session Preflight", maxsplit=1)[1].split("## 3.", maxsplit=1)[0]
    states_argument = re.search(r"`states: \[([^]]+)]`", preflight)

    assert states_argument is not None
    expected = {state.value for state in MemoryState if state is not MemoryState.DELETED}
    assert _quoted_values(states_argument.group(1)) == expected
    assert "`resolution_queue`" in preflight
    assert "what requires Cockpit" in preflight


def test_memory_structure_documents_the_runtime_state_enum() -> None:
    """The structure handbook remains the complete canonical state reference."""
    structure = _STRUCTURE.read_text(encoding="utf-8")
    state_values = re.search(r"- `state` values: ([^\n]+)", structure)

    assert state_values is not None
    assert set(re.findall(r"`([a-z]+)`", state_values.group(1))) == {state.value for state in MemoryState}
    assert "Cockpit (`MemoryEngine.resolve`)" in structure
