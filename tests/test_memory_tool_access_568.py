"""Tests for task #568: add owlbear-memory/* to all pipeline agent tools lists.

Static regression guard that parses agents/*.agent.md YAML frontmatter and asserts
'owlbear-memory/*' is present in every pipeline agent that should have it, and absent
from the three excluded agents (challenger, code-reader, orchestrator).

AC coverage:
  - AC1: 11 agents include 'owlbear-memory/*' in tools:
         (architect, auditor, builder, curator, kanban-planner, planner,
          researcher, reviewer, scribe, test-writer, writer)
  - AC2: 3 agents are NOT modified: challenger, code-reader, orchestrator
  - AC3: validate_agents.py passes (exit 0 on all HEAD agent files)
  - AC4: No other frontmatter changes (surgical edit only) — tested by
         TestFromAC_SurgicalEditOnly which compares current tools against the
         pre-#568 git baseline and asserts the only difference is owlbear-memory/*
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENTS_DIR = _REPO_ROOT / "agents"

# --- AC1: these 11 agents MUST include 'owlbear-memory/*' ---
AGENTS_REQUIRING_MEMORY: tuple[str, ...] = (
    "architect",
    "auditor",
    "builder",
    "curator",
    "kanban-planner",
    "planner",
    "researcher",
    "reviewer",
    "scribe",
    "test-writer",
    "writer",
)

# --- AC2: these 3 agents must NOT have 'owlbear-memory/*' ---
AGENTS_EXCLUDING_MEMORY: tuple[str, ...] = (
    "challenger",
    "code-reader",
    "orchestrator",
)


# ---------------------------------------------------------------------------
# Helpers (same pattern as test_reviewer_write_tools_533.py)
# ---------------------------------------------------------------------------

def _read_agent(name: str) -> str:
    path = _AGENTS_DIR / f"{name}.agent.md"
    assert path.is_file(), f"agents/{name}.agent.md does not exist"
    return path.read_text(encoding="utf-8")


def _extract_tools_text(content: str) -> str:
    """Return all text in the tools: block (handles multi-line bracket syntax)."""
    lines = content.splitlines()
    result: list[str] = []
    in_tools = False
    for line in lines:
        if re.match(r"^tools:", line):
            result.append(line)
            in_tools = True
        elif in_tools:
            if line.startswith((" ", "\t")):
                result.append(line)
            else:
                break
    return " ".join(result)


def _has_memory_tool(content: str) -> bool:
    """Return True if tools section contains 'owlbear-memory/*'."""
    tools_text = _extract_tools_text(content)
    return "owlbear-memory/*" in tools_text


def _parse_tools_from_content(content: str) -> list[str]:
    """Parse individual tool names from the tools: section (strips surrounding quotes)."""
    tools_text = _extract_tools_text(content)
    match = re.search(r"\[(.+)\]", tools_text, re.DOTALL)
    if not match:
        return []
    tools_str = match.group(1)
    return [t.strip().strip("'\"") for t in tools_str.split(",") if t.strip()]


def _git_agent_content(commit: str, agent_name: str) -> str:
    """Return agent file content at a given git ref (exits non-zero raises AssertionError)."""
    result = subprocess.run(
        ["git", "show", f"{commit}:agents/{agent_name}.agent.md"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"git show {commit}:agents/{agent_name}.agent.md failed: {result.stderr.strip()}"
    )
    return result.stdout


# ---------------------------------------------------------------------------
# TestFromAC_MemoryToolPresent — AC1
# ---------------------------------------------------------------------------

class TestFromAC_MemoryToolPresent:
    """AC1: All 11 pipeline agents must have 'owlbear-memory/*' in their tools list."""

    def test_architect_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("architect")), (
            "agents/architect.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_auditor_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("auditor")), (
            "agents/auditor.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_builder_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("builder")), (
            "agents/builder.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_curator_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("curator")), (
            "agents/curator.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_kanban_planner_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("kanban-planner")), (
            "agents/kanban-planner.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_planner_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("planner")), (
            "agents/planner.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_researcher_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("researcher")), (
            "agents/researcher.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_reviewer_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("reviewer")), (
            "agents/reviewer.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_scribe_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("scribe")), (
            "agents/scribe.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_test_writer_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("test-writer")), (
            "agents/test-writer.agent.md missing 'owlbear-memory/*' in tools:"
        )

    def test_writer_has_memory_tool(self) -> None:
        assert _has_memory_tool(_read_agent("writer")), (
            "agents/writer.agent.md missing 'owlbear-memory/*' in tools:"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MemoryToolAbsent — AC2
# ---------------------------------------------------------------------------

class TestFromAC_MemoryToolAbsent:
    """AC2: challenger, code-reader, orchestrator must NOT have 'owlbear-memory/*'."""

    def test_challenger_lacks_memory_tool(self) -> None:
        assert not _has_memory_tool(_read_agent("challenger")), (
            "agents/challenger.agent.md must NOT contain 'owlbear-memory/*'"
        )

    def test_code_reader_lacks_memory_tool(self) -> None:
        assert not _has_memory_tool(_read_agent("code-reader")), (
            "agents/code-reader.agent.md must NOT contain 'owlbear-memory/*'"
        )

    def test_orchestrator_lacks_memory_tool(self) -> None:
        assert not _has_memory_tool(_read_agent("orchestrator")), (
            "agents/orchestrator.agent.md must NOT contain 'owlbear-memory/*'"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ValidateAgentsPasses — AC3
# ---------------------------------------------------------------------------

class TestFromAC_ValidateAgentsPasses:
    """AC3: validate_agents.py exits 0 on all HEAD agent files."""

    def test_validate_agents_exits_zero(self) -> None:
        """validate_agents.py must pass (exit 0) on all current agent files."""
        agent_files = sorted(_AGENTS_DIR.glob("*.agent.md"))
        assert agent_files, "No agent files found in agents/"
        result = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "scripts" / "validate_agents.py")]
            + [str(f) for f in agent_files],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"validate_agents.py failed:\n{result.stdout}\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SurgicalEditOnly — AC4
# ---------------------------------------------------------------------------

# The git commit immediately before the task #568 builder commit (54c3710).
# This is the authoritative pre-task baseline for each agent's tools list.
_PRE_TASK_COMMIT = "54c3710~1"


def _assert_only_memory_tool_added(agent_name: str) -> None:
    """Shared assertion: current tools = baseline + owlbear-memory/* and nothing else.

    Fails if any tool was added beyond owlbear-memory/*, or if any existing tool was
    removed.  This is the precise gate for AC4 (surgical edit only).
    """
    baseline_tools = set(_parse_tools_from_content(_git_agent_content(_PRE_TASK_COMMIT, agent_name)))
    current_tools = set(_parse_tools_from_content(_read_agent(agent_name)))

    extra_added = current_tools - baseline_tools - {"owlbear-memory/*"}
    removed = baseline_tools - current_tools

    assert not extra_added, (
        f"agents/{agent_name}.agent.md: unauthorized tools added (AC4 violation): "
        f"{sorted(extra_added)}"
    )
    assert not removed, (
        f"agents/{agent_name}.agent.md: tools unexpectedly removed: {sorted(removed)}"
    )
    assert "owlbear-memory/*" in current_tools, (
        f"agents/{agent_name}.agent.md: 'owlbear-memory/*' missing from tools"
    )


class TestFromAC_SurgicalEditOnly:
    """AC4: Each target agent's tools list must differ from the pre-#568 baseline by
    exactly one addition: 'owlbear-memory/*'.  No other tools may be added or removed.

    Regression guard: the original builder commit added 'edit/rename' to architect
    alongside owlbear-memory/*, violating this AC.  These tests must fail until that
    unauthorised addition is reverted.
    """

    def test_architect_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("architect")

    def test_auditor_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("auditor")

    def test_builder_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("builder")

    def test_curator_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("curator")

    def test_kanban_planner_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("kanban-planner")

    def test_planner_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("planner")

    def test_researcher_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("researcher")

    def test_reviewer_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("reviewer")

    def test_scribe_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("scribe")

    def test_test_writer_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("test-writer")

    def test_writer_surgical_edit_only(self) -> None:
        _assert_only_memory_tool_added("writer")
