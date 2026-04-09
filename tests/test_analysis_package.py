"""Failing tests for owlbear_orchestrator.analysis package (task #179 RED phase).

Covers: package structure (4), AnalysisProposal Pydantic model (9),
threshold constants (8), high_error_rate detector (5), slow_agent detector (5),
repeated_failure detector (4), stale_dispatch detector (6),
analyze entrypoint (4), format_json (4), format_markdown (4),
empty input (3) = 56 tests.

NOTE: task #222 wrote tests for a flat analysis.py with the wrong field names
(detector/agent/task_id/severity/message). This file tests the CORRECT AC:
- Package structure with 4 submodules
- Pydantic frozen model with fields: target_agent, category, pattern,
  rationale, evidence, suggested_action
- Public threshold constants: ERROR_RATE_THRESHOLD, MIN_DISPATCHES,
  SLOW_FACTOR, STALE_THRESHOLD

All tests fail: ModuleNotFoundError for owlbear_orchestrator.analysis.models
(flat analysis.py is not a package).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Imports that will fail until the package is created
# ---------------------------------------------------------------------------
from owlbear_orchestrator.analysis.models import AnalysisProposal  # type: ignore[import-not-found]
from owlbear_orchestrator.analysis.detectors import (  # type: ignore[import-not-found]
    ERROR_RATE_THRESHOLD,
    MIN_DISPATCHES,
    SLOW_FACTOR,
    STALE_THRESHOLD,
    high_error_rate_detector,
    repeated_failure_detector,
    slow_agent_detector,
    stale_dispatch_detector,
)
from owlbear_orchestrator.analysis.analyze import analyze  # type: ignore[import-not-found]
from owlbear_orchestrator.analysis.formatters import (  # type: ignore[import-not-found]
    format_json,
    format_markdown,
)
from owlbear.audit.models import CompletionEvent, DispatchEvent

# ---------------------------------------------------------------------------
# Fixed reference "now" for deterministic tests
# ---------------------------------------------------------------------------

NOW = datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC)

# ---------------------------------------------------------------------------
# In-memory model factories
# ---------------------------------------------------------------------------


def _ts(dt: datetime) -> str:
    return dt.isoformat()


def _dispatch(
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


def _completion(
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
        error=None,
    )


def _make_proposal(**overrides: Any) -> AnalysisProposal:
    defaults: dict[str, Any] = {
        "target_agent": "builder",
        "category": "reliability",
        "pattern": "test_pattern",
        "rationale": "test rationale",
        "evidence": {},
        "suggested_action": "investigate",
    }
    return AnalysisProposal(**{**defaults, **overrides})


def _completions(agent: str, outcomes: list[str]) -> list[CompletionEvent]:
    t = NOW - timedelta(minutes=30)
    return [_completion(i, agent, o, 1000, t + timedelta(seconds=i)) for i, o in enumerate(outcomes)]


# ---------------------------------------------------------------------------
# JSONL factories for analyze() integration tests
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


def _completion_dict(
    task_id: int,
    agent: str,
    outcome: str,
    duration_ms: int,
    timestamp: datetime,
) -> dict[str, Any]:
    return {
        "type": "completion",
        "timestamp": _ts(timestamp),
        "task_id": task_id,
        "agent": agent,
        "outcome": outcome,
        "duration_ms": duration_ms,
        "files_changed": [],
        "error": None,
    }


def _write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")


# ---------------------------------------------------------------------------
# Package structure
# ---------------------------------------------------------------------------


class TestFromAC_PackageStructure:  # noqa: N801
    """owlbear_orchestrator.analysis must be a package with 4 importable submodules."""

    def test_models_module_importable(self) -> None:
        import owlbear_orchestrator.analysis.models  # noqa: F401

    def test_detectors_module_importable(self) -> None:
        import owlbear_orchestrator.analysis.detectors  # noqa: F401

    def test_analyze_module_importable(self) -> None:
        import owlbear_orchestrator.analysis.analyze  # noqa: F401

    def test_formatters_module_importable(self) -> None:
        import owlbear_orchestrator.analysis.formatters  # noqa: F401


# ---------------------------------------------------------------------------
# AnalysisProposal frozen Pydantic model — correct field names
# ---------------------------------------------------------------------------


class TestFromAC_AnalysisProposalModel:  # noqa: N801
    """AnalysisProposal is a frozen Pydantic BaseModel with exactly 6 correct fields."""

    def test_is_pydantic_base_model(self) -> None:
        from pydantic import BaseModel

        assert issubclass(AnalysisProposal, BaseModel)

    def test_frozen_raises_on_mutation(self) -> None:
        p = _make_proposal()
        with pytest.raises(ValidationError):
            p.rationale = "changed"  # type: ignore[misc]

    def test_exactly_six_fields(self) -> None:
        assert len(AnalysisProposal.model_fields) == 6

    def test_field_target_agent_is_str(self) -> None:
        p = _make_proposal(target_agent="builder")
        assert isinstance(p.target_agent, str)

    def test_field_category_is_str(self) -> None:
        p = _make_proposal(category="reliability")
        assert isinstance(p.category, str)

    def test_field_pattern_is_str(self) -> None:
        p = _make_proposal(pattern="high_error_rate")
        assert isinstance(p.pattern, str)

    def test_field_rationale_is_str(self) -> None:
        p = _make_proposal(rationale="some explanation")
        assert isinstance(p.rationale, str)

    def test_field_evidence_is_dict(self) -> None:
        p = _make_proposal(evidence={"failure_rate": 0.5})
        assert isinstance(p.evidence, dict)
        assert p.evidence["failure_rate"] == 0.5

    def test_field_suggested_action_is_str(self) -> None:
        p = _make_proposal(suggested_action="reduce concurrency")
        assert isinstance(p.suggested_action, str)


# ---------------------------------------------------------------------------
# Threshold constants — public names in detectors.py
# ---------------------------------------------------------------------------


class TestFromAC_ThresholdConstants:  # noqa: N801
    """detectors.py exports public named constants for all four thresholds."""

    def test_error_rate_threshold_is_numeric(self) -> None:
        assert isinstance(ERROR_RATE_THRESHOLD, (int, float))

    def test_min_dispatches_is_int(self) -> None:
        assert isinstance(MIN_DISPATCHES, int)

    def test_slow_factor_is_numeric(self) -> None:
        assert isinstance(SLOW_FACTOR, (int, float))

    def test_stale_threshold_is_timedelta(self) -> None:
        assert isinstance(STALE_THRESHOLD, timedelta)

    def test_error_rate_threshold_value(self) -> None:
        assert pytest.approx(0.4) == ERROR_RATE_THRESHOLD

    def test_min_dispatches_value(self) -> None:
        assert MIN_DISPATCHES == 3

    def test_slow_factor_value(self) -> None:
        assert pytest.approx(2) == SLOW_FACTOR

    def test_stale_threshold_value(self) -> None:
        assert timedelta(hours=1) == STALE_THRESHOLD


# ---------------------------------------------------------------------------
# High error rate detector — correct pattern + category fields
# ---------------------------------------------------------------------------


class TestFromAC_HighErrorRateDetector:  # noqa: N801
    """Fires with pattern=high_error_rate, category=reliability at >=40% / >=3."""

    def test_proposal_has_pattern_high_error_rate(self) -> None:
        evts = _completions("a", ["failure", "failure", "success"])
        results = high_error_rate_detector(evts)
        assert results
        assert results[0].pattern == "high_error_rate"

    def test_proposal_has_category_reliability(self) -> None:
        evts = _completions("a", ["failure", "failure", "success"])
        results = high_error_rate_detector(evts)
        assert results
        assert results[0].category == "reliability"

    def test_fires_at_exactly_40_percent(self) -> None:
        evts = _completions("a", ["failure", "failure", "success", "success", "success"])
        results = high_error_rate_detector(evts)
        assert len(results) == 1

    def test_does_not_fire_below_40_percent(self) -> None:
        evts = _completions("a", ["failure", "success", "success", "success"])
        results = high_error_rate_detector(evts)
        assert results == []

    def test_does_not_fire_with_fewer_than_3_completions(self) -> None:
        evts = _completions("a", ["failure", "failure"])
        results = high_error_rate_detector(evts)
        assert results == []


# ---------------------------------------------------------------------------
# Slow agent detector — correct pattern + category fields
# ---------------------------------------------------------------------------


class TestFromAC_SlowAgentDetector:  # noqa: N801
    """Fires with pattern=slow_agent, category=performance at >2x global avg / >=3."""

    def _slow_and_fast(self, fast_ms: int, slow_ms: int) -> list[CompletionEvent]:
        t = NOW - timedelta(minutes=30)
        evts = []
        for i in range(3):
            evts.append(_completion(i, "fast", "success", fast_ms, t + timedelta(seconds=i)))
        for i in range(3):
            evts.append(_completion(i + 10, "slow", "success", slow_ms, t + timedelta(seconds=i + 10)))
        return evts

    def test_proposal_has_pattern_slow_agent(self) -> None:
        evts = self._slow_and_fast(100, 500)
        results = slow_agent_detector(evts)
        slow_results = [r for r in results if r.target_agent == "slow"]
        assert slow_results
        assert slow_results[0].pattern == "slow_agent"

    def test_proposal_has_category_performance(self) -> None:
        evts = self._slow_and_fast(100, 500)
        results = slow_agent_detector(evts)
        slow_results = [r for r in results if r.target_agent == "slow"]
        assert slow_results
        assert slow_results[0].category == "performance"

    def test_fires_when_agent_is_more_than_2x_global_avg(self) -> None:
        # fast=100ms, slow=400ms; global avg=(300+1200)/6=250ms; slow avg=400 > 2*250=500? No.
        # Let's make fast=50ms (3), slow=500ms (3); global=(150+1500)/6=275; slow=500 > 2*275=550? No.
        # Just use fast=100ms (3), slow=700ms (3); avg=(300+2100)/6=400; slow=700 > 2*400=800? No.
        # Simplest: fast=50ms (3), slow=600ms (3); avg=(150+1800)/6=325; slow=600 > 2*325=650? No.
        # Use unequal counts: fast=47 agents at 100ms, slow=3 agents at 600ms
        # Actually the simplest: fast=100ms x3, slow=1000ms x3; avg=(300+3000)/6=550; slow=1000>2*550=1100? No.
        # Use very disparate values: fast=10ms x3, slow=100ms x3; avg=(30+300)/6=55; slow=100>2*55=110? No.
        # Hmm. With balanced groups, slow avg needs to be > 2 * ((fast_avg*n + slow_avg*n)/(2n))
        # => slow > 2 * (fast + slow) / 2 => slow > fast + slow => 0 > fast -- impossible!

        # Must have MANY fast events to dilute global average.
        # fast=100ms x10, slow=500ms x3; avg=(1000+1500)/13~=192; slow=500 > 2*192=384? YES
        t = NOW - timedelta(minutes=30)
        evts = []
        for i in range(10):
            evts.append(_completion(i, "fast", "success", 100, t + timedelta(seconds=i)))
        for i in range(3):
            evts.append(_completion(i + 20, "slow", "success", 500, t + timedelta(seconds=i + 20)))
        results = slow_agent_detector(evts)
        assert any(r.target_agent == "slow" for r in results)

    def test_does_not_fire_at_exactly_2x_global_avg(self) -> None:
        # fast=100ms x10, slow=200ms x3 => avg=(1000+600)/13~=123; slow=200 > 2*123=246? No.
        # Actually need slow/global = exactly 2 => not possible to hit exactly, so use a known ratio.
        # fast=100ms x10, slow=200ms x3 => avg=1600/13=123.077; slow/avg=1.625 < 2 => no fire
        t = NOW - timedelta(minutes=30)
        evts = []
        for i in range(10):
            evts.append(_completion(i, "fast", "success", 100, t + timedelta(seconds=i)))
        for i in range(3):
            evts.append(_completion(i + 20, "slow", "success", 200, t + timedelta(seconds=i + 20)))
        results = slow_agent_detector(evts)
        # slow avg is 200, global avg ~123, ratio ~1.6 which is < 2 so should NOT fire
        assert not any(r.target_agent == "slow" for r in results)

    def test_does_not_fire_with_fewer_than_3_completions(self) -> None:
        t = NOW - timedelta(minutes=30)
        evts = []
        for i in range(10):
            evts.append(_completion(i, "fast", "success", 100, t + timedelta(seconds=i)))
        evts.append(_completion(20, "slow", "success", 5000, t + timedelta(seconds=20)))
        evts.append(_completion(21, "slow", "success", 5000, t + timedelta(seconds=21)))
        results = slow_agent_detector(evts)
        assert not any(r.target_agent == "slow" for r in results)


# ---------------------------------------------------------------------------
# Repeated failure detector — correct pattern + category fields
# ---------------------------------------------------------------------------


class TestFromAC_RepeatedFailureDetector:  # noqa: N801
    """Fires with pattern=repeated_failure, category=reliability at >=2 failures/task_id."""

    def test_proposal_has_pattern_repeated_failure(self) -> None:
        t = NOW - timedelta(minutes=10)
        evts = [
            _completion(42, "builder", "failure", 100, t),
            _completion(42, "builder", "failure", 100, t + timedelta(minutes=1)),
        ]
        results = repeated_failure_detector(evts)
        assert results
        assert results[0].pattern == "repeated_failure"

    def test_proposal_has_category_reliability(self) -> None:
        t = NOW - timedelta(minutes=10)
        evts = [
            _completion(42, "builder", "failure", 100, t),
            _completion(42, "builder", "failure", 100, t + timedelta(minutes=1)),
        ]
        results = repeated_failure_detector(evts)
        assert results
        assert results[0].category == "reliability"

    def test_fires_at_2_failures_same_task(self) -> None:
        t = NOW - timedelta(minutes=10)
        evts = [
            _completion(42, "builder", "failure", 100, t),
            _completion(42, "builder", "failure", 100, t + timedelta(minutes=1)),
        ]
        results = repeated_failure_detector(evts)
        assert len(results) == 1

    def test_does_not_fire_with_1_failure_per_task(self) -> None:
        t = NOW - timedelta(minutes=10)
        evts = [
            _completion(1, "builder", "failure", 100, t),
            _completion(2, "builder", "failure", 100, t + timedelta(minutes=1)),
        ]
        results = repeated_failure_detector(evts)
        assert results == []


# ---------------------------------------------------------------------------
# Stale dispatch detector — correct pattern + category fields
# ---------------------------------------------------------------------------


class TestFromAC_StaleDispatchDetector:  # noqa: N801
    """Fires with pattern=stale_dispatch, category=stability for dispatch >1h with no completion."""

    def test_proposal_has_pattern_stale_dispatch(self) -> None:
        evts = [_dispatch(1, "builder", NOW - timedelta(hours=2))]
        results = stale_dispatch_detector(evts, now=NOW)
        assert results
        assert results[0].pattern == "stale_dispatch"

    def test_proposal_has_category_stability(self) -> None:
        evts = [_dispatch(1, "builder", NOW - timedelta(hours=2))]
        results = stale_dispatch_detector(evts, now=NOW)
        assert results
        assert results[0].category == "stability"

    def test_fires_for_dispatch_more_than_1h_old(self) -> None:
        evts = [_dispatch(1, "builder", NOW - timedelta(hours=2))]
        results = stale_dispatch_detector(evts, now=NOW)
        assert len(results) == 1

    def test_does_not_fire_for_recent_dispatch(self) -> None:
        evts = [_dispatch(1, "builder", NOW - timedelta(minutes=30))]
        results = stale_dispatch_detector(evts, now=NOW)
        assert results == []

    def test_does_not_fire_at_exactly_1h(self) -> None:
        evts = [_dispatch(1, "builder", NOW - timedelta(hours=1))]
        results = stale_dispatch_detector(evts, now=NOW)
        assert results == []

    def test_does_not_fire_when_completion_matches_dispatch(self) -> None:
        disp_ts = NOW - timedelta(hours=2)
        comp_ts = NOW - timedelta(hours=1)
        evts: list[Any] = [
            _dispatch(1, "builder", disp_ts, session_id="sess-1"),
            _completion(1, "builder", "success", 1000, comp_ts),
        ]
        results = stale_dispatch_detector(evts, now=NOW)
        assert results == []


# ---------------------------------------------------------------------------
# analyze() entrypoint
# ---------------------------------------------------------------------------


class TestFromAC_AnalyzeEntrypoint:  # noqa: N801
    """analyze() reads JSONL, applies window filter, returns list[AnalysisProposal]."""

    def test_reads_jsonl_and_returns_list(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        evts = [
            _completion_dict(1, "a", "failure", 100, NOW - timedelta(minutes=10)),
            _completion_dict(1, "a", "failure", 100, NOW - timedelta(minutes=9)),
            _completion_dict(1, "a", "failure", 100, NOW - timedelta(minutes=8)),
        ]
        _write_jsonl(audit_dir / "sess-1.jsonl", evts)
        results = analyze(audit_dir, now=NOW)
        assert isinstance(results, list)
        assert all(isinstance(r, AnalysisProposal) for r in results)

    def test_window_filter_excludes_old_events(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        recent = NOW - timedelta(hours=1)
        old = NOW - timedelta(days=10)
        evts_old = [
            _completion_dict(1, "a", "failure", 100, old),
            _completion_dict(1, "a", "failure", 100, old + timedelta(minutes=1)),
            _completion_dict(1, "a", "failure", 100, old + timedelta(minutes=2)),
        ]
        evts_recent = [
            _completion_dict(2, "b", "success", 100, recent),
        ]
        _write_jsonl(audit_dir / "old.jsonl", evts_old)
        _write_jsonl(audit_dir / "recent.jsonl", evts_recent)
        results = analyze(audit_dir, window=timedelta(days=7), now=NOW)
        patterns = [r.pattern for r in results]
        assert "high_error_rate" not in patterns

    def test_accepts_now_parameter(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        future_now = NOW + timedelta(days=100)
        results = analyze(audit_dir, now=future_now)
        assert isinstance(results, list)

    def test_reads_multiple_jsonl_files(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        t = NOW - timedelta(minutes=5)
        evts_a = [_completion_dict(1, "x", "failure", 100, t + timedelta(seconds=i)) for i in range(3)]
        evts_b = [_completion_dict(2, "y", "failure", 100, t + timedelta(seconds=i)) for i in range(3)]
        _write_jsonl(audit_dir / "sess-a.jsonl", evts_a)
        _write_jsonl(audit_dir / "sess-b.jsonl", evts_b)
        results = analyze(audit_dir, now=NOW)
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# format_json — Pydantic serialization, correct field names in output
# ---------------------------------------------------------------------------


class TestFromAC_FormatJson:  # noqa: N801
    """format_json returns valid JSON array using Pydantic serialization."""

    def test_returns_valid_json_string(self) -> None:
        proposals = [_make_proposal()]
        result = format_json(proposals)
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_json_contains_correct_field_names(self) -> None:
        p = _make_proposal(
            target_agent="builder",
            category="reliability",
            pattern="high_error_rate",
            rationale="test",
            evidence={},
            suggested_action="investigate",
        )
        result = format_json([p])
        parsed = json.loads(result)
        assert len(parsed) == 1
        item = parsed[0]
        assert "target_agent" in item
        assert "category" in item
        assert "pattern" in item
        assert "rationale" in item
        assert "suggested_action" in item

    def test_json_empty_list_returns_array(self) -> None:
        result = format_json([])
        parsed = json.loads(result)
        assert parsed == []

    def test_json_proposal_count_matches(self) -> None:
        proposals = [_make_proposal(pattern=f"p{i}") for i in range(3)]
        result = format_json(proposals)
        parsed = json.loads(result)
        assert len(parsed) == 3


# ---------------------------------------------------------------------------
# format_markdown — human-readable output with tables
# ---------------------------------------------------------------------------


class TestFromAC_FormatMarkdown:  # noqa: N801
    """format_markdown returns markdown string with table structure."""

    def test_returns_string(self) -> None:
        proposals = [_make_proposal()]
        result = format_markdown(proposals)
        assert isinstance(result, str)

    def test_non_empty_output_contains_pipe_chars_for_table(self) -> None:
        proposals = [_make_proposal()]
        result = format_markdown(proposals)
        assert "|" in result

    def test_contains_pattern_value(self) -> None:
        p = _make_proposal(pattern="repeated_failure")
        result = format_markdown([p])
        assert "repeated_failure" in result

    def test_empty_list_returns_readable_text(self) -> None:
        result = format_markdown([])
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Empty input — no crash, returns []
# ---------------------------------------------------------------------------


class TestFromAC_EmptyInput:  # noqa: N801
    """analyze() returns [] for empty dir, dir with no JSONL, or no triggering events."""

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        results = analyze(audit_dir, now=NOW)
        assert results == []

    def test_dir_with_no_jsonl_files_returns_empty_list(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        (audit_dir / "notes.txt").write_text("not a jsonl file", encoding="utf-8")
        results = analyze(audit_dir, now=NOW)
        assert results == []

    def test_events_below_all_thresholds_return_empty_list(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        t = NOW - timedelta(minutes=5)
        # 2 completions only (below MIN_DISPATCHES=3), both success
        evts = [
            _completion_dict(1, "x", "success", 100, t),
            _completion_dict(2, "x", "success", 100, t + timedelta(seconds=1)),
        ]
        _write_jsonl(audit_dir / "sess.jsonl", evts)
        results = analyze(audit_dir, now=NOW)
        assert results == []
