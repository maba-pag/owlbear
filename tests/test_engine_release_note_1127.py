"""RED-phase tests for AgentView.end_work release-outcome note appending (task #1127).

Tests:
  AC1 — AgentView.end_work(outcome="release", note=...) on a claimed task appends the
         timestamped note to the task body before releasing the claim
  AC2 — AgentView.end_work(outcome="release", note=...) on an unclaimed task is a
         pure no-op (regression guard — verifies existing correct behavior is preserved)
  AC3 — The note uses the same timestamped format as other outcomes:
         now.replace(microsecond=0).isoformat() + newline + note text
  AC4 — Activity event for release remains action="release", detail="released by agent"
         (regression guard — verifies no change to session classification)

All AC1 and AC3 tests are expected to FAIL (RED phase — note not yet appended).
AC2 and AC4 are regression guards for behavior that already works correctly; they
may pass immediately and are documented as such per w-tdd-red "X unchanged" exception.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.storage import read_task

# ---------------------------------------------------------------------------
# Board helpers (mirrored from test_engine_end_work_fail_1125.py convention)
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: {tags}
parent: {parent}
depends_on: {depends_on}
blocked: {blocked}
block_reason: {block_reason}
claimed_at: {claimed_at}
archival_reason: {archival_reason}
archival_refs: {archival_refs}
---
{body}
"""

_LIVE_CLAIM_TS = '"2026-04-26T08:00:00+00:00"'  # within 1h claim_timeout
_INITIAL_UPDATED = "2026-01-01T10:00:00+00:00"


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "in-progress",
    priority: str = "needed",
    tags: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    depends_on: str = "[]",
    body: str = "Initial body.",
    parent: str = "null",
    archival_reason: str = "null",
    archival_refs: str = "[]",
    claimed_at: str = "null",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        tags=tags,
        blocked=blocked,
        block_reason=block_reason,
        depends_on=depends_on,
        body=body,
        parent=parent,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
        claimed_at=claimed_at,
    )
    dest = kanban_dir / "tasks" / f"{task_id}-task.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest


def _make_view(base_dir: Path) -> tuple[AgentView, Path]:
    kanban_dir = _make_board(base_dir)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), kanban_dir


def _make_view_with_log(base_dir: Path) -> tuple[AgentView, Path]:
    """Create an AgentView backed by an engine with activity logging enabled."""
    kanban_dir = _make_board(base_dir)
    engine = KanbanEngine(kanban_dir, activity_log=True)
    return AgentView(engine), kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_ReleaseNoteAppending — AC1: claimed release appends note
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseNoteAppending:
    """AgentView.end_work(outcome='release', note=...) on a claimed task — AC1, AC3."""

    # --- AC1: note present in returned body ----------------------------------

    def test_release_claimed_note_in_returned_body(self, tmp_path: Path) -> None:
        """AC1: returned task body contains the note text after claimed release.

        FAIL reason: AgentView.end_work(outcome='release') delegates to
        engine.release_task() which does NOT append notes. The returned body will
        not contain the note text.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        note_text = "Releasing to allow another agent to claim."
        result = view.end_work(1, outcome="release", note=note_text)

        assert note_text in result.task.body, (
            f"Expected note to appear in returned body after release; body={result.task.body!r}"
        )

    def test_release_claimed_note_in_disk_body(self, tmp_path: Path) -> None:
        """AC1: on-disk task body contains the note text after claimed release.

        FAIL reason: engine.release_task() does not call write_task with note appended;
        the disk file will not contain the note.
        """
        view, kanban_dir = _make_view(tmp_path)
        task_path = _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        note_text = "Disk body note verification."
        view.end_work(1, outcome="release", note=note_text)

        disk_record = read_task(task_path)
        disk_body = disk_record.body if isinstance(disk_record.body, str) else str(disk_record.body)
        assert note_text in disk_body, (
            f"Expected note in on-disk body after release; disk_body={disk_body!r}"
        )

    def test_release_claimed_compound_note_and_claim_cleared(self, tmp_path: Path) -> None:
        """AC1: note is appended AND claim is cleared AND status is unchanged (compound guard).

        FAIL reason: engine.release_task() does not append the note, so the note
        assertion fails before the claim/status checks are reached.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        note_text = "Compound: note + claim cleared + status unchanged."
        result = view.end_work(1, outcome="release", note=note_text)

        assert note_text in result.task.body, (
            f"Note must be in returned body; body={result.task.body!r}"
        )
        assert result.task.claimed_at is None, (
            f"Claim must be cleared; claimed_at={result.task.claimed_at!r}"
        )
        assert result.task.status == "in-progress", (
            f"Status must be unchanged; status={result.task.status!r}"
        )

    # --- AC3: note format ----------------------------------------------------

    def test_release_claimed_note_has_iso_timestamp_prefix(self, tmp_path: Path) -> None:
        """AC3: appended note includes an ISO 8601 datetime prefix (no microseconds).

        FAIL reason: no note is appended at all on release; the timestamp prefix
        will not be found in the body.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        note_text = "Note with timestamp check."
        result = view.end_work(1, outcome="release", note=note_text)

        # ISO 8601 pattern with time component (YYYY-MM-DDTHH:MM:SS±HH:MM)
        # microseconds must NOT appear (now.replace(microsecond=0).isoformat())
        body = result.task.body
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", body), (
            f"Expected ISO 8601 datetime prefix (no microseconds) in body; body={body!r}"
        )

    def test_release_claimed_note_no_microseconds_in_timestamp(self, tmp_path: Path) -> None:
        """AC3: timestamp uses now.replace(microsecond=0) — no fractional seconds.

        FAIL reason: no note is appended; the timestamp format cannot be verified.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(1, outcome="release", note="Microsecond-free check.")

        body = result.task.body
        # Fractional seconds would look like 2026-04-26T10:00:00.123456+00:00
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", body), (
            f"Timestamp must not contain fractional seconds; body={body!r}"
        )
        # But the timestamp itself must exist
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", body), (
            f"Expected ISO 8601 datetime in body; body={body!r}"
        )

    def test_release_claimed_note_text_follows_timestamp(self, tmp_path: Path) -> None:
        """AC3: note text appears on a new line immediately after the timestamp.

        FAIL reason: no note is appended; neither timestamp nor note text will be
        found in the body.

        The expected format is:
            <existing body>
            <timestamp>
            <note text>
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", body="Original.", claimed_at=_LIVE_CLAIM_TS)

        note_text = "Release note content."
        result = view.end_work(1, outcome="release", note=note_text)

        body = result.task.body
        # Timestamp and note must both appear, with note after timestamp
        ts_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\n]*)", body)
        assert ts_match is not None, f"No timestamp found in body={body!r}"
        ts_end = ts_match.end()
        rest = body[ts_end:]
        assert note_text in rest, (
            f"Note text must follow timestamp; rest after timestamp={rest!r}"
        )

    def test_release_claimed_note_format_matches_other_outcomes(self, tmp_path: Path) -> None:
        """AC3: release note format matches the format used by success/block outcomes.

        FAIL reason: no note is appended on release so format cannot be compared.

        Both release and other outcomes must produce: <body>\n<timestamp>\n<note>.
        """
        view_success, kanban_dir_s = _make_view(tmp_path / "success")
        _write_task(kanban_dir_s, task_id=1, status="todo", claimed_at=_LIVE_CLAIM_TS)

        view_release, kanban_dir_r = _make_view(tmp_path / "release")
        _write_task(kanban_dir_r, task_id=1, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        note_text = "Shared note content."

        success_result = view_success.end_work(1, outcome="success", note=note_text)
        release_result = view_release.end_work(1, outcome="release", note=note_text)

        # Both bodies must end with <newline><timestamp><newline><note_text>
        success_body = success_result.task.body
        release_body = release_result.task.body

        # Strip prefix differences (success may advance status, release keeps it)
        # Focus: both should contain the same timestamp+note pattern
        success_ts = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", success_body)
        release_ts = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", release_body)

        assert success_ts is not None, f"No timestamp in success body={success_body!r}"
        assert release_ts is not None, (
            f"No timestamp in release body — note not appended; body={release_body!r}"
        )
        # Both timestamps must contain note text immediately after
        assert note_text in release_body[release_ts.start():], (
            f"Note text must appear after timestamp in release body; body={release_body!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ReleaseUnclaimedNoop — AC2: unclaimed release is pure no-op
# (Regression guard — verifies existing correct no-op behavior is preserved)
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseUnclaimedNoop:
    """Unclaimed release with note must remain a pure no-op — AC2 regression guard.

    These tests verify that the builder's implementation does NOT accidentally
    apply the note to unclaimed-task release paths. They may pass immediately
    on current code (behavior already correct) and are included as pre-emptive
    regression guards per w-tdd-red "X unchanged" exception.
    """

    def test_unclaimed_release_body_not_modified_in_memory(self, tmp_path: Path) -> None:
        """AC2: returned body is unchanged when release is called on an unclaimed task.

        The note parameter must be ignored for unclaimed tasks.
        """
        view, kanban_dir = _make_view(tmp_path)
        initial_body = "Original task body."
        _write_task(kanban_dir, status="in-progress", body=initial_body, claimed_at="null")

        note_text = "This note must NOT appear."
        result = view.end_work(1, outcome="release", note=note_text)

        assert note_text not in result.task.body, (
            f"Note must not be appended to unclaimed task body; body={result.task.body!r}"
        )

    def test_unclaimed_release_disk_body_unchanged(self, tmp_path: Path) -> None:
        """AC2: on-disk body is not modified when release is called on unclaimed task.

        No write must occur for unclaimed tasks — disk state must remain identical.
        """
        view, kanban_dir = _make_view(tmp_path)
        initial_body = "Disk body unchanged verification."
        task_path = _write_task(
            kanban_dir, status="in-progress", body=initial_body, claimed_at="null"
        )

        note_text = "Disk note must not appear."
        view.end_work(1, outcome="release", note=note_text)

        disk_record = read_task(task_path)
        disk_body = disk_record.body if isinstance(disk_record.body, str) else str(disk_record.body)
        assert note_text not in disk_body, (
            f"Note must not appear in on-disk body for unclaimed release; disk_body={disk_body!r}"
        )

    def test_unclaimed_release_updated_timestamp_not_advanced(self, tmp_path: Path) -> None:
        """AC2: the 'updated' timestamp is not advanced for unclaimed task release.

        No state mutation must occur — the updated field must remain unchanged.
        """
        view, kanban_dir = _make_view(tmp_path)
        task_path = _write_task(
            kanban_dir, status="in-progress", claimed_at="null"
        )

        before_mtime = task_path.stat().st_mtime
        view.end_work(1, outcome="release", note="Should not advance timestamp.")
        after_mtime = task_path.stat().st_mtime

        assert after_mtime == pytest.approx(before_mtime, abs=0.01), (
            "File mtime must not change for unclaimed release (no disk write allowed)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ReleaseActivityEvent — AC4: activity event unchanged
# (Regression guard — verifies existing correct activity event is preserved)
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseActivityEvent:
    """Activity event for release must remain action='release', detail='released by agent' — AC4.

    These tests verify that the builder's implementation does NOT change the
    activity event emitted for claimed-task releases. They may pass immediately
    on current code (event already correct) and are included as pre-emptive
    regression guards per w-tdd-red "X unchanged" exception.
    """

    def test_release_claimed_emits_release_action(self, tmp_path: Path) -> None:
        """AC4: claimed release with note emits action='release' in activity log.

        The activity action must be 'release', not 'end_work' or any other value.
        """
        view, kanban_dir = _make_view_with_log(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        view.end_work(1, outcome="release", note="Activity event check.")

        log_path = kanban_dir / "activity.jsonl"
        assert log_path.exists(), "Activity log must exist after release"
        entries = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        actions = [e["action"] for e in entries]
        assert "release" in actions, (
            f"Expected 'release' action in activity log; found actions={actions!r}"
        )

    def test_release_claimed_emits_released_by_agent_detail(self, tmp_path: Path) -> None:
        """AC4: claimed release with note emits detail='released by agent' in activity log.

        The detail must not be changed to include note content or other metadata.
        """
        view, kanban_dir = _make_view_with_log(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        view.end_work(1, outcome="release", note="Detail check note.")

        log_path = kanban_dir / "activity.jsonl"
        entries = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        release_entries = [e for e in entries if e.get("action") == "release"]
        assert release_entries, "Expected at least one 'release' entry in activity log"
        details = [e.get("detail", "") for e in release_entries]
        assert any("released by agent" in d for d in details), (
            f"Expected detail containing 'released by agent'; got details={details!r}"
        )

    def test_release_claimed_no_end_work_event(self, tmp_path: Path) -> None:
        """AC4: claimed release with note must NOT emit an 'end_work' action.

        The release path must not be rerouted through the end_work engine method,
        which would emit a different activity event and break session classification.
        """
        view, kanban_dir = _make_view_with_log(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        view.end_work(1, outcome="release", note="No end_work event check.")

        log_path = kanban_dir / "activity.jsonl"
        entries = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        actions = [e["action"] for e in entries]
        assert "end_work" not in actions, (
            f"'end_work' action must not appear in log for release outcome; actions={actions!r}"
        )
