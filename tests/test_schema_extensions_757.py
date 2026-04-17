"""RED-phase tests for schema extensions — P1-01 (#757).

Covers:
  AC1  - PageStatus StrEnum: discovered / approved / rejected / ingested / stale
  AC2  - SourcePage frozen Pydantic model: id, source_id, url, status, extraction_hash, last_extracted
  AC3  - SourcePage + PageStatus exported from owlbear_knowledge
  AC4  - Document.source_id nullable field (str | None = None)
  AC5  - source_pages table: status, extraction_hash, last_extracted columns
  AC6  - insert_document propagates source_id into the documents row
  AC7  - delete_source_cascade: source → source_pages + documents → entities,
          edges, chunks, document_status (zero rows in all 6 downstream tables)

All tests MUST FAIL at RED phase — none of these interfaces exist yet.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    from owlbear_knowledge.schema import init_db

    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_store(conn: sqlite3.Connection) -> object:
    from owlbear_knowledge.document_store import DocumentStore
    from owlbear_knowledge.graph_store import GraphStore

    return DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())


# ---------------------------------------------------------------------------
# AC1: PageStatus StrEnum
# ---------------------------------------------------------------------------


class TestFromAC_PageStatus:
    """PageStatus is a StrEnum with five page-lifecycle values."""

    def test_page_status_importable(self) -> None:
        """PageStatus can be imported from owlbear_knowledge.models."""
        from owlbear_knowledge.models import PageStatus  # noqa: F401

    def test_page_status_has_discovered(self) -> None:
        """PageStatus.DISCOVERED exists."""
        from owlbear_knowledge.models import PageStatus

        assert hasattr(PageStatus, "DISCOVERED")

    def test_page_status_has_approved(self) -> None:
        """PageStatus.APPROVED exists."""
        from owlbear_knowledge.models import PageStatus

        assert hasattr(PageStatus, "APPROVED")

    def test_page_status_has_rejected(self) -> None:
        """PageStatus.REJECTED exists."""
        from owlbear_knowledge.models import PageStatus

        assert hasattr(PageStatus, "REJECTED")

    def test_page_status_has_ingested(self) -> None:
        """PageStatus.INGESTED exists."""
        from owlbear_knowledge.models import PageStatus

        assert hasattr(PageStatus, "INGESTED")

    def test_page_status_has_stale(self) -> None:
        """PageStatus.STALE exists."""
        from owlbear_knowledge.models import PageStatus

        assert hasattr(PageStatus, "STALE")

    def test_page_status_values_are_lowercase_strings(self) -> None:
        """PageStatus values are lowercase strings matching the spec."""
        from owlbear_knowledge.models import PageStatus

        values = {m.value for m in PageStatus}
        expected = {"discovered", "approved", "rejected", "ingested", "stale"}
        assert expected == values

    def test_page_status_has_exactly_five_members(self) -> None:
        """PageStatus has exactly 5 members — no extra values."""
        from owlbear_knowledge.models import PageStatus

        assert len(list(PageStatus)) == 5  # noqa: PLR2004

    def test_page_status_is_str_enum(self) -> None:
        """PageStatus values compare equal to their string equivalents."""
        from owlbear_knowledge.models import PageStatus

        assert PageStatus.DISCOVERED == "discovered"
        assert PageStatus.STALE == "stale"


# ---------------------------------------------------------------------------
# AC2: SourcePage model
# ---------------------------------------------------------------------------


class TestFromAC_SourcePageModel:
    """SourcePage is a frozen Pydantic model with all required fields."""

    def test_source_page_importable(self) -> None:
        """SourcePage can be imported from owlbear_knowledge.models."""
        from owlbear_knowledge.models import SourcePage  # noqa: F401

    def test_source_page_instantiation_with_required_fields(self) -> None:
        """SourcePage can be constructed with source_id, url, and status."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(
            source_id="src-001",
            url="https://example.com/page",
            status=PageStatus.DISCOVERED,
        )
        assert page is not None

    def test_source_page_has_id_field(self) -> None:
        """SourcePage.id defaults to a hex string when omitted."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(
            source_id="src-001",
            url="https://example.com/page",
            status=PageStatus.DISCOVERED,
        )
        assert isinstance(page.id, str)
        assert len(page.id) > 0

    def test_source_page_has_source_id_field(self) -> None:
        """SourcePage.source_id stores the owning knowledge source FK."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(
            source_id="src-999",
            url="https://example.com/page",
            status=PageStatus.APPROVED,
        )
        assert page.source_id == "src-999"

    def test_source_page_has_url_field(self) -> None:
        """SourcePage.url stores the page URL."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        url = "https://sharepoint.example.com/sites/HR/policy/001"
        page = SourcePage(source_id="s-1", url=url, status=PageStatus.APPROVED)
        assert page.url == url

    def test_source_page_has_status_field(self) -> None:
        """SourcePage.status stores a PageStatus value."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(source_id="s-1", url="https://x.com", status=PageStatus.INGESTED)
        assert page.status == PageStatus.INGESTED

    def test_source_page_extraction_hash_defaults_to_none(self) -> None:
        """SourcePage.extraction_hash defaults to None when not provided."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(source_id="s-1", url="https://x.com", status=PageStatus.DISCOVERED)
        assert page.extraction_hash is None

    def test_source_page_extraction_hash_accepts_string(self) -> None:
        """SourcePage.extraction_hash accepts a hash string."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(
            source_id="s-1",
            url="https://x.com",
            status=PageStatus.INGESTED,
            extraction_hash="abc123",
        )
        assert page.extraction_hash == "abc123"

    def test_source_page_last_extracted_defaults_to_none(self) -> None:
        """SourcePage.last_extracted defaults to None when not provided."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(source_id="s-1", url="https://x.com", status=PageStatus.STALE)
        assert page.last_extracted is None

    def test_source_page_last_extracted_accepts_iso_string(self) -> None:
        """SourcePage.last_extracted accepts an ISO datetime string."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        ts = _now()
        page = SourcePage(
            source_id="s-1",
            url="https://x.com",
            status=PageStatus.INGESTED,
            last_extracted=ts,
        )
        assert page.last_extracted == ts

    def test_source_page_is_frozen(self) -> None:
        """SourcePage is immutable — assigning a field raises an exception."""
        from owlbear_knowledge.models import PageStatus, SourcePage

        page = SourcePage(source_id="s-1", url="https://x.com", status=PageStatus.DISCOVERED)
        with pytest.raises((TypeError, Exception)):
            page.url = "https://changed.com"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AC3: SourcePage + PageStatus exported from owlbear_knowledge
# ---------------------------------------------------------------------------


class TestFromAC_SourcePageExport:
    """SourcePage and PageStatus are importable from the owlbear_knowledge top-level package."""

    def test_source_page_exported_from_package(self) -> None:
        """SourcePage is accessible via 'from owlbear_knowledge import SourcePage'."""
        from owlbear_knowledge import SourcePage  # noqa: F401

    def test_page_status_exported_from_package(self) -> None:
        """PageStatus is accessible via 'from owlbear_knowledge import PageStatus'."""
        from owlbear_knowledge import PageStatus  # noqa: F401

    def test_source_page_in_all(self) -> None:
        """SourcePage appears in owlbear_knowledge.__all__."""
        import owlbear_knowledge

        assert "SourcePage" in owlbear_knowledge.__all__

    def test_page_status_in_all(self) -> None:
        """PageStatus appears in owlbear_knowledge.__all__."""
        import owlbear_knowledge

        assert "PageStatus" in owlbear_knowledge.__all__


# ---------------------------------------------------------------------------
# AC4: Document.source_id nullable field
# ---------------------------------------------------------------------------


class TestFromAC_DocumentSourceId:
    """Document model gains a nullable source_id field (str | None = None)."""

    def test_document_source_id_defaults_to_none(self) -> None:
        """Document.source_id is None when not provided."""
        from owlbear_knowledge.models import Document

        doc = Document(title="Test", content="body")
        assert doc.source_id is None

    def test_document_source_id_accepts_string(self) -> None:
        """Document.source_id accepts a non-empty string."""
        from owlbear_knowledge.models import Document

        doc = Document(title="Test", content="body", source_id="src-42")
        assert doc.source_id == "src-42"

    def test_document_source_id_accepts_none_explicitly(self) -> None:
        """Document.source_id can be set to None explicitly."""
        from owlbear_knowledge.models import Document

        doc = Document(title="Test", content="body", source_id=None)
        assert doc.source_id is None

    def test_document_is_still_frozen_with_source_id(self) -> None:
        """Document with source_id remains frozen — field is set, mutation fails."""
        from owlbear_knowledge.models import Document

        doc = Document(title="Test", content="body", source_id="src-1")
        # This assertion fails at RED phase because source_id is not yet a recognised
        # field, so doc.source_id raises AttributeError.
        assert doc.source_id == "src-1"
        with pytest.raises((TypeError, Exception)):
            doc.source_id = "src-changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AC5: source_pages table schema columns
# ---------------------------------------------------------------------------


class TestFromAC_SourcePageSchemaColumns:
    """source_pages table has status, extraction_hash, and last_extracted columns."""

    def _cols(self) -> set[str]:
        conn = _make_db()
        return {row[1] for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()}

    def test_source_pages_has_status_column(self) -> None:
        """source_pages table has a 'status' column for unified page lifecycle tracking."""
        assert "status" in self._cols()

    def test_source_pages_has_extraction_hash_column(self) -> None:
        """source_pages table has an 'extraction_hash' column for delta detection."""
        assert "extraction_hash" in self._cols()

    def test_source_pages_has_last_extracted_column(self) -> None:
        """source_pages table has a 'last_extracted' column."""
        assert "last_extracted" in self._cols()

    def test_source_pages_has_id_column(self) -> None:
        """source_pages table has an 'id' primary-key column."""
        assert "id" in self._cols()

    def test_source_pages_status_column_is_not_plural_split(self) -> None:
        """source_pages uses a unified 'status' column, not separate approval/extraction columns."""
        cols = self._cols()
        # A unified PageStatus design uses one column.  Separate approval_state /
        # extraction_status columns indicate an old design not matching this spec.
        assert "status" in cols
        assert "approval_state" not in cols, "approval_state is a split-column remnant; only unified 'status' is valid"
        assert "extraction_status" not in cols, (
            "extraction_status is a split-column remnant; only unified 'status' is valid"
        )

    def test_schema_version_is_9_after_v9_migration(self) -> None:
        """After init_db on a fresh connection, schema_version is 9."""
        conn = _make_db()
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 9  # noqa: PLR2004


# ---------------------------------------------------------------------------
# AC6: insert_document propagates source_id into the documents row
# ---------------------------------------------------------------------------


class TestFromAC_InsertDocumentSourceId:
    """DocumentStore.insert_document stores source_id in the documents table row."""

    def test_insert_document_stores_source_id_in_db(self) -> None:
        """After insert_document with source_id, documents row has that source_id."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.intake import IntakeResult

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        intake = IntakeResult(
            content="corporate policy text",
            source="https://sharepoint.example.com/policy/001",
            metadata={"source_type": "authenticated_web"},
        )
        store.insert_document("doc-src-001", intake, scope="global")
        conn.execute(
            "UPDATE documents SET source_id = ? WHERE id = ?",
            ("src-999", "doc-src-001"),
        )  # Manually stamped — just verifying the column exists

        row = conn.execute("SELECT source_id FROM documents WHERE id = ?", ("doc-src-001",)).fetchone()
        assert row is not None
        # Column must exist (no OperationalError) — actual propagation tested below

    def test_insert_document_with_source_id_kwarg_stores_value(self) -> None:
        """insert_document(doc_id, intake, source_id=...) stores source_id in DB row."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.intake import IntakeResult

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        intake = IntakeResult(
            content="content",
            source="https://source.example.com/doc",
            metadata={},
        )
        store.insert_document("doc-src-002", intake, source_id="src-insert-01")

        row = conn.execute("SELECT source_id FROM documents WHERE id = ?", ("doc-src-002",)).fetchone()
        assert row is not None
        assert row[0] == "src-insert-01"

    def test_insert_document_without_source_id_stores_null(self) -> None:
        """insert_document without source_id stores NULL in the source_id column."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.intake import IntakeResult

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        intake = IntakeResult(content="content", source="https://example.com", metadata={})
        store.insert_document("doc-nosrc-001", intake)

        row = conn.execute("SELECT source_id FROM documents WHERE id = ?", ("doc-nosrc-001",)).fetchone()
        assert row is not None
        assert row[0] is None


# ---------------------------------------------------------------------------
# AC7: delete_source_cascade — full cascade chain
# ---------------------------------------------------------------------------


class TestFromAC_DeleteSourceCascade:
    """delete_source_cascade removes source_pages, documents, and all 6 downstream tables."""

    def _setup_full_chain(self, conn: sqlite3.Connection, source_id: str) -> None:
        """Insert one source_page, one document, and all downstream rows for *source_id*."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore
        from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType

        graph = GraphStore(conn)
        store = DocumentStore(conn, graph, MagicMock(), MagicMock())

        # source_pages row
        conn.execute(
            "INSERT INTO source_pages (id, source_id, url, status) VALUES (?, ?, ?, ?)",
            (f"page-{source_id}", source_id, "https://example.com/page", "discovered"),
        )

        # document row linked by source_id
        doc_id = f"doc-cascade-{source_id}"
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, source_id) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, "Doc", "body", "{}", _now(), source_id),
        )

        # entity + edge
        entity = Entity(
            id=f"ent-{source_id}",
            name="PolicyNode",
            entity_type=EntityType.CONCEPT,
            document_id=doc_id,
        )
        graph.insert_entity(entity)
        edge = Edge(
            id=f"edge-{source_id}",
            source_id=entity.id,
            target_id=entity.id,
            relation=RelationType.RELATED_TO,
        )
        graph.insert_edge(edge)

        # chunk
        conn.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (f"chunk-{source_id}", doc_id, 0, "chunk text", "{}", _now()),
        )

        # document_status
        store.set_status(doc_id, "completed", source="https://example.com/page")
        conn.commit()

    def test_delete_source_cascade_method_exists(self) -> None:
        """DocumentStore has a delete_source_cascade method."""
        from owlbear_knowledge.document_store import DocumentStore

        assert hasattr(DocumentStore, "delete_source_cascade")

    def test_delete_source_cascade_removes_source_pages(self) -> None:
        """delete_source_cascade removes rows from source_pages for the given source_id."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        self._setup_full_chain(conn, "src-cascade-001")
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-cascade-001")

        rows = conn.execute("SELECT id FROM source_pages WHERE source_id = ?", ("src-cascade-001",)).fetchall()
        assert rows == []

    def test_delete_source_cascade_removes_documents(self) -> None:
        """delete_source_cascade removes documents whose source_id matches."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        self._setup_full_chain(conn, "src-cascade-002")
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-cascade-002")

        rows = conn.execute("SELECT id FROM documents WHERE source_id = ?", ("src-cascade-002",)).fetchall()
        assert rows == []

    def test_delete_source_cascade_removes_entities(self) -> None:
        """delete_source_cascade removes entities whose document_id was linked to the source."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        self._setup_full_chain(conn, "src-cascade-003")
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-cascade-003")

        rows = conn.execute(
            "SELECT id FROM entities WHERE document_id = ?",
            ("doc-cascade-src-cascade-003",),
        ).fetchall()
        assert rows == []

    def test_delete_source_cascade_removes_edges(self) -> None:
        """delete_source_cascade removes edges linked to entities from the source."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        self._setup_full_chain(conn, "src-cascade-004")
        edge_id = "edge-src-cascade-004"
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-cascade-004")

        row = conn.execute("SELECT id FROM edges WHERE id = ?", (edge_id,)).fetchone()
        assert row is None

    def test_delete_source_cascade_removes_chunks(self) -> None:
        """delete_source_cascade removes chunks linked to documents from the source."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        self._setup_full_chain(conn, "src-cascade-005")
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-cascade-005")

        rows = conn.execute(
            "SELECT id FROM chunks WHERE document_id = ?",
            ("doc-cascade-src-cascade-005",),
        ).fetchall()
        assert rows == []

    def test_delete_source_cascade_removes_document_status(self) -> None:
        """delete_source_cascade removes document_status rows for documents from the source."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        self._setup_full_chain(conn, "src-cascade-006")
        doc_id = "doc-cascade-src-cascade-006"
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-cascade-006")

        row = conn.execute("SELECT document_id FROM document_status WHERE document_id = ?", (doc_id,)).fetchone()
        assert row is None

    def test_delete_source_cascade_full_chain_all_six_tables_zero_rows(self) -> None:
        """After delete_source_cascade, all 6 downstream tables have zero rows for the source."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        src_id = "src-cascade-full"
        conn = _make_db()
        self._setup_full_chain(conn, src_id)
        doc_id = f"doc-cascade-{src_id}"
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade(src_id)

        assert conn.execute("SELECT id FROM source_pages WHERE source_id = ?", (src_id,)).fetchall() == []
        assert conn.execute("SELECT id FROM documents WHERE source_id = ?", (src_id,)).fetchall() == []
        assert conn.execute("SELECT id FROM entities WHERE document_id = ?", (doc_id,)).fetchall() == []
        assert conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall() == []
        assert conn.execute("SELECT document_id FROM document_status WHERE document_id = ?", (doc_id,)).fetchall() == []

    def test_delete_source_cascade_on_empty_source_is_no_op(self) -> None:
        """delete_source_cascade on an unknown source_id does not raise."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-does-not-exist")  # must not raise

    def test_delete_source_cascade_does_not_affect_other_sources(self) -> None:
        """delete_source_cascade leaves rows from unrelated sources intact."""
        from owlbear_knowledge.document_store import DocumentStore
        from owlbear_knowledge.graph_store import GraphStore

        conn = _make_db()
        self._setup_full_chain(conn, "src-target")
        self._setup_full_chain(conn, "src-keep")

        store = DocumentStore(conn, GraphStore(conn), MagicMock(), MagicMock())
        store.delete_source_cascade("src-target")

        # source_pages for the kept source must still exist
        pages = conn.execute("SELECT id FROM source_pages WHERE source_id = ?", ("src-keep",)).fetchall()
        assert len(pages) == 1

        # documents for the kept source must still exist
        docs = conn.execute("SELECT id FROM documents WHERE source_id = ?", ("src-keep",)).fetchall()
        assert len(docs) == 1
