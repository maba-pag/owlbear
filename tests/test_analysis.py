"""Failing tests for owlbear_orchestrator.analysis (task #222, RED phase for #179).

Covers: AnalysisProposal model (8), high_error_rate_detector (6),
slow_agent_detector (4), repeated_failure_detector (6),
stale_dispatch_detector (7), analyze entrypoint (5),
format_json (4), format_markdown (5), empty input (3) = 48 tests.

All tests import from owlbear_orchestrator.analysis (module not yet built).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from owlbear_orchestrator.analysis import (  # type: ignore[import-not-found]
    AnalysisProposal,
    analyze,
    format_json,
    format_markdown,
    high_error_rate_detector,
    repeated_failure_detector,
    slow_agent_detector,
    stale_dispatch_detector,
)
from owlbear.audit.models import CompletionEvent, DispatchEvent

# ---------------------------------------------------------------------------
# Fixed reference "now" for deterministic tests
# ---------------------------------------------------------------------------

NOW = datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# In-memory model factories (for unit tests of individual detectors)
# ---------------------------------------------------------------------------


def _ts(dt: datetime) -> str:
    return dt.isoformat()


def _dispatch_event(
    task_id: int,
    agent: str,
    timestamp: datetime,
    session_id: str = "sess-1",
) -> DispatchEvent:
    return DispatchEvent(
        timestamp=_ts(timestamp),
        task_id=task_id,
        agent=agent,
        prompt_summary=f"task {task_id}",
        session_id=session_id,
    )


def _completion_event(
    task_id: int,
    agent: str,
    outcome: str,
    duration_ms: int,
    timestamp: datetime,
) -> CompletionEvent:
    return CompletionEvent(
        timestamp=_ts(timestamp),
        task_id=task_id,
        agent=agent,
        outcome=outcome,  # type: ignore[arg-type]
        duration_ms=duration_ms,
        files_changed=[],
    )


# ---------------------------------------------------------------------------
# JSONL dict factories (for analyze() integration tests using tmp_path)
# ---------------------------------------------------------------------------


def _dispatch_dict(
    task_id: int,
    agent: str,
    timestamp: datetime,
    session_id: str = "sess-1",
) -> dict[str, Any]:
    return {
        "type": "dispatch",
        "timestamp": _ts(timestamp),
        "task_id": task_id,
        "agent": agent,
        "prompt_summary": f"task {task_id}",
        "session_id": session_id,
    }


def _cd(task_id: int, agent: str, outcome: str, dur: int, ts: datetime) -> dict[str, Any]:
    """Compact completion-dict factory — 5 args to stay within PLR0913 limit."""
    return {
        "type": "completion",
        "timestamp": _ts(ts),
        "task_id": task_id,
        "agent": agent,
        "outcome": outcome,
        "duration_ms": dur,
        "files_changed": [],
        "error": None,
    }


def _write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")


# ---------------------------------------------------------------------------
# AnalysisProposal model
# ---------------------------------------------------------------------------


class TestFromAC_AnalysisProposalModel:  # noqa: N801
    """AnalysisProposal is frozen, has exactly 6 fields with expected types."""

    def _make(self, **overrides: Any) -> AnalysisProposal:
        defaults: dict[str, Any] = {
            "detector": "test",
            "agent": "builder",
            "task_id": 1,
            "severity": "warning",
            "message": "test message",
            "evidence": {},
        }
        return AnalysisProposal(**{**defaults, **overrides})

    def test_frozen_raises_on_mutation(self) -> None:
        """AnalysisProposal must be immutable — assigning a field must raise."""
        p = self._make()
        with pytest.raises((AttributeError, TypeError)):
            p.message = "changed"  # type: ignore[misc]

    def test_exactly_six_fields(self) -> None:
        """Model must expose exactly 6 declared fields."""
        import dataclasses

        try:
            fields = dataclasses.fields(AnalysisProposal)
            count = len(fields)
        except TypeError:
            # Pydantic model
            count = len(AnalysisProposal.model_fields)
        assert count == 6, f"Expected 6 fields, got {count}"

    def test_field_detector_is_str(self) -> None:
        p = self._make(detector="high_error_rate")
        assert isinstance(p.detector, str)

    def test_field_agent_accepts_none(self) -> None:
        p = self._make(agent=None)
        assert p.agent is None

    def test_field_task_id_accepts_int(self) -> None:
        p = self._make(task_id=42)
        assert p.task_id == 42

    def test_field_task_id_accepts_none(self) -> None:
        p = self._make(task_id=None)
        assert p.task_id is None

    def test_field_severity_is_str(self) -> None:
        p = self._make(severity="critical")
        assert isinstance(p.severity, str)

    def test_field_evidence_is_dict(self) -> None:
        p = self._make(evidence={"rate": 0.42})
        assert isinstance(p.evidence, dict)
        assert p.evidence["rate"] == 0.42


# ---------------------------------------------------------------------------
# High error rate detector
# ---------------------------------------------------------------------------


class TestFromAC_HighErrorRateDetector:  # noqa: N801
    """Fires at >= 40% failure rate with >= 3 completions; silent otherwise."""

    def _completions(
        self,
        agent: str,
        outcomes: list[str],
        base: datetime | None = None,
    ) -> list[CompletionEvent]:
        t = base or NOW - timedelta(minutes=30)
        return [_completion_event(i, agent, o, 1000, t + timedelta(seconds=i)) for i, o in enumerate(outcomes)]

    def test_fires_at_60_percent_with_5_completions(self) -> None:
        events = self._completions("builder", ["failure", "failure", "failure", "success", "success"])
        proposals = high_error_rate_detector(events)
        assert len(proposals) == 1
        assert proposals[0].detector == "high_error_rate"
        assert proposals[0].agent == "builder"

    def test_fires_at_exactly_40_percent_with_5_completions(self) -> None:
        """2 failures out of 5 = 40% — at the threshold, must fire."""
        events = self._completions("agent-d", ["failure", "failure", "success", "success", "success"])
        proposals = high_error_rate_detector(events)
        assert len(proposals) == 1

    def test_does_not_fire_below_40_percent(self) -> None:
        """1 failure out of 3 = 33% — below threshold."""
        events = self._completions("agent-c", ["failure", "success", "success"])
        proposals = high_error_rate_detector(events)
        assert proposals == []

    def test_does_not_fire_with_only_2_completions(self) -> None:
        """100% failure rate but only 2 completions — below minimum dispatch count."""
        events = self._completions("agent-b", ["failure", "failure"])
        proposals = high_error_rate_detector(events)
        assert proposals == []

    def test_fires_only_for_agents_above_threshold(self) -> None:
        """Agent A: 40% failure (5 total) fires; Agent B: 2 failures (< 3 total) does not."""
        events = self._completions("agent-a", ["failure", "failure", "success", "success", "success"])
        events += self._completions("agent-b", ["failure", "failure"])
        proposals = high_error_rate_detector(events)
        agents = {p.agent for p in proposals}
        assert "agent-a" in agents
        assert "agent-b" not in agents

    def test_empty_events_returns_empty(self) -> None:
        assert high_error_rate_detector([]) == []


# ---------------------------------------------------------------------------
# Slow agent detector
# ---------------------------------------------------------------------------


class TestFromAC_SlowAgentDetector:  # noqa: N801
    """Fires at > 2x global average duration with >= 3 completions; silent otherwise."""

    def _completions(
        self,
        agent: str,
        durations_ms: list[int],
        base: datetime | None = None,
    ) -> list[CompletionEvent]:
        t = base or NOW - timedelta(minutes=30)
        return [_completion_event(i, agent, "success", d, t + timedelta(seconds=i)) for i, d in enumerate(durations_ms)]

    def test_fires_when_agent_is_more_than_2x_global_avg(self) -> None:
        """agent-slow 3 at 100s, agent-fast 6 at 1s: global=(300+6)/9=34s; 100/34=2.94x > 2x."""
        slow = self._completions("agent-slow", [100_000, 100_000, 100_000])
        fast = self._completions(
            "agent-fast",
            [1000, 1000, 1000, 1000, 1000, 1000],
            NOW - timedelta(minutes=20),
        )
        proposals = slow_agent_detector(slow + fast)
        agents = {p.agent for p in proposals}
        assert "agent-slow" in agents

    def test_does_not_fire_when_agent_is_below_2x_global_avg(self) -> None:
        """Agent A ratio < 2x global avg — must not fire."""
        events = self._completions("agent-a", [3000, 3000, 3000])
        events += self._completions("agent-b", [2000, 2000, 2000], NOW - timedelta(minutes=10))
        # global avg = 2500; agent-a ratio = 3000/2500 = 1.2x
        proposals = slow_agent_detector(events)
        agents = {p.agent for p in proposals}
        assert "agent-a" not in agents

    def test_does_not_fire_with_fewer_than_3_completions(self) -> None:
        """Agent with only 2 completions, even at 10x global, must not fire."""
        slow = self._completions("slow-agent", [100_000, 100_000])
        fast = self._completions(
            "fast-agent",
            [1000, 1000, 1000, 1000],
            NOW - timedelta(minutes=10),
        )
        proposals = slow_agent_detector(slow + fast)
        agents = {p.agent for p in proposals}
        assert "slow-agent" not in agents

    def test_empty_events_returns_empty(self) -> None:
        assert slow_agent_detector([]) == []


# ---------------------------------------------------------------------------
# Repeated failure detector
# ---------------------------------------------------------------------------


class TestFromAC_RepeatedFailureDetector:  # noqa: N801
    """Fires at >= 2 failures on same task_id; silent at 1 failure per task."""

    def test_fires_at_2_failures_same_task(self) -> None:
        base = NOW - timedelta(minutes=30)
        events = [
            _completion_event(42, "builder", "failure", 1000, base),
            _completion_event(42, "builder", "failure", 1000, base + timedelta(seconds=10)),
        ]
        proposals = repeated_failure_detector(events)
        assert len(proposals) == 1
        assert proposals[0].detector == "repeated_failure"
        assert proposals[0].task_id == 42

    def test_does_not_fire_with_1_failure_per_task(self) -> None:
        base = NOW - timedelta(minutes=30)
        events = [
            _completion_event(42, "builder", "failure", 1000, base),
            _completion_event(43, "builder", "failure", 1000, base + timedelta(seconds=5)),
        ]
        proposals = repeated_failure_detector(events)
        assert proposals == []

    def test_does_not_fire_for_success_completions(self) -> None:
        base = NOW - timedelta(minutes=30)
        events = [
            _completion_event(42, "builder", "success", 1000, base),
            _completion_event(42, "builder", "success", 1000, base + timedelta(seconds=5)),
        ]
        proposals = repeated_failure_detector(events)
        assert proposals == []

    def test_fires_exactly_once_for_task_with_3_failures(self) -> None:
        base = NOW - timedelta(minutes=30)
        events = [_completion_event(99, "reviewer", "failure", 1000, base + timedelta(seconds=i)) for i in range(3)]
        proposals = repeated_failure_detector(events)
        assert len(proposals) == 1
        assert proposals[0].task_id == 99

    def test_boundary_exactly_2_failures_fires(self) -> None:
        base = NOW - timedelta(minutes=30)
        events = [
            _completion_event(77, "auditor", "failure", 2000, base),
            _completion_event(77, "auditor", "failure", 2000, base + timedelta(seconds=1)),
        ]
        proposals = repeated_failure_detector(events)
        assert len(proposals) == 1

    def test_empty_events_returns_empty(self) -> None:
        assert repeated_failure_detector([]) == []


# ---------------------------------------------------------------------------
# Stale dispatch detector
# ---------------------------------------------------------------------------


class TestFromAC_StaleDispatchDetector:  # noqa: N801
    """Fires for dispatch > 1h without completion; silent for < 1h or matched dispatch."""

    def test_fires_for_dispatch_2h_old_without_completion(self) -> None:
        events = [_dispatch_event(55, "builder", NOW - timedelta(hours=2))]
        proposals = stale_dispatch_detector(events, now=NOW)
        assert len(proposals) == 1
        assert proposals[0].detector == "stale_dispatch"
        assert proposals[0].task_id == 55

    def test_does_not_fire_for_dispatch_30min_old(self) -> None:
        events = [_dispatch_event(55, "builder", NOW - timedelta(minutes=30))]
        proposals = stale_dispatch_detector(events, now=NOW)
        assert proposals == []

    def test_does_not_fire_for_matched_dispatch(self) -> None:
        """A dispatch that has a corresponding completion is not stale."""
        events: list[DispatchEvent | CompletionEvent] = [
            _dispatch_event(66, "builder", NOW - timedelta(hours=2), session_id="s1"),
            _completion_event(66, "builder", "success", 5000, NOW - timedelta(hours=1, minutes=50)),
        ]
        proposals = stale_dispatch_detector(events, now=NOW)
        assert proposals == []

    def test_boundary_at_exactly_1h_does_not_fire(self) -> None:
        """At exactly 1h old: condition is strictly > 1h, so must NOT fire."""
        events = [_dispatch_event(70, "builder", NOW - timedelta(hours=1))]
        proposals = stale_dispatch_detector(events, now=NOW)
        assert proposals == []

    def test_boundary_just_over_1h_fires(self) -> None:
        """1h + 1 second: strictly over threshold — must fire."""
        events = [_dispatch_event(71, "builder", NOW - timedelta(hours=1, seconds=1))]
        proposals = stale_dispatch_detector(events, now=NOW)
        assert len(proposals) == 1

    def test_only_stale_dispatches_fire(self) -> None:
        fresh = _dispatch_event(80, "builder", NOW - timedelta(minutes=30))
        stale = _dispatch_event(81, "builder", NOW - timedelta(hours=2))
        proposals = stale_dispatch_detector([fresh, stale], now=NOW)
        task_ids = {p.task_id for p in proposals}
        assert 81 in task_ids
        assert 80 not in task_ids

    def test_empty_events_returns_empty(self) -> None:
        assert stale_dispatch_detector([], now=NOW) == []


# ---------------------------------------------------------------------------
# analyze() entrypoint
# ---------------------------------------------------------------------------


class TestFromAC_AnalyzeEntrypoint:  # noqa: N801
    """analyze() reads JSONL from audit_dir, applies window filter, returns list[AnalysisProposal]."""

    def test_reads_jsonl_and_returns_list(self, tmp_path: Path) -> None:
        base = NOW - timedelta(minutes=30)
        events = [_cd(i, "builder", "success", 1000, base + timedelta(seconds=i)) for i in range(3)]
        _write_jsonl(tmp_path / "audit.jsonl", events)
        result = analyze(audit_dir=tmp_path, now=NOW)
        assert isinstance(result, list)

    def test_proposals_are_analysis_proposal_instances(self, tmp_path: Path) -> None:
        base = NOW - timedelta(minutes=30)
        # 2 failures on same task — triggers repeated_failure
        events = [_cd(200, "builder", "failure", 1000, base + timedelta(seconds=i)) for i in range(2)]
        _write_jsonl(tmp_path / "audit.jsonl", events)
        result = analyze(audit_dir=tmp_path, now=NOW)
        assert all(isinstance(p, AnalysisProposal) for p in result)

    def test_window_filter_excludes_old_events(self, tmp_path: Path) -> None:
        """Events older than the analysis window must be excluded."""
        old = NOW - timedelta(days=30)
        events = [_cd(300, "builder", "failure", 1000, old + timedelta(seconds=i)) for i in range(2)]
        _write_jsonl(tmp_path / "audit.jsonl", events)
        # Default window is much shorter than 30 days — old events filtered out
        result = analyze(audit_dir=tmp_path, now=NOW)
        assert result == []

    def test_accepts_now_parameter(self, tmp_path: Path) -> None:
        """analyze() must accept `now` keyword for deterministic stale detection."""
        events = [_dispatch_dict(400, "builder", NOW - timedelta(hours=2))]
        _write_jsonl(tmp_path / "audit.jsonl", events)
        # Should not raise TypeError for unexpected keyword argument
        result = analyze(audit_dir=tmp_path, now=NOW)
        assert isinstance(result, list)

    def test_reads_multiple_jsonl_files(self, tmp_path: Path) -> None:
        """All .jsonl files in audit_dir are read."""
        base = NOW - timedelta(minutes=30)
        _write_jsonl(tmp_path / "file1.jsonl", [_cd(1, "builder", "failure", 1000, base)])
        _write_jsonl(
            tmp_path / "file2.jsonl",
            [_cd(1, "builder", "failure", 1000, base + timedelta(seconds=1))],
        )
        result = analyze(audit_dir=tmp_path, now=NOW)
        # 2 failures on task 1 — repeated_failure should fire
        assert any(p.detector == "repeated_failure" for p in result)


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


class TestFromAC_FormatJson:  # noqa: N801
    """format_json outputs a valid JSON array of proposals."""

    def _proposal(self, detector: str = "test") -> AnalysisProposal:
        return AnalysisProposal(
            detector=detector,
            agent="builder",
            task_id=1,
            severity="warning",
            message="test message",
            evidence={"rate": 0.5},
        )

    def test_returns_valid_json_string(self) -> None:
        result = format_json([self._proposal()])
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_empty_list_produces_empty_json_array(self) -> None:
        result = format_json([])
        assert json.loads(result) == []

    def test_all_proposals_included(self) -> None:
        proposals = [self._proposal("high_error_rate"), self._proposal("slow_agent")]
        result = format_json(proposals)
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_json_contains_detector_field(self) -> None:
        result = format_json([self._proposal("my_detector")])
        parsed = json.loads(result)
        assert parsed[0]["detector"] == "my_detector"


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


class TestFromAC_FormatMarkdown:  # noqa: N801
    """format_markdown outputs markdown with tables."""

    def _proposal(self, detector: str = "test", agent: str = "builder") -> AnalysisProposal:
        return AnalysisProposal(
            detector=detector,
            agent=agent,
            task_id=1,
            severity="warning",
            message="test message",
            evidence={},
        )

    def test_returns_string(self) -> None:
        assert isinstance(format_markdown([self._proposal()]), str)

    def test_contains_markdown_table_pipe(self) -> None:
        result = format_markdown([self._proposal()])
        assert "|" in result

    def test_empty_list_returns_string(self) -> None:
        assert isinstance(format_markdown([]), str)

    def test_table_contains_detector_name(self) -> None:
        result = format_markdown([self._proposal("high_error_rate")])
        assert "high_error_rate" in result

    def test_table_contains_all_proposal_agents(self) -> None:
        proposals = [self._proposal("d1", "agent-a"), self._proposal("d2", "agent-b")]
        result = format_markdown(proposals)
        assert "agent-a" in result
        assert "agent-b" in result


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


class TestFromAC_EmptyInput:  # noqa: N801
    """analyze() returns [] for empty dir and for dir with no relevant events."""

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        assert analyze(audit_dir=tmp_path, now=NOW) == []

    def test_dir_with_no_jsonl_files_returns_empty_list(self, tmp_path: Path) -> None:
        (tmp_path / "notes.txt").write_text("not a jsonl file")
        assert analyze(audit_dir=tmp_path, now=NOW) == []

    def test_only_dispatch_events_within_1h_returns_empty(self, tmp_path: Path) -> None:
        """5 dispatch events < 1h old: no completions, no stale dispatches — no proposals."""
        base = NOW - timedelta(minutes=30)
        events = [_dispatch_dict(i, "builder", base + timedelta(seconds=i)) for i in range(5)]
        _write_jsonl(tmp_path / "audit.jsonl", events)
        assert analyze(audit_dir=tmp_path, now=NOW) == []
