"""Orchestrator dispatch loop — drives wave assembly and ACP dispatch."""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from owlbear.audit.models import CompletionEvent, DispatchEvent
from owlbear.orchestrator.waves import Wave, assemble_waves
from owlbear.planner.board import read_board
from owlbear.planner.selector import select_tasks
from owlbear_orchestrator.acp_client import AcpClient, AcpClientError
from owlbear_orchestrator.error_journal import ErrorJournal, ErrorLoggerAdapter
from owlbear_orchestrator.process_supervisor import ProcessSupervisor

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear.audit import AuditLog
    from owlbear.planner.models import DispatchEntry

try:
    from acp import PROTOCOL_VERSION, Client, connect_to_agent, text_block
except ImportError:  # pragma: no cover
    PROTOCOL_VERSION = "2025-02-14"  # type: ignore[assignment]
    Client = object  # type: ignore[assignment,misc]
    connect_to_agent = None  # type: ignore[assignment]

    def text_block(text: str) -> object:  # type: ignore[misc]
        """Fallback text block when acp is not installed."""

        @dataclasses.dataclass
        class _TextBlock:
            text: str

        return _TextBlock(text=text)


_logger = logging.getLogger(__name__)


def _try_audit(fn: Callable[..., None], *args: object, context: str) -> None:
    """Call an audit function, emitting a WARNING on OSError — never blocks dispatch."""
    try:
        fn(*args)
    except OSError as exc:
        _logger.warning("Audit I/O error in %s: %s", context, exc)


class _OrchestratorClient(Client):  # type: ignore[misc]
    """Minimal concrete ACP Client used by the orchestrator dispatch loop."""


# Prompt prefix per agent type.  Used by format_prompt() to build dispatch prompts.
AGENT_PROMPT_PREFIX: dict[str, str] = {
    "architect": "Architect Review",
    "builder": "Build",
    "reviewer": "Review",
    "test-writer": "Write tests",
    "researcher": "Research",
    "doc-writer": "Docs Gate",
    "auditor": "Audit",
    "planner": "Plan",
    "curator": "Curate: Periodic curation",
}

_RATE_LIMIT_PATTERNS = ("rate-limited", "rate_limited", "rate limits")


@dataclasses.dataclass(frozen=True)
class CycleResult:
    """Immutable summary of a single wave's dispatch outcomes."""

    successes: list[int]
    failures: list[int]
    rate_limited: bool


@dataclasses.dataclass
class LoopState:
    """Mutable cross-wave loop state for the dispatch loop."""

    sequential_remaining: int = 0
    cycle: int = 0
    stale_retried: set[int] = dataclasses.field(default_factory=set)
    crash_failures: set[int] = dataclasses.field(default_factory=set)


def format_prompt(entry: DispatchEntry) -> str:
    """Build the dispatch prompt string for a given entry.

    Curator entries return the prefix verbatim (no task ID).
    All others return "{prefix}: #{task_id}", plus an optional retry-context line.
    """
    prefix = AGENT_PROMPT_PREFIX[entry.agent]
    if entry.agent == "curator":
        return prefix
    result = f"{prefix}: #{entry.task_id}"
    if entry.retry_hint:
        result += f"\nRetry context: {entry.retry_hint}"
    return result


def _is_rate_limit(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(pattern in msg for pattern in _RATE_LIMIT_PATTERNS)


def _git_diff_names() -> list[str]:
    """Return file names currently modified relative to HEAD via git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        return [f for f in result.stdout.splitlines() if f]
    except Exception:  # noqa: BLE001
        return []


async def dispatch_entry(
    entry: DispatchEntry,
    client: AcpClient,
    *,
    audit_log: AuditLog | None = None,
    cycle_id: str = "",
) -> bool:
    """Dispatch a single entry via ACP.

    Args:
        entry: The dispatch entry to execute.
        client: ACP client to use for the session.
        audit_log: Optional audit logger for DispatchEvent and CompletionEvent.
        cycle_id: Cycle trace ID propagated to both DispatchEvent and CompletionEvent.

    Returns:
        True on success, False on AcpClientError or TimeoutError.
        Other exceptions propagate to the caller.
    """
    before_files = _git_diff_names()

    try:
        session_resp = await client.new_session(cwd=str(Path.cwd()), mcp_servers=[])
    except (AcpClientError, TimeoutError) as exc:
        if audit_log is not None:
            _failure_event = CompletionEvent(
                timestamp=datetime.now(tz=UTC).isoformat(),
                task_id=entry.task_id,
                agent=entry.agent,
                outcome="failure",
                duration_ms=0,
                files_changed=[],
                error=str(exc),
                cycle_id=cycle_id,
            )
            _try_audit(
                audit_log.log_completion,
                _failure_event,
                uuid4().hex,
                context="log_completion (new_session failure)",
            )
        return False

    session_id = session_resp.session_id
    prompt_text = format_prompt(entry)
    dispatch_event = DispatchEvent(
        timestamp=datetime.now(tz=UTC).isoformat(),
        task_id=entry.task_id,
        agent=entry.agent,
        prompt_summary=prompt_text[:100],
        session_id=session_id,
        cycle_id=cycle_id,
    )

    if audit_log is not None:
        _try_audit(audit_log.log_dispatch, dispatch_event, session_id, context="log_dispatch")

    t_start = time.monotonic()
    try:
        await client.prompt(session_id=session_id, prompt=[text_block(prompt_text)])
    except (AcpClientError, TimeoutError) as exc:
        t_end = time.monotonic()
        if audit_log is not None:
            _failure_event = CompletionEvent(
                timestamp=datetime.now(tz=UTC).isoformat(),
                task_id=entry.task_id,
                agent=entry.agent,
                outcome="failure",
                duration_ms=int((t_end - t_start) * 1000),
                files_changed=[],
                error=str(exc),
                cycle_id=cycle_id,
            )
            _try_audit(
                audit_log.log_completion,
                _failure_event,
                session_id,
                context="log_completion (prompt failure)",
            )
        return False
    t_end = time.monotonic()

    after_files = _git_diff_names()
    before_set = set(before_files)
    duration_ms = int((t_end - t_start) * 1000)
    files_changed = [f for f in after_files if f not in before_set]

    completion_event = CompletionEvent(
        timestamp=datetime.now(tz=UTC).isoformat(),
        task_id=entry.task_id,
        agent=entry.agent,
        outcome="success",
        duration_ms=duration_ms,
        files_changed=files_changed,
        cycle_id=cycle_id,
    )

    if audit_log is not None:
        _try_audit(
            audit_log.log_completion,
            completion_event,
            session_id,
            context="log_completion (success)",
        )

    return True


def _apply_wave_result(
    entry: DispatchEntry,
    result: bool | BaseException,  # noqa: FBT001
    successes: list[int],
    failures: list[int],
    state: LoopState,
) -> bool:
    """Apply a single dispatch result to the accumulators. Returns rate_limited flag."""
    if isinstance(result, BaseException):
        if _is_rate_limit(result):
            state.sequential_remaining = 3
            return True
        failures.append(entry.task_id)
    elif result:
        successes.append(entry.task_id)
    else:
        failures.append(entry.task_id)
    return False


async def _dispatch_sequential(  # noqa: PLR0913
    wave: Wave,
    client: AcpClient,
    state: LoopState,
    successes: list[int],
    failures: list[int],
    *,
    audit_log: AuditLog | None = None,
    cycle_id: str = "",
) -> bool:
    """Dispatch wave entries one at a time, decrementing sequential_remaining each call."""
    rate_limited = False
    for entry in wave.entries:
        try:
            ok = await dispatch_entry(entry, client, audit_log=audit_log, cycle_id=cycle_id)
        except Exception as exc:  # noqa: BLE001
            rl = _apply_wave_result(entry, exc, successes, failures, state)
        else:
            rl = _apply_wave_result(entry, ok, successes, failures, state)
        if rl:
            rate_limited = True
        if state.sequential_remaining > 0:
            state.sequential_remaining -= 1
    return rate_limited


async def _dispatch_parallel(  # noqa: PLR0913
    wave: Wave,
    client: AcpClient,
    state: LoopState,
    successes: list[int],
    failures: list[int],
    *,
    audit_log: AuditLog | None = None,
    cycle_id: str = "",
) -> bool:
    """Dispatch all wave entries concurrently via asyncio.gather."""
    results = await asyncio.gather(
        *[dispatch_entry(e, client, audit_log=audit_log, cycle_id=cycle_id) for e in wave.entries],
        return_exceptions=True,
    )
    rate_limited = False
    retry_entries: list[DispatchEntry] = []
    for entry, result in zip(wave.entries, results, strict=True):
        # Bare Exception (not a subclass) is a transient unknown crash — retry once.
        is_bare_exception = isinstance(result, BaseException) and type(result) is Exception
        if is_bare_exception and not _is_rate_limit(result):
            retry_entries.append(entry)
            continue
        rl = _apply_wave_result(entry, result, successes, failures, state)
        if rl:
            rate_limited = True

    if retry_entries:
        retry_results = await asyncio.gather(
            *[dispatch_entry(e, client, audit_log=audit_log, cycle_id=cycle_id) for e in retry_entries],
            return_exceptions=True,
        )
        for entry, result in zip(retry_entries, retry_results, strict=True):
            rl = _apply_wave_result(entry, result, successes, failures, state)
            if rl:
                rate_limited = True

    return rate_limited


async def dispatch_wave(
    wave: Wave,
    client: AcpClient,
    state: LoopState,
    *,
    audit_log: AuditLog | None = None,
    cycle_id: str = "",
) -> CycleResult:
    """Dispatch all entries in a wave, respecting sequential/parallel mode.

    Args:
        wave: The wave of entries to dispatch.
        client: ACP client.
        state: Mutable loop state (sequential_remaining updated in-place).
        audit_log: Optional audit logger passed through to dispatch_entry.
        cycle_id: Cycle trace ID forwarded to every dispatch_entry call.

    Returns:
        CycleResult summarising successes, failures, and rate-limit status.
    """
    successes: list[int] = []
    failures: list[int] = []

    if state.sequential_remaining > 0:
        rate_limited = await _dispatch_sequential(
            wave, client, state, successes, failures, audit_log=audit_log, cycle_id=cycle_id
        )
    else:
        rate_limited = await _dispatch_parallel(
            wave, client, state, successes, failures, audit_log=audit_log, cycle_id=cycle_id
        )

    return CycleResult(successes=successes, failures=failures, rate_limited=rate_limited)


async def run_loop(  # noqa: PLR0913
    kanban_bin: Path,
    kanban_dir: Path,
    client: AcpClient,
    *,
    wave_size: int = 4,
    scope: str | None = None,
    audit_log: AuditLog | None = None,
) -> None:
    """Run the orchestrator dispatch loop until the board is empty.

    Args:
        kanban_bin: Path to the kanban-md binary.
        kanban_dir: Path to the kanban directory.
        client: ACP client for dispatching agents.
        wave_size: Maximum entries per dispatch wave.
        scope: Optional tag filter forwarded to read_board().
        audit_log: Optional audit logger injected into each dispatch.
    """
    state = LoopState()

    while True:
        state.cycle += 1
        tasks = await read_board(kanban_bin=kanban_bin, kanban_dir=kanban_dir, scope=scope)
        filtered_tasks = [t for t in tasks if t.id not in state.crash_failures]
        plan = select_tasks(filtered_tasks)

        if not plan.entries:
            break

        # Track IDs dispatched with a retry_hint — they are "stale-retried".
        # Clear entries that reappear without a retry_hint (Amendment 1).
        new_stale = {e.task_id for e in plan.entries if e.retry_hint}
        ids_without_retry_hint = {e.task_id for e in plan.entries if not e.retry_hint}
        state.stale_retried = (state.stale_retried | new_stale) - ids_without_retry_hint

        waves = assemble_waves(plan.entries, wave_size=wave_size, cycle=state.cycle)
        cycle_id = uuid4().hex

        cycle_failures: set[int] = set()
        for wave_num, wave in enumerate(waves, start=1):
            for entry in wave.entries:
                _logger.debug(
                    "Dispatching task_id=%d agent=%s wave=%d",
                    entry.task_id,
                    entry.agent,
                    wave_num,
                )
            result = await dispatch_wave(wave, client, state, audit_log=audit_log, cycle_id=cycle_id)
            cycle_failures |= set(result.failures)

        _logger.debug(
            "Cycle %d complete: successes=%d failures=%d",
            state.cycle,
            sum(len(w.entries) for w in waves) - len(cycle_failures),
            len(cycle_failures),
        )
        state.crash_failures = cycle_failures


async def orchestrate(  # noqa: PLR0913
    kanban_bin: Path,
    kanban_dir: Path,
    *,
    copilot_cmd: list[str] | None = None,
    client: AcpClient | None = None,
    scope: str | None = None,
    wave_size: int = 4,
    audit_log: AuditLog | None = None,
    error_journal: ErrorJournal | None = None,
) -> None:
    """Top-level entry point: wire infrastructure and run the dispatch loop.

    When ``client`` is provided, uses it directly and skips subprocess setup.
    When ``copilot_cmd`` is provided, constructs a ProcessSupervisor, spawns
    the ACP subprocess, initialises the connection, then delegates to run_loop().

    Args:
        kanban_bin: Path to the kanban-md binary.
        kanban_dir: Path to the kanban directory.
        copilot_cmd: Command to spawn the Copilot ACP subprocess.
        client: Pre-built AcpClient (bypasses subprocess setup when provided).
        scope: Optional tag filter forwarded to read_board().
        wave_size: Maximum entries per dispatch wave.
        audit_log: Optional audit logger injected into dispatch.
        error_journal: Optional error journal injected into AcpClient; defaults
            to a new ErrorJournal at .owlbear/error-journal.jsonl.
    """
    if client is not None:
        await run_loop(
            kanban_bin=kanban_bin,
            kanban_dir=kanban_dir,
            client=client,
            wave_size=wave_size,
            scope=scope,
            audit_log=audit_log,
        )
        return

    if copilot_cmd is None:  # pragma: no cover
        msg = "Either client or copilot_cmd must be provided"
        raise ValueError(msg)

    async with ProcessSupervisor(copilot_cmd) as supervisor:
        stdin, stdout = await supervisor.ensure_running()
        client_impl = _OrchestratorClient()
        conn = connect_to_agent(client_impl, stdin, stdout)
        await conn.initialize(protocol_version=PROTOCOL_VERSION)
        if error_journal is None:
            error_journal = ErrorJournal(Path(".owlbear/error-journal.jsonl"))
        acp_client = AcpClient(conn, error_logger=ErrorLoggerAdapter(error_journal))
        await run_loop(
            kanban_bin=kanban_bin,
            kanban_dir=kanban_dir,
            client=acp_client,
            wave_size=wave_size,
            scope=scope,
            audit_log=audit_log,
        )
        supervisor.mark_healthy()
