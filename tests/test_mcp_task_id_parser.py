"""RED-phase tests for #1337: shared MCP task-ID parser at every endpoint trust boundary.

AC coverage:
  ac1-parser      — parse_task_id is importable and callable from server module
  ac1-endpoint    — move_task, edit_task, start_work, end_work, show_task each reject
                    invalid IDs via the shared parser (one proof per endpoint family)
  ac2-happy       — int 42 and '42' are accepted; result is int 42
  ac3-empty       — empty string '' rejected before engine call
  ac3-zero        — '0' and int 0 rejected before engine call
  ac3-negative    — '-1' and int -1 rejected before engine call
  ac3-path        — '../foo', '../etc/passwd' rejected (path-like)
  ac3-shell       — '1; rm -rf' rejected (shell-like)
  ac3-whitespace  — ' 42 ' rejected (whitespace-padded)
  ac3-mixed       — '42abc' rejected (mixed decimal+alpha)
  ac4-message     — ToolError message mentions field name or 'integer'/'numeric'
  ac4-show-string — show_task string rejection uses field-specific message ("positive")
  ac5-no-side-effect — rejected move_task, edit_task, start_work leave no state change
  ac6-regression  — valid int IDs continue to work on all task-id accepting endpoints
  ac7-breadth     — parser tested beyond create_dr, across every endpoint family

All tests FAIL (RED phase):
  - TestFromAC_SharedParserContract: ImportError at collection time — parse_task_id does
    not exist in owlbear_mcp_kanban.server yet; pytest cannot collect the file.
  - All remaining classes fail transitively due to collection failure.
  - TestFromAC_ShowTaskStringBoundary: FAIL (match pattern mismatch) — current show_task
    dispatches malformed strings through ShowTaskParams PydanticValidationError path,
    producing a generic "valid integer" message instead of the parse_task_id
    field-specific "id must be a positive integer" message.  The discriminating pattern
    is r"positive" which Pydantic does NOT emit but parse_task_id DOES.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import (
    AppContext,
    edit_task as mcp_edit_task,
    end_work as mcp_end_work,
    move_task as mcp_move_task,
    parse_task_id,  # NEW — ImportError until builder adds this function
    show_task as mcp_show_task,
    start_work as mcp_start_work,
)

# ---------------------------------------------------------------------------
# Board / context helpers (shared with existing create_dr test file)
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""

_INVALID_ID_MATCH = r"(?i)(integer|numeric|task_id|positive)"


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """AppContext with a real engine, no tasks."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_with_task(tmp_path: Path) -> tuple[AppContext, int]:
    """AppContext with one 'todo' task; returns (ctx, task_id)."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    task = engine.create_task("Seed task", status="todo", priority="important")
    return AppContext(engine=engine, kanban_dir=kanban_dir), task.id


# ---------------------------------------------------------------------------
# TestFromAC_SharedParserContract — AC1, AC2, AC3, AC4
# ---------------------------------------------------------------------------


class TestFromAC_SharedParserContract:
    """Direct unit tests for the shared parse_task_id function.

    Tests the contract: (str | int) → int, ToolError on invalid input.
    This class is the 'parser/table tests once' mandated by Test-Writer Notes.

    FAIL path (RED): parse_task_id is not yet defined in server.py →
    ImportError at collection time → 0 tests collected → RED gate satisfied.
    """

    # ------------------------------------------------------------------
    # AC2: accept JSON numbers and positive decimal strings
    # ------------------------------------------------------------------

    def test_accepts_positive_int(self) -> None:
        """AC2 happy: parse_task_id(42) returns int 42.

        FAIL (RED): ImportError at collection.
        """
        result = parse_task_id(42)
        assert result == 42
        assert isinstance(result, int)

    def test_accepts_positive_decimal_string(self) -> None:
        """AC2 happy: parse_task_id('42') returns int 42.

        FAIL (RED): ImportError at collection.
        """
        result = parse_task_id("42")
        assert result == 42
        assert isinstance(result, int)

    def test_accepts_minimum_valid_id_one(self) -> None:
        """AC3 boundary: '1' is the smallest valid task ID (positive integer).

        FAIL (RED): ImportError at collection.
        """
        result = parse_task_id("1")
        assert result == 1

    # ------------------------------------------------------------------
    # AC3: reject invalid categories (each gets its own test)
    # ------------------------------------------------------------------

    def test_rejects_empty_string(self) -> None:
        """AC3 reject: empty string '' must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("")

    def test_rejects_zero_string(self) -> None:
        """AC3 reject: '0' must raise ToolError (zero is not a valid task ID).

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("0")

    def test_rejects_zero_int(self) -> None:
        """AC3 reject: int 0 must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id(0)

    def test_rejects_negative_string(self) -> None:
        """AC3 reject: '-1' must raise ToolError (negative integer).

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("-1")

    def test_rejects_negative_int(self) -> None:
        """AC3 reject: int -1 must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id(-1)

    def test_rejects_alpha_string(self) -> None:
        """AC3 reject: 'abc' (non-decimal) must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("abc")

    def test_rejects_path_like_relative(self) -> None:
        """AC3 reject: '../foo' (path traversal) must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("../foo")

    def test_rejects_path_like_etc_passwd(self) -> None:
        """AC3 reject: '../etc/passwd' (path traversal) must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("../etc/passwd")

    def test_rejects_shell_injection(self) -> None:
        """AC3 reject: '1; rm -rf' (shell metacharacters) must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("1; rm -rf")

    def test_rejects_whitespace_padded(self) -> None:
        """AC3 reject: ' 42 ' (whitespace-padded decimal) must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id(" 42 ")

    def test_rejects_mixed_alpha_numeric(self) -> None:
        """AC3 reject: '42abc' (mixed decimal+alpha) must raise ToolError.

        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("42abc")

    # ------------------------------------------------------------------
    # AC4: error message mentions id field and positive integer requirement
    # ------------------------------------------------------------------

    def test_error_message_mentions_field_name_default(self) -> None:
        """AC4 message: default field label appears in the ToolError message.

        The error must help the caller identify *which* argument is invalid.
        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            parse_task_id("bad")

    def test_error_message_mentions_custom_field_name(self) -> None:
        """AC4 message: custom field= label appears in the ToolError message.

        When endpoints pass field='id', the error should reference 'id'.
        FAIL (RED): ImportError at collection.
        """
        with pytest.raises(ToolError, match=r"(?i)(id|integer|numeric|positive)"):
            parse_task_id("bad", field="id")


# ---------------------------------------------------------------------------
# TestFromAC_EndpointBoundaryProofs — AC1, AC3, AC4, AC7
# ---------------------------------------------------------------------------


class TestFromAC_EndpointBoundaryProofs:
    """One endpoint-level proof per task-id accepting tool: shared parser is wired.

    Each test calls an MCP tool with an invalid ID and asserts ToolError with
    a message that matches the parser's error contract (integer/numeric/task_id).

    This class provides the 'at least one endpoint-level proof for each task tool
    family' required by the Test-Writer Notes for this task.

    FAIL path (RED): collection fails due to parse_task_id ImportError.
    Once the import resolves, all tests still FAIL because the endpoints currently
    do not call parse_task_id — ValueError or no error propagates instead of
    a clearly-messaged ToolError.
    """

    @pytest.mark.asyncio
    async def test_move_task_rejects_path_traversal(self, app_ctx: AppContext) -> None:
        """AC1/AC3/AC4 endpoint: move_task rejects '../etc/passwd' with clear ToolError.

        FAIL (RED): current move_task calls int('../etc/passwd') → ValueError
        propagates uncaught; pytest.raises(ToolError) is not satisfied.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_move_task(ctx, id="../etc/passwd", status="todo")

    @pytest.mark.asyncio
    async def test_edit_task_rejects_shell_injection(self, app_ctx: AppContext) -> None:
        """AC1/AC3/AC4 endpoint: edit_task rejects '1; rm -rf' with clear ToolError.

        FAIL (RED): current edit_task calls int('1; rm -rf') → ValueError propagates;
        pytest.raises(ToolError) is not satisfied.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_edit_task(ctx, id="1; rm -rf", append_body="probe")

    @pytest.mark.asyncio
    async def test_start_work_rejects_negative_string(
        self, app_ctx: AppContext
    ) -> None:
        """AC1/AC3/AC4 endpoint: start_work rejects '-1' with clear ToolError.

        FAIL (RED): current start_work calls int('-1') which succeeds (int -1), then
        passes -1 to the view/engine. Engine raises KanbanError('not found') →
        ToolError('… not found') — message does not match 'integer|numeric|task_id'.
        pytest.raises(match=...) fails on message pattern.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_start_work(ctx, id="-1")

    @pytest.mark.asyncio
    async def test_end_work_rejects_zero(self, app_ctx: AppContext) -> None:
        """AC1/AC3/AC4 endpoint: end_work rejects '0' with clear ToolError.

        FAIL (RED): current end_work accepts '0' (StrId coerces to str '0');
        int('0') == 0 reaches engine → KanbanError('not found') → ToolError
        with 'not found' message; pattern match fails.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_end_work(ctx, id="0", note="test")

    @pytest.mark.asyncio
    async def test_show_task_rejects_zero_id(self, app_ctx: AppContext) -> None:
        """AC1/AC3/AC4 endpoint: show_task(id=0) raises ToolError with clear message.

        0 is the schema default and is not a valid task ID (the engine's 'default 0'
        is used as a sentinel for 'no id provided'; task IDs are positive integers).
        The shared parser must reject 0 before calling the view.

        FAIL (RED): current show_task passes id=0 to ShowTaskParams (valid int);
        view.show_task(task_id=0) raises KanbanError('not found') → ToolError
        with 'not found' message — does not match 'integer|numeric|task_id|positive'.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_show_task(ctx, id=0)

    @pytest.mark.asyncio
    async def test_show_task_rejects_negative_id(self, app_ctx: AppContext) -> None:
        """AC1/AC3/AC4 endpoint: show_task(id=-1) raises ToolError with clear message.

        FAIL (RED): same as zero case — engine raises not-found, message mismatch.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_show_task(ctx, id=-1)


# ---------------------------------------------------------------------------
# TestFromAC_NoSideEffects — AC5
# ---------------------------------------------------------------------------


class TestFromAC_NoSideEffects:
    """Rejected IDs must not mutate task state, claim tasks, or touch the filesystem.

    These tests verify that the parser rejection happens BEFORE any engine call
    or file I/O. They use a real engine (no mocks on the task operations).

    FAIL path (RED): ImportError at collection; once resolved, tests FAIL because
    the endpoints currently reach the engine before raising errors.
    """

    @pytest.mark.asyncio
    async def test_rejected_move_task_does_not_change_status(
        self, app_ctx_with_task: tuple[AppContext, int]
    ) -> None:
        """AC5: invalid ID for move_task leaves the existing task in its original status.

        A real task at 'todo' must remain at 'todo' after a rejected move_task call.
        FAIL (RED): current move_task does not reject before calling the engine
        (or raises ValueError uncaught, not ToolError); the pre-call status
        assertion is never verified because pytest.raises fails first.
        """
        app_ctx, task_id = app_ctx_with_task
        ctx = _make_mcp_ctx(app_ctx)

        original_task = app_ctx.engine.show_task(str(task_id))
        original_status = original_task.status

        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_move_task(ctx, id="../etc/passwd", status="done")

        post_task = app_ctx.engine.show_task(str(task_id))
        assert post_task.status == original_status, (
            f"Task status changed after rejected move_task; "
            f"expected {original_status!r}, got {post_task.status!r}"
        )

    @pytest.mark.asyncio
    async def test_rejected_edit_task_does_not_modify_body(
        self, app_ctx_with_task: tuple[AppContext, int]
    ) -> None:
        """AC5: invalid ID for edit_task leaves the existing task body unchanged.

        FAIL (RED): ImportError at collection.
        """
        app_ctx, task_id = app_ctx_with_task
        ctx = _make_mcp_ctx(app_ctx)

        original_task = app_ctx.engine.show_task(str(task_id))
        original_body = original_task.body

        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_edit_task(ctx, id="1; rm -rf .", append_body="injected-content")

        post_task = app_ctx.engine.show_task(str(task_id))
        assert post_task.body == original_body, (
            f"Task body modified after rejected edit_task; body now: {post_task.body!r}"
        )

    @pytest.mark.asyncio
    async def test_rejected_start_work_does_not_claim_any_task(
        self, app_ctx_with_task: tuple[AppContext, int]
    ) -> None:
        """AC5: invalid ID for start_work leaves no task claimed.

        FAIL (RED): ImportError at collection.
        """
        app_ctx, task_id = app_ctx_with_task
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError, match=_INVALID_ID_MATCH):
            await mcp_start_work(ctx, id="-5")

        post_task = app_ctx.engine.show_task(str(task_id))
        assert post_task.claimed_at is None, (
            "Task was claimed after rejected start_work with negative ID"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ValidIdsRegression — AC6
# ---------------------------------------------------------------------------


class TestFromAC_ValidIdsRegression:
    """Regression guard: valid positive integer IDs continue to reach the engine.

    These tests verify that the shared parser does not accidentally reject
    legitimate task IDs on any endpoint. They use a mock view to isolate
    endpoint routing from engine state.

    FAIL path (RED): ImportError at collection. Once the import resolves,
    these tests should PASS immediately (proving AC6 holds as soon as
    parse_task_id exists and accepts positive ints).
    """

    @pytest.fixture
    def app_ctx_mocked(self, tmp_path: Path) -> tuple[AppContext, MagicMock]:
        """Real engine with a mocked agent_view; single task pre-created."""
        from owlbear_kanban.models import SingleTaskResponse

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.create_task("Seed task", status="todo", priority="important")

        stub: dict[str, object] = {
            "id": 1,
            "title": "Seed task",
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
        response = SingleTaskResponse.model_validate(stub)

        mock_view = MagicMock()
        mock_view.move_task.return_value = response
        mock_view.edit_task.return_value = response
        mock_view.start_work.return_value = response
        mock_view.end_work.return_value = response
        mock_view.show_task.return_value = response

        engine._agent_view = mock_view  # noqa: SLF001
        return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view

    @pytest.mark.asyncio
    async def test_move_task_valid_int_id_reaches_engine(
        self, app_ctx_mocked: tuple[AppContext, MagicMock]
    ) -> None:
        """AC6 regression: move_task with valid int id='1' calls view.move_task.

        FAIL (RED): ImportError at collection.
        """
        app_ctx, mock_view = app_ctx_mocked
        ctx = _make_mcp_ctx(app_ctx)
        await mcp_move_task(ctx, id="1", status="in-progress")
        mock_view.move_task.assert_called_once()
        call_args = mock_view.move_task.call_args
        assert (
            call_args.args[0] == 1
            or call_args.kwargs.get("task_id") == 1
            or (call_args.args and call_args.args[0] == 1)
        ), f"move_task not called with int 1; args={call_args}"

    @pytest.mark.asyncio
    async def test_edit_task_valid_int_id_reaches_engine(
        self, app_ctx_mocked: tuple[AppContext, MagicMock]
    ) -> None:
        """AC6 regression: edit_task with valid int id='1' calls view.edit_task.

        FAIL (RED): ImportError at collection.
        """
        app_ctx, mock_view = app_ctx_mocked
        ctx = _make_mcp_ctx(app_ctx)
        await mcp_edit_task(ctx, id="1", append_body="ok")
        mock_view.edit_task.assert_called_once()
        call_args = mock_view.edit_task.call_args
        task_id_arg = (
            call_args.args[0] if call_args.args else call_args.kwargs.get("task_id")
        )
        assert task_id_arg == 1, f"edit_task must receive int 1; got {task_id_arg!r}"
        assert isinstance(task_id_arg, int), (
            f"task_id must be int, got {type(task_id_arg)}"
        )

    @pytest.mark.asyncio
    async def test_start_work_valid_int_id_reaches_engine(
        self, app_ctx_mocked: tuple[AppContext, MagicMock]
    ) -> None:
        """AC6 regression: start_work with valid int id='1' calls view.start_work.

        FAIL (RED): ImportError at collection.
        """
        app_ctx, mock_view = app_ctx_mocked
        ctx = _make_mcp_ctx(app_ctx)
        await mcp_start_work(ctx, id="1")
        mock_view.start_work.assert_called_once()
        call_args = mock_view.start_work.call_args
        task_id_arg = (
            call_args.args[0] if call_args.args else call_args.kwargs.get("task_id")
        )
        assert task_id_arg == 1, f"start_work must receive int 1; got {task_id_arg!r}"
        assert isinstance(task_id_arg, int), (
            f"task_id must be int, got {type(task_id_arg)}"
        )

    @pytest.mark.asyncio
    async def test_end_work_valid_int_id_reaches_engine(
        self, app_ctx_mocked: tuple[AppContext, MagicMock]
    ) -> None:
        """AC6 regression: end_work with valid int id='1' calls view.end_work.

        FAIL (RED): ImportError at collection.
        """
        app_ctx, mock_view = app_ctx_mocked
        ctx = _make_mcp_ctx(app_ctx)
        await mcp_end_work(ctx, id="1", note="done")
        mock_view.end_work.assert_called_once()
        call_args = mock_view.end_work.call_args
        task_id_arg = (
            call_args.args[0] if call_args.args else call_args.kwargs.get("task_id")
        )
        assert task_id_arg == 1, f"end_work must receive int 1; got {task_id_arg!r}"
        assert isinstance(task_id_arg, int), (
            f"task_id must be int, got {type(task_id_arg)}"
        )

    @pytest.mark.asyncio
    async def test_show_task_valid_int_id_reaches_engine(
        self, app_ctx_mocked: tuple[AppContext, MagicMock]
    ) -> None:
        """AC6 regression: show_task with valid int id=1 calls view.show_task.

        FAIL (RED): ImportError at collection.
        """
        app_ctx, mock_view = app_ctx_mocked
        ctx = _make_mcp_ctx(app_ctx)
        await mcp_show_task(ctx, id=1)
        mock_view.show_task.assert_called_once()
        call_args = mock_view.show_task.call_args
        task_id_arg = (
            call_args.kwargs.get("task_id")
            if call_args.kwargs
            else (call_args.args[0] if call_args.args else None)
        )
        assert task_id_arg == 1, (
            f"show_task must receive task_id=1; got {task_id_arg!r}"
        )
        assert isinstance(task_id_arg, int), (
            f"task_id must be int, got {type(task_id_arg)}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ShowTaskStringBoundary — AC4, AC7 (rework cycle)
# ---------------------------------------------------------------------------

# Discriminating match: parse_task_id emits "id must be a positive integer"
# Pydantic v2 emits "Input should be a valid integer, unable to parse string
# as an integer [type=int_parsing, ...]" — no "positive" in that message.
# So r"positive" is ONLY satisfied by the parse_task_id field-specific contract.
_FIELD_SPECIFIC_MATCH = r"positive"


class TestFromAC_ShowTaskStringBoundary:
    """show_task malformed-string inputs must use the parse_task_id field-specific
    ToolError contract ("id must be a positive integer"), NOT the generic Pydantic
    validation error path ("valid integer, unable to parse...").

    These tests are the 'malformed-string show_task boundary tests' required by the
    rework scope after the second reviewer cycle identified that show_task still
    used id: int = 0, routing strings through ShowTaskParams -> PydanticValidationError
    -> ToolError(str(exc)) before parse_task_id was reached.

    Discriminating pattern: r"positive"
      - parse_task_id output: "id must be a positive integer"      → MATCHES
      - Pydantic output:      "Input should be a valid integer, …"  → NO MATCH

    FAIL path (current implementation):
      show_task(id="abc") → ShowTaskParams.model_validate({"id": "abc"}) →
      PydanticValidationError → ToolError("1 validation error for ShowTaskParams…
      valid integer…") → does NOT contain "positive" →
      pytest.raises(match=r"positive") FAILS → RED gate satisfied.

    PASS path (after builder fix: id parameter changed to StrId):
      show_task(id="abc") → parse_task_id("abc", field="id") →
      ToolError("id must be a positive integer") → contains "positive" →
      pytest.raises(match=r"positive") PASSES.
    """

    @pytest.mark.asyncio
    async def test_show_task_rejects_path_traversal_string(
        self, app_ctx: AppContext
    ) -> None:
        """AC4/AC7: show_task("../foo") must raise field-specific ToolError.

        "positive" in the error proves parse_task_id was reached, not the
        PydanticValidationError fallback path.

        FAIL (current): generic Pydantic error "valid integer" lacks "positive".
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_FIELD_SPECIFIC_MATCH):
            await mcp_show_task(ctx, id="../foo")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_show_task_rejects_alpha_string(self, app_ctx: AppContext) -> None:
        """AC4/AC7: show_task("abc") must raise field-specific ToolError.

        FAIL (current): generic Pydantic error lacks "positive".
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_FIELD_SPECIFIC_MATCH):
            await mcp_show_task(ctx, id="abc")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_show_task_rejects_empty_string(self, app_ctx: AppContext) -> None:
        """AC4/AC7: show_task("") must raise field-specific ToolError.

        FAIL (current): generic Pydantic error lacks "positive".
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_FIELD_SPECIFIC_MATCH):
            await mcp_show_task(ctx, id="")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_show_task_rejects_shell_injection_string(
        self, app_ctx: AppContext
    ) -> None:
        """AC4/AC7: show_task("1; rm -rf") must raise field-specific ToolError.

        FAIL (current): generic Pydantic error lacks "positive".
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_FIELD_SPECIFIC_MATCH):
            await mcp_show_task(ctx, id="1; rm -rf")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_show_task_rejects_whitespace_padded_string(
        self, app_ctx: AppContext
    ) -> None:
        """AC4/AC7: show_task(" 42 ") must raise field-specific ToolError.

        Pydantic strips whitespace before int coercion; parse_task_id rejects
        whitespace-padded strings via .strip() check.

        FAIL (current): Pydantic may accept " 42 " as int 42, letting it pass
        Pydantic validation and reach parse_task_id — but parse_task_id should
        reject the padded string.  Either way the "positive" match discriminates.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=_FIELD_SPECIFIC_MATCH):
            await mcp_show_task(ctx, id=" 42 ")  # type: ignore[arg-type]
