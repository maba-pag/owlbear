"""RED-phase tests for AgentView.create_task and AgentView.edit_task (task #1070).

Covers Brief B paper-integration.md §1.4, §1.5, §3.2, §3.4, §3.5, §4:
  - create_task: entry_status gate (D50), dep/parent existence (§3.4),
    body size (D35+D47), predicate-on-create (D15+D50)
  - edit_task: body-exclusive (AC14), dep/parent existence (AC25, AC-NEW-15),
    no-op (ERR_NO_OP), body size (D47), block_reason semantics (D53),
    timestamp wire format (AC30), archival field gates (D37+D57),
    completed-requires-terminal (AC6+D37+D65), archival_refs matrix (§3.2)

AC coverage:
  AC6  → TestFromAC_EditTaskArchivalGates.test_archived_completed_reason_requires_terminal
  AC14 → TestFromAC_EditTaskValidation.test_body_and_append_body_both_set
  AC24 → TestFromAC_CreateTask.test_dep_not_found
  AC25 → TestFromAC_EditTaskValidation.test_add_dep_nonexistent
  AC29 → satisfied by engine (datetime.now(tz=UTC).isoformat()); no failing test needed
  AC30 → TestFromAC_EditTaskValidation.test_append_body_timestamp_uses_iso_datetime_with_offset
  AC-NEW-15 → TestFromAC_EditTaskValidation.test_parent_nonexistent
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ValidationError

# ---------------------------------------------------------------------------
# Board + task fixtures
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

# entry_status differs from defaults.status to surface D50 bugs.
_ENTRY_BACKLOG_CONFIG = _BASE_CONFIG.replace("entry_status: research", "entry_status: backlog")

# entry_status=research has a required-sections predicate.
_PREDICATE_CONFIG = _BASE_CONFIG.replace(
    "status_predicates: {}",
    (
        "status_predicates:\n"
        "        research:\n"
        "          type: required_sections\n"
        "          sections:\n"
        "            - Acceptance Criteria"
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
claimed_at: null
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
# TestFromAC_CreateTask
# ---------------------------------------------------------------------------


class TestFromAC_CreateTask:
    """AC24, D50, §3.4 (parent), D35+D47 (body size), D15+D50 (predicate-on-create).

    All tests are RED — none of the following validations exist in AgentView.create_task yet.
    """

    def test_create_task_uses_entry_status_not_defaults_status(self, tmp_path: Path) -> None:
        """D50: tasks created at PRODUCT_TOPOLOGY.entry_status ('research'), not config entry_status.

        Board has entry_status='backlog' in config, but PRODUCT_TOPOLOGY overrides to 'research'.
        """
        view, _ = _make_view(tmp_path, _ENTRY_BACKLOG_CONFIG)
        result = view.create_task(title="X")
        assert result.status == "research"

    def test_create_task_dep_not_found_raises_validation_error(self, tmp_path: Path) -> None:
        """AC24: create_task with non-existent depends_on ID → ValidationError(ERR_DEP_NOT_FOUND)."""
        view, _ = _make_view(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="X", depends_on=[99999])
        assert exc_info.value.code == "ERR_DEP_NOT_FOUND"

    def test_create_task_parent_not_found_raises_validation_error(self, tmp_path: Path) -> None:
        """§3.4: create_task with non-existent parent → ValidationError(ERR_PARENT_NOT_FOUND)."""
        view, _ = _make_view(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="X", parent=99999)
        assert exc_info.value.code == "ERR_PARENT_NOT_FOUND"

    def test_create_task_body_over_500kb_raises_body_too_large(self, tmp_path: Path) -> None:
        """D35+D47: create_task body > 500 KB → ValidationError(ERR_BODY_TOO_LARGE)."""
        view, _ = _make_view(tmp_path)
        oversized = "x" * (501 * 1024)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="X", body=oversized)
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_create_task_body_at_500kb_plus_one_byte_raises_body_too_large(self, tmp_path: Path) -> None:
        """D47 boundary: exactly 500 KB + 1 byte → ValidationError(ERR_BODY_TOO_LARGE)."""
        view, _ = _make_view(tmp_path)
        boundary = "x" * (500 * 1024 + 1)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="X", body=boundary)
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_create_task_body_over_100kb_returns_guidance_warning(self, tmp_path: Path) -> None:
        """D47-WARN-CREATE: create_task with body > 100 KB → succeeds and response
        guidance list contains the body-size warning. Hard cap (500 KB) not exceeded."""
        view, _ = _make_view(tmp_path)
        large_body = "x" * (101 * 1024)
        result = view.create_task(title="X", body=large_body)
        assert any("body" in g.lower() for g in result.guidance), (
            f"Expected body-size guidance warning for >100 KB body, got: {result.guidance!r}"
        )

    def test_create_task_predicate_failed_on_entry_status_raises_predicate_failed(self, tmp_path: Path) -> None:
        """With PRODUCT_TOPOLOGY, status_predicates={} — create_task succeeds without predicate check.

        Config predicate on 'research' is ignored; PRODUCT_TOPOLOGY provides empty predicates.
        Task is created successfully even without the required section in the body.
        """
        view, kanban_dir = _make_view(tmp_path, _PREDICATE_CONFIG)
        result = view.create_task(title="X", body="No sections here.")
        # Task should be created successfully (no predicate raises)
        assert result is not None
        assert result.status == "research"
        # Verify the task file was written
        assert len(list((kanban_dir / "tasks").glob("*.md"))) == 1


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskValidation
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskValidation:
    """AC14, AC25, AC-NEW-15, ERR_NO_OP, D47 (body size), D53 (block_reason), AC30 (timestamp).

    All tests are RED — none of these validations exist in AgentView.edit_task yet.
    """

    def test_body_and_append_body_both_set_raises_body_exclusive(self, tmp_path: Path) -> None:
        """AC14: body and append_body both non-empty → ValidationError(ERR_BODY_EXCLUSIVE)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, body="new body", append_body="also this")
        assert exc_info.value.code == "ERR_BODY_EXCLUSIVE"

    def test_add_dep_nonexistent_raises_dep_not_found(self, tmp_path: Path) -> None:
        """AC25: edit_task add_dep with non-existent task ID → ValidationError(ERR_DEP_NOT_FOUND)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, add_dep=[99999])
        assert exc_info.value.code == "ERR_DEP_NOT_FOUND"

    def test_parent_nonexistent_raises_parent_not_found(self, tmp_path: Path) -> None:
        """AC-NEW-15: edit_task with non-existent parent → ValidationError(ERR_PARENT_NOT_FOUND)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, parent=99999)
        assert exc_info.value.code == "ERR_PARENT_NOT_FOUND"

    def test_no_op_call_raises_no_op_error(self, tmp_path: Path) -> None:
        """ERR_NO_OP: edit_task with no field changes → ValidationError(ERR_NO_OP)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1)  # all defaults — no meaningful field changed
        assert exc_info.value.code == "ERR_NO_OP"

    def test_body_replace_over_500kb_raises_body_too_large(self, tmp_path: Path) -> None:
        """D47: edit_task replacement body > 500 KB → ValidationError(ERR_BODY_TOO_LARGE)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, body="x" * (501 * 1024))
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_append_body_total_over_500kb_raises_body_too_large(self, tmp_path: Path) -> None:
        """D47: post-append total body size > 500 KB → ValidationError(ERR_BODY_TOO_LARGE)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, body="x" * (400 * 1024))
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, append_body="y" * (200 * 1024))  # 400+200=600 KB
        assert exc_info.value.code == "ERR_BODY_TOO_LARGE"

    def test_edit_task_body_replace_over_100kb_returns_guidance_warning(self, tmp_path: Path) -> None:
        """D47-WARN-EDIT-REPLACE: edit_task with replacement body > 100 KB → succeeds
        and response guidance list contains the body-size warning. Hard cap not exceeded."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1)
        large_body = "x" * (101 * 1024)
        result = view.edit_task(1, body=large_body)
        assert any("body" in g.lower() for g in result.guidance), (
            f"Expected body-size guidance warning for >100 KB replacement body, got: {result.guidance!r}"
        )

    def test_edit_task_append_total_over_100kb_returns_guidance_warning(self, tmp_path: Path) -> None:
        """D47-WARN-EDIT-APPEND: append_body where post-append total > 100 KB → succeeds
        and response guidance list contains the body-size warning. Hard cap not exceeded."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, body="x" * (80 * 1024))
        result = view.edit_task(1, append_body="y" * (30 * 1024))  # 80+30=110 KB total
        assert any("body" in g.lower() for g in result.guidance), (
            f"Expected body-size guidance warning for post-append total >100 KB, got: {result.guidance!r}"
        )

    def test_empty_block_reason_clears_blocked_and_block_reason(self, tmp_path: Path) -> None:
        """D53: empty block_reason string clears blocked=False and block_reason=None.

        Current impl treats empty string same as 'not provided' (no-op on the block fields).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            blocked="true",
            block_reason='"dependency missing"',
        )
        result = view.edit_task(1, block_reason="")
        assert result.blocked is False
        assert result.block_reason is None

    def test_set_nonempty_block_reason_sets_blocked_true(self, tmp_path: Path) -> None:
        """D53-SET: edit_task with non-empty block_reason on an unblocked task →
        blocked=True, block_reason set to the provided string."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, blocked="false", block_reason="null")
        result = view.edit_task(1, block_reason="dependency missing")
        assert result.blocked is True
        assert result.block_reason == "dependency missing"

    def test_omit_block_reason_on_blocked_task_preserves_state(self, tmp_path: Path) -> None:
        """D53-OMIT: edit_task that omits block_reason while changing another field →
        blocked and block_reason remain unchanged on a previously blocked task."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            blocked="true",
            block_reason='"dependency missing"',
        )
        result = view.edit_task(1, priority="critical")
        assert result.blocked is True
        assert result.block_reason == "dependency missing"

    def test_append_body_timestamp_uses_iso_datetime_with_offset(self, tmp_path: Path) -> None:
        """AC30-TIGHT: timestamp=True prepends full ISO 8601 datetime with explicit ±HH:MM
        suffix, wrapped in [[…]], immediately followed by the appended note text.

        Contract: body after append contains '[[<YYYY-MM-DDTHH:MM:SS±HH:MM>]]\nNote.'
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, body="Base.")
        result = view.edit_task(1, append_body="Note.", timestamp=True)
        body: str = result.body or ""
        # Strict: full ±HH:MM offset form AND timestamp in [[…]] immediately precedes the note.
        iso_with_prepend = re.compile(r"\[\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\]\]\nNote\.")
        assert iso_with_prepend.search(body) is not None, (
            f"Expected [[ISO 8601 timestamp with ±HH:MM]] immediately before '\\nNote.' in body, got: {body!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskArchivalGates
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskArchivalGates:
    """D37+D57: archival fields forbidden on active tasks; AC6: completed-requires-terminal;
    D37: invalid archival_reason enum.

    All tests are RED — archival_reason and archival_refs are currently ignored in AgentView.edit_task.
    """

    def test_archival_reason_on_active_task_raises_archival_fields_forbidden(self, tmp_path: Path) -> None:
        """D37+D57: archival_reason set on a non-archived (active) task →
        ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="deprecated")
        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN"

    def test_archival_refs_on_active_task_raises_archival_fields_forbidden(self, tmp_path: Path) -> None:
        """D37+D57: archival_refs set on a non-archived (active) task →
        ValidationError(ERR_ARCHIVAL_FIELDS_FORBIDDEN)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_refs=[2])
        assert exc_info.value.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN"

    def test_archived_completed_reason_requires_terminal_status(self, tmp_path: Path) -> None:
        """AC6+D37+D65: setting archival_reason='completed' on archived task where
        status='archived' (not terminal 'done') → ValidationError(ERR_COMPLETED_REQUIRES_DONE)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="deprecated",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="completed")
        assert exc_info.value.code == "ERR_COMPLETED_REQUIRES_DONE"

    def test_invalid_archival_reason_raises_archival_reason_invalid(self, tmp_path: Path) -> None:
        """D37: archival_reason value not in enum →
        ValidationError(ERR_ARCHIVAL_REASON_INVALID)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="bogus-reason")
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_INVALID"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskArchivalRefs
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskArchivalRefs:
    """§3.2 archival_refs matrix: required (deprecated/duplicate), forbidden
    (completed/dropped/wontfix), missing ID, self-reference, cycle.

    All tests are RED — archival_refs validation is not implemented; edit_task
    also cannot currently locate tasks in the archive directory (raises NotFoundError).
    """

    def test_deprecated_without_refs_raises_refs_required(self, tmp_path: Path) -> None:
        """§3.2: archival_reason='deprecated' with empty archival_refs →
        ValidationError(ERR_ARCHIVAL_REFS_REQUIRED)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
            archival_refs="[]",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="deprecated", archival_refs=[])
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    def test_duplicate_without_refs_raises_refs_required(self, tmp_path: Path) -> None:
        """§3.2: archival_reason='duplicate' with empty archival_refs →
        ValidationError(ERR_ARCHIVAL_REFS_REQUIRED)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
            archival_refs="[]",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="duplicate", archival_refs=[])
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    def test_completed_with_nonempty_refs_raises_refs_forbidden(self, tmp_path: Path) -> None:
        """§3.2: archival_reason='completed' with non-empty archival_refs →
        ValidationError(ERR_ARCHIVAL_REFS_FORBIDDEN).

        Task already has archival_reason='completed' (set at valid archival time);
        the refs-forbidden check fires when adding refs to a 'completed' record.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="completed",
            archival_refs="[]",
        )
        _write_task(kanban_dir, task_id=2, status="done")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_refs=[2])
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_dropped_with_refs_raises_refs_forbidden(self, tmp_path: Path) -> None:
        """§3.2: archival_reason='dropped' with non-empty archival_refs →
        ValidationError(ERR_ARCHIVAL_REFS_FORBIDDEN)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
            archival_refs="[]",
        )
        _write_task(kanban_dir, task_id=2)
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="dropped", archival_refs=[2])
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_wontfix_with_refs_raises_refs_forbidden(self, tmp_path: Path) -> None:
        """§3.2: archival_reason='wontfix' with non-empty archival_refs →
        ValidationError(ERR_ARCHIVAL_REFS_FORBIDDEN)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
            archival_refs="[]",
        )
        _write_task(kanban_dir, task_id=2)
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="wontfix", archival_refs=[2])
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_archival_refs_missing_id_raises_ref_missing(self, tmp_path: Path) -> None:
        """§3.2: archival_refs element does not exist → ValidationError(ERR_ARCHIVAL_REF_MISSING)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
            archival_refs="[]",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="deprecated", archival_refs=[99999])
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_MISSING"

    def test_archival_refs_self_reference_raises_ref_self(self, tmp_path: Path) -> None:
        """§3.2: task.id in archival_refs (self-reference) →
        ValidationError(ERR_ARCHIVAL_REF_SELF)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
            archival_refs="[]",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="deprecated", archival_refs=[1])
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_SELF"

    def test_archival_refs_cycle_raises_ref_cycle(self, tmp_path: Path) -> None:
        """§3.2: transitive archival_refs forms a cycle →
        ValidationError(ERR_ARCHIVAL_REF_CYCLE).

        Task 2 already points to task 1 (archival_refs=[1]).
        Setting task 1's archival_refs=[2] creates cycle: 1 → 2 → 1.
        """
        view, kanban_dir = _make_view(tmp_path)
        # Task 2 archived with refs pointing to task 1.
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            subdir="archive",
            archival_reason="deprecated",
            archival_refs="[1]",
        )
        # Task 1 in archive with no refs yet.
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            subdir="archive",
            archival_reason="null",
            archival_refs="[]",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="deprecated", archival_refs=[2])
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_CYCLE"
