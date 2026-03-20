"""RED-phase tests for #841 — _log_to_journal must become async (task #541).

Tests verify the contract described in #841 AC:
1. _log_to_journal is a coroutine function
2. journal=None returns immediately without calling asyncio.to_thread
3. asyncio.to_thread is called with journal.log and correct kwargs
4. Exceptions from asyncio.to_thread are caught and logged (best-effort)
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.daemon import _log_to_journal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run an async coroutine synchronously (mirrors test_daemon.py pattern)."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_agent() -> MagicMock:
    """Build a minimal OwlBearAgent mock with a session path."""
    agent = MagicMock()
    agent.session = MagicMock()
    agent.session.path = Path("sessions/test.jsonl")
    return agent


def _make_journal() -> MagicMock:
    """Build a minimal ErrorJournal mock."""
    journal = MagicMock()
    journal.log = MagicMock()
    return journal


# ---------------------------------------------------------------------------
# AC1 — _log_to_journal is a coroutine function
# ---------------------------------------------------------------------------


class TestFromAC_LogToJournalIsCoroutine:  # noqa: N801
    """_log_to_journal must be declared as async def."""

    def test_is_coroutinefunction(self) -> None:
        """inspect.iscoroutinefunction(_log_to_journal) must return True."""
        assert inspect.iscoroutinefunction(_log_to_journal)


# ---------------------------------------------------------------------------
# AC2 — journal=None exits immediately, asyncio.to_thread not called
# ---------------------------------------------------------------------------


class TestFromAC_LogToJournalNoneJournal:  # noqa: N801
    """When journal is None, _log_to_journal must return without touching to_thread."""

    def test_journal_none_skips_to_thread(self) -> None:
        """asyncio.to_thread must NOT be called when journal is None."""
        agent = _make_agent()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    None,
                    error_type="transient",
                    exc=RuntimeError("boom"),
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )
        mock_to_thread.assert_not_called()

    def test_journal_none_does_not_raise(self) -> None:
        """Calling with journal=None must never raise an exception."""
        agent = _make_agent()
        _run(
            _log_to_journal(
                None,
                error_type="transient",
                exc=RuntimeError("boom"),
                action_taken="retry",
                attempt=1,
                resolved=False,
                agent=agent,
            )
        )  # must complete without error


# ---------------------------------------------------------------------------
# AC3 — asyncio.to_thread called with journal.log and correct kwargs
# ---------------------------------------------------------------------------


class TestFromAC_LogToJournalToThread:  # noqa: N801
    """_log_to_journal must delegate to asyncio.to_thread(journal.log, ...)."""

    def test_calls_to_thread_with_journal_log(self) -> None:
        """asyncio.to_thread must be called exactly once with journal.log."""
        journal = _make_journal()
        agent = _make_agent()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=RuntimeError("fail"),
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )
        mock_to_thread.assert_called_once()
        positional_args = mock_to_thread.call_args.args
        assert positional_args[0] is journal.log

    def test_to_thread_passes_error_type(self) -> None:
        """asyncio.to_thread must forward error_type kwarg to journal.log."""
        journal = _make_journal()
        agent = _make_agent()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    journal,
                    error_type="permanent",
                    exc=ValueError("bad"),
                    action_taken="abort",
                    attempt=2,
                    resolved=True,
                    agent=agent,
                )
            )
        kwargs = mock_to_thread.call_args.kwargs
        assert kwargs["error_type"] == "permanent"

    def test_to_thread_passes_tool_name_agent_turn(self) -> None:
        """asyncio.to_thread must pass tool_name='agent.turn'."""
        journal = _make_journal()
        agent = _make_agent()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=RuntimeError("x"),
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )
        kwargs = mock_to_thread.call_args.kwargs
        assert kwargs["tool_name"] == "agent.turn"

    def test_to_thread_passes_exc_message(self) -> None:
        """asyncio.to_thread must pass exc_message=str(exc)."""
        journal = _make_journal()
        agent = _make_agent()
        exc = RuntimeError("specific error message")
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=exc,
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )
        kwargs = mock_to_thread.call_args.kwargs
        assert kwargs["exc_message"] == str(exc)

    def test_to_thread_passes_action_taken(self) -> None:
        """asyncio.to_thread must forward action_taken kwarg."""
        journal = _make_journal()
        agent = _make_agent()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=RuntimeError("x"),
                    action_taken="transient_retries_exhausted",
                    attempt=3,
                    resolved=False,
                    agent=agent,
                )
            )
        kwargs = mock_to_thread.call_args.kwargs
        assert kwargs["action_taken"] == "transient_retries_exhausted"
        assert kwargs["attempt"] == 3
        assert kwargs["resolved"] is False

    def test_to_thread_passes_session_id_from_agent(self) -> None:
        """asyncio.to_thread must pass session_id derived from agent.session.path."""
        journal = _make_journal()
        agent = _make_agent()
        session_path = Path("sessions/my-session.jsonl")
        agent.session.path = session_path
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=RuntimeError("x"),
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )
        kwargs = mock_to_thread.call_args.kwargs
        assert kwargs["session_id"] == str(session_path)

    def test_to_thread_passes_ts_kwarg(self) -> None:
        """asyncio.to_thread must include a 'ts' timestamp kwarg."""
        journal = _make_journal()
        agent = _make_agent()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=RuntimeError("x"),
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )
        kwargs = mock_to_thread.call_args.kwargs
        assert "ts" in kwargs
        assert isinstance(kwargs["ts"], str)
        assert len(kwargs["ts"]) > 0


# ---------------------------------------------------------------------------
# AC4 — exceptions from asyncio.to_thread are caught (best-effort)
# ---------------------------------------------------------------------------


class TestFromAC_LogToJournalBestEffort:  # noqa: N801
    """_log_to_journal must swallow exceptions from asyncio.to_thread."""

    def test_exception_from_to_thread_does_not_propagate(self) -> None:
        """RuntimeError raised by asyncio.to_thread must be caught silently."""
        journal = _make_journal()
        agent = _make_agent()
        with patch(
            "asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=RuntimeError("thread pool exhausted"),
        ):
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=RuntimeError("original error"),
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )  # must not raise

    def test_exception_from_to_thread_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A failure inside asyncio.to_thread must emit a WARNING log entry."""
        journal = _make_journal()
        agent = _make_agent()
        with (
            patch(
                "asyncio.to_thread",
                new_callable=AsyncMock,
                side_effect=RuntimeError("thread pool exhausted"),
            ),
            caplog.at_level(logging.WARNING, logger="owlbear.daemon"),
        ):
            _run(
                _log_to_journal(
                    journal,
                    error_type="transient",
                    exc=RuntimeError("original error"),
                    action_taken="retry",
                    attempt=1,
                    resolved=False,
                    agent=agent,
                )
            )
        assert any("error journal" in record.message.lower() for record in caplog.records), (
            f"Expected 'error journal' warning, got: {[r.message for r in caplog.records]}"
        )

    def test_various_exception_types_are_caught(self) -> None:
        """Best-effort contract covers all exception types from to_thread."""
        journal = _make_journal()
        agent = _make_agent()
        for exc_type in (ValueError, OSError, MemoryError):
            with patch(
                "asyncio.to_thread",
                new_callable=AsyncMock,
                side_effect=exc_type("injected"),
            ):
                _run(
                    _log_to_journal(
                        journal,
                        error_type="transient",
                        exc=RuntimeError("original"),
                        action_taken="retry",
                        attempt=1,
                        resolved=False,
                        agent=agent,
                    )
                )  # must not raise for any exc_type
