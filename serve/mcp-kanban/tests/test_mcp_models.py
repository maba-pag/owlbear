"""RED phase tests — MCP boundary models (#1084).

Tests MCP-layer Pydantic input schemas for all 8 tools and verifies engine
projection types satisfy the Brief A §5-§6 contracts.

AC coverage:
- All 8 MCP tool input schemas exist in owlbear_mcp_kanban.models
- AC13: edit_task schema rejects status at adapter layer
- AC15: list_tasks schema rejects ids combined with other filter params
- AC16: No projection type includes a file field
- AC17: TaskSummary carries claimed_at + claimed; no claimed_by field
- Engine models carry archival_reason, archival_refs, dep_status on TaskSummary
- TaskFull, DispatchEntry, Wave importable from owlbear_kanban.models
- Response envelopes importable from owlbear_kanban.models
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# TestFromAC_MCPInputSchemas
# AC: Input schema for each of the 8 tools
# ---------------------------------------------------------------------------


class TestFromAC_MCPInputSchemas:
    """8 MCP tool parameter schemas exist and validate correctly."""

    def test_list_tasks_params_importable(self) -> None:
        """ListTasksParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import ListTasksParams  # noqa: F401

    def test_show_task_params_importable(self) -> None:
        """ShowTaskParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import ShowTaskParams  # noqa: F401

    def test_pick_tasks_params_importable(self) -> None:
        """PickTasksParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import PickTasksParams  # noqa: F401

    def test_create_task_params_importable(self) -> None:
        """CreateTaskParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import CreateTaskParams  # noqa: F401

    def test_edit_task_params_importable(self) -> None:
        """EditTaskParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import EditTaskParams  # noqa: F401

    def test_move_task_params_importable(self) -> None:
        """MoveTaskParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import MoveTaskParams  # noqa: F401

    def test_start_work_params_importable(self) -> None:
        """StartWorkParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import StartWorkParams  # noqa: F401

    def test_end_work_params_importable(self) -> None:
        """EndWorkParams exists in owlbear_mcp_kanban.models."""
        from owlbear_mcp_kanban.models import EndWorkParams  # noqa: F401

    def test_list_tasks_params_all_defaults(self) -> None:
        """ListTasksParams validates successfully with no arguments (all optional)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams()
        assert p.status is None
        assert p.tag is None
        assert p.priority is None
        assert p.ids is None

    def test_show_task_params_requires_task_id(self) -> None:
        """ShowTaskParams requires a task_id; missing it raises ValidationError."""
        from owlbear_mcp_kanban.models import ShowTaskParams

        with pytest.raises(ValidationError):
            ShowTaskParams()  # type: ignore[call-arg]

    def test_show_task_params_valid(self) -> None:
        """ShowTaskParams accepts canonical id; section is optional."""
        from owlbear_mcp_kanban.models import ShowTaskParams

        p = ShowTaskParams(id=42)
        assert p.id == 42  # noqa: PLR2004
        assert p.section is None

    def test_create_task_params_requires_title(self) -> None:
        """CreateTaskParams requires title; missing it raises ValidationError."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        with pytest.raises(ValidationError):
            CreateTaskParams()  # type: ignore[call-arg]

    def test_create_task_params_no_status_field(self) -> None:
        """CreateTaskParams has no status field (per paper-integration §1.4/D50)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        assert "status" not in CreateTaskParams.model_fields

    def test_end_work_params_requires_id(self) -> None:
        """EndWorkParams requires id; note is optional, outcome defaults to 'success'."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams()  # type: ignore[call-arg]

    def test_end_work_params_valid_minimal(self) -> None:
        """EndWorkParams valid with canonical id only; note optional, outcome defaults."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1)
        assert p.outcome == "success"

    def test_move_task_params_requires_id_and_status(self) -> None:
        """MoveTaskParams requires canonical id and status."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        with pytest.raises(ValidationError):
            MoveTaskParams(id=1)  # missing status

    def test_start_work_params_requires_task_id(self) -> None:
        """StartWorkParams requires task_id."""
        from owlbear_mcp_kanban.models import StartWorkParams

        with pytest.raises(ValidationError):
            StartWorkParams()  # type: ignore[call-arg]

    # --- Canonical id: task_id alias must be REJECTED (refined AC §5) ---

    def test_show_task_params_rejects_task_id(self) -> None:
        """ShowTaskParams must reject legacy task_id — canonical field is id (refined AC §5.2)."""
        from owlbear_mcp_kanban.models import ShowTaskParams

        with pytest.raises(ValidationError):
            ShowTaskParams(task_id=42)  # type: ignore[call-arg]

    def test_edit_task_params_rejects_task_id(self) -> None:
        """EditTaskParams must reject legacy task_id — canonical field is id (refined AC §5.5)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises(ValidationError):
            EditTaskParams(task_id=1)  # type: ignore[call-arg]

    def test_move_task_params_rejects_task_id(self) -> None:
        """MoveTaskParams must reject legacy task_id — canonical field is id (refined AC §5.6)."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        with pytest.raises(ValidationError):
            MoveTaskParams(task_id=1, status="todo")  # type: ignore[call-arg]

    def test_start_work_params_rejects_task_id(self) -> None:
        """StartWorkParams must reject legacy task_id — canonical field is id (refined AC §5.7)."""
        from owlbear_mcp_kanban.models import StartWorkParams

        with pytest.raises(ValidationError):
            StartWorkParams(task_id=1)  # type: ignore[call-arg]

    def test_end_work_params_rejects_task_id(self) -> None:
        """EndWorkParams must reject legacy task_id — canonical field is id (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams(task_id=1)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskNoStatusParam
# AC13: edit_task input schema does NOT accept status parameter
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskNoStatusParam:
    """AC13: EditTaskParams rejects status at the adapter/schema level."""

    def test_edit_task_params_rejects_status_field(self) -> None:
        """Passing status to EditTaskParams raises a ValidationError (AC13)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises((ValidationError, TypeError)):
            EditTaskParams(id=1, status="todo")  # type: ignore[call-arg]

    def test_edit_task_params_no_status_in_model_fields(self) -> None:
        """status is not declared in EditTaskParams.model_fields (AC13)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        assert "status" not in EditTaskParams.model_fields

    def test_edit_task_params_rejects_depends_on_field(self) -> None:
        """EditTaskParams rejects legacy depends_on (use add_dep/remove_dep)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises((ValidationError, TypeError)):
            EditTaskParams(id=1, depends_on="5")  # type: ignore[call-arg]

    def test_edit_task_params_rejects_tags_field(self) -> None:
        """EditTaskParams rejects legacy tags (use add_tag/remove_tag)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises((ValidationError, TypeError)):
            EditTaskParams(id=1, tags="foo,bar")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksIdsExclusivity
# AC15: list_tasks ids exclusive with other filter params at schema level
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksIdsExclusivity:
    """AC15: ids combined with other filter params is rejected at schema level."""

    def test_list_tasks_ids_alone_is_valid(self) -> None:
        """ids alone (no other filters) is valid."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams(ids=[1, 2, 3])
        assert p.ids == [1, 2, 3]

    def test_list_tasks_ids_with_status_raises(self) -> None:
        """ids combined with status raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], status="todo")

    def test_list_tasks_ids_with_tag_raises(self) -> None:
        """ids combined with tag raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], tag="phase:mcp")

    def test_list_tasks_ids_with_priority_raises(self) -> None:
        """ids combined with priority raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], priority="critical")

    def test_list_tasks_ids_with_search_raises(self) -> None:
        """ids combined with search raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], search="engine")

    def test_list_tasks_ids_with_unclaimed_raises(self) -> None:
        """ids combined with unclaimed raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], unclaimed=True)

    def test_list_tasks_ids_with_archival_reason_raises(self) -> None:
        """ids combined with archival_reason raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], archival_reason="deprecated")

    def test_list_tasks_ids_with_parent_raises(self) -> None:
        """ids combined with parent raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], parent=42)

    def test_list_tasks_ids_with_blocked_raises(self) -> None:
        """ids combined with blocked raises ValidationError (AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(ids=[1], blocked=True)


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksSchemaContract
# Refined AC §5.1: field plan, defaults, no archived, ids + display-modifier compat
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksSchemaContract:
    """Refined AC §5.1: ListTasksParams field contract — no archived, correct defaults,
    ids exclusivity limited to filter params (display modifiers are allowed)."""

    def test_list_tasks_no_archived_field(self) -> None:
        """ListTasksParams must NOT have an archived field (Brief A uses status='archived')."""
        from owlbear_mcp_kanban.models import ListTasksParams

        assert "archived" not in ListTasksParams.model_fields

    def test_list_tasks_rejects_archived_kwarg(self) -> None:
        """Passing archived=True to ListTasksParams raises ValidationError (extra=forbid)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        with pytest.raises(ValidationError):
            ListTasksParams(archived=True)  # type: ignore[call-arg]

    def test_list_tasks_unclaimed_defaults_false(self) -> None:
        """ListTasksParams.unclaimed defaults to False (refined AC §5.1)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams()
        assert p.unclaimed is False

    def test_list_tasks_limit_defaults_zero(self) -> None:
        """ListTasksParams.limit defaults to 0 (refined AC §5.1)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams()
        assert p.limit == 0

    def test_list_tasks_reverse_defaults_false(self) -> None:
        """ListTasksParams.reverse defaults to False (refined AC §5.1)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams()
        assert p.reverse is False

    def test_list_tasks_ids_allows_sort(self) -> None:
        """ids combined with sort (display modifier) is valid — not a filter (refined AC AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams(ids=[1, 2], sort="priority")
        assert p.ids == [1, 2]
        assert p.sort == "priority"

    def test_list_tasks_ids_allows_limit(self) -> None:
        """ids combined with limit (display modifier) is valid — not a filter (refined AC AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams(ids=[1, 2], limit=5)
        assert p.ids == [1, 2]
        assert p.limit == 5  # noqa: PLR2004

    def test_list_tasks_ids_allows_reverse(self) -> None:
        """ids combined with reverse (display modifier) is valid — not a filter (refined AC AC15)."""
        from owlbear_mcp_kanban.models import ListTasksParams

        p = ListTasksParams(ids=[1, 2], reverse=True)
        assert p.ids == [1, 2]
        assert p.reverse is True


# ---------------------------------------------------------------------------
# TestFromAC_NoFileInProjections
# AC16: No projection includes a file field
# ---------------------------------------------------------------------------


class TestFromAC_NoFileInProjections:
    """AC16: TaskFull and DispatchEntry projections carry no file field."""

    def test_task_full_no_file_field(self) -> None:
        """TaskFull.model_fields does not contain file (AC16)."""
        from owlbear_kanban.models import TaskFull

        assert "file" not in TaskFull.model_fields

    def test_dispatch_entry_no_file_field(self) -> None:
        """DispatchEntry.model_fields does not contain file (AC16)."""
        from owlbear_kanban.models import DispatchEntry

        assert "file" not in DispatchEntry.model_fields

    def test_task_summary_no_file_field(self) -> None:
        """TaskSummary.model_fields does not contain file (AC16 — refined)."""
        from owlbear_kanban.models import TaskSummary

        assert "file" not in TaskSummary.model_fields


# ---------------------------------------------------------------------------
# TestFromAC_ClaimFieldContracts
# AC17: No claimed_by in projections; claimed_at + claimed present
# ---------------------------------------------------------------------------


class TestFromAC_ClaimFieldContracts:
    """AC17: claimed_at and claimed present, claimed_by absent in projections."""

    def test_task_summary_has_claimed_at_field(self) -> None:
        """TaskSummary.model_fields contains claimed_at (AC17)."""
        from owlbear_kanban.models import TaskSummary

        assert "claimed_at" in TaskSummary.model_fields

    def test_task_full_no_claimed_by_field(self) -> None:
        """TaskFull.model_fields does not contain claimed_by (AC17)."""
        from owlbear_kanban.models import TaskFull

        assert "claimed_by" not in TaskFull.model_fields

    def test_task_summary_has_claimed_field(self) -> None:
        """TaskSummary.model_fields contains claimed (AC17 — refined)."""
        from owlbear_kanban.models import TaskSummary

        assert "claimed" in TaskSummary.model_fields

    def test_task_summary_no_claimed_by_field(self) -> None:
        """TaskSummary.model_fields does not contain claimed_by (AC17 — refined)."""
        from owlbear_kanban.models import TaskSummary

        assert "claimed_by" not in TaskSummary.model_fields


# ---------------------------------------------------------------------------
# TestFromAC_EngineSummaryProjectionFields
# §2.1: TaskSummary fields from paper-integration
# ---------------------------------------------------------------------------


class TestFromAC_EngineSummaryProjectionFields:
    """TaskSummary carries all §2.1 fields including archival + dep_status."""

    def test_task_summary_has_archival_reason(self) -> None:
        """TaskSummary has archival_reason field (§2.1)."""
        from owlbear_kanban.models import TaskSummary

        assert "archival_reason" in TaskSummary.model_fields

    def test_task_summary_has_archival_refs_int_list(self) -> None:
        """TaskSummary has archival_refs as list[int] (§2.1)."""
        from owlbear_kanban.models import TaskSummary

        assert "archival_refs" in TaskSummary.model_fields
        # Validate accepts list[int]
        s = TaskSummary(
            id=1,
            title="T",
            status="archived",
            priority="needed",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason="deprecated",
            archival_refs=[42, 99],
        )
        assert s.archival_refs == [42, 99]  # noqa: PLR2004

    def test_task_summary_has_dep_status(self) -> None:
        """TaskSummary has dep_status field (computed, §2.1 + D38)."""
        from owlbear_kanban.models import TaskSummary

        # dep_status must appear in model_fields or model_computed_fields
        all_fields = {**TaskSummary.model_fields, **TaskSummary.model_computed_fields}
        assert "dep_status" in all_fields

    def test_task_summary_dep_status_none_when_no_deps(self) -> None:
        """dep_status is None when depends_on is empty (D38)."""
        from owlbear_kanban.models import TaskSummary

        s = TaskSummary(
            id=1,
            title="T",
            status="todo",
            priority="needed",
            updated="2026-01-01T00:00:00+00:00",
            depends_on=[],
        )
        assert s.dep_status is None


# ---------------------------------------------------------------------------
# TestFromAC_TaskFullModel
# §2.2: TaskFull extends TaskSummary with created, updated, body
# ---------------------------------------------------------------------------


class TestFromAC_TaskFullModel:
    """TaskFull importable and has §2.2 fields."""

    def test_task_full_importable(self) -> None:
        """TaskFull is importable from owlbear_kanban.models."""
        from owlbear_kanban.models import TaskFull  # noqa: F401

    def test_task_full_has_created_updated_body(self) -> None:
        """TaskFull has created, updated, body fields (§2.2)."""
        from owlbear_kanban.models import TaskFull

        fields = TaskFull.model_fields
        assert "created" in fields
        assert "updated" in fields
        assert "body" in fields

    def test_task_full_body_optional(self) -> None:
        """TaskFull.body is str | None — None when section not found (§2.2)."""
        from owlbear_kanban.models import TaskFull

        # body=None must be valid (section not matched)
        t = TaskFull(
            id=1,
            title="T",
            status="todo",
            priority="needed",
            created="2026-04-22T00:00:00+00:00",
            updated="2026-04-22T00:00:00+00:00",
            body=None,
        )
        assert t.body is None


# ---------------------------------------------------------------------------
# TestFromAC_DispatchModels
# §2.3 DispatchEntry, §2.4 Wave
# ---------------------------------------------------------------------------


class TestFromAC_DispatchModels:
    """DispatchEntry and Wave importable with correct §2.3/§2.4 fields."""

    def test_dispatch_entry_importable(self) -> None:
        """DispatchEntry is importable from owlbear_kanban.models."""
        from owlbear_kanban.models import DispatchEntry  # noqa: F401

    def test_dispatch_entry_has_agent_field(self) -> None:
        """DispatchEntry has agent field (§2.3 + D24)."""
        from owlbear_kanban.models import DispatchEntry

        assert "agent" in DispatchEntry.model_fields

    def test_dispatch_entry_required_fields(self) -> None:
        """DispatchEntry has id, status, priority, title, tags, agent (§2.3)."""
        from owlbear_kanban.models import DispatchEntry

        fields = DispatchEntry.model_fields
        for name in ("id", "status", "priority", "title", "tags", "agent"):
            assert name in fields, f"DispatchEntry missing field: {name}"

    def test_wave_importable(self) -> None:
        """Wave is importable from owlbear_kanban.models."""
        from owlbear_kanban.models import Wave  # noqa: F401

    def test_wave_has_index_and_tasks(self) -> None:
        """Wave has index: int and tasks: list[DispatchEntry] (§2.4)."""
        from owlbear_kanban.models import Wave

        fields = Wave.model_fields
        assert "index" in fields
        assert "tasks" in fields


# ---------------------------------------------------------------------------
# TestFromAC_ResponseEnvelopes
# §2.5: Response envelopes importable from owlbear_kanban.models
# ---------------------------------------------------------------------------


class TestFromAC_ResponseEnvelopes:
    """All 4 response envelopes importable from engine models (§2.5)."""

    def test_list_tasks_response_importable(self) -> None:
        """ListTasksResponse importable from owlbear_kanban.models."""
        from owlbear_kanban.models import ListTasksResponse  # noqa: F401

    def test_show_task_response_importable(self) -> None:
        """ShowTaskResponse importable from owlbear_kanban.models."""
        from owlbear_kanban.models import ShowTaskResponse  # noqa: F401

    def test_pick_tasks_response_importable(self) -> None:
        """PickTasksResponse importable from owlbear_kanban.models."""
        from owlbear_kanban.models import PickTasksResponse  # noqa: F401

    def test_single_task_response_importable(self) -> None:
        """SingleTaskResponse importable from owlbear_kanban.models."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: F401

    def test_list_tasks_response_fields(self) -> None:
        """ListTasksResponse has tasks, missing_ids, guidance (§2.5)."""
        from owlbear_kanban.models import ListTasksResponse

        fields = ListTasksResponse.model_fields
        assert "tasks" in fields
        assert "guidance" in fields
        # missing_ids present (None when ids arg not used)
        assert "missing_ids" in fields

    def test_show_task_response_has_missing_sections(self) -> None:
        """ShowTaskResponse has missing_sections field (§2.5 + D56)."""
        from owlbear_kanban.models import ShowTaskResponse

        assert "missing_sections" in ShowTaskResponse.model_fields

    def test_pick_tasks_response_has_waves_and_guidance(self) -> None:
        """PickTasksResponse has waves and guidance (§2.5)."""
        from owlbear_kanban.models import PickTasksResponse

        fields = PickTasksResponse.model_fields
        assert "waves" in fields
        assert "guidance" in fields

    def test_single_task_response_has_guidance(self) -> None:
        """SingleTaskResponse has guidance field (§2.5)."""
        from owlbear_kanban.models import SingleTaskResponse

        assert "guidance" in SingleTaskResponse.model_fields


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksContract
# Refined AC §5.3: PickTasksParams field plan, types, defaults
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksContract:
    """Refined AC §5.3: PickTasksParams has wave_size and max_waves with correct defaults."""

    def test_pick_tasks_has_wave_size_field(self) -> None:
        """PickTasksParams has wave_size field (refined AC §5.3)."""
        from owlbear_mcp_kanban.models import PickTasksParams

        assert "wave_size" in PickTasksParams.model_fields

    def test_pick_tasks_wave_size_defaults_none(self) -> None:
        """PickTasksParams.wave_size defaults to None (refined AC §5.3)."""
        from owlbear_mcp_kanban.models import PickTasksParams

        p = PickTasksParams()
        assert p.wave_size is None

    def test_pick_tasks_has_max_waves_field(self) -> None:
        """PickTasksParams has max_waves field (refined AC §5.3)."""
        from owlbear_mcp_kanban.models import PickTasksParams

        assert "max_waves" in PickTasksParams.model_fields

    def test_pick_tasks_max_waves_defaults_three(self) -> None:
        """PickTasksParams.max_waves defaults to 3 (refined AC §5.3)."""
        from owlbear_mcp_kanban.models import PickTasksParams

        p = PickTasksParams()
        assert p.max_waves == 3  # noqa: PLR2004

    def test_pick_tasks_accepts_explicit_wave_size(self) -> None:
        """PickTasksParams accepts explicit wave_size (refined AC §5.3)."""
        from owlbear_mcp_kanban.models import PickTasksParams

        p = PickTasksParams(wave_size=5)
        assert p.wave_size == 5  # noqa: PLR2004

    def test_pick_tasks_accepts_explicit_max_waves(self) -> None:
        """PickTasksParams accepts explicit max_waves (refined AC §5.3)."""
        from owlbear_mcp_kanban.models import PickTasksParams

        p = PickTasksParams(max_waves=2)
        assert p.max_waves == 2  # noqa: PLR2004

    def test_pick_tasks_rejects_legacy_limit_and_tag(self) -> None:
        """PickTasksParams rejects legacy limit and tag fields (extra=forbid; refined AC §5.3)."""
        from owlbear_mcp_kanban.models import PickTasksParams

        with pytest.raises(ValidationError):
            PickTasksParams(limit=10, tag="backlog")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskContract
# Refined AC §5.4: CreateTaskParams field shapes, types, defaults
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskContract:
    """Refined AC §5.4: CreateTaskParams body, priority, tags, depends_on, parent defaults."""

    def test_create_task_body_defaults_empty(self) -> None:
        """CreateTaskParams.body defaults to empty string (refined AC §5.4)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        p = CreateTaskParams(title="T")
        assert p.body == ""

    def test_create_task_priority_defaults_needed(self) -> None:
        """CreateTaskParams.priority defaults to 'needed' (refined AC §5.4)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        p = CreateTaskParams(title="T")
        assert p.priority == "needed"

    def test_create_task_tags_defaults_none(self) -> None:
        """CreateTaskParams.tags defaults to None (refined AC §5.4)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        p = CreateTaskParams(title="T")
        assert p.tags is None

    def test_create_task_tags_accepts_list_of_str(self) -> None:
        """CreateTaskParams.tags accepts list[str] (refined AC §5.4)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        p = CreateTaskParams(title="T", tags=["foo", "bar"])
        assert p.tags == ["foo", "bar"]

    def test_create_task_depends_on_defaults_none(self) -> None:
        """CreateTaskParams.depends_on defaults to None (refined AC §5.4)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        p = CreateTaskParams(title="T")
        assert p.depends_on is None

    def test_create_task_depends_on_accepts_list_of_int(self) -> None:
        """CreateTaskParams.depends_on accepts list[int] (refined AC §5.4)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        p = CreateTaskParams(title="T", depends_on=[10, 20])
        assert p.depends_on == [10, 20]  # noqa: PLR2004

    def test_create_task_parent_defaults_none(self) -> None:
        """CreateTaskParams.parent defaults to None (refined AC §5.4)."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        p = CreateTaskParams(title="T")
        assert p.parent is None


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkParamsContract
# Refined AC §5.8: EndWorkParams outcome literals, archival/block fields
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkParamsContract:
    """Refined AC §5.8: EndWorkParams outcome set includes 'release', archival/block fields present."""

    def test_end_work_outcome_accepts_success(self) -> None:
        """EndWorkParams accepts outcome='success' (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, outcome="success")
        assert p.outcome == "success"

    def test_end_work_outcome_accepts_release(self) -> None:
        """EndWorkParams accepts outcome='release' (refined AC §5.8 — literal must include release)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, outcome="release")
        assert p.outcome == "release"

    def test_end_work_outcome_accepts_reject(self) -> None:
        """EndWorkParams accepts outcome='reject' (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, outcome="reject")
        assert p.outcome == "reject"

    def test_end_work_outcome_accepts_block(self) -> None:
        """EndWorkParams accepts outcome='block' (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, outcome="block")
        assert p.outcome == "block"

    def test_end_work_outcome_rejects_invalid_literal(self) -> None:
        """EndWorkParams rejects invalid outcome literals (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams(id=1, outcome="retry")  # type: ignore[arg-type]

    def test_end_work_has_archival_reason_field(self) -> None:
        """EndWorkParams has archival_reason field (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        assert "archival_reason" in EndWorkParams.model_fields

    def test_end_work_has_archival_refs_field(self) -> None:
        """EndWorkParams has archival_refs field (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        assert "archival_refs" in EndWorkParams.model_fields

    def test_end_work_archival_refs_accepts_list_of_int(self) -> None:
        """EndWorkParams.archival_refs accepts list[int] (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, archival_refs=[42, 99])
        assert p.archival_refs == [42, 99]  # noqa: PLR2004

    def test_end_work_has_block_reason_field(self) -> None:
        """EndWorkParams has block_reason field (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        assert "block_reason" in EndWorkParams.model_fields

    def test_end_work_has_move_to_field(self) -> None:
        """EndWorkParams has move_to field (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        assert "move_to" in EndWorkParams.model_fields

    def test_end_work_note_defaults_none(self) -> None:
        """EndWorkParams.note defaults to None — not required (refined AC §5.8)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1)
        assert p.note is None


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskContract
# Refined AC §5.6: MoveTaskParams id, status, archival fields
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskContract:
    """Refined AC §5.6: MoveTaskParams field coverage including archival fields."""

    def test_move_task_has_status_field(self) -> None:
        """MoveTaskParams has status field (refined AC §5.6)."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        assert "status" in MoveTaskParams.model_fields

    def test_move_task_valid_minimal(self) -> None:
        """MoveTaskParams accepts id and status; archival fields optional."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        p = MoveTaskParams(id=1, status="done")
        assert p.id == 1  # noqa: PLR2004
        assert p.status == "done"
        assert p.archival_reason is None
        assert p.archival_refs is None

    def test_move_task_has_archival_reason(self) -> None:
        """MoveTaskParams has optional archival_reason field (refined AC §5.6)."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        assert "archival_reason" in MoveTaskParams.model_fields

    def test_move_task_has_archival_refs(self) -> None:
        """MoveTaskParams has optional archival_refs field (refined AC §5.6)."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        assert "archival_refs" in MoveTaskParams.model_fields

    def test_move_task_archival_refs_accepts_list_of_int(self) -> None:
        """MoveTaskParams.archival_refs accepts list[int] (refined AC §5.6)."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        p = MoveTaskParams(id=1, status="archived", archival_refs=[10, 20])
        assert p.archival_refs == [10, 20]  # noqa: PLR2004


# ---------------------------------------------------------------------------
# TestFromAC_ExactFieldSets
# Loop-breaker closure (arch-review 2026-04-24): exact model_fields key-set
# assertions for all 8 *Params models — proves no missing AND no extra fields.
# ---------------------------------------------------------------------------


class TestFromAC_ExactFieldSets:
    """Exact model_fields key-set for all 8 MCP param schemas (loop-breaker closure)."""

    def test_list_tasks_params_exact_fields(self) -> None:
        """ListTasksParams has exactly the Brief A §5.1 field set — no more, no less."""
        from owlbear_mcp_kanban.models import ListTasksParams

        assert set(ListTasksParams.model_fields.keys()) == {
            "status",
            "tag",
            "priority",
            "archival_reason",
            "parent",
            "search",
            "sort",
            "unclaimed",
            "limit",
            "reverse",
            "blocked",
            "ids",
        }

    def test_show_task_params_exact_fields(self) -> None:
        """ShowTaskParams has exactly the Brief A §5.2 field set: id and section."""
        from owlbear_mcp_kanban.models import ShowTaskParams

        assert set(ShowTaskParams.model_fields.keys()) == {"id", "section"}

    def test_pick_tasks_params_exact_fields(self) -> None:
        """PickTasksParams has exactly the Brief A §5.3 field set: wave_size and max_waves."""
        from owlbear_mcp_kanban.models import PickTasksParams

        assert set(PickTasksParams.model_fields.keys()) == {"wave_size", "max_waves"}

    def test_create_task_params_exact_fields(self) -> None:
        """CreateTaskParams has exactly the Brief A §5.4 field set."""
        from owlbear_mcp_kanban.models import CreateTaskParams

        assert set(CreateTaskParams.model_fields.keys()) == {
            "title",
            "body",
            "priority",
            "tags",
            "parent",
            "depends_on",
        }

    def test_edit_task_params_exact_fields(self) -> None:
        """EditTaskParams has exactly the Brief A §5.5 field set — no status, no task_id."""
        from owlbear_mcp_kanban.models import EditTaskParams

        assert set(EditTaskParams.model_fields.keys()) == {
            "id",
            "title",
            "body",
            "append_body",
            "timestamp",
            "priority",
            "parent",
            "add_dep",
            "remove_dep",
            "add_tag",
            "remove_tag",
            "block_reason",
            "archival_reason",
            "archival_refs",
        }

    def test_move_task_params_exact_fields(self) -> None:
        """MoveTaskParams has exactly the Brief A §5.6 field set."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        assert set(MoveTaskParams.model_fields.keys()) == {
            "id",
            "status",
            "archival_reason",
            "archival_refs",
        }

    def test_start_work_params_exact_fields(self) -> None:
        """StartWorkParams has exactly the Brief A §5.7 field set: id only."""
        from owlbear_mcp_kanban.models import StartWorkParams

        assert set(StartWorkParams.model_fields.keys()) == {"id"}

    def test_end_work_params_exact_fields(self) -> None:
        """EndWorkParams has exactly the Brief A §5.8 field set."""
        from owlbear_mcp_kanban.models import EndWorkParams

        assert set(EndWorkParams.model_fields.keys()) == {
            "id",
            "outcome",
            "move_to",
            "note",
            "archival_reason",
            "archival_refs",
            "block_reason",
        }


# ---------------------------------------------------------------------------
# TestFromAC_AC13Exact
# Loop-breaker closure (arch-review 2026-04-24): AC13 tests narrowed to
# pytest.raises(ValidationError) only — extra="forbid" always raises
# ValidationError, never TypeError.
# ---------------------------------------------------------------------------


class TestFromAC_AC13Exact:
    """AC13 proof using only ValidationError — schema-layer rejection via extra=forbid."""

    def test_edit_task_status_raises_validation_error_not_type_error(self) -> None:
        """EditTaskParams(status=...) raises ValidationError specifically (AC13 exact)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises(ValidationError):
            EditTaskParams(id=1, status="todo")  # type: ignore[call-arg]

    def test_edit_task_depends_on_raises_validation_error_not_type_error(self) -> None:
        """EditTaskParams(depends_on=...) raises ValidationError specifically (AC13 exact)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises(ValidationError):
            EditTaskParams(id=1, depends_on="5")  # type: ignore[call-arg]

    def test_edit_task_tags_raises_validation_error_not_type_error(self) -> None:
        """EditTaskParams(tags=...) raises ValidationError specifically (AC13 exact)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises(ValidationError):
            EditTaskParams(id=1, tags="foo,bar")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkStringFieldContracts
# Retry strengthening (#1085): positive construction + strict-mode annotation
# proofs for EndWorkParams string fields per Brief A §5.8 wire contract.
# move_to, note, block_reason, archival_reason — typed str | None.
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkStringFieldContracts:
    """Brief A §5.8 wire contract: EndWorkParams string fields accept str and store correctly."""

    def test_end_work_move_to_accepts_string_value(self) -> None:
        """EndWorkParams.move_to accepts a str value and stores it (§5.8 annotation proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, outcome="reject", move_to="backlog")
        assert p.move_to == "backlog"
        assert isinstance(p.move_to, str)

    def test_end_work_note_accepts_string_value(self) -> None:
        """EndWorkParams.note accepts a str value and stores it (§5.8 annotation proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, note="Task completed with no issues.")
        assert p.note == "Task completed with no issues."
        assert isinstance(p.note, str)

    def test_end_work_block_reason_accepts_string_value(self) -> None:
        """EndWorkParams.block_reason accepts a str value and stores it (§5.8 annotation proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(id=1, outcome="block", block_reason="Waiting for dependency resolution.")
        assert p.block_reason == "Waiting for dependency resolution."
        assert isinstance(p.block_reason, str)

    def test_end_work_archival_reason_accepts_string_value(self) -> None:
        """EndWorkParams.archival_reason accepts a str value and stores it (§5.8 annotation proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(
            id=1,
            outcome="reject",
            move_to="archived",
            archival_reason="Superseded by #999.",
        )
        assert p.archival_reason == "Superseded by #999."
        assert isinstance(p.archival_reason, str)

    def test_end_work_move_to_strict_mode_accepts_str(self) -> None:
        """move_to annotation is str | None: strict mode accepts str (annotation plan proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams.model_validate({"id": 1, "outcome": "reject", "move_to": "todo"}, strict=True)
        assert p.move_to == "todo"

    def test_end_work_note_strict_mode_accepts_str(self) -> None:
        """note annotation is str | None: strict mode accepts str (annotation plan proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams.model_validate({"id": 1, "note": "some note"}, strict=True)
        assert p.note == "some note"

    def test_end_work_block_reason_strict_mode_accepts_str(self) -> None:
        """block_reason annotation is str | None: strict mode accepts str (annotation plan proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams.model_validate(
            {"id": 1, "outcome": "block", "block_reason": "blocked because"},
            strict=True,
        )
        assert p.block_reason == "blocked because"

    def test_end_work_archival_reason_strict_mode_accepts_str(self) -> None:
        """archival_reason annotation is str | None: strict mode accepts str (annotation plan proof)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams.model_validate(
            {
                "id": 1,
                "outcome": "reject",
                "move_to": "archived",
                "archival_reason": "done",
            },
            strict=True,
        )
        assert p.archival_reason == "done"

    def test_end_work_move_to_strict_mode_rejects_int(self) -> None:
        """move_to annotation is str | None: strict mode rejects int (annotation drift guard)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams.model_validate({"id": 1, "move_to": 42}, strict=True)

    def test_end_work_note_strict_mode_rejects_int(self) -> None:
        """note annotation is str | None: strict mode rejects int (annotation drift guard)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams.model_validate({"id": 1, "note": 42}, strict=True)

    def test_end_work_block_reason_strict_mode_rejects_int(self) -> None:
        """block_reason annotation is str | None: strict mode rejects int (annotation drift guard)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams.model_validate({"id": 1, "block_reason": 42}, strict=True)

    def test_end_work_archival_reason_strict_mode_rejects_int(self) -> None:
        """archival_reason annotation is str | None: strict mode rejects int (annotation drift guard)."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams.model_validate({"id": 1, "archival_reason": 42}, strict=True)
