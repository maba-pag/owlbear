"""Regression coverage for current Knowledge source platform identities."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


_ROOT = Path(__file__).resolve().parents[1]
_AGENT_PATH = _ROOT / "share/agents/knowledge-ingestor.agent.md"
_HANDBOOK_PATH = _ROOT / "share/skills/h-knowledge-ops/SKILL.md"
_WORKFLOW_PATH = _ROOT / ".github/workflows/knowledge-source-contracts.yml"
_WORKFLOW_PATHS = {
    ".owlbear/scripts/validate_agents.py",
    ".github/workflows/knowledge-source-contracts.yml",
    ".python-version",
    "conftest.py",
    "pyproject.toml",
    "serve/knowledge/**",
    "serve/knowledge-mcp/**",
    "share/agents/knowledge-ingestor.agent.md",
    "share/prompts/kb-ingest.prompt.md",
    "share/skills/h-knowledge-ops/SKILL.md",
    "tests/test_knowledge_ops_contract.py",
    "uv.lock",
}


def _frontmatter(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", raw, flags=re.DOTALL)
    assert match is not None
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


def test_knowledge_ingestor_uses_canonical_platform_identities() -> None:
    tools = _frontmatter(_AGENT_PATH)["tools"]
    assert isinstance(tools, list)
    assert {
        "owlbear-browser/acquire",
        "owlbear-memory/recall_memory",
        "owlbear-memory/save_memory",
    } <= set(tools)
    assert all(not tool.startswith("ob-") for tool in tools)


def test_handbook_documents_current_server_and_storage_contract() -> None:
    handbook = _HANDBOOK_PATH.read_text(encoding="utf-8")
    assert "`owlbear-knowledge` MCP server" in handbook
    assert "`.owlbear/knowledge/local.db`" in handbook
    assert "`.owlbear/knowledge/vectors`" in handbook
    assert "KNOWLEDGE_TOOLS_EXCLUDE" not in handbook


def test_source_contract_workflow_is_dev_only_and_canonical() -> None:
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    assert workflow["permissions"] == {}

    triggers = workflow["on"]
    assert isinstance(triggers, dict)
    for event in ("pull_request", "push"):
        event_filter = triggers[event]
        assert event_filter["branches"] == ["dev"]
        assert set(event_filter["paths"]) == _WORKFLOW_PATHS

    job = workflow["jobs"]["knowledge-source-contracts"]
    assert job["if"] == "github.repository == 'maba-pag/owlbear'"
    assert job["permissions"] == {"contents": "read"}
    assert job["runs-on"] == "ubuntu-latest"
    assert job["timeout-minutes"] == 15


@pytest.mark.asyncio
async def test_live_mcp_registry_exposes_source_lifecycle_tools() -> None:
    from owlbear_knowledge_mcp.server import mcp

    names = {tool.name for tool in await mcp.list_tools()}
    assert names >= {"register_knowledge_source", "delete_knowledge_source"}
