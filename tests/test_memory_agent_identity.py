"""Behavioral tests for memory agent identity discovery and validation."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_memory import MemoryCategory, MemoryEngine
from owlbear_memory_mcp.agents import AgentCatalog
from owlbear_memory_mcp.tools import delete_agent_memories, rename_agent_memories, save_memory


def _write_agent(directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.agent.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")


def _make_ctx(engine: MemoryEngine, catalog: AgentCatalog) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = SimpleNamespace(engine=engine, agents=catalog)
    return ctx


def _save(engine: MemoryEngine, *, source: str, scope: list[str]) -> str:
    entry = engine.save(
        title=f"Lesson from {source}",
        content="Specific reusable lesson.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent=source,
        scope_agents=scope,
    )
    return entry.id


def test_catalog_discovers_shared_workspace_and_configured_local_agents(tmp_path: Path) -> None:
    _write_agent(tmp_path / "share/agents", "builder")
    _write_agent(tmp_path / ".github/agents", "security-reviewer")
    external = tmp_path.parent / f"{tmp_path.name}-agents"
    _write_agent(external, "project-planner")
    settings = {
        "chat.agentFilesLocations": {
            "share/agents": True,
            ".github/agents": True,
            str(external): True,
            "disabled": False,
        }
    }
    settings_path = tmp_path / ".vscode/settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text("// active agent roots\n" + json.dumps(settings), encoding="utf-8")

    catalog = AgentCatalog(tmp_path)

    assert catalog.names() == {"builder", "security-reviewer", "project-planner"}
    catalog.require("security-reviewer")
    catalog.require_scope(["builder", "*"])


def test_catalog_rejects_host_product_identity(tmp_path: Path) -> None:
    _write_agent(tmp_path / "share/agents", "builder")

    with pytest.raises(ValueError, match="Unknown agent 'GitHub Copilot'"):
        AgentCatalog(tmp_path).require("GitHub Copilot")


def test_catalog_reports_source_and_scope_drift(tmp_path: Path) -> None:
    _write_agent(tmp_path / "share/agents", "builder")
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    entry_id = _save(engine, source="GitHub Copilot", scope=["builder", "verifier"])

    assert AgentCatalog(tmp_path).validate_entries(engine.get_entries()) == [
        f"{entry_id}: unknown source_agent 'GitHub Copilot'",
        f"{entry_id}: unknown scope_agents ['verifier']",
    ]


@pytest.mark.asyncio
async def test_save_rejects_host_identity_and_defaults_to_unscoped(tmp_path: Path) -> None:
    _write_agent(tmp_path / "share/agents", "builder")
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    ctx = _make_ctx(engine, AgentCatalog(tmp_path))

    with pytest.raises(ToolError, match="Unknown agent 'GitHub Copilot'"):
        await save_memory(
            ctx,
            title="Bad provenance",
            content="Should not persist.",
            categories=[MemoryCategory.PITFALL],
            confidence=0.8,
            source_agent="GitHub Copilot",
        )

    result = await save_memory(
        ctx,
        title="Valid provenance",
        content="Curator decides the audience.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="builder",
    )

    assert result["scope_agents"] == []
    assert len(engine.get_entries()) == 1

    with pytest.raises(TypeError, match="scope_agents"):
        await save_memory(
            ctx,
            title="Producer-assigned scope",
            content="Writers cannot select an audience.",
            categories=[MemoryCategory.PROCESS],
            confidence=0.8,
            source_agent="builder",
            scope_agents=["builder"],  # type: ignore[call-arg]
        )


@pytest.mark.asyncio
async def test_rename_agent_rewrites_sources_and_scopes(tmp_path: Path) -> None:
    _write_agent(tmp_path / "share/agents", "build-reviewer")
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    _save(engine, source="verifier", scope=["verifier", "builder"])
    _save(engine, source="builder", scope=["verifier"])

    result = await rename_agent_memories(
        _make_ctx(engine, AgentCatalog(tmp_path)),
        old_name="verifier",
        new_name="build-reviewer",
    )

    assert result == {"entries_updated": 2, "sources_updated": 1, "scopes_updated": 2}
    entries = engine.get_entries()
    assert {entry.source_agent for entry in entries} == {"build-reviewer", "builder"}
    assert all("verifier" not in entry.scope_agents for entry in entries)


@pytest.mark.asyncio
async def test_delete_agent_removes_sourced_and_scope_orphaned_memories(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    sourced_id = _save(engine, source="verifier", scope=["builder"])
    orphaned_id = _save(engine, source="builder", scope=["verifier"])
    retained_id = _save(engine, source="builder", scope=["builder", "verifier"])

    result = await delete_agent_memories(
        _make_ctx(engine, AgentCatalog(tmp_path)),
        agent="verifier",
    )

    assert result == {"entries_deleted": 2, "scopes_updated": 1}
    entries = {entry.id: entry for entry in engine.get_entries()}
    assert sourced_id not in entries
    assert orphaned_id not in entries
    assert entries[retained_id].scope_agents == ["builder"]
