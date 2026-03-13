"""Tests for owlbear.safety.policy — ApprovalPolicy model.

TDD red-phase tests for task #338. The module ``owlbear.safety.policy``
does not exist yet — all tests are expected to fail on import until the
implementation task is completed.

Extended for task #655 — GrantRecord and scoped ApprovalSession.
"""

from __future__ import annotations

from unittest.mock import patch

from pydantic import BaseModel

from owlbear.safety.policy import (
    ApprovalPolicy,
    ApprovalRule,
    ApprovalSession,
    GrantRecord,
)


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
        policy = ApprovalPolicy(rules=[ApprovalRule(tool_name="run_command", arg_pattern="rm -rf")])
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
        policy = ApprovalPolicy(rules=[ApprovalRule(tool_name="*", arg_pattern="dangerous")])
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


# ==========================================================================
# Task #655 — GrantRecord and scoped ApprovalSession
# ==========================================================================


class TestGrantRecordDataclass:
    """GrantRecord has the required fields."""

    def test_grant_record_fields(self) -> None:
        """GrantRecord has tool_name, granted_at, remaining_uses, ttl, arg_pattern."""
        record = GrantRecord(
            tool_name="git_push",
            granted_at=100.0,
            remaining_uses=5,
            ttl=60.0,
            arg_pattern=r"origin main",
        )
        assert record.tool_name == "git_push"
        assert record.granted_at == 100.0
        assert record.remaining_uses == 5
        assert record.ttl == 60.0
        assert record.arg_pattern == r"origin main"

    def test_grant_record_optional_fields(self) -> None:
        """remaining_uses, ttl, arg_pattern can be None."""
        record = GrantRecord(
            tool_name="deploy",
            granted_at=50.0,
            remaining_uses=None,
            ttl=None,
            arg_pattern=None,
        )
        assert record.remaining_uses is None
        assert record.ttl is None
        assert record.arg_pattern is None


# ---------------------------------------------------------------------------
# AC: Grant with max_uses=3 allows 3 calls then denies
# ---------------------------------------------------------------------------


class TestMaxUses:
    """GrantRecord with remaining_uses limits how many times a grant can fire."""

    def test_max_uses_allows_exactly_n_calls(self) -> None:
        """Grant with max_uses=3 returns True 3 times then False."""
        session = ApprovalSession()
        session.grant("git_push", max_uses=3)

        assert session.is_pre_granted("git_push") is True
        assert session.is_pre_granted("git_push") is True
        assert session.is_pre_granted("git_push") is True
        assert session.is_pre_granted("git_push") is False

    def test_max_uses_one_is_single_shot(self) -> None:
        """max_uses=1 allows exactly one call."""
        session = ApprovalSession()
        session.grant("deploy", max_uses=1)

        assert session.is_pre_granted("deploy") is True
        assert session.is_pre_granted("deploy") is False

    def test_exhausted_grant_cleaned_up(self) -> None:
        """After max_uses exhausted, the grant entry is removed."""
        session = ApprovalSession()
        session.grant("deploy", max_uses=1)

        session.is_pre_granted("deploy")  # use the single grant
        # Grant should be cleaned up
        assert session.is_pre_granted("deploy") is False

    def test_max_uses_zero_denied_immediately(self) -> None:
        """max_uses=0 denies on the very first check and cleans up."""
        session = ApprovalSession()
        session.grant("deploy", max_uses=0)

        assert session.is_pre_granted("deploy") is False
        assert "deploy" not in session._grants


# ---------------------------------------------------------------------------
# AC: Grant with ttl=1.0 expires after time passes (mock monotonic)
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    """GrantRecord with ttl expires after the specified duration."""

    def test_ttl_grant_valid_within_window(self) -> None:
        """Grant with ttl=10.0 is valid immediately after creation."""
        session = ApprovalSession()
        session.grant("git_push", ttl=10.0)

        assert session.is_pre_granted("git_push") is True

    def test_ttl_grant_expires_after_duration(self) -> None:
        """Grant with ttl=1.0 expires when monotonic clock advances past it."""
        with patch("owlbear.safety.policy.monotonic", return_value=100.0):
            session = ApprovalSession()
            session.grant("git_push", ttl=1.0)

        with patch("owlbear.safety.policy.monotonic", return_value=101.5):
            assert session.is_pre_granted("git_push") is False

    def test_ttl_grant_valid_just_before_expiry(self) -> None:
        """Grant is still valid at exactly ttl boundary."""
        with patch("owlbear.safety.policy.monotonic", return_value=100.0):
            session = ApprovalSession()
            session.grant("git_push", ttl=5.0)

        with patch("owlbear.safety.policy.monotonic", return_value=105.0):
            assert session.is_pre_granted("git_push") is True

    def test_expired_grant_cleaned_up(self) -> None:
        """Expired grants are removed from internal storage on check."""
        with patch("owlbear.safety.policy.monotonic", return_value=100.0):
            session = ApprovalSession()
            session.grant("git_push", ttl=1.0)

        with patch("owlbear.safety.policy.monotonic", return_value=200.0):
            session.is_pre_granted("git_push")  # triggers cleanup
            assert "git_push" not in session._grants


# ---------------------------------------------------------------------------
# AC: Grant with arg_pattern allows matching args, denies non-matching
# ---------------------------------------------------------------------------


class TestArgPattern:
    """GrantRecord with arg_pattern filters by argument values."""

    def test_matching_args_allowed(self) -> None:
        """Args matching the pattern pass the check."""
        session = ApprovalSession()
        session.grant("git_push", arg_pattern=r"origin main")

        assert session.is_pre_granted("git_push", args={"ref": "origin main"}) is True

    def test_non_matching_args_denied(self) -> None:
        """Args not matching the pattern are denied."""
        session = ApprovalSession()
        session.grant("git_push", arg_pattern=r"^origin main$")

        assert session.is_pre_granted("git_push", args={"ref": "origin --force main"}) is False

    def test_regex_pattern_matching(self) -> None:
        """Arg pattern is treated as a regex."""
        session = ApprovalSession()
        session.grant("git_push", arg_pattern=r"^origin (main|develop)$")

        assert session.is_pre_granted("git_push", args={"ref": "origin main"}) is True
        assert session.is_pre_granted("git_push", args={"ref": "origin develop"}) is True
        assert session.is_pre_granted("git_push", args={"ref": "origin feature/x"}) is False

    def test_no_pattern_matches_any_args(self) -> None:
        """Grant without arg_pattern matches regardless of args."""
        session = ApprovalSession()
        session.grant("git_push")

        assert session.is_pre_granted("git_push", args={"ref": "anything"}) is True

    def test_pattern_checked_against_all_string_args(self) -> None:
        """Pattern is searched across all string-valued args."""
        session = ApprovalSession()
        session.grant("run_command", arg_pattern=r"safe_script")

        assert (
            session.is_pre_granted(
                "run_command",
                args={"cmd": "safe_script.sh", "cwd": "/work"},
            )
            is True
        )
        assert (
            session.is_pre_granted(
                "run_command",
                args={"cmd": "dangerous.sh", "cwd": "/work"},
            )
            is False
        )


# ---------------------------------------------------------------------------
# AC: Grant with no constraints behaves like current blanket grant
# ---------------------------------------------------------------------------


class TestBlanketGrant:
    """Grant with no max_uses/ttl/arg_pattern behaves like old set[str] grant."""

    def test_unlimited_grant_always_valid(self) -> None:
        """Grant with no constraints allows unlimited uses."""
        session = ApprovalSession()
        session.grant("git_push")

        for _ in range(100):
            assert session.is_pre_granted("git_push") is True

    def test_grant_with_policy_defaults(self) -> None:
        """grant() with no kwargs uses policy defaults when provided."""
        policy = ApprovalPolicy(default_grant_ttl=300.0, default_max_uses=10)
        session = ApprovalSession(policy=policy)
        session.grant("git_push")

        # Should use the policy defaults (max_uses=10)
        for _ in range(10):
            assert session.is_pre_granted("git_push") is True
        assert session.is_pre_granted("git_push") is False

    def test_grant_explicit_overrides_policy_defaults(self) -> None:
        """Explicit kwargs override policy defaults."""
        policy = ApprovalPolicy(default_grant_ttl=300.0, default_max_uses=10)
        session = ApprovalSession(policy=policy)
        session.grant("git_push", max_uses=2)

        assert session.is_pre_granted("git_push") is True
        assert session.is_pre_granted("git_push") is True
        assert session.is_pre_granted("git_push") is False


# ---------------------------------------------------------------------------
# AC: Backward compat — is_pre_granted(tool_name) still works when args omitted
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    """Existing code calling is_pre_granted(name) without args still works."""

    def test_is_pre_granted_no_args_param(self) -> None:
        """is_pre_granted(tool_name) with no args still returns True for grants."""
        session = ApprovalSession()
        session.grant("git_push")

        assert session.is_pre_granted("git_push") is True

    def test_grant_no_kwargs(self) -> None:
        """grant(tool_name) with no kwargs creates a working grant."""
        session = ApprovalSession()
        session.grant("git_push")

        assert session.is_pre_granted("git_push") is True

    def test_non_granted_tool_returns_false(self) -> None:
        """is_pre_granted for a non-granted tool still returns False."""
        session = ApprovalSession()

        assert session.is_pre_granted("run_command") is False

    def test_clear_removes_all_scoped_grants(self) -> None:
        """clear() removes all grants just like the old set-based clear()."""
        session = ApprovalSession()
        session.grant("git_push")
        session.grant("deploy")

        session.clear()

        assert session.is_pre_granted("git_push") is False
        assert session.is_pre_granted("deploy") is False


# ---------------------------------------------------------------------------
# AC: ApprovalPolicy gains default_grant_ttl and default_max_uses
# ---------------------------------------------------------------------------


class TestPolicyGrantDefaults:
    """ApprovalPolicy has configurable default grant limits."""

    def test_default_grant_ttl_field(self) -> None:
        """ApprovalPolicy has default_grant_ttl with default=300.0."""
        policy = ApprovalPolicy()
        assert policy.default_grant_ttl == 300.0

    def test_default_max_uses_field(self) -> None:
        """ApprovalPolicy has default_max_uses with default=10."""
        policy = ApprovalPolicy()
        assert policy.default_max_uses == 10

    def test_custom_policy_defaults(self) -> None:
        """Policy defaults can be overridden."""
        policy = ApprovalPolicy(default_grant_ttl=60.0, default_max_uses=5)
        assert policy.default_grant_ttl == 60.0
        assert policy.default_max_uses == 5

    def test_none_max_uses_means_unlimited(self) -> None:
        """default_max_uses=None means grants are unlimited by default."""
        policy = ApprovalPolicy(default_max_uses=None)
        assert policy.default_max_uses is None
