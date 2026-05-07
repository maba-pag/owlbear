"""Complementary tests for task #1330: Phase 2 + stats tools.

Tests written by the test-writer phase for #1330.  The primary RED-phase suite
lives in ``tests/test_mcp_knowledge_phase2_tools_1329.py`` (36 tests, all
written as RED before implementation).  This file adds coverage for error paths
and boundary conditions not targeted by the #1329 suite:

  - AC1 boundary: get_consolidation_candidates on empty DB → empty list
  - AC2 boundary: entity with NULL chunk_id → source_a/b_chunk returns ""
  - AC3 error: store_enrichment with malformed candidate_id → ToolError
  - AC3 error: store_enrichment with valid JSON but wrong structure → ToolError
  - AC3 boundary: Phase 2 with multiple edges writes all of them
  - AC4 boundary: Phase 2 dismissal is idempotent (INSERT OR IGNORE)
  - AC6 boundary: get_stats returns all 7 required fields in a single call
  - AC6 boundary: chunks_enriched_ratio = 1.0 when every chunk is enriched

Run with: uv run pytest tests/test_mcp_knowledge_phase2_tools_1330.py
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_knowledge.schema import init_db
from owlbear_mcp_knowledge.server import get_consolidation_candidates, get_stats, store_enrichment


# ---------------------------------------------------------------------------
# Fixtures and helpers (mirrors _1329 but self-contained for isolation)
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    init_db(c)
    return c


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_mcp_ctx(conn: sqlite3.Connection) -> MagicMock:
    mcp_ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.conn = conn
    mcp_ctx.request_context.lifespan_context = app_ctx
    return mcp_ctx


def _make_mcp_ctx_with_graph(
    conn: sqlite3.Connection,
    *,
    doc_count: int = 0,
    entity_count: int = 0,
    edge_count: int = 0,
) -> MagicMock:
    mcp_ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.conn = conn
    gs = MagicMock()
    gs.get_counts.return_value = (doc_count, entity_count, edge_count)
    app_ctx.graph_store = gs
    mcp_ctx.request_context.lifespan_context = app_ctx
    return mcp_ctx


def _insert_source(conn: sqlite3.Connection, *, name: str = "Test Source") -> str:
    sid = str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO knowledge_sources "
        "(id, name, source_type, fetch_method, enrich, config, scope, enabled, priority, created_at, updated_at) "
        "VALUES (?, ?, 'web', 'http', 1, '{}', 'global', 1, 0, ?, ?)",
        (sid, name, now, now),
    )
    conn.commit()
    return sid


def _insert_document(conn: sqlite3.Connection, *, source_id: str) -> str:
    did = str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id) "
        "VALUES (?, 'Doc', 'content', '{}', ?, 'global', ?)",
        (did, now, source_id),
    )
    conn.commit()
    return did


def _insert_entity(
    conn: sqlite3.Connection,
    *,
    name: str,
    document_id: str,
    chunk_id: str | None = None,
) -> str:
    eid = str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO entities "
        "(id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id) "
        "VALUES (?, ?, 'concept', 'desc', '{}', ?, 'global', ?, ?)",
        (eid, name, now, document_id, chunk_id),
    )
    conn.commit()
    return eid


def _insert_chunk(
    conn: sqlite3.Connection,
    *,
    document_id: str,
    content: str = "chunk text",
    enrichment_state: str = "pending",
) -> str:
    cid = str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO chunks "
        "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state) "
        "VALUES (?, ?, 0, ?, '{}', ?, 'global', ?)",
        (cid, document_id, content, now, enrichment_state),
    )
    conn.commit()
    return cid


def _get_field(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item[field]
    return getattr(item, field)


# ---------------------------------------------------------------------------
# TestFromAC_GetConsolidationCandidates (1330 additions)
# ---------------------------------------------------------------------------


class TestFromAC_GetConsolidationCandidates:
    """AC1/AC2 boundary and edge cases not covered in #1329 suite."""

    # --- AC1 boundary: empty DB → empty list ---

    @pytest.mark.asyncio
    async def test_empty_database_returns_empty_candidate_list(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC1 boundary: when no entities or sources exist, get_consolidation_candidates
        returns an empty list (not None, not an exception)."""
        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        assert isinstance(candidates, list), (
            f"Expected list, got {type(candidates)}"
        )
        assert len(candidates) == 0, (
            f"Expected empty list for empty DB, got: {candidates}"
        )

    # --- AC2 boundary: entity with NULL chunk_id → chunk fields return "" ---

    @pytest.mark.asyncio
    async def test_entity_with_no_chunk_id_yields_empty_chunk_fields(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC2 boundary: when entity.chunk_id IS NULL (no associated chunk), the
        candidate's source_a_chunk and source_b_chunk fields are both empty strings,
        not None and not an error."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        # Insert entities WITHOUT chunk_id (chunk_id=None → NULL in DB)
        _insert_entity(conn, name="NullChunkEntity", document_id=doc_a, chunk_id=None)
        _insert_entity(conn, name="NullChunkEntity", document_id=doc_b, chunk_id=None)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        nce = [c for c in candidates if _get_field(c, "entity_name") == "NullChunkEntity"]
        assert nce, "Expected 'NullChunkEntity' in candidates"
        candidate = nce[0]

        source_a_chunk = _get_field(candidate, "source_a_chunk")
        source_b_chunk = _get_field(candidate, "source_b_chunk")

        assert source_a_chunk == "", (
            f"Expected source_a_chunk='' when entity has no chunk, got: {source_a_chunk!r}"
        )
        assert source_b_chunk == "", (
            f"Expected source_b_chunk='' when entity has no chunk, got: {source_b_chunk!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_StoreEnrichmentPhase2 (1330 additions)
# ---------------------------------------------------------------------------


class TestFromAC_StoreEnrichmentPhase2:
    """AC3/AC4 error paths and boundary conditions not covered in #1329 suite."""

    # --- AC3 error: malformed candidate_id → ToolError ---

    @pytest.mark.asyncio
    async def test_malformed_candidate_id_raises_tool_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 error: store_enrichment Phase 2 with a non-JSON candidate_id raises
        ToolError — the implementation must not crash with a generic exception."""
        ctx = _make_mcp_ctx(conn)

        with pytest.raises(ToolError):
            await store_enrichment(ctx, candidate_id="not-valid-json", edges=[])

    @pytest.mark.asyncio
    async def test_candidate_id_with_wrong_json_structure_raises_tool_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 error: candidate_id that is valid JSON but not a 3-element string list
        raises ToolError (not IndexError, not KeyError)."""
        ctx = _make_mcp_ctx(conn)

        # Valid JSON but wrong shape (object, not list of 3 strings)
        with pytest.raises(ToolError):
            await store_enrichment(ctx, candidate_id='{"entity": "x"}', edges=[])

    @pytest.mark.asyncio
    async def test_candidate_id_with_too_few_elements_raises_tool_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 error: candidate_id that is a JSON list with fewer than 3 elements
        raises ToolError."""
        ctx = _make_mcp_ctx(conn)

        with pytest.raises(ToolError):
            await store_enrichment(ctx, candidate_id='["only", "two"]', edges=[])

    # --- AC3 boundary: multiple edges in one Phase 2 call → all written ---

    @pytest.mark.asyncio
    async def test_phase2_multiple_edges_writes_all_edges(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 boundary: Phase 2 store_enrichment with edges=[e1, e2, e3] writes
        exactly 3 new rows to the edges table, not just the first."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        entity_a1 = _insert_entity(conn, name="MultiEdge", document_id=doc_a)
        entity_a2 = _insert_entity(conn, name="MultiEdge2", document_id=doc_a)
        entity_b1 = _insert_entity(conn, name="MultiEdge", document_id=doc_b)
        entity_b2 = _insert_entity(conn, name="MultiEdge2", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        multi_cands = [c for c in candidates if _get_field(c, "entity_name") == "MultiEdge"]
        assert multi_cands, "Expected 'MultiEdge' to be a candidate"
        candidate_id = _get_field(multi_cands[0], "candidate_id")

        edges_before = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        await store_enrichment(
            ctx,
            candidate_id=candidate_id,
            edges=[
                {"source_id": entity_a1, "target_id": entity_b1, "relation": "same_as"},
                {"source_id": entity_a2, "target_id": entity_b2, "relation": "related_to"},
                {"source_id": entity_b1, "target_id": entity_a2, "relation": "references"},
            ],
        )

        edges_after = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert edges_after == edges_before + 3, (
            f"Expected 3 new edges after Phase 2 call with 3-edge list, "
            f"before={edges_before}, after={edges_after}"
        )

    # --- AC4 boundary: dismissal is idempotent ---

    @pytest.mark.asyncio
    async def test_phase2_dismissal_is_idempotent(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC4 boundary: calling Phase 2 dismissal (empty edges) twice for the same
        candidate does NOT raise an error and does NOT create duplicate reviewed_pairs
        rows (INSERT OR IGNORE semantics)."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="IdempotentEntity", document_id=doc_a)
        _insert_entity(conn, name="IdempotentEntity", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)
        ie_cands = [c for c in candidates if _get_field(c, "entity_name") == "IdempotentEntity"]
        assert ie_cands, "Expected 'IdempotentEntity' to be a candidate"
        candidate_id = _get_field(ie_cands[0], "candidate_id")

        # First dismissal
        await store_enrichment(ctx, candidate_id=candidate_id, edges=[])

        reviewed_after_first = conn.execute(
            "SELECT COUNT(*) FROM reviewed_pairs"
        ).fetchone()[0]

        # Second dismissal — must not raise and must not duplicate the row
        await store_enrichment(ctx, candidate_id=candidate_id, edges=[])

        reviewed_after_second = conn.execute(
            "SELECT COUNT(*) FROM reviewed_pairs"
        ).fetchone()[0]

        assert reviewed_after_second == reviewed_after_first, (
            f"Expected idempotent dismissal to not add duplicate row, "
            f"after first call: {reviewed_after_first}, "
            f"after second call: {reviewed_after_second}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GetStatsExpansion (1330 additions)
# ---------------------------------------------------------------------------


class TestFromAC_GetStatsExpansion:
    """AC6 shape and boundary conditions not covered in #1329 suite."""

    # --- AC6 boundary: single call returns ALL required fields together ---

    @pytest.mark.asyncio
    async def test_stats_returns_all_required_fields_in_single_call(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 boundary: a single get_stats call must return a dict containing
        all 7 required fields simultaneously — not a subset."""
        required_fields = {
            "documents",
            "entities",
            "edges",
            "total_sources",
            "total_chunks",
            "chunks_enriched_ratio",
            "consolidation_candidates_remaining",
        }

        ctx = _make_mcp_ctx_with_graph(conn, doc_count=1, entity_count=1, edge_count=1)
        result = await get_stats(ctx)

        missing = required_fields - set(result.keys())
        assert not missing, (
            f"get_stats is missing required fields: {missing}. "
            f"Got fields: {set(result.keys())}"
        )

    # --- AC6 boundary: chunks_enriched_ratio = 1.0 when all enriched ---

    @pytest.mark.asyncio
    async def test_stats_enriched_ratio_is_one_when_all_chunks_enriched(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 boundary: chunks_enriched_ratio = 1.0 when every chunk in the
        table has enrichment_state='enriched' (100% enrichment)."""
        source_a = _insert_source(conn, name="Source A")
        doc_a = _insert_document(conn, source_id=source_a)
        _insert_chunk(conn, document_id=doc_a, enrichment_state="enriched")
        _insert_chunk(conn, document_id=doc_a, enrichment_state="enriched")
        _insert_chunk(conn, document_id=doc_a, enrichment_state="enriched")

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        ratio = result["chunks_enriched_ratio"]
        assert ratio == 1.0, (
            f"Expected chunks_enriched_ratio=1.0 when all chunks enriched, got: {ratio}"
        )

    # --- AC6 boundary: total_chunks = 0 and ratio = 0.0 when no chunks ---

    @pytest.mark.asyncio
    async def test_stats_total_chunks_zero_and_ratio_zero_when_no_chunks(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 boundary: with no chunks in the DB, total_chunks=0 and
        chunks_enriched_ratio=0.0 (no division-by-zero error)."""
        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert result["total_chunks"] == 0, (
            f"Expected total_chunks=0 with no chunks, got: {result['total_chunks']}"
        )
        assert result["chunks_enriched_ratio"] == 0.0, (
            f"Expected ratio=0.0 with no chunks, got: {result['chunks_enriched_ratio']}"
        )

    # --- AC6 boundary: total_sources = 0 when knowledge_sources is empty ---

    @pytest.mark.asyncio
    async def test_stats_total_sources_zero_when_no_sources(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 boundary: with no knowledge_sources rows, total_sources=0."""
        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert result["total_sources"] == 0, (
            f"Expected total_sources=0 with no sources, got: {result['total_sources']}"
        )

    # --- AC6 boundary: consolidation_candidates_remaining = 0 on empty DB ---

    @pytest.mark.asyncio
    async def test_stats_consolidation_candidates_zero_on_empty_db(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 boundary: with no entities or sources, consolidation_candidates_remaining=0."""
        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert result["consolidation_candidates_remaining"] == 0, (
            f"Expected 0 consolidation candidates on empty DB, "
            f"got: {result['consolidation_candidates_remaining']}"
        )
