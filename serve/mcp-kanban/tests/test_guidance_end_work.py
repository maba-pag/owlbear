"""Integration tests for guidance wiring in end_work MCP tool (task #989).

RED phase — tests fail until server.py wires guidance into end_work.

AC coverage:
- end_work(outcome="block") returns guidance with DR-required message
- end_work(outcome="block") removes block:user tag if present
- end_work(outcome="success") returns guidance with commit reminder
- end_work(outcome="fail") → empty guidance
- end_work(outcome="reject") → empty guidance
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, end_work

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
    """AppContext with a board containing one claimed task at status=in-progress."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Alpha task", status="in-progress", priority="important")
    engine.list_tasks()  # populate id→filename cache
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkGuidanceIntegration
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkGuidanceIntegration:
    """Integration tests for guidance wiring in MCP end_work tool (AC #989).

    All tests fail in RED because server.py does not yet call collect_guidance.
    """

    @pytest.mark.asyncio
    async def test_block_outcome_returns_dr_guidance(self, app_ctx: AppContext) -> None:
        """end_work(outcome='block') → guidance contains DR-required message."""
        ctx = _make_ctx(app_ctx)
        result = await end_work(
            ctx,
            id="1",
            note="blocking for dependency",
            outcome="block",
            block_reason="waiting on infra",
        )
        assert len(result.guidance) > 0, (
            f"Expected non-empty guidance for block outcome, got {result.guidance!r}"
        )
        assert "Decision Request" in result.guidance[0], (
            f"Expected 'Decision Request' in guidance, got {result.guidance[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_block_outcome_removes_block_user_tag_if_present(
        self, app_ctx: AppContext
    ) -> None:
        """end_work(outcome='block') on task with block:user → block:user removed."""
        # Setup: add block:user tag before end_work
        app_ctx.engine.edit_task("1", add_tags=["block:user"])
        ctx = _make_ctx(app_ctx)
        result = await end_work(
            ctx,
            id="1",
            note="agent re-blocking",
            outcome="block",
            block_reason="stale dependency",
        )
        assert "block:user" not in result.tags, (
            f"Expected block:user removed after end_work/block, tags={result.tags!r}"
        )

    @pytest.mark.asyncio
    async def test_success_outcome_returns_commit_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """end_work(outcome='success') → guidance contains commit reminder."""
        ctx = _make_ctx(app_ctx)
        result = await end_work(
            ctx,
            id="1",
            note="all done",
            outcome="success",
        )
        assert len(result.guidance) > 0, (
            f"Expected non-empty guidance for success outcome, got {result.guidance!r}"
        )
        assert "commit" in result.guidance[0].lower(), (
            f"Expected 'commit' in guidance message, got {result.guidance[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_fail_outcome_returns_empty_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """end_work(outcome='fail') → empty guidance."""
        ctx = _make_ctx(app_ctx)
        result = await end_work(
            ctx,
            id="1",
            note="failed attempt",
            outcome="fail",
        )
        assert result.guidance == [], (
            f"Expected empty guidance for fail outcome, got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_reject_outcome_returns_empty_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """end_work(outcome='reject') may include status-transition guidance."""
        ctx = _make_ctx(app_ctx)
        result = await end_work(
            ctx,
            id="1",
            note="rejecting to backlog",
            outcome="reject",
            move_to="backlog",
        )
        assert result.guidance, (
            f"Expected non-empty guidance for reject outcome, got {result.guidance!r}"
        )
        assert "Status skip" in result.guidance[0], (
            f"Expected status-skip guidance for reject outcome, got {result.guidance!r}"
        )
