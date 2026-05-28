"""Retry-cycle tests for AgentView.end_work (task #1080).

Reviewer cited two gaps after second builder pass (B-12):

GAP-1 — Missing direct ``end_work`` ``_move_file`` fault-injection proof.
  The B-12 builder added an archive-move rollback branch in
  ``KanbanEngine.end_work``.  No task-owned test proved that branch; the only
  ``_move_file`` fault-injection proof in the workspace targeted the sibling
  ``move_task`` path.  Tests here prove the ``end_work`` rollback directly for
  both archive-triggering outcomes: success-from-terminal and reject-to-archived.

GAP-2 — Weak guidance assertions for D54 (AR hint + skip-warning).
  Existing tests used ``any("decision" in hint.lower() or "AR" in hint …)`` and
  ``any("skip" in hint.lower() …)`` which pass on partial or malformed strings.
  Tests here use exact-list equality so that drift in AR-hint wording, skip-count
  arithmetic, or status names causes a suite failure.

Tests added in loop-breaker pass (task #1080 cycle 3) prove the reject-to-archived
rollback restores body, archival_reason, and archival_refs fields.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView

# ---------------------------------------------------------------------------
# Board helpers (mirrors conventions from test_engine_end_work_1077.py)
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
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

_LIVE_CLAIM_TS = '"2026-04-25T08:00:00+00:00"'  # non-null, within 1 h claim_timeout

# Exact D54 contract strings emitted by AgentView.
_EXPECTED_BLOCK_AR_HINT = (
    "\u26a0\ufe0f ACTION REQUIRED: Create a Decision Request via the create_dr tool."
    " Blocks without a DR are invisible to the pipeline."
)


def _expected_skip_warning(before: str, after: str, skipped: int) -> str:
    return (
        f"\u26a0\ufe0f Status skip: moved from '{before}' to '{after}'"
        f" (skipped {skipped} column(s)). Verify this jump is intentional."
    )


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
    body: str = "Original body.",
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
# TestFromAC_EndWorkArchiveRollback
#
# GAP-1: direct _move_file fault-injection proof for end_work archive paths.
#
# Covers:
#   - success outcome from terminal status (needs_archive=True path, D51)
#   - reject outcome to archived (needs_archive=True path)
#
# Contract: when _move_file raises OSError the engine must:
#   (a) NOT leave a file in archive/
#   (b) restore the ORIGINAL task record in tasks/ (pre-mutation body, original
#       claimed_at, original status)
#   (c) re-raise the OSError to the caller
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkArchiveRollback:
    """GAP-1: _move_file fault injection for end_work archive paths (D41 + new rollback branch)."""

    def test_success_from_terminal_move_failure_reraises_oserror(self, tmp_path: Path) -> None:
        """end_work(success) from terminal + _move_file OSError → OSError propagates to caller.

        FAIL reason: the rollback branch in KanbanEngine.end_work catches OSError
        only to restore state and re-raise; if the catch-and-re-raise is missing,
        the OSError is swallowed and the file is left in a partially-archived state.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="done", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError, match="disk full"),
        ):
            view.end_work(1, outcome="success", note="Done.")

    def test_success_from_terminal_move_failure_no_archive_file(self, tmp_path: Path) -> None:
        """end_work(success) from terminal + _move_file OSError → no file left in archive/.

        FAIL reason: the post-write state before rollback has the mutated record in
        tasks/ (status=archived); if rollback is missing the record stays there and
        the file is never moved to archive/, but if _move_file raises AFTER a partial
        move, a file could appear in archive/.  The contract: archive/ must be empty.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="done", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(1, outcome="success", note="Done.")

        assert not any((kanban_dir / "archive").glob("1-*.md")), (
            "archive/ must be empty after _move_file OSError in end_work(success)"
        )

    def test_success_from_terminal_move_failure_restores_original_status(self, tmp_path: Path) -> None:
        """end_work(success) from terminal + _move_file OSError → original status restored in tasks/.

        FAIL reason: KanbanEngine.end_work calls write_task(record, …) BEFORE _move_file;
        if the OSError rollback write_task(original, …) is missing, the file in tasks/
        has status=archived instead of the pre-mutation status (done).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="done", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(1, outcome="success", note="Done.")

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        assert restored.status == "done", f"status must be restored to 'done' after rollback; got {restored.status!r}"

    def test_success_from_terminal_move_failure_restores_claimed_at(self, tmp_path: Path) -> None:
        """end_work(success) + _move_file OSError → claimed_at restored (not cleared) in tasks/.

        FAIL reason: KanbanEngine.end_work clears claimed_at in the mutated record
        before write_task(record, …); rollback must restore original where claimed_at
        is non-null.  If rollback is absent, the persisted record has claimed_at=null.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="done", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(1, outcome="success", note="Done.")

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        assert restored.claimed_at is not None, (
            "claimed_at must be restored (non-null) after _move_file OSError rollback"
        )

    def test_success_from_terminal_move_failure_restores_original_body(self, tmp_path: Path) -> None:
        """end_work(success) + _move_file OSError → original body restored (note NOT prepended).

        FAIL reason: KanbanEngine.end_work prepends the timestamped note before
        write_task(record, …); rollback must restore original which has no note.
        If rollback is absent, the persisted body contains the prepended note.
        """
        original_body = "Original body before end_work."
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="done", claimed_at=_LIVE_CLAIM_TS, body=original_body)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(1, outcome="success", note="Prepended note that must be gone.")

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        body_text = restored.body if isinstance(restored.body, str) else "\n".join(restored.body or [])
        assert "Prepended note that must be gone." not in body_text, (
            "note must NOT be present in restored body after _move_file OSError rollback"
        )
        assert original_body in body_text, "original body content must be present in restored record after rollback"

    def test_reject_to_archived_move_failure_reraises_oserror(self, tmp_path: Path) -> None:
        """end_work(reject, move_to='archived') + _move_file OSError → OSError propagates.

        FAIL reason: same rollback branch covers reject-to-archived path; must re-raise.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError, match="disk full"),
        ):
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                archival_reason="dropped",
                note="Dropping.",
            )

    def test_reject_to_archived_move_failure_no_archive_file(self, tmp_path: Path) -> None:
        """end_work(reject, archived) + _move_file OSError → no file in archive/.

        FAIL reason: same as success path — rollback must leave archive/ empty.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                archival_reason="dropped",
                note="Dropping.",
            )

        assert not any((kanban_dir / "archive").glob("1-*.md")), (
            "archive/ must be empty after _move_file OSError in end_work(reject-to-archived)"
        )

    def test_reject_to_archived_move_failure_restores_original_status(self, tmp_path: Path) -> None:
        """end_work(reject, archived) + _move_file OSError → original status restored in tasks/.

        FAIL reason: without rollback, tasks/ holds the mutated record with
        status=archived instead of original status (in-progress).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                archival_reason="dropped",
                note="Dropping.",
            )

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        assert restored.status == "in-progress", (
            f"status must be restored to 'in-progress' after reject-to-archived rollback; got {restored.status!r}"
        )

    def test_reject_to_archived_move_failure_restores_claimed_at(self, tmp_path: Path) -> None:
        """end_work(reject, archived) + _move_file OSError → claimed_at restored.

        FAIL reason: without rollback, the mutated record has claimed_at=null;
        rollback must restore the original non-null claimed_at.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, status="in-progress", claimed_at=_LIVE_CLAIM_TS)

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                archival_reason="dropped",
                note="Dropping.",
            )

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        assert restored.claimed_at is not None, (
            "claimed_at must be non-null (restored from original) after reject-to-archived rollback"
        )

    def test_reject_to_archived_move_failure_restores_original_body(self, tmp_path: Path) -> None:
        """end_work(reject, archived) + _move_file OSError → original body restored (note NOT prepended).

        FAIL reason: KanbanEngine.end_work prepends the timestamped note before
        write_task(record, …); rollback must restore original which has no prepended note.
        If rollback is absent, the persisted body contains the prepended note.
        Mirrors the success-path proof at test_success_from_terminal_move_failure_restores_original_body.
        """
        original_body = "Original reject body before end_work."
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            status="in-progress",
            claimed_at=_LIVE_CLAIM_TS,
            body=original_body,
        )

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                archival_reason="dropped",
                note="Prepended reject note that must be gone.",
            )

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        body_text = restored.body if isinstance(restored.body, str) else "\n".join(restored.body or [])
        assert "Prepended reject note that must be gone." not in body_text, (
            "note must NOT be present in restored body after reject-to-archived _move_file OSError rollback"
        )
        assert original_body in body_text, "original body content must be present in restored record after rollback"

    def test_reject_to_archived_move_failure_restores_archival_reason(self, tmp_path: Path) -> None:
        """end_work(reject, archived) + _move_file OSError → archival_reason restored to None.

        FAIL reason: _apply_outcome sets record.archival_reason = archival_reason
        (e.g. 'dropped') before write_task(record, …); rollback must restore original
        where archival_reason is None.  If rollback is absent, the persisted record
        has archival_reason='dropped' instead of None.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            status="in-progress",
            claimed_at=_LIVE_CLAIM_TS,
            archival_reason="null",
        )

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                archival_reason="dropped",
                note="Dropping.",
            )

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        assert restored.archival_reason is None, (
            f"archival_reason must be None (original) after reject-to-archived rollback;"
            f" got {restored.archival_reason!r}"
        )

    def test_reject_to_archived_move_failure_restores_archival_refs(self, tmp_path: Path) -> None:
        """end_work(reject, archived) + _move_file OSError → archival_refs restored to [] (not caller-supplied).

        FAIL reason: _apply_outcome sets record.archival_refs = archival_refs
        ([2]) before write_task(record, …); rollback must restore the original
        empty list.  If rollback is absent, the persisted record has archival_refs=[2]
        instead of [].

        Uses archival_reason='duplicate' (requires non-empty refs per validation) so
        that a non-trivial archival_refs=[2] is legitimately set during mutation.
        A second task (id=2) is created to satisfy the archival-ref-exists check.
        """
        view, kanban_dir = _make_view(tmp_path)
        # Task 1: target (to be rejected to archived)
        _write_task(
            kanban_dir,
            task_id=1,
            status="in-progress",
            claimed_at=_LIVE_CLAIM_TS,
            archival_refs="[]",
        )
        # Task 2: the duplicate reference required by archival_reason='duplicate'
        _write_task(kanban_dir, task_id=2, status="done", archival_refs="[]")

        with (
            patch(
                "owlbear_kanban.engine._move_file",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError),
        ):
            view.end_work(
                1,
                outcome="reject",
                move_to="archived",
                archival_reason="duplicate",
                archival_refs=[2],
                note="Dropping as duplicate.",
            )

        fresh = KanbanEngine(kanban_dir, activity_log=False)
        restored = fresh.show_task("1")
        assert (restored.archival_refs or []) == [], (
            f"archival_refs must be [] (original) after reject-to-archived rollback; got {restored.archival_refs!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GuidanceExact
#
# GAP-2: exact guidance string assertions for D54 contract.
#
# Prior tests only checked generic substrings ("decision", "AR", "skip");
# these tests use exact-list equality so that:
#   - a changed AR-hint wording fails
#   - a wrong skip-count or wrong status name fails
#   - extra/missing guidance items fail
#   - empty guidance where a hint is expected fails
# ---------------------------------------------------------------------------


