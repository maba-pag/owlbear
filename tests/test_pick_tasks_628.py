"""Failing tests for task #628: pick_tasks tag parameter passthrough.

Covers all AC items from #628:
  - pick_tasks signature extended to (limit: int = 25, tag: str = "") -> dict
  - When tag is non-empty, --tag {value} appended to _run_kanban args
  - Default "" preserves zero-config semantics -- no --tag arg passed when empty
  - Follows list_tasks tag passthrough pattern (if tag: args += ["--tag", tag])
  - Behavioral preservation: no change when tag is not provided

All tests FAIL in RED phase -- pick_tasks does not yet accept a `tag` parameter.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import (  # type: ignore[import]
    AppContext,
    pick_tasks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_ctx() -> AppContext:
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


def _task(**overrides: object) -> dict:
    """Build a minimal task dict matching kanban-md list --json output."""
    base: dict = {
        "id": 1,
        "title": "Implement feature",
        "status": "todo",
        "priority": "important",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "tags": ["phase-2"],
        "depends_on": [],
        "class": "standard",
        "body": "## AC\n- do something\n",
        "file": "/kanban/tasks/1-impl.md",
        "blocked": False,
        "block_reason": None,
        "claimed_by": None,
    }
    return {**base, **overrides}


def _board(*tasks: dict) -> tuple[str, str, int]:
    return (json.dumps(list(tasks)), "", 0)


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksTagSignature
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksTagSignature:
    """pick_tasks exposes a `tag` keyword parameter with default ""."""

    def test_has_tag_parameter(self) -> None:
        """pick_tasks must accept a `tag` keyword parameter per AC."""
        sig = inspect.signature(pick_tasks)
        assert "tag" in sig.parameters

    def test_default_tag_is_empty_string(self) -> None:
        """Default value for `tag` is "" (empty string) per AC -- not None."""
        sig = inspect.signature(pick_tasks)
        assert sig.parameters["tag"].default == ""

    def test_tag_parameter_annotation_is_str(self) -> None:
        """The `tag` parameter annotation is str (not str | None)."""
        sig = inspect.signature(pick_tasks)
        assert sig.parameters["tag"].annotation is str


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksTagPassthrough
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksTagPassthrough:
    """When tag is non-empty, --tag {value} is appended to _run_kanban args."""

    @pytest.mark.asyncio
    async def test_tag_flag_passed_when_tag_provided(self) -> None:
        """When tag='phase-2', '--tag' appears in the args forwarded to _run_kanban."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="phase-2")
        positional_args = mock_run.call_args[0]
        assert "--tag" in positional_args

    @pytest.mark.asyncio
    async def test_tag_value_passed_after_flag(self) -> None:
        """The tag value appears immediately after '--tag' in the args."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="phase-2")
        positional_args = list(mock_run.call_args[0])
        tag_index = positional_args.index("--tag")
        assert positional_args[tag_index + 1] == "phase-2"

    @pytest.mark.asyncio
    async def test_tag_with_colon_passed_literally(self) -> None:
        """Tags containing colons (e.g. 'scope:mcp') are passed as-is."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="scope:mcp")
        positional_args = list(mock_run.call_args[0])
        assert "scope:mcp" in positional_args


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksTagZeroConfig
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksTagZeroConfig:
    """Default "" preserves zero-config -- no --tag arg passed when tag is empty."""

    @pytest.mark.asyncio
    async def test_empty_tag_omits_flag(self) -> None:
        """When tag='' (explicit empty), '--tag' is NOT forwarded to _run_kanban."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="")
        positional_args = mock_run.call_args[0]
        assert "--tag" not in positional_args


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksTagBehavioralPreservation
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksTagBehavioralPreservation:
    """No behavioral change when tag is not provided -- fixed flags preserved."""

    @pytest.mark.asyncio
    async def test_fixed_flags_present_when_tag_provided(self) -> None:
        """--unblocked, --not-blocked, --unclaimed are still passed when tag is non-empty."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="phase-2")
        positional_args = mock_run.call_args[0]
        assert "--unblocked" in positional_args
        assert "--not-blocked" in positional_args
        assert "--unclaimed" in positional_args

    @pytest.mark.asyncio
    async def test_result_format_unchanged_with_tag(self) -> None:
        """Return value is still {'dispatch': [...]} when tag is provided."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=5, status="todo")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx, tag="phase-2")
        assert isinstance(result, dict)
        assert "dispatch" in result
        assert isinstance(result["dispatch"], list)

    @pytest.mark.asyncio
    async def test_limit_and_tag_both_applied(self) -> None:
        """Both limit and tag params are forwarded correctly when provided together."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, limit=5, tag="phase-2")
        positional_args = list(mock_run.call_args[0])
        assert "--tag" in positional_args
        assert positional_args[positional_args.index("--tag") + 1] == "phase-2"
