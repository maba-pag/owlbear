"""End-to-end dispatch tests for the ``owlbear dispatch`` CLI.

Task #23: End-to-end dispatch test.

Validates the full owlbear dispatch pipeline::

    owlbear dispatch <id>
    -> planner gates -> AcpClient spawn -> agent execution
    -> kanban state updates -> audit log entries

Requirements:
  - Copilot CLI on PATH (all tests skip otherwise via ``_skip_if_no_copilot``)
  - Live kanban board at ``kanban/``
  - ``owlbear dispatch`` CLI entry point (delivered by tasks #20 + #22)

Run with::

    uv run pytest -m e2e
"""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = pytest.mark.e2e

_PROJECT_ROOT = Path(__file__).parent.parent
_KANBAN_BIN = _PROJECT_ROOT / ".owlbear" / "kanban" / "kanban-md.exe"
_AUDIT_DIR = _PROJECT_ROOT / "store" / "audit"


# ---------------------------------------------------------------------------
# Helpers / skip guards
# ---------------------------------------------------------------------------


def _skip_if_no_copilot() -> None:
    """Skip the calling test if the ``gh`` CLI is not on PATH.

    ``owlbear dispatch`` requires ``gh`` (the GitHub CLI that hosts the
    ``gh copilot`` ACP extension).  Checking for ``copilot`` is insufficient
    because a different binary with that name may exist on PATH.
    """
    if shutil.which("gh") is None:
        pytest.skip("gh CLI not found on PATH — install GitHub CLI to run e2e tests")


def _run_kanban(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a kanban-md command from the project root; return the completed process."""
    return subprocess.run(
        [str(_KANBAN_BIN), *args],
        capture_output=True,
        text=True,
        check=check,
        cwd=str(_PROJECT_ROOT),
    )


def _create_seed_task() -> int:
    """Create an isolation task on the real kanban board; return its integer ID.

    Uses a UUID4 suffix in the title so multiple concurrent runs do not collide.
    """
    title = f"E2E-Test-{uuid.uuid4()}"
    _run_kanban(
        [
            "create",
            title,
            "--status",
            "todo",
            "--tags",
            "e2e-test",
            "--body",
            "Trivial AC for e2e test isolation",
        ]
    )
    # Resolve the integer ID by listing tasks in todo with the e2e-test tag.
    # The UUID4 title guarantees uniqueness even under concurrent test runs.
    result = _run_kanban(["list", "--json", "--tag", "e2e-test", "--status", "todo"])
    tasks: list[dict] = json.loads(result.stdout)
    for task in tasks:
        if task.get("title") == title:
            return int(task["id"])
    msg = f"Could not find seed task with title {title!r} after creation"
    raise RuntimeError(msg)


def _delete_task(task_id: int) -> None:
    """Delete a kanban task; swallow errors so fixture teardown never propagates."""
    with contextlib.suppress(OSError):
        subprocess.run(
            [str(_KANBAN_BIN), "delete", str(task_id), "--yes"],
            capture_output=True,
            cwd=str(_PROJECT_ROOT),
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_task() -> Generator[int, None, None]:
    """Create a test kanban task at ``todo`` status, yield its integer ID, delete on teardown.

    Skips if ``kanban-md`` binary is missing or Copilot CLI is not on PATH.
    Teardown runs even when the test fails.
    """
    if not _KANBAN_BIN.exists():
        pytest.skip("kanban-md binary not found — run kanban/setup.ps1")
    _skip_if_no_copilot()

    task_id = _create_seed_task()
    try:
        yield task_id
    finally:
        _delete_task(task_id)


# ---------------------------------------------------------------------------
# TestFromAC_E2EDispatch
# ---------------------------------------------------------------------------


class TestFromAC_E2EDispatch:
    """E2E validation of the ``owlbear dispatch`` CLI pipeline.

    Each test receives an independent seed task from the ``seed_task`` fixture.
    Tests are excluded from default pytest runs; invoke specifically with::

        uv run pytest -m e2e
    """

    def test_dispatch_exit_zero(self, seed_task: int) -> None:
        """Dispatch completes: ``owlbear dispatch <id>`` exits with code 0."""
        result = subprocess.run(
            ["owlbear", "dispatch", str(seed_task)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_PROJECT_ROOT),
        )
        assert result.returncode == 0, (
            f"owlbear dispatch exited {result.returncode}; expected 0.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_dispatch_stdout_contains_dispatched_string(self, seed_task: int) -> None:
        """Dispatch stdout contains the ``Dispatched #<id> to`` confirmation string."""
        result = subprocess.run(
            ["owlbear", "dispatch", str(seed_task)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_PROJECT_ROOT),
        )
        expected = f"Dispatched #{seed_task} to"
        assert expected in result.stdout, f"Expected {expected!r} in stdout.\nActual stdout: {result.stdout!r}"

    def test_kanban_status_not_todo_after_dispatch(self, seed_task: int) -> None:
        """After dispatch, task status is no longer ``todo`` (agent advanced it)."""
        subprocess.run(
            ["owlbear", "dispatch", str(seed_task)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_PROJECT_ROOT),
            check=True,
        )
        show = _run_kanban(["show", str(seed_task), "--json"])
        task_data = json.loads(show.stdout)
        assert task_data["status"] != "todo", (
            f"Task #{seed_task} status is still 'todo' after dispatch; expected the agent to advance it forward."
        )

    def test_kanban_claimed_by_not_null_after_dispatch(self, seed_task: int) -> None:
        """After dispatch, task ``claimed_by`` is set (agent claimed during execution)."""
        subprocess.run(
            ["owlbear", "dispatch", str(seed_task)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_PROJECT_ROOT),
            check=True,
        )
        show = _run_kanban(["show", str(seed_task), "--json"])
        task_data = json.loads(show.stdout)
        assert task_data.get("claimed_by") is not None, (
            f"Task #{seed_task} claimed_by is null after dispatch; expected agent name."
        )

    def test_audit_log_file_exists_after_dispatch(self, seed_task: int) -> None:
        """At least one ``.jsonl`` file exists under ``data/audit/`` after dispatch."""
        subprocess.run(
            ["owlbear", "dispatch", str(seed_task)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_PROJECT_ROOT),
            check=True,
        )
        jsonl_files = list(_AUDIT_DIR.glob("*.jsonl"))
        assert jsonl_files, f"No .jsonl files found under {_AUDIT_DIR} after dispatch."

    def test_audit_log_contains_dispatch_event_for_seed(self, seed_task: int) -> None:
        """Audit log contains a JSON line with ``type='dispatch'`` and matching ``task_id``."""
        subprocess.run(
            ["owlbear", "dispatch", str(seed_task)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_PROJECT_ROOT),
            check=True,
        )
        found = False
        for jsonl_file in _AUDIT_DIR.glob("*.jsonl"):
            for raw_line in jsonl_file.read_text(encoding="utf-8").splitlines():
                stripped = raw_line.strip()
                if not stripped:
                    continue
                event = json.loads(stripped)
                if event.get("type") == "dispatch" and event.get("task_id") == seed_task:
                    found = True
                    break
            if found:
                break
        assert found, f"No dispatch event with task_id={seed_task} found under {_AUDIT_DIR}."


# ---------------------------------------------------------------------------
# TestFromAC_RepeatableExecution
# ---------------------------------------------------------------------------


class TestFromAC_RepeatableExecution:
    """Two sequential dispatches with distinct seed tasks do not interfere."""

    def test_two_sequential_dispatches_complete_independently(self) -> None:
        """Both dispatches exit 0; each seed task is independently cleaned up."""
        if not _KANBAN_BIN.exists():
            pytest.skip("kanban-md binary not found — run kanban/setup.ps1")
        _skip_if_no_copilot()

        task_a = _create_seed_task()
        task_b = _create_seed_task()
        try:
            result_a = subprocess.run(
                ["owlbear", "dispatch", str(task_a)],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(_PROJECT_ROOT),
            )
            result_b = subprocess.run(
                ["owlbear", "dispatch", str(task_b)],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(_PROJECT_ROOT),
            )
            assert result_a.returncode == 0, (
                f"First dispatch (#{task_a}) failed.\nstdout: {result_a.stdout}\nstderr: {result_a.stderr}"
            )
            assert result_b.returncode == 0, (
                f"Second dispatch (#{task_b}) failed.\nstdout: {result_b.stdout}\nstderr: {result_b.stderr}"
            )
        finally:
            _delete_task(task_a)
            _delete_task(task_b)
