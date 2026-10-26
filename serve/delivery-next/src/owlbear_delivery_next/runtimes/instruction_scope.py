"""A step reads only its repository's instructions: every source whose file lies outside the worktree is switched off.

The user's ``~/.copilot`` instruction files load even with config discovery off, so they are dropped by where they
live, not by name; a new kind of user source is dropped too (D-01M5X05KTVCSBYA5BZ14XH62N6). The repository's own
files stay on (TD-139).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from copilot.rpc import SessionUpdateOptionsParams

from owlbear_delivery_next.runtimes.sdk_teardown import call as _call


async def own(session: Any, worktree: Path) -> list[str]:  # noqa: ANN401 - the SDK session
    """Switch off the session's instruction sources outside *worktree* before its first message; return their IDs."""
    listed = (await _call(session.rpc.instructions.get_sources(), "instruction sources")).sources
    off = outside(listed, worktree)
    if off:
        update = session.rpc.options.update(SessionUpdateOptionsParams(disabled_instruction_sources=off))
        if not (await _call(update, "instruction scope")).success:
            msg = f"the runtime kept instruction sources outside the worktree on: {', '.join(off)}"
            raise RuntimeError(msg)
    return off


def outside(sources: list[Any], worktree: Path) -> list[str]:
    """The IDs of *sources* whose file, relative to *worktree* unless absolute, lies outside it; no file is outside."""
    root = worktree.resolve()
    return [s.id for s in sources if not s.source_path or not _resolved(s.source_path, root).is_relative_to(root)]


def _resolved(path: str, root: Path) -> Path:
    file = Path(path)
    return (file if file.is_absolute() else root / file).resolve()
