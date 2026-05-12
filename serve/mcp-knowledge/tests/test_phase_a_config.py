"""Failing tests for task #16: mcp-knowledge server Phase A configuration.

Covers AC items not tested by prior test tasks (#104, #55, #152):
  - Package config: pyproject.toml for mcp-knowledge declares owlbear-knowledge dependency
  - Integration: .vscode/mcp.json registers the owlbear-knowledge MCP server
  - Docs gate: skills/knowledge-ops/SKILL.md documents the MCP search_knowledge tool

All tests fail (RED phase) against the current codebase because:
  - pyproject.toml only has mcp[cli]>=1.26, not owlbear-knowledge
  - .vscode/mcp.json has no owlbear_mcp_knowledge entry
  - SKILL.md documents PydanticAI runtime tools, not the MCP server tools
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

# ---------------------------------------------------------------------------
# Path helpers — resolve relative to this file so tests work from any cwd
# ---------------------------------------------------------------------------

_PKG_ROOT = Path(__file__).parent.parent  # packages/mcp-knowledge/
_REPO_ROOT = _PKG_ROOT.parent.parent  # owlbear/


# ---------------------------------------------------------------------------
# TestFromAC_PackageConfiguration
# ---------------------------------------------------------------------------


class TestFromAC_PackageConfiguration:
    """Contract tests for pyproject.toml dependency declarations (AC: Package configuration)."""

    def test_pyproject_declares_owlbear_knowledge_dependency(self) -> None:
        """packages/mcp-knowledge/pyproject.toml lists owlbear-knowledge in [project.dependencies]."""
        pyproject_path = _PKG_ROOT / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"
        with pyproject_path.open("rb") as fh:
            data = tomllib.load(fh)
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        assert any("owlbear-knowledge" in dep for dep in deps), (
            f"'owlbear-knowledge' not found in [{pyproject_path}] dependencies: {deps}\n"
            "AC requires: add owlbear-knowledge to [project.dependencies] so the "
            "package properly declares its runtime dependency on the knowledge engine."
        )


# ---------------------------------------------------------------------------
# TestFromAC_McpJsonRegistration
# ---------------------------------------------------------------------------


class TestFromAC_McpJsonRegistration:
    """Contract tests for .vscode/mcp.json MCP server registration (AC: Integration)."""

    def test_vscode_mcp_json_registers_knowledge_server(self) -> None:
        """The workspace .vscode/mcp.json has an entry that runs owlbear_mcp_knowledge."""
        mcp_json = _REPO_ROOT / ".vscode" / "mcp.json"
        assert mcp_json.exists(), (
            f".vscode/mcp.json not found at {mcp_json}. "
            "AC requires: Register server in .vscode/mcp.json (create file if absent)."
        )
        data = json.loads(mcp_json.read_text(encoding="utf-8"))
        servers: dict = data.get("servers", {})
        knowledge_server = next(
            (v for v in servers.values() if "owlbear_mcp_knowledge" in str(v)),
            None,
        )
        assert knowledge_server is not None, (
            f"No owlbear_mcp_knowledge entry found in .vscode/mcp.json 'servers'.\n"
            f"Registered servers: {list(servers.keys())}\n"
            "AC requires: add an owlbear-knowledge stdio server entry to .vscode/mcp.json."
        )


# ---------------------------------------------------------------------------
# TestFromAC_SkillMdUpdate
# ---------------------------------------------------------------------------


class TestFromAC_SkillMdUpdate:
    """Contract tests for skills/knowledge-ops/SKILL.md MCP tool documentation (AC: Integration)."""

    def test_skill_md_documents_search_knowledge_mcp_tool(self) -> None:
        """skills/knowledge-ops/SKILL.md mentions the MCP search_knowledge tool by name."""
        skill_path = _REPO_ROOT / "share" / "skills" / "h-knowledge-ops" / "SKILL.md"
        assert skill_path.exists(), f"SKILL.md not found at {skill_path}"
        content = skill_path.read_text(encoding="utf-8")
        assert "search_knowledge" in content, (
            "skills/knowledge-ops/SKILL.md does not document the MCP search_knowledge tool.\n"
            "AC requires: Update SKILL.md with MCP server tool descriptions. "
            "The file currently documents PydanticAI runtime tools (query_knowledge, etc.); "
            "it must be updated to reflect the owlbear-knowledge MCP server tools "
            "(search_knowledge, ingest_document, list_entities, list_sources, get_stats)."
        )
