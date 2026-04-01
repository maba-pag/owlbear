"""Failing tests for task #493: TOOLS_EXCLUDE in mcp-knowledge and mcp-project servers (TDD RED).

Covers the AC contract for both servers:
  - _apply_tool_exclusions(server) reads the correct env var per server
  - Calls server.remove_tool for each comma-separated name (whitespace stripped)
  - Invalid/unknown tool names silently ignored (exception swallowed)
  - Default (no env var): no removals (backward-compatible)
  - app_lifespan calls _apply_tool_exclusions before yield
  - __all__ in both server modules includes _apply_tool_exclusions

All tests FAIL in RED phase — ImportError until builder implements #493.
"""

from __future__ import annotations

import os
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import targets — _apply_tool_exclusions does not exist yet in either server (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_knowledge.server import (  # type: ignore[import]
    _apply_tool_exclusions as knowledge_apply_exclusions,
    app_lifespan as knowledge_app_lifespan,
)
from owlbear_mcp_project.server import (  # type: ignore[import]
    _apply_tool_exclusions as project_apply_exclusions,
    app_lifespan as project_app_lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_server() -> MagicMock:
    """Return a MagicMock mimicking a FastMCP server with remove_tool."""
    server = MagicMock()
    server.remove_tool = MagicMock()
    return server


def _knowledge_patches() -> list:
    """Patch objects for knowledge server heavyweight deps (DB, vector store, embeddings)."""
    return [
        patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
        patch("owlbear_mcp_knowledge.server.GraphStore"),
        patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
        patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
        patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        patch("owlbear_mcp_knowledge.server.DocumentStore"),
        patch("owlbear_mcp_knowledge.server.EntityExtractor"),
        patch("owlbear_mcp_knowledge.server.TextChunker"),
        patch("owlbear_mcp_knowledge.server.IngestPipeline"),
        patch("owlbear_mcp_knowledge.server.KnowledgeSourceStore"),
    ]


# ---------------------------------------------------------------------------
# TestFromAC_KnowledgeToolExclusions
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeToolExclusions:
    """Contract tests for _apply_tool_exclusions in mcp-knowledge server (#493 AC)."""

    # AC: reads KNOWLEDGE_TOOLS_EXCLUDE env var, calls remove_tool per tool name
    def test_exclude_single_tool_calls_remove_tool_once(self) -> None:
        """Excluding one tool name causes remove_tool to be called exactly once with that name."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KNOWLEDGE_TOOLS_EXCLUDE": "search_knowledge"}):
            knowledge_apply_exclusions(server)
        server.remove_tool.assert_called_once_with("search_knowledge")

    # AC: comma-separated list → each name gets a remove_tool call
    def test_exclude_multiple_tools_calls_remove_tool_for_each(self) -> None:
        """Excluding multiple comma-separated tools calls remove_tool for each name."""
        server = _make_mock_server()
        with patch.dict(
            os.environ,
            {"KNOWLEDGE_TOOLS_EXCLUDE": "search_knowledge,list_sources,ingest_document"},
        ):
            knowledge_apply_exclusions(server)
        assert server.remove_tool.call_count == 3
        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert called_names == {"search_knowledge", "list_sources", "ingest_document"}

    # AC: Default (no env var): backward-compatible — remove_tool never called
    def test_no_env_var_remove_tool_never_called(self) -> None:
        """When KNOWLEDGE_TOOLS_EXCLUDE is not set, remove_tool is never called."""
        server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "KNOWLEDGE_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            knowledge_apply_exclusions(server)
        server.remove_tool.assert_not_called()

    # AC: invalid/unknown tool names silently ignored
    def test_invalid_tool_name_does_not_raise(self) -> None:
        """An unknown tool name causes remove_tool to raise, but the exception is swallowed."""
        server = _make_mock_server()
        server.remove_tool.side_effect = Exception("unknown tool: no_such_tool")
        with patch.dict(os.environ, {"KNOWLEDGE_TOOLS_EXCLUDE": "no_such_tool"}):
            knowledge_apply_exclusions(server)  # must not raise

    # Edge: empty env var → no removals (backward-compatible)
    def test_empty_env_var_no_removals(self) -> None:
        """When KNOWLEDGE_TOOLS_EXCLUDE is empty, remove_tool is never called."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KNOWLEDGE_TOOLS_EXCLUDE": ""}):
            knowledge_apply_exclusions(server)
        server.remove_tool.assert_not_called()

    # Edge: whitespace stripped from each tool name
    def test_whitespace_stripped_from_tool_names(self) -> None:
        """Leading/trailing whitespace around each tool name is stripped before calling remove_tool."""
        server = _make_mock_server()
        with patch.dict(
            os.environ,
            {"KNOWLEDGE_TOOLS_EXCLUDE": " search_knowledge , list_sources "},
        ):
            knowledge_apply_exclusions(server)
        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert "search_knowledge" in called_names
        assert "list_sources" in called_names
        assert not any(" " in name for name in called_names)

    # Edge: trailing comma does not produce an empty-string tool call
    def test_trailing_comma_ignored(self) -> None:
        """A trailing comma does not call remove_tool with an empty string."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KNOWLEDGE_TOOLS_EXCLUDE": "search_knowledge,"}):
            knowledge_apply_exclusions(server)
        called_names = [call.args[0] for call in server.remove_tool.call_args_list]
        assert "" not in called_names

    # Error: invalid name in list does not prevent valid names from being excluded
    def test_invalid_mixed_with_valid_still_excludes_valid(self) -> None:
        """When the list mixes valid and invalid names, valid names are still excluded."""
        call_log: list[str] = []

        def _selective_remove(name: str) -> None:
            if name == "no_such_tool":
                msg = "unknown tool"
                raise ValueError(msg)
            call_log.append(name)

        server = _make_mock_server()
        server.remove_tool.side_effect = _selective_remove
        with patch.dict(
            os.environ,
            {"KNOWLEDGE_TOOLS_EXCLUDE": "search_knowledge,no_such_tool,list_sources"},
        ):
            knowledge_apply_exclusions(server)
        assert "search_knowledge" in call_log
        assert "list_sources" in call_log

    # Boundary: function returns a set type
    def test_returns_set_type(self) -> None:
        """_apply_tool_exclusions returns a set (set[str])."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"KNOWLEDGE_TOOLS_EXCLUDE": "search_knowledge"}):
            result = knowledge_apply_exclusions(server)
        assert isinstance(result, set)

    # Boundary: returns empty set when no env var set
    def test_returns_empty_set_when_no_env_var(self) -> None:
        """_apply_tool_exclusions returns an empty set when no env var is set."""
        server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "KNOWLEDGE_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            result = knowledge_apply_exclusions(server)
        assert result == set()


# ---------------------------------------------------------------------------
# TestFromAC_ProjectToolExclusions
# ---------------------------------------------------------------------------


class TestFromAC_ProjectToolExclusions:
    """Contract tests for _apply_tool_exclusions in mcp-project server (#493 AC)."""

    # AC: reads PROJECT_TOOLS_EXCLUDE env var, calls remove_tool per tool name
    def test_exclude_single_tool_calls_remove_tool_once(self) -> None:
        """Excluding one tool name causes remove_tool to be called exactly once with that name."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"PROJECT_TOOLS_EXCLUDE": "project_info"}):
            project_apply_exclusions(server)
        server.remove_tool.assert_called_once_with("project_info")

    # AC: comma-separated list → each name gets a remove_tool call
    def test_exclude_multiple_tools_calls_remove_tool_for_each(self) -> None:
        """Excluding multiple comma-separated tools calls remove_tool for each name."""
        server = _make_mock_server()
        with patch.dict(
            os.environ,
            {"PROJECT_TOOLS_EXCLUDE": "project_info,project_list,project_readme"},
        ):
            project_apply_exclusions(server)
        assert server.remove_tool.call_count == 3
        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert called_names == {"project_info", "project_list", "project_readme"}

    # AC: Default (no env var): backward-compatible — remove_tool never called
    def test_no_env_var_remove_tool_never_called(self) -> None:
        """When PROJECT_TOOLS_EXCLUDE is not set, remove_tool is never called."""
        server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "PROJECT_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            project_apply_exclusions(server)
        server.remove_tool.assert_not_called()

    # AC: invalid/unknown tool names silently ignored
    def test_invalid_tool_name_does_not_raise(self) -> None:
        """An unknown tool name causes remove_tool to raise, but the exception is swallowed."""
        server = _make_mock_server()
        server.remove_tool.side_effect = Exception("unknown tool: no_such_tool")
        with patch.dict(os.environ, {"PROJECT_TOOLS_EXCLUDE": "no_such_tool"}):
            project_apply_exclusions(server)  # must not raise

    # Edge: empty env var → no removals (backward-compatible)
    def test_empty_env_var_no_removals(self) -> None:
        """When PROJECT_TOOLS_EXCLUDE is empty, remove_tool is never called."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"PROJECT_TOOLS_EXCLUDE": ""}):
            project_apply_exclusions(server)
        server.remove_tool.assert_not_called()

    # Edge: whitespace stripped from each tool name
    def test_whitespace_stripped_from_tool_names(self) -> None:
        """Leading/trailing whitespace around each tool name is stripped before calling remove_tool."""
        server = _make_mock_server()
        with patch.dict(
            os.environ,
            {"PROJECT_TOOLS_EXCLUDE": " project_info , project_list "},
        ):
            project_apply_exclusions(server)
        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert "project_info" in called_names
        assert "project_list" in called_names
        assert not any(" " in name for name in called_names)

    # Edge: trailing comma does not produce an empty-string tool call
    def test_trailing_comma_ignored(self) -> None:
        """A trailing comma does not call remove_tool with an empty string."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"PROJECT_TOOLS_EXCLUDE": "project_info,"}):
            project_apply_exclusions(server)
        called_names = [call.args[0] for call in server.remove_tool.call_args_list]
        assert "" not in called_names

    # Error: invalid name in list does not prevent valid names from being excluded
    def test_invalid_mixed_with_valid_still_excludes_valid(self) -> None:
        """When the list mixes valid and invalid names, valid names are still excluded."""
        call_log: list[str] = []

        def _selective_remove(name: str) -> None:
            if name == "no_such_tool":
                msg = "unknown tool"
                raise ValueError(msg)
            call_log.append(name)

        server = _make_mock_server()
        server.remove_tool.side_effect = _selective_remove
        with patch.dict(
            os.environ,
            {"PROJECT_TOOLS_EXCLUDE": "project_info,no_such_tool,project_list"},
        ):
            project_apply_exclusions(server)
        assert "project_info" in call_log
        assert "project_list" in call_log

    # Boundary: function returns a set type
    def test_returns_set_type(self) -> None:
        """_apply_tool_exclusions returns a set (set[str])."""
        server = _make_mock_server()
        with patch.dict(os.environ, {"PROJECT_TOOLS_EXCLUDE": "project_info"}):
            result = project_apply_exclusions(server)
        assert isinstance(result, set)

    # Boundary: returns empty set when no env var set
    def test_returns_empty_set_when_no_env_var(self) -> None:
        """_apply_tool_exclusions returns an empty set when no env var is set."""
        server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "PROJECT_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            result = project_apply_exclusions(server)
        assert result == set()


# ---------------------------------------------------------------------------
# TestFromAC_KnowledgeLifespanExclusion
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeLifespanExclusion:
    """Contract tests: app_lifespan calls _apply_tool_exclusions (mcp-knowledge)."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_apply_tool_exclusions(self) -> None:
        """app_lifespan calls _apply_tool_exclusions during startup (before yield)."""
        mock_server = _make_mock_server()
        with ExitStack() as stack:
            for p in _knowledge_patches():
                stack.enter_context(p)
            mock_apply = stack.enter_context(
                patch("owlbear_mcp_knowledge.server._apply_tool_exclusions")
            )
            async with knowledge_app_lifespan(mock_server):
                mock_apply.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_passes_server_to_apply_tool_exclusions(self) -> None:
        """app_lifespan passes the MCP server object as the argument to _apply_tool_exclusions."""
        mock_server = _make_mock_server()
        with ExitStack() as stack:
            for p in _knowledge_patches():
                stack.enter_context(p)
            mock_apply = stack.enter_context(
                patch("owlbear_mcp_knowledge.server._apply_tool_exclusions")
            )
            async with knowledge_app_lifespan(mock_server):
                call_args = mock_apply.call_args
                assert call_args is not None
                assert call_args.args[0] is mock_server

    @pytest.mark.asyncio
    async def test_lifespan_default_no_tool_removals(self) -> None:
        """With no KNOWLEDGE_TOOLS_EXCLUDE set, no tools are removed during lifespan startup."""
        mock_server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "KNOWLEDGE_TOOLS_EXCLUDE"}
        with ExitStack() as stack:
            for p in _knowledge_patches():
                stack.enter_context(p)
            stack.enter_context(patch.dict(os.environ, env_without, clear=True))
            async with knowledge_app_lifespan(mock_server):
                pass
        mock_server.remove_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_lifespan_removes_tool_when_env_var_set(self) -> None:
        """app_lifespan removes tools specified in KNOWLEDGE_TOOLS_EXCLUDE during startup."""
        mock_server = _make_mock_server()
        with ExitStack() as stack:
            for p in _knowledge_patches():
                stack.enter_context(p)
            stack.enter_context(
                patch.dict(os.environ, {"KNOWLEDGE_TOOLS_EXCLUDE": "search_knowledge"})
            )
            async with knowledge_app_lifespan(mock_server):
                pass
        mock_server.remove_tool.assert_called_with("search_knowledge")


# ---------------------------------------------------------------------------
# TestFromAC_ProjectLifespanExclusion
# ---------------------------------------------------------------------------


class TestFromAC_ProjectLifespanExclusion:
    """Contract tests: app_lifespan calls _apply_tool_exclusions (mcp-project)."""

    @pytest.mark.asyncio
    async def test_lifespan_calls_apply_tool_exclusions(self) -> None:
        """app_lifespan calls _apply_tool_exclusions during startup (before yield)."""
        mock_server = _make_mock_server()
        with patch("owlbear_mcp_project.server._apply_tool_exclusions") as mock_apply:
            async with project_app_lifespan(mock_server):
                mock_apply.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_passes_server_to_apply_tool_exclusions(self) -> None:
        """app_lifespan passes the MCP server object as the argument to _apply_tool_exclusions."""
        mock_server = _make_mock_server()
        with patch("owlbear_mcp_project.server._apply_tool_exclusions") as mock_apply:
            async with project_app_lifespan(mock_server):
                call_args = mock_apply.call_args
                assert call_args is not None
                assert call_args.args[0] is mock_server

    @pytest.mark.asyncio
    async def test_lifespan_default_no_tool_removals(self) -> None:
        """With no PROJECT_TOOLS_EXCLUDE set, no tools are removed during lifespan startup."""
        mock_server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "PROJECT_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            async with project_app_lifespan(mock_server):
                pass
        mock_server.remove_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_lifespan_removes_tool_when_env_var_set(self) -> None:
        """app_lifespan removes tools specified in PROJECT_TOOLS_EXCLUDE during startup."""
        mock_server = _make_mock_server()
        with patch.dict(os.environ, {"PROJECT_TOOLS_EXCLUDE": "project_info"}):
            async with project_app_lifespan(mock_server):
                pass
        mock_server.remove_tool.assert_called_with("project_info")


# ---------------------------------------------------------------------------
# TestFromAC_AllExports
# ---------------------------------------------------------------------------


class TestFromAC_AllExports:
    """Contract tests: both server __all__ lists include _apply_tool_exclusions."""

    def test_knowledge_all_includes_apply_tool_exclusions(self) -> None:
        """owlbear_mcp_knowledge.server.__all__ must export _apply_tool_exclusions."""
        import owlbear_mcp_knowledge.server as mod

        assert "_apply_tool_exclusions" in mod.__all__

    def test_project_all_includes_apply_tool_exclusions(self) -> None:
        """owlbear_mcp_project.server.__all__ must export _apply_tool_exclusions."""
        import owlbear_mcp_project.server as mod

        assert "_apply_tool_exclusions" in mod.__all__
