r"""E2E smoke test script for real Copilot CLI dispatch.

Purpose
-------
Validates the full owlbear stack with a real invocation of ``owlbear dispatch``.
Creates a temporary kanban task, dispatches it, verifies the board state advanced
past ``todo``, and cleans up.  This is a *manual* smoke test — run it when you
want evidence that the live Copilot CLI integration is working end-to-end.

Prerequisites
-------------
1. ``gh`` CLI on PATH (GitHub CLI)
2. ``gh copilot --help`` exits 0 — Copilot extension installed
3. ``.owlbear/kanban/kanban-md.exe`` exists — kanban-md binary available
4. ``owlbear`` on PATH — owlbear CLI installed in environment

Invocation
----------
    python .owlbear/scripts/e2e_smoke.py [timeout_seconds]

Timeout defaults to 300 seconds but can be overridden via the ``E2E_TIMEOUT``
environment variable (takes precedence) or a positional argument.

Exit codes
----------
    0 — PASS
    1 — FAIL (dispatch ran but task state wrong, or dispatch error)
    2 — prerequisite error

Known Limitations
-----------------
- Process tree: timeout kills ``owlbear dispatch`` but the grandchild Copilot
  CLI process may survive (orphaned).  Kill it manually if needed.
- Orphan recovery: if cleanup fails after a crash, find orphaned tasks via::

      kanban\\kanban-md.exe list --tag e2e-smoke
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_KANBAN_BIN = _PROJECT_ROOT / ".owlbear" / "kanban" / "kanban-md.exe"
_DEFAULT_TIMEOUT = 300


def _print_err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _check_prerequisites() -> None:
    """Check all prerequisites; print descriptive message to stderr and exit 2 on failure."""
    if shutil.which("gh") is None:
        _print_err("PREREQUISITE FAILED: 'gh' CLI not found on PATH.")
        _print_err("  Install GitHub CLI: https://cli.github.com/")
        sys.exit(2)

    result = subprocess.run(
        ["gh", "copilot", "--help"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _print_err("PREREQUISITE FAILED: 'gh copilot --help' exited non-zero.")
        _print_err("  Install: gh extension install github/gh-copilot")
        sys.exit(2)

    if not _KANBAN_BIN.exists():
        _print_err(f"PREREQUISITE FAILED: kanban-md binary not found at {_KANBAN_BIN}")
        _print_err("  Run .owlbear/kanban/setup.ps1 to download it.")
        sys.exit(2)

    if shutil.which("owlbear") is None:
        _print_err("PREREQUISITE FAILED: 'owlbear' CLI not found on PATH.")
        _print_err("  Install owlbear in your environment: uv sync")
        sys.exit(2)


def _run_kanban(
    args: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(_KANBAN_BIN), *args],
        capture_output=True,
        text=True,
        check=check,
        cwd=str(_PROJECT_ROOT),
    )


def _create_task(title: str) -> int:
    """Create temp task on the board; return its integer ID."""
    _run_kanban(
        [
            "create",
            title,
            "--status",
            "todo",
            "--tags",
            "e2e-smoke",
            "--body",
            "Temp task for E2E smoke test — safe to delete.",
        ]
    )
    result = _run_kanban(["list", "--json", "--tag", "e2e-smoke", "--status", "todo"])
    tasks: list[dict] = json.loads(result.stdout)
    # Match both tag (already filtered) AND UUID title substring for uniqueness
    for task in tasks:
        if title in task.get("title", ""):
            return int(task["id"])
    msg = f"Could not resolve task ID for title {title!r}"
    raise RuntimeError(msg)


def _get_task_info(task_id: int) -> dict:
    """Return parsed JSON from kanban-md show --json for task_id."""
    result = _run_kanban(["show", str(task_id), "--json"], check=False)
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def _cleanup(task_id: int | None, task_file: str | None) -> None:
    """Delete the temp task from the board and remove its file; swallow all errors."""
    if task_id is None:
        return
    with contextlib.suppress(OSError):
        _run_kanban(["delete", str(task_id), "--yes"], check=False)
    if task_file:
        with contextlib.suppress(OSError):
            Path(task_file).unlink()


def _resolve_timeout() -> int:
    """Return timeout in seconds: E2E_TIMEOUT env var takes precedence, then argv, then default."""
    env_val = os.environ.get("E2E_TIMEOUT")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except ValueError:
            pass
    return _DEFAULT_TIMEOUT


def main() -> None:
    _check_prerequisites()

    timeout = _resolve_timeout()
    title = f"E2E-smoke-{uuid.uuid4()}"
    task_id: int | None = None
    task_file: str | None = None

    try:
        task_id = _create_task(title)
        task_info = _get_task_info(task_id)
        task_file = task_info.get("file")

        dispatch_result = subprocess.run(  # noqa: S603
            ["owlbear", "dispatch", str(task_id)],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(_PROJECT_ROOT),
        )

        final_info = _get_task_info(task_id)
        final_status = final_info.get("status")

        if final_status != "todo":
            print(f"PASS — task #{task_id}, final status: {final_status!r}")
            sys.exit(0)
        else:
            print(f"FAIL — task #{task_id}, status still 'todo' after dispatch")
            print(f"--- dispatch stdout ---\n{dispatch_result.stdout}")
            print(f"--- dispatch stderr ---\n{dispatch_result.stderr}")
            sys.exit(1)

    except subprocess.TimeoutExpired as exc:
        captured_stdout = exc.stdout if exc.stdout is not None else ""
        captured_stderr = exc.stderr if exc.stderr is not None else ""
        print(f"FAIL — task #{task_id}, dispatch timed out after {timeout}s")
        print(f"--- dispatch stdout ---\n{captured_stdout}")
        print(f"--- dispatch stderr ---\n{captured_stderr}")
        sys.exit(1)

    finally:
        _cleanup(task_id, task_file)


if __name__ == "__main__":
    main()
