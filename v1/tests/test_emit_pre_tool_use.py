"""Tests for emit_pre_tool_use() — DRY extraction of _emit_hook (#518).

RED phase: all tests must fail until the builder implements the utility.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Paths for static analysis checks
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "owlbear"
_HOOKS_PY = _SRC_ROOT / "core" / "hooks.py"
_GIT_LOCAL_PY = _SRC_ROOT / "tools" / "git_local.py"
_KANBAN_PY = _SRC_ROOT / "tools" / "kanban.py"
_GITHUB_API_PY = _SRC_ROOT / "tools" / "github_api.py"
_TERMINAL_PY = _SRC_ROOT / "tools" / "terminal.py"


class TestFromAC_EmitPreToolUseExists:
    """AC: async def emit_pre_tool_use() added to hooks.py and exported."""

    def test_importable_from_hooks_module(self) -> None:
        """The function is importable from owlbear.core.hooks."""
        from owlbear.core.hooks import emit_pre_tool_use  # noqa: F401

    def test_is_async_function(self) -> None:
        """emit_pre_tool_use must be an async (coroutine) function."""
        from owlbear.core.hooks import emit_pre_tool_use

        assert inspect.iscoroutinefunction(emit_pre_tool_use)

    def test_exported_in_dunder_all(self) -> None:
        """emit_pre_tool_use must appear in hooks.__all__."""
        import owlbear.core.hooks as hooks_mod

        assert hasattr(hooks_mod, "__all__"), "__all__ not defined in hooks.py"
        assert "emit_pre_tool_use" in hooks_mod.__all__

    def test_signature_accepts_hooks_tool_name_args(self) -> None:
        """Signature: (hooks, tool_name, args) with correct annotations."""
        from owlbear.core.hooks import HookRegistry, emit_pre_tool_use

        sig = inspect.signature(emit_pre_tool_use)
        params = list(sig.parameters.keys())

        assert params == ["hooks", "tool_name", "args"], (
            f"Expected params [hooks, tool_name, args], got {params}"
        )

        # Return annotation should be None
        assert sig.return_annotation is None

        # hooks param should accept HookRegistry | None
        hooks_param = sig.parameters["hooks"]
        ann = hooks_param.annotation
        # Accept both HookRegistry | None and Optional[HookRegistry]
        assert HookRegistry in (getattr(ann, "__args__", ()) or ()), (
            f"hooks param annotation should include HookRegistry, got {ann}"
        )


class TestFromAC_EmitPreToolUseBehavior:
    """AC: null-guard on hooks inside the utility; emits PRE_TOOL_USE."""

    @pytest.mark.asyncio
    async def test_none_hooks_is_noop(self) -> None:
        """Calling with hooks=None must not raise — silent no-op."""
        from owlbear.core.hooks import emit_pre_tool_use

        # Must not raise
        await emit_pre_tool_use(None, "some_tool", {"key": "value"})

    @pytest.mark.asyncio
    async def test_emits_pre_tool_use_event(self) -> None:
        """With a real registry, PRE_TOOL_USE fires with correct payload."""
        from owlbear.core.hooks import HookEvent, HookRegistry, emit_pre_tool_use

        handler = AsyncMock()
        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, handler)

        await emit_pre_tool_use(registry, "my_tool", {"arg1": 42})

        handler.assert_awaited_once()
        payload = handler.call_args[0][0]
        assert payload["tool_name"] == "my_tool"
        assert payload["args"] == {"arg1": 42}

    @pytest.mark.asyncio
    async def test_payload_shape_matches_pre_tool_use_data(self) -> None:
        """Payload must have exactly 'tool_name' and 'args' keys."""
        from owlbear.core.hooks import HookEvent, HookRegistry, emit_pre_tool_use

        captured: list[dict[str, Any]] = []

        def sync_handler(data: dict[str, Any]) -> None:
            captured.append(data)

        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, sync_handler)

        await emit_pre_tool_use(registry, "test_tool", {"x": 1})

        assert len(captured) == 1
        assert set(captured[0].keys()) == {"tool_name", "args"}

    @pytest.mark.asyncio
    async def test_empty_args_dict(self) -> None:
        """Utility works with an empty args dict."""
        from owlbear.core.hooks import HookEvent, HookRegistry, emit_pre_tool_use

        handler = AsyncMock()
        registry = HookRegistry()
        registry.register(HookEvent.PRE_TOOL_USE, handler)

        await emit_pre_tool_use(registry, "no_args_tool", {})

        handler.assert_awaited_once()
        assert handler.call_args[0][0]["args"] == {}


class TestFromAC_NoEmitHookMethodsRemain:
    """AC: No _emit_hook methods remain in git_local, kanban, github_api.

    Also: no inline PRE_TOOL_USE emission in terminal.py.
    """

    @staticmethod
    def _has_method(filepath: Path, method_name: str) -> bool:
        """Check if *filepath* defines a method named *method_name* via AST."""
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
        for node in ast.walk(tree):
            is_func = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if is_func and node.name == method_name:
                return True
        return False

    def test_git_local_no_emit_hook(self) -> None:
        assert not self._has_method(_GIT_LOCAL_PY, "_emit_hook"), (
            "git_local.py still defines _emit_hook"
        )

    def test_kanban_no_emit_hook(self) -> None:
        assert not self._has_method(_KANBAN_PY, "_emit_hook"), "kanban.py still defines _emit_hook"

    def test_github_api_no_emit_hook(self) -> None:
        assert not self._has_method(_GITHUB_API_PY, "_emit_hook"), (
            "github_api.py still defines _emit_hook"
        )

    def test_terminal_no_inline_hook_emission(self) -> None:
        """terminal.py should not contain inline HookEvent.PRE_TOOL_USE emit."""
        source = _TERMINAL_PY.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(_TERMINAL_PY))

        # Walk for `self._hooks.emit(HookEvent.PRE_TOOL_USE, ...)` patterns
        # inside any function body (inline usage).  The builder should replace
        # them with `await emit_pre_tool_use(...)`.
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "emit":
                # Check if the call has HookEvent.PRE_TOOL_USE as first arg
                # by looking at the parent Call node's args
                # We detect self._hooks.emit(HookEvent.PRE_TOOL_USE, ...) pattern
                # in the source text more reliably:
                pass  # fall through to string check

        # Simpler: ensure no `self._hooks.emit(` pattern remains in terminal.py
        assert "self._hooks.emit(" not in source, (
            "terminal.py still has inline self._hooks.emit() — "
            "should use emit_pre_tool_use() utility"
        )


class TestFromAC_CallSitesUseUtility:
    """AC: All 4 call-sites use await emit_pre_tool_use(self._hooks, ...)."""

    @staticmethod
    def _source_contains(filepath: Path, text: str) -> bool:
        return text in filepath.read_text(encoding="utf-8")

    def test_git_local_calls_emit_pre_tool_use(self) -> None:
        assert self._source_contains(_GIT_LOCAL_PY, "emit_pre_tool_use"), (
            "git_local.py does not call emit_pre_tool_use"
        )

    def test_kanban_calls_emit_pre_tool_use(self) -> None:
        assert self._source_contains(_KANBAN_PY, "emit_pre_tool_use"), (
            "kanban.py does not call emit_pre_tool_use"
        )

    def test_github_api_calls_emit_pre_tool_use(self) -> None:
        assert self._source_contains(_GITHUB_API_PY, "emit_pre_tool_use"), (
            "github_api.py does not call emit_pre_tool_use"
        )

    def test_terminal_calls_emit_pre_tool_use(self) -> None:
        assert self._source_contains(_TERMINAL_PY, "emit_pre_tool_use"), (
            "terminal.py does not call emit_pre_tool_use"
        )
