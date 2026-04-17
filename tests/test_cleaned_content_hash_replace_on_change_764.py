"""RED-phase tests for cleaned-content hash and replace-on-change cascade (#764).

Tests the contract for:
  - AC1: Delta detection hashes cleaned markdown, not raw HTML
  - AC2: Changed content → old doc + entities + edges cascade-deleted before re-ingestion
  - AC3: Unchanged content hash → skip (even when raw HTML differs)
  - AC4: No entity accumulation on refresh

All tests fail (RED) because IngestPipeline.ingest() does not yet accept a
content_cleaner parameter.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    from owlbear_knowledge.schema import init_db

    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _make_store(conn: sqlite3.Connection) -> tuple[object, object]:
    from owlbear_knowledge.document_store import DocumentStore
    from owlbear_knowledge.graph_store import GraphStore

    graph = GraphStore(conn)
    vector_store = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1, 0.2]]
    return DocumentStore(conn, graph, vector_store, embedder), graph


def _make_pipeline(store: object) -> object:
    """Pipeline with mock extractor that returns no entities."""
    from owlbear_knowledge.chunker import TextChunker
    from owlbear_knowledge.extractor import ExtractionResult
    from owlbear_knowledge.ingest import IngestPipeline

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=ExtractionResult(entities=[], edges=[]))
    return IngestPipeline(
        document_store=store,
        entity_extractor=mock_extractor,
        text_chunker=TextChunker(),
    )


def _make_pipeline_with_fresh_entities(
    store: object,
    n_entities: int = 2,
    n_edges: int = 0,
) -> object:
    """Pipeline whose extractor returns fresh entity/edge objects on every call.

    Creates new UUIDs for each extraction so primary-key conflicts cannot mask
    missing cascade-delete behavior during the GREEN phase.
    """
    from owlbear_knowledge.chunker import TextChunker
    from owlbear_knowledge.extractor import ExtractionResult
    from owlbear_knowledge.ingest import IngestPipeline
    from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType

    def _fresh(_text: str) -> ExtractionResult:
        entities = [Entity(name=f"E{i}", entity_type=EntityType.CONCEPT) for i in range(n_entities)]
        edges: list[Edge] = []
        if n_edges > 0 and len(entities) >= 2:
            edges = [
                Edge(
                    source_id=entities[0].id,
                    target_id=entities[-1].id,
                    relation=RelationType.RELATED_TO,
                )
            ]
        return ExtractionResult(entities=entities, edges=edges)

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(side_effect=_fresh)
    return IngestPipeline(
        document_store=store,
        entity_extractor=mock_extractor,
        text_chunker=TextChunker(),
    )


def _make_intake(content: str, source: str = "test://source") -> object:
    from owlbear_knowledge.intake import IntakeResult

    return IntakeResult(content=content, source=source, metadata={"source_type": "text"})


def _strip_tags(html: str) -> str:
    """Minimal HTML tag stripper used as a stand-in cleaner in tests."""
    import re

    return re.sub(r"<[^>]+>", "", html).strip()


def _normalize_whitespace(text: str) -> str:
    """Whitespace normalizer used as a stand-in cleaner in tests."""
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# AC1: Delta detection hashes cleaned markdown, not raw HTML
# ---------------------------------------------------------------------------


class TestFromAC_HashCleanedContent:
    """AC1: ingest() accepts a content_cleaner param; hash is computed on the cleaned output."""

    @pytest.mark.asyncio
    async def test_ingest_accepts_content_cleaner_kwarg(self) -> None:
        """ingest() accepts a content_cleaner keyword argument without raising TypeError."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline(store)
        intake = _make_intake("<html>hello world</html>")

        # Fails: IngestPipeline.ingest() has no content_cleaner parameter yet
        result = await pipeline.ingest(intake, content_cleaner=lambda _: "hello world")  # type: ignore[call-arg]
        assert result.status in {"ok", "skipped"}

    @pytest.mark.asyncio
    async def test_cleaner_called_with_raw_intake_content(self) -> None:
        """When content_cleaner is provided, ingest() calls it with the raw intake.content."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline(store)

        raw_html = "<html><body>some content</body></html>"
        mock_cleaner = MagicMock(return_value="some content")
        intake = _make_intake(raw_html)

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(intake, content_cleaner=mock_cleaner)  # type: ignore[call-arg]
        mock_cleaner.assert_called_once_with(raw_html)

    @pytest.mark.asyncio
    async def test_hash_computed_on_cleaner_output_not_raw(self) -> None:
        """Two different raw strings that clean to the same output → second ingest is skipped."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline(store)

        # Both raw strings clean to the same markdown
        raw_v1 = "<html>  normalized  content  </html>"
        raw_v2 = "<html><b>normalized content</b></html>"
        intake_v1 = _make_intake(raw_v1, source="test://hash-page")
        intake_v2 = _make_intake(raw_v2, source="test://hash-page")

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(intake_v1, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        result2 = await pipeline.ingest(intake_v2, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        assert result2.status == "skipped"

    @pytest.mark.asyncio
    async def test_no_cleaner_hashes_raw_content(self) -> None:
        """With content_cleaner=None, ingest() hashes the raw content (existing behavior)."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline(store)

        intake = _make_intake("raw content", source="test://nocleaner")

        # Fails: content_cleaner kwarg not accepted
        result = await pipeline.ingest(intake, content_cleaner=None)  # type: ignore[call-arg]
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# AC2: Changed content → cascade-delete old doc + entities + edges before re-ingestion
# ---------------------------------------------------------------------------


class TestFromAC_CascadeDeleteOnChange:
    """AC2: When cleaned content changes, old entities and edges are removed before re-ingest."""

    @pytest.mark.asyncio
    async def test_changed_content_old_entities_removed_from_db(self) -> None:
        """After re-ingest with changed content, entity count equals the first-ingest count."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline_with_fresh_entities(store, n_entities=2)

        intake_v1 = _make_intake("content version one", source="test://cascade-entities")
        intake_v2 = _make_intake("content version two", source="test://cascade-entities")

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(intake_v1, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        count_after_first = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        assert count_after_first > 0  # entities were stored

        await pipeline.ingest(intake_v2, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        count_after_second = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        # Old entities must be replaced, not accumulated
        assert count_after_second == count_after_first

    @pytest.mark.asyncio
    async def test_changed_content_old_edges_removed_from_db(self) -> None:
        """After re-ingest with changed content, edge count equals the first-ingest count."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline_with_fresh_entities(store, n_entities=2, n_edges=1)

        intake_v1 = _make_intake("edge content v1", source="test://cascade-edges")
        intake_v2 = _make_intake("edge content v2", source="test://cascade-edges")

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(intake_v1, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        edge_count_first = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert edge_count_first > 0  # edges were stored

        await pipeline.ingest(intake_v2, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        edge_count_second = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        # Old edges must be replaced, not accumulated
        assert edge_count_second == edge_count_first

    @pytest.mark.asyncio
    async def test_cascade_preserves_unrelated_document_entities(self) -> None:
        """Cascade delete for one document does not remove another document's entities."""
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.models import Entity, EntityType

        conn = _make_db()
        store, _ = _make_store(conn)

        # Two independent pipelines for two sources — they share the same store
        sentinel_entity = Entity(name="UnrelatedDocEntity", entity_type=EntityType.CONCEPT)

        mock_extractor_doc2 = MagicMock()
        mock_extractor_doc2.extract = AsyncMock(return_value=ExtractionResult(entities=[sentinel_entity], edges=[]))
        from owlbear_knowledge.chunker import TextChunker
        from owlbear_knowledge.ingest import IngestPipeline

        pipeline_doc1 = _make_pipeline_with_fresh_entities(store, n_entities=1)
        pipeline_doc2 = IngestPipeline(
            document_store=store,
            entity_extractor=mock_extractor_doc2,
            text_chunker=TextChunker(),
        )

        # Ingest doc1 v1 and doc2 independently
        # Fails: content_cleaner kwarg not accepted
        await pipeline_doc1.ingest(  # type: ignore[call-arg]
            _make_intake("doc1 initial", source="test://doc1"), content_cleaner=_strip_tags
        )
        await pipeline_doc2.ingest(  # type: ignore[call-arg]
            _make_intake("doc2 content", source="test://doc2"), content_cleaner=_strip_tags
        )

        # Re-ingest doc1 with changed content — cascade deletes doc1's entities only
        await pipeline_doc1.ingest(  # type: ignore[call-arg]
            _make_intake("doc1 changed", source="test://doc1"), content_cleaner=_strip_tags
        )

        # doc2's sentinel entity must still be in the DB
        count = conn.execute("SELECT COUNT(*) FROM entities WHERE name = ?", ("UnrelatedDocEntity",)).fetchone()[0]
        assert count == 1


# ---------------------------------------------------------------------------
# AC3: Unchanged content hash → skip (even when raw HTML differs)
# ---------------------------------------------------------------------------


class TestFromAC_SkipUnchangedCleanedContent:
    """AC3: ingest() skips when cleaned content hash matches, even if raw HTML differs."""

    @pytest.mark.asyncio
    async def test_different_raw_same_cleaned_content_returns_skipped(self) -> None:
        """Two different raw HTML strings that clean to the same result → second is skipped."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline(store)

        # raw_v2 differs from raw_v1 only in <b> tags — same after cleaning
        raw_v1 = "same content"
        raw_v2 = "<b>same content</b>"
        intake_v1 = _make_intake(raw_v1, source="test://skiptest")
        intake_v2 = _make_intake(raw_v2, source="test://skiptest")

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(intake_v1, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        result2 = await pipeline.ingest(intake_v2, content_cleaner=_strip_tags)  # type: ignore[call-arg]
        assert result2.status == "skipped"

    @pytest.mark.asyncio
    async def test_whitespace_only_raw_difference_skips(self) -> None:
        """Raw content differing only in whitespace that normalizes to the same string → skip."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline(store)

        source = "test://whitespace-skip"
        intake_v1 = _make_intake("hello   world", source=source)
        intake_v2 = _make_intake("hello world", source=source)  # Same after normalization

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(intake_v1, content_cleaner=_normalize_whitespace)  # type: ignore[call-arg]
        result2 = await pipeline.ingest(intake_v2, content_cleaner=_normalize_whitespace)  # type: ignore[call-arg]
        # Both clean to "hello world" → second call is skipped
        assert result2.status == "skipped"


# ---------------------------------------------------------------------------
# AC4: No entity accumulation on refresh
# ---------------------------------------------------------------------------


class TestFromAC_NoEntityAccumulationOnRefresh:
    """AC4: Entity and edge counts remain stable across refresh cycles -- no accumulation."""

    @pytest.mark.asyncio
    async def test_entity_count_stable_after_content_change(self) -> None:
        """Re-ingest with changed content replaces old entities; count does not increase."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline_with_fresh_entities(store, n_entities=2)

        source = "test://entity-accumulation"

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(
            _make_intake("content v1", source=source),
            content_cleaner=_strip_tags,
        )  # type: ignore[call-arg]
        count_after_first = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        await pipeline.ingest(
            _make_intake("content v2", source=source),
            content_cleaner=_strip_tags,
        )  # type: ignore[call-arg]
        count_after_second = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        assert count_after_first > 0  # entities were actually stored
        assert count_after_second == count_after_first  # no accumulation

    @pytest.mark.asyncio
    async def test_multiple_refresh_cycles_entity_count_stable(self) -> None:
        """Three refresh cycles with changing content produce the same entity count, not 3x."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline_with_fresh_entities(store, n_entities=1)

        source = "test://multi-refresh"

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(
            _make_intake("version one", source=source),
            content_cleaner=_strip_tags,
        )  # type: ignore[call-arg]
        await pipeline.ingest(
            _make_intake("version two", source=source),
            content_cleaner=_strip_tags,
        )  # type: ignore[call-arg]
        await pipeline.ingest(
            _make_intake("version three", source=source),
            content_cleaner=_strip_tags,
        )  # type: ignore[call-arg]

        total_entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        # Must equal 1 (from the last ingest cycle), not 3 (accumulated across all cycles)
        assert total_entities == 1

    @pytest.mark.asyncio
    async def test_edge_count_stable_after_refresh(self) -> None:
        """Edge count does not accumulate across re-ingest cycles."""
        conn = _make_db()
        store, _ = _make_store(conn)
        pipeline = _make_pipeline_with_fresh_entities(store, n_entities=2, n_edges=1)

        source = "test://edge-refresh"

        # Fails: content_cleaner kwarg not accepted
        await pipeline.ingest(
            _make_intake("edge content v1", source=source),
            content_cleaner=_strip_tags,
        )  # type: ignore[call-arg]
        edge_count_first = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        await pipeline.ingest(
            _make_intake("edge content v2", source=source),
            content_cleaner=_strip_tags,
        )  # type: ignore[call-arg]
        edge_count_second = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        assert edge_count_first > 0  # edges were actually stored
        assert edge_count_second == edge_count_first  # no accumulation
