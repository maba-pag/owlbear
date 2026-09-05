"""Regression coverage for current Knowledge source platform identities."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_AGENT_PATH = _ROOT / "share/agents/knowledge-ingestor.agent.md"
_HANDBOOK_PATH = _ROOT / "share/skills/h-knowledge-ops/SKILL.md"
_FAILURE_FIELDS = ("stage", "code", "retryable", "message")
_FAILURE_STAGES = ("acquisition", "extraction", "indexing", "persistence", "query")
_FAILURE_CODES = (
    "url_rejected",
    "dns_failure",
    "transport_failure",
    "http_status",
    "timeout",
    "response_too_large",
    "unsupported_media_type",
    "content_boundary_missing",
    "extraction_failed",
    "persistence_failed",
    "embedding_failed",
    "vector_write_failed",
    "query_embedding_failed",
    "vector_query_failed",
)


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


def test_handbook_documents_typed_search_and_refresh_unions() -> None:
    handbook = _HANDBOOK_PATH.read_text(encoding="utf-8")
    search_section = handbook.split("### knowledge_search", 1)[1].split("### knowledge_ingest", 1)[0]
    refresh_section = handbook.split("### refresh_knowledge_source", 1)[1].split("### register_knowledge_source", 1)[0]

    assert "list[dict] | KnowledgeFailure" in search_section
    assert "An empty `[]` is a successful no-match result." in search_section
    assert all(f"`{field}`" in search_section for field in _FAILURE_FIELDS)
    assert "ToolError" in search_section
    assert "error string" not in search_section.lower()
    assert "error: ..." not in search_section

    assert "KnowledgeFailure" in refresh_section
    assert all(field in refresh_section for field in ("source_id", "sources_refreshed", "documents_created"))
    assert all(f"`{field}`" in refresh_section for field in _FAILURE_FIELDS)
    assert "Partial URL-list success" in refresh_section
    assert "error-free no-op" in refresh_section
    assert "ToolError" in refresh_section
    assert "error string" not in refresh_section.lower()
    assert "error: ..." not in refresh_section


def test_handbook_enumerates_typed_failure_literals_and_fail_closed_extraction() -> None:
    handbook = _HANDBOOK_PATH.read_text(encoding="utf-8")

    assert all(f"`{stage}`" in handbook for stage in _FAILURE_STAGES)
    assert all(f"`{code}`" in handbook for code in _FAILURE_CODES)
    assert "authoritative boolean" in handbook
    assert "redacted operational summary" in handbook
    assert "no document for persistence" in handbook


def test_knowledge_ingestor_reports_structured_failures_without_claiming_success() -> None:
    agent = _AGENT_PATH.read_text(encoding="utf-8")
    output_format = agent.split("<output_format>", 1)[1].split("</output_format>", 1)[0]
    channel_a = output_format.split("### Channel A", 1)[1].split("### Channel B", 1)[0]
    channel_b = output_format.split("### Channel B", 1)[1]

    assert all(f"`{field}`" in channel_a for field in _FAILURE_FIELDS)
    assert "per-source failures" in channel_a
    assert "Never parse operational text" in agent
    assert all(stage in channel_a for stage in ("acquisition", "extraction", "persistence", "indexing", "query"))
    assert "error string" not in agent.lower()
    assert "knowledge_search" not in channel_b
    assert "Not applicable" in channel_b


@pytest.mark.asyncio
async def test_live_mcp_registry_exposes_source_lifecycle_tools() -> None:
    from owlbear_knowledge_mcp.server import mcp  # noqa: PLC0415

    names = {tool.name for tool in await mcp.list_tools()}
    assert names >= {"register_knowledge_source", "delete_knowledge_source"}
