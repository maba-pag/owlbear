"""Discover canonical custom-agent identities from the active workspace."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from owlbear_memory import MemoryEntry

_DEFAULT_AGENT_DIRS = (Path(".github/agents"), Path(".owlbear/agents"), Path("share/agents"))
_FRONTMATTER_PART_COUNT = 3
_JSONC_LINE_COMMENT_RE = re.compile(r"(?<!:)//.*$", re.MULTILINE)


class AgentCatalog:
    """Canonical names discovered from active VS Code custom-agent files."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    def names(self) -> frozenset[str]:
        """Return exact frontmatter names from active agent directories."""
        names: set[str] = set()
        for directory in self._agent_directories():
            if not directory.is_dir():
                continue
            for path in directory.glob("*.agent.md"):
                name = self._read_name(path)
                if name:
                    names.add(name)
        return frozenset(names)

    def require(self, agent: str) -> None:
        """Reject an identity that is not an active custom-agent name."""
        if agent not in self.names():
            allowed = ", ".join(sorted(self.names())) or "none discovered"
            msg = f"Unknown agent {agent!r}. Active agents: {allowed}."
            raise ValueError(msg)

    def require_scope(self, agents: list[str]) -> None:
        """Reject scope values other than active names or the wildcard."""
        for agent in agents:
            if agent != "*":
                self.require(agent)

    def validate_entries(self, entries: list[MemoryEntry]) -> list[str]:
        """Return drift errors for provenance or scopes without active agents."""
        active = self.names()
        errors: list[str] = []
        for entry in entries:
            if entry.source_agent not in active:
                errors.append(f"{entry.id}: unknown source_agent {entry.source_agent!r}")
            unknown_scope = sorted(name for name in entry.scope_agents if name != "*" and name not in active)
            if unknown_scope:
                errors.append(f"{entry.id}: unknown scope_agents {unknown_scope}")
        return errors

    def _agent_directories(self) -> set[Path]:
        directories = {self._workspace_root / path for path in _DEFAULT_AGENT_DIRS}
        settings_path = self._workspace_root / ".vscode/settings.json"
        if not settings_path.is_file():
            return directories
        try:
            text = _JSONC_LINE_COMMENT_RE.sub("", settings_path.read_text(encoding="utf-8"))
            settings = json.loads(text)
        except OSError, json.JSONDecodeError:
            return directories
        locations = settings.get("chat.agentFilesLocations", {})
        if isinstance(locations, dict):
            for raw_path, enabled in locations.items():
                if enabled is True and isinstance(raw_path, str):
                    directories.add((self._workspace_root / raw_path).resolve())
        return directories

    @staticmethod
    def _read_name(path: Path) -> str | None:
        try:
            parts = path.read_text(encoding="utf-8").split("---", 2)
            metadata = yaml.safe_load(parts[1]) if len(parts) == _FRONTMATTER_PART_COUNT else None
        except OSError, yaml.YAMLError:
            return None
        if not isinstance(metadata, dict):
            return None
        name = metadata.get("name")
        return name.strip() if isinstance(name, str) and name.strip() else None
