"""Tests for the frontend-design skill package — SKILL.md frontmatter + reference files.

RED phase for task #941. All tests fail until #934 creates the
.github/skills/frontend-design/ package.
"""

from __future__ import annotations

from pathlib import Path

from owlbear.skills.registry import SkillRegistry

# Resolve repo root from this test file's location.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILL_FILE = _REPO_ROOT / ".github" / "skills" / "frontend-design" / "SKILL.md"
_REFERENCES_DIR = _REPO_ROOT / ".github" / "skills" / "frontend-design" / "references"

_EXPECTED_REFERENCE_FILES = [
    "typography.md",
    "color-and-contrast.md",
    "spatial-design.md",
    "motion-design.md",
    "interaction-design.md",
    "responsive-design.md",
    "ux-writing.md",
]


class TestFromAC_FrontendDesignSkillPackage:
    """Verify the frontend-design skill package exists and meets the AC contract."""

    # ------------------------------------------------------------------
    # AC1 + AC2: SKILL.md exists and is loadable by SkillRegistry
    # ------------------------------------------------------------------

    def test_skill_file_exists(self) -> None:
        """AC1: .github/skills/frontend-design/SKILL.md must exist on disk."""
        assert _SKILL_FILE.exists(), f"Expected skill file at {_SKILL_FILE}"

    def test_frontmatter_parses_without_error(self) -> None:
        """AC2: SkillRegistry._parse_frontmatter must return a non-None SkillMeta."""
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None, "Frontmatter parsing returned None"

    # ------------------------------------------------------------------
    # AC3: frontmatter name and description
    # ------------------------------------------------------------------

    def test_frontmatter_name_is_frontend_design(self) -> None:
        """AC3: parsed frontmatter name must equal 'frontend-design'."""
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None
        assert meta.name == "frontend-design", (
            f"Expected name 'frontend-design', got '{meta.name}'"
        )

    def test_frontmatter_description_is_nonempty(self) -> None:
        """AC3: parsed frontmatter description must be non-empty."""
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None
        assert meta.description, "Frontmatter description must not be empty"

    # ------------------------------------------------------------------
    # AC4: seven reference files exist under references/
    # ------------------------------------------------------------------

    def test_typography_reference_exists(self) -> None:
        """AC4: references/typography.md must exist."""
        assert (_REFERENCES_DIR / "typography.md").exists()

    def test_color_and_contrast_reference_exists(self) -> None:
        """AC4: references/color-and-contrast.md must exist."""
        assert (_REFERENCES_DIR / "color-and-contrast.md").exists()

    def test_spatial_design_reference_exists(self) -> None:
        """AC4: references/spatial-design.md must exist."""
        assert (_REFERENCES_DIR / "spatial-design.md").exists()

    def test_motion_design_reference_exists(self) -> None:
        """AC4: references/motion-design.md must exist."""
        assert (_REFERENCES_DIR / "motion-design.md").exists()

    def test_interaction_design_reference_exists(self) -> None:
        """AC4: references/interaction-design.md must exist."""
        assert (_REFERENCES_DIR / "interaction-design.md").exists()

    def test_responsive_design_reference_exists(self) -> None:
        """AC4: references/responsive-design.md must exist."""
        assert (_REFERENCES_DIR / "responsive-design.md").exists()

    def test_ux_writing_reference_exists(self) -> None:
        """AC4: references/ux-writing.md must exist."""
        assert (_REFERENCES_DIR / "ux-writing.md").exists()

    def test_all_seven_reference_files_exist(self) -> None:
        """AC4: all seven required reference files are present."""
        missing = [
            name
            for name in _EXPECTED_REFERENCE_FILES
            if not (_REFERENCES_DIR / name).exists()
        ]
        assert missing == [], f"Missing reference files: {missing}"
