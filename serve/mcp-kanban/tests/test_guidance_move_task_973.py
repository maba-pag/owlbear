"""Integration tests for guidance wiring in move_task MCP tool (task #991).

RED phase — tests fail until server.py wires guidance + pre-read into move_task.

AC coverage:
- move_task forward skip >1 slot → guidance with forward-skip message
- move_task forward skip exactly 1 slot → empty guidance
- move_task backward move → empty guidance
- move_task to 'archived' → empty guidance (excluded from skip detection)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, move_task

# ---------------------------------------------------------------------------
# Board fixture helpers
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """AppContext with a board containing tasks at different statuses."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    # Task 1: research (for forward-skip tests)
    engine.create_task("Alpha task", status="research", priority="important")
    # Task 2: todo (for backward move test)
    engine.create_task("Beta task", status="todo", priority="important")
    # Task 3: done (for archive test — already at end of pipeline)
    engine.create_task("Gamma task", status="done", priority="important")
    engine.list_tasks()  # populate id→filename cache
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskGuidanceIntegration
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskGuidanceIntegration:
    """Integration tests for guidance wiring in MCP move_task tool (AC #991).

    All tests fail in RED because server.py does not yet pre-read or wire guidance.
    """

    @pytest.mark.asyncio
    async def test_forward_skip_more_than_one_slot_returns_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """move_task forward skip >1 slot → guidance with skip message."""
        ctx = _make_ctx(app_ctx)
        # Task 1 is at "research"; skip to "todo" (2 slots: research→backlog→todo)
        result = await move_task(ctx, task_id="1", status="todo")
        assert len(result.guidance) > 0, (
            f"Expected guidance for >1-slot skip (research→todo), got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_forward_skip_one_slot_returns_empty_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """move_task forward skip exactly 1 slot → empty guidance."""
        ctx = _make_ctx(app_ctx)
        # Task 1 is at "research"; advance to "backlog" (1 slot)
        result = await move_task(ctx, task_id="1", status="backlog")
        assert result.guidance == [], (
            f"Expected empty guidance for 1-slot move (research→backlog), got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_backward_move_returns_empty_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """move_task backward move → empty guidance."""
        ctx = _make_ctx(app_ctx)
        # Task 2 is at "todo"; move back to "backlog"
        result = await move_task(ctx, task_id="2", status="backlog")
        assert result.guidance == [], (
            f"Expected empty guidance for backward move (todo→backlog), got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_archive_move_returns_empty_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """move_task to 'archived' → empty guidance (archived excluded from skip detection)."""
        ctx = _make_ctx(app_ctx)
        # Task 3 is at "done"; archive it
        result = await move_task(ctx, task_id="3", status="archived")
        assert result.guidance == [], (
            f"Expected empty guidance for archive move, got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_forward_skip_guidance_references_from_and_to_status(
        self, app_ctx: AppContext
    ) -> None:
        """Forward-skip guidance message references both source and target status."""
        ctx = _make_ctx(app_ctx)
        result = await move_task(ctx, task_id="1", status="todo")
        assert len(result.guidance) > 0
        assert "research" in result.guidance[0], (
            f"Expected 'research' in skip message, got {result.guidance[0]!r}"
        )
        assert "todo" in result.guidance[0], (
            f"Expected 'todo' in skip message, got {result.guidance[0]!r}"
        )
