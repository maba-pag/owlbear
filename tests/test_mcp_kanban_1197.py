"""Structural tests for #1197 — _agent_view_for removal and related cleanup.

AC1/AC2 behavioral tests removed: _canonical_agent_view_for was deleted in #1360.
Surviving: structural source-scan tests for AC1, AC2, AC4, and NonCallableMagicMock.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).parent
_SERVER_PY = (
    _TESTS_DIR.parent
    / "serve"
    / "mcp-kanban"
    / "src"
    / "owlbear_mcp_kanban"
    / "server.py"
)
_LIFECYCLE_TOOLS_PY = (
    _TESTS_DIR.parent / "serve" / "mcp-kanban" / "tests" / "test_mcp_lifecycle_tools.py"
)


# ---------------------------------------------------------------------------
# TestFromAC_NoMockImport — AC1 (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_NoMockImport:
    """AC1: server.py must not import or reference unittest.mock.Mock."""

    def test_server_has_no_unittest_mock_import(self) -> None:
        """AC1: 'from unittest.mock import Mock' must be absent from server.py."""
        source = _SERVER_PY.read_text(encoding="utf-8")
        assert "from unittest.mock import Mock" not in source

    def test_server_has_no_isinstance_mock_check(self) -> None:
        """AC1: isinstance(return_value, Mock) check must be absent from server.py."""
        source = _SERVER_PY.read_text(encoding="utf-8")
        assert "isinstance(return_value, Mock)" not in source


# ---------------------------------------------------------------------------
# TestFromAC_AgentViewForRemoved — AC2 (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewForRemoved:
    """AC2: _agent_view_for removed; structural check only.

    Behavioral spy tests removed — _canonical_agent_view_for was also deleted in #1360.
    """

    def test_agent_view_for_not_defined_in_server(self) -> None:
        """AC2: 'def _agent_view_for' must not appear in server.py."""
        source = _SERVER_PY.read_text(encoding="utf-8")
        assert "def _agent_view_for" not in source


# ---------------------------------------------------------------------------
# TestFromAC_NonCallableMockFixtures — AC4 revised (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_NonCallableMockFixtures:
    """AC4 (revised): test fixtures must use NonCallableMagicMock for engine.agent_view."""

    def test_server_1170_make_engine_mock_uses_noncallable_agent_view(self) -> None:
        """AC4 (revised): _make_engine_mock in test_server_1170.py must use NonCallableMagicMock."""
        source = (_TESTS_DIR / "test_server_1170.py").read_text(encoding="utf-8")
        assert "NonCallableMagicMock" in source

    def test_lifecycle_tools_mock_av_fixture_uses_noncallable_agent_view(self) -> None:
        """AC4 (revised): mock_av fixture in test_mcp_lifecycle_tools.py must use NonCallableMagicMock."""
        source = _LIFECYCLE_TOOLS_PY.read_text(encoding="utf-8")
        assert "NonCallableMagicMock" in source
