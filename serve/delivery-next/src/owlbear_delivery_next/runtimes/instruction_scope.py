"""A step reads its repository's instructions and, when the owner switches them on, his own instruction files.

The user's ``~/.copilot`` instruction files load even with config discovery off, so every source whose file lies
outside the worktree is switched off by where it lives, not by name; a new kind of user source is dropped too
(D-01M5YE55W7P4A6PS8YZV8K7J6A). The repository's own files stay on (TD-139).

With "load user instructions" on (D-01M5YE4TRV2T08TW0FA2FGSDBK), a source outside the worktree stays on only when the
runtime places it as the user's and its file, links followed, is one of his: an entry of ``<home>/instructions/`` or
``<home>/copilot-instructions.md``. A plugin's file, or anything else the runtime reports, stays off even then.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copilot.rpc import InstructionLocation, SessionUpdateOptionsParams

from owlbear_delivery_next.runtimes.sdk_teardown import call as _call


@dataclass(frozen=True)
class Scope:
    """What a session's instruction scope did: the source IDs it switched off and the user's it kept on."""

    off: list[str]
    user: list[str]


async def own(
    session: Any,  # noqa: ANN401 - the SDK session
    worktree: Path,
    *,
    user_instructions: bool = False,
    home: Path | None = None,
) -> Scope:
    """Switch off the session's instruction sources outside *worktree* before its first message.

    With *user_instructions*, the user's own files under *home* stay on (``admitted``).

    Raises:
        RuntimeError: The runtime refused to switch them off; the step ends before any message.
    """
    listed = (await _call(session.rpc.instructions.get_sources(), "instruction sources")).sources
    allowed = user_files(home) if user_instructions and home is not None else set()
    out = outside(listed, worktree)
    user = [s.id for s in listed if s.id in out and admitted(s, allowed)]
    off = [i for i in out if i not in user]
    if off:
        update = session.rpc.options.update(SessionUpdateOptionsParams(disabled_instruction_sources=off))
        if not (await _call(update, "instruction scope")).success:
            msg = f"the runtime kept instruction sources outside the worktree on: {', '.join(off)}"
            raise RuntimeError(msg)
    return Scope(off=off, user=user)


def outside(sources: list[Any], worktree: Path) -> list[str]:
    """The IDs of *sources* whose file, relative to *worktree* unless absolute, lies outside it; no file is outside."""
    root = worktree.resolve()
    return [s.id for s in sources if not s.source_path or not _resolved(s.source_path, root).is_relative_to(root)]


def user_files(home: Path) -> set[Path]:
    """The user's instruction files, links followed: each entry of ``<home>/instructions/`` and the root file.

    A missing home or folder has none; a link to nothing names no file.
    """
    folder, root = home / "instructions", home / "copilot-instructions.md"
    try:
        entries = list(folder.iterdir())
    except OSError:
        entries = []
    return {p.resolve() for p in (*entries, root) if p.exists()}


def admitted(source: Any, allowed: set[Path]) -> bool:  # noqa: ANN401 - the SDK's instruction source
    """Whether *source* is one of the user's files: placed as the user's by the runtime, and its file in *allowed*."""
    if getattr(source, "location", None) != InstructionLocation.USER or not source.source_path:
        return False
    file = Path(source.source_path)
    return file.is_absolute() and file.resolve() in allowed


def _resolved(path: str, root: Path) -> Path:
    file = Path(path)
    return (file if file.is_absolute() else root / file).resolve()
