"""RED tests — guidance passthrough and KanbanError → ToolError mapping (#1089).

AC coverage:
- Guidance passthrough: engine (AgentView) response guidance passes through unmodified
- show_task section occurrence count guidance (AC12) passes through
- pick_tasks dispatch hints pass through
- create_task body size warning (>100 KB) passes through
- edit_task body size warning (>100 KB) passes through
- move_task skip-transition warning passes through (AC-NEW-5)
- end_work(reject) skip-transition warning passes through (AC-NEW-5)
- end_work(outcome="block") Action-Request/Decision-Request hint passes through (AC-NEW-4)
- ValidationError → ToolError (user_message only, no code on wire per §7)
- NotFoundError → ToolError
- ConcurrencyError → ToolError (e.g. already-claimed)

All tests must FAIL (RED phase).

FAIL paths summary:
- Guidance tests (1-8): AgentView stub methods raise NotImplementedError (or TypeError on
  unexpected kwargs), which the server does NOT catch as ToolError — the exception propagates
  raw. For move_task (no move_task on AgentView stub) and end_work block (stub falls through),
  the fallback path runs: collect_guidance is patched to a sentinel, so the assertion
  result.guidance == expected_engine_string fails.
- Error mapping tests (9-11): AgentView stub raises NotImplementedError/TypeError instead of
  the expected KanbanError subclass, so the adapter never raises ToolError in the expected
  way (or, for ConcurrencyError, the ValueError fallback message does not match the
  ConcurrencyError-specific user_message fragment).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ShowTaskResponse
from owlbear_mcp_kanban.server import (
    AppContext,
    create_task,
    edit_task,
    end_work,
    move_task,
    pick_tasks,
    show_task,
    start_work,
)

# ---------------------------------------------------------------------------
# Board config — full flat schema required by BoardConfig._validate_agent_map
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
# Expected guidance strings (spec for AgentView implementation)
# ---------------------------------------------------------------------------

_LARGE_BODY = "x" * (100 * 1024 + 1)  # 100 KB + 1 byte

_BODY_WITH_DUPLICATE_AUDIT = """\
## Overview
First section.

## Audit
First audit entry.

## Audit
Second audit entry.
"""

_BODY_SIZE_WARNING = "⚠️ Task body is large (>100 KB); consider splitting."
_SECTION_OCCURRENCE_MSG = "Section 'Audit' matched 2 occurrences; returning the first section."
_PICK_DISPATCH_HINT = "Dispatch hints: 3 task(s) across 1 wave(s)."

_SKIP_MOVE_WARNING = (
    "⚠️ Status skip: moved from 'todo' to 'review' (skipped 1 column(s))."
    " Verify this jump is intentional."
)

_SKIP_REJECT_WARNING = (
    "⚠️ Status skip: moved from 'todo' to 'done' (skipped 4 column(s))."
    " Verify this jump is intentional."
)

_BLOCK_AR_HINT = (
    "⚠️ ACTION REQUIRED: Create a Decision Request for this block via the"
    " scribe agent (see w-decision-routing)."
    " Blocks without a DR are invisible to the pipeline."
)

# Sentinel returned by patched collect_guidance — proves guidance did NOT come
# from the adapter's fallback logic when AgentView is expected to be the source.
_ADAPTER_FALLBACK_SENTINEL = ["__ADAPTER_FALLBACK_SENTINEL__"]

# ---------------------------------------------------------------------------
# Board helpers
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
    """AppContext with one unclaimed task at todo."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Test task", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_with_section_task(tmp_path: Path) -> AppContext:
    """AppContext with a task whose body contains ## Audit twice."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task(
        "Audit task",
        body=_BODY_WITH_DUPLICATE_AUDIT,
        status="todo",
        priority="important",
    )
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_multi(tmp_path: Path) -> AppContext:
    """AppContext with 3 unclaimed tasks at todo — enough to trigger dispatch hints."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Task Alpha", status="todo", priority="important")
    engine.create_task("Task Beta", status="todo", priority="important")
    engine.create_task("Task Gamma", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_claimed(tmp_path: Path) -> AppContext:
    """AppContext with one claimed task at in-progress."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Beta task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_GuidancePassthrough
# ---------------------------------------------------------------------------


class TestFromAC_GuidancePassthrough:
    """AgentView response guidance passes through the MCP adapter unmodified."""

    @pytest.mark.asyncio
    async def test_show_task_section_occurrence_count_guidance(
        self, app_ctx_with_section_task: AppContext
    ) -> None:
        """AC12: When requested section appears more than once, guidance includes the count.

        AgentView.show_task must detect the duplicate '## Audit' sections and include
        an occurrence-count string in the guidance list. The adapter must return it
        unchanged.

        FAIL path (RED): AgentView.show_task() raises TypeError (unexpected 'section'
        kwarg) or NotImplementedError — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx_with_section_task)
        result = await show_task(ctx, task_id="1", section="Audit")
        assert result.guidance == [_SECTION_OCCURRENCE_MSG], (
            f"Expected exact occurrence-count guidance {[_SECTION_OCCURRENCE_MSG]!r}; "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_show_task_guidance_passes_through_unmodified(
        self, app_ctx: AppContext
    ) -> None:
        """Guidance returned by AgentView.show_task is not stripped or transformed.

        The adapter must return whatever guidance list AgentView provides, without
        filtering, sorting, or converting to another type.

        FAIL path (RED): AgentView.show_task() raises TypeError (unexpected 'section'
        kwarg) or NotImplementedError — the call propagates before the assertion.
        """
        sentinel_guidance = ["__sentinel_a__", "__sentinel_b__"]
        ctx = _make_ctx(app_ctx)
        task = app_ctx.engine.show_task("1")
        payload = task.model_dump()
        if isinstance(payload.get("body"), list):
            payload["body"] = None
        payload["guidance"] = sentinel_guidance
        payload["missing_sections"] = None
        sentinel_response = ShowTaskResponse.model_validate(payload)
        with patch.object(AgentView, "show_task", return_value=sentinel_response):
            result = await show_task(ctx, task_id="1")
        assert result.guidance == sentinel_guidance, (
            f"Adapter must pass guidance through unmodified; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_dispatch_hints_guidance(
        self, app_ctx_multi: AppContext
    ) -> None:
        """pick_tasks with dispatchable tasks → guidance includes wave/task count hints.

        AgentView.pick_tasks must populate the guidance field with dispatch context
        (e.g. '3 tasks across 1 wave'). The adapter must return this list unchanged.

        FAIL path (RED): AgentView.pick_tasks() raises TypeError (unexpected
        wave_size/max_waves kwargs) — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx_multi)
        result = await pick_tasks(ctx)
        assert result.guidance == [_PICK_DISPATCH_HINT], (
            f"Expected exact dispatch hint {[_PICK_DISPATCH_HINT]!r}; "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_create_task_body_size_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """create_task with body > 100 KB → guidance includes body-size warning from AgentView.

        AgentView.create_task must detect the oversized body and append the warning
        string to the SingleTaskResponse guidance. The adapter must not drop it.

        FAIL path (RED): AgentView.create_task() raises TypeError (unexpected kwargs
        body/priority/…) — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx)
        result = await create_task(ctx, title="Big task", body=_LARGE_BODY)
        assert result.guidance == [_BODY_SIZE_WARNING], (
            f"Expected exact body-size warning {[_BODY_SIZE_WARNING]!r}; "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_edit_task_body_size_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """edit_task with body > 100 KB → guidance includes body-size warning from AgentView.

        AgentView.edit_task must detect the oversized body on edit and append the
        warning string. The adapter must not drop it.

        FAIL path (RED): AgentView.edit_task() raises TypeError (unexpected 'body' kwarg)
        — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, task_id="1", body=_LARGE_BODY)
        assert result.guidance == [_BODY_SIZE_WARNING], (
            f"Expected exact body-size warning {[_BODY_SIZE_WARNING]!r} in edit_task guidance; "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_move_task_skip_transition_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """AC-NEW-5: move_task skipping >1 column → skip-transition warning from AgentView.

        AgentView is the authoritative source. The adapter's collect_guidance fallback
        must NOT be the origin. This test patches collect_guidance to a sentinel so
        that if the fallback path runs the assertion catches the wrong guidance.

        FAIL path (RED): AgentView has no move_task method → the server skips the view
        path and runs the fallback. The patched collect_guidance returns the sentinel,
        which does not equal the expected engine string — assertion fails.
        """
        ctx = _make_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=_ADAPTER_FALLBACK_SENTINEL,
        ):
            result = await move_task(ctx, task_id="1", status="review")
        assert result.guidance == [_SKIP_MOVE_WARNING], (
            f"Expected AgentView skip-transition warning {_SKIP_MOVE_WARNING!r}; "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_end_work_reject_skip_transition_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """AC-NEW-5: end_work(reject, move_to='done') skipping columns → skip warning in guidance.

        AgentView.end_work must emit the skip-transition warning for large-jump rejects.
        The adapter's collect_guidance does NOT produce skip warnings for 'reject' outcome,
        so if the fallback path runs the guidance is [].

        FAIL path (RED): AgentView.end_work() stub falls through to the direct engine
        path; collect_guidance returns [] for 'reject'; result.guidance == [] ≠ expected
        skip warning — assertion fails.
        """
        ctx = _make_ctx(app_ctx)
        result = await end_work(
            ctx,
            task_id="1",
            note="rejected to done",
            outcome="reject",
            move_to="done",
        )
        assert result.guidance == [_SKIP_REJECT_WARNING], (
            f"Expected skip-transition warning from AgentView.end_work; "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_end_work_block_action_request_hint_guidance(
        self, app_ctx_claimed: AppContext
    ) -> None:
        """AC-NEW-4: end_work(outcome='block') → AR/DR hint from AgentView, not collect_guidance.

        AgentView.end_work must supply the Action-Request/Decision-Request hint when
        the outcome is 'block'. This test patches collect_guidance to a sentinel so
        that if the fallback path runs the assertion catches the wrong guidance.

        FAIL path (RED): AgentView.end_work stub falls through to the direct engine
        path; the patched collect_guidance returns the sentinel, which does not equal
        the expected AR/DR hint string — assertion fails.
        """
        ctx = _make_ctx(app_ctx_claimed)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=_ADAPTER_FALLBACK_SENTINEL,
        ):
            result = await end_work(
                ctx,
                task_id="1",
                note="blocked on external dependency",
                outcome="block",
                block_reason="waiting for decision",
            )
        assert result.guidance == [_BLOCK_AR_HINT], (
            f"Expected AR/DR hint from AgentView.end_work; got {result.guidance!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ErrorMapping
# ---------------------------------------------------------------------------


class TestFromAC_ErrorMapping:
    """KanbanError subclasses raised by AgentView → ToolError with user_message only."""

    @pytest.mark.asyncio
    async def test_validation_error_maps_to_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """ValidationError from AgentView.create_task(title='') → ToolError(user_message).

        An empty title is invalid input. AgentView.create_task must raise ValidationError;
        the adapter must catch it as KanbanError and re-raise as ToolError(user_message).

        FAIL path (RED): AgentView.create_task() raises TypeError (unexpected kwargs
        body/priority/…), which is NOT a ToolError — pytest.raises(ToolError) fails.
        """
        ctx = _make_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await create_task(ctx, title="")
        error_text = str(exc_info.value)
        assert "title" in error_text.lower() or "invalid" in error_text.lower() or "empty" in error_text.lower(), (
            f"ToolError must describe the validation failure; got {exc_info.value!r}"
        )
        assert not any(word.startswith("ERR_") for word in error_text.split()), (
            f"ToolError must not expose machine error code on wire; got {error_text!r}"
        )

    @pytest.mark.asyncio
    async def test_not_found_error_maps_to_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """NotFoundError from AgentView.show_task(non-existent ID) → ToolError(user_message).

        Requesting a non-existent task ID must cause AgentView.show_task to raise
        NotFoundError; the adapter must catch it as KanbanError and re-raise as ToolError.

        FAIL path (RED): AgentView.show_task() raises TypeError (unexpected 'section'
        kwarg) or NotImplementedError — neither is a ToolError — pytest.raises fails.
        """
        ctx = _make_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await show_task(ctx, task_id="9999")
        error_text = str(exc_info.value).lower()
        assert "9999" in error_text or "not found" in error_text, (
            f"ToolError must reference the missing task; got {exc_info.value!r}"
        )

    @pytest.mark.asyncio
    async def test_concurrency_error_maps_to_tool_error_user_message_only(
        self, app_ctx_claimed: AppContext
    ) -> None:
        """ConcurrencyError (already-claimed) → ToolError; machine code must not be on wire.

        Claiming a task that is already actively claimed must raise ConcurrencyError.
        The adapter must map it to ToolError(user_message) — the machine-readable error
        code (ERR_ALREADY_CLAIMED) must NOT appear in the wire response per §7.

        FAIL path (RED): AgentView.start_work stub raises NotImplementedError → server
        falls through to engine.start_work() which raises ValueError (not ConcurrencyError).
        ToolError IS raised but its text is str(ValueError) which does NOT include the
        ConcurrencyError-specific phrase 'by another agent' — assertion fails.
        """
        ctx = _make_ctx(app_ctx_claimed)
        code = "ERR_ALREADY_CLAIMED"
        user_msg_fragment = "by another agent"
        with pytest.raises(ToolError) as exc_info:
            await start_work(ctx, task_id="1")
        error_text = str(exc_info.value)
        assert user_msg_fragment in error_text, (
            f"ToolError must contain ConcurrencyError user_message fragment "
            f"{user_msg_fragment!r}; got {error_text!r}"
        )
        assert code not in error_text, (
            f"ToolError must NOT expose machine code on wire; "
            f"found {code!r} in {error_text!r}"
        )
