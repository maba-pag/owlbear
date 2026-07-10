"""Tests for knowledge_enrichment_store MCP tool — phase-1 wiring to submit_extractions (task #1892).

Source files under test:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py

Target interface:
  knowledge_enrichment_store — async MCP tool function

AC coverage:
  AC1 — Phase-1 path (chunk_id provided) calls EnrichmentStore.submit_extractions()
  AC2 — Entity dicts parsed into ExtractedEntity: id→local_ref, entity_type→EntityType,
         description/confidence use protocol defaults
  AC3 — Edge dicts parsed into ExtractedRelation: source_id→source_ref, target_id→target_ref,
         'relation'/'relationship' key→RelationType, weight defaults to 1.0
  AC4 — Phase-2 path (candidate_id provided) remains on _persist_phase2_enrichment (regression guard)
  AC5 — LookupError from submit_extractions raised as ToolError
  AC6 — Parsing failure: mark_failed(chunk_id, error) called then ToolError raised
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.protocols.common import EntityType, RelationType
from owlbear_mcp_knowledge.server import store_enrichment as knowledge_enrichment_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHUNK_ID = "chunk-1892-test"


def _make_enrichment_store_mock() -> MagicMock:
    """Return a mock EnrichmentStore whose submit_extractions succeeds."""
    store = MagicMock()
    store.submit_extractions.return_value = MagicMock(
        chunk_id=_CHUNK_ID,
        entity_ids=(),
        edge_ids=(),
        evidence_ids=(),
    )
    return store


def _make_ctx(*, enrichment_store: MagicMock | None = None) -> tuple[MagicMock, MagicMock]:
    """Return (ctx, enrichment_store_mock).

    ``ctx.request_context.lifespan_context`` is an AppContext-like mock with
    enrichment_store and conn pre-wired.
    """
    store = enrichment_store if enrichment_store is not None else _make_enrichment_store_mock()
    app_ctx = MagicMock()
    app_ctx.enrichment_store = store
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx, store


def _extract_submit_args(store: MagicMock) -> tuple[str, tuple, tuple]:
    """Return (chunk_id, entities_tuple, relations_tuple) from the submit_extractions call."""
    c = store.submit_extractions.call_args
    args = c.args or ()
    kwargs = c.kwargs or {}
    chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
    entities = args[1] if len(args) > 1 else kwargs.get("entities", ())
    relations = args[2] if len(args) > 2 else kwargs.get("relations", ())
    return str(chunk_id), tuple(entities), tuple(relations)


# ---------------------------------------------------------------------------
# AC1 — Phase-1 path calls EnrichmentStore.submit_extractions()
# ---------------------------------------------------------------------------


class TestPhase1UsesSubmitExtractions:
    """AC1: chunk_id path delegates to enrichment_store.submit_extractions()."""

    @pytest.mark.asyncio
    async def test_phase1_calls_submit_extractions(self) -> None:
        """Providing chunk_id causes enrichment_store.submit_extractions to be called."""
        ctx, store = _make_ctx()
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        store.submit_extractions.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase1_passes_chunk_id_to_submit_extractions(self) -> None:
        """submit_extractions receives the exact chunk_id passed to knowledge_enrichment_store."""
        ctx, store = _make_ctx()
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        chunk_id_arg, _, _ = _extract_submit_args(store)
        assert chunk_id_arg == _CHUNK_ID

    @pytest.mark.asyncio
    async def test_phase1_no_direct_sql_begin_in_phase1_path(self) -> None:
        """Phase-1 path does NOT call conn.execute with BEGIN IMMEDIATE."""
        ctx, _ = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context
        conn_mock = MagicMock()
        app_ctx.conn = conn_mock
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        # None of the conn.execute calls should be "BEGIN IMMEDIATE"
        begin_calls = [c for c in conn_mock.execute.call_args_list if "BEGIN" in str(c)]
        assert begin_calls == [], "Phase-1 path must not call conn.execute with BEGIN"


# ---------------------------------------------------------------------------
# AC2 — Entity dict parsed into ExtractedEntity with correct field mapping
# ---------------------------------------------------------------------------


class TestEntityDictParsing:
    """AC2: entity dict keys mapped correctly to ExtractedEntity fields."""

    @pytest.mark.asyncio
    async def test_entity_id_key_mapped_to_local_ref(self) -> None:
        """Entity dict 'id' key → ExtractedEntity.local_ref."""
        ctx, store = _make_ctx()
        entity = {"id": "ref-abc", "name": "Alpha", "entity_type": "concept"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert len(entities_arg) == 1
        assert entities_arg[0].local_ref == "ref-abc"

    @pytest.mark.asyncio
    async def test_entity_name_mapped(self) -> None:
        """Entity dict 'name' key → ExtractedEntity.name."""
        ctx, store = _make_ctx()
        entity = {"id": "ref-1", "name": "MyEntity", "entity_type": "concept"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].name == "MyEntity"

    @pytest.mark.asyncio
    async def test_entity_type_defaults_to_concept_when_absent(self) -> None:
        """Entity dict without 'entity_type' → ExtractedEntity.entity_type == CONCEPT."""
        ctx, store = _make_ctx()
        entity = {"id": "ref-1", "name": "MyEntity"}  # no entity_type
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].entity_type == EntityType.CONCEPT

    @pytest.mark.asyncio
    async def test_entity_description_defaults_to_empty_string(self) -> None:
        """Entity dict without 'description' → ExtractedEntity.description == ''."""
        ctx, store = _make_ctx()
        entity = {"id": "ref-1", "name": "MyEntity", "entity_type": "concept"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].description == ""

    @pytest.mark.asyncio
    async def test_entity_confidence_defaults_to_one(self) -> None:
        """Entity dict without 'confidence' → ExtractedEntity.confidence == 1.0."""
        ctx, store = _make_ctx()
        entity = {"id": "ref-1", "name": "MyEntity", "entity_type": "concept"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].confidence == 1.0

    @pytest.mark.asyncio
    async def test_entity_type_validated_against_protocol_enum_technology(self) -> None:
        """entity_type='technology' → ExtractedEntity.entity_type == EntityType.TECHNOLOGY."""
        ctx, store = _make_ctx()
        entity = {"id": "ref-1", "name": "Python", "entity_type": "technology"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].entity_type == EntityType.TECHNOLOGY

    @pytest.mark.asyncio
    async def test_entity_type_validated_against_protocol_enum_person(self) -> None:
        """entity_type='person' (valid in 12-value protocol enum) → EntityType.PERSON."""
        ctx, store = _make_ctx()
        entity = {"id": "ref-1", "name": "Jane", "entity_type": "person"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].entity_type == EntityType.PERSON

    @pytest.mark.asyncio
    async def test_multiple_entities_all_parsed(self) -> None:
        """Multiple entity dicts → same number of ExtractedEntity objects passed."""
        ctx, store = _make_ctx()
        entities = [
            {"id": "r1", "name": "A", "entity_type": "concept"},
            {"id": "r2", "name": "B", "entity_type": "tool"},
        ]
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert len(entities_arg) == 2


# ---------------------------------------------------------------------------
# AC3 — Edge dict parsed into ExtractedRelation with correct field mapping
# ---------------------------------------------------------------------------


class TestEdgeDictParsing:
    """AC3: edge dict keys mapped correctly to ExtractedRelation fields."""

    @pytest.mark.asyncio
    async def test_edge_source_id_mapped_to_source_ref(self) -> None:
        """Edge dict 'source_id' key → ExtractedRelation.source_ref."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relation": "related_to"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        _, _, relations_arg = _extract_submit_args(store)
        assert len(relations_arg) == 1
        assert relations_arg[0].source_ref == "r1"

    @pytest.mark.asyncio
    async def test_edge_target_id_mapped_to_target_ref(self) -> None:
        """Edge dict 'target_id' key → ExtractedRelation.target_ref."""
        ctx, store = _make_ctx()
        entities = [
            {"id": "r1", "name": "A", "entity_type": "concept"},
            {"id": "r2", "name": "B", "entity_type": "concept"},
        ]
        edge = {"source_id": "r1", "target_id": "r2", "relation": "depends_on"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        _, _, relations_arg = _extract_submit_args(store)
        assert relations_arg[0].target_ref == "r2"

    @pytest.mark.asyncio
    async def test_edge_relation_key_maps_to_relation_type(self) -> None:
        """Edge dict 'relation' key → ExtractedRelation.relation_type == RelationType.DEPENDS_ON."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relation": "depends_on"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        _, _, relations_arg = _extract_submit_args(store)
        assert relations_arg[0].relation_type == RelationType.DEPENDS_ON

    @pytest.mark.asyncio
    async def test_edge_relationship_alias_key_accepted(self) -> None:
        """Edge dict 'relationship' key is accepted as alias for relation type."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relationship": "contains"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        _, _, relations_arg = _extract_submit_args(store)
        assert relations_arg[0].relation_type == RelationType.CONTAINS

    @pytest.mark.asyncio
    async def test_edge_weight_defaults_to_one(self) -> None:
        """Edge dict without 'weight' → ExtractedRelation.weight == 1.0."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relation": "related_to"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        _, _, relations_arg = _extract_submit_args(store)
        assert relations_arg[0].weight == 1.0

    @pytest.mark.asyncio
    async def test_edge_relation_type_validates_against_protocol_enum(self) -> None:
        """relation='references' → ExtractedRelation.relation_type == RelationType.REFERENCES."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relation": "references"}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        _, _, relations_arg = _extract_submit_args(store)
        assert relations_arg[0].relation_type == RelationType.REFERENCES

    @pytest.mark.asyncio
    async def test_no_edges_passes_empty_relations_tuple(self) -> None:
        """edges=[] → submit_extractions receives empty relations tuple."""
        ctx, store = _make_ctx()
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        _, _, relations_arg = _extract_submit_args(store)
        assert len(relations_arg) == 0


# ---------------------------------------------------------------------------
# AC5 — LookupError from submit_extractions raised as ToolError
# ---------------------------------------------------------------------------


class TestLookupErrorAsToolError:
    """AC5: submit_extractions LookupError → ToolError."""

    @pytest.mark.asyncio
    async def test_lookup_error_from_submit_extractions_raised_as_tool_error(self) -> None:
        """LookupError raised by submit_extractions is converted to ToolError.

        Asserts submit_extractions was actually called to confirm the error
        originated there (not from a pre-existing SQL validation guard).
        """
        store = _make_enrichment_store_mock()
        store.submit_extractions.side_effect = LookupError("chunk not in progress")
        ctx, _ = _make_ctx(enrichment_store=store)
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        store.submit_extractions.assert_called_once()


# ---------------------------------------------------------------------------
# AC6 — Parsing failure: mark_failed called, then ToolError raised
# ---------------------------------------------------------------------------


class TestParsingFailureMarksFailed:
    """AC6: invalid entity/edge input → mark_failed(chunk_id, error) + ToolError."""

    @pytest.mark.asyncio
    async def test_invalid_entity_type_raises_tool_error(self) -> None:
        """Invalid entity_type value raises ToolError and mark_failed is called."""
        ctx, store = _make_ctx()
        entity = {"id": "r1", "name": "X", "entity_type": "NOT_A_REAL_ENTITY_TYPE_1892"}
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        store.mark_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_entity_type_calls_mark_failed(self) -> None:
        """Invalid entity_type → enrichment_store.mark_failed(chunk_id, error) is called."""
        ctx, store = _make_ctx()
        entity = {"id": "r1", "name": "X", "entity_type": "NOT_A_REAL_ENTITY_TYPE_1892"}
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        reported_chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
        assert reported_chunk_id == _CHUNK_ID

    @pytest.mark.asyncio
    async def test_mark_failed_receives_error_string(self) -> None:
        """mark_failed receives a non-empty error string describing the failure."""
        ctx, store = _make_ctx()
        entity = {"id": "r1", "name": "X", "entity_type": "BOGUS_TYPE_1892"}
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        error_str = args[1] if len(args) > 1 else kwargs.get("error", "")
        assert isinstance(error_str, str)
        assert len(error_str) > 0

    @pytest.mark.asyncio
    async def test_invalid_relation_type_raises_tool_error(self) -> None:
        """Invalid relation_type value raises ToolError and mark_failed is called."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "X", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relation": "NOT_A_REAL_RELATION_1892"}
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        store.mark_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_relation_type_calls_mark_failed(self) -> None:
        """Invalid relation_type → enrichment_store.mark_failed(chunk_id, error) is called."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "X", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relation": "NOT_A_REAL_RELATION_1892"}
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        store.mark_failed.assert_called_once()

    # ---- missing required field paths (AC6 gap-fill) ----

    @pytest.mark.asyncio
    async def test_missing_entity_id_raises_tool_error(self) -> None:
        """Entity dict without 'id' → ToolError raised."""
        ctx, _ = _make_ctx()
        entity = {"name": "X", "entity_type": "concept"}  # no 'id'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])

    @pytest.mark.asyncio
    async def test_missing_entity_id_calls_mark_failed(self) -> None:
        """Entity dict without 'id' → mark_failed(chunk_id, error_str) called."""
        ctx, store = _make_ctx()
        entity = {"name": "X", "entity_type": "concept"}  # no 'id'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        reported_chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
        error_str = args[1] if len(args) > 1 else kwargs.get("error", "")
        assert reported_chunk_id == _CHUNK_ID
        assert isinstance(error_str, str)
        assert len(error_str) > 0

    @pytest.mark.asyncio
    async def test_missing_entity_name_raises_tool_error(self) -> None:
        """Entity dict without 'name' → ToolError raised."""
        ctx, _ = _make_ctx()
        entity = {"id": "r1", "entity_type": "concept"}  # no 'name'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])

    @pytest.mark.asyncio
    async def test_missing_entity_name_calls_mark_failed(self) -> None:
        """Entity dict without 'name' → mark_failed(chunk_id, error_str) called."""
        ctx, store = _make_ctx()
        entity = {"id": "r1", "entity_type": "concept"}  # no 'name'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        reported_chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
        error_str = args[1] if len(args) > 1 else kwargs.get("error", "")
        assert reported_chunk_id == _CHUNK_ID
        assert isinstance(error_str, str)
        assert len(error_str) > 0

    @pytest.mark.asyncio
    async def test_missing_edge_source_id_raises_tool_error(self) -> None:
        """Edge dict without 'source_id' → ToolError raised."""
        ctx, _ = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"target_id": "r1", "relation": "related_to"}  # no 'source_id'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])

    @pytest.mark.asyncio
    async def test_missing_edge_source_id_calls_mark_failed(self) -> None:
        """Edge dict without 'source_id' → mark_failed(chunk_id, error_str) called."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"target_id": "r1", "relation": "related_to"}  # no 'source_id'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        reported_chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
        error_str = args[1] if len(args) > 1 else kwargs.get("error", "")
        assert reported_chunk_id == _CHUNK_ID
        assert isinstance(error_str, str)
        assert len(error_str) > 0

    @pytest.mark.asyncio
    async def test_missing_edge_target_id_raises_tool_error(self) -> None:
        """Edge dict without 'target_id' → ToolError raised."""
        ctx, _ = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "relation": "related_to"}  # no 'target_id'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])

    @pytest.mark.asyncio
    async def test_missing_edge_target_id_calls_mark_failed(self) -> None:
        """Edge dict without 'target_id' → mark_failed(chunk_id, error_str) called."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "relation": "related_to"}  # no 'target_id'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        reported_chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
        error_str = args[1] if len(args) > 1 else kwargs.get("error", "")
        assert reported_chunk_id == _CHUNK_ID
        assert isinstance(error_str, str)
        assert len(error_str) > 0

    @pytest.mark.asyncio
    async def test_missing_edge_relation_and_relationship_raises_tool_error(self) -> None:
        """Edge dict with neither 'relation' nor 'relationship' → ToolError raised."""
        ctx, _ = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1"}  # no 'relation' or 'relationship'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])

    @pytest.mark.asyncio
    async def test_missing_edge_relation_and_relationship_calls_mark_failed(self) -> None:
        """Edge dict with neither 'relation' nor 'relationship' → mark_failed(chunk_id, error_str) called."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1"}  # no 'relation' or 'relationship'
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        reported_chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
        error_str = args[1] if len(args) > 1 else kwargs.get("error", "")
        assert reported_chunk_id == _CHUNK_ID
        assert isinstance(error_str, str)
        assert len(error_str) > 0


# ---------------------------------------------------------------------------
# AC2/AC3 gap-fill — explicit non-default values pass through parsing
# ---------------------------------------------------------------------------


class TestExplicitFieldPassthrough:
    """Retry gap-fill: prove explicit non-default values survive dict→model parsing."""

    @pytest.mark.asyncio
    async def test_entity_explicit_description_passes_through(self) -> None:
        """Entity dict with 'description' set → ExtractedEntity.description matches exactly."""
        ctx, store = _make_ctx()
        entity = {
            "id": "r1",
            "name": "MyEntity",
            "entity_type": "concept",
            "description": "A custom description string",
        }
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].description == "A custom description string"

    @pytest.mark.asyncio
    async def test_entity_explicit_confidence_passes_through(self) -> None:
        """Entity dict with 'confidence' set to non-default → ExtractedEntity.confidence matches."""
        ctx, store = _make_ctx()
        entity = {
            "id": "r1",
            "name": "MyEntity",
            "entity_type": "concept",
            "confidence": 0.42,
        }
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[entity], edges=[])
        _, entities_arg, _ = _extract_submit_args(store)
        assert entities_arg[0].confidence == pytest.approx(0.42)

    @pytest.mark.asyncio
    async def test_edge_explicit_weight_passes_through(self) -> None:
        """Edge dict with 'weight' set to non-default → ExtractedRelation.weight matches."""
        ctx, store = _make_ctx()
        entities = [{"id": "r1", "name": "A", "entity_type": "concept"}]
        edge = {"source_id": "r1", "target_id": "r1", "relation": "related_to", "weight": 0.25}
        await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=entities, edges=[edge])
        _, _, relations_arg = _extract_submit_args(store)
        assert relations_arg[0].weight == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# AC7 — ValueError from submit_extractions → mark_failed + ToolError
# ---------------------------------------------------------------------------


class TestSubmitExtractionsValueError:
    """AC7: ValueError from submit_extractions (unresolved ref) → mark_failed + ToolError."""

    @pytest.mark.asyncio
    async def test_value_error_from_submit_extractions_raised_as_tool_error(self) -> None:
        """ValueError raised by submit_extractions is wrapped as ToolError, not left uncaught."""
        store = _make_enrichment_store_mock()
        store.submit_extractions.side_effect = ValueError("source_ref 'r1' not found in entity local_refs")
        ctx, _ = _make_ctx(enrichment_store=store)
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])

    @pytest.mark.asyncio
    async def test_value_error_from_submit_extractions_calls_mark_failed(self) -> None:
        """ValueError raised by submit_extractions causes mark_failed to be called."""
        store = _make_enrichment_store_mock()
        store.submit_extractions.side_effect = ValueError("target_ref 'r2' not in submitted entities")
        ctx, _ = _make_ctx(enrichment_store=store)
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        store.mark_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_value_error_mark_failed_receives_chunk_id(self) -> None:
        """mark_failed receives the exact chunk_id when ValueError escapes submit_extractions."""
        store = _make_enrichment_store_mock()
        store.submit_extractions.side_effect = ValueError("unresolved relation ref")
        ctx, _ = _make_ctx(enrichment_store=store)
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        reported_chunk_id = args[0] if len(args) > 0 else kwargs.get("chunk_id", "")
        assert reported_chunk_id == _CHUNK_ID

    @pytest.mark.asyncio
    async def test_value_error_mark_failed_receives_error_string(self) -> None:
        """mark_failed receives a non-empty error string describing the ValueError."""
        store = _make_enrichment_store_mock()
        err_msg = "source_ref 'r1' not found among submitted entity local_refs"
        store.submit_extractions.side_effect = ValueError(err_msg)
        ctx, _ = _make_ctx(enrichment_store=store)
        with pytest.raises(ToolError):
            await knowledge_enrichment_store(ctx, chunk_id=_CHUNK_ID, entities=[], edges=[])
        call_args = store.mark_failed.call_args
        args = call_args.args or ()
        kwargs = call_args.kwargs or {}
        error_str = args[1] if len(args) > 1 else kwargs.get("error", "")
        assert isinstance(error_str, str)
        assert len(error_str) > 0
