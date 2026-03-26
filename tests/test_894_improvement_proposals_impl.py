"""Tests for task #894 — GREEN implementation: self-improvement proposal pipeline.

AC for #894:
1. Typed proposal-generation service reads existing EventStore observability aggregates.
2. Returns proposals with: target_agent, change_category (prompt/tools/skills),
   evidence summary, and suggested agent-definition change content.
3. Empty or insufficient metrics return an empty result or neutral no-op, never raises.
4. Never applies changes or prompts the user.
5. Unit tests from #893 pass.

These tests enforce the stricter #894 contract above, specifically:
- change_category must be one of {"prompt", "tools", "skills"} (AC item 2)
- suggested_change must describe agent-definition modifications (AC item 2)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import TypeAdapter

from owlbear.core.improvement_proposals import generate_proposals
from owlbear.core.observability import EventStore, ObservabilityEvent

# ---------------------------------------------------------------------------
# AC-specified valid change categories (AC item 2 contract)
# ---------------------------------------------------------------------------

_VALID_CHANGE_CATEGORIES: frozenset[str] = frozenset({"prompt", "tools", "skills"})

# Keywords that indicate agent-definition change content
# A suggestion about modifying how an agent is *defined* (not a runtime/infra fix)
_AGENT_DEFINITION_KEYWORDS: frozenset[str] = frozenset({
    "prompt",
    "instruction",
    "system",
    "skill",
    "definition",
})

# ---------------------------------------------------------------------------
# Shared helpers (mirrors test_improvement_proposals.py fixtures, no shared state)
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


def _high_error_events(total: int = 10, error_count: int = 8) -> list[ObservabilityEvent]:
    """Return *total* events where *error_count* fail — high error rate (≥ 0.5)."""
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
    """Return *count* events with very high latency (5 000 ms per call)."""
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
# AC item 2: change_category must be "prompt", "tools", or "skills"
# ---------------------------------------------------------------------------


class TestFromAC_ChangeCategorySpec:
    """AC2: change_category is 'prompt', 'tools', or 'skills' — never a runtime metric name.

    The AC explicitly enumerates the valid categories as agent-definition categories
    (prompt/tools/skills), not operational/runtime categories like 'reliability' or
    'performance'.  Every proposal returned by generate_proposals() must use one of
    the three enumerated values.
    """

    def test_error_rate_proposal_change_category_in_valid_set(self, tmp_path: Path) -> None:
        """High-error proposals must have change_category in {'prompt', 'tools', 'skills'}."""
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        proposals = generate_proposals(store)
        assert proposals, "high-error scenario must produce at least one proposal"
        for p in proposals:
            assert p.change_category in _VALID_CHANGE_CATEGORIES, (
                f"change_category {p.change_category!r} is not a valid agent-definition "
                f"category; expected one of {sorted(_VALID_CHANGE_CATEGORIES)}"
            )

    def test_latency_proposal_change_category_in_valid_set(self, tmp_path: Path) -> None:
        """High-latency proposals must have change_category in {'prompt', 'tools', 'skills'}."""
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        proposals = generate_proposals(store)
        assert proposals, "high-latency scenario must produce at least one proposal"
        for p in proposals:
            assert p.change_category in _VALID_CHANGE_CATEGORIES, (
                f"change_category {p.change_category!r} is not a valid agent-definition "
                f"category; expected one of {sorted(_VALID_CHANGE_CATEGORIES)}"
            )

    def test_change_category_is_not_runtime_operational_reliability(self, tmp_path: Path) -> None:
        """'reliability' is a runtime operational term, not an agent-definition category."""
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            assert p.change_category != "reliability", (
                "change_category must NOT be 'reliability' — the AC specifies agent-definition "
                "categories: prompt, tools, or skills"
            )

    def test_change_category_is_not_runtime_operational_performance(self, tmp_path: Path) -> None:
        """'performance' is a runtime operational term, not an agent-definition category."""
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        proposals = generate_proposals(store)
        assert proposals
        for p in proposals:
            assert p.change_category != "performance", (
                "change_category must NOT be 'performance' — the AC specifies agent-definition "
                "categories: prompt, tools, or skills"
            )

    def test_mixed_triggers_all_proposals_have_valid_category(self, tmp_path: Path) -> None:
        """All proposals from a mix of error and latency triggers use AC-specified categories."""
        events = _high_error_events(total=10, error_count=8) + [
            _event(
                tool_name="slow_search",
                agent_name="researcher",
                success=True,
                duration_ms=5000.0,
                minutes_ago=i + 20,
            )
            for i in range(5)
        ]
        store = _store_with_events(tmp_path, events)
        proposals = generate_proposals(store)
        assert proposals, "mixed high-error and high-latency scenario must produce proposals"
        for p in proposals:
            assert p.change_category in _VALID_CHANGE_CATEGORIES, (
                f"change_category {p.change_category!r} is not a valid agent-definition category; "
                f"expected one of {sorted(_VALID_CHANGE_CATEGORIES)}"
            )


# ---------------------------------------------------------------------------
# AC item 2: suggested_change describes agent-definition modification content
# ---------------------------------------------------------------------------


class TestFromAC_AgentDefinitionSuggestedChange:
    """AC2: suggested_change must describe agent-definition modifications.

    The AC says 'suggested agent-definition change content', meaning the suggestion
    must reference how to modify the owning agent's definition (its prompt, instruction
    set, skill configuration, or tool access) — not generic operational advice about
    infrastructure or runtime code.
    """

    def test_error_proposal_suggested_change_references_agent_definition(
        self, tmp_path: Path
    ) -> None:
        """Error-rate proposals must reference agent-definition concepts in suggested_change.

        The suggestion must include at least one term that refers to the agent's definition
        (e.g., 'prompt', 'instruction', 'system', 'skill', 'definition') because the
        AC requires *agent-definition* change content, not generic runtime advice.
        """
        store = _store_with_events(tmp_path, _high_error_events(total=10, error_count=8))
        proposals = generate_proposals(store)
        assert proposals, "high-error scenario must produce at least one proposal"
        for p in proposals:
            suggestion_lower = p.suggested_change.lower()
            keywords_found = {kw for kw in _AGENT_DEFINITION_KEYWORDS if kw in suggestion_lower}
            assert keywords_found, (
                f"suggested_change must reference agent-definition concepts "
                f"(one of: {sorted(_AGENT_DEFINITION_KEYWORDS)}), but got: "
                f"{p.suggested_change!r}"
            )

    def test_latency_proposal_suggested_change_references_agent_definition(
        self, tmp_path: Path
    ) -> None:
        """Latency proposals must reference agent-definition concepts in suggested_change.

        The suggestion must include at least one term that refers to the agent's definition
        (e.g., 'prompt', 'instruction', 'system', 'skill', 'definition') because the
        AC requires *agent-definition* change content, not generic operational tuning.
        """
        store = _store_with_events(tmp_path, _high_latency_events(count=5))
        proposals = generate_proposals(store)
        assert proposals, "high-latency scenario must produce at least one proposal"
        for p in proposals:
            suggestion_lower = p.suggested_change.lower()
            keywords_found = {kw for kw in _AGENT_DEFINITION_KEYWORDS if kw in suggestion_lower}
            assert keywords_found, (
                f"suggested_change must reference agent-definition concepts "
                f"(one of: {sorted(_AGENT_DEFINITION_KEYWORDS)}), but got: "
                f"{p.suggested_change!r}"
            )
