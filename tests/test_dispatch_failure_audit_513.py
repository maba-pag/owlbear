"""Tests for task #513 — Fix dispatch failure audit logging gap.

dispatch_entry() currently emits CompletionEvent only on success. This test
suite verifies the missing failure-path audit emission for both failure sites:

  1. client.new_session() raises AcpClientError or TimeoutError
  2. client.prompt() raises AcpClientError or TimeoutError

All tests must FAIL until loop.py is updated (RED phase).

Module under test: owlbear.orchestrator.loop.dispatch_entry
Integration under test: owlbear_orchestrator.analysis.detectors
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.audit import AuditLog
from owlbear.audit.models import CompletionEvent
from owlbear.orchestrator import dispatch_entry
from owlbear.planner.models import DispatchEntry
from owlbear_orchestrator.acp_client import AcpClientError, ErrorCategory
from owlbear_orchestrator.analysis.detectors import (
    high_error_rate_detector,
    repeated_failure_detector,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def entry() -> DispatchEntry:
    return DispatchEntry(task_id=99, agent="builder", target_status="review")


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    session_resp = MagicMock()
    session_resp.session_id = "real-session-xyz"
    client.new_session = AsyncMock(return_value=session_resp)
    client.prompt = AsyncMock(return_value=MagicMock())
    return client


@pytest.fixture
def mock_audit_log() -> MagicMock:
    return MagicMock(spec=AuditLog)


@pytest.fixture
def acp_error() -> AcpClientError:
    return AcpClientError("acp connection refused", category=ErrorCategory.TRANSIENT)


# ---------------------------------------------------------------------------
# AC1: new_session() failure — CompletionEvent emission
# ---------------------------------------------------------------------------


class TestFromAC_DispatchFailureNewSession:  # noqa: N801
    """AC1: new_session() failure emits CompletionEvent(outcome='failure') via audit_log."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_acperror_emits_completion_event_failure(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """log_completion must be called with outcome='failure' when new_session raises AcpClientError."""
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_completion.assert_called_once()
        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert isinstance(event, CompletionEvent)
        assert event.outcome == "failure"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_timeout_emits_completion_event_failure(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """log_completion must be called with outcome='failure' when new_session raises TimeoutError."""
        mock_client.new_session = AsyncMock(side_effect=TimeoutError("deadline exceeded"))

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_completion.assert_called_once()
        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.outcome == "failure"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_error_field_contains_exception_message(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """CompletionEvent.error must equal str(exc) so detectors can access the message."""
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.error == str(acp_error)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_duration_ms_is_zero(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """duration_ms must be 0 on new_session failure since timing hadn't started."""
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.duration_ms == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_files_changed_is_empty(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """files_changed must be [] on new_session failure since no agent ran."""
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.files_changed == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_completion_event_carries_entry_fields(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """CompletionEvent.task_id and .agent must match the dispatch entry."""
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.task_id == entry.task_id
        assert event.agent == entry.agent

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_uses_synthetic_session_id_for_routing(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """audit_log.log_completion must be called with a non-empty synthetic session_id string.

        No real session exists, so the session_id in the file routing call must
        be a generated identifier (e.g. uuid4().hex), never None or empty string.
        """
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        # The second positional arg to log_completion is the session_id
        routing_session_id: str = mock_audit_log.log_completion.call_args.args[1]
        assert isinstance(routing_session_id, str)
        assert routing_session_id  # must be non-empty


# ---------------------------------------------------------------------------
# AC2: prompt() failure — CompletionEvent emission
# ---------------------------------------------------------------------------


class TestFromAC_DispatchFailurePrompt:  # noqa: N801
    """AC2: prompt() failure emits CompletionEvent(outcome='failure') with elapsed duration."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_acperror_emits_completion_event_failure(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """log_completion must be called with outcome='failure' when prompt raises AcpClientError."""
        mock_client.prompt = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_completion.assert_called_once()
        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert isinstance(event, CompletionEvent)
        assert event.outcome == "failure"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_timeout_emits_completion_event_failure(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """log_completion must be called with outcome='failure' when prompt raises TimeoutError."""
        mock_client.prompt = AsyncMock(side_effect=TimeoutError("agent timed out"))

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_completion.assert_called_once()
        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.outcome == "failure"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_failure_error_field_contains_exception_message(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """CompletionEvent.error must equal str(exc) so detectors can access the message."""
        mock_client.prompt = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.error == str(acp_error)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_failure_duration_ms_is_nonnegative(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """duration_ms must be >= 0 on prompt failure (elapsed since t_start)."""
        mock_client.prompt = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.duration_ms >= 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_failure_files_changed_is_empty(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """files_changed must be [] on prompt failure (no successful agent run)."""
        mock_client.prompt = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.files_changed == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_failure_completion_event_carries_entry_fields(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """CompletionEvent.task_id and .agent must match the dispatch entry."""
        mock_client.prompt = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        event: CompletionEvent = mock_audit_log.log_completion.call_args.args[0]
        assert event.task_id == entry.task_id
        assert event.agent == entry.agent

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_failure_uses_real_session_id_for_routing(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """audit_log.log_completion must be routed to the real session_id from new_session.

        Unlike new_session failure, prompt failure has a real session_id available
        (new_session succeeded). The completion event must be written to the same
        session file where the DispatchEvent was already written.
        """
        mock_client.prompt = AsyncMock(side_effect=acp_error)

        await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        routing_session_id: str = mock_audit_log.log_completion.call_args.args[1]
        assert routing_session_id == "real-session-xyz"


# ---------------------------------------------------------------------------
# AC3: audit_log=None guard — no-op when audit_log is None
# ---------------------------------------------------------------------------


class TestFromAC_DispatchFailureAuditNoneGuard:  # noqa: N801
    """AC3: failure-path audit emission is skipped when audit_log is None."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_no_audit_log_returns_false(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """dispatch_entry must return False without error when audit_log=None and new_session fails."""
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        result = await dispatch_entry(entry, mock_client, audit_log=None)

        assert result is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_failure_no_audit_log_returns_false(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """dispatch_entry must return False without error when audit_log=None and prompt fails."""
        mock_client.prompt = AsyncMock(side_effect=acp_error)

        result = await dispatch_entry(entry, mock_client, audit_log=None)

        assert result is False


# ---------------------------------------------------------------------------
# AC4: OSError suppression — log_completion OSError must not propagate
# ---------------------------------------------------------------------------


class TestFromAC_DispatchFailureOSErrorSuppression:  # noqa: N801
    """AC4: failure-path log_completion calls are wrapped in contextlib.suppress(OSError)."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_oserror_in_log_completion_suppressed(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """OSError raised by log_completion must be suppressed; dispatch_entry returns False.

        Verifies: (a) log_completion WAS called (new failure-path emission), and
        (b) the resulting OSError is suppressed (not propagated).
        """
        mock_client.new_session = AsyncMock(side_effect=acp_error)
        mock_audit_log.log_completion.side_effect = OSError("disk full")

        # Must not raise — OSError must be suppressed to match success-path pattern
        result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_completion.assert_called_once()  # emission happened
        assert result is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_failure_oserror_in_log_completion_suppressed(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """OSError raised by log_completion must be suppressed; dispatch_entry returns False.

        Verifies: (a) log_completion WAS called (new failure-path emission), and
        (b) the resulting OSError is suppressed (not propagated).
        """
        mock_client.prompt = AsyncMock(side_effect=acp_error)
        mock_audit_log.log_completion.side_effect = OSError("no space left")

        result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        mock_audit_log.log_completion.assert_called_once()  # emission happened
        assert result is False

    @pytest.mark.asyncio(loop_scope="function")
    async def test_new_session_failure_non_oserror_in_log_completion_propagates(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """Non-OSError from log_completion must propagate (only OSError is suppressed).

        This is a boundary test to ensure suppress(OSError) is specific, not broad.
        """
        mock_client.new_session = AsyncMock(side_effect=acp_error)
        mock_audit_log.log_completion.side_effect = RuntimeError("unexpected error")

        with pytest.raises(RuntimeError, match="unexpected error"):
            await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)


# ---------------------------------------------------------------------------
# AC6: Integration — failure CompletionEvents trigger detector proposals
# ---------------------------------------------------------------------------


class TestFromAC_DispatchFailureDetectorIntegration:  # noqa: N801
    """AC6: failure CompletionEvents feed high_error_rate and repeated_failure detectors."""

    def _make_failure_event(
        self,
        task_id: int,
        agent: str = "builder",
        error: str = "acp session failed",
    ) -> CompletionEvent:
        return CompletionEvent(
            timestamp=datetime.now(tz=UTC).isoformat(),
            task_id=task_id,
            agent=agent,
            outcome="failure",
            duration_ms=0,
            files_changed=[],
            error=error,
        )

    def test_high_error_rate_detector_fires_on_dispatch_failure_events(self) -> None:
        """high_error_rate_detector must produce AnalysisProposal for 3+ dispatch failures."""
        # 3 failure events for same agent (100% failure rate meets >= 40% threshold)
        events = [self._make_failure_event(task_id=i, agent="builder") for i in range(3)]

        proposals = high_error_rate_detector(events)

        assert len(proposals) >= 1
        agents = {p.target_agent for p in proposals}
        assert "builder" in agents

    def test_high_error_rate_detector_pattern_is_high_error_rate(self) -> None:
        """AnalysisProposal from high_error_rate_detector must have pattern='high_error_rate'."""
        events = [self._make_failure_event(task_id=i, agent="reviewer") for i in range(3)]

        proposals = high_error_rate_detector(events)

        assert any(p.pattern == "high_error_rate" for p in proposals)

    def test_repeated_failure_detector_fires_on_dispatch_failure_events(self) -> None:
        """repeated_failure_detector must produce AnalysisProposal when same task fails >= 2 times."""
        # 2 failure events for the same task_id — satisfies MIN_REPEATED_FAILURES = 2
        events = [
            self._make_failure_event(task_id=42, agent="builder"),
            self._make_failure_event(task_id=42, agent="builder"),
        ]

        proposals = repeated_failure_detector(events)

        assert len(proposals) >= 1
        task_ids = {p.evidence["task_id"] for p in proposals}
        assert 42 in task_ids

    def test_repeated_failure_detector_pattern_is_repeated_failure(self) -> None:
        """AnalysisProposal from repeated_failure_detector must have pattern='repeated_failure'."""
        events = [
            self._make_failure_event(task_id=77, agent="architect"),
            self._make_failure_event(task_id=77, agent="architect"),
        ]

        proposals = repeated_failure_detector(events)

        assert any(p.pattern == "repeated_failure" for p in proposals)

    def test_high_error_rate_detector_below_min_dispatches_no_proposal(self) -> None:
        """high_error_rate_detector must NOT fire when fewer than MIN_DISPATCHES (3) events."""
        # Only 2 events — below the minimum threshold
        events = [self._make_failure_event(task_id=i, agent="writer") for i in range(2)]

        proposals = high_error_rate_detector(events)

        writer_proposals = [p for p in proposals if p.target_agent == "writer"]
        assert writer_proposals == []


# ---------------------------------------------------------------------------
# AC7: Return type — dispatch_entry always returns bool on failure paths
# ---------------------------------------------------------------------------


class TestFromAC_DispatchReturnType:  # noqa: N801
    """AC7: dispatch_entry return type (bool) is unchanged — only loop.py is modified."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_entry_failure_path_returns_false_and_emits_event(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
        acp_error: AcpClientError,
    ) -> None:
        """dispatch_entry must return False AND emit CompletionEvent on new_session failure.

        Verifies the full AC7 contract: return type unchanged (bool) while new
        failure-path emission (AC1) is also present.
        """
        mock_client.new_session = AsyncMock(side_effect=acp_error)

        result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        # AC7: return type unchanged
        assert isinstance(result, bool)
        assert result is False
        # AC1: failure-path emission — this is the new behavior that makes test fail
        mock_audit_log.log_completion.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_dispatch_entry_returns_true_on_success_path_still_works(
        self,
        entry: DispatchEntry,
        mock_client: MagicMock,
        mock_audit_log: MagicMock,
    ) -> None:
        """Success path must still return True (no regression from failure-path additions)."""
        result = await dispatch_entry(entry, mock_client, audit_log=mock_audit_log)

        assert result is True
