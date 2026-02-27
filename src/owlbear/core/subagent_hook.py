"""Subagent-complete verification hook for OwlBear.

Provides :class:`SubagentVerificationHook` — a ``SUBAGENT_COMPLETE`` hook
that inspects subagent result payloads, verifying that created files exist
and that tests pass (when applicable).  Failures are logged as warnings
but never raise — the hook is purely observational.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

_DEFAULT_PYTEST_CMD: list[str] = ["uv", "run", "pytest"]


class SubagentVerificationHook:
    """``SUBAGENT_COMPLETE`` hook that verifies subagent deliverables.

    After a subagent reports completion, this hook checks:

    1. **File existence** — every path in ``created_files`` must exist.
    2. **Test execution** — if ``test_files`` are provided, run pytest on them.

    Results are stored on the data dict under ``data["verification"]`` with
    keys ``files_ok``, ``tests_ok``, and ``details``.

    **Error isolation:** all failures are caught, logged, and stored — the
    hook never raises exceptions.

    Args:
        pytest_cmd: Command prefix for running pytest.
            Defaults to ``["uv", "run", "pytest"]``.
    """

    def __init__(self, pytest_cmd: list[str] | None = None) -> None:
        self._pytest_cmd = pytest_cmd or list(_DEFAULT_PYTEST_CMD)

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: object) -> None:
        """Inspect a ``SUBAGENT_COMPLETE`` payload and verify deliverables.

        Args:
            data: Event payload — expected to be a dict with ``task_id``,
                ``created_files``, ``test_files``, and ``result`` keys.
                Non-dict payloads are silently ignored.
        """
        if not isinstance(data, dict):
            return

        created_files: list[str] = data.get("created_files", [])
        test_files: list[str] = data.get("test_files", [])

        if not isinstance(created_files, list):
            created_files = []
        if not isinstance(test_files, list):
            test_files = []

        details_parts: list[str] = []

        files_ok = self._check_files(created_files, details_parts)
        tests_ok = self._check_tests(test_files, details_parts)

        data["verification"] = {
            "files_ok": files_ok,
            "tests_ok": tests_ok,
            "details": "; ".join(details_parts) if details_parts else "all checks passed",
        }

        if not files_ok or not tests_ok:
            logger.warning(
                "Subagent verification failed for task %s: %s",
                data.get("task_id", "?"),
                data["verification"]["details"],
            )

    # -- convenience ---------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on :pyattr:`HookEvent.SUBAGENT_COMPLETE`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.SUBAGENT_COMPLETE, self)

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _check_files(
        created_files: list[str],
        details: list[str],
    ) -> bool:
        """Return *True* if every path in *created_files* exists."""
        if not created_files:
            return True

        missing: list[str] = []
        for file_path in created_files:
            try:
                if not Path(file_path).exists():
                    missing.append(file_path)
            except Exception:
                logger.exception("Error checking file %s", file_path)
                missing.append(file_path)

        if missing:
            details.append(f"missing files: {', '.join(missing)}")
            return False
        return True

    def _check_tests(
        self,
        test_files: list[str],
        details: list[str],
    ) -> bool:
        """Return *True* if pytest passes on *test_files*."""
        if not test_files:
            return True

        cmd = [*self._pytest_cmd, *test_files]
        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            logger.exception("Test execution failed for %s", test_files)
            details.append(f"test execution error for: {', '.join(test_files)}")
            return False

        if result.returncode != 0:
            output = result.stdout.strip() or result.stderr.strip()
            details.append(f"tests failed: {output}")
            return False
        return True
