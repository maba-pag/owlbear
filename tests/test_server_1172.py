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

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, move_task

# ---------------------------------------------------------------------------
# Board config — post-Brief-C list[str] statuses (flat, no dict-form)
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


class TestFromAC_StatusNamesDictFormBug:
    """Contract tests for the server.py L481 status_names dict-form bug (#1172).

    All integration tests force the legacy L481 path (agent_view=None).
    All tests fail with the current code: the dict-subscript ``s["name"]``
    raises ``TypeError`` on ``list[str]`` statuses, which is silently caught
    by ``contextlib.suppress(Exception)``.  As a result, ``collect_guidance``
    is never reached and ``result.guidance`` is always ``[]``.
    """

    # -- Happy path: forward-skip guidance is populated --------------------

    @pytest.mark.asyncio
    async def test_forward_skip_more_than_one_slot_returns_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """move_task forward-skip >1 slot returns non-empty guidance (fallback path).

        Task 1 is at 'research'; moving to 'todo' skips 'backlog' (2-slot jump).
        FAILS: TypeError at L481 swallowed → guidance stays [].
        """
        ctx = _make_ctx(app_ctx)
        result = await move_task(ctx, task_id="1", status="todo")
        assert len(result.guidance) > 0, (
            f"Expected non-empty guidance for research→todo skip, got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_forward_skip_guidance_contains_source_status(
        self, app_ctx: AppContext
    ) -> None:
        """Forward-skip guidance message references the source status name.

        FAILS: guidance is [] due to suppressed TypeError at L481.
        """
        ctx = _make_ctx(app_ctx)
        result = await move_task(ctx, task_id="1", status="todo")
        assert len(result.guidance) > 0, (
            "No guidance returned — TypeError at L481 still suppressed"
        )
        assert "research" in result.guidance[0], (
            f"Expected source status 'research' in guidance, got {result.guidance[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_forward_skip_guidance_contains_target_status(
        self, app_ctx: AppContext
    ) -> None:
        """Forward-skip guidance message references the target status name.

        FAILS: guidance is [] due to suppressed TypeError at L481.
        """
        ctx = _make_ctx(app_ctx)
        result = await move_task(ctx, task_id="1", status="todo")
        assert len(result.guidance) > 0, (
            "No guidance returned — TypeError at L481 still suppressed"
        )
        assert "todo" in result.guidance[0], (
            f"Expected target status 'todo' in guidance, got {result.guidance[0]!r}"
        )

    # -- Error path: collect_guidance must be reachable --------------------

    @pytest.mark.asyncio
    async def test_collect_guidance_called_with_list_str_status_names(
        self, app_ctx: AppContext
    ) -> None:
        """collect_guidance is reached and receives status_names as list[str].

        FAILS: TypeError at L481 fires before collect_guidance is reached →
        mock is never called.
        """
        ctx = _make_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=[]
        ) as mock_cg:
            await move_task(ctx, task_id="1", status="todo")

        assert mock_cg.called, (
            "collect_guidance was never called — TypeError at L481 is still suppressed"
        )
        _, kwargs = mock_cg.call_args
        status_names = kwargs.get("status_names", [])
        assert isinstance(status_names, list), (
            f"Expected status_names to be list, got {type(status_names)!r}"
        )
        assert all(isinstance(s, str) for s in status_names), (
            f"Expected status_names to be list[str], got {status_names!r}"
        )

    # -- Boundary: larger skip also triggers guidance ----------------------

    @pytest.mark.asyncio
    async def test_four_slot_forward_skip_returns_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """move_task with a 4-slot skip (research→review) also returns guidance.

        Verifies the fix works for skips larger than the minimum 2-slot case.
        FAILS: TypeError at L481 swallowed, guidance is always [].
        """
        ctx = _make_ctx(app_ctx)
        # research(0) → review(4): delta=4, 3 columns skipped
        result = await move_task(ctx, task_id="1", status="review")
        assert len(result.guidance) > 0, (
            f"Expected skip guidance for research→review (4 slots), got {result.guidance!r}"
        )

    # -- AC 3 (strict): collect_guidance receives exact board status list ---

    @pytest.mark.asyncio
    async def test_collect_guidance_receives_exact_board_status_list(
        self, app_ctx: AppContext
    ) -> None:
        """collect_guidance is called with status_names equal to the board's ordered list.

        Uses ``kwargs["status_names"]`` (no default) so the test FAILS if the kwarg
        is omitted.  Asserts the exact value — not just type — so it FAILS if
        contents differ or ordering changes.
        """
        ctx = _make_ctx(app_ctx)
        expected = list(app_ctx.engine.board_config().statuses)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=[]
        ) as mock_cg:
            await move_task(ctx, task_id="1", status="todo")

        assert mock_cg.called, (
            "collect_guidance was never called — fallback path not reached"
        )
        _, kwargs = mock_cg.call_args
        # KeyError here if status_names kwarg was omitted — intentional, no default
        actual = kwargs["status_names"]
        assert actual == expected, (
            f"status_names mismatch: expected {expected!r}, got {actual!r}"
        )

    # -- AC 4: collect_guidance return value is wired to result.guidance ----

    @pytest.mark.asyncio
    async def test_collect_guidance_return_value_assigned_to_result_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """result.guidance is set to the return value of collect_guidance.

        Mocks collect_guidance to return a sentinel list and asserts the
        sentinel propagates to result.guidance.  Fails if the return value
        is not assigned (e.g. the assignment line is removed or broken).
        """
        sentinel = ["sentinel-guidance-item"]
        ctx = _make_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=sentinel
        ):
            result = await move_task(ctx, task_id="1", status="todo")

        assert result.guidance == sentinel, (
            f"result.guidance should equal sentinel {sentinel!r}, got {result.guidance!r}"
        )
