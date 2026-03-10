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


class TestFromAC_TypedDictImports:  # noqa: N801
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


class TestFromAC_PayloadFieldShapes:  # noqa: N801
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


class TestFromAC_PostToolUseDataShapes:  # noqa: N801
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


class TestFromAC_HandlerType:  # noqa: N801
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


class TestFromAC_CoreInitExports:  # noqa: N801
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
