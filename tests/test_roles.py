"""Tests for agent role policies — builder vs validator tool restrictions."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.toolsets.combined import CombinedToolset
from pydantic_ai.toolsets.filtered import FilteredToolset

from owlbear.core.roles import (
    BUILDER_POLICY,
    VALIDATOR_POLICY,
    AgentRole,
    RolePolicy,
    apply_role_policy,
)

# ── Helpers ────────────────────────────────────────────────────────


def _make_toolset() -> FunctionToolset:
    """Build a toolset with mixed read/write/execute tools.

    Tool names match real toolset registrations:
    - FileToolset: read_file, write_file, create_file, list_directory, search_files
    - TerminalToolset: run_command
    """
    ts = FunctionToolset()

    # Read tools
    ts.add_function(
        lambda path: f"<content of {path}>",
        name="read_file",
        description="Read a file.",
    )
    ts.add_function(
        lambda query: f"<results for {query}>",
        name="search_files",
        description="Search the workspace.",
    )

    # Write tools (denied for validator)
    ts.add_function(
        lambda path, content: f"wrote {path} ({content!r})",
        name="write_file",
        description="Write a file.",
    )
    ts.add_function(
        lambda path, content: f"created {path} ({content!r})",
        name="create_file",
        description="Create a file.",
    )

    # Terminal tool (allowed for validator — safety via CommandGuard)
    ts.add_function(
        lambda cmd: f"<output of {cmd}>",
        name="run_command",
        description="Run a shell command.",
    )

    return ts


# ── AgentRole enum ────────────────────────────────────────────────


class TestAgentRole:
    def test_builder_value(self) -> None:
        assert AgentRole.BUILDER == "builder"

    def test_validator_value(self) -> None:
        assert AgentRole.VALIDATOR == "validator"

    def test_all_roles(self) -> None:
        assert len(AgentRole) >= 2


# ── RolePolicy dataclass ─────────────────────────────────────────


class TestRolePolicy:
    def test_builder_policy_allows_all(self) -> None:
        assert BUILDER_POLICY.denied_tools == frozenset()

    def test_validator_policy_denies_write_tools(self) -> None:
        """Write tools must NOT be in the validator allow-list."""
        assert "write_file" not in VALIDATOR_POLICY.allowed_tools
        assert "create_file" not in VALIDATOR_POLICY.allowed_tools

    def test_validator_policy_allows_reads(self) -> None:
        """Read tools must be in the validator allow-list."""
        assert "read_file" in VALIDATOR_POLICY.allowed_tools
        assert "search_files" in VALIDATOR_POLICY.allowed_tools

    def test_validator_policy_allows_run_command(self) -> None:
        """run_command included in allow-list — validators need pytest/ruff (#741)."""
        assert "run_command" in VALIDATOR_POLICY.allowed_tools

    def test_validator_policy_uses_allow_list(self) -> None:
        """VALIDATOR_POLICY must have a non-empty allowed_tools set."""
        assert len(VALIDATOR_POLICY.allowed_tools) > 2

    def test_custom_policy(self) -> None:
        policy = RolePolicy(
            role=AgentRole.BUILDER,
            denied_tools=frozenset({"run_command"}),
        )
        assert policy.denied_tools == frozenset({"run_command"})


# ── apply_role_policy ─────────────────────────────────────────────


class TestApplyRolePolicy:
    def test_builder_keeps_all_tools(self) -> None:
        ts = _make_toolset()
        # Builder has no denials → returns the original toolset unchanged
        filtered = apply_role_policy(ts, BUILDER_POLICY)
        assert filtered is ts

    def test_validator_returns_filtered_toolset(self) -> None:
        ts = _make_toolset()
        filtered = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(filtered, FilteredToolset)

    def test_validator_filter_accepts_read_tools(self) -> None:
        ts = _make_toolset()
        result = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        read_td = SimpleNamespace(name="read_file")
        search_td = SimpleNamespace(name="search_files")
        assert result.filter_func(None, read_td) is True
        assert result.filter_func(None, search_td) is True

    def test_validator_filter_rejects_write_tools(self) -> None:
        ts = _make_toolset()
        result = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        for name in ("write_file", "create_file"):
            td = SimpleNamespace(name=name)
            assert result.filter_func(None, td) is False, f"{name} should be denied"

    def test_validator_filter_accepts_run_command(self) -> None:
        """run_command included — validators need pytest/ruff execution (#741)."""
        assert "run_command" in VALIDATOR_POLICY.allowed_tools  # precondition
        ts = _make_toolset()
        result = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        td = SimpleNamespace(name="run_command")
        assert result.filter_func(None, td) is True

    def test_validator_cannot_write(self) -> None:
        """Core AC: filter rejects all write-category tools."""
        ts = _make_toolset()
        result = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        write_tools = ["write_file", "create_file"]
        results = [result.filter_func(None, SimpleNamespace(name=n)) for n in write_tools]
        assert all(r is False for r in results)

    def test_filtered_is_a_toolset(self) -> None:
        ts = _make_toolset()
        from pydantic_ai.toolsets.abstract import AbstractToolset

        filtered = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(filtered, AbstractToolset)

    def test_empty_denied_set_keeps_all(self) -> None:
        """A policy with no denials should pass through everything."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.BUILDER,
            denied_tools=frozenset(),
        )
        filtered = apply_role_policy(ts, policy)
        assert filtered is ts


class TestApplyRolePolicyCombinedToolset:
    """AC: filtering a CombinedToolset (non-FunctionToolset) works correctly."""

    @staticmethod
    def _make_combined() -> CombinedToolset:
        """Create a CombinedToolset from two FunctionToolsets."""
        ts_read = FunctionToolset()
        ts_read.add_function(
            lambda path: f"<content of {path}>",
            name="read_file",
            description="Read a file.",
        )
        ts_read.add_function(
            lambda query: f"<results for {query}>",
            name="search_files",
            description="Search the workspace.",
        )

        ts_write = FunctionToolset()
        ts_write.add_function(
            lambda path, content: f"wrote {path} ({content!r})",
            name="write_file",
            description="Write a file.",
        )
        ts_write.add_function(
            lambda cmd: f"<output of {cmd}>",
            name="run_command",
            description="Run a shell command.",
        )

        return CombinedToolset(toolsets=[ts_read, ts_write])

    def test_combined_toolset_accepted(self) -> None:
        """apply_role_policy accepts a CombinedToolset (AbstractToolset subclass)."""
        combined = self._make_combined()
        assert isinstance(combined, CombinedToolset)
        # Should not raise — accepts any AbstractToolset
        result = apply_role_policy(combined, VALIDATOR_POLICY)
        assert result is not combined  # validator has denials → filtered

    def test_combined_filter_rejects_denied(self) -> None:
        combined = self._make_combined()
        result = apply_role_policy(combined, VALIDATOR_POLICY)
        from pydantic_ai.toolsets.filtered import FilteredToolset

        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        td = SimpleNamespace(name="write_file")
        assert result.filter_func(None, td) is False, "write_file should be denied"

    def test_combined_filter_accepts_allowed(self) -> None:
        combined = self._make_combined()
        result = apply_role_policy(combined, VALIDATOR_POLICY)
        from pydantic_ai.toolsets.filtered import FilteredToolset

        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        # run_command included per #741 deviation, tested separately
        for name in ("read_file", "search_files"):
            td = SimpleNamespace(name=name)
            assert result.filter_func(None, td) is True, f"{name} should be allowed"

    def test_combined_filter_accepts_run_command(self) -> None:
        """run_command is in the validator allow-list (#741 deviation)."""
        assert "run_command" in VALIDATOR_POLICY.allowed_tools  # precondition
        combined = self._make_combined()
        result = apply_role_policy(combined, VALIDATOR_POLICY)
        from pydantic_ai.toolsets.filtered import FilteredToolset

        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        td = SimpleNamespace(name="run_command")
        assert result.filter_func(None, td) is True, "run_command should be allowed"

    def test_combined_builder_keeps_all(self) -> None:
        combined = self._make_combined()
        result = apply_role_policy(combined, BUILDER_POLICY)
        assert result is combined  # no denials → returned as-is


# ── TestFromAC: allowed_tools field (AC1) ─────────────────────────


class TestFromAC_AllowedToolsField:  # noqa: N801
    """AC1: RolePolicy.allowed_tools: frozenset[str] field exists."""

    def test_role_policy_has_allowed_tools_field(self) -> None:
        """RolePolicy must expose an allowed_tools attribute."""
        policy = RolePolicy(role=AgentRole.BUILDER)
        assert hasattr(policy, "allowed_tools")

    def test_allowed_tools_default_empty_frozenset(self) -> None:
        """Default value must be an empty frozenset (backwards-compatible)."""
        policy = RolePolicy(role=AgentRole.BUILDER)
        assert policy.allowed_tools == frozenset()

    def test_allowed_tools_is_frozenset_type(self) -> None:
        """allowed_tools must be frozenset[str], not set or list."""
        policy = RolePolicy(
            role=AgentRole.VALIDATOR,
            allowed_tools=frozenset({"read_file", "search_files"}),
        )
        assert isinstance(policy.allowed_tools, frozenset)

    def test_allowed_tools_custom_value(self) -> None:
        """RolePolicy stores a custom allowed_tools frozenset."""
        tools = frozenset({"read_file", "git_status", "web_search"})
        policy = RolePolicy(role=AgentRole.VALIDATOR, allowed_tools=tools)
        assert policy.allowed_tools == tools


# ── TestFromAC: apply_role_policy with allow-list (AC2, AC3, AC4, AC6) ──


class TestFromAC_ApplyAllowList:  # noqa: N801
    """AC2-4,6: apply_role_policy honours allowed_tools filtering."""

    def test_non_empty_allowed_permits_listed_tools(self) -> None:
        """AC2: only tools named in allowed_tools pass the filter."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.VALIDATOR,
            allowed_tools=frozenset({"read_file", "search_files"}),
        )
        result = apply_role_policy(ts, policy)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        assert result.filter_func(None, SimpleNamespace(name="read_file")) is True
        assert result.filter_func(None, SimpleNamespace(name="search_files")) is True

    def test_non_empty_allowed_rejects_unlisted_tools(self) -> None:
        """AC2/AC6: tools NOT in allowed_tools are rejected (fail-safe)."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.VALIDATOR,
            allowed_tools=frozenset({"read_file"}),
        )
        result = apply_role_policy(ts, policy)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        for name in ("write_file", "create_file", "run_command", "search_files"):
            td = SimpleNamespace(name=name)
            assert result.filter_func(None, td) is False, f"{name} should be denied"

    def test_empty_allowed_permits_all_tools(self) -> None:
        """AC3: empty allowed_tools (default) permits all tools — backwards-compat."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.BUILDER,
            allowed_tools=frozenset(),
            denied_tools=frozenset(),
        )
        result = apply_role_policy(ts, policy)
        # No restrictions — original toolset returned as-is
        assert result is ts

    def test_both_allowed_and_denied_intersection(self) -> None:
        """AC4: tool must be in allowed AND not in denied."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.VALIDATOR,
            allowed_tools=frozenset({"read_file", "write_file"}),
            denied_tools=frozenset({"write_file"}),
        )
        result = apply_role_policy(ts, policy)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        # read_file: allowed + not denied → pass
        assert result.filter_func(None, SimpleNamespace(name="read_file")) is True
        # write_file: allowed but denied → rejected
        assert result.filter_func(None, SimpleNamespace(name="write_file")) is False

    def test_both_allowed_and_denied_rejects_even_if_allowed(self) -> None:
        """AC4: denied_tools wins over allowed_tools for the same tool."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.VALIDATOR,
            allowed_tools=frozenset({"create_file", "read_file"}),
            denied_tools=frozenset({"create_file"}),
        )
        result = apply_role_policy(ts, policy)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        assert result.filter_func(None, SimpleNamespace(name="create_file")) is False

    def test_unlisted_tool_auto_rejected(self) -> None:
        """AC6: any tool not in allowed_tools is automatically rejected."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.VALIDATOR,
            allowed_tools=frozenset({"read_file"}),
        )
        result = apply_role_policy(ts, policy)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        # Completely unknown tool — not in allowed → rejected
        assert result.filter_func(None, SimpleNamespace(name="unknown_tool")) is False

    def test_single_tool_in_allowed(self) -> None:
        """Boundary: allow-list with exactly one tool."""
        ts = _make_toolset()
        policy = RolePolicy(
            role=AgentRole.VALIDATOR,
            allowed_tools=frozenset({"read_file"}),
        )
        result = apply_role_policy(ts, policy)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        assert result.filter_func(None, SimpleNamespace(name="read_file")) is True
        assert result.filter_func(None, SimpleNamespace(name="search_files")) is False


# ── TestFromAC: VALIDATOR_POLICY allow-list model (AC5) ───────────


class TestFromAC_ValidatorAllowListModel:  # noqa: N801
    """AC5: VALIDATOR_POLICY uses allow-list, not 2-item deny-list."""

    def test_validator_policy_has_non_empty_allowed_tools(self) -> None:
        """VALIDATOR_POLICY.allowed_tools must contain the read-only tool set."""
        assert len(VALIDATOR_POLICY.allowed_tools) > 0

    def test_validator_policy_not_two_item_deny_list(self) -> None:
        """The old 2-item deny-list model is replaced by the allow-list."""
        # The new model should NOT rely solely on denied_tools
        assert VALIDATOR_POLICY.allowed_tools != frozenset()

    def test_validator_allows_read_file(self) -> None:
        assert "read_file" in VALIDATOR_POLICY.allowed_tools

    def test_validator_allows_list_directory(self) -> None:
        assert "list_directory" in VALIDATOR_POLICY.allowed_tools

    def test_validator_allows_search_files(self) -> None:
        assert "search_files" in VALIDATOR_POLICY.allowed_tools

    def test_validator_allows_git_readonly_tools(self) -> None:
        """git_status, git_diff, git_log must be in the allow-list."""
        for tool in ("git_status", "git_diff", "git_log"):
            assert tool in VALIDATOR_POLICY.allowed_tools, f"{tool} missing"

    def test_validator_allows_web_read_tools(self) -> None:
        for tool in ("web_search", "web_read"):
            assert tool in VALIDATOR_POLICY.allowed_tools, f"{tool} missing"

    def test_validator_allows_kanban_readonly_tools(self) -> None:
        for tool in ("kanban_list", "kanban_show", "kanban_context"):
            assert tool in VALIDATOR_POLICY.allowed_tools, f"{tool} missing"

    def test_validator_denies_write_file(self) -> None:
        assert "write_file" not in VALIDATOR_POLICY.allowed_tools

    def test_validator_denies_create_file(self) -> None:
        assert "create_file" not in VALIDATOR_POLICY.allowed_tools

    def test_validator_allows_run_command(self) -> None:
        """#741 deviation: INCLUDE run_command (validators need pytest/ruff)."""
        assert "run_command" in VALIDATOR_POLICY.allowed_tools

    def test_validator_denies_git_push(self) -> None:
        assert "git_push" not in VALIDATOR_POLICY.allowed_tools

    def test_validator_denies_browser_click(self) -> None:
        assert "browser_click" not in VALIDATOR_POLICY.allowed_tools

    def test_new_tool_not_in_allowed_is_denied(self) -> None:
        """Fail-safe: any tool NOT explicitly listed is denied for validator."""
        assert "hypothetical_new_tool" not in VALIDATOR_POLICY.allowed_tools


# ── TestFromAC: AgentRegistry applies allow-list (AC7) ────────────


class TestFromAC_RegistryAllowListPolicy:  # noqa: N801
    """AC7: AgentRegistry applies allow-list policy to agents with role=validator."""

    def test_registry_applies_allow_list_to_validator_role(
        self, tmp_path: Path,
    ) -> None:
        """When an agent has role=validator, its toolsets must be filtered
        through the allow-list policy — not the old 2-item deny-list."""
        from unittest.mock import patch

        from pydantic_ai import Agent

        from owlbear.core.agent_registry import AgentRegistry

        md = tmp_path / "val.md"
        md.write_text(
            "---\nname: val\ndescription: Validator\nrole: validator\n"
            "tools:\n  - fs\n---\nBody.\n",
            encoding="utf-8",
        )

        # Provide a toolset with both read and write tools
        ts = _make_toolset()

        registry = AgentRegistry(
            tmp_path,
            lambda _name: ts,
            default_model="test",
        )
        registry.scan()

        # Patch apply_role_policy so we can inspect which policy is used
        patch_target = "owlbear.core.agent_registry.apply_role_policy"
        with patch(patch_target, wraps=apply_role_policy) as mock_apply:
            agent = registry.get("val")
            assert isinstance(agent, Agent)
            # apply_role_policy must have been called
            assert mock_apply.call_count >= 1
            # The policy passed must have a non-empty allowed_tools
            call_args = mock_apply.call_args
            policy_used = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("policy")
            assert hasattr(policy_used, "allowed_tools")
            assert len(policy_used.allowed_tools) > 0, (
                "Registry must apply a policy with non-empty allowed_tools for validator role"
            )


# ── TestFromAC: #741 VALIDATOR_POLICY deviations (AC3) ───────────


class TestFromAC_ValidatorPolicyDeviations741:  # noqa: N801
    """#741 AC3 deviations from research doc Section 5."""

    def test_validator_includes_run_command(self) -> None:
        """INCLUDE run_command — validators need pytest/ruff, protected by CommandSafetyGuard."""
        assert "run_command" in VALIDATOR_POLICY.allowed_tools

    def test_validator_includes_kanban_edit(self) -> None:
        """INCLUDE kanban_edit — validators must append pipeline notes per agent-common."""
        assert "kanban_edit" in VALIDATOR_POLICY.allowed_tools

    def test_validator_includes_kanban_move(self) -> None:
        """INCLUDE kanban_move — validators must advance task status per agent-common."""
        assert "kanban_move" in VALIDATOR_POLICY.allowed_tools

    def test_validator_excludes_delegate_to_agent(self) -> None:
        """EXCLUDE delegate_to_agent — validators report findings, orchestrator re-dispatches."""
        assert "delegate_to_agent" not in VALIDATOR_POLICY.allowed_tools

    def test_run_command_not_in_denied_tools(self) -> None:
        """run_command is in allowed_tools, not blocked by denied_tools."""
        assert "run_command" in VALIDATOR_POLICY.allowed_tools
        assert "run_command" not in VALIDATOR_POLICY.denied_tools

    def test_kanban_edit_not_in_denied_tools(self) -> None:
        """kanban_edit is in allowed_tools, not blocked by denied_tools."""
        assert "kanban_edit" in VALIDATOR_POLICY.allowed_tools
        assert "kanban_edit" not in VALIDATOR_POLICY.denied_tools

    def test_kanban_move_not_in_denied_tools(self) -> None:
        """kanban_move is in allowed_tools, not blocked by denied_tools."""
        assert "kanban_move" in VALIDATOR_POLICY.allowed_tools
        assert "kanban_move" not in VALIDATOR_POLICY.denied_tools


# ── TestFromAC: #741 BUILDER_POLICY unchanged (AC4) ──────────────


class TestFromAC_BuilderPolicyUnchanged741:  # noqa: N801
    """#741 AC4: BUILDER_POLICY unchanged — empty allowed_tools = full access."""

    def test_builder_has_empty_allowed_tools(self) -> None:
        """Builder must retain empty allowed_tools (backwards-compatible full access)."""
        assert BUILDER_POLICY.allowed_tools == frozenset()

    def test_builder_allowed_tools_is_frozenset(self) -> None:
        """Builder allowed_tools must be frozenset type."""
        assert isinstance(BUILDER_POLICY.allowed_tools, frozenset)
