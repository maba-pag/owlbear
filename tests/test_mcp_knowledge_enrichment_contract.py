"""Behavioral contract tests for MCP knowledge enrichment payloads."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_mcp_knowledge.server import knowledge_stats, store_enrichment


def _context(enrichment_store: MagicMock) -> MagicMock:
    context = MagicMock()
    context.request_context.lifespan_context = SimpleNamespace(enrichment_store=enrichment_store)
    return context


@pytest.mark.asyncio
async def test_store_enrichment_accepts_documented_local_reference_payload() -> None:
    """Entities expose local IDs that relations use as endpoints."""
    enrichment_store = MagicMock()

    await store_enrichment(
        _context(enrichment_store),
        chunk_id="chunk-1",
        entities=[
            {
                "id": "azure-devops",
                "name": "Azure DevOps",
                "entity_type": "technology",
                "description": "Source control and work tracking platform",
                "confidence": 0.9,
                "metadata": {"alias": "AzDO"},
            },
            {
                "id": "ci-cd-pipeline",
                "name": "CI/CD Pipeline",
                "entity_type": "process",
                "description": "Build and deployment pipeline hosted in Azure DevOps",
                "confidence": 0.9,
                "metadata": {},
            },
        ],
        edges=[
            {
                "source_id": "ci-cd-pipeline",
                "target_id": "azure-devops",
                "relation": "belongs_to",
                "weight": 0.7,
                "confidence": 0.9,
                "metadata": {},
            }
        ],
    )

    enrichment_store.submit_extractions.assert_called_once()
    entities, relations = enrichment_store.submit_extractions.call_args.args[1:]
    assert [entity.local_ref for entity in entities] == ["azure-devops", "ci-cd-pipeline"]
    assert [(relation.source_ref, relation.target_ref) for relation in relations] == [
        ("ci-cd-pipeline", "azure-devops")
    ]


@pytest.mark.asyncio
async def test_store_enrichment_rejects_entity_without_local_id() -> None:
    """Missing local references fail before any extraction is persisted."""
    enrichment_store = MagicMock()

    with pytest.raises(ToolError, match="entity id is required"):
        await store_enrichment(
            _context(enrichment_store),
            chunk_id="chunk-1",
            entities=[{"name": "Azure DevOps", "entity_type": "system"}],
            edges=[],
        )

    enrichment_store.mark_failed.assert_called_once_with("chunk-1", "entity id is required")
    enrichment_store.submit_extractions.assert_not_called()


@pytest.mark.asyncio
async def test_knowledge_stats_reports_enrichment_state_without_consolidation() -> None:
    """Stats expose the maintained extraction queue rather than a removed workflow."""
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = (3,)
    ingest_coordinator = MagicMock()
    ingest_coordinator.stats.return_value = SimpleNamespace(
        documents_total=5,
        graph_entities=8,
        graph_edges=7,
        sources_total=2,
        chunks_total=10,
    )
    enrichment_store = MagicMock()
    enrichment_store.stats.return_value = SimpleNamespace(
        pending=2,
        in_progress=1,
        failed=1,
        completed=6,
    )
    context = MagicMock()
    context.request_context.lifespan_context = SimpleNamespace(
        conn=connection,
        ingest_coordinator=ingest_coordinator,
        enrichment_store=enrichment_store,
    )

    result = await knowledge_stats(context)

    assert result == {
        "documents": 5,
        "entities": 8,
        "edges": 7,
        "total_sources": 2,
        "total_chunks": 10,
        "chunks_pending": 2,
        "chunks_claimed": 1,
        "chunks_failed": 1,
        "chunks_enriched": 6,
        "chunks_claimable": 3,
        "chunks_enriched_ratio": 0.6,
    }
