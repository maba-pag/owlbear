"""RED-phase tests for untrusted content wrapping in mcp-knowledge URL intake (#735).

Tests the contract for:
  - owlbear_knowledge.content_safety: wrap_untrusted_content() sentinel-tag utility
  - owlbear_knowledge.ingest: IngestPipeline.ingest() wraps URL-sourced chunks pre-extraction
  - owlbear_knowledge.llm_extractor: LLM_EXTRACTION_PROMPT contains sentinel-aware data instruction

All 16 tests must FAIL at RED phase — content_safety module does not yet exist, ingest()
applies no wrapping, and LLM_EXTRACTION_PROMPT lacks sentinel instructions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# content_safety.py — wrap_untrusted_content
# ---------------------------------------------------------------------------


class TestFromAC_WrapUntrustedContent:
    """wrap_untrusted_content wraps text in <untrusted_web_content> sentinel tags (AC1, AC2)."""

    def test_wrap_untrusted_content_importable(self) -> None:
        """wrap_untrusted_content can be imported from owlbear_knowledge.content_safety."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content  # noqa: F401

    def test_wrap_returns_string(self) -> None:
        """wrap_untrusted_content returns a str."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content

        result = wrap_untrusted_content("some text")
        assert isinstance(result, str)

    def test_wrap_contains_open_sentinel_tag(self) -> None:
        """Result contains opening <untrusted_web_content ...> tag."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content

        assert "<untrusted_web_content" in wrap_untrusted_content("some text")

    def test_wrap_contains_close_sentinel_tag(self) -> None:
        """Result contains closing </untrusted_web_content> tag."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content

        assert "</untrusted_web_content>" in wrap_untrusted_content("some text")

    def test_original_text_preserved_inside_tags(self) -> None:
        """Original text appears between the open and close sentinel tags."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content

        original = "hello world content"
        result = wrap_untrusted_content(original)
        open_end = result.index(">")
        close_start = result.index("</untrusted_web_content>")
        inner = result[open_end + 1 : close_start]
        assert original in inner

    def test_source_url_attribute_in_open_tag(self) -> None:
        """When source_url is provided, the open tag contains the URL as an attribute."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content

        result = wrap_untrusted_content("text", source_url="https://example.com/page")
        # URL must appear within the opening tag (before the first '>')
        open_tag_end = result.index(">")
        assert "https://example.com/page" in result[:open_tag_end]

    def test_idempotency_guard_no_double_wrap(self) -> None:
        """Calling wrap_untrusted_content on already-wrapped text returns unchanged content."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content

        wrapped_once = wrap_untrusted_content("raw content")
        wrapped_twice = wrap_untrusted_content(wrapped_once)
        assert wrapped_twice == wrapped_once

    def test_empty_string_returns_empty(self) -> None:
        """wrap_untrusted_content with empty string returns empty string (no-op guard)."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content

        assert wrap_untrusted_content("") == ""


# ---------------------------------------------------------------------------
# ingest.py — IngestPipeline.ingest() URL-sourced wrapping (AC1, AC2, AC5)
# ---------------------------------------------------------------------------


class TestFromAC_IngestUrlWrapping:
    """ingest() wraps URL-sourced chunks in sentinel tags before extraction (per-chunk, URL only)."""

    @pytest.mark.asyncio
    async def test_url_sourced_ingest_wraps_chunk_before_extractor(self) -> None:
        """ingest() passes sentinel-wrapped text to extractor for URL-sourced content."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "raw web page content"
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
        assert "</untrusted_web_content>" in call_text
        assert chunk_text in call_text

    @pytest.mark.asyncio
    async def test_url_sourced_ingest_wraps_each_chunk_independently(self) -> None:
        """ingest() wraps every chunk for URL-sourced content (per-chunk, not whole-content)."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [
            Chunk(text="chunk A content", index=0),
            Chunk(text="chunk B content", index=1),
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
            content="chunk A content\n\nchunk B content",
            source="https://example.com/multi",
            metadata={"source_type": "url"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) == 2
        for call in calls:
            arg: str = call[0][0]
            assert "<untrusted_web_content" in arg
            assert "</untrusted_web_content>" in arg

    @pytest.mark.asyncio
    async def test_file_sourced_ingest_does_not_wrap_chunks(self) -> None:
        """ingest() does not sentinel-wrap chunks for file-sourced content (AC5)."""
        # Import gates this test: fails at RED phase because module doesn't exist yet
        from owlbear_knowledge.content_safety import wrap_untrusted_content  # noqa: F401

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
            source="/workspace/doc.md",
            metadata={"source_type": "file"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" not in call_text

    @pytest.mark.asyncio
    async def test_text_sourced_ingest_does_not_wrap_chunks(self) -> None:
        """ingest() does not sentinel-wrap chunks for text-sourced (inline) content (AC5)."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content  # noqa: F401

        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "inline text snippet"
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
            source="inline",
            metadata={"source_type": "text"},
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" not in call_text

    @pytest.mark.asyncio
    async def test_ingest_without_source_type_metadata_does_not_wrap(self) -> None:
        """ingest() does not sentinel-wrap when source_type is absent from metadata (AC5)."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content  # noqa: F401

        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline
        from owlbear_knowledge.intake import IntakeResult

        chunk_text = "mystery source text"
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
            source="mystery://source",
            metadata={},  # no source_type key
        )
        await pipeline.ingest(intake)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" not in call_text

    @pytest.mark.asyncio
    async def test_ingest_text_method_does_not_wrap_chunks(self) -> None:
        """ingest_text() is out of scope for sentinel wrapping — AC5 bookmark pipeline guard."""
        from owlbear_knowledge.content_safety import wrap_untrusted_content  # noqa: F401

        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline

        chunk_text = "bookmark extracted text"
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text=chunk_text, index=0)]

        mock_extractor = MagicMock(spec=EntityExtractor)
        mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

        doc_store = MagicMock()
        doc_store.store_chunks.return_value = ["cid-1"]
        doc_store.store_extractions.return_value = (0, 0)

        pipeline = IngestPipeline(
            document_store=doc_store,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )
        await pipeline.ingest_text(chunk_text)

        calls = mock_extractor.extract.call_args_list
        assert len(calls) >= 1
        call_text: str = calls[0][0][0]
        assert "<untrusted_web_content" not in call_text


# ---------------------------------------------------------------------------
# llm_extractor.py — LLM_EXTRACTION_PROMPT sentinel instruction (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_ExtractionPromptSentinel:
    """LLM_EXTRACTION_PROMPT instructs LLM to treat <untrusted_web_content> as data, not instructions (AC3)."""

    def test_llm_extraction_prompt_contains_sentinel_tag_name(self) -> None:
        """LLM_EXTRACTION_PROMPT references the untrusted_web_content sentinel tag."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        assert "untrusted_web_content" in LLM_EXTRACTION_PROMPT

    def test_llm_extraction_prompt_has_data_only_instruction(self) -> None:
        """LLM_EXTRACTION_PROMPT instructs LLM to treat sentinel content as data only, not as instructions."""
        from owlbear_knowledge.llm_extractor import LLM_EXTRACTION_PROMPT

        lower = LLM_EXTRACTION_PROMPT.lower()
        assert any(phrase in lower for phrase in ["data only", "not as instructions", "as data"])
