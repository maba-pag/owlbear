"""skills_ref.errors — custom exception types for skills_ref."""

from __future__ import annotations


class ParseError(Exception):
    """Raised when SKILL.md frontmatter cannot be parsed."""
