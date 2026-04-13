"""RED tests — TaskSummary model (task #801).

AC coverage:
  AC1 - TaskSummary schema includes: id, title, status, priority, tags, blocked,
        block_reason, claimed (bool), parent, depends_on  (10 fields)
  AC2 - TaskSummary excludes:  body, created, updated, claimed_by, claimed_at, file
  AC3 - list_tasks returns TaskSummary projections instead of hand-built dicts
  AC4 - TaskSummary can be constructed from a Task instance

All tests FAIL in RED phase — TaskSummary is missing block_reason, claimed (bool),
parent, depends_on and still has claimed_by; extra="allow" lets excluded fields
leak through; list_tasks return type annotation is still list[dict].
"""

from __future__ import annotations

import inspect
import typing

from owlbear_kanban.models import Task, TaskSummary

# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

_MINIMAL_TASK_DATA: dict = {
    "id": 10,
    "title": "Sample task",
    "status": "todo",
    "priority": "important",
    "created": "2026-04-10T10:00:00+00:00",
    "updated": "2026-04-10T11:00:00+00:00",
    "body": "Some body text that must not leak into summaries.",
}

_FULL_TASK_DATA: dict = {
    **_MINIMAL_TASK_DATA,
    "tags": ["phase-1", "type:test"],
    "parent": 5,
    "depends_on": [8, 9],
    "blocked": True,
    "block_reason": "Waiting on upstream fix",
    "claimed_by": "builder-agent",
    "claimed_at": "2026-04-10T10:30:00+00:00",
    "file": "tasks/0010-sample-task.md",
}

_INCLUSION_FIELDS: frozenset[str] = frozenset({
    "id",
    "title",
    "status",
    "priority",
    "tags",
    "blocked",
    "block_reason",
    "claimed",
    "parent",
    "depends_on",
})

_EXCLUSION_FIELDS: frozenset[str] = frozenset({
    "body",
    "created",
    "updated",
    "claimed_by",
    "claimed_at",
    "file",
})


# ---------------------------------------------------------------------------
# AC1 — TaskSummary schema includes the 10 required fields
# ---------------------------------------------------------------------------


class TestFromAC_TaskSummarySchema:
    """AC1: TaskSummary has exactly the 10 fields specified in AC."""

    def test_inclusion_fields_all_present(self) -> None:
        """All 10 inclusion fields are declared in TaskSummary.model_fields."""
        missing = _INCLUSION_FIELDS - set(TaskSummary.model_fields)
        assert missing == set(), (
            f"TaskSummary.model_fields is missing required fields: {missing}"
        )

    def test_claimed_is_bool_not_optional_string(self) -> None:
        """claimed field annotation must be bool, not str | None or claimed_by-style string."""
        assert "claimed" in TaskSummary.model_fields, (
            "TaskSummary must have a 'claimed' field (bool), not 'claimed_by' (str)"
        )
        field_info = TaskSummary.model_fields["claimed"]
        annotation = field_info.annotation
        # Accept bare bool; reject any Optional[str], str, or NoneType.
        assert annotation is bool, (
            f"TaskSummary.claimed annotation must be bool, got {annotation!r}"
        )

    def test_block_reason_field_present(self) -> None:
        """block_reason must be a declared field in TaskSummary (currently absent)."""
        assert "block_reason" in TaskSummary.model_fields, (
            "TaskSummary.block_reason field is missing — AC requires it"
        )

    def test_parent_field_present(self) -> None:
        """parent must be a declared field in TaskSummary (currently absent)."""
        assert "parent" in TaskSummary.model_fields, (
            "TaskSummary.parent field is missing — AC requires it"
        )

    def test_depends_on_field_present(self) -> None:
        """depends_on must be a declared field in TaskSummary (currently absent)."""
        assert "depends_on" in TaskSummary.model_fields, (
            "TaskSummary.depends_on field is missing — AC requires it"
        )


# ---------------------------------------------------------------------------
# AC2 — TaskSummary excludes the 6 forbidden fields
# ---------------------------------------------------------------------------


class TestFromAC_TaskSummaryExcludes:
    """AC2: TaskSummary must NOT contain body, created, updated, claimed_by, claimed_at, file."""

    def test_excluded_fields_absent_from_schema(self) -> None:
        """All 6 exclusion fields are absent from TaskSummary.model_fields."""
        present = _EXCLUSION_FIELDS & set(TaskSummary.model_fields)
        assert present == set(), (
            f"TaskSummary.model_fields must not include: {present}"
        )

    def test_claimed_by_not_in_schema(self) -> None:
        """claimed_by (str) must NOT appear in TaskSummary — replaced by claimed (bool)."""
        assert "claimed_by" not in TaskSummary.model_fields, (
            "TaskSummary still has 'claimed_by' — it must be replaced by 'claimed: bool'"
        )

    def test_body_not_in_construction_output(self) -> None:
        """Constructing TaskSummary from full task data must not include body in output."""
        summary = TaskSummary.model_validate(_FULL_TASK_DATA)
        dumped = summary.model_dump()
        assert "body" not in dumped, (
            f"body leaked into TaskSummary.model_dump(): {list(dumped.keys())}"
        )

    def test_temporal_fields_not_in_construction_output(self) -> None:
        """Constructing TaskSummary from full task data must not include created or updated."""
        summary = TaskSummary.model_validate(_FULL_TASK_DATA)
        dumped = summary.model_dump()
        leaked = {"created", "updated"} & set(dumped)
        assert leaked == set(), (
            f"Temporal fields leaked into TaskSummary.model_dump(): {leaked}"
        )

    def test_claimed_by_not_in_construction_output(self) -> None:
        """Constructing TaskSummary from full task data must not expose claimed_by string."""
        summary = TaskSummary.model_validate(_FULL_TASK_DATA)
        dumped = summary.model_dump()
        assert "claimed_by" not in dumped, (
            f"claimed_by leaked into TaskSummary.model_dump(): {list(dumped.keys())}"
        )


# ---------------------------------------------------------------------------
# AC4 — TaskSummary can be constructed from a Task instance
# ---------------------------------------------------------------------------


class TestFromAC_TaskSummaryFromTask:
    """AC4: TaskSummary can be constructed from an owlbear_kanban.models.Task instance."""

    def _make_task(self, **kwargs: object) -> Task:
        base = {
            "id": 42,
            "title": "Test task",
            "status": "in-progress",
            "priority": "needed",
            "created": "2026-04-10T10:00:00+00:00",
            "updated": "2026-04-10T11:00:00+00:00",
        }
        base.update(kwargs)
        return Task.model_validate(base)

    def test_from_task_instance_construction_succeeds(self) -> None:
        """TaskSummary.model_validate(task.model_dump()) must not raise AND exposes claimed."""
        task = self._make_task()
        summary = TaskSummary.model_validate(task.model_dump())
        assert summary.id == 42
        assert summary.title == "Test task"
        # claimed must be accessible as a bool (fails RED: attribute does not exist yet)
        assert isinstance(summary.claimed, bool)

    def test_claimed_true_when_task_has_claimed_by(self) -> None:
        """Task with claimed_by='some-agent' → TaskSummary.claimed is True."""
        task = self._make_task(claimed_by="some-agent", claimed_at="2026-04-10T10:30:00+00:00")
        summary = TaskSummary.model_validate(task.model_dump())
        assert summary.claimed is True, (
            f"Expected claimed=True when claimed_by is set, got {summary.claimed!r}"
        )

    def test_claimed_false_when_task_unclaimed(self) -> None:
        """Task with claimed_by=None → TaskSummary.claimed is False."""
        task = self._make_task(claimed_by=None)
        summary = TaskSummary.model_validate(task.model_dump())
        assert summary.claimed is False, (
            f"Expected claimed=False when claimed_by is None, got {summary.claimed!r}"
        )


# ---------------------------------------------------------------------------
# AC3 — list_tasks returns TaskSummary projections, not hand-built dicts
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksProjection:
    """AC3: list_tasks return type annotation must be list[TaskSummary], not list[dict]."""

    def test_list_tasks_return_type_is_list_of_tasksummary(self) -> None:
        """list_tasks return annotation resolves to list[TaskSummary], not list[dict]."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = inspect.unwrap(server_mod.list_tasks)
        hints = typing.get_type_hints(fn)
        ret = hints.get("return")

        assert ret is not None, "list_tasks has no return type annotation"

        origin = getattr(ret, "__origin__", None)
        args = getattr(ret, "__args__", ())

        assert origin is list, (
            f"list_tasks return type origin must be list, got {origin!r} from {ret!r}"
        )
        assert len(args) == 1, (
            f"list_tasks return type must have exactly one type arg, got {args!r}"
        )
        assert args[0] is TaskSummary, (
            f"list_tasks must return list[TaskSummary], not {ret!r}"
        )
