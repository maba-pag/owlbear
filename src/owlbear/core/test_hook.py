"""Session-end test verification hook.

Provides :class:`TestVerificationHook` — a ``SESSION_END`` hook that runs
the project test suite via ``pytest`` and reports results.  Test failures
are logged as warnings but never block the session from ending.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)


class TestResult(TypedDict):
    """Structured result from a test verification run."""

    passed: int
    failed: int
    output: str


_DEFAULT_PYTEST_CMD: list[str] = [
    "uv",
    "run",
    "pytest",
    "tests/",
    "-m",
    "not api",
    "--tb=short",
    "-q",
]
_DEFAULT_TIMEOUT: int = 120

# Regex to extract passed/failed counts from pytest summary line.
# Examples: "42 passed in 3.21s", "3 failed, 39 passed in 4.56s", "5 failed"
_PASSED_RE = re.compile(r"(\d+)\s+passed")
_FAILED_RE = re.compile(r"(\d+)\s+failed")


class TestVerificationHook:
    """``SESSION_END`` hook that runs the test suite and reports results.

    After a session ends, the hook invokes ``pytest`` in a subprocess,
    parses the summary output, and stores the results on the event payload
    dict under ``data["test_results"]``.

    **Error isolation:** subprocess failures, timeouts, and test failures
    are logged as warnings — they never propagate to the caller.

    Args:
        pytest_cmd: Command list to run (default: ``uv run pytest …``).
        timeout: Subprocess timeout in seconds (default: 120).
    """

    __test__ = False  # prevent pytest collection

    def __init__(
        self,
        pytest_cmd: list[str] | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._cmd = pytest_cmd if pytest_cmd is not None else list(_DEFAULT_PYTEST_CMD)
        self._timeout = timeout

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: object) -> None:
        """Run the test suite and store results on *data*.

        Args:
            data: Event payload — expected ``{"session_id": str, ...}``.
                Non-dict payloads are silently ignored.
        """
        if not isinstance(data, dict):
            return

        results = self._run_tests()
        data["test_results"] = results

        if results["failed"] > 0:
            logger.warning(
                "Test verification: %d failed, %d passed — %s",
                results["failed"],
                results["passed"],
                results["output"],
            )

    # -- convenience ---------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on :pyattr:`HookEvent.SESSION_END`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.SESSION_END, self)

    # -- internal ------------------------------------------------------------

    def _run_tests(self) -> TestResult:
        """Execute the pytest subprocess and parse results."""
        try:
            result = subprocess.run(  # noqa: S603
                self._cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Test verification timeout after %ds", self._timeout)
            return {"passed": 0, "failed": 0, "output": "Timeout: tests did not complete"}
        except OSError:
            logger.warning("Test verification error", exc_info=True)
            return {"passed": 0, "failed": 0, "output": "Error: failed to run tests"}

        output = result.stdout.strip()
        passed = self._parse_count(_PASSED_RE, output)
        failed = self._parse_count(_FAILED_RE, output)

        return {"passed": passed, "failed": failed, "output": output}

    @staticmethod
    def _parse_count(pattern: re.Pattern[str], text: str) -> int:
        """Extract an integer count from *text* using *pattern*, or 0."""
        match = pattern.search(text)
        return int(match.group(1)) if match else 0
