"""Durable consolidation tests for the knowledge source lifecycle.

Verifies integration across three completed tasks:
- O2 refresh honesty (#1651): _update_source_record preserves last_refreshed_at on skipped
- O1 health exposure (#1654): list_sources returns all 5 health fields
- O4 remove_source (#1652): remove_source counts, delete_embedding calls, no orphans

Consolidation task: #1655
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore
from owlbear_mcp_knowledge.server import AppContext, list_sources, remove_source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _mcp_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """Real in-memory SQLite with schema initialised."""
    c = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(c)
    return c


@pytest.fixture()
def mock_vs() -> MagicMock:
    """Stub vector store — captures delete_embedding calls."""
    vs = MagicMock()
    vs.delete_embedding = MagicMock()
    return vs


@pytest.fixture()
def lifecycle(conn: sqlite3.Connection, mock_vs: MagicMock) -> dict:
    """Full lifecycle fixture.

    Creates a KnowledgeSource via KnowledgeSourceStore.create(), then inserts
    1 document, 1 chunk, 1 entity, 1 edge, and 1 document_status row linked to
    that source.  Returns a dict with all components needed by AC tests.
    """
    source_store = KnowledgeSourceStore(conn)
    now = _now()

    src = KnowledgeSource(
        id="src-lc-1",
        name="Lifecycle Source",
        source_type=SourceType.URL_LIST,
        fetch_method="http",
        enrich=True,
        config={"urls": ["https://example.test/page"]},
        scope="team",
        enabled=True,
        priority=5,
        created_at=now,
        updated_at=now,
    )
    source_store.create(src)

    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("doc-lc-1", "Lifecycle Doc", "content for lifecycle testing", "{}", now, "team", "src-lc-1"),
    )
    conn.execute(
        "INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at, scope)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("chunk-lc-1", "doc-lc-1", 0, "chunk content text", "{}", now, "team"),
    )
    conn.execute(
        "INSERT INTO entities"
        " (id, name, entity_type, description, metadata, created_at, scope, document_id, chunk_id, importance)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("entity-lc-1", "Lifecycle Entity", "concept", "", "{}", now, "team", "doc-lc-1", "chunk-lc-1", 0.5),
    )
    conn.execute(
        "INSERT INTO edges"
        " (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("edge-lc-1", "entity-lc-1", "entity-lc-1", "relates_to", "doc-lc-1", 1.0, "{}", now, "team"),
    )
    conn.execute(
        "INSERT INTO document_status"
        " (document_id, status, source, created_at, updated_at, scope, content_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("doc-lc-1", "ingested", "https://example.test/page", now, now, "team", "hash-lc-1"),
    )
    conn.commit()

    app_ctx = AppContext(
        conn=conn,
        query_service=None,
        graph_store=None,
        ingest_pipeline=None,
        source_store=source_store,
        vector_store=mock_vs,
    )

    return {
        "conn": conn,
        "source_store": source_store,
        "source": src,
        "app_ctx": app_ctx,
        "mock_vs": mock_vs,
    }


# ---------------------------------------------------------------------------
# TestKnowledgeSourceLifecycleDurable
# ---------------------------------------------------------------------------


class TestKnowledgeSourceLifecycleDurable:
    """Integration lifecycle: create -> _update_source_record x 2 -> list_sources -> remove_source.

    Tests the interaction between KnowledgeSourceStore (knowledge package),
    RefreshOrchestrator._update_source_record (knowledge package), and the
    list_sources / remove_source MCP tools (mcp-knowledge package).
    """

    # ------------------------------------------------------------------
    # AC-1: create() persists source + fixture has ≥1 doc/chunk/entity
    # ------------------------------------------------------------------

    def test_ac1_create_persists_source_in_db(self, lifecycle: dict) -> None:
        """KnowledgeSourceStore.create() must insert the source row into knowledge_sources."""
        conn = lifecycle["conn"]
        row = conn.execute(
            "SELECT id, name FROM knowledge_sources WHERE id = ?",
            ("src-lc-1",),
        ).fetchone()
        assert row is not None, "Source row not found after create()"
        assert row[0] == "src-lc-1"
        assert row[1] == "Lifecycle Source"

    def test_ac1_fixture_has_at_least_one_document(self, lifecycle: dict) -> None:
        """Fixture must have ≥1 document linked to the source."""
        count = (
            lifecycle["conn"]
            .execute(
                "SELECT COUNT(*) FROM documents WHERE source_id = ?",
                ("src-lc-1",),
            )
            .fetchone()[0]
        )
        assert count >= 1, f"Expected ≥1 document linked to source, got {count}"

    def test_ac1_fixture_has_at_least_one_chunk(self, lifecycle: dict) -> None:
        """Fixture must have ≥1 chunk linked to the document."""
        count = (
            lifecycle["conn"]
            .execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id = ?",
                ("doc-lc-1",),
            )
            .fetchone()[0]
        )
        assert count >= 1, f"Expected ≥1 chunk linked to document, got {count}"

    def test_ac1_fixture_has_at_least_one_entity(self, lifecycle: dict) -> None:
        """Fixture must have ≥1 entity linked to the document."""
        count = (
            lifecycle["conn"]
            .execute(
                "SELECT COUNT(*) FROM entities WHERE document_id = ?",
                ("doc-lc-1",),
            )
            .fetchone()[0]
        )
        assert count >= 1, f"Expected ≥1 entity linked to document, got {count}"

    # ------------------------------------------------------------------
    # AC-2: _update_source_record — refreshed then skipped
    # ------------------------------------------------------------------

    def test_ac2_refreshed_result_sets_last_refreshed_at(self, lifecycle: dict) -> None:
        """_update_source_record with refreshed=1 sets last_refreshed_at."""
        ss = lifecycle["source_store"]
        src = lifecycle["source"]
        orchestrator = RefreshOrchestrator(store=ss, pipeline=MagicMock())

        result = RefreshResult(source_id="src-lc-1", refreshed=1, skipped=0, failed=0)
        orchestrator._update_source_record(src, result)

        updated = ss.get("src-lc-1")
        assert updated is not None
        assert updated.last_refreshed_at is not None, (
            "last_refreshed_at must be set after _update_source_record(refreshed=1)"
        )

    def test_ac2_refreshed_result_sets_last_checked_at(self, lifecycle: dict) -> None:
        """_update_source_record with refreshed=1 sets last_checked_at."""
        ss = lifecycle["source_store"]
        src = lifecycle["source"]
        orchestrator = RefreshOrchestrator(store=ss, pipeline=MagicMock())

        result = RefreshResult(source_id="src-lc-1", refreshed=1, skipped=0, failed=0)
        orchestrator._update_source_record(src, result)

        updated = ss.get("src-lc-1")
        assert updated is not None
        assert updated.last_checked_at is not None, (
            "last_checked_at must be set after _update_source_record(refreshed=1)"
        )

    def test_ac2_skipped_result_preserves_last_refreshed_at(self, lifecycle: dict) -> None:
        """After refreshed then skipped, last_refreshed_at retains the value from the refreshed call."""
        ss = lifecycle["source_store"]
        src = lifecycle["source"]
        orchestrator = RefreshOrchestrator(store=ss, pipeline=MagicMock())

        # Step 1: refreshed path — sets last_refreshed_at
        result_refreshed = RefreshResult(source_id="src-lc-1", refreshed=1, skipped=0, failed=0)
        orchestrator._update_source_record(src, result_refreshed)
        after_refreshed = ss.get("src-lc-1")
        assert after_refreshed is not None
        first_refreshed_at = after_refreshed.last_refreshed_at
        assert first_refreshed_at is not None, "Precondition: refreshed path must set last_refreshed_at"

        # Step 2: skipped path — last_refreshed_at must not change
        result_skipped = RefreshResult(source_id="src-lc-1", refreshed=0, skipped=1, failed=0)
        orchestrator._update_source_record(after_refreshed, result_skipped)
        after_skipped = ss.get("src-lc-1")
        assert after_skipped is not None

        assert after_skipped.last_refreshed_at == first_refreshed_at, (
            f"last_refreshed_at must be preserved on skipped refresh: "
            f"expected {first_refreshed_at!r}, got {after_skipped.last_refreshed_at!r}"
        )

    def test_ac2_skipped_result_sets_last_checked_at(self, lifecycle: dict) -> None:
        """After skipped refresh, last_checked_at is set (reflects the skipped check timestamp)."""
        ss = lifecycle["source_store"]
        src = lifecycle["source"]
        orchestrator = RefreshOrchestrator(store=ss, pipeline=MagicMock())

        result_refreshed = RefreshResult(source_id="src-lc-1", refreshed=1, skipped=0, failed=0)
        orchestrator._update_source_record(src, result_refreshed)
        after_refreshed = ss.get("src-lc-1")

        result_skipped = RefreshResult(source_id="src-lc-1", refreshed=0, skipped=1, failed=0)
        orchestrator._update_source_record(after_refreshed, result_skipped)
        after_skipped = ss.get("src-lc-1")

        assert after_skipped is not None
        assert after_skipped.last_checked_at is not None, "last_checked_at must be set after skipped refresh"

    # ------------------------------------------------------------------
    # AC-3: list_sources includes all 5 health fields with correct values
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ac3_list_sources_includes_last_refreshed_at(self, lifecycle: dict) -> None:
        """list_sources response includes last_refreshed_at for each source."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        sources = await list_sources(ctx)
        src_item = next((s for s in sources if s["id"] == "src-lc-1"), None)
        assert src_item is not None, "src-lc-1 not found in list_sources response"
        assert "last_refreshed_at" in src_item, "Health field 'last_refreshed_at' missing from list_sources"

    @pytest.mark.asyncio
    async def test_ac3_list_sources_includes_last_checked_at(self, lifecycle: dict) -> None:
        """list_sources response includes last_checked_at for each source."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        sources = await list_sources(ctx)
        src_item = next(s for s in sources if s["id"] == "src-lc-1")
        assert "last_checked_at" in src_item, "Health field 'last_checked_at' missing from list_sources"

    @pytest.mark.asyncio
    async def test_ac3_list_sources_includes_last_error(self, lifecycle: dict) -> None:
        """list_sources response includes last_error for each source."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        sources = await list_sources(ctx)
        src_item = next(s for s in sources if s["id"] == "src-lc-1")
        assert "last_error" in src_item, "Health field 'last_error' missing from list_sources"

    @pytest.mark.asyncio
    async def test_ac3_list_sources_includes_enabled(self, lifecycle: dict) -> None:
        """list_sources response includes enabled for each source."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        sources = await list_sources(ctx)
        src_item = next(s for s in sources if s["id"] == "src-lc-1")
        assert "enabled" in src_item, "Health field 'enabled' missing from list_sources"

    @pytest.mark.asyncio
    async def test_ac3_list_sources_includes_fetch_method(self, lifecycle: dict) -> None:
        """list_sources response includes fetch_method for each source."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        sources = await list_sources(ctx)
        src_item = next(s for s in sources if s["id"] == "src-lc-1")
        assert "fetch_method" in src_item, "Health field 'fetch_method' missing from list_sources"

    @pytest.mark.asyncio
    async def test_ac3_last_refreshed_at_retained_after_skipped_refresh(self, lifecycle: dict) -> None:
        """list_sources shows last_refreshed_at from refreshed path, not overwritten by skipped refresh."""
        ss = lifecycle["source_store"]
        src = lifecycle["source"]
        app_ctx = lifecycle["app_ctx"]
        orchestrator = RefreshOrchestrator(store=ss, pipeline=MagicMock())

        # Refreshed path → sets last_refreshed_at
        orchestrator._update_source_record(src, RefreshResult(source_id="src-lc-1", refreshed=1, skipped=0, failed=0))
        after_refreshed = ss.get("src-lc-1")
        assert after_refreshed is not None
        expected_refreshed_at = after_refreshed.last_refreshed_at

        # Skipped path → must NOT overwrite last_refreshed_at
        orchestrator._update_source_record(
            after_refreshed, RefreshResult(source_id="src-lc-1", refreshed=0, skipped=1, failed=0)
        )

        ctx = _mcp_ctx(app_ctx)
        sources = await list_sources(ctx)
        src_item = next(s for s in sources if s["id"] == "src-lc-1")

        assert src_item["last_refreshed_at"] == expected_refreshed_at, (
            "list_sources last_refreshed_at must retain the refreshed-path value "
            "and not be overwritten by the subsequent skipped refresh"
        )
        assert src_item["last_checked_at"] is not None, "list_sources last_checked_at must reflect the skipped refresh"

    # ------------------------------------------------------------------
    # AC-4: remove_source counts and delete_embedding calls
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ac4_remove_source_returns_nonzero_document_count(self, lifecycle: dict) -> None:
        """remove_source returns documents > 0 matching the pre-removal fixture."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        result = await remove_source(ctx, "src-lc-1")
        assert result["documents"] > 0, f"Expected documents > 0, got {result['documents']}"

    @pytest.mark.asyncio
    async def test_ac4_remove_source_returns_nonzero_chunk_count(self, lifecycle: dict) -> None:
        """remove_source returns chunks > 0 matching the pre-removal fixture."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        result = await remove_source(ctx, "src-lc-1")
        assert result["chunks"] > 0, f"Expected chunks > 0, got {result['chunks']}"

    @pytest.mark.asyncio
    async def test_ac4_remove_source_returns_nonzero_entity_count(self, lifecycle: dict) -> None:
        """remove_source returns entities > 0 matching the pre-removal fixture."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        result = await remove_source(ctx, "src-lc-1")
        assert result["entities"] > 0, f"Expected entities > 0, got {result['entities']}"

    @pytest.mark.asyncio
    async def test_ac4_remove_source_counts_match_fixture_exactly(self, lifecycle: dict) -> None:
        """remove_source counts exactly match the fixture: 1 document, 1 chunk, 1 entity."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        result = await remove_source(ctx, "src-lc-1")
        assert result["documents"] == 1, f"Expected documents=1, got {result['documents']}"
        assert result["chunks"] == 1, f"Expected chunks=1, got {result['chunks']}"
        assert result["entities"] == 1, f"Expected entities=1, got {result['entities']}"

    @pytest.mark.asyncio
    async def test_ac4_delete_embedding_called_for_chunk_id(self, lifecycle: dict) -> None:
        """remove_source calls delete_embedding with the chunk ID."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        mock_vs = lifecycle["mock_vs"]

        await remove_source(ctx, "src-lc-1")

        called_ids = [c.args[0] for c in mock_vs.delete_embedding.call_args_list]
        assert "chunk-lc-1" in called_ids, (
            f"delete_embedding must be called with chunk ID 'chunk-lc-1'; got: {called_ids}"
        )

    @pytest.mark.asyncio
    async def test_ac4_delete_embedding_called_for_entity_id(self, lifecycle: dict) -> None:
        """remove_source calls delete_embedding with the entity ID."""
        ctx = _mcp_ctx(lifecycle["app_ctx"])
        mock_vs = lifecycle["mock_vs"]

        await remove_source(ctx, "src-lc-1")

        called_ids = [c.args[0] for c in mock_vs.delete_embedding.call_args_list]
        assert "entity-lc-1" in called_ids, (
            f"delete_embedding must be called with entity ID 'entity-lc-1'; got: {called_ids}"
        )

    # ------------------------------------------------------------------
    # AC-5: No orphan rows after remove_source
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ac5_no_orphan_documents(self, lifecycle: dict) -> None:
        """After remove_source, documents table has zero rows for the removed source."""
        conn = lifecycle["conn"]
        await remove_source(_mcp_ctx(lifecycle["app_ctx"]), "src-lc-1")

        count = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE source_id = ?",
            ("src-lc-1",),
        ).fetchone()[0]
        assert count == 0, f"Expected 0 document rows after remove_source, got {count}"

    @pytest.mark.asyncio
    async def test_ac5_no_orphan_chunks(self, lifecycle: dict) -> None:
        """After remove_source, chunks linked to the removed document are deleted."""
        conn = lifecycle["conn"]
        await remove_source(_mcp_ctx(lifecycle["app_ctx"]), "src-lc-1")

        count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?",
            ("doc-lc-1",),
        ).fetchone()[0]
        assert count == 0, f"Expected 0 chunk rows after remove_source, got {count}"

    @pytest.mark.asyncio
    async def test_ac5_no_orphan_entities(self, lifecycle: dict) -> None:
        """After remove_source, entities linked to the removed document are deleted."""
        conn = lifecycle["conn"]
        await remove_source(_mcp_ctx(lifecycle["app_ctx"]), "src-lc-1")

        count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE document_id = ?",
            ("doc-lc-1",),
        ).fetchone()[0]
        assert count == 0, f"Expected 0 entity rows after remove_source, got {count}"

    @pytest.mark.asyncio
    async def test_ac5_no_orphan_edges(self, lifecycle: dict) -> None:
        """After remove_source, edges referencing the removed entity are deleted."""
        conn = lifecycle["conn"]
        await remove_source(_mcp_ctx(lifecycle["app_ctx"]), "src-lc-1")

        count = conn.execute(
            "SELECT COUNT(*) FROM edges WHERE source_id = ? OR target_id = ?",
            ("entity-lc-1", "entity-lc-1"),
        ).fetchone()[0]
        assert count == 0, f"Expected 0 edge rows after remove_source, got {count}"

    @pytest.mark.asyncio
    async def test_ac5_no_orphan_document_status(self, lifecycle: dict) -> None:
        """After remove_source, document_status rows for the removed document are deleted."""
        conn = lifecycle["conn"]
        await remove_source(_mcp_ctx(lifecycle["app_ctx"]), "src-lc-1")

        count = conn.execute(
            "SELECT COUNT(*) FROM document_status WHERE document_id = ?",
            ("doc-lc-1",),
        ).fetchone()[0]
        assert count == 0, f"Expected 0 document_status rows after remove_source, got {count}"
