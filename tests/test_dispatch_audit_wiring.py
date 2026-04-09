"""Tests for task #204 — Audit log wired into dispatch loop.

TDD RED phase: all tests fail before #164 wires audit log into the dispatch loop.

Module under test: owlbear.orchestrator (loop.py)
  Imports expected after #146 + #164 are implemented:
    dispatch_entry(entry, client, *, audit_log, ...) -> bool
    run_loop(kanban_bin, kanban_dir, client, *, audit_log, ...) -> None

Conventions: asyncio_mode=strict → @pytest.mark.asyncio(loop_scope="function").
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.audit import AuditLog, CompletionEvent, DispatchEvent
from owlbear.planner.models import DispatchEntry

# These imports fail RED-phase until #146 + #164 are implemented.
from owlbear.orchestrator import dispatch_entry, run_loop  # type: ignore[import]


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
    session_resp.session_id = "test-session-abc"
    client.new_session = AsyncMock(return_value=session_resp)
    client.prompt = AsyncMock(return_value=MagicMock())
    return client


@pytest.fixture
def mock_audit_log() -> MagicMock:
    return MagicMock(spec=AuditLog)


# ---------------------------------------------------------------------------
# AC #204 tests
# ---------------------------------------------------------------------------


class TestFromAC_DispatchAuditWiring:  # noqa: N801
    """Audit log wired into dispatch loop — all 8 AC lines covered."""

    # ------------------------------------------------------------------
    # AC1: AuditLog injected via parameter (not instantiated globally)
    # ------------------------------------------------------------------

    def test_run_loop_accepts_audit_log_parameter(self) -> None:
        """run_loop must declare audit_log as a parameter, not create it internally."""
        sig = inspect.signature(run_loop)
        assert "audit_log" in sig.parameters, "run_loop must accept audit_log as an injection parameter"

    # ------------------------------------------------------------------
    # AC2: log_dispatch() called before prompt(), DispatchEvent fields
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_dispatch_called_before_prompt(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """log_dispatch must be invoked before client.prompt."""
        call_order: list[str] = []

        def _record_dispatch(*_args: Any, **_kw: Any) -> None:
            call_order.append("log_dispatch")

        async def _record_prompt(*_args: Any, **_kw: Any) -> MagicMock:
            call_order.append("prompt")
            return MagicMock()

        mock_audit_log.log_dispatch.side_effect = _record_dispatch
        mock_client.prompt.side_effect = _record_prompt

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        assert "log_dispatch" in call_order, "log_dispatch was never called"
        assert "prompt" in call_order, "prompt was never called"
        assert call_order.index("log_dispatch") < call_order.index("prompt")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_event_task_id_and_agent(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """DispatchEvent passed to log_dispatch must carry task_id and agent from entry."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_dispatch.assert_called_once()
        dispatch_event: DispatchEvent = mock_audit_log.log_dispatch.call_args.args[0]
        assert isinstance(dispatch_event, DispatchEvent)
        assert dispatch_event.task_id == 42
        assert dispatch_event.agent == "builder"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_event_session_id_matches_new_session(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """DispatchEvent.session_id must match the session created by new_session()."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        dispatch_event: DispatchEvent = mock_audit_log.log_dispatch.call_args.args[0]
        assert dispatch_event.session_id == "test-session-abc"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_event_timestamp_is_iso8601(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """DispatchEvent.timestamp must be a non-empty ISO-8601 string."""
        from datetime import datetime

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        dispatch_event: DispatchEvent = mock_audit_log.log_dispatch.call_args.args[0]
        assert isinstance(dispatch_event.timestamp, str)
        assert dispatch_event.timestamp  # non-empty
        datetime.fromisoformat(dispatch_event.timestamp)  # must parse

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_event_prompt_summary_max_100_chars(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """prompt_summary must be at most 100 characters (DispatchEvent model constraint)."""
        # Inject a long format_prompt return value to trigger truncation logic
        with patch("owlbear.orchestrator.loop.format_prompt", return_value="x" * 200):
            await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        dispatch_event: DispatchEvent = mock_audit_log.log_dispatch.call_args.args[0]
        assert len(dispatch_event.prompt_summary) <= 100

    # ------------------------------------------------------------------
    # AC3: log_completion() called after prompt() returns, CompletionEvent fields
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_completion_called_after_prompt(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """log_completion must be invoked after client.prompt returns."""
        call_order: list[str] = []

        async def _record_prompt(*_args: Any, **_kw: Any) -> MagicMock:
            call_order.append("prompt")
            return MagicMock()

        def _record_completion(*_args: Any, **_kw: Any) -> None:
            call_order.append("log_completion")

        mock_client.prompt.side_effect = _record_prompt
        mock_audit_log.log_completion.side_effect = _record_completion

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        assert "prompt" in call_order, "prompt was never called"
        assert "log_completion" in call_order, "log_completion was never called"
        assert call_order.index("prompt") < call_order.index("log_completion")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_completion_event_task_id_agent_and_outcome(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """CompletionEvent must carry task_id, agent, and outcome='success' on normal return."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_completion.assert_called_once()
        completion_event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert isinstance(completion_event, CompletionEvent)
        assert completion_event.task_id == 42
        assert completion_event.agent == "builder"
        assert completion_event.outcome == "success"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_completion_event_duration_ms_is_int(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """CompletionEvent.duration_ms must be an int."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        completion_event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert isinstance(completion_event.duration_ms, int)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_completion_event_files_changed_is_list(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """CompletionEvent.files_changed must be a list."""
        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        completion_event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert isinstance(completion_event.files_changed, list)

    # ------------------------------------------------------------------
    # AC4: duration_ms uses time.monotonic (not wall clock)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_duration_ms_uses_monotonic_clock(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """duration_ms must be derived from time.monotonic, not time.time."""
        with patch("time.monotonic", side_effect=[1000.0, 1001.5]) as mock_mono:
            await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        # At least start and end measurements
        assert mock_mono.call_count >= 2

        completion_event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        # 1001.5 - 1000.0 = 1.5 s = 1500 ms
        assert completion_event.duration_ms == 1500

    # ------------------------------------------------------------------
    # AC5: files_changed populated via git diff before/after dispatch
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_files_changed_populated_via_git_diff(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """files_changed must reflect files that changed during dispatch (git diff)."""
        before = MagicMock()
        before.stdout = ""  # no changes before dispatch
        after = MagicMock()
        after.stdout = "src/foo.py\nsrc/bar.py\n"  # two files changed after

        with patch("subprocess.run", side_effect=[before, after]):
            await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        completion_event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert "src/foo.py" in completion_event.files_changed
        assert "src/bar.py" in completion_event.files_changed

    @pytest.mark.asyncio(loop_scope="function")
    async def test_files_changed_empty_when_no_diff(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """files_changed is empty list when git diff returns no output."""
        empty = MagicMock()
        empty.stdout = ""

        with patch("subprocess.run", side_effect=[empty, empty]):
            await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        completion_event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert completion_event.files_changed == []

    # ------------------------------------------------------------------
    # AC6: audit I/O error in log_dispatch does not propagate
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_dispatch_io_error_does_not_propagate(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """OSError from log_dispatch must not abort dispatch — prompt still called."""
        mock_audit_log.log_dispatch.side_effect = OSError("disk full")

        # Must not raise; dispatch must continue
        result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_client.prompt.assert_called_once()
        assert result is True

    # ------------------------------------------------------------------
    # AC7: audit I/O error in log_completion does not propagate
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_log_completion_io_error_does_not_propagate(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """OSError from log_completion must not abort dispatch — returns success."""
        mock_audit_log.log_completion.side_effect = OSError("disk full")

        # Must not raise; dispatch must report success
        result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        assert result is True

    # ------------------------------------------------------------------
    # AC8: full integration round-trip — both events in session JSONL
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_integration_round_trip_both_events_in_jsonl(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Full round-trip: DispatchEvent and CompletionEvent both written to session JSONL."""
        session_resp = MagicMock()
        session_resp.session_id = "sess-round-trip"
        mock_client.new_session = AsyncMock(return_value=session_resp)

        audit_log = AuditLog(audit_dir=tmp_path / "audit")
        await dispatch_entry(entry, mock_client, audit_log=audit_log)

        session_file = tmp_path / "audit" / "sess-round-trip.jsonl"
        assert session_file.exists(), "session JSONL file must be created"

        lines = [json.loads(line) for line in session_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2, f"Expected 2 events (dispatch + completion), got {len(lines)}"

        event_types = {line["type"] for line in lines}
        assert event_types == {"dispatch", "completion"}

        dispatch_line = next(ln for ln in lines if ln["type"] == "dispatch")
        assert dispatch_line["task_id"] == 42
        assert dispatch_line["agent"] == "builder"
        assert dispatch_line["session_id"] == "sess-round-trip"

        completion_line = next(ln for ln in lines if ln["type"] == "completion")
        assert completion_line["task_id"] == 42
        assert completion_line["agent"] == "builder"
        assert completion_line["outcome"] in ("success", "failure")
