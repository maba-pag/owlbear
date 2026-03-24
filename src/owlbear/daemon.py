"""Daemon lifecycle — PID file, logging, and async run loop.

Provides the building blocks for ``bearclaw run``:

- :class:`PidFile` — context manager that writes/removes ``owlbear.pid``
- :func:`setup_logging` — ``RotatingFileHandler`` + stderr ``StreamHandler``
- :func:`run_daemon` — async daemon loop; runs ``channel_loop`` alone or
  both ``channel_loop`` + ``poll_loop`` (autonomous mode) in a ``TaskGroup``
- :class:`OrchestratorState` / :class:`RunningTask` — in-memory state for
  the poll-dispatch-reconcile loop
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import logging
import logging.handlers
import os
import random
import signal
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Self

import httpx
from pydantic_ai import Agent

try:
    import logfire
except ImportError:  # logfire is an optional dependency
    logfire = None  # type: ignore[assignment]
from rich.console import Console
from rich.logging import RichHandler

from owlbear.core.delegation import DispatchContext, format_dispatch_context
from owlbear.core.deps import OwlBearDeps
from owlbear.core.errors import (
    ErrorCategory,
    classify_error,
    error_to_user_message,
)
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.lint_gate import LintGateError, run_lint_gate
from owlbear.process import is_process_alive
from owlbear.providers.copilot import create_copilot_client

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings
    from owlbear.core.agent import OwlBearAgent
    from owlbear.core.agent_registry import AgentRegistry
    from owlbear.memory.error_journal import ErrorJournal
    from owlbear.memory.wip import WipStore
    from owlbear.tools.kanban import KanbanToolset

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3

# WIP injection prefix (Quoorum-pattern)
CONTINUE_FORWARD_PREFIX = (
    "## CONTINUE FORWARD\n\n"
    "You attempted this task in a previous cycle. "
    "Here is your work-in-progress summary:\n\n"
)

_WIP_MAX_CHARS = 500

# Transient retry constants — apply only to model-level transients (#512)
_TRANSIENT_MAX_RETRIES = 3
_TRANSIENT_BACKOFF_BASE = 1.0  # seconds
_TRANSIENT_BACKOFF_MAX = 30.0  # seconds
_JITTER_FACTOR = 0.5

# Priority sort order (highest first)
_PRIORITY_ORDER: dict[str, int] = {
    "critical": 0,
    "needed": 1,
    "important": 2,
    "nice-to-have": 3,
    "someday": 4,
}


# ---------------------------------------------------------------------------
# Orchestrator state
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class RunningTask:
    """Tracks a single dispatched autonomous task."""

    task_id: str
    asyncio_task: asyncio.Task[object]
    started_at: datetime = dataclasses.field(default_factory=lambda: datetime.now(UTC))


@dataclasses.dataclass
class RetryEntry:
    """Tracks a pending task-level retry with exponential backoff."""

    task_id: str
    next_due: datetime
    attempt: int = 1
    last_error: str = ""


@dataclasses.dataclass
class OrchestratorState:
    """Mutable state for the poll-dispatch-reconcile loop."""

    running: dict[str, RunningTask] = dataclasses.field(default_factory=dict)
    claimed: set[str] = dataclasses.field(default_factory=set)
    retries: dict[str, RetryEntry] = dataclasses.field(default_factory=dict)
    last_attempted_at: dict[str, datetime] = dataclasses.field(default_factory=dict)


# ---------------------------------------------------------------------------
# PidFile context manager
# ---------------------------------------------------------------------------


class PidFile:
    """Context manager that writes the current PID on enter and removes it on exit.

    On enter, if the PID file already exists:

    - **Stale** (process dead): the file is removed and re-created.
    - **Alive** (process running): :exc:`RuntimeError` is raised.

    Parameters
    ----------
    path:
        Absolute path to the PID file (e.g. ``config_dir / "owlbear.pid"``).
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def __enter__(self) -> Self:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if self._path.exists():
            existing_pid = int(self._path.read_text().strip())
            if is_process_alive(existing_pid):
                msg = (
                    f"OwlBear daemon already running (PID {existing_pid}). "
                    "Stop it first with `bearclaw stop`."
                )
                raise RuntimeError(msg)
            # Stale PID — remove and proceed
            logger.info("Removing stale PID file (PID %d no longer alive)", existing_pid)
            self._path.unlink()

        self._path.write_text(str(os.getpid()))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self._path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def setup_logging(log_file: Path) -> logging.Logger:
    """Configure the root logger with a rotating file handler and rich stderr output.

    The stderr handler uses :class:`rich.logging.RichHandler` for coloured,
    human-friendly console output.  The file handler remains a plain
    :class:`~logging.handlers.RotatingFileHandler` (no ANSI escapes).
    :func:`rich.traceback.install` is called so unhandled exceptions render
    rich tracebacks on stderr.

    Parameters
    ----------
    log_file:
        Path to the log file (e.g. ``config_dir / "owlbear.log"``).

    Returns:
    -------
    logging.Logger
        The root logger, configured with both handlers.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)

    console = Console(stderr=True)
    stream_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        markup=False,
        show_path=False,
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    return root


# ---------------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------------


def _make_signal_handler(
    loop: asyncio.AbstractEventLoop,
    shutdown_event: asyncio.Event,
) -> Callable[[int, FrameType | None], None]:
    """Return a signal handler that sets *shutdown_event* via the event loop.

    Uses :meth:`loop.call_soon_threadsafe` so the event is set from the
    correct thread.  A ``RuntimeError`` is caught silently — this can
    happen when the loop is already closed during a shutdown race.
    """

    def _handler(signum: int, frame: FrameType | None) -> None:  # noqa: ARG001
        logger.info("Received signal %s — shutting down", signum)
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(shutdown_event.set)

    return _handler


def configure_otel(otel_endpoint: str) -> None:
    """Configure the Logfire SDK to export spans to an OTLP endpoint.

    Sets ``OTEL_EXPORTER_OTLP_ENDPOINT`` in the process environment and
    calls :func:`logfire.configure` with ``send_to_logfire=False``.

    Parameters
    ----------
    otel_endpoint:
        The OTLP endpoint URL (e.g. ``http://localhost:4318``).

    Raises:
    ------
    RuntimeError
        When ``logfire`` is not installed.
    """
    if logfire is None:
        msg = "logfire is required for OTel configuration but is not installed"
        raise RuntimeError(msg)
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otel_endpoint
    logfire.configure(send_to_logfire=False, additional_span_processors=[])
    logger.info("OTel configured — exporting to %s", otel_endpoint)


async def _log_to_journal(  # noqa: PLR0913
    journal: ErrorJournal | None,
    *,
    error_type: str,
    exc: Exception,
    action_taken: str,
    attempt: int,
    resolved: bool,
    agent: OwlBearAgent,
) -> None:
    """Best-effort write to the error journal (never raises)."""
    if journal is None:
        return
    try:
        await asyncio.to_thread(
            journal.log,
            ts=datetime.now(UTC).isoformat(),
            error_type=error_type,
            tool_name="agent.turn",
            exc_message=str(exc),
            action_taken=action_taken,
            attempt=attempt,
            resolved=resolved,
            session_id=str(agent.session.path),
        )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to write error journal entry", exc_info=True)


async def _recover_from_error(  # noqa: PLR0913, PLR0912, PLR0915, C901
    exc: Exception,
    message: str,
    *,
    agent: OwlBearAgent,
    channel: ChannelPlugin,
    settings: OwlBearSettings | None,
    error_journal: ErrorJournal | None = None,
) -> None:
    """Apply classified recovery strategy for a failed ``agent.turn()`` call.

    - **TRANSIENT**: exponential backoff with jitter, up to 3 retries.
    - **AUTH**: token refresh via :func:`create_copilot_client`, retry once.
    - **PERMANENT / TOOL_SEMANTIC / AUTH without settings**: log and send error.
    """
    category = classify_error(exc)

    if category is ErrorCategory.TRANSIENT:
        # Tool-level transients are already retried by HookedToolset (#512).
        # Only model-level transients (HTTPStatusError 429/502/503/504) get
        # daemon retry.  Attribute check covers explicit marking; isinstance
        # check catches tool-originated network errors (ConnectError, etc.).
        if getattr(exc, "_tool_retries_exhausted", False) or not isinstance(
            exc, httpx.HTTPStatusError
        ):
            await _log_to_journal(
                error_journal,
                error_type=category.value,
                exc=exc,
                action_taken="tool_retries_exhausted",
                attempt=1,
                resolved=False,
                agent=agent,
            )
            logger.error(
                "Tool-level transient retries exhausted — not retrying at daemon level: %s",
                exc,
            )
            try:
                await channel.send(f"Error: {error_to_user_message(exc)}")
            except Exception:
                logger.exception("Failed to send error to channel (original: %s)", exc)
            return

        last_exc: Exception = exc
        for attempt in range(1, _TRANSIENT_MAX_RETRIES + 1):
            delay = min(
                _TRANSIENT_BACKOFF_BASE * (2 ** (attempt - 1)),
                _TRANSIENT_BACKOFF_MAX,
            )
            jitter = random.uniform(0, delay * _JITTER_FACTOR)  # noqa: S311
            await asyncio.sleep(delay + jitter)
            try:
                response = await agent.turn(message)
                await channel.send(response)
            except Exception as retry_exc:  # noqa: BLE001
                last_exc = retry_exc
                logger.warning(
                    "Transient retry %d/%d failed: %s",
                    attempt,
                    _TRANSIENT_MAX_RETRIES,
                    retry_exc,
                )
            else:
                await _log_to_journal(
                    error_journal,
                    error_type=category.value,
                    exc=exc,
                    action_taken="transient_retry",
                    attempt=attempt,
                    resolved=True,
                    agent=agent,
                )
                return
        await _log_to_journal(
            error_journal,
            error_type=category.value,
            exc=last_exc,
            action_taken="transient_retries_exhausted",
            attempt=_TRANSIENT_MAX_RETRIES,
            resolved=False,
            agent=agent,
        )
        logger.exception("Transient retries exhausted", exc_info=last_exc)
        try:
            await channel.send(f"Error: {error_to_user_message(last_exc)}")
        except Exception:
            logger.exception("Failed to send error to channel (original: %s)", last_exc)

    elif category is ErrorCategory.AUTH and settings is not None:
        # Close old OpenAI client before replacement (#514)
        old_client = getattr(agent, "_openai_client", None)
        if old_client is not None:
            await old_client.close()
        try:
            from pydantic_ai.models.openai import OpenAIChatModel  # noqa: PLC0415
            from pydantic_ai.providers.openai import OpenAIProvider  # noqa: PLC0415

            new_client = await create_copilot_client(settings)
            provider = OpenAIProvider(openai_client=new_client)
            new_model = OpenAIChatModel(settings.chat_model, provider=provider)
            agent.update_model(new_model)
            agent._openai_client = new_client  # noqa: SLF001
            response = await agent.turn(message)
            await channel.send(response)
            await _log_to_journal(
                error_journal,
                error_type=category.value,
                exc=exc,
                action_taken="auth_refresh",
                attempt=1,
                resolved=True,
                agent=agent,
            )
        except Exception as retry_exc:
            await _log_to_journal(
                error_journal,
                error_type=category.value,
                exc=retry_exc,
                action_taken="auth_refresh_failed",
                attempt=1,
                resolved=False,
                agent=agent,
            )
            logger.exception("Token refresh/retry failed")
            try:
                await channel.send(f"Error: {error_to_user_message(retry_exc)}")
            except Exception:
                logger.exception("Failed to send error to channel (original: %s)", retry_exc)  # noqa: TRY401

    else:  # PERMANENT, TOOL_SEMANTIC, or AUTH without settings
        await _log_to_journal(
            error_journal,
            error_type=category.value,
            exc=exc,
            action_taken="permanent",
            attempt=1,
            resolved=False,
            agent=agent,
        )
        logger.exception("Error processing message")
        try:
            await channel.send(f"Error: {error_to_user_message(exc)}")
        except Exception:
            logger.exception("Failed to send error to channel (original: %s)", exc)


async def channel_loop(  # noqa: PLR0913
    shutdown_event: asyncio.Event,
    sentinel: Path,
    channel: ChannelPlugin,
    agent: OwlBearAgent,
    settings: OwlBearSettings | None = None,
    error_journal: ErrorJournal | None = None,
) -> None:
    """Receive-turn-send loop extracted from run_daemon."""
    while not shutdown_event.is_set():
        if sentinel.exists():  # noqa: ASYNC240
            logger.info("Sentinel file detected — shutting down")
            shutdown_event.set()
            break

        message = await channel.receive()
        if message is None:
            logger.info("Channel returned None — shutting down")
            shutdown_event.set()
            break

        if shutdown_event.is_set():
            break

        if not message.strip():
            continue

        try:
            response = await agent.turn(message)
            await channel.send(response)
        except Exception as exc:  # noqa: BLE001
            await _recover_from_error(
                exc,
                message,
                agent=agent,
                channel=channel,
                settings=settings,
                error_journal=error_journal,
            )


# ---------------------------------------------------------------------------
# Poll-dispatch-reconcile
# ---------------------------------------------------------------------------

# Default retry configuration (mirrors config defaults)
_DEFAULT_MAX_RETRY_ATTEMPTS = 5
_DEFAULT_BACKOFF_BASE = 10.0
_DEFAULT_BACKOFF_MAX = 320.0


def _compute_retry_delay(*, attempt: int, base: float, maximum: float) -> float:
    """Compute exponential backoff delay capped at *maximum*.

    Formula: ``min(base * 2 ** (attempt - 1), maximum)``
    """
    return min(base * 2 ** (attempt - 1), maximum)


async def schedule_task_retry(  # noqa: PLR0913
    *,
    state: OrchestratorState,
    kanban: KanbanToolset,
    task_id: str,
    error: Exception,
    max_attempts: int,
    backoff_base: float,
    backoff_max: float,
) -> None:
    """Handle task-level retry policy for a failed task.

    The write path is idempotent for concurrent callers that compute the
    same ``next_attempt`` value.
    """
    from owlbear.core.errors import BudgetExceededError  # noqa: PLC0415

    if isinstance(error, BudgetExceededError):
        reason = f"Budget exceeded: {error}"
        try:
            await kanban.kanban_edit(task_id, block=reason)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to block budget-exceeded task %s", task_id, exc_info=True)
        state.retries.pop(task_id, None)
        state.claimed.discard(task_id)
        return

    prev = state.retries.get(task_id)
    next_attempt = (prev.attempt + 1) if prev else 1

    # Allow same-attempt concurrent callers to observe and skip duplicate writes.
    await asyncio.sleep(0)
    current = state.retries.get(task_id)
    if current is not None and current.attempt >= next_attempt:
        return

    if next_attempt > max_attempts:
        reason = f"Retry exhausted after {max_attempts} attempts. Last error: {error}"
        try:
            await kanban.kanban_edit(task_id, block=reason)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to block exhausted task %s", task_id, exc_info=True)
        state.retries.pop(task_id, None)
        state.claimed.discard(task_id)
        return

    delay = _compute_retry_delay(
        attempt=next_attempt,
        base=backoff_base,
        maximum=backoff_max,
    )
    state.retries[task_id] = RetryEntry(
        task_id=task_id,
        attempt=next_attempt,
        next_due=datetime.now(UTC) + timedelta(seconds=delay),
        last_error=str(error),
    )


async def reconcile_tasks(  # noqa: PLR0913
    *,
    state: OrchestratorState,
    kanban: KanbanToolset,
    wip_store: WipStore | None = None,
    hooks: HookRegistry | None = None,
    max_retry_attempts: int = _DEFAULT_MAX_RETRY_ATTEMPTS,
    backoff_base: float = _DEFAULT_BACKOFF_BASE,
    backoff_max: float = _DEFAULT_BACKOFF_MAX,
    lint_gate_enabled: bool = False,
    workspace: Path | None = None,
) -> None:
    """Check completed/failed asyncio Tasks and update state + kanban.

    When *wip_store* is provided, clears WIP on success and saves a
    truncated failure summary (up to :data:`_WIP_MAX_CHARS` chars) on
    failure so the next poll cycle can resume with context.

    :class:`~owlbear.core.errors.BudgetExceededError` is treated as
    permanent: the task is blocked immediately and retry logic is skipped.

    Emits :attr:`HookEvent.TASK_COMPLETE` with ``{task_id, outcome}``
    for each finished task when *hooks* is provided.
    """
    done_ids = [tid for tid, rt in state.running.items() if rt.asyncio_task.done()]
    for tid in done_ids:
        rt = state.running.pop(tid)
        exc = rt.asyncio_task.exception()

        # --- Lint gate (#704) ---
        if exc is None and lint_gate_enabled and workspace is not None:
            lint_result = await run_lint_gate(workspace)
            if not lint_result.passed:
                logger.warning("Lint gate failed for task %s: %s", tid, lint_result.errors)
                exc = LintGateError(lint_result.errors)

        if exc is not None:
            logger.error("Task %s failed: %s", tid, exc)
            if wip_store is not None:
                summary = f"Failed: {type(exc).__name__}: {exc}"
                wip_store.save(
                    agent="builder",
                    task_id=tid,
                    summary=summary[:_WIP_MAX_CHARS],
                )
            if hooks is not None:
                from owlbear.core.errors import BudgetExceededError  # noqa: PLC0415

                outcome = "budget_exceeded" if isinstance(exc, BudgetExceededError) else "failure"
                await hooks.emit(
                    HookEvent.TASK_COMPLETE,
                    {"task_id": tid, "outcome": outcome},
                )

            await schedule_task_retry(
                state=state,
                kanban=kanban,
                task_id=tid,
                error=exc,
                max_attempts=max_retry_attempts,
                backoff_base=backoff_base,
                backoff_max=backoff_max,
            )
        else:
            if wip_store is not None:
                wip_store.clear(agent="builder", task_id=tid)
            await kanban.kanban_move(tid, "review")
            if hooks is not None:
                await hooks.emit(
                    HookEvent.TASK_COMPLETE,
                    {"task_id": tid, "outcome": "success"},
                )
            state.claimed.discard(tid)


async def detect_stale_tasks(
    *,
    state: OrchestratorState,
    kanban: KanbanToolset,
    channel: ChannelPlugin,
    stale_timeout: float,
) -> None:
    """Cancel tasks running longer than *stale_timeout* seconds.

    For each stale task: (1) cancel the asyncio task, (2) remove from
    ``state.running`` and ``state.claimed``, (3) block on kanban with a
    reason string, (4) alert via channel.  Steps 3/4 are best-effort —
    failures are logged but do not prevent processing remaining stale tasks.
    """
    now = datetime.now(UTC)
    stale_ids = [
        tid
        for tid, rt in state.running.items()
        if (now - rt.started_at).total_seconds() >= stale_timeout
    ]
    for tid in stale_ids:
        rt = state.running.pop(tid)
        rt.asyncio_task.cancel()
        state.claimed.discard(tid)
        try:
            await kanban.kanban_edit(
                tid, block=f"Stale: no progress for {stale_timeout}s, auto-cancelled"
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to block stale task %s on kanban", tid, exc_info=True)
        try:
            await channel.send(
                f"Task {tid} cancelled — stale after {stale_timeout}s with no progress."
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to send stale alert for task %s", tid, exc_info=True)


async def _apply_hydration(
    hydrator: Callable | None,
    prompt: str,
    body: str,
) -> str:
    """Call *hydrator* and append results to *prompt*. Never raises."""
    if hydrator is None or not body:
        return prompt
    try:
        result = await hydrator(body)
    except Exception:  # noqa: BLE001
        logger.warning("Hydrator failed, proceeding without hydrated context", exc_info=True)
        return prompt

    sections: list[str] = []
    if hasattr(result, "urls") and result.urls:
        for url, content in result.urls.items():
            sections.append(f"### {url}\n{content}")
    if hasattr(result, "files") and result.files:
        for path, content in result.files.items():
            sections.append(f"### {path}\n{content}")

    if sections:
        prompt += "\n\n## Pre-hydrated Context\n\n" + "\n\n".join(sections)
    return prompt


def _build_builder_run_kwargs(  # noqa: PLR0913
    *,
    task_id: str,
    task_title: str,
    task_status: str,
    channel: ChannelPlugin | None,
    workspace: Path | None,
    hooks: HookRegistry | None,
) -> dict[str, object]:
    """Build consistent run kwargs for builder dispatch calls."""
    dispatch_context = DispatchContext(
        workspace_root=str(workspace or Path.cwd()),
        channel_name=getattr(channel, "name", "cli"),
        task_id=task_id,
        task_title=task_title,
        task_status=task_status,
    )
    instructions, metadata = format_dispatch_context(dispatch_context)
    return {
        "deps": OwlBearDeps(
            hooks=hooks or HookRegistry(),
            dispatch_context=dispatch_context,
        ),
        "instructions": instructions,
        "metadata": metadata,
    }


def _run_builder_with_context(
    builder: object,
    prompt: str,
    run_kwargs: dict[str, object],
) -> object:
    """Call builder.run with context kwargs.

    Falls back to ``builder.run(prompt)`` only when kwargs are rejected at
    call-time (legacy fakes without ``**kwargs``). Errors raised while awaiting
    the returned coroutine must propagate unchanged.
    """
    try:
        run_coro = builder.run(prompt, **run_kwargs)  # type: ignore[no-any-return, attr-defined]
    except TypeError as exc:
        if "unexpected keyword argument" not in str(exc):
            raise
        return builder.run(prompt)  # type: ignore[no-any-return, attr-defined]

    async def _await_run() -> object:
        return await run_coro

    return _await_run()


async def poll_tick(  # noqa: PLR0913, PLR0912, PLR0915, C901
    *,
    state: OrchestratorState,
    kanban: KanbanToolset,
    agent_registry: AgentRegistry,
    max_concurrent: int,
    shutdown_event: asyncio.Event,
    wip_store: WipStore | None = None,
    hooks: HookRegistry | None = None,
    channel: ChannelPlugin | None = None,
    stale_timeout: float = 300.0,
    max_retry_attempts: int = _DEFAULT_MAX_RETRY_ATTEMPTS,
    backoff_base: float = _DEFAULT_BACKOFF_BASE,
    backoff_max: float = _DEFAULT_BACKOFF_MAX,
    lint_gate_enabled: bool = False,
    workspace: Path | None = None,
    hydrator: Callable | None = None,
) -> None:
    """Execute one poll tick: plan and dispatch todo tasks.

    Sequence: reconcile → detect stale → retry dispatch → fetch todo →
    dedup → sort → dispatch.

    When *wip_store* is provided, loads any existing WIP summary for each
    dispatched task and prepends :data:`CONTINUE_FORWARD_PREFIX` to the
    prompt so the builder agent can resume with prior context.
    """
    # 1. Reconcile completed/failed tasks
    await reconcile_tasks(
        state=state,
        kanban=kanban,
        wip_store=wip_store,
        hooks=hooks,
        max_retry_attempts=max_retry_attempts,
        backoff_base=backoff_base,
        backoff_max=backoff_max,
        lint_gate_enabled=lint_gate_enabled,
        workspace=workspace,
    )

    # 2. Detect and cancel stale tasks
    if channel is not None:
        await detect_stale_tasks(
            state=state,
            kanban=kanban,
            channel=channel,
            stale_timeout=stale_timeout,
        )

    # 3. Re-dispatch due retries
    now = datetime.now(UTC)
    due_ids = [tid for tid, entry in state.retries.items() if entry.next_due <= now]
    for tid in due_ids:
        if len(state.running) >= max_concurrent:
            break
        if shutdown_event.is_set():
            return
        state.retries.pop(tid)

        # Get task details for prompt
        details_raw = await kanban.kanban_show(tid)
        details = json.loads(details_raw)
        prompt = f"Build task #{tid}: {details['title']}\n\n{details.get('body', '')}"
        run_kwargs = _build_builder_run_kwargs(
            task_id=tid,
            task_title=details.get("title", ""),
            task_status=details.get("status", "todo"),
            channel=channel,
            workspace=workspace,
            hooks=hooks,
        )

        # Hydrate context from task body
        prompt = await _apply_hydration(hydrator, prompt, details.get("body", ""))

        # Load WIP context and prepend if available
        if wip_store is not None:
            wip_summary = wip_store.load(agent="builder", task_id=tid)
            if wip_summary is not None:
                prompt = CONTINUE_FORWARD_PREFIX + wip_summary + "\n\n" + prompt

        builder = agent_registry.get("builder")
        async_task = asyncio.create_task(
            _run_builder_with_context(builder, prompt, run_kwargs),
            name=f"poll-retry-{tid}",
        )
        state.running[tid] = RunningTask(task_id=tid, asyncio_task=async_task)
        state.last_attempted_at[tid] = now

    # 4. Available slots
    available = max_concurrent - len(state.running)
    if available <= 0:
        return

    # 4. Fetch todo tasks
    raw = await kanban.kanban_list(status="todo", format="json")
    if shutdown_event.is_set():
        return
    tasks: list[dict[str, str]] = json.loads(raw)

    # 5. Filter already-claimed
    tasks = [t for t in tasks if t["id"] not in state.claimed]

    # 5b. Skip tasks with no new activity since last attempt
    now = datetime.now(UTC)
    filtered: list[dict[str, str]] = []
    for t in tasks:
        tid = t["id"]
        prev = state.last_attempted_at.get(tid)
        if prev is not None:
            updated_str = t.get("updated", "")
            if updated_str:
                task_updated = datetime.fromisoformat(updated_str)
                if task_updated < prev:
                    logger.debug("Skipping task %s — no new activity since last attempt", tid)
                    continue
        filtered.append(t)
    tasks = filtered

    # 6. Sort by priority
    tasks.sort(key=lambda t: _PRIORITY_ORDER.get(t.get("priority", "important"), 2))

    # 7. Dispatch up to available slots
    for task_info in tasks[:available]:
        if shutdown_event.is_set():
            return
        task_id = task_info["id"]

        # Move to in-progress
        await kanban.kanban_move(task_id, "in-progress")
        state.claimed.add(task_id)

        # Get task details for prompt
        details_raw = await kanban.kanban_show(task_id)
        details = json.loads(details_raw)
        prompt = f"Build task #{task_id}: {details['title']}\n\n{details.get('body', '')}"
        run_kwargs = _build_builder_run_kwargs(
            task_id=task_id,
            task_title=details.get("title", ""),
            task_status=details.get("status", "todo"),
            channel=channel,
            workspace=workspace,
            hooks=hooks,
        )

        # Hydrate context from task body
        prompt = await _apply_hydration(hydrator, prompt, details.get("body", ""))

        # Load WIP context and prepend if available
        if wip_store is not None:
            wip_summary = wip_store.load(agent="builder", task_id=task_id)
            if wip_summary is not None:
                prompt = CONTINUE_FORWARD_PREFIX + wip_summary + "\n\n" + prompt

        # Resolve builder agent and spawn
        builder = agent_registry.get("builder")
        async_task = asyncio.create_task(
            _run_builder_with_context(builder, prompt, run_kwargs),
            name=f"poll-task-{task_id}",
        )
        state.running[task_id] = RunningTask(task_id=task_id, asyncio_task=async_task)
        state.last_attempted_at[task_id] = now


async def poll_loop(  # noqa: PLR0913
    *,
    state: OrchestratorState,
    kanban: KanbanToolset,
    agent_registry: AgentRegistry,
    settings: OwlBearSettings,
    shutdown_event: asyncio.Event,
    wip_store: WipStore | None = None,
    hooks: HookRegistry | None = None,
    channel: ChannelPlugin | None = None,
    lint_gate_enabled: bool = False,
    workspace: Path | None = None,
    hydrator: Callable | None = None,
) -> None:
    """Periodic poll-dispatch-reconcile loop."""
    while not shutdown_event.is_set():
        try:
            await poll_tick(
                state=state,
                kanban=kanban,
                agent_registry=agent_registry,
                max_concurrent=settings.max_concurrent_tasks,
                shutdown_event=shutdown_event,
                wip_store=wip_store,
                hooks=hooks,
                channel=channel,
                stale_timeout=settings.stale_task_timeout,
                max_retry_attempts=settings.task_retry_max_attempts,
                backoff_base=settings.task_retry_backoff_base,
                backoff_max=settings.task_retry_backoff_max,
                lint_gate_enabled=lint_gate_enabled,
                workspace=workspace,
                hydrator=hydrator,
            )
        except Exception:
            logger.exception("poll_tick failed")

        # Sleep interruptibly
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=settings.poll_interval,
            )


async def run_daemon(  # noqa: PLR0913, PLR0915, PLR0912, C901
    *,
    channel: ChannelPlugin,
    agent: OwlBearAgent,
    config_dir: Path,
    settings: OwlBearSettings | None = None,
    otel_endpoint: str | None = None,
    error_journal: ErrorJournal | None = None,
    kanban_toolset: KanbanToolset | None = None,
    agent_registry: AgentRegistry | None = None,
    workspace_root: Path | None = None,
    hydrator: Callable | None = None,
    consolidation_svc: object | None = None,
) -> None:
    """Run the daemon loop.

    When ``autonomous_mode`` is enabled in *settings* (and *kanban_toolset* /
    *agent_registry* are provided), runs both ``channel_loop`` and ``poll_loop``
    concurrently in an ``asyncio.TaskGroup``.  Otherwise only ``channel_loop``
    is started.

    The loop exits when any of the following occurs:

    - The channel returns ``None`` (EOF / disconnect)
    - The sentinel file ``config_dir / "owlbear.stop"`` appears
    - A signal (SIGINT / SIGTERM) sets the shutdown event

    Parameters
    ----------
    channel:
        The I/O channel to read from and write to.
    agent:
        The OwlBearAgent that processes each message.
    config_dir:
        Directory containing PID and sentinel files.
    settings:
        Optional application settings.  Enables token refresh and, when
        ``autonomous_mode`` is ``True``, the poll-dispatch-reconcile loop.
    otel_endpoint:
        Optional OTLP endpoint URL. When set, Logfire SDK is configured
        before instrumentation.
    error_journal:
        Optional :class:`~owlbear.memory.error_journal.ErrorJournal` for
        logging errors from ``_recover_from_error``.  When *None*, error
        journal logging is silently skipped.
    kanban_toolset:
        Required for autonomous mode.  Provides board I/O (list, show,
        move) used by the poll-dispatch-reconcile loop.
    agent_registry:
        Required for autonomous mode.  Supplies the ``'builder'`` agent
        used to execute dispatched tasks.
    workspace_root:
        Optional workspace root path included in the ``SESSION_START``
        hook payload.  Defaults to ``Path.cwd()`` when *None*.
    """
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # --- Observability bootstrap ---
    if otel_endpoint:
        configure_otel(otel_endpoint)
    Agent.instrument_all()

    sentinel = config_dir / "owlbear.stop"

    # Install signal handlers (cross-platform — NOT loop.add_signal_handler)
    handler = _make_signal_handler(loop, shutdown_event)
    prev_sigint = signal.signal(signal.SIGINT, handler)
    prev_sigterm = signal.signal(signal.SIGTERM, handler)

    try:
        await agent.hooks.emit(
            HookEvent.DAEMON_STARTUP,
            {"channel": channel.name, "config_dir": str(config_dir)},
        )

        _ws_root = workspace_root if workspace_root is not None else Path.cwd()
        await agent.hooks.emit(
            HookEvent.SESSION_START,
            {
                "session_id": str(agent.session.path),
                "workspace_root": str(_ws_root),
            },
        )
        logger.info("Daemon started on channel '%s'", channel.name)

        # --- Heartbeat runner ---
        heartbeat_task: asyncio.Task[None] | None = None
        if settings is not None and settings.heartbeat_enabled:
            from owlbear.heartbeat import HeartbeatRunner  # noqa: PLC0415

            hb_runner = HeartbeatRunner(
                agent=agent,
                channel=channel,
                interval_seconds=settings.heartbeat_interval,
                active_hours=settings.heartbeat_active_hours,
                shutdown_event=shutdown_event,
                heartbeat_path=config_dir / "HEARTBEAT.md",
            )
            heartbeat_task = asyncio.create_task(hb_runner.run(), name="heartbeat")

        # --- Consolidation timer ---
        consolidation_task: asyncio.Task[None] | None = None
        if consolidation_svc is not None and settings is not None:
            interval = getattr(settings, "consolidation_interval", 1800)
            consolidation_task = asyncio.create_task(
                consolidation_svc.schedule_periodic(interval=interval),
                name="consolidation",
            )

        autonomous = (
            settings is not None
            and settings.autonomous_mode
            and kanban_toolset is not None
            and agent_registry is not None
        )
        if autonomous and settings is not None:
            if kanban_toolset is None or agent_registry is None:  # pragma: no cover - guarded above
                msg = "autonomous_mode requires kanban_toolset and agent_registry"
                raise RuntimeError(msg)
            from owlbear.memory.wip import WipStore as _WipStore  # noqa: PLC0415

            wip_store = _WipStore(config_dir)
            state = OrchestratorState()
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(
                        channel_loop(
                            shutdown_event,
                            sentinel,
                            channel,
                            agent,
                            settings,
                            error_journal,
                        )
                    )
                    tg.create_task(
                        poll_loop(
                            state=state,
                            kanban=kanban_toolset,
                            agent_registry=agent_registry,
                            settings=settings,
                            shutdown_event=shutdown_event,
                            wip_store=wip_store,
                            hooks=agent.hooks,
                            channel=channel,
                            lint_gate_enabled=settings.lint_gate_enabled,
                            workspace=Path.cwd(),
                            hydrator=hydrator,
                        )
                    )
            finally:
                # Cancel in-flight tasks spawned by poll_loop
                inflight = [
                    rt.asyncio_task for rt in state.running.values() if not rt.asyncio_task.done()
                ]
                for t in inflight:
                    t.cancel()
                if inflight:
                    with contextlib.suppress(asyncio.CancelledError):
                        await asyncio.wait(inflight, timeout=5.0)
        else:
            await channel_loop(
                shutdown_event,
                sentinel,
                channel,
                agent,
                settings,
                error_journal,
            )

    finally:
        # Cancel heartbeat if running
        if heartbeat_task is not None and not heartbeat_task.done():
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        # Cancel consolidation timer if running
        if consolidation_task is not None and not consolidation_task.done():
            consolidation_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consolidation_task

        # Emit SESSION_END before restoring signal handlers
        try:
            messages = agent.session.load()
            if asyncio.iscoroutine(messages):
                messages = await messages
        except Exception:  # noqa: BLE001 — AC requires fallback on *any* error
            messages = []
        await agent.hooks.emit(
            HookEvent.SESSION_END,
            {
                "session_id": str(agent.session.path),
                "messages": messages,
            },
        )

        # Restore previous signal handlers
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)

        # Clean up sentinel file
        sentinel.unlink(missing_ok=True)

        logger.info("Daemon stopped")
