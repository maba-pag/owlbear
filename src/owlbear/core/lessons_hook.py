"""SESSION_START hook that injects lessons context from markdown files.

Reads ``.md`` files from a lessons directory, sorted newest-first by
modification time, concatenating their contents within a token budget.
The result is stored as ``data["lessons"]``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

_DEFAULT_LESSONS_DIR = Path(".owlbear/lessons")
_DEFAULT_MAX_TOKENS = 500


class LessonsInjectionHook:
    """``SESSION_START`` hook that enriches the payload with lessons content.

    On invocation the hook:

    1. Globs ``*.md`` files from *lessons_dir*.
    2. Sorts them by modification time (newest first).
    3. Concatenates file contents until the token budget is exhausted.
    4. Stores the result under ``data["lessons"]``.

    Token estimation uses ``len(text) // 4``.  When a file would exceed the
    remaining budget, it is truncated at the last newline that fits.

    Args:
        lessons_dir: Directory containing lesson ``.md`` files.
            Defaults to ``.owlbear/lessons``.
        max_tokens: Maximum token budget for the concatenated text.
            Defaults to ``500``.
    """

    def __init__(
        self,
        lessons_dir: Path | None = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.lessons_dir: Path = lessons_dir if lessons_dir is not None else _DEFAULT_LESSONS_DIR
        self.max_tokens: int = max_tokens

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: dict[str, Any]) -> None:
        """Read lessons files and inject concatenated text into *data*."""
        data["lessons"] = self._collect_lessons()

    # -- convenience ---------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on :pyattr:`HookEvent.SESSION_START`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.SESSION_START, self)

    # -- internal ------------------------------------------------------------

    def _sorted_md_files(self) -> list[Path]:
        """Return .md files from lessons_dir sorted by mtime descending."""
        if not self.lessons_dir.is_dir():
            return []
        try:
            return sorted(
                self.lessons_dir.glob("*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError as exc:
            logger.warning("Failed to list/sort lessons in %s: %s", self.lessons_dir, exc)
            return []

    def _collect_lessons(self) -> str:
        """Read and concatenate lesson files within the token budget."""
        md_files = self._sorted_md_files()
        if not md_files:
            return ""

        budget_chars = self.max_tokens * 4
        parts: list[str] = []
        used = 0

        for path in md_files:
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Could not read lesson file %s: %s", path, exc)
                continue
            remaining = budget_chars - used

            if remaining <= 0:
                break

            if len(content) <= remaining:
                parts.append(content)
                used += len(content)
            else:
                # Truncate at newline boundary
                truncated = content[:remaining]
                last_nl = truncated.rfind("\n")
                if last_nl > 0:
                    truncated = truncated[:last_nl]
                elif last_nl == 0:
                    truncated = ""
                else:
                    # No newline found — take nothing from this file
                    truncated = ""
                if truncated:
                    parts.append(truncated)
                    used += len(truncated)
                break

        return "\n".join(parts) if len(parts) > 1 else (parts[0] if parts else "")
