"""Contract tests for #809 — Eliminate _run() from 27 in-scope test files.

Verifies:
- No local `_run()` helper definition in any in-scope file.
- No `_run(...)` call sites in any in-scope file.
- Each in-scope file has at least one `async def test_` function after
  conversion, and every such async test carries `@pytest.mark.asyncio`
  (or a module-level ``pytestmark``).

``asyncio_mode = strict`` in pyproject.toml enforces the mark at collection
time; these meta-tests catch structural violations at the file level.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

# AC — exhaustive list of the 27 in-scope files
IN_SCOPE_FILES = [
    "tests/test_approval_gate.py",
    "tests/test_ask_user.py",
    "tests/test_browser_safety.py",
    "tests/test_budget_threshold.py",
    "tests/test_command_guard.py",
    "tests/test_content_guard.py",
    "tests/test_context_hook.py",
    "tests/test_daemon.py",
    "tests/test_daemon_coverage_gaps.py",
    "tests/test_delegation.py",
    "tests/test_error_recovery.py",
    "tests/test_error_sanitization_callsites.py",
    "tests/test_hooked_toolset.py",
    "tests/test_hydration_integration.py",
    "tests/test_lessons_hook.py",
    "tests/test_lint_gate.py",
    "tests/test_lint_hook.py",
    "tests/test_loop_detection.py",
    "tests/test_notification_hook.py",
    "tests/test_poll_dedup.py",
    "tests/test_poll_dispatch.py",
    "tests/test_session_hooks.py",
    "tests/test_slack_interactive.py",
    "tests/test_soft_fail_exit.py",
    "tests/test_subagent_hook.py",
    "tests/test_terminal_tools.py",
    "tests/test_test_hook.py",
]

# AC — files explicitly excluded from #809 (other task contexts handle them)
OUT_OF_SCOPE_FILES = [
    "tests/test_conftest_helpers.py",
    "tests/test_daemon_journal_async.py",
    "tests/test_security_audit_log.py",
]


class TestFromAC_RunHelperRemoved:  # noqa: N801
    """AC: In the 27 in-scope files the local _run() helper is removed and no
    _run() call sites remain."""

    @pytest.mark.parametrize("filepath", IN_SCOPE_FILES)
    def test_no_run_helper_definition(self, filepath: str) -> None:
        """Each in-scope file must not define a top-level ``_run()`` helper."""
        content = (ROOT / filepath).read_text(encoding="utf-8")
        assert not re.search(r"^def _run\b", content, re.MULTILINE), (
            f"{filepath} still defines a local _run() helper — remove it"
        )

    @pytest.mark.parametrize("filepath", IN_SCOPE_FILES)
    def test_no_run_call_sites(self, filepath: str) -> None:
        """Each in-scope file must have zero ``_run(...)`` call sites."""
        content = (ROOT / filepath).read_text(encoding="utf-8")
        matches = re.findall(r"\b_run\(", content)
        assert not matches, (
            f"{filepath} still has {len(matches)} _run() call site(s) — "
            "convert each to `await` inside an async def test"
        )


class TestFromAC_AsyncConversion:  # noqa: N801
    """AC: Every test that executed a coroutine via _run() is converted to
    ``async def`` + ``@pytest.mark.asyncio``.  Tests that did not execute
    coroutines remain synchronous."""

    @pytest.mark.parametrize("filepath", IN_SCOPE_FILES)
    def test_async_tests_present_and_marked(self, filepath: str) -> None:
        """Each in-scope file must have zero ``_run(...)`` call sites AND at
        least one ``async def test_`` function (proving that _run() was converted
        rather than simply deleted).  Every async test must also carry
        ``@pytest.mark.asyncio`` or the file must declare ``pytestmark`` at
        module level (required by ``asyncio_mode = strict``).
        """
        content = (ROOT / filepath).read_text(encoding="utf-8")

        # This assertion fails for all 27 files before the builder's work,
        # even for files that already have some async tests.
        run_calls = re.findall(r"\b_run\(", content)
        assert not run_calls, (
            f"{filepath} still has {len(run_calls)} _run() call site(s) — "
            "convert each to `await` inside an async def test"
        )

        async_tests = re.findall(r"^\s*async def (test_\w+)", content, re.MULTILINE)
        assert len(async_tests) >= 1, (
            f"{filepath} has no async def test_ functions — "
            "_run() call sites must be converted to async tests, not simply deleted"
        )

        # Guard: with asyncio_mode=strict every async test needs explicit marking
        has_module_mark = bool(re.search(r"pytestmark\s*=.*asyncio", content))
        if has_module_mark:
            return  # module-level mark covers all async tests in the file

        for m in re.finditer(r"^(\s*)async def (test_\w+)", content, re.MULTILINE):
            pos = m.start()
            preceding = content[max(0, pos - 300) : pos]
            line_no = content[:pos].count("\n") + 1
            assert re.search(r"@pytest\.mark\.asyncio", preceding), (
                f"{filepath}:{line_no} `async def {m.group(2)}` "
                "is missing @pytest.mark.asyncio (asyncio_mode=strict requires it)"
            )
