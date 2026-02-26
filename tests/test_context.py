"""Tests for owlbear.memory.context — ContextManager for agent instructions."""

from __future__ import annotations

from pathlib import Path

from owlbear.memory.context import ContextManager

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestContextManagerCreate:
    """ContextManager points at a workspace root."""

    def test_default_filename(self, tmp_path: Path) -> None:
        mgr = ContextManager(tmp_path)
        assert mgr.path == tmp_path / "context.md"

    def test_custom_filename(self, tmp_path: Path) -> None:
        mgr = ContextManager(tmp_path, filename="AGENTS.md")
        assert mgr.path == tmp_path / "AGENTS.md"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


class TestContextManagerLoad:
    """load() reads the context file."""

    def test_load_existing_file(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text("# Project\nYou are OwlBear.", encoding="utf-8")
        mgr = ContextManager(tmp_path)
        assert mgr.load() == "# Project\nYou are OwlBear."

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        mgr = ContextManager(tmp_path)
        assert mgr.load() is None

    def test_load_empty_file_returns_none(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text("", encoding="utf-8")
        mgr = ContextManager(tmp_path)
        assert mgr.load() is None

    def test_load_whitespace_only_returns_none(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "context.md"
        ctx_file.write_text("   \n  \n  ", encoding="utf-8")
        mgr = ContextManager(tmp_path)
        assert mgr.load() is None


# ---------------------------------------------------------------------------
# Existence check
# ---------------------------------------------------------------------------


class TestContextManagerExists:
    """exists() checks whether the context file is present."""

    def test_exists_true(self, tmp_path: Path) -> None:
        (tmp_path / "context.md").write_text("content", encoding="utf-8")
        mgr = ContextManager(tmp_path)
        assert mgr.exists() is True

    def test_exists_false(self, tmp_path: Path) -> None:
        mgr = ContextManager(tmp_path)
        assert mgr.exists() is False


# ---------------------------------------------------------------------------
# instructions property (for PydanticAI Agent)
# ---------------------------------------------------------------------------


class TestContextManagerInstructions:
    """instructions returns a string suitable for PydanticAI Agent(instructions=...)."""

    def test_instructions_with_content(self, tmp_path: Path) -> None:
        (tmp_path / "context.md").write_text("Be helpful.", encoding="utf-8")
        mgr = ContextManager(tmp_path)
        inst = mgr.instructions
        assert inst == "Be helpful."

    def test_instructions_no_file_returns_empty(self, tmp_path: Path) -> None:
        mgr = ContextManager(tmp_path)
        assert mgr.instructions == ""
