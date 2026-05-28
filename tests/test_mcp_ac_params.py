"""RED phase tests — MCP ac/proof_bundle tool parameter passthrough (#1519).

Tests verify:
- MCP create_task exposes ac/proof_bundle params and forwards them to AgentView
- MCP edit_task exposes ac/add_ac/remove_ac/proof_bundle params and forwards them
- ShowTaskResponse model carries ac and proof_bundle fields (regression backstop)

AC coverage:
- AC1: create_task exposes ac: list[str]|None and proof_bundle: str|None; when
       non-None, each reaches AgentView.create_task() as the corresponding kwarg
- AC2: edit_task exposes ac: list[str]|None, add_ac: list[str]|None,
       remove_ac: list[str]|None, proof_bundle: str|None; when non-None, each
       reaches AgentView.edit_task() as the corresponding kwarg
- AC3: ShowTaskResponse includes ac (list[str]) and proof_bundle (str|None) fields
       (regression backstop — GREEN by architect design; fields already shipped
        via TaskFull / TaskSummary inheritance; see #1519 arch-review)
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban.models import ShowTaskResponse, SingleTaskResponse
from owlbear_mcp_kanban.server import AppContext, create_task, edit_task


# ---------------------------------------------------------------------------
# Shared board configuration (matches test_mcp_mutation_tools.py pattern)
# ---------------------------------------------------------------------------

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
    """Wrap an AppContext in a MagicMock mimicking MCP Context."""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx_with_mock_agent_view(
    tmp_path: Path,
) -> tuple[AppContext, MagicMock]:
    """AppContext with mock AgentView that returns a SingleTaskResponse."""
    from owlbear_kanban import KanbanEngine

    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Initial task", status="todo", priority="important")
    engine.list_tasks()  # populate id_to_filename cache
    mock_av = MagicMock()
    mock_av.create_task.return_value = _make_single_task_response()
    mock_av.edit_task.return_value = _make_single_task_response()
    engine._agent_view = mock_av  # noqa: SLF001
    app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
    return app_ctx, mock_av


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskACParams
# AC1: create_task exposes ac/proof_bundle params; forwards to AgentView when non-None
# ---------------------------------------------------------------------------


class TestCreateTaskACParams:
    """MCP create_task must expose and forward ac and proof_bundle params."""

    # --- Signature / structure (happy-path existence checks) ---

    def test_create_task_exposes_ac_param(self) -> None:
        """create_task must expose an 'ac' parameter (list[str] | None)."""
        params = inspect.signature(create_task).parameters
        assert "ac" in params, (
            f"create_task must expose 'ac: list[str] | None' parameter per AC1; current params: {list(params)}"
        )

    def test_create_task_exposes_proof_bundle_param(self) -> None:
        """create_task must expose a 'proof_bundle' parameter (str | None)."""
        params = inspect.signature(create_task).parameters
        assert "proof_bundle" in params, (
            f"create_task must expose 'proof_bundle: str | None' parameter per AC1; current params: {list(params)}"
        )

    # --- Forwarding (happy path) ---

    @pytest.mark.asyncio
    async def test_create_task_forwards_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        """When ac is non-None, create_task must forward it to AgentView.create_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", ac=["Implement feature X"])
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("ac") == ["Implement feature X"], (
            "ac must be forwarded to AgentView.create_task when non-None"
        )

    @pytest.mark.asyncio
    async def test_create_task_forwards_proof_bundle_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        """When proof_bundle is non-None, create_task must forward it to AgentView.create_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", proof_bundle="behavioral")
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("proof_bundle") == "behavioral", (
            "proof_bundle must be forwarded to AgentView.create_task when non-None"
        )

    # --- Edge / boundary ---

    @pytest.mark.asyncio
    async def test_create_task_forwards_ac_empty_list(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        """ac=[] (empty list, not None) is 'provided' and must reach AgentView.create_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", ac=[])
        _, kwargs = mock_av.create_task.call_args
        assert "ac" in kwargs, "ac=[] (non-None empty list) must be forwarded to AgentView.create_task"
        assert kwargs["ac"] == [], "ac=[] must be forwarded as an empty list, not dropped"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskACParams
# AC2: edit_task exposes ac/add_ac/remove_ac/proof_bundle params;
#      each forwarded to AgentView.edit_task when non-None
# ---------------------------------------------------------------------------


class TestEditTaskACParams:
    """MCP edit_task must expose and forward ac, add_ac, remove_ac, proof_bundle params."""

    # --- Signature / structure ---

    def test_edit_task_exposes_ac_param(self) -> None:
        """edit_task must expose an 'ac' parameter (list[str] | None)."""
        params = inspect.signature(edit_task).parameters
        assert "ac" in params, (
            f"edit_task must expose 'ac: list[str] | None' parameter per AC2; current params: {list(params)}"
        )

    def test_edit_task_exposes_add_ac_param(self) -> None:
        """edit_task must expose an 'add_ac' parameter (list[str] | None)."""
        params = inspect.signature(edit_task).parameters
        assert "add_ac" in params, (
            f"edit_task must expose 'add_ac: list[str] | None' parameter per AC2; current params: {list(params)}"
        )

    def test_edit_task_exposes_remove_ac_param(self) -> None:
        """edit_task must expose a 'remove_ac' parameter (list[str] | None)."""
        params = inspect.signature(edit_task).parameters
        assert "remove_ac" in params, (
            f"edit_task must expose 'remove_ac: list[str] | None' parameter per AC2; current params: {list(params)}"
        )

    def test_edit_task_exposes_proof_bundle_param(self) -> None:
        """edit_task must expose a 'proof_bundle' parameter (str | None)."""
        params = inspect.signature(edit_task).parameters
        assert "proof_bundle" in params, (
            f"edit_task must expose 'proof_bundle: str | None' parameter per AC2; current params: {list(params)}"
        )

    # --- Forwarding (happy path) ---

    @pytest.mark.asyncio
    async def test_edit_task_forwards_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        """When ac is non-None, edit_task must forward it to AgentView.edit_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", ac=["New criterion A", "New criterion B"])
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("ac") == ["New criterion A", "New criterion B"], (
            "ac must be forwarded to AgentView.edit_task when non-None"
        )

    @pytest.mark.asyncio
    async def test_edit_task_forwards_add_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        """When add_ac is non-None, edit_task must forward it to AgentView.edit_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", add_ac=["Extra criterion"])
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("add_ac") == ["Extra criterion"], (
            "add_ac must be forwarded to AgentView.edit_task when non-None"
        )

    @pytest.mark.asyncio
    async def test_edit_task_forwards_remove_ac_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        """When remove_ac is non-None, edit_task must forward it to AgentView.edit_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", remove_ac=["Old criterion"])
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("remove_ac") == ["Old criterion"], (
            "remove_ac must be forwarded to AgentView.edit_task when non-None"
        )

    @pytest.mark.asyncio
    async def test_edit_task_forwards_proof_bundle_when_provided(
        self,
        app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock],
    ) -> None:
        """When proof_bundle is non-None, edit_task must forward it to AgentView.edit_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", proof_bundle="smoke")
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("proof_bundle") == "smoke", (
            "proof_bundle must be forwarded to AgentView.edit_task when non-None"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ShowTaskResponseFields
# AC3: ShowTaskResponse includes ac (list[str]) and proof_bundle (str|None)
#      NOTE: These tests are intentionally GREEN (regression backstop).
#      ShowTaskResponse already has these fields via TaskFull/TaskSummary
#      inheritance. Architect pre-approved green AC3 tests (#1519 arch-review,
#      challenger finding (4) REJECTED).
# ---------------------------------------------------------------------------


class TestShowTaskResponseFields:
    """ShowTaskResponse must include ac and proof_bundle fields from task frontmatter."""

    def test_show_task_response_model_has_ac_field(self) -> None:
        """ShowTaskResponse must declare an 'ac' field of type list[str]."""
        assert "ac" in ShowTaskResponse.model_fields, (
            "ShowTaskResponse must have 'ac' as a declared model field; "
            f"current fields: {list(ShowTaskResponse.model_fields)}"
        )

    def test_show_task_response_model_has_proof_bundle_field(self) -> None:
        """ShowTaskResponse must declare a 'proof_bundle' field (str | None)."""
        assert "proof_bundle" in ShowTaskResponse.model_fields, (
            "ShowTaskResponse must have 'proof_bundle' as a declared model field; "
            f"current fields: {list(ShowTaskResponse.model_fields)}"
        )

    def test_show_task_response_ac_accepts_list_of_strings(self) -> None:
        """ShowTaskResponse.ac must accept and store a list of strings."""
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
        assert resp.ac == ["criterion 1", "criterion 2"], (
            "ShowTaskResponse.ac must store the provided list of strings exactly"
        )

    def test_show_task_response_proof_bundle_accepts_string(self) -> None:
        """ShowTaskResponse.proof_bundle must accept a string value and return it."""
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
        assert resp.proof_bundle == "behavioral", "ShowTaskResponse.proof_bundle must store the provided string value"
