"""Smoke tests for enrichment tool rename and MCP_TOOL_ROUTING additions (task #1901).

Source files under test:
  serve/knowledge/src/owlbear_knowledge/protocols/registry.py
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
  share/agents/knowledge-enricher.agent.md
  serve/mcp-knowledge/README.md
  share/skills/h-knowledge-ops/SKILL.md
  share/skills/w-knowledge-enrichment/SKILL.md
  share/prompts/kb-enrich.prompt.md
  tests/test_store_enrichment_phase1_1892.py
  tests/test_get_next_batch_1891.py

AC coverage:
  AC1 — MCP_TOOL_ROUTING in protocols/registry.py contains 3 new entries with correct
         routing values (EnrichmentStore.claim_batch / .submit_extractions / .reset_failed)
  AC2 — 3 enrichment functions renamed in server.py; new names callable, in __all__,
         and old names absent from __all__
  AC3 — Dead bare-function definition of retry_failed_enrichment removed; only one def
         per renamed tool remains in server.py
  AC4 — knowledge-enricher.agent.md tools allowlist updated to new names; old names absent
  AC5 — No old enrichment tool names remain in the 4 doc files
  AC6 — Affected test files import new symbol names; pytest collection succeeds on both
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parent.parent


class TestFromAC_EnrichmentToolRename:
    """Smoke tests — one test per AC line (proof_bundle=smoke)."""

    def test_ac1_mcp_tool_routing_has_three_enrichment_entries(self) -> None:
        """AC1: MCP_TOOL_ROUTING contains 3 new enrichment entries with correct routing values."""
        from owlbear_knowledge.protocols.registry import MCP_TOOL_ROUTING

        assert MCP_TOOL_ROUTING.get("knowledge_enrichment_claim_batch") == "EnrichmentStore.claim_batch"
        assert MCP_TOOL_ROUTING.get("knowledge_enrichment_store") == "EnrichmentStore.submit_extractions"
        assert MCP_TOOL_ROUTING.get("knowledge_enrichment_retry") == "EnrichmentStore.reset_failed"

    def test_ac2_new_function_names_callable_and_in_all(self) -> None:
        """AC2: 3 enrichment functions renamed in server.py; new names callable and in __all__."""
        from owlbear_mcp_knowledge import server

        assert callable(server.knowledge_enrichment_claim_batch)
        assert callable(server.knowledge_enrichment_store)
        assert callable(server.knowledge_enrichment_retry)
        assert "knowledge_enrichment_claim_batch" in server.__all__
        assert "knowledge_enrichment_store" in server.__all__
        assert "knowledge_enrichment_retry" in server.__all__
        assert "retry_failed_enrichment" not in server.__all__

    def test_ac3_dead_bare_retry_definition_removed(self) -> None:
        """AC3: Dead bare-function definition of retry_failed_enrichment removed; one def per renamed tool."""
        src = (_ROOT / "serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py").read_text()

        assert "def retry_failed_enrichment" not in src
        assert src.count("def knowledge_enrichment_retry") == 1

    def test_ac4_agent_file_allowlist_uses_new_names(self) -> None:
        """AC4: knowledge-enricher.agent.md tools allowlist and prose updated to new names."""
        content = (_ROOT / "share/agents/knowledge-enricher.agent.md").read_text()

        assert "ob-knowledge/knowledge_enrichment_claim_batch" in content
        assert "ob-knowledge/get_next_batch" not in content

    def test_ac5_doc_files_contain_no_old_enrichment_names(self) -> None:
        """AC5: No old enrichment tool names remain in the 4 affected doc files."""
        doc_files = [
            "serve/mcp-knowledge/README.md",
            "share/skills/h-knowledge-ops/SKILL.md",
            "share/skills/w-knowledge-enrichment/SKILL.md",
            "share/prompts/kb-enrich.prompt.md",
        ]
        old_names = ("get_next_batch", "store_enrichment", "retry_failed_enrichment")

        for doc_path in doc_files:
            content = (_ROOT / doc_path).read_text()
            for old_name in old_names:
                assert old_name not in content, (
                    f"Old enrichment tool name '{old_name}' still present in {doc_path}"
                )

    def test_ac6_affected_test_files_use_new_import_names(self) -> None:
        """AC6: test_get_next_batch_1891.py and test_store_enrichment_phase1_1892.py import new names."""
        expected_new_names = {
            "tests/test_get_next_batch_1891.py": "knowledge_enrichment_claim_batch",
            "tests/test_store_enrichment_phase1_1892.py": "knowledge_enrichment_store",
        }

        for test_file, new_name in expected_new_names.items():
            content = (_ROOT / test_file).read_text()
            assert new_name in content, (
                f"New symbol '{new_name}' not found in {test_file}"
            )
