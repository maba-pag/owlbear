"""Tests for owlbear.process — shared process-alive utility."""

from __future__ import annotations

import os
from unittest.mock import patch


class TestFromAC_IsProcessAlive:  # noqa: N801
    """Contract tests for is_process_alive(pid) in owlbear.process.

    AC: New file src/owlbear/process.py with public
    is_process_alive(pid: int) -> bool using os.kill(pid, 0).
    """

    # --- Happy paths ---

    def test_alive_pid_returns_true(self) -> None:
        """os.kill(pid, 0) succeeds → True."""
        from owlbear.process import is_process_alive

        with patch("owlbear.process.os.kill"):
            assert is_process_alive(12345) is True

    def test_current_process_is_alive(self) -> None:
        """Current process should report alive (integration-style)."""
        from owlbear.process import is_process_alive

        assert is_process_alive(os.getpid()) is True

    # --- Error paths ---

    def test_dead_pid_returns_false_process_lookup_error(self) -> None:
        """os.kill raises ProcessLookupError → False."""
        from owlbear.process import is_process_alive

        with patch(
            "owlbear.process.os.kill",
            side_effect=ProcessLookupError("No such process"),
        ):
            assert is_process_alive(99999) is False

    def test_dead_pid_returns_false_os_error(self) -> None:
        """os.kill raises OSError → False."""
        from owlbear.process import is_process_alive

        with patch(
            "owlbear.process.os.kill",
            side_effect=OSError("mocked"),
        ):
            assert is_process_alive(99999) is False

    # --- Edge / boundary ---

    def test_signal_zero_is_used(self) -> None:
        """Verify os.kill is called with signal 0 (probe, not terminate)."""
        from owlbear.process import is_process_alive

        with patch("owlbear.process.os.kill") as mock_kill:
            is_process_alive(42)
            mock_kill.assert_called_once_with(42, 0)

    def test_return_type_is_bool(self) -> None:
        """Return value must be exactly bool, not truthy int."""
        from owlbear.process import is_process_alive

        with patch("owlbear.process.os.kill"):
            result = is_process_alive(1)
            assert isinstance(result, bool)

    def test_permission_error_subclass_of_os_error(self) -> None:
        """PermissionError (subclass of OSError) should also return False.

        On some platforms os.kill raises PermissionError for a process owned
        by another user — that means the process exists but we can't signal it.
        The current contract treats all OSError subtypes as 'not alive'.
        """
        from owlbear.process import is_process_alive

        with patch(
            "owlbear.process.os.kill",
            side_effect=PermissionError("Operation not permitted"),
        ):
            assert is_process_alive(1) is False


class TestFromAC_ModuleImportability:  # noqa: N801
    """AC: owlbear.process must be importable and expose is_process_alive."""

    def test_module_importable(self) -> None:
        """owlbear.process can be imported."""
        import owlbear.process  # noqa: F401

    def test_function_is_public(self) -> None:
        """is_process_alive is a public name (no leading underscore)."""
        from owlbear.process import is_process_alive

        assert not is_process_alive.__name__.startswith("_")

    def test_function_is_callable(self) -> None:
        """is_process_alive is callable."""
        from owlbear.process import is_process_alive

        assert callable(is_process_alive)
