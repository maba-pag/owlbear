"""Regression tests — Replace-on-change refresh semantics (#791, subtask of #775).

F1 regression isolation: ghost document bug — existing_id was unused in the
changed branch of IngestPipeline.ingest().  After fix, delete_document_data()
must be called with the prior document's ID before any new insertion.

AC coverage:
  AC1 — changed content triggers delete_document_data(existing_id) before insert
  AC2 — no ghost documents remain after content-change re-ingest (F1 regression)
  AC3 — unchanged content still skips (no delete, no re-ingest)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pipeline(doc_store: object) -> object:
    """Return an IngestPipeline wired to *doc_store* with minimal mock deps."""
    from owlbear_knowledge.chunker import Chunk
    from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
    from owlbear_knowledge.ingest import IngestPipeline

    mock_chunker = MagicMock()
    mock_chunker.chunk.return_value = [Chunk(text="content", index=0)]

    mock_extractor = MagicMock(spec=EntityExtractor)
    mock_extractor.extract = AsyncMock(return_value=ExtractionResult())

    return IngestPipeline(
        document_store=doc_store,
        entity_extractor=mock_extractor,
        text_chunker=mock_chunker,
    )


def _make_intake(content: str = "content", source: str = "https://example.com/doc") -> object:
    from owlbear_knowledge.intake import IntakeResult

    return IntakeResult(content=content, source=source, metadata={})


def _base_doc_store(*, changed: bool, existing_id: str | None) -> MagicMock:
    doc_store = MagicMock()
    doc_store.check_content_changed.return_value = (changed, existing_id)
    doc_store.store_chunks.return_value = ["cid-1"]
    doc_store.store_extractions.return_value = (0, 0)
    return doc_store


# ---------------------------------------------------------------------------
# AC1: delete_document_data(existing_id) called before insert when content changes
# ---------------------------------------------------------------------------


class TestFromAC_ReplaceOnChangeSemantics:
    """IngestPipeline.ingest() replace-on-change semantics (SC10 regression)."""

    # -- AC1: delete called with exact prior ID --------------------------------

    @pytest.mark.asyncio
    async def test_delete_called_with_exact_existing_id(self) -> None:
        """delete_document_data is called with the prior document's exact ID."""
        prior_id = "prior-doc-abc123"
        doc_store = _base_doc_store(changed=True, existing_id=prior_id)
        pipeline = _make_pipeline(doc_store)

        await pipeline.ingest(_make_intake())

        doc_store.delete_document_data.assert_called_once_with(prior_id)

    @pytest.mark.asyncio
    async def test_delete_precedes_insert_when_content_changes(self) -> None:
        """delete_document_data is called BEFORE insert_document in the change path."""
        call_order: list[str] = []
        prior_id = "prior-doc-xyz"
        doc_store = _base_doc_store(changed=True, existing_id=prior_id)
        doc_store.delete_document_data.side_effect = lambda *_: call_order.append("delete")
        doc_store.insert_document.side_effect = lambda *_, **__: call_order.append("insert")

        pipeline = _make_pipeline(doc_store)
        await pipeline.ingest(_make_intake())

        assert "delete" in call_order, "delete_document_data was never called"
        assert "insert" in call_order, "insert_document was never called"
        assert call_order.index("delete") < call_order.index("insert"), (
            f"expected delete before insert, got order: {call_order}"
        )

    @pytest.mark.asyncio
    async def test_new_document_no_prior_id_skips_delete(self) -> None:
        """When content changes but there is no prior document (existing_id=None), no delete fires."""
        doc_store = _base_doc_store(changed=True, existing_id=None)
        pipeline = _make_pipeline(doc_store)

        await pipeline.ingest(_make_intake())

        doc_store.delete_document_data.assert_not_called()

    # -- AC2: F1 regression — no ghost documents after content-change re-ingest ---

    @pytest.mark.asyncio
    async def test_f1_regression_ghost_doc_not_left_after_change(self) -> None:
        """F1 regression: re-ingest of changed content must delete the prior document record.

        Before the fix, existing_id was captured but never passed to
        delete_document_data(), leaving a ghost document in the store.
        """
        prior_id = "ghost-doc-f1"
        doc_store = _base_doc_store(changed=True, existing_id=prior_id)
        pipeline = _make_pipeline(doc_store)

        await pipeline.ingest(_make_intake(content="changed content"))

        # Prior document must be removed — no ghost
        doc_store.delete_document_data.assert_called_once_with(prior_id)
        # New document must be inserted
        doc_store.insert_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_back_to_back_changes_each_delete_own_prior(self) -> None:
        """Each re-ingest deletes its own prior document, not a shared or stale ID."""
        from owlbear_knowledge.chunker import Chunk
        from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
        from owlbear_knowledge.ingest import IngestPipeline

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [Chunk(text="updated", index=0)]
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

        prior_ids = ("prior-a", "prior-b")
        for pid in prior_ids:
            doc_store.check_content_changed.return_value = (True, pid)
            await pipeline.ingest(_make_intake())

        assert doc_store.delete_document_data.call_count == 2  # noqa: PLR2004
        actual_calls = [c.args[0] for c in doc_store.delete_document_data.call_args_list]
        assert actual_calls == list(prior_ids), f"expected deletes for {list(prior_ids)}, got {actual_calls}"

    @pytest.mark.asyncio
    async def test_change_path_returns_ok_status(self) -> None:
        """ingest() returns status='ok' after deleting the prior doc and inserting the new one."""
        from owlbear_knowledge.ingest import IngestResult

        doc_store = _base_doc_store(changed=True, existing_id="stale-id")
        pipeline = _make_pipeline(doc_store)

        result = await pipeline.ingest(_make_intake(content="updated content"))

        assert isinstance(result, IngestResult)
        assert result.status == "ok"

    # -- AC3: unchanged content skips — no delete, no re-ingest ---------------

    @pytest.mark.asyncio
    async def test_unchanged_content_returns_skipped(self) -> None:
        """ingest() returns status='skipped' when content has not changed."""
        from owlbear_knowledge.ingest import IngestResult

        existing_id = "existing-doc-unchanged"
        doc_store = _base_doc_store(changed=False, existing_id=existing_id)
        pipeline = _make_pipeline(doc_store)

        result = await pipeline.ingest(_make_intake())

        assert isinstance(result, IngestResult)
        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_unchanged_content_skips_delete(self) -> None:
        """delete_document_data is NOT called when content is unchanged."""
        doc_store = _base_doc_store(changed=False, existing_id="existing-abc")
        pipeline = _make_pipeline(doc_store)

        await pipeline.ingest(_make_intake())

        doc_store.delete_document_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_unchanged_content_skips_insert(self) -> None:
        """insert_document is NOT called when content is unchanged."""
        doc_store = _base_doc_store(changed=False, existing_id="existing-abc")
        pipeline = _make_pipeline(doc_store)

        await pipeline.ingest(_make_intake())

        doc_store.insert_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_unchanged_content_preserves_existing_document_id_in_result(self) -> None:
        """ingest() returns the existing document_id in the skipped result (no new allocation)."""
        existing_id = "preserved-doc-id"
        doc_store = _base_doc_store(changed=False, existing_id=existing_id)
        pipeline = _make_pipeline(doc_store)

        result = await pipeline.ingest(_make_intake())

        assert result.document_id == existing_id
