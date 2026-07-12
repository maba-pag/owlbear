"""Regression tests for shared and project-local architecture authority boundaries."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_ARCHITECTURE_INSTRUCTIONS = _REPO_ROOT / ".owlbear/instructions/architecture.instructions.md"
_MCP_INSTRUCTIONS = _REPO_ROOT / ".owlbear/instructions/mcp-server.instructions.md"
_MODULE_DESIGN = _REPO_ROOT / "share/skills/h-module-design/SKILL.md"


def test_project_architecture_instruction_owns_serve_topology() -> None:
    """Concrete package topology remains local to the OwlBear source repository."""
    content = _ARCHITECTURE_INSTRUCTIONS.read_text(encoding="utf-8")

    assert 'applyTo: "serve/**"' in content
    for contract in ("## Architecture Overview", "## Dependency Rules", "## Domain Scope Map"):
        assert contract in content
    assert "serve/mcp-kanban/" in content
    assert "serve/knowledge/" in content


def test_module_design_skill_contains_only_portable_diagnostics() -> None:
    """Consuming projects receive module diagnostics without OwlBear package policy."""
    content = _MODULE_DESIGN.read_text(encoding="utf-8")

    for contract in (
        "## Module Quality Vocabulary",
        "## Deletion Test",
        "## Interface Is the Test Surface",
        "## Seam Discipline",
        "## Dependency Classification",
    ):
        assert contract in content
    for local_detail in ("serve/", "ToolError", "AppContext", "mcp-kanban"):
        assert local_detail not in content


def test_mcp_instruction_owns_server_implementation_contracts() -> None:
    """OwlBear MCP implementation rules auto-load only for MCP server source."""
    content = _MCP_INSTRUCTIONS.read_text(encoding="utf-8")

    assert 'applyTo: "serve/mcp-*/**"' in content
    for contract in ("ToolError", "readOnlyHint", "AppContext", "server.py", "__all__"):
        assert contract in content
