"""Tests for task #923: list_sessions() engine helper.

AC coverage:
  1.  One session per claim cycle (claim → close event)
  2.  Session state: completed-pass  (end_work success)
  3.  Session state: completed-fail  (end_work fail)
  4.  Session state: completed-fail  (end_work block → maps to completed-fail)
  5.  Session state: completed-rejected (end_work reject)
  6.  Session state: released (release event)
  7.  Session state: running (open claim, age < timeout)
  8.  Session state: stuck  (open claim, age ≥ timeout, no recent activity)
  9.  Stuck anti-test: old claim with recent mid-session activity remains running
  10. sweep-release: release + sweep-release pair closes exactly one session (no phantom)
  11. Filter: active-only (default) returns running + stuck only
  12. Filter: all returns every session regardless of state
  13. Filter: failed-or-rejected returns completed-fail + completed-rejected
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
    return KanbanEngine(board, agent_name="test-agent", activity_log=True)


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
        _write_log(log_path, [
            _entry(action="claim", task_id=1, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=1, detail="success: todo -> in-progress"),
        ])
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert len(task_sessions) == 1

    # ------------------------------------------------------------------ AC 2: completed-pass

    def test_end_work_success_state_is_completed_pass(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with success detail prefix produces state=completed-pass."""
        _write_log(log_path, [
            _entry(action="claim", task_id=1, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=1, detail="success: todo -> in-progress"),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 1]
        assert states == ["completed-pass"]

    # ------------------------------------------------------------------ AC 3: completed-fail (fail)

    def test_end_work_fail_state_is_completed_fail(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with 'outcome=fail' detail produces state=completed-fail."""
        _write_log(log_path, [
            _entry(action="claim", task_id=2, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=2, detail="outcome=fail"),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 2]
        assert states == ["completed-fail"]

    # ------------------------------------------------------------------ AC 4: completed-fail (block)

    def test_end_work_block_maps_to_completed_fail(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with 'blocked:' detail maps to completed-fail (no 7th state for block)."""
        _write_log(log_path, [
            _entry(action="claim", task_id=3, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=3, detail="blocked: needs DB migration"),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 3]
        assert states == ["completed-fail"]

    # ------------------------------------------------------------------ AC 5: completed-rejected

    def test_end_work_reject_state_is_completed_rejected(self, engine: KanbanEngine, log_path: Path) -> None:
        """end_work with 'reject:' detail prefix produces state=completed-rejected."""
        _write_log(log_path, [
            _entry(action="claim", task_id=4, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=4, detail="reject: in-progress -> todo"),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 4]
        assert states == ["completed-rejected"]

    # ------------------------------------------------------------------ AC 6: released

    def test_release_event_state_is_released(self, engine: KanbanEngine, log_path: Path) -> None:
        """A release event closes the session with state=released."""
        _write_log(log_path, [
            _entry(action="claim", task_id=5, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="release", task_id=5, detail="test-agent"),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 5]
        assert states == ["released"]

    # ------------------------------------------------------------------ AC 7: running

    def test_open_recent_claim_state_is_running(self, engine: KanbanEngine, log_path: Path) -> None:
        """Unclosed claim younger than claim_timeout (1h) produces state=running."""
        _write_log(log_path, [
            _entry(action="claim", task_id=6, detail="test-agent", ts=_ts(timedelta(minutes=-10))),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 6]
        assert states == ["running"]

    # ------------------------------------------------------------------ AC 8: stuck detection

    def test_old_claim_no_activity_state_is_stuck(self, engine: KanbanEngine, log_path: Path) -> None:
        """Unclosed claim older than claim_timeout (1h) with no subsequent activity is stuck."""
        _write_log(log_path, [
            _entry(action="claim", task_id=7, detail="test-agent", ts=_ts(timedelta(hours=-2))),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 7]
        assert states == ["stuck"]

    # ------------------------------------------------------------------ AC 9: stuck anti-test

    def test_old_claim_with_recent_activity_is_running_not_stuck(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """Claim older than timeout but with recent mid-session activity remains running, not stuck."""
        _write_log(log_path, [
            _entry(action="claim", task_id=8, detail="test-agent", ts=_ts(timedelta(hours=-2))),
            _entry(action="edit", task_id=8, detail="updated body", ts=_ts(timedelta(minutes=-5))),
        ])
        sessions = engine.list_sessions(filter="all")
        states = [s.state for s in sessions if s.task_id == 8]
        assert states == ["running"]

    # ------------------------------------------------------------------ AC 10: sweep-release dual events

    def test_sweep_release_pair_produces_one_released_session(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """Engine sweep emits release then sweep-release — exactly one released session, no phantom second."""
        _write_log(log_path, [
            _entry(action="claim", task_id=9, detail="test-agent", ts=_ts(timedelta(hours=-2))),
            _entry(action="release", task_id=9, detail="test-agent"),
            _entry(action="sweep-release", task_id=9, detail="expired claim by test-agent released"),
        ])
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 9]
        assert len(task_sessions) == 1
        assert task_sessions[0].state == "released"

    # ------------------------------------------------------------------ AC 11: filter active-only (default)

    def test_default_filter_returns_running_and_stuck_only(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """list_sessions() with no filter arg returns only running and stuck sessions."""
        _write_log(log_path, [
            # running
            _entry(action="claim", task_id=10, detail="test-agent", ts=_ts(timedelta(minutes=-5))),
            # stuck
            _entry(action="claim", task_id=11, detail="test-agent", ts=_ts(timedelta(hours=-3))),
            # completed-pass (must be excluded)
            _entry(action="claim", task_id=12, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=12, detail="success: todo -> in-progress"),
        ])
        sessions = engine.list_sessions()  # default = active-only
        returned_ids = {s.task_id for s in sessions}
        assert 10 in returned_ids, "running session must be in active-only results"
        assert 11 in returned_ids, "stuck session must be in active-only results"
        assert 12 not in returned_ids, "completed-pass session must not appear in active-only"

    def test_active_only_excludes_released(self, engine: KanbanEngine, log_path: Path) -> None:
        """list_sessions() default filter excludes released sessions."""
        _write_log(log_path, [
            _entry(action="claim", task_id=13, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="release", task_id=13, detail="test-agent"),
        ])
        sessions = engine.list_sessions()
        returned_ids = {s.task_id for s in sessions}
        assert 13 not in returned_ids, "released session must not appear in active-only"

    # ------------------------------------------------------------------ AC 12: filter all

    def test_filter_all_returns_every_session(self, engine: KanbanEngine, log_path: Path) -> None:
        """filter='all' returns every session regardless of state."""
        _write_log(log_path, [
            _entry(action="claim", task_id=20, detail="test-agent", ts=_ts(timedelta(minutes=-5))),
            _entry(action="claim", task_id=21, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=21, detail="success: todo -> in-progress"),
            _entry(action="claim", task_id=22, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="release", task_id=22, detail="test-agent"),
        ])
        sessions = engine.list_sessions(filter="all")
        returned_ids = {s.task_id for s in sessions}
        assert {20, 21, 22}.issubset(returned_ids)

    # ------------------------------------------------------------------ AC 13: filter failed-or-rejected

    def test_filter_failed_or_rejected_includes_fail_and_reject(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """filter='failed-or-rejected' includes completed-fail and completed-rejected sessions."""
        _write_log(log_path, [
            _entry(action="claim", task_id=30, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=30, detail="outcome=fail"),
            _entry(action="claim", task_id=31, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=31, detail="reject: in-progress -> todo"),
        ])
        sessions = engine.list_sessions(filter="failed-or-rejected")
        returned_ids = {s.task_id for s in sessions}
        assert 30 in returned_ids, "completed-fail must be in failed-or-rejected"
        assert 31 in returned_ids, "completed-rejected must be in failed-or-rejected"

    def test_filter_failed_or_rejected_excludes_pass_and_released(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """filter='failed-or-rejected' excludes completed-pass and released sessions."""
        _write_log(log_path, [
            _entry(action="claim", task_id=32, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=32, detail="success: todo -> in-progress"),
            _entry(action="claim", task_id=33, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="release", task_id=33, detail="test-agent"),
        ])
        sessions = engine.list_sessions(filter="failed-or-rejected")
        returned_ids = {s.task_id for s in sessions}
        assert 32 not in returned_ids, "completed-pass must be excluded from failed-or-rejected"
        assert 33 not in returned_ids, "released must be excluded from failed-or-rejected"

    # ------------------------------------------------------------------ AC 14: filter released

    def test_filter_released_returns_released_sessions_only(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """filter='released' returns only released-state sessions."""
        _write_log(log_path, [
            _entry(action="claim", task_id=40, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="release", task_id=40, detail="test-agent"),
            _entry(action="claim", task_id=41, detail="test-agent", ts=_ts(timedelta(minutes=-30))),
            _entry(action="end_work", task_id=41, detail="success: todo -> in-progress"),
        ])
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
        valid_before = _entry(action="claim", task_id=50, detail="test-agent", ts=_ts(timedelta(minutes=-30)))
        valid_close = _entry(action="end_work", task_id=50, detail="success: todo -> in-progress")
        with log_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(valid_before) + "\n")
            f.write("NOT VALID JSON\n")
            f.write(json.dumps(valid_close) + "\n")
        sessions = engine.list_sessions(filter="all")
        assert [s.task_id for s in sessions if s.task_id == 50] == [50]

    # ------------------------------------------------------------------ AC 18: incomplete entries

    def test_incomplete_entry_missing_fields_skipped_gracefully(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """An entry missing required fields (action) is skipped; subsequent entries still processed."""
        incomplete = {"timestamp": _ts(), "task_id": 60}  # missing action, detail, actor
        valid = _entry(action="claim", task_id=61, detail="test-agent", ts=_ts(timedelta(minutes=-5)))
        _write_log(log_path, [incomplete, valid])
        sessions = engine.list_sessions(filter="all")
        returned_ids = {s.task_id for s in sessions}
        assert 61 in returned_ids, "valid entry following incomplete entry must be processed"

    # ------------------------------------------------------------------ AC 19: re-claim cycles

    def test_reclaim_after_release_produces_two_distinct_sessions(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """Same task claimed → released → re-claimed produces two distinct session rows."""
        _write_log(log_path, [
            _entry(action="claim", task_id=70, detail="agent-1", ts=_ts(timedelta(hours=-2))),
            _entry(action="release", task_id=70, detail="agent-1", ts=_ts(timedelta(hours=-1, minutes=-30))),
            _entry(action="claim", task_id=70, detail="agent-2", ts=_ts(timedelta(minutes=-20))),
        ])
        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 70]
        assert len(task_sessions) == 2, f"expected 2 distinct sessions for task 70, got {len(task_sessions)}"
        states = {s.state for s in task_sessions}
        assert "released" in states, "first claim-cycle session should be released"
        assert "running" in states, "second claim-cycle session should be running"

    # ------------------------------------------------------------------ AC 20: multi-task interleaved

    def test_interleaved_events_attributed_to_correct_task(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """Events for multiple tasks interleaved in the log are assigned to the correct task."""
        _write_log(log_path, [
            _entry(action="claim", task_id=80, detail="agent-a", ts=_ts(timedelta(minutes=-40))),
            _entry(action="claim", task_id=81, detail="agent-b", ts=_ts(timedelta(minutes=-35))),
            _entry(action="end_work", task_id=80, detail="success: todo -> in-progress", ts=_ts(timedelta(minutes=-20))),
            _entry(action="end_work", task_id=81, detail="outcome=fail", ts=_ts(timedelta(minutes=-10))),
        ])
        sessions = engine.list_sessions(filter="all")
        by_task = {s.task_id: s for s in sessions}
        assert by_task[80].state == "completed-pass"
        assert by_task[81].state == "completed-fail"


# ---------------------------------------------------------------------------
# TestBuilderDiscovered
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered edge cases not covered by TestFromAC_ListSessions."""

    def test_invalid_timestamp_value_skipped_gracefully(
        self, engine: KanbanEngine, log_path: Path
    ) -> None:
        """Entry with all required keys but an unparseable timestamp is skipped gracefully.

        Discovered: _read_log_entries only validates key presence; a syntactically valid
        JSON entry with timestamp='not-a-date' passes the key check and crashes
        datetime.fromisoformat() in _collect_task_sessions with an unhandled ValueError.
        The AC guarantees malformed/incomplete entries are skipped gracefully — this
        path was not tested.
        """
        valid_before = _entry(action="claim", task_id=90, detail="test-agent", ts=_ts(timedelta(minutes=-30)))
        bad_ts_entry = {
            "timestamp": "not-a-date",
            "action": "claim",
            "task_id": 91,
            "detail": "test-agent",
            "actor": "test-agent",
        }
        valid_after = _entry(action="claim", task_id=92, detail="test-agent", ts=_ts(timedelta(minutes=-5)))
        _write_log(log_path, [valid_before, bad_ts_entry, valid_after])
        sessions = engine.list_sessions(filter="all")
        returned_ids = {s.task_id for s in sessions}
        assert 90 in returned_ids, "valid entry before bad-timestamp entry must be processed"
        assert 91 not in returned_ids, "entry with unparseable timestamp must be skipped"
        assert 92 in returned_ids, "valid entry after bad-timestamp entry must be processed"
