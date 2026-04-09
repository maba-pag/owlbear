"""Tests for #496: Standardize error handling, return types, and exports across MCP servers.

TDD RED phase — the following tests fail until the builder implements:
- mcp-project project_readme: catch OSError on read_text() and return error: string
- mcp-project project_structure: catch unexpected exceptions from build_tree() and return error: string
- mcp-knowledge __all__: add init_db to the exports list

Regression guards (currently passing) verify the happy path is not broken by the builder
when adding try/except wrappers.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_mcp_project.server import (
    AppContext as ProjectAppContext,
    project_readme,
    project_structure,
)
import owlbear_mcp_knowledge.server as _knowledge_server_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project_ctx(project_root: Path) -> MagicMock:
    """Return a FastMCP Context mock with ProjectAppContext as lifespan_context."""
    ctx = MagicMock()
    app_ctx = ProjectAppContext(
        project_file=None,
        project_root=project_root,
        owlbear_root=Path("/fake/owlbear"),
    )
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_ProjectReadmeErrorHandling
# ---------------------------------------------------------------------------


class TestFromAC_ProjectReadmeErrorHandling:
    """AC: mcp-project: add error returns where appropriate (e.g., file read failures).

    project_readme handles missing README (returns error: string) but currently does
    not handle the case where the file exists but read_text() raises OSError.
    The builder must add a try/except around read_text() and return an error: string.
    """

    @pytest.mark.asyncio
    async def test_read_text_oserror_returns_string_not_raises(self, tmp_path: Path) -> None:
        """project_readme must return a string (not raise) when read_text raises OSError."""
        (tmp_path / "README.md").touch()
        ctx = _make_project_ctx(tmp_path)

        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            try:
                result = await project_readme(ctx)
            except OSError as exc:
                pytest.fail(
                    f"project_readme propagated OSError to caller — "
                    f"must catch and return error: string; got exception: {exc}"
                )

        assert isinstance(result, str), f"project_readme must return str on read_text OSError; got: {type(result)}"

    @pytest.mark.asyncio
    async def test_read_text_oserror_returns_error_prefix(self, tmp_path: Path) -> None:
        """project_readme error return for OSError must start with 'error:'."""
        (tmp_path / "README.md").touch()
        ctx = _make_project_ctx(tmp_path)

        with patch.object(Path, "read_text", side_effect=OSError("disk failure")):
            result = await project_readme(ctx)

        assert isinstance(result, str)
        assert result.startswith("error:"), (
            f"project_readme must return error:-prefixed string on read_text failure; got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_permission_error_is_caught_and_returns_error_prefix(self, tmp_path: Path) -> None:
        """PermissionError (OSError subclass) on read_text must be caught; returns error: string."""
        (tmp_path / "README.md").touch()
        ctx = _make_project_ctx(tmp_path)

        with patch.object(Path, "read_text", side_effect=PermissionError("access denied")):
            result = await project_readme(ctx)

        assert isinstance(result, str)
        assert result.startswith("error:"), (
            f"project_readme must catch PermissionError and return error: string; got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_successful_read_still_returns_content(self, tmp_path: Path) -> None:
        """project_readme still returns file content when read succeeds (regression guard)."""
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\nHello world.", encoding="utf-8")
        ctx = _make_project_ctx(tmp_path)

        result = await project_readme(ctx)

        assert result == "# My Project\nHello world."


# ---------------------------------------------------------------------------
# TestFromAC_ProjectStructureErrorHandling
# ---------------------------------------------------------------------------


class TestFromAC_ProjectStructureErrorHandling:
    """AC: mcp-project: add error returns where appropriate.

    project_structure delegates to build_tree(). While build_tree catches OSError
    internally per directory, an unexpected exception raised from build_tree itself
    (e.g., a programming error or unexpected state) should be caught and returned
    as an error: string rather than propagated.
    """

    @pytest.mark.asyncio
    async def test_build_tree_exception_returns_string_not_raises(self, tmp_path: Path) -> None:
        """project_structure must return a string (not raise) when build_tree raises."""
        ctx = _make_project_ctx(tmp_path)

        with patch("owlbear_mcp_project.server.build_tree", side_effect=RuntimeError("unexpected")):
            try:
                result = await project_structure(ctx)
            except RuntimeError as exc:  # noqa: BLE001
                pytest.fail(
                    f"project_structure propagated exception to caller — "
                    f"must catch and return error: string; got: {exc}"
                )

        assert isinstance(result, str), f"project_structure must return str when build_tree raises; got: {type(result)}"

    @pytest.mark.asyncio
    async def test_build_tree_exception_returns_error_prefix(self, tmp_path: Path) -> None:
        """project_structure error return for build_tree exception must start with 'error:'."""
        ctx = _make_project_ctx(tmp_path)

        with patch("owlbear_mcp_project.server.build_tree", side_effect=OSError("root not accessible")):
            result = await project_structure(ctx)

        assert isinstance(result, str)
        assert result.startswith("error:"), (
            f"project_structure must return error:-prefixed string on build_tree failure; got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_successful_traversal_still_returns_tree(self, tmp_path: Path) -> None:
        """project_structure still returns a non-error string when build_tree succeeds (regression guard)."""
        (tmp_path / "src").mkdir()
        ctx = _make_project_ctx(tmp_path)

        result = await project_structure(ctx)

        assert isinstance(result, str)
        assert not result.startswith("error:"), f"project_structure must not return error: on success; got: {result!r}"


# ---------------------------------------------------------------------------
# TestFromAC_KnowledgeServerExports
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeServerExports:
    """AC: Add __all__ to mcp-knowledge server.py listing all public symbols.

    init_db is a public function defined in server.py but currently absent
    from __all__. The builder must add it to complete the exports list.
    """

    def test_init_db_exported(self) -> None:
        """init_db is a public function and must appear in __all__."""
        assert "init_db" in _knowledge_server_module.__all__, (
            f"'init_db' is a public function in server.py but missing from __all__;\n"
            f"current __all__: {sorted(_knowledge_server_module.__all__)}"
        )

    def test_all_symbols_actually_exist_on_module(self) -> None:
        """Every symbol listed in __all__ must exist as a module attribute."""
        for name in _knowledge_server_module.__all__:
            assert hasattr(_knowledge_server_module, name), (
                f"__all__ references '{name}' but it does not exist on the module"
            )
