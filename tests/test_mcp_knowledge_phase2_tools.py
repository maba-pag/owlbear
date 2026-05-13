from __future__ import annotations

# --- merged from tests/test_mcp_knowledge_phase2_tools_1329.py ---
"""Failing tests for task #1329: Phase 2 consolidation tools (get_consolidation_candidates, get_stats expansion).

TDD RED phase — all tests FAIL until task #1330 implements the tools.

Covers:
  - AC1: get_consolidation_candidates(ctx, limit=20): deterministic SQL
         (ORDER BY entity_name) finding entity names in 2+ sources (td:2)
  - AC2: candidates exclude entries with existing cross-source edges or
         reviewed_pairs rows (td:2)
  - AC3: candidates return list of dicts with entity_name + relevant chunks
         from both sources inline (td:1)
  - AC4: store_enrichment Phase 2 mode (ctx, candidate_id, edges=[...]): writes
         cross-source edges when edges non-empty (td:1)
  - AC5: store_enrichment Phase 2 mode with empty edges=[] marks pair in
         reviewed_pairs (dismissal) (td:1)
  - AC6: new sources generate new candidate pairs; old dismissals in
         reviewed_pairs preserved (td:2)
  - AC7: get_stats additive result: preserves existing {documents, entities,
         edges} AND adds total_sources, total_chunks, chunks_enriched_ratio,
         consolidation_candidates_remaining (td:2)

Run with: uv run pytest tests/test_mcp_knowledge_phase2_tools_1329.py
"""


import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Import targets — get_consolidation_candidates raises ImportError until
# builder implements #1330 (RED).  get_stats and store_enrichment exist but
# their tests assert on new fields / new signature and will fail (RED).
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.server import get_consolidation_candidates  # type: ignore[import]
from owlbear_mcp_knowledge.server import get_stats, store_enrichment


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """In-memory SQLite connection with schema initialized."""
    c = sqlite3.connect(":memory:")
    init_db(c)
    return c


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_mcp_ctx(conn: sqlite3.Connection) -> MagicMock:
    """Return a MagicMock MCP context with a real AppContext.conn."""
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
    """Return a MagicMock MCP context with real conn and mocked graph_store."""
    mcp_ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.conn = conn
    gs = MagicMock()
    gs.get_counts.return_value = (doc_count, entity_count, edge_count)
    app_ctx.graph_store = gs
    mcp_ctx.request_context.lifespan_context = app_ctx
    return mcp_ctx


def _insert_source(
    conn: sqlite3.Connection,
    *,
    source_id: str | None = None,
    name: str = "Test Source",
    enrich: int = 1,
) -> str:
    """Insert a knowledge_sources row and return its id."""
    sid = source_id or str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO knowledge_sources "
        "(id, name, source_type, fetch_method, enrich, config, scope, enabled, priority, created_at, updated_at) "
        "VALUES (?, ?, 'web', 'http', ?, '{}', 'global', 1, 0, ?, ?)",
        (sid, name, enrich, now, now),
    )
    conn.commit()
    return sid


def _insert_document(
    conn: sqlite3.Connection,
    *,
    doc_id: str | None = None,
    title: str = "Test Doc",
    source_id: str | None = None,
) -> str:
    """Insert a documents row and return its id."""
    did = doc_id or str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id) "
        "VALUES (?, ?, 'content', '{}', ?, 'global', ?)",
        (did, title, now, source_id),
    )
    conn.commit()
    return did


def _insert_chunk(
    conn: sqlite3.Connection,
    *,
    chunk_id: str | None = None,
    document_id: str,
    content: str = "chunk text",
    enrichment_state: str = "pending",
) -> str:
    """Insert a chunks row and return its id."""
    cid = chunk_id or str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO chunks "
        "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state) "
        "VALUES (?, ?, 0, ?, '{}', ?, 'global', ?)",
        (cid, document_id, content, now, enrichment_state),
    )
    conn.commit()
    return cid


def _insert_entity(  # noqa: PLR0913
    conn: sqlite3.Connection,
    *,
    entity_id: str | None = None,
    name: str = "TestEntity",
    entity_type: str = "concept",
    description: str = "A test entity",
    document_id: str | None = None,
    chunk_id: str | None = None,
) -> str:
    """Insert an entities row and return its id."""
    eid = entity_id or str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO entities "
        "(id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id) "
        "VALUES (?, ?, ?, ?, '{}', ?, 'global', ?, ?)",
        (eid, name, entity_type, description, now, document_id, chunk_id),
    )
    conn.commit()
    return eid


def _insert_edge(  # noqa: PLR0913
    conn: sqlite3.Connection,
    *,
    edge_id: str | None = None,
    source_entity_id: str,
    target_entity_id: str,
    relation: str = "related",
    document_id: str | None = None,
) -> str:
    """Insert an edge between two entity records and return its id."""
    eid = edge_id or str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO edges "
        "(id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope) "
        "VALUES (?, ?, ?, ?, ?, 1.0, '{}', ?, 'global')",
        (eid, source_entity_id, target_entity_id, relation, document_id, now),
    )
    conn.commit()
    return eid


def _insert_reviewed_pair(
    conn: sqlite3.Connection,
    *,
    entity_name: str,
    source_a: str,
    source_b: str,
) -> None:
    """Insert a reviewed_pairs dismissal row."""
    conn.execute(
        "INSERT INTO reviewed_pairs (entity_name, source_a, source_b) VALUES (?, ?, ?)",
        (entity_name, source_a, source_b),
    )
    conn.commit()


def _get_field(item: Any, field: str) -> Any:
    """Extract a named field from a result item (dict or object)."""
    if isinstance(item, dict):
        return item[field]
    return getattr(item, field)


def _has_field(item: Any, field: str) -> bool:
    """Check whether a named field exists on a result item."""
    if isinstance(item, dict):
        return field in item
    return hasattr(item, field)


# ---------------------------------------------------------------------------
# TestFromAC_GetConsolidationCandidates
# ---------------------------------------------------------------------------


class TestFromAC_GetConsolidationCandidates:
    """Tests derived from AC1, AC2, AC3 for get_consolidation_candidates."""

    # --- AC1: deterministic SQL, ORDER BY entity_name, 2+ sources (td:2) ---

    @pytest.mark.asyncio
    async def test_entity_in_two_sources_appears_as_candidate(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC1 happy: entity name appearing in 2 distinct sources is returned."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Python", document_id=doc_a)
        _insert_entity(conn, name="Python", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [_get_field(c, "entity_name") for c in candidates]
        assert "Python" in names, f"Expected 'Python' in candidates, got: {names}"

    @pytest.mark.asyncio
    async def test_candidates_ordered_alphabetically_by_entity_name(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC1 boundary: results ordered alphabetically ascending by entity_name."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        # Insert in reverse alphabetical order to prove ordering is not insertion-order
        _insert_entity(conn, name="Zebra", document_id=doc_a)
        _insert_entity(conn, name="Zebra", document_id=doc_b)
        _insert_entity(conn, name="Alpha", document_id=doc_a)
        _insert_entity(conn, name="Alpha", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [_get_field(c, "entity_name") for c in candidates]
        alpha_index = names.index("Alpha")
        zebra_index = names.index("Zebra")
        assert alpha_index < zebra_index, (
            f"Expected 'Alpha' before 'Zebra' (ORDER BY entity_name), "
            f"got indices {alpha_index} and {zebra_index} in: {names}"
        )

    @pytest.mark.asyncio
    async def test_limit_caps_number_of_candidates(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC1 boundary: limit=1 returns at most 1 result even with multiple candidates."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        for name in ("Alpha", "Beta", "Gamma"):
            _insert_entity(conn, name=name, document_id=doc_a)
            _insert_entity(conn, name=name, document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=1)

        assert len(candidates) <= 1, (
            f"Expected at most 1 candidate with limit=1, got {len(candidates)}"
        )

    @pytest.mark.asyncio
    async def test_entity_in_single_source_excluded_from_candidates(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC1 edge: entity name appearing in only one source is NOT returned."""
        source_a = _insert_source(conn, name="Source A")
        doc_a = _insert_document(conn, source_id=source_a)
        _insert_entity(conn, name="SingleSourceEntity", document_id=doc_a)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [_get_field(c, "entity_name") for c in candidates]
        assert "SingleSourceEntity" not in names, (
            f"Expected 'SingleSourceEntity' excluded (only 1 source), got: {names}"
        )

    # --- AC2: exclude entries with cross-source edges or reviewed_pairs (td:2) ---

    @pytest.mark.asyncio
    async def test_entity_with_cross_source_edge_excluded_from_candidates(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC2 edge: entity pair with existing cross-source edge is excluded."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        entity_a_id = _insert_entity(conn, name="PyTorch", document_id=doc_a)
        entity_b_id = _insert_entity(conn, name="PyTorch", document_id=doc_b)
        # Insert a cross-source edge between the two entity records
        _insert_edge(conn, source_entity_id=entity_a_id, target_entity_id=entity_b_id)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [_get_field(c, "entity_name") for c in candidates]
        assert "PyTorch" not in names, (
            f"Expected 'PyTorch' excluded (cross-source edge exists), got: {names}"
        )

    @pytest.mark.asyncio
    async def test_entity_with_reviewed_pairs_entry_excluded_from_candidates(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC2 boundary: entity pair with reviewed_pairs dismissal is excluded."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Keras", document_id=doc_a)
        _insert_entity(conn, name="Keras", document_id=doc_b)
        _insert_reviewed_pair(
            conn, entity_name="Keras", source_a=source_a, source_b=source_b
        )

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [_get_field(c, "entity_name") for c in candidates]
        assert "Keras" not in names, (
            f"Expected 'Keras' excluded (reviewed_pairs entry exists), got: {names}"
        )

    @pytest.mark.asyncio
    async def test_other_entity_candidates_unaffected_by_reviewed_pair(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC2 edge: reviewed_pairs exclusion is entity+source-pair scoped, not global."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        # Dismissed entity
        _insert_entity(conn, name="Dismissed", document_id=doc_a)
        _insert_entity(conn, name="Dismissed", document_id=doc_b)
        _insert_reviewed_pair(
            conn, entity_name="Dismissed", source_a=source_a, source_b=source_b
        )
        # Other entity that should still appear
        _insert_entity(conn, name="Active", document_id=doc_a)
        _insert_entity(conn, name="Active", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [_get_field(c, "entity_name") for c in candidates]
        assert "Active" in names, (
            f"Expected 'Active' in candidates (no dismissal for it), got: {names}"
        )
        assert "Dismissed" not in names, (
            f"Expected 'Dismissed' excluded (dismissed pair), got: {names}"
        )

    # --- AC3: candidates return list of dicts with entity_name + chunks (td:1) ---

    @pytest.mark.asyncio
    async def test_candidate_dict_contains_entity_name_key(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 smoke: each candidate dict has an 'entity_name' key."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="NumPy", document_id=doc_a)
        _insert_entity(conn, name="NumPy", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        assert len(candidates) >= 1, "Expected at least one candidate"
        candidate = candidates[0]
        assert _has_field(candidate, "entity_name"), (
            f"Expected 'entity_name' field in candidate dict, got: {candidate}"
        )
        assert _get_field(candidate, "entity_name") == "NumPy"

    @pytest.mark.asyncio
    async def test_candidate_dict_contains_chunks_from_both_sources(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 smoke: candidate dict includes chunk content from both sources."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        entity_a = _insert_entity(conn, name="TensorFlow", document_id=doc_a)
        entity_b = _insert_entity(conn, name="TensorFlow", document_id=doc_b)
        _insert_chunk(conn, document_id=doc_a, content="TensorFlow chunk from source A")
        _insert_chunk(conn, document_id=doc_b, content="TensorFlow chunk from source B")
        # Link chunks to entities
        conn.execute(
            "UPDATE entities SET chunk_id = (SELECT id FROM chunks WHERE document_id = ? LIMIT 1) "
            "WHERE id = ?",
            (doc_a, entity_a),
        )
        conn.execute(
            "UPDATE entities SET chunk_id = (SELECT id FROM chunks WHERE document_id = ? LIMIT 1) "
            "WHERE id = ?",
            (doc_b, entity_b),
        )
        conn.commit()

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        assert len(candidates) >= 1, "Expected at least one candidate for 'TensorFlow'"
        tf_candidates = [
            c for c in candidates if _get_field(c, "entity_name") == "TensorFlow"
        ]
        assert tf_candidates, "Expected 'TensorFlow' in candidates"
        candidate = tf_candidates[0]

        # The candidate must carry context from BOTH sources — check via serialized form
        candidate_str = str(candidate)
        assert (
            "Source A" in candidate_str
            or "source_a" in candidate_str.lower()
            or any(
                "source" in str(_get_field(candidate, k)).lower()
                for k in (candidate.keys() if isinstance(candidate, dict) else [])
            )
        ), (
            "Expected candidate to contain source information from both sources, "
            f"got: {candidate}"
        )

    @pytest.mark.asyncio
    async def test_candidate_chunk_payloads_are_exact_source_content(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 exact (retry): source_a_chunk and source_b_chunk fields hold the
        specific chunk content for each source — not just a substring of the
        serialised candidate object."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        chunk_a = _insert_chunk(
            conn, document_id=doc_a, content="Chunk text from Source A only"
        )
        chunk_b = _insert_chunk(
            conn, document_id=doc_b, content="Chunk text from Source B only"
        )
        _insert_entity(
            conn, name="TensorFlowExact", document_id=doc_a, chunk_id=chunk_a
        )
        _insert_entity(
            conn, name="TensorFlowExact", document_id=doc_b, chunk_id=chunk_b
        )

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        tf_candidates = [
            c for c in candidates if _get_field(c, "entity_name") == "TensorFlowExact"
        ]
        assert tf_candidates, "Expected 'TensorFlowExact' in candidates"
        candidate = tf_candidates[0]

        source_a_chunk = _get_field(candidate, "source_a_chunk")
        source_b_chunk = _get_field(candidate, "source_b_chunk")

        actual_chunks = {source_a_chunk, source_b_chunk}
        assert "Chunk text from Source A only" in actual_chunks, (
            "Expected 'Chunk text from Source A only' in source_a_chunk or source_b_chunk, "
            f"got: source_a_chunk={source_a_chunk!r}, source_b_chunk={source_b_chunk!r}"
        )
        assert "Chunk text from Source B only" in actual_chunks, (
            "Expected 'Chunk text from Source B only' in source_a_chunk or source_b_chunk, "
            f"got: source_a_chunk={source_a_chunk!r}, source_b_chunk={source_b_chunk!r}"
        )
        assert source_a_chunk != source_b_chunk, (
            "source_a_chunk and source_b_chunk must be distinct (different source content)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_StoreEnrichmentPhase2
# ---------------------------------------------------------------------------


class TestFromAC_StoreEnrichmentPhase2:
    """Tests derived from AC4, AC5, AC6 for Phase 2 store_enrichment behavior."""

    # --- AC4: Phase 2 with non-empty edges writes cross-source edges (td:1) ---

    @pytest.mark.asyncio
    async def test_phase2_non_empty_edges_writes_edge_to_db(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC4 smoke: Phase 2 call with edges=[...] inserts edge into edges table."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        entity_a_id = _insert_entity(conn, name="JAX", document_id=doc_a)
        entity_b_id = _insert_entity(conn, name="JAX", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        # get_consolidation_candidates returns the candidate with its candidate_id
        candidates = await get_consolidation_candidates(ctx, limit=20)
        jax_candidates = [
            c for c in candidates if _get_field(c, "entity_name") == "JAX"
        ]
        assert jax_candidates, "Expected 'JAX' to be a candidate"
        candidate_id = _get_field(jax_candidates[0], "candidate_id")

        edges_before = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        # Phase 2 call: (ctx, candidate_id, edges=[...]) — different from Phase 1
        await store_enrichment(
            ctx,
            candidate_id=candidate_id,
            edges=[
                {
                    "source_id": entity_a_id,
                    "target_id": entity_b_id,
                    "relation": "same_as",
                }
            ],
        )

        edges_after = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert edges_after == edges_before + 1, (
            f"Expected 1 new edge after Phase 2 store_enrichment with non-empty edges, "
            f"before={edges_before}, after={edges_after}"
        )

    # --- AC5: Phase 2 with empty edges marks reviewed_pairs (td:1) ---

    @pytest.mark.asyncio
    async def test_phase2_empty_edges_inserts_reviewed_pair_dismissal(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC5 smoke: Phase 2 call with edges=[] inserts row into reviewed_pairs."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="SciPy", document_id=doc_a)
        _insert_entity(conn, name="SciPy", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)
        scipy_candidates = [
            c for c in candidates if _get_field(c, "entity_name") == "SciPy"
        ]
        assert scipy_candidates, "Expected 'SciPy' to be a candidate"
        candidate_id = _get_field(scipy_candidates[0], "candidate_id")

        reviewed_before = conn.execute(
            "SELECT COUNT(*) FROM reviewed_pairs"
        ).fetchone()[0]

        # Phase 2 dismissal: empty edges
        await store_enrichment(ctx, candidate_id=candidate_id, edges=[])

        reviewed_after = conn.execute("SELECT COUNT(*) FROM reviewed_pairs").fetchone()[
            0
        ]
        assert reviewed_after == reviewed_before + 1, (
            f"Expected 1 new reviewed_pairs row after dismissal, "
            f"before={reviewed_before}, after={reviewed_after}"
        )

    @pytest.mark.asyncio
    async def test_phase2_empty_edges_does_not_write_new_edges(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC5 boundary: dismissal writes no edges — only marks reviewed_pairs."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Matplotlib", document_id=doc_a)
        _insert_entity(conn, name="Matplotlib", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)
        mpl_candidates = [
            c for c in candidates if _get_field(c, "entity_name") == "Matplotlib"
        ]
        assert mpl_candidates, "Expected 'Matplotlib' to be a candidate"
        candidate_id = _get_field(mpl_candidates[0], "candidate_id")

        edges_before = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        await store_enrichment(ctx, candidate_id=candidate_id, edges=[])
        edges_after = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        assert edges_after == edges_before, (
            f"Expected no new edges written for a dismissal, "
            f"before={edges_before}, after={edges_after}"
        )

    # --- AC6: new sources generate new candidate pairs; old dismissals preserved (td:2) ---

    @pytest.mark.asyncio
    async def test_new_source_generates_new_candidate_pair_for_same_entity(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 happy: after dismissing (entity, A, B), adding source C creates (entity, *, C) candidate."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Pandas", document_id=doc_a)
        _insert_entity(conn, name="Pandas", document_id=doc_b)
        # Dismiss the (A, B) pair for "Pandas"
        _insert_reviewed_pair(
            conn, entity_name="Pandas", source_a=source_a, source_b=source_b
        )

        # Add a new source C with the same entity
        source_c = _insert_source(conn, name="Source C")
        doc_c = _insert_document(conn, source_id=source_c)
        _insert_entity(conn, name="Pandas", document_id=doc_c)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [_get_field(c, "entity_name") for c in candidates]
        assert "Pandas" in names, (
            f"Expected 'Pandas' back in candidates after new source C added, "
            f"got: {names}"
        )

    @pytest.mark.asyncio
    async def test_old_dismissal_preserved_in_reviewed_pairs_after_new_source(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 boundary: reviewed_pairs row (A, B) still present after source C is added."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Seaborn", document_id=doc_a)
        _insert_entity(conn, name="Seaborn", document_id=doc_b)
        _insert_reviewed_pair(
            conn, entity_name="Seaborn", source_a=source_a, source_b=source_b
        )

        source_c = _insert_source(conn, name="Source C")
        doc_c = _insert_document(conn, source_id=source_c)
        _insert_entity(conn, name="Seaborn", document_id=doc_c)

        # Calling get_consolidation_candidates should NOT delete old reviewed_pairs rows
        ctx = _make_mcp_ctx(conn)
        await get_consolidation_candidates(ctx, limit=20)

        row = conn.execute(
            "SELECT 1 FROM reviewed_pairs "
            "WHERE entity_name = ? AND source_a = ? AND source_b = ?",
            ("Seaborn", source_a, source_b),
        ).fetchone()
        assert row is not None, (
            "Expected reviewed_pairs entry (Seaborn, A, B) to be preserved after "
            "new source C was added and get_consolidation_candidates was called"
        )

    @pytest.mark.asyncio
    async def test_dismissed_pair_remains_excluded_after_new_source_added(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 boundary: (entity, A, B) pair stays excluded from candidates even after source C added."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Bokeh", document_id=doc_a)
        _insert_entity(conn, name="Bokeh", document_id=doc_b)
        _insert_reviewed_pair(
            conn, entity_name="Bokeh", source_a=source_a, source_b=source_b
        )

        # Add source C — generates new (Bokeh, ?, C) pair, but (A, B) stays dismissed
        source_c = _insert_source(conn, name="Source C")
        doc_c = _insert_document(conn, source_id=source_c)
        _insert_entity(conn, name="Bokeh", document_id=doc_c)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        # There should be at most 2 "Bokeh" candidate pairs (A-C and B-C), but NOT A-B
        bokeh_candidates = [
            c for c in candidates if _get_field(c, "entity_name") == "Bokeh"
        ]
        # Verify: no candidate has source_a, source_b that match the dismissed pair
        # The key assertion: only NEW pairs appear, not the dismissed (A, B) pair
        # If the implementation encodes source info in the candidate, check directly:
        for cand in bokeh_candidates:
            cand_str = str(cand)
            # The dismissed A-B pair must not appear as a candidate
            # (Both source_a AND source_b appear together only in dismissed pair)
            has_a = source_a in cand_str
            has_b = source_b in cand_str
            # The pair encoding both A and B is the dismissed pair
            assert not (has_a and has_b), (
                f"Expected dismissed pair (A, B) to remain excluded, "
                f"but found candidate referencing both sources: {cand}"
            )

    @pytest.mark.asyncio
    async def test_exact_candidate_pairs_after_dismissal_and_new_source(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC6 exact (retry): after dismissing (Dask, A, B), only the (A,C) and (B,C)
        pairs appear for 'Dask' — proven via structured source_a/source_b fields,
        not via string representation of the candidate object."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="DaskExact", document_id=doc_a)
        _insert_entity(conn, name="DaskExact", document_id=doc_b)
        _insert_reviewed_pair(
            conn, entity_name="DaskExact", source_a=source_a, source_b=source_b
        )

        source_c = _insert_source(conn, name="Source C")
        doc_c = _insert_document(conn, source_id=source_c)
        _insert_entity(conn, name="DaskExact", document_id=doc_c)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        dask_candidates = [
            c for c in candidates if _get_field(c, "entity_name") == "DaskExact"
        ]

        candidate_pairs = {
            frozenset({_get_field(c, "source_a"), _get_field(c, "source_b")})
            for c in dask_candidates
        }

        ab_pair = frozenset({source_a, source_b})
        assert ab_pair not in candidate_pairs, (
            f"Dismissed (A, B) pair must not appear in structured candidates, "
            f"got pairs: {candidate_pairs}"
        )

        ac_pair = frozenset({source_a, source_c})
        bc_pair = frozenset({source_b, source_c})
        assert candidate_pairs == {ac_pair, bc_pair}, (
            f"Expected exactly pairs {{(A,C), (B,C)}}, got: {candidate_pairs}. "
            f"Raw candidates: {dask_candidates}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GetStatsExpansion
# ---------------------------------------------------------------------------


class TestFromAC_GetStatsExpansion:
    """Tests derived from AC7 for get_stats additive expansion."""

    # --- AC7: preserves existing fields AND adds new Phase 2 fields (td:2) ---

    @pytest.mark.asyncio
    async def test_stats_preserves_existing_documents_field(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 happy: 'documents' field still present and matches graph_store count."""
        ctx = _make_mcp_ctx_with_graph(conn, doc_count=7, entity_count=0, edge_count=0)
        result = await get_stats(ctx)
        assert "documents" in result, (
            f"Expected 'documents' key in stats, got: {result}"
        )
        assert result["documents"] == 7, (
            f"Expected documents=7 from graph_store.get_counts(), got: {result['documents']}"
        )

    @pytest.mark.asyncio
    async def test_stats_preserves_existing_entities_field(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 happy: 'entities' field still present and matches graph_store count."""
        ctx = _make_mcp_ctx_with_graph(conn, doc_count=0, entity_count=42, edge_count=0)
        result = await get_stats(ctx)
        assert "entities" in result, f"Expected 'entities' key in stats, got: {result}"
        assert result["entities"] == 42

    @pytest.mark.asyncio
    async def test_stats_preserves_existing_edges_field(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 happy: 'edges' field still present and matches graph_store count."""
        ctx = _make_mcp_ctx_with_graph(conn, doc_count=0, entity_count=0, edge_count=15)
        result = await get_stats(ctx)
        assert "edges" in result, f"Expected 'edges' key in stats, got: {result}"
        assert result["edges"] == 15

    @pytest.mark.asyncio
    async def test_stats_returns_total_sources_field(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 happy: 'total_sources' field is present and counts knowledge_sources rows."""
        _insert_source(conn, name="Source A")
        _insert_source(conn, name="Source B")
        _insert_source(conn, name="Source C")

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "total_sources" in result, (
            f"Expected 'total_sources' key in expanded stats, got: {list(result.keys())}"
        )
        assert result["total_sources"] == 3, (
            f"Expected total_sources=3 (3 sources inserted), got: {result['total_sources']}"
        )

    @pytest.mark.asyncio
    async def test_stats_returns_total_chunks_field(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 happy: 'total_chunks' field is present and counts chunks rows."""
        source_a = _insert_source(conn, name="Source A")
        doc_a = _insert_document(conn, source_id=source_a)
        _insert_chunk(conn, document_id=doc_a)
        _insert_chunk(conn, document_id=doc_a)
        _insert_chunk(conn, document_id=doc_a)

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "total_chunks" in result, (
            f"Expected 'total_chunks' key in expanded stats, got: {list(result.keys())}"
        )
        assert result["total_chunks"] == 3, (
            f"Expected total_chunks=3, got: {result['total_chunks']}"
        )

    @pytest.mark.asyncio
    async def test_stats_returns_chunks_enriched_ratio_field(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 happy: 'chunks_enriched_ratio' present and equals enriched/total."""
        source_a = _insert_source(conn, name="Source A")
        doc_a = _insert_document(conn, source_id=source_a)
        _insert_chunk(conn, document_id=doc_a, enrichment_state="enriched")
        _insert_chunk(conn, document_id=doc_a, enrichment_state="enriched")
        _insert_chunk(conn, document_id=doc_a, enrichment_state="pending")
        _insert_chunk(conn, document_id=doc_a, enrichment_state="pending")

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "chunks_enriched_ratio" in result, (
            f"Expected 'chunks_enriched_ratio' key in expanded stats, got: {list(result.keys())}"
        )
        # 2 enriched / 4 total = 0.5
        ratio = result["chunks_enriched_ratio"]
        assert abs(ratio - 0.5) < 1e-9, (
            f"Expected chunks_enriched_ratio=0.5 (2 enriched of 4 total), got: {ratio}"
        )

    @pytest.mark.asyncio
    async def test_stats_returns_consolidation_candidates_remaining_field(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 happy: 'consolidation_candidates_remaining' present and reflects candidate count."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="SciKit", document_id=doc_a)
        _insert_entity(conn, name="SciKit", document_id=doc_b)

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "consolidation_candidates_remaining" in result, (
            f"Expected 'consolidation_candidates_remaining' in expanded stats, "
            f"got: {list(result.keys())}"
        )
        assert result["consolidation_candidates_remaining"] >= 1, (
            f"Expected at least 1 consolidation candidate remaining (SciKit in 2 sources), "
            f"got: {result['consolidation_candidates_remaining']}"
        )

    @pytest.mark.asyncio
    async def test_stats_enriched_ratio_is_zero_when_no_chunks(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 boundary: chunks_enriched_ratio = 0.0 when no chunks exist (no division by zero)."""
        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "chunks_enriched_ratio" in result, (
            f"Expected 'chunks_enriched_ratio' key, got: {list(result.keys())}"
        )
        assert result["chunks_enriched_ratio"] == 0.0, (
            f"Expected chunks_enriched_ratio=0.0 with no chunks, "
            f"got: {result['chunks_enriched_ratio']}"
        )

    @pytest.mark.asyncio
    async def test_stats_enriched_ratio_is_one_when_all_chunks_enriched(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 boundary: chunks_enriched_ratio = 1.0 when all chunks are enriched."""
        source_a = _insert_source(conn, name="Source A")
        doc_a = _insert_document(conn, source_id=source_a)
        _insert_chunk(conn, document_id=doc_a, enrichment_state="enriched")
        _insert_chunk(conn, document_id=doc_a, enrichment_state="enriched")

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        ratio = result.get("chunks_enriched_ratio")
        assert ratio == 1.0, (
            f"Expected chunks_enriched_ratio=1.0 when all chunks enriched, got: {ratio}"
        )

    @pytest.mark.asyncio
    async def test_stats_total_sources_zero_when_no_sources(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 boundary: total_sources = 0 when knowledge_sources table is empty."""
        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "total_sources" in result
        assert result["total_sources"] == 0, (
            f"Expected total_sources=0 with no sources, got: {result['total_sources']}"
        )

    @pytest.mark.asyncio
    async def test_stats_consolidation_candidates_zero_when_all_pairs_dismissed(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 boundary: consolidation_candidates_remaining = 0 when all pairs dismissed."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Arrow", document_id=doc_a)
        _insert_entity(conn, name="Arrow", document_id=doc_b)
        _insert_reviewed_pair(
            conn, entity_name="Arrow", source_a=source_a, source_b=source_b
        )

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "consolidation_candidates_remaining" in result
        assert result["consolidation_candidates_remaining"] == 0, (
            f"Expected 0 candidates remaining (all pairs dismissed), "
            f"got: {result['consolidation_candidates_remaining']}"
        )

    @pytest.mark.asyncio
    async def test_stats_consolidation_candidates_remaining_exact_count(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC7 exact (retry): consolidation_candidates_remaining == 1 for a
        single-pair fixture — not >= 1, so overcounting is caught."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="Polars", document_id=doc_a)
        _insert_entity(conn, name="Polars", document_id=doc_b)

        ctx = _make_mcp_ctx_with_graph(conn)
        result = await get_stats(ctx)

        assert "consolidation_candidates_remaining" in result, (
            f"Expected 'consolidation_candidates_remaining' in stats, "
            f"got: {list(result.keys())}"
        )
        assert result["consolidation_candidates_remaining"] == 1, (
            f"Expected exactly 1 consolidation_candidates_remaining "
            f"(single pair: Polars in sources A and B), "
            f"got: {result['consolidation_candidates_remaining']}"
        )


# ---------------------------------------------------------------------------
# Additional exact-proof tests for AC3, AC4, AC5 (cycle-2 review gaps)
# ---------------------------------------------------------------------------


class TestFromAC_ExactProofs:
    """Cycle-2 retry: exact assertions for AC3 dict shape, AC4 edge row, AC5 reviewed_pairs row."""

    @pytest.mark.asyncio
    async def test_ac3_candidates_are_dicts_not_objects(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 exact (cycle 2): every candidate must be a plain dict — isinstance(candidate, dict)
        required so duck-typing objects cannot slip past the shape contract."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="DictProofEntity", document_id=doc_a)
        _insert_entity(conn, name="DictProofEntity", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        assert len(candidates) >= 1, "Expected at least one candidate"
        for candidate in candidates:
            assert isinstance(candidate, dict), (
                f"Expected each candidate to be a plain dict, "
                f"got {type(candidate).__name__}: {candidate!r}"
            )

    @pytest.mark.asyncio
    async def test_ac4_exact_edge_row_content_after_phase2_store(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC4 exact (cycle 2): store_enrichment Phase 2 with non-empty edges writes
        an edge row whose source_id, target_id, and relation exactly match the
        caller-supplied values — not just a count increment."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        entity_a_id = _insert_entity(conn, name="ExactEdgeEntity", document_id=doc_a)
        entity_b_id = _insert_entity(conn, name="ExactEdgeEntity", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)
        target = next(
            c for c in candidates if _get_field(c, "entity_name") == "ExactEdgeEntity"
        )
        candidate_id = _get_field(target, "candidate_id")

        await store_enrichment(
            ctx,
            candidate_id=candidate_id,
            edges=[
                {
                    "source_id": entity_a_id,
                    "target_id": entity_b_id,
                    "relation": "exact_match_proof",
                }
            ],
        )

        row = conn.execute(
            "SELECT source_id, target_id, relation FROM edges "
            "WHERE source_id = ? AND target_id = ? AND relation = ?",
            (entity_a_id, entity_b_id, "exact_match_proof"),
        ).fetchone()
        assert row is not None, (
            f"Expected edge row (source_id={entity_a_id!r}, "
            f"target_id={entity_b_id!r}, relation='exact_match_proof') — not found in DB"
        )
        assert row[0] == entity_a_id, (
            f"source_id mismatch: {row[0]!r} != {entity_a_id!r}"
        )
        assert row[1] == entity_b_id, (
            f"target_id mismatch: {row[1]!r} != {entity_b_id!r}"
        )
        assert row[2] == "exact_match_proof", f"relation mismatch: {row[2]!r}"

    @pytest.mark.asyncio
    async def test_ac5_exact_reviewed_pairs_row_content_after_dismissal(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC5 exact (cycle 2): store_enrichment Phase 2 with edges=[] writes a
        reviewed_pairs row whose entity_name, source_a, source_b match the candidate
        decoded from candidate_id — not just a count increment."""
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        _insert_entity(conn, name="ExactDismissalEntity", document_id=doc_a)
        _insert_entity(conn, name="ExactDismissalEntity", document_id=doc_b)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)
        target = next(
            c
            for c in candidates
            if _get_field(c, "entity_name") == "ExactDismissalEntity"
        )
        candidate_id = _get_field(target, "candidate_id")

        await store_enrichment(ctx, candidate_id=candidate_id, edges=[])

        row = conn.execute(
            "SELECT entity_name, source_a, source_b FROM reviewed_pairs "
            "WHERE entity_name = ?",
            ("ExactDismissalEntity",),
        ).fetchone()
        assert row is not None, (
            "Expected reviewed_pairs row for 'ExactDismissalEntity' — not found in DB"
        )
        assert row[0] == "ExactDismissalEntity", (
            f"entity_name mismatch: {row[0]!r} != 'ExactDismissalEntity'"
        )
        # source_a and source_b may be stored in canonicalized order — check set equality
        stored_sources = {row[1], row[2]}
        expected_sources = {source_a, source_b}
        assert stored_sources == expected_sources, (
            f"Expected reviewed_pairs sources to be {expected_sources}, "
            f"got: {stored_sources}"
        )


# ---------------------------------------------------------------------------
# Cycle-3 proof tests: AC2 reversed order, AC3 positional chunks, AC5 positional columns
# ---------------------------------------------------------------------------


class TestFromAC_Cycle3Proofs:
    """Cycle-3 retry: close remaining false-green paths in AC2, AC3, and AC5."""

    # --- AC2: reversed reviewed_pairs still excludes candidate ---

    @pytest.mark.asyncio
    async def test_ac2_reversed_reviewed_pair_still_excludes_candidate(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC2 exact (cycle 3): a reviewed_pairs row inserted with source_a and source_b
        swapped relative to the candidate's canonical order (min/max) must still exclude
        the pair — proving the OR branch in the SQL filter fires correctly."""
        source_x = _insert_source(conn, name="Source X")
        source_y = _insert_source(conn, name="Source Y")
        doc_x = _insert_document(conn, source_id=source_x)
        doc_y = _insert_document(conn, source_id=source_y)
        _insert_entity(conn, name="ReversedPairEntity", document_id=doc_x)
        _insert_entity(conn, name="ReversedPairEntity", document_id=doc_y)

        # Determine which source_id is canonical source_a (the lexicographically smaller one)
        canonical_a, canonical_b = (
            (source_x, source_y) if source_x < source_y else (source_y, source_x)
        )
        # Insert reviewed_pairs with the order DELIBERATELY REVERSED
        _insert_reviewed_pair(
            conn,
            entity_name="ReversedPairEntity",
            source_a=canonical_b,
            source_b=canonical_a,
        )

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [c["entity_name"] for c in candidates]
        assert "ReversedPairEntity" not in names, (
            "Expected 'ReversedPairEntity' excluded even when reviewed_pairs row uses "
            f"reversed source_a/source_b order — got candidates: {names}"
        )

    # --- AC3: positional chunk content assertion (direct dict indexing, no set) ---

    @pytest.mark.asyncio
    async def test_ac3_source_a_chunk_and_source_b_chunk_match_positionally(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC3 exact (cycle 3): source_a_chunk must equal the chunk text from the
        source assigned as source_a (min source_id), and source_b_chunk must equal
        the chunk text from the source assigned as source_b (max source_id) — tested
        with direct dict key access, no set comparison, no _get_field helper."""
        source_p = _insert_source(conn, name="Source P")
        source_q = _insert_source(conn, name="Source Q")
        doc_p = _insert_document(conn, source_id=source_p)
        doc_q = _insert_document(conn, source_id=source_q)
        chunk_p = _insert_chunk(
            conn, document_id=doc_p, content="Positional chunk from Source P"
        )
        chunk_q = _insert_chunk(
            conn, document_id=doc_q, content="Positional chunk from Source Q"
        )
        _insert_entity(
            conn, name="PositionalChunkEntity", document_id=doc_p, chunk_id=chunk_p
        )
        _insert_entity(
            conn, name="PositionalChunkEntity", document_id=doc_q, chunk_id=chunk_q
        )

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        target = next(
            c for c in candidates if c["entity_name"] == "PositionalChunkEntity"
        )

        # Determine canonical assignment: source with smaller string ID becomes source_a
        if source_p < source_q:
            expected_source_a_chunk = "Positional chunk from Source P"
            expected_source_b_chunk = "Positional chunk from Source Q"
        else:
            expected_source_a_chunk = "Positional chunk from Source Q"
            expected_source_b_chunk = "Positional chunk from Source P"

        # Positional equality — direct dict indexing, no set/frozenset
        assert target["source_a_chunk"] == expected_source_a_chunk, (
            f"source_a_chunk must equal the chunk from canonical source_a exactly — "
            f"expected {expected_source_a_chunk!r}, got {target['source_a_chunk']!r}"
        )
        assert target["source_b_chunk"] == expected_source_b_chunk, (
            f"source_b_chunk must equal the chunk from canonical source_b exactly — "
            f"expected {expected_source_b_chunk!r}, got {target['source_b_chunk']!r}"
        )

    # --- AC5: positional column equality decoded from candidate_id ---

    @pytest.mark.asyncio
    async def test_ac5_reviewed_pairs_columns_match_candidate_id_decoded_positionally(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC5 exact (cycle 3): after store_enrichment(ctx, candidate_id=..., edges=[]),
        the reviewed_pairs row's source_a column must equal json.loads(candidate_id)[1]
        and source_b column must equal json.loads(candidate_id)[2] — no set comparison."""
        import json as _json  # noqa: PLC0415

        source_r = _insert_source(conn, name="Source R")
        source_s = _insert_source(conn, name="Source S")
        doc_r = _insert_document(conn, source_id=source_r)
        doc_s = _insert_document(conn, source_id=source_s)
        _insert_entity(conn, name="PositionalDismissalEntity", document_id=doc_r)
        _insert_entity(conn, name="PositionalDismissalEntity", document_id=doc_s)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)
        target = next(
            c for c in candidates if c["entity_name"] == "PositionalDismissalEntity"
        )
        candidate_id = target["candidate_id"]

        # Decode per implementation contract: json.loads(candidate_id) == [entity_name, source_a, source_b]
        decoded = _json.loads(candidate_id)
        decoded_entity_name: str = decoded[0]
        decoded_source_a: str = decoded[1]
        decoded_source_b: str = decoded[2]

        await store_enrichment(ctx, candidate_id=candidate_id, edges=[])

        row = conn.execute(
            "SELECT entity_name, source_a, source_b FROM reviewed_pairs "
            "WHERE entity_name = ?",
            (decoded_entity_name,),
        ).fetchone()
        assert row is not None, (
            f"Expected reviewed_pairs row for {decoded_entity_name!r} — not found in DB"
        )
        # Positional column equality — no set/frozenset comparison
        assert row[1] == decoded_source_a, (
            f"reviewed_pairs.source_a must equal decoded candidate_id source_a exactly — "
            f"expected {decoded_source_a!r}, got {row[1]!r}"
        )
        assert row[2] == decoded_source_b, (
            f"reviewed_pairs.source_b must equal decoded candidate_id source_b exactly — "
            f"expected {decoded_source_b!r}, got {row[2]!r}"
        )


# ---------------------------------------------------------------------------
# Cycle-4 proof tests: AC2 reverse cross-source edge direction
# ---------------------------------------------------------------------------


class TestFromAC_Cycle4Proofs:
    """Cycle-4 retry: prove the reverse edge-direction SQL branch for AC2.

    The candidate query join uses ``e1.id < e2.id``, so the forward exclusion
    branch is ``ed.source_id = e1.id AND ed.target_id = e2.id`` (server.py:233)
    and the reverse branch is ``ed.source_id = e2.id AND ed.target_id = e1.id``
    (server.py:234).  Removing server.py:234 must cause this test to fail.
    """

    @pytest.mark.asyncio
    async def test_ac2_reversed_edge_direction_still_excludes_candidate(
        self, conn: sqlite3.Connection
    ) -> None:
        """AC2 exact (cycle 4): a cross-source edge inserted in the *reverse* entity
        ordering (source_entity_id = the larger-id entity, target_entity_id = the
        smaller-id entity) must still exclude the candidate pair.

        The candidate SQL join is ``e1.id < e2.id``, so the forward branch handles
        edges ``(e1, e2)`` and the reverse branch handles edges ``(e2, e1)``
        (``server.py:234``).  This test inserts only the reverse-direction edge, so
        removing that branch from the SQL would leave the candidate visible and cause
        this test to fail.
        """
        source_a = _insert_source(conn, name="Source A")
        source_b = _insert_source(conn, name="Source B")
        doc_a = _insert_document(conn, source_id=source_a)
        doc_b = _insert_document(conn, source_id=source_b)
        entity_a_id = _insert_entity(conn, name="ReverseEdgeEntity", document_id=doc_a)
        entity_b_id = _insert_entity(conn, name="ReverseEdgeEntity", document_id=doc_b)

        # In the SQL join: e1.id < e2.id, so e1 = smaller string ID, e2 = larger.
        # The forward exclusion branch covers (e1→e2); we need to exercise (e2→e1).
        e1_id = min(entity_a_id, entity_b_id)
        e2_id = max(entity_a_id, entity_b_id)
        # Insert ONLY the reverse-direction edge (e2 → e1)
        _insert_edge(conn, source_entity_id=e2_id, target_entity_id=e1_id)

        ctx = _make_mcp_ctx(conn)
        candidates = await get_consolidation_candidates(ctx, limit=20)

        names = [c["entity_name"] for c in candidates]
        assert "ReverseEdgeEntity" not in names, (
            "Expected 'ReverseEdgeEntity' excluded because a reverse-direction cross-source "
            "edge (e2→e1) exists — but it appeared in candidates. "
            "This proves the OR branch at server.py:234 is required.\n"
            f"Got candidates: {names}"
        )


# --- merged from tests/test_mcp_knowledge_phase2_tools_1330.py ---
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


import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_knowledge.schema import init_db
from owlbear_mcp_knowledge.server import (
    get_consolidation_candidates,
    get_stats,
    store_enrichment,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers (mirrors _1329 but self-contained for isolation)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TestFromAC_GetConsolidationCandidates (1330 additions)
# ---------------------------------------------------------------------------


class TestFromAC_GetConsolidationCandidates_1330:
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

        assert isinstance(candidates, list), f"Expected list, got {type(candidates)}"
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

        nce = [
            c for c in candidates if _get_field(c, "entity_name") == "NullChunkEntity"
        ]
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


class TestFromAC_StoreEnrichmentPhase2_1330:
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

        multi_cands = [
            c for c in candidates if _get_field(c, "entity_name") == "MultiEdge"
        ]
        assert multi_cands, "Expected 'MultiEdge' to be a candidate"
        candidate_id = _get_field(multi_cands[0], "candidate_id")

        edges_before = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        await store_enrichment(
            ctx,
            candidate_id=candidate_id,
            edges=[
                {"source_id": entity_a1, "target_id": entity_b1, "relation": "same_as"},
                {
                    "source_id": entity_a2,
                    "target_id": entity_b2,
                    "relation": "related_to",
                },
                {
                    "source_id": entity_b1,
                    "target_id": entity_a2,
                    "relation": "references",
                },
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
        ie_cands = [
            c for c in candidates if _get_field(c, "entity_name") == "IdempotentEntity"
        ]
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


class TestFromAC_GetStatsExpansion_1330:
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
