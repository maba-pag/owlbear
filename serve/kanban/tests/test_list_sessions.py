"""Tests for task #923: list_sessions() engine helper.

AC coverage:
  1.  One session per claim cycle (claim → close event)
    2.  Session state: completed  (end_work success)
    3.  Session state: blocked  (end_work fail)
    4.  Session state: blocked  (end_work block)
    5.  Session state: rejected (end_work reject)
  6.  Session state: released (release event)
  7.  Session state: running (open claim, age < timeout)
  8.  Session state: stuck  (open claim, age ≥ timeout, no recent activity)
  9.  Stuck anti-test: old claim with recent mid-session activity remains running
  10. sweep-release: release + sweep-release pair closes exactly one session (no phantom)
  11. Filter: active-only (default) returns running + stuck only
  12. Filter: all returns every session regardless of state
    13. Filter: blocked-or-rejected returns blocked + rejected
  14. Filter: released returns released sessions only
  15. Empty activity log returns empty list
  16. Missing activity log returns empty list (no crash)
  17. Malformed JSON line skipped gracefully (valid sessions still returned)
  18. Incomplete entry (missing required fields) skipped gracefully
  19. Same task re-claimed after release → two distinct sessions
  20. Multi-task interleaved events → correct session assignment per task

All tests FAIL in RED phase — list_sessions() not yet implemented on KanbanEngine.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 100
archive_dir: archive
activity_log: true
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board with activity_log enabled. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _ts(delta: timedelta | None = None) -> str:
    """Return an ISO-8601 UTC timestamp offset by *delta* from now. Defaults to now."""
    t = datetime.now(tz=UTC)
    if delta is not None:
        t = t + delta
    return t.isoformat()


def _entry(
    *,
    action: str,
    task_id: int,
    detail: str,
    actor: str = "test-agent",
    ts: str | None = None,
) -> dict:
    """Build one activity log entry dict."""
    return {
        "timestamp": ts or _ts(),
        "action": action,
        "task_id": task_id,
        "detail": detail,
        "actor": actor,
    }


def _write_log(log_path: Path, entries: list[dict]) -> None:
    """Write a list of entry dicts as JSONL to *log_path*."""
    with log_path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board(tmp_path: Path) -> Path:
    """Minimal board with activity_log enabled. Returns kanban_dir."""
    return _make_board(tmp_path)


@pytest.fixture
def engine(board: Path) -> KanbanEngine:
    """KanbanEngine for the board fixture."""
    return KanbanEngine(board, activity_log=True)


@pytest.fixture
def log_path(board: Path) -> Path:
    """Path to activity.jsonl inside the board fixture."""
    return board / "activity.jsonl"


# ---------------------------------------------------------------------------
# TestFromAC_ListSessions
# ---------------------------------------------------------------------------


class TestFromAC_ListSessions:
    """Verifies list_sessions() engine helper contract per task #923 AC."""

    # ------------------------------------------------------------------ AC 1: claim cycle derivation

    def test_claim_to_end_work_is_one_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """Claim followed by end_work produces exactly one session for that task."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=1,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=1, detail="success: todo -> in-progress"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert len(task_sessions) == 1

    # ------------------------------------------------------------------ AC 2: completed

    def test_end_work_success_state_is_completed_pass(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with success detail prefix produces state=completed."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=1,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=1, detail="success: todo -> in-progress"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 1]
        assert states == ["completed"]

    # ------------------------------------------------------------------ AC 3: blocked (fail)

    def test_end_work_fail_state_is_completed_fail(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with 'outcome=fail' detail produces state=blocked."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=2,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=2, detail="outcome=fail"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 2]
        assert states == ["blocked"]

    # ------------------------------------------------------------------ AC 4: blocked (block)

    def test_end_work_block_maps_to_completed_fail(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with 'blocked:' detail maps to blocked state."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=3,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=3, detail="blocked: needs DB migration"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 3]
        assert states == ["blocked"]

    # ------------------------------------------------------------------ AC 5: rejected

    def test_end_work_reject_state_is_completed_rejected(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with 'reject:' detail prefix produces state=rejected."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=4,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=4, detail="reject: in-progress -> todo"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 4]
        assert states == ["rejected"]

    # ------------------------------------------------------------------ AC 6: released

    def test_release_event_state_is_released(self, engine: KanbanEngine, log_path: Path) -> None:
        """A release event closes the session with state=released."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=5,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="release", task_id=5, detail="test-agent"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 5]
        assert states == ["released"]

    # ------------------------------------------------------------------ AC 7: running

    def test_open_recent_claim_state_is_running(self, engine: KanbanEngine, log_path: Path) -> None:
        """Unclosed claim younger than claim_timeout (1h) produces state=running."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=6,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-10)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 6]
        assert states == ["running"]

    # ------------------------------------------------------------------ AC 8: stuck detection

    def test_old_claim_no_activity_state_is_stuck(self, engine: KanbanEngine, log_path: Path) -> None:
        """Unclosed claim older than claim_timeout (1h) with no subsequent activity is stuck."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=7,
                    detail="test-agent",
                    ts=_ts(timedelta(hours=-2)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 7]
        assert states == ["stuck"]

    # ------------------------------------------------------------------ AC 9: stuck anti-test

    def test_old_claim_with_recent_activity_is_running_not_stuck(self, engine: KanbanEngine, log_path: Path) -> None:
        """Claim older than timeout but with recent mid-session activity remains running, not stuck."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=8,
                    detail="test-agent",
                    ts=_ts(timedelta(hours=-2)),
                ),
                _entry(
                    action="edit",
                    task_id=8,
                    detail="updated body",
                    ts=_ts(timedelta(minutes=-5)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 8]
        assert states == ["running"]

    # ------------------------------------------------------------------ AC 10: sweep-release dual events

    def test_sweep_release_pair_produces_one_released_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """Engine sweep emits release then sweep-release — exactly one released session, no phantom second."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=9,
                    detail="test-agent",
                    ts=_ts(timedelta(hours=-2)),
                ),
                _entry(action="release", task_id=9, detail="test-agent"),
                _entry(
                    action="sweep-release",
                    task_id=9,
                    detail="expired claim by test-agent released",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 9]
        assert len(task_sessions) == 1
        assert task_sessions[0].state == "released"

    # ------------------------------------------------------------------ AC 11: filter active-only (default)

    def test_default_filter_returns_running_and_stuck_only(self, engine: KanbanEngine, log_path: Path) -> None:
        """list_sessions() with no filter arg returns only running and stuck sessions."""
        _write_log(
            log_path,
            [
                # running
                _entry(
                    action="claim",
                    task_id=10,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-5)),
                ),
                # stuck
                _entry(
                    action="claim",
                    task_id=11,
                    detail="test-agent",
                    ts=_ts(timedelta(hours=-3)),
                ),
                # completed (must be excluded)
                _entry(
                    action="claim",
                    task_id=12,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=12, detail="success: todo -> in-progress"),
            ],
        )
        sessions = engine.list_sessions()  # default = active-only
        returned_ids = {s.task_id for s in sessions}
        assert 10 in returned_ids, "running session must be in active-only results"
        assert 11 in returned_ids, "stuck session must be in active-only results"
        assert 12 not in returned_ids, "completed session must not appear in active-only"

    def test_active_only_excludes_released(self, engine: KanbanEngine, log_path: Path) -> None:
        """list_sessions() default filter excludes released sessions."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=13,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="release", task_id=13, detail="test-agent"),
            ],
        )
        sessions = engine.list_sessions()
        returned_ids = {s.task_id for s in sessions}
        assert 13 not in returned_ids, "released session must not appear in active-only"

    # ------------------------------------------------------------------ AC 12: filter all

    def test_filter_all_returns_every_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """filter='all' returns every session regardless of state."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=20,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-5)),
                ),
                _entry(
                    action="claim",
                    task_id=21,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=21, detail="success: todo -> in-progress"),
                _entry(
                    action="claim",
                    task_id=22,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="release", task_id=22, detail="test-agent"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        returned_ids = {s.task_id for s in sessions}
        assert {20, 21, 22}.issubset(returned_ids)

    # ------------------------------------------------------------------ AC 13: filter blocked-or-rejected

    def test_filter_blocked_or_rejected_includes_block_and_reject(self, engine: KanbanEngine, log_path: Path) -> None:
        """filter='blocked-or-rejected' includes blocked and rejected sessions."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=30,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=30, detail="outcome=fail"),
                _entry(
                    action="claim",
                    task_id=31,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=31, detail="reject: in-progress -> todo"),
            ],
        )
        sessions = engine.list_sessions(filter="blocked-or-rejected")
        returned_ids = {s.task_id for s in sessions}
        assert 30 in returned_ids, "blocked state must be in blocked-or-rejected"
        assert 31 in returned_ids, "rejected state must be in blocked-or-rejected"

    def test_filter_blocked_or_rejected_excludes_pass_and_released(self, engine: KanbanEngine, log_path: Path) -> None:
        """filter='blocked-or-rejected' excludes completed and released sessions."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=32,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=32, detail="success: todo -> in-progress"),
                _entry(
                    action="claim",
                    task_id=33,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="release", task_id=33, detail="test-agent"),
            ],
        )
        sessions = engine.list_sessions(filter="blocked-or-rejected")
        returned_ids = {s.task_id for s in sessions}
        assert 32 not in returned_ids, "completed must be excluded from blocked-or-rejected"
        assert 33 not in returned_ids, "released must be excluded from blocked-or-rejected"

    # ------------------------------------------------------------------ AC 14: filter released

    def test_filter_released_returns_released_sessions_only(self, engine: KanbanEngine, log_path: Path) -> None:
        """filter='released' returns only released-state sessions."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=40,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="release", task_id=40, detail="test-agent"),
                _entry(
                    action="claim",
                    task_id=41,
                    detail="test-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=41, detail="success: todo -> in-progress"),
            ],
        )
        sessions = engine.list_sessions(filter="released")
        returned_ids = {s.task_id for s in sessions}
        states = {s.state for s in sessions}
        assert states <= {"released"}, "released filter must return only released-state sessions"
        assert 40 in returned_ids
        assert 41 not in returned_ids

    # ------------------------------------------------------------------ AC 15: empty log

    def test_empty_activity_log_returns_empty_list(self, engine: KanbanEngine, log_path: Path) -> None:
        """An empty activity.jsonl file returns an empty list."""
        log_path.write_text("", encoding="utf-8")
        sessions = engine.list_sessions(filter="all")
        assert sessions == []

    # ------------------------------------------------------------------ AC 16: missing log

    def test_missing_activity_log_returns_empty_list(self, engine: KanbanEngine, board: Path) -> None:
        """If activity.jsonl does not exist, list_sessions() returns empty list without crashing."""
        assert not (board / "activity.jsonl").exists()
        sessions = engine.list_sessions(filter="all")
        assert sessions == []

    # ------------------------------------------------------------------ AC 17: malformed entries

    def test_malformed_json_line_skipped_gracefully(self, engine: KanbanEngine, log_path: Path) -> None:
        """A malformed JSON line is skipped; valid entries before and after it are processed."""
        valid_before = _entry(
            action="claim",
            task_id=50,
            detail="test-agent",
            ts=_ts(timedelta(minutes=-30)),
        )
        valid_close = _entry(action="end_work", task_id=50, detail="success: todo -> in-progress")
        with log_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(valid_before) + "\n")
            f.write("NOT VALID JSON\n")
            f.write(json.dumps(valid_close) + "\n")
        sessions = engine.list_sessions(filter="all")
        assert [s.task_id for s in sessions if s.task_id == 50] == [50]

    # ------------------------------------------------------------------ AC 18: incomplete entries

    def test_incomplete_entry_missing_fields_skipped_gracefully(self, engine: KanbanEngine, log_path: Path) -> None:
        """An entry missing required fields (action) is skipped; subsequent entries still processed."""
        incomplete = {
            "timestamp": _ts(),
            "task_id": 60,
        }  # missing action, detail, actor
        valid = _entry(
            action="claim",
            task_id=61,
            detail="test-agent",
            ts=_ts(timedelta(minutes=-5)),
        )
        _write_log(log_path, [incomplete, valid])
        sessions = engine.list_sessions(filter="all")
        returned_ids = {s.task_id for s in sessions}
        assert 61 in returned_ids, "valid entry following incomplete entry must be processed"

    # ------------------------------------------------------------------ AC 19: re-claim cycles

    def test_reclaim_after_release_produces_two_distinct_sessions(self, engine: KanbanEngine, log_path: Path) -> None:
        """Same task claimed → released → re-claimed produces two distinct session rows."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=70,
                    detail="agent-1",
                    ts=_ts(timedelta(hours=-2)),
                ),
                _entry(
                    action="release",
                    task_id=70,
                    detail="agent-1",
                    ts=_ts(timedelta(hours=-1, minutes=-30)),
                ),
                _entry(
                    action="claim",
                    task_id=70,
                    detail="agent-2",
                    ts=_ts(timedelta(minutes=-20)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 70]
        assert len(task_sessions) == 2, f"expected 2 distinct sessions for task 70, got {len(task_sessions)}"
        states = {s.state for s in task_sessions}
        assert "released" in states, "first claim-cycle session should be released"
        assert "running" in states, "second claim-cycle session should be running"

    # ------------------------------------------------------------------ AC 20: multi-task interleaved

    def test_interleaved_events_attributed_to_correct_task(self, engine: KanbanEngine, log_path: Path) -> None:
        """Events for multiple tasks interleaved in the log are assigned to the correct task."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=80,
                    detail="agent-a",
                    ts=_ts(timedelta(minutes=-40)),
                ),
                _entry(
                    action="claim",
                    task_id=81,
                    detail="agent-b",
                    ts=_ts(timedelta(minutes=-35)),
                ),
                _entry(
                    action="end_work",
                    task_id=80,
                    detail="success: todo -> in-progress",
                    ts=_ts(timedelta(minutes=-20)),
                ),
                _entry(
                    action="end_work",
                    task_id=81,
                    detail="outcome=fail",
                    ts=_ts(timedelta(minutes=-10)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        by_task = {s.task_id: s for s in sessions}
        assert by_task[80].state == "completed"
        assert by_task[81].state == "blocked"


# ---------------------------------------------------------------------------
# TestBuilderDiscovered
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered edge cases not covered by TestFromAC_ListSessions."""

    def test_invalid_timestamp_value_skipped_gracefully(self, engine: KanbanEngine, log_path: Path) -> None:
        """Entry with all required keys but an unparseable timestamp is skipped gracefully.

        Discovered: _read_log_entries only validates key presence; a syntactically valid
        JSON entry with timestamp='not-a-date' passes the key check and crashes
        datetime.fromisoformat() in _collect_task_sessions with an unhandled ValueError.
        The AC guarantees malformed/incomplete entries are skipped gracefully — this
        path was not tested.
        """
        valid_before = _entry(
            action="claim",
            task_id=90,
            detail="test-agent",
            ts=_ts(timedelta(minutes=-30)),
        )
        bad_ts_entry = {
            "timestamp": "not-a-date",
            "action": "claim",
            "task_id": 91,
            "detail": "test-agent",
            "actor": "test-agent",
        }
        valid_after = _entry(
            action="claim",
            task_id=92,
            detail="test-agent",
            ts=_ts(timedelta(minutes=-5)),
        )
        _write_log(log_path, [valid_before, bad_ts_entry, valid_after])
        sessions = engine.list_sessions(filter="all")
        returned_ids = {s.task_id for s in sessions}
        assert 90 in returned_ids, "valid entry before bad-timestamp entry must be processed"
        assert 91 not in returned_ids, "entry with unparseable timestamp must be skipped"
        assert 92 in returned_ids, "valid entry after bad-timestamp entry must be processed"

    def test_young_superseded_claim_is_running_not_stuck(self, engine: KanbanEngine, log_path: Path) -> None:
        """A claim superseded by a re-claim before the timeout is 'running', not 'stuck'.

        Discovered: _collect_task_sessions() marks the previous session as 'stuck'
        unconditionally when a second claim arrives without a close event. The AC for
        stuck detection requires age >= claim_timeout. A young superseded claim (age <
        timeout) must not be classified as 'stuck'.
        """
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=95,
                    detail="agent-1",
                    ts=_ts(timedelta(minutes=-10)),
                ),
                _entry(
                    action="claim",
                    task_id=95,
                    detail="agent-2",
                    ts=_ts(timedelta(minutes=-5)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 95]
        assert len(task_sessions) == 2, "two consecutive claims must produce two distinct sessions"
        states = [s.state for s in task_sessions]
        assert "stuck" not in states, "young superseded claim (10 min < 1h timeout) must not be classified as 'stuck'"
        assert "running" in states, "young superseded claim must be 'running' (age < timeout)"


# ---------------------------------------------------------------------------
# TestFromAC_WorkSessionFields  (#953)
# ---------------------------------------------------------------------------


class TestFromAC_WorkSessionFields:
    """AC #953: WorkSession extended with agent, started_at, duration, outcome fields.

    AC coverage:
      AC1 - WorkSession has fields: task_id, agent, state, started_at, duration, outcome
      AC3 - agent derived from claim event detail (not actor)
      AC4 - started_at derived from claim event timestamp
      AC5 - duration = close_ts - claim_ts in seconds; None for open/superseded
    AC6 - outcome = classified label from end_work/release; "release" for release; None for open/superseded
      AC9 - WorkSession exported from owlbear_kanban.__init__
      New - superseded claim carries agent and started_at from original claim
    """

    # ------------------------------------------------------------------ AC9: export

    def test_worksession_exported_from_package(self) -> None:
        """WorkSession must be accessible as owlbear_kanban.WorkSession."""
        import importlib

        mod = importlib.import_module("owlbear_kanban")
        assert hasattr(mod, "WorkSession"), "WorkSession must be exported from owlbear_kanban package"

    def test_worksession_in_package_all(self) -> None:
        """WorkSession must appear in owlbear_kanban.__all__."""
        import owlbear_kanban

        assert "WorkSession" in owlbear_kanban.__all__

    # ------------------------------------------------------------------ AC1: field presence

    def test_session_has_agent_field(self, engine: KanbanEngine, log_path: Path) -> None:
        """Completed session must expose an `agent` attribute."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=200,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(
                    action="end_work",
                    task_id=200,
                    detail="success: todo -> in-progress",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 200)
        _ = s.agent  # AttributeError if field absent

    def test_session_has_started_at_field(self, engine: KanbanEngine, log_path: Path) -> None:
        """Completed session must expose a `started_at` attribute."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=201,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(
                    action="end_work",
                    task_id=201,
                    detail="success: todo -> in-progress",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 201)
        _ = s.started_at  # AttributeError if field absent

    def test_session_has_duration_field(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session must expose a `duration` attribute."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=202,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(
                    action="end_work",
                    task_id=202,
                    detail="success: todo -> in-progress",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 202)
        _ = s.duration  # AttributeError if field absent

    def test_session_has_outcome_field(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session must expose an `outcome` attribute."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=203,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(
                    action="end_work",
                    task_id=203,
                    detail="success: todo -> in-progress",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 203)
        _ = s.outcome  # AttributeError if field absent

    # ------------------------------------------------------------------ AC3: agent from claim detail

    def test_agent_equals_claim_event_detail(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.agent must equal the `detail` field of the claim event."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=210,
                    detail="builder-agent",
                    actor="different-actor",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(
                    action="end_work",
                    task_id=210,
                    detail="success: todo -> in-progress",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 210)
        assert s.agent == "builder-agent"

    def test_agent_is_detail_not_actor(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.agent must be the claim `detail` field, not `actor`, when they differ."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=211,
                    detail="the-detail-agent",
                    actor="the-actor-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(
                    action="end_work",
                    task_id=211,
                    detail="success: todo -> in-progress",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 211)
        assert s.agent == "the-detail-agent"
        assert s.agent != "the-actor-agent"

    # ------------------------------------------------------------------ AC4: started_at from claim timestamp

    def test_started_at_equals_claim_timestamp(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.started_at must equal the claim event's timestamp string."""
        claim_ts = "2026-01-15T10:00:00+00:00"
        _write_log(
            log_path,
            [
                _entry(action="claim", task_id=220, detail="my-agent", ts=claim_ts),
                _entry(
                    action="end_work",
                    task_id=220,
                    detail="success: todo -> in-progress",
                    ts="2026-01-15T10:30:00+00:00",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 220)
        assert s.started_at == claim_ts

    def test_started_at_is_iso8601_string(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.started_at must be a string parseable as ISO-8601 datetime."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=221,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(
                    action="end_work",
                    task_id=221,
                    detail="success: todo -> in-progress",
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 221)
        assert isinstance(s.started_at, str)
        datetime.fromisoformat(s.started_at)  # must not raise

    # ------------------------------------------------------------------ AC5: duration

    def test_duration_is_close_minus_claim_seconds(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.duration must equal (close_ts - claim_ts).total_seconds() for closed sessions."""
        claim_ts = "2026-01-15T10:00:00+00:00"
        close_ts = "2026-01-15T10:30:00+00:00"  # 1800 s
        _write_log(
            log_path,
            [
                _entry(action="claim", task_id=230, detail="my-agent", ts=claim_ts),
                _entry(
                    action="end_work",
                    task_id=230,
                    detail="success: todo -> in-progress",
                    ts=close_ts,
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 230)
        assert s.duration == pytest.approx(1800.0)

    def test_duration_is_none_for_running_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.duration is None for an open (running) session."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=231,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-5)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 231)
        assert s.duration is None

    def test_duration_is_none_for_stuck_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.duration is None for an open (stuck) session."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=232,
                    detail="my-agent",
                    ts=_ts(timedelta(hours=-3)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 232)
        assert s.duration is None

    def test_duration_is_none_for_superseded_claim(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.duration is None for a superseded (orphaned) claim."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=233,
                    detail="agent-1",
                    ts=_ts(timedelta(hours=-2)),
                ),
                _entry(
                    action="claim",
                    task_id=233,
                    detail="agent-2",
                    ts=_ts(timedelta(minutes=-10)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 233]
        # First claim was 2h ago without close → classified as "stuck" when superseded
        superseded = next(s for s in task_sessions if s.state == "stuck")
        assert superseded.duration is None

    def test_duration_with_tz_naive_claim_timestamp(self, engine: KanbanEngine, log_path: Path) -> None:
        """Duration computed correctly when claim timestamp is tz-naive (no UTC offset)."""
        # tz-naive claim vs tz-aware close — engine must normalize both to UTC
        claim_ts = "2026-01-15T10:00:00"  # no tz info
        close_ts = "2026-01-15T10:30:00+00:00"
        _write_log(
            log_path,
            [
                _entry(action="claim", task_id=234, detail="my-agent", ts=claim_ts),
                _entry(
                    action="end_work",
                    task_id=234,
                    detail="success: todo -> in-progress",
                    ts=close_ts,
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 234)
        assert s.duration == pytest.approx(1800.0)

    def test_duration_is_set_for_released_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.duration is a non-None float for a released session."""
        claim_ts = "2026-01-15T10:00:00+00:00"
        close_ts = "2026-01-15T11:00:00+00:00"  # 3600 s
        _write_log(
            log_path,
            [
                _entry(action="claim", task_id=235, detail="my-agent", ts=claim_ts),
                _entry(action="release", task_id=235, detail="my-agent", ts=close_ts),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 235)
        assert s.duration == pytest.approx(3600.0)

    # ------------------------------------------------------------------ AC6: outcome

    def test_outcome_is_raw_end_work_detail_for_success(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.outcome is the classified end_work outcome label."""
        detail = "success: todo -> in-progress"
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=240,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=240, detail=detail),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 240)
        assert s.outcome == "success"

    def test_outcome_is_raw_end_work_detail_for_fail(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.outcome is the classified fail label for a blocked session."""
        detail = "outcome=fail"
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=241,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="end_work", task_id=241, detail=detail),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 241)
        assert s.outcome == "fail"

    def test_outcome_is_released_string_for_release_event(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.outcome is the literal string 'release' when closed by a release event."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=242,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-30)),
                ),
                _entry(action="release", task_id=242, detail="my-agent"),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 242)
        assert s.outcome == "release"

    def test_outcome_is_none_for_running_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.outcome is None for an open (running) session."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=243,
                    detail="my-agent",
                    ts=_ts(timedelta(minutes=-5)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 243)
        assert s.outcome is None

    def test_outcome_is_none_for_stuck_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.outcome is None for an open (stuck) session."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=244,
                    detail="my-agent",
                    ts=_ts(timedelta(hours=-3)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        s = next(s for s in sessions if s.task_id == 244)
        assert s.outcome is None

    def test_outcome_is_none_for_superseded_claim(self, engine: KanbanEngine, log_path: Path) -> None:
        """Session.outcome is None for a superseded (orphaned) claim."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=245,
                    detail="agent-1",
                    ts=_ts(timedelta(hours=-2)),
                ),
                _entry(
                    action="claim",
                    task_id=245,
                    detail="agent-2",
                    ts=_ts(timedelta(minutes=-10)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 245]
        superseded = next(s for s in task_sessions if s.state == "stuck")
        assert superseded.outcome is None

    # ------------------------------------------------------------------ New AC: superseded claim fields

    def test_superseded_claim_agent_from_original_claim_detail(self, engine: KanbanEngine, log_path: Path) -> None:
        """Superseded session.agent is from the original (first) claim detail field."""
        _write_log(
            log_path,
            [
                _entry(
                    action="claim",
                    task_id=250,
                    detail="original-agent",
                    ts=_ts(timedelta(hours=-2)),
                ),
                _entry(
                    action="claim",
                    task_id=250,
                    detail="new-agent",
                    ts=_ts(timedelta(minutes=-10)),
                ),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 250]
        # original claim was 2h ago without close → classified as "stuck" when superseded
        superseded = next(s for s in task_sessions if s.state == "stuck")
        assert superseded.agent == "original-agent"

    def test_superseded_claim_started_at_from_original_claim_timestamp(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """Superseded session.started_at equals the original claim event's timestamp."""
        original_ts = _ts(timedelta(hours=-2))
        new_ts = _ts(timedelta(minutes=-10))
        _write_log(
            log_path,
            [
                _entry(action="claim", task_id=251, detail="original-agent", ts=original_ts),
                _entry(action="claim", task_id=251, detail="new-agent", ts=new_ts),
            ],
        )
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 251]
        superseded = next(s for s in task_sessions if s.state == "stuck")
        assert superseded.started_at == original_ts


# --- merged from serve/kanban/tests/test_list_sessions_detail.py ---
_TASK_TEMPLATE = """\
---
id: {task_id}
title: "Task {task_id}"
status: {status}
priority: important
created: 2026-04-18T10:00:00.000000+00:00
updated: 2026-04-18T10:00:00.000000+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Task body.
"""


def _write_task(kanban_dir: Path, task_id: int, status: str = "todo") -> None:
    """Write a synthetic task file into the board's tasks directory."""
    content = _TASK_TEMPLATE.format(task_id=task_id, status=status)
    slug = f"{task_id}-task-{task_id}.md"
    (kanban_dir / "tasks" / slug).write_text(content, encoding="utf-8")


def _last_end_work_detail(log_path: Path) -> str:
    """Return the detail field of the last end_work entry in the activity log."""
    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    end_work_entries = [e for e in entries if e.get("action") == "end_work"]
    assert end_work_entries, "No end_work entry found in activity log"
    return end_work_entries[-1]["detail"]


class TestFromAC_EndWorkDetailPrefix:
    """Verifies end_work() detail prefix contract per task #952 AC."""

    # ------------------------------------------------------------------ AC1: success prefix

    def test_end_work_success_detail_has_success_prefix(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(success) writes a detail string that starts with 'success:'."""
        _write_task(board, 1, status="todo")
        engine.start_work("1")
        engine.end_work("1", note="done", outcome="success")

        detail = _last_end_work_detail(log_path)
        assert detail.startswith("success:"), f"Expected detail to start with 'success:' but got: {detail!r}"

    def test_end_work_success_detail_exact_format(self, board: Path, engine: KanbanEngine, log_path: Path) -> None:
        """end_work(success) detail is exactly 'success: {old} -> {new}'."""
        _write_task(board, 2, status="todo")
        engine.start_work("2")
        engine.end_work("2", note="done", outcome="success")

        detail = _last_end_work_detail(log_path)
        assert detail == "success: todo -> in-progress", f"Expected 'success: todo -> in-progress' but got: {detail!r}"

    def test_end_work_success_from_non_todo_status(self, board: Path, engine: KanbanEngine, log_path: Path) -> None:
        """end_work(success) reflects the actual old status in the prefix."""
        _write_task(board, 3, status="in-progress")
        engine.start_work("3")
        engine.end_work("3", note="done", outcome="success")

        detail = _last_end_work_detail(log_path)
        assert detail == "success: in-progress -> review", (
            f"Expected 'success: in-progress -> review' but got: {detail!r}"
        )

    # ------------------------------------------------------------------ AC2: reject prefix

    def test_end_work_reject_detail_has_reject_prefix(self, board: Path, engine: KanbanEngine, log_path: Path) -> None:
        """end_work(reject) writes a detail string that starts with 'reject:'."""
        _write_task(board, 4, status="todo")
        engine.start_work("4")
        engine.end_work("4", note="rejected", outcome="reject", move_to="research")

        detail = _last_end_work_detail(log_path)
        assert detail.startswith("reject:"), f"Expected detail to start with 'reject:' but got: {detail!r}"

    def test_end_work_reject_detail_exact_format(self, board: Path, engine: KanbanEngine, log_path: Path) -> None:
        """end_work(reject) detail is exactly 'reject: {old} -> {target}'."""
        _write_task(board, 5, status="todo")
        engine.start_work("5")
        engine.end_work("5", note="rejected", outcome="reject", move_to="research")

        detail = _last_end_work_detail(log_path)
        assert detail == "reject: todo -> research", f"Expected 'reject: todo -> research' but got: {detail!r}"

    def test_end_work_reject_detail_reflects_explicit_move_to(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(reject, move_to='backlog') detail shows the explicit target."""
        _write_task(board, 6, status="in-progress")
        engine.start_work("6")
        engine.end_work("6", note="rejected", outcome="reject", move_to="backlog")

        detail = _last_end_work_detail(log_path)
        assert detail == "reject: in-progress -> backlog", (
            f"Expected 'reject: in-progress -> backlog' but got: {detail!r}"
        )

    # ------------------------------------------------------------------ AC5: integration success → completed

    def test_integration_end_work_success_classifies_as_completed_pass(self, board: Path, engine: KanbanEngine) -> None:
        """Integration: start_work → end_work(success) → list_sessions returns completed."""
        _write_task(board, 7, status="todo")
        engine.start_work("7")
        engine.end_work("7", note="done", outcome="success")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 7]
        assert task_sessions, "No session found for task 7"
        assert task_sessions[-1].state == "completed", f"Expected 'completed' but got: {task_sessions[-1].state!r}"

    def test_integration_end_work_success_not_misclassified_as_completed_fail(
        self, board: Path, engine: KanbanEngine
    ) -> None:
        """Regression: end_work(success) must NOT produce blocked."""
        _write_task(board, 8, status="todo")
        engine.start_work("8")
        engine.end_work("8", note="done", outcome="success")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 8]
        assert task_sessions, "No session found for task 8"
        assert task_sessions[-1].state != "blocked", "end_work(success) was misclassified as blocked"

    # ------------------------------------------------------------------ AC6: integration reject → rejected

    def test_integration_end_work_reject_classifies_as_completed_rejected(
        self, board: Path, engine: KanbanEngine
    ) -> None:
        """Integration: start_work → end_work(reject) → list_sessions returns rejected."""
        _write_task(board, 9, status="todo")
        engine.start_work("9")
        engine.end_work("9", note="rejected", outcome="reject", move_to="research")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 9]
        assert task_sessions, "No session found for task 9"
        assert task_sessions[-1].state == "rejected", f"Expected 'rejected' but got: {task_sessions[-1].state!r}"

    def test_integration_end_work_reject_not_misclassified_as_completed_fail(
        self, board: Path, engine: KanbanEngine
    ) -> None:
        """Regression: end_work(reject) must NOT produce blocked."""
        _write_task(board, 10, status="todo")
        engine.start_work("10")
        engine.end_work("10", note="rejected", outcome="reject", move_to="research")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 10]
        assert task_sessions, "No session found for task 10"
        assert task_sessions[-1].state != "blocked", "end_work(reject) was misclassified as blocked"

    # ------------------------------------------------------------------ AC3: fail/block details unchanged

    def test_end_work_fail_detail_is_outcome_equals_fail(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(fail) writes detail 'outcome=fail' — unchanged from pre-fix format."""
        _write_task(board, 1, status="in-progress")
        engine.start_work("1")
        engine.end_work("1", note="failed", outcome="fail")

        detail = _last_end_work_detail(log_path)
        assert detail == "outcome=fail", f"Expected 'outcome=fail' but got: {detail!r}"

    def test_end_work_block_detail_is_blocked_with_reason(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(block) writes detail 'blocked: {reason}' — unchanged from pre-fix format."""
        _write_task(board, 1, status="in-progress")
        engine.start_work("1")
        engine.end_work(
            "1",
            note="blocked",
            outcome="block",
            block_reason="external dependency",
        )

        detail = _last_end_work_detail(log_path)
        assert detail == "blocked: external dependency", f"Expected 'blocked: external dependency' but got: {detail!r}"
