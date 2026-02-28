"""Workspace context loader for PydanticAI agent instructions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_DEFAULT_FILENAME = "context.md"


class ContextManager:
    """Load a static context file and expose it as PydanticAI instructions.

    The context file (default ``context.md``) lives at the workspace root and
    contains persistent instructions that every agent run should receive.

    Usage::

        mgr = ContextManager(Path("/project"))
        agent = Agent("model", instructions=mgr.instructions)
    """

    def __init__(self, root: Path, *, filename: str = _DEFAULT_FILENAME) -> None:
        self._root = root
        self._path = root / filename

    @property
    def path(self) -> Path:
        """Absolute path to the context file."""
        return self._path

    def exists(self) -> bool:
        """Whether the context file is present on disk."""
        return self._path.exists()

    def load(self) -> str | None:
        """Read the context file.

        Returns ``None`` when the file is missing or contains only whitespace.
        """
        if not self._path.exists():
            return None
        text = self._path.read_text(encoding="utf-8").strip()
        return text or None

    @property
    def instructions(self) -> str:
        """Context content formatted for ``Agent(instructions=...)``.

        Combines the static context file with MEMORY.md (if present).
        Returns an empty string when neither file is available, so it is
        always safe to pass directly to PydanticAI.
        """
        parts: list[str] = []
        context = self.load()
        if context:
            parts.append(context)
        memory_path = self._root / "MEMORY.md"
        if memory_path.exists():
            memory = memory_path.read_text(encoding="utf-8").strip()
            if memory:
                parts.append(memory)
        return "\n\n".join(parts)
