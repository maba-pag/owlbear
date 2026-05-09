"""RED-phase tests for AgentView.end_work (task #1077).

Tests Brief B paper-integration.md §1.8, §4:
  AC18  — success advances one step; from terminal archives completed/[]; clears claim
  AC19  — reject to archived archives + appends + clears
  AC20  — release clears claim, no status change (D52: note appended when provided)
  AC-NEW-1  — block without block_reason → ERR_BLOCK_REASON_REQUIRED
  AC-NEW-2  — block+block_reason sets blocked+block_reason, clears claim
  AC-NEW-3  — block+block_reason+move_to additionally moves (predicate fires)
  AC-NEW-4  — block guidance suggests AR/DR creation
  AC-NEW-5  — reject skip >1 emits skip-warning
  AC-NEW-6  — invalid outcome → ERR_INVALID_OUTCOME
  AC-NEW-7  — release on unclaimed → pure no-op (updated NOT advanced, note NOT appended)
  AC-NEW-8  — success/reject/block on unclaimed → ERR_NOT_CLAIMED
  AC-NEW-9  — forbidden-parameter matrix (success+move_to, success+archival_reason, etc.)
  AC-NEW-10 — reject without move_to → ERR_REJECT_REQUIRES_MOVE_TO
  AC-NEW-11 — non-block outcome with block_reason → ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK
  AC-NEW-12 — success + predicate fail → ERR_PREDICATE_FAILED; claim NOT cleared (D41)
  AC-NEW-13 — block+move_to + predicate fail → claim NOT cleared, blocked NOT set (D41)
  AC-NEW-17 — reject to archived without archival_reason → ERR_ARCHIVAL_REASON_REQUIRED
  AC-NEW-18 — release with move_to → ERR_MOVE_TO_FORBIDDEN_ON_RELEASE
  AC-NEW-19 — release with archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN
  AC-NEW-20 — block with archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN
  D20/AC30  — note prepended with ISO 8601 datetime (not date-only)
  matrix    — deterministic: leftmost-row/col violation raised first

All 30 tests are expected to FAIL — RED phase.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ValidationError

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
schema: grouped
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
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map:
        research: researcher
        backlog: architect
        todo: test-writer
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# Config with predicate on "review" requiring "## Test Results" section.
_PREDICATE_CONFIG = _BASE_CONFIG.replace(
    "status_predicates: {}",
    (
        "status_predicates:\n"
        "        review:\n"
        "          type: required_sections\n"
        "          sections:\n"
        "            - Test Results"
    ),
)

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

_LIVE_CLAIM_TS = '"2026-04-25T08:00:00+00:00"'  # non-null, within 1 h claim_timeout


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
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
    subdir: str = "tasks",
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
    dest_dir = kanban_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_view(
    base_dir: Path, config_yaml: str = _BASE_CONFIG
) -> tuple[AgentView, Path]:
    kanban_dir = _make_board(base_dir, config_yaml)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_EndWork — all 30 tests, all expected FAIL
# ---------------------------------------------------------------------------


class TestFromAC_EndWork:
    """AgentView.end_work -- 4-outcome lifecycle endpoint (AC18-AC-NEW-20)."""

    # --- Happy path tests (AC18, AC19, AC20, AC-NEW-2, AC-NEW-3, AC-NEW-4) ---

    def test_success_advances_status_with_iso_datetime_in_note(
        self, tmp_path: Path
    ) -> None:
        """AC18 + D20: success advances status; note body contains ISO 8601 datetime
        (not just a date-only [[YYYY-MM-DD]] stamp).

        FAIL reason: engine.end_work prepends `[[YYYY-MM-DD]]` (date-only);
        new spec requires a full ISO 8601 datetime with time component.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(1, outcome="success", note="Ship it.")

        # Status must advance from "in-progress" to "review".
        assert result.status == "review", f"Expected 'review', got {result.status!r}"
        # Note must contain a full ISO 8601 datetime, not a bracketed date.
        assert result.body is not None, "body must be returned"
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.body), (
            "Note must be prepended with ISO 8601 datetime (YYYY-MM-DDTHH:MM:SS); "
            f"body was: {result.body!r}"
        )

    def test_success_from_terminal_archives_with_completed_reason(
        self, tmp_path: Path
    ) -> None:
        """AC18: success from terminal status ('done') archives task with
        archival_reason='completed' and archival_refs=[].

        FAIL reason: engine.end_work moves the file but does NOT set
        archival_reason='completed'.  Result.archival_reason is None.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="done", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(1, outcome="success", note="All done.")

        assert result.archival_reason == "completed", (
            f"Terminal success must archive with archival_reason='completed'; "
            f"got {result.archival_reason!r}"
        )
        assert result.archival_refs == [], (
            f"Terminal success must archive with archival_refs=[]; got {result.archival_refs!r}"
        )
        # File must be in archive/ directory.
        archive_file = kanban_dir / "archive" / "1-task.md"
        assert archive_file.exists(), "Archived task file must reside in archive/"

    def test_reject_to_non_archived_status_updates_status_with_iso_datetime(
        self, tmp_path: Path
    ) -> None:
        """AC19 partial + D20: reject moves status; note contains full ISO 8601 datetime.

        FAIL reason: engine.end_work prepends date-only [[YYYY-MM-DD]]; new spec
        requires ISO 8601 datetime with time component.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="review", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(
            1, outcome="reject", move_to="todo", note="Needs more tests."
        )

        assert result.status == "todo", f"Expected 'todo', got {result.status!r}"
        assert result.body is not None
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.body), (
            "Note must be prepended with ISO 8601 datetime (YYYY-MM-DDTHH:MM:SS); "
            f"body was: {result.body!r}"
        )

    def test_reject_to_archived_moves_file_to_archive_dir(self, tmp_path: Path) -> None:
        """AC19: reject with move_to='archived' and archival_reason moves file to archive/.

        FAIL reason: engine.end_work does not move the file for reject outcome;
        move_to='archived' is also currently rejected by validation as not in
        valid statuses.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="review", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(
            1,
            outcome="reject",
            move_to="archived",
            archival_reason="wontfix",
            note="Not going forward.",
        )

        archive_file = kanban_dir / "archive" / "1-task.md"
        assert archive_file.exists(), "Reject to 'archived' must move file to archive/"
        assert result.archival_reason == "wontfix", (
            f"archival_reason must be stored; got {result.archival_reason!r}"
        )
        assert result.claimed_at is None, "claim must be cleared after reject"

    def test_release_clears_claim_no_status_change(self, tmp_path: Path) -> None:
        """AC20 (updated for D52): release clears claimed_at; status unchanged;
        note appended to body when provided on a claimed task.

        FAIL reason: 'release' is not a valid outcome in engine.end_work;
        raises ValidationError(ERR_INVALID_OUTCOME) instead of succeeding.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            status="in-progress",
            claimed_at=_LIVE_CLAIM_TS,
            body="Work in progress.",
        )

        result = view.end_work(1, outcome="release", note="Releasing claim.")

        assert result.claimed_at is None, "release must clear claimed_at"
        assert result.status == "in-progress", "release must not change status"
        # D52: note must be appended to body when provided on a claimed release.
        assert "Releasing claim." in (result.body or ""), (
            "D52: release with note on claimed task must append note to body"
        )

    def test_release_on_unclaimed_is_pure_noop_not_updated(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-7: release on unclaimed task is a pure no-op.
        updated timestamp must NOT be advanced, note NOT appended.

        FAIL reason: 'release' is not a valid outcome; raises ERR_INVALID_OUTCOME.
        """
        view, kanban_dir = _make_view(tmp_path)
        original_updated = "2026-01-01T10:00:00+00:00"
        _write_task(
            kanban_dir,
            status="in-progress",
            claimed_at="null",
            body="Untouched body.",
        )

        result = view.end_work(1, outcome="release", note="Should be ignored.")

        assert result.claimed_at is None, "unclaimed release: claimed_at stays None"
        assert result.status == "in-progress", "unclaimed release: status unchanged"
        assert result.body == "Untouched body.", (
            "unclaimed release: note must NOT be appended"
        )
        # Re-read task from disk to verify updated was not advanced.
        from owlbear_kanban.storage import read_task  # noqa: PLC0415

        on_disk = read_task(kanban_dir / "tasks" / "1-task.md")
        assert on_disk.updated == original_updated, (
            "unclaimed release must not advance 'updated' timestamp"
        )

    def test_block_with_reason_on_claimed_sets_blocked_clears_claim(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-2: block+block_reason on claimed task sets blocked=True,
        stores block_reason, clears claimed_at; note has ISO 8601 datetime.

        FAIL reason: note prepended with date-only [[YYYY-MM-DD]], not full datetime.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(
            1,
            outcome="block",
            block_reason="Blocked on external API outage.",
            note="Cannot proceed.",
        )

        assert result.blocked is True, "blocked must be True"
        assert result.block_reason == "Blocked on external API outage."
        assert result.claimed_at is None, "claim must be cleared"
        assert result.body is not None
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.body), (
            f"Note must be prepended with ISO 8601 datetime; body was: {result.body!r}"
        )

    def test_block_with_reason_and_move_to_moves_status_and_sets_blocked(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-3: block+block_reason+move_to additionally moves task status.

        FAIL reason: _apply_outcome ignores move_to for 'block' outcome;
        status stays at 'in-progress' instead of advancing to 'todo'.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(
            1,
            outcome="block",
            block_reason="Blocked waiting for decision.",
            move_to="todo",
            note="Moving back while blocked.",
        )

        assert result.blocked is True, "blocked must be True after block outcome"
        assert result.block_reason == "Blocked waiting for decision."
        assert result.status == "todo", (
            f"block+move_to must change status to 'todo'; got {result.status!r}"
        )
        assert result.claimed_at is None, "claim must be cleared"

    def test_block_with_move_to_guidance_contains_ar_hint_and_skip_warning(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-4 + AC-NEW-3: block+move_to returns guidance with both AR/DR hint
        and skip-warning when move_to skips >1 status.

        FAIL reason: block+move_to is not implemented; engine ignores move_to for
        block outcome, so guidance cannot include skip-warning.
        """
        view, kanban_dir = _make_view(tmp_path)
        # Task at review (idx=4); move_to=backlog (idx=1) → skip 3 columns.
        _write_task(kanban_dir, status="review", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(
            1,
            outcome="block",
            block_reason="Major design flaw found.",
            move_to="backlog",
            note="Back to drawing board.",
        )

        assert any(
            "decision" in hint.lower() or "AR" in hint for hint in result.guidance
        ), "guidance must include AR/DR creation hint for block outcome"
        assert any("skip" in hint.lower() for hint in result.guidance), (
            "guidance must include skip-warning when move_to skips >1 status; "
            f"got guidance={result.guidance!r}"
        )

    # --- Error path tests ---

    def test_block_without_reason_raises_err_block_reason_required(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-1: block without block_reason raises ERR_BLOCK_REASON_REQUIRED.

        FAIL reason: AgentView passes block_reason="" to engine.end_work which
        silently sets block_reason="" without raising an error.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="block", note="Something is stuck.")

        assert exc_info.value.code == "ERR_BLOCK_REASON_REQUIRED", (
            f"Expected ERR_BLOCK_REASON_REQUIRED; got {exc_info.value.code!r}"
        )

    def test_reject_without_move_to_raises_err_reject_requires_move_to(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-10: reject without move_to raises ERR_REJECT_REQUIRES_MOVE_TO.

        FAIL reason: AgentView defaults move_to to 'research' when None, so
        engine.end_work proceeds without error.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="review", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="reject", note="Not done yet.")

        assert exc_info.value.code == "ERR_REJECT_REQUIRES_MOVE_TO", (
            f"Expected ERR_REJECT_REQUIRES_MOVE_TO; got {exc_info.value.code!r}"
        )

    def test_fail_outcome_keeps_status_and_releases_claim(self, tmp_path: Path) -> None:
        """AC-NEW-6: 'fail' outcome is accepted by AgentView.end_work.

        It should delegate to engine.end_work, keep the current status, and
        release the claim.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(1, outcome="fail", note="Outcome fail.")

        assert result.task.status == "in-progress"
        assert result.task.claimed_at is None

    def test_success_with_block_reason_raises_err_block_reason_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-11: non-block outcome (success) with block_reason raises
        ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK.

        FAIL reason: AgentView passes block_reason to engine without validation;
        for success outcome, engine silently ignores block_reason.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="success",
                block_reason="Should not be allowed.",
                note="Done.",
            )

        assert exc_info.value.code == "ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK", (
            f"success+block_reason must raise ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK; "
            f"got {exc_info.value.code!r}"
        )

    def test_reject_with_block_reason_raises_err_block_reason_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-11: reject with block_reason raises ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK.

        FAIL reason: AgentView passes block_reason to engine without validation.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="review", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="reject",
                move_to="todo",
                block_reason="Also not allowed.",
                note="Going back.",
            )

        assert exc_info.value.code == "ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK", (
            f"reject+block_reason must raise ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK; "
            f"got {exc_info.value.code!r}"
        )

    def test_release_with_block_reason_raises_err_block_reason_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-11: release with block_reason raises ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK.

        FAIL reason: 'release' is not a valid outcome; currently raises
        ERR_INVALID_OUTCOME instead.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="release",
                block_reason="Not allowed on release either.",
                note="Releasing.",
            )

        assert exc_info.value.code == "ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK", (
            f"release+block_reason must raise ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK; "
            f"got {exc_info.value.code!r}"
        )

    def test_unclaimed_success_raises_err_not_claimed(self, tmp_path: Path) -> None:
        """AC-NEW-8: success on unclaimed task raises ERR_NOT_CLAIMED.

        FAIL reason: AgentView.end_work does not validate whether the task
        is claimed before proceeding.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at="null")

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="success", note="Done.")

        assert exc_info.value.code == "ERR_NOT_CLAIMED", (
            f"success on unclaimed task must raise ERR_NOT_CLAIMED; "
            f"got {exc_info.value.code!r}"
        )

    def test_unclaimed_reject_raises_err_not_claimed(self, tmp_path: Path) -> None:
        """AC-NEW-8: reject on unclaimed task raises ERR_NOT_CLAIMED.

        FAIL reason: AgentView.end_work does not validate claim state.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="review", claimed_at="null")

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="reject", move_to="todo", note="Going back.")

        assert exc_info.value.code == "ERR_NOT_CLAIMED", (
            f"reject on unclaimed task must raise ERR_NOT_CLAIMED; "
            f"got {exc_info.value.code!r}"
        )

    def test_unclaimed_block_raises_err_not_claimed(self, tmp_path: Path) -> None:
        """AC-NEW-8: block on unclaimed task raises ERR_NOT_CLAIMED.

        FAIL reason: AgentView.end_work does not validate claim state.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at="null")

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="block",
                block_reason="Stuck.",
                note="Blocking.",
            )

        assert exc_info.value.code == "ERR_NOT_CLAIMED", (
            f"block on unclaimed task must raise ERR_NOT_CLAIMED; "
            f"got {exc_info.value.code!r}"
        )

    def test_success_with_invalid_move_to_raises_move_to_invalid_status(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-9: success+move_to with invalid status raises ERR_MOVE_TO_INVALID_STATUS.

        move_to on success is allowed for any valid pipeline status (forward or
        backward). An invalid status name is rejected.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="success", move_to="nonexistent", note="Done.")

        assert exc_info.value.code == "ERR_MOVE_TO_INVALID_STATUS", (
            f"success+invalid move_to must raise ERR_MOVE_TO_INVALID_STATUS; "
            f"got {exc_info.value.code!r}"
        )

    def test_success_with_archival_reason_raises_archival_fields_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-9: success+archival_reason raises ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS.

        FAIL reason: AgentView silently ignores archival_reason
        (_ = (archival_reason, archival_refs)) without raising an error.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="success",
                archival_reason="completed",
                note="Done.",
            )

        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS", (
            f"success+archival_reason must raise ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS; "
            f"got {exc_info.value.code!r}"
        )

    def test_block_with_archival_reason_raises_archival_fields_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-20: block+archival_reason raises ERR_ARCHIVAL_FIELDS_FORBIDDEN.

        FAIL reason: AgentView silently ignores archival fields.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="block",
                block_reason="Some block.",
                archival_reason="dropped",
                note="Block note.",
            )

        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN", (
            f"block+archival_reason must raise ERR_ARCHIVAL_FIELDS_FORBIDDEN; "
            f"got {exc_info.value.code!r}"
        )

    def test_block_with_archival_refs_raises_archival_fields_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-20: block+archival_refs raises ERR_ARCHIVAL_FIELDS_FORBIDDEN.

        FAIL reason: AgentView silently ignores archival fields.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="block",
                block_reason="Block reason.",
                archival_refs=[99],
                note="Block with refs.",
            )

        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN", (
            f"block+archival_refs must raise ERR_ARCHIVAL_FIELDS_FORBIDDEN; "
            f"got {exc_info.value.code!r}"
        )

    def test_release_with_move_to_raises_err_move_to_forbidden_on_release(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-18: release+move_to raises ERR_MOVE_TO_FORBIDDEN_ON_RELEASE.

        FAIL reason: 'release' is not a valid outcome; raises ERR_INVALID_OUTCOME
        instead of ERR_MOVE_TO_FORBIDDEN_ON_RELEASE.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="release",
                move_to="todo",
                note="Releasing with invalid move_to.",
            )

        assert exc_info.value.code == "ERR_MOVE_TO_FORBIDDEN_ON_RELEASE", (
            f"release+move_to must raise ERR_MOVE_TO_FORBIDDEN_ON_RELEASE; "
            f"got {exc_info.value.code!r}"
        )

    def test_release_with_archival_reason_raises_archival_fields_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-19: release+archival_reason raises ERR_ARCHIVAL_FIELDS_FORBIDDEN.

        FAIL reason: 'release' is not a valid outcome; raises ERR_INVALID_OUTCOME.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="release",
                archival_reason="wontfix",
                note="Archival on release.",
            )

        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN", (
            f"release+archival_reason must raise ERR_ARCHIVAL_FIELDS_FORBIDDEN; "
            f"got {exc_info.value.code!r}"
        )

    def test_reject_to_archived_without_archival_reason_raises_required(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-17: reject+move_to='archived' without archival_reason raises
        ERR_ARCHIVAL_REASON_REQUIRED.

        FAIL reason: engine raises ValueError (move_to='archived' not in valid
        statuses) → AgentView wraps as ERR_INVALID_OUTCOME, not
        ERR_ARCHIVAL_REASON_REQUIRED.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="review", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                note="Not going forward, no reason given.",
            )

        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED", (
            f"reject-to-archived without archival_reason must raise "
            f"ERR_ARCHIVAL_REASON_REQUIRED; got {exc_info.value.code!r}"
        )

    def test_release_with_move_to_error_is_not_err_invalid_outcome(
        self, tmp_path: Path
    ) -> None:
        """Matrix determinism: release+move_to must raise ERR_MOVE_TO_FORBIDDEN_ON_RELEASE,
        NOT ERR_INVALID_OUTCOME.

        The param-matrix check must fire BEFORE the outcome-validity check so that
        param errors on known outcomes produce their specific codes.

        FAIL reason: 'release' is currently unknown → raises ERR_INVALID_OUTCOME.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="release",
                move_to="backlog",
                note="Matrix test.",
            )

        assert exc_info.value.code != "ERR_INVALID_OUTCOME", (
            "release+move_to must NOT raise ERR_INVALID_OUTCOME; "
            "specific param error must take precedence"
        )
        assert exc_info.value.code == "ERR_MOVE_TO_FORBIDDEN_ON_RELEASE", (
            f"Expected ERR_MOVE_TO_FORBIDDEN_ON_RELEASE; got {exc_info.value.code!r}"
        )

    # --- D41 atomicity tests ---

    def test_product_topology_ignores_config_predicate_success_claim_cleared(self, tmp_path: Path) -> None:
        """With PRODUCT_TOPOLOGY, status_predicates={} — end_work succeeds without predicate check.

        Config predicate on 'review' is ignored; PRODUCT_TOPOLOGY provides empty predicates.
        end_work(success) from 'in-progress' advances to 'review' and clears claimed_at.
        """
        view, kanban_dir = _make_view(tmp_path, config_yaml=_PREDICATE_CONFIG)
        # Task at in-progress (next=review, which config says requires ## Test Results).
        _write_task(
            kanban_dir,
            status="in-progress",
            claimed_at=_LIVE_CLAIM_TS,
            body="No test results here.",
        )

        # No predicate fires — operation succeeds and task advances to 'review'
        result = view.end_work(1, outcome="success", note="Advancing without predicate.")

        assert result.status == "review", (
            f"Task must advance to 'review' (no predicate enforcement); got {result.status!r}"
        )
        from owlbear_kanban.storage import read_task  # noqa: PLC0415

        on_disk = read_task(kanban_dir / "tasks" / "1-task.md")
        assert on_disk.claimed_at is None, (
            "claimed_at must be cleared after successful end_work (no predicate)"
        )

    def test_product_topology_ignores_config_predicate_block_sets_blocked_clears_claim(
        self, tmp_path: Path
    ) -> None:
        """With PRODUCT_TOPOLOGY, status_predicates={} — block+move_to succeeds without predicate check.

        Config predicate on 'review' is ignored; PRODUCT_TOPOLOGY provides empty predicates.
        end_work(block, move_to='review') sets blocked=True and clears claimed_at.
        """
        view, kanban_dir = _make_view(tmp_path, config_yaml=_PREDICATE_CONFIG)
        # review config predicate requires ## Test Results; body doesn't have it.
        _write_task(
            kanban_dir,
            status="in-progress",
            claimed_at=_LIVE_CLAIM_TS,
            body="No test results section.",
        )

        # No predicate fires — operation succeeds
        result = view.end_work(
            1,
            outcome="block",
            block_reason="Design issue.",
            move_to="review",
            note="Moving and blocking.",
        )

        assert result.blocked is True, (
            "blocked must be set to True after end_work(block) (no predicate enforcement)"
        )
        from owlbear_kanban.storage import read_task  # noqa: PLC0415

        on_disk = read_task(kanban_dir / "tasks" / "1-task.md")
        assert on_disk.blocked is True, (
            "blocked must be set on disk after end_work(block)"
        )
        assert on_disk.claimed_at is None, (
            "claimed_at must be cleared after end_work(block)"
        )

    # --- Boundary tests ---

    def test_block_with_move_to_fires_predicate_on_destination(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-3 + predicate: block+block_reason+move_to fires destination predicate.
        When body satisfies predicate, move succeeds; both blocked=True and new status set.

        FAIL reason: engine ignores move_to for block outcome; status stays unchanged.
        """
        view, kanban_dir = _make_view(tmp_path, config_yaml=_PREDICATE_CONFIG)
        # Body satisfies 'review' predicate.
        _write_task(
            kanban_dir,
            status="in-progress",
            claimed_at=_LIVE_CLAIM_TS,
            body="## Test Results\nAll tests pass.",
        )

        result = view.end_work(
            1,
            outcome="block",
            block_reason="External dependency.",
            move_to="review",
            note="Moving to review while blocked.",
        )

        assert result.blocked is True, "blocked must be True"
        assert result.status == "review", (
            f"block+move_to='review' (predicate satisfied) must change status; "
            f"got {result.status!r}"
        )
        assert result.claimed_at is None, "claim must be cleared after successful block"

    def test_reject_backwards_skip_multiple_statuses_emits_skip_warning(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-5: reject skipping >1 status backwards emits skip-warning.

        FAIL reason: _skip_transition_guidance computes delta = to_idx - from_idx;
        for backwards jumps delta is negative and ≤ 1, so no warning is emitted.
        The new implementation must handle backwards skips.
        """
        view, kanban_dir = _make_view(tmp_path)
        # Task at 'done' (idx=5); reject to 'research' (idx=0) skips 5 columns.
        _write_task(kanban_dir, status="done", claimed_at=_LIVE_CLAIM_TS)

        result = view.end_work(
            1,
            outcome="reject",
            move_to="research",
            note="Sending all the way back.",
        )

        assert result.status == "research", (
            f"reject must change status to 'research'; got {result.status!r}"
        )
        assert any("skip" in hint.lower() for hint in result.guidance), (
            "reject skipping >1 status backwards must emit skip-warning; "
            f"got guidance={result.guidance!r}"
        )

    # --- Retry additions: AC-NEW-1 empty/whitespace block_reason (reviewer gap) ---

    def test_block_with_empty_string_reason_raises_err_block_reason_required(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-1 (retry): block with block_reason='' raises ERR_BLOCK_REASON_REQUIRED.

        An empty string is not a valid block reason.  AgentView.end_work only
        guards ``block_reason is None``; an empty string passes that check and is
        silently normalised to '' via ``block_reason or ""``.

        FAIL reason: no ValidationError is raised for block_reason=''.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="block", block_reason="", note="Stuck.")

        assert exc_info.value.code == "ERR_BLOCK_REASON_REQUIRED", (
            "block_reason='' must raise ERR_BLOCK_REASON_REQUIRED; "
            f"got {exc_info.value.code!r}"
        )

    def test_block_with_whitespace_only_reason_raises_err_block_reason_required(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-1 (retry): block with block_reason='   ' raises ERR_BLOCK_REASON_REQUIRED.

        Whitespace-only is not a valid block reason.  '   ' is not None (passes
        the None guard) and is truthy (not caught by ``block_reason or ''``), so
        it is stored as-is without raising any error.

        FAIL reason: no ValidationError is raised for whitespace-only block_reason.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(1, outcome="block", block_reason="   ", note="Stuck.")

        assert exc_info.value.code == "ERR_BLOCK_REASON_REQUIRED", (
            "block_reason='   ' (whitespace-only) must raise ERR_BLOCK_REASON_REQUIRED; "
            f"got {exc_info.value.code!r}"
        )

    # --- Retry addition: AC-NEW-9 matrix proof (reject + non-archived + archival fields) ---

    def test_reject_to_non_archived_with_archival_reason_raises_archival_fields_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-9 matrix proof: reject+move_to=non-archived+archival_reason raises
        ERR_ARCHIVAL_FIELDS_FORBIDDEN.

        This exercises the reject-branch archival-guard (``elif archival_reason is
        not None or archival_refs is not None``), which was not covered by any
        task-scoped test.  The branch exists in the production code; this test
        establishes the authoritative contract assertion.

        FAIL reason (if branch is missing/removed): no error raised, archival_reason
        silently accepted for a non-archival move.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="review", claimed_at=_LIVE_CLAIM_TS)

        with pytest.raises(ValidationError) as exc_info:
            view.end_work(
                1,
                outcome="reject",
                move_to="backlog",
                archival_reason="deprecated",
                note="Back to backlog.",
            )

        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN", (
            "reject+move_to='backlog'+archival_reason must raise "
            "ERR_ARCHIVAL_FIELDS_FORBIDDEN; "
            f"got {exc_info.value.code!r}"
        )
