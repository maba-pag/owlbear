"""Regression coverage for the shipped Knowledge source lifecycle contract."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest
import yaml

from owlbear_knowledge.protocols.sources import SourceRegistration, SourceState
from owlbear_knowledge.stores.sources import SqliteSourceStore


_ROOT = Path(__file__).resolve().parents[1]
_AGENT_PATH = _ROOT / "share/agents/knowledge-ingestor.agent.md"
_PROMPT_PATH = _ROOT / "share/prompts/kb-ingest.prompt.md"
_HANDBOOK_PATH = _ROOT / "share/skills/h-knowledge-ops/SKILL.md"
_WORKFLOW_PATH = _ROOT / ".github/workflows/knowledge-source-contracts.yml"
_REGISTRATION_FIELDS = {
    "name",
    "kind",
    "fetch_method",
    "config",
    "scope",
    "enrich",
    "refreshable",
    "priority",
    "metadata",
}
_REQUIRED_MARKERS = {
    "knowledge-registration-url-list",
    "knowledge-registration-file-glob",
}
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


def _registration_payloads() -> list[dict[str, object]]:
    handbook = _HANDBOOK_PATH.read_text(encoding="utf-8")
    section = handbook.split("## Registration Payload Examples", maxsplit=1)[1].split("## ", maxsplit=1)[0]
    fenced_payloads = re.findall(r"```json ([^\n]+)\n(.*?)\n```", section, flags=re.DOTALL)
    assert fenced_payloads

    payloads: list[dict[str, object]] = []
    markers: set[str] = set()
    for marker, raw_payload in fenced_payloads:
        assert marker.startswith("knowledge-registration-")
        parsed = json.loads(raw_payload)
        assert isinstance(parsed, dict)
        assert parsed.keys() >= _REGISTRATION_FIELDS
        assert isinstance(parsed["config"], dict)
        assert isinstance(parsed["metadata"], dict)
        markers.add(marker)
        payloads.append(parsed)

    assert markers >= _REQUIRED_MARKERS
    return payloads


def test_shipped_role_and_prompt_declare_source_lifecycle_contract() -> None:
    frontmatter = _frontmatter(_AGENT_PATH)
    tools = frontmatter["tools"]
    assert isinstance(tools, list)
    assert {"owlbear-knowledge/register_knowledge_source", "owlbear-knowledge/delete_knowledge_source"} <= set(tools)

    agent = _AGENT_PATH.read_text(encoding="utf-8")
    for field in ("id", "name", "state", "kind", "scope"):
        assert field in agent
    for field in ("status", "completed_steps", "failed_step", "error", "source", "content", "enrichment", "graph"):
        assert field in agent

    prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    for declaration in ("Registers sources", "intentionally deletes", "operation-specific result"):
        assert declaration in prompt


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


def test_handbook_documents_current_source_contract_and_valid_payloads() -> None:
    handbook = _HANDBOOK_PATH.read_text(encoding="utf-8")
    for declaration in (
        "### register_knowledge_source",
        "### delete_knowledge_source",
        "Agent tool allowlists own callability",
        "purge summary with `status`, `completed_steps`, `failed_step`, `error`, `source`, `content`, `enrichment`, and `graph`",
    ):
        assert declaration in handbook
    assert "## Config Examples per Source Type" not in handbook

    _registration_payloads()


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

    steps = job["steps"]
    assert steps[0]["uses"] == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    assert steps[1]["uses"] == "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9"
    assert steps[1]["with"] == {
        "cache-dependency-glob": "uv.lock",
        "enable-cache": True,
    }
    assert [step["run"] for step in steps[2:]] == [
        "uv python install",
        "uv run python .owlbear/scripts/validate_agents.py",
        "uv run --frozen pytest -q tests/test_knowledge_ops_contract.py",
    ]


def test_registration_examples_validate_and_persist_as_active_sources() -> None:
    store = SqliteSourceStore(sqlite3.connect(":memory:"))
    store.ensure_tables()

    for payload in _registration_payloads():
        registration = SourceRegistration.model_validate(payload, strict=False)
        persisted = store.register_source(registration)
        assert persisted.state is SourceState.ACTIVE
        assert persisted.kind is registration.kind
        assert persisted.scope == registration.scope


def test_store_rejects_outer_and_config_kind_mismatch() -> None:
    registration = SourceRegistration.model_validate(
        {
            "name": "Mismatched source",
            "kind": "file_glob",
            "fetch_method": "filesystem",
            "config": {"kind": "url_list", "urls": ["https://example.com"]},
        },
        strict=False,
    )
    store = SqliteSourceStore(sqlite3.connect(":memory:"))
    store.ensure_tables()

    with pytest.raises(ValueError, match="config kind mismatch"):
        store.register_source(registration)


@pytest.mark.asyncio
async def test_live_mcp_registry_exposes_source_lifecycle_tools() -> None:
    from owlbear_knowledge_mcp.server import mcp

    names = {tool.name for tool in await mcp.list_tools()}
    assert names >= {"register_knowledge_source", "delete_knowledge_source"}
