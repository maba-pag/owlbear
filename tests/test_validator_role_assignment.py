"""Tests for #742: Assign validator role to read-only agent definitions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pydantic_ai.models
import pytest
from pydantic_ai import Agent
from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.agent_def import parse_agent_definition
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.roles import AgentRole, apply_role_policy

# Block real LLM calls in the test suite.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

# Real agents directory containing shipped .md definitions.
AGENTS_DIR = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"


def _dummy_resolver(_tool_name: str) -> FunctionToolset:
    """Return an empty FunctionToolset for any tool name."""
    return FunctionToolset()


# ── AC2: writer.agent.md declares role: validator ────────────────


class TestFromAC_WriterRole:  # noqa: N801
    """AC2: writer.agent.md frontmatter declares role: validator."""

    def test_writer_frontmatter_declares_validator(self) -> None:
        defn = parse_agent_definition(AGENTS_DIR / "writer.md")
        assert defn.role == "validator", (
            f"writer.md must declare role: validator, got '{defn.role}'"
        )

    def test_writer_role_enum_is_validator(self) -> None:
        defn = parse_agent_definition(AGENTS_DIR / "writer.md")
        assert AgentRole(defn.role) is AgentRole.VALIDATOR


# ── AC4: Exactly three validators, no other agents changed ──────


class TestFromAC_ValidatorCount:  # noqa: N801
    """AC4: Only reviewer, writer, and auditor are validators."""

    def test_exactly_four_validators(self) -> None:
        """After #742, exactly four agents declare role: validator.

        Architect, reviewer, and auditor were already validators.
        Writer is the new addition from #742.
        """
        validators = []
        for md_path in sorted(AGENTS_DIR.glob("*.md")):
            defn = parse_agent_definition(md_path)
            if defn.role == "validator":
                validators.append(defn.name)
        assert sorted(validators) == ["architect", "auditor", "reviewer", "writer"], (
            f"Expected [architect, auditor, reviewer, writer] as validators, got {validators}"
        )


# ── AC1/AC3/AC5: All three validators get allow-list policy ─────


class TestFromAC_AllValidatorsAllowList:  # noqa: N801
    """AC1/AC3/AC5: Registry applies allow-list policy to reviewer, writer, auditor."""

    @pytest.mark.parametrize("agent_name", ["reviewer", "writer", "auditor"])
    def test_validator_gets_allow_list_policy(self, agent_name: str) -> None:
        """apply_role_policy must be called with a policy that has allowed_tools."""
        registry = AgentRegistry(AGENTS_DIR, _dummy_resolver, default_model="test")
        registry.scan()

        with patch(
            "owlbear.core.agent_registry.apply_role_policy",
            wraps=apply_role_policy,
        ) as mock_apply:
            agent = registry.get(agent_name)
            assert isinstance(agent, Agent)
            assert mock_apply.call_count >= 1, (
                f"{agent_name} must have validator role, triggering apply_role_policy"
            )
            _, policy = mock_apply.call_args[0]
            assert hasattr(policy, "allowed_tools"), (
                f"Policy for {agent_name} must have allowed_tools field"
            )
            assert len(policy.allowed_tools) > 0, (
                f"Policy for {agent_name} must use non-empty allowed_tools"
            )


# ── AC6: Auditor kanban tool access ─────────────────────────────


class TestFromAC_AuditorKanbanAccess:  # noqa: N801
    """AC6: Auditor's role policy must allow kanban_create/edit/move."""

    @pytest.mark.parametrize(
        "tool_name",
        [
            "kanban_create",
            "kanban_edit",
            "kanban_move",
        ],
    )
    def test_auditor_kanban_tool_in_policy(self, tool_name: str) -> None:
        """The policy applied to auditor must include kanban tools in allowed_tools."""
        registry = AgentRegistry(AGENTS_DIR, _dummy_resolver, default_model="test")
        registry.scan()

        with patch(
            "owlbear.core.agent_registry.apply_role_policy",
            wraps=apply_role_policy,
        ) as mock_apply:
            registry.get("auditor")
            assert mock_apply.call_count >= 1
            _, policy = mock_apply.call_args[0]
            assert hasattr(policy, "allowed_tools"), (
                "Policy must use allow-list model (allowed_tools field)"
            )
            assert tool_name in policy.allowed_tools, (
                f"Auditor needs {tool_name} but it's not in policy allowed_tools"
            )
