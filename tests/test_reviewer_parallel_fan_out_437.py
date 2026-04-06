"""Tests for task #437: Parallel fan-out in reviewer agent.

AC contract under test:
1. reviewer.agent.md frontmatter agents: field contains both quality-runner and code-reader
   (change-detecting — FAIL before #265 implementation)
2. reviewer.agent.md frontmatter tools: list matches the 16-entry baseline exactly
   (regression guard — PASSES throughout RED and GREEN)
3. w-code-review SKILL.md contains a ## Step 2.5 heading (parallel dispatch section)
   (change-detecting — FAIL before #265 implementation)
4. w-code-review SKILL.md Step 8 section contains at least one of: Quality-Runner,
   Code-Reader, or subagent (synthesis from parallel reports)
   (change-detecting — FAIL before #265 implementation)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
REVIEWER_AGENT = ROOT / "share" / "agents" / "reviewer.agent.md"
CODE_REVIEW_SKILL = ROOT / "share" / "skills" / "w-code-review" / "SKILL.md"

# Exact 8-entry tools baseline for reviewer.agent.md (AC 2 regression guard)
# Updated by #457/#458: execute/* tools and read/terminalLastCommand removed.
EXPECTED_TOOLS: list[str] = [
    "vscode/memory",
    "read/problems",
    "read/readFile",
    "read/viewImage",
    "agent",
    "search",
    "owlbear-kanban/*",
    "owlbear-memory/*",
]


def _get_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter text between the first pair of --- delimiters."""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No frontmatter found in {path}")
    return match.group(1)


def _parse_yaml_inline_list(frontmatter: str, field: str) -> list[str]:
    """Parse an inline YAML list from frontmatter for the given field name.

    Handles both same-line syntax (field: [a, b]) and next-line syntax:
        field:
          [a, b]
    """
    pattern = rf"^{field}:\s*(?:\n\s*)?\[(.+?)\]"
    match = re.search(pattern, frontmatter, re.MULTILINE | re.DOTALL)
    if match is None:
        return []
    raw = match.group(1)
    entries = [entry.strip().strip("'\"") for entry in raw.split(",")]
    return [e for e in entries if e]


class TestFromAC_ReviewerParallelFanOut:
    """Validate structural changes to reviewer.agent.md and w-code-review SKILL.md
    for parallel fan-out wiring (parent task #265).
    """

    # --- AC 1: agents: contains both quality-runner and code-reader (parallel fan-out) ---

    def test_reviewer_agents_contains_quality_runner_and_code_reader(self) -> None:
        "`reviewer.agent.md agents: must include both quality-runner and code-reader for parallel fan-out."
        fm = _get_frontmatter(REVIEWER_AGENT)
        agents = _parse_yaml_inline_list(fm, "agents")
        assert "quality-runner" in agents, (
            f"reviewer.agent.md 'agents:' does not contain 'quality-runner'. "
            f"Current agents: {agents}"
        )
        assert "code-reader" in agents, (
            f"reviewer.agent.md 'agents:' does not contain 'code-reader'. "
            f"Current agents: {agents}"
        )

    # --- AC 2: tools: matches 16-entry baseline (regression guard, PASSES throughout) ---

    def test_reviewer_tools_count_is_8(self) -> None:
        """reviewer.agent.md tools: must have exactly 8 entries (regression guard).

        Updated by #457/#458: execute/* tools and read/terminalLastCommand removed.
        """
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert len(tools) == 8, (
            f"Expected exactly 8 tools entries, got {len(tools)}. "
            f"Current tools: {tools}"
        )

    def test_reviewer_tools_contains_all_baseline_entries(self) -> None:
        """reviewer.agent.md tools: must contain all 8 baseline entries (regression guard)."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        missing = [t for t in EXPECTED_TOOLS if t not in tools]
        assert not missing, (
            f"reviewer.agent.md tools missing baseline entries: {missing}. "
            f"Current tools: {tools}"
        )

    # --- AC 3: SKILL.md has ## Step 2.5 heading (change-detecting, FAIL before #265) ---

    def test_code_review_skill_has_step_2_5_heading(self) -> None:
        """w-code-review SKILL.md must contain '## Step 2.5' parallel dispatch heading."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        assert "## Step 2.5" in content, (
            "w-code-review SKILL.md does not contain '## Step 2.5' heading. "
            "This section must be added for parallel fan-out dispatch."
        )

    # --- AC 4: SKILL.md Step 8 contains synthesis keywords (change-detecting, FAIL before #265) ---

    def test_code_review_skill_step8_references_parallel_synthesis(self) -> None:
        """Step 8 of w-code-review SKILL.md must reference Quality-Runner, Code-Reader,
        or subagent for parallel report synthesis.
        """
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        step8_match = re.search(r"(## Step 8.*?)(?=\n## |\Z)", content, re.DOTALL)
        assert step8_match is not None, (
            "Could not locate '## Step 8' section in w-code-review SKILL.md"
        )
        step8 = step8_match.group(1)
        keywords = [
            "Quality-Runner",
            "quality-runner",
            "Code-Reader",
            "code-reader",
            "subagent",
            "Subagent",
        ]
        found = [kw for kw in keywords if kw in step8]
        assert found, (
            f"Step 8 of w-code-review SKILL.md does not reference parallel synthesis. "
            f"Expected at least one of: Quality-Runner, Code-Reader, subagent. "
            f"Step 8 preview: {step8[:300]!r}"
        )
