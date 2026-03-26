"""Agent definition model — parse YAML frontmatter agent specs.

Each agent is defined by a markdown file with YAML frontmatter containing
identity fields (name, description, role) and a markdown body that becomes
the agent's system prompt.

Usage::

    from owlbear.core.agent_def import parse_agent_definition
    defn = parse_agent_definition(Path(".github/agents/builder.md"))
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["AgentDefinition", "parse_agent_definition"]

logger = logging.getLogger(__name__)


class AgentDefinition(BaseModel):
    """Pydantic model describing an agent's configuration.

    Fields are populated from YAML frontmatter (``name``, ``description``,
    ``role``, ``tools``, ``skills``, ``model``, ``max_delegation_depth``)
    and the markdown body (``system_prompt``).
    """

    name: str
    description: str
    role: str = "builder"
    tools: list[str] = []
    skills: list[str] = []
    model: str | None = None
    max_delegation_depth: int = 3
    system_prompt: str = ""


def parse_agent_definition(path: Path) -> AgentDefinition:
    """Parse an agent definition from a markdown file with YAML frontmatter.

    The file format is::

        ---
        name: builder
        description: Builds code via TDD
        role: builder
        tools:
          - file_read
          - file_write
        ---
        You are a builder agent.

    Args:
        path: Path to the ``.md`` agent definition file.

    Returns:
        Populated :class:`AgentDefinition`.

    Raises:
        ValueError: If frontmatter is missing, YAML is invalid, or
            required fields (``name``, ``description``) are absent.
    """
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        msg = f"No YAML frontmatter found in {path}"
        raise ValueError(msg)

    end = text.find("---", 3)
    if end == -1:
        msg = f"No closing frontmatter delimiter in {path}"
        raise ValueError(msg)

    raw_yaml = text[3:end]
    data = _safe_parse_yaml(raw_yaml, path)

    body = text[end + 3 :]
    body = body.removeprefix("\n")

    if "name" not in data:
        msg = f"Missing required field 'name' in {path}"
        raise ValueError(msg)
    if "description" not in data:
        msg = f"Missing required field 'description' in {path}"
        raise ValueError(msg)

    return AgentDefinition(
        name=str(data["name"]),
        description=str(data["description"]),
        role=str(data.get("role", "builder")),
        tools=[str(t) for t in data.get("tools", [])],
        skills=[str(s) for s in data.get("skills", [])],
        model=str(data["model"]) if data.get("model") is not None else None,
        max_delegation_depth=int(data.get("max_delegation_depth", 3)),
        system_prompt=body,
    )


def _safe_parse_yaml(raw: str, path: Path) -> dict:
    """Parse YAML string, raising :class:`ValueError` on failure."""
    try:
        result = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        msg = f"Invalid YAML frontmatter in {path}: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(result, dict):
        msg = f"YAML frontmatter is not a mapping in {path}"
        raise TypeError(msg)
    return result
