"""TDD RED: C-04 — activity_store append/query/compact tests.

Task: #1049 (Brief C #1043) — paper-c.md §8.9
AC:   C42, C44, C44a
All tests FAIL (RED phase — activity_store not yet implemented).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


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

    def test_ac_c44a_a_before_dt_none_resolves_to_latest_closed_session(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a (a): before_dt=None uses most-recently-closed session ended_at as cutoff."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # Old closed session
        old_ts = (now - timedelta(hours=3)).isoformat()
        append_activity_event(_make_event(action="claim", ts=old_ts, task_id=1), kanban_dir)
        close_ts = (now - timedelta(hours=2)).isoformat()
        append_activity_event(
            _make_event(action="end_work", ts=close_ts, task_id=1, source="agent", detail="success: done"),
            kanban_dir,
        )
        # Recent entries (after cutoff)
        for i in range(3):
            recent_ts = (now - timedelta(minutes=30 - i * 5)).isoformat()
            append_activity_event(_make_event(ts=recent_ts, task_id=2), kanban_dir)

        result = compact_activity_log(kanban_dir, before_dt=None)
        assert isinstance(result, ActivityCompactionResult)
        # Before > after (something was compacted)
        assert result.before_bytes > result.after_bytes

    def test_ac_c44a_a_resolves_to_most_recent_close_not_oldest(self, tmp_path: Path) -> None:
        """AC-C44a(a): before_dt=None resolves to the MOST RECENTLY closed session timestamp.

        Two closed sessions exist. Verifies the cutoff is the newer one, not the older,
        by checking which event survives compaction. An event between the two close timestamps
        must be removed (proves newer cutoff), whereas it would be retained if the older
        cutoff was erroneously selected.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        older_close_dt = now - timedelta(hours=4)
        newer_close_dt = now - timedelta(hours=2)

        # Older closed session
        append_activity_event(
            _make_event(action="claim", ts=(now - timedelta(hours=6)).isoformat(), task_id=1),
            kanban_dir,
        )
        append_activity_event(
            _make_event(action="end_work", ts=older_close_dt.isoformat(), task_id=1),
            kanban_dir,
        )

        # Event BETWEEN the two close timestamps — removed only if newer cutoff is used
        between_ts = (now - timedelta(hours=3)).isoformat()
        append_activity_event(
            _make_event(action="edit", ts=between_ts, task_id=2),
            kanban_dir,
        )

        # Newer closed session
        append_activity_event(
            _make_event(action="end_work", ts=newer_close_dt.isoformat(), task_id=2),
            kanban_dir,
        )

        # Event after newer close — must always be retained
        append_activity_event(
            _make_event(action="edit", ts=(now - timedelta(hours=1)).isoformat(), task_id=3),
            kanban_dir,
        )

        compact_activity_log(kanban_dir, before_dt=None)
        remaining = list_activity_events(kanban_dir)

        # The edit event between the two close timestamps must be gone (newer cutoff applied)
        assert not any(
            e.task_id == 2 and e.action == "edit" for e in remaining
        ), "Edit between older and newer close must be removed — proves newer cutoff was used"

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

    def test_ac_c44a_b_reclaim_same_task_compacts_closed_cycle_entries(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(b): compaction removes closed-cycle entries for a task that was later re-claimed.

        A task claimed, then closed/released, then re-claimed: only the current open cycle
        must survive compaction. The old closed cycle's entries are eligible for removal.
        Reference domain path: test_list_sessions.py:444-459.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # First (closed) claim cycle for task 7
        first_claim_ts = (now - timedelta(hours=6)).isoformat()
        first_close_ts = (now - timedelta(hours=5)).isoformat()
        append_activity_event(
            _make_event(action="claim", ts=first_claim_ts, task_id=7), kanban_dir
        )
        append_activity_event(
            _make_event(action="end_work", ts=first_close_ts, task_id=7), kanban_dir
        )

        # Second (open) claim cycle for the same task 7
        second_claim_ts = (now - timedelta(minutes=30)).isoformat()
        append_activity_event(
            _make_event(action="claim", ts=second_claim_ts, task_id=7), kanban_dir
        )

        # Compact with cutoff that makes the first cycle eligible for removal
        cutoff = now - timedelta(hours=4)
        compact_activity_log(kanban_dir, before_dt=cutoff)

        remaining = list_activity_events(kanban_dir, task_id=7)

        # Old closed-cycle claim must be gone (closed cycle, before cutoff)
        assert not any(
            e.action == "claim" and e.timestamp == first_claim_ts for e in remaining
        ), "Old closed-cycle claim must be compacted"

        # Current open-cycle claim must be retained (open session always kept)
        assert any(
            e.action == "claim" and e.timestamp == second_claim_ts for e in remaining
        ), "Current open-cycle claim must always be retained"

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
