"""Stub: skills_ref.parser — not yet implemented (task #84)."""

from __future__ import annotations

from pathlib import Path


def find_skill_md(skill_dir: Path) -> Path | None:
    """Return the SKILL.md path in skill_dir, or None if absent."""
    candidate = Path(skill_dir) / "SKILL.md"
    return candidate if candidate.exists() else None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from content.  Stub — raises NotImplementedError."""
    raise NotImplementedError("parse_frontmatter not yet implemented (task #84)")
