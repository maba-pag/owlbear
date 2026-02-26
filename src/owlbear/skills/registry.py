"""SkillRegistry — progressive-loading toolset for markdown skills.

Skills are markdown files with YAML frontmatter (``name``, ``description``).
At init only frontmatter is parsed (summaries). Full content is loaded on
demand via the ``load_skill`` tool, keeping token budgets small.

Usage::

    from owlbear.skills.registry import SkillRegistry
    skills = SkillRegistry(Path(".github/skills"))
    agent = Agent("model", toolsets=[skills])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml
from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["SkillMeta", "SkillRegistry"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SkillMeta:
    """Lightweight metadata extracted from skill YAML frontmatter."""

    name: str
    description: str
    file_path: Path


class SkillRegistry(FunctionToolset):
    """Progressive-loading registry backed by :class:`FunctionToolset`.

    Scans *skills_dir* for ``*.md`` files with YAML frontmatter and
    registers two tools on itself:

    * **list_skills** — returns a summary of all available skills.
    * **load_skill** — loads the full content of a skill by name.
    """

    def __init__(self, skills_dir: Path) -> None:
        super().__init__()
        self._skills_dir = skills_dir
        self._skill_map: dict[str, SkillMeta] = {}
        self._scan()

        # Register tools on this toolset so an Agent sees them.
        self.add_function(
            self._list_skills_tool,
            name="list_skills",
            description="List available skills with their descriptions.",
        )
        self.add_function(
            self._load_skill_tool,
            name="load_skill",
            description=(
                "Load the full content of a skill by name. "
                "Use list_skills first to discover available names."
            ),
        )

    # ------------------------------------------------------------------
    # Public helpers (non-tool access for code that holds the registry)
    # ------------------------------------------------------------------

    @property
    def skills(self) -> dict[str, SkillMeta]:
        """Read-only view of registered skill metadata."""
        return dict(self._skill_map)

    def list_skills(self) -> str:
        """Return a plain-text summary of all skills."""
        return self._list_skills_tool()

    def load_skill(self, *, name: str) -> str:
        """Load full skill content by *name*.

        Raises:
            KeyError: If *name* is not registered.
        """
        return self._load_skill_tool(name=name)

    # ------------------------------------------------------------------
    # Tool implementations (registered on FunctionToolset)
    # ------------------------------------------------------------------

    def _list_skills_tool(self) -> str:
        if not self._skill_map:
            return "No skills available."
        lines = [
            f"- **{m.name}**: {m.description}"
            for m in sorted(self._skill_map.values(), key=lambda m: m.name)
        ]
        return "\n".join(lines)

    def _load_skill_tool(self, name: str) -> str:
        meta = self._skill_map.get(name)
        if meta is None:
            available = ", ".join(sorted(self._skill_map))
            msg = f"Skill '{name}' not found. Available: {available}"
            raise KeyError(msg)
        return meta.file_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _scan(self) -> None:
        """Walk *skills_dir* for ``*.md`` files with valid frontmatter."""
        if not self._skills_dir.is_dir():
            logger.debug(
                "Skills directory does not exist: %s",
                self._skills_dir,
            )
            return

        for md_path in sorted(self._skills_dir.glob("*.md")):
            meta = self._parse_frontmatter(md_path)
            if meta is not None:
                self._skill_map[meta.name] = meta
                logger.debug("Registered skill: %s", meta.name)

    @staticmethod
    def _parse_frontmatter(path: Path) -> SkillMeta | None:
        """Extract YAML frontmatter from a markdown file.

        Returns ``None`` when frontmatter is missing or invalid.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("Cannot read skill file: %s", path)
            return None

        if not text.startswith("---"):
            return None

        end = text.find("---", 3)
        if end == -1:
            return None

        data = _safe_parse_yaml(text[3:end], path)
        if not isinstance(data, dict) or not data.get("name"):
            return None

        return SkillMeta(
            name=str(data["name"]),
            description=str(data.get("description", "")),
            file_path=path,
        )


def _safe_parse_yaml(raw: str, path: Path) -> dict | None:
    """Parse YAML, returning ``None`` on failure."""
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError:
        logger.warning("Invalid YAML frontmatter in %s", path)
        return None
