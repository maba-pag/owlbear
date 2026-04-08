"""Tests for task #264: Wire Quality-Runner into pipeline agents.

Test task: #430
AC contract under test:
1. builder, reviewer, auditor, test-writer agent.md files have quality-runner in agents array
2. agents array is not empty (no leftover agents: [])
3. tdd-workflow, code-review, task-verification, tdd-red SKILL.md files contain
   Quality-Runner invocation references
4. Each updated skill retains a dedicated fallback section with direct uv run commands
5. No execute/* tools were removed from any of the 4 agents (compound invariant with AC1)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / "share" / "agents"
SKILLS_DIR = ROOT / "share" / "skills"

# The 4 pipeline agents that must have quality-runner wired in
QUALITY_RUNNER_AGENTS = [
    "builder",
    "reviewer",
    "auditor",
    "test-writer",
]

# The 4 skills that must have Quality-Runner invocation references
QUALITY_RUNNER_SKILLS = [
    "tdd-workflow",
    "code-review",
    "task-verification",
    "tdd-red",
]

# Full set of execute/* tools that must be preserved in all 4 agents after wiring
EXECUTE_TOOLS_ALL = [
    "execute/testFailure",
    "execute/getTerminalOutput",
    "execute/sendToTerminal",
    "execute/awaitTerminal",
    "execute/killTerminal",
    "execute/executionSubagent",
    "execute/runInTerminal",
    "execute/runTests",
]


def _get_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter text between the first pair of --- delimiters."""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No frontmatter found in {path}")
    return match.group(1)


def _agent_path(name: str) -> Path:
    return AGENTS_DIR / f"{name}.agent.md"


def _skill_path(name: str) -> Path:
    return SKILLS_DIR / name / "SKILL.md"


class TestFromAC_AgentsArrayHasQualityRunner:
    """AC1: builder, reviewer, auditor, test-writer agents must have quality-runner in agents array."""

    def test_builder_agents_contains_quality_runner(self) -> None:
        """builder.agent.md frontmatter agents array must contain 'quality-runner'."""
        fm = _get_frontmatter(_agent_path("builder"))
        assert "quality-runner" in fm.lower(), (
            "builder.agent.md agents array must contain 'quality-runner'"
        )

    def test_reviewer_agents_contains_quality_runner(self) -> None:
        """reviewer.agent.md frontmatter agents array must contain 'quality-runner'."""
        fm = _get_frontmatter(_agent_path("reviewer"))
        assert "quality-runner" in fm.lower(), (
            "reviewer.agent.md agents array must contain 'quality-runner'"
        )

    def test_auditor_agents_contains_quality_runner(self) -> None:
        """auditor.agent.md frontmatter agents array must contain 'quality-runner'."""
        fm = _get_frontmatter(_agent_path("auditor"))
        assert "quality-runner" in fm.lower(), (
            "auditor.agent.md agents array must contain 'quality-runner'"
        )

    def test_test_writer_agents_contains_quality_runner(self) -> None:
        """test-writer.agent.md frontmatter agents array must contain 'quality-runner'."""
        fm = _get_frontmatter(_agent_path("test-writer"))
        assert "quality-runner" in fm.lower(), (
            "test-writer.agent.md agents array must contain 'quality-runner'"
        )

    def test_all_four_agents_have_quality_runner(self) -> None:
        """All 4 pipeline agents must have quality-runner — bulk sentinel for completeness."""
        missing = [
            name
            for name in QUALITY_RUNNER_AGENTS
            if "quality-runner" not in _get_frontmatter(_agent_path(name)).lower()
        ]
        assert missing == [], f"These agents are missing quality-runner: {missing}"


class TestFromAC_AgentsArrayNotEmpty:
    """AC2: agents array must not be the empty literal '[]' for all 4 agents.

    Tests verify quality-runner is present AND existing agents (scribe) are preserved,
    ensuring no regression when wiring quality-runner in.
    """

    def _get_agents_list(self, name: str) -> str:
        """Extract the raw agents array content."""
        fm = _get_frontmatter(_agent_path(name))
        match = re.search(r"^agents:\s*\[(.+?)\]", fm, re.MULTILINE)
        if match is None:
            return ""
        return match.group(1)

    def test_builder_agents_array_has_quality_runner_and_preserves_scribe(self) -> None:
        """builder.agent.md agents array must contain quality-runner AND preserve scribe."""
        fm = _get_frontmatter(_agent_path("builder"))
        assert "quality-runner" in fm.lower(), (
            "builder.agent.md agents array must contain 'quality-runner'"
        )
        agents = self._get_agents_list("builder")
        assert "scribe" in agents, (
            "builder.agent.md must preserve 'scribe' in agents array after wiring quality-runner"
        )

    def test_reviewer_agents_array_has_quality_runner_and_preserves_scribe(self) -> None:
        """reviewer.agent.md agents array must contain quality-runner AND preserve scribe."""
        fm = _get_frontmatter(_agent_path("reviewer"))
        assert "quality-runner" in fm.lower(), (
            "reviewer.agent.md agents array must contain 'quality-runner'"
        )
        agents = self._get_agents_list("reviewer")
        assert "scribe" in agents, (
            "reviewer.agent.md must preserve 'scribe' in agents array after wiring quality-runner"
        )

    def test_auditor_agents_array_has_quality_runner_and_preserves_scribe(self) -> None:
        """auditor.agent.md agents array must contain quality-runner AND preserve scribe."""
        fm = _get_frontmatter(_agent_path("auditor"))
        assert "quality-runner" in fm.lower(), (
            "auditor.agent.md agents array must contain 'quality-runner'"
        )
        agents = self._get_agents_list("auditor")
        assert "scribe" in agents, (
            "auditor.agent.md must preserve 'scribe' in agents array after wiring quality-runner"
        )

    def test_test_writer_agents_array_not_empty(self) -> None:
        """test-writer.agent.md must not have agents: [] (currently empty, must be wired)."""
        fm = _get_frontmatter(_agent_path("test-writer"))
        match = re.search(r"^agents:\s*\[\s*\]", fm, re.MULTILINE)
        assert match is None, "test-writer.agent.md must not have agents: []"


class TestFromAC_SkillsContainQualityRunnerInvocation:
    """AC3: tdd-workflow, code-review, task-verification, tdd-red SKILL.md files
    must contain Quality-Runner invocation references.
    """

    def test_tdd_workflow_skill_contains_quality_runner_invocation(self) -> None:
        """tdd-workflow SKILL.md must reference Quality-Runner invocation."""
        content = _skill_path("tdd-workflow").read_text(encoding="utf-8")
        assert "quality-runner" in content.lower(), (
            "tdd-workflow SKILL.md must contain Quality-Runner invocation reference"
        )

    def test_code_review_skill_contains_quality_runner_invocation(self) -> None:
        """code-review SKILL.md must reference Quality-Runner invocation."""
        content = _skill_path("code-review").read_text(encoding="utf-8")
        assert "quality-runner" in content.lower(), (
            "code-review SKILL.md must contain Quality-Runner invocation reference"
        )

    def test_task_verification_skill_contains_quality_runner_invocation(self) -> None:
        """task-verification SKILL.md must reference Quality-Runner invocation."""
        content = _skill_path("task-verification").read_text(encoding="utf-8")
        assert "quality-runner" in content.lower(), (
            "task-verification SKILL.md must contain Quality-Runner invocation reference"
        )

    def test_tdd_red_skill_contains_quality_runner_invocation(self) -> None:
        """tdd-red SKILL.md must reference Quality-Runner invocation."""
        content = _skill_path("tdd-red").read_text(encoding="utf-8")
        assert "quality-runner" in content.lower(), (
            "tdd-red SKILL.md must contain Quality-Runner invocation reference"
        )

    def test_all_four_skills_have_quality_runner_invocation(self) -> None:
        """All 4 skills must have Quality-Runner invocation reference — bulk sentinel."""
        missing = [
            name
            for name in QUALITY_RUNNER_SKILLS
            if "quality-runner" not in _skill_path(name).read_text(encoding="utf-8").lower()
        ]
        assert missing == [], f"These skills are missing quality-runner invocation: {missing}"


class TestFromAC_SkillsRetainFallbackSection:
    """AC4: Each updated skill must retain a dedicated fallback section containing direct
    uv run commands (for when quality-runner is unavailable).

    The fallback is a labeled markdown heading (e.g. '## Fallback', '### Fallback: Direct commands')
    that contains uv run invocations so agents can run tests manually if quality-runner fails.
    """

    def _assert_fallback_section_with_uv_run(self, skill_name: str) -> None:
        content = _skill_path(skill_name).read_text(encoding="utf-8")
        # Must have a dedicated fallback heading (markdown heading containing "fallback")
        fallback_heading = re.search(r"#{1,4}\s+.*fallback.*", content, re.IGNORECASE)
        assert fallback_heading is not None, (
            f"{skill_name} SKILL.md must have a dedicated Fallback heading section "
            f"(e.g. '## Fallback: Direct Commands') for when quality-runner is unavailable"
        )
        # The fallback section must contain uv run commands
        pos = fallback_heading.start()
        section_text = content[pos : pos + 1500]
        assert "uv run" in section_text, (
            f"{skill_name} SKILL.md fallback section must contain 'uv run' commands"
        )

    def test_tdd_workflow_skill_has_fallback_section_with_uv_run(self) -> None:
        """tdd-workflow SKILL.md must have a Fallback heading with uv run commands."""
        self._assert_fallback_section_with_uv_run("tdd-workflow")

    def test_code_review_skill_has_fallback_section_with_uv_run(self) -> None:
        """code-review SKILL.md must have a Fallback heading with uv run commands."""
        self._assert_fallback_section_with_uv_run("code-review")

    def test_task_verification_skill_has_fallback_section_with_uv_run(self) -> None:
        """task-verification SKILL.md must have a Fallback heading with uv run commands."""
        self._assert_fallback_section_with_uv_run("task-verification")

    def test_tdd_red_skill_has_fallback_section_with_uv_run(self) -> None:
        """tdd-red SKILL.md must have a Fallback heading with uv run commands."""
        self._assert_fallback_section_with_uv_run("tdd-red")


class TestFromAC_ExecuteToolsPreservedWithQualityRunner:
    """AC5: No execute/* tools were removed from any of the 4 agents when wiring quality-runner.

    Tests the compound invariant: quality-runner present in agents array AND all execute/*
    tools preserved in tools list. Tests fail in RED phase because quality-runner is not
    yet present. After #264, tests also fail if any execute/* tool is accidentally removed.
    """

    def _get_tools_string(self, name: str) -> str:
        """Extract the raw tools array value from agent frontmatter."""
        fm = _get_frontmatter(_agent_path(name))
        match = re.search(r"^tools:\s*\[(.+?)\]", fm, re.DOTALL | re.MULTILINE)
        if match is None:
            raise ValueError(f"No tools field found in {name}.agent.md")
        return match.group(1)

    def _assert_quality_runner_and_execute_tools(self, name: str) -> None:
        fm = _get_frontmatter(_agent_path(name))
        # quality-runner must be present (fails in RED phase — drives the failing behavior)
        assert "quality-runner" in fm.lower(), (
            f"{name}.agent.md must have quality-runner in agents array"
        )
        tools = self._get_tools_string(name)
        for tool in EXECUTE_TOOLS_ALL:
            assert tool in tools, (
                f"{name}.agent.md must retain {tool!r} after quality-runner wiring"
            )

    def test_builder_retains_execute_tools_with_quality_runner(self) -> None:
        """builder.agent.md: quality-runner present AND all execute/* tools preserved."""
        self._assert_quality_runner_and_execute_tools("builder")

    def test_reviewer_retains_execute_tools_with_quality_runner(self) -> None:
        """reviewer.agent.md: quality-runner present AND all execute/* tools preserved."""
        self._assert_quality_runner_and_execute_tools("reviewer")

    def test_auditor_retains_execute_tools_with_quality_runner(self) -> None:
        """auditor.agent.md: quality-runner present AND all execute/* tools preserved."""
        self._assert_quality_runner_and_execute_tools("auditor")

    def test_test_writer_retains_execute_tools_with_quality_runner(self) -> None:
        """test-writer.agent.md: quality-runner present AND all execute/* tools preserved."""
        self._assert_quality_runner_and_execute_tools("test-writer")
