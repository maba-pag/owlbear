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
        """ShowTaskParams accepts task_id; section is optional."""
        from owlbear_mcp_kanban.models import ShowTaskParams

        p = ShowTaskParams(task_id=42)
        assert p.task_id == 42  # noqa: PLR2004
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

    def test_end_work_params_requires_task_id_note_outcome(self) -> None:
        """EndWorkParams requires task_id and note; outcome defaults to 'success'."""
        from owlbear_mcp_kanban.models import EndWorkParams

        with pytest.raises(ValidationError):
            EndWorkParams()  # type: ignore[call-arg]

    def test_end_work_params_valid_minimal(self) -> None:
        """EndWorkParams valid with task_id + note; outcome defaults."""
        from owlbear_mcp_kanban.models import EndWorkParams

        p = EndWorkParams(task_id=1, note="Done.")
        assert p.outcome == "success"

    def test_move_task_params_requires_task_id_and_status(self) -> None:
        """MoveTaskParams requires task_id and status."""
        from owlbear_mcp_kanban.models import MoveTaskParams

        with pytest.raises(ValidationError):
            MoveTaskParams(task_id=1)  # missing status

    def test_start_work_params_requires_task_id(self) -> None:
        """StartWorkParams requires task_id."""
        from owlbear_mcp_kanban.models import StartWorkParams

        with pytest.raises(ValidationError):
            StartWorkParams()  # type: ignore[call-arg]


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
            EditTaskParams(task_id=1, status="todo")  # type: ignore[call-arg]

    def test_edit_task_params_no_status_in_model_fields(self) -> None:
        """status is not declared in EditTaskParams.model_fields (AC13)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        assert "status" not in EditTaskParams.model_fields

    def test_edit_task_params_rejects_depends_on_field(self) -> None:
        """EditTaskParams rejects legacy depends_on (use add_dep/remove_dep)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises((ValidationError, TypeError)):
            EditTaskParams(task_id=1, depends_on="5")  # type: ignore[call-arg]

    def test_edit_task_params_rejects_tags_field(self) -> None:
        """EditTaskParams rejects legacy tags (use add_tag/remove_tag)."""
        from owlbear_mcp_kanban.models import EditTaskParams

        with pytest.raises((ValidationError, TypeError)):
            EditTaskParams(task_id=1, tags="foo,bar")  # type: ignore[call-arg]


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
            id=1, title="T", status="todo", priority="needed", depends_on=[]
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
