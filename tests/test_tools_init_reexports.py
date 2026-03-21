"""Tests for tools/__init__.py re-exports (task #814, #878)."""

from __future__ import annotations

import subprocess
import sys


class TestFromAC_ToolsReExports:
    """Every symbol listed in the AC must be importable from owlbear.tools."""

    def test_import_ask_user_toolset(self) -> None:
        from owlbear.tools import AskUserToolset

        assert AskUserToolset is not None

    def test_import_file_toolset(self) -> None:
        from owlbear.tools import FileToolset

        assert FileToolset is not None

    def test_import_git_local_toolset(self) -> None:
        from owlbear.tools import GitLocalToolset

        assert GitLocalToolset is not None

    def test_import_github_toolset(self) -> None:
        from owlbear.tools import GitHubToolset

        assert GitHubToolset is not None

    def test_import_kanban_toolset(self) -> None:
        from owlbear.tools import KanbanToolset

        assert KanbanToolset is not None

    def test_import_terminal_toolset(self) -> None:
        from owlbear.tools import TerminalToolset

        assert TerminalToolset is not None

    def test_import_hooked_toolset(self) -> None:
        from owlbear.tools import HookedToolset

        assert HookedToolset is not None

    def test_import_mcp_server_registry(self) -> None:
        from owlbear.tools import MCPServerRegistry

        assert MCPServerRegistry is not None

    def test_import_find_toolset(self) -> None:
        from owlbear.tools import find_toolset

        assert callable(find_toolset)

    def test_import_unwrap(self) -> None:
        from owlbear.tools import unwrap

        assert callable(unwrap)


class TestFromAC_ToolsReExportIdentity:
    """Each re-export must resolve to the canonical class/function."""

    def test_ask_user_toolset_identity(self) -> None:
        from owlbear.tools import AskUserToolset
        from owlbear.tools.ask_user import AskUserToolset as Original

        assert AskUserToolset is Original

    def test_file_toolset_identity(self) -> None:
        from owlbear.tools import FileToolset
        from owlbear.tools.filesystem import FileToolset as Original

        assert FileToolset is Original

    def test_git_local_toolset_identity(self) -> None:
        from owlbear.tools import GitLocalToolset
        from owlbear.tools.git_local import GitLocalToolset as Original

        assert GitLocalToolset is Original

    def test_github_toolset_identity(self) -> None:
        from owlbear.tools import GitHubToolset
        from owlbear.tools.github_api import GitHubToolset as Original

        assert GitHubToolset is Original

    def test_kanban_toolset_identity(self) -> None:
        from owlbear.tools import KanbanToolset
        from owlbear.tools.kanban import KanbanToolset as Original

        assert KanbanToolset is Original

    def test_terminal_toolset_identity(self) -> None:
        from owlbear.tools import TerminalToolset
        from owlbear.tools.terminal import TerminalToolset as Original

        assert TerminalToolset is Original

    def test_hooked_toolset_identity(self) -> None:
        from owlbear.tools import HookedToolset
        from owlbear.tools.hooked import HookedToolset as Original

        assert HookedToolset is Original

    def test_mcp_server_registry_identity(self) -> None:
        from owlbear.tools import MCPServerRegistry
        from owlbear.tools.mcp_registry import MCPServerRegistry as Original

        assert MCPServerRegistry is Original

    def test_find_toolset_identity(self) -> None:
        from owlbear.tools import find_toolset
        from owlbear.tools.protocols import find_toolset as original

        assert find_toolset is original

    def test_unwrap_identity(self) -> None:
        from owlbear.tools import unwrap
        from owlbear.tools.protocols import unwrap as original

        assert unwrap is original


class TestFromAC_ToolsAllTuple:
    """__all__ must be defined and contain exactly the 10 AC symbols."""

    EXPECTED_NAMES: frozenset[str] = frozenset(
        {
            "AskUserToolset",
            "FileToolset",
            "GitLocalToolset",
            "GitHubToolset",
            "KanbanToolset",
            "TerminalToolset",
            "HookedToolset",
            "MCPServerRegistry",
            "find_toolset",
            "unwrap",
        }
    )

    def test_all_is_defined(self) -> None:
        import owlbear.tools

        assert hasattr(owlbear.tools, "__all__"), "__all__ must be defined"

    def test_all_is_sequence(self) -> None:
        import owlbear.tools

        assert isinstance(owlbear.tools.__all__, (tuple, list)), "__all__ must be tuple or list"

    def test_all_contains_all_expected_names(self) -> None:
        import owlbear.tools

        actual = set(owlbear.tools.__all__)
        missing = self.EXPECTED_NAMES - actual
        assert not missing, f"Missing from __all__: {missing}"

    def test_all_has_no_unexpected_names(self) -> None:
        import owlbear.tools

        actual = set(owlbear.tools.__all__)
        extra = actual - self.EXPECTED_NAMES
        assert not extra, f"Unexpected entries in __all__: {extra}"


class TestFromAC_NoCircularImport:
    """Importing owlbear.tools must not trigger a circular import."""

    def test_import_owlbear_tools_exposes_all_symbols(self) -> None:
        """Smoke test matching AC: python -c 'import owlbear.tools'.

        After the re-exports are added, a bare ``import owlbear.tools``
        must succeed AND expose the 10 listed symbols as attributes.
        """
        import importlib

        mod = importlib.import_module("owlbear.tools")
        for name in (
            "AskUserToolset",
            "FileToolset",
            "GitLocalToolset",
            "GitHubToolset",
            "KanbanToolset",
            "TerminalToolset",
            "HookedToolset",
            "MCPServerRegistry",
            "find_toolset",
            "unwrap",
        ):
            assert hasattr(mod, name), f"{name} not accessible via 'import owlbear.tools'"


class TestFromAC_ToolsImportSideEffect:
    """A bare ``import owlbear.tools`` must not pull sub-module side-effects (#878).

    On the current tree this class produces a FAILING test because
    ``src/owlbear/tools/__init__.py`` eagerly imports ``owlbear.tools.github_api``
    (which transitively loads ``owlbear.core.retry``).  The builder's GREEN task
    (#879) must implement lazy exports so this test passes.
    """

    def test_bare_import_does_not_load_github_api_or_retry(self) -> None:
        """Fresh subprocess: bare import owlbear.tools must not load github_api or core.retry."""
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                (
                    "import sys; import owlbear.tools; "
                    "assert 'owlbear.tools.github_api' not in sys.modules, "
                    "'owlbear.tools.github_api eagerly loaded by bare import'; "
                    "assert 'owlbear.core.retry' not in sys.modules, "
                    "'owlbear.core.retry eagerly loaded by bare import'"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Bare import of owlbear.tools loaded unexpected modules:\n{result.stderr}"
        )
