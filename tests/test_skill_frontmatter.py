"""Tests for task #42: Add user-invocable: false to pipeline-only skills.

AC contract under test:
1. user-invocable: false in YAML frontmatter of exactly the 11 pipeline-only skills:
   arch-review, code-review, curation-workflow, dispatch-planning, docs-gate,
   orchestration, research-workflow, task-decomposition, task-verification,
   tdd-red, tdd-workflow
2. The 10 user-invocable skills do NOT have user-invocable: false:
   architecture-standards, decision-requests, excalidraw-diagram, frontend-design,
   kanban-md, knowledge-ops, project-definition, pytest-and-linting, retro, visual-output
3. Slash-command menu (modeled from frontmatter — decision 42-ac3 approved this proxy):
   skills visible in the menu equal exactly the 10 user-invocable skills

History: original test file was v1/tests/test_skill_frontmatter.py (lost during v1 cleanup).
Recreated in tests/ for retry cycle following decision-request resolution (approved: A).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / ".github" / "skills"

# AC 1: 11 pipeline-only skills — must have user-invocable: false
PIPELINE_ONLY_SKILLS = [
    "arch-review",
    "code-review",
    "curation-workflow",
    "dispatch-planning",
    "docs-gate",
    "orchestration",
    "research-workflow",
    "task-decomposition",
    "task-verification",
    "tdd-red",
    "tdd-workflow",
]

# AC 2: 10 user-invocable skills — must NOT have user-invocable: false
USER_INVOCABLE_SKILLS = [
    "architecture-standards",
    "decision-requests",
    "excalidraw-diagram",
    "frontend-design",
    "kanban-md",
    "knowledge-ops",
    "project-definition",
    "pytest-and-linting",
    "retro",
    "visual-output",
]


def _get_frontmatter(skill_name: str) -> str:
    """Return the YAML frontmatter body for the given skill."""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No frontmatter found in {skill_file}")
    return match.group(1)


class TestFromAC_PipelineOnlySkills:
    """AC 1: Each of the 11 pipeline-only skills must have `user-invocable: false` in frontmatter."""

    @pytest.mark.parametrize("skill_name", PIPELINE_ONLY_SKILLS)
    def test_pipeline_skill_has_user_invocable_false(self, skill_name: str) -> None:
        """Pipeline-only skill frontmatter must contain the exact line 'user-invocable: false'."""
        frontmatter = _get_frontmatter(skill_name)
        assert "user-invocable: false" in frontmatter, (
            f"Expected 'user-invocable: false' in {skill_name}/SKILL.md frontmatter"
        )

    def test_pipeline_skill_count_is_eleven(self) -> None:
        """Exactly 11 pipeline skills are listed — guard against silent list drift."""
        assert len(PIPELINE_ONLY_SKILLS) == 11


class TestFromAC_ExactFrontmatterChanges:
    """AC 2: The 10 user-invocable skills must NOT have `user-invocable: false`."""

    @pytest.mark.parametrize("skill_name", USER_INVOCABLE_SKILLS)
    def test_user_invocable_skill_not_marked_false(self, skill_name: str) -> None:
        """User-invocable skill must not contain 'user-invocable: false' in its frontmatter."""
        frontmatter = _get_frontmatter(skill_name)
        assert "user-invocable: false" not in frontmatter, (
            f"Unexpected 'user-invocable: false' found in {skill_name}/SKILL.md frontmatter"
        )

    def test_user_invocable_skill_count_is_ten(self) -> None:
        """Exactly 10 user-invocable skills are listed — guard against silent list drift."""
        assert len(USER_INVOCABLE_SKILLS) == 10

    def test_pipeline_and_user_invocable_sets_are_disjoint(self) -> None:
        """No skill appears in both the pipeline-only and user-invocable lists."""
        overlap = set(PIPELINE_ONLY_SKILLS) & set(USER_INVOCABLE_SKILLS)
        assert overlap == set(), f"Skills appear in both lists: {overlap}"


class TestFromAC_SlashCommandMenu:
    """AC 3: Slash-command menu visibility modeled from frontmatter.

    Decision 42-ac3-slash-command-menu-verification (resolved, approved=true, option A):
    The frontmatter-inference test is accepted as the maximum automated proxy for the
    VS Code slash-command menu, which cannot be exercised from pytest.

    A skill is visible in the slash-command menu unless its frontmatter contains
    'user-invocable: false'. The set of visible skills must exactly equal the 10
    user-invocable skills — no more, no less.
    """

    def test_slash_command_menu_shows_only_user_invocable_skills(self) -> None:
        """Set of skills visible in slash-command menu equals exactly the 10 user-invocable skills."""
        visible: set[str] = set()
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            content = skill_file.read_text(encoding="utf-8")
            fm_match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
            if fm_match is None:
                continue
            fm = fm_match.group(1)
            # A skill without 'user-invocable: false' is visible in the slash-command menu
            if "user-invocable: false" not in fm:
                visible.add(skill_dir.name)

        expected = set(USER_INVOCABLE_SKILLS)
        assert visible == expected, (
            f"Slash-command menu visibility mismatch.\n"
            f"Expected visible ({len(expected)}): {sorted(expected)}\n"
            f"Actually visible ({len(visible)}): {sorted(visible)}"
        )
