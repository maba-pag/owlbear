"""TASK_COMPLETE hook that writes an audit-map advisory to docs/scratch/."""

from __future__ import annotations

import json
import logging
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator
    from pathlib import Path

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings
    from owlbear.core.hook_worker_supervisor import HookWorkerSupervisor
    from owlbear.core.hooks import HookRegistry, TaskCompleteData

logger = logging.getLogger(__name__)

_AUDIT_MAP_TAG = "worker:audit-map"


class _LazyCoroutine:
    """Create a coroutine only when first awaited by the supervisor."""

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


class AuditMapAdvisoryHook:
    """TASK_COMPLETE hook that writes an audit-map advisory worker artifact.

    The worker is scheduled only when all eligibility gates pass:
    successful task outcome, feature flag enabled, and task tagged with
    ``worker:audit-map``.
    """

    def __init__(
        self,
        settings: OwlBearSettings,
        supervisor: HookWorkerSupervisor,
        kanban_root: Path,
        workspace_root: Path,
        channel: ChannelPlugin | None = None,
    ) -> None:
        self._settings = settings
        self._supervisor = supervisor
        self._kanban_root = kanban_root
        self._workspace_root = workspace_root
        self._channel = channel

    async def __call__(self, data: TaskCompleteData) -> None:
        """Schedule the advisory worker when all eligibility gates pass."""
        if data.get("outcome") != "success":
            return

        if not bool(getattr(self._settings, "audit_map_worker_enabled", False)):
            return

        task_id = str(data.get("task_id", ""))
        if not task_id:
            return

        if not self._task_has_tag(task_id=task_id, tag=_AUDIT_MAP_TAG):
            return

        self._supervisor.schedule(_LazyCoroutine(lambda: self._run_worker(task_id)))

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on ``HookEvent.TASK_COMPLETE``."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.TASK_COMPLETE, self)

    def _task_has_tag(self, *, task_id: str, tag: str) -> bool:
        """Return ``True`` when ``kanban-md show --json`` reports *tag*."""
        kanban_exe = self._kanban_root / "kanban-md.exe"
        try:
            result = subprocess.run(  # noqa: S603
                [str(kanban_exe), "show", task_id, "--json"],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(self._kanban_root),
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to read tags for task %s", task_id, exc_info=True)
            return False

        if result.returncode != 0:
            return False

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False

        if not isinstance(payload, dict):
            return False

        raw_tags = payload.get("tags", [])
        if not isinstance(raw_tags, list):
            return False

        tags = {str(item) for item in raw_tags}
        return tag in tags

    async def _run_worker(self, task_id: str) -> None:
        """Write an advisory markdown file under docs/scratch and optionally notify."""
        scratch_dir = self._workspace_root / "docs" / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)

        advisory_path = scratch_dir / f"{task_id}-audit-map.md"
        advisory_path.write_text(self._build_advisory(task_id), encoding="utf-8")

        if self._channel is not None:
            await self._channel.send(
                f"Audit-map advisory generated for task #{task_id}: {advisory_path}"
            )

    @staticmethod
    def _build_advisory(task_id: str) -> str:
        """Build a minimal human-readable advisory artifact."""
        return (
            f"# Audit-Map Advisory - Task #{task_id}\n\n"
            "This advisory worker ran in safe mode.\n\n"
            "- Output is restricted to docs/scratch/.\n"
            "- No kanban mutations were performed.\n"
            "- No source files were modified.\n"
        )
