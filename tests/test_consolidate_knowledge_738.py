"""Failing tests for task #738: consolidate_knowledge MCP tool in mcp-knowledge server.

Covers (TDD RED phase — all tests must FAIL before builder implements #738):
  - AC1: consolidate_knowledge tool importable from server, registered as MCP tool
  - AC2: Tool accepts optional batch_size parameter (default=50)
  - AC3: Tool delegates to ConsolidationService.consolidate() with correct batch_size
  - AC4: Returns human-readable string: "Consolidated: 1 insight created" (result=1)
         or "No unconsolidated chunks available" (result=0)
  - AC5: AppContext dataclass has consolidation_service field; tool handles None gracefully

All tests mock ConsolidationService and MCP Context — no real DB, LLM, or
network required. Tests fail with ImportError until builder adds the tool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import targets
# AppContext already exists; consolidate_knowledge is added by builder (#738).
# consolidate_knowledge is imported inside each test so AppContext tests can
# collect and fail independently with AssertionError.
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.server import AppContext  # type: ignore[import]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_context(
    *,
    consolidation_service: Any = None,
) -> MagicMock:
    """Return a MagicMock shaped like the extended AppContext."""
    ctx = MagicMock()
    ctx.consolidation_service = consolidation_service
    return ctx


def _make_mcp_ctx(app_ctx: Any = None) -> MagicMock:
    """Return a MagicMock mimicking a FastMCP Context with a lifespan_context."""
    mcp_ctx = MagicMock()
    mcp_ctx.request_context.lifespan_context = app_ctx or _make_app_context()
    return mcp_ctx


def _make_service(return_value: int = 1) -> AsyncMock:
    """Return an AsyncMock ConsolidationService whose consolidate() returns return_value."""
    svc = MagicMock()
    svc.consolidate = AsyncMock(return_value=return_value)
    return svc


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidateKnowledgeTool
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidateKnowledgeTool:
    """Contract tests for the consolidate_knowledge MCP tool derived from AC1-AC4."""

    # -- AC1: tool importable / registered -----------------------------------

    def test_consolidate_knowledge_is_callable(self) -> None:
        """AC1: consolidate_knowledge must be importable and callable from server module."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        assert callable(consolidate_knowledge)

    # -- AC4: happy path — result = 1 ----------------------------------------

    @pytest.mark.asyncio
    async def test_returns_success_string_when_consolidate_returns_one(self) -> None:
        """AC4: consolidate() returning 1 produces a string containing 'Consolidated' and '1'."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=1)
        output = await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
        )

        assert isinstance(output, str)
        assert "Consolidated" in output or "consolidated" in output.lower()
        assert "1" in output

    @pytest.mark.asyncio
    async def test_success_string_mentions_insight(self) -> None:
        """AC4: Success string (result=1) must include 'insight' to describe what was created."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=1)
        output = await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
        )

        assert "insight" in output.lower()

    # -- AC4: happy path — result = 0 ----------------------------------------

    @pytest.mark.asyncio
    async def test_returns_no_chunks_string_when_consolidate_returns_zero(self) -> None:
        """AC4: consolidate() returning 0 produces a string indicating nothing was consolidated."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=0)
        output = await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
        )

        assert isinstance(output, str)
        # Must NOT claim success; must communicate 'no work done'
        assert "0" in output or "no" in output.lower() or "available" in output.lower()

    @pytest.mark.asyncio
    async def test_zero_result_string_does_not_say_consolidated_one(self) -> None:
        """AC4: When consolidate() returns 0, the output must not say '1 insight created'."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=0)
        output = await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
        )

        assert "1 insight" not in output

    # -- AC2 + AC3: batch_size parameter -------------------------------------

    @pytest.mark.asyncio
    async def test_default_batch_size_fifty_passed_to_consolidate(self) -> None:
        """AC2+AC3: When no batch_size supplied, consolidate() is called with batch_size=50."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=1)
        await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
        )

        svc.consolidate.assert_called_once()
        call_kwargs = svc.consolidate.call_args.kwargs or {}
        call_args = svc.consolidate.call_args.args or ()
        batch_arg = call_kwargs.get("batch_size") or (call_args[0] if call_args else None)
        assert batch_arg == 50

    @pytest.mark.asyncio
    async def test_custom_batch_size_forwarded_to_consolidate(self) -> None:
        """AC2+AC3: Explicit batch_size value is forwarded unchanged to consolidate()."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=1)
        await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
            batch_size=10,
        )

        svc.consolidate.assert_called_once()
        call_kwargs = svc.consolidate.call_args.kwargs or {}
        call_args = svc.consolidate.call_args.args or ()
        batch_arg = call_kwargs.get("batch_size") or (call_args[0] if call_args else None)
        assert batch_arg == 10

    @pytest.mark.asyncio
    async def test_consolidate_called_exactly_once(self) -> None:
        """AC3: consolidate_knowledge calls consolidate() exactly once per invocation."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=1)
        await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
        )

        svc.consolidate.assert_called_once()

    # -- AC2: boundary batch_size values -------------------------------------

    @pytest.mark.asyncio
    async def test_batch_size_one_forwarded(self) -> None:
        """AC2 boundary: batch_size=1 is a valid minimum and must be forwarded."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        svc = _make_service(return_value=1)
        await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=svc)),
            batch_size=1,
        )

        svc.consolidate.assert_called_once()
        call_kwargs = svc.consolidate.call_args.kwargs or {}
        call_args = svc.consolidate.call_args.args or ()
        batch_arg = call_kwargs.get("batch_size") or (call_args[0] if call_args else None)
        assert batch_arg == 1

    # -- AC1/AC5: consolidation_service=None guard ---------------------------

    @pytest.mark.asyncio
    async def test_consolidation_service_none_returns_error_string(self) -> None:
        """AC5 failure-map: When consolidation_service is None, tool returns an error string."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        output = await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=None)),
        )

        assert isinstance(output, str)
        assert "error" in output.lower() or "not available" in output.lower()

    @pytest.mark.asyncio
    async def test_consolidation_service_none_does_not_raise(self) -> None:
        """AC5 failure-map: None consolidation_service must not propagate an exception."""
        from owlbear_mcp_knowledge.server import consolidate_knowledge  # noqa: PLC0415  # type: ignore[attr-defined]

        # If this raises, the tool is not handling None gracefully
        result = await consolidate_knowledge(
            _make_mcp_ctx(_make_app_context(consolidation_service=None)),
        )
        assert result is not None


# ---------------------------------------------------------------------------
# TestFromAC_AppContextWiring
# ---------------------------------------------------------------------------


class TestFromAC_AppContextWiring:
    """AC5: AppContext dataclass must have a consolidation_service field."""

    def test_appcontext_has_consolidation_service_attribute(self) -> None:
        """AC5: AppContext dataclass must declare a consolidation_service field."""
        import dataclasses  # noqa: PLC0415

        field_names = {f.name for f in dataclasses.fields(AppContext)}
        assert "consolidation_service" in field_names, (
            "AppContext must have a 'consolidation_service' field (added by #738)"
        )

    def test_appcontext_consolidation_service_field_allows_none(self) -> None:
        """AC5: consolidation_service field type must allow None (ConsolidationService | None)."""
        import dataclasses  # noqa: PLC0415

        fields_by_name = {f.name: f for f in dataclasses.fields(AppContext)}
        field = fields_by_name["consolidation_service"]
        # The default or type annotation must permit None
        # We verify by checking the type hint string or that it's not required
        hint = str(field.type)
        assert "None" in hint or "Optional" in hint or "consolidation_service" in hint, (
            "consolidation_service field must be typed as ConsolidationService | None"
        )
