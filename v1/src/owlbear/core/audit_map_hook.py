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
_AC_HEADING = "## Acceptance Criteria"


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

        safe_task_id = self._safe_task_id(task_id)
        advisory_path = scratch_dir / f"{safe_task_id}-audit-map.md"
        advisory_path.write_text(self._build_advisory(task_id=task_id), encoding="utf-8")

        if self._channel is not None:
            await self._channel.send(
                f"Audit-map advisory generated for task #{task_id}: {advisory_path}"
            )

    def _build_advisory(self, *, task_id: str) -> str:
        """Build a template-based advisory artifact from kanban task metadata."""
        title = "(unknown title)"
        status = "unknown"
        tags: list[str] = []
        acceptance_criteria: list[str] = []

        task_file = self._resolve_task_file(task_id)
        if task_file is not None:
            try:
                raw = task_file.read_text(encoding="utf-8")
                frontmatter, body = self._split_frontmatter_and_body(raw)
                title, status, tags = self._parse_frontmatter(frontmatter)
                acceptance_criteria = self._extract_acceptance_criteria(body)
            except OSError:
                logger.warning(
                    "Failed to read task metadata for advisory task %s",
                    task_id,
                    exc_info=True,
                )

        lines = [
            f"# Audit-Map Advisory - Task #{task_id}",
            "",
            "## Task Metadata",
            f"- Title: {title}",
            f"- Status: {status}",
            f"- Tags: {', '.join(tags) if tags else '(none)'}",
            "",
            "## Acceptance Criteria",
        ]

        if acceptance_criteria:
            lines.extend(acceptance_criteria)
        else:
            lines.append("- (Acceptance Criteria section not found in task file)")

        lines.extend(
            [
                "",
                "## Safety Notes",
                "- Output is restricted to docs/scratch/.",
                "- No kanban mutations were performed.",
                "- No source files were modified.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _resolve_task_file(self, task_id: str) -> Path | None:
        """Locate the markdown task file for *task_id* under kanban/tasks/."""
        tasks_dir = self._kanban_root / "tasks"
        if not tasks_dir.is_dir():
            return None
        safe_task_id = self._safe_task_id(task_id)
        matches = sorted(tasks_dir.glob(f"{safe_task_id}-*.md"))
        return matches[0] if matches else None

    @staticmethod
    def _split_frontmatter_and_body(markdown: str) -> tuple[list[str], list[str]]:
        """Split markdown into frontmatter lines and body lines."""
        lines = markdown.splitlines()
        if not lines or lines[0].strip() != "---":
            return [], lines

        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return lines[1:index], lines[index + 1 :]

        return [], lines

    @staticmethod
    def _parse_frontmatter(lines: list[str]) -> tuple[str, str, list[str]]:
        """Parse title, status, and tags from task frontmatter lines."""
        title = "(unknown title)"
        status = "unknown"
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("title:"):
                value = stripped.split(":", maxsplit=1)[1].strip()
                if value:
                    title = value
            elif stripped.startswith("status:"):
                value = stripped.split(":", maxsplit=1)[1].strip()
                if value:
                    status = value

        return title, status, AuditMapAdvisoryHook._collect_frontmatter_tags(lines)

    @staticmethod
    def _collect_frontmatter_tags(lines: list[str]) -> list[str]:
        """Collect list-style tags from frontmatter lines."""
        tags: list[str] = []
        in_tags = False

        for line in lines:
            stripped = line.strip()

            if stripped == "tags:":
                in_tags = True
                continue

            if not in_tags:
                continue

            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if value:
                    tags.append(value)
                continue

            if stripped == "" or line.startswith((" ", "\t")):
                continue

            break

        return tags

    @staticmethod
    def _extract_acceptance_criteria(lines: list[str]) -> list[str]:
        """Extract the acceptance-criteria section lines from task markdown body."""
        collecting = False
        criteria: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not collecting:
                if stripped == _AC_HEADING:
                    collecting = True
                continue

            if line.startswith("## "):
                break

            if stripped:
                criteria.append(line.rstrip())

        return criteria

    @staticmethod
    def _safe_task_id(task_id: str) -> str:
        """Convert task IDs into a single safe filename segment."""
        leaf = task_id.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
        safe = "".join(ch for ch in leaf if ch.isalnum() or ch in {"-", "_"})
        return safe or "task"
