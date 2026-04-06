"""Tests for task #264: Wire Quality-Runner into pipeline agents.

AC contract under test:
1. builder, reviewer, auditor, test-writer agent.md frontmatter agents: includes quality-runner
2. w-tdd-red/SKILL.md contains Quality-Runner invocation (mode: scoped)
3. w-code-review/SKILL.md Steps 3,4,5 contain Quality-Runner invocation
4. w-task-verification/SKILL.md Step 2 contains Quality-Runner invocation (mode: full)
5. w-tdd-red/SKILL.md Step 5 contains Quality-Runner invocation
6. Each updated skill retains a fallback section (heading) with direct uv run commands
7. No existing execute/* tools removed from any agent's tools list
8. agents: [] replaced — no empty array remains on any wired agent
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / "share" / "agents"
SKILLS_DIR = ROOT / "share" / "skills"

# The 4 pipeline agents that must have quality-runner wired in
WIRED_AGENTS = ["builder", "reviewer", "auditor", "test-writer"]

# execute/* tools that must be preserved on all 4 wired agents
REQUIRED_EXECUTE_TOOLS = [
    "execute/testFailure",
    "execute/getTerminalOutput",
    "execute/awaitTerminal",
    "execute/killTerminal",
    "execute/createAndRunTask",
    "execute/runInTerminal",
    "execute/runTests",
]


def _read_frontmatter(path: Path) -> str:
    """Extract YAML frontmatter text (between the two --- delimiters)."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return ""
    end = content.find("---", 3)
    if end == -1:
        return ""
    return content[3:end]


def _agent_path(name: str) -> Path:
    return AGENTS_DIR / f"{name}.agent.md"


def _skill_path(name: str) -> Path:
    return SKILLS_DIR / name / "SKILL.md"


# ---------------------------------------------------------------------------
# AC1 + AC8: agents: includes quality-runner and no empty agents: [] remains
# ---------------------------------------------------------------------------


class TestFromAC_AgentFrontmatterWiring:
    """AC1: builder, reviewer, auditor, test-writer must have quality-runner in agents: list."""

    def test_builder_agents_includes_quality_runner(self) -> None:
        fm = _read_frontmatter(_agent_path("builder"))
        assert "quality-runner" in fm, "builder.agent.md agents: must include quality-runner"

    def test_reviewer_agents_includes_quality_runner(self) -> None:
        fm = _read_frontmatter(_agent_path("reviewer"))
        assert "quality-runner" in fm, "reviewer.agent.md agents: must include quality-runner"

    def test_auditor_agents_includes_quality_runner(self) -> None:
        fm = _read_frontmatter(_agent_path("auditor"))
        assert "quality-runner" in fm, "auditor.agent.md agents: must include quality-runner"

    def test_test_writer_agents_includes_quality_runner(self) -> None:
        fm = _read_frontmatter(_agent_path("test-writer"))
        assert "quality-runner" in fm, "test-writer.agent.md agents: must include quality-runner"

    def test_agents_field_uses_replacement_not_second_line(self) -> None:
        """agents: [quality-runner] must appear as a single field, not agents: [] with extra line."""
        for name in WIRED_AGENTS:
            fm = _read_frontmatter(_agent_path(name))
            assert re.search(r"agents:\s*\[.*quality-runner.*\]", fm), (
                f"{name}.agent.md: agents: field must be agents: [quality-runner] (or superset)"
            )


class TestFromAC_NoEmptyAgentsArray:
    """AC11: existing agents: [] must be replaced — no empty array remains."""

    def test_builder_has_no_empty_agents_array(self) -> None:
        fm = _read_frontmatter(_agent_path("builder"))
        assert "agents: []" not in fm, "builder.agent.md still has agents: [] — must be replaced"

    def test_reviewer_has_no_empty_agents_array(self) -> None:
        fm = _read_frontmatter(_agent_path("reviewer"))
        assert "agents: []" not in fm, "reviewer.agent.md still has agents: [] — must be replaced"

    def test_auditor_has_no_empty_agents_array(self) -> None:
        fm = _read_frontmatter(_agent_path("auditor"))
        assert "agents: []" not in fm, "auditor.agent.md still has agents: [] — must be replaced"

    def test_test_writer_has_no_empty_agents_array(self) -> None:
        fm = _read_frontmatter(_agent_path("test-writer"))
        assert "agents: []" not in fm, "test-writer.agent.md still has agents: [] — must be replaced"


# ---------------------------------------------------------------------------
# AC10: No existing execute/* tools removed — tested as compound with QR presence
# ---------------------------------------------------------------------------


class TestFromAC_ExecuteToolsPreserved:
    """AC10: No existing execute/* tools removed from any wired agent's tools list.

    Each test first verifies quality-runner is present (RED gate), then checks
    every execute/* tool is still listed — both conditions must be satisfied.
    """

    def _assert_wired_and_tools_intact(self, name: str) -> None:
        content = _agent_path(name).read_text(encoding="utf-8")
        assert "quality-runner" in content, (
            f"{name}.agent.md: quality-runner not wired in yet"
        )
        for tool in REQUIRED_EXECUTE_TOOLS:
            assert tool in content, (
                f"{name}.agent.md: execute tool {tool!r} was removed — must be preserved"
            )

    def test_builder_tools_intact_after_wiring(self) -> None:
        self._assert_wired_and_tools_intact("builder")

    def test_reviewer_tools_intact_after_wiring(self) -> None:
        self._assert_wired_and_tools_intact("reviewer")

    def test_auditor_tools_intact_after_wiring(self) -> None:
        self._assert_wired_and_tools_intact("auditor")

    def test_test_writer_tools_intact_after_wiring(self) -> None:
        self._assert_wired_and_tools_intact("test-writer")


# ---------------------------------------------------------------------------
# AC5: w-tdd-red/SKILL.md contains Quality-Runner invocation (mode: scoped)
# (Previously tdd-workflow; now split into w-tdd-red + w-tdd-green)
# ---------------------------------------------------------------------------


class TestFromAC_TddWorkflowSkillQualityRunner:
    """AC5: w-tdd-red/SKILL.md contains Quality-Runner invocation."""

    def _skill(self) -> str:
        return _skill_path("w-tdd-red").read_text(encoding="utf-8")

    def test_tdd_workflow_references_quality_runner(self) -> None:
        assert "quality-runner" in self._skill().lower()

    def test_tdd_workflow_uses_mode_scoped(self) -> None:
        assert "mode: scoped" in self._skill()

    def test_tdd_workflow_includes_test_paths_param(self) -> None:
        assert "test_paths" in self._skill()

    def test_tdd_workflow_includes_lint_paths_param(self) -> None:
        assert "lint_paths" in self._skill()

    def test_tdd_workflow_has_fallback_section_heading(self) -> None:
        """A markdown heading containing 'fallback' must exist for when QR is unavailable."""
        assert re.search(r"#+\s+.*fallback", self._skill(), re.IGNORECASE), (
            "w-tdd-red/SKILL.md: missing fallback section heading"
        )

    def test_tdd_workflow_fallback_references_pytest_and_linting_skill(self) -> None:
        """Fallback section must reference the pytest-and-linting skill for direct commands."""
        skill = self._skill()
        # QR must be wired before the fallback can meaningfully exist
        assert "quality-runner" in skill.lower(), "quality-runner not wired — fallback context absent"
        assert "pytest-and-linting" in skill


# ---------------------------------------------------------------------------
# AC6: w-code-review/SKILL.md Steps 3,4,5 use Quality-Runner
# ---------------------------------------------------------------------------


class TestFromAC_CodeReviewSkillQualityRunner:
    """AC6: w-code-review/SKILL.md Steps 3, 4, 5 use Quality-Runner invocation."""

    def _skill(self) -> str:
        return _skill_path("w-code-review").read_text(encoding="utf-8")

    def test_code_review_references_quality_runner(self) -> None:
        assert "quality-runner" in self._skill().lower()

    def test_code_review_uses_mode_scoped(self) -> None:
        assert "mode: scoped" in self._skill()

    def test_code_review_includes_test_paths_param(self) -> None:
        assert "test_paths" in self._skill()

    def test_code_review_has_fallback_section_heading(self) -> None:
        """A markdown heading containing 'fallback' must exist for when QR is unavailable."""
        assert re.search(r"#+\s+.*fallback", self._skill(), re.IGNORECASE), (
            "w-code-review/SKILL.md: missing fallback section heading"
        )

    def test_code_review_fallback_references_pytest_and_linting_skill(self) -> None:
        skill = self._skill()
        assert "quality-runner" in skill.lower(), "quality-runner not wired — fallback context absent"
        assert "pytest-and-linting" in skill


# ---------------------------------------------------------------------------
# AC7: w-task-verification/SKILL.md Step 2 uses Quality-Runner (mode: full)
# ---------------------------------------------------------------------------


class TestFromAC_TaskVerificationSkillQualityRunner:
    """AC7: w-task-verification/SKILL.md Step 2 uses Quality-Runner invocation (mode: full)."""

    def _skill(self) -> str:
        return _skill_path("w-task-verification").read_text(encoding="utf-8")

    def test_task_verification_references_quality_runner(self) -> None:
        assert "quality-runner" in self._skill().lower()

    def test_task_verification_uses_mode_full(self) -> None:
        """Auditor runs full suite regression check — must use mode: full."""
        assert "mode: full" in self._skill()

    def test_task_verification_has_fallback_section_heading(self) -> None:
        assert re.search(r"#+\s+.*fallback", self._skill(), re.IGNORECASE), (
            "w-task-verification/SKILL.md: missing fallback section heading"
        )

    def test_task_verification_fallback_references_pytest_and_linting_skill(self) -> None:
        skill = self._skill()
        assert "quality-runner" in skill.lower(), "quality-runner not wired — fallback context absent"
        assert "pytest-and-linting" in skill


# ---------------------------------------------------------------------------
# AC8: w-tdd-red/SKILL.md Step 5 uses Quality-Runner
# ---------------------------------------------------------------------------


class TestFromAC_TddRedSkillQualityRunner:
    """AC8: w-tdd-red/SKILL.md Step 5 uses Quality-Runner invocation."""

    def _skill(self) -> str:
        return _skill_path("w-tdd-red").read_text(encoding="utf-8")

    def test_tdd_red_references_quality_runner(self) -> None:
        assert "quality-runner" in self._skill().lower()

    def test_tdd_red_uses_mode_scoped(self) -> None:
        assert "mode: scoped" in self._skill()

    def test_tdd_red_has_fallback_section_heading(self) -> None:
        skill = self._skill()
        assert "quality-runner" in skill.lower(), (
            "quality-runner not wired — no QR fallback section can exist yet"
        )
        assert re.search(r"#+\s+.*fallback", skill, re.IGNORECASE), (
            "w-tdd-red/SKILL.md: missing fallback section heading for QR unavailability"
        )

    def test_tdd_red_fallback_references_pytest_and_linting_skill(self) -> None:
        skill = self._skill()
        assert "quality-runner" in skill.lower(), "quality-runner not wired — fallback context absent"
        assert "pytest-and-linting" in skill
