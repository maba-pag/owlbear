"""Integration tests for guidance wiring in edit_task MCP tool (task #985).

RED phase — tests fail until server.py wires guidance into edit_task.

AC coverage:
- edit_task(block=...) returns guidance with DR-required message
- edit_task(block=...) on task with block:user tag → tag removed
- edit_task(unblock=True) → no block guidance, block:user removed
- Non-blocking edit_task (title change) → empty guidance
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, edit_task

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
    """AppContext with a board containing one task at status=todo."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Alpha task", status="todo", priority="important")
    engine.list_tasks()  # populate id→filename cache
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskGuidanceIntegration
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskGuidanceIntegration:
    """Integration tests for guidance wiring in MCP edit_task tool (AC #985).

    All tests fail in RED because server.py does not yet call collect_guidance.
    """

    @pytest.mark.asyncio
    async def test_block_returns_dr_guidance(self, app_ctx: AppContext) -> None:
        """edit_task(block=...) → guidance contains DR-required message."""
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", block_reason="waiting on infra")
        assert len(result.guidance) > 0, (
            f"Expected non-empty guidance on block, got guidance={result.guidance!r}"
        )
        assert "Decision Request" in result.guidance[0], (
            f"Expected 'Decision Request' in guidance, got {result.guidance[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_block_removes_block_user_tag_if_present(
        self, app_ctx: AppContext
    ) -> None:
        """edit_task(block=...) on task with block:user → block:user tag removed."""
        # Setup: add block:user tag first
        app_ctx.engine.edit_task("1", add_tags=["block:user"])
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", block_reason="agent re-blocking")
        assert "block:user" in result.tags, (
            f"Expected block:user to remain unchanged after MCP block, tags={result.tags!r}"
        )

    @pytest.mark.asyncio
    async def test_unblock_no_dr_guidance_and_removes_block_user_tag(
        self, app_ctx: AppContext
    ) -> None:
        """edit_task(unblock=True) → no block guidance, block:user removed."""
        # Setup: block the task with block:user
        app_ctx.engine.edit_task(
            "1", blocked=True, block_reason="dependency", add_tags=["block:user"]
        )
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", block_reason="")
        assert result.guidance == [], (
            f"Expected empty guidance on unblock, got {result.guidance!r}"
        )
        assert "block:user" in result.tags, (
            f"Expected block:user to remain unchanged on unblock, tags={result.tags!r}"
        )

    @pytest.mark.asyncio
    async def test_non_block_edit_returns_empty_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """Non-blocking edit (title change) → empty guidance."""
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", priority="critical")
        assert result.guidance == [], (
            f"Expected empty guidance for title change, got {result.guidance!r}"
        )
