"""RED-phase tests for Brief B engine models and error hierarchy (task #1065).

Covers:
  - TaskSummary §2.1 full field contract (AC1)
  - TaskFull §2.2 field contract — extends TaskSummary (AC2)
  - DispatchEntry §2.3 + agent field per D24 (AC3)
  - Wave §2.4 — index int + tasks list[DispatchEntry] (AC4)
  - Response envelopes §2.5 (AC5)
  - No `file` field in any projection (AC16)
  - No `claimed_by` field; `claimed_at` + `claimed` present (AC17)
  - KanbanError subclasses carry code + user_message (§3.6 + D57)
  - Error code catalogue for all ERR_* codes from §1/§4 (D57)

All tests FAIL in RED phase: new types imported below do not yet exist in
owlbear_kanban.models — the import block raises ImportError at collection time.
"""

from __future__ import annotations

import pytest

from owlbear_kanban.models import (
    ConcurrencyError,
    ConfigError,
    DispatchEntry,
    KanbanError,
    ListTasksResponse,
    MigrationRequiredError,
    NotFoundError,
    PickTasksResponse,
    ShowTaskResponse,
    SingleTaskResponse,
    TaskFull,
    TaskSummary,
    ValidationError,
    Wave,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUMMARY_REQUIRED = {
    "id": 1,
    "title": "A task",
    "status": "todo",
    "priority": "needed",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
}


def _make_summary(**kwargs: object) -> TaskSummary:
    return TaskSummary(**{**_SUMMARY_REQUIRED, **kwargs})


def _make_full(**kwargs: object) -> TaskFull:
    return TaskFull(**{**_SUMMARY_REQUIRED, **kwargs})


def _make_dispatch(**kwargs: object) -> DispatchEntry:
    base = {
        "id": 1,
        "status": "todo",
        "priority": "needed",
        "title": "T",
        "tags": [],
        "agent": "builder",
    }
    return DispatchEntry(**{**base, **kwargs})


# ---------------------------------------------------------------------------
# AC1 — TaskSummary §2.1 field contract
# ---------------------------------------------------------------------------


class TestFromAC_TaskSummary:
    """AC1: TaskSummary has all §2.1 fields including computed claimed and dep_status."""

    def test_basic_fields_accepted(self) -> None:
        s = _make_summary()
        assert s.id == 1
        assert s.title == "A task"
        assert s.status == "todo"
        assert s.priority == "needed"

    def test_tags_defaults_to_empty_list(self) -> None:
        s = _make_summary()
        assert s.tags == []

    def test_parent_defaults_to_none(self) -> None:
        s = _make_summary()
        assert s.parent is None

    def test_depends_on_defaults_to_empty_list(self) -> None:
        s = _make_summary()
        assert s.depends_on == []

    def test_blocked_defaults_to_false(self) -> None:
        s = _make_summary()
        assert s.blocked is False

    def test_block_reason_defaults_to_none(self) -> None:
        s = _make_summary()
        assert s.block_reason is None

    # §2.1 fields missing from current TaskSummary implementation --

    def test_claimed_at_field_present_and_defaults_to_none(self) -> None:
        """AC1 + AC17: claimed_at is a first-class field on TaskSummary (§2.1, D11)."""
        s = _make_summary()
        assert s.claimed_at is None

    def test_claimed_at_accepts_iso8601_string(self) -> None:
        s = _make_summary(claimed_at="2026-04-01T10:00:00+00:00")
        assert s.claimed_at == "2026-04-01T10:00:00+00:00"

    def test_claimed_computed_true_when_claimed_at_set(self) -> None:
        """AC17: claimed is computed from claimed_at is not None."""
        s = _make_summary(claimed_at="2026-04-01T10:00:00+00:00")
        assert s.claimed is True

    def test_claimed_computed_false_when_claimed_at_none(self) -> None:
        s = _make_summary()
        assert s.claimed is False

    def test_archival_reason_field_present_and_defaults_to_none(self) -> None:
        """AC1: archival_reason included in TaskSummary per §2.1."""
        s = _make_summary()
        assert s.archival_reason is None

    def test_archival_reason_accepts_completed(self) -> None:
        s = _make_summary(archival_reason="completed")
        assert s.archival_reason == "completed"

    def test_archival_refs_field_present_and_defaults_to_empty(self) -> None:
        """AC1: archival_refs included in TaskSummary per §2.1."""
        s = _make_summary()
        assert s.archival_refs == []

    def test_archival_refs_accepts_list_of_int(self) -> None:
        s = _make_summary(archival_refs=[42, 99])
        assert s.archival_refs == [42, 99]

    def test_dep_status_field_present_and_defaults_to_none(self) -> None:
        """AC1: dep_status is a computed projection field on TaskSummary (D38 §2.1)."""
        s = _make_summary()
        assert s.dep_status is None

    def test_dep_status_accepts_ok(self) -> None:
        s = _make_summary(dep_status="ok")
        assert s.dep_status == "ok"

    def test_dep_status_accepts_redirect(self) -> None:
        s = _make_summary(dep_status="redirect")
        assert s.dep_status == "redirect"

    def test_dep_status_accepts_blocked(self) -> None:
        s = _make_summary(dep_status="blocked")
        assert s.dep_status == "blocked"

    def test_claimed_overridden_to_false_when_claimed_at_none(self) -> None:
        """AC1 polarity A: explicit claimed=True must be overridden when claimed_at is None."""
        s = _make_summary(claimed=True, claimed_at=None)
        assert s.claimed is False

    def test_claimed_overridden_to_true_when_claimed_at_set(self) -> None:
        """AC1 polarity B: explicit claimed=False must be overridden when claimed_at is present."""
        s = _make_summary(claimed=False, claimed_at="2026-04-01T10:00:00+00:00")
        assert s.claimed is True


# ---------------------------------------------------------------------------
# AC16 — No `file` field in projections
# ---------------------------------------------------------------------------


class TestFromAC_NoFileField:
    """AC16: No projection model includes a file field."""

    def test_task_summary_has_no_file_field(self) -> None:
        s = _make_summary()
        assert not hasattr(s, "file"), "TaskSummary must not expose a 'file' field"

    def test_task_full_has_no_file_field(self) -> None:
        f = _make_full()
        assert not hasattr(f, "file"), "TaskFull must not expose a 'file' field"

    def test_dispatch_entry_has_no_file_field(self) -> None:
        d = _make_dispatch()
        assert not hasattr(d, "file"), "DispatchEntry must not expose a 'file' field"


# ---------------------------------------------------------------------------
# AC17 — No claimed_by; claimed_at + claimed present
# ---------------------------------------------------------------------------


class TestFromAC_ClaimFields:
    """AC17: No claimed_by field; claimed_at + claimed present on projections."""

    def test_task_summary_has_no_claimed_by_in_model_fields(self) -> None:
        """claimed_by must not be a model field on TaskSummary (AC17)."""
        assert "claimed_by" not in TaskSummary.model_fields

    def test_task_summary_claimed_by_not_propagated_from_input(self) -> None:
        """claimed_by input is silently dropped; claimed derives from claimed_at."""
        s = TaskSummary(
            id=1,
            title="T",
            status="todo",
            priority="needed",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
            claimed_by="agent-x",
        )
        assert not hasattr(s, "claimed_by") or getattr(s, "claimed_by", _SENTINEL) is _SENTINEL
        # claimed should be derived from claimed_at, not claimed_by
        assert s.claimed is False

    def test_task_full_has_no_claimed_by_in_model_fields(self) -> None:
        assert "claimed_by" not in TaskFull.model_fields

    def test_task_summary_has_claimed_at_in_model_fields(self) -> None:
        assert "claimed_at" in TaskSummary.model_fields

    def test_task_full_has_claimed_at_in_model_fields(self) -> None:
        assert "claimed_at" in TaskFull.model_fields


_SENTINEL = object()


# ---------------------------------------------------------------------------
# AC2 — TaskFull §2.2 field contract
# ---------------------------------------------------------------------------


class TestFromAC_TaskFull:
    """AC2: TaskFull extends TaskSummary with created, updated, body per §2.2."""

    def test_task_full_is_task_summary_subclass(self) -> None:
        """AC2: TaskFull must inherit from TaskSummary, not just share fields."""
        assert issubclass(TaskFull, TaskSummary)

    def test_task_full_is_task_summary_subclass_or_has_all_summary_fields(self) -> None:
        """TaskFull must expose every field from TaskSummary (§2.2 'extends')."""
        summary_fields = set(TaskSummary.model_fields)
        full_fields = set(TaskFull.model_fields)
        missing = summary_fields - full_fields
        assert not missing, f"TaskFull missing inherited fields: {missing}"

    def test_task_full_has_created_field(self) -> None:
        assert "created" in TaskFull.model_fields

    def test_task_full_has_updated_field(self) -> None:
        assert "updated" in TaskFull.model_fields

    def test_task_full_has_body_field(self) -> None:
        assert "body" in TaskFull.model_fields

    def test_task_full_body_can_be_none(self) -> None:
        """body is str | None per D30 wire shape — None when section not matched."""
        f = _make_full(body=None)
        assert f.body is None

    def test_task_full_body_can_be_str(self) -> None:
        f = _make_full(body="## Section\n\nContent")
        assert f.body == "## Section\n\nContent"

    def test_task_full_created_and_updated_are_str(self) -> None:
        f = _make_full()
        assert isinstance(f.created, str)
        assert isinstance(f.updated, str)

    def test_task_full_carries_all_ac1_fields(self) -> None:
        """AC2 implies every §2.1 field appears on TaskFull (it extends TaskSummary)."""
        f = _make_full(
            claimed_at="2026-04-01T00:00:00+00:00",
            archival_reason="completed",
            archival_refs=[],
            dep_status="ok",
        )
        assert f.claimed_at == "2026-04-01T00:00:00+00:00"
        assert f.claimed is True
        assert f.archival_reason == "completed"
        assert f.dep_status == "ok"


# ---------------------------------------------------------------------------
# AC3 — DispatchEntry §2.3 + agent field (D24)
# ---------------------------------------------------------------------------


class TestFromAC_DispatchEntry:
    """AC3: DispatchEntry has agent field per §2.3 + D24."""

    def test_dispatch_entry_has_agent_field(self) -> None:
        """D24: agent is derived from BoardConfig.agent_map[task.status]."""
        assert "agent" in DispatchEntry.model_fields

    def test_dispatch_entry_agent_is_string(self) -> None:
        d = _make_dispatch(agent="builder")
        assert d.agent == "builder"

    def test_dispatch_entry_has_id(self) -> None:
        assert "id" in DispatchEntry.model_fields

    def test_dispatch_entry_has_status(self) -> None:
        assert "status" in DispatchEntry.model_fields

    def test_dispatch_entry_has_priority(self) -> None:
        assert "priority" in DispatchEntry.model_fields

    def test_dispatch_entry_has_title(self) -> None:
        assert "title" in DispatchEntry.model_fields

    def test_dispatch_entry_has_tags(self) -> None:
        assert "tags" in DispatchEntry.model_fields

    def test_dispatch_entry_tags_defaults_to_empty(self) -> None:
        d = DispatchEntry(id=1, status="todo", priority="needed", title="T", agent="builder")
        assert d.tags == []

    def test_dispatch_entry_round_trips(self) -> None:
        d = _make_dispatch(id=7, status="review", priority="critical", title="My task", tags=["x"])
        assert d.id == 7
        assert d.status == "review"
        assert d.priority == "critical"
        assert d.title == "My task"
        assert d.tags == ["x"]
        assert d.agent == "builder"


# ---------------------------------------------------------------------------
# AC4 — Wave §2.4
# ---------------------------------------------------------------------------


class TestFromAC_Wave:
    """AC4: Wave has index: int + tasks: list[DispatchEntry] per §2.4."""

    def test_wave_has_index_field(self) -> None:
        assert "index" in Wave.model_fields

    def test_wave_index_is_int(self) -> None:
        w = Wave(index=0, tasks=[])
        assert isinstance(w.index, int)
        assert w.index == 0

    def test_wave_has_tasks_field(self) -> None:
        assert "tasks" in Wave.model_fields

    def test_wave_tasks_defaults_to_empty_list(self) -> None:
        w = Wave(index=0)
        assert w.tasks == []

    def test_wave_tasks_accepts_dispatch_entries(self) -> None:
        d = _make_dispatch()
        w = Wave(index=1, tasks=[d])
        assert len(w.tasks) == 1
        assert w.tasks[0].agent == "builder"

    def test_wave_index_is_zero_based(self) -> None:
        """D42: Wave index is 0-based ordinal."""
        w0 = Wave(index=0, tasks=[])
        w1 = Wave(index=1, tasks=[])
        assert w0.index == 0
        assert w1.index == 1


# ---------------------------------------------------------------------------
# AC5 — Response envelopes §2.5
# ---------------------------------------------------------------------------


class TestFromAC_ResponseEnvelopes:
    """AC5: ListTasksResponse, ShowTaskResponse, PickTasksResponse, SingleTaskResponse per §2.5."""

    # ListTasksResponse
    def test_list_tasks_response_has_tasks(self) -> None:
        assert "tasks" in ListTasksResponse.model_fields

    def test_list_tasks_response_has_guidance(self) -> None:
        assert "guidance" in ListTasksResponse.model_fields

    def test_list_tasks_response_has_missing_ids(self) -> None:
        assert "missing_ids" in ListTasksResponse.model_fields

    def test_list_tasks_response_missing_ids_defaults_to_none(self) -> None:
        r = ListTasksResponse(tasks=[], guidance=[])
        assert r.missing_ids is None

    def test_list_tasks_response_tasks_is_list_of_task_summary(self) -> None:
        s = _make_summary()
        r = ListTasksResponse(tasks=[s], guidance=["hint"])
        assert len(r.tasks) == 1
        assert r.tasks[0].id == 1

    def test_list_tasks_response_missing_ids_accepts_list(self) -> None:
        r = ListTasksResponse(tasks=[], guidance=[], missing_ids=[5, 6])
        assert r.missing_ids == [5, 6]

    # ShowTaskResponse
    def test_show_task_response_has_missing_sections(self) -> None:
        assert "missing_sections" in ShowTaskResponse.model_fields

    def test_show_task_response_has_guidance(self) -> None:
        assert "guidance" in ShowTaskResponse.model_fields

    def test_show_task_response_has_task_full_fields(self) -> None:
        """ShowTaskResponse = TaskFull ⊕ {missing_sections, guidance} (§2.5)."""
        assert "id" in ShowTaskResponse.model_fields
        assert "body" in ShowTaskResponse.model_fields
        assert "created" in ShowTaskResponse.model_fields
        assert "updated" in ShowTaskResponse.model_fields

    def test_show_task_response_missing_sections_defaults_to_none(self) -> None:
        r = ShowTaskResponse(**{**_SUMMARY_REQUIRED, "guidance": []})
        assert r.missing_sections is None

    # PickTasksResponse
    def test_pick_tasks_response_has_waves(self) -> None:
        assert "waves" in PickTasksResponse.model_fields

    def test_pick_tasks_response_has_guidance(self) -> None:
        assert "guidance" in PickTasksResponse.model_fields

    def test_pick_tasks_response_waves_accepts_list_of_wave(self) -> None:
        w = Wave(index=0, tasks=[])
        r = PickTasksResponse(waves=[w], guidance=[])
        assert len(r.waves) == 1
        assert r.waves[0].index == 0

    def test_pick_tasks_response_waves_defaults_to_empty(self) -> None:
        r = PickTasksResponse(guidance=[])
        assert r.waves == []

    # SingleTaskResponse
    def test_single_task_response_has_guidance(self) -> None:
        assert "guidance" in SingleTaskResponse.model_fields

    def test_single_task_response_has_task_full_fields(self) -> None:
        """SingleTaskResponse = TaskFull ⊕ {guidance} (§2.5)."""
        assert "id" in SingleTaskResponse.model_fields
        assert "body" in SingleTaskResponse.model_fields
        assert "created" in SingleTaskResponse.model_fields
        assert "updated" in SingleTaskResponse.model_fields

    def test_single_task_response_guidance_defaults_to_empty(self) -> None:
        r = SingleTaskResponse(**_SUMMARY_REQUIRED)
        assert r.guidance == []


# ---------------------------------------------------------------------------
# KanbanError hierarchy — §3.6 + D57
# ---------------------------------------------------------------------------


class TestFromAC_KanbanErrorHierarchy:
    """KanbanError subclasses carry code: str and user_message: str per §3.6 + D57."""

    def test_kanban_error_has_code_attribute(self) -> None:
        e = KanbanError(code="ERR_NO_OP", user_message="test error")
        assert e.code == "ERR_NO_OP"

    def test_kanban_error_has_user_message_attribute(self) -> None:
        e = KanbanError(code="ERR_NO_OP", user_message="human readable")
        assert e.user_message == "human readable"

    def test_kanban_error_is_exception(self) -> None:
        assert issubclass(KanbanError, Exception)

    def test_kanban_error_str_is_user_message(self) -> None:
        e = KanbanError(code="ERR_NOT_FOUND", user_message="msg")
        assert str(e) == "msg"

    def test_validation_error_is_kanban_error(self) -> None:
        assert issubclass(ValidationError, KanbanError)

    def test_validation_error_has_code_and_user_message(self) -> None:
        e = ValidationError(code="ERR_NO_OP", user_message="no-op")
        assert e.code == "ERR_NO_OP"
        assert e.user_message == "no-op"

    def test_not_found_error_is_kanban_error(self) -> None:
        assert issubclass(NotFoundError, KanbanError)

    def test_not_found_error_has_code_and_user_message(self) -> None:
        e = NotFoundError(code="ERR_NOT_FOUND", user_message="task 42 not found")
        assert e.code == "ERR_NOT_FOUND"
        assert e.user_message == "task 42 not found"

    def test_concurrency_error_is_kanban_error(self) -> None:
        assert issubclass(ConcurrencyError, KanbanError)

    def test_concurrency_error_has_code_and_user_message(self) -> None:
        e = ConcurrencyError(code="ERR_STALE", user_message="stale version")
        assert e.code == "ERR_STALE"
        assert e.user_message == "stale version"

    def test_config_error_is_kanban_error(self) -> None:
        assert issubclass(ConfigError, KanbanError)

    def test_config_error_has_code_and_user_message(self) -> None:
        e = ConfigError(code="ERR_ENTRY_STATUS_INVALID", user_message="invalid entry status")
        assert e.code == "ERR_ENTRY_STATUS_INVALID"
        assert e.user_message == "invalid entry status"

    def test_migration_required_error_is_kanban_error(self) -> None:
        assert issubclass(MigrationRequiredError, KanbanError)

    def test_migration_required_error_has_code_and_user_message(self) -> None:
        e = MigrationRequiredError(code="ERR_MIGRATION_REQUIRED", user_message="migration required")
        assert e.code == "ERR_MIGRATION_REQUIRED"
        assert e.user_message == "migration required"

    def test_validation_error_is_not_not_found_error(self) -> None:
        """Distinct subclass: ValidationError and NotFoundError are siblings, not nested."""
        assert not issubclass(ValidationError, NotFoundError)
        assert not issubclass(NotFoundError, ValidationError)

    def test_kanban_error_is_raiseable(self) -> None:
        with pytest.raises(KanbanError) as exc_info:
            raise ValidationError(code="ERR_NO_OP", user_message="noop")
        assert exc_info.value.code == "ERR_NO_OP"

    def test_not_found_error_is_raiseable_as_kanban_error(self) -> None:
        with pytest.raises(KanbanError):
            raise NotFoundError(code="ERR_NOT_FOUND", user_message="not found")

    def test_unknown_code_raises_value_error(self) -> None:
        """Error code catalogue is frozen — unknown codes must be rejected."""
        with pytest.raises(ValueError, match="Unknown error code"):
            KanbanError(code="ERR_TOTALLY_UNKNOWN_XYZ", user_message="should fail")


# ---------------------------------------------------------------------------
# Error code catalogue — D57 ERR_* codes
# ---------------------------------------------------------------------------


class TestFromAC_ErrorCodeCatalogue:
    """Error code catalogue covers all ERR_* codes from §1 and §4 (D57)."""

    # ValidationError codes from §1 (tool validation)
    def test_err_not_claimed(self) -> None:
        e = ValidationError(code="ERR_NOT_CLAIMED", user_message="not claimed")
        assert e.code == "ERR_NOT_CLAIMED"

    def test_err_block_reason_required(self) -> None:
        e = ValidationError(code="ERR_BLOCK_REASON_REQUIRED", user_message="block_reason required")
        assert e.code == "ERR_BLOCK_REASON_REQUIRED"

    def test_err_no_op(self) -> None:
        e = ValidationError(code="ERR_NO_OP", user_message="no fields would change")
        assert e.code == "ERR_NO_OP"

    def test_err_body_exclusive(self) -> None:
        e = ValidationError(code="ERR_BODY_EXCLUSIVE", user_message="body exclusive")
        assert e.code == "ERR_BODY_EXCLUSIVE"

    def test_err_ids_exclusive(self) -> None:
        e = ValidationError(code="ERR_IDS_EXCLUSIVE", user_message="ids exclusive")
        assert e.code == "ERR_IDS_EXCLUSIVE"

    def test_err_section_empty(self) -> None:
        e = ValidationError(code="ERR_SECTION_EMPTY", user_message="section empty")
        assert e.code == "ERR_SECTION_EMPTY"

    def test_err_invalid_status(self) -> None:
        e = ValidationError(code="ERR_INVALID_STATUS", user_message="invalid status")
        assert e.code == "ERR_INVALID_STATUS"

    def test_err_invalid_priority(self) -> None:
        e = ValidationError(code="ERR_INVALID_PRIORITY", user_message="invalid priority")
        assert e.code == "ERR_INVALID_PRIORITY"

    def test_err_invalid_wave_param(self) -> None:
        e = ValidationError(code="ERR_INVALID_WAVE_PARAM", user_message="invalid wave param")
        assert e.code == "ERR_INVALID_WAVE_PARAM"

    def test_err_parent_not_found(self) -> None:
        e = ValidationError(code="ERR_PARENT_NOT_FOUND", user_message="parent not found")
        assert e.code == "ERR_PARENT_NOT_FOUND"

    def test_err_dep_not_found(self) -> None:
        e = ValidationError(code="ERR_DEP_NOT_FOUND", user_message="dep not found")
        assert e.code == "ERR_DEP_NOT_FOUND"

    def test_err_archival_reason_invalid(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_REASON_INVALID", user_message="invalid reason")
        assert e.code == "ERR_ARCHIVAL_REASON_INVALID"

    def test_err_archival_reason_required(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_REASON_REQUIRED", user_message="reason required")
        assert e.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    def test_err_archival_fields_forbidden(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_FIELDS_FORBIDDEN", user_message="archival forbidden")
        assert e.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN"

    def test_err_archival_refs_required(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_REFS_REQUIRED", user_message="refs required")
        assert e.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    def test_err_archival_refs_forbidden(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_REFS_FORBIDDEN", user_message="refs forbidden")
        assert e.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_err_archival_ref_missing(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_REF_MISSING", user_message="ref missing")
        assert e.code == "ERR_ARCHIVAL_REF_MISSING"

    def test_err_archival_ref_self(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_REF_SELF", user_message="self ref")
        assert e.code == "ERR_ARCHIVAL_REF_SELF"

    def test_err_archival_ref_cycle(self) -> None:
        e = ValidationError(code="ERR_ARCHIVAL_REF_CYCLE", user_message="cycle ref")
        assert e.code == "ERR_ARCHIVAL_REF_CYCLE"

    def test_err_completed_requires_done(self) -> None:
        e = ValidationError(code="ERR_COMPLETED_REQUIRES_DONE", user_message="completed requires done")
        assert e.code == "ERR_COMPLETED_REQUIRES_DONE"

    def test_err_invalid_outcome(self) -> None:
        e = ValidationError(code="ERR_INVALID_OUTCOME", user_message="invalid outcome")
        assert e.code == "ERR_INVALID_OUTCOME"

    def test_err_reject_requires_move_to(self) -> None:
        e = ValidationError(code="ERR_REJECT_REQUIRES_MOVE_TO", user_message="reject requires move_to")
        assert e.code == "ERR_REJECT_REQUIRES_MOVE_TO"

    def test_err_block_reason_forbidden_on_non_block(self) -> None:
        e = ValidationError(
            code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
            user_message="block_reason forbidden",
        )
        assert e.code == "ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK"

    def test_err_move_to_forbidden_on_success(self) -> None:
        e = ValidationError(code="ERR_MOVE_TO_FORBIDDEN_ON_SUCCESS", user_message="move_to forbidden")
        assert e.code == "ERR_MOVE_TO_FORBIDDEN_ON_SUCCESS"

    def test_err_move_to_forbidden_on_release(self) -> None:
        e = ValidationError(
            code="ERR_MOVE_TO_FORBIDDEN_ON_RELEASE",
            user_message="move_to forbidden on release",
        )
        assert e.code == "ERR_MOVE_TO_FORBIDDEN_ON_RELEASE"

    def test_err_archival_fields_forbidden_on_success(self) -> None:
        e = ValidationError(
            code="ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS",
            user_message="archival fields forbidden on success",
        )
        assert e.code == "ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS"

    def test_err_predicate_failed(self) -> None:
        e = ValidationError(code="ERR_PREDICATE_FAILED", user_message="predicate failed")
        assert e.code == "ERR_PREDICATE_FAILED"

    def test_err_archived_not_claimable(self) -> None:
        e = ValidationError(
            code="ERR_ARCHIVED_NOT_CLAIMABLE",
            user_message="archived task not claimable",
        )
        assert e.code == "ERR_ARCHIVED_NOT_CLAIMABLE"

    def test_err_blocked_not_claimable(self) -> None:
        e = ValidationError(code="ERR_BLOCKED_NOT_CLAIMABLE", user_message="blocked task not claimable")
        assert e.code == "ERR_BLOCKED_NOT_CLAIMABLE"

    def test_err_body_too_large(self) -> None:
        e = ValidationError(code="ERR_BODY_TOO_LARGE", user_message="body too large")
        assert e.code == "ERR_BODY_TOO_LARGE"

    # NotFoundError codes
    def test_err_not_found(self) -> None:
        e = NotFoundError(code="ERR_NOT_FOUND", user_message="task 1 not found")
        assert e.code == "ERR_NOT_FOUND"

    # ConcurrencyError codes
    def test_err_stale(self) -> None:
        e = ConcurrencyError(code="ERR_STALE", user_message="stale version")
        assert e.code == "ERR_STALE"

    def test_err_already_claimed(self) -> None:
        e = ConcurrencyError(code="ERR_ALREADY_CLAIMED", user_message="task already claimed")
        assert e.code == "ERR_ALREADY_CLAIMED"

    # ConfigError codes
    def test_err_entry_status_invalid(self) -> None:
        e = ConfigError(code="ERR_ENTRY_STATUS_INVALID", user_message="entry status invalid")
        assert e.code == "ERR_ENTRY_STATUS_INVALID"

    def test_err_invalid_claim_timeout(self) -> None:
        e = ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT", user_message="invalid claim timeout")
        assert e.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_err_terminal_status_invalid(self) -> None:
        e = ConfigError(code="ERR_TERMINAL_STATUS_INVALID", user_message="terminal status invalid")
        assert e.code == "ERR_TERMINAL_STATUS_INVALID"

    # MigrationRequiredError code
    def test_err_migration_required(self) -> None:
        e = MigrationRequiredError(code="ERR_MIGRATION_REQUIRED", user_message="migration required")
        assert e.code == "ERR_MIGRATION_REQUIRED"
