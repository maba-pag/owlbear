"""Failing tests for owlbear.core.improvement_proposals — proposal-generation pipeline.

Task #893: Test self-improvement proposal pipeline from observability metrics.

All tests must FAIL until the implementation module is created (#894 GREEN phase).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import TypeAdapter

from owlbear.core.improvement_proposals import (  # type: ignore[import]
    ImprovementProposal,
    generate_proposals,
)
from owlbear.core.observability import EventStore, ObservabilityEvent

# ---------------------------------------------------------------------------
# Test helpers — build ObservabilityEvent fixtures
# ---------------------------------------------------------------------------

_event_adapter: TypeAdapter[ObservabilityEvent] = TypeAdapter(ObservabilityEvent)


def _event(  # noqa: PLR0913
    *,
    event_type: str = "post_tool_use",
    agent_name: str | None = "builder",
    tool_name: str | None = "read_file",
    session_id: str | None = "sess-001",
    success: bool = True,
    error: str | None = None,
    duration_ms: float | None = 50.0,
    minutes_ago: int = 0,
) -> ObservabilityEvent:
    """Build an ObservabilityEvent with a timestamp *minutes_ago* from now."""
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return ObservabilityEvent(
        timestamp=ts.isoformat(),
        event_type=event_type,
        agent_name=agent_name,
        tool_name=tool_name,
        session_id=session_id,
        success=success,
        error=error,
        duration_ms=duration_ms,
    )


def _write_events(path: Path, events: list[ObservabilityEvent]) -> None:
    """Write events as JSONL for test fixtures."""
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(_event_adapter.dump_json(ev).decode("utf-8") + "\n")


def _store_with_events(tmp_path: Path, events: list[ObservabilityEvent]) -> EventStore:
    """Create an EventStore pre-populated with *events*."""
    p = tmp_path / "events.jsonl"
    _write_events(p, events)
    return EventStore(p)


def _healthy_events(count: int = 10) -> list[ObservabilityEvent]:
    """Return *count* healthy post_tool_use events — low error rate, low latency."""
    return [
        _event(
            event_type="post_tool_use",
            tool_name="read_file",
            success=True,
            duration_ms=40.0,
            minutes_ago=i,
        )
        for i in range(count)
    ]


def _high_error_events(total: int = 10, error_count: int = 8) -> list[ObservabilityEvent]:
    """Return *total* events where *error_count* fail — high error rate."""
    return [
        _event(
            event_type="post_tool_use",
            tool_name="run_terminal",
            agent_name="builder",
            success=(i >= error_count),
            error=None if i >= error_count else "Exit code 1",
            duration_ms=100.0,
            minutes_ago=i,
        )
        for i in range(total)
    ]


def _high_latency_events(count: int = 5) -> list[ObservabilityEvent]:
    """Return *count* events with very high latency (5 seconds per call)."""
    return [
        _event(
            event_type="post_tool_use",
            tool_name="semantic_search",
            agent_name="researcher",
            success=True,
            error=None,
            duration_ms=5000.0,
            minutes_ago=i,
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# AC1: Public entrypoint consumes EventStore outputs (not a new analytics store)
# ---------------------------------------------------------------------------


class TestFromAC_EntrypointContract:
    """generate_proposals() is importable, accepts an EventStore, returns list."""

    def test_generate_proposals_is_callable(self) -> None:
        """generate_proposals must be a callable entrypoint."""
        assert callable(generate_proposals)

    def test_improvement_proposal_is_importable_class(self) -> None:
        """ImprovementProposal must be importable from owlbear.core.improvement_proposals."""
        assert ImprovementProposal is not None

    def test_accepts_event_store_argument(self, tmp_path: Path) -> None:
        """generate_proposals(store) accepts a single EventStore positional arg."""
        store = EventStore(tmp_path / "empty.jsonl")
        result = generate_proposals(store)
        assert isinstance(result, list)

    def test_accepts_optional_window_parameter(self, tmp_path: Path) -> None:
        """generate_proposals(store, window=...) accepts an optional timedelta window."""
        store = EventStore(tmp_path / "empty.jsonl")
        result = generate_proposals(store, window=timedelta(hours=24))
        assert isinstance(result, list)

    def test_accepts_none_window_for_all_time(self, tmp_path: Path) -> None:
        """generate_proposals(store, window=None) queries the whole store, not a subrange."""
        store = EventStore(tmp_path / "empty.jsonl")
        result = generate_proposals(store, window=None)
        assert isinstance(result, list)

    def test_does_not_create_a_second_store(self, tmp_path: Path) -> None:
        """generate_proposals must not create any new files in the filesystem."""
        store = EventStore(tmp_path / "events.jsonl")
        files_before = set(tmp_path.iterdir())
        generate_proposals(store)
        files_after = set(tmp_path.iterdir())
        # The events.jsonl may or may not exist; no new files should appear
        assert files_after == files_before


# ---------------------------------------------------------------------------
# AC2: Empty / low-signal windows return no proposals, no exception
# ---------------------------------------------------------------------------


class TestFromAC_EmptyAndLowSignal:
    """Empty or healthy EventStore → empty list, never raises."""

    def test_empty_store_returns_empty_list(self, tmp_path: Path) -> None:
        """EventStore with no events → generate_proposals returns []."""
        store = EventStore(tmp_path / "events.jsonl")
        result = generate_proposals(store)
        assert result == []

    def test_empty_store_does_not_raise(self, tmp_path: Path) -> None:
        """generate_proposals on empty store must not raise any exception."""
        store = EventStore(tmp_path / "events.jsonl")
        try:
            generate_proposals(store)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"generate_proposals raised on empty store: {exc}")

    def test_low_signal_healthy_metrics_returns_no_proposals(self, tmp_path: Path) -> None:
        """Store with low error rate and normal latency produces no proposals."""
        store = _store_with_events(tmp_path, _healthy_events(count=10))
        result = generate_proposals(store)
        assert result == []

    def test_low_signal_does_not_raise(self, tmp_path: Path) -> None:
        """generate_proposals with low-signal data never raises."""
        store = _store_with_events(tmp_path, _healthy_events(count=3))
        try:
            generate_proposals(store)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"generate_proposals raised on low-signal data: {exc}")

    def test_single_event_returns_no_proposals(self, tmp_path: Path) -> None:
        """A single healthy event is insufficient signal — must return []."""
        store = _store_with_events(tmp_path, [_event(success=True, duration_ms=20.0)])
        result = generate_proposals(store)
        assert result == []

    def test_zero_error_rate_returns_no_proposals(self, tmp_path: Path) -> None:
        """100% success rate with normal latency must produce no proposals."""
        events = [
            _event(event_type="post_tool_use", success=True, duration_ms=30.0, minutes_ago=i)
            for i in range(20)
        ]
        store = _store_with_events(tmp_path, events)
        result = generate_proposals(store)
        assert result == []


# ---------------------------------------------------------------------------
# AC3: High-error / high-latency scenarios produce typed, evidence-backed proposals
# ---------------------------------------------------------------------------


class TestFromAC_HighSignalScenarios:
    """High-error or high-latency data → at least one ImprovementProposal with evidence."""

    def test_high_error_rate_returns_at_least_one_proposal(self, tmp_path: Path) -> None:
        """80% error rate on a tool must produce ≥1 proposal."""
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        result = generate_proposals(store)
        assert len(result) >= 1

    def test_high_latency_returns_at_least_one_proposal(self, tmp_path: Path) -> None:
        """Consistent very-high tool latency (5s+) must produce ≥1 proposal."""
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        result = generate_proposals(store)
        assert len(result) >= 1

    def test_high_error_proposals_are_typed(self, tmp_path: Path) -> None:
        """All returned proposals are ImprovementProposal instances (not dicts)."""
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        result = generate_proposals(store)
        assert len(result) >= 1
        for proposal in result:
            assert isinstance(proposal, ImprovementProposal), (
                f"Expected ImprovementProposal, got {type(proposal)}"
            )

    def test_high_error_proposals_contain_evidence(self, tmp_path: Path) -> None:
        """Proposals reference observed data (error count or rate in rationale/evidence)."""
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        result = generate_proposals(store)
        assert len(result) >= 1
        for proposal in result:
            # Evidence must be a non-empty string with numeric content (ratio, count, etc.)
            evidence_text = str(proposal.evidence) + str(proposal.rationale)
            assert len(evidence_text.strip()) > 0, "Evidence/rationale must not be empty"

    def test_high_latency_proposals_are_typed(self, tmp_path: Path) -> None:
        """High-latency proposals are ImprovementProposal instances."""
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        result = generate_proposals(store)
        assert len(result) >= 1
        for proposal in result:
            assert isinstance(proposal, ImprovementProposal)

    def test_high_latency_proposals_contain_evidence(self, tmp_path: Path) -> None:
        """High-latency proposals must reference latency data in evidence/rationale."""
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        result = generate_proposals(store)
        assert len(result) >= 1
        for proposal in result:
            evidence_text = str(proposal.evidence) + str(proposal.rationale)
            assert len(evidence_text.strip()) > 0


# ---------------------------------------------------------------------------
# AC4: Proposals are review artifacts — correct shape, no side effects
# ---------------------------------------------------------------------------


class TestFromAC_ProposalReviewArtifact:
    """ImprovementProposal has the required contract fields; generation has no side effects."""

    def _make_proposal_store(self, tmp_path: Path) -> EventStore:
        """Return a store with high-error data that should produce at least one proposal."""
        return _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))

    # -- field contract ------------------------------------------------------

    def test_proposal_has_target_agent_field(self, tmp_path: Path) -> None:
        """ImprovementProposal.target_agent is a non-empty string."""
        store = self._make_proposal_store(tmp_path)
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            assert hasattr(p, "target_agent"), "Missing field: target_agent"
            assert isinstance(p.target_agent, str)
            assert p.target_agent.strip() != "", "target_agent must not be blank"

    def test_proposal_has_change_category_field(self, tmp_path: Path) -> None:
        """ImprovementProposal.change_category is a non-empty string."""
        store = self._make_proposal_store(tmp_path)
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            assert hasattr(p, "change_category"), "Missing field: change_category"
            assert isinstance(p.change_category, str)
            assert p.change_category.strip() != "", "change_category must not be blank"

    def test_proposal_has_rationale_field(self, tmp_path: Path) -> None:
        """ImprovementProposal.rationale is a non-empty string."""
        store = self._make_proposal_store(tmp_path)
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            assert hasattr(p, "rationale"), "Missing field: rationale"
            assert isinstance(p.rationale, str)
            assert p.rationale.strip() != "", "rationale must not be blank"

    def test_proposal_has_evidence_field(self, tmp_path: Path) -> None:
        """ImprovementProposal.evidence is present (non-empty string or dict)."""
        store = self._make_proposal_store(tmp_path)
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            assert hasattr(p, "evidence"), "Missing field: evidence"
            assert p.evidence is not None, "evidence must not be None"

    def test_proposal_has_suggested_change_field(self, tmp_path: Path) -> None:
        """ImprovementProposal.suggested_change is a non-empty string."""
        store = self._make_proposal_store(tmp_path)
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            assert hasattr(p, "suggested_change"), "Missing field: suggested_change"
            assert isinstance(p.suggested_change, str)
            assert p.suggested_change.strip() != "", "suggested_change must not be blank"

    # -- no side effects (no file writes, no user prompts) -------------------

    def test_generate_proposals_does_not_write_files(self, tmp_path: Path) -> None:
        """generate_proposals must not create or modify any files on disk."""
        store = self._make_proposal_store(tmp_path)
        # Capture exact file set before call (the events.jsonl already exists)
        files_before = {p: p.stat().st_mtime for p in tmp_path.rglob("*") if p.is_file()}
        generate_proposals(store)
        files_after = {p: p.stat().st_mtime for p in tmp_path.rglob("*") if p.is_file()}
        assert files_before == files_after, (
            "generate_proposals must not write, modify, or create any files"
        )

    def test_generate_proposals_does_not_call_ask_user(self, tmp_path: Path) -> None:
        """generate_proposals must not prompt the user via ask_user or similar."""
        store = self._make_proposal_store(tmp_path)
        ask_user_mock = MagicMock()
        # Patch at both potential call sites
        with (
            patch("owlbear.core.improvement_proposals.ask_user", ask_user_mock, create=True),
            patch("owlbear.tools.ask_user.ask_user", ask_user_mock, create=True),
        ):
            generate_proposals(store)
        ask_user_mock.assert_not_called()

    def test_improvement_proposal_has_all_required_fields(self) -> None:
        """ImprovementProposal instances must have all five required fields accessible."""
        required = {"target_agent", "change_category", "rationale", "evidence", "suggested_change"}
        # Check annotations / class definition carries all fields
        import inspect

        # If the class uses Pydantic, check model_fields; otherwise annotations
        if hasattr(ImprovementProposal, "model_fields"):
            fields = set(ImprovementProposal.model_fields.keys())
        else:
            fields = set(inspect.get_annotations(ImprovementProposal))
        missing = required - fields
        assert not missing, f"ImprovementProposal is missing fields: {missing}"


# ---------------------------------------------------------------------------
# Retry AC1 enforcement: verify EventStore API delegation (not re-aggregation)
# ---------------------------------------------------------------------------


class TestFromAC_EntrypointContractStrong:
    """Retry: stronger contract — generate_proposals delegates to EventStore APIs."""

    def test_generate_proposals_calls_store_summary(self) -> None:
        """generate_proposals must call store.summary() — not re-aggregate from store.load()."""
        store = MagicMock(spec=EventStore)
        store.summary.return_value = {
            "total_tool_calls": 0,
            "error_count": 0,
            "avg_tool_duration_ms": 0.0,
            "tools_by_frequency": {},
            "agents_by_usage": {},
        }
        generate_proposals(store)
        store.summary.assert_called_once_with(None)

    def test_generate_proposals_calls_store_summary_with_window(self) -> None:
        """generate_proposals(store, window=X) must pass the window to store.summary(X)."""
        window = timedelta(hours=6)
        store = MagicMock(spec=EventStore)
        store.summary.return_value = {
            "total_tool_calls": 0,
            "error_count": 0,
            "avg_tool_duration_ms": 0.0,
            "tools_by_frequency": {},
            "agents_by_usage": {},
        }
        generate_proposals(store, window=window)
        store.summary.assert_called_once_with(window)

    def test_generate_proposals_calls_store_tool_stats_when_threshold_met(self) -> None:
        """generate_proposals must call store.tool_stats() when total_tool_calls >= threshold."""
        store = MagicMock(spec=EventStore)
        store.summary.return_value = {
            "total_tool_calls": 10,
            "error_count": 0,
            "avg_tool_duration_ms": 50.0,
            "tools_by_frequency": {"read_file": 10},
            "agents_by_usage": {"builder": 10},
        }
        store.tool_stats.return_value = {}
        generate_proposals(store)
        store.tool_stats.assert_called_once_with(None)

    def test_tool_stats_not_called_when_below_min_total_calls(self) -> None:
        """generate_proposals short-circuits before calling tool_stats if total < 5."""
        store = MagicMock(spec=EventStore)
        store.summary.return_value = {
            "total_tool_calls": 4,  # below _MIN_TOTAL_CALLS=5
            "error_count": 0,
            "avg_tool_duration_ms": 0.0,
            "tools_by_frequency": {},
            "agents_by_usage": {},
        }
        generate_proposals(store)
        store.tool_stats.assert_not_called()

    def test_empty_tool_stats_despite_sufficient_total_calls_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """When summary reports >= 5 calls but all events lack tool_name, return []."""
        # post_tool_use events with tool_name=None count toward total_tool_calls (summary)
        # but produce an empty dict from tool_stats (which filters on tool_name)
        events = [
            _event(
                event_type="post_tool_use",
                tool_name=None,
                success=True,
                duration_ms=50.0,
                minutes_ago=i,
            )
            for i in range(10)
        ]
        store = _store_with_events(tmp_path, events)
        result = generate_proposals(store)
        assert result == []


# ---------------------------------------------------------------------------
# Retry AC3 enforcement: evidence must carry specific observed metric values
# ---------------------------------------------------------------------------


class TestFromAC_EvidenceStructure:
    """Retry: stronger enforcement that evidence payloads contain real observed metrics."""

    def test_high_error_evidence_is_a_dict(self, tmp_path: Path) -> None:
        """High-error proposal evidence must be a dict, not a generic string."""
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        proposals = generate_proposals(store)
        assert proposals
        reliability = [p for p in proposals if p.change_category == "reliability"]
        assert reliability
        for p in reliability:
            assert isinstance(p.evidence, dict), (
                f"evidence must be a dict for reliability proposals, got {type(p.evidence)}"
            )

    def test_high_error_evidence_contains_error_rate_key(self, tmp_path: Path) -> None:
        """High-error evidence dict must have 'error_rate' as a numeric value in (0, 1]."""
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            if p.change_category == "reliability":
                assert isinstance(p.evidence, dict)
                assert "error_rate" in p.evidence, "evidence must contain 'error_rate'"
                assert isinstance(p.evidence["error_rate"], float), "error_rate must be float"
                assert 0 < p.evidence["error_rate"] <= 1.0, "error_rate must be a valid ratio"

    def test_high_error_evidence_reflects_actual_observed_counts(self, tmp_path: Path) -> None:
        """Evidence error_count and call_count must match the actual observed data."""
        events = _high_error_events(total=10, error_count=8)
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        assert proposals
        reliability = [p for p in proposals if p.change_category == "reliability"]
        assert reliability
        for p in reliability:
            assert isinstance(p.evidence, dict)
            assert p.evidence.get("error_count") == 8, (
                f"evidence must report observed error_count=8, got {p.evidence.get('error_count')}"
            )
            assert p.evidence.get("call_count") == 10, (
                f"evidence must report observed call_count=10, got {p.evidence.get('call_count')}"
            )

    def test_high_latency_evidence_is_a_dict(self, tmp_path: Path) -> None:
        """High-latency proposal evidence must be a dict, not a generic string."""
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        proposals = generate_proposals(store)
        assert proposals
        perf = [p for p in proposals if p.change_category == "performance"]
        assert perf
        for p in perf:
            assert isinstance(p.evidence, dict), (
                f"evidence must be a dict for performance proposals, got {type(p.evidence)}"
            )

    def test_high_latency_evidence_contains_avg_duration_ms_key(self, tmp_path: Path) -> None:
        """High-latency evidence dict must have 'avg_duration_ms' above the latency threshold."""
        high_latency_ms = 3000.0
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            if p.change_category == "performance":
                assert isinstance(p.evidence, dict)
                assert "avg_duration_ms" in p.evidence, "evidence must contain 'avg_duration_ms'"
                assert isinstance(p.evidence["avg_duration_ms"], float)
                assert p.evidence["avg_duration_ms"] >= high_latency_ms, (
                    "avg_duration_ms in evidence must be at or above the latency threshold"
                )


# ---------------------------------------------------------------------------
# Retry: policy boundary conditions and previously uncovered code paths
# ---------------------------------------------------------------------------


class TestFromAC_PolicyBoundaries:
    """Retry: boundary values for thresholds and uncovered code paths (lines 57, 65, 137)."""

    def test_tool_with_fewer_than_min_calls_is_skipped_even_at_high_error_rate(
        self, tmp_path: Path
    ) -> None:
        """Tool with call_count < 3 is skipped even at 100% error rate (line 65 path)."""
        # 2 events for tool_A (both fail) — below _MIN_TOOL_CALLS=3
        # 3 healthy events for tool_B — meets minimum, zero errors
        events_a = [
            _event(
                tool_name="tool_A",
                success=False,
                error="err",
                duration_ms=50.0,
                minutes_ago=i,
            )
            for i in range(2)
        ]
        events_b = [
            _event(tool_name="tool_B", success=True, duration_ms=40.0, minutes_ago=10 + i)
            for i in range(3)
        ]
        store = _store_with_events(tmp_path, events_a + events_b)
        proposals = generate_proposals(store)
        tool_a_proposals = [p for p in proposals if "tool_A" in str(p.rationale)]
        assert not tool_a_proposals, (
            "Tool with fewer than 3 calls must not produce proposals even at high error rate"
        )

    def test_error_rate_at_threshold_produces_proposal(self, tmp_path: Path) -> None:
        """error_rate == 0.5 is exactly at the >= threshold and must produce a proposal."""
        # 6 events: 3 fail, 3 succeed  → error_rate = 3/6 = 0.5 exactly
        events = [
            _event(
                tool_name="threshold_tool",
                success=(i >= 3),
                error=None if i >= 3 else "err",
                duration_ms=50.0,
                minutes_ago=i,
            )
            for i in range(6)
        ]
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        threshold_proposals = [p for p in proposals if "threshold_tool" in str(p.rationale)]
        assert threshold_proposals, (
            "error_rate == 0.5 is at the '>=' threshold and must produce a proposal"
        )

    def test_error_rate_just_below_threshold_produces_no_proposal(self, tmp_path: Path) -> None:
        """error_rate < 0.5 must NOT trigger a reliability proposal."""
        # 10 events: 4 fail, 6 succeed → error_rate = 0.4 (below threshold)
        events = [
            _event(
                tool_name="subthreshold_tool",
                success=(i >= 4),
                error=None if i >= 4 else "err",
                duration_ms=50.0,
                minutes_ago=i,
            )
            for i in range(10)
        ]
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        sub_proposals = [p for p in proposals if "subthreshold_tool" in str(p.rationale)]
        assert not sub_proposals, (
            "error_rate = 0.4 is below the threshold and must NOT produce a proposal"
        )

    def test_latency_at_threshold_produces_proposal(self, tmp_path: Path) -> None:
        """avg_duration_ms == 3000.0 is exactly at the >= threshold and must produce a proposal."""
        events = [
            _event(tool_name="slow_tool", success=True, duration_ms=3000.0, minutes_ago=i)
            for i in range(5)
        ]
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        latency_proposals = [p for p in proposals if "slow_tool" in str(p.rationale)]
        assert latency_proposals, (
            "avg_duration_ms == 3000.0 is at the '>=' threshold and must produce a proposal"
        )

    def test_latency_below_threshold_produces_no_proposal(self, tmp_path: Path) -> None:
        """avg_duration_ms < 3000.0 must NOT trigger a latency proposal."""
        events = [
            _event(tool_name="fast_enough_tool", success=True, duration_ms=2999.0, minutes_ago=i)
            for i in range(5)
        ]
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        fast_proposals = [p for p in proposals if "fast_enough_tool" in str(p.rationale)]
        assert not fast_proposals, (
            "avg_duration_ms = 2999.0 is below the threshold and must NOT produce a proposal"
        )

    def test_target_agent_defaults_to_builder_when_events_have_no_agent_name(
        self, tmp_path: Path
    ) -> None:
        """When all high-error events lack agent_name, target_agent must default to 'builder'."""
        events = [
            _event(
                tool_name="agentless_tool",
                agent_name=None,
                success=(i >= 8),
                error=None if i >= 8 else "err",
                duration_ms=50.0,
                minutes_ago=i,
            )
            for i in range(10)
        ]
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        agentless = [p for p in proposals if "agentless_tool" in str(p.rationale)]
        assert agentless, "High-error tool with no agent_name should still produce proposals"
        for p in agentless:
            assert p.target_agent == "builder", (
                f"target_agent must default to 'builder' when no agent_name present, "
                f"got '{p.target_agent}'"
            )


# ---------------------------------------------------------------------------
# Retry-3 AC1 window-propagation: tool_stats(window) and store.query(window)
# ---------------------------------------------------------------------------

_SUMMARY_WITH_CALLS: dict = {
    "total_tool_calls": 10,
    "error_count": 0,
    "avg_tool_duration_ms": 50.0,
    "tools_by_frequency": {"probe_tool": 10},
    "agents_by_usage": {"builder": 10},
}
_NONEMPTY_TOOL_STATS: dict = {
    "probe_tool": {"call_count": 5, "error_count": 0, "avg_duration_ms": 50.0},
}


class TestFromAC_WindowPropagation:
    """AC1 final coverage: the window arg is propagated to store.tool_stats and store.query."""

    def test_generate_proposals_calls_store_tool_stats_with_window(self) -> None:
        """When window is provided, store.tool_stats must be called with that window, not None."""
        window = timedelta(hours=6)
        store = MagicMock(spec=EventStore)
        store.summary.return_value = _SUMMARY_WITH_CALLS
        store.tool_stats.return_value = _NONEMPTY_TOOL_STATS
        store.query.return_value = []
        generate_proposals(store, window=window)
        store.tool_stats.assert_called_once_with(window)

    def test_generate_proposals_calls_store_query_with_window_for_target_agent(self) -> None:
        """When window is provided and tool_stats is non-empty, store.query(window) is called."""
        window = timedelta(hours=6)
        store = MagicMock(spec=EventStore)
        store.summary.return_value = _SUMMARY_WITH_CALLS
        store.tool_stats.return_value = _NONEMPTY_TOOL_STATS
        store.query.return_value = []
        generate_proposals(store, window=window)
        store.query.assert_called_once_with(window)

    def test_generate_proposals_calls_store_load_not_query_when_window_is_none(self) -> None:
        """When window=None, store.load() is called for event loading, not store.query()."""
        store = MagicMock(spec=EventStore)
        store.summary.return_value = _SUMMARY_WITH_CALLS
        store.tool_stats.return_value = _NONEMPTY_TOOL_STATS
        store.load.return_value = []
        generate_proposals(store, window=None)
        store.load.assert_called()
        store.query.assert_not_called()


# ---------------------------------------------------------------------------
# Retry-4: Non-fallback _target_agent correctness — most-common agent selection
# ---------------------------------------------------------------------------


class TestFromAC_TargetAgentSelection:
    """Non-fallback target_agent: the most-common observed agent per tool is selected.

    The existing suite proves target_agent is non-empty (field presence) and that the
    fallback branch returns "builder" when no agent_name is present.  These tests cover
    the non-fallback path: when real agent names are present, the most-common one is
    chosen — not the first seen, not a global aggregate, and not always "builder".
    """

    def test_target_agent_is_most_common_not_first_seen(self, tmp_path: Path) -> None:
        """Majority agent is selected even when a different agent appears first in the stream."""
        # "auditor" appears 2x first; "researcher" appears 5x after.
        # Counter.most_common must return "researcher", not "auditor" (first seen).
        events = (
            [
                _event(
                    tool_name="contested_tool",
                    agent_name="auditor",
                    success=False,
                    error="err",
                    duration_ms=100.0,
                    minutes_ago=i,
                )
                for i in range(2)
            ]
            + [
                _event(
                    tool_name="contested_tool",
                    agent_name="researcher",
                    success=False,
                    error="err",
                    duration_ms=100.0,
                    minutes_ago=10 + i,
                )
                for i in range(5)
            ]
            + [
                _event(
                    tool_name="contested_tool",
                    agent_name="researcher",
                    success=True,
                    duration_ms=100.0,
                    minutes_ago=20,
                )
            ]
        )
        # 7 errors out of 8 calls → 87.5% error rate → proposal generated
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        relevant = [p for p in proposals if "contested_tool" in p.rationale]
        assert relevant, "High-error tool must produce a proposal"
        for p in relevant:
            assert p.target_agent == "researcher", (
                f"Most common agent is 'researcher' (5 of 8 events), not 'auditor' (2 events). "
                f"Got: '{p.target_agent}'"
            )

    def test_target_agent_is_non_builder_when_other_agent_dominates(self, tmp_path: Path) -> None:
        """target_agent must not default to 'builder' when a real non-builder agent dominates."""
        events = [
            _event(
                tool_name="writer_tool",
                agent_name="writer",
                success=False,
                error="err",
                duration_ms=100.0,
                minutes_ago=i,
            )
            for i in range(8)
        ] + [
            _event(
                tool_name="writer_tool",
                agent_name="writer",
                success=True,
                duration_ms=100.0,
                minutes_ago=10 + i,
            )
            for i in range(2)
        ]
        # 8/10 error rate; all events from "writer"
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        relevant = [p for p in proposals if "writer_tool" in p.rationale]
        assert relevant, "High-error tool with agent_name present must produce proposals"
        for p in relevant:
            assert p.target_agent == "writer", (
                f"target_agent must be the observed agent 'writer' (non-fallback path). "
                f"Got: '{p.target_agent}'"
            )
            assert p.target_agent != "builder", (
                "target_agent must NOT fall back to 'builder' when observed agent is present"
            )

    def test_target_agent_is_per_tool_not_global(self, tmp_path: Path) -> None:
        """Each proposal uses the per-tool most-common agent, not a global event aggregate."""
        # tool_x: all 6 events from "reviewer"
        # tool_y: all 6 events from "architect"
        # Per-tool selection must pick "reviewer" for x and "architect" for y.
        tool_x_events = [
            _event(
                tool_name="tool_x",
                agent_name="reviewer",
                success=False,
                error="err",
                duration_ms=100.0,
                minutes_ago=i,
            )
            for i in range(6)
        ]
        tool_y_events = [
            _event(
                tool_name="tool_y",
                agent_name="architect",
                success=False,
                error="err",
                duration_ms=100.0,
                minutes_ago=20 + i,
            )
            for i in range(6)
        ]
        # Both tools: 100% error rate on 6 calls each → both produce proposals
        store = _store_with_events(tmp_path, tool_x_events + tool_y_events)
        proposals = generate_proposals(store)
        x_proposals = [p for p in proposals if "tool_x" in p.rationale]
        y_proposals = [p for p in proposals if "tool_y" in p.rationale]
        assert x_proposals, "tool_x with 100% error rate must produce proposals"
        assert y_proposals, "tool_y with 100% error rate must produce proposals"
        for p in x_proposals:
            assert p.target_agent == "reviewer", (
                f"tool_x proposals must target per-tool agent 'reviewer', got '{p.target_agent}'"
            )
        for p in y_proposals:
            assert p.target_agent == "architect", (
                f"tool_y proposals must target per-tool agent 'architect', got '{p.target_agent}'"
            )
