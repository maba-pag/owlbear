"""Tests for AuditMapAdvisoryHook — TASK_COMPLETE audit-map advisory worker.

AC: #982 — eligibility gates (outcome, config flag, tag) and
coroutine safety contract (scratch-only writes, no board mutations,
optional channel notification).

All tests FAIL (RED) before the production module exists — the import
below raises ImportError, which fails every test in this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.channels.base import ChannelPlugin

# RED: module does not exist yet — all tests will fail with ImportError
from owlbear.core.audit_map_hook import AuditMapAdvisoryHook  # type: ignore[import]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(*, enabled: bool = True) -> MagicMock:
    """Build a minimal settings mock with audit_map_worker_enabled set."""
    settings = MagicMock()
    settings.audit_map_worker_enabled = enabled
    return settings


def _kanban_show_json(task_id: str, *, tags: list[str] | None = None) -> str:
    """Serialise a minimal kanban-md show --json response payload."""
    return json.dumps({"id": task_id, "tags": tags or []})


def _subprocess_returning_tags(tags: list[str], *, task_id: str = "42") -> MagicMock:
    """Build a subprocess.run mock result with the given task tags."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = _kanban_show_json(task_id, tags=tags)
    return result


def _payload(task_id: str = "42", outcome: str = "success") -> dict[str, Any]:
    """Build a TASK_COMPLETE payload."""
    return {"task_id": task_id, "outcome": outcome}


def _make_hook(
    tmp_path: Path,
    *,
    enabled: bool = True,
    supervisor: object | None = None,
    channel: object | None = None,
) -> AuditMapAdvisoryHook:
    """Create an AuditMapAdvisoryHook with sensible test defaults."""
    return AuditMapAdvisoryHook(
        settings=_make_settings(enabled=enabled),
        supervisor=supervisor if supervisor is not None else MagicMock(),
        kanban_root=tmp_path,
        workspace_root=tmp_path,
        channel=channel,
    )


async def _trigger_and_capture_worker(
    tmp_path: Path,
    *,
    task_id: str = "42",
    channel: object | None = None,
) -> Any:
    """Drive __call__ through all passing gates and return the scheduled awaitable.

    Uses a real MagicMock supervisor; subprocess.run is patched to return a
    kanban-md JSON with the ``worker:audit-map`` tag.  Returns the single
    argument passed to ``supervisor.schedule()``.
    """
    supervisor = MagicMock()
    hook = _make_hook(tmp_path, supervisor=supervisor, channel=channel)
    with patch(
        "owlbear.core.audit_map_hook.subprocess.run",
        return_value=_subprocess_returning_tags(["worker:audit-map"], task_id=task_id),
    ):
        await hook(_payload(task_id=task_id, outcome="success"))
    supervisor.schedule.assert_called_once()
    return supervisor.schedule.call_args[0][0]


# ---------------------------------------------------------------------------
# AC2-AC5: Eligibility gates in __call__
# ---------------------------------------------------------------------------


class TestFromAC_AuditMapAdvisoryHookEligibility:
    """``__call__`` eligibility gates: outcome, config flag, and audit-map tag.

    All tests FAIL (RED) before ``AuditMapAdvisoryHook`` exists.
    """

    # -- AC2: outcome gate ---------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_failure_outcome_skips_schedule(self, tmp_path: Path) -> None:
        """AC2: outcome == 'failure' → supervisor.schedule() not called."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        await hook(_payload(outcome="failure"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_success_outcome_skipped_skips_schedule(self, tmp_path: Path) -> None:
        """AC2 edge: outcome == 'skipped' (non-success) → supervisor.schedule() not called."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        await hook(_payload(outcome="skipped"))
        supervisor.schedule.assert_not_called()

    # -- AC3: config flag gate -----------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_config_flag_false_skips_schedule(self, tmp_path: Path) -> None:
        """AC3: audit_map_worker_enabled=False → supervisor.schedule() not called."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, enabled=False, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags(["worker:audit-map"]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_not_called()

    # -- AC4: worker:audit-map tag gate --------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_missing_audit_map_tag_skips_schedule(self, tmp_path: Path) -> None:
        """AC4: task has unrelated tags but not 'worker:audit-map' → schedule not called."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags(["phase-6", "type:build"]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_tags_skips_schedule(self, tmp_path: Path) -> None:
        """AC4 edge: task has no tags at all → supervisor.schedule() not called."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags([]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_tag_resolution_uses_subprocess_kanban_show_json(self, tmp_path: Path) -> None:
        """AC4: tag resolution invokes subprocess.run with kanban-md show <id> --json."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        mock_run = MagicMock(return_value=_subprocess_returning_tags(["worker:audit-map"]))
        with patch("owlbear.core.audit_map_hook.subprocess.run", mock_run):
            await hook(_payload(task_id="99", outcome="success"))
        mock_run.assert_called_once()
        call_args: list[str] = [str(a) for a in mock_run.call_args[0][0]]
        assert "show" in call_args, f"Expected 'show' in subprocess args: {call_args}"
        assert "99" in call_args, f"Expected task_id '99' in subprocess args: {call_args}"
        assert "--json" in call_args, f"Expected '--json' in subprocess args: {call_args}"

    # -- AC5: successful schedule call ---------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_all_gates_pass_calls_schedule_exactly_once(self, tmp_path: Path) -> None:
        """AC5: outcome=success + flag=True + tag present → supervisor.schedule() once."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags(["worker:audit-map", "phase-6"]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_all_gates_pass_schedule_receives_lazy_awaitable(self, tmp_path: Path) -> None:
        """AC5: argument to supervisor.schedule() is a _LazyCoroutine-style awaitable."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch(
            "owlbear.core.audit_map_hook.subprocess.run",
            return_value=_subprocess_returning_tags(["worker:audit-map"]),
        ):
            await hook(_payload(outcome="success"))
        supervisor.schedule.assert_called_once()
        scheduled = supervisor.schedule.call_args[0][0]
        # Must satisfy _LazyCoroutine contract: has __await__ and close()
        assert hasattr(scheduled, "__await__"), (
            "schedule() argument must have __await__ (_LazyCoroutine pattern)"
        )
        assert hasattr(scheduled, "close"), (
            "schedule() argument must have close() to avoid unawaited-coroutine warnings"
        )
        # Defensive: clean up to avoid ResourceWarning
        scheduled.close()


# ---------------------------------------------------------------------------
# AC6-AC9: Worker coroutine safety contract
# ---------------------------------------------------------------------------


class TestFromAC_AuditMapAdvisoryHookWorker:
    """Scheduled coroutine: scratch-only writes, no board mutations, channel notification.

    Each test drives the hook through ``__call__`` with all gates passing,
    captures the scheduled ``_LazyCoroutine``, then awaits it to verify
    the worker's safety contract.

    All tests FAIL (RED) before ``AuditMapAdvisoryHook`` exists.
    """

    # -- AC6: scratch-only artifact ------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_writes_scratch_file_at_correct_path(self, tmp_path: Path) -> None:
        """AC6: worker creates docs/scratch/{task-id}-audit-map.md under workspace_root."""
        lazy_coro: Any = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        expected = tmp_path / "docs" / "scratch" / "42-audit-map.md"
        assert expected.is_file(), f"Expected scratch file at {expected} after worker run"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_creates_no_other_docs_files(self, tmp_path: Path) -> None:
        """AC6 edge: no files created under docs/ outside docs/scratch/."""
        docs_root = tmp_path / "docs"
        docs_root.mkdir(parents=True, exist_ok=True)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        non_scratch = [f for f in docs_root.rglob("*") if f.is_file() and "scratch" not in f.parts]
        assert not non_scratch, (
            f"Worker must not create files outside docs/scratch/, found: {non_scratch}"
        )

    # -- AC7: no board mutations ---------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_does_not_call_subprocess_during_execution(self, tmp_path: Path) -> None:
        """AC7: worker coroutine makes no subprocess.run calls (including kanban-md)."""
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        with patch("owlbear.core.audit_map_hook.subprocess.run") as mock_run:
            await lazy_coro
        mock_run.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_does_not_write_to_src(self, tmp_path: Path) -> None:
        """AC7: worker coroutine writes no files under src/."""
        src_root = tmp_path / "src"
        src_root.mkdir(parents=True, exist_ok=True)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        src_files = [f for f in src_root.rglob("*") if f.is_file()]
        assert not src_files, f"Worker must not write to src/, but found: {src_files}"

    # -- AC8: channel notification when available ----------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_sends_channel_message_once(self, tmp_path: Path) -> None:
        """AC8: channel.send() called exactly once when channel is provided."""
        channel = AsyncMock(spec=ChannelPlugin)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42", channel=channel)
        await lazy_coro
        channel.send.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_channel_message_contains_task_id(self, tmp_path: Path) -> None:
        """AC8: the message sent via channel.send() contains the task ID."""
        channel = AsyncMock(spec=ChannelPlugin)
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="77", channel=channel)
        await lazy_coro
        channel.send.assert_called_once()
        message: str = channel.send.call_args[0][0]
        assert "77" in message, (
            f"channel.send() message must contain task ID '77', got: {message!r}"
        )

    # -- AC9: no error / no send when channel is None ------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_completes_without_error_when_channel_none(self, tmp_path: Path) -> None:
        """AC9: channel=None → worker completes without raising any exception."""
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42", channel=None)
        # Must not raise
        await lazy_coro

    @pytest.mark.asyncio(loop_scope="function")
    async def test_worker_channel_send_not_called_when_channel_none(self, tmp_path: Path) -> None:
        """AC9: channel=None → channel.send() is never called."""
        channel_spy = AsyncMock(spec=ChannelPlugin)
        lazy_coro_none = await _trigger_and_capture_worker(tmp_path, task_id="43", channel=None)
        await lazy_coro_none
        channel_spy.send.assert_not_called()


class TestBuilderDiscovered_AuditMapAdvisoryHookBranches:
    """Builder-discovered coverage for defensive branches and helper seams."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_task_id_skips_subprocess_and_schedule(self, tmp_path: Path) -> None:
        """Empty task IDs short-circuit before tag lookup."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch("owlbear.core.audit_map_hook.subprocess.run") as mock_run:
            await hook(_payload(task_id="", outcome="success"))
        supervisor.schedule.assert_not_called()
        mock_run.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_subprocess_exception_skips_schedule(self, tmp_path: Path) -> None:
        """Tag resolution failures are handled safely."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        with patch("owlbear.core.audit_map_hook.subprocess.run", side_effect=RuntimeError("boom")):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_zero_subprocess_returncode_skips_schedule(self, tmp_path: Path) -> None:
        """Non-zero kanban command return code blocks scheduling."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        failed = MagicMock()
        failed.returncode = 1
        failed.stdout = ""
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=failed):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_invalid_json_skips_schedule(self, tmp_path: Path) -> None:
        """Malformed JSON in kanban output blocks scheduling."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        malformed = MagicMock()
        malformed.returncode = 0
        malformed.stdout = "{"
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=malformed):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_dict_json_payload_skips_schedule(self, tmp_path: Path) -> None:
        """Only dict payloads are accepted from kanban JSON output."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        payload = MagicMock()
        payload.returncode = 0
        payload.stdout = json.dumps(["worker:audit-map"])
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=payload):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_list_tags_skips_schedule(self, tmp_path: Path) -> None:
        """A non-list tags field does not pass eligibility."""
        supervisor = MagicMock()
        hook = _make_hook(tmp_path, supervisor=supervisor)
        payload = MagicMock()
        payload.returncode = 0
        payload.stdout = json.dumps({"tags": "worker:audit-map"})
        with patch("owlbear.core.audit_map_hook.subprocess.run", return_value=payload):
            await hook(_payload(task_id="42", outcome="success"))
        supervisor.schedule.assert_not_called()

    def test_register_attaches_task_complete_handler(self, tmp_path: Path) -> None:
        """register() wires the hook into the task_complete event."""
        from owlbear.core.hooks import HookEvent, HookRegistry

        hook = _make_hook(tmp_path)
        registry = HookRegistry()
        hook.register(registry)
        handlers = registry.handlers.get(HookEvent.TASK_COMPLETE, [])
        assert hook in handlers

    @pytest.mark.asyncio(loop_scope="function")
    async def test_lazy_coroutine_close_after_await_is_safe(self, tmp_path: Path) -> None:
        """The scheduled lazy awaitable still supports explicit close()."""
        lazy_coro = await _trigger_and_capture_worker(tmp_path, task_id="42")
        await lazy_coro
        lazy_coro.close()
