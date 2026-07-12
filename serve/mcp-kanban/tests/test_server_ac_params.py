"""Durable MCP server regression tests for ac/proof_bundle parameter passthrough."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban.models import ShowTaskResponse, SingleTaskResponse
from owlbear_mcp_kanban.server import AppContext, create_task, edit_task

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
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
archive_dir: archive
activity_log: false
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_mcp_ctx(app_ctx: object) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_single_task_response(**overrides: object) -> SingleTaskResponse:
    defaults: dict[str, object] = {
        "id": 1,
        "title": "Test Task",
        "status": "todo",
        "priority": "important",
        "tags": [],
        "depends_on": [],
        "blocked": False,
        "block_reason": None,
        "claimed": False,
        "claimed_at": None,
        "archival_reason": None,
        "archival_refs": [],
        "dep_status": None,
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "body": "",
        "guidance": [],
    }
    defaults.update(overrides)
    return SingleTaskResponse.model_validate(defaults)


@pytest.fixture
def app_ctx_with_mock_agent_view(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    from owlbear_kanban import KanbanEngine

    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Initial task", status="build", priority="medium")
    engine.list_tasks()
    mock_av = MagicMock()
    mock_av.create_task.return_value = _make_single_task_response()
    mock_av.edit_task.return_value = _make_single_task_response()
    engine._agent_view = mock_av  # noqa: SLF001
    app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
    return app_ctx, mock_av


class TestCreateTaskACParams:
    def test_create_task_exposes_ac_param(self) -> None:
        params = inspect.signature(create_task).parameters
        assert "ac" in params, (
            f"create_task must expose 'ac: list[str] | None' parameter per AC1; current params: {list(params)}"
        )

    def test_create_task_exposes_proof_bundle_param(self) -> None:
        params = inspect.signature(create_task).parameters
        assert "proof_bundle" in params, (
            f"create_task must expose 'proof_bundle: str | None' parameter per AC1; current params: {list(params)}"
        )

    @pytest.mark.asyncio
    async def test_create_task_forwards_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", ac=["Implement feature X"])
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("ac") == ["Implement feature X"]

    @pytest.mark.asyncio
    async def test_create_task_forwards_proof_bundle_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", proof_bundle="behavioral")
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("proof_bundle") == "behavioral"

    @pytest.mark.asyncio
    async def test_create_task_forwards_ac_empty_list(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", ac=[])
        _, kwargs = mock_av.create_task.call_args
        assert "ac" in kwargs
        assert kwargs["ac"] == []


class TestEditTaskACParams:
    def test_edit_task_exposes_ac_param(self) -> None:
        params = inspect.signature(edit_task).parameters
        assert "ac" in params, (
            f"edit_task must expose 'ac: list[str] | None' parameter per AC2; current params: {list(params)}"
        )

    def test_edit_task_exposes_add_ac_param(self) -> None:
        params = inspect.signature(edit_task).parameters
        assert "add_ac" in params, (
            f"edit_task must expose 'add_ac: list[str] | None' parameter per AC2; current params: {list(params)}"
        )

    def test_edit_task_exposes_remove_ac_param(self) -> None:
        params = inspect.signature(edit_task).parameters
        assert "remove_ac" in params, (
            f"edit_task must expose 'remove_ac: list[str] | None' parameter per AC2; current params: {list(params)}"
        )

    def test_edit_task_exposes_proof_bundle_param(self) -> None:
        params = inspect.signature(edit_task).parameters
        assert "proof_bundle" in params, (
            f"edit_task must expose 'proof_bundle: str | None' parameter per AC2; current params: {list(params)}"
        )

    @pytest.mark.asyncio
    async def test_edit_task_forwards_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", ac=["New criterion A", "New criterion B"])
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("ac") == ["New criterion A", "New criterion B"]

    @pytest.mark.asyncio
    async def test_edit_task_forwards_add_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", add_ac=["Extra criterion"])
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("add_ac") == ["Extra criterion"]

    @pytest.mark.asyncio
    async def test_edit_task_forwards_remove_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", remove_ac=["Old criterion"])
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("remove_ac") == ["Old criterion"]

    @pytest.mark.asyncio
    async def test_edit_task_forwards_proof_bundle_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", proof_bundle="smoke")
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("proof_bundle") == "smoke"


class TestShowTaskResponseFields:
    def test_show_task_response_model_has_ac_field(self) -> None:
        assert "ac" in ShowTaskResponse.model_fields, (
            "ShowTaskResponse must have 'ac' as a declared model field; "
            f"current fields: {list(ShowTaskResponse.model_fields)}"
        )

    def test_show_task_response_model_has_proof_bundle_field(self) -> None:
        assert "proof_bundle" in ShowTaskResponse.model_fields, (
            "ShowTaskResponse must have 'proof_bundle' as a declared model field; "
            f"current fields: {list(ShowTaskResponse.model_fields)}"
        )

    def test_show_task_response_ac_accepts_list_of_strings(self) -> None:
        resp = ShowTaskResponse.model_validate(
            {
                "id": 1,
                "title": "T",
                "status": "todo",
                "priority": "important",
                "tags": [],
                "depends_on": [],
                "blocked": False,
                "block_reason": None,
                "claimed": False,
                "claimed_at": None,
                "archival_reason": None,
                "archival_refs": [],
                "dep_status": None,
                "created": "2026-01-01T00:00:00+00:00",
                "updated": "2026-01-01T00:00:00+00:00",
                "body": "",
                "missing_sections": None,
                "guidance": [],
                "ac": ["criterion 1", "criterion 2"],
            }
        )
        assert resp.ac == ["criterion 1", "criterion 2"]

    def test_show_task_response_proof_bundle_accepts_string(self) -> None:
        resp = ShowTaskResponse.model_validate(
            {
                "id": 1,
                "title": "T",
                "status": "todo",
                "priority": "important",
                "tags": [],
                "depends_on": [],
                "blocked": False,
                "block_reason": None,
                "claimed": False,
                "claimed_at": None,
                "archival_reason": None,
                "archival_refs": [],
                "dep_status": None,
                "created": "2026-01-01T00:00:00+00:00",
                "updated": "2026-01-01T00:00:00+00:00",
                "body": "",
                "missing_sections": None,
                "guidance": [],
                "proof_bundle": "behavioral",
            }
        )
        assert resp.proof_bundle == "behavioral"
