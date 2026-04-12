"""RED tests — TaskSummary server integration (#802).

AC coverage:
  AC3 - KanbanEngine.list_tasks() return annotation is list[TaskSummary] and
        runtime items are TaskSummary instances (not Task)
  AC4 - server.py _strip dict eliminated; list_tasks uses TaskSummary model_dump
  AC5 - list_tasks outputSchema patching uses TaskSummary.model_json_schema()

AC6 (#801 tests pass GREEN) and AC7 (existing MCP tests unaffected) are
meta-conditions verified by the builder — no new code tests apply.

All tests MUST FAIL in RED:
  - KanbanEngine.list_tasks is annotated list[Task], not list[TaskSummary]
  - Runtime items are Task instances, not TaskSummary
  - Task.claimed does not exist (claimed_by does); body leaks in model_dump
  - AC4 server.py _strip already removed (prior push) — no new tests apply
  - outputSchema items are a hardcoded dict, not TaskSummary.model_json_schema()
"""

from __future__ import annotations

import typing
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine, TaskSummary

# ---------------------------------------------------------------------------
# Shared board config — mirrors pattern from test_config_staleness_fix_828.py
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: research
    - name: backlog
    - name: todo
    - name: in-progress
    - name: review
    - name: docs
    - name: done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
defaults:
    status: research
    priority: important
claim_timeout: 1h
next_id: 1
"""


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine instance wired to the temp kanban directory."""
    return KanbanEngine(kanban_dir)


# ---------------------------------------------------------------------------
# AC3 — KanbanEngine.list_tasks() returns list[TaskSummary]
# ---------------------------------------------------------------------------


class TestFromAC_EngineListTasksReturn:
    """AC3: KanbanEngine.list_tasks annotation + runtime output must be list[TaskSummary]."""

    def test_engine_list_tasks_return_annotation_is_list_of_tasksummary(self) -> None:
        """KanbanEngine.list_tasks return annotation must resolve to list[TaskSummary].

        RED: currently annotated list[Task].
        """
        hints = typing.get_type_hints(KanbanEngine.list_tasks)
        ret = hints.get("return")

        assert ret is not None, "KanbanEngine.list_tasks has no return type annotation"

        origin = getattr(ret, "__origin__", None)
        args = getattr(ret, "__args__", ())

        assert origin is list, (
            f"KanbanEngine.list_tasks annotation origin must be list, got {origin!r}"
        )
        assert len(args) == 1, (
            f"KanbanEngine.list_tasks annotation must have exactly one type arg, got {args!r}"
        )
        assert args[0] is TaskSummary, (
            f"KanbanEngine.list_tasks must be annotated list[TaskSummary], got list[{args[0]!r}]"
        )

    def test_engine_list_tasks_runtime_returns_tasksummary_instances(
        self, engine: KanbanEngine
    ) -> None:
        """Each item returned by engine.list_tasks() must be a TaskSummary instance.

        RED: currently returns Task instances.
        """
        engine.create_task("Integration test task", tags=["phase-1"])
        results = engine.list_tasks()

        assert len(results) >= 1, "Expected at least one task from list_tasks"
        for item in results:
            assert isinstance(item, TaskSummary), (
                f"Expected TaskSummary instance, got {type(item).__name__!r}"
            )

    def test_engine_list_tasks_claimed_is_bool_not_string_attribute(
        self, engine: KanbanEngine
    ) -> None:
        """Items from engine.list_tasks() must expose claimed (bool), not claimed_by (str).

        RED: Task has claimed_by: str | None — no claimed bool attribute.
        """
        engine.create_task("Claimed-bool test task")
        results = engine.list_tasks()

        assert len(results) >= 1, "Expected at least one task"
        item = results[0]

        assert hasattr(item, "claimed"), (
            "Item from engine.list_tasks() has no 'claimed' attribute — TaskSummary must expose it"
        )
        assert isinstance(item.claimed, bool), (
            f"Item.claimed must be bool, got {type(item.claimed).__name__!r}"
        )
        assert not hasattr(item, "claimed_by") or "claimed_by" not in item.model_dump(), (
            "claimed_by must not appear in TaskSummary — replaced by claimed (bool)"
        )

    def test_engine_list_tasks_body_not_in_model_dump(self, engine: KanbanEngine) -> None:
        """Items from engine.list_tasks() must not expose 'body' in model_dump().

        RED: Task.model_dump() includes body (Task stores it as a field).
        """
        engine.create_task("Body exclusion test", body="Private body text that must stay hidden")
        results = engine.list_tasks()

        task = next(t for t in results if t.title == "Body exclusion test")
        dumped = task.model_dump()

        assert "body" not in dumped, (
            f"'body' must not appear in TaskSummary.model_dump(), got keys: {list(dumped.keys())}"
        )


# ---------------------------------------------------------------------------
# AC4 — server.py _strip dict eliminated
#
# Note: server.py was already updated in a prior push — `_strip = {...}` is
# gone and replaced by `TaskSummary.model_validate(record.model_dump())`.
# The server return type annotation (list[TaskSummary]) is covered by
# #801 TestFromAC_ListTasksProjection. No new R#802-specific AC4 tests apply.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AC5 — outputSchema patching uses TaskSummary.model_json_schema()
# ---------------------------------------------------------------------------


def _get_list_tasks_output_schema() -> dict | None:
    """Return fn_metadata.output_schema for the list_tasks tool, or None."""
    import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

    mcp_obj = server_mod.mcp
    if hasattr(mcp_obj, "_tool_manager") and hasattr(mcp_obj._tool_manager, "_tools"):  # noqa: SLF001
        for t in mcp_obj._tool_manager._tools.values():  # noqa: SLF001
            if getattr(t, "name", None) == "list_tasks":
                return getattr(getattr(t, "fn_metadata", None), "output_schema", None)
    return None


class TestFromAC_OutputSchemaDerivedFromModel:
    """AC5: list_tasks outputSchema items must be derived from TaskSummary.model_json_schema()."""

    def test_output_schema_items_equal_tasksummary_model_json_schema(self) -> None:
        """outputSchema.properties.result.items must equal TaskSummary.model_json_schema().

        RED: items is a manually specified dict that predates model completion;
        TaskSummary.model_json_schema() produces a different schema (wrong fields,
        missing 'title', missing 'required', has 'claimed_by' instead of 'claimed').
        """
        schema = _get_list_tasks_output_schema()
        assert schema is not None, "list_tasks output_schema not found on tool object"

        items = schema.get("properties", {}).get("result", {}).get("items")
        assert items is not None, (
            f"output_schema.properties.result.items not found; top-level keys: {list(schema.keys())}"
        )

        model_schema = TaskSummary.model_json_schema()
        assert items == model_schema, (
            "list_tasks outputSchema items do not match TaskSummary.model_json_schema().\n"
            f"Expected (from model):\n  {model_schema}\n"
            f"Actual (in outputSchema):\n  {items}"
        )

    def test_output_schema_items_include_pydantic_title_from_model(self) -> None:
        """outputSchema items must contain the 'title' key emitted by model_json_schema().

        Pydantic's model_json_schema() adds 'title': 'TaskSummary' at the model root.
        The current handwritten items dict has no 'title' key, so this test exposes
        that the patching was NOT regenerated from the model.

        RED: current items dict is {'type': 'object', 'properties': {...}} — no 'title'.
        """
        schema = _get_list_tasks_output_schema()
        assert schema is not None, "list_tasks output_schema not found on tool object"

        items = schema.get("properties", {}).get("result", {}).get("items", {})

        assert "title" in items, (
            "outputSchema items is missing 'title' key — expected 'title': 'TaskSummary' "
            "from TaskSummary.model_json_schema(). The schema is still hardcoded, not derived "
            f"from the model. Current items keys: {list(items.keys())}"
        )
        assert items["title"] == "TaskSummary", (
            f"outputSchema items['title'] must be 'TaskSummary', got {items['title']!r}"
        )

    def test_output_schema_items_have_required_array_from_model_schema(self) -> None:
        """outputSchema items must contain a 'required' array emitted by model_json_schema().

        Pydantic's model_json_schema() adds 'required': ['id', 'title', ...] for
        non-optional fields. The current handwritten items dict has no 'required' key.

        RED: current items dict is {'type': 'object', 'properties': {...}} — no 'required'.
        """
        schema = _get_list_tasks_output_schema()
        assert schema is not None, "list_tasks output_schema not found on tool object"

        items = schema.get("properties", {}).get("result", {}).get("items", {})

        assert "required" in items, (
            "outputSchema items is missing 'required' array — expected from "
            "TaskSummary.model_json_schema(). The schema is still hardcoded, not derived "
            f"from the model. Current items keys: {list(items.keys())}"
        )
