"""RED tests — guidance text update across all emission points (#1183).

AC5 coverage (td:1):
- `_DR_REQUIRED_MSG` in guidance.py equals the new canonical text
- `AgentView._BLOCK_AR_HINT` in engine.py equals the new canonical text
- h-mcp-kanban/SKILL.md agent-obligation prose references create_dr tool, not scribe agent

All tests must FAIL (RED phase) — current code still has old text.
"""

from __future__ import annotations

import pathlib

_REPO_ROOT = pathlib.Path(__file__).parent.parent

# The new canonical guidance text per AC5.
_NEW_DR_MSG = (
    "⚠️ ACTION REQUIRED: Create a Decision Request via the create_dr tool."
    " Blocks without a DR are invisible to the pipeline."
)


class TestFromAC_GuidanceTextUpdate:
    """AC5 — guidance text updated at every emission point to new canonical text."""

    def test_dr_required_msg_guidance_py(self) -> None:
        """_DR_REQUIRED_MSG in guidance.py must equal the new canonical DR text."""
        from owlbear_mcp_kanban.guidance import _DR_REQUIRED_MSG

        assert _DR_REQUIRED_MSG == _NEW_DR_MSG, (
            f"guidance.py _DR_REQUIRED_MSG not updated.\n  Expected: {_NEW_DR_MSG!r}\n  Got:      {_DR_REQUIRED_MSG!r}"
        )

    def test_block_ar_hint_engine_py(self) -> None:
        """AgentView._BLOCK_AR_HINT in engine.py must equal the new canonical DR text."""
        from owlbear_kanban.engine import AgentView

        assert AgentView._BLOCK_AR_HINT == _NEW_DR_MSG, (
            f"engine.py AgentView._BLOCK_AR_HINT not updated.\n"
            f"  Expected: {_NEW_DR_MSG!r}\n"
            f"  Got:      {AgentView._BLOCK_AR_HINT!r}"
        )

    def test_skill_doc_references_create_dr_tool(self) -> None:
        """h-mcp-kanban/SKILL.md agent-obligation line must reference create_dr tool."""
        skill_path = _REPO_ROOT / "share" / "skills" / "h-mcp-kanban" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")

        assert "create_dr tool" in content, (
            "h-mcp-kanban/SKILL.md does not contain 'create_dr tool'. "
            "Update the agent-obligation prose to reference the create_dr tool."
        )

    def test_skill_doc_drops_scribe_agent_reference(self) -> None:
        """h-mcp-kanban/SKILL.md agent-obligation line must not reference the scribe agent."""
        skill_path = _REPO_ROOT / "share" / "skills" / "h-mcp-kanban" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")

        assert "via the scribe agent" not in content, (
            "h-mcp-kanban/SKILL.md still contains 'via the scribe agent'. Replace with 'via the create_dr tool'."
        )
