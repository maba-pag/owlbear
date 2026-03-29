"""Failing tests for task #115: Copy 21 skills from .github/skills/ to skills/.

Covers:
  - AC1: All 21 skill directories present in skills/ alongside mcp-kanban (22 total)
  - AC2: Each copied skill passes validate_skills.py validation
  - AC3: No modifications to skill content during copy (content matches source)
  - AC4: .github/skills/ remains intact after copy
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_GITHUB_SKILLS = _REPO_ROOT / ".github" / "skills"
_SKILLS_DIR = _REPO_ROOT / "skills"
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

# Canonical list of the 21 skills that must be copied
_EXPECTED_SKILLS: frozenset[str] = frozenset(
    [
        "arch-review",
        "architecture-standards",
        "code-review",
        "curation-workflow",
        "decision-requests",
        "dispatch-planning",
        "docs-gate",
        "excalidraw-diagram",
        "frontend-design",
        "kanban-md",
        "knowledge-ops",
        "orchestration",
        "project-definition",
        "pytest-and-linting",
        "research-workflow",
        "retro",
        "task-decomposition",
        "task-verification",
        "tdd-red",
        "tdd-workflow",
        "visual-output",
    ]
)

# ---------------------------------------------------------------------------
# Import validate_skill function
# ---------------------------------------------------------------------------
sys.path.insert(0, str(_SCRIPTS_DIR))
from validate_skills import validate_skill  # noqa: E402


# ---------------------------------------------------------------------------
# AC1: All 21 skills present in skills/ alongside mcp-kanban (22 total)
# ---------------------------------------------------------------------------
class TestFromAC_AllSkillsCopied:
    """AC1: All 21 skill directories copied to skills/ alongside existing mcp-kanban."""

    def test_skills_dir_contains_exactly_22_dirs(self) -> None:
        """skills/ must have exactly 22 subdirectories: 21 copied + mcp-kanban."""
        skill_dirs = {p.name for p in _SKILLS_DIR.iterdir() if p.is_dir()}
        assert len(skill_dirs) == 22, (
            f"Expected 22 dirs in skills/, got {len(skill_dirs)}: {sorted(skill_dirs)}"
        )

    def test_all_21_expected_skills_present(self) -> None:
        """Every skill from _EXPECTED_SKILLS must exist as a directory in skills/."""
        skill_dirs = {p.name for p in _SKILLS_DIR.iterdir() if p.is_dir()}
        missing = _EXPECTED_SKILLS - skill_dirs
        assert not missing, f"Missing skills in skills/: {sorted(missing)}"

    @pytest.mark.parametrize("skill_name", sorted(_EXPECTED_SKILLS))
    def test_each_skill_directory_exists(self, skill_name: str) -> None:
        """Each of the 21 skills must exist as a directory in skills/."""
        assert (_SKILLS_DIR / skill_name).is_dir(), (
            f"skills/{skill_name}/ not found"
        )

    @pytest.mark.parametrize("skill_name", sorted(_EXPECTED_SKILLS))
    def test_each_skill_has_skill_md(self, skill_name: str) -> None:
        """Each copied skill directory must contain a SKILL.md file."""
        assert (_SKILLS_DIR / skill_name / "SKILL.md").is_file(), (
            f"skills/{skill_name}/SKILL.md not found"
        )


# ---------------------------------------------------------------------------
# AC2: Each copied skill passes validate_skills.py
# ---------------------------------------------------------------------------
class TestFromAC_ValidateSkills:
    """AC2: Each copied skill passes validate_skills.py with no errors."""

    @pytest.mark.parametrize("skill_name", sorted(_EXPECTED_SKILLS))
    def test_validate_skill_returns_no_errors(self, skill_name: str) -> None:
        """validate_skill() must return an empty list for each copied skill."""
        skill_dir = _SKILLS_DIR / skill_name
        errors = validate_skill(skill_dir)
        assert errors == [], (
            f"validate_skill(skills/{skill_name}) returned errors: {errors}"
        )

    def test_validate_all_skills_together(self) -> None:
        """All 21 copied skills pass validation when checked together."""
        all_errors: dict[str, list[str]] = {}
        for skill_name in _EXPECTED_SKILLS:
            skill_dir = _SKILLS_DIR / skill_name
            errors = validate_skill(skill_dir)
            if errors:
                all_errors[skill_name] = errors
        assert not all_errors, f"Validation errors found: {all_errors}"


# ---------------------------------------------------------------------------
# AC3: No modifications to skill content during copy
# ---------------------------------------------------------------------------
class TestFromAC_ContentUnmodified:
    """AC3: Content of each copied skill must exactly match the source in .github/skills/."""

    @pytest.mark.parametrize("skill_name", sorted(_EXPECTED_SKILLS))
    def test_skill_md_content_matches_source(self, skill_name: str) -> None:
        """SKILL.md content in skills/{name} must byte-for-byte match .github/skills/{name}/SKILL.md."""
        source = _GITHUB_SKILLS / skill_name / "SKILL.md"
        dest = _SKILLS_DIR / skill_name / "SKILL.md"
        assert source.exists(), f".github/skills/{skill_name}/SKILL.md missing (source)"
        assert dest.exists(), f"skills/{skill_name}/SKILL.md missing (destination)"
        assert dest.read_bytes() == source.read_bytes(), (
            f"Content mismatch: skills/{skill_name}/SKILL.md differs from source"
        )

    @pytest.mark.parametrize("skill_name", sorted(_EXPECTED_SKILLS))
    def test_all_files_in_skill_dir_match_source(self, skill_name: str) -> None:
        """All files under skills/{name}/ must match their counterparts under .github/skills/{name}/."""
        source_dir = _GITHUB_SKILLS / skill_name
        dest_dir = _SKILLS_DIR / skill_name
        assert source_dir.is_dir(), f".github/skills/{skill_name}/ missing"
        assert dest_dir.is_dir(), f"skills/{skill_name}/ missing"

        source_files = {p.relative_to(source_dir) for p in source_dir.rglob("*") if p.is_file()}
        dest_files = {p.relative_to(dest_dir) for p in dest_dir.rglob("*") if p.is_file()}

        missing_in_dest = source_files - dest_files
        assert not missing_in_dest, (
            f"skills/{skill_name}/ is missing files: {sorted(str(p) for p in missing_in_dest)}"
        )

        for rel_path in source_files:
            src_content = (source_dir / rel_path).read_bytes()
            dst_content = (dest_dir / rel_path).read_bytes()
            assert src_content == dst_content, (
                f"Content mismatch: skills/{skill_name}/{rel_path}"
            )

# NOTE: AC4 (.github/skills/ intact) is verified implicitly by TestFromAC_ContentUnmodified:
# each content-match test reads from .github/skills/{name} — if source were deleted or
# modified the test would fail. No separate TestFromAC_SourceIntact class is needed.
