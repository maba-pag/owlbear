"""RED tests — dead TypeError fallback chain removal in MCP server end_work and move_task (#1126).

AC coverage:
- AC1: end_work 'except TypeError:' fallback chain removed — view.end_work called exactly
  once; TypeError propagates immediately (call_count == 1, not 3 with two nested fallbacks)
- AC2: move_task 'except TypeError:' fallback chain removed — view.move_task called exactly
  once; TypeError propagates immediately (call_count == 1, not 2 with one nested fallback)

- AC3: Structural regression — 'except TypeError' blocks absent from server.py (both sites)

All tests must FAIL (RED phase).

FAIL paths summary:
- call_count tests (AC1/AC2): current server.py catches TypeError from the primary
  view call and retries with fewer kwargs.  view.end_work is called 3x and
  view.move_task is called 2x before TypeError escapes.  Assertions call_count == 1
  therefore fail (3 != 1 and 2 != 1).
- Boundary test (AC1): same call-count failure for the null-archival-args edge of the
  kwargs set — primary call still passes archival_reason=None, archival_refs=None as
  kwargs, so the TypeError handler fires and fallbacks run identically.
- Source inspection test (AC3): server.py contains 'except TypeError' at two sites
  (move_task ~L285, end_work ~L421).  Assertion 'except TypeError' not in source fails.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import owlbear_mcp_kanban.server as _server_mod
from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import (
    AppContext,
    end_work,
    move_task,
)

# ---------------------------------------------------------------------------
# Board config — minimal flat schema accepted by BoardConfig
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx_todo(tmp_path: Path) -> AppContext:
    """AppContext with one unclaimed task at todo (for move_task tests)."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Test task", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_claimed(tmp_path: Path) -> AppContext:
    """AppContext with one claimed task at in-progress (for end_work tests)."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Beta task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_DeadTypeErrorFallback
# ---------------------------------------------------------------------------


class TestFromAC_DeadTypeErrorFallback:
    """Dead TypeError fallback chains must be removed from end_work and move_task."""

    # ------------------------------------------------------------------
    # AC1 — end_work: TypeError propagates immediately without fallback
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_end_work_typeerror_propagates_after_one_call(
        self, app_ctx_claimed: AppContext
    ) -> None:
        """AC1: view.end_work raising TypeError must propagate immediately (call_count == 1).

        FAIL path (RED): current code has two nested fallback blocks inside the
        'except TypeError:' handler.  The primary call and both fallbacks each invoke
        view.end_work, so the mock is called 3x total.  call_count == 1 fails
        because call_count is 3.

        Expected (GREEN): 'except TypeError' block removed; TypeError propagates on
        the primary call alone.  call_count == 1.
        """
        ctx = _make_ctx(app_ctx_claimed)
        mock_view = MagicMock()
        mock_view.end_work.side_effect = TypeError("unexpected kwarg: archival_refs")

        with (
            patch("owlbear_mcp_kanban.server._agent_view_for", return_value=mock_view),
            pytest.raises(TypeError),
        ):
            await end_work(
                ctx,
                task_id="1",
                outcome="success",
                note="done",
                move_to=None,
                block_reason=None,
                archival_reason="completed",
                archival_refs=[999],
            )

        assert mock_view.end_work.call_count == 1  # FAILS NOW: call_count is 3

    @pytest.mark.asyncio
    async def test_end_work_typeerror_null_archival_args_propagates_after_one_call(
        self, app_ctx_claimed: AppContext
    ) -> None:
        """AC1 boundary: null archival args still triggers the fallback chain in current code.

        The primary call always passes archival_reason=None, archival_refs=None as kwargs.
        If view.end_work raises TypeError, the handler fires regardless of arg values.
        The call_count must be 1 (not 3) after the fallback chain is removed.

        FAIL path (RED): same 3-call sequence as above despite None archival args.
        """
        ctx = _make_ctx(app_ctx_claimed)
        mock_view = MagicMock()
        mock_view.end_work.side_effect = TypeError("unexpected kwarg: archival_refs")

        with (
            patch("owlbear_mcp_kanban.server._agent_view_for", return_value=mock_view),
            pytest.raises(TypeError),
        ):
            await end_work(
                ctx,
                task_id="1",
                outcome="fail",
                note=None,
                move_to=None,
                block_reason=None,
                archival_reason=None,
                archival_refs=None,
            )

        assert mock_view.end_work.call_count == 1  # FAILS NOW: call_count is 3

    # ------------------------------------------------------------------
    # AC2 — move_task: TypeError propagates immediately without fallback
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_move_task_typeerror_propagates_after_one_call(
        self, app_ctx_todo: AppContext
    ) -> None:
        """AC2: view.move_task raising TypeError must propagate immediately (call_count == 1).

        FAIL path (RED): current code has one nested fallback inside
        'contextlib.suppress(NotImplementedError)'.  That suppress does NOT cover
        TypeError, so the second call's TypeError escapes — but two calls already
        happened.  call_count == 1 fails because call_count is 2.

        Expected (GREEN): 'except TypeError' block removed; TypeError propagates on
        the primary call alone.  call_count == 1.
        """
        ctx = _make_ctx(app_ctx_todo)
        mock_view = MagicMock()
        mock_view.move_task.side_effect = TypeError("unexpected kwarg: archival_refs")

        with (
            patch("owlbear_mcp_kanban.server._agent_view_for", return_value=mock_view),
            pytest.raises(TypeError),
        ):
            await move_task(
                ctx,
                task_id="1",
                status="done",
                archival_reason="completed",
                archival_refs=[999],
            )

        assert mock_view.move_task.call_count == 1  # FAILS NOW: call_count is 2

    # ------------------------------------------------------------------
    # AC3 — structural: 'except TypeError' absent from server source
    # ------------------------------------------------------------------

    def test_no_except_typeerror_in_server_source(self) -> None:
        """AC3: After cleanup, 'except TypeError' must not appear anywhere in server.py.

        FAIL path (RED): server.py contains 'except TypeError' at two sites —
        move_task (~L285) and end_work (~L421).  The assertion fails because the
        string is found.

        Expected (GREEN): both 'except TypeError' blocks removed.  String absent
        from source.  Assertion passes.

        Structural evidence requirement: behavioral tests prove the fallbacks are
        unreachable but cannot prove the dead branches are actually gone from the
        source.  This test satisfies that evidence gap (see review-dead-code-
        structural-evidence).
        """
        source = Path(_server_mod.__file__).read_text(encoding="utf-8")
        assert "except TypeError" not in source  # FAILS NOW: 2 instances present
