"""Tests for UsageTracker secondary wiring — TDD RED phase (#846 + #844).

AC coverage (from #846):
1. UsageRecord.operation field (default 'turn', backward compat)
2. record_agent_usage() creates correct UsageRecord and appends to tracker
3. record_agent_usage() is a no-op when tracker is None
4. record_agent_usage() enriches estimated_cost_usd and premium_requests
5. SummarizingCondenser records UsageRecord with operation='condenser'
6. EntityExtractor records UsageRecord with operation='entity_extraction'

AC coverage (from #844):
3. Constructor params for RetrospectiveHook, ProjectDefinitionExtractor,
   SourceEvaluator, IntraDocGraphBuilder, InterDocGraphBuilder
4. Operation values for all secondary call sites
5. SessionMemoryHook bootstrap closure captures tracker
6. Bootstrap functions accept and pass tracker to all secondary components
7. OwlBearAgent._record_usage explicitly passes operation='turn'
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.memory.usage import UsageRecord, UsageTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_usage_result(
    input_tokens: int = 10,
    output_tokens: int = 5,
    requests: int = 1,
) -> MagicMock:
    """Return a mock pydantic_ai RunResult with a usage() method."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_tokens = 0
    usage.cache_write_tokens = 0
    usage.requests = requests
    usage.tool_calls = 0

    result = MagicMock()
    result.usage.return_value = usage
    return result


def _make_tracker(tmp_path: Path) -> UsageTracker:
    return UsageTracker(tmp_path / "usage.jsonl")


# ===========================================================================
# AC1 — UsageRecord.operation field
# ===========================================================================


class TestFromAC_UsageRecordOperationField:
    """AC1: UsageRecord accepts operation field with default 'turn'."""

    def test_operation_field_default_is_turn(self) -> None:
        """UsageRecord created without operation should default to 'turn'."""
        record = UsageRecord(
            timestamp=datetime.now(UTC),
            session_id="test-session",
            model="gpt-4o",
            provider="copilot",
            input_tokens=10,
            output_tokens=5,
            requests=1,
        )
        assert record.operation == "turn"

    def test_operation_field_accepts_custom_value(self) -> None:
        """UsageRecord.operation can be set to any string value."""
        record = UsageRecord(
            timestamp=datetime.now(UTC),
            session_id="test-session",
            model="gpt-4o",
            provider="copilot",
            input_tokens=10,
            output_tokens=5,
            requests=1,
            operation="condenser",
        )
        assert record.operation == "condenser"

    def test_backward_compat_jsonl_without_operation(self) -> None:
        """Deserializing a JSONL record that lacks 'operation' remains valid."""
        raw = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": "old-session",
            "model": "gpt-4o",
            "provider": "copilot",
            "input_tokens": 10,
            "output_tokens": 5,
            "requests": 1,
        }
        record = UsageRecord.model_validate(raw)
        assert record.operation == "turn"

    def test_operation_field_serializes(self) -> None:
        """operation field is included in model_dump output."""
        record = UsageRecord(
            timestamp=datetime.now(UTC),
            session_id="s",
            model="m",
            provider="p",
            input_tokens=1,
            output_tokens=1,
            requests=1,
            operation="entity_extraction",
        )
        data = record.model_dump()
        assert "operation" in data
        assert data["operation"] == "entity_extraction"


# ===========================================================================
# AC2, AC3, AC4 — record_agent_usage()
# ===========================================================================


class TestFromAC_RecordAgentUsage:
    """AC2-4: record_agent_usage() helper in memory.usage."""

    def test_import_from_memory_usage(self) -> None:
        """record_agent_usage must be importable from owlbear.memory.usage."""
        from owlbear.memory.usage import record_agent_usage  # noqa: F401 — existence check

    def test_creates_record_appended_to_tracker(self, tmp_path: Path) -> None:
        """AC2: creates a UsageRecord and appends it to the tracker."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        record_agent_usage(
            tracker=tracker,
            result=result,
            model="gpt-4o",
            provider="copilot",
            session_id="background:condenser",
            operation="condenser",
        )

        records = tracker.load()
        assert len(records) == 1
        rec = records[0]
        assert rec.model == "gpt-4o"
        assert rec.provider == "copilot"
        assert rec.session_id == "background:condenser"
        assert rec.operation == "condenser"
        assert rec.input_tokens == 10
        assert rec.output_tokens == 5

    def test_noop_when_tracker_is_none(self) -> None:
        """AC3: record_agent_usage is a silent no-op when tracker is None."""
        from owlbear.memory.usage import record_agent_usage

        result = _make_usage_result()
        # Must not raise anything
        record_agent_usage(
            tracker=None,
            result=result,
            model="gpt-4o",
            provider="copilot",
            session_id="background:entity_extraction",
            operation="entity_extraction",
        )

    def test_enriches_estimated_cost_usd(self, tmp_path: Path) -> None:
        """AC4: record_agent_usage populates estimated_cost_usd via calc_estimated_cost."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        with patch(
            "owlbear.memory.usage_cost.calc_estimated_cost",
            return_value=0.0042,
        ):
            record_agent_usage(
                tracker=tracker,
                result=result,
                model="gpt-4o",
                provider="copilot",
                session_id="background:condenser",
                operation="condenser",
            )

        records = tracker.load()
        assert len(records) == 1
        assert records[0].estimated_cost_usd == 0.0042

    def test_enriches_premium_requests(self, tmp_path: Path) -> None:
        """AC4: record_agent_usage populates premium_requests via get_premium_requests."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                return_value=None,
            ),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
                return_value=2.5,
            ),
        ):
            record_agent_usage(
                tracker=tracker,
                result=result,
                model="gpt-4o",
                provider="copilot",
                session_id="background:condenser",
                operation="condenser",
            )

        records = tracker.load()
        assert len(records) == 1
        assert records[0].premium_requests == 2.5

    def test_operation_stored_in_record(self, tmp_path: Path) -> None:
        """AC2: operation argument is stored on the created UsageRecord."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        record_agent_usage(
            tracker=tracker,
            result=result,
            model="gpt-4o",
            provider="copilot",
            session_id="background:entity_extraction",
            operation="entity_extraction",
        )

        records = tracker.load()
        assert records[0].operation == "entity_extraction"

    def test_enrichment_failure_does_not_raise(self, tmp_path: Path) -> None:
        """AC4: enrichment errors are swallowed (mirrors existing _record_usage pattern)."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        with patch(
            "owlbear.memory.usage_cost.calc_estimated_cost",
            side_effect=RuntimeError("price lookup failed"),
        ):
            # Must not raise — mirrors try/except in _record_usage
            record_agent_usage(
                tracker=tracker,
                result=result,
                model="gpt-4o",
                provider="copilot",
                session_id="background:condenser",
                operation="condenser",
            )


# ===========================================================================
# AC5 — SummarizingCondenser records usage
# ===========================================================================


class TestFromAC_CondenserUsageWiring:
    """AC5: SummarizingCondenser records UsageRecord with operation='condenser'."""

    def test_condenser_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """SummarizingCondenser accepts tracker and provider constructor params."""
        from owlbear.core.condenser import SummarizingCondenser

        tracker = _make_tracker(tmp_path)
        condenser = SummarizingCondenser(
            model="gpt-4o",
            tracker=tracker,
            provider="copilot",
        )
        assert condenser is not None

    @pytest.mark.asyncio
    async def test_condenser_records_operation_condenser(self, tmp_path: Path) -> None:
        """AC5: after condensation appends record with operation='condenser'."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        from owlbear.core.condenser import SummarizingCondenser

        tracker = _make_tracker(tmp_path)
        condenser = SummarizingCondenser(
            max_events=2,
            keep_first=1,
            target_size=2,
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        # Build a message list that triggers condensation (len > max_events)
        messages = [ModelRequest(parts=[UserPromptPart(content=f"msg {i}")]) for i in range(4)]
        ctx = MagicMock()

        with (
            patch.object(condenser, "_summarize", new_callable=AsyncMock, return_value="summary"),
            patch("owlbear.core.condenser.record_agent_usage") as mock_record,
        ):
            await condenser(ctx, messages)
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args
            # Verify operation='condenser' was passed
            assert call_kwargs.kwargs.get("operation") == "condenser" or (
                len(call_kwargs.args) >= 6 and call_kwargs.args[5] == "condenser"
            )

    @pytest.mark.asyncio
    async def test_condenser_no_record_when_no_tracker(self) -> None:
        """AC5: no UsageRecord created when condenser has no tracker."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(
            max_events=2,
            keep_first=1,
            target_size=2,
            model="test",
            tracker=None,
        )
        messages = [ModelRequest(parts=[UserPromptPart(content=f"msg {i}")]) for i in range(4)]
        ctx = MagicMock()

        with (
            patch.object(condenser, "_summarize", new_callable=AsyncMock, return_value="summary"),
            patch("owlbear.core.condenser.record_agent_usage") as mock_record,
        ):
            await condenser(ctx, messages)
            mock_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_condenser_no_record_when_below_threshold(self, tmp_path: Path) -> None:
        """Edge: no condensation (below threshold) means no UsageRecord appended."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        from owlbear.core.condenser import SummarizingCondenser

        tracker = _make_tracker(tmp_path)
        condenser = SummarizingCondenser(
            max_events=100,
            model="test",
            tracker=tracker,
            provider="copilot",
        )
        messages = [ModelRequest(parts=[UserPromptPart(content="only one")])]
        ctx = MagicMock()

        await condenser(ctx, messages)

        assert tracker.load() == []


# ===========================================================================
# AC6 — EntityExtractor records usage
# ===========================================================================


class TestFromAC_EntityExtractorUsageWiring:
    """AC6: EntityExtractor records UsageRecord with operation='entity_extraction'."""

    def test_extractor_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """EntityExtractor accepts tracker and provider constructor params."""
        from owlbear.memory.knowledge.extractor import EntityExtractor

        tracker = _make_tracker(tmp_path)
        extractor = EntityExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_extractor_records_operation_entity_extraction(self, tmp_path: Path) -> None:
        """AC6: after extraction appends record with operation='entity_extraction'."""
        from owlbear.memory.knowledge.extractor import EntityExtractor, ExtractionResult

        tracker = _make_tracker(tmp_path)
        extractor = EntityExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        mock_run_result = MagicMock()
        mock_run_result.output = ExtractionResult()
        mock_run_result.usage.return_value = MagicMock(
            input_tokens=5,
            output_tokens=3,
            cache_read_tokens=0,
            cache_write_tokens=0,
            requests=1,
            tool_calls=0,
        )

        mock_run = AsyncMock(return_value=mock_run_result)
        with (
            patch.object(extractor._agent, "run", mock_run),
            patch("owlbear.memory.knowledge.extractor.record_agent_usage") as mock_record,
        ):
            await extractor.extract("some text")
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args
            assert call_kwargs.kwargs.get("operation") == "entity_extraction" or (
                len(call_kwargs.args) >= 6 and call_kwargs.args[5] == "entity_extraction"
            )

    @pytest.mark.asyncio
    async def test_extractor_no_record_when_no_tracker(self) -> None:
        """AC6: no UsageRecord when extractor has no tracker."""
        from owlbear.memory.knowledge.extractor import EntityExtractor, ExtractionResult

        extractor = EntityExtractor(model="test", tracker=None)

        mock_run_result = MagicMock()
        mock_run_result.output = ExtractionResult()
        mock_run_result.usage.return_value = MagicMock(
            input_tokens=5,
            output_tokens=3,
            cache_read_tokens=0,
            cache_write_tokens=0,
            requests=1,
            tool_calls=0,
        )

        mock_run = AsyncMock(return_value=mock_run_result)
        with (
            patch.object(extractor._agent, "run", mock_run),
            patch("owlbear.memory.knowledge.extractor.record_agent_usage") as mock_record,
        ):
            await extractor.extract("some text")
            mock_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_extractor_no_record_on_empty_text(self, tmp_path: Path) -> None:
        """Edge: empty/whitespace text returns early — no usage recorded."""
        from owlbear.memory.knowledge.extractor import EntityExtractor

        tracker = _make_tracker(tmp_path)
        extractor = EntityExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        await extractor.extract("")
        assert tracker.load() == []


# ===========================================================================
# AC3 & AC4 — RetrospectiveHook records usage
# ===========================================================================


class TestFromAC_RetrospectiveHookWiring:
    """AC3-4: RetrospectiveHook accepts tracker/provider and records operation='retrospective'."""

    def test_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """RetrospectiveHook constructor accepts tracker and provider params."""
        from owlbear.core.retrospective_hook import RetrospectiveHook

        tracker = _make_tracker(tmp_path)
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=MagicMock(),
            kanban_root=tmp_path,
            tracker=tracker,
            provider="copilot",
        )
        assert hook is not None

    @pytest.mark.asyncio
    async def test_records_operation_retrospective(self, tmp_path: Path) -> None:
        """After _run_retrospective, tracker receives a record with operation='retrospective'."""
        from owlbear.core.retrospective_hook import RetroFindings, RetrospectiveHook

        tracker = _make_tracker(tmp_path)
        mock_ingest = MagicMock()
        mock_ingest.ingest_text = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
            tracker=tracker,
            provider="copilot",
        )

        mock_run_result = _make_usage_result()
        mock_run_result.output = RetroFindings(
            what_worked=[],
            what_failed=[],
            error_patterns=[],
            reusable_patterns=[],
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_run_result)

        with patch.object(hook, "_get_agent", return_value=mock_agent):
            await hook._run_retrospective("42")

        records = tracker.load()
        assert len(records) == 1
        assert records[0].operation == "retrospective"

    @pytest.mark.asyncio
    async def test_no_record_when_no_tracker(self, tmp_path: Path) -> None:
        """No record_agent_usage call when retrospective hook has tracker=None."""
        from owlbear.core.retrospective_hook import RetroFindings, RetrospectiveHook

        mock_ingest = MagicMock()
        mock_ingest.ingest_text = AsyncMock()
        hook = RetrospectiveHook(
            model=MagicMock(),
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
            tracker=None,
        )

        mock_run_result = _make_usage_result()
        mock_run_result.output = RetroFindings(
            what_worked=[],
            what_failed=[],
            error_patterns=[],
            reusable_patterns=[],
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_run_result)

        with (
            patch.object(hook, "_get_agent", return_value=mock_agent),
            patch("owlbear.core.retrospective_hook.record_agent_usage") as mock_record,
        ):
            await hook._run_retrospective("42")
            mock_record.assert_not_called()


# ===========================================================================
# AC3 & AC4 — ProjectDefinitionExtractor records usage
# ===========================================================================


class TestFromAC_ProjectDefinitionExtractorWiring:
    """AC3-4: ProjectDefinitionExtractor accepts tracker/provider.

    Verifies constructor params and operation='project_extraction' recording.
    """

    def test_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """ProjectDefinitionExtractor constructor accepts tracker and provider params."""
        from owlbear.planning.extractor import ProjectDefinitionExtractor

        tracker = _make_tracker(tmp_path)
        extractor = ProjectDefinitionExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_records_operation_project_extraction(self, tmp_path: Path) -> None:
        """After extract(), tracker receives a record with operation='project_extraction'."""
        from owlbear.planning.extractor import ProjectDefinitionExtractor

        tracker = _make_tracker(tmp_path)
        extractor = ProjectDefinitionExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        mock_run_result = _make_usage_result()
        mock_run_result.output = MagicMock()  # ProjectDefinition mock

        with patch.object(extractor._agent, "run", AsyncMock(return_value=mock_run_result)):
            await extractor.extract("build a project about AI assistants")

        records = tracker.load()
        assert len(records) == 1
        assert records[0].operation == "project_extraction"

    @pytest.mark.asyncio
    async def test_no_record_when_no_tracker(self) -> None:
        """No record_agent_usage call when ProjectDefinitionExtractor has tracker=None."""
        from owlbear.planning.extractor import ProjectDefinitionExtractor

        extractor = ProjectDefinitionExtractor(model="test", tracker=None)

        mock_run_result = _make_usage_result()
        mock_run_result.output = MagicMock()

        with (
            patch.object(extractor._agent, "run", AsyncMock(return_value=mock_run_result)),
            patch("owlbear.planning.extractor.record_agent_usage") as mock_record,
        ):
            await extractor.extract("build a project")
            mock_record.assert_not_called()


# ===========================================================================
# AC3 & AC4 — SourceEvaluator records usage
# ===========================================================================


class TestFromAC_SourceEvaluatorWiring:
    """AC3-4: SourceEvaluator accepts tracker/provider and records operation='source_evaluation'."""

    def test_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """SourceEvaluator constructor accepts tracker and provider params."""
        from owlbear.memory.knowledge.evaluator import SourceEvaluator

        tracker = _make_tracker(tmp_path)
        evaluator = SourceEvaluator(
            model="test",
            tracker=tracker,
            provider="copilot",
        )
        assert evaluator is not None

    @pytest.mark.asyncio
    async def test_records_operation_source_evaluation(self, tmp_path: Path) -> None:
        """After evaluate(), tracker receives a record with operation='source_evaluation'."""
        from owlbear.memory.knowledge.evaluator import EvaluationResult, SourceEvaluator

        tracker = _make_tracker(tmp_path)
        evaluator = SourceEvaluator(
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        mock_run_result = _make_usage_result()
        mock_run_result.output = EvaluationResult(
            relevance_score=0.8,
            tags=[],
            summary="relevant",
            worth_ingesting=True,
        )

        with patch.object(evaluator._agent, "run", AsyncMock(return_value=mock_run_result)):
            await evaluator.evaluate(
                "some content about the project",
                {"name": "proj", "description": "about AI", "goals": ["build"]},
            )

        records = tracker.load()
        assert len(records) == 1
        assert records[0].operation == "source_evaluation"

    @pytest.mark.asyncio
    async def test_no_record_when_no_tracker(self) -> None:
        """No record_agent_usage call when SourceEvaluator has tracker=None."""
        from owlbear.memory.knowledge.evaluator import EvaluationResult, SourceEvaluator

        evaluator = SourceEvaluator(model="test", tracker=None)

        mock_run_result = _make_usage_result()
        mock_run_result.output = EvaluationResult(
            relevance_score=0.8,
            tags=[],
            summary="relevant",
            worth_ingesting=True,
        )

        with (
            patch.object(evaluator._agent, "run", AsyncMock(return_value=mock_run_result)),
            patch("owlbear.memory.knowledge.evaluator.record_agent_usage") as mock_record,
        ):
            await evaluator.evaluate(
                "content",
                {"name": "p", "description": "d", "goals": []},
            )
            mock_record.assert_not_called()


# ===========================================================================
# AC3 & AC4 — IntraDocGraphBuilder records usage
# ===========================================================================


class TestFromAC_IntraDocGraphBuilderWiring:
    """AC3-4: IntraDocGraphBuilder accepts tracker/provider.

    Verifies constructor params and operation='intra_doc_graph' recording.
    """

    def test_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """IntraDocGraphBuilder constructor accepts tracker and provider params."""
        from owlbear.memory.knowledge.graph_builder import IntraDocGraphBuilder

        tracker = _make_tracker(tmp_path)
        builder = IntraDocGraphBuilder(
            model="test",
            tracker=tracker,
            provider="copilot",
        )
        assert builder is not None

    @pytest.mark.asyncio
    async def test_records_operation_intra_doc_graph(self, tmp_path: Path) -> None:
        """After build(), tracker receives a record with operation='intra_doc_graph'."""
        from owlbear.memory.knowledge.extractor import ExtractionResult
        from owlbear.memory.knowledge.graph_builder import IntraDocGraphBuilder
        from owlbear.memory.knowledge.models import Entity, EntityType

        tracker = _make_tracker(tmp_path)
        builder = IntraDocGraphBuilder(
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        entities = [
            Entity(name="Alpha", entity_type=EntityType.CONCEPT),
            Entity(name="Beta", entity_type=EntityType.CONCEPT),
        ]

        mock_run_result = _make_usage_result()
        mock_run_result.output = ExtractionResult()  # empty result — no edges

        with patch.object(builder._agent, "run", AsyncMock(return_value=mock_run_result)):
            await builder.build(entities)

        records = tracker.load()
        assert len(records) == 1
        assert records[0].operation == "intra_doc_graph"

    @pytest.mark.asyncio
    async def test_no_record_when_no_tracker(self) -> None:
        """No record_agent_usage call when IntraDocGraphBuilder tracker=None."""
        from owlbear.memory.knowledge.extractor import ExtractionResult
        from owlbear.memory.knowledge.graph_builder import IntraDocGraphBuilder
        from owlbear.memory.knowledge.models import Entity, EntityType

        builder = IntraDocGraphBuilder(model="test", tracker=None)

        entities = [
            Entity(name="Alpha", entity_type=EntityType.CONCEPT),
            Entity(name="Beta", entity_type=EntityType.CONCEPT),
        ]

        mock_run_result = _make_usage_result()
        mock_run_result.output = ExtractionResult()

        with (
            patch.object(builder._agent, "run", AsyncMock(return_value=mock_run_result)),
            patch("owlbear.memory.knowledge.graph_builder.record_agent_usage") as mock_record,
        ):
            await builder.build(entities)
            mock_record.assert_not_called()


# ===========================================================================
# AC3 & AC4 — InterDocGraphBuilder records usage
# ===========================================================================


class TestFromAC_InterDocGraphBuilderWiring:
    """AC3-4: InterDocGraphBuilder accepts tracker/provider.

    Verifies constructor params and operation='inter_doc_graph' recording.
    """

    def test_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """InterDocGraphBuilder constructor accepts tracker and provider params."""
        from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder

        tracker = _make_tracker(tmp_path)
        builder = InterDocGraphBuilder(
            model="test",
            vector_store=MagicMock(),
            graph_store=MagicMock(),
            tracker=tracker,
            provider="copilot",
        )
        assert builder is not None

    @pytest.mark.asyncio
    async def test_records_operation_inter_doc_graph(self, tmp_path: Path) -> None:
        """After build() with candidate pairs, tracker gets operation='inter_doc_graph' record."""
        from owlbear.memory.knowledge.extractor import ExtractionResult
        from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder
        from owlbear.memory.knowledge.models import Entity, EntityType

        tracker = _make_tracker(tmp_path)
        builder = InterDocGraphBuilder(
            model="test",
            vector_store=MagicMock(),
            graph_store=MagicMock(),
            tracker=tracker,
            provider="copilot",
        )

        entities = [
            Entity(name="Alpha", entity_type=EntityType.CONCEPT, document_id="doc-1"),
            Entity(name="Beta", entity_type=EntityType.CONCEPT, document_id="doc-2"),
        ]

        mock_run_result = _make_usage_result()
        mock_run_result.output = ExtractionResult()  # empty result — no edges

        with (
            patch.object(builder, "_find_candidate_pairs", return_value=[("id-a", "id-b")]),
            patch.object(builder._agent, "run", AsyncMock(return_value=mock_run_result)),
        ):
            await builder.build(entities)

        records = tracker.load()
        assert len(records) == 1
        assert records[0].operation == "inter_doc_graph"

    @pytest.mark.asyncio
    async def test_no_record_when_no_tracker(self) -> None:
        """No record_agent_usage call when InterDocGraphBuilder tracker=None."""
        from owlbear.memory.knowledge.extractor import ExtractionResult
        from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder
        from owlbear.memory.knowledge.models import Entity, EntityType

        builder = InterDocGraphBuilder(
            model="test",
            vector_store=MagicMock(),
            graph_store=MagicMock(),
            tracker=None,
        )

        entities = [
            Entity(name="Alpha", entity_type=EntityType.CONCEPT, document_id="doc-1"),
            Entity(name="Beta", entity_type=EntityType.CONCEPT, document_id="doc-2"),
        ]

        mock_run_result = _make_usage_result()
        mock_run_result.output = ExtractionResult()

        with (
            patch.object(builder, "_find_candidate_pairs", return_value=[("id-a", "id-b")]),
            patch.object(builder._agent, "run", AsyncMock(return_value=mock_run_result)),
            patch(
                "owlbear.memory.knowledge.inter_doc_graph_builder.record_agent_usage"
            ) as mock_record,
        ):
            await builder.build(entities)
            mock_record.assert_not_called()


# ===========================================================================
# AC5 — SessionMemoryHook bootstrap closure captures tracker
# ===========================================================================


class TestFromAC_SessionMemoryHookClosure:
    """AC5: _wire_session_memory_hook accepts tracker/provider.

    Verifies the bootstrap closure records operation='session_summary'.
    """

    def test_wire_function_accepts_tracker_param(self) -> None:
        """_wire_session_memory_hook signature has a 'tracker' parameter."""
        import inspect

        from owlbear.bootstrap import _wire_session_memory_hook

        sig = inspect.signature(_wire_session_memory_hook)
        assert "tracker" in sig.parameters, (
            "_wire_session_memory_hook must have a 'tracker' parameter"
        )

    @pytest.mark.asyncio
    async def test_session_summarizer_records_operation_session_summary(
        self, tmp_path: Path
    ) -> None:
        """After _summarize runs, tracker receives a record with operation='session_summary'."""
        from owlbear.bootstrap import _wire_session_memory_hook
        from owlbear.core.hooks import HookEvent, HookRegistry

        tracker = _make_tracker(tmp_path)
        hooks = HookRegistry()
        mock_model = MagicMock()

        mock_run_result = _make_usage_result()
        mock_run_result.output = "a structured summary"
        mock_agent_inst = MagicMock()
        mock_agent_inst.run = AsyncMock(return_value=mock_run_result)

        with patch("pydantic_ai.Agent", return_value=mock_agent_inst):
            # Will fail in RED — _wire_session_memory_hook does not yet accept tracker
            _wire_session_memory_hook(
                mock_model, tmp_path, hooks, tracker=tracker, provider="copilot"
            )

            session_handlers = hooks._handlers.get(HookEvent.SESSION_END, [])
            assert session_handlers, "No SESSION_END handler was registered"
            hook = session_handlers[0]

            # Call the internal summarizer directly (bypasses SessionMemoryHook.__call__)
            await hook._summarizer("some conversation text")

        records = tracker.load()
        assert len(records) == 1
        assert records[0].operation == "session_summary"


# ===========================================================================
# AC6 — Bootstrap functions accept and pass tracker to secondary components
# ===========================================================================


class TestFromAC_BootstrapTrackerWiring:
    """AC6: Bootstrap helpers accept tracker/provider and route it to secondary components."""

    def test_build_knowledge_infra_accepts_tracker(self) -> None:
        """_build_knowledge_infra signature includes a 'tracker' parameter."""
        import inspect

        from owlbear.bootstrap.knowledge import _build_knowledge_infra

        sig = inspect.signature(_build_knowledge_infra)
        assert "tracker" in sig.parameters, "_build_knowledge_infra must have a 'tracker' parameter"

    def test_build_knowledge_toolset_accepts_tracker(self) -> None:
        """_build_knowledge_toolset signature includes a 'tracker' parameter."""
        import inspect

        from owlbear.bootstrap.knowledge import _build_knowledge_toolset

        sig = inspect.signature(_build_knowledge_toolset)
        assert "tracker" in sig.parameters, (
            "_build_knowledge_toolset must have a 'tracker' parameter"
        )

    def test_build_bookmark_toolset_accepts_tracker(self) -> None:
        """_build_bookmark_toolset signature includes a 'tracker' parameter."""
        import inspect

        from owlbear.bootstrap.knowledge import _build_bookmark_toolset

        sig = inspect.signature(_build_bookmark_toolset)
        assert "tracker" in sig.parameters, (
            "_build_bookmark_toolset must have a 'tracker' parameter"
        )

    def test_wire_post_model_hooks_accepts_tracker(self) -> None:
        """_wire_post_model_hooks signature includes a 'tracker' parameter."""
        import inspect

        from owlbear.bootstrap import _wire_post_model_hooks

        sig = inspect.signature(_wire_post_model_hooks)
        assert "tracker" in sig.parameters, "_wire_post_model_hooks must have a 'tracker' parameter"

    def test_bootstrap_condenser_receives_tracker(self) -> None:
        """bootstrap() source passes tracker= to SummarizingCondenser."""
        import ast
        import inspect
        import textwrap

        from owlbear.bootstrap import bootstrap

        source = textwrap.dedent(inspect.getsource(bootstrap))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "SummarizingCondenser"
            ):
                for kw in node.keywords:
                    if kw.arg == "tracker":
                        return  # Found tracker= kwarg in SummarizingCondenser(...)
        pytest.fail("bootstrap() does not pass tracker= to SummarizingCondenser")


# ===========================================================================
# AC7 — OwlBearAgent._record_usage explicitly passes operation='turn'
# ===========================================================================


class TestFromAC_OwlBearAgentOperationTurn:
    """AC7: OwlBearAgent._record_usage creates UsageRecord with explicit operation='turn'."""

    def test_record_usage_passes_operation_turn(self) -> None:
        """_record_usage source contains an explicit operation='turn' kwarg in UsageRecord(...)."""
        import ast
        import inspect
        import textwrap

        from owlbear.core.agent import OwlBearAgent

        source = textwrap.dedent(inspect.getsource(OwlBearAgent._record_usage))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "UsageRecord"
            ):
                for kw in node.keywords:
                    if kw.arg == "operation":
                        return  # Found explicit operation= kwarg — test passes
        pytest.fail("_record_usage() does not explicitly pass operation= to UsageRecord(**kwargs)")


# ===========================================================================
# AC2 gap — record_agent_usage must accept model: str | Model and resolve name
# ===========================================================================


class TestFromAC_RecordAgentUsageModelResolution:
    """AC2 gap: record_agent_usage(model=) must accept a Model object and resolve its name."""

    def test_model_object_name_resolved_in_record(self, tmp_path: Path) -> None:
        """When a Model object with model_name attr is passed, stored model must be model_name.

        AC2: model: str | Model -- resolves name internally (same logic as
        OwlBearAgent._extract_model_name).
        """
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        mock_model = MagicMock()
        mock_model.model_name = "gpt-4o-resolved"
        # Ensure str(mock_model) differs so we can distinguish resolution from plain str cast
        mock_model.__str__ = MagicMock(return_value="mock-model-str-repr")

        record_agent_usage(
            tracker=tracker,
            result=result,
            model=mock_model,  # Model object, not string
            provider="copilot",
            session_id="background:condenser",
            operation="condenser",
        )

        records = tracker.load()
        assert len(records) == 1
        # AC2: must extract model_name via _extract_model_name logic, not str(model)
        assert records[0].model == "gpt-4o-resolved", (
            f"expected 'gpt-4o-resolved' but got {records[0].model!r}; "
            "record_agent_usage must resolve Model.model_name not str(model)"
        )


# ===========================================================================
# AC3 gap — provider constructor param must default to 'copilot' in all components
# ===========================================================================


class TestFromAC_ProviderDefaultCopilot:
    """AC3 gap: all listed secondary components must default provider to 'copilot', not None."""

    def test_summarizing_condenser_provider_default_is_copilot(self) -> None:
        """SummarizingCondenser provider parameter must default to 'copilot'."""
        import inspect

        from owlbear.core.condenser import SummarizingCondenser

        sig = inspect.signature(SummarizingCondenser.__init__)
        assert "provider" in sig.parameters, "SummarizingCondenser missing provider param"
        assert sig.parameters["provider"].default == "copilot", (
            f"SummarizingCondenser provider default is {sig.parameters['provider'].default!r}, "
            "expected 'copilot'"
        )

    def test_entity_extractor_provider_default_is_copilot(self) -> None:
        """EntityExtractor provider parameter must default to 'copilot'."""
        import inspect

        from owlbear.memory.knowledge.extractor import EntityExtractor

        sig = inspect.signature(EntityExtractor.__init__)
        assert "provider" in sig.parameters, "EntityExtractor missing provider param"
        assert sig.parameters["provider"].default == "copilot", (
            f"EntityExtractor provider default is {sig.parameters['provider'].default!r}, "
            "expected 'copilot'"
        )

    def test_project_definition_extractor_provider_default_is_copilot(self) -> None:
        """ProjectDefinitionExtractor provider parameter must default to 'copilot'."""
        import inspect

        from owlbear.planning.extractor import ProjectDefinitionExtractor

        sig = inspect.signature(ProjectDefinitionExtractor.__init__)
        assert "provider" in sig.parameters, "ProjectDefinitionExtractor missing provider param"
        assert sig.parameters["provider"].default == "copilot", (
            f"ProjectDefinitionExtractor provider default is "
            f"{sig.parameters['provider'].default!r}, expected 'copilot'"
        )

    def test_source_evaluator_provider_default_is_copilot(self) -> None:
        """SourceEvaluator provider parameter must default to 'copilot'."""
        import inspect

        from owlbear.memory.knowledge.evaluator import SourceEvaluator

        sig = inspect.signature(SourceEvaluator.__init__)
        assert "provider" in sig.parameters, "SourceEvaluator missing provider param"
        assert sig.parameters["provider"].default == "copilot", (
            f"SourceEvaluator provider default is {sig.parameters['provider'].default!r}, "
            "expected 'copilot'"
        )

    def test_intra_doc_graph_builder_provider_default_is_copilot(self) -> None:
        """IntraDocGraphBuilder provider parameter must default to 'copilot'."""
        import inspect

        from owlbear.memory.knowledge.graph_builder import IntraDocGraphBuilder

        sig = inspect.signature(IntraDocGraphBuilder.__init__)
        assert "provider" in sig.parameters, "IntraDocGraphBuilder missing provider param"
        assert sig.parameters["provider"].default == "copilot", (
            f"IntraDocGraphBuilder provider default is {sig.parameters['provider'].default!r}, "
            "expected 'copilot'"
        )

    def test_inter_doc_graph_builder_provider_default_is_copilot(self) -> None:
        """InterDocGraphBuilder provider parameter must default to 'copilot'."""
        import inspect

        from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder

        sig = inspect.signature(InterDocGraphBuilder.__init__)
        assert "provider" in sig.parameters, "InterDocGraphBuilder missing provider param"
        assert sig.parameters["provider"].default == "copilot", (
            f"InterDocGraphBuilder provider default is {sig.parameters['provider'].default!r}, "
            "expected 'copilot'"
        )


# ===========================================================================
# AC6 gap — Bootstrap must actually forward tracker at runtime, not just accept it
# ===========================================================================


class TestFromAC_BootstrapRuntimeForwarding:
    """AC6 gap: bootstrap helper functions must *forward* tracker to secondary constructors.

    The prior cycle's tests checked only that these functions have a 'tracker' parameter.
    The reviewer found tracker is accepted but unused (ARG001).  These tests verify
    the runtime forwarding behavior.
    """

    def test_wire_post_model_hooks_forwards_tracker_to_retrospective_hook(
        self, tmp_path: Path
    ) -> None:
        """_wire_post_model_hooks must forward tracker= to RetrospectiveHook constructor.

        Current impl marks tracker as ARG001 (unused) and omits it from the
        RetrospectiveHook(...) call.
        """
        from owlbear.bootstrap import _wire_post_model_hooks

        tracker = _make_tracker(tmp_path)
        mock_ingest = MagicMock()
        mock_hooks = MagicMock()
        mock_settings = MagicMock()
        mock_settings.session_memory_enabled = False
        mock_model = MagicMock()

        with (
            patch("owlbear.core.retrospective_hook.RetrospectiveHook") as mock_retro_cls,
            patch("owlbear.core.hook_worker_supervisor.HookWorkerSupervisor"),
        ):
            mock_retro_instance = MagicMock()
            mock_retro_cls.return_value = mock_retro_instance

            _wire_post_model_hooks(
                mock_settings,
                mock_model,
                tmp_path,
                mock_hooks,
                mock_ingest,
                tracker=tracker,
            )

        assert mock_retro_cls.called, "RetrospectiveHook was never instantiated"
        forwarded = mock_retro_cls.call_args.kwargs.get("tracker")
        assert forwarded is tracker, (
            f"_wire_post_model_hooks did not forward tracker= to RetrospectiveHook; "
            f"got tracker={forwarded!r}"
        )

    def test_wire_post_model_hooks_forwards_tracker_to_session_hook(self, tmp_path: Path) -> None:
        """_wire_post_model_hooks must forward tracker= to _wire_session_memory_hook.

        Current impl calls _wire_session_memory_hook(model, workspace, hooks) with no tracker.
        """
        from owlbear.bootstrap import _wire_post_model_hooks

        tracker = _make_tracker(tmp_path)
        mock_hooks = MagicMock()
        mock_settings = MagicMock()
        mock_settings.session_memory_enabled = True
        mock_model = MagicMock()

        with patch("owlbear.bootstrap._wire_session_memory_hook") as mock_wire:
            _wire_post_model_hooks(
                mock_settings,
                mock_model,
                tmp_path,
                mock_hooks,
                None,  # ingest_pipeline=None — skips RetrospectiveHook branch
                tracker=tracker,
            )

        assert mock_wire.called, "_wire_session_memory_hook was never called"
        forwarded = mock_wire.call_args.kwargs.get("tracker")
        assert forwarded is tracker, (
            f"_wire_post_model_hooks did not forward tracker= to _wire_session_memory_hook; "
            f"got tracker={forwarded!r}"
        )

    def test_build_knowledge_infra_passes_tracker_to_entity_extractor(self) -> None:
        """_build_knowledge_infra must pass tracker= to EntityExtractor constructor.

        Current impl marks tracker as ARG001 and calls EntityExtractor(model=chat_model)
        with no tracker kwarg.
        """
        import ast
        import inspect
        import textwrap

        from owlbear.bootstrap.knowledge import _build_knowledge_infra

        source = textwrap.dedent(inspect.getsource(_build_knowledge_infra))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "EntityExtractor"
            ):
                for kw in node.keywords:
                    if kw.arg == "tracker":
                        return  # tracker= kwarg found in EntityExtractor(...)
        pytest.fail(
            "_build_knowledge_infra does not pass tracker= to EntityExtractor; "
            "AC6 requires tracker forwarded to all secondary components"
        )

    def test_build_knowledge_toolset_passes_tracker_to_inter_doc_builder(self) -> None:
        """_build_knowledge_toolset must pass tracker= to InterDocGraphBuilder constructor.

        Current impl calls InterDocGraphBuilder(model=, vector_store=, graph_store=)
        with no tracker kwarg.
        """
        import ast
        import inspect
        import textwrap

        from owlbear.bootstrap.knowledge import _build_knowledge_toolset

        source = textwrap.dedent(inspect.getsource(_build_knowledge_toolset))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "InterDocGraphBuilder"
            ):
                for kw in node.keywords:
                    if kw.arg == "tracker":
                        return  # tracker= kwarg found in InterDocGraphBuilder(...)
        pytest.fail(
            "_build_knowledge_toolset does not pass tracker= to InterDocGraphBuilder; "
            "AC6 requires tracker forwarded to all secondary components"
        )

    def test_build_bookmark_toolset_passes_tracker_to_source_evaluator(self) -> None:
        """_build_bookmark_toolset must pass tracker= to SourceEvaluator constructor.

        Current impl calls SourceEvaluator(model=chat_model) with no tracker kwarg.
        """
        import ast
        import inspect
        import textwrap

        from owlbear.bootstrap.knowledge import _build_bookmark_toolset

        source = textwrap.dedent(inspect.getsource(_build_bookmark_toolset))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "SourceEvaluator"
            ):
                for kw in node.keywords:
                    if kw.arg == "tracker":
                        return  # tracker= kwarg found in SourceEvaluator(...)
        pytest.fail(
            "_build_bookmark_toolset does not pass tracker= to SourceEvaluator; "
            "AC6 requires tracker forwarded to all secondary components"
        )


# ===========================================================================
# AC4 gap (retry-2) — RetrospectiveHook must pass model object, not str(model)
# ===========================================================================


class TestFromAC_RetrospectiveHookModelFidelity:
    """AC4 (retry-2): RetrospectiveHook must forward the model object to record_agent_usage.

    The previous cycle passed model=str(self._model), which bypasses the
    model_name resolution in record_agent_usage() and stores a wrong identifier.
    AC2 requires model: str | Model -- resolves name internally; the call site
    must pass the raw Model, not a pre-stringified version.
    """

    @pytest.mark.asyncio
    async def test_retrospective_hook_stores_model_name_not_str_repr(self, tmp_path: Path) -> None:
        """UsageRecord.model must equal model.model_name, not str(model).

        Creates a mock model where str(model) != model.model_name.
        If the call site passes str(self._model), the stored identifier will be
        the str-repr, not the resolved model_name — and this test will FAIL.
        """
        from owlbear.core.retrospective_hook import RetroFindings, RetrospectiveHook

        tracker = _make_tracker(tmp_path)
        mock_ingest = MagicMock()
        mock_ingest.ingest_text = AsyncMock()

        # Craft a model mock where str() and model_name differ so we can detect
        # which one was forwarded to record_agent_usage.
        mock_model = MagicMock()
        mock_model.model_name = "copilot-gpt-4o-resolved"
        mock_model.__str__ = MagicMock(return_value="copilot-gpt-4o-stringified")

        hook = RetrospectiveHook(
            model=mock_model,
            ingest_pipeline=mock_ingest,
            kanban_root=tmp_path,
            tracker=tracker,
            provider="copilot",
        )

        mock_run_result = _make_usage_result()
        mock_run_result.output = RetroFindings(
            what_worked=[],
            what_failed=[],
            error_patterns=[],
            reusable_patterns=[],
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_run_result)

        with patch.object(hook, "_get_agent", return_value=mock_agent):
            await hook._run_retrospective("42")

        records = tracker.load()
        assert len(records) == 1, "Expected exactly one UsageRecord after _run_retrospective"
        assert records[0].model == "copilot-gpt-4o-resolved", (
            f"UsageRecord.model is {records[0].model!r}; "
            "RetrospectiveHook must pass model=self._model (not str(self._model)) "
            "to record_agent_usage so that model_name resolution runs correctly"
        )


# ===========================================================================
# AC5 gap (retry-2) — Session closure must pass model object, not str(model)
# ===========================================================================


class TestFromAC_SessionMemoryHookModelFidelity:
    """AC5 (retry-2): session closure must pass model object to record_agent_usage.

    The previous cycle passed model=str(model), which bypasses model_name
    resolution and stores a wrong identifier in the UsageRecord.
    AC2 requires model: str | Model -- resolves name internally; the closure
    must pass the raw Model, not a pre-stringified version.
    """

    @pytest.mark.asyncio
    async def test_session_closure_stores_model_name_not_str_repr(self, tmp_path: Path) -> None:
        """UsageRecord.model for session_summary must equal model.model_name, not str(model).

        Creates a mock model where str(model) != model.model_name.
        If the closure passes str(model), the stored identifier will be the
        str-repr — and this test will FAIL.
        """
        from owlbear.bootstrap import _wire_session_memory_hook
        from owlbear.core.hooks import HookEvent, HookRegistry

        tracker = _make_tracker(tmp_path)
        hooks = HookRegistry()

        # Craft a model mock where str() and model_name differ.
        mock_model = MagicMock()
        mock_model.model_name = "copilot-gpt-4o-resolved"
        mock_model.__str__ = MagicMock(return_value="copilot-gpt-4o-stringified")

        mock_run_result = _make_usage_result()
        mock_run_result.output = "summary text"
        mock_agent_inst = MagicMock()
        mock_agent_inst.run = AsyncMock(return_value=mock_run_result)

        with patch("pydantic_ai.Agent", return_value=mock_agent_inst):
            _wire_session_memory_hook(
                mock_model, tmp_path, hooks, tracker=tracker, provider="copilot"
            )

            session_handlers = hooks._handlers.get(HookEvent.SESSION_END, [])
            assert session_handlers, "No SESSION_END handler was registered"
            hook = session_handlers[0]

            await hook._summarizer("some conversation text")

        records = tracker.load()
        assert len(records) == 1, "Expected exactly one UsageRecord after _summarize"
        assert records[0].model == "copilot-gpt-4o-resolved", (
            f"UsageRecord.model is {records[0].model!r}; "
            "session memory closure must pass model=model (not str(model)) "
            "to record_agent_usage so that model_name resolution runs correctly"
        )
