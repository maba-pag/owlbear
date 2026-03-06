"""Comprehensive error recovery tests — fills coverage gaps and adds integration scenarios.

Targets >= 90 % coverage on:
- owlbear.core.errors (ErrorCategory, classify_error, ToolError)
- owlbear.tools.hooked (HookedToolset retry logic)
- owlbear.core.escalation (EscalationHook, _parse_response, _on_error)
- owlbear.memory.error_journal (ErrorJournal log/query/rotate)

Task: #364
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import httpx
import pytest

from owlbear.core.command_guard import BlockedCommandError
from owlbear.core.errors import ErrorCategory, ToolError, classify_error
from owlbear.core.escalation import EscalationAction, EscalationHook
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.memory.error_journal import ErrorJournal
from owlbear.tools.hooked import HookedToolset, _is_transient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> Any:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _http_status_error(code: int) -> httpx.HTTPStatusError:
    """Build an ``httpx.HTTPStatusError`` with the given status code."""
    response = httpx.Response(code, request=httpx.Request("GET", "https://x"))
    return httpx.HTTPStatusError("err", request=response.request, response=response)


def _make_channel(response: str | None = "retry") -> AsyncMock:
    """Create a mock ChannelPlugin."""
    channel = AsyncMock()
    type(channel).name = PropertyMock(return_value="test")
    channel.receive = AsyncMock(return_value=response)
    return channel


def _make_journal(tmp_path: Path) -> ErrorJournal:
    """Create an ErrorJournal pointing at a temp directory."""
    return ErrorJournal(workspace=tmp_path)


def _log_entry(  # noqa: PLR0913
    journal: ErrorJournal,
    *,
    ts: str = "2026-03-01T12:00:00Z",
    error_type: str = "transient",
    tool_name: str = "run_command",
    exc_message: str = "connection refused",
    action_taken: str = "retry",
    attempt: int = 1,
    resolved: bool = False,
    session_id: str = "sess-001",
) -> None:
    """Log a single entry with configurable defaults."""
    journal.log(
        ts=ts,
        error_type=error_type,
        tool_name=tool_name,
        exc_message=exc_message,
        action_taken=action_taken,
        attempt=attempt,
        resolved=resolved,
        session_id=session_id,
    )


# ===========================================================================
# 1. Error classification — coverage gap: _classify_http_status permanent path
# ===========================================================================


class TestClassifyHttpStatusPermanent:
    """HTTP status codes that are neither transient nor auth → PERMANENT."""

    def test_http_500_is_permanent(self) -> None:
        assert classify_error(_http_status_error(500)) is ErrorCategory.PERMANENT

    def test_http_404_is_permanent(self) -> None:
        assert classify_error(_http_status_error(404)) is ErrorCategory.PERMANENT

    def test_http_400_is_permanent(self) -> None:
        assert classify_error(_http_status_error(400)) is ErrorCategory.PERMANENT

    def test_http_422_is_permanent(self) -> None:
        assert classify_error(_http_status_error(422)) is ErrorCategory.PERMANENT

    def test_http_405_is_permanent(self) -> None:
        assert classify_error(_http_status_error(405)) is ErrorCategory.PERMANENT

    def test_http_409_is_permanent(self) -> None:
        assert classify_error(_http_status_error(409)) is ErrorCategory.PERMANENT


# ===========================================================================
# 2. _is_transient helper (hooked.py)
# ===========================================================================


class TestIsTransient:
    """_is_transient predicate used by tenacity retry decorator."""

    def test_transient_network_error_returns_true(self) -> None:
        assert _is_transient(httpx.ConnectError("fail")) is True

    def test_transient_timeout_returns_true(self) -> None:
        assert _is_transient(httpx.TimeoutException("t")) is True

    def test_transient_429_returns_true(self) -> None:
        assert _is_transient(_http_status_error(429)) is True

    def test_permanent_error_returns_false(self) -> None:
        assert _is_transient(FileNotFoundError("x")) is False

    def test_auth_error_returns_false(self) -> None:
        assert _is_transient(_http_status_error(401)) is False

    def test_tool_semantic_returns_false(self) -> None:
        assert _is_transient(ValueError("bad")) is False

    def test_base_exception_returns_false(self) -> None:
        """BaseException (non-Exception) is never transient."""
        assert _is_transient(KeyboardInterrupt()) is False

    def test_system_exit_returns_false(self) -> None:
        assert _is_transient(SystemExit(1)) is False


# ===========================================================================
# 3. EscalationHook._on_error edge cases — coverage gaps lines 91, 94
# ===========================================================================


class TestOnErrorEdgeCases:
    """_on_error early-return paths — non-dict data, missing error key."""

    def test_on_error_ignores_non_dict_data(self) -> None:
        """When data is not a dict, _on_error returns without escalating."""
        hooks = HookRegistry()
        channel = _make_channel("retry")
        EscalationHook(hooks=hooks, channel=channel)

        # Emit ON_ERROR with a string (not a dict)
        _run(hooks.emit(HookEvent.ON_ERROR, "not a dict"))

        # channel.send should NOT have been called
        channel.send.assert_not_called()

    def test_on_error_ignores_none_data(self) -> None:
        """When data is None, _on_error returns without escalating."""
        hooks = HookRegistry()
        channel = _make_channel("retry")
        EscalationHook(hooks=hooks, channel=channel)

        _run(hooks.emit(HookEvent.ON_ERROR, None))

        channel.send.assert_not_called()

    def test_on_error_ignores_dict_without_error_key(self) -> None:
        """When dict has no 'error' key or it's not an Exception, skip."""
        hooks = HookRegistry()
        channel = _make_channel("retry")
        EscalationHook(hooks=hooks, channel=channel)

        _run(hooks.emit(HookEvent.ON_ERROR, {"tool_name": "fetch", "attempt": 3}))

        channel.send.assert_not_called()

    def test_on_error_ignores_non_exception_error_value(self) -> None:
        """When 'error' key is a string (not Exception), skip."""
        hooks = HookRegistry()
        channel = _make_channel("retry")
        EscalationHook(hooks=hooks, channel=channel)

        _run(hooks.emit(HookEvent.ON_ERROR, {"error": "just a string", "tool_name": "x"}))

        channel.send.assert_not_called()

    def test_on_error_uses_defaults_for_missing_tool_name_and_attempt(self) -> None:
        """When tool_name/attempt are missing, defaults to 'unknown'/0."""
        hooks = HookRegistry()
        channel = _make_channel("skip")
        EscalationHook(hooks=hooks, channel=channel)

        _run(hooks.emit(HookEvent.ON_ERROR, {"error": RuntimeError("boom")}))

        channel.send.assert_called_once()
        sent_msg = channel.send.call_args[0][0]
        assert "unknown" in sent_msg
        assert "0" in sent_msg


# ===========================================================================
# 4. EscalationHook._parse_response — additional edge cases
# ===========================================================================


class TestParseResponseEdgeCases:
    """_parse_response boundary conditions beyond the main test file."""

    def test_whitespace_retry(self) -> None:
        assert EscalationHook._parse_response("  retry  ") is EscalationAction.RETRY

    def test_uppercase_skip(self) -> None:
        assert EscalationHook._parse_response("SKIP") is EscalationAction.SKIP

    def test_mixed_case_abort(self) -> None:
        assert EscalationHook._parse_response("Abort") is EscalationAction.ABORT

    def test_empty_string_aborts(self) -> None:
        assert EscalationHook._parse_response("") is EscalationAction.ABORT

    def test_numeric_with_whitespace(self) -> None:
        assert EscalationHook._parse_response("  2  ") is EscalationAction.SKIP

    def test_out_of_range_number(self) -> None:
        assert EscalationHook._parse_response("4") is EscalationAction.ABORT

    def test_zero_is_invalid(self) -> None:
        assert EscalationHook._parse_response("0") is EscalationAction.ABORT


# ===========================================================================
# 5. ToolError — integration with classify_error
# ===========================================================================


class TestToolErrorIntegration:
    """ToolError construction from classify_error output."""

    def test_tool_error_from_classified_exception(self) -> None:
        """classify_error → ToolError → to_dict round-trip."""
        exc = httpx.ConnectError("network down")
        cat = classify_error(exc)
        err = ToolError(error_type=cat, tool_name="web_fetch", message=str(exc))

        d = err.to_dict()
        assert d["error_type"] == "transient"
        assert d["tool_name"] == "web_fetch"
        assert "network down" in d["message"]

    def test_tool_error_permanent_from_blocked_command(self) -> None:
        exc = BlockedCommandError("rm -rf /", r"rm\s+-rf\s+/")
        cat = classify_error(exc)
        err = ToolError(error_type=cat, tool_name="run_command", message=str(exc))

        assert err.error_type is ErrorCategory.PERMANENT
        assert err.to_dict()["status"] == "error"

    def test_tool_error_all_categories_round_trip_json(self) -> None:
        """Every ErrorCategory produces a valid JSON-serializable ToolError."""
        for cat in ErrorCategory:
            err = ToolError(error_type=cat, tool_name="test", message="msg")
            raw = json.dumps(err.to_dict())
            parsed = json.loads(raw)
            assert parsed["error_type"] == cat.value
            assert parsed["status"] == "error"

    def test_tool_error_slots(self) -> None:
        """ToolError uses __slots__ — no __dict__."""
        err = ToolError(error_type=ErrorCategory.AUTH, tool_name="t", message="m")
        assert not hasattr(err, "__dict__")


# ===========================================================================
# 6. ErrorJournal — additional edge cases
# ===========================================================================


class TestErrorJournalEdgeCases:
    """Additional edge cases for error_journal.py."""

    def test_query_on_nonexistent_file(self, tmp_path: Path) -> None:
        """query() on a never-written journal returns empty list."""
        journal = _make_journal(tmp_path)
        assert journal.query() == []

    def test_log_special_characters(self, tmp_path: Path) -> None:
        """Entries with special characters (quotes, newlines) survive round-trip."""
        journal = _make_journal(tmp_path)
        journal.log(
            ts="2026-03-01T12:00:00Z",
            error_type="transient",
            tool_name='tool "with" quotes',
            exc_message="line1\nline2",
            action_taken="retry",
            attempt=1,
            resolved=False,
            session_id="sess-special",
        )
        results = journal.query()
        assert len(results) == 1
        assert results[0].tool_name == 'tool "with" quotes'
        assert "line1\nline2" in results[0].exception_message

    def test_rotation_preserves_json_integrity(self, tmp_path: Path) -> None:
        """After rotation, every line is still valid JSON."""
        journal = ErrorJournal(workspace=tmp_path, max_entries=5)
        for i in range(10):
            _log_entry(journal, tool_name=f"tool_{i}")
        lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            json.loads(line)  # must not raise
        assert len(lines) == 5

    def test_multiple_rotations(self, tmp_path: Path) -> None:
        """Multiple rotation cycles produce correct final state."""
        journal = ErrorJournal(workspace=tmp_path, max_entries=3)
        for i in range(20):
            _log_entry(journal, tool_name=f"tool_{i}")
        results = journal.query()
        assert len(results) == 3
        assert results[-1].tool_name == "tool_19"

    def test_query_filter_combination_no_match(self, tmp_path: Path) -> None:
        """Query with filters that eliminate all entries returns []."""
        journal = _make_journal(tmp_path)
        _log_entry(journal, tool_name="a", error_type="transient")
        _log_entry(journal, tool_name="b", error_type="auth")
        results = journal.query(tool_name="a", error_type="auth")
        assert results == []


# ===========================================================================
# 7. HookedToolset retry — additional integration scenarios
# ===========================================================================


class TestHookedToolsetRetryEdgeCases:
    """Additional retry scenarios for HookedToolset."""

    def test_two_transient_failures_then_success(self) -> None:
        """Two transient failures followed by success — 3 total attempts."""
        hooks = HookRegistry()
        mock_ts = MagicMock()
        mock_ts.call_tool = AsyncMock(
            side_effect=[
                httpx.ConnectError("fail1"),
                httpx.TimeoutException("timeout"),
                "finally ok",
            ]
        )
        hooked = HookedToolset(wrapped=mock_ts, hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(hooked.call_tool("fetch", {}, ctx, tool))
        assert result == "finally ok"
        assert mock_ts.call_tool.call_count == 3

    def test_post_hook_not_emitted_on_retry_failure(self) -> None:
        """POST_TOOL_USE is NOT emitted when all retries are exhausted."""
        hooks = HookRegistry()
        post_calls: list[dict[str, Any]] = []
        hooks.register(HookEvent.POST_TOOL_USE, post_calls.append)

        mock_ts = MagicMock()
        mock_ts.call_tool = AsyncMock(side_effect=httpx.ConnectError("fail"))
        hooked = HookedToolset(wrapped=mock_ts, hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        with pytest.raises(httpx.ConnectError):
            _run(hooked.call_tool("fetch", {}, ctx, tool))

        assert len(post_calls) == 0

    def test_pre_hook_emitted_once_even_with_retries(self) -> None:
        """PRE_TOOL_USE fires once regardless of retry count."""
        hooks = HookRegistry()
        pre_calls: list[dict[str, Any]] = []
        hooks.register(HookEvent.PRE_TOOL_USE, pre_calls.append)

        mock_ts = MagicMock()
        mock_ts.call_tool = AsyncMock(side_effect=[httpx.ConnectError("fail"), "ok"])
        hooked = HookedToolset(wrapped=mock_ts, hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        _run(hooked.call_tool("fetch", {}, ctx, tool))

        assert len(pre_calls) == 1

    def test_runtime_error_not_retried(self) -> None:
        """RuntimeError (PERMANENT) propagates immediately — 1 attempt."""
        hooks = HookRegistry()
        mock_ts = MagicMock()
        mock_ts.call_tool = AsyncMock(side_effect=RuntimeError("fatal"))
        hooked = HookedToolset(wrapped=mock_ts, hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        with pytest.raises(RuntimeError, match="fatal"):
            _run(hooked.call_tool("compute", {}, ctx, tool))

        assert mock_ts.call_tool.call_count == 1


# ===========================================================================
# 8. End-to-end: classify → ToolError → journal log
# ===========================================================================


class TestEndToEndErrorFlow:
    """Integration: classify_error → ToolError → ErrorJournal.log."""

    def test_transient_error_flows_through_pipeline(self, tmp_path: Path) -> None:
        """Transient error is classified, packaged as ToolError, and logged."""
        exc = httpx.ConnectError("connection refused")
        cat = classify_error(exc)
        tool_err = ToolError(error_type=cat, tool_name="web_fetch", message=str(exc))

        journal = _make_journal(tmp_path)
        journal.log(
            ts="2026-03-03T10:00:00Z",
            error_type=tool_err.error_type.value,
            tool_name=tool_err.tool_name,
            exc_message=tool_err.message,
            action_taken="retry",
            attempt=1,
            resolved=False,
            session_id="sess-e2e",
        )

        results = journal.query(tool_name="web_fetch", error_type="transient")
        assert len(results) == 1
        assert results[0].exception_message == "connection refused"

    def test_permanent_error_flows_through_pipeline(self, tmp_path: Path) -> None:
        exc = FileNotFoundError("missing.txt")
        cat = classify_error(exc)
        tool_err = ToolError(error_type=cat, tool_name="read_file", message=str(exc))

        journal = _make_journal(tmp_path)
        journal.log(
            ts="2026-03-03T10:01:00Z",
            error_type=tool_err.error_type.value,
            tool_name=tool_err.tool_name,
            exc_message=tool_err.message,
            action_taken="escalate",
            attempt=1,
            resolved=True,
            session_id="sess-e2e",
        )

        results = journal.query(error_type="permanent")
        assert len(results) == 1
        assert results[0].resolved is True

    def test_auth_error_flows_through_pipeline(self, tmp_path: Path) -> None:
        exc = _http_status_error(401)
        cat = classify_error(exc)
        tool_err = ToolError(error_type=cat, tool_name="llm_call", message=str(exc))

        journal = _make_journal(tmp_path)
        journal.log(
            ts="2026-03-03T10:02:00Z",
            error_type=tool_err.error_type.value,
            tool_name=tool_err.tool_name,
            exc_message=tool_err.message,
            action_taken="refresh_token",
            attempt=1,
            resolved=True,
            session_id="sess-e2e",
        )

        results = journal.query(error_type="auth")
        assert len(results) == 1
        assert results[0].action_taken == "refresh_token"

    def test_tool_semantic_error_flows_through_pipeline(self, tmp_path: Path) -> None:
        exc = ValueError("invalid argument")
        cat = classify_error(exc)
        assert cat is ErrorCategory.TOOL_SEMANTIC

        tool_err = ToolError(error_type=cat, tool_name="compute", message=str(exc))
        journal = _make_journal(tmp_path)
        journal.log(
            ts="2026-03-03T10:03:00Z",
            error_type=tool_err.error_type.value,
            tool_name=tool_err.tool_name,
            exc_message=tool_err.message,
            action_taken="model_retry",
            attempt=1,
            resolved=True,
            session_id="sess-e2e",
        )

        results = journal.query(error_type="tool_semantic")
        assert len(results) == 1
