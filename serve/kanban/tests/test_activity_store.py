"""TDD RED: C-04 — activity_store append/query/compact tests.

Task: #1049 (Brief C #1043) — paper-c.md §8.9
AC:   C42, C44, C44a
All tests FAIL (RED phase — activity_store not yet implemented).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_kanban.activity_store import (  # NEW module — ImportError in RED
    append_activity_event,
    list_activity_events,
    compact_activity_log,
)
from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    ActivityEvent,
    ActivityCompactionResult,
)

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _ts(delta: timedelta | None = None) -> str:
    t = datetime.now(tz=UTC)
    if delta is not None:
        t = t + delta
    return t.isoformat()


def _make_event(
    *,
    task_id: int | None = 1001,
    action: str = "claim",
    source: str = "agent",
    detail: str = "test event",
    ts: str | None = None,
) -> ActivityEvent:
    return ActivityEvent(
        timestamp=ts or _ts(),
        task_id=task_id,
        action=action,
        source=source,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# TestFromAC_ActivityAppendQuery — AC-C42, AC-C44
# ---------------------------------------------------------------------------


class TestFromAC_ActivityAppendQuery:
    """AC-C42, AC-C44: append_activity_event / list_activity_events contract."""

    def test_ac_c42_append_writes_to_activity_jsonl(self, tmp_path: Path) -> None:
        """AC-C42: append_activity_event writes a JSONL record to activity.jsonl."""
        kanban_dir = _make_board(tmp_path)
        event = _make_event(task_id=1001, action="claim")
        append_activity_event(event, kanban_dir)

        activity_file = kanban_dir / "activity.jsonl"
        assert activity_file.exists()
        lines = activity_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["task_id"] == 1001
        assert record["action"] == "claim"
        assert record["source"] == "agent"

    def test_ac_c42_append_multiple_events_each_on_own_line(self, tmp_path: Path) -> None:
        """AC-C42: multiple appends produce one JSON record per line (JSONL)."""
        kanban_dir = _make_board(tmp_path)
        for action in ("claim", "edit", "end_work"):
            append_activity_event(_make_event(action=action), kanban_dir)

        lines = (kanban_dir / "activity.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
        actions = [json.loads(line)["action"] for line in lines]
        assert actions == ["claim", "edit", "end_work"]

    def test_ac_c42_event_fields_match_activity_event_schema(self, tmp_path: Path) -> None:
        """AC-C42: written JSONL line contains all ActivityEvent fields."""
        kanban_dir = _make_board(tmp_path)
        event = _make_event(task_id=42, action="move", source="cockpit", detail="todo→in-progress")
        append_activity_event(event, kanban_dir)

        line = (kanban_dir / "activity.jsonl").read_text(encoding="utf-8").strip()
        record = json.loads(line)
        assert "timestamp" in record
        assert record["task_id"] == 42
        assert record["action"] == "move"
        assert record["source"] == "cockpit"
        assert record["detail"] == "todo→in-progress"

    def test_ac_c42_list_filter_by_task_id(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events(task_id=X) returns only events for task X."""
        kanban_dir = _make_board(tmp_path)
        append_activity_event(_make_event(task_id=1, action="claim"), kanban_dir)
        append_activity_event(_make_event(task_id=2, action="claim"), kanban_dir)
        append_activity_event(_make_event(task_id=1, action="end_work"), kanban_dir)

        result = list_activity_events(kanban_dir, task_id=1)
        assert len(result) == 2
        assert all(e.task_id == 1 for e in result)

    def test_ac_c42_list_filter_by_action(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events(action='claim') returns only claim events."""
        kanban_dir = _make_board(tmp_path)
        append_activity_event(_make_event(action="claim"), kanban_dir)
        append_activity_event(_make_event(action="edit"), kanban_dir)
        append_activity_event(_make_event(action="claim", task_id=2), kanban_dir)

        result = list_activity_events(kanban_dir, action="claim")
        assert len(result) == 2
        assert all(e.action == "claim" for e in result)

    def test_ac_c42_list_filter_by_source(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events(source='cockpit') filters by source."""
        kanban_dir = _make_board(tmp_path)
        append_activity_event(_make_event(source="agent"), kanban_dir)
        append_activity_event(_make_event(source="cockpit"), kanban_dir)

        result = list_activity_events(kanban_dir, source="cockpit")
        assert len(result) == 1
        assert result[0].source == "cockpit"

    def test_ac_c42_list_filter_by_since(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events(since=T) returns events at or after T."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        past = (now - timedelta(hours=2)).isoformat()
        future = (now + timedelta(seconds=5)).isoformat()

        append_activity_event(_make_event(ts=(now - timedelta(hours=3)).isoformat()), kanban_dir)
        append_activity_event(_make_event(ts=(now - timedelta(hours=1)).isoformat()), kanban_dir)
        append_activity_event(_make_event(ts=future), kanban_dir)

        result = list_activity_events(kanban_dir, since=past)
        assert len(result) == 2

    def test_ac_c42_list_filter_by_limit(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events(limit=N) returns at most N events."""
        kanban_dir = _make_board(tmp_path)
        for i in range(10):
            append_activity_event(_make_event(task_id=i), kanban_dir)

        result = list_activity_events(kanban_dir, limit=3)
        assert len(result) == 3

    def test_ac_c42_list_no_filters_returns_all(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events with no filters returns all events."""
        kanban_dir = _make_board(tmp_path)
        for i in range(5):
            append_activity_event(_make_event(task_id=i), kanban_dir)

        result = list_activity_events(kanban_dir)
        assert len(result) == 5

    def test_ac_c42_does_not_scan_task_frontmatter(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events never reads task .md files (storage separation)."""
        from unittest.mock import patch  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        append_activity_event(_make_event(), kanban_dir)

        read_calls: list[str] = []

        original_open = open

        def spy_open(path: object, *args: object, **kwargs: object) -> object:
            p = str(path)
            if p.endswith(".md"):
                read_calls.append(p)
            return original_open(path, *args, **kwargs)  # type: ignore[call-overload]

        with patch("builtins.open", side_effect=spy_open):
            list_activity_events(kanban_dir, task_id=1001)

        assert read_calls == [], f"Unexpectedly read .md files: {read_calls}"

    def test_ac_c42_frontmatter_exclusion_via_path_read_text(self, tmp_path: Path) -> None:
        """AC-C42: list_activity_events never reads .md files via Path.read_text or Path.open.

        Complements test_ac_c42_does_not_scan_task_frontmatter by also patching
        Path.read_text and Path.open — the actual file-read paths used by the implementation.
        """
        from unittest.mock import patch  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        append_activity_event(_make_event(), kanban_dir)

        # Create a task md file to ensure one is present in the board
        task_file = kanban_dir / "tasks" / "0001-test.md"
        task_file.write_text("---\nid: 1\n---\n## Body\n", encoding="utf-8")

        md_read_calls: list[str] = []

        original_path_read_text = Path.read_text  # type: ignore[attr-defined]
        original_path_open = Path.open  # type: ignore[attr-defined]

        def spy_read_text(self: Path, *args: object, **kwargs: object) -> str:
            if str(self).endswith(".md"):
                md_read_calls.append(str(self))
            return original_path_read_text(self, *args, **kwargs)

        def spy_path_open(self: Path, *args: object, **kwargs: object) -> object:
            if str(self).endswith(".md"):
                md_read_calls.append(str(self))
            return original_path_open(self, *args, **kwargs)

        with (
            patch.object(Path, "read_text", spy_read_text),
            patch.object(Path, "open", spy_path_open),
        ):
            list_activity_events(kanban_dir, task_id=1001)

        assert md_read_calls == [], f"Unexpectedly read .md files via Path: {md_read_calls}"

    def test_ac_c44_no_session_jsonl_file_on_disk(self, tmp_path: Path) -> None:
        """AC-C44: no session table on disk — only activity.jsonl."""
        kanban_dir = _make_board(tmp_path)
        append_activity_event(_make_event(action="claim"), kanban_dir)
        append_activity_event(_make_event(action="end_work"), kanban_dir)

        json_files = list(kanban_dir.glob("*.jsonl"))
        assert len(json_files) == 1
        assert json_files[0].name == "activity.jsonl"

    def test_ac_c44_empty_log_returns_empty_list(self, tmp_path: Path) -> None:
        """AC-C44: empty or missing activity.jsonl → list_activity_events returns []."""
        kanban_dir = _make_board(tmp_path)
        result = list_activity_events(kanban_dir)
        assert result == []


# ---------------------------------------------------------------------------
# TestFromAC_ActivityCompaction — AC-C44a (a through e)
# ---------------------------------------------------------------------------


class TestFromAC_ActivityCompaction:
    """AC-C44a: compact_activity_log contract — cutoff, open sessions, floor, atomic, idempotent."""

    def test_ac_c44a_a_before_dt_none_resolves_to_latest_closed_session(self, tmp_path: Path) -> None:
        """AC-C44a (a): before_dt=None uses most-recently-closed session ended_at as cutoff.

        Uses >500 entries so the hard floor is active and the compat branch
        (``len(all_lines) <= _HARD_FLOOR``) never suppresses it.  The closed session
        (task 1) occupies the two oldest positions, both outside the last-500 floor
        window.  500 filler entries fill the floor window.  The old claim (strictly
        before the auto-resolved cutoff) is the only entry removed, proving
        ``before_dt=None`` resolved to the session's ``end_work`` timestamp.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # Closed session for task 1 — positions 1-2, both outside the last-500 window.
        old_claim_ts = (now - timedelta(hours=601)).isoformat()
        append_activity_event(_make_event(action="claim", ts=old_claim_ts, task_id=1), kanban_dir)
        old_close_ts = (now - timedelta(hours=600)).isoformat()
        append_activity_event(
            _make_event(
                action="end_work",
                ts=old_close_ts,
                task_id=1,
                source="agent",
                detail="success: done",
            ),
            kanban_dir,
        )

        # 500 filler entries after the session — fills the floor window (positions 3-502).
        # All timestamps are newer than old_close_ts so they survive both floor and
        # session/cutoff logic.
        for i in range(500):
            ts = (now - timedelta(hours=599 - i)).isoformat()
            append_activity_event(_make_event(action="edit", ts=ts, task_id=2), kanban_dir)

        # Total: 502 entries. Last 500 = filler[0..499] (positions 3-502).
        result = compact_activity_log(kanban_dir, before_dt=None)
        remaining = list_activity_events(kanban_dir)

        assert isinstance(result, ActivityCompactionResult)

        # Auto-cutoff = old_close_ts (the only closed session's end_work).
        # old_claim (before cutoff, outside floor) must be compacted.
        assert not any(e.task_id == 1 and e.action == "claim" for e in remaining), (
            "Old claim before the closed-session cutoff must be compacted"
        )

        # Session close (AT cutoff, outside floor window) retained by session/cutoff logic —
        # proves the resolved cutoff was <= old_close_ts.
        assert any(e.task_id == 1 and e.action == "end_work" for e in remaining), (
            "Session close event must be retained — proves before_dt=None resolved to this session's end"
        )

        # Exactly one record compacted (old_claim only).
        assert result.records_compacted == 1, (
            f"Exactly 1 record (old claim) should be compacted; got {result.records_compacted}"
        )

    def test_ac_c44a_a_resolves_to_most_recent_close_not_oldest(self, tmp_path: Path) -> None:
        """AC-C44a(a): before_dt=None resolves to the MOST RECENTLY closed session timestamp.

        Uses >500 entries so the hard floor is active.  Both closed sessions and the
        between_edit entry occupy positions 1-4, all outside the last-500 floor window.
        500 entries fill the floor window.  If the older (wrong) cutoff were used,
        between_edit would survive; the correct (newer) cutoff removes it.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        older_close_dt = now - timedelta(hours=604)
        newer_close_dt = now - timedelta(hours=602)

        # Older closed session (task 1) — position 1-2, outside floor window.
        append_activity_event(
            _make_event(action="claim", ts=(now - timedelta(hours=606)).isoformat(), task_id=1),
            kanban_dir,
        )
        append_activity_event(
            _make_event(action="end_work", ts=older_close_dt.isoformat(), task_id=1),
            kanban_dir,
        )

        # Event BETWEEN the two close timestamps — position 3, outside floor window.
        # Removed only if the newer cutoff is used.
        between_ts = (now - timedelta(hours=603)).isoformat()
        append_activity_event(
            _make_event(action="edit", ts=between_ts, task_id=2),
            kanban_dir,
        )

        # Newer closed session end_work (task 2) — position 4, outside floor window.
        # AT the newer cutoff → retained by session/cutoff logic (ts >= cutoff).
        append_activity_event(
            _make_event(action="end_work", ts=newer_close_dt.isoformat(), task_id=2),
            kanban_dir,
        )

        # 499 filler entries + 1 after-entry — positions 5-504, fills the floor window.
        # All are newer than newer_close_dt so they survive both floor and cutoff logic.
        for i in range(499):
            ts = (now - timedelta(hours=601 - i)).isoformat()
            append_activity_event(_make_event(action="edit", ts=ts, task_id=3), kanban_dir)
        append_activity_event(
            _make_event(action="edit", ts=(now - timedelta(hours=1)).isoformat(), task_id=3),
            kanban_dir,
        )

        # Total: 504 entries. Last 500 = filler + after-entry (positions 5-504).
        compact_activity_log(kanban_dir, before_dt=None)
        remaining = list_activity_events(kanban_dir)

        # The edit event between the two close timestamps must be gone (newer cutoff applied)
        assert not any(e.task_id == 2 and e.action == "edit" for e in remaining), (
            "Edit between older and newer close must be removed — proves newer cutoff was used"
        )

        # The newer close event itself must be retained (proves cutoff <= newer_close_dt)
        assert any(e.task_id == 2 and e.action == "end_work" for e in remaining), (
            "Newer close event (task_id=2, end_work) must be retained — proves cutoff <= newer close timestamp"
        )

        # Event after newer close must be present
        assert any(e.task_id == 3 for e in remaining), "Event after newer close must be retained"

    def test_ac_c44a_b_open_sessions_always_retained(self, tmp_path: Path) -> None:
        """AC-C44a (b): entries in open sessions (no matching end event) always retained."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # An old claim with no close event = open session
        old_claim_ts = (now - timedelta(hours=5)).isoformat()
        append_activity_event(
            _make_event(action="claim", ts=old_claim_ts, task_id=99),
            kanban_dir,
        )

        # Compact with explicit past cutoff that would otherwise remove the claim
        cutoff = now - timedelta(hours=4)
        compact_activity_log(kanban_dir, before_dt=cutoff)

        # The open-session claim must still be present
        remaining = list_activity_events(kanban_dir, task_id=99)
        assert len(remaining) >= 1
        assert any(e.action == "claim" for e in remaining)

    def test_ac_c44a_b_reclaim_same_task_compacts_closed_cycle_entries(self, tmp_path: Path) -> None:
        """AC-C44a(b): compaction removes closed-cycle entries for a task that was later re-claimed.

        Uses >500 entries so the hard floor is active.  The old closed cycle (first_claim
        + first_close) occupies positions 1-2, both outside the last-500 floor window.
        499 filler entries + second_claim fill the floor window.  first_claim and
        first_close are removed by cutoff logic (not floor); second_claim is retained by
        the open-session guard.
        Reference domain path: test_list_sessions.py:444-459.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # First (closed) claim cycle for task 7 — positions 1-2, outside floor window.
        first_claim_ts = (now - timedelta(hours=506)).isoformat()
        first_close_ts = (now - timedelta(hours=505)).isoformat()
        append_activity_event(_make_event(action="claim", ts=first_claim_ts, task_id=7), kanban_dir)
        append_activity_event(_make_event(action="end_work", ts=first_close_ts, task_id=7), kanban_dir)

        # 499 filler entries — fills the floor window (positions 3-501).
        for i in range(499):
            ts = (now - timedelta(hours=504 - i)).isoformat()
            append_activity_event(_make_event(action="move", ts=ts, task_id=i % 6 + 1), kanban_dir)

        # Second (open) claim cycle for task 7 — inside floor window (position 502).
        second_claim_ts = (now - timedelta(minutes=30)).isoformat()
        append_activity_event(_make_event(action="claim", ts=second_claim_ts, task_id=7), kanban_dir)

        # Total: 502 entries. Last 500 = filler + second_claim (positions 3-502).
        # Compact with explicit cutoff that makes first_claim and first_close eligible.
        cutoff = now - timedelta(hours=4)
        compact_activity_log(kanban_dir, before_dt=cutoff)

        remaining = list_activity_events(kanban_dir, task_id=7)

        # Old closed-cycle claim must be gone (outside floor, before cutoff).
        assert not any(e.action == "claim" and e.timestamp == first_claim_ts for e in remaining), (
            "Old closed-cycle claim must be compacted"
        )

        # Old closed-cycle close/end_work must also be gone — entire closed cycle eligible.
        assert not any(e.action == "end_work" and e.timestamp == first_close_ts for e in remaining), (
            "Old closed-cycle end_work must also be compacted — not just the claim row"
        )

        # Current open-cycle claim must be retained (open session always kept).
        assert any(e.action == "claim" and e.timestamp == second_claim_ts for e in remaining), (
            "Current open-cycle claim must always be retained"
        )

    def test_ac_c44a_c_last_500_entries_always_retained(self, tmp_path: Path) -> None:
        """AC-C44a (c): at least last 500 entries always retained regardless of cutoff."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # Write 600 old entries
        for i in range(600):
            ts = (now - timedelta(hours=600 - i)).isoformat()
            append_activity_event(_make_event(ts=ts, task_id=i % 10), kanban_dir)

        # Compact with a cutoff that would remove all 600 entries
        past_cutoff = now - timedelta(hours=10)
        compact_activity_log(kanban_dir, before_dt=past_cutoff)

        remaining = list_activity_events(kanban_dir)
        assert len(remaining) >= 500
        # Survivors must be the chronologically LAST 500 entries, not the first 500.
        # Entry at index 100 (0-based) is the 101st written: ts = now - timedelta(hours=500).
        expected_first_survivor_ts = (now - timedelta(hours=500)).isoformat()
        assert remaining[0].timestamp == expected_first_survivor_ts, (
            "Survivors must be the last 500 entries — earliest retained timestamp must match "
            "entry 101 (0-indexed), not entry 1"
        )

    def test_ac_c44a_d_rewritten_atomically(self, tmp_path: Path) -> None:
        """AC-C44a (d): compaction rewrites activity.jsonl via atomic_write (no .tmp- left)."""
        kanban_dir = _make_board(tmp_path)
        for i in range(10):
            append_activity_event(_make_event(task_id=i), kanban_dir)

        compact_activity_log(kanban_dir)

        # No leftover .tmp- files
        tmp_files = list(kanban_dir.glob(".tmp-*"))
        assert tmp_files == [], f"Leftover tmp files after compaction: {tmp_files}"

    def test_ac_c44a_d_delegates_to_atomic_write(self, tmp_path: Path) -> None:
        """AC-C44a(d): compact_activity_log delegates the file rewrite to atomic_write.

        Patches atomic_write at the module level and asserts it is called exactly once
        with the activity.jsonl path as the first argument and a string as the second.
        """
        from unittest.mock import patch  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        for i in range(5):
            ts = (now - timedelta(hours=10 + i)).isoformat()
            append_activity_event(_make_event(task_id=i, ts=ts), kanban_dir)

        # Use a future cutoff so compaction actually rewrites the file
        cutoff = now + timedelta(hours=1)

        with patch("owlbear_kanban.activity_store.atomic_write") as mock_atomic_write:
            compact_activity_log(kanban_dir, before_dt=cutoff)

        mock_atomic_write.assert_called_once()
        call_args = mock_atomic_write.call_args
        # First positional arg: the activity.jsonl path
        assert call_args[0][0] == kanban_dir / "activity.jsonl"
        # Second positional arg: string content (new file body)
        assert isinstance(call_args[0][1], str)

    def test_ac_c44a_e_idempotent_no_new_appends(self, tmp_path: Path) -> None:
        """AC-C44a (e): re-running compaction with same before_dt and no new appends is idempotent."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        old_ts = (now - timedelta(hours=3)).isoformat()
        recent_ts = (now - timedelta(minutes=10)).isoformat()
        append_activity_event(_make_event(ts=old_ts, task_id=1, action="claim"), kanban_dir)
        append_activity_event(
            _make_event(ts=(now - timedelta(hours=2)).isoformat(), task_id=1, action="end_work"),
            kanban_dir,
        )
        append_activity_event(_make_event(ts=recent_ts, task_id=2), kanban_dir)

        cutoff = now - timedelta(hours=1)
        compact_activity_log(kanban_dir, before_dt=cutoff)
        result2 = compact_activity_log(kanban_dir, before_dt=cutoff)

        # Second run compacts zero additional records
        assert result2.records_compacted == 0
        assert result2.before_bytes == result2.after_bytes

    def test_ac_c44a_returns_activity_compaction_result(self, tmp_path: Path) -> None:
        """AC-C44a: compact_activity_log returns ActivityCompactionResult with required fields."""
        kanban_dir = _make_board(tmp_path)
        for i in range(5):
            append_activity_event(_make_event(task_id=i), kanban_dir)

        result = compact_activity_log(kanban_dir)

        assert hasattr(result, "before_bytes")
        assert hasattr(result, "after_bytes")
        assert hasattr(result, "records_compacted")
        assert isinstance(result.before_bytes, int)
        assert isinstance(result.after_bytes, int)
        assert isinstance(result.records_compacted, int)


# ---------------------------------------------------------------------------
# TestBuilderDiscovered — additional coverage for activity_store.py
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered tests for activity_store edge cases."""

    def test_compact_activity_log_floor_applies_to_small_session_logs(self, tmp_path: Path) -> None:
        """Small session-bearing logs retain all rows when cutoff would compact everything."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        n = 120

        for i in range(n):
            ts = (now - timedelta(minutes=n - i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=i % 10, action="end_work"),
                kanban_dir,
            )

        # Future cutoff makes every row a compaction candidate; only hard floor protects.
        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0
        assert len(list_activity_events(kanban_dir)) == n

    def test_list_activity_events_skips_malformed_rows(self, tmp_path: Path) -> None:
        """Malformed JSONL rows are ignored and valid rows are still returned."""
        kanban_dir = _make_board(tmp_path)
        activity_file = kanban_dir / "activity.jsonl"
        valid_ts = datetime.now(tz=UTC).isoformat()

        activity_file.write_text(
            "\n"  # blank line
            "{not-json}\n"  # invalid JSON
            "[]\n"  # non-dict JSON value
            '{"timestamp":"2026-04-21T10:00:00+00:00"}\n'  # missing required action
            '{"timestamp":"2026-04-21T10:00:00+00:00","action":"claim","task_id":{"bad":1}}\n'  # invalid schema
            f'{{"timestamp":"{valid_ts}","task_id":77,"action":"claim","source":"agent","detail":"ok"}}\n',
            encoding="utf-8",
        )

        result = list_activity_events(kanban_dir)
        assert len(result) == 1
        assert result[0].task_id == 77

    def test_compact_activity_log_missing_file_returns_zeroes(self, tmp_path: Path) -> None:
        """Compaction on a missing activity.jsonl returns zero-byte/zero-record result."""
        kanban_dir = _make_board(tmp_path)

        result = compact_activity_log(kanban_dir)

        assert result.before_bytes == 0
        assert result.after_bytes == 0
        assert result.records_compacted == 0

    def test_compact_activity_log_empty_file_returns_noop(self, tmp_path: Path) -> None:
        """Compaction on an empty activity.jsonl is a no-op preserving file size."""
        kanban_dir = _make_board(tmp_path)
        activity_file = kanban_dir / "activity.jsonl"
        activity_file.write_text("\n\n", encoding="utf-8")

        result = compact_activity_log(kanban_dir)

        assert result.before_bytes == result.after_bytes
        assert result.records_compacted == 0

    def test_list_activity_events_until_filter(self, tmp_path: Path) -> None:
        """list_activity_events with until= excludes events after the cutoff."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        old_ts = (now - timedelta(hours=2)).isoformat()
        recent_ts = now.isoformat()
        append_activity_event(_make_event(ts=old_ts, task_id=1), kanban_dir)
        append_activity_event(_make_event(ts=recent_ts, task_id=2), kanban_dir)

        cutoff = (now - timedelta(hours=1)).isoformat()
        results = list_activity_events(kanban_dir, until=cutoff)
        task_ids = [e.task_id for e in results]
        assert 1 in task_ids
        assert 2 not in task_ids

    def test_compact_activity_log_hard_floor_500(self, tmp_path: Path) -> None:
        """compact_activity_log hard floor: with >500 old events and old cutoff, keeps >=500."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        # Write 600 old events
        for i in range(600):
            ts = (now - timedelta(hours=600 - i)).isoformat()
            append_activity_event(_make_event(ts=ts, task_id=i % 10, action="edit"), kanban_dir)
        # Compact with a cutoff newer than all entries so floor logic is required.
        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)
        # Hard floor: should not compact below 500
        assert result.records_compacted == 100
        assert len(list_activity_events(kanban_dir)) == 500

    def test_parse_dt_naive_datetime_gets_utc(self) -> None:
        """_parse_dt adds UTC timezone to naive datetimes."""
        from owlbear_kanban.activity_store import _parse_dt  # noqa: PLC0415

        dt = _parse_dt("2026-04-20T10:00:00")
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.tzinfo == UTC

    def test_parse_dt_invalid_returns_none(self) -> None:
        """_parse_dt returns None for invalid ISO-8601 strings."""
        from owlbear_kanban.activity_store import _parse_dt  # noqa: PLC0415

        assert _parse_dt("not-a-datetime") is None

    def test_list_activity_events_source_filter(self, tmp_path: Path) -> None:
        """list_activity_events with source= filter returns only matching events."""
        kanban_dir = _make_board(tmp_path)
        append_activity_event(_make_event(source="engine", task_id=1), kanban_dir)
        append_activity_event(_make_event(source="agent", task_id=2), kanban_dir)
        results = list_activity_events(kanban_dir, source="engine")
        assert all(e.source == "engine" for e in results)
        assert len(results) == 1


# Promoted from task #1058: floor-boundary, idempotency, and model contract regressions.


def _make_board_1058(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _ts_1058(delta: timedelta | None = None) -> str:
    t = datetime.now(tz=UTC)
    if delta is not None:
        t = t + delta
    return t.isoformat()


def _make_event_1058(
    *,
    task_id: int | None = 1001,
    action: str = "claim",
    source: str = "agent",
    detail: str = "test event",
    ts: str | None = None,
) -> ActivityEvent:
    return ActivityEvent(
        timestamp=ts or _ts_1058(),
        task_id=task_id,
        action=action,
        source=source,
        detail=detail,
    )


class TestFromAC_ActivityStoreFloorBoundary:
    """AC-C44a(c): hard-floor boundary — exactly 500 entries and fewer than 500 entries.

    The brief states: "always retain the last 500 entries by timestamp regardless of
    cutoff or session state (prevents catastrophic compaction on a small board)."

    The implementation uses ``len(all_lines) > _HARD_FLOOR`` (strict greater-than), so
    for exactly 500 entries ``500 > 500 == False`` and the floor is never activated.
    All 500 entries are removed.  The same defect applies to any board smaller than 500.
    """

    def test_ac_c44a_c_exactly_500_entries_floor_retains_all(self, tmp_path: Path) -> None:
        """AC-C44a(c): exactly 500 entries + future cutoff → records_compacted == 0.

        When the total log size equals the floor (500), the floor must protect all entries.
        No records should be compacted.

        Bug: ``len(all_lines) > _HARD_FLOOR`` evaluates to ``500 > 500 == False``, so
        the floor guard never runs.  All 500 entries are removed instead.

        Uses action="move" (not claim/end_work) to avoid the open-session guard,
        isolating the floor mechanism as the sole protection path.
        """
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)

        for i in range(500):
            ts = (now - timedelta(hours=500 - i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=i % 20, action="move"), kanban_dir)

        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            f"Floor must protect all 500 entries when log size == _HARD_FLOOR; "
            f"wrongly compacted {result.records_compacted}"
        )
        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == 500

    def test_ac_c44a_c_small_board_fewer_than_500_entries_all_retained(self, tmp_path: Path) -> None:
        """AC-C44a(c): small board (300 entries) + future cutoff → records_compacted == 0.

        Brief §7.1 explicitly names "prevents catastrophic compaction on a small board".
        For a board with 300 entries the effective floor is min(500, 300) == 300; every
        entry must be retained, even with a cutoff newer than all of them.

        Bug: ``len(all_lines) > _HARD_FLOOR`` → ``300 > 500 == False``.  Floor skipped.
        All 300 entries wrongly removed.

        Uses action="move" to isolate floor protection from the open-session guard.
        """
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)
        n = 300

        for i in range(n):
            ts = (now - timedelta(hours=n - i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=i % 10, action="move"), kanban_dir)

        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            f"Floor must protect all {n} entries on a small board; wrongly compacted {result.records_compacted}"
        )
        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == n

    def test_ac_c44a_c_single_entry_board_floor_retains_it(self, tmp_path: Path) -> None:
        """AC-C44a(c): single-entry board + future cutoff → record is retained (floor protects).

        A board with 1 entry has an effective floor of 1; that entry must never be
        compacted regardless of the cutoff.  This is the extreme small-board case.

        Bug: ``1 > 500 == False`` → floor not activated → entry wrongly removed.

        Uses action="move" so the open-session guard cannot protect the entry,
        leaving only the floor as protection.
        """
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)

        old_ts = (now - timedelta(hours=48)).isoformat()
        append_activity_event(_make_event_1058(ts=old_ts, task_id=7, action="move"), kanban_dir)

        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            f"A single-entry board must not compact its only record; wrongly compacted {result.records_compacted}"
        )
        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == 1


class TestFromAC_ActivityCompactionIdempotency:
    """AC-C44a(e): idempotency — re-running compact with same before_dt is a no-op.

    The existing idempotency test covers the normal case (> 500 entries).  This class
    covers idempotency at the boundary where floor behaviour must hold on every run.
    """

    def test_ac_c44a_e_idempotent_at_floor_boundary_small_board(self, tmp_path: Path) -> None:
        """AC-C44a(e): two successive compactions on a 300-entry board both compact 0 records.

        With a future cutoff the first run must compact 0 records (floor protects all).
        The second run on the unchanged file must also compact 0 records.  Any run that
        removes entries violates the floor and also breaks idempotency.

        Bug: first run removes all 300 (floor inactive) → second run sees empty file and
        compacts 0 → appears idempotent but produces wrong final state.
        """
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)
        n = 300

        for i in range(n):
            ts = (now - timedelta(hours=n - i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=i % 10, action="move"), kanban_dir)

        cutoff = now + timedelta(hours=1)
        result1 = compact_activity_log(kanban_dir, before_dt=cutoff)
        result2 = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result1.records_compacted == 0, (
            f"First compact must not remove entries (floor protects 300); compacted {result1.records_compacted}"
        )
        assert result2.records_compacted == 0, (
            f"Second compact must also compact 0 (idempotent); compacted {result2.records_compacted}"
        )
        assert result1.before_bytes == result2.before_bytes, (
            "File size must be unchanged between runs — idempotency violated"
        )


class TestFromAC_ActivityEventModel:
    """AC §1.2: ActivityEvent and ActivityCompactionResult model field contracts.

    Brief C §1.2 specifies ``detail: str`` — a required, non-nullable string field.
    The implementation has ``detail: str | None = None``, allowing omission and None.
    """

    def test_ac_activity_event_detail_is_required_non_nullable(self) -> None:
        """AC §1.2: ActivityEvent must reject creation when detail is omitted.

        Brief C §1.2:
            detail: str  # human-readable structured detail payload

        No Optional, no default.  Creating ActivityEvent without detail must raise
        ValidationError.  Currently the field is ``str | None = None`` — no error raised.
        """
        from pydantic import ValidationError  # noqa: PLC0415

        with pytest.raises(ValidationError):
            ActivityEvent(
                timestamp="2026-04-23T00:00:00+00:00",
                task_id=1,
                action="claim",
                source="agent",
            )

    def test_ac_activity_event_detail_none_is_rejected(self) -> None:
        """AC §1.2: ActivityEvent.detail=None must be rejected (required str, not Optional).

        Brief C §1.2 specifies ``detail: str``.  Explicitly passing ``None`` must
        raise ValidationError.  Currently the model accepts None silently.
        """
        from pydantic import ValidationError  # noqa: PLC0415

        with pytest.raises(ValidationError):
            ActivityEvent(
                timestamp="2026-04-23T00:00:00+00:00",
                task_id=1,
                action="claim",
                source="agent",
                detail=None,
            )

    def test_ac_activity_event_written_detail_none_not_in_jsonl(self, tmp_path: Path) -> None:
        """AC §1.2: when detail is required, an event without detail must never appear in JSONL.

        If ActivityEvent requires detail, appending an event with detail=None must either
        be rejected at construction (tested above) or produce a record that list_activity_events
        skips.  list_activity_events must not return events whose detail violates the schema.

        Since the model currently allows detail=None, this test constructs the invalid event
        via raw JSON injection and asserts list_activity_events filters it out.
        """
        kanban_dir = _make_board_1058(tmp_path)
        activity_file = kanban_dir / "activity.jsonl"

        raw = {
            "timestamp": "2026-04-23T00:00:00+00:00",
            "task_id": 99,
            "action": "claim",
            "source": "agent",
            "detail": None,
        }
        activity_file.write_text(json.dumps(raw) + "\n", encoding="utf-8")

        events = list_activity_events(kanban_dir)
        assert events == [], (
            f"list_activity_events must skip JSONL lines whose detail violates §1.2 (detail=null); got {events}"
        )


class TestFromAC_ActivityStoreFloorSessionBearing:
    """AC-C44a(c): hard floor applies regardless of cutoff or session state.

    Brief C §7.1: "always retain the last 500 entries by timestamp regardless of
    cutoff or session state (prevents catastrophic compaction on a small board)."

    The existing floor tests (TestFromAC_ActivityStoreFloorBoundary) isolate the floor
    path using action="move" (non-session actions).  These tests cover the two remaining
    branches where session state suppresses the floor for small (<=500) logs:

    1. auto_cutoff=True (before_dt=None) — floor_count incorrectly set to 0.
    2. open_session_starts non-empty — floor_count incorrectly set to 0.
    """

    def test_ac_c44a_c_auto_cutoff_session_bearing_small_log_floor_retains_all(self, tmp_path: Path) -> None:
        """AC-C44a(c): before_dt=None on a small (<=500) fully-closed session log retains all."""
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)
        n = 50

        for i in range(n // 2):
            claim_ts = (now - timedelta(hours=n - i * 2)).isoformat()
            close_ts = (now - timedelta(hours=n - i * 2 - 1)).isoformat()
            append_activity_event(_make_event_1058(ts=claim_ts, task_id=i + 1, action="claim"), kanban_dir)
            append_activity_event(
                _make_event_1058(ts=close_ts, task_id=i + 1, action="end_work"),
                kanban_dir,
            )

        assert len(list_activity_events(kanban_dir)) == n
        result = compact_activity_log(kanban_dir)

        assert result.records_compacted == 0, (
            f"Floor must protect all {n} session entries (<=500) even with auto_cutoff; "
            f"wrongly compacted {result.records_compacted}"
        )
        assert len(list_activity_events(kanban_dir)) == n, (
            f"All {n} entries must survive; found {len(list_activity_events(kanban_dir))}"
        )

    def test_ac_c44a_c_open_session_small_log_floor_protects_all_entries(self, tmp_path: Path) -> None:
        """AC-C44a(c): small (<=500) log with an open session retains all entries via hard floor."""
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)
        n_move = 80

        for i in range(n_move):
            ts = (now - timedelta(hours=n_move - i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=i % 10, action="move"), kanban_dir)

        claim_ts = (now - timedelta(minutes=30)).isoformat()
        append_activity_event(_make_event_1058(ts=claim_ts, task_id=999, action="claim"), kanban_dir)

        total = n_move + 1
        assert len(list_activity_events(kanban_dir)) == total

        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            f"Floor must protect all {total} entries (<=500) even with an open session; "
            f"wrongly compacted {result.records_compacted}"
        )
        assert len(list_activity_events(kanban_dir)) == total, (
            f"All {total} entries must survive; found {len(list_activity_events(kanban_dir))}"
        )


class TestFromAC_ActivityStoreFloorActiveStream:
    """AC-C44a(c): hard floor applies when before_dt < latest_entry_dt (active-stream)."""

    def test_ac_c44a_c_auto_cutoff_active_stream_small_log_floor_retains_all(self, tmp_path: Path) -> None:
        """AC-C44a(c): auto-cutoff + active-stream entries newer than cutoff + small log."""
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)

        n_pairs = 5
        for i in range(n_pairs):
            claim_ts = (now - timedelta(hours=50 - i * 2)).isoformat()
            end_work_ts = (now - timedelta(hours=49 - i * 2)).isoformat()
            append_activity_event(_make_event_1058(ts=claim_ts, task_id=i + 1, action="claim"), kanban_dir)
            append_activity_event(
                _make_event_1058(ts=end_work_ts, task_id=i + 1, action="end_work"),
                kanban_dir,
            )

        n_active = 20
        for i in range(n_active):
            ts = (now - timedelta(hours=30 - i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=99, action="move"), kanban_dir)

        total = n_pairs * 2 + n_active
        assert len(list_activity_events(kanban_dir)) == total

        result = compact_activity_log(kanban_dir)

        assert result.records_compacted == 0, (
            f"Floor must protect all {total} entries (<=500) when auto_cutoff=True and "
            f"active-stream entries are newer than the resolved cutoff; "
            f"wrongly compacted {result.records_compacted}"
        )
        assert len(list_activity_events(kanban_dir)) == total, (
            f"All {total} entries must survive; found {len(list_activity_events(kanban_dir))}"
        )

    def test_ac_c44a_c_explicit_cutoff_active_stream_open_session_small_log_floor_retains_all(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(c): explicit cutoff < latest_entry_dt + open session + small log."""
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)

        n_old = 30
        for i in range(n_old):
            ts = (now - timedelta(hours=60 - i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=i % 5, action="move"), kanban_dir)

        claim_ts = (now - timedelta(hours=20)).isoformat()
        append_activity_event(_make_event_1058(ts=claim_ts, task_id=999, action="claim"), kanban_dir)

        n_new = 15
        for i in range(n_new):
            ts = (now - timedelta(hours=15 - i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=i % 5, action="move"), kanban_dir)

        total = n_old + 1 + n_new
        assert len(list_activity_events(kanban_dir)) == total

        before_dt = now - timedelta(hours=25)
        result = compact_activity_log(kanban_dir, before_dt=before_dt)

        assert result.records_compacted == 0, (
            f"Floor must protect all {total} entries (<=500) when "
            f"before_dt < latest_entry_dt and an open session exists; "
            f"wrongly compacted {result.records_compacted}"
        )
        assert len(list_activity_events(kanban_dir)) == total, (
            f"All {total} entries must survive; found {len(list_activity_events(kanban_dir))}"
        )


class TestFromAC_ActivityStoreFloorTimestampOrder:
    """AC-C44a-ts: floor retains entries by parsed timestamp value, not by file position."""

    def test_ac_c44a_ts_backdated_entry_excluded_from_floor_non_monotonic(self, tmp_path: Path) -> None:
        """AC-C44a-ts: backdated late-appended entry is dropped; more-recent entry retained."""
        kanban_dir = _make_board_1058(tmp_path)
        now = datetime.now(tz=UTC)

        backdated_task_id = 9999

        for i in range(1, 502):
            ts = (now + timedelta(hours=i)).isoformat()
            append_activity_event(_make_event_1058(ts=ts, task_id=i, action="move"), kanban_dir)

        backdated_ts = (now - timedelta(hours=10_000)).isoformat()
        append_activity_event(
            _make_event_1058(ts=backdated_ts, task_id=backdated_task_id, action="move"),
            kanban_dir,
        )

        assert len(list_activity_events(kanban_dir)) == 502

        cutoff = now + timedelta(hours=100_000)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 2

        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == 500

        remaining_task_ids = {e.task_id for e in remaining}

        assert backdated_task_id not in remaining_task_ids, (
            f"task_id={backdated_task_id} (timestamp=T-10000h, position=502) must be "
            "excluded by timestamp-based floor; position-based floor wrongly retains it."
        )

        assert 2 in remaining_task_ids, (
            "task_id=2 (timestamp=T+2h, rank 500 by recency) must be retained; position-based floor wrongly drops it."
        )
