from __future__ import annotations

"""Failing tests for #1862: Remove create_dr MCP tool and engine function.

AC coverage:
  ac1 — create_dr function and @mcp.tool() registration removed from server.py
  ac2 — create_dr engine function removed from decisions.py
  ac3 — guidance strings in agent_view.py and guidance.py reference create_request
  ac4 — exclusive create_dr test files deleted; remaining test files cleaned of imports
  ac5 — surface contract EXPECTED_TOOLS no longer includes create_dr
  ac6 — serve/mcp-kanban/README.md no longer references create_dr
  ac7 — skill files no longer present create_dr as an available tool
"""

from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent


class TestRemoveCreateDr:
    """Tests for create_dr removal mapped to AC lines 1-7."""

    # ------------------------------------------------------------------ AC1 --

    def test_create_dr_not_in_server_all(self) -> None:
        """AC1 happy: 'create_dr' must not appear in server.__all__ after removal."""
        import owlbear_mcp_kanban.server as srv

        assert "create_dr" not in srv.__all__

    def test_create_dr_not_defined_in_server_module(self) -> None:
        """AC1 happy: create_dr function must not exist as an attribute of the server module."""
        import owlbear_mcp_kanban.server as srv

        assert not hasattr(srv, "create_dr")

    # ------------------------------------------------------------------ AC2 --

    def test_create_dr_not_in_decisions_module(self) -> None:
        """AC2 happy: create_dr must not be callable in owlbear_kanban.decisions."""
        import owlbear_kanban.decisions as dec

        assert not hasattr(dec, "create_dr")

    # ------------------------------------------------------------------ AC3 --

    def test_agent_view_block_hint_does_not_reference_create_dr(self) -> None:
        """AC3 happy: AgentView._BLOCK_AR_HINT must not contain the string 'create_dr'."""
        from owlbear_kanban.agent_view import AgentView

        assert "create_dr" not in AgentView._BLOCK_AR_HINT

    def test_agent_view_block_hint_references_create_request(self) -> None:
        """AC3 boundary: AgentView._BLOCK_AR_HINT must reference 'create_request'."""
        from owlbear_kanban.agent_view import AgentView

        assert "create_request" in AgentView._BLOCK_AR_HINT

    def test_mcp_guidance_dr_msg_does_not_reference_create_dr(self) -> None:
        """AC3 happy: _DR_REQUIRED_MSG in guidance.py must not contain 'create_dr'."""
        from owlbear_mcp_kanban.guidance import _DR_REQUIRED_MSG

        assert "create_dr" not in _DR_REQUIRED_MSG

    def test_mcp_guidance_dr_msg_references_create_request(self) -> None:
        """AC3 boundary: _DR_REQUIRED_MSG in guidance.py must reference 'create_request'."""
        from owlbear_mcp_kanban.guidance import _DR_REQUIRED_MSG

        assert "create_request" in _DR_REQUIRED_MSG

    # ------------------------------------------------------------------ AC4 --

    def test_mcp_create_dr_dedicated_test_file_deleted(self) -> None:
        """AC4 edge: serve/mcp-kanban/tests/test_mcp_create_dr.py must not exist."""
        test_file = WORKSPACE_ROOT / "serve" / "mcp-kanban" / "tests" / "test_mcp_create_dr.py"
        assert not test_file.exists(), f"Expected {test_file} to be deleted but it still exists"

    def test_mcp_create_dr_coerce_test_file_deleted(self) -> None:
        """AC4 edge: tests/test_mcp_create_dr_coerce.py must not exist."""
        test_file = WORKSPACE_ROOT / "tests" / "test_mcp_create_dr_coerce.py"
        assert not test_file.exists(), f"Expected {test_file} to be deleted but it still exists"

    def test_test_decisions_does_not_reference_create_dr(self) -> None:
        """AC4 happy: tests/test_decisions.py must not contain any reference to create_dr.

        The AC requires all create_dr tests and references to be removed from this file,
        including docstrings and inline comments, not just import statements.
        """
        test_file = WORKSPACE_ROOT / "tests" / "test_decisions.py"
        content = test_file.read_text(encoding="utf-8")
        assert "create_dr" not in content, (
            "tests/test_decisions.py still contains references to create_dr "
            "(including docstrings/comments — all must be removed per AC4)"
        )

    def test_test_mcp_kanban_does_not_reference_create_dr(self) -> None:
        """AC4 happy: tests/test_mcp_kanban.py must not reference create_dr at all."""
        test_file = WORKSPACE_ROOT / "tests" / "test_mcp_kanban.py"
        content = test_file.read_text(encoding="utf-8")
        assert "create_dr" not in content, "tests/test_mcp_kanban.py still contains references to create_dr"

    def test_server_newline_normalization_test_does_not_reference_create_dr(self) -> None:
        """AC4 happy: serve/mcp-kanban/tests/test_server_newline_normalization.py must not reference create_dr."""
        test_file = WORKSPACE_ROOT / "serve" / "mcp-kanban" / "tests" / "test_server_newline_normalization.py"
        content = test_file.read_text(encoding="utf-8")
        assert "create_dr" not in content, "test_server_newline_normalization.py still contains references to create_dr"

    def test_server_error_envelopes_test_does_not_reference_create_dr(self) -> None:
        """AC4 happy: serve/mcp-kanban/tests/test_server_error_envelopes.py must not reference create_dr."""
        test_file = WORKSPACE_ROOT / "serve" / "mcp-kanban" / "tests" / "test_server_error_envelopes.py"
        content = test_file.read_text(encoding="utf-8")
        assert "create_dr" not in content, "test_server_error_envelopes.py still contains references to create_dr"

    # ------------------------------------------------------------------ AC5 --

    def test_surface_contract_expected_tools_excludes_create_dr(self) -> None:
        """AC5 happy: EXPECTED_TOOLS in test_mcp_surface_contract.py must not include 'create_dr'."""
        surface_test = WORKSPACE_ROOT / "serve" / "mcp-kanban" / "tests" / "test_mcp_surface_contract.py"
        content = surface_test.read_text(encoding="utf-8")
        assert '"create_dr"' not in content, "test_mcp_surface_contract.py still contains 'create_dr' in EXPECTED_TOOLS"

    # ------------------------------------------------------------------ AC6 --

    def test_mcp_kanban_readme_does_not_reference_create_dr(self) -> None:
        """AC6 happy: serve/mcp-kanban/README.md must not reference create_dr."""
        readme = WORKSPACE_ROOT / "serve" / "mcp-kanban" / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "create_dr" not in content, "serve/mcp-kanban/README.md still references create_dr"

    # ------------------------------------------------------------------ AC7 --

    def test_h_mcp_kanban_skill_does_not_list_create_dr(self) -> None:
        """AC7 happy: share/skills/h-mcp-kanban/SKILL.md must not present create_dr as a tool."""
        skill_file = WORKSPACE_ROOT / "share" / "skills" / "h-mcp-kanban" / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        assert "create_dr" not in content, "share/skills/h-mcp-kanban/SKILL.md still references create_dr"

    def test_h_decision_requests_skill_does_not_present_create_dr_as_available(self) -> None:
        """AC7 happy: share/skills/h-decision-requests/SKILL.md must not present create_dr as available."""
        skill_file = WORKSPACE_ROOT / "share" / "skills" / "h-decision-requests" / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        assert "create_dr" not in content, "share/skills/h-decision-requests/SKILL.md still mentions create_dr"
