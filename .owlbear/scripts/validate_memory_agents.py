"""Validate memory provenance and scopes against active custom agents."""

from __future__ import annotations

import sys
from pathlib import Path

from owlbear_memory import MemoryEngine

from owlbear_memory_mcp.agents import AgentCatalog


def validate_memory_agents(workspace_root: Path) -> list[str]:
    """Return identity drift errors in the workspace memory store."""
    engine = MemoryEngine(workspace_root / ".owlbear/memory")
    return AgentCatalog(workspace_root).validate_entries(engine.get_entries())


def main() -> int:
    """Validate the current workspace and print actionable errors."""
    errors = validate_memory_agents(Path.cwd().resolve())
    for error in errors:
        sys.stderr.write(f"{error}\n")
    if not errors:
        print("PASS — memory agent references resolve to active custom agents")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
