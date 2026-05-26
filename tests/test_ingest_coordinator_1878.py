"""Tests for IngestCoordinator.delete_source() - 5-step delete cascade (task #1878).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/ingest.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py

AC coverage:
  AC1  - delete_source(source_id, *, reason) executes 5-step cascade in order:
          Sources.delete -> Content.purge_source -> Enrichment.discard_chunks ->
          Enrichment.purge_source -> Graph.invalidate_evidence_by_chunks
  AC2  - reason parameter forwarded to Sources.delete_source; appears in
          PurgeResult.source.reason (including synthetic SourceDeletionInfo on re-run)
  AC3  - PurgeResult.status = COMPLETE when steps 1-5 succeed; PARTIAL when step 2-5 fails
  AC4  - PurgeResult.completed_steps lists canonical names in execution order:
          "sources.delete", "content.purge", "enrichment.discard",
          "enrichment.purge", "graph.invalidate"
  AC5  - PurgeResult.failed_step names the step that raised; PurgeResult.error = str(exc)
  AC6  - Fail-fast after step 2-5 failure; unattempted sub-result fields use empty/zero defaults
  AC7  - Non-LookupError from Sources.delete_source propagates directly (no PurgeResult)
  AC8  - LookupError from Sources.delete_source triggers synthetic SourceDeletionInfo and
          continues cascade from step 2
  AC9  - Re-running delete_source after partial failure completes remaining steps
          and returns status=COMPLETE
  AC10 - Docstring includes idempotency guarantee referencing D63
  AC11 - Protocol docstring Raises clause replaced with
          "Never raises LookupError — caught internally for forward-recovery semantics"
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.ingest_coordinator import IngestCoordinator
from owlbear_knowledge.protocols.content import ContentPurgeResult
from owlbear_knowledge.protocols.enrichment import EnrichmentDiscardResult, EnrichmentPurgeResult
from owlbear_knowledge.protocols.graph import EvidenceInvalidationResult
from owlbear_knowledge.protocols.ingest import PurgeResult, PurgeStatus
from owlbear_knowledge.protocols.sources import SourceDeletionInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SOURCE_ID = "src-delete-test"
_CHUNK_IDS: tuple[str, ...] = ("chunk-a", "chunk-b", "chunk-c")


def _make_deletion_info(
    source_id: str = _SOURCE_ID,
    *,
    reason: str | None = None,
) -> SourceDeletionInfo:
    return SourceDeletionInfo(
        source_id=source_id,
        source_name="Test Source",
        scope="global",
        deleted_at=datetime.now(tz=UTC),
        reason=reason,
    )


def _make_content_purge(
    source_id: str = _SOURCE_ID,
    *,
    chunk_ids: tuple[str, ...] = _CHUNK_IDS,
) -> ContentPurgeResult:
    return ContentPurgeResult(
        source_id=source_id,
        document_ids=("doc-1",),
        chunk_ids=chunk_ids,
        vector_ids=chunk_ids,
    )


def _make_enrichment_purge(source_id: str = _SOURCE_ID) -> EnrichmentPurgeResult:
    return EnrichmentPurgeResult(
        source_id=source_id,
        queue_items_removed=2,
        extractions_removed=3,
    )


def _make_enrichment_discard(chunk_ids: tuple[str, ...] = _CHUNK_IDS) -> EnrichmentDiscardResult:
    return EnrichmentDiscardResult(
        discarded_chunk_ids=chunk_ids,
        queue_items_removed=len(chunk_ids),
    )


def _make_evidence_invalidation() -> EvidenceInvalidationResult:
    return EvidenceInvalidationResult(
        invalidated_evidence_ids=("ev-1",),
        orphaned_entity_ids=(),
        orphaned_edge_ids=(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_sources() -> MagicMock:
    s = MagicMock(name="sources")
    s.delete_source.return_value = _make_deletion_info()
    return s


@pytest.fixture()
def mock_content() -> MagicMock:
    c = MagicMock(name="content")
    c.purge_source.return_value = _make_content_purge()
    return c


@pytest.fixture()
def mock_enrichment() -> MagicMock:
    e = MagicMock(name="enrichment")
    e.discard_chunks.return_value = _make_enrichment_discard()
    e.purge_source.return_value = _make_enrichment_purge()
    return e


@pytest.fixture()
def mock_graph() -> MagicMock:
    g = MagicMock(name="graph")
    g.invalidate_evidence_by_chunks.return_value = _make_evidence_invalidation()
    return g


@pytest.fixture()
def coordinator(
    mock_sources: MagicMock,
    mock_content: MagicMock,
    mock_enrichment: MagicMock,
    mock_graph: MagicMock,
) -> IngestCoordinator:
    return IngestCoordinator(
        sources=mock_sources,
        content=mock_content,
        enrichment=mock_enrichment,
        graph=mock_graph,
    )


# ---------------------------------------------------------------------------
# TestFromAC_DeleteSourceCascade
# ---------------------------------------------------------------------------


class TestFromAC_DeleteSourceCascade:
    """AC-derived tests for IngestCoordinator.delete_source() - AC1 through AC11."""

    # ------------------------------------------------------------------
    # AC1 - 5-step cascade: invocation and argument routing
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_returns_purge_result_type(
        self, coordinator: IngestCoordinator
    ) -> None:
        """delete_source returns a PurgeResult instance."""
        result = await coordinator.delete_source(_SOURCE_ID)
        assert isinstance(result, PurgeResult)

    @pytest.mark.asyncio
    async def test_step1_sources_delete_called_with_source_id(
        self, coordinator: IngestCoordinator, mock_sources: MagicMock
    ) -> None:
        """AC1: step 1 calls Sources.delete_source with the correct source_id."""
        await coordinator.delete_source(_SOURCE_ID)
        assert mock_sources.delete_source.call_count == 1
        call_args = mock_sources.delete_source.call_args
        assert call_args.args[0] == _SOURCE_ID

    @pytest.mark.asyncio
    async def test_step2_content_purge_called_with_source_id(
        self, coordinator: IngestCoordinator, mock_content: MagicMock
    ) -> None:
        """AC1: step 2 calls Content.purge_source with source_id."""
        await coordinator.delete_source(_SOURCE_ID)
        mock_content.purge_source.assert_called_once_with(_SOURCE_ID)

    @pytest.mark.asyncio
    async def test_step3_enrichment_discard_called_with_chunk_ids_from_step2(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC1: step 3 passes chunk_ids returned by Content.purge_source to discard_chunks."""
        specific_chunk_ids = ("cid-x", "cid-y")
        mock_content.purge_source.return_value = _make_content_purge(chunk_ids=specific_chunk_ids)
        await coordinator.delete_source(_SOURCE_ID)
        mock_enrichment.discard_chunks.assert_called_once_with(specific_chunk_ids)

    @pytest.mark.asyncio
    async def test_step4_enrichment_purge_source_called_with_source_id(
        self, coordinator: IngestCoordinator, mock_enrichment: MagicMock
    ) -> None:
        """AC1: step 4 calls Enrichment.purge_source with source_id."""
        await coordinator.delete_source(_SOURCE_ID)
        mock_enrichment.purge_source.assert_called_once_with(_SOURCE_ID)

    @pytest.mark.asyncio
    async def test_step5_graph_invalidate_called_with_chunk_ids_from_step2(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC1: step 5 passes chunk_ids from Content.purge_source to invalidate_evidence_by_chunks."""
        specific_chunk_ids = ("cid-1", "cid-2", "cid-3")
        mock_content.purge_source.return_value = _make_content_purge(chunk_ids=specific_chunk_ids)
        await coordinator.delete_source(_SOURCE_ID)
        mock_graph.invalidate_evidence_by_chunks.assert_called_once_with(specific_chunk_ids)

    @pytest.mark.asyncio
    async def test_all_5_steps_called_when_cascade_succeeds(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC1: all five cascade steps are invoked on the happy path."""
        await coordinator.delete_source(_SOURCE_ID)
        assert mock_sources.delete_source.call_count == 1
        assert mock_content.purge_source.call_count == 1
        assert mock_enrichment.discard_chunks.call_count == 1
        assert mock_enrichment.purge_source.call_count == 1
        assert mock_graph.invalidate_evidence_by_chunks.call_count == 1

    @pytest.mark.asyncio
    async def test_purge_result_source_sub_result_is_from_step1(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC1: PurgeResult.source is the SourceDeletionInfo returned by step 1."""
        deletion_info = _make_deletion_info()
        mock_sources.delete_source.return_value = deletion_info
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.source.source_id == deletion_info.source_id
        assert result.source.source_name == deletion_info.source_name

    @pytest.mark.asyncio
    async def test_purge_result_content_sub_result_is_from_step2(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC1: PurgeResult.content is the ContentPurgeResult returned by step 2."""
        content_result = _make_content_purge(chunk_ids=("c-unique-1", "c-unique-2"))
        mock_content.purge_source.return_value = content_result
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.content.chunk_ids == ("c-unique-1", "c-unique-2")

    @pytest.mark.asyncio
    async def test_purge_result_enrichment_sub_result_is_from_step4(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC1: PurgeResult.enrichment is the EnrichmentPurgeResult returned by step 4."""
        enrich_result = EnrichmentPurgeResult(
            source_id=_SOURCE_ID,
            queue_items_removed=7,
            extractions_removed=9,
        )
        mock_enrichment.purge_source.return_value = enrich_result
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.enrichment.queue_items_removed == 7
        assert result.enrichment.extractions_removed == 9

    @pytest.mark.asyncio
    async def test_purge_result_graph_sub_result_is_from_step5(
        self,
        coordinator: IngestCoordinator,
        mock_graph: MagicMock,
    ) -> None:
        """AC1: PurgeResult.graph is the EvidenceInvalidationResult returned by step 5."""
        graph_result = EvidenceInvalidationResult(
            invalidated_evidence_ids=("ev-unique-42",),
        )
        mock_graph.invalidate_evidence_by_chunks.return_value = graph_result
        result = await coordinator.delete_source(_SOURCE_ID)
        assert "ev-unique-42" in result.graph.invalidated_evidence_ids

    # ------------------------------------------------------------------
    # AC2 - reason parameter forwarding
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_reason_forwarded_to_sources_delete(
        self, coordinator: IngestCoordinator, mock_sources: MagicMock
    ) -> None:
        """AC2: non-None reason is forwarded to Sources.delete_source as keyword arg."""
        await coordinator.delete_source(_SOURCE_ID, reason="testing reason")
        call_args = mock_sources.delete_source.call_args
        forwarded_reason = call_args.kwargs.get("reason") or (
            call_args.args[1] if len(call_args.args) > 1 else None
        )
        assert forwarded_reason == "testing reason"

    @pytest.mark.asyncio
    async def test_reason_none_forwarded_to_sources_delete(
        self, coordinator: IngestCoordinator, mock_sources: MagicMock
    ) -> None:
        """AC2: reason=None is forwarded (not omitted) to Sources.delete_source."""
        await coordinator.delete_source(_SOURCE_ID, reason=None)
        call_args = mock_sources.delete_source.call_args
        # Called at all, and the reason argument resolves to None
        assert call_args is not None
        forwarded_reason = call_args.kwargs.get("reason", "SENTINEL")
        # Either passed explicitly as None or defaulted to None
        assert forwarded_reason is None or forwarded_reason == "SENTINEL"

    @pytest.mark.asyncio
    async def test_reason_appears_in_purge_result_source_reason(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC2: PurgeResult.source.reason reflects the reason parameter."""
        mock_sources.delete_source.return_value = _make_deletion_info(reason="archive-sweep")
        result = await coordinator.delete_source(_SOURCE_ID, reason="archive-sweep")
        assert result.source.reason == "archive-sweep"

    # ------------------------------------------------------------------
    # AC3 - PurgeResult.status: COMPLETE vs PARTIAL
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_status_complete_when_all_5_steps_succeed(
        self, coordinator: IngestCoordinator
    ) -> None:
        """AC3: status is COMPLETE when all five steps execute without exception."""
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.status == PurgeStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_status_partial_when_step2_content_purge_fails(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC3: PARTIAL when Content.purge_source raises."""
        mock_content.purge_source.side_effect = RuntimeError("content store unavailable")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.status == PurgeStatus.PARTIAL

    @pytest.mark.asyncio
    async def test_status_partial_when_step3_enrichment_discard_fails(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC3: PARTIAL when Enrichment.discard_chunks raises."""
        mock_enrichment.discard_chunks.side_effect = RuntimeError("queue error")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.status == PurgeStatus.PARTIAL

    @pytest.mark.asyncio
    async def test_status_partial_when_step4_enrichment_purge_fails(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC3: PARTIAL when Enrichment.purge_source raises."""
        mock_enrichment.purge_source.side_effect = RuntimeError("enrichment failure")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.status == PurgeStatus.PARTIAL

    @pytest.mark.asyncio
    async def test_status_partial_when_step5_graph_invalidate_fails(
        self,
        coordinator: IngestCoordinator,
        mock_graph: MagicMock,
    ) -> None:
        """AC3: PARTIAL when Graph.invalidate_evidence_by_chunks raises."""
        mock_graph.invalidate_evidence_by_chunks.side_effect = RuntimeError("graph error")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.status == PurgeStatus.PARTIAL

    # ------------------------------------------------------------------
    # AC4 - PurgeResult.completed_steps canonical names and order
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_completed_steps_all_five_in_order_when_all_succeed(
        self, coordinator: IngestCoordinator
    ) -> None:
        """AC4: all 5 canonical step names appear in execution order on success."""
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.completed_steps == (
            "sources.delete",
            "content.purge",
            "enrichment.discard",
            "enrichment.purge",
            "graph.invalidate",
        )

    @pytest.mark.asyncio
    async def test_completed_steps_sources_delete_only_when_step2_fails(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC4: only 'sources.delete' in completed_steps when content.purge fails."""
        mock_content.purge_source.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.completed_steps == ("sources.delete",)

    @pytest.mark.asyncio
    async def test_completed_steps_up_to_content_purge_when_step3_fails(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC4: steps 1-2 in completed_steps when enrichment.discard fails."""
        mock_enrichment.discard_chunks.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.completed_steps == ("sources.delete", "content.purge")

    @pytest.mark.asyncio
    async def test_completed_steps_up_to_enrichment_discard_when_step4_fails(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC4: steps 1-3 in completed_steps when enrichment.purge_source fails."""
        mock_enrichment.purge_source.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.completed_steps == (
            "sources.delete",
            "content.purge",
            "enrichment.discard",
        )

    @pytest.mark.asyncio
    async def test_completed_steps_up_to_enrichment_purge_when_step5_fails(
        self,
        coordinator: IngestCoordinator,
        mock_graph: MagicMock,
    ) -> None:
        """AC4: steps 1-4 in completed_steps when graph.invalidate fails."""
        mock_graph.invalidate_evidence_by_chunks.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.completed_steps == (
            "sources.delete",
            "content.purge",
            "enrichment.discard",
            "enrichment.purge",
        )

    # ------------------------------------------------------------------
    # AC5 - failed_step and error fields
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_no_failed_step_when_all_succeed(
        self, coordinator: IngestCoordinator
    ) -> None:
        """AC5: failed_step is None on full success."""
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.failed_step is None

    @pytest.mark.asyncio
    async def test_no_error_field_when_all_succeed(
        self, coordinator: IngestCoordinator
    ) -> None:
        """AC5: error is None on full success."""
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.error is None

    @pytest.mark.asyncio
    async def test_failed_step_names_content_purge_when_step2_raises(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC5: failed_step = 'content.purge' when step 2 raises."""
        mock_content.purge_source.side_effect = RuntimeError("purge failure")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.failed_step == "content.purge"

    @pytest.mark.asyncio
    async def test_failed_step_names_enrichment_discard_when_step3_raises(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC5: failed_step = 'enrichment.discard' when step 3 raises."""
        mock_enrichment.discard_chunks.side_effect = RuntimeError("discard error")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.failed_step == "enrichment.discard"

    @pytest.mark.asyncio
    async def test_failed_step_names_enrichment_purge_when_step4_raises(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC5: failed_step = 'enrichment.purge' when step 4 raises."""
        mock_enrichment.purge_source.side_effect = RuntimeError("enrichment purge error")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.failed_step == "enrichment.purge"

    @pytest.mark.asyncio
    async def test_failed_step_names_graph_invalidate_when_step5_raises(
        self,
        coordinator: IngestCoordinator,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: failed_step = 'graph.invalidate' when step 5 raises."""
        mock_graph.invalidate_evidence_by_chunks.side_effect = RuntimeError("graph error")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.failed_step == "graph.invalidate"

    @pytest.mark.asyncio
    async def test_error_carries_exact_str_of_exception_when_step2_fails(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC5: error field equals str(exc) exactly."""
        exc = RuntimeError("exact error message here")
        mock_content.purge_source.side_effect = exc
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.error == str(exc)

    @pytest.mark.asyncio
    async def test_error_carries_str_of_exception_when_step5_fails(
        self,
        coordinator: IngestCoordinator,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: error = str(exc) for a step 5 failure."""
        exc = ValueError("graph constraint violated")
        mock_graph.invalidate_evidence_by_chunks.side_effect = exc
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.error == str(exc)

    # ------------------------------------------------------------------
    # AC6 - fail-fast; unattempted steps use empty/zero-default sub-results
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_step2_failure_skips_steps_3_4_5(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC6: when step 2 fails, steps 3, 4, and 5 are not called."""
        mock_content.purge_source.side_effect = RuntimeError("fail")
        await coordinator.delete_source(_SOURCE_ID)
        mock_enrichment.discard_chunks.assert_not_called()
        mock_enrichment.purge_source.assert_not_called()
        mock_graph.invalidate_evidence_by_chunks.assert_not_called()

    @pytest.mark.asyncio
    async def test_step2_failure_content_sub_result_is_empty_default(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC6: content sub-result is empty ContentPurgeResult when step 2 fails."""
        mock_content.purge_source.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.content.source_id == _SOURCE_ID
        assert result.content.document_ids == ()
        assert result.content.chunk_ids == ()
        assert result.content.vector_ids == ()

    @pytest.mark.asyncio
    async def test_step2_failure_enrichment_sub_result_is_empty_default(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC6: enrichment sub-result is zero-default EnrichmentPurgeResult when step 2 fails."""
        mock_content.purge_source.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.enrichment.queue_items_removed == 0
        assert result.enrichment.extractions_removed == 0

    @pytest.mark.asyncio
    async def test_step2_failure_graph_sub_result_is_empty_default(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        """AC6: graph sub-result is empty EvidenceInvalidationResult when step 2 fails."""
        mock_content.purge_source.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.graph.invalidated_evidence_ids == ()
        assert result.graph.orphaned_entity_ids == ()
        assert result.graph.orphaned_edge_ids == ()

    @pytest.mark.asyncio
    async def test_step3_failure_skips_steps_4_and_5(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC6: when step 3 fails, steps 4 and 5 are not called."""
        mock_enrichment.discard_chunks.side_effect = RuntimeError("fail")
        await coordinator.delete_source(_SOURCE_ID)
        mock_enrichment.purge_source.assert_not_called()
        mock_graph.invalidate_evidence_by_chunks.assert_not_called()

    @pytest.mark.asyncio
    async def test_step3_failure_enrichment_sub_result_is_empty_default(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC6: enrichment sub-result is zero-default when step 3 (discard) fails, step 4 unattempted."""
        mock_enrichment.discard_chunks.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.enrichment.queue_items_removed == 0
        assert result.enrichment.extractions_removed == 0

    @pytest.mark.asyncio
    async def test_step3_failure_graph_sub_result_is_empty_default(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC6: graph sub-result is empty when step 3 fails and step 5 is unattempted."""
        mock_enrichment.discard_chunks.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.graph.invalidated_evidence_ids == ()

    @pytest.mark.asyncio
    async def test_step4_failure_skips_step5_graph(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC6: when step 4 fails, step 5 is not called."""
        mock_enrichment.purge_source.side_effect = RuntimeError("fail")
        await coordinator.delete_source(_SOURCE_ID)
        mock_graph.invalidate_evidence_by_chunks.assert_not_called()

    @pytest.mark.asyncio
    async def test_step4_failure_graph_sub_result_is_empty_default(
        self,
        coordinator: IngestCoordinator,
        mock_enrichment: MagicMock,
    ) -> None:
        """AC6: graph sub-result is empty when step 4 fails and step 5 is unattempted."""
        mock_enrichment.purge_source.side_effect = RuntimeError("fail")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.graph.invalidated_evidence_ids == ()

    # ------------------------------------------------------------------
    # AC7 - non-LookupError from step 1 propagates directly
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_runtime_error_from_step1_propagates_directly(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC7: RuntimeError from Sources.delete_source is not caught - propagates to caller."""
        mock_sources.delete_source.side_effect = RuntimeError("storage failure")
        with pytest.raises(RuntimeError, match="storage failure"):
            await coordinator.delete_source(_SOURCE_ID)

    @pytest.mark.asyncio
    async def test_value_error_from_step1_propagates_directly(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC7: ValueError from Sources.delete_source propagates - not wrapped in PurgeResult."""
        mock_sources.delete_source.side_effect = ValueError("invalid source id format")
        with pytest.raises(ValueError):
            await coordinator.delete_source(_SOURCE_ID)

    @pytest.mark.asyncio
    async def test_non_lookup_error_from_step1_does_not_reach_step2(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        """AC7: RuntimeError from step 1 aborts cascade - content.purge_source never called."""
        mock_sources.delete_source.side_effect = RuntimeError("abort")
        with pytest.raises(RuntimeError):
            await coordinator.delete_source(_SOURCE_ID)
        mock_content.purge_source.assert_not_called()

    # ------------------------------------------------------------------
    # AC8 - LookupError from step 1 -> synthetic SourceDeletionInfo + continue from step 2
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lookup_error_from_step1_does_not_raise(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8: LookupError from Sources.delete_source is caught - no exception raised."""
        mock_sources.delete_source.side_effect = LookupError("source not found")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert isinstance(result, PurgeResult)

    @pytest.mark.asyncio
    async def test_lookup_error_cascade_continues_from_step2(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC8: cascade continues from step 2 when step 1 raises LookupError."""
        mock_sources.delete_source.side_effect = LookupError("already deleted")
        await coordinator.delete_source(_SOURCE_ID)
        mock_content.purge_source.assert_called_once()
        mock_enrichment.discard_chunks.assert_called_once()
        mock_enrichment.purge_source.assert_called_once()
        mock_graph.invalidate_evidence_by_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_error_synthetic_source_deletion_info_source_id(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8: synthetic SourceDeletionInfo has the requested source_id."""
        mock_sources.delete_source.side_effect = LookupError("not found")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.source.source_id == _SOURCE_ID

    @pytest.mark.asyncio
    async def test_lookup_error_synthetic_source_name_is_empty_string(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8: synthetic SourceDeletionInfo.source_name = '' (not None or a real name)."""
        mock_sources.delete_source.side_effect = LookupError("not found")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.source.source_name == ""

    @pytest.mark.asyncio
    async def test_lookup_error_synthetic_scope_is_empty_string(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8: synthetic SourceDeletionInfo.scope = '' (not None or a real scope)."""
        mock_sources.delete_source.side_effect = LookupError("not found")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.source.scope == ""

    @pytest.mark.asyncio
    async def test_lookup_error_synthetic_reason_matches_argument(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8: synthetic SourceDeletionInfo.reason carries the reason argument."""
        mock_sources.delete_source.side_effect = LookupError("not found")
        result = await coordinator.delete_source(_SOURCE_ID, reason="cleanup-run-2")
        assert result.source.reason == "cleanup-run-2"

    @pytest.mark.asyncio
    async def test_lookup_error_synthetic_deleted_at_is_approximately_now(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8: synthetic SourceDeletionInfo.deleted_at is within a few seconds of now."""
        mock_sources.delete_source.side_effect = LookupError("not found")
        before = datetime.now(tz=UTC)
        result = await coordinator.delete_source(_SOURCE_ID)
        after = datetime.now(tz=UTC)
        assert before <= result.source.deleted_at <= after

    @pytest.mark.asyncio
    async def test_lookup_error_returns_complete_status_when_steps_2_to_5_succeed(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8/AC9: LookupError from step 1 + steps 2-5 succeed -> COMPLETE status."""
        mock_sources.delete_source.side_effect = LookupError("already purged in prior run")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.status == PurgeStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_lookup_error_completed_steps_contains_all_five(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC8/AC9: LookupError + all downstream steps succeed -> all 5 step names."""
        mock_sources.delete_source.side_effect = LookupError("prior run")
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.completed_steps == (
            "sources.delete",
            "content.purge",
            "enrichment.discard",
            "enrichment.purge",
            "graph.invalidate",
        )

    # ------------------------------------------------------------------
    # AC9 - re-run after partial failure completes remaining steps
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rerun_after_partial_failure_returns_complete(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        """AC9: re-run triggers LookupError on step 1; steps 2-5 succeed -> COMPLETE."""
        # Simulate a second call where source was already deleted
        mock_sources.delete_source.side_effect = LookupError(
            "source already deleted in prior run"
        )
        result = await coordinator.delete_source(_SOURCE_ID)
        assert result.status == PurgeStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_rerun_after_partial_failure_all_downstream_steps_called(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC9: re-run continues all downstream steps after step-1 LookupError."""
        mock_sources.delete_source.side_effect = LookupError("prior partial run")
        await coordinator.delete_source(_SOURCE_ID)
        mock_content.purge_source.assert_called_once_with(_SOURCE_ID)
        mock_enrichment.discard_chunks.assert_called_once()
        mock_enrichment.purge_source.assert_called_once_with(_SOURCE_ID)
        mock_graph.invalidate_evidence_by_chunks.assert_called_once()

    # ------------------------------------------------------------------
    # AC10 - Docstring includes idempotency guarantee and D63 reference
    # ------------------------------------------------------------------

    def test_delete_source_docstring_mentions_idempotency(self) -> None:
        """AC10: delete_source docstring contains 'idempoten' (idempotent/idempotency)."""
        method = getattr(IngestCoordinator, "delete_source", None)
        assert method is not None, "delete_source method does not exist on IngestCoordinator"
        doc = method.__doc__ or ""
        assert "idempoten" in doc.lower(), (
            f"Expected docstring to mention idempotency, got: {doc!r}"
        )

    def test_delete_source_docstring_references_d63(self) -> None:
        """AC10: delete_source docstring references design decision D63."""
        method = getattr(IngestCoordinator, "delete_source", None)
        assert method is not None, "delete_source method does not exist on IngestCoordinator"
        doc = method.__doc__ or ""
        assert "D63" in doc, f"Expected docstring to reference D63, got: {doc!r}"

    # ------------------------------------------------------------------
    # AC11 - Protocol docstring Raises clause updated to "Never raises LookupError"
    # ------------------------------------------------------------------

    def test_protocol_delete_source_docstring_says_never_raises_lookup_error(self) -> None:
        """AC11: protocol IngestCoordinator.delete_source docstring says 'Never raises LookupError'."""
        from owlbear_knowledge.protocols.ingest import IngestCoordinator as ProtocolIC

        method = getattr(ProtocolIC, "delete_source", None)
        assert method is not None, "delete_source not found on protocol IngestCoordinator"
        doc = method.__doc__ or ""
        assert "Never raises LookupError" in doc, (
            f"Expected protocol docstring to say 'Never raises LookupError', got: {doc!r}"
        )

    def test_protocol_delete_source_docstring_mentions_forward_recovery(self) -> None:
        """AC11: protocol docstring Raises clause mentions 'forward-recovery semantics'."""
        from owlbear_knowledge.protocols.ingest import IngestCoordinator as ProtocolIC

        method = getattr(ProtocolIC, "delete_source", None)
        assert method is not None, "delete_source not found on protocol IngestCoordinator"
        doc = method.__doc__ or ""
        assert "forward-recovery" in doc, (
            f"Expected protocol docstring to mention 'forward-recovery', got: {doc!r}"
        )

    def test_protocol_delete_source_docstring_no_lookup_error_raises_clause(self) -> None:
        """AC11: protocol docstring Raises clause no longer lists LookupError as raised."""
        from owlbear_knowledge.protocols.ingest import IngestCoordinator as ProtocolIC

        method = getattr(ProtocolIC, "delete_source", None)
        assert method is not None, "delete_source not found on protocol IngestCoordinator"
        doc = method.__doc__ or ""
        # The old Raises clause said "LookupError if source_id does not exist".
        # That text must be gone.
        assert "if source_id does not exist" not in doc, (
            f"Old 'LookupError if source_id does not exist' Raises clause still present: {doc!r}"
        )

    def test_protocol_delete_source_docstring_mentions_caught_internally(self) -> None:
        """AC11: protocol docstring notes LookupError is caught internally."""
        from owlbear_knowledge.protocols.ingest import IngestCoordinator as ProtocolIC

        method = getattr(ProtocolIC, "delete_source", None)
        assert method is not None, "delete_source not found on protocol IngestCoordinator"
        doc = method.__doc__ or ""
        assert "caught internally" in doc, (
            f"Expected protocol docstring to say 'caught internally', got: {doc!r}"
        )
