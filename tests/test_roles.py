"""Tests for agent role policies — builder vs validator tool restrictions."""

from __future__ import annotations

from pydantic_ai.toolsets import FunctionToolset
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
    """Build a toolset with mixed read/write/execute tools."""
    ts = FunctionToolset()

    # Read tools
    ts.add_function(
        lambda path: f"<content of {path}>",
        name="file_read",
        description="Read a file.",
    )
    ts.add_function(
        lambda query: f"<results for {query}>",
        name="search",
        description="Search the workspace.",
    )

    # Write tools
    ts.add_function(
        lambda path, content: f"wrote {path} ({content!r})",
        name="file_write",
        description="Write a file.",
    )
    ts.add_function(
        lambda path, old, new: f"edited {path}: {old}->{new}",
        name="file_edit",
        description="Edit a file.",
    )
    ts.add_function(
        lambda path: f"deleted {path}",
        name="file_delete",
        description="Delete a file.",
    )

    # Execute tools
    ts.add_function(
        lambda cmd: f"<output of {cmd}>",
        name="execute_command",
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
        assert "file_write" in VALIDATOR_POLICY.denied_tools
        assert "file_edit" in VALIDATOR_POLICY.denied_tools
        assert "file_delete" in VALIDATOR_POLICY.denied_tools
        assert "execute_command" in VALIDATOR_POLICY.denied_tools

    def test_validator_policy_allows_reads(self) -> None:
        # denied_tools should NOT include read tools
        assert "file_read" not in VALIDATOR_POLICY.denied_tools
        assert "search" not in VALIDATOR_POLICY.denied_tools

    def test_custom_policy(self) -> None:
        policy = RolePolicy(
            role=AgentRole.BUILDER,
            denied_tools=frozenset({"execute_command"}),
        )
        assert policy.denied_tools == frozenset({"execute_command"})


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

        read_td = SimpleNamespace(name="file_read")
        search_td = SimpleNamespace(name="search")
        assert result.filter_func(None, read_td) is True
        assert result.filter_func(None, search_td) is True

    def test_validator_filter_rejects_write_tools(self) -> None:
        ts = _make_toolset()
        result = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        for name in ("file_write", "file_edit", "file_delete"):
            td = SimpleNamespace(name=name)
            assert result.filter_func(None, td) is False, f"{name} should be denied"

    def test_validator_filter_rejects_execute(self) -> None:
        ts = _make_toolset()
        result = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        td = SimpleNamespace(name="execute_command")
        assert result.filter_func(None, td) is False

    def test_validator_cannot_write(self) -> None:
        """Core AC: filter rejects all write-category tools."""
        ts = _make_toolset()
        result = apply_role_policy(ts, VALIDATOR_POLICY)
        assert isinstance(result, FilteredToolset)
        from types import SimpleNamespace

        write_tools = ["file_write", "file_edit", "file_delete"]
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
