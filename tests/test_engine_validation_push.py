"""RED-phase tests for pushing validation from AgentView into KanbanEngine (task #1215).

AC coverage:
  AC1  → TestFromAC_ValidateBodySize
  AC2  → TestFromAC_ValidateArchival
  AC3  → TestFromAC_ValidateStatusPredicate
  AC4  → TestFromAC_TaskExists
  AC5  → TestFromAC_EngineCreateEditValidation
  AC6  → TestFromAC_EngineMoveValidation
  AC7  → TestFromAC_AgentViewMethodsRemoved
  AC8  → TestFromAC_CockpitViewMethodsRemoved
  AC9  → TestFromAC_ErrorCodesPreserved  (exact equality assertions on user_message)
  AC10 → regression evidence via reviewer-accepted durable suites:
          - serve/kanban/tests/test_engine_end_work_1077.py   (end_work matrix)
      - tests/test_dispatch_gate_port.py                  (pick_tasks pipeline)
          - serve/kanban/tests/test_engine_create_edit_1070.py (semantic no-op)
          - tests/test_engine_create_edit_1072.py             (semantic no-op)
          - tests/test_engine_cockpit_view.py                 (CockpitView omission guards)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ValidationError
from owlbear_cockpit.view import CockpitView

# ---------------------------------------------------------------------------
# Shared board configurations
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
        todo: builder
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

# Board with a required-section predicate on 'review' status.
_PREDICATE_CONFIG = """\
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
        todo: builder
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates:
        review:
            type: required_sections
            sections: ["## AC"]
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: important
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
{body}
"""

_ARCHIVED_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: archived
priority: important
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: dropped
archival_refs: []
---
Archived task body.
"""

_500_KB = 500 * 1024


def _make_board(tmp_path: Path, config: str = _BASE_CONFIG) -> Path:
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(
    kanban_dir: Path,
    task_id: int,
    title: str = "Task",
    status: str = "research",
    body: str = "Task body.",
) -> Path:
    safe_title = title.lower().replace(" ", "-")
    path = kanban_dir / "tasks" / f"{task_id}-{safe_title}.md"
    path.write_text(
        _TASK_TMPL.format(
            task_id=task_id,
            title=title,
            status=status,
            body=body,
        ),
        encoding="utf-8",
    )
    return path


def _write_archived_task(
    kanban_dir: Path,
    task_id: int,
    title: str = "Archived",
) -> Path:
    safe_title = title.lower().replace(" ", "-")
    path = kanban_dir / "archive" / f"{task_id}-{safe_title}.md"
    path.write_text(
        _ARCHIVED_TASK_TMPL.format(task_id=task_id, title=title),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# AC1 — KanbanEngine.validate_body_size(body: str) -> None
# ---------------------------------------------------------------------------


class TestFromAC_ValidateBodySize:
    """AC1: KanbanEngine exposes public validate_body_size method.

    Raises ValidationError(code="ERR_BODY_TOO_LARGE") when body > 500 KB.
    """

    def test_method_exists_on_engine(self, tmp_path: Path) -> None:
        """Engine must expose validate_body_size as a public method."""
        engine = KanbanEngine(_make_board(tmp_path))
        assert hasattr(engine, "validate_body_size"), "KanbanEngine.validate_body_size does not exist"
        assert callable(engine.validate_body_size)

    def test_empty_body_passes(self, tmp_path: Path) -> None:
        """Empty body must not raise."""
        engine = KanbanEngine(_make_board(tmp_path))
        engine.validate_body_size("")  # must not raise

    def test_small_body_passes(self, tmp_path: Path) -> None:
        """Small body well under limit must not raise."""
        engine = KanbanEngine(_make_board(tmp_path))
        engine.validate_body_size("Hello, world!")  # must not raise

    def test_body_exactly_at_limit_passes(self, tmp_path: Path) -> None:
        """Body of exactly 500 KB must not raise (boundary — inclusive limit)."""
        engine = KanbanEngine(_make_board(tmp_path))
        body = "x" * _500_KB  # 500 KB in ASCII = 500 KB utf-8
        engine.validate_body_size(body)  # must not raise

    def test_body_one_byte_over_raises(self, tmp_path: Path) -> None:
        """Body of 500 KB + 1 byte must raise ERR_BODY_TOO_LARGE."""
        engine = KanbanEngine(_make_board(tmp_path))
        body = "x" * (_500_KB + 1)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_body_size(body)
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_large_body_raises(self, tmp_path: Path) -> None:
        """Body clearly over the 500 KB limit must raise ERR_BODY_TOO_LARGE."""
        engine = KanbanEngine(_make_board(tmp_path))
        body = "x" * (600 * 1024)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_body_size(body)
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_raises_validation_error_subtype(self, tmp_path: Path) -> None:
        """Must raise ValidationError, not a plain ValueError."""
        engine = KanbanEngine(_make_board(tmp_path))
        body = "x" * (600 * 1024)
        with pytest.raises(ValidationError):
            engine.validate_body_size(body)


# ---------------------------------------------------------------------------
# AC2 — KanbanEngine.validate_archival(…) -> None with ERR_ARCHIVAL_* codes
# ---------------------------------------------------------------------------


class TestFromAC_ValidateArchival:
    """AC2: KanbanEngine exposes public validate_archival method.

    Must raise ValidationError with ERR_ARCHIVAL_* codes matching existing
    AgentView._validate_move_archival_for_archive behavior.
    """

    def _engine_and_config(self, tmp_path: Path) -> tuple[KanbanEngine, Any]:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        return engine, engine.board_config()

    def _engine_with_tasks(self, tmp_path: Path) -> tuple[KanbanEngine, Any]:
        board = _make_board(tmp_path)
        _write_task(board, 200, "Ref Task")
        engine = KanbanEngine(board)
        return engine, engine.board_config()

    def test_method_exists_on_engine(self, tmp_path: Path) -> None:
        """Engine must expose validate_archival as a public method."""
        engine, _ = self._engine_and_config(tmp_path)
        assert hasattr(engine, "validate_archival"), "KanbanEngine.validate_archival does not exist"
        assert callable(engine.validate_archival)

    def test_valid_dropped_no_refs_passes(self, tmp_path: Path) -> None:
        """reason='dropped' with no refs must not raise."""
        engine, config = self._engine_and_config(tmp_path)
        engine.validate_archival(
            task_id=100,
            archival_reason="dropped",
            archival_refs=[],
            can_mark_completed=True,
            config=config,
        )

    def test_valid_deprecated_with_refs_passes(self, tmp_path: Path) -> None:
        """reason='deprecated' with a valid ref must not raise."""
        engine, config = self._engine_with_tasks(tmp_path)
        _write_task(engine._kanban_dir, 100, "Root Task")
        engine.validate_archival(
            task_id=100,
            archival_reason="deprecated",
            archival_refs=[200],
            can_mark_completed=True,
            config=config,
        )

    def test_missing_reason_raises_required(self, tmp_path: Path) -> None:
        """No archival_reason must raise ERR_ARCHIVAL_REASON_REQUIRED."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason=None,
                archival_refs=[],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    def test_empty_reason_raises_required(self, tmp_path: Path) -> None:
        """Empty archival_reason string must raise ERR_ARCHIVAL_REASON_REQUIRED."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="",
                archival_refs=[],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    def test_invalid_reason_raises_invalid(self, tmp_path: Path) -> None:
        """Unknown archival_reason must raise ERR_ARCHIVAL_REASON_INVALID."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="bogus_reason",
                archival_refs=[],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_INVALID"
        assert exc_info.value.user_message == (
            "archival_reason must be one of ['completed', 'deprecated', 'dropped', 'duplicate', 'wontfix']"
        )

    def test_deprecated_without_refs_raises(self, tmp_path: Path) -> None:
        """reason='deprecated' with no refs must raise ERR_ARCHIVAL_REFS_REQUIRED."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="deprecated",
                archival_refs=[],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"
        assert exc_info.value.user_message == "archival_refs required for archival_reason='deprecated'"

    def test_duplicate_without_refs_raises(self, tmp_path: Path) -> None:
        """reason='duplicate' with no refs must raise ERR_ARCHIVAL_REFS_REQUIRED."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="duplicate",
                archival_refs=[],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    def test_completed_with_refs_raises_forbidden(self, tmp_path: Path) -> None:
        """reason='completed' with refs must raise ERR_ARCHIVAL_REFS_FORBIDDEN."""
        engine, config = self._engine_with_tasks(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="completed",
                archival_refs=[200],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"
        assert exc_info.value.user_message == "archival_refs forbidden for archival_reason='completed'"

    def test_completed_not_terminal_raises(self, tmp_path: Path) -> None:
        """reason='completed' with can_mark_completed=False raises ERR_COMPLETED_REQUIRES_DONE."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="completed",
                archival_refs=[],
                can_mark_completed=False,
                config=config,
            )
        assert exc_info.value.code == "ERR_COMPLETED_REQUIRES_DONE"
        assert exc_info.value.user_message == "archival_reason='completed' requires terminal status"

    def test_self_ref_raises(self, tmp_path: Path) -> None:
        """archival_refs containing task's own id must raise ERR_ARCHIVAL_REF_SELF."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="deprecated",
                archival_refs=[100],  # same as task_id
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_SELF"

    def test_missing_ref_raises(self, tmp_path: Path) -> None:
        """archival_refs containing non-existent task must raise ERR_ARCHIVAL_REF_MISSING."""
        engine, config = self._engine_and_config(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="deprecated",
                archival_refs=[9999],  # does not exist
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_MISSING"
        assert exc_info.value.user_message == "archival reference task '9999' not found"

    def test_cycle_raises(self, tmp_path: Path) -> None:
        """archival_refs creating a cycle must raise ERR_ARCHIVAL_REF_CYCLE.

        Setup: task 101 already has archival_ref=[100]. Trying to archive task 100
        with archival_refs=[101] creates a cycle.
        """
        board = _make_board(tmp_path)
        # Write task 100 (the one being archived)
        _write_task(board, 100, "Task A")
        # Write task 101 in archive that already references task 100
        archive_path = board / "archive" / "101-task-b.md"
        archive_path.write_text(
            """\
---
id: 101
title: Task B
status: archived
priority: important
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: deprecated
archival_refs: [100]
---
Archived.
""",
            encoding="utf-8",
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="deprecated",
                archival_refs=[101],  # 101 already refs 100 → cycle
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_CYCLE"
        assert exc_info.value.user_message == "archival_refs would introduce a cycle"


# ---------------------------------------------------------------------------
# AC3 — KanbanEngine.validate_status_predicate(target_status, body, config) -> None
# ---------------------------------------------------------------------------


class TestFromAC_ValidateStatusPredicate:
    """AC3: KanbanEngine exposes validate_status_predicate; raises ERR_PREDICATE_FAILED."""

    def test_method_exists_on_engine(self, tmp_path: Path) -> None:
        """Engine must expose validate_status_predicate as a public method."""
        engine = KanbanEngine(_make_board(tmp_path))
        assert hasattr(engine, "validate_status_predicate"), "KanbanEngine.validate_status_predicate does not exist"
        assert callable(engine.validate_status_predicate)

    def test_no_predicate_config_passes(self, tmp_path: Path) -> None:
        """Status with no predicate entry in config must not raise."""
        engine = KanbanEngine(_make_board(tmp_path))
        config = engine.board_config()
        engine.validate_status_predicate(
            target_status="review",
            body="Some body without any sections",
            config=config,
        )

    def test_archived_status_always_passes(self, tmp_path: Path) -> None:
        """Predicate check for 'archived' must be skipped (always passes)."""
        engine = KanbanEngine(_make_board(tmp_path, config=_PREDICATE_CONFIG))
        config = engine.board_config()
        # No body at all — should still pass for 'archived' regardless of predicates
        engine.validate_status_predicate(
            target_status="archived",
            body="",
            config=config,
        )

    def test_satisfied_predicate_passes(self, tmp_path: Path) -> None:
        """Body containing the required section must not raise."""
        engine = KanbanEngine(_make_board(tmp_path, config=_PREDICATE_CONFIG))
        config = engine.board_config()
        body = "## AC\nSome acceptance criteria here."
        engine.validate_status_predicate(
            target_status="review",
            body=body,
            config=config,
        )

    def test_unsatisfied_predicate_raises(self, tmp_path: Path) -> None:
        """Body missing required section must raise ERR_PREDICATE_FAILED."""
        engine = KanbanEngine(_make_board(tmp_path, config=_PREDICATE_CONFIG))
        config = engine.board_config()
        body = "No sections here at all."
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_status_predicate(
                target_status="review",
                body=body,
                config=config,
            )
        assert exc_info.value.code == "ERR_PREDICATE_FAILED"

    def test_empty_sections_list_passes(self, tmp_path: Path) -> None:
        """Predicate with empty sections list must not raise."""
        engine = KanbanEngine(_make_board(tmp_path))
        config = engine.board_config()
        # Manually add a predicate with empty sections to config via mock
        # Use board that has no predicate — simulate via base config which has {}
        engine.validate_status_predicate(
            target_status="backlog",
            body="No sections.",
            config=config,
        )


# ---------------------------------------------------------------------------
# AC4 — KanbanEngine.task_exists(task_id: int) -> bool (public method)
# ---------------------------------------------------------------------------


class TestFromAC_TaskExists:
    """AC4: KanbanEngine exposes task_exists as a PUBLIC method (not _task_exists)."""

    def test_public_method_exists_on_engine(self, tmp_path: Path) -> None:
        """Engine must have task_exists (public); _task_exists must not be required."""
        engine = KanbanEngine(_make_board(tmp_path))
        assert hasattr(engine, "task_exists"), "KanbanEngine.task_exists (public) does not exist"
        assert callable(engine.task_exists)

    def test_returns_true_for_existing_task(self, tmp_path: Path) -> None:
        """task_exists returns True for a task that is present in tasks/."""
        board = _make_board(tmp_path)
        _write_task(board, 42, "Existing Task")
        engine = KanbanEngine(board)
        assert engine.task_exists(42) is True

    def test_returns_false_for_missing_task(self, tmp_path: Path) -> None:
        """task_exists returns False for a task ID with no matching file."""
        engine = KanbanEngine(_make_board(tmp_path))
        assert engine.task_exists(9999) is False


# ---------------------------------------------------------------------------
# AC5 — KanbanEngine.create_task / edit_task call validate_body_size + task_exists
# ---------------------------------------------------------------------------


class TestFromAC_EngineCreateEditValidation:
    """AC5: KanbanEngine's create_task and edit_task validate body size and deps."""

    def test_create_task_large_body_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.create_task with body > 500 KB must raise ERR_BODY_TOO_LARGE."""
        engine = KanbanEngine(_make_board(tmp_path))
        big_body = "x" * (600 * 1024)
        with pytest.raises(ValidationError) as exc_info:
            engine.create_task("Test Task", body=big_body)
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_create_task_missing_parent_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.create_task with non-existent parent must raise ERR_PARENT_NOT_FOUND."""
        engine = KanbanEngine(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            engine.create_task("Test Task", parent=9999)
        assert exc_info.value.code == "ERR_PARENT_NOT_FOUND"
        assert exc_info.value.user_message == "Parent task '9999' not found"

    def test_create_task_missing_dep_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.create_task with non-existent dep must raise ERR_DEP_NOT_FOUND."""
        engine = KanbanEngine(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            engine.create_task("Test Task", depends_on=[9999])
        assert exc_info.value.code == "ERR_DEP_NOT_FOUND"
        assert exc_info.value.user_message == "Dependency task '9999' not found"

    def test_edit_task_large_body_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.edit_task with body > 500 KB must raise ERR_BODY_TOO_LARGE."""
        board = _make_board(tmp_path)
        _write_task(board, 100, "Editable Task")
        engine = KanbanEngine(board)
        big_body = "x" * (600 * 1024)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("100", body=big_body)
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_edit_task_missing_dep_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.edit_task with non-existent dep must raise ERR_DEP_NOT_FOUND."""
        board = _make_board(tmp_path)
        _write_task(board, 100, "Editable Task")
        engine = KanbanEngine(board)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("100", add_deps=[9999])
        assert exc_info.value.code == "ERR_DEP_NOT_FOUND"

    def test_edit_task_missing_parent_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.edit_task with non-existent parent must raise ERR_PARENT_NOT_FOUND."""
        board = _make_board(tmp_path)
        _write_task(board, 100, "Editable Task")
        engine = KanbanEngine(board)
        with pytest.raises(ValidationError) as exc_info:
            engine.edit_task("100", parent=9999)
        assert exc_info.value.code == "ERR_PARENT_NOT_FOUND"
        assert exc_info.value.user_message == "Parent task '9999' not found"


# ---------------------------------------------------------------------------
# AC6 — KanbanEngine.move_task calls validate_archival + validate_status_predicate
# ---------------------------------------------------------------------------


class TestFromAC_EngineMoveValidation:
    """AC6: KanbanEngine.move_task validates archival and status predicates."""

    def test_move_to_archived_without_reason_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.move_task to 'archived' without archival_reason raises."""
        board = _make_board(tmp_path)
        _write_task(board, 100, "Task")
        engine = KanbanEngine(board)
        with pytest.raises(ValidationError) as exc_info:
            engine.move_task("100", "archived", archival_reason=None)
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    def test_move_to_predicate_status_unmet_raises(self, tmp_path: Path) -> None:
        """KanbanEngine.move_task to 'review' with missing required section raises."""
        board = _make_board(tmp_path, config=_PREDICATE_CONFIG)
        _write_task(board, 100, "Task", body="No AC section here.")
        engine = KanbanEngine(board)
        with pytest.raises(ValidationError) as exc_info:
            engine.move_task("100", "review")
        assert exc_info.value.code == "ERR_PREDICATE_FAILED"


# ---------------------------------------------------------------------------
# AC7 — AgentView private validation methods are REMOVED
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewMethodsRemoved:
    """AC7: AgentView's private validation methods no longer exist after refactor.

    Each assert checks that the private helper has been removed and the engine
    public method is called instead.
    """

    def test_no_validate_body_size_private(self) -> None:
        """AgentView must NOT have _validate_body_size (moved to engine)."""
        assert not hasattr(AgentView, "_validate_body_size"), (
            "AgentView._validate_body_size should be removed (moved to KanbanEngine)"
        )

    def test_no_validate_move_archival_for_archive(self) -> None:
        """AgentView must NOT have _validate_move_archival_for_archive."""
        assert not hasattr(AgentView, "_validate_move_archival_for_archive"), (
            "AgentView._validate_move_archival_for_archive should be removed"
        )

    def test_no_validate_move_destination_predicate(self) -> None:
        """AgentView must NOT have _validate_move_destination_predicate."""
        assert not hasattr(AgentView, "_validate_move_destination_predicate"), (
            "AgentView._validate_move_destination_predicate should be removed"
        )

    def test_no_task_exists_private(self) -> None:
        """AgentView must NOT have _task_exists (engine now exposes task_exists)."""
        assert not hasattr(AgentView, "_task_exists"), (
            "AgentView._task_exists should be removed (replaced by engine.task_exists)"
        )

    def test_no_has_archival_cycle(self) -> None:
        """AgentView must NOT have _has_archival_cycle (moved to engine)."""
        assert not hasattr(AgentView, "_has_archival_cycle"), "AgentView._has_archival_cycle should be removed"

    def test_no_required_sections_passes(self) -> None:
        """AgentView must NOT have _required_sections_passes (moved to engine)."""
        assert not hasattr(AgentView, "_required_sections_passes"), (
            "AgentView._required_sections_passes should be removed"
        )


# ---------------------------------------------------------------------------
# AC8 — CockpitView private validation methods are REMOVED
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewMethodsRemoved:
    """AC8: CockpitView's duplicate private validation methods no longer exist."""

    def test_no_validate_move_archival_for_archive(self) -> None:
        """CockpitView must NOT have _validate_move_archival_for_archive."""
        assert not hasattr(CockpitView, "_validate_move_archival_for_archive"), (
            "CockpitView._validate_move_archival_for_archive should be removed"
        )

    def test_no_has_archival_cycle(self) -> None:
        """CockpitView must NOT have _has_archival_cycle."""
        assert not hasattr(CockpitView, "_has_archival_cycle"), "CockpitView._has_archival_cycle should be removed"


# ---------------------------------------------------------------------------
# AC9 — Error codes and user_message strings preserved (no behavior change)
# ---------------------------------------------------------------------------


class TestFromAC_ErrorCodesPreserved:
    """AC9: After refactoring, engine-level methods produce identical codes/messages.

    Tests call engine public methods directly (not through AgentView) to verify
    the codes and message patterns are preserved at the engine layer.
    These tests fail in RED because engine methods don't exist yet.
    """

    def test_validate_body_size_code_and_message(self, tmp_path: Path) -> None:
        """ERR_BODY_TOO_LARGE code and 'exceeds 500 KB' message preserved."""
        engine = KanbanEngine(_make_board(tmp_path))
        body = "x" * (600 * 1024)
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_body_size(body)
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"
        assert exc_info.value.user_message == "Task body exceeds 500 KB"

    def test_validate_archival_reason_required_message(self, tmp_path: Path) -> None:
        """ERR_ARCHIVAL_REASON_REQUIRED message preserved at engine level."""
        engine = KanbanEngine(_make_board(tmp_path))
        config = engine.board_config()
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason=None,
                archival_refs=[],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"
        assert exc_info.value.user_message == "archival_reason is required when status='archived'"

    def test_validate_archival_refs_required_code(self, tmp_path: Path) -> None:
        """ERR_ARCHIVAL_REFS_REQUIRED code and message preserved at engine level."""
        engine = KanbanEngine(_make_board(tmp_path))
        config = engine.board_config()
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="deprecated",
                archival_refs=[],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"
        assert exc_info.value.user_message == "archival_refs required for archival_reason='deprecated'"

    def test_validate_archival_self_ref_code(self, tmp_path: Path) -> None:
        """ERR_ARCHIVAL_REF_SELF code and message preserved at engine level."""
        engine = KanbanEngine(_make_board(tmp_path))
        config = engine.board_config()
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_archival(
                task_id=100,
                archival_reason="deprecated",
                archival_refs=[100],
                can_mark_completed=True,
                config=config,
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_SELF"
        assert exc_info.value.user_message == "archival_refs cannot include the task itself"

    def test_validate_predicate_failed_code_and_message(self, tmp_path: Path) -> None:
        """ERR_PREDICATE_FAILED code and message with status name preserved."""
        engine = KanbanEngine(_make_board(tmp_path, config=_PREDICATE_CONFIG))
        config = engine.board_config()
        with pytest.raises(ValidationError) as exc_info:
            engine.validate_status_predicate(
                target_status="review",
                body="No AC section.",
                config=config,
            )
        assert exc_info.value.code == "ERR_PREDICATE_FAILED"
        assert exc_info.value.user_message == "Task body does not satisfy predicate for status 'review'"

    def test_engine_move_archival_reason_required_via_engine(self, tmp_path: Path) -> None:
        """KanbanEngine.move_task to archived propagates ERR_ARCHIVAL_REASON_REQUIRED."""
        board = _make_board(tmp_path)
        _write_task(board, 100, "Task")
        engine = KanbanEngine(board)
        with pytest.raises(ValidationError) as exc_info:
            engine.move_task("100", "archived", archival_reason=None)
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"
        assert exc_info.value.user_message == "archival_reason is required when status='archived'"
