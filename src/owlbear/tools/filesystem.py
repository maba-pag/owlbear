"""FileToolset — FunctionToolset wrapping 5 sync filesystem tools.

Provides ``read_file``, ``write_file``, ``create_file``, ``list_directory``,
and ``search_files`` — all sandboxed to a ``workspace_root`` via a path
traversal guard.

Usage::

    from owlbear.tools.filesystem import FileToolset
    toolset = FileToolset(workspace_root=Path("."))
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["FileToolset"]

logger = logging.getLogger(__name__)

_MAX_SEARCH_RESULTS = 100


class FileToolset(FunctionToolset):
    """FunctionToolset subclass exposing 5 filesystem tools.

    All paths are sandboxed to *workspace_root* via :meth:`_safe_path`.
    Tools are sync — PydanticAI wraps them in an executor automatically.

    Args:
        workspace_root: Root directory for all file operations.
            Must be an existing directory.  Stored resolved (absolute).
    """

    def __init__(self, workspace_root: Path) -> None:
        super().__init__()
        self._root = workspace_root.resolve()
        self._register_tools()

    # ------------------------------------------------------------------
    # Path traversal guard
    # ------------------------------------------------------------------

    def _safe_path(self, user_path: str) -> Path:
        """Resolve *user_path* against workspace root with traversal guard.

        Returns the resolved absolute ``Path``.

        Raises:
            PermissionError: If the resolved path escapes the workspace.
        """
        # Reject null bytes early (some OSes silently truncate).
        if "\x00" in user_path:
            msg = f"Path outside workspace: {user_path!r}"
            raise PermissionError(msg)

        resolved = (self._root / user_path).resolve()
        if not resolved.is_relative_to(self._root):
            msg = f"Path outside workspace: {user_path}"
            raise PermissionError(msg)
        return resolved

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all 5 filesystem tools on this toolset."""
        self.add_function(
            self._read_file,
            name="read_file",
            description="Read file content. Lines are 1-indexed inclusive.",
        )
        self.add_function(
            self._write_file,
            name="write_file",
            description=(
                "Write content to a file. Creates parent directories. "
                "Overwrites if the file exists."
            ),
        )
        self.add_function(
            self._create_file,
            name="create_file",
            description=("Create a new file with content. Fails if the file already exists."),
        )
        self.add_function(
            self._list_directory,
            name="list_directory",
            description=(
                "List directory entries sorted alphabetically. Directories have a trailing /."
            ),
        )
        self.add_function(
            self._search_files,
            name="search_files",
            description=(
                "Search for files by glob pattern, optionally filtering "
                "by content regex. Returns relative paths (max 100)."
            ),
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        """Read file content with optional line range.

        Args:
            path: Relative path within the workspace.
            start_line: First line to read (1-indexed, inclusive).
            end_line: Last line to read (1-indexed, inclusive).

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the path escapes the workspace.
        """
        target = self._safe_path(path)
        if not target.is_file():
            msg = f"File not found: {path}"
            raise FileNotFoundError(msg)

        text = target.read_text(encoding="utf-8")

        if start_line is None and end_line is None:
            return text

        lines = text.splitlines(keepends=True)
        # Convert to 0-indexed
        start = (start_line - 1) if start_line is not None else 0
        end = end_line if end_line is not None else len(lines)
        return "".join(lines[start:end])

    def _write_file(self, path: str, content: str) -> str:
        """Write content to a file, creating parent directories.

        Overwrites if the file already exists.

        Raises:
            PermissionError: If the path escapes the workspace.
        """
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {path}"

    def _create_file(self, path: str, content: str) -> str:
        """Create a new file. Fails if it already exists.

        Raises:
            FileExistsError: If the file already exists.
            PermissionError: If the path escapes the workspace.
        """
        target = self._safe_path(path)
        if target.exists():
            msg = f"File already exists: {path}"
            raise FileExistsError(msg)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Created {path}"

    def _list_directory(self, path: str) -> str:
        """List directory entries, sorted, with ``/`` suffix for dirs.

        Raises:
            FileNotFoundError: If the directory does not exist.
            PermissionError: If the path escapes the workspace.
        """
        target = self._safe_path(path)
        if not target.is_dir():
            msg = f"Directory not found: {path}"
            raise FileNotFoundError(msg)

        entries: list[str] = []
        for child in sorted(target.iterdir(), key=lambda p: p.name):
            name = child.name + ("/" if child.is_dir() else "")
            entries.append(name)
        return "\n".join(entries)

    def _search_files(
        self,
        glob_pattern: str,
        content_regex: str | None = None,
    ) -> str:
        """Search for files by glob, optionally filtering by content regex.

        Returns newline-separated relative paths (max 100 results).

        Args:
            glob_pattern: Glob pattern relative to workspace root.
            content_regex: Optional regex to match against file content.
        """
        matches: list[str] = []
        compiled = re.compile(content_regex) if content_regex else None

        for hit in sorted(self._root.glob(glob_pattern)):
            if not hit.is_file():
                continue
            # Ensure hit is within workspace (glob shouldn't escape, but guard)
            if not hit.resolve().is_relative_to(self._root):
                continue
            if compiled is not None:
                try:
                    text = hit.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if not compiled.search(text):
                    continue
            rel = hit.relative_to(self._root)
            matches.append(str(rel).replace("\\", "/"))
            if len(matches) > _MAX_SEARCH_RESULTS:
                break

        if len(matches) > _MAX_SEARCH_RESULTS:
            truncated = matches[:_MAX_SEARCH_RESULTS]
            total = _MAX_SEARCH_RESULTS
            return "\n".join(truncated) + f"\n[truncated — showing {total} of {total}+ results]"

        return "\n".join(matches)
