"""Supervisor for hook-triggered background worker tasks.

Owns a tracked set of :class:`asyncio.Task` instances and a shared
:class:`asyncio.Semaphore` that bounds concurrent worker critical sections.
Replaces bare :func:`asyncio.create_task` calls with a managed, shutdown-safe
lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Coroutine

logger = logging.getLogger(__name__)


class HookWorkerSupervisor:
    """Manages background worker tasks with semaphore-bounded concurrency.

    Owns ``_background_tasks`` and ``_bg_semaphore`` following the same
    ownership model as :class:`~owlbear.memory.knowledge.enrichment.GraphEnricher`.

    Args:
        bg_concurrency: Maximum number of concurrent worker critical sections.
            Defaults to ``1`` (serialised workers).
    """

    def __init__(self, bg_concurrency: int = 1) -> None:
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._bg_semaphore = asyncio.Semaphore(bg_concurrency)

    def schedule(self, coro: Coroutine[Any, Any, None]) -> None:
        """Schedule *coro* as a semaphore-bounded background task.

        Keeps a strong reference to the spawned task until it completes; a done
        callback removes the finished task from :attr:`_background_tasks`.
        """

        async def _wrapper() -> None:
            async with self._bg_semaphore:
                await coro

        task = asyncio.create_task(_wrapper())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def shutdown(self) -> None:
        """Cancel all tracked tasks and await their cleanup.

        Returns only after every tracked task has finished or been cancelled.
        Leaves :attr:`_background_tasks` empty on return.
        """
        tasks = list(self._background_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
