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


# ---------------------------------------------------------------------------
# TestFromAC_ActivityStoreFloorSessionBearing — AC-C44a(c) session-state branches
# ---------------------------------------------------------------------------


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

    def test_ac_c44a_c_auto_cutoff_session_bearing_small_log_floor_retains_all(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(c): before_dt=None on a small (<=500) fully-closed session log retains all.

        The auto-cutoff resolves to the most recent end_work timestamp.  Entries strictly
        before that timestamp become compaction candidates.  With N <= 500 total entries
        the hard floor (min(500, N) == N) must prevent any compaction regardless of the
        auto_cutoff flag.

        Bug: current code evaluates ``has_session_actions and auto_cutoff`` as True and
        sets ``floor_count = _HARD_FLOOR if N > _HARD_FLOOR else 0`` = 0 for N <= 500.
        All entries before the resolved cutoff are removed, violating "regardless of
        cutoff or session state."
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        n = 50  # well below the 500 floor

        # Build n entries as closed claim/end_work cycles, all in the past.
        # The last end_work timestamp becomes the auto-resolved cutoff, making all
        # earlier entries compaction candidates.
        for i in range(n // 2):
            claim_ts = (now - timedelta(hours=n - i * 2)).isoformat()
            close_ts = (now - timedelta(hours=n - i * 2 - 1)).isoformat()
            append_activity_event(
                _make_event(ts=claim_ts, task_id=i + 1, action="claim"), kanban_dir
            )
            append_activity_event(
                _make_event(ts=close_ts, task_id=i + 1, action="end_work"), kanban_dir
            )

        assert len(list_activity_events(kanban_dir)) == n

        # before_dt=None: auto-cutoff resolves to last end_work; 49 earlier entries
        # become candidates.  Floor (min(500, 50) = 50) must retain all.
        result = compact_activity_log(kanban_dir)

        assert result.records_compacted == 0, (
            f"Floor must protect all {n} session entries (<=500) even with auto_cutoff; "
            f"wrongly compacted {result.records_compacted}"
        )
        assert len(list_activity_events(kanban_dir)) == n, (
            f"All {n} entries must survive; found {len(list_activity_events(kanban_dir))}"
        )

    def test_ac_c44a_c_open_session_small_log_floor_protects_all_entries(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(c): small (<=500) log with an open session retains all entries via hard floor.

        An open session (unmatched claim) causes open_session_starts to be non-empty.
        The open-session guard already retains the claim entry; the hard floor
        (min(500, N) == N) must retain every other entry too, since N <= 500.

        Bug: current code evaluates ``has_session_actions and bool(open_session_starts)``
        as True and sets ``floor_count = 0`` for N <= 500.  Only the open-session entry
        survives; all other entries are wrongly compacted.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)
        n_move = 80  # non-session entries that rely solely on the floor for protection

        # Non-session "move" entries, all old (before the future cutoff).
        for i in range(n_move):
            ts = (now - timedelta(hours=n_move - i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=i % 10, action="move"), kanban_dir
            )

        # Open session: a claim with no matching end_work.
        claim_ts = (now - timedelta(minutes=30)).isoformat()
        append_activity_event(
            _make_event(ts=claim_ts, task_id=999, action="claim"), kanban_dir
        )

        total = n_move + 1  # 81 entries, all <= 500
        assert len(list_activity_events(kanban_dir)) == total

        # Future cutoff makes every entry a compaction candidate except the open-session
        # claim (protected by open-session guard).  Floor (min(500, 81) = 81) must
        # protect all 81 entries — records_compacted must be 0.
        cutoff = now + timedelta(hours=1)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        assert result.records_compacted == 0, (
            f"Floor must protect all {total} entries (<=500) even with an open session; "
            f"wrongly compacted {result.records_compacted}"
        )
        assert len(list_activity_events(kanban_dir)) == total, (
            f"All {total} entries must survive; found {len(list_activity_events(kanban_dir))}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ActivityStoreFloorActiveStream — AC-C44a(c) active-stream branch
# ---------------------------------------------------------------------------


class TestFromAC_ActivityStoreFloorActiveStream:
    """AC-C44a(c): hard floor applies when before_dt < latest_entry_dt (active-stream).

    Brief C §7.1: "always retain the last 500 entries by timestamp regardless of
    cutoff or session state (prevents catastrophic compaction on a small board)."

    The existing TestFromAC_ActivityStoreFloorSessionBearing tests avoid the
    compatibility branch in ``compact_activity_log`` (lines 183-202) because their
    cutoffs equal or exceed the latest log entry.  This class targets the distinct
    ``before_dt < latest_entry_dt`` condition, which causes ``floor_count = 0`` and
    allows compaction below the hard floor for small session-bearing logs.

    Two branches trigger this path:
    1. ``auto_cutoff=True`` — cutoff resolves to the last closed session's ``end_work``,
       but the log has newer entries written after that session (active stream).
    2. ``bool(open_session_starts)=True`` — explicit cutoff older than the latest entry
       with an open (unmatched) claim in the log.
    """

    def test_ac_c44a_c_auto_cutoff_active_stream_small_log_floor_retains_all(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a(c): auto-cutoff + active-stream entries newer than cutoff + small log.

        When ``before_dt=None``, the cutoff auto-resolves to the last closed session's
        ``end_work``.  If the log has newer non-session entries written after that session
        (an active stream), then ``before_dt < latest_entry_dt``.

        For a small log (total ≤ 500) the brief's hard floor ``min(500, N) == N`` must
        protect ALL entries — records_compacted must be 0.

        Bug: the compatibility branch fires because
        ``has_session_actions=True, auto_cutoff=True, N<=500, before_dt < latest_entry_dt``
        → ``floor_count = 0`` → entries before the resolved cutoff are wrongly compacted.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # 5 closed claim/end_work pairs — all old.
        # Auto-cutoff resolves to the last end_work at now-41h.
        n_pairs = 5
        for i in range(n_pairs):
            claim_ts = (now - timedelta(hours=50 - i * 2)).isoformat()
            end_work_ts = (now - timedelta(hours=49 - i * 2)).isoformat()
            append_activity_event(
                _make_event(ts=claim_ts, task_id=i + 1, action="claim"), kanban_dir
            )
            append_activity_event(
                _make_event(ts=end_work_ts, task_id=i + 1, action="end_work"),
                kanban_dir,
            )
        # Last end_work at: now - (49 - (n_pairs-1)*2) = now - (49 - 8) = now - 41h.

        # 20 move entries written AFTER the last session closed — the "active stream".
        # latest_entry_dt = now - 11h > before_dt (now - 41h) → triggers compat branch.
        n_active = 20
        for i in range(n_active):
            ts = (now - timedelta(hours=30 - i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=99, action="move"), kanban_dir
            )

        total = n_pairs * 2 + n_active  # 30 entries, all <= 500
        assert len(list_activity_events(kanban_dir)) == total

        # before_dt=None: auto-cutoff resolves to last end_work (now-41h).
        # 8 earlier claim/end_work entries (first 4 pairs) are compaction candidates.
        # Floor min(500, 30)==30 must retain all 30; records_compacted must be 0.
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
        """AC-C44a(c): explicit cutoff < latest_entry_dt + open session + small log.

        When ``before_dt`` is explicitly set to a timestamp older than the most recent
        log entry and an unmatched claim exists (open session), the brief's hard floor
        must still protect all entries for small (N ≤ 500) logs.

        This targets the compat-branch condition:
        ``has_session_actions=True, bool(open_session_starts)=True,
        len(all_lines)<=500, before_dt < latest_entry_dt`` → ``floor_count = 0``.
        Without the floor, all 30 entries before the explicit cutoff are wrongly compacted.

        Bug: compat branch fires, setting floor_count=0 → 30 old move entries are
        removed even though the total log (46 entries) is below the 500 floor threshold.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        # 30 old move entries — all before the explicit cutoff (compaction candidates).
        n_old = 30
        for i in range(n_old):
            ts = (now - timedelta(hours=60 - i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=i % 5, action="move"), kanban_dir
            )

        # 1 open claim (no matching end_work) — newer than the cutoff.
        # open_session_starts becomes non-empty, satisfying the compat branch predicate.
        claim_ts = (now - timedelta(hours=20)).isoformat()
        append_activity_event(
            _make_event(ts=claim_ts, task_id=999, action="claim"), kanban_dir
        )

        # 15 newer move entries — newer than both the cutoff and the claim.
        # latest_entry_dt = now-1h; before_dt = now-25h → before_dt < latest_entry_dt.
        n_new = 15
        for i in range(n_new):
            ts = (now - timedelta(hours=15 - i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=i % 5, action="move"), kanban_dir
            )

        total = n_old + 1 + n_new  # 46 entries, all <= 500
        assert len(list_activity_events(kanban_dir)) == total

        # Explicit cutoff at now-25h: all 30 old moves are candidates.
        # Claim (now-20h) and 15 new moves (now-15h to now-1h) are newer than cutoff.
        # Floor min(500, 46)==46 must retain all 46; records_compacted must be 0.
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


# ---------------------------------------------------------------------------
# TestFromAC_ActivityStoreFloorTimestampOrder — AC-C44a-ts
# ---------------------------------------------------------------------------


class TestFromAC_ActivityStoreFloorTimestampOrder:
    """AC-C44a-ts: floor retains entries by parsed timestamp value, not by file position.

    Architecture Review (cycle 2): "Floor retention must select entries by parsed
    timestamp field value, not by file position.  At least one regression test must
    append entries with non-chronological timestamps (a late-appended entry with a
    backdated timestamp) and verify the floor retains the 500 entries with the most
    recent timestamps, not the last 500 appended lines."

    Current implementation: ``parsed[-floor_count:]`` — insertion/append order.
    When a backdated entry is appended after monotonically-timestamped entries, the
    position-based floor keeps it (it occupies the last position) and drops an
    earlier-appended entry that has a more recent timestamp.
    """

    def test_ac_c44a_ts_backdated_entry_excluded_from_floor_non_monotonic(
        self, tmp_path: Path
    ) -> None:
        """AC-C44a-ts: backdated late-appended entry is dropped; more-recent entry retained.

        Setup:
        - 501 entries with monotonically increasing timestamps (T+1h ... T+501h),
          task_ids 1-501, action="move".
        - 1 backdated entry appended last (task_id=9999, timestamp=T-10000h).
        - Total: 502 entries.  Floor = min(500, 502) = 500.  Records to drop: 2.

        Timestamp-based floor (required):
          500 most recent by timestamp = task_ids 2-501 (T+2h ... T+501h).
          Dropped: task_id=1 (T+1h, rank 501) and task_id=9999 (T-10000h, rank 502).

        Position-based floor (current bug):
          Last 500 appended = positions 3-502 = task_ids 3-501 plus task_id=9999.
          Dropped: task_ids 1 and 2.

        Proof assertions — both fail with the current position-based floor:
        1. task_id=9999 NOT in remaining: position-based wrongly retains it at pos 502.
        2. task_id=2 IN remaining: position-based wrongly drops it at pos 2.
        """
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC)

        backdated_task_id = 9999

        # 501 entries with monotonically increasing timestamps.
        # Entry i (1-indexed) has timestamp now + i*hours.
        # task_id=2 → T+2h (500th most recent — retained by timestamp-based floor).
        # task_id=1 → T+1h (501st most recent — dropped by timestamp-based floor).
        for i in range(1, 502):
            ts = (now + timedelta(hours=i)).isoformat()
            append_activity_event(
                _make_event(ts=ts, task_id=i, action="move"), kanban_dir
            )

        # Backdated entry appended last — position 502 (newest by position),
        # but timestamp T-10000h (oldest by timestamp).
        backdated_ts = (now - timedelta(hours=10_000)).isoformat()
        append_activity_event(
            _make_event(ts=backdated_ts, task_id=backdated_task_id, action="move"),
            kanban_dir,
        )

        assert len(list_activity_events(kanban_dir)) == 502

        # Far-future cutoff: all 502 entries become compaction candidates.
        # Floor min(500, 502)=500 must select by timestamp order, not append position.
        cutoff = now + timedelta(hours=100_000)
        result = compact_activity_log(kanban_dir, before_dt=cutoff)

        # Both position-based and timestamp-based approaches drop exactly 2 entries,
        # but drop different ones — this assertion passes in both cases.
        assert result.records_compacted == 2

        remaining = list_activity_events(kanban_dir)
        assert len(remaining) == 500

        remaining_task_ids = {e.task_id for e in remaining}

        # Backdated entry (oldest timestamp) must NOT be in the retained set.
        # Bug: position-based floor retains it because it was appended last (pos 502).
        assert backdated_task_id not in remaining_task_ids, (
            f"task_id={backdated_task_id} (timestamp=T-10000h, position=502) must be "
            "excluded by timestamp-based floor; position-based floor wrongly retains it."
        )

        # task_id=2 (timestamp=T+2h) must BE in the retained set.
        # It is the 500th most recent by timestamp → retained by timestamp-based floor.
        # Bug: position-based floor drops it because position 2 is outside last 500 of 502.
        assert 2 in remaining_task_ids, (
            "task_id=2 (timestamp=T+2h, rank 500 by recency) must be retained; "
            "position-based floor wrongly drops it."
        )
