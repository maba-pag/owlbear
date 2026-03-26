"""Tests for owlbear.paths — sandbox_path utility."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.paths import sandbox_path


class TestSandboxPath:
    """sandbox_path confines user-supplied paths to a workspace root."""

    def test_traversal_escape_raises(self, tmp_path: Path) -> None:
        """../escape resolves outside root and is rejected."""
        with pytest.raises(PermissionError, match="Path outside workspace"):
            sandbox_path(tmp_path, "../escape")

    def test_absolute_outside_raises(self, tmp_path: Path) -> None:
        """/etc/passwd is outside root and is rejected."""
        with pytest.raises(PermissionError, match="Path outside workspace"):
            sandbox_path(tmp_path, "/etc/passwd")

    def test_null_byte_raises(self, tmp_path: Path) -> None:
        """Null bytes in path are rejected early."""
        with pytest.raises(PermissionError, match="Path outside workspace"):
            sandbox_path(tmp_path, "file\x00.txt")

    def test_valid_relative_resolves(self, tmp_path: Path) -> None:
        """A valid relative path resolves inside root."""
        result = sandbox_path(tmp_path, "sub/file.txt")
        assert result == tmp_path / "sub" / "file.txt"
        assert result.is_absolute()

    def test_dot_resolves_to_root(self, tmp_path: Path) -> None:
        """'.' resolves to the root itself."""
        result = sandbox_path(tmp_path, ".")
        assert result == tmp_path

    def test_accepts_path_object(self, tmp_path: Path) -> None:
        """user_path can be a Path, not just str."""
        result = sandbox_path(tmp_path, Path("sub/file.txt"))
        assert result == tmp_path / "sub" / "file.txt"

    def test_absolute_inside_root_ok(self, tmp_path: Path) -> None:
        """An absolute path that stays within root is accepted."""
        inner = tmp_path / "sub" / "file.txt"
        result = sandbox_path(tmp_path, str(inner))
        assert result == inner

    def test_leaf_module_no_heavy_imports(self) -> None:
        """Module must not import from owlbear.core, .tools, .memory, .agents."""
        import ast
        import importlib
        import inspect

        src = inspect.getsource(importlib.import_module("owlbear.paths"))
        tree = ast.parse(src)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        for forbidden in ("owlbear.core", "owlbear.tools", "owlbear.memory", "owlbear.agents"):
            for mod in imported:
                assert not mod.startswith(forbidden), f"Leaf module must not import {forbidden}"
