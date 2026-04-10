"""RED-phase tests for the Authenticated Content Pipeline (#751).

Covers all testable Python interfaces described in the brief's Outcomes and Approach:

  AC1  - SourceType.AUTHENTICATED_WEB enum value in models.py
  AC2  - Corporate entity types: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
  AC3  - Corporate relation types: GOVERNS, SUPERSEDES_VERSION
  AC4  - ContentFetcher protocol importable from owlbear_knowledge.protocol
  AC5  - IngestPipeline wraps AUTHENTICATED_WEB-sourced chunks in untrusted-content tags
  AC6  - Schema v9: source_pages table + source_id FK on documents
  AC7  - LLM_EXTRACTION_PROMPT includes corporate entity/relation types
  AC8  - ALLOWED_IMPORTS includes owlbear_browser and owlbear_mcp_browser entries

All tests MUST FAIL at RED phase — none of these interfaces exist yet.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# AC1-3: models.py — new enum values
# ---------------------------------------------------------------------------


class TestFromAC_AuthenticatedContentModels:
    """SourceType, EntityType, RelationType carry new corporate/browser values (AC1-3)."""

    def test_source_type_authenticated_web_exists(self) -> None:
        """SourceType.AUTHENTICATED_WEB is defined in models."""
        from owlbear_knowledge.models import SourceType

        assert hasattr(SourceType, "AUTHENTICATED_WEB")

    def test_source_type_authenticated_web_value(self) -> None:
        """SourceType.AUTHENTICATED_WEB has value 'authenticated_web'."""
        from owlbear_knowledge.models import SourceType

        assert SourceType.AUTHENTICATED_WEB == "authenticated_web"

    def test_authenticated_web_is_member_of_source_type(self) -> None:
        """SourceType.AUTHENTICATED_WEB appears when iterating SourceType members."""
        from owlbear_knowledge.models import SourceType

        values = [s.value for s in SourceType]
        assert "authenticated_web" in values

    def test_entity_type_requirement_exists(self) -> None:
        """EntityType.REQUIREMENT is defined for corporate knowledge extraction."""
        from owlbear_knowledge.models import EntityType

        assert hasattr(EntityType, "REQUIREMENT")

    def test_entity_type_solution_exists(self) -> None:
        """EntityType.SOLUTION is defined for corporate knowledge extraction."""
        from owlbear_knowledge.models import EntityType

        assert hasattr(EntityType, "SOLUTION")

    def test_entity_type_procedure_exists(self) -> None:
        """EntityType.PROCEDURE is defined for corporate knowledge extraction."""
        from owlbear_knowledge.models import EntityType

        assert hasattr(EntityType, "PROCEDURE")

    def test_entity_type_policy_exists(self) -> None:
        """EntityType.POLICY is defined for corporate knowledge extraction."""
        from owlbear_knowledge.models import EntityType

        assert hasattr(EntityType, "POLICY")

    def test_entity_type_standard_exists(self) -> None:
        """EntityType.STANDARD is defined for corporate knowledge extraction."""
        from owlbear_knowledge.models import EntityType

        assert hasattr(EntityType, "STANDARD")

    def test_corporate_entity_types_distinct_from_existing(self) -> None:
        """Corporate entity type values do not collide with existing EntityType values."""
        from owlbear_knowledge.models import EntityType

        existing = {"file", "function", "class_", "decision", "pattern", "concept"}
        corporate = {
            EntityType.REQUIREMENT.value,
            EntityType.SOLUTION.value,
            EntityType.PROCEDURE.value,
            EntityType.POLICY.value,
            EntityType.STANDARD.value,
        }
        assert not existing.intersection(corporate)

    def test_relation_type_governs_exists(self) -> None:
        """RelationType.GOVERNS is defined for corporate policy links."""
        from owlbear_knowledge.models import RelationType

        assert hasattr(RelationType, "GOVERNS")

    def test_relation_type_supersedes_version_exists(self) -> None:
        """RelationType.SUPERSEDES_VERSION is defined for document versioning."""
        from owlbear_knowledge.models import RelationType

        assert hasattr(RelationType, "SUPERSEDES_VERSION")


# ---------------------------------------------------------------------------
# AC4: protocol.py — ContentFetcher injection interface
# ---------------------------------------------------------------------------


class TestFromAC_AuthenticatedContentProtocol:
    """ContentFetcher protocol is importable and satisfies the injection contract (AC4)."""

    def test_content_fetcher_importable(self) -> None:
        """ContentFetcher can be imported from owlbear_knowledge.protocol."""
        from owlbear_knowledge.protocol import ContentFetcher  # noqa: F401

    def test_content_fetcher_is_runtime_checkable_protocol(self) -> None:
        """ContentFetcher is a runtime-checkable Protocol."""
        from typing import Protocol

        from owlbear_knowledge.protocol import ContentFetcher

        # A @runtime_checkable Protocol class is itself a subclass of Protocol
        assert issubclass(ContentFetcher, Protocol)

    def test_content_fetcher_has_fetch_method(self) -> None:
        """ContentFetcher defines a 'fetch' method."""
        from owlbear_knowledge.protocol import ContentFetcher

        assert hasattr(ContentFetcher, "fetch")

    def test_content_fetcher_fetch_accepts_url(self) -> None:
        """ContentFetcher.fetch accepts a url positional argument."""
        import inspect

        from owlbear_knowledge.protocol import ContentFetcher

        sig = inspect.signature(ContentFetcher.fetch)
        params = list(sig.parameters)
        assert "url" in params

    def test_content_fetcher_isinstance_duck_typing(self) -> None:
        """isinstance(obj, ContentFetcher) returns True for duck-typed objects with fetch (AC4)."""
        from owlbear_knowledge.protocol import ContentFetcher

        class _StubFetcher:
            async def fetch(self, url: str) -> str:  # noqa: ARG002
                return ""

        stub = _StubFetcher()
        assert isinstance(stub, ContentFetcher)


# ---------------------------------------------------------------------------
# AC5: ingest.py — AUTHENTICATED_WEB content wrapped pre-extraction
# ---------------------------------------------------------------------------


class TestFromAC_AuthenticatedContentSafety:
    """IngestPipeline wraps AUTHENTICATED_WEB chunks in sentinel tags (AC5)."""

    @pytest.mark.asyncio
    async def test_authenticated_web_sourced_ingest_wraps_chunk(self) -> None:
        """ingest() passes sentinel-wrapped text to extractor for authenticated_web content."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "corporate security policy content"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source="https://sharepoint.example.com/sites/Security/policy",
            metadata={"source_type": "authenticated_web"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" in call_text
        assert "</untrusted_web_content>" in call_text
        assert chunk_text in call_text

    @pytest.mark.asyncio
    async def test_authenticated_web_wrapping_includes_source_url_attribute(self) -> None:
        """ingest() includes the source URL as an attribute on the sentinel tag for authenticated_web."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "standard operating procedure"
        source_url = "https://sharepoint.example.com/sites/Ops/procedure"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source=source_url,
            metadata={"source_type": "authenticated_web"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert source_url in call_text

    @pytest.mark.asyncio
    async def test_authenticated_web_all_chunks_wrapped(self) -> None:
        """ingest() wraps every chunk for authenticated_web content, not just the first."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [
            Chunk(text="requirement section A", index=0),
            Chunk(text="requirement section B", index=1),
        ]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1", "cid-2"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content="requirement section A\n\nrequirement section B",
            source="https://sharepoint.example.com/requirements",
            metadata={"source_type": "authenticated_web"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) == 2
        for call in calls:
            arg: str = call[0][0]
            assert "<untrusted_web_content" in arg

    @pytest.mark.asyncio
    async def test_url_sourced_ingest_wraps_chunk(self) -> None:
        """ingest() still wraps source_type='url' chunks — regression guard on predicate set (AC5)."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "public website content"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source="https://example.com/page",
            metadata={"source_type": "url"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" in call_text

    @pytest.mark.asyncio
    async def test_file_glob_sourced_ingest_does_not_wrap_chunk(self) -> None:
        """ingest() does NOT wrap source_type='file_glob' chunks — negative boundary (AC5)."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "local file content"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source="/docs/design.md",
            metadata={"source_type": "file_glob"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" not in call_text

    @pytest.mark.asyncio
    async def test_none_source_type_does_not_wrap_chunk(self) -> None:
        """ingest() does NOT wrap when source_type is absent from metadata — boundary (AC5)."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "plain text content with no source type"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.check_content_changed.return_value = (True, None)
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        intake = IntakeResult(
            content=chunk_text,
            source="text://inline",
            metadata={},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" not in call_text


# ---------------------------------------------------------------------------
# AC6: schema.py — v9 migration (source_pages table + source_id FK on documents)
# ---------------------------------------------------------------------------


class TestFromAC_AuthenticatedContentSchema:
    """Schema v9 adds source_pages table and source_id FK on documents (AC6)."""

    def _make_conn(self) -> sqlite3.Connection:
        """Return an in-memory SQLite connection with schema initialized."""
        from owlbear_knowledge.schema import init_db

        conn = sqlite3.connect(":memory:")
        init_db(conn)
        return conn

    def test_schema_version_is_9_after_init(self) -> None:
        """init_db sets schema_version to 9."""
        conn = self._make_conn()
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 9  # noqa: PLR2004

    def test_init_db_creates_source_pages_table(self) -> None:
        """init_db creates the source_pages table."""
        conn = self._make_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='source_pages'"
        ).fetchone()
        assert row is not None

    def test_source_pages_has_source_id_column(self) -> None:
        """source_pages table has a source_id column for linking to knowledge_sources."""
        conn = self._make_conn()
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()
        }
        assert "source_id" in cols

    def test_source_pages_has_url_column(self) -> None:
        """source_pages table has a url column."""
        conn = self._make_conn()
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()
        }
        assert "url" in cols

    def test_source_pages_has_approval_state_column(self) -> None:
        """source_pages table tracks approval_state (discovered/approved/rejected)."""
        conn = self._make_conn()
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()
        }
        assert "approval_state" in cols

    def test_source_pages_has_extraction_status_column(self) -> None:
        """source_pages table tracks extraction_status (pending/ingested/stale)."""
        conn = self._make_conn()
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()
        }
        assert "extraction_status" in cols

    def test_documents_table_has_source_id_column(self) -> None:
        """documents table gains a source_id column in v9 (enables cascade delete)."""
        conn = self._make_conn()
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        assert "source_id" in cols

    def test_schema_v8_migrates_to_v9(self) -> None:
        """init_db migrates a v8 database to v9 adding source_pages and source_id."""
        conn = sqlite3.connect(":memory:")

        # Bootstrap a v8 schema manually without calling init_db fully
        conn.execute(
            "CREATE TABLE schema_version (version INTEGER, applied_at TEXT)"
        )
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (8, '2026-01-01')"
        )
        conn.execute(
            "CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT, content TEXT, "
            "metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
        )
        conn.commit()

        from owlbear_knowledge.schema import init_db

        init_db(conn)

        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 9  # noqa: PLR2004

        page_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='source_pages'"
        ).fetchone()
        assert page_table is not None


# ---------------------------------------------------------------------------
# AC7: llm_extractor.py — corporate types in extraction prompt
# ---------------------------------------------------------------------------


class TestFromAC_AuthenticatedContentExtractionPrompt:
    """LLM_EXTRACTION_PROMPT contains corporate entity and relation type guidance (AC7)."""

    def test_extraction_prompt_includes_requirement_entity_type(self) -> None:
        """LLM_EXTRACTION_PROMPT lists 'requirement' as an entity type."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "requirement" in LLM_EXTRACTION_PROMPT.lower()

    def test_extraction_prompt_includes_solution_entity_type(self) -> None:
        """LLM_EXTRACTION_PROMPT lists 'solution' as an entity type."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "solution" in LLM_EXTRACTION_PROMPT.lower()

    def test_extraction_prompt_includes_procedure_entity_type(self) -> None:
        """LLM_EXTRACTION_PROMPT lists 'procedure' as an entity type."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "procedure" in LLM_EXTRACTION_PROMPT.lower()

    def test_extraction_prompt_includes_policy_entity_type(self) -> None:
        """LLM_EXTRACTION_PROMPT lists 'policy' as an entity type."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "policy" in LLM_EXTRACTION_PROMPT.lower()

    def test_extraction_prompt_includes_standard_entity_type(self) -> None:
        """LLM_EXTRACTION_PROMPT lists 'standard' as an entity type."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "standard" in LLM_EXTRACTION_PROMPT.lower()

    def test_extraction_prompt_includes_governs_relation_type(self) -> None:
        """LLM_EXTRACTION_PROMPT lists 'governs' as a relation type."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "governs" in LLM_EXTRACTION_PROMPT.lower()

    def test_extraction_prompt_includes_supersedes_version_relation_type(self) -> None:
        """LLM_EXTRACTION_PROMPT lists 'supersedes_version' as a relation type (AC7)."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "supersedes_version" in LLM_EXTRACTION_PROMPT.lower()


# ---------------------------------------------------------------------------
# AC8: test_package_boundary.py — ALLOWED_IMPORTS entries for browser packages
# ---------------------------------------------------------------------------


class TestFromAC_AuthenticatedContentPackageBoundaries:
    """ALLOWED_IMPORTS covers owlbear_browser and owlbear_mcp_browser namespaces (AC8)."""

    def test_owlbear_browser_in_allowed_imports(self) -> None:
        """ALLOWED_IMPORTS contains an entry for owlbear_browser."""
        from tests.test_package_boundary import ALLOWED_IMPORTS

        assert "owlbear_browser" in ALLOWED_IMPORTS

    def test_owlbear_mcp_browser_in_allowed_imports(self) -> None:
        """ALLOWED_IMPORTS contains an entry for owlbear_mcp_browser."""
        from tests.test_package_boundary import ALLOWED_IMPORTS

        assert "owlbear_mcp_browser" in ALLOWED_IMPORTS

    def test_owlbear_browser_is_foundation_layer(self) -> None:
        """owlbear_browser has no owlbear-namespace cross-deps (foundation layer)."""
        from tests.test_package_boundary import ALLOWED_IMPORTS

        assert ALLOWED_IMPORTS.get("owlbear_browser") == set()

    def test_owlbear_mcp_browser_may_only_import_owlbear_browser(self) -> None:
        """owlbear_mcp_browser is permitted to import owlbear_browser only."""
        from tests.test_package_boundary import ALLOWED_IMPORTS

        assert ALLOWED_IMPORTS.get("owlbear_mcp_browser") == {"owlbear_browser"}

    def test_owlbear_browser_package_importable(self) -> None:
        """owlbear_browser package exists at serve/browser/ and is importable."""
        import owlbear_browser  # type: ignore[import-not-found]  # noqa: F401
