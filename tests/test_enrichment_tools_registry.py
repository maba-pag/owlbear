"""Runtime integrity tests for enrichment tool routing and registration."""

from __future__ import annotations

import pytest

from owlbear_knowledge_mcp.server import mcp

_NEW_ENRICHMENT_NAMES: frozenset[str] = frozenset(
    {
        "claim_enrichment_batch",
        "store_enrichment",
        "retry_enrichment",
    }
)


async def _registered_tool_names() -> set[str]:
    """Return the set of tool names registered in the live MCP server."""
    return {tool.name for tool in await mcp.list_tools()}


class TestEnrichmentToolRename:
    """Smoke tests — one test per AC line (proof_bundle=smoke)."""

    def test_ac1_mcp_tool_routing_has_three_enrichment_entries(self) -> None:
        """AC1: MCP_TOOL_ROUTING contains 3 new enrichment entries with correct routing values."""
        from owlbear_knowledge.protocols.registry import MCP_TOOL_ROUTING  # noqa: PLC0415

        assert MCP_TOOL_ROUTING.get("claim_enrichment_batch") == "EnrichmentStore.claim_batch"
        assert MCP_TOOL_ROUTING.get("store_enrichment") == "EnrichmentStore.submit_extractions"
        assert MCP_TOOL_ROUTING.get("retry_enrichment") == "EnrichmentStore.reset_failed"

    def test_ac2_new_function_names_callable_and_in_all(self) -> None:
        """AC2: 3 enrichment functions renamed in server.py; new names callable and in __all__."""
        from owlbear_knowledge_mcp import server  # noqa: PLC0415

        assert callable(server.claim_enrichment_batch)
        assert callable(server.store_enrichment)
        assert callable(server.retry_enrichment)
        assert "claim_enrichment_batch" in server.__all__
        assert "store_enrichment" in server.__all__
        assert "retry_enrichment" in server.__all__
        assert "knowledge_enrichment_retry" not in server.__all__

    @pytest.mark.asyncio
    async def test_ac2_new_enrichment_names_in_live_mcp_registry(self) -> None:
        """AC2 (retry): all 3 new enrichment names appear in the live MCP registry.

        Callability and __all__ membership do not prove registry wiring; a broken
        implementation could export aliases in __all__ while the registry retains
        old names.  This test exercises the same registry introspection pattern as
        test_knowledge_tool_rename_1895.py.
        """
        registry = await _registered_tool_names()
        missing = _NEW_ENRICHMENT_NAMES - registry
        assert not missing, (
            f"New enrichment tool names missing from live MCP registry: {sorted(missing)}. "
            f"Registry snapshot: {sorted(n for n in registry if n)}"
        )
