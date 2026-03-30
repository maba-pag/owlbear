"""Async board reader — wraps kanban-md list --json."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from owlbear.errors import OwlBearError

if TYPE_CHECKING:
    from pathlib import Path
from owlbear.planner.models import Task, task_list_adapter


class BoardReadError(OwlBearError):
    """Raised when kanban-md exits with a non-zero return code."""


async def read_board(
    kanban_bin: Path,
    kanban_dir: Path,
    *,
    scope: str | None = None,
) -> list[Task]:
    """Read the kanban board and return a list of matching tasks.

    Args:
        kanban_bin: Path to the kanban-md binary.
        kanban_dir: Path to the kanban directory (passed via --dir).
        scope: Optional tag filter; when provided, appends --tag {scope}.

    Returns:
        Parsed list of Task objects (empty list when no tasks match).

    Raises:
        BoardReadError: When kanban-md exits with a non-zero return code.
        FileNotFoundError: When the kanban-md binary is not found (propagates naturally).
    """
    args = [
        str(kanban_bin),
        "list",
        "--json",
        "--unblocked",
        "--not-blocked",
        "--unclaimed",
        "--no-color",
        "--dir",
        str(kanban_dir),
    ]
    if scope is not None:
        args += ["--tag", scope]

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()

    if proc.returncode != 0:
        stderr_text = stderr_bytes.decode(errors="replace")
        raise BoardReadError(stderr_text)

    return task_list_adapter.validate_json(stdout_bytes)
