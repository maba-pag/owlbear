"""Engine activity/session regression tests.

Promoted from the task-scoped suite for task #1063.

Original coverage preserved from the task-scoped suite:
  AC-C42: Engine methods (claim, edit, move, end_work, sweep) emit ActivityEvent
          entries via append_activity_event.
  AC-C43: list_sessions(filter=...) derives SessionRecord values from activity.jsonl
          with active/all/blocked-or-rejected/released filter semantics per spec.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# Provenance: promoted from task-scoped suite for task #1063.

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""

_TASK_TEMPLATE = """\
---
id: {task_id}
title: Task {task_id}
status: {status}
priority: important
created: "2026-04-21T10:00:00+00:00"
updated: "2026-04-21T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Task body.
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal board. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(kanban_dir: Path, task_id: int, status: str = "todo") -> None:
    content = _TASK_TEMPLATE.format(task_id=task_id, status=status)
    filename = f"{task_id}-task-{task_id}.md"
    (kanban_dir / "tasks" / filename).write_text(content, encoding="utf-8")


def _read_activity(kanban_dir: Path) -> list[dict]:
    """Parse activity.jsonl and return all valid event dicts."""
    activity_path = kanban_dir / "activity.jsonl"
    if not activity_path.exists():
        return []
    events: list[dict] = []
    for raw_line in activity_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            events.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return events


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board(tmp_path: Path) -> Path:
    """Board with 3 tasks and activity logging enabled."""
    kanban_dir = _make_board(tmp_path)
    for i in (1, 2, 3):
        _write_task(kanban_dir, i, status="todo")
    return kanban_dir


@pytest.fixture
def engine(board: Path) -> KanbanEngine:
    """KanbanEngine with activity_log=True; agent_name is session-generated."""
    eng = KanbanEngine(board, activity_log=True)
    eng.list_tasks()  # populate id→filename cache
    return eng


# ---------------------------------------------------------------------------
# TestFromAC_SessionAgentField — AC-C42 + AC-C43
#
# AC-C42 mandates that claim events store the agent name in detail.
# AC-C43 mandates that list_sessions() derives SessionRecord values from
# activity.jsonl — including surfacing the agent name as session.agent.
# ---------------------------------------------------------------------------


class TestFromAC_SessionAgentField:
    """AC-C42 + AC-C43: claim event detail (agent name) must surface as session.agent.

    The claim event emitted by the engine stores the agent_name in its `detail`
    field.  list_sessions() must derive this value and expose it on the returned
    session record as the `agent` attribute.
    """

    def test_session_has_agent_attribute(self, engine: KanbanEngine) -> None:
        """Closed session from list_sessions() exposes an `agent` attribute."""
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert task_sessions, "Expected a session for task 1"
        _ = task_sessions[-1].agent  # AttributeError if field absent

    def test_open_session_has_agent_attribute(self, engine: KanbanEngine) -> None:
        """Open (running) session from list_sessions() exposes an `agent` attribute."""
        engine.claim_task("2")
        sessions = engine.list_sessions(filter="active")
        task_sessions = [s for s in sessions if s.task_id == 2]
        assert task_sessions, "Expected a running session for task 2"
        _ = task_sessions[-1].agent  # AttributeError if field absent

    def test_agent_equals_engine_agent_name_from_claim(self, engine: KanbanEngine, board: Path) -> None:
        """session.agent equals the agent_name stored in the claim event's detail field.

        AC-C42: engine stores agent_name as the claim event detail.
        AC-C43: list_sessions() derives session.agent from that detail.
        """
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")

        expected_agent = engine.agent_name

        # Verify the claim event detail IS the agent name (AC-C42)
        events = _read_activity(board)
        claim_events = [e for e in events if e.get("action") == "claim" and e.get("task_id") == 1]
        assert claim_events, "Expected a claim event for task 1"
        assert claim_events[-1].get("detail") == expected_agent, (
            f"claim event detail must equal engine agent_name {expected_agent!r}; "
            f"got {claim_events[-1].get('detail')!r}"
        )

        # Verify list_sessions() surfaces that detail as session.agent (AC-C43)
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert task_sessions, "Expected session for task 1"
        assert task_sessions[-1].agent == expected_agent, (  # type: ignore[attr-defined]
            f"session.agent must equal the claim event detail {expected_agent!r}; got {task_sessions[-1].agent!r}"  # type: ignore[attr-defined]
        )

    def test_agent_derives_from_claim_detail_not_actor(self, engine: KanbanEngine, board: Path) -> None:
        """session.agent comes from claim event `detail`, not from a hypothetical `actor` field.

        This guards against using the wrong source for agent name derivation.
        The claim event emitted by the engine has detail=agent_name and no
        separate 'actor' key.
        """
        engine.claim_task("1")
        events = _read_activity(board)
        claim_events = [e for e in events if e.get("action") == "claim" and e.get("task_id") == 1]
        assert claim_events, "Expected a claim event for task 1"
        # Engine-emitted events must NOT have an 'actor' field
        assert "actor" not in claim_events[-1], (
            "Engine claim events must not include an 'actor' field; agent name lives in 'detail'"
        )

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert task_sessions, "Expected a session for task 1"
        # session.agent must equal the claim event's detail value
        assert task_sessions[-1].agent == claim_events[-1]["detail"]  # type: ignore[attr-defined]

    def test_agent_for_released_session(self, engine: KanbanEngine) -> None:
        """Released session exposes the correct agent name."""
        expected_agent = engine.agent_name
        engine.claim_task("3")
        engine.release_task("3")
        sessions = engine.list_sessions(filter="released")
        task_sessions = [s for s in sessions if s.task_id == 3]
        assert task_sessions, "Expected released session for task 3"
        assert task_sessions[-1].agent == expected_agent  # type: ignore[attr-defined]

    def test_agent_for_blocked_session(self, engine: KanbanEngine) -> None:
        """Blocked session (end_work outcome=block) exposes the correct agent name."""
        expected_agent = engine.agent_name
        engine.claim_task("1")
        engine.end_work("1", note="blocked", outcome="block", block_reason="dep missing")
        sessions = engine.list_sessions(filter="blocked-or-rejected")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert task_sessions, "Expected blocked session for task 1"
        assert task_sessions[-1].agent == expected_agent  # type: ignore[attr-defined]

    def test_agent_for_rejected_session(self, engine: KanbanEngine) -> None:
        """Rejected session (end_work outcome=reject) exposes the correct agent name."""
        expected_agent = engine.agent_name
        engine.claim_task("1")
        engine.end_work("1", note="moved back", outcome="reject", move_to="research")
        sessions = engine.list_sessions(filter="blocked-or-rejected")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert task_sessions, "Expected rejected session for task 1"
        assert task_sessions[-1].agent == expected_agent  # type: ignore[attr-defined]

    def test_reclaim_second_session_has_correct_agent(self, engine: KanbanEngine) -> None:
        """After re-claim, the second session's agent comes from the second claim event."""
        engine.claim_task("1")
        engine.release_task("1")

        eng2 = KanbanEngine(engine._kanban_dir, activity_log=True)
        eng2.list_tasks()
        agent_name_2 = eng2.agent_name
        eng2.claim_task("1")

        sessions = engine.list_sessions(filter="all")
        task_sessions = sorted(
            [s for s in sessions if s.task_id == 1],
            key=lambda s: s.started_at,
        )
        assert len(task_sessions) >= 2, "Expected two distinct sessions for task 1"
        # Second session must carry the second agent's name
        assert task_sessions[-1].agent == agent_name_2  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TestFromAC_SessionDurationField — AC-C43
# ---------------------------------------------------------------------------


class TestFromAC_SessionDurationField:
    """AC-C43: list_sessions() sessions expose a `duration` attribute (seconds float).

    The WorkSession dataclass exported from owlbear_kanban already declares
    `duration: float | None`.  SessionRecord (the current return type) only has
    `duration_s`.  The builder must add `duration` so callers can use either name,
    or switch the return type to WorkSession.
    """

    def test_closed_session_has_duration_attribute(self, engine: KanbanEngine) -> None:
        """Closed session exposes a `duration` attribute."""
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert task_sessions, "Expected session for task 1"
        _ = task_sessions[-1].duration  # AttributeError if field absent

    def test_open_session_has_duration_attribute(self, engine: KanbanEngine) -> None:
        """Open session exposes a `duration` attribute."""
        engine.claim_task("2")
        sessions = engine.list_sessions(filter="active")
        task_sessions = [s for s in sessions if s.task_id == 2]
        assert task_sessions, "Expected active session for task 2"
        _ = task_sessions[-1].duration  # AttributeError if field absent

    def test_closed_session_duration_is_non_negative_float(self, engine: KanbanEngine) -> None:
        """Closed session has duration >= 0.0."""
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert task_sessions, "Expected session for task 1"
        duration = task_sessions[-1].duration  # type: ignore[attr-defined]
        assert duration is not None, "duration must not be None for a closed session"
        assert duration >= 0.0, f"duration must be non-negative; got {duration}"

    def test_open_session_duration_is_none(self, engine: KanbanEngine) -> None:
        """Open (running) session has duration=None."""
        engine.claim_task("2")
        sessions = engine.list_sessions(filter="active")
        task_sessions = [s for s in sessions if s.task_id == 2]
        assert task_sessions, "Expected active session for task 2"
        duration = task_sessions[-1].duration  # type: ignore[attr-defined]
        assert duration is None, f"Open session must have duration=None; got {duration!r}"

    def test_released_session_has_duration(self, engine: KanbanEngine) -> None:
        """Released session (release_task) has duration set (non-None)."""
        engine.claim_task("3")
        engine.release_task("3")
        sessions = engine.list_sessions(filter="released")
        task_sessions = [s for s in sessions if s.task_id == 3]
        assert task_sessions, "Expected released session for task 3"
        duration = task_sessions[-1].duration  # type: ignore[attr-defined]
        assert duration is not None, "Released session must have duration set"
        assert duration >= 0.0


# ---------------------------------------------------------------------------
# TestFromAC_WorkSessionExport — AC-C43 (WorkSession public contract)
# ---------------------------------------------------------------------------


class TestFromAC_WorkSessionExport:
    """AC-C43: WorkSession is exported from owlbear_kanban and usable as session type.

    The WorkSession dataclass (engine.py) is already in owlbear_kanban.__all__.
    These tests verify that list_sessions() returns objects compatible with
    the WorkSession field contract (agent + duration).
    """

    def test_list_sessions_result_compatible_with_worksession_agent_field(self, engine: KanbanEngine) -> None:
        """list_sessions() returns objects with an `agent` field, compatible with WorkSession."""
        engine.claim_task("1")
        sessions = engine.list_sessions(filter="all")
        assert sessions
        session = sessions[0]
        # This fails if SessionRecord is returned without agent field
        assert hasattr(session, "agent"), (
            "list_sessions() must return objects with `agent` field (WorkSession contract)"
        )

    def test_list_sessions_result_compatible_with_worksession_duration_field(self, engine: KanbanEngine) -> None:
        """list_sessions() returns objects with a `duration` field, compatible with WorkSession."""
        engine.claim_task("1")
        sessions = engine.list_sessions(filter="all")
        assert sessions
        session = sessions[0]
        # This fails if SessionRecord is returned without duration field
        assert hasattr(session, "duration"), (
            "list_sessions() must return objects with `duration` field (WorkSession contract)"
        )

    def test_ac_c43_filter_active_excludes_session_with_agent_field_access(self, engine: KanbanEngine) -> None:
        """Active filter excludes closed sessions; remaining sessions all have agent field."""
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")
        engine.claim_task("2")  # Open/running
        sessions = engine.list_sessions(filter="active")
        assert sessions, "Expected at least one active session"
        for s in sessions:
            assert hasattr(s, "agent"), "Every session in active filter must have agent field"
            assert s.agent is not None, "Running session agent must not be None"  # type: ignore[attr-defined]
