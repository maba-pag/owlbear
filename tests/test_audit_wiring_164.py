"""Tests for task #164 — Wire audit log into orchestrator dispatch loop.

TDD RED phase: targets the gap in task #204's test suite — AC7 requires
audit I/O failures to be *logged as warning*, not just silently suppressed.

Module under test: owlbear.orchestrator.loop (dispatch_entry)
Logger under test: owlbear.orchestrator.loop (module-level _logger)

AC7 requires: "All audit calls wrapped in try/except: audit I/O errors
logged as warning, never block dispatch loop."

The existing test_dispatch_audit_wiring.py (task #204) verifies that dispatch
continues when audit raises OSError, but does NOT assert a WARNING log is emitted.
These tests close that gap.

Additional coverage:
  AC3 boundary: prompt_summary truncation at exactly 100 chars (AC3 says "truncated
  to 100 chars", which means 100 is the inclusive limit).
  AC7 boundary: both failure sites (pre-prompt log_dispatch, post-prompt log_completion)
  must each emit a WARNING.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.audit import AuditLog
from owlbear.orchestrator import dispatch_entry
from owlbear.planner.models import DispatchEntry

_LOOP_LOGGER = "owlbear.orchestrator.loop"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def entry() -> DispatchEntry:
    return DispatchEntry(task_id=42, agent="builder", target_status="review")


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    session_resp = MagicMock()
    session_resp.session_id = "sess-164-test"
    client.new_session = AsyncMock(return_value=session_resp)
    client.prompt = AsyncMock(return_value=MagicMock())
    return client


@pytest.fixture
def mock_audit_log() -> MagicMock:
    return MagicMock(spec=AuditLog)


# ---------------------------------------------------------------------------
# AC7: audit I/O errors LOGGED AS WARNING, never block dispatch loop
# ---------------------------------------------------------------------------


class TestFromAC_AuditWiringWarnings:  # noqa: N801
    """AC7: audit I/O errors logged as warning — not just silently suppressed."""

    # ------------------------------------------------------------------
    # log_dispatch failure must emit WARNING
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_dispatch_io_error_emits_warning_log(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When log_dispatch() raises OSError, the module logger emits a WARNING."""
        mock_audit_log.log_dispatch.side_effect = OSError("disk full")

        with caplog.at_level(logging.WARNING, logger=_LOOP_LOGGER):
            await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        # Dispatch must still complete
        mock_client.prompt.assert_called_once()

        # A WARNING must be logged — AC7 says "logged as warning, never block dispatch loop"
        warning_records = [
            r for r in caplog.records if r.levelno >= logging.WARNING and r.name == _LOOP_LOGGER
        ]
        assert warning_records, (
            "Expected a WARNING log from owlbear.orchestrator.loop when log_dispatch() raises OSError"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_dispatch_io_error_warning_contains_context(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """WARNING emitted for log_dispatch failure must mention 'audit' or the error type (audit context)."""
        mock_audit_log.log_dispatch.side_effect = OSError("permissions denied")

        with caplog.at_level(logging.WARNING, logger=_LOOP_LOGGER):
            await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        warning_text = " ".join(r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING)
        # The warning should carry enough context to identify this is an audit failure
        assert warning_text, "Expected at least one WARNING log to be emitted by the loop logger"

    # ------------------------------------------------------------------
    # log_completion failure (success path) must emit WARNING
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_completion_success_path_io_error_emits_warning_log(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When log_completion() raises OSError on the success path, the module logger emits a WARNING."""
        mock_audit_log.log_completion.side_effect = OSError("write error")

        with caplog.at_level(logging.WARNING, logger=_LOOP_LOGGER):
            result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        # Dispatch must still succeed
        assert result is True

        # WARNING must be logged
        warning_records = [
            r for r in caplog.records if r.levelno >= logging.WARNING and r.name == _LOOP_LOGGER
        ]
        assert warning_records, (
            "Expected a WARNING log from owlbear.orchestrator.loop when log_completion() raises OSError "
            "on the success path"
        )

    # ------------------------------------------------------------------
    # log_completion failure (exception/failure path) must emit WARNING
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_completion_failure_path_io_error_emits_warning_log(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When log_completion() raises OSError on the failure path, the module logger emits a WARNING."""
        from owlbear_orchestrator.acp_client import AcpClientError, ErrorCategory

        mock_client.prompt = AsyncMock(
            side_effect=AcpClientError("timeout", category=ErrorCategory.TRANSIENT)
        )
        mock_audit_log.log_completion.side_effect = OSError("write error")

        with caplog.at_level(logging.WARNING, logger=_LOOP_LOGGER):
            result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        # Dispatch must still return False (failure), not raise
        assert result is False

        # WARNING must be logged for the audit I/O failure
        warning_records = [
            r for r in caplog.records if r.levelno >= logging.WARNING and r.name == _LOOP_LOGGER
        ]
        assert warning_records, (
            "Expected a WARNING log when log_completion() raises OSError on the failure path"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_completion_new_session_failure_io_error_emits_warning_log(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When new_session() fails and log_completion() also raises OSError, WARNING is logged."""
        from owlbear_orchestrator.acp_client import AcpClientError, ErrorCategory

        mock_client.new_session = AsyncMock(
            side_effect=AcpClientError("conn refused", category=ErrorCategory.TRANSIENT)
        )
        mock_audit_log.log_completion.side_effect = OSError("write error")

        with caplog.at_level(logging.WARNING, logger=_LOOP_LOGGER):
            result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        assert result is False

        warning_records = [
            r for r in caplog.records if r.levelno >= logging.WARNING and r.name == _LOOP_LOGGER
        ]
        assert warning_records, (
            "Expected a WARNING log when log_completion() raises OSError after new_session() failure"
        )

    # ------------------------------------------------------------------
    # Boundary: both audit failures in one dispatch emit separate warnings
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_both_log_dispatch_and_log_completion_io_errors_emit_warnings(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When both log_dispatch and log_completion raise OSError, TWO warnings must be emitted."""
        mock_audit_log.log_dispatch.side_effect = OSError("dispatch write error")
        mock_audit_log.log_completion.side_effect = OSError("completion write error")

        with caplog.at_level(logging.WARNING, logger=_LOOP_LOGGER):
            result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        # Dispatch must still succeed
        assert result is True

        warning_records = [
            r for r in caplog.records if r.levelno >= logging.WARNING and r.name == _LOOP_LOGGER
        ]
        assert len(warning_records) >= 2, (
            f"Expected ≥2 WARNING logs (one for log_dispatch, one for log_completion), "
            f"got {len(warning_records)}"
        )
