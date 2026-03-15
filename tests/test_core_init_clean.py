"""Tests for core/__init__.py re-export removal (#812).

Verifies the contract: owlbear.core must NOT re-export symbols from submodules
and must NOT define __all__. All imports should go through deep paths
(e.g. ``from owlbear.core.agent import OwlBearAgent``).
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# AC: Remove re-exports and __all__ from core/__init__.py
# ---------------------------------------------------------------------------

_PREVIOUSLY_EXPORTED = [
    "AgentRole",
    "DaemonStartupData",
    "HookEvent",
    "HookRegistry",
    "OnErrorData",
    "OnMessageData",
    "OwlBearAgent",
    "OwlBearDeps",
    "OwlBearError",
    "PostToolUseData",
    "PreToolUseData",
    "RolePolicy",
    "SessionEndData",
    "SessionStartData",
    "SubagentCompleteData",
    "TaskCompleteData",
]


class TestFromAC_CoreInitNoReExports:  # noqa: N801
    """core/__init__.py must not re-export symbols or define __all__."""

    def test_no_all_attribute(self) -> None:
        """__all__ must not be defined after re-export removal."""
        import owlbear.core

        assert not hasattr(owlbear.core, "__all__"), (
            "owlbear.core still defines __all__; re-exports not removed"
        )

    @pytest.mark.parametrize("symbol", _PREVIOUSLY_EXPORTED)
    def test_symbol_not_in_namespace(self, symbol: str) -> None:
        """Previously re-exported symbols must not be accessible on owlbear.core."""
        import owlbear.core

        assert not hasattr(owlbear.core, symbol), (
            f"owlbear.core.{symbol} still accessible; re-export not removed"
        )
