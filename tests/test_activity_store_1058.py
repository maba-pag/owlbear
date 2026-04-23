"""TDD RED: C-13 — activity_store boundary and model contract tests.

Task: #1058 (Brief C #1043) — paper-c.md §7, §8.9
AC:   AC-C44a(c) hard-floor boundary, AC-C44a(e) idempotency at boundary,
      ActivityEvent.detail required (§1.2)
All tests FAIL (RED phase).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_kanban.activity_store import (
    append_activity_event,
    compact_activity_log,
    list_activity_events,
)
from owlbear_kanban.models import ActivityEvent


# ---------------------------------------------------------------------------
# Board helpers (mirrors serve/kanban/tests/test_activity_store.py)
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
# TestFromAC_ActivityStoreFloorBoundary — AC-C44a(c)
# ---------------------------------------------------------------------------


class TestFromAC_ActivityStoreFloorBoundary:
    """AC-C44a(c): hard-floor boundary — exactly 500 entries and fewer than 500 entries.

    The brief states: "always retain the last 500 entries by timestamp regardless of
    cutoff or session state (prevents catastrophic compaction on a small board)."

    The implementation uses ``len(all_lines) > _HARD_FLOOR`` (strict greater-than), so
    for exactly 500 entries ``500 > 500 == False`` and the floor is never activated.
    All 500 entries are removed.  The same defect applies to any board smaller than 500.
    """

    def test_ac_c44a_c_exactly_500_entries_floor_retains_all(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(c): exactly 500 entries + future cutoff → records_compacted == 0.

        When the total log size equals the floor (500), the floor must protect all entries.
        No records should be compacted.

        Bug: ``len(all_lines) > _HARD_FLOOR`` evaluates to ``500 > 500 == False``, so
        the floor guard never runs.  All 500 entries are removed instead.

        Uses action="move" (not claim/end_work) to avoid the open-session guard,
        isolating the floor mechanism as the sole protection path.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        for i in range(500):
            ts = (now - timedelta(hours=500 - i)).isoformat()
            # action="move" is not a session-open or session-close action, so no entry
            # is protected by the open-session guard — only the floor can protect them.
            append_activity_event(
                _make_event(ts=ts, task_id=i % 20, action="move"), kanban_dir
            )

        # Future cutoff makes every entry a compaction candidate
        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            f"Floor must protect all 500 entries when log size == _HARD_FLOOR; "
            f"wrongly compacted {result.records_compacted}"
        )
        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == 500

    def test_ac_c44a_c_small_board_fewer_than_500_entries_all_retained(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(c): small board (300 entries) + future cutoff → records_compacted == 0.

        Brief §7.1 explicitly names "prevents catastrophic compaction on a small board".
        For a board with 300 entries the effective floor is min(500, 300) == 300; every
        entry must be retained, even with a cutoff newer than all of them.

        Bug: ``len(all_lines) > _HARD_FLOOR`` → ``300 > 500 == False``.  Floor skipped.
        All 300 entries wrongly removed.

        Uses action="move" to isolate floor protection from the open-session guard.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        n = 300

        for i in range(n):
            ts = (now - timedelta(hours=n - i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=i % 10, action="move"), kanban_dir
            )

        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            f"Floor must protect all {n} entries on a small board; "
            f"wrongly compacted {result.records_compacted}"
        )
        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == n

    def test_ac_c44a_c_single_entry_board_floor_retains_it(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(c): single-entry board + future cutoff → record is retained (floor protects).

        A board with 1 entry has an effective floor of 1; that entry must never be
        compacted regardless of the cutoff.  This is the extreme small-board case.

        Bug: ``1 > 500 == False`` → floor not activated → entry wrongly removed.

        Uses action="move" so the open-session guard cannot protect the entry,
        leaving only the floor as protection.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        old_ts = (now - timedelta(hours=48)).isoformat()
        # action="move" is not a session action → entry is NOT in an open session;
        # only the floor can protect it.
        append_activity_event(
            _make_event(ts=old_ts, task_id=7, action="move"), kanban_dir
        )

        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            "A single-entry board must not compact its only record; "
            f"wrongly compacted {result.records_compacted}"
        )
        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == 1


# ---------------------------------------------------------------------------
# TestFromAC_ActivityCompactionIdempotency — AC-C44a(e) at floor boundary
# ---------------------------------------------------------------------------


class TestFromAC_ActivityCompactionIdempotency:
    """AC-C44a(e): idempotency — re-running compact with same before_dt is a no-op.

    The existing idempotency test covers the normal case (> 500 entries).  This class
    covers idempotency at the boundary where floor behaviour must hold on every run.
    """

    def test_ac_c44a_e_idempotent_at_floor_boundary_small_board(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(e): two successive compactions on a 300-entry board both compact 0 records.

        With a future cutoff the first run must compact 0 records (floor protects all).
        The second run on the unchanged file must also compact 0 records.  Any run that
        removes entries violates the floor and also breaks idempotency.

        Bug: first run removes all 300 (floor inactive) → second run sees empty file and
        compacts 0 → appears idempotent but produces wrong final state.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        n = 300

        for i in range(n):
            ts = (now - timedelta(hours=n - i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=i % 10, action="move"), kanban_dir
            )

        cutoff = now + timedelta(hours=1)
        result1 = compact_activity_log(kanban_dir, before_dt=cutoff)
        result2 = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result1.records_compacted == 0, (
            f"First compact must not remove entries (floor protects 300); "
            f"compacted {result1.records_compacted}"
        )
        assert result2.records_compacted == 0, (
            f"Second compact must also compact 0 (idempotent); "
            f"compacted {result2.records_compacted}"
        )
        assert result1.before_bytes == result2.before_bytes, (
            "File size must be unchanged between runs — idempotency violated"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ActivityEventModel — ActivityEvent and ActivityCompactionResult §1.2
# ---------------------------------------------------------------------------


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
                # detail intentionally omitted
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
                detail=None,  # must be rejected — brief says `detail: str` not `str | None`
            )

    def test_ac_activity_event_written_detail_none_not_in_jsonl(
        self, tmp_path: Path
    ) -> None:
        """AC §1.2: when detail is required, an event without detail must never appear in JSONL.

        If ActivityEvent requires detail, appending an event with detail=None must either
        be rejected at construction (tested above) or produce a record that list_activity_events
        skips.  list_activity_events must not return events whose detail violates the schema.

        Since the model currently allows detail=None, this test constructs the invalid event
        via raw JSON injection and asserts list_activity_events filters it out.
        """
        import json  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        activity_file = kanban_dir / "activity.jsonl"

        # Write a raw record with detail=null — simulates what a buggy writer could produce
        raw = {
            "timestamp": "2026-04-23T00:00:00+00:00",
            "task_id": 99,
            "action": "claim",
            "source": "agent",
            "detail": None,  # null detail violates §1.2 `detail: str`
        }
        activity_file.write_text(json.dumps(raw) + "\n", encoding="utf-8")

        # list_activity_events must skip events that violate the canonical schema
        events = list_activity_events(kanban_dir)
        assert events == [], (
            "list_activity_events must skip JSONL lines whose detail violates §1.2 "
            f"(detail=null); got {events}"
        )
