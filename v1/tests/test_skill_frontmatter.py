"""Tests: SKILL.md user-invocable frontmatter enforcement (#42)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Location of skills relative to this test file
# v1/tests/ -> v1/ -> owlbear/ -> .github/skills/
# ---------------------------------------------------------------------------
SKILLS_DIR = Path(__file__).parent.parent.parent / ".github" / "skills"

# AC line 1: these 11 skills must have user-invocable: false
PIPELINE_ONLY = [
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

# AC line 2: these 10 skills must NOT have user-invocable: false
USER_INVOCABLE = [
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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _extract_frontmatter_text(skill_name: str) -> str:
    """Return raw YAML frontmatter block (between --- delimiters) as a string."""
    path = SKILLS_DIR / skill_name / "SKILL.md"
    assert path.exists(), f"SKILL.md not found for skill '{skill_name}': {path}"
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match, f"No valid YAML frontmatter found in {path}"
    return match.group(1)


# ---------------------------------------------------------------------------
# AC line 1 — pipeline-only skills must have user-invocable: false
# ---------------------------------------------------------------------------


class TestFromAC_PipelineOnlySkills:
    """Each of the 11 pipeline-only skills must declare user-invocable: false."""

    @pytest.mark.parametrize("skill_name", PIPELINE_ONLY)
    def test_pipeline_skill_has_user_invocable_false(self, skill_name: str) -> None:
        """The frontmatter of a pipeline-only skill must contain 'user-invocable: false'."""
        frontmatter = _extract_frontmatter_text(skill_name)
        # Exact line match: key must be present, value must be false (not true, not absent)
        assert re.search(r"^user-invocable:\s*false\s*$", frontmatter, re.MULTILINE), (
            f"Expected 'user-invocable: false' in frontmatter of '{skill_name}', "
            f"but it was not found.\nFrontmatter:\n{frontmatter}"
        )


# ---------------------------------------------------------------------------
# AC lines 1 + 2 combined — exactly the 11 pipeline skills are marked false,
# the 10 user-invocable skills are not touched
# ---------------------------------------------------------------------------


class TestFromAC_ExactFrontmatterChanges:
    """Exactly 11 skills (the pipeline-only set) have user-invocable: false.

    Prevents the builder from accidentally marking user-invocable skills as false.
    Also serves as a count check that all 11 required skills were updated.
    """

    def test_exactly_eleven_skills_marked_not_user_invocable(self) -> None:
        """Exactly the 11 pipeline-only skills and no others should have user-invocable: false."""
        all_skills = PIPELINE_ONLY + USER_INVOCABLE
        skills_with_false = [
            s
            for s in all_skills
            if re.search(
                r"^user-invocable:\s*false\s*$",
                _extract_frontmatter_text(s),
                re.MULTILINE,
            )
        ]
        assert set(skills_with_false) == set(PIPELINE_ONLY), (
            f"Expected exactly these skills to have user-invocable: false:\n"
            f"  {sorted(PIPELINE_ONLY)}\n"
            f"But found:\n"
            f"  {sorted(skills_with_false)}"
        )
        assert len(skills_with_false) == 11, (
            f"Expected 11 skills with user-invocable: false, got {len(skills_with_false)}"
        )


# ---------------------------------------------------------------------------
# AC line 3 — slash-command menu shows only user-invocable skills
# ---------------------------------------------------------------------------


class TestFromAC_SlashCommandMenu:
    """Slash-command menu shows exactly the 10 user-invocable skills.

    The VS Code slash-command menu displays all skills that do NOT have
    'user-invocable: false' in their frontmatter. This test scans every
    SKILL.md in the skills directory dynamically (not just the 21 hard-coded
    names) so any newly-added skill without proper categorisation will cause
    this test to fail before reaching the menu.
    """

    def test_slash_command_menu_shows_only_user_invocable_skills(self) -> None:
        """Skills visible in the slash-command menu equal exactly the USER_INVOCABLE set."""
        # Discover all skill directories that contain a SKILL.md
        skill_names = sorted(
            d.name
            for d in SKILLS_DIR.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )
        assert skill_names, f"No SKILL.md files found under {SKILLS_DIR}"

        # Skills visible in the slash-command menu = those WITHOUT user-invocable: false
        menu_visible: set[str] = set()
        for skill_name in skill_names:
            frontmatter = _extract_frontmatter_text(skill_name)
            if not re.search(r"^user-invocable:\s*false\s*$", frontmatter, re.MULTILINE):
                menu_visible.add(skill_name)

        assert menu_visible == set(USER_INVOCABLE), (
            f"Slash-command menu would show unexpected skills.\n"
            f"Expected: {sorted(USER_INVOCABLE)}\n"
            f"Got:      {sorted(menu_visible)}"
        )
