"""Failing tests for task #153: planner data models (TDD RED).

Covers the interface contract from AC:
  - Task model: roundtrip, class field alias, frozen, optional fields
  - DispatchEntry model: validation, frozen
  - DispatchPlan model: entries list, frozen
  - task_list_adapter: JSON array parsing, empty array

All tests FAIL in RED phase — ImportError expected until builder implements #144.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Import targets — will raise ImportError until builder implements #144 (RED)
# ---------------------------------------------------------------------------
from owlbear.planner.models import (  # type: ignore[import]
    DispatchEntry,
    DispatchPlan,
    Task,
    task_list_adapter,
)

# ---------------------------------------------------------------------------
# Canned kanban-md JSON fixtures (S3.1 schema, 15 fields each)
# ---------------------------------------------------------------------------

FULL_TASK_JSON: dict[str, Any] = {
    "id": 42,
    "title": "Implement feature",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T10:00:00+02:00",
    "updated": "2026-01-02T11:00:00+02:00",
    "started": "2026-01-03T09:00:00+02:00",
    "completed": "2026-01-04T17:00:00+02:00",
    "tags": ["phase-1", "type:build"],
    "depends_on": [10, 20],
    "claimed_by": "builder",
    "claimed_at": "2026-01-03T09:00:00+02:00",
    "class": "standard",
    "body": "## Acceptance Criteria\n- [ ] item",
    "file": "/kanban/tasks/42-implement-feature.md",
}

MINIMAL_TASK_JSON: dict[str, Any] = {
    "id": 1,
    "title": "Minimal task",
    "status": "backlog",
    "priority": "nice-to-have",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
    "tags": [],
    "depends_on": [],
    "class": "standard",
    "body": "",
    "file": "/kanban/tasks/1-minimal.md",
}


# ---------------------------------------------------------------------------
# TestFromAC_TaskModel
# ---------------------------------------------------------------------------


class TestFromAC_TaskModel:
    """Contract tests for Task Pydantic model derived from #153 AC."""

    def test_roundtrip_all_15_fields(self) -> None:
        """Task model round-trips all 15 fields from a complete kanban-md JSON object."""
        task = Task.model_validate(FULL_TASK_JSON)

        assert task.id == 42
        assert task.title == "Implement feature"
        assert task.status == "todo"
        assert task.priority == "important"
        assert task.created is not None
        assert task.updated is not None
        assert task.started is not None
        assert task.completed is not None
        assert task.tags == ["phase-1", "type:build"]
        assert task.depends_on == [10, 20]
        assert task.claimed_by == "builder"
        assert task.claimed_at is not None
        assert task.task_class == "standard"
        assert task.body == "## Acceptance Criteria\n- [ ] item"
        assert task.file == "/kanban/tasks/42-implement-feature.md"

    def test_class_field_alias_maps_to_task_class(self) -> None:
        """JSON key 'class' maps to the task_class attribute on the model."""
        task = Task.model_validate(FULL_TASK_JSON)
        assert task.task_class == "standard"

    def test_class_field_alias_via_model_validate_json(self) -> None:
        """Task.model_validate_json correctly maps JSON 'class' key to task_class."""
        payload = {**MINIMAL_TASK_JSON, "class": "urgent"}
        task = Task.model_validate_json(json.dumps(payload))
        assert task.task_class == "urgent"

    def test_frozen_raises_on_id_assignment(self) -> None:
        """Frozen model: assigning to id raises TypeError or ValidationError."""
        task = Task.model_validate(MINIMAL_TASK_JSON)
        with pytest.raises((TypeError, ValidationError)):
            task.id = 999  # type: ignore[misc]

    def test_frozen_raises_on_title_assignment(self) -> None:
        """Frozen model: assigning to title raises TypeError or ValidationError."""
        task = Task.model_validate(MINIMAL_TASK_JSON)
        with pytest.raises((TypeError, ValidationError)):
            task.title = "mutated"  # type: ignore[misc]

    def test_optional_fields_default_to_none_when_absent(self) -> None:
        """started, completed, claimed_by, claimed_at all default to None when absent."""
        task = Task.model_validate(MINIMAL_TASK_JSON)
        assert task.started is None
        assert task.completed is None
        assert task.claimed_by is None
        assert task.claimed_at is None

    def test_required_int_id_rejects_string(self) -> None:
        """Task raises ValidationError when id is a string instead of int."""
        bad = {**MINIMAL_TASK_JSON, "id": "not-an-int"}
        with pytest.raises(ValidationError):
            Task.model_validate(bad)

    def test_required_fields_missing_title_raises(self) -> None:
        """Task raises ValidationError when required field title is absent."""
        bad = {k: v for k, v in MINIMAL_TASK_JSON.items() if k != "title"}
        with pytest.raises(ValidationError):
            Task.model_validate(bad)


# ---------------------------------------------------------------------------
# TestFromAC_DispatchEntryModel
# ---------------------------------------------------------------------------


class TestFromAC_DispatchEntryModel:
    """Contract tests for DispatchEntry Pydantic model derived from #153 AC."""

    def test_dispatch_entry_valid_all_fields(self) -> None:
        """DispatchEntry validates task_id (int), agent (str), target_status (str)."""
        entry = DispatchEntry(task_id=42, agent="builder", target_status="in-progress")
        assert entry.task_id == 42
        assert entry.agent == "builder"
        assert entry.target_status == "in-progress"

    def test_dispatch_entry_frozen_raises_on_assignment(self) -> None:
        """DispatchEntry is frozen — assignment raises TypeError or ValidationError."""
        entry = DispatchEntry(task_id=1, agent="reviewer", target_status="review")
        with pytest.raises((TypeError, ValidationError)):
            entry.task_id = 999  # type: ignore[misc]

    def test_dispatch_entry_missing_agent_raises(self) -> None:
        """DispatchEntry raises when required field agent is missing."""
        with pytest.raises((ValidationError, TypeError)):
            DispatchEntry(task_id=1, target_status="in-progress")  # type: ignore[call-arg]

    def test_dispatch_entry_missing_task_id_raises(self) -> None:
        """DispatchEntry raises when required field task_id is missing."""
        with pytest.raises((ValidationError, TypeError)):
            DispatchEntry(agent="builder", target_status="in-progress")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestFromAC_DispatchPlanModel
# ---------------------------------------------------------------------------


class TestFromAC_DispatchPlanModel:
    """Contract tests for DispatchPlan Pydantic model derived from #153 AC."""

    def test_dispatch_plan_valid_entries_list(self) -> None:
        """DispatchPlan wraps a list of DispatchEntry objects."""
        entries = [
            DispatchEntry(task_id=1, agent="builder", target_status="in-progress"),
            DispatchEntry(task_id=2, agent="reviewer", target_status="review"),
        ]
        plan = DispatchPlan(entries=entries)
        assert len(plan.entries) == 2
        assert plan.entries[0].task_id == 1
        assert plan.entries[1].agent == "reviewer"

    def test_dispatch_plan_frozen_raises_on_assignment(self) -> None:
        """DispatchPlan is frozen — assignment raises TypeError or ValidationError."""
        plan = DispatchPlan(entries=[])
        with pytest.raises((TypeError, ValidationError)):
            plan.entries = []  # type: ignore[misc]

    def test_dispatch_plan_empty_entries_is_valid(self) -> None:
        """DispatchPlan with an empty entries list is valid."""
        plan = DispatchPlan(entries=[])
        assert plan.entries == []


# ---------------------------------------------------------------------------
# TestFromAC_TaskListAdapter
# ---------------------------------------------------------------------------


class TestFromAC_TaskListAdapter:
    """Contract tests for task_list_adapter TypeAdapter derived from #153 AC."""

    def test_adapter_parses_valid_json_array(self) -> None:
        """task_list_adapter.validate_json parses a single-task JSON array into list[Task]."""
        json_str = json.dumps([FULL_TASK_JSON])
        tasks = task_list_adapter.validate_json(json_str)
        assert len(tasks) == 1
        assert tasks[0].id == 42
        assert tasks[0].title == "Implement feature"

    def test_adapter_parses_multiple_tasks(self) -> None:
        """task_list_adapter parses a JSON array containing multiple Task objects."""
        json_str = json.dumps([FULL_TASK_JSON, MINIMAL_TASK_JSON])
        tasks = task_list_adapter.validate_json(json_str)
        assert len(tasks) == 2
        assert tasks[0].id == 42
        assert tasks[1].id == 1

    def test_adapter_parses_empty_array(self) -> None:
        """task_list_adapter.validate_json('[]') returns an empty list."""
        tasks = task_list_adapter.validate_json("[]")
        assert tasks == []

    def test_adapter_returns_list_of_task_instances(self) -> None:
        """task_list_adapter result contains Task instances (not plain dicts)."""
        json_str = json.dumps([MINIMAL_TASK_JSON])
        tasks = task_list_adapter.validate_json(json_str)
        assert isinstance(tasks[0], Task)
