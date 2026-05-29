"""skills_ref.parser — YAML frontmatter parsing for SKILL.md files."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML, YAMLError

from skills_ref.errors import ParseError

_ERR_NO_FRONTMATTER = "No YAML frontmatter found: content does not start with '---'"
_ERR_UNCLOSED = "Unclosed frontmatter: no closing '---' delimiter found"
_ERR_NOT_MAPPING = "Frontmatter must be a YAML mapping"


def find_skill_md(skill_dir: Path) -> Path | None:
    """Return the SKILL.md path in skill_dir, or None if absent."""
    candidate = Path(skill_dir) / "SKILL.md"
    return candidate if candidate.exists() else None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter delimited by '---' from content.

    Args:
        content: Full text of a SKILL.md file.

    Returns:
        Tuple of (metadata dict, body text).

    Raises:
        ParseError: If frontmatter delimiters are missing or YAML is invalid.
    """
    if not content.startswith("---"):
        raise ParseError(_ERR_NO_FRONTMATTER)

    after_open = content[3:].lstrip("\n")
    close_idx = after_open.find("\n---")
    if close_idx == -1:
        raise ParseError(_ERR_UNCLOSED)

    yaml_text = after_open[:close_idx]
    body = after_open[close_idx + 4 :]

    try:
        yaml = YAML(typ="safe")
        data = yaml.load(yaml_text)
    except YAMLError as exc:
        msg = f"YAML parse error: {exc}"
        raise ParseError(msg) from exc

    if not isinstance(data, dict):
        raise ParseError(_ERR_NOT_MAPPING)

    return data, body
