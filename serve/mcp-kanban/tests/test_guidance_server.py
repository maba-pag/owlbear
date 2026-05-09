"""Integration tests for guidance resilience and suppress contract (task #980).

RED phase — tests verify the suppress(Exception) contract around guidance calls
in edit_task and end_work: a failing collect_guidance must never propagate and
must never block a successful tool response.

AC coverage:
- edit_task: guidance failure suppressed → task returned, guidance=[]
- edit_task: collect_guidance called with correct operation ("edit_task") and task
- end_work(block): guidance failure suppressed → task returned, guidance=[]
- end_work(block): block:user removed BEFORE guidance check → DR message present
  even when task originally had block:user tag
- end_work(success): collect_guidance called with outcome="success" kwarg
- end_work(fail): collect_guidance called (returns empty for fail outcome)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, edit_task, end_work

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
def app_ctx_edit(tmp_path: Path) -> AppContext:
    """AppContext with one task at todo — for edit_task tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Alpha task", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_end(tmp_path: Path) -> AppContext:
    """AppContext with one claimed task at in-progress — for end_work tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Beta task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_GuidanceSuppressContract
# ---------------------------------------------------------------------------


class TestFromAC_GuidanceSuppressContract:
    """Verify that guidance exceptions are suppressed and never block tool success.

    AC: "All guidance calls wrapped in contextlib.suppress(Exception) —
         guidance is advisory, never blocks tool success."
    """

    @pytest.mark.asyncio
    async def test_edit_task_guidance_exception_suppressed(
        self, app_ctx_edit: AppContext
    ) -> None:
        """collect_guidance raising in edit_task → task still returned, guidance=[]."""
        ctx = _make_ctx(app_ctx_edit)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            side_effect=RuntimeError("boom"),
        ):
            result = await edit_task(ctx, id="1", priority="critical")
        assert result.id is not None, (
            "Expected valid KanbanTask returned despite guidance failure"
        )
        assert result.guidance == [], (
            f"Expected empty guidance when collect_guidance raises, got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_end_work_guidance_exception_suppressed(
        self, app_ctx_end: AppContext
    ) -> None:
        """collect_guidance raising in end_work → task still returned, guidance=[]."""
        ctx = _make_ctx(app_ctx_end)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            side_effect=RuntimeError("boom"),
        ):
            result = await end_work(ctx, id="1", note="done", outcome="success")
        assert result.id is not None, (
            "Expected valid KanbanTask returned despite guidance failure"
        )
        assert result.guidance == [], (
            f"Expected empty guidance when collect_guidance raises, got {result.guidance!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GuidanceCallWiring
# ---------------------------------------------------------------------------


class TestFromAC_GuidanceCallWiring:
    """Verify collect_guidance is called with correct operation and kwargs.

    AC: edit_task calls collect_guidance("edit_task", None, task);
        end_work calls collect_guidance("end_work", None, task, outcome=outcome).
    """

    @pytest.mark.asyncio
    async def test_edit_task_calls_collect_guidance_with_edit_task_operation(
        self, app_ctx_edit: AppContext
    ) -> None:
        """edit_task invokes collect_guidance("edit_task", None, task)."""
        ctx = _make_ctx(app_ctx_edit)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=[]
        ) as mock_cg:
            await edit_task(ctx, id="1", priority="critical")
        mock_cg.assert_called_once_with("edit_task", None, ANY)

    @pytest.mark.asyncio
    async def test_end_work_success_calls_collect_guidance_with_outcome_kwarg(
        self, app_ctx_end: AppContext
    ) -> None:
        """end_work(success) invokes collect_guidance("end_work", None, task, outcome="success")."""
        ctx = _make_ctx(app_ctx_end)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=[]
        ) as mock_cg:
            await end_work(ctx, id="1", note="all done", outcome="success")
        mock_cg.assert_called_once_with("end_work", None, ANY, outcome="success")

    @pytest.mark.asyncio
    async def test_end_work_fail_calls_collect_guidance_with_outcome_kwarg(
        self, app_ctx_end: AppContext
    ) -> None:
        """end_work(fail) invokes collect_guidance("end_work", None, task, outcome="fail")."""
        ctx = _make_ctx(app_ctx_end)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=[]
        ) as mock_cg:
            await end_work(ctx, id="1", note="failed", outcome="fail")
        mock_cg.assert_called_once_with("end_work", None, ANY, outcome="fail")


# ---------------------------------------------------------------------------
# TestFromAC_BlockUserTagOrderingInEndWork
# ---------------------------------------------------------------------------


class TestFromAC_BlockUserTagOrderingInEndWork:
    """Verify block:user removal happens BEFORE guidance collection in end_work(block).

    AC: "Remove block:user tag via separate engine.edit_task call before guidance collection."
    When block:user is removed before collect_guidance, the task passed to
    _block_guidance lacks block:user → DR message is emitted (not suppressed).
    If ordering were reversed, _block_guidance would see block:user and return [].
    """

    @pytest.mark.asyncio
    async def test_end_work_block_with_block_user_tag_emits_dr_guidance(
        self, app_ctx_end: AppContext
    ) -> None:
        """end_work(block) on task with block:user → DR guidance emitted (tag removed first).

        Verifies ordering: block:user is stripped before collect_guidance runs,
        so _block_guidance sees no block:user and returns the DR message.
        """
        app_ctx_end.engine.edit_task("1", add_tags=["block:user"])
        ctx = _make_ctx(app_ctx_end)
        result = await end_work(
            ctx,
            id="1",
            note="agent re-blocking",
            outcome="block",
            block_reason="dependency on external service",
        )
        assert "block:user" not in result.tags, (
            f"Expected block:user removed, tags={result.tags!r}"
        )
        assert len(result.guidance) > 0, (
            f"Expected DR guidance emitted (block:user removed before guidance check), "
            f"got guidance={result.guidance!r}"
        )
        assert any("Decision Request" in msg for msg in result.guidance), (
            f"Expected 'Decision Request' in guidance, got {result.guidance!r}"
        )
