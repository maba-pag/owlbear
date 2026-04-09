"""RED-phase tests for TypedDict hook payloads and Handler type alias.

Task: #714 (RED tests for #483)
Tests the contract defined in #483 AC — 9 TypedDict payload classes,
PostToolUseData dual-shape support, Handler type alias, and core __init__
exports.
"""

from __future__ import annotations

from typing import get_type_hints

# ---------------------------------------------------------------------------
# AC2 — 9 TypedDict classes importable from owlbear.core.hooks
# ---------------------------------------------------------------------------


class TestFromAC_TypedDictImports:
    """Each of the 9 TypedDict classes must be importable from owlbear.core.hooks."""

    def test_import_pre_tool_use_data(self) -> None:
        from owlbear.core.hooks import PreToolUseData  # noqa: F401

    def test_import_post_tool_use_data(self) -> None:
        from owlbear.core.hooks import PostToolUseData  # noqa: F401

    def test_import_on_message_data(self) -> None:
        from owlbear.core.hooks import OnMessageData  # noqa: F401

    def test_import_on_error_data(self) -> None:
        from owlbear.core.hooks import OnErrorData  # noqa: F401

    def test_import_session_start_data(self) -> None:
        from owlbear.core.hooks import SessionStartData  # noqa: F401

    def test_import_session_end_data(self) -> None:
        from owlbear.core.hooks import SessionEndData  # noqa: F401

    def test_import_subagent_complete_data(self) -> None:
        from owlbear.core.hooks import SubagentCompleteData  # noqa: F401

    def test_import_task_complete_data(self) -> None:
        from owlbear.core.hooks import TaskCompleteData  # noqa: F401

    def test_import_daemon_startup_data(self) -> None:
        from owlbear.core.hooks import DaemonStartupData  # noqa: F401


# ---------------------------------------------------------------------------
# AC2 (detailed from #483) — each TypedDict has the correct fields
# ---------------------------------------------------------------------------


class TestFromAC_PayloadFieldShapes:
    """Verify each TypedDict declares the expected keys via get_type_hints."""

    def test_pre_tool_use_data_has_tool_name_and_args(self) -> None:
        from owlbear.core.hooks import PreToolUseData

        hints = get_type_hints(PreToolUseData)
        assert "tool_name" in hints
        assert "args" in hints

    def test_on_message_data_has_prompt(self) -> None:
        from owlbear.core.hooks import OnMessageData

        hints = get_type_hints(OnMessageData)
        assert "prompt" in hints

    def test_on_error_data_has_error_and_prompt(self) -> None:
        from owlbear.core.hooks import OnErrorData

        hints = get_type_hints(OnErrorData)
        assert "error" in hints
        assert "prompt" in hints

    def test_session_start_data_has_session_id(self) -> None:
        from owlbear.core.hooks import SessionStartData

        hints = get_type_hints(SessionStartData)
        assert "session_id" in hints

    def test_session_end_data_has_session_id(self) -> None:
        from owlbear.core.hooks import SessionEndData

        hints = get_type_hints(SessionEndData)
        assert "session_id" in hints

    def test_task_complete_data_has_task_id_and_outcome(self) -> None:
        from owlbear.core.hooks import TaskCompleteData

        hints = get_type_hints(TaskCompleteData)
        assert "task_id" in hints
        assert "outcome" in hints

    def test_daemon_startup_data_has_channel_and_config_dir(self) -> None:
        from owlbear.core.hooks import DaemonStartupData

        hints = get_type_hints(DaemonStartupData)
        assert "channel" in hints
        assert "config_dir" in hints

    def test_subagent_complete_data_has_optional_fields(self) -> None:
        """SubagentCompleteData: all fields are NotRequired per AC."""
        from owlbear.core.hooks import SubagentCompleteData

        hints = get_type_hints(SubagentCompleteData, include_extras=True)
        # At minimum these keys should appear in the type hints
        expected = {"task_id", "created_files", "test_files", "result", "verification"}
        assert expected.issubset(set(hints.keys()))


# ---------------------------------------------------------------------------
# AC3 — PostToolUseData accepts both emitter shapes
# ---------------------------------------------------------------------------


class TestFromAC_PostToolUseDataShapes:
    """PostToolUseData must accept HookedToolset and ApprovalGateToolset shapes."""

    def test_hooked_toolset_shape(self) -> None:
        """HookedToolset shape: tool_name + result."""
        from owlbear.core.hooks import PostToolUseData

        payload: PostToolUseData = {"tool_name": "search", "result": [1, 2, 3]}
        assert payload["tool_name"] == "search"
        assert payload["result"] == [1, 2, 3]

    def test_approval_gate_shape(self) -> None:
        """ApprovalGateToolset shape: tool_name + event_type + approval fields."""
        from owlbear.core.hooks import PostToolUseData

        payload: PostToolUseData = {
            "tool_name": "rm_file",
            "event_type": "destructive",
            "approval_required": True,
            "approval_decision": "approved",
        }
        assert payload["tool_name"] == "rm_file"
        assert payload["event_type"] == "destructive"
        assert payload["approval_required"] is True
        assert payload["approval_decision"] == "approved"

    def test_minimal_shape_tool_name_only(self) -> None:
        """Minimal valid shape — just the required tool_name field."""
        from owlbear.core.hooks import PostToolUseData

        payload: PostToolUseData = {"tool_name": "noop"}
        assert payload["tool_name"] == "noop"

    def test_post_tool_use_has_not_required_fields(self) -> None:
        """PostToolUseData should have NotRequired optional fields in hints."""
        from owlbear.core.hooks import PostToolUseData

        hints = get_type_hints(PostToolUseData, include_extras=True)
        # Required field
        assert "tool_name" in hints
        # NotRequired fields from both emitters
        for field in ("result", "event_type", "approval_required", "approval_decision"):
            assert field in hints, f"Missing NotRequired field: {field}"


# ---------------------------------------------------------------------------
# AC4 — Handler type alias is Callable[[dict[str, Any]], None]
# ---------------------------------------------------------------------------


class TestFromAC_HandlerType:
    """Handler must be Callable[[dict[str, Any]], None]."""

    def test_handler_param_is_dict(self) -> None:
        """Handler's first parameter type must be dict[str, Any], not object."""
        from owlbear.core.hooks import Handler

        args = getattr(Handler, "__args__", None)
        assert args is not None, "Handler should be parameterized Callable"
        # Callable[[dict[str, Any]], None] -> __args__ = ([dict[str, Any]], None)
        param_types = args[0]  # the list of parameter types
        assert isinstance(param_types, list), "Expected list of param types"
        assert len(param_types) == 1
        # The param type should be dict (specifically dict[str, Any])
        param = param_types[0]
        origin = getattr(param, "__origin__", param)
        assert origin is dict, f"Handler param should be dict, got {origin}"

    def test_handler_return_is_none(self) -> None:
        """Handler's return type must be None, not object."""
        from owlbear.core.hooks import Handler

        args = getattr(Handler, "__args__", None)
        assert args is not None, "Handler should be parameterized Callable"
        return_type = args[-1]
        assert return_type is type(None), f"Handler return type should be None, got {return_type}"


# ---------------------------------------------------------------------------
# AC5 — all 9 TypedDicts exported in core/__init__.py __all__
# ---------------------------------------------------------------------------


class TestFromAC_CoreInitExports:
    """All 9 TypedDict names must appear in owlbear.core.__all__."""

    EXPECTED_EXPORTS = (
        "PreToolUseData",
        "PostToolUseData",
        "OnMessageData",
        "OnErrorData",
        "SessionStartData",
        "SessionEndData",
        "SubagentCompleteData",
        "TaskCompleteData",
        "DaemonStartupData",
    )

    def test_all_typeddicts_in_core_all(self) -> None:
        from owlbear import core

        all_exports = getattr(core, "__all__", [])
        for name in self.EXPECTED_EXPORTS:
            assert name in all_exports, f"{name} missing from owlbear.core.__all__"

    def test_typeddicts_importable_from_core(self) -> None:
        """Each TypedDict should be directly importable from owlbear.core."""
        from owlbear import core

        for name in self.EXPECTED_EXPORTS:
            assert hasattr(core, name), f"{name} not importable from owlbear.core"


# ---------------------------------------------------------------------------
# Builder-discovered: AC fields missing from test-writer's coverage
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Fields specified in AC but not covered by TestFromAC_* tests."""

    def test_post_tool_use_data_has_grant_ttl_and_grant_max_uses(self) -> None:
        """AC1: PostToolUseData must include grant_ttl and grant_max_uses."""
        from owlbear.core.hooks import PostToolUseData

        hints = get_type_hints(PostToolUseData, include_extras=True)
        assert "grant_ttl" in hints, "Missing NotRequired field: grant_ttl"
        assert "grant_max_uses" in hints, "Missing NotRequired field: grant_max_uses"

    def test_session_start_data_has_workspace_root_and_context(self) -> None:
        """AC1: SessionStartData must include workspace_root and context."""
        from owlbear.core.hooks import SessionStartData

        hints = get_type_hints(SessionStartData, include_extras=True)
        assert "workspace_root" in hints, "Missing NotRequired field: workspace_root"
        assert "context" in hints, "Missing NotRequired field: context"

    def test_session_end_data_has_messages_and_test_results(self) -> None:
        """AC1: SessionEndData must include messages and test_results."""
        from owlbear.core.hooks import SessionEndData

        hints = get_type_hints(SessionEndData, include_extras=True)
        assert "messages" in hints, "Missing NotRequired field: messages"
        assert "test_results" in hints, "Missing NotRequired field: test_results"

    def test_subagent_complete_data_result_accepts_object(self) -> None:
        """AC1: SubagentCompleteData.result should accept any object."""
        from owlbear.core.hooks import SubagentCompleteData

        payload: SubagentCompleteData = {"result": {"nested": True}}
        assert payload["result"] == {"nested": True}

    def test_subagent_complete_data_verification_accepts_dict(self) -> None:
        """AC1: SubagentCompleteData.verification should accept any dict."""
        from owlbear.core.hooks import SubagentCompleteData

        payload: SubagentCompleteData = {"verification": {"passed": True, "coverage": 95}}
        assert payload["verification"] == {"passed": True, "coverage": 95}

    def test_post_tool_use_data_approval_with_grants(self) -> None:
        """PostToolUseData should accept the full ApprovalGateToolset shape."""
        from owlbear.core.hooks import PostToolUseData

        payload: PostToolUseData = {
            "tool_name": "rm_file",
            "event_type": "destructive",
            "approval_required": True,
            "approval_decision": "approved",
            "grant_ttl": 300,
            "grant_max_uses": 5,
        }
        assert payload["grant_ttl"] == 300
        assert payload["grant_max_uses"] == 5
