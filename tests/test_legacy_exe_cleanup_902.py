"""Failing RED-phase tests for legacy kanban-md.exe cleanup (task #902).

Verifies that all bare 'kanban-md.exe' references have been removed from
serve/orchestrator/ source and the affected test/fixture files, and that
module-level binary defaults no longer carry the .exe suffix.

AC coverage:
  AC1: All .exe references identified (precondition — research confirmed 8 files)
  AC2: References removed (tested indirectly via AC3/AC4)
  AC3: No bare .exe in serve/orchestrator/ or tests/ (module attribute + file content)
  AC4: grep equivalent — all 7 affected files assert no 'kanban-md.exe' literal
  AC5: Existing tests still pass — not tested here (regression guard, builder's job)
"""

from __future__ import annotations

from pathlib import Path

from owlbear.cli import _KANBAN_BIN as _CLI_KANBAN_BIN
from tests.fixtures.mock_acp_agent import _DEFAULT_KANBAN_BIN as _MOCK_DEFAULT_BIN

_REPO_ROOT = Path(__file__).parent.parent
_EXE_LITERAL = "kanban-md.exe"

_CLI_SOURCE = _REPO_ROOT / "serve" / "orchestrator" / "src" / "owlbear" / "cli.py"
_MOCK_ACP_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "mock_acp_agent.py"
_ORCHESTRATOR_LOOP_TEST = _REPO_ROOT / "tests" / "test_orchestrator_loop.py"
_DISPATCH_CYCLE_TEST = _REPO_ROOT / "tests" / "test_dispatch_cycle_trace_id.py"
_E2E_DISPATCH_TEST = _REPO_ROOT / "tests" / "test_e2e_dispatch.py"
_DISPATCH_INTEGRATION_TEST = _REPO_ROOT / "tests" / "test_dispatch_integration.py"
_MOCK_ACP_AGENT_TEST = _REPO_ROOT / "tests" / "test_mock_acp_agent.py"


# ---------------------------------------------------------------------------
# TestFromAC_CliDefaultBinary (AC3, AC4)
# ---------------------------------------------------------------------------


class TestFromAC_CliDefaultBinary:
    """owlbear.cli._KANBAN_BIN must not carry a .exe suffix after cleanup."""

    def test_cli_default_binary_has_no_exe_suffix(self) -> None:
        """_KANBAN_BIN must not end with .exe."""
        assert _CLI_KANBAN_BIN.suffix != ".exe", (
            f"_KANBAN_BIN must not have .exe suffix, got '{_CLI_KANBAN_BIN}'"
        )

    def test_cli_default_binary_equals_kanban_md(self) -> None:
        """_KANBAN_BIN must equal Path('kanban/kanban-md')."""
        assert Path("kanban/kanban-md") == _CLI_KANBAN_BIN, (
            f"Expected Path('kanban/kanban-md'), got '{_CLI_KANBAN_BIN}'"
        )

    def test_cli_source_file_contains_no_exe_reference(self) -> None:
        """serve/orchestrator/src/owlbear/cli.py must contain no 'kanban-md.exe' literal."""
        content = _CLI_SOURCE.read_text()
        assert _EXE_LITERAL not in content, (
            f"cli.py still contains '{_EXE_LITERAL}' — legacy reference not removed"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MockAgentDefaultBinary (AC3, AC4)
# ---------------------------------------------------------------------------


class TestFromAC_MockAgentDefaultBinary:
    """tests.fixtures.mock_acp_agent._DEFAULT_KANBAN_BIN must not carry a .exe suffix."""

    def test_mock_acp_default_binary_has_no_exe_suffix(self) -> None:
        """_DEFAULT_KANBAN_BIN must not contain '.exe'."""
        assert ".exe" not in _MOCK_DEFAULT_BIN, (
            f"_DEFAULT_KANBAN_BIN must not contain '.exe', got '{_MOCK_DEFAULT_BIN}'"
        )

    def test_mock_acp_default_binary_equals_kanban_md(self) -> None:
        """_DEFAULT_KANBAN_BIN must equal 'kanban/kanban-md'."""
        assert _MOCK_DEFAULT_BIN == "kanban/kanban-md", (
            f"Expected 'kanban/kanban-md', got '{_MOCK_DEFAULT_BIN}'"
        )

    def test_mock_acp_fixture_file_contains_no_exe_reference(self) -> None:
        """tests/fixtures/mock_acp_agent.py must contain no 'kanban-md.exe' literal."""
        content = _MOCK_ACP_FIXTURE.read_text()
        assert _EXE_LITERAL not in content, (
            f"mock_acp_agent.py still contains '{_EXE_LITERAL}' — legacy reference not removed"
        )


# ---------------------------------------------------------------------------
# TestFromAC_TestFilesNoExeReference (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_TestFilesNoExeReference:
    """All affected test files must contain no bare 'kanban-md.exe' literal after cleanup."""

    def test_orchestrator_loop_file_contains_no_exe_reference(self) -> None:
        """tests/test_orchestrator_loop.py must contain no 'kanban-md.exe' literal."""
        content = _ORCHESTRATOR_LOOP_TEST.read_text()
        assert _EXE_LITERAL not in content, (
            "test_orchestrator_loop.py still contains 'kanban-md.exe' — "
            "legacy kanban_bin=Path(...) references not removed"
        )

    def test_dispatch_cycle_trace_file_contains_no_exe_reference(self) -> None:
        """tests/test_dispatch_cycle_trace_id.py must contain no 'kanban-md.exe' literal."""
        content = _DISPATCH_CYCLE_TEST.read_text()
        assert _EXE_LITERAL not in content, (
            "test_dispatch_cycle_trace_id.py still contains 'kanban-md.exe' — "
            "legacy kanban_bin references not removed"
        )

    def test_e2e_dispatch_file_contains_no_exe_reference(self) -> None:
        """tests/test_e2e_dispatch.py must contain no 'kanban-md.exe' literal."""
        content = _E2E_DISPATCH_TEST.read_text()
        assert _EXE_LITERAL not in content, (
            "test_e2e_dispatch.py still contains 'kanban-md.exe' — "
            "_KANBAN_BIN constant not updated"
        )

    def test_dispatch_integration_file_contains_no_exe_reference(self) -> None:
        """tests/test_dispatch_integration.py must contain no 'kanban-md.exe' literal."""
        content = _DISPATCH_INTEGRATION_TEST.read_text()
        assert _EXE_LITERAL not in content, (
            "test_dispatch_integration.py still contains 'kanban-md.exe' — "
            "convention path not updated"
        )

    def test_mock_acp_agent_test_contains_no_exe_reference(self) -> None:
        """tests/test_mock_acp_agent.py must contain no 'kanban-md.exe' literal."""
        content = _MOCK_ACP_AGENT_TEST.read_text()
        assert _EXE_LITERAL not in content, (
            "test_mock_acp_agent.py still contains 'kanban-md.exe' — "
            "fallback assertion not updated to 'kanban/kanban-md'"
        )
