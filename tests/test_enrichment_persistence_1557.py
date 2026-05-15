"""Tests for manual enrichment graph persistence contract — task #1557.

Covers AC-1 through AC-6:
- AC-1: get_next_batch must return provenance fields (document_id, source_id, scope)
- AC-2: store_enrichment Phase 1 must derive entity/edge provenance server-side
- AC-3: store_enrichment must reject unresolvable provenance without inserting NULL rows
- AC-4: get_consolidation_candidates must expose durable entity row identifiers
- AC-5: store_enrichment Phase 2 must persist edges with non-NULL endpoints
- AC-6: get_next_batch must exclude orphan chunks (document.source_id = NULL)
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from mcp.server.fastmcp.exceptions import ToolError

from owlbear_knowledge.schema import init_db
from owlbear_mcp_knowledge.server import (
    AppContext,
    get_consolidation_candidates,
    get_next_batch,
    store_enrichment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_ctx(conn: sqlite3.Connection) -> MagicMock:
    """Return a FastMCP-shaped Context mock backed by a minimal AppContext."""
    ctx = MagicMock()
    app_ctx = AppContext(
        conn=conn,
        query_service=None,
        graph_store=None,
        ingest_pipeline=None,
        source_store=None,
        bookmark_pipeline=None,
        bookmark_store=None,
    )
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _insert_source(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    name: str,
    enrich: int,
    scope: str = "global",
) -> None:
    now = _now_iso()
    conn.execute(
        "INSERT INTO knowledge_sources"
        " (id, name, source_type, fetch_method, enrich, config, scope, enabled, priority,"
        "  created_at, updated_at)"
        " VALUES (?, ?, 'url_list', 'http', ?, '{}', ?, 1, 0, ?, ?)",
        (source_id, name, enrich, scope, now, now),
    )
    conn.commit()


def _insert_document(
    conn: sqlite3.Connection,
    *,
    doc_id: str,
    title: str,
    source_id: str | None,
    scope: str = "global",
) -> None:
    now = _now_iso()
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)"
        " VALUES (?, ?, '', '{}', ?, ?, ?)",
        (doc_id, title, now, scope, source_id),
    )
    conn.commit()


def _insert_chunk(
    conn: sqlite3.Connection,
    *,
    chunk_id: str,
    doc_id: str,
    content: str = "test content",
    state: str = "pending",
) -> None:
    now = _now_iso()
    conn.execute(
        "INSERT INTO chunks"
        " (id, document_id, chunk_index, content, metadata, created_at, enrichment_state)"
        " VALUES (?, ?, 0, ?, '{}', ?, ?)",
        (chunk_id, doc_id, content, now, state),
    )
    conn.commit()


def _insert_entity(  # noqa: PLR0913
    conn: sqlite3.Connection,
    *,
    entity_id: str,
    name: str,
    doc_id: str,
    chunk_id: str | None = None,
    scope: str = "global",
) -> None:
    now = _now_iso()
    conn.execute(
        "INSERT INTO entities"
        " (id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id)"
        " VALUES (?, ?, 'concept', '', '{}', ?, ?, ?, ?)",
        (entity_id, name, now, scope, doc_id, chunk_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """In-memory SQLite with full schema; thread-safe for asyncio."""
    c = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(c)
    return c


# ---------------------------------------------------------------------------
# TestFromAC_GetNextBatchProvenance  (AC-1)
# ---------------------------------------------------------------------------


class TestFromAC_GetNextBatchProvenance:
    """AC-1: get_next_batch must return provenance fields sufficient for store_enrichment."""

    @pytest.mark.asyncio
    async def test_batch_item_includes_document_id(self, conn: sqlite3.Connection) -> None:
        """Batch item must include document_id — currently absent from return dict."""
        _insert_source(conn, source_id="src-1", name="Source A", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="Doc A", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a")
        ctx = _make_ctx(conn)

        results = await get_next_batch(ctx, limit=1)

        assert len(results) == 1, "Expected one chunk to be claimed"
        assert "document_id" in results[0], (
            f"batch item must include 'document_id'; got keys: {list(results[0].keys())}"
        )
        assert results[0]["document_id"] == "doc-a"

    @pytest.mark.asyncio
    async def test_batch_item_includes_source_id(self, conn: sqlite3.Connection) -> None:
        """Batch item must include source_id — currently absent from return dict."""
        _insert_source(conn, source_id="src-1", name="Source A", enrich=1)
        _insert_document(conn, doc_id="doc-a", title="Doc A", source_id="src-1")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a")
        ctx = _make_ctx(conn)

        results = await get_next_batch(ctx, limit=1)

        assert len(results) == 1
        assert "source_id" in results[0], (
            f"batch item must include 'source_id'; got keys: {list(results[0].keys())}"
        )
        assert results[0]["source_id"] == "src-1"

    @pytest.mark.asyncio
    async def test_batch_item_includes_scope(self, conn: sqlite3.Connection) -> None:
        """Batch item must include scope — currently absent from return dict."""
        _insert_source(conn, source_id="src-1", name="Source A", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="Doc A", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a")
        ctx = _make_ctx(conn)

        results = await get_next_batch(ctx, limit=1)

        assert len(results) == 1
        assert "scope" in results[0], (
            f"batch item must include 'scope'; got keys: {list(results[0].keys())}"
        )
        assert results[0]["scope"] == "team-a"


# ---------------------------------------------------------------------------
# TestFromAC_StoreEnrichmentPhase1Provenance  (AC-2)
# ---------------------------------------------------------------------------


class TestFromAC_StoreEnrichmentPhase1Provenance:
    """AC-2: store_enrichment Phase 1 must derive provenance from chunk_id server-side."""

    @pytest.mark.asyncio
    async def test_entity_document_id_derived_server_side(self, conn: sqlite3.Connection) -> None:
        """Entity document_id must match chunk's document — not caller-supplied (which is absent)."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        # Caller provides NO document_id — server must derive from chunk lookup
        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
        )

        row = conn.execute(
            "SELECT document_id FROM entities WHERE name='ProbeEntity'"
        ).fetchone()
        assert row is not None, "Entity must be inserted"
        assert row[0] == "doc-a", (
            f"entity document_id must be 'doc-a' (derived server-side), got {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_entity_chunk_id_derived_from_call_parameter(
        self, conn: sqlite3.Connection
    ) -> None:
        """Entity chunk_id column must equal the chunk_id passed to store_enrichment."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1)
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        # Caller provides no chunk_id in entity dict — server must stamp from call param
        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
        )

        row = conn.execute(
            "SELECT chunk_id FROM entities WHERE name='ProbeEntity'"
        ).fetchone()
        assert row is not None
        assert row[0] == "chk-1", (
            f"entity chunk_id must be 'chk-1' (stamped from call parameter), got {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_entity_scope_derived_from_document(self, conn: sqlite3.Connection) -> None:
        """Entity scope must equal the document's scope — not the caller default 'global'."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
        )

        row = conn.execute(
            "SELECT scope FROM entities WHERE name='ProbeEntity'"
        ).fetchone()
        assert row is not None
        assert row[0] == "team-a", (
            f"entity scope must be 'team-a' (derived from document), got {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_no_null_in_entity_required_provenance_fields(
        self, conn: sqlite3.Connection
    ) -> None:
        """No entity row from store_enrichment may have NULL in document_id, chunk_id, or scope."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[
                {"name": "E1", "type": "concept"},
                {"name": "E2", "type": "concept"},
            ],
        )

        rows = conn.execute(
            "SELECT name, document_id, chunk_id, scope FROM entities WHERE name IN ('E1', 'E2')"
        ).fetchall()
        assert len(rows) == 2, "Both entities must be inserted"
        for name, doc_id, chunk_id, scope in rows:
            assert doc_id is not None, f"entity '{name}' has NULL document_id"
            assert chunk_id is not None, f"entity '{name}' has NULL chunk_id"
            assert scope is not None, f"entity '{name}' has NULL scope"

    @pytest.mark.asyncio
    async def test_edge_document_id_derived_server_side(self, conn: sqlite3.Connection) -> None:
        """Edge document_id must be derived from chunk's document, not caller-supplied."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        # Edge dict has no document_id — server must derive from chunk
        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
            edges=[{"relationship": "mentions", "target_name": "ProbeTarget"}],
        )

        row = conn.execute("SELECT document_id FROM edges").fetchone()
        assert row is not None, "Edge must be inserted"
        assert row[0] == "doc-a", (
            f"edge document_id must be 'doc-a' (derived server-side), got {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_edge_scope_derived_from_document(self, conn: sqlite3.Connection) -> None:
        """Edge scope must be derived from chunk's document, not defaulted to 'global'."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
            edges=[{"relationship": "mentions", "target_name": "ProbeTarget"}],
        )

        row = conn.execute("SELECT scope FROM edges").fetchone()
        assert row is not None, "Edge must be inserted"
        assert row[0] == "team-a", (
            f"edge scope must be 'team-a' (derived from document), got {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_relationship_key_stored_as_non_null_relation(
        self, conn: sqlite3.Connection
    ) -> None:
        """Edge payload key 'relationship' must persist as a non-NULL 'relation' column value."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1)
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
            edges=[{"relationship": "mentions", "target_name": "ProbeTarget"}],
        )

        row = conn.execute("SELECT relation FROM edges").fetchone()
        assert row is not None, "Edge must be inserted"
        assert row[0] is not None, (
            "edge 'relation' column must not be NULL when caller uses 'relationship' key"
        )
        assert row[0] == "mentions"

    @pytest.mark.asyncio
    async def test_no_null_in_edge_required_fields(self, conn: sqlite3.Connection) -> None:
        """No edge may have NULL in source_id, target_id, relation, document_id, or scope."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1, scope="team-a")
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1", scope="team-a")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
            edges=[{"relationship": "mentions", "target_name": "ProbeTarget"}],
        )

        row = conn.execute(
            "SELECT source_id, target_id, relation, document_id, scope FROM edges"
        ).fetchone()
        assert row is not None, "Edge must be inserted"
        source_id, target_id, relation, doc_id, scope = row
        assert source_id is not None, "edge source_id must not be NULL"
        assert target_id is not None, "edge target_id must not be NULL"
        assert relation is not None, "edge relation must not be NULL"
        assert doc_id is not None, "edge document_id must not be NULL"
        assert scope is not None, "edge scope must not be NULL"

    @pytest.mark.asyncio
    async def test_edge_chunk_id_in_metadata(self, conn: sqlite3.Connection) -> None:
        """Edge metadata must include chunk_id (edges table has no chunk_id column per schema)."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1)
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "ProbeEntity", "type": "concept"}],
            edges=[{"relationship": "mentions", "target_name": "ProbeTarget"}],
        )

        row = conn.execute("SELECT metadata FROM edges").fetchone()
        assert row is not None, "Edge must be inserted"
        metadata = json.loads(row[0]) if row[0] else {}
        assert "chunk_id" in metadata, (
            f"edge metadata must include 'chunk_id' field; got {metadata!r}"
        )
        assert metadata["chunk_id"] == "chk-1"


# ---------------------------------------------------------------------------
# TestFromAC_StoreEnrichmentRejection  (AC-3)
# ---------------------------------------------------------------------------


class TestFromAC_StoreEnrichmentRejection:
    """AC-3: store_enrichment must reject unresolvable provenance without inserting NULL rows."""

    @pytest.mark.asyncio
    async def test_ghost_chunk_does_not_succeed_silently(
        self, conn: sqlite3.Connection
    ) -> None:
        """store_enrichment with chunk_id not in DB must raise or return a non-None error result."""
        ctx = _make_ctx(conn)

        raised = False
        result = None
        try:
            result = await store_enrichment(
                ctx, chunk_id="ghost-chk", entities=[{"name": "BrokenEntity"}]
            )
        except Exception:  # noqa: BLE001
            raised = True

        # Must either have raised OR returned a non-None error result — silent None is wrong
        assert raised or result is not None, (
            "store_enrichment with nonexistent chunk_id succeeded silently (returned None "
            "without raising). Must raise a ToolError or return an explicit error result."
        )

    @pytest.mark.asyncio
    async def test_ghost_chunk_inserts_no_entity(self, conn: sqlite3.Connection) -> None:
        """No entity must be inserted when chunk_id cannot be found in the database."""
        ctx = _make_ctx(conn)
        count_before = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        with contextlib.suppress(Exception):
            await store_enrichment(
                ctx, chunk_id="ghost-chk", entities=[{"name": "BrokenEntity"}]
            )

        count_after = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        assert count_after == count_before, (
            f"store_enrichment inserted {count_after - count_before} entity row(s) "
            "for a nonexistent chunk_id — must insert zero"
        )

    @pytest.mark.asyncio
    async def test_orphan_chunk_not_marked_enriched(self, conn: sqlite3.Connection) -> None:
        """Chunk whose document has NULL source_id must not be marked 'enriched'."""
        # Orphan document: source_id is NULL, so scope/source cannot be derived
        _insert_document(conn, doc_id="orphan-doc", title="Orphan", source_id=None)
        _insert_chunk(conn, chunk_id="orphan-chk", doc_id="orphan-doc", state="pending")
        ctx = _make_ctx(conn)

        with contextlib.suppress(Exception):
            await store_enrichment(
                ctx,
                chunk_id="orphan-chk",
                entities=[{"name": "BrokenEntity"}],
            )

        row = conn.execute(
            "SELECT enrichment_state FROM chunks WHERE id='orphan-chk'"
        ).fetchone()
        assert row is not None
        assert row[0] != "enriched", (
            f"Orphan chunk (NULL source_id document) was marked '{row[0]}' — "
            "must remain 'pending' or 'failed' since provenance is unresolvable"
        )

    @pytest.mark.asyncio
    async def test_unresolvable_edge_not_inserted_with_null_endpoints(
        self, conn: sqlite3.Connection
    ) -> None:
        """No edge with NULL source_id or target_id must be inserted by Phase 1 store_enrichment."""
        _insert_source(conn, source_id="src-1", name="S1", enrich=1)
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1")
        _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        # Edge with no resolvable source_id / target_id in caller payload
        await store_enrichment(
            ctx,
            chunk_id="chk-1",
            entities=[{"name": "SomeEntity", "type": "concept"}],
            edges=[{"relationship": "mentions", "target_name": "NonExistentTarget"}],
        )

        null_edge = conn.execute(
            "SELECT id FROM edges WHERE source_id IS NULL OR target_id IS NULL"
        ).fetchone()
        assert null_edge is None, (
            "Edge with NULL source_id or target_id must not be inserted — "
            "endpoint names must be resolved to entity row IDs before insert"
        )

    @pytest.mark.asyncio
    async def test_already_enriched_chunk_raises_tool_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """store_enrichment on an already-enriched chunk must raise or return an error.

        AC-3: the call must reject and leave the chunk in its 'enriched' state;
        no new entity rows may be inserted.
        """
        _insert_source(conn, source_id="src-1", name="S1", enrich=1)
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1")
        _insert_chunk(conn, chunk_id="enr-chk", doc_id="doc-a", state="enriched")
        ctx = _make_ctx(conn)

        entity_count_before = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        raised = False
        try:
            await store_enrichment(
                ctx,
                chunk_id="enr-chk",
                entities=[{"name": "ShouldNotBeInserted", "type": "concept"}],
            )
        except Exception:  # noqa: BLE001
            raised = True

        assert raised, (
            "store_enrichment on already-enriched chunk must raise (e.g. ToolError)"
        )
        entity_count_after = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        assert entity_count_after == entity_count_before, (
            "store_enrichment on already-enriched chunk must not insert new entity rows"
        )

        state_row = conn.execute(
            "SELECT enrichment_state FROM chunks WHERE id='enr-chk'"
        ).fetchone()
        assert state_row is not None
        assert state_row[0] == "enriched", (
            f"Already-enriched chunk state must remain 'enriched', got '{state_row[0]}'"
        )

    @pytest.mark.asyncio
    async def test_claimed_chunk_state_becomes_failed_on_rejected_phase1_write(
        self, conn: sqlite3.Connection
    ) -> None:
        """On rejected Phase 1 write from a claimed chunk, state becomes 'failed' and claimed_at clears.

        AC-3: a claimed chunk whose provenance cannot be resolved must not remain
        stuck in 'claimed' state — store_enrichment must recover it to 'failed'
        and clear claimed_at so get_next_batch can reclaim it (stale-lease expiry).
        """
        # Orphan doc (NULL source_id) so provenance resolution fails, but chunk IS in DB
        _insert_document(conn, doc_id="orphan-doc2", title="Orphan2", source_id=None)
        now_iso = _now_iso()
        conn.execute(
            "INSERT INTO chunks"
            " (id, document_id, chunk_index, content, metadata, created_at, enrichment_state, claimed_at)"
            " VALUES (?, ?, 0, 'content', '{}', ?, 'claimed', ?)",
            ("claimed-chk", "orphan-doc2", now_iso, now_iso),
        )
        conn.commit()

        ctx = _make_ctx(conn)

        with contextlib.suppress(Exception):
            await store_enrichment(
                ctx,
                chunk_id="claimed-chk",
                entities=[{"name": "AnyEntity", "type": "concept"}],
            )

        row = conn.execute(
            "SELECT enrichment_state, claimed_at FROM chunks WHERE id='claimed-chk'"
        ).fetchone()
        assert row is not None
        assert row[0] == "failed", (
            f"Claimed chunk must become 'failed' after rejected Phase 1 write, got '{row[0]}'"
        )
        assert row[1] is None, (
            f"claimed_at must be cleared (NULL) after rejected Phase 1 write, got '{row[1]}'"
        )

    @pytest.mark.asyncio
    async def test_truly_unresolvable_edge_raises_tool_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """entities=[] edge with no source/target fields → ToolError, zero edges, chunk not enriched.

        PO-1 (AC-3): when no entities are provided and the edge dict contains no source_name,
        target_name, source_id, or target_id, both endpoint resolution sides return None and
        server.py:_resolve_phase1_edge_endpoints must raise ToolError. No edge row may be
        inserted and the chunk enrichment_state must not become 'enriched'.
        """
        _insert_source(conn, source_id="src-1", name="S1", enrich=1)
        _insert_document(conn, doc_id="doc-a", title="D", source_id="src-1")
        _insert_chunk(conn, chunk_id="chk-x", doc_id="doc-a", state="claimed")
        ctx = _make_ctx(conn)

        with pytest.raises(ToolError):
            await store_enrichment(
                ctx,
                chunk_id="chk-x",
                entities=[],
                edges=[{"relationship": "mentions"}],
            )

        edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            f"store_enrichment with truly unresolvable edge endpoints must insert zero edges, "
            f"got {edge_count}"
        )

        state_row = conn.execute(
            "SELECT enrichment_state FROM chunks WHERE id='chk-x'"
        ).fetchone()
        assert state_row is not None
        assert state_row[0] != "enriched", (
            f"Chunk must not be marked 'enriched' when edge endpoint resolution fails, "
            f"got '{state_row[0]}'"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidationCandidateIdentifiers  (AC-4)
# ---------------------------------------------------------------------------


def _setup_cross_source_entities(conn: sqlite3.Connection) -> tuple[str, str]:
    """Insert two entities with same name from different sources; return (entity_id_a, entity_id_b)."""
    _insert_source(conn, source_id="src-1", name="Source A", enrich=1)
    _insert_source(conn, source_id="src-2", name="Source B", enrich=1)
    _insert_document(conn, doc_id="doc-1", title="D1", source_id="src-1")
    _insert_document(conn, doc_id="doc-2", title="D2", source_id="src-2")
    _insert_chunk(conn, chunk_id="chk-1", doc_id="doc-1", content="context A")
    _insert_chunk(conn, chunk_id="chk-2", doc_id="doc-2", content="context B")
    _insert_entity(conn, entity_id="ent-a1", name="ProbeEntity", doc_id="doc-1", chunk_id="chk-1")
    _insert_entity(conn, entity_id="ent-b1", name="ProbeEntity", doc_id="doc-2", chunk_id="chk-2")
    return "ent-a1", "ent-b1"


class TestFromAC_ConsolidationCandidateIdentifiers:
    """AC-4: get_consolidation_candidates must expose durable entity row identifiers."""

    @pytest.mark.asyncio
    async def test_candidate_has_entity_id_a(self, conn: sqlite3.Connection) -> None:
        """Candidate must include a durable entity row ID for the source_a entity."""
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)

        assert len(candidates) == 1, "Expected one consolidation candidate"
        assert "entity_id_a" in candidates[0], (
            f"candidate must include 'entity_id_a'; got keys: {list(candidates[0].keys())}"
        )

    @pytest.mark.asyncio
    async def test_candidate_has_entity_id_b(self, conn: sqlite3.Connection) -> None:
        """Candidate must include a durable entity row ID for the source_b entity."""
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)

        assert len(candidates) == 1
        assert "entity_id_b" in candidates[0], (
            f"candidate must include 'entity_id_b'; got keys: {list(candidates[0].keys())}"
        )

    @pytest.mark.asyncio
    async def test_candidate_entity_ids_match_actual_db_rows(
        self, conn: sqlite3.Connection
    ) -> None:
        """Candidate entity_id_a and entity_id_b must equal the actual entity table PKs."""
        ent_a, ent_b = _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)

        assert len(candidates) == 1
        c = candidates[0]
        assert "entity_id_a" in c, f"Missing entity_id_a; got keys: {list(c.keys())}"
        assert "entity_id_b" in c, f"Missing entity_id_b; got keys: {list(c.keys())}"

        valid_ids = {ent_a, ent_b}
        assert c["entity_id_a"] in valid_ids, (
            f"entity_id_a {c['entity_id_a']!r} not one of the expected entity IDs {valid_ids}"
        )
        assert c["entity_id_b"] in valid_ids, (
            f"entity_id_b {c['entity_id_b']!r} not one of the expected entity IDs {valid_ids}"
        )
        assert c["entity_id_a"] != c["entity_id_b"], "entity_id_a and entity_id_b must differ"


# ---------------------------------------------------------------------------
# TestFromAC_StoreEnrichmentPhase2Edges  (AC-5)
# ---------------------------------------------------------------------------


class TestFromAC_StoreEnrichmentPhase2Edges:
    """AC-5: store_enrichment Phase 2 must persist edges with non-NULL, matched endpoints."""

    @pytest.mark.asyncio
    async def test_phase2_edge_source_id_non_null(self, conn: sqlite3.Connection) -> None:
        """Edge persisted via candidate_id must have non-NULL source_id."""
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)
        assert len(candidates) == 1
        candidate_id = candidates[0]["candidate_id"]

        await store_enrichment(
            ctx, candidate_id=candidate_id, edges=[{"relationship": "same_as"}]
        )

        row = conn.execute("SELECT source_id FROM edges").fetchone()
        assert row is not None, "Edge must be inserted"
        assert row[0] is not None, (
            "Phase 2 edge source_id must not be NULL — "
            "must be derived from candidate entity row IDs"
        )

    @pytest.mark.asyncio
    async def test_phase2_edge_target_id_non_null(self, conn: sqlite3.Connection) -> None:
        """Edge persisted via candidate_id must have non-NULL target_id."""
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)
        assert len(candidates) == 1

        await store_enrichment(
            ctx,
            candidate_id=candidates[0]["candidate_id"],
            edges=[{"relationship": "same_as"}],
        )

        row = conn.execute("SELECT target_id FROM edges").fetchone()
        assert row is not None, "Edge must be inserted"
        assert row[0] is not None, (
            "Phase 2 edge target_id must not be NULL — "
            "must be derived from candidate entity row IDs"
        )

    @pytest.mark.asyncio
    async def test_phase2_edge_endpoints_match_entity_row_ids(
        self, conn: sqlite3.Connection
    ) -> None:
        """Edge source_id and target_id must match the candidate's entity row PKs."""
        ent_a, ent_b = _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)
        assert len(candidates) == 1

        await store_enrichment(
            ctx,
            candidate_id=candidates[0]["candidate_id"],
            edges=[{"relationship": "same_as"}],
        )

        row = conn.execute("SELECT source_id, target_id FROM edges").fetchone()
        assert row is not None, "Edge must be inserted"
        valid_ids = {ent_a, ent_b}
        assert row[0] in valid_ids, (
            f"edge source_id {row[0]!r} must be one of the entity row IDs {valid_ids}"
        )
        assert row[1] in valid_ids, (
            f"edge target_id {row[1]!r} must be one of the entity row IDs {valid_ids}"
        )

    @pytest.mark.asyncio
    async def test_phase2_edge_idempotent_no_duplicate(self, conn: sqlite3.Connection) -> None:
        """Repeating the same Phase 2 payload must not create duplicate edges."""
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)
        assert len(candidates) == 1
        candidate_id = candidates[0]["candidate_id"]

        await store_enrichment(
            ctx, candidate_id=candidate_id, edges=[{"relationship": "same_as"}]
        )
        await store_enrichment(
            ctx, candidate_id=candidate_id, edges=[{"relationship": "same_as"}]
        )

        count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert count == 1, (
            f"Expected 1 edge after two identical Phase 2 calls, got {count} — "
            "idempotent retry must not create duplicate edges"
        )

    @pytest.mark.asyncio
    async def test_accepted_candidate_absent_from_next_batch(
        self, conn: sqlite3.Connection
    ) -> None:
        """Candidate for which an edge was stored must not reappear in the next batch."""
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=10)
        assert len(candidates) == 1, "Expected one candidate before store_enrichment"
        candidate_id = candidates[0]["candidate_id"]

        # Store an edge for this candidate
        await store_enrichment(
            ctx, candidate_id=candidate_id, edges=[{"relationship": "same_as"}]
        )

        next_candidates = await get_consolidation_candidates(ctx, limit=10)
        ids_in_next = [c["candidate_id"] for c in next_candidates]
        assert candidate_id not in ids_in_next, (
            "Candidate whose edge was stored must not appear in the next "
            "get_consolidation_candidates batch"
        )

    @pytest.mark.asyncio
    async def test_phase2_two_sided_mismatched_endpoints_rejected(
        self, conn: sqlite3.Connection
    ) -> None:
        """Both source_id and target_id explicitly wrong → ToolError, zero edges.

        PO-2 (AC-5): when both explicit endpoint fields do not match either candidate
        entity row ID, _resolve_phase2_edge_endpoints must raise ToolError and
        store_enrichment must not insert any edge.
        """
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)
        assert len(candidates) == 1
        candidate_id = candidates[0]["candidate_id"]

        with pytest.raises(ToolError):
            await store_enrichment(
                ctx,
                candidate_id=candidate_id,
                edges=[{"relationship": "same_as", "source_id": "wrong-id", "target_id": "also-wrong-id"}],
            )

        edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            f"Two-sided mismatched explicit endpoints must not insert any edge, got {edge_count}"
        )

    @pytest.mark.asyncio
    async def test_phase2_one_sided_invalid_target_rejected(
        self, conn: sqlite3.Connection
    ) -> None:
        """Only target_id explicitly wrong (source_id omitted) → ToolError, zero edges.

        PO-2 (AC-5): when only target_id is supplied and does not match either candidate
        entity row ID, _resolve_phase2_edge_endpoints must raise ToolError.
        """
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)
        assert len(candidates) == 1
        candidate_id = candidates[0]["candidate_id"]

        with pytest.raises(ToolError):
            await store_enrichment(
                ctx,
                candidate_id=candidate_id,
                edges=[{"relationship": "same_as", "target_id": "wrong-id"}],
            )

        edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            f"One-sided invalid target_id must not insert any edge, got {edge_count}"
        )

    @pytest.mark.asyncio
    async def test_phase2_one_sided_invalid_source_rejected(
        self, conn: sqlite3.Connection
    ) -> None:
        """Only source_id explicitly wrong (target_id omitted) → ToolError, zero edges.

        PO-2 (AC-5): when only source_id is supplied and does not match either candidate
        entity row ID, _resolve_phase2_edge_endpoints must raise ToolError.
        """
        _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=1)
        assert len(candidates) == 1
        candidate_id = candidates[0]["candidate_id"]

        with pytest.raises(ToolError):
            await store_enrichment(
                ctx,
                candidate_id=candidate_id,
                edges=[{"relationship": "same_as", "source_id": "wrong-id"}],
            )

        edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            f"One-sided invalid source_id must not insert any edge, got {edge_count}"
        )

    @pytest.mark.asyncio
    async def test_reviewed_without_edge_excludes_candidate_and_persists_pair_identity(
        self, conn: sqlite3.Connection
    ) -> None:
        """store_enrichment(edges=[]) marks candidate reviewed and excludes it from next batch.

        PO-3 (AC-5): reviewed-without-edge action must:
        (a) cause get_consolidation_candidates to no longer return that candidate,
        (b) write a reviewed_pairs row whose entity_id_a and entity_id_b match the
            candidate's actual entity row PKs (non-empty, durable pair identity).
        """
        ent_a, ent_b = _setup_cross_source_entities(conn)
        ctx = _make_ctx(conn)

        candidates = await get_consolidation_candidates(ctx, limit=10)
        assert len(candidates) == 1, "Expected one candidate before reviewed-without-edge"
        cand = candidates[0]
        candidate_id = cand["candidate_id"]
        expected_ids = {ent_a, ent_b}

        # Reviewed-without-edge: edges=[] means no edge inserted but candidate is dismissed
        await store_enrichment(ctx, candidate_id=candidate_id, edges=[])

        # (a) candidate absent from next batch
        next_candidates = await get_consolidation_candidates(ctx, limit=10)
        ids_in_next = [c["candidate_id"] for c in next_candidates]
        assert candidate_id not in ids_in_next, (
            "Reviewed-without-edge candidate must not reappear in next get_consolidation_candidates batch"
        )

        # (b) reviewed_pairs row has durable pair identity
        row = conn.execute(
            "SELECT entity_id_a, entity_id_b FROM reviewed_pairs"
        ).fetchone()
        assert row is not None, (
            "reviewed_pairs must contain a row after reviewed-without-edge store_enrichment"
        )
        assert row[0], f"reviewed_pairs.entity_id_a must be non-empty, got {row[0]!r}"
        assert row[0] != "", f"reviewed_pairs.entity_id_a must be non-empty, got {row[0]!r}"
        assert row[1], f"reviewed_pairs.entity_id_b must be non-empty, got {row[1]!r}"
        assert row[1] != "", f"reviewed_pairs.entity_id_b must be non-empty, got {row[1]!r}"
        assert row[0] in expected_ids, (
            f"reviewed_pairs.entity_id_a {row[0]!r} must match one of the candidate entity PKs {expected_ids}"
        )
        assert row[1] in expected_ids, (
            f"reviewed_pairs.entity_id_b {row[1]!r} must match one of the candidate entity PKs {expected_ids}"
        )
        assert row[0] != row[1], (
            "reviewed_pairs.entity_id_a and entity_id_b must differ"
        )


# ---------------------------------------------------------------------------
# TestFromAC_OrphanChunkExclusion  (AC-6)
# ---------------------------------------------------------------------------


class TestFromAC_OrphanChunkExclusion:
    """AC-6: get_next_batch must exclude chunks from documents with NULL source_id."""

    @pytest.mark.asyncio
    async def test_orphan_chunk_excluded_from_batch(self, conn: sqlite3.Connection) -> None:
        """Chunk whose document has NULL source_id must not be returned by get_next_batch."""
        # Orphan document: no knowledge_sources row, so source_id is NULL
        _insert_document(conn, doc_id="orphan-doc", title="Orphan", source_id=None)
        _insert_chunk(conn, chunk_id="orphan-chk", doc_id="orphan-doc", content="orphan text")
        ctx = _make_ctx(conn)

        results = await get_next_batch(ctx, limit=10)
        chunk_ids = [r["chunk_id"] for r in results]

        assert "orphan-chk" not in chunk_ids, (
            "Chunk from a document with NULL source_id must not be returned by get_next_batch "
            "(current LEFT JOIN + COALESCE makes orphan chunks eligible)"
        )

    @pytest.mark.asyncio
    async def test_source_linked_chunk_returned_while_orphan_excluded(
        self, conn: sqlite3.Connection
    ) -> None:
        """Source-linked enrich-enabled chunk is included; orphan chunk is excluded."""
        # Orphan chunk
        _insert_document(conn, doc_id="orphan-doc", title="Orphan", source_id=None)
        _insert_chunk(conn, chunk_id="orphan-chk", doc_id="orphan-doc")

        # Source-linked enrich-enabled chunk
        _insert_source(conn, source_id="src-1", name="Source", enrich=1)
        _insert_document(conn, doc_id="linked-doc", title="Linked", source_id="src-1")
        _insert_chunk(conn, chunk_id="linked-chk", doc_id="linked-doc")

        ctx = _make_ctx(conn)
        results = await get_next_batch(ctx, limit=10)
        chunk_ids = [r["chunk_id"] for r in results]

        assert "orphan-chk" not in chunk_ids, "Orphan chunk must be excluded"
        assert "linked-chk" in chunk_ids, "Source-linked chunk must be included"

    @pytest.mark.asyncio
    async def test_all_orphan_chunks_return_empty_batch(self, conn: sqlite3.Connection) -> None:
        """When only orphan chunks exist, get_next_batch must return an empty list."""
        for i in range(3):
            _insert_document(
                conn, doc_id=f"orphan-{i}", title=f"O{i}", source_id=None
            )
            _insert_chunk(conn, chunk_id=f"ochk-{i}", doc_id=f"orphan-{i}")
        ctx = _make_ctx(conn)

        results = await get_next_batch(ctx, limit=10)

        assert results == [], (
            f"Expected empty batch when only orphan chunks exist, "
            f"got {len(results)} chunk(s) — COALESCE(NULL, 1) incorrectly makes "
            "orphan chunks eligible for enrichment"
        )
