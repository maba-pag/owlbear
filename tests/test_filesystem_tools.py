"""Tests for FileToolset — FunctionToolset wrapping 5 filesystem tools.

Covers: tool registration, path traversal guard, read_file (full + line
range), write_file, create_file (happy + exists error), list_directory
(sorting + dir suffix), search_files (glob-only, glob+regex, truncation),
and PermissionError on escape attempts.
"""

from __future__ import annotations

import pytest
from pydantic_ai.toolsets import FunctionToolset

from owlbear.tools.filesystem import FileToolset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_TOOL_NAMES = frozenset(
    {
        "read_file",
        "write_file",
        "create_file",
        "list_directory",
        "search_files",
    }
)


@pytest.fixture
def toolset(tmp_path: object) -> FileToolset:
    """FileToolset rooted at a temporary directory."""
    from pathlib import Path

    return FileToolset(workspace_root=Path(str(tmp_path)))


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestFileToolsetRegistration:
    """FileToolset registers all 5 filesystem tools on FunctionToolset."""

    def test_registers_five_tools(self, toolset: FileToolset) -> None:
        assert len(toolset.tools) == 5

    def test_tool_names_match(self, toolset: FileToolset) -> None:
        assert set(toolset.tools) == EXPECTED_TOOL_NAMES

    def test_inherits_from_function_toolset(self, toolset: FileToolset) -> None:
        assert isinstance(toolset, FunctionToolset)


# ---------------------------------------------------------------------------
# Path traversal guard (_safe_path)
# ---------------------------------------------------------------------------


class TestSafePath:
    """_safe_path prevents access outside workspace root."""

    def test_relative_escape_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(PermissionError, match="outside workspace"):
            toolset._safe_path("../escape")

    def test_absolute_path_outside_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(PermissionError, match="outside workspace"):
            toolset._safe_path("/etc/passwd")

    def test_null_byte_raises(self, toolset: FileToolset) -> None:
        with pytest.raises((PermissionError, ValueError)):
            toolset._safe_path("file\x00.txt")

    def test_valid_path_resolves(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        result = toolset._safe_path("sub/file.txt")
        assert result == root / "sub" / "file.txt"
        assert result.is_absolute()

    def test_dot_resolves_to_root(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        result = toolset._safe_path(".")
        assert result == root


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


class TestReadFile:
    """read_file reads file content with optional line range."""

    def test_read_full_file(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        f = Path(str(tmp_path)) / "hello.txt"
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")
        content = toolset._read_file("hello.txt")
        assert content == "line1\nline2\nline3\n"

    def test_read_with_line_range(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        f = Path(str(tmp_path)) / "lines.txt"
        f.write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
        content = toolset._read_file("lines.txt", start_line=2, end_line=4)
        assert content == "b\nc\nd\n"

    def test_read_start_line_only(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        f = Path(str(tmp_path)) / "lines.txt"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        content = toolset._read_file("lines.txt", start_line=2)
        assert content == "b\nc\n"

    def test_read_end_line_only(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        f = Path(str(tmp_path)) / "lines.txt"
        f.write_text("a\nb\nc\n", encoding="utf-8")
        content = toolset._read_file("lines.txt", end_line=2)
        assert content == "a\nb\n"

    def test_read_missing_file_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(FileNotFoundError):
            toolset._read_file("nonexistent.txt")

    def test_read_path_traversal_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(PermissionError):
            toolset._read_file("../escape.txt")


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


class TestWriteFile:
    """write_file creates or overwrites files with parent dir creation."""

    def test_write_new_file(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        result = toolset._write_file("new.txt", "hello")
        f = Path(str(tmp_path)) / "new.txt"
        assert f.read_text(encoding="utf-8") == "hello"
        assert "new.txt" in result

    def test_write_creates_parent_dirs(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        toolset._write_file("deep/nested/file.txt", "content")
        f = Path(str(tmp_path)) / "deep" / "nested" / "file.txt"
        assert f.read_text(encoding="utf-8") == "content"

    def test_write_overwrites_existing(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        f = Path(str(tmp_path)) / "overwrite.txt"
        f.write_text("old", encoding="utf-8")
        toolset._write_file("overwrite.txt", "new")
        assert f.read_text(encoding="utf-8") == "new"

    def test_write_path_traversal_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(PermissionError):
            toolset._write_file("../escape.txt", "bad")


# ---------------------------------------------------------------------------
# create_file
# ---------------------------------------------------------------------------


class TestCreateFile:
    """create_file creates new files but refuses to overwrite existing."""

    def test_create_new_file(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        result = toolset._create_file("brand_new.txt", "content")
        f = Path(str(tmp_path)) / "brand_new.txt"
        assert f.read_text(encoding="utf-8") == "content"
        assert "brand_new.txt" in result

    def test_create_makes_parent_dirs(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        toolset._create_file("a/b/c.txt", "nested")
        f = Path(str(tmp_path)) / "a" / "b" / "c.txt"
        assert f.read_text(encoding="utf-8") == "nested"

    def test_create_existing_file_raises(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        f = Path(str(tmp_path)) / "exists.txt"
        f.write_text("already here", encoding="utf-8")
        with pytest.raises(FileExistsError):
            toolset._create_file("exists.txt", "should fail")

    def test_create_path_traversal_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(PermissionError):
            toolset._create_file("../escape.txt", "bad")


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------


class TestListDirectory:
    """list_directory returns sorted names with / suffix for dirs."""

    def test_lists_files_and_dirs(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        (root / "alpha.txt").write_text("a", encoding="utf-8")
        (root / "beta").mkdir()
        (root / "gamma.py").write_text("g", encoding="utf-8")
        result = toolset._list_directory(".")
        lines = result.strip().split("\n")
        assert lines == ["alpha.txt", "beta/", "gamma.py"]

    def test_lists_subdirectory(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        sub = root / "sub"
        sub.mkdir()
        (sub / "file.txt").write_text("f", encoding="utf-8")
        (sub / "inner").mkdir()
        result = toolset._list_directory("sub")
        lines = result.strip().split("\n")
        assert lines == ["file.txt", "inner/"]

    def test_missing_directory_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(FileNotFoundError):
            toolset._list_directory("no_such_dir")

    def test_list_path_traversal_raises(self, toolset: FileToolset) -> None:
        with pytest.raises(PermissionError):
            toolset._list_directory("../")


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------


class TestSearchFiles:
    """search_files combines glob matching with optional content regex."""

    def test_glob_only(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        (root / "a.py").write_text("print('a')", encoding="utf-8")
        (root / "b.txt").write_text("text", encoding="utf-8")
        (root / "c.py").write_text("print('c')", encoding="utf-8")
        result = toolset._search_files("*.py")
        paths = result.strip().split("\n")
        assert sorted(paths) == ["a.py", "c.py"]

    def test_glob_with_content_regex(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        (root / "match.py").write_text("def hello():\n    pass\n", encoding="utf-8")
        (root / "nomatch.py").write_text("x = 1\n", encoding="utf-8")
        result = toolset._search_files("*.py", content_regex="def hello")
        paths = result.strip().split("\n")
        assert paths == ["match.py"]

    def test_recursive_glob(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        sub = root / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("code", encoding="utf-8")
        (root / "top.py").write_text("code", encoding="utf-8")
        result = toolset._search_files("**/*.py")
        paths = sorted(result.strip().split("\n"))
        # Should find both: top.py and pkg/mod.py (relative to root)
        assert len(paths) == 2

    def test_no_matches_returns_empty(self, toolset: FileToolset) -> None:
        result = toolset._search_files("*.nonexistent")
        assert result == ""

    def test_truncation_at_100(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        for i in range(120):
            (root / f"f{i:04d}.txt").write_text(f"file {i}", encoding="utf-8")
        result = toolset._search_files("*.txt")
        lines = [ln for ln in result.split("\n") if ln]
        # Should have 100 paths + truncation note
        file_lines = [ln for ln in lines if not ln.startswith("[")]
        assert len(file_lines) == 100
        assert any("[truncated" in ln for ln in lines)

    def test_search_only_files_not_dirs(self, toolset: FileToolset, tmp_path: object) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        (root / "match.py").write_text("code", encoding="utf-8")
        (root / "match_dir.py").mkdir()  # dir with .py name
        result = toolset._search_files("*.py")
        paths = result.strip().split("\n")
        assert paths == ["match.py"]

    # -- ReDoS protection tests (#653, pending #496 implementation) --------

    def test_search_files_invalid_regex(self, toolset: FileToolset) -> None:
        with pytest.raises(ValueError, match="Invalid content_regex"):
            toolset._search_files("*", content_regex="[invalid")

    def test_search_files_nested_quantifier_rejected(self, toolset: FileToolset) -> None:
        with pytest.raises(ValueError, match="nested quantifiers"):
            toolset._search_files("*", content_regex="(a+)+b")

    def test_search_files_regex_too_long(self, toolset: FileToolset) -> None:
        with pytest.raises(ValueError, match="too long"):
            toolset._search_files("*", content_regex="a" * 1001)

    def test_search_files_valid_regex_still_works(
        self, toolset: FileToolset, tmp_path: object
    ) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        (root / "greet.py").write_text("def hello():\n    pass\n", encoding="utf-8")
        (root / "other.py").write_text("x = 1\n", encoding="utf-8")
        result = toolset._search_files("*.py", content_regex="def hello")
        paths = result.strip().split("\n")
        assert paths == ["greet.py"]

    def test_search_files_none_regex_still_works(
        self, toolset: FileToolset, tmp_path: object
    ) -> None:
        from pathlib import Path

        root = Path(str(tmp_path))
        (root / "a.py").write_text("code", encoding="utf-8")
        result = toolset._search_files("*.py")
        assert result.strip() == "a.py"
