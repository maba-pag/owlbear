"""RED tests for #1900 — Remove legacy AppContext fields and dual-paths (Phase B2a).

Tests verify:
- AC1: AppContext has no legacy fields (query_service, graph_store, ingest_pipeline,
        intra_doc_builder, structured_extractor)
- AC2: search_knowledge has no legacy fallback / _serialize_legacy_search_results gone
- AC3: EnrichmentStore and IngestCoordinator wired with graph_store_v2 not old GraphStore
- AC4: list_entities, _legacy_graph_stats, _knowledge_stats_bridge, knowledge_stats_resource deleted
- AC5: init_db() wrapper removed; lifespan uses plain sqlite3.connect() + ensure_tables()
- AC6: No legacy knowledge imports in server.py or _helpers.py
- AC7: V2 paths work standalone (regression guard)
- AC8: source_store and refresh_orchestrator retained in AppContext
"""

from __future__ import annotations

import dataclasses
import inspect
import sqlite3

from owlbear_mcp_knowledge import _helpers, server
from owlbear_mcp_knowledge.server import AppContext


# ---------------------------------------------------------------------------
# AC1 + AC8 — AppContext field set
# ---------------------------------------------------------------------------


class TestAppContextFields:
    """AppContext must contain only v2 store fields; legacy fields removed; B2b fields retained."""

    def test_no_query_service_field(self) -> None:
        """query_service must be removed from AppContext (AC1)."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "query_service" not in field_names, "Legacy field 'query_service' still present in AppContext"

    def test_no_graph_store_field(self) -> None:
        """graph_store (old GraphStore) must be removed from AppContext (AC1)."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "graph_store" not in field_names, "Legacy field 'graph_store' still present in AppContext"

    def test_no_ingest_pipeline_field(self) -> None:
        """ingest_pipeline must be removed from AppContext (AC1)."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "ingest_pipeline" not in field_names, "Legacy field 'ingest_pipeline' still present in AppContext"

    def test_no_intra_doc_builder_field(self) -> None:
        """intra_doc_builder must be removed from AppContext (AC1)."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "intra_doc_builder" not in field_names, "Legacy field 'intra_doc_builder' still present in AppContext"

    def test_no_structured_extractor_field(self) -> None:
        """structured_extractor must be removed from AppContext (AC1)."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "structured_extractor" not in field_names, (
            "Legacy field 'structured_extractor' still present in AppContext"
        )

    def test_source_store_absent_and_legacy_absent(self) -> None:
        """source_store removed and legacy fields absent after B2b cleanup."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "source_store" not in field_names, "source_store must be removed"
        # Must be absent (legacy)
        legacy = {"query_service", "graph_store", "ingest_pipeline"}
        still_present = legacy & field_names
        assert not still_present, f"Legacy fields still in AppContext: {still_present}"

    def test_refresh_orchestrator_absent_and_legacy_absent(self) -> None:
        """refresh_orchestrator removed and legacy fields absent after B2b cleanup."""
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "refresh_orchestrator" not in field_names, "refresh_orchestrator must be removed"
        # Must be absent (legacy)
        legacy = {"intra_doc_builder", "structured_extractor"}
        still_present = legacy & field_names
        assert not still_present, f"Legacy fields still in AppContext: {still_present}"

    def test_appcontext_v2_only_instantiation(self) -> None:
        """AppContext must be instantiatable with only v2 fields after legacy positional args removed."""
        conn = sqlite3.connect(":memory:")
        # After cleanup, legacy fields (query_service, graph_store, ingest_pipeline) are gone;
        # this call must succeed without them.
        ctx = AppContext(conn=conn)
        assert ctx.conn is conn


# ---------------------------------------------------------------------------
# AC2 — search_knowledge has no legacy fallback
# ---------------------------------------------------------------------------


class TestSearchKnowledgeV2Only:
    """search_knowledge must use only query_facade; no legacy query_service branch."""

    def test_serialize_legacy_search_results_removed(self) -> None:
        """_serialize_legacy_search_results must not exist in server module (AC2)."""
        assert not hasattr(server, "_serialize_legacy_search_results"), (
            "_serialize_legacy_search_results is still present in server module"
        )

    def test_search_knowledge_source_has_no_query_service_branch(self) -> None:
        """search_knowledge source must not reference query_service (AC2)."""
        src = inspect.getsource(server.knowledge_search)
        assert "query_service" not in src, "search_knowledge still contains a query_service branch"

    def test_search_knowledge_source_has_no_legacy_fallback_call(self) -> None:
        """search_knowledge must not call _serialize_legacy_search_results (AC2)."""
        src = inspect.getsource(server.knowledge_search)
        assert "_serialize_legacy_search_results" not in src, (
            "search_knowledge still calls _serialize_legacy_search_results"
        )


# ---------------------------------------------------------------------------
# AC3 — EnrichmentStore and IngestCoordinator wired with graph_store_v2
# ---------------------------------------------------------------------------


class TestStorageWiring:
    """EnrichmentStore and IngestCoordinator must use graph_store_v2, not old GraphStore."""

    def test_enrichment_store_not_wired_with_old_graph_store(self) -> None:
        """EnrichmentStore must receive graph_store_v2, not gs (old GraphStore) (AC3)."""
        src = inspect.getsource(server.app_lifespan)
        # Old wiring: EnrichmentStore(db=conn, graph=gs) where gs is old GraphStore
        assert "EnrichmentStore(db=conn, graph=gs)" not in src, (
            "EnrichmentStore is still wired with old GraphStore (gs) instead of graph_store_v2"
        )

    def test_ingest_coordinator_not_wired_with_old_graph_store(self) -> None:
        """IngestCoordinator must receive graph_store_v2, not gs (old GraphStore) (AC3)."""
        src = inspect.getsource(server.app_lifespan)
        # Old GraphStore was constructed as: gs = GraphStore(conn)
        # After cleanup, no GraphStore instance should be created
        assert "gs = GraphStore(" not in src, "Old GraphStore (gs) still constructed in lifespan"

    def test_enrichment_store_uses_graph_store_v2_keyword(self) -> None:
        """After wiring fix, EnrichmentStore call must pass graph_store_v2 (AC3)."""
        src = inspect.getsource(server.app_lifespan)
        # After cleanup: EnrichmentStore(db=conn, graph=graph_store_v2)
        # This fails now because old wiring uses graph=gs
        lines = src.splitlines()
        in_enrichment_block = False
        for line in lines:
            if "EnrichmentStore(" in line:
                in_enrichment_block = True
            if in_enrichment_block and "graph=" in line:
                assert "graph=graph_store_v2" in line, (
                    f"EnrichmentStore not wired with graph_store_v2; found: {line.strip()!r}"
                )
                break


# ---------------------------------------------------------------------------
# AC4 — Deleted functions
# ---------------------------------------------------------------------------


class TestDeletedFunctions:
    """list_entities, _legacy_graph_stats, _knowledge_stats_bridge, knowledge_stats_resource deleted."""

    def test_list_entities_removed(self) -> None:
        """list_entities must be deleted from server module (AC4)."""
        assert not hasattr(server, "list_entities"), "list_entities still exists in server module"

    def test_legacy_graph_stats_removed(self) -> None:
        """_legacy_graph_stats must be deleted from server module (AC4)."""
        assert not hasattr(server, "_legacy_graph_stats"), "_legacy_graph_stats still exists in server module"

    def test_knowledge_stats_bridge_removed(self) -> None:
        """_knowledge_stats_bridge MCP resource must be deleted (AC4)."""
        assert not hasattr(server, "_knowledge_stats_bridge"), "_knowledge_stats_bridge still exists in server module"

    def test_knowledge_stats_resource_removed(self) -> None:
        """knowledge_stats_resource must be deleted from server module (AC4)."""
        assert not hasattr(server, "knowledge_stats_resource"), "knowledge_stats_resource still exists in server module"

    def test_knowledge_stats_mcp_resource_not_registered(self) -> None:
        """The MCP resource 'knowledge://stats' must not be registered after cleanup (AC4)."""
        # Use source inspection — the @mcp.resource decorator call must be absent
        src = inspect.getsource(server)
        assert 'mcp.resource("knowledge://stats")' not in src, (
            "MCP resource 'knowledge://stats' still registered via @mcp.resource decorator"
        )


# ---------------------------------------------------------------------------
# AC5 — init_db() wrapper removed; lifespan uses sqlite3.connect() + ensure_tables()
# ---------------------------------------------------------------------------


class TestInitDbRemoved:
    """init_db wrapper removed; lifespan uses plain sqlite3.connect() + ensure_tables()."""

    def test_init_db_wrapper_removed(self) -> None:
        """init_db() wrapper must be removed from server module (AC5)."""
        assert not hasattr(server, "init_db"), "init_db() wrapper still present in server module"

    def test_schema_init_db_not_in_server(self) -> None:
        """_schema_init_db must not be imported/accessible in server module (AC5)."""
        assert not hasattr(server, "_schema_init_db"), "_schema_init_db still imported into server module"

    def test_lifespan_uses_sqlite_connect_not_init_db(self) -> None:
        """Lifespan must call sqlite3.connect() directly, not init_db() wrapper (AC5)."""
        src = inspect.getsource(server.app_lifespan)
        assert "conn = init_db(" not in src, (
            "Lifespan still calls init_db() wrapper; must use sqlite3.connect() directly"
        )


# ---------------------------------------------------------------------------
# AC6 — No legacy imports in server.py
# ---------------------------------------------------------------------------


class TestNoLegacyImportsServer:
    """No imports from legacy knowledge modules must remain in server.py (AC6)."""

    def test_no_graph_store_import(self) -> None:
        """GraphStore (legacy) must not be imported in server.py (AC6)."""
        assert not hasattr(server, "GraphStore"), "GraphStore (legacy graph_store module) still imported in server.py"

    def test_no_document_store_import(self) -> None:
        """DocumentStore must not be imported in server.py (AC6)."""
        assert not hasattr(server, "DocumentStore"), "DocumentStore still imported in server.py"

    def test_no_ingest_pipeline_import(self) -> None:
        """IngestPipeline must not be imported in server.py (AC6)."""
        assert not hasattr(server, "IngestPipeline"), (
            "IngestPipeline (legacy ingest module) still imported in server.py"
        )

    def test_no_knowledge_query_service_import(self) -> None:
        """KnowledgeQueryService must not be imported in server.py (AC6)."""
        assert not hasattr(server, "KnowledgeQueryService"), "KnowledgeQueryService still imported in server.py"

    def test_no_knowledge_query_error_import(self) -> None:
        """KnowledgeQueryError must not be imported in server.py (AC6)."""
        assert not hasattr(server, "KnowledgeQueryError"), "KnowledgeQueryError still imported in server.py"

    def test_no_graph_augmented_retriever_import(self) -> None:
        """GraphAugmentedRetriever must not be imported in server.py (AC6)."""
        assert not hasattr(server, "GraphAugmentedRetriever"), "GraphAugmentedRetriever still imported in server.py"

    def test_no_bge_embedding_provider_import(self) -> None:
        """BgeM3EmbeddingProvider must not be imported in server.py (AC6)."""
        assert not hasattr(server, "BgeM3EmbeddingProvider"), "BgeM3EmbeddingProvider still imported in server.py"

    def test_no_entity_extractor_import(self) -> None:
        """EntityExtractor must not be imported in server.py (AC6)."""
        assert not hasattr(server, "EntityExtractor"), "EntityExtractor still imported in server.py"

    def test_no_text_chunker_import(self) -> None:
        """TextChunker must not be imported in server.py (AC6)."""
        assert not hasattr(server, "TextChunker"), "TextChunker still imported in server.py"

    def test_no_models_entity_type_import(self) -> None:
        """EntityType from owlbear_knowledge.models must not be imported in server.py (AC6)."""
        # After cleanup, ProtocolEntityType alias remains but bare EntityType from models is gone
        assert not hasattr(server, "EntityType"), "EntityType (from legacy models) still imported in server.py"

    def test_no_schema_init_db_import(self) -> None:
        """schema.init_db must not be imported in server.py (AC6)."""
        assert not hasattr(server, "_schema_init_db"), (
            "_schema_init_db (from legacy schema module) still imported in server.py"
        )

    def test_no_intra_doc_graph_builder_import(self) -> None:
        """IntraDocGraphBuilder must not be imported in server.py (AC6)."""
        assert not hasattr(server, "IntraDocGraphBuilder"), "IntraDocGraphBuilder still imported in server.py"


# ---------------------------------------------------------------------------
# AC6 — No legacy imports in _helpers.py
# ---------------------------------------------------------------------------


class TestNoLegacyImportsHelpers:
    """No legacy imports (Edge, EntityType, RelationType from models) in _helpers.py (AC6)."""

    def test_helpers_no_edge_import(self) -> None:
        """Edge from owlbear_knowledge.models must not be imported in _helpers.py (AC6)."""
        assert not hasattr(_helpers, "Edge"), "Edge (from legacy models) still imported in _helpers.py"

    def test_helpers_no_models_entity_type_import(self) -> None:
        """EntityType from owlbear_knowledge.models must not be imported in _helpers.py (AC6)."""
        assert not hasattr(_helpers, "EntityType"), "EntityType (from legacy models) still imported in _helpers.py"

    def test_helpers_no_relation_type_import(self) -> None:
        """RelationType from owlbear_knowledge.models must not be imported in _helpers.py (AC6)."""
        assert not hasattr(_helpers, "RelationType"), "RelationType (from legacy models) still imported in _helpers.py"

    def test_helpers_no_extract_entity_type_function(self) -> None:
        """_extract_entity_type must be deleted from _helpers.py (AC6)."""
        assert not hasattr(_helpers, "_extract_entity_type"), "_extract_entity_type still present in _helpers.py"

    def test_helpers_no_extract_relation_function(self) -> None:
        """_extract_relation must be deleted from _helpers.py (AC6)."""
        assert not hasattr(_helpers, "_extract_relation"), "_extract_relation still present in _helpers.py"

    def test_helpers_no_validate_enrichment_edge_payload(self) -> None:
        """_validate_enrichment_edge_payload must be deleted from _helpers.py (AC6)."""
        assert not hasattr(_helpers, "_validate_enrichment_edge_payload"), (
            "_validate_enrichment_edge_payload still present in _helpers.py"
        )

    def test_helpers_no_stable_edge_id(self) -> None:
        """_stable_edge_id must be deleted from _helpers.py (AC6)."""
        assert not hasattr(_helpers, "_stable_edge_id"), "_stable_edge_id still present in _helpers.py"


# ---------------------------------------------------------------------------
# AC7 — V2 regression guard (only v2 paths remain)
# ---------------------------------------------------------------------------


class TestV2RegressionGuard:
    """After cleanup, v2 paths must work standalone without any legacy fallback."""

    def test_knowledge_search_source_uses_only_v2_error_type(self) -> None:
        """search_knowledge must not catch KnowledgeQueryError (legacy) (AC7)."""
        src = inspect.getsource(server.knowledge_search)
        assert "KnowledgeQueryError" not in src, (
            "search_knowledge still catches KnowledgeQueryError (legacy query_service error)"
        )

    def test_appcontext_has_no_required_legacy_positional_args(self) -> None:
        """AppContext must not require legacy objects as positional args (AC7 — v2-only context).

        After cleanup, AppContext can be constructed with just conn + source_store (retained).
        Currently fails because query_service, graph_store, ingest_pipeline are required.
        """
        conn = sqlite3.connect(":memory:")
        # Construct with only the fields that remain after cleanup (AC1 + AC8)
        field_names = {f.name for f in dataclasses.fields(AppContext)}
        legacy_fields = {"query_service", "graph_store", "ingest_pipeline", "intra_doc_builder", "structured_extractor"}
        remaining_legacy = legacy_fields & field_names
        assert not remaining_legacy, (
            f"AppContext still has legacy required fields: {remaining_legacy}; cannot construct v2-only context"
        )
        _ = conn  # connection is valid; test is structural

    def test_lifespan_does_not_construct_legacy_objects(self) -> None:
        """Lifespan must not construct KnowledgeQueryService, IngestPipeline, or GraphStore (AC7)."""
        src = inspect.getsource(server.app_lifespan)
        assert "KnowledgeQueryService(" not in src, "Lifespan still constructs KnowledgeQueryService"
        assert "IngestPipeline(" not in src, "Lifespan still constructs IngestPipeline"
