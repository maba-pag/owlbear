"""TDD RED-phase tests for #522 -- Wire ErrorLogger adapter at AcpClient construction sites.

Covers:
  AC#1: ErrorLoggerAdapter class in error_journal.py implements _ErrorLogger Protocol,
        delegates to ErrorJournal.log()
  AC#2: Fixed immutable sentinel session_id ('pre-session' or empty string) -- no mutable
        instance attribute that could race under asyncio.gather() parallel dispatch
  AC#3: AcpClient construction in orchestrate() passes error_logger= adapter instance
  AC#4: orchestrate() accepts optional error_journal: ErrorJournal | None; default path
        .owlbear/error-journal.jsonl

All tests fail on current HEAD because ErrorLoggerAdapter does not exist in
error_journal.py and orchestrate() does not accept error_journal= parameter.

Module under test:
  owlbear_orchestrator.error_journal.ErrorLoggerAdapter  (AC#1, AC#2, AC#5)
  owlbear.orchestrator.loop.orchestrate                  (AC#3, AC#4)

Test categories:
  happy: 5 -- basic delegation, all fields forwarded, multiple categories
  edge: 2 -- empty message, empty method
  boundary: 6 -- sentinel invariants, keyword-only signature, protocol conformance
  wiring: 4 -- orchestrate() parameter, AcpClient construction, default path
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# -- AC#1, AC#2, AC#5 -- adapter import (fails RED-phase: class not yet created) --
from owlbear_orchestrator.acp_client import ErrorCategory
from owlbear_orchestrator.error_journal import ErrorJournal, ErrorLoggerAdapter  # type: ignore[attr-defined]

# -- AC#3, AC#4 -- orchestrate import (fails RED-phase: error_journal param missing) --
from owlbear.orchestrator.loop import orchestrate  # type: ignore[import]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_journal() -> MagicMock:
    """Return a mock ErrorJournal with .log as a MagicMock."""
    journal = MagicMock(spec=ErrorJournal)
    journal.log = MagicMock()
    return journal


def _make_mock_supervisor() -> AsyncMock:
    """Return an AsyncMock suitable for use as ProcessSupervisor context manager."""
    supervisor = AsyncMock()
    supervisor.__aenter__ = AsyncMock(return_value=supervisor)
    supervisor.__aexit__ = AsyncMock(return_value=None)
    supervisor.ensure_running = AsyncMock(return_value=(MagicMock(), MagicMock()))
    supervisor.mark_healthy = MagicMock()
    return supervisor


# ---------------------------------------------------------------------------
# AC#1 + AC#2 + AC#5 -- ErrorLoggerAdapter class
# ---------------------------------------------------------------------------


class TestFromAC_ErrorLoggerAdapter:  # noqa: N801
    """ErrorLoggerAdapter: _ErrorLogger Protocol implementation delegating to ErrorJournal.log()."""

    # ------------------------------------------------------------------
    # Happy path: delegation
    # ------------------------------------------------------------------

    def test_log_error_calls_journal_log(self) -> None:
        """log_error() must call ErrorJournal.log() exactly once."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        adapter.log_error(category=ErrorCategory.TRANSIENT, method="initialize", message="conn refused")
        journal.log.assert_called_once()

    def test_log_error_forwards_method(self) -> None:
        """log_error() must forward method= argument to ErrorJournal.log()."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        adapter.log_error(category=ErrorCategory.TRANSIENT, method="new_session", message="timeout")
        kwargs = journal.log.call_args.kwargs
        assert kwargs["method"] == "new_session"

    def test_log_error_forwards_message(self) -> None:
        """log_error() must forward message= argument to ErrorJournal.log()."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        adapter.log_error(category=ErrorCategory.PERMANENT, method="prompt", message="bad input error")
        kwargs = journal.log.call_args.kwargs
        assert kwargs["message"] == "bad input error"

    def test_log_error_forwards_category_as_string_value(self) -> None:
        """log_error() forwards category as a string matching ErrorCategory value."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        adapter.log_error(category=ErrorCategory.AUTH, method="initialize", message="auth failure")
        kwargs = journal.log.call_args.kwargs
        assert kwargs["category"] == "auth"

    def test_log_error_all_error_categories_delegate(self) -> None:
        """Each ErrorCategory variant routes through ErrorJournal.log() with correct string."""
        for cat in ErrorCategory:
            journal = _make_mock_journal()
            adapter = ErrorLoggerAdapter(journal)
            adapter.log_error(category=cat, method="prompt", message="x")
            kwargs = journal.log.call_args.kwargs
            assert kwargs["category"] == str(cat), f"category for {cat!r} not forwarded as expected string"

    # ------------------------------------------------------------------
    # Edge: empty fields propagate unchanged
    # ------------------------------------------------------------------

    def test_log_error_empty_message_forwarded(self) -> None:
        """Empty message string must be forwarded unchanged to ErrorJournal.log()."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        adapter.log_error(category=ErrorCategory.TRANSIENT, method="prompt", message="")
        kwargs = journal.log.call_args.kwargs
        assert kwargs["message"] == ""

    def test_log_error_empty_method_forwarded(self) -> None:
        """Empty method string must be forwarded unchanged to ErrorJournal.log()."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        adapter.log_error(category=ErrorCategory.TRANSIENT, method="", message="oops")
        kwargs = journal.log.call_args.kwargs
        assert kwargs["method"] == ""

    # ------------------------------------------------------------------
    # Boundary / AC#2: immutable sentinel session_id
    # ------------------------------------------------------------------

    def test_sentinel_session_id_is_non_empty_string(self) -> None:
        """The sentinel session_id passed to ErrorJournal.log() must be a non-empty string."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        adapter.log_error(category=ErrorCategory.TRANSIENT, method="prompt", message="err")
        kwargs = journal.log.call_args.kwargs
        sentinel = kwargs.get("session_id")
        assert isinstance(sentinel, str), "session_id must be a str"
        assert sentinel != "", "sentinel session_id must not be empty (use 'pre-session')"

    def test_sentinel_same_on_every_call(self) -> None:
        """The session_id sentinel must be identical across multiple log_error() calls."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        for method in ("initialize", "new_session", "prompt"):
            adapter.log_error(category=ErrorCategory.TRANSIENT, method=method, message="err")
        all_session_ids = [call.kwargs["session_id"] for call in journal.log.call_args_list]
        assert len(set(all_session_ids)) == 1, "All log_error() calls must use the identical sentinel session_id"

    def test_sentinel_not_derived_from_instance_state(self) -> None:
        """Two separate adapter instances must use the same sentinel value (class constant)."""
        journal1 = _make_mock_journal()
        journal2 = _make_mock_journal()
        adapter1 = ErrorLoggerAdapter(journal1)
        adapter2 = ErrorLoggerAdapter(journal2)
        adapter1.log_error(category=ErrorCategory.TRANSIENT, method="m", message="e")
        adapter2.log_error(category=ErrorCategory.TRANSIENT, method="m", message="e")
        sentinel1 = journal1.log.call_args.kwargs["session_id"]
        sentinel2 = journal2.log.call_args.kwargs["session_id"]
        assert sentinel1 == sentinel2, "sentinel must be a class-level constant, not an instance attribute"

    # ------------------------------------------------------------------
    # Protocol conformance: keyword-only signature
    # ------------------------------------------------------------------

    def test_log_error_accepts_keyword_only_args(self) -> None:
        """log_error() must accept category, method, message as keyword-only arguments."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        sig = inspect.signature(adapter.log_error)
        params = sig.parameters
        for name in ("category", "method", "message"):
            assert name in params, f"log_error() must have '{name}' parameter"
            assert params[name].kind == inspect.Parameter.KEYWORD_ONLY, f"'{name}' must be keyword-only"

    def test_adapter_has_log_error_method(self) -> None:
        """ErrorLoggerAdapter must expose a callable log_error method."""
        journal = _make_mock_journal()
        adapter = ErrorLoggerAdapter(journal)
        assert callable(getattr(adapter, "log_error", None)), "ErrorLoggerAdapter must have a callable log_error method"


# ---------------------------------------------------------------------------
# AC#3 + AC#4 -- orchestrate() wiring
# ---------------------------------------------------------------------------


class TestFromAC_OrchestrateWiring:  # noqa: N801
    """orchestrate() accepts error_journal and wires ErrorLoggerAdapter into AcpClient."""

    # ------------------------------------------------------------------
    # AC#4: signature check
    # ------------------------------------------------------------------

    def test_orchestrate_accepts_error_journal_parameter(self) -> None:
        """orchestrate() must declare error_journal as a parameter."""
        sig = inspect.signature(orchestrate)
        assert "error_journal" in sig.parameters, "orchestrate() must accept error_journal= injection parameter"

    def test_orchestrate_error_journal_defaults_to_none(self) -> None:
        """error_journal parameter must default to None (optional injection)."""
        sig = inspect.signature(orchestrate)
        param = sig.parameters.get("error_journal")
        assert param is not None
        assert param.default is None, "error_journal default must be None (follow AuditLog injection pattern)"

    # ------------------------------------------------------------------
    # AC#3: AcpClient receives error_logger= adapter
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_orchestrate_passes_error_logger_to_acp_client(self) -> None:
        """orchestrate() must pass error_logger= when constructing AcpClient (subprocess path)."""
        mock_supervisor = _make_mock_supervisor()
        mock_conn = AsyncMock()
        mock_conn.initialize = AsyncMock(return_value=MagicMock())
        mock_acp_client_cls = MagicMock(return_value=AsyncMock())
        mock_journal = _make_mock_journal()

        with (
            patch("owlbear.orchestrator.loop.ProcessSupervisor", return_value=mock_supervisor),
            patch("owlbear.orchestrator.loop.connect_to_agent", return_value=mock_conn),
            patch("owlbear.orchestrator.loop.AcpClient", mock_acp_client_cls),
            patch("owlbear.orchestrator.loop.run_loop", new_callable=AsyncMock),
        ):
            await orchestrate(
                kanban_bin=Path("/fake/kanban"),
                kanban_dir=Path("/fake/dir"),
                copilot_cmd=["copilot"],
                error_journal=mock_journal,
            )

        mock_acp_client_cls.assert_called_once()
        call_kwargs = mock_acp_client_cls.call_args.kwargs
        assert "error_logger" in call_kwargs, "AcpClient construction must include error_logger= keyword argument"
        assert call_kwargs["error_logger"] is not None, (
            "error_logger passed to AcpClient must not be None when error_journal is provided"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_orchestrate_uses_provided_error_journal_for_adapter(self) -> None:
        """Adapter passed to AcpClient must delegate to the user-supplied ErrorJournal."""
        mock_supervisor = _make_mock_supervisor()
        mock_conn = AsyncMock()
        mock_conn.initialize = AsyncMock(return_value=MagicMock())
        captured: list[object] = []
        mock_journal = _make_mock_journal()

        def capture_acp_client(_conn, *, error_logger=None, **_kw):  # type: ignore[no-untyped-def]
            captured.append(error_logger)
            return AsyncMock()

        with (
            patch("owlbear.orchestrator.loop.ProcessSupervisor", return_value=mock_supervisor),
            patch("owlbear.orchestrator.loop.connect_to_agent", return_value=mock_conn),
            patch("owlbear.orchestrator.loop.AcpClient", side_effect=capture_acp_client),
            patch("owlbear.orchestrator.loop.run_loop", new_callable=AsyncMock),
        ):
            await orchestrate(
                kanban_bin=Path("/fake/kanban"),
                kanban_dir=Path("/fake/dir"),
                copilot_cmd=["copilot"],
                error_journal=mock_journal,
            )

        assert len(captured) == 1
        adapter = captured[0]
        # Trigger one delegation call and verify the provided journal was used
        adapter.log_error(  # type: ignore[union-attr]
            category=ErrorCategory.TRANSIENT, method="probe", message="test"
        )
        mock_journal.log.assert_called_once()

    # ------------------------------------------------------------------
    # AC#4: default path .owlbear/error-journal.jsonl
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_orchestrate_default_error_journal_path(self) -> None:
        """When error_journal=None, orchestrate() must create ErrorJournal at .owlbear/error-journal.jsonl."""
        mock_supervisor = _make_mock_supervisor()
        mock_conn = AsyncMock()
        mock_conn.initialize = AsyncMock(return_value=MagicMock())

        with (
            patch("owlbear.orchestrator.loop.ProcessSupervisor", return_value=mock_supervisor),
            patch("owlbear.orchestrator.loop.connect_to_agent", return_value=mock_conn),
            patch("owlbear.orchestrator.loop.AcpClient", return_value=AsyncMock()),
            patch("owlbear.orchestrator.loop.run_loop", new_callable=AsyncMock),
            patch("owlbear.orchestrator.loop.ErrorJournal") as mock_journal_cls,
        ):
            await orchestrate(
                kanban_bin=Path("/fake/kanban"),
                kanban_dir=Path("/fake/dir"),
                copilot_cmd=["copilot"],
                # error_journal omitted -- should create default
            )

        mock_journal_cls.assert_called_once()
        call_args = mock_journal_cls.call_args
        # path is the first positional argument
        path_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("path")
        assert Path(path_arg) == Path(".owlbear/error-journal.jsonl"), (
            f"Default ErrorJournal path must be .owlbear/error-journal.jsonl, got {path_arg!r}"
        )
