"""RED-phase tests for #860 — BlockedURLError dependency inversion contract.

Guards the move of BlockedURLError from owlbear.tools.browser.safety to
owlbear.core.exceptions, and verifies that the resulting clean-process import
regression is resolved so owlbear.daemon can be imported without manual
owlbear.tools pre-seeding.
"""

from __future__ import annotations

import ast
import inspect
import subprocess
import sys


class TestFromAC_BlockedURLErrorLocation:  # noqa: N801
    """BlockedURLError must be defined in owlbear.core.exceptions (task #850)."""

    # -- AC2: structural — errors.py must not import from tools.browser.safety --

    def test_errors_no_import_from_browser_safety(self) -> None:
        """errors.py must not contain any import from owlbear.tools.browser.safety."""
        import owlbear.core.errors as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "tools.browser.safety" not in node.module, (
                    f"errors.py has inverted dependency: imports from {node.module}"
                )

    # -- AC3: BlockedURLError must originate in owlbear.core.exceptions ---------

    def test_blocked_url_error_module(self) -> None:
        """BlockedURLError.__module__ must resolve to owlbear.core.exceptions."""
        from owlbear.core.exceptions import BlockedURLError  # ImportError until #850

        assert BlockedURLError.__module__ == "owlbear.core.exceptions"

    def test_classify_error_returns_permanent(self) -> None:
        """classify_error must map BlockedURLError to PERMANENT after relocation."""
        from owlbear.core.errors import ErrorCategory, classify_error
        from owlbear.core.exceptions import BlockedURLError

        err = BlockedURLError("http://blocked.example.com", r"blocked\.example\.com")
        assert classify_error(err) == ErrorCategory.PERMANENT


class TestFromAC_DaemonCleanImport:  # noqa: N801
    """A fresh subprocess must import owlbear.daemon without owlbear.tools pre-seeding."""

    # -- AC4: cold import of owlbear.daemon without tools pre-seeding -----------

    def test_daemon_import_without_tools_preseeding(self) -> None:
        """Fresh subprocess can import owlbear.daemon with no owlbear.tools pre-seeding."""
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                ("from owlbear.daemon import _log_to_journal; print('ok')"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"owlbear.daemon import failed without owlbear.tools pre-seeding:\n{result.stderr}"
        )

    # -- AC5: owlbear.config then owlbear.daemon, no manual pre-seeding ---------

    def test_daemon_import_config_then_daemon(self) -> None:
        """Fresh subprocess: import owlbear.config then owlbear.daemon, then verify
        BlockedURLError is importable from owlbear.core.exceptions with no pre-seeding.
        """
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                (
                    "import owlbear.config; "
                    "from owlbear.daemon import _log_to_journal; "
                    # After #850 BlockedURLError lives in owlbear.core.exceptions;
                    # this line causes ImportError until that move is complete.
                    "from owlbear.core.exceptions import BlockedURLError; "
                    "assert BlockedURLError.__module__ == 'owlbear.core.exceptions'; "
                    "print('ok')"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            "owlbear.daemon import failed after owlbear.config with no pre-seeding:\n"
            + result.stderr
        )
