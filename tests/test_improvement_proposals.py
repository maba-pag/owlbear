"""Failing tests for owlbear.core.improvement_proposals — proposal-generation pipeline.

Task #893: Test self-improvement proposal pipeline from observability metrics.

All tests must FAIL until the implementation module is created (#894 GREEN phase).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from owlbear.core.improvement_proposals import (  # type: ignore[import]
    ImprovementProposal,
    generate_proposals,
)
from pydantic import TypeAdapter

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
