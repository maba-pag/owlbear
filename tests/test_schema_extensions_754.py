"""RED-phase tests for schema extensions (#754).

Tests the contract for:
1. AUTHENTICATED_WEB in SourceType enum
2. Corporate EntityType values: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
3. Corporate RelationType values: GOVERNS, SUPERSEDES_VERSION
4. SourcePage model with PageStatus enum (5 status values)
5. source_id FK column on documents table
6. Cascade delete: source → source_pages + documents → entities + edges + chunks + document_status

All tests fail (RED phase). No source edits permitted.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from owlbear_knowledge import init_db
from owlbear_knowledge.models import EntityType, RelationType, SourceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


# ===========================================================================
# AC 1 — AUTHENTICATED_WEB in SourceType
# ===========================================================================


class TestFromAC_SourceTypeAuthenticatedWeb:  # noqa: N801
    """SourceType enum must include AUTHENTICATED_WEB."""

    def test_source_type_authenticated_web_member_exists(self) -> None:
        assert hasattr(SourceType, "AUTHENTICATED_WEB")

    def test_source_type_authenticated_web_value_is_string(self) -> None:
        assert SourceType.AUTHENTICATED_WEB == "authenticated_web"

    def test_source_type_authenticated_web_is_str_enum(self) -> None:
        assert isinstance(SourceType.AUTHENTICATED_WEB, str)

    def test_source_type_from_string_authenticated_web(self) -> None:
        """StrEnum must round-trip from its string value."""
        assert SourceType("authenticated_web") is SourceType.AUTHENTICATED_WEB


# ===========================================================================
# AC 2 — Corporate EntityType values
# ===========================================================================


class TestFromAC_EntityTypeCorporate:  # noqa: N801
    """EntityType must include the five corporate document classification values."""

    @pytest.mark.parametrize(
        "member",
        ["REQUIREMENT", "SOLUTION", "PROCEDURE", "POLICY", "STANDARD"],
    )
    def test_entity_type_corporate_member_exists(self, member: str) -> None:
        assert hasattr(EntityType, member)

    @pytest.mark.parametrize(
        ("member", "expected_value"),
        [
            ("REQUIREMENT", "requirement"),
            ("SOLUTION", "solution"),
            ("PROCEDURE", "procedure"),
            ("POLICY", "policy"),
            ("STANDARD", "standard"),
        ],
    )
    def test_entity_type_corporate_value_matches(self, member: str, expected_value: str) -> None:
        assert EntityType[member] == expected_value

    @pytest.mark.parametrize(
        "expected_value",
        ["requirement", "solution", "procedure", "policy", "standard"],
    )
    def test_entity_type_corporate_round_trips_from_string(self, expected_value: str) -> None:
        assert EntityType(expected_value).value == expected_value


# ===========================================================================
# AC 3 — Corporate RelationType values
# ===========================================================================


class TestFromAC_RelationTypeCorporate:  # noqa: N801
    """RelationType must include GOVERNS and SUPERSEDES_VERSION."""

    def test_relation_type_governs_exists(self) -> None:
        assert hasattr(RelationType, "GOVERNS")

    def test_relation_type_governs_value(self) -> None:
        assert RelationType.GOVERNS == "governs"

    def test_relation_type_supersedes_version_exists(self) -> None:
        assert hasattr(RelationType, "SUPERSEDES_VERSION")

    def test_relation_type_supersedes_version_value(self) -> None:
        assert RelationType.SUPERSEDES_VERSION == "supersedes_version"

    def test_relation_type_governs_round_trips_from_string(self) -> None:
        assert RelationType("governs") is RelationType.GOVERNS

    def test_relation_type_supersedes_version_round_trips_from_string(self) -> None:
        assert RelationType("supersedes_version") is RelationType.SUPERSEDES_VERSION


# ===========================================================================
# AC 4 — SourcePage model and PageStatus enum
# ===========================================================================


class TestFromAC_SourcePageModel:  # noqa: N801
    """SourcePage model and PageStatus StrEnum must exist with correct fields/values."""

    def test_page_status_import(self) -> None:
        from owlbear_knowledge.models import PageStatus  # noqa: PLC0415

        assert PageStatus is not None

    @pytest.mark.parametrize(
        ("member", "expected_value"),
        [
            ("DISCOVERED", "discovered"),
            ("APPROVED", "approved"),
            ("REJECTED", "rejected"),
            ("INGESTED", "ingested"),
            ("STALE", "stale"),
        ],
    )
    def test_page_status_member_exists_and_value(self, member: str, expected_value: str) -> None:
        from owlbear_knowledge.models import PageStatus  # noqa: PLC0415

        assert hasattr(PageStatus, member)
        assert PageStatus[member] == expected_value

    def test_page_status_is_str_enum(self) -> None:
        from owlbear_knowledge.models import PageStatus  # noqa: PLC0415

        assert isinstance(PageStatus.DISCOVERED, str)

    def test_source_page_import(self) -> None:
        from owlbear_knowledge.models import SourcePage  # noqa: PLC0415

        assert SourcePage is not None

    def test_source_page_has_source_id_field(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        page = SourcePage(source_id="src-1", url="https://example.com/page", status=PageStatus.DISCOVERED)
        assert page.source_id == "src-1"

    def test_source_page_has_url_field(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        page = SourcePage(source_id="src-1", url="https://example.com/page", status=PageStatus.DISCOVERED)
        assert page.url == "https://example.com/page"

    def test_source_page_has_status_field(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        page = SourcePage(source_id="src-1", url="https://example.com/page", status=PageStatus.DISCOVERED)
        assert page.status == PageStatus.DISCOVERED

    def test_source_page_has_extraction_hash_field_nullable(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        page = SourcePage(source_id="src-1", url="https://example.com/page", status=PageStatus.DISCOVERED)
        assert page.extraction_hash is None

    def test_source_page_has_last_extracted_field_nullable(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        page = SourcePage(source_id="src-1", url="https://example.com/page", status=PageStatus.DISCOVERED)
        assert page.last_extracted is None

    def test_source_page_extraction_hash_can_be_set(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        page = SourcePage(
            source_id="src-1",
            url="https://example.com/page",
            status=PageStatus.INGESTED,
            extraction_hash="abc123",
        )
        assert page.extraction_hash == "abc123"

    def test_source_page_last_extracted_can_be_set(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        ts = _now()
        page = SourcePage(
            source_id="src-1",
            url="https://example.com/page",
            status=PageStatus.INGESTED,
            last_extracted=ts,
        )
        assert page.last_extracted == ts

    def test_source_page_has_auto_id(self) -> None:
        from owlbear_knowledge.models import PageStatus, SourcePage  # noqa: PLC0415

        page = SourcePage(source_id="src-1", url="https://example.com/", status=PageStatus.DISCOVERED)
        assert page.id is not None
        assert len(page.id) == 32  # uuid hex


# ===========================================================================
# AC 5 — source_id FK on documents table
# ===========================================================================


class TestFromAC_DocumentsSourceIdFK:  # noqa: N801
    """documents table must have a source_id column after init_db (v9)."""

    def test_documents_table_has_source_id_column(self) -> None:
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
        assert "source_id" in cols

    def test_schema_version_is_9_after_init_db(self) -> None:
        conn = _make_db()
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 9  # noqa: PLR2004

    def test_source_pages_table_exists_after_init_db(self) -> None:
        conn = _make_db()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='source_pages'"
        ).fetchone()
        assert row is not None

    def test_source_pages_table_has_source_id_column(self) -> None:
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()}
        assert "source_id" in cols

    def test_source_pages_table_has_url_column(self) -> None:
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()}
        assert "url" in cols

    def test_source_pages_table_has_status_column(self) -> None:
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()}
        assert "status" in cols

    def test_source_pages_table_has_extraction_hash_column(self) -> None:
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()}
        assert "extraction_hash" in cols

    def test_source_pages_table_has_last_extracted_column(self) -> None:
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()}
        assert "last_extracted" in cols


# ===========================================================================
# AC 6 — Cascade delete: source → source_pages + documents → downstream
# ===========================================================================


class TestFromAC_CascadeDelete:  # noqa: N801
    """Deleting a knowledge source must cascade to all downstream tables.

    Chain: source → source_pages (via source_id FK)
                  → documents (via source_id FK)
                     → entities, edges, chunks, document_status
    """

    def _seed_full_chain(self, conn: sqlite3.Connection) -> str:
        """Insert one source, one page, one document, and all downstream rows.

        Returns the source ID.
        """
        now = _now()
        source_id = "src-cascade-test"
        doc_id = "doc-cascade-test"
        entity_id = "ent-cascade-test"

        # source
        conn.execute(
            "INSERT INTO knowledge_sources"
            " (id, name, source_type, config, scope, enabled, priority, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (source_id, "cascade-source", "authenticated_web", "{}", "global", 1, 0, now, now),
        )
        # source_page
        conn.execute(
            "INSERT INTO source_pages (id, source_id, url, status) VALUES (?, ?, ?, ?)",
            ("page-1", source_id, "https://example.com/doc", "discovered"),
        )
        # document with source_id FK
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doc_id, "Cascade Doc", "body", "{}", now, "global", source_id),
        )
        # entity
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, description, metadata, created_at, scope, document_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entity_id, "CascadeEnt", "concept", "", "{}", now, "global", doc_id),
        )
        # edge (self-referencing for simplicity)
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, weight, metadata, created_at, scope)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("edge-1", entity_id, entity_id, "related_to", 1.0, "{}", now, "global"),
        )
        # chunk
        conn.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at, scope)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("chunk-1", doc_id, 0, "chunk body", "{}", now, "global"),
        )
        # document_status
        conn.execute(
            "INSERT INTO document_status (document_id, status, source, created_at, updated_at, scope)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, "complete", "https://example.com/doc", now, now, "global"),
        )
        conn.commit()
        return source_id

    def test_cascade_delete_removes_source_pages(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        # The cascade delete method must exist and remove source_pages
        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute("SELECT count(*) FROM source_pages WHERE source_id = ?", (source_id,)).fetchone()[0]
        assert count == 0

    def test_cascade_delete_removes_documents(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute("SELECT count(*) FROM documents WHERE source_id = ?", (source_id,)).fetchone()[0]
        assert count == 0

    def test_cascade_delete_removes_entities(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
        assert count == 0

    def test_cascade_delete_removes_edges(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert count == 0

    def test_cascade_delete_removes_chunks(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        assert count == 0

    def test_cascade_delete_removes_document_status(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute("SELECT count(*) FROM document_status").fetchone()[0]
        assert count == 0

    def test_cascade_delete_removes_source_row_itself(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute(
            "SELECT count(*) FROM knowledge_sources WHERE id = ?", (source_id,)
        ).fetchone()[0]
        assert count == 0

    def test_cascade_delete_nonexistent_source_returns_false(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        store = KnowledgeSourceStore(conn)
        result = store.delete_cascade("does-not-exist")
        assert result is False

    def test_cascade_delete_existing_source_returns_true(self) -> None:
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        store = KnowledgeSourceStore(conn)
        result = store.delete_cascade(source_id)
        assert result is True

    def test_cascade_delete_does_not_remove_unrelated_documents(self) -> None:
        """Only documents linked to the deleted source are removed."""
        from owlbear_knowledge.source_store import KnowledgeSourceStore  # noqa: PLC0415

        conn = _make_db()
        source_id = self._seed_full_chain(conn)

        # Insert a document NOT linked to the source
        now = _now()
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, scope)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            ("other-doc", "Unrelated", "body", "{}", now, "global"),
        )
        conn.commit()

        store = KnowledgeSourceStore(conn)
        store.delete_cascade(source_id)

        count = conn.execute("SELECT count(*) FROM documents WHERE id = 'other-doc'").fetchone()[0]
        assert count == 1
