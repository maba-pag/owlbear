"""Failing tests for task #43: Add argument-hint to user-invocable skills.

Covers: argument-hint key present in frontmatter, exact value, field placement
(frontmatter not body), and frontmatter-block structural integrity for both
project-definition and retro skill files.

All tests fail on current HEAD because neither
  .github/skills/project-definition/SKILL.md
  .github/skills/retro/SKILL.md
has an ``argument-hint`` key in its YAML frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROJECT_DEF_SKILL = ROOT / ".github" / "skills" / "project-definition" / "SKILL.md"
RETRO_SKILL = ROOT / ".github" / "skills" / "retro" / "SKILL.md"


def _get_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter text (between the first pair of --- delimiters)."""
    content = path.read_text(encoding="utf-8")
    # A frontmatter block starts and ends with a line of exactly "---"
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No frontmatter found in {path}")
    return match.group(1)


class TestFromAC_ProjectDefinitionArgumentHint:
    """AC: Add argument-hint to project-definition (value '[project name or idea]')."""

    def test_argument_hint_key_present(self) -> None:
        """project-definition SKILL.md frontmatter must contain an argument-hint key."""
        frontmatter = _get_frontmatter(PROJECT_DEF_SKILL)
        assert "argument-hint:" in frontmatter

    def test_argument_hint_value_correct(self) -> None:
        """argument-hint value must be exactly '[project name or idea]'."""
        frontmatter = _get_frontmatter(PROJECT_DEF_SKILL)
        assert "[project name or idea]" in frontmatter

    def test_argument_hint_value_no_extra_brackets(self) -> None:
        """argument-hint value must not embed extra text beyond the hint phrase."""
        frontmatter = _get_frontmatter(PROJECT_DEF_SKILL)
        line = next(
            (ln for ln in frontmatter.splitlines() if ln.startswith("argument-hint:")),
            None,
        )
        assert line is not None, "argument-hint key not found"
        # Value (stripped of key, quotes, whitespace) must be exactly the hint phrase
        value = line.split("argument-hint:", 1)[1].strip().strip('"').strip("'")
        assert value == "[project name or idea]", f"Unexpected value: {value!r}"

    def test_argument_hint_in_frontmatter_not_body(self) -> None:
        """argument-hint must be inside the opening frontmatter block, not in the body."""
        content = PROJECT_DEF_SKILL.read_text(encoding="utf-8")
        # Frontmatter is the region before the closing --- that follows the opening ---
        frontmatter = _get_frontmatter(PROJECT_DEF_SKILL)
        # The body is everything after the closing ---
        body_start = content.index("---\n", 4)  # skip the opening ---
        body = content[body_start + 4:]
        assert "argument-hint:" in frontmatter
        # Sanity: the body should not accidentally contain a bare key line
        body_lines_with_key = [
            ln for ln in body.splitlines() if ln.startswith("argument-hint:")
        ]
        assert body_lines_with_key == [], (
            "argument-hint key found in body, must be in frontmatter only"
        )


class TestFromAC_RetroArgumentHint:
    """AC: Add argument-hint to retro (value '[date range or sprint name]')."""

    def test_argument_hint_key_present(self) -> None:
        """retro SKILL.md frontmatter must contain an argument-hint key."""
        frontmatter = _get_frontmatter(RETRO_SKILL)
        assert "argument-hint:" in frontmatter

    def test_argument_hint_value_correct(self) -> None:
        """argument-hint value must be exactly '[date range or sprint name]'."""
        frontmatter = _get_frontmatter(RETRO_SKILL)
        assert "[date range or sprint name]" in frontmatter

    def test_argument_hint_value_no_extra_brackets(self) -> None:
        """argument-hint value must not embed extra text beyond the hint phrase."""
        frontmatter = _get_frontmatter(RETRO_SKILL)
        line = next(
            (ln for ln in frontmatter.splitlines() if ln.startswith("argument-hint:")),
            None,
        )
        assert line is not None, "argument-hint key not found"
        value = line.split("argument-hint:", 1)[1].strip().strip('"').strip("'")
        assert value == "[date range or sprint name]", f"Unexpected value: {value!r}"

    def test_argument_hint_in_frontmatter_not_body(self) -> None:
        """argument-hint must be inside the opening frontmatter block, not in the body."""
        frontmatter = _get_frontmatter(RETRO_SKILL)
        content = RETRO_SKILL.read_text(encoding="utf-8")
        body_start = content.index("---\n", 4)
        body = content[body_start + 4:]
        assert "argument-hint:" in frontmatter
        body_lines_with_key = [
            ln for ln in body.splitlines() if ln.startswith("argument-hint:")
        ]
        assert body_lines_with_key == [], (
            "argument-hint key found in body, must be in frontmatter only"
        )
