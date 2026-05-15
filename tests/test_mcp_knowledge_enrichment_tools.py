"""Failing tests for task #1327: Phase 1 enrichment tools (get_next_batch, store_enrichment).

TDD RED phase — all tests FAIL until task #1328 implements the tools.

Covers:
  - AC1: get_next_batch uses atomic SELECT+UPDATE with IMMEDIATE transaction (td:2)
  - AC2: get_next_batch returns chunk metadata (chunk_id, text, doc_title,
         section_path, source_name) via JOINed document/source data (td:1)
  - AC3: claimed chunks are not returned in subsequent get_next_batch calls (td:1)
  - AC4: lease expiry — stale claims (>10 min) revert to pending (td:2)
  - AC5: store_enrichment UPSERT entities via INSERT OR REPLACE on entities
         table primary key (td:1)
  - AC6: store_enrichment INSERT OR IGNORE edges with
         UNIQUE(source_id, target_id, relation, document_id) constraint (td:1)
  - AC7: store_enrichment updates enrichment_state to 'enriched' (td:1)
  - AC8: WAL mode concurrent write safety (file-backed DB, multiple connections
         from separate threads) (td:2)
  - AC9: get_next_batch excludes chunks from sources with enrich=false (td:1)

Run with: uv run pytest tests/test_mcp_knowledge_enrichment_tools_1327.py
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Import targets — will raise ImportError until builder implements #1328 (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.server import get_next_batch, store_enrichment  # type: ignore[import]


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


def _make_app_context(conn: sqlite3.Connection) -> MagicMock:
    """Return a MagicMock shaped like AppContext with a real SQLite connection."""
    ctx = MagicMock()
    ctx.conn = conn
    return ctx


def _make_mcp_ctx(conn: sqlite3.Connection) -> MagicMock:
    """Return a MagicMock mimicking a FastMCP Context with a real AppContext.conn."""
    mcp_ctx = MagicMock()
    mcp_ctx.request_context.lifespan_context = _make_app_context(conn)
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


def _insert_chunk(  # noqa: PLR0913
    conn: sqlite3.Connection,
    *,
    chunk_id: str | None = None,
    document_id: str,
    content: str = "chunk text",
    enrichment_state: str = "pending",
    claimed_at: str | None = None,
) -> str:
    """Insert a chunks row and return its id."""
    cid = chunk_id or str(uuid.uuid4())
    now = _now_iso()
    conn.execute(
        "INSERT INTO chunks "
        "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state, claimed_at) "
        "VALUES (?, ?, 0, ?, '{}', ?, 'global', ?, ?)",
        (cid, document_id, content, now, enrichment_state, claimed_at),
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


def _get_chunk_field(item: Any, field: str) -> Any:
    """Extract a named field from a result item (dict or dataclass/namedtuple)."""
    if isinstance(item, dict):
        return item[field]
    return getattr(item, field)


def _has_chunk_field(item: Any, field: str) -> bool:
    """Check whether a named field exists on a result item."""
    if isinstance(item, dict):
        return field in item
    return hasattr(item, field)


# ---------------------------------------------------------------------------
# TestFromAC_GetNextBatch
# ---------------------------------------------------------------------------


class TestFromAC_GetNextBatch:
    """Tests derived from AC1, AC2, AC3, AC4, AC9 for get_next_batch."""

    # --- AC1: atomic SELECT+UPDATE with IMMEDIATE transaction (td:2) ---

    @pytest.mark.asyncio
    async def test_uses_immediate_transaction(self, conn: sqlite3.Connection) -> None:
        """BEGIN IMMEDIATE appears in SQL trace for a get_next_batch call."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        _insert_chunk(conn, document_id=doc_id)

        sql_trace: list[str] = []
        conn.set_trace_callback(sql_trace.append)

        ctx = _make_mcp_ctx(conn)
        await get_next_batch(ctx, limit=1)

        conn.set_trace_callback(None)
        assert any("BEGIN IMMEDIATE" in s.upper() for s in sql_trace), (
            f"Expected BEGIN IMMEDIATE in SQL trace, got: {sql_trace}"
        )

    @pytest.mark.asyncio
    async def test_immediate_transaction_used_when_no_pending_chunks(
        self, conn: sqlite3.Connection
    ) -> None:
        """BEGIN IMMEDIATE is used even when no pending chunks exist (atomicity guarantee)."""
        sql_trace: list[str] = []
        conn.set_trace_callback(sql_trace.append)

        ctx = _make_mcp_ctx(conn)
        await get_next_batch(ctx, limit=5)

        conn.set_trace_callback(None)
        assert any("BEGIN IMMEDIATE" in s.upper() for s in sql_trace), (
            "BEGIN IMMEDIATE must be used even when no chunks are pending"
        )

    @pytest.mark.asyncio
    async def test_select_and_update_within_single_immediate_transaction(
        self, conn: sqlite3.Connection
    ) -> None:
        """SQL trace must show BEGIN IMMEDIATE → SELECT → UPDATE → COMMIT with no COMMIT between SELECT and UPDATE.

        Discriminating proof: a split-transaction implementation (BEGIN→SELECT→COMMIT,
        BEGIN→UPDATE→COMMIT) would have a COMMIT between the SELECT and UPDATE positions
        and would therefore FAIL this test.
        """
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        _insert_chunk(conn, document_id=doc_id)

        sql_trace: list[str] = []
        conn.set_trace_callback(sql_trace.append)

        ctx = _make_mcp_ctx(conn)
        await get_next_batch(ctx, limit=1)

        conn.set_trace_callback(None)

        upper_trace = [s.upper().strip() for s in sql_trace]

        begin_idx = next(
            (i for i, s in enumerate(upper_trace) if "BEGIN IMMEDIATE" in s), None
        )
        assert begin_idx is not None, (
            f"BEGIN IMMEDIATE not found in SQL trace: {sql_trace}"
        )

        select_idx = next(
            (i for i, s in enumerate(upper_trace) if "SELECT" in s and i > begin_idx),
            None,
        )
        assert select_idx is not None, (
            f"SELECT not found after BEGIN IMMEDIATE in SQL trace: {sql_trace}"
        )

        update_idx = next(
            (
                i
                for i, s in enumerate(upper_trace)
                if s.startswith("UPDATE") and i > begin_idx
            ),
            None,
        )
        assert update_idx is not None, (
            f"UPDATE not found after BEGIN IMMEDIATE in SQL trace: {sql_trace}"
        )

        commit_idx = next(
            (i for i, s in enumerate(upper_trace) if s == "COMMIT" and i > begin_idx),
            None,
        )
        assert commit_idx is not None, (
            f"COMMIT not found after BEGIN IMMEDIATE in SQL trace: {sql_trace}"
        )

        # Discriminating: both SELECT and UPDATE precede the COMMIT
        assert select_idx < commit_idx, "SELECT must occur before COMMIT"
        assert update_idx < commit_idx, "UPDATE must occur before COMMIT"

        # Discriminating: no COMMIT may appear between SELECT and UPDATE
        intermediate_commits = [
            i
            for i, s in enumerate(upper_trace)
            if s == "COMMIT" and select_idx < i < update_idx
        ]
        assert not intermediate_commits, (
            "COMMIT must not occur between SELECT and UPDATE — "
            f"found intermediate commits at positions {intermediate_commits} in trace: {sql_trace}"
        )

    # --- AC2: returns chunk metadata via JOINed data (td:1) ---

    @pytest.mark.asyncio
    async def test_returns_chunk_id_field(self, conn: sqlite3.Connection) -> None:
        """Each result item carries a chunk_id field matching the database row."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_id = _insert_chunk(conn, document_id=doc_id, content="hello world")

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        assert len(result) == 1
        item = result[0]
        assert _has_chunk_field(item, "chunk_id"), "Result item missing chunk_id field"
        assert _get_chunk_field(item, "chunk_id") == chunk_id

    @pytest.mark.asyncio
    async def test_returns_text_field_with_chunk_content(
        self, conn: sqlite3.Connection
    ) -> None:
        """Each result item carries a text field containing the chunk's content."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        _insert_chunk(conn, document_id=doc_id, content="the quick brown fox")

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        assert len(result) == 1
        item = result[0]
        assert _has_chunk_field(item, "text"), "Result item missing text field"
        assert _get_chunk_field(item, "text") == "the quick brown fox"

    @pytest.mark.asyncio
    async def test_returns_doc_title_from_documents_join(
        self, conn: sqlite3.Connection
    ) -> None:
        """doc_title field reflects the title from the joined documents row."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, title="My Document Title", source_id=source_id)
        _insert_chunk(conn, document_id=doc_id)

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        assert len(result) == 1
        item = result[0]
        assert _has_chunk_field(item, "doc_title"), (
            "Result item missing doc_title field"
        )
        assert _get_chunk_field(item, "doc_title") == "My Document Title"

    @pytest.mark.asyncio
    async def test_returns_source_name_from_knowledge_sources_join(
        self, conn: sqlite3.Connection
    ) -> None:
        """source_name field reflects the name from the joined knowledge_sources row."""
        source_id = _insert_source(conn, name="My Knowledge Source")
        doc_id = _insert_document(conn, source_id=source_id)
        _insert_chunk(conn, document_id=doc_id)

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        assert len(result) == 1
        item = result[0]
        assert _has_chunk_field(item, "source_name"), (
            "Result item missing source_name field"
        )
        assert _get_chunk_field(item, "source_name") == "My Knowledge Source"

    @pytest.mark.asyncio
    async def test_source_name_is_none_for_document_without_knowledge_source(
        self, conn: sqlite3.Connection
    ) -> None:
        """Chunk from a document with no linked knowledge_source must NOT be returned.

        AC-6 compliance: get_next_batch uses INNER JOIN to knowledge_sources so that
        orphan chunks (NULL source_id documents) are excluded — provenance cannot be
        derived for them and they must not be claimed for enrichment.
        """
        doc_id = _insert_document(conn, title="Sourceless Doc", source_id=None)
        _insert_chunk(conn, document_id=doc_id, content="sourceless chunk")

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        assert len(result) == 0, (
            "Chunk from a document with no linked knowledge_source must NOT be returned "
            "by get_next_batch (INNER JOIN must exclude orphan documents). "
            f"Got {len(result)} item(s)."
        )

    @pytest.mark.asyncio
    async def test_returns_section_path_field(self, conn: sqlite3.Connection) -> None:
        """Each result item carries a section_path field (may be None if not stored)."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        _insert_chunk(conn, document_id=doc_id)

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        assert len(result) == 1
        item = result[0]
        assert _has_chunk_field(item, "section_path"), (
            "Result item missing section_path field"
        )

    @pytest.mark.asyncio
    async def test_section_path_round_trip_from_metadata_json(
        self, conn: sqlite3.Connection
    ) -> None:
        """section_path is parsed from chunks.metadata JSON — insert a known value and assert exact round-trip.

        Discriminating proof: a constant/None section_path would fail this test because
        the assertion requires the exact value stored in the JSON metadata field.
        """
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)

        chunk_id = str(uuid.uuid4())
        now = _now_iso()
        metadata_json = json.dumps({"section_path": "Introduction/Background"})
        conn.execute(
            "INSERT INTO chunks "
            "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state, claimed_at) "
            "VALUES (?, ?, 0, ?, ?, ?, 'global', 'pending', NULL)",
            (chunk_id, doc_id, "round-trip chunk", metadata_json, now),
        )
        conn.commit()

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        assert len(result) == 1, f"Expected exactly 1 chunk, got {len(result)}"
        item = result[0]
        actual_section_path = _get_chunk_field(item, "section_path")
        assert actual_section_path == "Introduction/Background", (
            f"section_path round-trip failed: expected 'Introduction/Background', "
            f"got {actual_section_path!r}"
        )

    @pytest.mark.asyncio
    async def test_limit_parameter_caps_returned_items(
        self, conn: sqlite3.Connection
    ) -> None:
        """get_next_batch(limit=2) returns at most 2 items when 5 are pending."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        for i in range(5):
            _insert_chunk(conn, document_id=doc_id, content=f"chunk {i}")

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=2)

        assert len(result) <= 2

    # --- AC3: claimed chunks not returned in subsequent calls (td:1) ---

    @pytest.mark.asyncio
    async def test_claimed_chunks_not_returned_in_second_call(
        self, conn: sqlite3.Connection
    ) -> None:
        """A chunk returned by get_next_batch is not returned again on the next call."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_id = _insert_chunk(conn, document_id=doc_id)

        ctx = _make_mcp_ctx(conn)
        first = await get_next_batch(ctx, limit=10)
        second = await get_next_batch(ctx, limit=10)

        first_ids = {_get_chunk_field(r, "chunk_id") for r in first}
        second_ids = {_get_chunk_field(r, "chunk_id") for r in second}

        assert chunk_id in first_ids, "Pending chunk should appear in first call"
        assert chunk_id not in second_ids, (
            "Claimed chunk must not appear in subsequent get_next_batch call"
        )

    @pytest.mark.asyncio
    async def test_all_pending_claimed_then_empty(
        self, conn: sqlite3.Connection
    ) -> None:
        """With 3 pending chunks and limit=10, first call returns all 3; second returns 0."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        for i in range(3):
            _insert_chunk(conn, document_id=doc_id, content=f"chunk {i}")

        ctx = _make_mcp_ctx(conn)
        first = await get_next_batch(ctx, limit=10)
        second = await get_next_batch(ctx, limit=10)

        assert len(first) == 3
        assert len(second) == 0

    # --- AC4: lease expiry — stale claims (>10 min) revert to pending (td:2) ---

    @pytest.mark.asyncio
    async def test_stale_claimed_chunk_returned_after_lease_expiry(
        self, conn: sqlite3.Connection
    ) -> None:
        """A chunk claimed 11 min ago is returned by get_next_batch (treated as pending)."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        stale_time = (datetime.now(tz=UTC) - timedelta(minutes=11)).isoformat()
        chunk_id = _insert_chunk(
            conn,
            document_id=doc_id,
            enrichment_state="claimed",
            claimed_at=stale_time,
        )

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert chunk_id in returned_ids, (
            "Stale claimed chunk (11 min) should be re-returned as expired lease"
        )

    @pytest.mark.asyncio
    async def test_fresh_claimed_chunk_not_returned(
        self, conn: sqlite3.Connection
    ) -> None:
        """A chunk claimed 5 min ago (within lease window) is NOT returned."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        fresh_time = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()
        chunk_id = _insert_chunk(
            conn,
            document_id=doc_id,
            enrichment_state="claimed",
            claimed_at=fresh_time,
        )

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert chunk_id not in returned_ids, (
            "Freshly claimed chunk (5 min) must not be returned before lease expires"
        )

    @pytest.mark.asyncio
    async def test_exactly_10_min_boundary_not_expired(
        self, conn: sqlite3.Connection
    ) -> None:
        """A chunk claimed exactly 10 min ago is NOT returned (boundary: >10 min required)."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        boundary_time = (datetime.now(tz=UTC) - timedelta(minutes=10)).isoformat()
        chunk_id = _insert_chunk(
            conn,
            document_id=doc_id,
            enrichment_state="claimed",
            claimed_at=boundary_time,
        )

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert chunk_id not in returned_ids, (
            "Chunk claimed exactly 10 min ago must NOT be returned (lease requires >10 min to expire)"
        )

    @pytest.mark.asyncio
    async def test_enriched_chunks_not_returned_even_with_stale_claimed_at(
        self, conn: sqlite3.Connection
    ) -> None:
        """Chunks in 'enriched' state are never returned, even with old claimed_at."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        old_time = (datetime.now(tz=UTC) - timedelta(minutes=30)).isoformat()
        chunk_id = _insert_chunk(
            conn,
            document_id=doc_id,
            enrichment_state="enriched",
            claimed_at=old_time,
        )

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert chunk_id not in returned_ids, (
            "Enriched chunks must never be returned, even with stale claimed_at"
        )

    # --- AC9: excludes chunks from sources with enrich=false (td:1) ---

    @pytest.mark.asyncio
    async def test_excludes_chunks_from_non_enrich_sources(
        self, conn: sqlite3.Connection
    ) -> None:
        """Chunks whose source has enrich=0 are not returned by get_next_batch."""
        no_enrich_source = _insert_source(conn, name="NoEnrich Source", enrich=0)
        doc_id = _insert_document(conn, source_id=no_enrich_source)
        chunk_id = _insert_chunk(conn, document_id=doc_id, content="should be excluded")

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert chunk_id not in returned_ids, (
            "Chunks from sources with enrich=0 must be excluded from get_next_batch"
        )

    @pytest.mark.asyncio
    async def test_includes_chunks_from_enrich_true_sources(
        self, conn: sqlite3.Connection
    ) -> None:
        """Chunks whose source has enrich=1 ARE returned by get_next_batch."""
        enrich_source = _insert_source(conn, name="EnrichSource", enrich=1)
        doc_id = _insert_document(conn, source_id=enrich_source)
        chunk_id = _insert_chunk(conn, document_id=doc_id, content="should be included")

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert chunk_id in returned_ids, (
            "Chunks from sources with enrich=1 must be included in get_next_batch"
        )

    @pytest.mark.asyncio
    async def test_mixed_sources_only_enrich_true_chunks_returned(
        self, conn: sqlite3.Connection
    ) -> None:
        """With mixed enrich=0 and enrich=1 sources, only enrich=1 chunks are returned."""
        good_source = _insert_source(conn, name="GoodSource", enrich=1)
        bad_source = _insert_source(conn, name="BadSource", enrich=0)
        good_doc = _insert_document(conn, source_id=good_source)
        bad_doc = _insert_document(conn, source_id=bad_source)
        good_chunk = _insert_chunk(conn, document_id=good_doc, content="include me")
        bad_chunk = _insert_chunk(conn, document_id=bad_doc, content="exclude me")

        ctx = _make_mcp_ctx(conn)
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert good_chunk in returned_ids, "enrich=1 chunk must be returned"
        assert bad_chunk not in returned_ids, "enrich=0 chunk must be excluded"


# ---------------------------------------------------------------------------
# TestFromAC_StoreEnrichment
# ---------------------------------------------------------------------------


class TestFromAC_StoreEnrichment:
    """Tests derived from AC5, AC6, AC7, AC8 for store_enrichment."""

    # --- AC5: UPSERT entities via INSERT OR REPLACE (td:1) ---

    @pytest.mark.asyncio
    async def test_upsert_replaces_existing_entity_on_same_id(
        self, conn: sqlite3.Connection
    ) -> None:
        """Calling store_enrichment with an existing entity id updates it (single row)."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_id = _insert_chunk(conn, document_id=doc_id)
        entity_id = _insert_entity(
            conn, name="OriginalName", document_id=doc_id, chunk_id=chunk_id
        )

        entities = [
            {
                "id": entity_id,
                "name": "UpdatedName",
                "entity_type": "concept",
                "description": "Updated description",
                "document_id": doc_id,
                "chunk_id": chunk_id,
            }
        ]
        ctx = _make_mcp_ctx(conn)
        await store_enrichment(ctx, chunk_id=chunk_id, entities=entities, edges=[])

        rows = conn.execute(
            "SELECT name FROM entities WHERE id = ?", (entity_id,)
        ).fetchall()
        assert len(rows) == 1, f"UPSERT must produce exactly one row, got {len(rows)}"
        assert rows[0][0] == "UpdatedName", (
            f"Entity name should be 'UpdatedName' after UPSERT, got {rows[0][0]!r}"
        )

    @pytest.mark.asyncio
    async def test_new_entity_inserted_by_store_enrichment(
        self, conn: sqlite3.Connection
    ) -> None:
        """store_enrichment creates a new entity row that did not exist before."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_id = _insert_chunk(conn, document_id=doc_id)
        new_entity_id = str(uuid.uuid4())

        entities = [
            {
                "id": new_entity_id,
                "name": "BrandNewEntity",
                "entity_type": "technology",
                "description": "Created by store_enrichment",
                "document_id": doc_id,
                "chunk_id": chunk_id,
            }
        ]
        ctx = _make_mcp_ctx(conn)
        await store_enrichment(ctx, chunk_id=chunk_id, entities=entities, edges=[])

        row = conn.execute(
            "SELECT name FROM entities WHERE id = ?", (new_entity_id,)
        ).fetchone()
        assert row is not None, "New entity must be inserted by store_enrichment"
        assert row[0] == "BrandNewEntity"

    # --- AC6: INSERT OR IGNORE edges with UNIQUE constraint (td:1) ---

    @pytest.mark.asyncio
    async def test_duplicate_edge_does_not_raise_error(
        self, conn: sqlite3.Connection
    ) -> None:
        """Inserting a duplicate edge (same source_id, target_id, relation, document_id) raises no error."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_a = _insert_chunk(conn, document_id=doc_id, content="chunk A")
        chunk_b = _insert_chunk(conn, document_id=doc_id, content="chunk B")
        ent_a = _insert_entity(conn, document_id=doc_id, chunk_id=chunk_a)
        ent_b = _insert_entity(conn, document_id=doc_id, chunk_id=chunk_a)

        edge = {
            "source_id": ent_a,
            "target_id": ent_b,
            "relation": "related_to",
            "document_id": doc_id,
            "weight": 1.0,
        }
        ctx = _make_mcp_ctx(conn)
        # First call — inserts edge, marks chunk_a enriched
        await store_enrichment(ctx, chunk_id=chunk_a, entities=[], edges=[edge])
        # Second call on different chunk, same edge — must be ignored, not error
        await store_enrichment(ctx, chunk_id=chunk_b, entities=[], edges=[edge])

    @pytest.mark.asyncio
    async def test_duplicate_edge_results_in_single_row(
        self, conn: sqlite3.Connection
    ) -> None:
        """After two store_enrichment calls with the same edge, exactly one edge row exists."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_a = _insert_chunk(conn, document_id=doc_id, content="chunk A")
        chunk_b = _insert_chunk(conn, document_id=doc_id, content="chunk B")
        ent_a = _insert_entity(conn, document_id=doc_id, chunk_id=chunk_a)
        ent_b = _insert_entity(conn, document_id=doc_id, chunk_id=chunk_a)

        edge = {
            "source_id": ent_a,
            "target_id": ent_b,
            "relation": "causes",
            "document_id": doc_id,
            "weight": 0.8,
        }
        ctx = _make_mcp_ctx(conn)
        await store_enrichment(ctx, chunk_id=chunk_a, entities=[], edges=[edge])
        await store_enrichment(ctx, chunk_id=chunk_b, entities=[], edges=[edge])

        count = conn.execute(
            "SELECT count(*) FROM edges "
            "WHERE source_id=? AND target_id=? AND relation=? AND document_id=?",
            (ent_a, ent_b, "causes", doc_id),
        ).fetchone()[0]
        assert count == 1, (
            f"Expected exactly 1 edge row after duplicate insert, got {count}"
        )

    # --- AC7: updates enrichment_state to 'enriched' (td:1) ---

    @pytest.mark.asyncio
    async def test_store_enrichment_sets_state_to_enriched(
        self, conn: sqlite3.Connection
    ) -> None:
        """After store_enrichment, the chunk's enrichment_state is 'enriched'."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_id = _insert_chunk(conn, document_id=doc_id, enrichment_state="claimed")

        ctx = _make_mcp_ctx(conn)
        await store_enrichment(ctx, chunk_id=chunk_id, entities=[], edges=[])

        row = conn.execute(
            "SELECT enrichment_state FROM chunks WHERE id=?", (chunk_id,)
        ).fetchone()
        assert row is not None
        assert row[0] == "enriched", (
            f"Expected enrichment_state='enriched', got {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_enriched_chunk_not_returned_by_get_next_batch(
        self, conn: sqlite3.Connection
    ) -> None:
        """After store_enrichment, the chunk does not appear in get_next_batch results."""
        source_id = _insert_source(conn)
        doc_id = _insert_document(conn, source_id=source_id)
        chunk_id = _insert_chunk(conn, document_id=doc_id)

        ctx = _make_mcp_ctx(conn)
        await store_enrichment(ctx, chunk_id=chunk_id, entities=[], edges=[])
        result = await get_next_batch(ctx, limit=10)

        returned_ids = {_get_chunk_field(r, "chunk_id") for r in result}
        assert chunk_id not in returned_ids, (
            "Enriched chunk must not appear in get_next_batch results"
        )

    # --- AC8: WAL concurrent write safety (td:2) ---

    @pytest.mark.asyncio
    async def test_concurrent_store_enrichment_no_operational_error(
        self, tmp_path: Path
    ) -> None:
        """Two concurrent store_enrichment calls on a WAL file-backed DB succeed without error."""
        db_path = str(tmp_path / "wal_concurrent.db")

        # Set up shared file-backed DB with WAL mode
        setup_conn = sqlite3.connect(db_path)
        init_db(setup_conn)
        setup_conn.execute("PRAGMA journal_mode=WAL")

        sid = str(uuid.uuid4())
        did = str(uuid.uuid4())
        now = _now_iso()
        setup_conn.execute(
            "INSERT INTO knowledge_sources "
            "(id, name, source_type, fetch_method, enrich, config, scope, enabled, priority, created_at, updated_at) "
            "VALUES (?, 'WALSource', 'web', 'http', 1, '{}', 'global', 1, 0, ?, ?)",
            (sid, now, now),
        )
        setup_conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id) "
            "VALUES (?, 'WAL Doc', 'c', '{}', ?, 'global', ?)",
            (did, now, sid),
        )
        chunk_id_a = str(uuid.uuid4())
        chunk_id_b = str(uuid.uuid4())
        setup_conn.execute(
            "INSERT INTO chunks "
            "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state) "
            "VALUES (?, ?, 0, 'chunk-a', '{}', ?, 'global', 'claimed')",
            (chunk_id_a, did, now),
        )
        setup_conn.execute(
            "INSERT INTO chunks "
            "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state) "
            "VALUES (?, ?, 1, 'chunk-b', '{}', ?, 'global', 'claimed')",
            (chunk_id_b, did, now),
        )
        setup_conn.commit()
        setup_conn.close()

        errors: list[Exception] = []

        def _write_chunk(chunk_id: str) -> None:
            c = sqlite3.connect(db_path)
            c.execute("PRAGMA journal_mode=WAL")
            ctx = _make_mcp_ctx(c)
            try:
                asyncio.run(
                    store_enrichment(ctx, chunk_id=chunk_id, entities=[], edges=[])
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                c.close()

        t1 = threading.Thread(target=_write_chunk, args=(chunk_id_a,))
        t2 = threading.Thread(target=_write_chunk, args=(chunk_id_b,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not errors, f"Concurrent WAL writes raised errors: {errors}"

    @pytest.mark.asyncio
    async def test_concurrent_writes_both_chunks_become_enriched(
        self, tmp_path: Path
    ) -> None:
        """After concurrent store_enrichment, both chunks are in 'enriched' state."""
        db_path = str(tmp_path / "wal_both_enriched.db")

        setup_conn = sqlite3.connect(db_path)
        init_db(setup_conn)
        setup_conn.execute("PRAGMA journal_mode=WAL")

        sid = str(uuid.uuid4())
        did = str(uuid.uuid4())
        now = _now_iso()
        setup_conn.execute(
            "INSERT INTO knowledge_sources "
            "(id, name, source_type, fetch_method, enrich, config, scope, enabled, priority, created_at, updated_at) "
            "VALUES (?, 'WALSource2', 'web', 'http', 1, '{}', 'global', 1, 0, ?, ?)",
            (sid, now, now),
        )
        setup_conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id) "
            "VALUES (?, 'WAL Doc 2', 'c', '{}', ?, 'global', ?)",
            (did, now, sid),
        )
        chunk_id_a = str(uuid.uuid4())
        chunk_id_b = str(uuid.uuid4())
        setup_conn.execute(
            "INSERT INTO chunks "
            "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state) "
            "VALUES (?, ?, 0, 'a', '{}', ?, 'global', 'claimed')",
            (chunk_id_a, did, now),
        )
        setup_conn.execute(
            "INSERT INTO chunks "
            "(id, document_id, chunk_index, content, metadata, created_at, scope, enrichment_state) "
            "VALUES (?, ?, 1, 'b', '{}', ?, 'global', 'claimed')",
            (chunk_id_b, did, now),
        )
        setup_conn.commit()
        setup_conn.close()

        errors: list[Exception] = []

        def _write_chunk(chunk_id: str) -> None:
            c = sqlite3.connect(db_path)
            c.execute("PRAGMA journal_mode=WAL")
            ctx = _make_mcp_ctx(c)
            try:
                asyncio.run(
                    store_enrichment(ctx, chunk_id=chunk_id, entities=[], edges=[])
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                c.close()

        t1 = threading.Thread(target=_write_chunk, args=(chunk_id_a,))
        t2 = threading.Thread(target=_write_chunk, args=(chunk_id_b,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not errors, f"Concurrent WAL writes raised errors: {errors}"

        verify_conn = sqlite3.connect(db_path)
        rows = verify_conn.execute(
            "SELECT id, enrichment_state FROM chunks WHERE id IN (?, ?)",
            (chunk_id_a, chunk_id_b),
        ).fetchall()
        verify_conn.close()

        states = {row[0]: row[1] for row in rows}
        assert states.get(chunk_id_a) == "enriched", (
            f"chunk_a expected 'enriched', got {states.get(chunk_id_a)!r}"
        )
        assert states.get(chunk_id_b) == "enriched", (
            f"chunk_b expected 'enriched', got {states.get(chunk_id_b)!r}"
        )
