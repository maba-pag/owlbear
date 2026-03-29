"""Tests for #17/#99: build_tree helper in tree.py — TDD RED phase.

All tests fail in RED phase — ImportError expected until builder implements tree.py.
Related tasks: #17 (builder), #99 (test task).
"""

from __future__ import annotations

import inspect
from pathlib import Path

from owlbear_mcp_project.tree import build_tree  # type: ignore[import]


# ---------------------------------------------------------------------------
# TestFromAC_BuildTree
# ---------------------------------------------------------------------------


class TestFromAC_BuildTree:
    """AC: build_tree(root, max_depth=3, exclude=None) in tree.py; returns indented text tree."""

    def test_returns_string(self, tmp_path: Path) -> None:
        """build_tree returns a str for any directory."""
        result = build_tree(tmp_path)
        assert isinstance(result, str)

    def test_includes_file_names_in_output(self, tmp_path: Path) -> None:
        """build_tree includes the names of files in the directory."""
        (tmp_path / "hello.txt").write_text("content")
        result = build_tree(tmp_path)
        assert "hello.txt" in result

    def test_includes_subdirectory_names_in_output(self, tmp_path: Path) -> None:
        """build_tree includes the names of subdirectories."""
        (tmp_path / "subdir").mkdir()
        result = build_tree(tmp_path)
        assert "subdir" in result

    def test_nested_files_are_indented_more_than_parent(self, tmp_path: Path) -> None:
        """build_tree indents nested entries more than their parent directory entry."""
        parent = tmp_path / "parent_dir"
        parent.mkdir()
        (parent / "nested_file.txt").write_text("x")
        result = build_tree(tmp_path)
        lines = result.splitlines()
        parent_line = next((ln for ln in lines if "parent_dir" in ln), None)
        child_line = next((ln for ln in lines if "nested_file.txt" in ln), None)
        assert parent_line is not None, "parent_dir not found in tree output"
        assert child_line is not None, "nested_file.txt not found in tree output"
        parent_indent = len(parent_line) - len(parent_line.lstrip())
        child_indent = len(child_line) - len(child_line.lstrip())
        assert child_indent > parent_indent

    def test_default_depth_3_excludes_content_at_level_4(self, tmp_path: Path) -> None:
        """build_tree default max_depth=3 does not show content 4 levels deep."""
        deep = tmp_path
        for name in ("l1", "l2", "l3", "l4"):
            deep = deep / name
            deep.mkdir()
        (deep / "too_deep.txt").write_text("deep")
        result = build_tree(tmp_path)
        assert "too_deep.txt" not in result

    def test_default_depth_3_includes_content_at_level_3(self, tmp_path: Path) -> None:
        """build_tree default max_depth=3 includes content exactly 3 levels deep."""
        deep = tmp_path / "l1" / "l2" / "l3"
        deep.mkdir(parents=True)
        (deep / "present.txt").write_text("here")
        result = build_tree(tmp_path)
        assert "present.txt" in result

    def test_custom_max_depth_1_hides_grandchildren(self, tmp_path: Path) -> None:
        """build_tree(max_depth=1) includes direct children but NOT grandchildren."""
        child = tmp_path / "child_dir"
        child.mkdir()
        (child / "grandchild.txt").write_text("g")
        result = build_tree(tmp_path, max_depth=1)
        assert "child_dir" in result
        assert "grandchild.txt" not in result

    def test_exclude_set_hides_named_entries(self, tmp_path: Path) -> None:
        """build_tree exclude set removes directories with matching names from output."""
        (tmp_path / "visible_dir").mkdir()
        (tmp_path / "hidden_dir").mkdir()
        result = build_tree(tmp_path, exclude={"hidden_dir"})
        assert "visible_dir" in result
        assert "hidden_dir" not in result

    def test_exclude_none_does_not_hide_regular_entries(self, tmp_path: Path) -> None:
        """build_tree with exclude=None (default) includes all ordinary entries."""
        (tmp_path / "regular_dir").mkdir()
        result = build_tree(tmp_path, exclude=None)
        assert "regular_dir" in result

    def test_signature_matches_ac_spec(self) -> None:
        """build_tree has signature (root, max_depth=3, exclude=None) per AC."""
        sig = inspect.signature(build_tree)
        params = sig.parameters
        assert "root" in params, "build_tree must have 'root' parameter"
        assert "max_depth" in params, "build_tree must have 'max_depth' parameter"
        assert "exclude" in params, "build_tree must have 'exclude' parameter"
        assert sig.parameters["max_depth"].default == 3
        assert sig.parameters["exclude"].default is None
