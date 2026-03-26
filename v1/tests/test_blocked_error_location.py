"""Tests for #548 — BlockedCommandError lives in core/errors.py, not command_guard.py.

Verifies the refactoring contract: BlockedCommandError is *defined* in
``owlbear.core.errors`` (not just re-exported), and no inverted dependency
exists from errors → command_guard.
"""

from __future__ import annotations

import ast
import inspect


class TestFromAC_BlockedCommandErrorLocation:
    """BlockedCommandError must be defined in owlbear.core.errors."""

    # -- AC: class defined in errors.py (not command_guard.py) ---------------

    def test_module_attr_is_errors(self) -> None:
        """``BlockedCommandError.__module__`` must be ``owlbear.core.errors``."""
        from owlbear.core.errors import BlockedCommandError

        assert BlockedCommandError.__module__ == "owlbear.core.errors"

    # -- AC: no inverted dependency (errors must NOT import from command_guard)

    def test_errors_no_import_from_command_guard(self) -> None:
        """``errors.py`` must not contain any import from ``command_guard``."""
        import owlbear.core.errors as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "command_guard" not in node.module, (
                    f"errors.py has inverted dependency: imports from {node.module}"
                )

    # -- AC: command_guard imports BlockedCommandError FROM errors -----------

    def test_command_guard_imports_from_errors(self) -> None:
        """``command_guard.py`` must import BlockedCommandError from errors."""
        import owlbear.core.command_guard as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "errors" in node.module
            ):
                for alias in node.names:
                    if alias.name == "BlockedCommandError":
                        found = True
        assert found, (
            "command_guard.py should import BlockedCommandError from owlbear.core.errors"
        )


class TestFromAC_BlockedCommandErrorPreserved:
    """Behavioral contract — BlockedCommandError still works after the move."""

    def test_inherits_owlbearerror(self) -> None:
        """BlockedCommandError must remain an OwlBearError subclass."""
        from owlbear.core.errors import BlockedCommandError
        from owlbear.core.exceptions import OwlBearError

        assert issubclass(BlockedCommandError, OwlBearError)

    def test_stores_command_and_pattern(self) -> None:
        """Constructor must still accept and store command + pattern."""
        from owlbear.core.errors import BlockedCommandError

        err = BlockedCommandError("rm -rf /", r"rm\s+-rf")
        assert err.command == "rm -rf /"
        assert err.pattern == r"rm\s+-rf"

    def test_classify_error_returns_permanent(self) -> None:
        """classify_error must still map BlockedCommandError to PERMANENT."""
        from owlbear.core.errors import (
            BlockedCommandError,
            ErrorCategory,
            classify_error,
        )

        err = BlockedCommandError("drop table", r"drop")
        assert classify_error(err) == ErrorCategory.PERMANENT
