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
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine, storage
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
    ("status_predicates:\n  review:\n    type: required_sections\n    sections:\n      - Test Results"),
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


def _make_view(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> tuple[AgentView, Path]:
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

    def test_archive_without_reason_raises_archival_reason_required(self, tmp_path: Path) -> None:
        """AC4: move_task(id, "archived") with no archival_reason → ERR_ARCHIVAL_REASON_REQUIRED.

        Every archive operation must carry an archival_reason. Current impl
        ignores archival_reason entirely and archives the task unconditionally.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(1, "archived")
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    def test_archive_completed_from_non_terminal_raises_completed_requires_done(self, tmp_path: Path) -> None:
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

    def test_archive_deprecated_without_refs_raises_archival_refs_required(self, tmp_path: Path) -> None:
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

    def test_archive_dropped_with_refs_raises_archival_refs_forbidden(self, tmp_path: Path) -> None:
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

    def test_archive_invalid_reason_raises_archival_reason_invalid(self, tmp_path: Path) -> None:
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

    def test_archive_with_missing_ref_raises_archival_ref_missing(self, tmp_path: Path) -> None:
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
            view.move_task(1, "archived", archival_reason="deprecated", archival_refs=[99999])
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_MISSING"

    def test_archival_reason_on_active_status_raises_fields_forbidden(self, tmp_path: Path) -> None:
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

    def test_product_topology_ignores_config_predicate_move_succeeds(self, tmp_path: Path) -> None:
        """With PRODUCT_TOPOLOGY, status_predicates={} — move_task to 'review' succeeds.

        Config predicate on 'review' is ignored; PRODUCT_TOPOLOGY provides empty predicates.
        move_task(1, 'review') succeeds and task is moved to 'review'.
        """
        view, kanban_dir = _make_view(tmp_path, _PREDICATE_CONFIG)
        _write_task(kanban_dir, task_id=1, status="in-progress", body="No test results here.")
        result = view.move_task(1, "review")  # must NOT raise
        assert result.status == "review", f"move_task must succeed (no predicate enforcement); got {result.status!r}"

    def test_product_topology_ignores_config_predicate_task_is_moved(self, tmp_path: Path) -> None:
        """With PRODUCT_TOPOLOGY, status_predicates={} — task IS moved to 'review'.

        Config predicate on 'review' is ignored; PRODUCT_TOPOLOGY provides empty predicates.
        After move_task(1, 'review'), show_task reports task at 'review'.
        """
        view, kanban_dir = _make_view(tmp_path, _PREDICATE_CONFIG)
        _write_task(kanban_dir, task_id=1, status="in-progress", body="No test results here.")
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

    def test_archive_cleared_claim_persisted_in_archive_file(self, tmp_path: Path) -> None:
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
        assert any((kanban_dir / "archive").glob("1-*.md")), "task file must exist in archive/ after archive"
        assert not any((kanban_dir / "tasks").glob("1-*.md")), "task file must not remain in tasks/ after archive"
        # Fresh engine: bypasses any in-memory cache from the view's engine.
        fresh_engine = KanbanEngine(kanban_dir, activity_log=False)
        on_disk = fresh_engine.show_task("1")
        assert on_disk.claimed_at is None

    def test_move_skipping_two_columns_emits_skip_guidance(self, tmp_path: Path) -> None:
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

    def test_archive_move_failure_restores_original_task_record(self, tmp_path: Path) -> None:
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
        assert restored.status == "todo", "status must be restored to pre-archive value after rollback"
        assert restored.claimed_at is not None, "claimed_at must not be cleared on a failed archive"


# ---------------------------------------------------------------------------
# TestFromAC_StartWork
#
# Tests for AgentView.start_work:
#   - blocked task → ERR_BLOCKED_NOT_CLAIMABLE
#   - archived task → ERR_ARCHIVED_NOT_CLAIMABLE
#
# The assertions below preserve the resolved claim-guard behavior for blocked,
# archived, missing, and already-claimed tasks.
# ---------------------------------------------------------------------------


class TestFromAC_StartWork:
    """Claim-guard semantics for start_work on blocked and archived tasks."""

    def test_blocked_task_raises_blocked_not_claimable(self, tmp_path: Path) -> None:
        """start_work on a blocked task → ValidationError(ERR_BLOCKED_NOT_CLAIMABLE).

        The engine raises ValueError("Task '1' is blocked and cannot be claimed"),
        and AgentView.start_work translates it to ERR_BLOCKED_NOT_CLAIMABLE.
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

        Archived tasks live in archive/, not tasks/. AgentView.start_work checks
        archived storage and reports ERR_ARCHIVED_NOT_CLAIMABLE.
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

    def test_start_work_already_claimed_raises_already_claimed(self, tmp_path: Path) -> None:
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
        assert result.claimed_at is not None, "expired claim should be released and re-claimed"
        assert result.claimed_at != stale, "re-claim must issue a new timestamp, not return the stale expired one"


# --- merged from serve/kanban/tests/test_engine_move_claim_edges.py ---
class TestFromAC_StartWork_1075:
    """D18+D36 CAS contract tests for AgentView.start_work."""

    def test_already_claimed_error_includes_claimed_at(self, tmp_path: Path) -> None:
        """D18+D36: ConcurrencyError(ERR_ALREADY_CLAIMED) must include claimed_at in message.

        Brief §1.7: ``ConcurrencyError(code="ERR_ALREADY_CLAIMED", detail="claimed_at={ts}")``.
        The error message must contain the live claim timestamp so callers can
        compute retry delay.  Current AgentView.start_work raises the error
        with a generic "already claimed by another agent" message that omits
        the timestamp.
        """
        view, kanban_dir = _make_view(tmp_path)
        live_ts = "2099-12-31T23:59:59+00:00"
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{live_ts}"')
        with pytest.raises(ConcurrencyError) as exc_info:
            view.start_work(1)
        assert exc_info.value.code == "ERR_ALREADY_CLAIMED"
        # D18+D36 brief contract: error detail must include the live claimed_at value.
        assert live_ts in exc_info.value.user_message, (
            f"ERR_ALREADY_CLAIMED message must contain claimed_at timestamp; got: {exc_info.value.user_message!r}"
        )

    def test_expired_claim_release_uses_cas_primitive(self, tmp_path: Path) -> None:
        """D18+D36: start_work on expired-claim task must route the release write
        through storage.write_task_if_unchanged (CAS), not plain write_task.

        Brief §1.7: "lazy-release first per D18+D36 by routing the release through
        storage.write_task_if_unchanged(cleared_task, expected_updated=current.updated, ...)".
        Current engine.claim_task uses plain write_task for the release — the CAS
        primitive is never called.
        """
        view, kanban_dir = _make_view(tmp_path)
        stale = "2026-01-01T00:00:00+00:00"  # well over 1h ago — expired
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{stale}"')

        mock_cas: MagicMock = MagicMock(wraps=storage.write_task_if_unchanged)
        with patch("owlbear_kanban.storage.write_task_if_unchanged", mock_cas):
            view.start_work(1)

        assert mock_cas.called, (
            "storage.write_task_if_unchanged must be called during expired-claim "
            "lazy-release (D18+D36); engine.claim_task currently uses plain write_task"
        )

    def test_fresh_claim_uses_cas_primitive(self, tmp_path: Path) -> None:
        """D18+D36: start_work on an unclaimed task must route the claim write
        through storage.write_task_if_unchanged (CAS).

        Brief §1.7: "otherwise proceed to claim via the same CAS primitive."
        An unclaimed task also uses CAS for the claim write to prevent two
        agents from simultaneously overwriting each other's claim tokens.
        Current engine.claim_task uses plain write_task — CAS is never called.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")  # no claim

        mock_cas: MagicMock = MagicMock(wraps=storage.write_task_if_unchanged)
        with patch("owlbear_kanban.storage.write_task_if_unchanged", mock_cas):
            view.start_work(1)

        assert mock_cas.called, (
            "storage.write_task_if_unchanged must be called for the claim write "
            "even on a fresh (unclaimed) task (D18+D36 — 'same CAS primitive'); "
            "engine.claim_task currently uses plain write_task"
        )

    def test_expired_claim_cas_stale_retry_raises_already_claimed(self, tmp_path: Path) -> None:
        """D18+D36: when the CAS write for expired-claim release raises ERR_STALE
        (concurrent agent beat us), start_work retries from the top; if the re-read
        finds a live claim, it raises ConcurrencyError(ERR_ALREADY_CLAIMED).

        Brief §1.7: "on ERR_STALE (another writer beat us to it), re-read and
        re-evaluate from the top."

        Simulation: on the first write_task_if_unchanged call we inject a
        concurrent live claim into the file then raise ConcurrencyError(ERR_STALE).
        The CAS-aware implementation retries, reads the live claim, and raises
        ERR_ALREADY_CLAIMED.  Without CAS, write_task_if_unchanged is never
        called, no injection occurs, and start_work returns success — causing this
        test to fail with "DID NOT RAISE ConcurrencyError".
        """
        view, kanban_dir = _make_view(tmp_path)
        stale = "2026-01-01T00:00:00+00:00"  # expired claim
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{stale}"')

        call_count = 0

        def inject_then_stale(task: object, expected_updated: str, kdir: Path) -> Path:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate: another agent claims the task before our CAS write.
                current_path = next((kdir / "tasks").glob("1-*.md"))
                from owlbear_kanban.storage import read_task, write_task  # noqa: PLC0415

                live_record = read_task(current_path)
                live_record.claimed_at = "2099-12-31T00:00:00+00:00"
                live_record.updated = "2099-12-31T00:00:00+00:00"
                write_task(live_record, kdir)
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message="simulated concurrent modification",
                )
            # Allow subsequent calls through (second attempt after retry).
            return storage.write_task_if_unchanged(task, expected_updated, kdir)

        with (
            patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=inject_then_stale,
            ),
            pytest.raises(ConcurrencyError) as exc_info,
        ):
            view.start_work(1)

        assert exc_info.value.code == "ERR_ALREADY_CLAIMED", (
            f"Expected ERR_ALREADY_CLAIMED after ERR_STALE retry sees live claim; got {exc_info.value.code!r}"
        )

    def test_expired_claim_release_before_claim_two_cas_writes(self, tmp_path: Path) -> None:
        """D18+D36: expired-claim path must issue TWO CAS writes in sequence:
        (1) release write — task with claimed_at=None, then (2) claim write —
        task with claimed_at=<now>.

        Brief §1.7: "lazy-release first per D18+D36 by routing the release through
        storage.write_task_if_unchanged(cleared_task, expected_updated=current.updated, ...);
        ... otherwise proceed to claim via the same CAS primitive."

        The current engine.claim_task performs a single CAS write that sets
        claimed_at to the new timestamp directly (no prior release step), so:
          - cas_call_claimed_ats has only 1 entry → assertion len >= 2 fails.
        Even if len were to pass, the first entry would have claimed_at != None.
        """
        view, kanban_dir = _make_view(tmp_path)
        stale = "2026-01-01T00:00:00+00:00"  # well over 1h ago — expired
        _write_task(kanban_dir, task_id=1, status="todo", claimed_at=f'"{stale}"')

        real_cas = storage.write_task_if_unchanged
        cas_call_claimed_ats: list[str | None] = []

        def capture(task: object, expected_updated: str, kdir: Path) -> Path:
            cas_call_claimed_ats.append(getattr(task, "claimed_at", None))
            return real_cas(task, expected_updated, kdir)

        with patch("owlbear_kanban.storage.write_task_if_unchanged", side_effect=capture):
            view.start_work(1)

        assert len(cas_call_claimed_ats) >= 2, (
            f"Expected ≥2 CAS writes (release then claim) for expired-claim path; "
            f"got {len(cas_call_claimed_ats)} write(s) with claimed_at values: "
            f"{cas_call_claimed_ats!r}. "
            f"Brief §1.7 requires a release step (claimed_at=None) before the claim write."
        )
        assert cas_call_claimed_ats[0] is None, (
            f"First CAS write must be the release step with claimed_at=None; "
            f"got claimed_at={cas_call_claimed_ats[0]!r}. "
            f"Current implementation skips the release step and claims directly."
        )
        assert cas_call_claimed_ats[1] is not None, (
            f"Second CAS write must be the claim step with claimed_at=<new timestamp>; "
            f"got claimed_at={cas_call_claimed_ats[1]!r}"
        )

    def test_stale_retry_success_produces_fresh_timestamps(self, tmp_path: Path) -> None:
        """D14: on stale-retry-success, claimed_at and updated must be fresher
        than the pre-attempt snapshot (effective_now refreshed inside retry loop).

        Brief §3.2: updated is advanced on every successful write.
        Regression guard: if effective_now were captured once before the retry loop
        (old bug), successful retries after ERR_STALE could reuse a stale timestamp
        and set updated/claimed_at to a value that lags the re-read snapshot.
        Fix at engine.py:1136 refreshes effective_now inside the loop.

        Failure mode: CAS-raise-stale logic is absent (write_task_if_unchanged never
        called) → second call never fires → call_count stays 1 → assertion fails.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")

        # Read the initial snapshot so we have a definite lower bound for freshness.
        task_path = next((kanban_dir / "tasks").glob("1-*.md"))
        snapshot = storage.read_task(task_path)
        snapshot_updated_str = snapshot.updated  # "2026-01-01T10:00:00+00:00"

        call_count = 0
        real_cas = storage.write_task_if_unchanged

        def stale_on_first(task: object, expected_updated: str, kdir: Path) -> Path:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message="simulated stale — retry should refresh timestamps",
                )
            return real_cas(task, expected_updated, kdir)

        with patch("owlbear_kanban.storage.write_task_if_unchanged", side_effect=stale_on_first):
            result = view.start_work(1)

        from datetime import datetime  # noqa: PLC0415

        snapshot_dt = datetime.fromisoformat(snapshot_updated_str)
        result_claimed_at = datetime.fromisoformat(result.claimed_at)
        result_updated = datetime.fromisoformat(result.updated)

        assert result_claimed_at > snapshot_dt, (
            f"D14: after stale-retry-success, claimed_at={result.claimed_at!r} must be "
            f"fresher than pre-attempt snapshot.updated={snapshot_updated_str!r}"
        )
        assert result_updated > snapshot_dt, (
            f"D14: after stale-retry-success, updated={result.updated!r} must be "
            f"fresher than pre-attempt snapshot.updated={snapshot_updated_str!r}"
        )
        assert call_count == 2, (  # noqa: PLR2004
            f"Expected exactly 2 CAS calls (first stale, second success); got {call_count}"
        )

    def test_stale_retry_success_timestamps_fresher_than_concurrent_update(self, tmp_path: Path) -> None:
        """D14 (mutation-resistant): stale-retry claimed_at/updated must be fresher
        than the concurrent update written during ERR_STALE.

        Mechanism (architect AC refinement — prescribes HOW, not just WHAT):
          T1 < T_concurrent < T3
          - datetime.now mocked: first loop iteration → T1, retry iteration → T3
          - ERR_STALE callback writes the task file with updated=T_concurrent
            (simulates a concurrent edit that beat our CAS)
          - Engine re-reads: task.updated=T_concurrent, effective_now=T3 (refreshed)
          - Assertions: result.claimed_at >= T3 AND result.updated >= T3

        Mutation guard: if effective_now were captured once before the loop
        (reverting engine.py:1136), both iterations use T1.  T1 < T_concurrent so
        the second CAS succeeds but result.updated = T1 < T3 → assertion fails.

        NOTE: regression guard — PASSES because engine.py:1136 fix is already in place.
        """
        import datetime as _dt  # noqa: PLC0415

        t1 = _dt.datetime(2026, 1, 1, 10, 0, 1, tzinfo=_dt.UTC)
        t_concurrent = _dt.datetime(2026, 1, 1, 10, 0, 2, tzinfo=_dt.UTC)
        t3 = _dt.datetime(2026, 1, 1, 10, 0, 3, tzinfo=_dt.UTC)

        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")

        scheduled: list[_dt.datetime] = [t1, t3]

        class _MockDatetime(_dt.datetime):
            @classmethod
            def now(cls, tz: object = None) -> _dt.datetime:  # type: ignore[override]
                if scheduled:
                    return scheduled.pop(0)
                return _dt.datetime.now(tz=tz)  # type: ignore[arg-type]

        real_cas = storage.write_task_if_unchanged
        cas_call_count = 0

        def stale_then_succeed(task: object, expected_updated: str, kdir: Path) -> Path:
            nonlocal cas_call_count
            cas_call_count += 1
            if cas_call_count == 1:
                # Concurrent update: write t_concurrent to disk, then raise ERR_STALE.
                task_path = next((kdir / "tasks").glob("1-*.md"))
                from owlbear_kanban.storage import (
                    read_task as _read,
                    write_task as _write,
                )  # noqa: PLC0415

                concurrent_record = _read(task_path)
                concurrent_record.updated = t_concurrent.isoformat()
                _write(concurrent_record, kdir)
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message="simulated concurrent edit",
                )
            return real_cas(task, expected_updated, kdir)

        with (
            patch("owlbear_kanban.engine.datetime", _MockDatetime),
            patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=stale_then_succeed,
            ),
        ):
            result = view.start_work(1)

        result_claimed_at = _dt.datetime.fromisoformat(result.claimed_at)
        result_updated = _dt.datetime.fromisoformat(result.updated)

        assert result_claimed_at >= t3, (
            f"D14: stale-retry-success claimed_at={result.claimed_at!r} must be "
            f">= t3={t3.isoformat()!r}; mutation guard: reverting engine.py:1136 "
            f"gives effective_now=t1={t1.isoformat()!r} < t3"
        )
        assert result_updated >= t3, (
            f"D14: stale-retry-success updated={result.updated!r} must be "
            f">= t3={t3.isoformat()!r}; mutation guard: reverting engine.py:1136 "
            f"gives effective_now=t1={t1.isoformat()!r} < t3"
        )
        assert cas_call_count == 2, (  # noqa: PLR2004
            f"Expected 2 CAS calls (stale then succeed); got {cas_call_count}"
        )


class TestFromAC_MoveTask_D37_1075:
    """D37 archival-matrix self-ref and cycle tests for AgentView.move_task."""

    def test_move_task_archival_rejects_self_reference(self, tmp_path: Path) -> None:
        """D37: move_task('archived') must raise ERR_ARCHIVAL_REF_SELF when
        archival_refs includes the task's own id.

        Brief §1.6 D37 matrix (same as edit_task): self-references are always
        forbidden.  The edit_task path enforces this at engine.py:2443-2445.
        Current _validate_move_archival omits the check (no task_id param) so
        the call completes without raising.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="done")

        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                archival_reason="deprecated",
                archival_refs=[1],  # self-reference
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_SELF", (
            f"move_task must reject self-referencing archival_refs with "
            f"ERR_ARCHIVAL_REF_SELF; got {exc_info.value.code!r}"
        )

    def test_move_task_archival_rejects_cycle(self, tmp_path: Path) -> None:
        """D37: move_task('archived') must raise ERR_ARCHIVAL_REF_CYCLE when
        archival_refs would introduce a transitive cycle.

        Setup: task 2 already references task 1 (archival_refs=[1]).
        Archiving task 1 with archival_refs=[2] creates the cycle 1→2→1.
        The edit_task path catches this at engine.py:2454-2456 via the existing
        _has_archival_cycle helper.  Current _validate_move_archival never calls
        that helper, so no error is raised.
        """
        view, kanban_dir = _make_view(tmp_path)
        # task 2 already archived and references task 1
        _write_task(
            kanban_dir,
            task_id=2,
            status="todo",
            archival_refs="[1]",
        )
        # task 1 (the one being moved) references task 2 → creates cycle 1→2→1
        _write_task(kanban_dir, task_id=1, status="done")

        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                archival_reason="deprecated",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_CYCLE", (
            f"move_task must reject cycles in archival_refs with ERR_ARCHIVAL_REF_CYCLE; got {exc_info.value.code!r}"
        )
