"""RED-phase tests for #1337: MCP create_dr — validate and coerce task_id at trust boundary.

AC coverage:
  ac1-error      — non-numeric 'abc' → ToolError with clear message mentioning task_id/integer
  ac1-error      — shell-injection '1; rm -rf' → ToolError with clear message
  ac1-error      — path-traversal '../foo' → ToolError with clear message
  ac2-integration — '../etc/passwd' rejected in integration (no mock): ToolError raised
  ac2-integration — '1; rm -rf' rejected in integration (no mock): ToolError with clear message
  ac2-integration — 'abc' rejected in integration (no mock): ToolError with clear message
  ac2-integration — '../etc/passwd' rejected before file traversal: decisions/pending unchanged
  ac4-happy      — valid numeric string '99' is forwarded as int 99 to decisions.create_dr
  ac4-happy      — valid literal int 99 is forwarded as int 99 to decisions.create_dr

All tests FAIL (RED phase):
  - AC1 tests: current create_dr performs no validation; ToolError is not raised for invalid
    inputs → pytest.raises(ToolError, match=...) fails with 'DID NOT RAISE'.
  - AC2 integration tests:
      '../etc/passwd': os.open raises FileNotFoundError (not ToolError) when decisions.create_dr
      attempts to create decisions/etc/passwd-decision.md — pytest.raises(ToolError) fails as
      FileNotFoundError propagates;
      '1; rm -rf' and 'abc': ToolError IS raised (via engine.edit_task NotFoundError path) but
      the message says "not found", not the required "integer"/"numeric"/"task_id" match →
      pytest.raises(ToolError, match=...) fails on message pattern;
      decisions/pending test: outer pytest.raises(ToolError) fails (FileNotFoundError) before
      the dir-unchanged assertion is reached.
  - AC4 tests: current create_dr forwards task_id='99' as str; isinstance(task_id, int) fails
    because str != int.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext
from owlbear_mcp_kanban.server import create_dr as mcp_create_dr

# ---------------------------------------------------------------------------
# Board / context helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """Minimal AppContext with real engine; decisions.create_dr mocked in unit tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_ErrorMessageClarity
# ---------------------------------------------------------------------------


class TestFromAC_ErrorMessageClarity:
    """AC1: non-numeric task_id must raise ToolError with a clear, user-readable message.

    The error message must help the caller understand *why* the input is invalid —
    it should reference 'task_id', 'integer', or 'numeric'. A generic or empty
    message is not acceptable.
    """

    @pytest.mark.asyncio
    async def test_non_numeric_string_error_message_is_clear(self, app_ctx: AppContext) -> None:
        """AC1 error: 'abc' → ToolError whose message mentions integer/numeric/task_id.

        FAIL path (RED): no validation exists; no ToolError raised at all.
        pytest.raises(ToolError, match=...) fails with 'DID NOT RAISE'.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id)"),
        ):
            await mcp_create_dr(ctx, task_id="abc", agent="builder", request_type="decision", body="b")

    @pytest.mark.asyncio
    async def test_shell_injection_error_message_is_clear(self, app_ctx: AppContext) -> None:
        """AC1 error: '1; rm -rf' → ToolError whose message mentions integer/numeric/task_id.

        FAIL path (RED): no validation exists; no ToolError raised at all.
        pytest.raises(ToolError, match=...) fails with 'DID NOT RAISE'.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id)"),
        ):
            await mcp_create_dr(
                ctx,
                task_id="1; rm -rf",
                agent="builder",
                request_type="decision",
                body="b",
            )

    @pytest.mark.asyncio
    async def test_path_traversal_error_message_is_clear(self, app_ctx: AppContext) -> None:
        """AC1 error: '../foo' → ToolError whose message mentions integer/numeric/task_id.

        FAIL path (RED): no validation exists; no ToolError raised at all.
        pytest.raises(ToolError, match=...) fails with 'DID NOT RAISE'.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id)"),
        ):
            await mcp_create_dr(
                ctx,
                task_id="../foo",
                agent="builder",
                request_type="decision",
                body="b",
            )


# ---------------------------------------------------------------------------
# TestFromAC_IntegrationRejection
# ---------------------------------------------------------------------------


class TestFromAC_IntegrationRejection:
    """AC2: integration tests (decisions.create_dr NOT mocked) prove payloads are rejected.

    These tests verify rejection at the MCP boundary (server.create_dr validation),
    before any file I/O occurs in the decisions directory.
    """

    @pytest.mark.asyncio
    async def test_integration_etc_passwd_traversal_rejected(self, app_ctx: AppContext) -> None:
        """AC2 integration: '../etc/passwd' raises ToolError at MCP boundary (no mock).

        FAIL path (RED): current code calls decisions.create_dr with the traversal path.
        decisions.create_dr attempts to create decisions/etc/passwd-decision.md, but
        decisions/etc/ does not exist → os.open raises FileNotFoundError (not ToolError).
        pytest.raises(ToolError) is not satisfied; FileNotFoundError propagates → ERROR.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id)"):
            await mcp_create_dr(
                ctx,
                task_id="../etc/passwd",
                agent="builder",
                request_type="decision",
                body="probe",
            )

    @pytest.mark.asyncio
    async def test_integration_shell_injection_rejected(self, app_ctx: AppContext) -> None:
        """AC2 integration: '1; rm -rf' raises ToolError with a clear message (no mock).

        FAIL path (RED): current code calls decisions.create_dr; the semicolon-containing
        filename is valid on Unix, so the file is created. engine.edit_task then fails
        with NotFoundError → ToolError("… not found"). The message does not match the
        required 'integer|numeric|task_id' pattern → pytest.raises(match=...) fails.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id)"):
            await mcp_create_dr(
                ctx,
                task_id="1; rm -rf",
                agent="builder",
                request_type="decision",
                body="probe",
            )

    @pytest.mark.asyncio
    async def test_integration_alpha_string_rejected(self, app_ctx: AppContext) -> None:
        """AC2 integration: 'abc' raises ToolError with a clear message (no mock).

        FAIL path (RED): current code calls decisions.create_dr; 'abc-decision.md'
        is a valid filename, so the file is created. engine.edit_task then fails with
        NotFoundError → ToolError("… not found"). The message does not match
        'integer|numeric|task_id' → pytest.raises(match=...) fails.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id)"):
            await mcp_create_dr(
                ctx,
                task_id="abc",
                agent="builder",
                request_type="decision",
                body="probe",
            )

    @pytest.mark.asyncio
    async def test_integration_decisions_pending_unchanged_after_traversal(self, app_ctx: AppContext) -> None:
        """AC2 integration: rejection of '../etc/passwd' leaves decisions/pending untouched.

        After early validation rejection, the decisions/pending directory must contain
        no new files — the traversal attempt must not result in any file creation.

        FAIL path (RED): pytest.raises(ToolError) fails with FileNotFoundError propagating
        from decisions.create_dr (os.open fails because decisions/etc/ doesn't exist).
        The assertion is never reached; the test ERRORS.
        """
        ctx = _make_mcp_ctx(app_ctx)
        decisions_pending = app_ctx.kanban_dir / "decisions" / "pending"

        with pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id)"):
            await mcp_create_dr(
                ctx,
                task_id="../etc/passwd",
                agent="builder",
                request_type="decision",
                body="probe",
            )

        existing_files = list(decisions_pending.rglob("*")) if decisions_pending.exists() else []
        assert existing_files == [], (
            f"decisions/pending must be empty after path-traversal rejection; found: {existing_files}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_RegressionValidIds
# ---------------------------------------------------------------------------


class TestFromAC_RegressionValidIds:
    """AC4: valid integer task_ids must still reach decisions.create_dr as int after the fix.

    These are regression guards — they verify the coercion (str→int) is applied
    and that valid inputs are not accidentally rejected.
    """

    @pytest.mark.asyncio
    async def test_valid_numeric_string_forwarded_as_int(self, app_ctx: AppContext) -> None:
        """AC4 happy: '99' is coerced to int 99 before forwarding to decisions.create_dr.

        FAIL path (RED): current code forwards task_id='99' (str) unchanged.
        isinstance(call_kwargs['task_id'], int) fails because the actual argument
        is str '99', not int 99.
        """
        ctx = _make_mcp_ctx(app_ctx)
        mock_create_dr = MagicMock(return_value=MagicMock())
        with patch("owlbear_mcp_kanban.server.decisions.create_dr", mock_create_dr):
            await mcp_create_dr(
                ctx,
                task_id="99",
                agent="builder",
                request_type="decision",
                body="body",
            )

        call_kwargs = mock_create_dr.call_args.kwargs
        assert call_kwargs["task_id"] == 99, f"task_id forwarded as {call_kwargs['task_id']!r}; expected int 99"
        assert isinstance(call_kwargs["task_id"], int), (
            f"task_id must be int after coercion, got {type(call_kwargs['task_id']).__name__}"
        )
