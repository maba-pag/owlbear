"""Retrospective learning hook for completed tasks.

Listens on :pyattr:`HookEvent.TASK_COMPLETE`, filters trivial tasks, runs a
PydanticAI agent for structured retrospective analysis, and ingests findings
into the knowledge graph.  The heavy work runs fire-and-forget via
:func:`asyncio.create_task`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent

from owlbear.core.hooks import TaskCompleteData  # noqa: TC001
from owlbear.memory.knowledge.cancellation import LinkedCancelSignal

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator
    from pathlib import Path

    from pydantic_ai.models import Model

    from owlbear.core.hook_worker_supervisor import HookWorkerSupervisor
    from owlbear.core.hooks import HookRegistry
    from owlbear.memory.knowledge.cancellation import CancelSignal
    from owlbear.memory.knowledge.ingest import IngestPipeline
    from owlbear.memory.usage import UsageTracker

from owlbear.memory.usage import record_agent_usage

logger = logging.getLogger(__name__)

# Priority ordering — lower index = lower priority.
_PRIORITY_ORDER: list[str] = [
    "someday",
    "nice-to-have",
    "important",
    "needed",
    "critical",
]

# Backward-move targets that count as rejections.
_REJECTION_TARGETS: frozenset[str] = frozenset({"todo", "backlog", "ideation"})

_RETRO_SYSTEM_PROMPT = (
    "You are a retrospective analyst for a software development team. "
    "Given a completed task description and its activity history, produce "
    "structured findings: what worked, what failed, error patterns observed, "
    "and reusable patterns discovered."
)


class _LazyCoroutine:
    """Create the coroutine only when first awaited by the supervisor.

    Tests inject a mock supervisor that only asserts ``schedule()`` calls. With
    eager coroutine creation this leaves an unawaited coroutine warning; a lazy
    awaitable keeps the same production behavior without leaking coroutines.
    """

    def __init__(self, factory: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._factory = factory
        self._coro: Coroutine[Any, Any, None] | None = None

    def __await__(self) -> Generator[Any, None, None]:
        if self._coro is None:
            self._coro = self._factory()
        return self._coro.__await__()

    def close(self) -> None:
        if self._coro is not None:
            self._coro.close()


# ---------------------------------------------------------------------------
# Structured output model
# ---------------------------------------------------------------------------


class RetroFindings(BaseModel):
    """Structured retrospective findings for a completed task."""

    model_config = ConfigDict(frozen=True)

    what_worked: list[str]
    what_failed: list[str]
    error_patterns: list[str]
    reusable_patterns: list[str]


# ---------------------------------------------------------------------------
# Hook implementation
# ---------------------------------------------------------------------------


class RetrospectiveHook:
    """TASK_COMPLETE hook that generates and ingests retrospective findings.

    Args:
        model: PydanticAI model for the retrospective agent.
        ingest_pipeline: Knowledge graph ingest pipeline.
        kanban_root: Path to the kanban directory (contains ``activity.jsonl``).
        shutdown_event: Optional daemon shutdown event.  When set, the
            per-operation cancel signal passed to ``ingest_text`` is also set.
    """

    def __init__(  # noqa: PLR0913
        self,
        model: Model,
        ingest_pipeline: IngestPipeline,
        kanban_root: Path,
        shutdown_event: asyncio.Event | None = None,
        cancel: CancelSignal | None = None,
        supervisor: HookWorkerSupervisor | None = None,
        tracker: UsageTracker | None = None,
        provider: str = "copilot",
    ) -> None:
        self._ingest_pipeline = ingest_pipeline
        self._kanban_root = kanban_root
        self._model = model
        self._shutdown_event = shutdown_event
        self._cancel = self._compose_cancel(cancel=cancel, shutdown_event=shutdown_event)
        self._supervisor = supervisor
        self._tracker = tracker
        self._provider = provider
        self._agent: Agent[None, RetroFindings] | None = None

    @staticmethod
    def _compose_cancel(
        *,
        cancel: CancelSignal | None,
        shutdown_event: asyncio.Event | None,
    ) -> CancelSignal:
        """Compose optional cancel sources into one linked signal."""
        if cancel is not None and shutdown_event is not None:
            return LinkedCancelSignal(cancel, shutdown_event)
        if cancel is not None:
            return cancel
        if shutdown_event is not None:
            return shutdown_event
        return asyncio.Event()

    def _get_agent(self) -> Agent[None, RetroFindings]:
        """Lazily create the PydanticAI agent on first use."""
        if self._agent is None:
            self._agent = Agent(
                self._model,
                system_prompt=_RETRO_SYSTEM_PROMPT,
                output_type=RetroFindings,
            )
        return self._agent

    # -- Hook callback -------------------------------------------------------

    async def __call__(self, data: TaskCompleteData) -> None:
        """Handle a ``TASK_COMPLETE`` event.

        Spawns the retrospective analysis as a fire-and-forget background
        task.  Non-success outcomes are silently skipped.
        """
        outcome = data.get("outcome")
        if outcome != "success":
            return

        task_id = str(data.get("task_id", ""))
        if not task_id:
            return

        rejection_count = self._count_rejections(task_id)

        if rejection_count == 0:
            priority = self._get_priority(task_id)
            if _PRIORITY_ORDER.index(priority) < _PRIORITY_ORDER.index("needed"):
                return

        if self._supervisor is not None:
            self._supervisor.schedule(_LazyCoroutine(lambda: self._run_retrospective(task_id)))
        else:
            asyncio.create_task(self._run_retrospective(task_id))  # noqa: RUF006

    # -- Registration --------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on :pyattr:`HookEvent.TASK_COMPLETE`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.TASK_COMPLETE, self)

    # -- Internal ------------------------------------------------------------

    def _count_rejections(self, task_id: str) -> int:
        """Count backward moves for *task_id* in ``activity.jsonl``."""
        log_path = self._kanban_root / "activity.jsonl"
        if not log_path.is_file():
            return 0

        count = 0
        with log_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()  # noqa: PLW2901
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entry.get("action") != "move":
                    continue
                if str(entry.get("task_id", "")) != task_id:
                    continue

                detail = entry.get("detail", "")
                parts = detail.split(" -> ", maxsplit=1)
                if len(parts) == 2:  # noqa: PLR2004
                    to_status = parts[1].strip()
                    if to_status in _REJECTION_TARGETS:
                        count += 1
        return count

    def _get_priority(self, task_id: str) -> str:
        """Get task priority via ``kanban-md show --json``."""
        kanban_exe = self._kanban_root / "kanban-md.exe"
        try:
            result = subprocess.run(  # noqa: S603
                [str(kanban_exe), "show", task_id, "--json"],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(self._kanban_root),
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                priority = data.get("priority", "important")
                if priority in _PRIORITY_ORDER:
                    return priority
        except Exception:  # noqa: BLE001
            logger.warning("Failed to get priority for task %s", task_id, exc_info=True)
        return "important"

    async def _run_retrospective(self, task_id: str) -> None:
        """Run the retrospective agent and ingest findings."""
        try:
            agent = self._get_agent()
            result = await agent.run(f"Generate a retrospective for completed task #{task_id}.")
            if self._tracker is not None:
                record_agent_usage(
                    tracker=self._tracker,
                    result=result,
                    model=str(self._model),
                    provider=self._provider,
                    session_id="background:retrospective",
                    operation="retrospective",
                )
            findings: RetroFindings = result.output

            text = self._format_findings(task_id, findings)
            metadata = {"source_type": "retrospective", "task_id": task_id}
            await self._ingest_pipeline.ingest_text(
                text=text,
                metadata=metadata,
                cancel=self._cancel,
            )
        except Exception:
            logger.exception("Retrospective failed for task %s", task_id)

    @staticmethod
    def _format_findings(task_id: str, findings: RetroFindings) -> str:
        """Format findings as human-readable text for KG ingestion."""
        sections: list[str] = [f"# Retrospective — Task #{task_id}"]

        if findings.what_worked:
            sections.append("\n## What Worked")
            sections.extend(f"- {item}" for item in findings.what_worked)

        if findings.what_failed:
            sections.append("\n## What Failed")
            sections.extend(f"- {item}" for item in findings.what_failed)

        if findings.error_patterns:
            sections.append("\n## Error Patterns")
            sections.extend(f"- {item}" for item in findings.error_patterns)

        if findings.reusable_patterns:
            sections.append("\n## Reusable Patterns")
            sections.extend(f"- {item}" for item in findings.reusable_patterns)

        return "\n".join(sections)
