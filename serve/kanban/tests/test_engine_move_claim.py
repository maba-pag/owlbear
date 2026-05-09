"""RED-phase tests for AgentView.move_task and AgentView.start_work (task #1073).

Covers Brief B paper-integration.md §1.6, §1.7, §3.1, §3.2, §3.4, §4:
  - move_task: archival validation matrix (§3.1, §3.2), predicate-on-destination
    (D15/D41), archive clears claim atomically (D17), archival fields forbidden
    on active tasks (ERR_ARCHIVAL_FIELDS_FORBIDDEN)
  - start_work: blocked-not-claimable (ERR_BLOCKED_NOT_CLAIMABLE),
    archived-not-claimable (ERR_ARCHIVED_NOT_CLAIMABLE)

AC coverage:
  AC4   → TestFromAC_MoveTask.test_archive_without_reason_raises_archival_reason_required
  AC5   → TestFromAC_MoveTask.test_archive_completed_from_non_terminal_raises_completed_requires_done
  AC7   → TestFromAC_MoveTask.test_archive_deprecated_without_refs_raises_archival_refs_required
  AC8   → TestFromAC_MoveTask.test_archive_dropped_with_refs_raises_archival_refs_forbidden
  AC9   → TestFromAC_MoveTask.test_archive_invalid_reason_raises_archival_reason_invalid
  AC26  → TestFromAC_MoveTask.test_archive_with_missing_ref_raises_archival_ref_missing
  ERR_ARCHIVAL_FIELDS_FORBIDDEN
        → TestFromAC_MoveTask.test_archival_reason_on_active_status_raises_fields_forbidden
  D15   → TestFromAC_MoveTask.test_predicate_on_destination_fails_raises_predicate_failed
  D41   → TestFromAC_MoveTask.test_predicate_on_destination_fails_task_not_moved
  D17   → TestFromAC_MoveTask.test_archive_claimed_task_clears_claim
  ERR_BLOCKED_NOT_CLAIMABLE
        → TestFromAC_StartWork.test_blocked_task_raises_blocked_not_claimable
  ERR_ARCHIVED_NOT_CLAIMABLE
        → TestFromAC_StartWork.test_archived_task_raises_archived_not_claimable

NOT TESTABLE AS RED (already implemented, no failing test possible):
  AC-NEW-5  → skip warning: _skip_transition_guidance already fires for delta > 1
  AC-NEW-16 → missing id → ERR_NOT_FOUND: FileNotFoundError already converted by both
              move_task and start_work
  Invalid status enum → ERR_INVALID_STATUS: engine ValueError already re-wrapped in
              AgentView.move_task
  ERR_ALREADY_CLAIMED → "already claimed" substr check already fires for active claims
              in AgentView.start_work
  D18+D36   → expired claim re-claim: engine.claim_task already handles expiry
              transparently; AgentView.start_work inherits it
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ConcurrencyError, NotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Board + task fixtures (mirrors conventions from test_engine_create_edit_1070.py)
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
  todo: builder
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

# Board with a required-sections predicate on the "review" status.
# Used for D15/D41 predicate-on-destination tests.
_PREDICATE_CONFIG = _BASE_CONFIG.replace(
    "status_predicates: {}",
    (
        "status_predicates:\n"
        "  review:\n"
        "    type: required_sections\n"
        "    sections:\n"
        "      - Test Results"
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
    status: str = "todo",
    priority: str = "needed",
    tags: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    depends_on: str = "[]",
    body: str = "Body.",
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
# TestFromAC_MoveTask
#
# Tests for AgentView.move_task:
#   - archival validation matrix (AC4, AC5, AC7, AC8, AC9, AC26)
#   - archival fields forbidden on active-status targets (ERR_ARCHIVAL_FIELDS_FORBIDDEN)
#   - predicate-on-destination gate (D15, D41)
#   - archive clears claim atomically (D17)
#
# All tests are RED — the current AgentView.move_task stubs out archival fields
# with `_ = (archival_reason, archival_refs)` and performs no predicate check
# on the destination status.
# ---------------------------------------------------------------------------


class TestFromAC_MoveTask:
    """Archival validation, predicate-on-destination, and claim-clearing for move_task."""

    def test_archive_without_reason_raises_archival_reason_required(
        self, tmp_path: Path
    ) -> None:
        """AC4: move_task(id, "archived") with no archival_reason → ERR_ARCHIVAL_REASON_REQUIRED.

        Every archive operation must carry an archival_reason. Current impl
        ignores archival_reason entirely and archives the task unconditionally.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "archived")
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    def test_archive_completed_from_non_terminal_raises_completed_requires_done(
        self, tmp_path: Path
    ) -> None:
        """AC5: move_task(id, "archived", archival_reason="completed") from a
        non-terminal status → ERR_COMPLETED_REQUIRES_DONE.

        archival_reason="completed" signals work finished — only valid at the
        terminal status ("done"). From "todo" it must be rejected. Current impl
        ignores archival_reason and archives unconditionally.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "archived", archival_reason="completed")
        assert exc_info.value.code == "ERR_COMPLETED_REQUIRES_DONE"

    def test_archive_deprecated_without_refs_raises_archival_refs_required(
        self, tmp_path: Path
    ) -> None:
        """AC7: move_task(id, "archived", archival_reason="deprecated") with no
        archival_refs → ERR_ARCHIVAL_REFS_REQUIRED.

        "deprecated" and "duplicate" require at least one archival_ref pointing
        to the successor or replacement task. Current impl ignores all archival
        parameters.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "archived", archival_reason="deprecated")
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    def test_archive_dropped_with_refs_raises_archival_refs_forbidden(
        self, tmp_path: Path
    ) -> None:
        """AC8: move_task(id, "archived", archival_reason="dropped", archival_refs=[ref])
        → ERR_ARCHIVAL_REFS_FORBIDDEN.

        "dropped", "completed", and "wontfix" must NOT be accompanied by
        archival_refs. Current impl ignores all archival parameters.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="todo")
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "archived", archival_reason="dropped", archival_refs=[2])
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_archive_invalid_reason_raises_archival_reason_invalid(
        self, tmp_path: Path
    ) -> None:
        """AC9: move_task with archival_reason not in config.archival_reasons enum
        → ERR_ARCHIVAL_REASON_INVALID.

        Only the configured set {completed, deprecated, dropped, duplicate,
        wontfix} are valid. Current impl ignores archival_reason entirely, so
        the invalid value passes through undetected.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "archived", archival_reason="invalid-reason-xyz")
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_INVALID"

    def test_archive_with_missing_ref_raises_archival_ref_missing(
        self, tmp_path: Path
    ) -> None:
        """AC26: move_task(..., archival_refs=[99999]) where 99999 does not exist
        → ERR_ARCHIVAL_REF_MISSING.

        Every ID in archival_refs must refer to an existing task (active or
        archived). "deprecated" requires refs, so ref [99999] satisfies
        ERR_ARCHIVAL_REFS_REQUIRED — but the non-existent ID fires
        ERR_ARCHIVAL_REF_MISSING. Current impl ignores archival_refs entirely.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1, "archived", archival_reason="deprecated", archival_refs=[99999]
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_MISSING"

    def test_archival_reason_on_active_status_raises_fields_forbidden(
        self, tmp_path: Path
    ) -> None:
        """ERR_ARCHIVAL_FIELDS_FORBIDDEN: move_task(id, active_status, archival_reason=...)
        → ERR_ARCHIVAL_FIELDS_FORBIDDEN.

        archival_reason is only meaningful when the target status is "archived".
        Passing it with a live status such as "done" must be rejected. Current
        impl ignores archival_reason regardless of the target status.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="in-progress")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "done", archival_reason="completed")
        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN"

    def test_predicate_on_destination_fails_raises_predicate_failed(
        self, tmp_path: Path
    ) -> None:
        """With PRODUCT_TOPOLOGY, status_predicates={} — move_task to 'review' succeeds.

        Config predicate on 'review' is ignored; PRODUCT_TOPOLOGY provides empty predicates.
        move_task(1, 'review') succeeds and task is moved to 'review'.
        """
        view, kanban_dir = _make_view(tmp_path, _PREDICATE_CONFIG)
        _write_task(
            kanban_dir, task_id=1, status="in-progress", body="No test results here."
        )
        result = view.move_task(1, "review")  # must NOT raise
        assert result.status == "review", (
            f"move_task must succeed (no predicate enforcement); got {result.status!r}"
        )

    def test_predicate_on_destination_fails_task_not_moved(
        self, tmp_path: Path
    ) -> None:
        """With PRODUCT_TOPOLOGY, status_predicates={} — task IS moved to 'review'.

        Config predicate on 'review' is ignored; PRODUCT_TOPOLOGY provides empty predicates.
        After move_task(1, 'review'), show_task reports task at 'review'.
        """
        view, kanban_dir = _make_view(tmp_path, _PREDICATE_CONFIG)
        _write_task(
            kanban_dir, task_id=1, status="in-progress", body="No test results here."
        )
        view.move_task(1, "review")  # succeeds (no predicate)
        result = view.show_task(1)
        assert result.status == "review", (
            f"Task must be at 'review' after successful move (no predicate enforcement); got {result.status!r}"
        )

    def test_archive_claimed_task_clears_claim(self, tmp_path: Path) -> None:
        """D17: archiving a currently-claimed task clears claimed_at atomically.

        The returned SingleTaskResponse must have claimed_at=None after a
        successful archive. Current engine.move_task does not clear claimed_at
        when archiving, so the claim field leaks into the archive file.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="todo",
            claimed_at='"2026-04-25T10:00:00+00:00"',
        )
        result = view.move_task(1, "archived", archival_reason="dropped")
        assert result.claimed_at is None

    def test_archive_cleared_claim_persisted_in_archive_file(
        self, tmp_path: Path
    ) -> None:
        """D17 (persistence proof): archiving a claimed task writes claimed_at=null to disk.

        The SingleTaskResponse.claimed_at=None only proves the in-memory record is correct;
        this test re-reads the task from disk via a fresh KanbanEngine to prove the persisted
        archive file also has claimed_at cleared (D17 atomicity — full persistence proof).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="todo",
            claimed_at='"2026-04-25T10:00:00+00:00"',
        )
        view.move_task(1, "archived", archival_reason="dropped")
        # File must exist in archive/ and NOT remain in tasks/.
        assert any((kanban_dir / "archive").glob("1-*.md")), (
            "task file must exist in archive/ after archive"
        )
        assert not any((kanban_dir / "tasks").glob("1-*.md")), (
            "task file must not remain in tasks/ after archive"
        )
        # Fresh engine: bypasses any in-memory cache from the view's engine.
        fresh_engine = KanbanEngine(kanban_dir, activity_log=False)
        on_disk = fresh_engine.show_task("1")
        assert on_disk.claimed_at is None

    def test_move_skipping_two_columns_emits_skip_guidance(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-5: move_task that skips >1 status position returns non-empty guidance.

        Moving from 'research' (index 0) to 'in-progress' (index 3) skips 'backlog'
        and 'todo' (delta=3, skipped=2). The returned SingleTaskResponse.guidance must
        contain a skip-warning string.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="research")
        result = view.move_task(1, "in-progress")
        assert result.guidance, "expected non-empty guidance for a 2-column skip"
        assert any("skip" in g.lower() for g in result.guidance)

    def test_move_missing_task_raises_not_found(self, tmp_path: Path) -> None:
        """AC-NEW-16 (move_task): move_task on a non-existent id → NotFoundError(ERR_NOT_FOUND).

        engine.show_task raises FileNotFoundError for an unknown id; AgentView.move_task
        must wrap it as NotFoundError(ERR_NOT_FOUND).
        """
        view, _kanban_dir = _make_view(tmp_path)
        with pytest.raises(NotFoundError) as exc_info:
            view.move_task(99999, "todo")
        assert exc_info.value.code == "ERR_NOT_FOUND"

    def test_move_invalid_status_raises_invalid_status(self, tmp_path: Path) -> None:
        """Invalid status enum → ValidationError(ERR_INVALID_STATUS) from move_task.

        engine.move_task raises ValueError for an unrecognised status string;
        AgentView.move_task must translate that ValueError to
        ValidationError(ERR_INVALID_STATUS). D49 — no ERR_TRANSITION_FORBIDDEN code.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "not-a-valid-status-xyz")
        assert exc_info.value.code == "ERR_INVALID_STATUS"

    def test_archive_move_failure_restores_original_task_record(
        self, tmp_path: Path
    ) -> None:
        """D17 (rollback proof): _move_file OSError during archive restores the original task record.

        If _move_file raises OSError after write_task has written the archived record
        to tasks/, the rollback branch (engine.py) must write the original record back
        to tasks/ and re-raise. After the failure the task must remain in tasks/ (not
        archive/) with its pre-archive status and claimed_at intact — proving the
        partial write is unwound and the board is left in a consistent state.
        """
        original_claimed_at = "2026-04-25T10:00:00+00:00"
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="todo",
            claimed_at=f'"{original_claimed_at}"',
        )
        with (
            patch("owlbear_kanban.engine._move_file", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            view.move_task(1, "archived", archival_reason="dropped")
        # Rollback must have restored the file to tasks/, not left it in archive/.
        assert any((kanban_dir / "tasks").glob("1-*.md")), (
            "original task file must be restored in tasks/ after _move_file OSError"
        )
        assert not any((kanban_dir / "archive").glob("1-*.md")), (
            "no task file must exist in archive/ when the file move failed"
        )
        # Fresh engine proves the persisted record matches the pre-archive state.
        fresh_engine = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh_engine.show_task("1")
        assert restored.status == "todo", (
            "status must be restored to pre-archive value after rollback"
        )
        assert restored.claimed_at is not None, (
            "claimed_at must not be cleared on a failed archive"
        )


# ---------------------------------------------------------------------------
# TestFromAC_StartWork
#
# Tests for AgentView.start_work:
#   - blocked task → ERR_BLOCKED_NOT_CLAIMABLE
#   - archived task → ERR_ARCHIVED_NOT_CLAIMABLE
#
# All tests are RED:
#   - blocked: engine raises ValueError("...is blocked..."), AgentView re-raises
#     as ValidationError(ERR_INVALID_STATUS) — wrong code, should be
#     ERR_BLOCKED_NOT_CLAIMABLE
#   - archived: engine raises FileNotFoundError (task not in tasks_dir), AgentView
#     re-raises as NotFoundError(ERR_NOT_FOUND) — wrong type and code, should be
#     ValidationError(ERR_ARCHIVED_NOT_CLAIMABLE)
# ---------------------------------------------------------------------------


class TestFromAC_StartWork:
    """Claim-guard semantics for start_work on blocked and archived tasks."""

    def test_blocked_task_raises_blocked_not_claimable(self, tmp_path: Path) -> None:
        """start_work on a blocked task → ValidationError(ERR_BLOCKED_NOT_CLAIMABLE).

        The engine raises ValueError("Task '1' is blocked and cannot be claimed").
        AgentView.start_work currently catches this as a generic ValueError and
        re-raises it as ValidationError(ERR_INVALID_STATUS) — wrong code.
        The correct code is ERR_BLOCKED_NOT_CLAIMABLE.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="todo",
            blocked="true",
            block_reason='"Dependency pending"',
        )
        with pytest.raises(ValidationError) as exc_info:
            view.start_work(1)
        assert exc_info.value.code == "ERR_BLOCKED_NOT_CLAIMABLE"

    def test_archived_task_raises_archived_not_claimable(self, tmp_path: Path) -> None:
        """start_work on an archived task → ValidationError(ERR_ARCHIVED_NOT_CLAIMABLE).

        Archived tasks live in archive/, not tasks/. engine.claim_task raises
        FileNotFoundError (task not found in tasks_dir). AgentView.start_work
        currently converts FileNotFoundError to NotFoundError(ERR_NOT_FOUND) —
        wrong exception type and wrong code.
        The correct error is ValidationError(ERR_ARCHIVED_NOT_CLAIMABLE).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason='"dropped"',
            subdir="archive",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.start_work(1)
        assert exc_info.value.code == "ERR_ARCHIVED_NOT_CLAIMABLE"

    def test_start_work_missing_task_raises_not_found(self, tmp_path: Path) -> None:
        """AC-NEW-16 (start_work): start_work on a non-existent id → NotFoundError(ERR_NOT_FOUND).

        engine.show_task raises FileNotFoundError for an unknown id; AgentView.start_work
        must wrap it as NotFoundError(ERR_NOT_FOUND).
        """
        view, _kanban_dir = _make_view(tmp_path)
        with pytest.raises(NotFoundError) as exc_info:
            view.start_work(99999)
        assert exc_info.value.code == "ERR_NOT_FOUND"

    def test_start_work_already_claimed_raises_already_claimed(
        self, tmp_path: Path
    ) -> None:
        """start_work on an already-claimed (non-expired) task → ConcurrencyError(ERR_ALREADY_CLAIMED).

        engine.claim_task raises ValueError('already claimed') when the existing claim
        has not expired. AgentView.start_work must translate that to
        ConcurrencyError(ERR_ALREADY_CLAIMED). claimed_at is far in the future to ensure
        the timeout guard treats the claim as live.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="todo",
            claimed_at='"2099-12-31T23:59:59+00:00"',
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            view.start_work(1)
        assert exc_info.value.code == "ERR_ALREADY_CLAIMED"

    def test_start_work_expired_claim_allows_reclaim(self, tmp_path: Path) -> None:
        """D18+D36: start_work on a task with an expired claim re-claims it (lazy release).

        When claimed_at is older than claim_timeout (1h), engine.claim_task releases
        the old claim and issues a new one. AgentView.start_work must return a
        SingleTaskResponse with a fresh claimed_at (not None).
        """
        stale = "2026-01-01T00:00:00+00:00"
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="todo",
            claimed_at=f'"{stale}"',  # well over 1h ago
        )
        result = view.start_work(1)
        assert result.claimed_at is not None, (
            "expired claim should be released and re-claimed"
        )
        assert result.claimed_at != stale, (
            "re-claim must issue a new timestamp, not return the stale expired one"
        )
