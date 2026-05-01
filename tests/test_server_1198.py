"""Tests for #1198: Remove legacy compat code from MCP server.

AC line (td:1):
- Tool functions use id: StrId directly — no resolution indirection

Retry cycle — strengthened per reviewer required follow-up:
- TestFromAC_LegacyCompatRemoval: VAR_KEYWORD absence (original 4 tests)
- TestFromAC_IdParameterContract: named 'id' + StrId annotation for all 4 tools
- TestFromAC_IdDirectPassthrough: behavioral proof via real board + TypeError rejection
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, edit_task, end_work, move_task, start_work

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
def app_ctx(tmp_path: Path) -> AppContext:
    """AppContext backed by a real board with one task at 'research'."""
    kanban_dir = _make_board(tmp_path)
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
        assert "id" in sig.parameters, (
            "move_task must have 'id' as named parameter — legacy 'task_id' has been removed"
        )

    def test_edit_task_has_named_id_parameter(self) -> None:
        """edit_task has 'id' as the named task-identifier parameter (not 'task_id')."""
        sig = inspect.signature(edit_task)
        assert "id" in sig.parameters, (
            "edit_task must have 'id' as named parameter — legacy 'task_id' has been removed"
        )

    def test_start_work_has_named_id_parameter(self) -> None:
        """start_work has 'id' as the named task-identifier parameter (not 'task_id')."""
        sig = inspect.signature(start_work)
        assert "id" in sig.parameters, (
            "start_work must have 'id' as named parameter — legacy 'task_id' has been removed"
        )

    def test_end_work_has_named_id_parameter(self) -> None:
        """end_work has 'id' as the named task-identifier parameter (not 'task_id')."""
        sig = inspect.signature(end_work)
        assert "id" in sig.parameters, (
            "end_work must have 'id' as named parameter — legacy 'task_id' has been removed"
        )

    # --- StrId annotation ----------------------------------------------------

    def test_move_task_id_annotation_strid_based(self) -> None:
        """move_task 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(move_task)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, (
            f"move_task 'id' annotation should include StrId, got {annotation!r}"
        )

    def test_edit_task_id_annotation_strid_based(self) -> None:
        """edit_task 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(edit_task)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, (
            f"edit_task 'id' annotation should include StrId, got {annotation!r}"
        )

    def test_start_work_id_annotation_strid_based(self) -> None:
        """start_work 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(start_work)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, (
            f"start_work 'id' annotation should include StrId, got {annotation!r}"
        )

    def test_end_work_id_annotation_strid_based(self) -> None:
        """end_work 'id' annotation includes StrId — not a plain str or int."""
        sig = inspect.signature(end_work)
        annotation = str(sig.parameters["id"].annotation)
        assert "StrId" in annotation, (
            f"end_work 'id' annotation should include StrId, got {annotation!r}"
        )


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
    async def test_move_task_id_routes_to_correct_task(self, app_ctx: AppContext) -> None:
        """move_task(id='1') moves task 1; proves id is used directly."""
        ctx = _make_ctx(app_ctx)
        result = await move_task(ctx, id="1", status="backlog")
        assert result.id == 1, (
            f"Expected id=1 in result, got {result.id!r} — id not routed directly"
        )

    @pytest.mark.asyncio
    async def test_edit_task_id_routes_to_correct_task(self, app_ctx: AppContext) -> None:
        """edit_task(id='1') edits task 1 and returns it; proves id is used directly."""
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", append_body="probe-payload")
        assert result.id == 1, (
            f"Expected id=1 in result, got {result.id!r} — id not routed directly"
        )

    # --- Negative: legacy task_id= kwarg is rejected -----------------------

    @pytest.mark.asyncio
    async def test_move_task_rejects_legacy_task_id_kwarg(self, app_ctx: AppContext) -> None:
        """move_task(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx(app_ctx)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await move_task(ctx, task_id="1", status="backlog")  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_edit_task_rejects_legacy_task_id_kwarg(self, app_ctx: AppContext) -> None:
        """edit_task(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx(app_ctx)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await edit_task(ctx, task_id="1", append_body="x")  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_start_work_rejects_legacy_task_id_kwarg(self, app_ctx: AppContext) -> None:
        """start_work(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx(app_ctx)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await start_work(ctx, task_id="1")  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_end_work_rejects_legacy_task_id_kwarg(self, app_ctx: AppContext) -> None:
        """end_work(task_id=...) raises TypeError — **legacy catch-all is gone."""
        ctx = _make_ctx(app_ctx)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await end_work(ctx, task_id="1", note="done")  # type: ignore[call-arg]
