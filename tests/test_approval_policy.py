"""Tests for owlbear.safety.policy — ApprovalPolicy model.

TDD red-phase tests for task #338. The module ``owlbear.safety.policy``
does not exist yet — all tests are expected to fail on import until the
implementation task is completed.
"""

from __future__ import annotations

from pydantic import BaseModel

from owlbear.safety.policy import ApprovalPolicy, ApprovalRule, ApprovalSession


class TestApprovalRuleModel:
    """Verify ApprovalRule structure (tool_name + optional arg_pattern)."""

    def test_rule_with_tool_name_only(self) -> None:
        """A rule can specify only a tool name, no arg_pattern."""
        rule = ApprovalRule(tool_name="git_push")
        assert rule.tool_name == "git_push"
        assert rule.arg_pattern is None

    def test_rule_with_arg_pattern(self) -> None:
        """A rule can specify both tool_name and arg_pattern (regex)."""
        rule = ApprovalRule(tool_name="run_command", arg_pattern="git push")
        assert rule.tool_name == "run_command"
        assert rule.arg_pattern == "git push"

    def test_rule_is_pydantic_model(self) -> None:
        """ApprovalRule should be a Pydantic BaseModel."""
        assert issubclass(ApprovalRule, BaseModel)


class TestApprovalPolicyModel:
    """Verify ApprovalPolicy is a Pydantic BaseModel with rules list."""

    def test_policy_is_pydantic_model(self) -> None:
        """ApprovalPolicy should be a Pydantic BaseModel."""
        assert issubclass(ApprovalPolicy, BaseModel)

    def test_policy_with_rules(self) -> None:
        """Policy accepts a list of ApprovalRule objects."""
        policy = ApprovalPolicy(
            rules=[
                ApprovalRule(tool_name="git_push"),
                ApprovalRule(tool_name="run_command", arg_pattern="rm -rf"),
            ]
        )
        assert len(policy.rules) == 2

    def test_empty_policy(self) -> None:
        """Policy with no rules should instantiate with empty list."""
        policy = ApprovalPolicy(rules=[])
        assert policy.rules == []

    def test_policy_default_empty_rules(self) -> None:
        """Policy with no rules argument should default to empty list."""
        policy = ApprovalPolicy()
        assert policy.rules == []

    def test_json_serialization_roundtrip(self) -> None:
        """ApprovalPolicy should serialize to/from JSON."""
        policy = ApprovalPolicy(
            rules=[
                ApprovalRule(tool_name="git_push"),
                ApprovalRule(tool_name="run_command", arg_pattern="git push"),
            ]
        )
        json_str = policy.model_dump_json()
        restored = ApprovalPolicy.model_validate_json(json_str)
        assert restored == policy


class TestRequiresApprovalToolMatch:
    """Test requires_approval() for exact tool name matching."""

    def test_returns_true_when_tool_in_rules(self) -> None:
        """requires_approval('git_push', {}) returns True when 'git_push' in rules."""
        policy = ApprovalPolicy(rules=[ApprovalRule(tool_name="git_push")])
        assert policy.requires_approval("git_push", {}) is True

    def test_returns_false_when_tool_not_in_rules(self) -> None:
        """requires_approval('read_file', {}) returns False when not in rules."""
        policy = ApprovalPolicy(rules=[ApprovalRule(tool_name="git_push")])
        assert policy.requires_approval("read_file", {}) is False

    def test_multiple_rules_match_any(self) -> None:
        """Approval required if any rule matches the tool name."""
        policy = ApprovalPolicy(
            rules=[
                ApprovalRule(tool_name="git_push"),
                ApprovalRule(tool_name="delete_file"),
            ]
        )
        assert policy.requires_approval("delete_file", {}) is True
        assert policy.requires_approval("read_file", {}) is False


class TestRequiresApprovalArgPattern:
    """Test requires_approval() with arg_pattern regex matching."""

    def test_arg_pattern_matches_command_arg(self) -> None:
        """Arg pattern 'git push' matches command='git push origin main'."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="run_command", arg_pattern="git push")]
        )
        assert policy.requires_approval("run_command", {"command": "git push origin main"}) is True

    def test_arg_pattern_no_match(self) -> None:
        """Arg pattern should not match when no arg value contains the pattern."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="run_command", arg_pattern="git push")]
        )
        assert policy.requires_approval("run_command", {"command": "git status"}) is False

    def test_arg_pattern_matches_any_arg_value(self) -> None:
        """Arg pattern should be checked against all string arg values."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="run_command", arg_pattern="rm -rf")]
        )
        assert (
            policy.requires_approval("run_command", {"command": "rm -rf /tmp", "cwd": "/home"})
            is True
        )

    def test_tool_matches_but_no_arg_pattern_match(self) -> None:
        """When tool matches and arg_pattern is set but args don't match, return False."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="run_command", arg_pattern="git push")]
        )
        assert policy.requires_approval("run_command", {"command": "ls -la"}) is False

    def test_tool_matches_rule_without_arg_pattern(self) -> None:
        """When rule has no arg_pattern, any args is a match (tool name alone is enough)."""
        policy = ApprovalPolicy(rules=[ApprovalRule(tool_name="run_command")])
        assert policy.requires_approval("run_command", {"command": "ls -la"}) is True


class TestRequiresApprovalWildcard:
    """Test wildcard rule: {tool: '*'} matches all tool names."""

    def test_wildcard_matches_any_tool(self) -> None:
        """A rule with tool_name='*' should match any tool."""
        policy = ApprovalPolicy(rules=[ApprovalRule(tool_name="*")])
        assert policy.requires_approval("git_push", {}) is True
        assert policy.requires_approval("read_file", {}) is True
        assert policy.requires_approval("delete_file", {}) is True

    def test_wildcard_with_arg_pattern(self) -> None:
        """Wildcard + arg_pattern: matches any tool when args match the pattern."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="*", arg_pattern="dangerous")]
        )
        assert policy.requires_approval("any_tool", {"x": "dangerous operation"}) is True
        assert policy.requires_approval("any_tool", {"x": "safe operation"}) is False


class TestRequiresApprovalEmptyPolicy:
    """Test empty policy: requires_approval always returns False."""

    def test_empty_rules_always_false(self) -> None:
        """Empty policy should never require approval."""
        policy = ApprovalPolicy(rules=[])
        assert policy.requires_approval("git_push", {}) is False
        assert policy.requires_approval("read_file", {}) is False
        assert policy.requires_approval("run_command", {"command": "rm -rf /"}) is False

    def test_default_policy_always_false(self) -> None:
        """Default-constructed policy should never require approval."""
        policy = ApprovalPolicy()
        assert policy.requires_approval("anything", {}) is False


class TestApprovalSession:
    """Test ApprovalSession per-session pre-grant tracking."""

    def test_session_is_pre_granted_returns_false_initially(self) -> None:
        """A fresh session has no pre-grants."""
        session = ApprovalSession()
        assert session.is_pre_granted("git_push") is False

    def test_session_grant_adds_tool(self) -> None:
        """Granting a tool adds it to the pre-grant set."""
        session = ApprovalSession()
        session.grant("git_push")
        assert session.is_pre_granted("git_push") is True

    def test_session_is_pre_granted_returns_true_after_grant(self) -> None:
        """Multiple tools can be granted independently."""
        session = ApprovalSession()
        session.grant("git_push")
        session.grant("delete_file")
        assert session.is_pre_granted("git_push") is True
        assert session.is_pre_granted("delete_file") is True
        assert session.is_pre_granted("read_file") is False

    def test_session_clear_removes_all_grants(self) -> None:
        """clear() removes every pre-grant."""
        session = ApprovalSession()
        session.grant("git_push")
        session.grant("delete_file")
        session.clear()
        assert session.is_pre_granted("git_push") is False
        assert session.is_pre_granted("delete_file") is False
