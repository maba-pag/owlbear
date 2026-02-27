"""Post-tool-use auto-lint hook for Python files.

Provides :class:`AutoLintHook` — a ``POST_TOOL_USE`` hook that runs
``ruff check --fix`` on Python files touched by tool-call operations.
Lint failures are logged but never block the agent pipeline.
"""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)


class AutoLintHook:
    """``POST_TOOL_USE`` hook that auto-lints edited Python files.

    After a tool call completes, the hook inspects the event payload for
    file paths ending in ``.py``.  When found, it runs
    ``uv run ruff check --fix <path>`` in a subprocess.

    **Error isolation:** subprocess failures (missing binary, non-zero exit)
    are logged and swallowed — they never propagate to the agent.
    """

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: object) -> None:
        """Inspect a ``POST_TOOL_USE`` payload and lint any ``.py`` file.

        Args:
            data: Event payload — expected ``{"tool_name": str, "args": dict, ...}``.
                Non-dict payloads are silently ignored.
        """
        if not isinstance(data, dict):
            return

        args = data.get("args")
        if not isinstance(args, dict):
            return

        file_path = self._extract_py_path(args)
        if file_path is None:
            return

        self._run_ruff(file_path)

    # -- convenience ---------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on :pyattr:`HookEvent.POST_TOOL_USE`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.POST_TOOL_USE, self)

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _extract_py_path(args: dict[str, object]) -> str | None:
        """Return the first ``.py`` file path found in *args* values."""
        for value in args.values():
            if isinstance(value, str) and value.endswith(".py"):
                return value
        return None

    @staticmethod
    def _run_ruff(file_path: str) -> None:
        """Run ``ruff check --fix`` on *file_path*, logging the result."""
        cmd = ["uv", "run", "ruff", "check", "--fix", file_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
        except Exception:
            logger.exception("Auto-lint failed for %s", file_path)
            return

        if result.returncode == 0:
            logger.debug("Auto-lint clean: %s", file_path)
        else:
            logger.warning(
                "Auto-lint issues in %s: %s",
                file_path,
                result.stdout.strip() or result.stderr.strip(),
            )
