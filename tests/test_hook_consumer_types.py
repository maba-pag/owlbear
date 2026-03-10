"""RED-phase tests for hook consumer typed payload annotations.

Task: #715 (RED tests for #716)
Tests the contract: each hook consumer's callback method must declare a
specific TypedDict (or dict[str, Any]) parameter type instead of ``object``,
and ``isinstance(data, dict)`` early-return guards must be removed from
``__call__`` methods.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from typing import Any, get_type_hints

# ---------------------------------------------------------------------------
# AC2 — Each consumer's callback accepts its specific TypedDict param type
# ---------------------------------------------------------------------------


class TestFromAC_ConsumerParamAnnotations:  # noqa: N801
    """Each hook consumer callback must declare a typed payload parameter,
    not ``object``.

    AC2 specifies the mapping:
      - CommandSafetyGuard.__call__      -> PreToolUseData
      - URLSafetyGuard.__call__          -> PreToolUseData
      - AutoLintHook.__call__            -> PostToolUseData
      - NotificationHook.__call__        -> dict (mixed events)
      - ObservabilityHook._make_handler  -> dict (mixed events)
      - ContextInjectionHook.__call__    -> SessionStartData
      - SubagentVerificationHook.__call__-> SubagentCompleteData
      - TestVerificationHook.__call__    -> SessionEndData
      - RetrospectiveHook.__call__       -> TaskCompleteData
      - ProgressReporter.on_tool_complete-> PostToolUseData
      - ScreenshotOnErrorHook.handle     -> OnErrorData
    """

    # -- PRE_TOOL_USE consumers -------------------------------------------

    def test_command_safety_guard_accepts_pre_tool_use_data(self) -> None:
        from owlbear.core.command_guard import CommandSafetyGuard
        from owlbear.core.hooks import PreToolUseData

        hints = get_type_hints(CommandSafetyGuard.__call__)
        data_type = hints.get("data")
        assert data_type is PreToolUseData, (
            f"CommandSafetyGuard.__call__ data param should be PreToolUseData, got {data_type}"
        )

    def test_url_safety_guard_accepts_pre_tool_use_data(self) -> None:
        from owlbear.core.hooks import PreToolUseData
        from owlbear.tools.browser.safety import URLSafetyGuard

        hints = get_type_hints(URLSafetyGuard.__call__)
        data_type = hints.get("data")
        assert data_type is PreToolUseData, (
            f"URLSafetyGuard.__call__ data param should be PreToolUseData, got {data_type}"
        )

    # -- POST_TOOL_USE consumers ------------------------------------------

    def test_auto_lint_hook_accepts_post_tool_use_data(self) -> None:
        from owlbear.core.hooks import PostToolUseData
        from owlbear.core.lint_hook import AutoLintHook

        hints = get_type_hints(AutoLintHook.__call__)
        data_type = hints.get("data")
        assert data_type is PostToolUseData, (
            f"AutoLintHook.__call__ data param should be PostToolUseData, got {data_type}"
        )

    def test_progress_reporter_on_tool_complete_accepts_post_tool_use_data(self) -> None:
        from owlbear.core.hooks import PostToolUseData
        from owlbear.core.progress import ProgressReporter

        hints = get_type_hints(ProgressReporter.on_tool_complete)
        data_type = hints.get("data")
        assert data_type is PostToolUseData, (
            f"ProgressReporter.on_tool_complete data param should be "
            f"PostToolUseData, got {data_type}"
        )

    # -- Mixed-event consumers (dict[str, Any]) ---------------------------

    def test_notification_hook_accepts_dict(self) -> None:
        """NotificationHook registers on multiple events — uses dict[str, Any]."""
        from owlbear.core.notification_hook import NotificationHook

        hints = get_type_hints(NotificationHook.__call__)
        data_type = hints.get("data")
        # Should be dict[str, Any] — check origin is dict
        origin = getattr(data_type, "__origin__", data_type)
        assert origin is dict, (
            f"NotificationHook.__call__ data param should be dict[str, Any], got {data_type}"
        )

    def test_observability_hook_handler_accepts_dict(self) -> None:
        """ObservabilityHook._make_handler closure — uses dict[str, Any]."""
        from owlbear.core.hooks import HookEvent
        from owlbear.core.observability import EventStore, ObservabilityHook

        store = EventStore.__new__(EventStore)
        hook = ObservabilityHook.__new__(ObservabilityHook)
        hook._store = store
        hook._timers = {}
        handler = hook._make_handler(HookEvent.PRE_TOOL_USE)
        handler_hints = get_type_hints(handler)
        data_type = handler_hints.get("data")
        origin = getattr(data_type, "__origin__", data_type)
        assert origin is dict, (
            f"ObservabilityHook._make_handler closure data param should be "
            f"dict[str, Any], got {data_type}"
        )

    # -- SESSION_START consumer -------------------------------------------

    def test_context_injection_hook_accepts_session_start_data(self) -> None:
        from owlbear.core.context_hook import ContextInjectionHook
        from owlbear.core.hooks import SessionStartData

        hints = get_type_hints(ContextInjectionHook.__call__)
        data_type = hints.get("data")
        assert data_type is SessionStartData, (
            f"ContextInjectionHook.__call__ data param should be SessionStartData, got {data_type}"
        )

    # -- SUBAGENT_COMPLETE consumer ---------------------------------------

    def test_subagent_verification_hook_accepts_subagent_complete_data(self) -> None:
        from owlbear.core.hooks import SubagentCompleteData
        from owlbear.core.subagent_hook import SubagentVerificationHook

        hints = get_type_hints(SubagentVerificationHook.__call__)
        data_type = hints.get("data")
        assert data_type is SubagentCompleteData, (
            f"SubagentVerificationHook.__call__ data param should be "
            f"SubagentCompleteData, got {data_type}"
        )

    # -- SESSION_END consumer ---------------------------------------------

    def test_test_verification_hook_accepts_session_end_data(self) -> None:
        from owlbear.core.hooks import SessionEndData
        from owlbear.core.test_hook import TestVerificationHook

        hints = get_type_hints(TestVerificationHook.__call__)
        data_type = hints.get("data")
        assert data_type is SessionEndData, (
            f"TestVerificationHook.__call__ data param should be SessionEndData, got {data_type}"
        )

    # -- TASK_COMPLETE consumer -------------------------------------------

    def test_retrospective_hook_accepts_task_complete_data(self) -> None:
        from owlbear.core.hooks import TaskCompleteData
        from owlbear.core.retrospective_hook import RetrospectiveHook

        hints = get_type_hints(RetrospectiveHook.__call__)
        data_type = hints.get("data")
        assert data_type is TaskCompleteData, (
            f"RetrospectiveHook.__call__ data param should be TaskCompleteData, got {data_type}"
        )

    # -- ON_ERROR consumer ------------------------------------------------

    def test_screenshot_on_error_hook_handle_accepts_on_error_data(self) -> None:
        from owlbear.core.hooks import OnErrorData
        from owlbear.tools.screenshot_hook import ScreenshotOnErrorHook

        hints = get_type_hints(ScreenshotOnErrorHook.handle)
        data_type = hints.get("data")
        assert data_type is OnErrorData, (
            f"ScreenshotOnErrorHook.handle data param should be OnErrorData, got {data_type}"
        )


# ---------------------------------------------------------------------------
# AC3 — No isinstance(data, dict) early-return guards in __call__ methods
# ---------------------------------------------------------------------------


class TestFromAC_NoIsinstanceGuards:  # noqa: N801
    """Consumer __call__ methods must not contain ``isinstance(data, dict)``
    early-return guards.  Once the parameter is typed, the guard is dead code.

    AC3 specifies zero such guards remain.  We inspect the source AST of
    each __call__ method for the pattern:
      ``if not isinstance(data, dict): return``
    """

    @staticmethod
    def _has_isinstance_dict_guard(method: Any) -> bool:
        """Return True if *method* contains ``if not isinstance(data, dict): return``."""
        source = textwrap.dedent(inspect.getsource(method))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            # Pattern: ``if not isinstance(data, dict)``
            test = node.test
            if (
                isinstance(test, ast.UnaryOp)
                and isinstance(test.op, ast.Not)
                and isinstance(test.operand, ast.Call)
                and isinstance(test.operand.func, ast.Name)
                and test.operand.func.id == "isinstance"
                and len(test.operand.args) == 2
                and isinstance(test.operand.args[0], ast.Name)
                and test.operand.args[0].id == "data"
                and isinstance(test.operand.args[1], ast.Name)
                and test.operand.args[1].id == "dict"
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Return)
                and node.body[0].value is None
            ):
                return True
            # Also catch positive form: ``if isinstance(data, dict):`` used as
            # a conditional guard wrapping the method body
            if (
                isinstance(test, ast.Call)
                and isinstance(test.func, ast.Name)
                and test.func.id == "isinstance"
                and len(test.args) == 2
                and isinstance(test.args[0], ast.Name)
                and test.args[0].id == "data"
                and isinstance(test.args[1], ast.Name)
                and test.args[1].id == "dict"
            ):
                return True
        return False

    def test_command_safety_guard_no_isinstance_guard(self) -> None:
        from owlbear.core.command_guard import CommandSafetyGuard

        assert not self._has_isinstance_dict_guard(CommandSafetyGuard.__call__), (
            "CommandSafetyGuard.__call__ still has isinstance(data, dict) guard"
        )

    def test_url_safety_guard_no_isinstance_guard(self) -> None:
        from owlbear.tools.browser.safety import URLSafetyGuard

        assert not self._has_isinstance_dict_guard(URLSafetyGuard.__call__), (
            "URLSafetyGuard.__call__ still has isinstance(data, dict) guard"
        )

    def test_auto_lint_hook_no_isinstance_guard(self) -> None:
        from owlbear.core.lint_hook import AutoLintHook

        assert not self._has_isinstance_dict_guard(AutoLintHook.__call__), (
            "AutoLintHook.__call__ still has isinstance(data, dict) guard"
        )

    def test_notification_hook_no_isinstance_guard(self) -> None:
        from owlbear.core.notification_hook import NotificationHook

        assert not self._has_isinstance_dict_guard(NotificationHook.__call__), (
            "NotificationHook.__call__ still has isinstance(data, dict) guard"
        )

    def test_context_injection_hook_no_isinstance_guard(self) -> None:
        from owlbear.core.context_hook import ContextInjectionHook

        assert not self._has_isinstance_dict_guard(ContextInjectionHook.__call__), (
            "ContextInjectionHook.__call__ still has isinstance(data, dict) guard"
        )

    def test_subagent_verification_hook_no_isinstance_guard(self) -> None:
        from owlbear.core.subagent_hook import SubagentVerificationHook

        assert not self._has_isinstance_dict_guard(SubagentVerificationHook.__call__), (
            "SubagentVerificationHook.__call__ still has isinstance(data, dict) guard"
        )

    def test_test_verification_hook_no_isinstance_guard(self) -> None:
        from owlbear.core.test_hook import TestVerificationHook

        assert not self._has_isinstance_dict_guard(TestVerificationHook.__call__), (
            "TestVerificationHook.__call__ still has isinstance(data, dict) guard"
        )

    def test_retrospective_hook_no_isinstance_guard(self) -> None:
        from owlbear.core.retrospective_hook import RetrospectiveHook

        assert not self._has_isinstance_dict_guard(RetrospectiveHook.__call__), (
            "RetrospectiveHook.__call__ still has isinstance(data, dict) guard"
        )
