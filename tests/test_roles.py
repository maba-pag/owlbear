"""Tests for agent role policies — builder vs validator tool restrictions."""

from __future__ import annotations

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
        assert "write_file" in VALIDATOR_POLICY.denied_tools
        assert "create_file" in VALIDATOR_POLICY.denied_tools

    def test_validator_policy_allows_reads(self) -> None:
        # denied_tools should NOT include read tools
        assert "read_file" not in VALIDATOR_POLICY.denied_tools
        assert "search_files" not in VALIDATOR_POLICY.denied_tools

    def test_validator_policy_allows_run_command(self) -> None:
        """Reviewer needs terminal for pytest/ruff — safety via CommandGuard."""
        assert "run_command" not in VALIDATOR_POLICY.denied_tools

    def test_validator_policy_exact_denied_set(self) -> None:
        """Denied set must be exactly write_file + create_file, nothing else."""
        assert VALIDATOR_POLICY.denied_tools == frozenset({"write_file", "create_file"})

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

    def test_validator_filter_allows_run_command(self) -> None:
        """run_command must pass filter — reviewer needs pytest/ruff."""
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

        for name in ("read_file", "search_files", "run_command"):
            td = SimpleNamespace(name=name)
            assert result.filter_func(None, td) is True, f"{name} should be allowed"

    def test_combined_builder_keeps_all(self) -> None:
        combined = self._make_combined()
        result = apply_role_policy(combined, BUILDER_POLICY)
        assert result is combined  # no denials → returned as-is
