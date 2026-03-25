"""RED-phase tests for daemon LLM usage tracking — #845.

Tests describe the contract for refined AC:

AC1. _run_builder_with_context accepts tracker (UsageTracker|None, default None),
     model (str, default ""), provider (str, default "copilot") kwargs.
     Existing callers (3 positional args) are unaffected by defaults.

AC2. After awaiting builder result in the normal (kwargs-accepted) code path,
     record_agent_usage is called with tracker, result, model, provider,
     session_id="background:builder_dispatch", operation="builder_dispatch".

AC3. After awaiting builder result in the TypeError-fallback code path,
     the same record_agent_usage call is made with identical arguments.

AC4. poll_tick accepts tracker, model, provider params and threads them
     to both the retry-dispatch and fresh-dispatch _run_builder_with_context
     call sites.

AC5. poll_loop accepts tracker (default None) and provider (default "copilot")
     and threads them plus settings.chat_model to poll_tick as model=.

AC6. run_daemon passes agent.tracker, settings.provider, and settings.chat_model
     to poll_loop at the existing autonomous-mode call site.

All tests MUST FAIL until the feature is implemented in owlbear.daemon.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.daemon import (
    OrchestratorState,
    RetryEntry,
    _run_builder_with_context,
    poll_loop,
    poll_tick,
    run_daemon,
)
from owlbear.memory.usage import UsageTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_result() -> MagicMock:
    """Build a mock PydanticAI RunResult with plausible usage data."""
    result = MagicMock()
    usage = MagicMock()
    usage.requests = 1
    usage.input_tokens = 100
    usage.output_tokens = 50
    usage.cache_read_tokens = 0
    usage.cache_write_tokens = 0
    usage.tool_calls = 0
    result.usage.return_value = usage
    return result


def _make_builder_mock(*, raises_unexpected_kwarg: bool = False) -> MagicMock:
    """Return a builder mock whose .run() returns a fresh coroutine each call.

    When *raises_unexpected_kwarg* is True, the first call raises
    TypeError("unexpected keyword argument 'instructions'") and the second
    call (prompt-only fallback) succeeds.
    """
    mock_result = _make_mock_result()

    async def _coro() -> MagicMock:
        return mock_result

    if not raises_unexpected_kwarg:

        def _run(*args: object, **kwargs: object) -> object:  # noqa: ARG001
            return _coro()

    else:
        _calls: list[int] = [0]
        _err_msg = "unexpected keyword argument 'instructions'"

        def _run(*args: object, **kwargs: object) -> object:  # noqa: ARG001
            _calls[0] += 1
            if len(kwargs) > 0:
                raise TypeError(_err_msg)
def _make_kanban_show_json(
    task_id: str,
    title: str = "Test task",
    body: str = "AC line 1",
) -> str:
    return json.dumps({"id": task_id, "title": title, "status": "todo", "body": body})


# ---------------------------------------------------------------------------
# AC1: _run_builder_with_context — new optional params (signature)
# ---------------------------------------------------------------------------


class TestFromAC_RunBuilderWithContextSignature:
    """_run_builder_with_context must accept tracker, model, provider kwargs
    which all default to None/"" /"copilot" so existing callers are unaffected."""

    @pytest.mark.asyncio
    async def test_accepts_tracker_none_kwarg(self) -> None:
        """tracker=None can be passed without TypeError."""
        builder = _make_builder_mock()
        result = _run_builder_with_context(builder, "prompt", {}, tracker=None)
        await result

    @pytest.mark.asyncio
    async def test_accepts_tracker_model_provider_kwargs(self) -> None:
        """tracker, model, provider kwargs accepted together without TypeError."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)
        result = _run_builder_with_context(
            builder, "prompt", {}, tracker=tracker, model="gpt-4o", provider="copilot"
        )
        await result

    @pytest.mark.asyncio
    async def test_default_provider_is_copilot(self) -> None:
        """When only tracker and model provided, provider defaults silently."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)
        result = _run_builder_with_context(
            builder, "prompt", {}, tracker=tracker, model="gpt-4o"
        )
        await result  # must not raise

    @pytest.mark.asyncio
    async def test_default_model_is_empty_string(self) -> None:
        """When only tracker and provider provided, model defaults silently."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)
        result = _run_builder_with_context(
            builder, "prompt", {}, tracker=tracker, provider="copilot"
        )
        await result  # must not raise


# ---------------------------------------------------------------------------
# AC2: record_agent_usage called in normal code path
# ---------------------------------------------------------------------------


class TestFromAC_RunBuilderWithContextUsageNormalPath:
    """After awaiting the normal (kwargs-accepted) code path,
    record_agent_usage is called with the correct arguments."""

    @pytest.mark.asyncio
    async def test_record_called_with_tracker(self) -> None:
        """record_agent_usage receives the populated tracker mock."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=tracker, model="gpt-4o", provider="copilot"
            )
            mock_record.assert_called_once()
            assert mock_record.call_args.kwargs["tracker"] is tracker

    @pytest.mark.asyncio
    async def test_record_called_with_correct_model(self) -> None:
        """record_agent_usage receives model='gpt-4o'."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=tracker, model="gpt-4o", provider="copilot"
            )
            assert mock_record.call_args.kwargs["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_record_called_with_correct_provider(self) -> None:
        """record_agent_usage receives provider='copilot'."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=tracker, model="gpt-4o", provider="copilot"
            )
            assert mock_record.call_args.kwargs["provider"] == "copilot"

    @pytest.mark.asyncio
    async def test_session_id_is_background_builder_dispatch(self) -> None:
        """record_agent_usage receives session_id='background:builder_dispatch'."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=tracker, model="", provider="copilot"
            )
            assert mock_record.call_args.kwargs["session_id"] == "background:builder_dispatch"

    @pytest.mark.asyncio
    async def test_operation_is_builder_dispatch(self) -> None:
        """record_agent_usage receives operation='builder_dispatch'."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=tracker, model="", provider="copilot"
            )
            assert mock_record.call_args.kwargs["operation"] == "builder_dispatch"

    @pytest.mark.asyncio
    async def test_result_passed_to_record(self) -> None:
        """record_agent_usage receives the builder's return value as result=."""
        mock_result = _make_mock_result()

        async def _coro() -> MagicMock:
            return mock_result

        builder = MagicMock()
        builder.run = MagicMock(side_effect=lambda *a, **kw: _coro())  # noqa: ARG005
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=tracker, model="", provider="copilot"
            )
            assert mock_record.call_args.kwargs["result"] is mock_result

    @pytest.mark.asyncio
    async def test_no_record_when_tracker_is_none(self) -> None:
        """When tracker=None, record_agent_usage is not called (no-op path)."""
        builder = _make_builder_mock()

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=None, model="gpt-4o", provider="copilot"
            )
            mock_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_called_once_not_multiple_times(self) -> None:
        """record_agent_usage called exactly once per invocation."""
        builder = _make_builder_mock()
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {}, tracker=tracker, model="", provider="copilot"
            )
            assert mock_record.call_count == 1


# ---------------------------------------------------------------------------
# AC3: record_agent_usage called in TypeError-fallback code path
# ---------------------------------------------------------------------------


class TestFromAC_RunBuilderWithContextUsageFallbackPath:
    """After awaiting the TypeError-fallback (prompt-only) code path,
    the same record_agent_usage call is made with identical arguments."""

    @pytest.mark.asyncio
    async def test_record_called_in_fallback_path(self) -> None:
        """record_agent_usage is called even when kwargs are rejected."""
        builder = _make_builder_mock(raises_unexpected_kwarg=True)
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {"instructions": "ctx"}, tracker=tracker,
                model="gpt-4o", provider="copilot",
            )
            mock_record.assert_called_once()
            assert mock_record.call_args.kwargs["tracker"] is tracker

    @pytest.mark.asyncio
    async def test_fallback_path_session_id_is_background_builder_dispatch(self) -> None:
        """Fallback path: session_id='background:builder_dispatch'."""
        builder = _make_builder_mock(raises_unexpected_kwarg=True)
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {"instructions": "ctx"}, tracker=tracker,
                model="", provider="copilot",
            )
            assert mock_record.call_args.kwargs["session_id"] == "background:builder_dispatch"

    @pytest.mark.asyncio
    async def test_fallback_path_operation_is_builder_dispatch(self) -> None:
        """Fallback path: operation='builder_dispatch'."""
        builder = _make_builder_mock(raises_unexpected_kwarg=True)
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {"instructions": "ctx"}, tracker=tracker,
                model="", provider="copilot",
            )
            assert mock_record.call_args.kwargs["operation"] == "builder_dispatch"

    @pytest.mark.asyncio
    async def test_fallback_path_result_is_from_fallback_run(self) -> None:
        """Fallback path: record receives the prompt-only run's result."""
        mock_result = _make_mock_result()

        async def _coro() -> MagicMock:
            return mock_result

        call_count = [0]

        def _run(*args: object, **kwargs: object) -> object:  # noqa: ARG001
            _err = "unexpected keyword argument 'instructions'"
            call_count[0] += 1
            if len(kwargs) > 0:
                raise TypeError(_err)
            return _coro()

        builder = MagicMock()
        builder.run = MagicMock(side_effect=_run)
        tracker = MagicMock(spec=UsageTracker)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {"instructions": "ctx"}, tracker=tracker,
                model="", provider="copilot",
            )
            assert mock_record.call_args.kwargs["result"] is mock_result

    @pytest.mark.asyncio
    async def test_fallback_path_no_record_when_tracker_none(self) -> None:
        """Fallback path: tracker=None → record_agent_usage is not called."""
        builder = _make_builder_mock(raises_unexpected_kwarg=True)

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await _run_builder_with_context(
                builder, "prompt", {"instructions": "ctx"}, tracker=None,
                model="gpt-4o", provider="copilot",
            )
            mock_record.assert_not_called()


# ---------------------------------------------------------------------------
# AC4: poll_tick accepts and threads tracker/model/provider
# ---------------------------------------------------------------------------


class TestFromAC_PollTickUsageParams:
    """poll_tick must accept tracker, model, and provider params and thread
    them to both the retry-dispatch and fresh-dispatch _run_builder_with_context
    call sites."""

    @pytest.mark.asyncio
    async def test_poll_tick_accepts_tracker_kwarg(self) -> None:
        """poll_tick signature accepts tracker= without TypeError."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_kanban.kanban_list.return_value = json.dumps([])
        tracker = MagicMock(spec=UsageTracker)

        # Will raise TypeError if tracker not in signature
        await poll_tick(
            state=state,
            kanban=mock_kanban,
            agent_registry=mock_registry,
            max_concurrent=3,
            shutdown_event=asyncio.Event(),
            tracker=tracker,
        )

    @pytest.mark.asyncio
    async def test_poll_tick_accepts_model_kwarg(self) -> None:
        """poll_tick signature accepts model= without TypeError."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_kanban.kanban_list.return_value = json.dumps([])

        await poll_tick(
            state=state,
            kanban=mock_kanban,
            agent_registry=mock_registry,
            max_concurrent=3,
            shutdown_event=asyncio.Event(),
            model="gpt-4o",
        )

    @pytest.mark.asyncio
    async def test_poll_tick_accepts_provider_kwarg(self) -> None:
        """poll_tick signature accepts provider= without TypeError."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_kanban.kanban_list.return_value = json.dumps([])

        await poll_tick(
            state=state,
            kanban=mock_kanban,
            agent_registry=mock_registry,
            max_concurrent=3,
            shutdown_event=asyncio.Event(),
            provider="copilot",
        )

    @pytest.mark.asyncio
    async def test_fresh_dispatch_records_usage_with_tracker(self) -> None:
        """In the fresh-dispatch branch, tracker is threaded to _run_builder_with_context
        so record_agent_usage is eventually called with that tracker."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        tracker = MagicMock(spec=UsageTracker)

        todo_task = {
            "id": "T845A", "title": "Fresh task", "status": "todo", "priority": "important"
        }
        mock_kanban.kanban_list.return_value = json.dumps([todo_task])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("T845A", "Fresh task")

        mock_builder = _make_builder_mock()
        mock_registry.get.return_value = mock_builder

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                tracker=tracker,
                model="gpt-4o",
                provider="copilot",
            )
            # Drain the spawned asyncio task so record_agent_usage executes
            await asyncio.sleep(0)

        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs["tracker"] is tracker

    @pytest.mark.asyncio
    async def test_retry_dispatch_records_usage_with_tracker(self) -> None:
        """In the retry-dispatch branch, tracker is threaded to _run_builder_with_context
        so record_agent_usage is eventually called with that tracker."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        tracker = MagicMock(spec=UsageTracker)

        state.retries["T845B"] = RetryEntry(
            task_id="T845B",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
            last_error="prior failure",
        )
        state.claimed.add("T845B")
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("T845B")
        mock_kanban.kanban_list.return_value = json.dumps([])

        mock_builder = _make_builder_mock()
        mock_registry.get.return_value = mock_builder

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                tracker=tracker,
                model="gpt-4o",
                provider="copilot",
            )
            await asyncio.sleep(0)

        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs["tracker"] is tracker

    @pytest.mark.asyncio
    async def test_fresh_dispatch_threads_model_to_record(self) -> None:
        """poll_tick threads model= to _run_builder_with_context (fresh dispatch)."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        tracker = MagicMock(spec=UsageTracker)

        todo_task = {
            "id": "T845C", "title": "Model threading", "status": "todo", "priority": "important"
        }
        mock_kanban.kanban_list.return_value = json.dumps([todo_task])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("T845C")

        mock_builder = _make_builder_mock()
        mock_registry.get.return_value = mock_builder

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                tracker=tracker,
                model="claude-3.7-sonnet",
                provider="copilot",
            )
            await asyncio.sleep(0)

        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs["model"] == "claude-3.7-sonnet"

    @pytest.mark.asyncio
    async def test_fresh_dispatch_no_record_when_tracker_none(self) -> None:
        """When poll_tick is called with tracker=None explicitly,
        record_agent_usage is not called (no-op)."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_task = {
            "id": "T845D", "title": "No tracker", "status": "todo", "priority": "important"
        }
        mock_kanban.kanban_list.return_value = json.dumps([todo_task])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("T845D")

        mock_builder = _make_builder_mock()
        mock_registry.get.return_value = mock_builder

        with patch("owlbear.memory.usage.record_agent_usage") as mock_record:
            # Pass tracker=None explicitly — fails today (TypeError) since param doesn't exist;
            # after implementation, poll_tick must accept it and produce a no-op.
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                tracker=None,
            )
            await asyncio.sleep(0)

        mock_record.assert_not_called()


# ---------------------------------------------------------------------------
# AC5: poll_loop accepts tracker/provider and threads to poll_tick
# ---------------------------------------------------------------------------


class TestFromAC_PollLoopUsageParams:
    """poll_loop must accept tracker and provider params and thread them,
    together with settings.chat_model as model=, to poll_tick."""

    @pytest.mark.asyncio
    async def test_poll_loop_accepts_tracker_kwarg(self) -> None:
        """poll_loop signature accepts tracker= without TypeError."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()
        settings = MagicMock()
        settings.max_concurrent_tasks = 2
        settings.poll_interval = 0.001
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.chat_model = "gpt-4o"

        tracker = MagicMock(spec=UsageTracker)

        async def _fast_tick(**_kwargs: object) -> None:
            shutdown.set()

        with patch("owlbear.daemon.poll_tick", side_effect=_fast_tick):
            # Must not raise TypeError for tracker kwarg
            await poll_loop(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                settings=settings,
                shutdown_event=shutdown,
                tracker=tracker,
            )

    @pytest.mark.asyncio
    async def test_poll_loop_accepts_provider_kwarg(self) -> None:
        """poll_loop signature accepts provider= without TypeError."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()
        settings = MagicMock()
        settings.max_concurrent_tasks = 2
        settings.poll_interval = 0.001
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.chat_model = "gpt-4o"

        async def _fast_tick(**_kwargs: object) -> None:
            shutdown.set()

        with patch("owlbear.daemon.poll_tick", side_effect=_fast_tick):
            await poll_loop(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                settings=settings,
                shutdown_event=shutdown,
                provider="copilot",
            )

    @pytest.mark.asyncio
    async def test_poll_loop_threads_tracker_to_poll_tick(self) -> None:
        """poll_loop passes tracker= to poll_tick."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()
        settings = MagicMock()
        settings.max_concurrent_tasks = 2
        settings.poll_interval = 0.001
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.chat_model = "gpt-4o"

        tracker = MagicMock(spec=UsageTracker)
        captured_kwargs: list[dict[str, object]] = []

        async def _capture_tick(**kwargs: object) -> None:
            captured_kwargs.append(dict(kwargs))
            shutdown.set()

        with patch("owlbear.daemon.poll_tick", side_effect=_capture_tick):
            await poll_loop(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                settings=settings,
                shutdown_event=shutdown,
                tracker=tracker,
            )

        assert len(captured_kwargs) == 1
        assert captured_kwargs[0].get("tracker") is tracker

    @pytest.mark.asyncio
    async def test_poll_loop_threads_provider_to_poll_tick(self) -> None:
        """poll_loop passes provider= to poll_tick."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()
        settings = MagicMock()
        settings.max_concurrent_tasks = 2
        settings.poll_interval = 0.001
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.chat_model = "gpt-4o"

        captured_kwargs: list[dict[str, object]] = []

        async def _capture_tick(**kwargs: object) -> None:
            captured_kwargs.append(dict(kwargs))
            shutdown.set()

        with patch("owlbear.daemon.poll_tick", side_effect=_capture_tick):
            await poll_loop(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                settings=settings,
                shutdown_event=shutdown,
                provider="openai-org",
            )

        assert len(captured_kwargs) == 1
        assert captured_kwargs[0].get("provider") == "openai-org"

    @pytest.mark.asyncio
    async def test_poll_loop_threads_chat_model_as_model_to_poll_tick(self) -> None:
        """poll_loop passes settings.chat_model as model= to poll_tick."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()
        settings = MagicMock()
        settings.max_concurrent_tasks = 2
        settings.poll_interval = 0.001
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.chat_model = "claude-3.7-sonnet"

        captured_kwargs: list[dict[str, object]] = []

        async def _capture_tick(**kwargs: object) -> None:
            captured_kwargs.append(dict(kwargs))
            shutdown.set()

        with patch("owlbear.daemon.poll_tick", side_effect=_capture_tick):
            await poll_loop(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                settings=settings,
                shutdown_event=shutdown,
            )

        assert len(captured_kwargs) == 1
        assert captured_kwargs[0].get("model") == "claude-3.7-sonnet"

    @pytest.mark.asyncio
    async def test_poll_loop_default_tracker_is_none(self) -> None:
        """When poll_loop is called without tracker=, poll_tick receives tracker=None."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()
        settings = MagicMock()
        settings.max_concurrent_tasks = 2
        settings.poll_interval = 0.001
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.chat_model = "gpt-4o"

        captured_kwargs: list[dict[str, object]] = []

        async def _capture_tick(**kwargs: object) -> None:
            captured_kwargs.append(dict(kwargs))
            shutdown.set()

        with patch("owlbear.daemon.poll_tick", side_effect=_capture_tick):
            await poll_loop(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                settings=settings,
                shutdown_event=shutdown,
                # no tracker
            )

        assert len(captured_kwargs) == 1
        # Use direct key access to fail if poll_loop omits the tracker kwarg entirely.
        # Before implementation poll_loop does not pass tracker= at all, so this raises KeyError.
        assert captured_kwargs[0]["tracker"] is None


# ---------------------------------------------------------------------------
# AC6: run_daemon threads agent.tracker, settings.provider, settings.chat_model
# ---------------------------------------------------------------------------


class TestFromAC_RunDaemonUsageThreading:
    """run_daemon must pass agent.tracker, settings.provider, and
    settings.chat_model to poll_loop at the autonomous-mode call site."""

    @staticmethod
    def _make_mock_agent_with_tracker(tracker: object) -> MagicMock:
        agent = MagicMock()
        agent.tracker = tracker
        agent.hooks = AsyncMock()
        agent.session = MagicMock()
        agent.session.path = Path("/fake/session")
        agent.session.load.return_value = []
        return agent

    @staticmethod
    def _make_autonomous_settings(
        *,
        provider: str = "copilot",
        chat_model: str = "gpt-4o",
    ) -> MagicMock:
        settings = MagicMock()
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.lint_gate_enabled = False
        settings.task_retry_max_attempts = 3
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0
        settings.provider = provider
        settings.chat_model = chat_model
        return settings

    @pytest.mark.asyncio
    async def test_run_daemon_passes_tracker_to_poll_loop(self, tmp_path: Path) -> None:
        """run_daemon passes agent.tracker as tracker= to poll_loop."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        tracker = MagicMock(spec=UsageTracker)
        agent = self._make_mock_agent_with_tracker(tracker)
        settings = self._make_autonomous_settings()

        captured_poll_kwargs: list[dict[str, object]] = []

        async def _fake_poll_loop(*, shutdown_event: asyncio.Event, **kwargs: object) -> None:
            captured_poll_kwargs.append(kwargs)
            shutdown_event.set()

        async def _fake_channel_loop(
            shutdown_event: asyncio.Event,
            *_args: object,
            **_kwargs: object,
        ) -> None:
            await shutdown_event.wait()

        with (
            patch("owlbear.daemon.poll_loop", side_effect=_fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=_fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            await run_daemon(
                channel=MockChannel([None]),
                agent=agent,
                config_dir=tmp_path,
                settings=settings,
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
            )

        assert len(captured_poll_kwargs) == 1
        assert captured_poll_kwargs[0].get("tracker") is tracker

    @pytest.mark.asyncio
    async def test_run_daemon_passes_provider_to_poll_loop(self, tmp_path: Path) -> None:
        """run_daemon passes settings.provider as provider= to poll_loop."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        agent = self._make_mock_agent_with_tracker(None)
        settings = self._make_autonomous_settings(provider="azure-openai")

        captured_poll_kwargs: list[dict[str, object]] = []

        async def _fake_poll_loop(*, shutdown_event: asyncio.Event, **kwargs: object) -> None:
            captured_poll_kwargs.append(kwargs)
            shutdown_event.set()

        async def _fake_channel_loop(
            shutdown_event: asyncio.Event,
            *_args: object,
            **_kwargs: object,
        ) -> None:
            await shutdown_event.wait()

        with (
            patch("owlbear.daemon.poll_loop", side_effect=_fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=_fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            await run_daemon(
                channel=MockChannel([None]),
                agent=agent,
                config_dir=tmp_path,
                settings=settings,
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
            )

        assert len(captured_poll_kwargs) == 1
        assert captured_poll_kwargs[0].get("provider") == "azure-openai"

    @pytest.mark.asyncio
    async def test_run_daemon_passes_provider_and_tracker_to_poll_loop(
        self, tmp_path: Path
    ) -> None:
        """run_daemon passes settings.provider as provider= and agent.tracker
        as tracker= to poll_loop at the autonomous-mode call site.

        Verifies both fields in a single test to confirm run_daemon threads both
        new params together. Either field missing causes a failure.
        """
        from conftest import MockChannel  # type: ignore[import-untyped]

        tracker = MagicMock(spec=UsageTracker)
        agent = self._make_mock_agent_with_tracker(tracker)
        settings = self._make_autonomous_settings(provider="github-copilot", chat_model="gpt-4o")

        captured_poll_kwargs: list[dict[str, object]] = []

        async def _fake_poll_loop(*, shutdown_event: asyncio.Event, **kwargs: object) -> None:
            captured_poll_kwargs.append(kwargs)
            shutdown_event.set()

        async def _fake_channel_loop(
            shutdown_event: asyncio.Event,
            *_args: object,
            **_kwargs: object,
        ) -> None:
            await shutdown_event.wait()

        with (
            patch("owlbear.daemon.poll_loop", side_effect=_fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=_fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            await run_daemon(
                channel=MockChannel([None]),
                agent=agent,
                config_dir=tmp_path,
                settings=settings,
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
            )

        assert len(captured_poll_kwargs) == 1
        # Both must be present — use direct key access to fail if absent.
        assert captured_poll_kwargs[0]["tracker"] is tracker, (
            "run_daemon must pass agent.tracker as tracker= to poll_loop"
        )
        assert captured_poll_kwargs[0]["provider"] == "github-copilot", (
            "run_daemon must pass settings.provider as provider= to poll_loop"
        )

    @pytest.mark.asyncio
    async def test_run_daemon_tracker_none_when_agent_has_no_tracker(
        self, tmp_path: Path
    ) -> None:
        """When agent.tracker is None, run_daemon passes tracker=None to poll_loop."""
        from conftest import MockChannel  # type: ignore[import-untyped]

        agent = self._make_mock_agent_with_tracker(None)
        agent.tracker = None
        settings = self._make_autonomous_settings()

        captured_poll_kwargs: list[dict[str, object]] = []

        async def _fake_poll_loop(*, shutdown_event: asyncio.Event, **kwargs: object) -> None:
            captured_poll_kwargs.append(kwargs)
            shutdown_event.set()

        async def _fake_channel_loop(
            shutdown_event: asyncio.Event,
            *_args: object,
            **_kwargs: object,
        ) -> None:
            await shutdown_event.wait()

        with (
            patch("owlbear.daemon.poll_loop", side_effect=_fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=_fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            await run_daemon(
                channel=MockChannel([None]),
                agent=agent,
                config_dir=tmp_path,
                settings=settings,
                kanban_toolset=AsyncMock(),
                agent_registry=MagicMock(),
            )

        assert len(captured_poll_kwargs) == 1
        # Direct key access: fail if run_daemon omits tracker= kwarg entirely.
        assert captured_poll_kwargs[0]["tracker"] is None, (
            "run_daemon must pass agent.tracker (None) as tracker= to poll_loop"
        )
