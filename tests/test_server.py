from __future__ import annotations

# --- merged from tests/test_server_1170.py ---
"""Coverage-gap tests for server.py uncovered paths (#1170).

Target: >=90% line coverage for owlbear_mcp_kanban.server combined with
the canonical scoped test set.

Paths covered: AppContext.__contains__, app_lifespan, list_tasks error handlers,
_to_single_task_response branches, _show_validated FileNotFoundError,
show_task PydanticValidationError, create_task, edit_task, move_task status guard.

Note: Tests for deleted helpers (_invoke_view_move_task, _invoke_engine_end_work,
_invoke_view_end_work, _canonical_agent_view_for) and engine fallback paths
removed in #1360 — those symbols no longer exist in server.py.
"""


from pathlib import Path
from unittest.mock import MagicMock, NonCallableMagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban.errors import NotFoundError, ValidationError
from owlbear_kanban.models import SingleTaskResponse

from owlbear_mcp_kanban.server import (
    AppContext,
    _show_validated,
    _to_single_task_response,
    create_task,
    edit_task,
    list_tasks,
    move_task,
    show_task,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_task_dict(**overrides: object) -> dict:
    defaults: dict[str, object] = {
        "id": 42,
        "title": "Coverage Task",
        "status": "todo",
        "priority": "needed",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T01:00:00+00:00",
        "claimed": False,
        "tags": [],
        "body": None,
        "blocked": False,
        "block_reason": None,
        "parent": None,
        "depends_on": [],
        "guidance": [],
    }
    defaults.update(overrides)
    return defaults


def _make_single_task_response(**overrides: object) -> SingleTaskResponse:
    return SingleTaskResponse.model_validate(_make_task_dict(**overrides))


def _make_engine_mock(*, agent_view: object | None = "default") -> MagicMock:
    """Return a MagicMock engine.

    agent_view="default" → NonCallableMagicMock (non-callable view).
    agent_view=None → None (forces fallback paths).
    """
    engine = MagicMock()
    if agent_view == "default":
        av = NonCallableMagicMock()
        engine.agent_view = av
    else:
        engine.agent_view = agent_view
    task_dict = _make_task_dict()
    for method in (
        "show_task",
        "move_task",
        "start_work",
        "end_work",
        "edit_task",
        "create_task",
    ):
        getattr(engine, method).return_value.model_dump.return_value = task_dict
    engine.board_config.return_value.statuses = [
        "research",
        "backlog",
        "todo",
        "in-progress",
        "review",
        "docs",
        "done",
    ]
    return engine


def _make_app_ctx(engine: MagicMock, kanban_dir: Path | None = None) -> AppContext:
    return AppContext(engine=engine, kanban_dir=kanban_dir or Path())


def _make_ctx_from_app_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_ctx_from_engine(engine: MagicMock) -> MagicMock:
    """MCP ctx where lifespan_context.engine = engine (mock AppContext)."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_AppContextHelpers — line 89
# ---------------------------------------------------------------------------


class TestFromAC_AppContextHelpers:
    """AppContext.__contains__ coverage — line 89."""

    def test_contains_always_returns_false_for_string(self) -> None:
        """AppContext.__contains__ returns False for any string (line 89).

        FAILS: if __contains__ is missing or raises TypeError instead.
        """
        engine = _make_engine_mock()
        app_ctx = _make_app_ctx(engine)
        assert "engine" not in app_ctx

    def test_contains_always_returns_false_for_integer(self) -> None:
        """AppContext.__contains__ returns False for integers too.

        FAILS: if __contains__ is removed and membership check raises.
        """
        engine = _make_engine_mock()
        app_ctx = _make_app_ctx(engine)
        assert 0 not in app_ctx


# ---------------------------------------------------------------------------
# TestFromAC_AppLifespan — lines 116-120
# ---------------------------------------------------------------------------


class TestFromAC_AppLifespan:
    """app_lifespan async context manager coverage — lines 116-120."""

    @pytest.mark.asyncio
    async def test_lifespan_yields_app_context_with_swept_engine(self) -> None:
        """app_lifespan yields AppContext; engine.sweep() called (lines 116-120).

        FAILS: if sweep() is not called or the yielded object is not an AppContext.
        """
        from owlbear_mcp_kanban.server import app_lifespan

        mock_engine = MagicMock()
        with patch("owlbear_mcp_kanban.server.KanbanEngine", return_value=mock_engine):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert isinstance(ctx, AppContext)
                mock_engine.sweep.assert_called_once()


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksErrorPaths — lines 162, 177
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksErrorPaths:
    """list_tasks error handlers for KanbanError and PydanticValidationError."""

    @pytest.mark.asyncio
    async def test_kanban_error_mapped_to_tool_error(self) -> None:
        """list_tasks: KanbanError from engine → ToolError (line 162).

        FAILS: if the KanbanError handler is missing from list_tasks.
        """
        av = MagicMock()
        av.list_tasks.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message="board not accessible")
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        with pytest.raises(ToolError, match="board not accessible"):
            await list_tasks(ctx)

    @pytest.mark.asyncio
    async def test_pydantic_validation_error_mapped_to_tool_error(self) -> None:
        """list_tasks: PydanticValidationError → ToolError (line 177).

        FAILS: if the PydanticValidationError handler is missing from list_tasks.
        """
        ctx = MagicMock()
        ctx.request_context.lifespan_context.engine.agent_view.return_value = MagicMock()
        with pytest.raises(ToolError):
            await list_tasks(ctx, ids=["not_an_int"])  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# TestFromAC_ToSingleTaskResponse — lines 203, 207-209
# ---------------------------------------------------------------------------


class TestFromAC_ToSingleTaskResponse:
    """_to_single_task_response handles all input branches."""

    def test_kanban_task_converted_to_single_task_response(self) -> None:
        """KanbanTask input → SingleTaskResponse (line 203).

        FAILS: if the isinstance(record, KanbanTask) branch is absent.
        """
        from owlbear_mcp_kanban.models import KanbanTask

        kt = KanbanTask.model_validate(_make_task_dict())
        result = _to_single_task_response(kt)
        assert isinstance(result, SingleTaskResponse)
        assert result.id == 42

    def test_object_with_model_dump_converted(self) -> None:
        """Object with model_dump() is converted via dump (lines 207-208).

        FAILS: if the hasattr(model_dump) branch is removed.
        """
        obj = MagicMock(spec_set=["model_dump"])
        obj.model_dump.return_value = _make_task_dict()
        result = _to_single_task_response(obj)
        assert isinstance(result, SingleTaskResponse)

    def test_dict_input_converted_to_single_task_response(self) -> None:
        """dict input is validated into SingleTaskResponse (line 209).

        FAILS: if the dict branch is removed.
        """
        d = _make_task_dict()
        result = _to_single_task_response(d)
        assert isinstance(result, SingleTaskResponse)
        assert result.title == "Coverage Task"


# ---------------------------------------------------------------------------
# TestFromAC_ShowValidated — line 332
# ---------------------------------------------------------------------------


class TestFromAC_ShowValidated:
    """_show_validated wraps FileNotFoundError as ToolError."""

    @pytest.mark.asyncio
    async def test_file_not_found_raises_tool_error(self) -> None:
        """_show_validated: FileNotFoundError → ToolError (line 332).

        FAILS: if FileNotFoundError is not caught and wrapped.
        """
        engine = MagicMock()
        engine.show_task.side_effect = FileNotFoundError("task file missing")
        app_ctx = _make_app_ctx(engine)
        with pytest.raises(ToolError, match="task file missing"):
            await _show_validated(app_ctx, "99")


# ---------------------------------------------------------------------------
# TestFromAC_ShowTaskPydanticError — line 463
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskPydanticError:
    """show_task PydanticValidationError → ToolError."""

    @pytest.mark.asyncio
    async def test_pydantic_error_raises_tool_error(self) -> None:
        """show_task: PydanticValidationError → ToolError (line 463).

        FAILS: if the PydanticValidationError handler is missing.
        """
        ctx = MagicMock()
        with pytest.raises(ToolError):
            await show_task(ctx, id="not_an_int")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskPaths — lines 474-478
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskPaths:
    """create_task success path and KanbanError handler."""

    @pytest.mark.asyncio
    async def test_create_task_delegates_to_agent_view_and_returns(self) -> None:
        """create_task calls agent_view().create_task and returns SingleTaskResponse (lines 474-478).

        FAILS: if create_task doesn't route through agent_view or returns wrong type.
        """
        av = MagicMock()
        av.create_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        result = await create_task(ctx, title="My New Task")
        assert isinstance(result, SingleTaskResponse)
        av.create_task.assert_called_once()
        _, kwargs = av.create_task.call_args
        assert kwargs.get("title") == "My New Task"

    @pytest.mark.asyncio
    async def test_create_task_kanban_error_mapped_to_tool_error(self) -> None:
        """create_task: KanbanError from agent_view → ToolError.

        FAILS: if KanbanError is not caught in create_task.
        """
        av = MagicMock()
        av.create_task.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message="create failed: board not found")
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        with pytest.raises(ToolError, match="create failed: board not found"):
            await create_task(ctx, title="New Task")


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskCoverage — lines 508-592
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskCoverage:
    """edit_task full body coverage — kwargs building, engine call, guidance."""

    @pytest.mark.asyncio
    async def test_body_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: non-empty body forwarded to agent_view().edit_task (lines 508-548).

        FAILS: if the body kwarg branch is removed or body not forwarded.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", body="New body content")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("body") == "New body content"

    @pytest.mark.asyncio
    async def test_append_body_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: non-empty append_body forwarded (lines 508+).

        FAILS: if append_body branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", append_body="Appended section")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("append_body") == "Appended section"

    @pytest.mark.asyncio
    async def test_priority_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: non-empty priority forwarded.

        FAILS: if priority branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", priority="critical")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("priority") == "critical"

    @pytest.mark.asyncio
    async def test_add_dep_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: add_dep list forwarded when not None.

        FAILS: if add_dep branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", add_dep=[10, 20])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("add_dep") == [10, 20]

    @pytest.mark.asyncio
    async def test_add_tag_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: add_tag list forwarded when not None.

        FAILS: if add_tag branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", add_tag=["phase-2", "scope:kanban"])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("add_tag") == ["phase-2", "scope:kanban"]

    @pytest.mark.asyncio
    async def test_block_reason_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: block_reason forwarded when not None.

        FAILS: if block_reason branch filters out non-None values.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", block_reason="Waiting for design review")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("block_reason") == "Waiting for design review"

    @pytest.mark.asyncio
    async def test_edit_task_kanban_error_mapped_to_tool_error(self) -> None:
        """edit_task: KanbanError from agent_view → ToolError.

        FAILS: if KanbanError is not caught in edit_task.
        """
        av = MagicMock()
        av.edit_task.side_effect = ValidationError(code="ERR_INVALID_PRIORITY", user_message="invalid priority value")
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        with pytest.raises(ToolError, match="invalid priority value"):
            await edit_task(ctx, id="42", priority="bad-priority")

    @pytest.mark.asyncio
    async def test_edit_task_returns_single_task_response(self) -> None:
        """edit_task returns SingleTaskResponse (lines 570-592).

        FAILS: if edit_task returns the wrong type.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        result = await edit_task(ctx, id="42", append_body="Note added")
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_remove_dep_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: remove_dep list forwarded when not None.

        FAILS: if remove_dep branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", remove_dep=[5])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("remove_dep") == [5]

    @pytest.mark.asyncio
    async def test_timestamp_true_forwarded_to_engine(self) -> None:
        """edit_task: timestamp=True forwarded (lines 508+).

        FAILS: if timestamp branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", timestamp=True)
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("timestamp") is True

    @pytest.mark.asyncio
    async def test_parent_nonzero_forwarded_to_engine(self) -> None:
        """edit_task: parent > 0 forwarded to agent_view().edit_task.

        FAILS: if the `if parent > 0` branch is removed or parent not forwarded.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", parent=7)
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("parent") == 7

    @pytest.mark.asyncio
    async def test_remove_tag_forwarded_to_engine(self) -> None:
        """edit_task: remove_tag list forwarded when not None.

        FAILS: if the `if remove_tag is not None` branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", remove_tag=["phase-1", "scope:old"])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("remove_tag") == ["phase-1", "scope:old"]

    @pytest.mark.asyncio
    async def test_archival_reason_nonempty_forwarded_to_engine(self) -> None:
        """edit_task: non-empty archival_reason forwarded to engine.

        FAILS: if the `if archival_reason` branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", archival_reason="superseded by #99")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("archival_reason") == "superseded by #99"

    @pytest.mark.asyncio
    async def test_archival_refs_forwarded_to_engine(self) -> None:
        """edit_task: archival_refs list forwarded when not None.

        FAILS: if the `if archival_refs is not None` branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", archival_refs=[98, 99])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("archival_refs") == [98, 99]


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskFallbackPath — lines 508-548 (move_task engine path)
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskFallbackPath:
    """move_task input validation — status=None guard fires before engine call."""

    @pytest.mark.asyncio
    async def test_status_none_raises_tool_error_before_engine_call(self) -> None:
        """move_task: status=None raises ToolError before engine fallback.

        FAILS: if the status=None guard is removed.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="status is required"):
            await move_task(ctx, id="42")
        engine.move_task.assert_not_called()


# --- merged from tests/test_server_1172.py ---
"""RED tests — server.py L481 status_names dict-form bug (#1172).

Bug: ``move_task`` at L481 extracts status names via::

    status_names = [s["name"] for s in app_ctx.engine.board_config().statuses]

Post-Brief-C, ``board_config().statuses`` is ``list[str]``; the dict subscript
``s["name"]`` on a plain string raises ``TypeError``.  The surrounding
``contextlib.suppress(Exception)`` silently swallows the error, so
``collect_guidance`` is never called and forward-skip guidance is always empty
on new-schema boards.

Note: In normal operation the ``AgentView`` path executes first and provides
guidance correctly.  The L481 bug lives in the *fallback* path (``agent_view``
absent).  Tests force the fallback by monkeypatching ``engine.agent_view = None``.

Fix: replace the list-comprehension with
``list(app_ctx.engine.board_config().statuses)``.

AC (derived from #1172 research + #1173 AC):
1. ``move_task`` forward-skip (>1 slot) returns non-empty guidance when
   ``board_config().statuses`` is ``list[str]`` and the AgentView fallback
   path is active.
2. Guidance message references both the source and target status names.
3. ``collect_guidance`` is reached (not short-circuited by TypeError) and
   receives ``status_names`` as ``list[str]``.
"""


from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, move_task

# ---------------------------------------------------------------------------
# Board config — post-Brief-C list[str] statuses (flat, no dict-form)
# ---------------------------------------------------------------------------

_CONFIG_YAML_1198 = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
wave_size: 4
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_board_1198(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML_1198, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_ctx_1198(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """AppContext backed by a post-Brief-C board with agent_view disabled.

    Monkeypatching ``engine.agent_view = None`` forces ``move_task`` past the
    AgentView short-circuit path and into the legacy fallback at L481, where
    the dict-form bug lives.
    """
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Alpha task", status="research", priority="important")
    engine.list_tasks()  # populate id→filename cache
    engine.agent_view = None  # type: ignore[assignment] — force fallback to L481 path
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_StatusNamesDictFormBug
# ---------------------------------------------------------------------------


"""Tests for #1198: Remove legacy compat code from MCP server.

AC line (td:1):
- Tool functions use id: StrId directly — no resolution indirection

Retry cycle — strengthened per reviewer required follow-up:
- TestFromAC_LegacyCompatRemoval: VAR_KEYWORD absence (original 4 tests)
- TestFromAC_IdParameterContract: named 'id' + StrId annotation for all 4 tools
- TestFromAC_IdDirectPassthrough: behavioral proof via real board + TypeError rejection
"""


import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import (
    AppContext,
    edit_task,
    end_work,
    move_task,
    start_work,
)

# ---------------------------------------------------------------------------
# Minimal board config for behavioral tests
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
wave_size: 4
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


@pytest.fixture
def app_ctx_1198(tmp_path: Path) -> AppContext:
    """AppContext backed by a real board with one task at 'research'."""
    kanban_dir = _make_board_1198(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Probe task", status="research", priority="important")
    engine.list_tasks()  # populate id→filename cache
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_LegacyCompatRemoval — original VAR_KEYWORD checks (4 tests)
# ---------------------------------------------------------------------------


class TestFromAC_LegacyCompatRemoval:
    """AC: Tool functions use id: StrId directly — no resolution indirection (td:1)."""

    def test_move_task_uses_id_directly_no_legacy_kwargs(self) -> None:
        """move_task signature has no **legacy catch-all parameter."""
        sig = inspect.signature(move_task)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "move_task still has **legacy catch-all — should use id: StrId directly"
        )

    def test_edit_task_uses_id_directly_no_legacy_kwargs(self) -> None:
        """edit_task signature has no **legacy catch-all parameter."""
        sig = inspect.signature(edit_task)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "edit_task still has **legacy catch-all — should use id: StrId directly"
        )

    def test_start_work_uses_id_directly_no_legacy_kwargs(self) -> None:
        """start_work signature has no **legacy catch-all parameter."""
        sig = inspect.signature(start_work)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "start_work still has **legacy catch-all — should use id: StrId directly"
        )

    def test_end_work_uses_id_directly_no_legacy_kwargs(self) -> None:
        """end_work signature has no **legacy catch-all parameter."""
        sig = inspect.signature(end_work)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "end_work still has **legacy catch-all — should use id: StrId directly"
        )


# ---------------------------------------------------------------------------
# TestFromAC_IdParameterContract — named 'id' + StrId annotation (8 tests)
# ---------------------------------------------------------------------------


class TestFromAC_IdParameterContract:
    """AC: Tool functions use id: StrId directly — parameter name and annotation proof."""

    # --- Named 'id' parameter ------------------------------------------------

    def test_move_task_has_named_id_parameter(self) -> None:
        """move_task has 'id' as the named task-identifier parameter (not 'task_id')."""
        sig = inspect.signature(move_task)
        assert "id" in sig.parameters, "move_task must have 'id' as named parameter — legacy 'task_id' has been removed"

    def test_edit_task_has_named_id_parameter(self) -> None:
        """edit_task has 'id' as the named task-identifier parameter (not 'task_id')."""
        sig = inspect.signature(edit_task)
        assert "id" in sig.parameters, "edit_task must have 'id' as named parameter — legacy 'task_id' has been removed"

    def test_start_work_has_named_id_parameter(self) -> None:
        """start_work has 'id' as the named task-identifier parameter (not 'task_id')."""
        sig = inspect.signature(start_work)
        assert "id" in sig.parameters, (
            "start_work must have 'id' as named parameter — legacy 'task_id' has been removed"
        )

    def test_end_work_has_named_id_parameter(self) -> None:
        """end_work has 'id' as the named task-identifier parameter (not 'task_id')."""
        sig = inspect.signature(end_work)
        assert "id" in sig.parameters, "end_work must have 'id' as named parameter — legacy 'task_id' has been removed"

    # --- StrId annotation ----------------------------------------------------

    def test_move_task_id_annotation_strid_based(self) -> None:
        """move_task 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(move_task)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, f"move_task 'id' annotation should include StrId, got {annotation!r}"

    def test_edit_task_id_annotation_strid_based(self) -> None:
        """edit_task 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(edit_task)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, f"edit_task 'id' annotation should include StrId, got {annotation!r}"

    def test_start_work_id_annotation_strid_based(self) -> None:
        """start_work 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(start_work)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, f"start_work 'id' annotation should include StrId, got {annotation!r}"

    def test_end_work_id_annotation_strid_based(self) -> None:
        """end_work 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(end_work)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, f"end_work 'id' annotation should include StrId, got {annotation!r}"


# ---------------------------------------------------------------------------
# TestFromAC_IdDirectPassthrough — behavioral proof (6 tests)
# ---------------------------------------------------------------------------


class TestFromAC_IdDirectPassthrough:
    """AC: id is passed directly to the engine without resolution indirection.

    Positive tests: calling with id=<value> operates on the correct task.
    Negative tests: calling with task_id=<value> raises TypeError — the legacy
    kwarg catch-all is gone, so unknown keyword arguments are now rejected.
    """

    # --- Positive: id routes to the correct task ----------------------------

    @pytest.mark.asyncio
    async def test_move_task_id_routes_to_correct_task(self, app_ctx_1198: AppContext) -> None:
        """move_task(id='1') moves task 1; proves id is used directly."""
        ctx = _make_ctx_1198(app_ctx_1198)
        result = await move_task(ctx, id="1", status="backlog")
        assert result.id == 1, f"Expected id=1 in result, got {result.id!r} — id not routed directly"

    @pytest.mark.asyncio
    async def test_edit_task_id_routes_to_correct_task(self, app_ctx_1198: AppContext) -> None:
        """edit_task(id='1') edits task 1 and returns it; proves id is used directly."""
        ctx = _make_ctx_1198(app_ctx_1198)
        result = await edit_task(ctx, id="1", append_body="probe-payload")
        assert result.id == 1, f"Expected id=1 in result, got {result.id!r} — id not routed directly"

    # --- Negative: legacy task_id= kwarg is rejected -----------------------

    @pytest.mark.asyncio
    async def test_move_task_rejects_legacy_task_id_kwarg(self, app_ctx_1198: AppContext) -> None:
        """move_task(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx_1198(app_ctx_1198)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await move_task(ctx, task_id="1", status="backlog")  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_edit_task_rejects_legacy_task_id_kwarg(self, app_ctx_1198: AppContext) -> None:
        """edit_task(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx_1198(app_ctx_1198)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await edit_task(ctx, task_id="1", append_body="x")  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_start_work_rejects_legacy_task_id_kwarg(self, app_ctx_1198: AppContext) -> None:
        """start_work(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx_1198(app_ctx_1198)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await start_work(ctx, task_id="1")  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_end_work_rejects_legacy_task_id_kwarg(self, app_ctx_1198: AppContext) -> None:
        """end_work(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx_1198(app_ctx_1198)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await end_work(ctx, task_id="1", note="done")  # type: ignore[call-arg]


# --- merged from tests/test_server_1199.py ---
"""Failing tests for removal of KANBAN_TOOLS_EXCLUDE / _apply_tool_exclusions (#1199).

AC coverage:
  - _apply_tool_exclusions function removed from server.py (td:1)
  - _apply_tool_exclusions call removed from app_lifespan (td:1)
  - Server starts and registers all tools normally (td:1) [regression guard]
  - outputSchema and _patch_params functionality preserved (td:1) [regression guard]
"""


from unittest.mock import MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import app_lifespan


# ---------------------------------------------------------------------------
# TestFromAC_FunctionRemoval
# AC: _apply_tool_exclusions function removed from server.py (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_LifespanCallRemoval:
    """app_lifespan must not invoke server.remove_tool for KANBAN_TOOLS_EXCLUDE."""

    @pytest.mark.asyncio
    async def test_lifespan_does_not_remove_tools_when_env_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With KANBAN_TOOLS_EXCLUDE set, lifespan never calls server.remove_tool.

        FAILS now: _apply_tool_exclusions IS called inside app_lifespan and it
        calls server.remove_tool("list_tasks") when the env var is set.
        PASSES after: builder removes the _apply_tool_exclusions call from
        app_lifespan so no tool removal can occur.
        """
        monkeypatch.setenv("KANBAN_TOOLS_EXCLUDE", "list_tasks")
        mock_engine = MagicMock()
        with patch("owlbear_mcp_kanban.server.KanbanEngine", return_value=mock_engine):
            server_mock = MagicMock()
            async with app_lifespan(server_mock) as _ctx:
                server_mock.remove_tool.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_OutputSchemaPreserved
# AC: Existing outputSchema and _patch_params functionality preserved (td:1)
# [regression guard — passes now; would fail if builder over-deletes]
# ---------------------------------------------------------------------------


"""Compatibility tests for MCP startup without copilot_auth (task #1317)."""


import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import app_lifespan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_auth_module(token: str = "copilot_tok_xyz") -> ModuleType:  # noqa: S107
    """Return a fake owlbear_knowledge.copilot_auth module."""
    mod = ModuleType("owlbear_knowledge.copilot_auth")
    mod.get_copilot_token = AsyncMock(return_value=token)  # type: ignore[attr-defined]
    mod.detect_editor_versions = MagicMock(  # type: ignore[attr-defined]
        return_value={"Editor-Version": "vscode/1.97.1"}
    )
    return mod


def _mock_llm_module() -> ModuleType:
    """Return a fake owlbear_knowledge.llm_extractor module."""
    mod = ModuleType("owlbear_knowledge.llm_extractor")
    mock_instance = MagicMock(name="LLMExtractorInstance")
    mod.LLMExtractor = MagicMock(  # type: ignore[attr-defined]
        name="LLMExtractorCls", return_value=mock_instance
    )
    return mod


# ---------------------------------------------------------------------------
# Autouse fixture: patches I/O-heavy constructors so app_lifespan runs fast
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_lifespan_deps() -> None:
    """Patch heavy I/O deps so app_lifespan runs without real DB or network."""
    with patch("owlbear_mcp_knowledge.server.QdrantVectorStore"):
        yield


# ---------------------------------------------------------------------------
# TestFromAC_LifespanNoCopilotAuth
# AC: copilot_auth not imported in app_lifespan
# ---------------------------------------------------------------------------


class TestFromAC_LifespanNoCopilotAuth:
    """app_lifespan does not import copilot_auth after removal."""

    @pytest.mark.asyncio
    async def test_copilot_auth_not_imported_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_copilot_token is NOT called when OWLBEAR_LLM_API_KEY is unset.

        In the new code (after #1318), the copilot_auth import branch is removed,
        so get_copilot_token is never invoked.

        Currently FAILS: current lifespan enters the copilot fallback branch and
        calls get_copilot_token when no API key env var is set.
        """
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        mock_auth = _mock_auth_module()
        mock_llm = _mock_llm_module()

        with patch.dict(
            sys.modules,
            {
                "owlbear_knowledge.copilot_auth": mock_auth,
                "owlbear_knowledge.llm_extractor": mock_llm,
            },
        ):
            async with app_lifespan(MagicMock()):
                pass

        # New code: copilot_auth branch removed — get_copilot_token never called.
        # Current code: enters else-branch, calls get_copilot_token → assertion FAILS.
        mock_auth.get_copilot_token.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_copilot_auth_module_absent_from_sys_modules_after_lifespan(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """owlbear_knowledge.copilot_auth is NOT in sys.modules after lifespan exits.

        AC1 postcondition: 'absent from sys.modules after lifespan completes'.
        Stronger than a getter-call check: catches any import (even without getter use).
        """
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Ensure copilot_auth is NOT pre-loaded so the check is meaningful.
        monkeypatch.delitem(sys.modules, "owlbear_knowledge.copilot_auth", raising=False)
        monkeypatch.delitem(sys.modules, "owlbear_knowledge", raising=False)

        async with app_lifespan(MagicMock()):
            pass

        assert "owlbear_knowledge.copilot_auth" not in sys.modules  # noqa: S101


# --- merged from tests/test_server_1358.py ---
"""Regression tests for legacy API key branch removal (task #1358)."""


import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import app_lifespan

_REPO_ROOT = Path(__file__).parent.parent
_SERVER_PY = _REPO_ROOT / "serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py"
_README = _REPO_ROOT / "serve/mcp-knowledge/README.md"
_MCP_KNOWLEDGE_TESTS = _REPO_ROOT / "serve/mcp-knowledge/tests"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_llm_mod(llm_cls: MagicMock | None = None) -> ModuleType:
    """Return a fake owlbear_knowledge.llm_extractor module."""
    mod = ModuleType("owlbear_knowledge.llm_extractor")
    mod.LLMExtractor = llm_cls or MagicMock(name="LLMExtractorCls")  # type: ignore[attr-defined]
    return mod


# ---------------------------------------------------------------------------
# Autouse fixture — patches heavy I/O deps so app_lifespan runs without real DB/network
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_lifespan_deps_1358() -> None:
    """Patch I/O-heavy constructors so app_lifespan can run without real resources."""
    with patch("owlbear_mcp_knowledge.server.QdrantVectorStore"):
        yield


# ---------------------------------------------------------------------------
# TestFromAC_ApiKeyBranchRemoved — AC1
# API key env vars do not reactivate LLM extractor wiring
# ---------------------------------------------------------------------------


class TestFromAC_ApiKeyBranchRemoved:
    """AC1: API key env vars no longer wire in LLM extractor components."""

    @pytest.mark.asyncio
    async def test_llmextractor_never_instantiated_when_both_keys_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLMExtractor.__init__ is never called even when both API key env vars are present.

        Currently FAILS: current code calls LLMExtractor() inside the if api_key: branch.
        """
        monkeypatch.setenv("OWLBEAR_LLM_API_KEY", "sk-primary")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fallback")
        mock_llm_cls = MagicMock(name="LLMExtractorCls")
        with patch.dict(
            sys.modules,
            {"owlbear_knowledge.llm_extractor": _make_llm_mod(mock_llm_cls)},
        ):
            async with app_lifespan(MagicMock()):
                pass
        mock_llm_cls.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_DeadImportsRemoved — AC2
# LLMExtractor lazy import and env-var reads absent from server.py source text
# ---------------------------------------------------------------------------


class TestFromAC_DeadImportsRemoved:
    """AC2: server.py source no longer references LLMExtractor or the removed env vars."""

    def test_server_source_no_llm_extractor_import(self) -> None:
        """server.py contains no reference to 'llm_extractor'.

        Currently FAILS: conditional 'from owlbear_knowledge.llm_extractor import LLMExtractor'
        is present inside the api_key branch at L536.
        """
        source = _SERVER_PY.read_text()
        assert "llm_extractor" not in source  # noqa: S101

    def test_server_source_no_owlbear_llm_api_key(self) -> None:
        """server.py contains no os.environ read for 'OWLBEAR_LLM_API_KEY'.

        Currently FAILS: the api_key branch reads this env var at L531.
        """
        source = _SERVER_PY.read_text()
        assert "OWLBEAR_LLM_API_KEY" not in source  # noqa: S101

    def test_server_source_no_openai_api_key(self) -> None:
        """server.py contains no os.environ read for 'OPENAI_API_KEY'.

        Currently FAILS: the api_key branch reads this as a fallback key at L532.
        """
        source = _SERVER_PY.read_text()
        assert "OPENAI_API_KEY" not in source  # noqa: S101


# ---------------------------------------------------------------------------
# TestFromAC_ReadmeCleanup — AC3
# README.md no longer documents the removed API key env vars
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeCleanup:
    """AC3: README.md env-var table row for LLM API keys has been removed."""

    def test_readme_no_owlbear_llm_api_key(self) -> None:
        """README.md does not mention OWLBEAR_LLM_API_KEY.

        Currently FAILS: README configuration table includes this env var at L43.
        """
        readme = _README.read_text()
        assert "OWLBEAR_LLM_API_KEY" not in readme  # noqa: S101

    def test_readme_no_openai_api_key(self) -> None:
        """README.md does not mention OPENAI_API_KEY as an LLM key fallback.

        Currently FAILS: README configuration table includes this env var at L44.
        """
        readme = _README.read_text()
        assert "OPENAI_API_KEY" not in readme  # noqa: S101


# ---------------------------------------------------------------------------
# TestFromAC_DeadTestsRemoved — AC4
# Dead test files asserting API-key-present behavior have been deleted
# ---------------------------------------------------------------------------


class TestFromAC_DeadTestsRemoved:
    """AC4: test files covering the removed API key path no longer exist."""

    def test_copilot_server_wiring_888_file_deleted(self) -> None:
        """test_copilot_server_wiring_888.py has been deleted from serve/mcp-knowledge/tests/.

        Currently FAILS: the file exists and covers the now-removed API key path.
        """
        dead_file = _MCP_KNOWLEDGE_TESTS / "test_copilot_server_wiring_888.py"
        assert not dead_file.exists()  # noqa: S101

    def test_llmextractor_wiring_876_file_deleted(self) -> None:
        """test_llmextractor_wiring_876.py has been deleted from serve/mcp-knowledge/tests/.

        Currently FAILS: the file exists and tests conditional LLMExtractor wiring
        that the removed api_key branch enabled.
        """
        dead_file = _MCP_KNOWLEDGE_TESTS / "test_llmextractor_wiring_876.py"
        assert not dead_file.exists()  # noqa: S101
