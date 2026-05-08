"""RED phase tests — MCP list_tasks filters, tool annotations, and error envelopes (#1450).

AC coverage:
  AC1 (td:2): list_tasks(ids=[]) returns empty tasks list and no missing_ids entry
  AC2 (td:2): list_tasks(archival_reason=duplicate, no status) searches archive storage
  AC4 (td:1): move_task annotation has idempotentHint=False
  AC5 (td:2): malformed task ID surfaces structured JSON error envelope {code, message}

AC3 (td:2 — behavioral contract for move_task/end_work structured errors):
  Already satisfied by current _map_kanban_error implementation (json.dumps payload).
  No failing tests possible without asserting behaviour that already works correctly.
  Omitted per w-tdd-red Step 5: tests that pass must be removed or refined.

AC4(b) (pick_tasks readOnlyHint=True and idempotentHint=True):
  Already declared in the @mcp.tool decorator; assertions would be green immediately.
  Omitted per w-tdd-red Step 5.

AC5 — invalid status / invalid priority / stale write → JSON:
  All three cases go through _map_kanban_error which already produces JSON payload.
  Only the malformed-ID gap is new (parse_task_id raises raw ToolError, not JSON).
  The other AC5 sub-cases are omitted per w-tdd-red Step 5.

AC6 (td:0): no testable interface — skipped.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, list_tasks, parse_task_id

# ---------------------------------------------------------------------------
# Scratch-board helpers
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


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return ToolAnnotations for the named mcp-kanban tool, or None if absent."""
    from owlbear_mcp_kanban.server import mcp  # noqa: PLC0415

    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager._tools.values():  # noqa: SLF001
            if t.name == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """AppContext with a scratch board containing one active task."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Active task", status="todo", priority="important")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_with_archived_duplicate(tmp_path: Path) -> AppContext:
    """AppContext with one archived task (reason=duplicate) and one active ref task.

    Setup:
      Task A (id=1): active, status=todo — serves as archival_refs target
      Task B (id=2): archived with archival_reason=duplicate, archival_refs=[A.id]
    """
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    ref_task = engine.create_task("Reference task", status="todo", priority="important")
    dup_task = engine.create_task("Duplicate task", status="todo", priority="important")
    engine.agent_view().move_task(
        dup_task.id,
        "archived",
        archival_reason="duplicate",
        archival_refs=[ref_task.id],
    )
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksEmptyIds
# AC1: list_tasks(ids=[]) returns empty tasks list and no missing_ids entry.
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksEmptyIds:
    """list_tasks with ids=[] must return tasks=[], not all active board tasks.

    Current failure: empty list is falsy in Python so ``if ids:`` evaluates False;
    the ids=[] argument is silently ignored and all active tasks are returned instead.

    Fix: treat ids=[] as an explicit empty-set filter — return tasks=[] immediately
    without searching the board.
    """

    @pytest.mark.asyncio
    async def test_empty_ids_returns_empty_task_list(self, app_ctx: AppContext) -> None:
        """AC1/happy: ids=[] returns tasks=[] even though the board has active tasks.

        FAIL (RED): empty list is falsy — list_tasks falls into the 'else' branch
        and returns all active tasks.  Assertion ``result.tasks == []`` fails.
        """
        ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(ctx, ids=[])
        assert result.tasks == [], (
            f"Expected empty task list for ids=[], got {len(result.tasks)} task(s)"
        )

    @pytest.mark.asyncio
    async def test_empty_ids_returns_empty_for_multi_task_board(
        self, tmp_path: Path
    ) -> None:
        """AC1/boundary: board with several active tasks — ids=[] still returns tasks=[].

        FAIL (RED): same falsy-list bug applies regardless of board size; all tasks
        are returned rather than the empty set implied by ids=[].
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.create_task("Alpha task", status="todo", priority="important")
        engine.create_task("Beta task", status="backlog", priority="needed")
        engine.create_task("Gamma task", status="review", priority="needed")
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(ctx, ids=[])
        assert result.tasks == [], (
            f"Expected [] for ids=[] with 3-task board, got {len(result.tasks)} task(s)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ArchivalReasonFilter
# AC2: list_tasks(archival_reason=duplicate, no status) searches archive storage.
# ---------------------------------------------------------------------------


class TestFromAC_ArchivalReasonFilter:
    """list_tasks with archival_reason must search the archive even without status='archived'.

    Current failure: when archival_reason is set but status is absent,
    ``read_archived = archived or status == "archived"`` evaluates to False;
    only the active tasks directory is scanned.  Archived tasks with a matching
    reason are never found.

    Fix: when archival_reason is provided (and status is absent), implicitly set
    read_archived=True so the archive directory is included in the search.
    """

    @pytest.mark.asyncio
    async def test_archival_reason_without_status_finds_archived_task(
        self, app_ctx_with_archived_duplicate: AppContext
    ) -> None:
        """AC2/happy: archival_reason='duplicate' (no status arg) returns the archived task.

        FAIL (RED): archive is not searched → result.tasks is [] even though the
        board contains one task archived with archival_reason='duplicate'.
        """
        ctx = _make_mcp_ctx(app_ctx_with_archived_duplicate)
        result = await list_tasks(ctx, archival_reason="duplicate")
        assert len(result.tasks) >= 1, (
            "Expected at least one archived task with reason='duplicate'; "
            "archive directory was not searched (no status='archived' arg)"
        )

    @pytest.mark.asyncio
    async def test_archival_reason_filter_all_returned_tasks_match(
        self, app_ctx_with_archived_duplicate: AppContext
    ) -> None:
        """AC2/edge: every task returned has archival_reason='duplicate'.

        FAIL (RED): archive is not searched at all, so result.tasks is empty;
        the non-empty precondition assertion fails before the per-task check.
        """
        ctx = _make_mcp_ctx(app_ctx_with_archived_duplicate)
        result = await list_tasks(ctx, archival_reason="duplicate")
        assert result.tasks, (
            "Expected non-empty result for archival_reason='duplicate'"
        )
        assert all(t.archival_reason == "duplicate" for t in result.tasks), (
            "All returned tasks must have archival_reason='duplicate'"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskAnnotations
# AC4: move_task annotation has idempotentHint=False.
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskAnnotations:
    """move_task must declare idempotentHint=False in its ToolAnnotations.

    Current failure: the @mcp.tool decorator uses idempotentHint=True.

    Fix: change to idempotentHint=False — moving a task to the same status
    twice produces different side effects (activity log entries, guidance
    messages) so it is not idempotent.
    """

    def test_move_task_idempotent_hint_is_false(self) -> None:
        """AC4/smoke: move_task ToolAnnotations must have idempotentHint=False.

        FAIL (RED): current @mcp.tool decorator sets idempotentHint=True.
        """
        ann = _get_tool_annotations("move_task")
        assert ann is not None, "move_task has no ToolAnnotations registered"
        assert ann.idempotentHint is False, (  # type: ignore[union-attr]
            f"Expected idempotentHint=False for move_task, got: {ann.idempotentHint!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MalformedIdEnvelope
# AC5: malformed task ID surfaces structured JSON error envelope {code, message}.
# ---------------------------------------------------------------------------


class TestFromAC_MalformedIdEnvelope:
    """parse_task_id must raise ToolError whose message is a JSON {code, message} payload.

    Current failure: parse_task_id raises ToolError(plain_text_message) where the
    ToolError string is raw human-readable text, not JSON.  json.loads() raises
    JSONDecodeError.

    Fix: emit json.dumps({"code": "ERR_INVALID_ID", "message": ...}) inside
    parse_task_id so agents can programmatically distinguish this error.
    """

    def test_non_numeric_id_raises_tool_error_with_json_payload(self) -> None:
        """AC5/happy: parse_task_id('abc') raises ToolError with parseable JSON body.

        FAIL (RED): current ToolError message is plain text
        'task_id must be a positive integer' — json.loads raises JSONDecodeError.
        """
        with pytest.raises(ToolError) as exc_info:
            parse_task_id("abc")
        # Currently plain text → JSONDecodeError → test FAILS
        payload = json.loads(str(exc_info.value))
        assert isinstance(payload, dict)

    def test_malformed_id_json_has_code_and_message_fields(self) -> None:
        """AC5/edge: JSON error payload from parse_task_id contains 'code' and 'message'.

        FAIL (RED): current ToolError message is not JSON — json.loads raises
        JSONDecodeError before the field assertions are reached.
        """
        with pytest.raises(ToolError) as exc_info:
            parse_task_id("not-a-number")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload, "JSON error envelope must contain 'code' field"
        assert "message" in payload, "JSON error envelope must contain 'message' field"
