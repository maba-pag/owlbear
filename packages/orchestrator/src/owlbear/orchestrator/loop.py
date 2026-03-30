"""Orchestrator dispatch loop — drives wave assembly and ACP dispatch."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import TYPE_CHECKING

from owlbear.orchestrator.waves import Wave, assemble_waves
from owlbear.planner.board import read_board
from owlbear.planner.selector import select_tasks
from owlbear_orchestrator.acp_client import AcpClient, AcpClientError

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.planner.models import DispatchEntry

# Prompt prefix per agent type.  Used by format_prompt() to build dispatch prompts.
AGENT_PROMPT_PREFIX: dict[str, str] = {
    "architect": "Architect Review",
    "builder": "Build",
    "reviewer": "Review",
    "test-writer": "Write tests",
    "researcher": "Research",
    "writer": "Docs Gate",
    "auditor": "Audit",
    "kanban-planner": "Plan",
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


async def dispatch_entry(entry: DispatchEntry, client: AcpClient) -> bool:
    """Dispatch a single entry via ACP.

    Args:
        entry: The dispatch entry to execute.
        client: ACP client to use for the session.

    Returns:
        True on success, False on AcpClientError or TimeoutError.
        Other exceptions propagate to the caller.
    """
    try:
        session_resp = await client.new_session(
            session_name=f"owlbear-{entry.agent}-{entry.task_id}"
        )
        await client.prompt(session_id=session_resp.session_id)
        return True  # noqa: TRY300
    except (AcpClientError, TimeoutError):
        return False


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


async def _dispatch_sequential(
    wave: Wave,
    client: AcpClient,
    state: LoopState,
    successes: list[int],
    failures: list[int],
) -> bool:
    """Dispatch wave entries one at a time, decrementing sequential_remaining each call."""
    rate_limited = False
    for entry in wave.entries:
        try:
            ok = await dispatch_entry(entry, client)
        except Exception as exc:  # noqa: BLE001
            rl = _apply_wave_result(entry, exc, successes, failures, state)
        else:
            rl = _apply_wave_result(entry, ok, successes, failures, state)
        if rl:
            rate_limited = True
        if state.sequential_remaining > 0:
            state.sequential_remaining -= 1
    return rate_limited


async def _dispatch_parallel(
    wave: Wave,
    client: AcpClient,
    state: LoopState,
    successes: list[int],
    failures: list[int],
) -> bool:
    """Dispatch all wave entries concurrently via asyncio.gather."""
    results = await asyncio.gather(
        *[dispatch_entry(e, client) for e in wave.entries],
        return_exceptions=True,
    )
    rate_limited = False
    for entry, result in zip(wave.entries, results, strict=True):
        rl = _apply_wave_result(entry, result, successes, failures, state)
        if rl:
            rate_limited = True
    return rate_limited


async def dispatch_wave(
    wave: Wave,
    client: AcpClient,
    state: LoopState,
) -> CycleResult:
    """Dispatch all entries in a wave, respecting sequential/parallel mode.

    Args:
        wave: The wave of entries to dispatch.
        client: ACP client.
        state: Mutable loop state (sequential_remaining updated in-place).

    Returns:
        CycleResult summarising successes, failures, and rate-limit status.
    """
    successes: list[int] = []
    failures: list[int] = []

    if state.sequential_remaining > 0:
        rate_limited = await _dispatch_sequential(wave, client, state, successes, failures)
    else:
        rate_limited = await _dispatch_parallel(wave, client, state, successes, failures)

    return CycleResult(successes=successes, failures=failures, rate_limited=rate_limited)


async def run_loop(
    kanban_bin: Path,
    kanban_dir: Path,
    client: AcpClient,
    *,
    wave_size: int = 4,
) -> None:
    """Run the orchestrator dispatch loop until the board is empty.

    Args:
        kanban_bin: Path to the kanban-md binary.
        kanban_dir: Path to the kanban directory.
        client: ACP client for dispatching agents.
        wave_size: Maximum entries per dispatch wave.
    """
    state = LoopState()

    while True:
        state.cycle += 1
        tasks = await read_board(kanban_bin=kanban_bin, kanban_dir=kanban_dir)
        plan = select_tasks(
            tasks,
            crash_failures=state.crash_failures,
            stale_retried=state.stale_retried,
        )

        if not plan.entries:
            break

        # Track IDs dispatched with a retry_hint — they are "stale-retried"
        new_stale = {e.task_id for e in plan.entries if e.retry_hint}
        state.stale_retried = state.stale_retried | new_stale

        waves = assemble_waves(plan.entries, wave_size=wave_size, cycle=state.cycle)

        cycle_failures: set[int] = set()
        for wave in waves:
            result = await dispatch_wave(wave, client, state)
            cycle_failures |= set(result.failures)

        state.crash_failures = cycle_failures
