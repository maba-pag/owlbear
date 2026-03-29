"""RED-phase tests for CancelSignal and sandbox_path extraction (#143).

Tests the contract for:
  - owlbear_knowledge.cancellation: CancelSignal (Protocol) and LinkedCancelSignal
  - owlbear_knowledge._paths: sandbox_path

All tests import from owlbear_knowledge (not v1 paths) and are expected to
fail at RED phase — the target modules do not yet exist in v2.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# CancelSignal — Protocol contract
# ---------------------------------------------------------------------------


class TestFromAC_CancelSignal:
    """CancelSignal is a @runtime_checkable Protocol with is_set() -> bool.

    AC:
    - CancelSignal is @runtime_checkable Protocol with is_set() -> bool
    - Any object with is_set() -> bool satisfies CancelSignal (isinstance check)
    """

    def test_cancel_signal_importable(self) -> None:
        """CancelSignal can be imported from owlbear_knowledge.cancellation."""
        from owlbear_knowledge.cancellation import CancelSignal  # noqa: F401

    def test_cancel_signal_is_runtime_checkable_protocol(self) -> None:
        """CancelSignal is a runtime_checkable Protocol — isinstance() does not raise."""
        from owlbear_knowledge.cancellation import CancelSignal

        class _AnyObject:
            pass

        # runtime_checkable: isinstance must not raise TypeError
        result = isinstance(_AnyObject(), CancelSignal)
        assert isinstance(result, bool)

    def test_object_with_is_set_satisfies_cancel_signal(self) -> None:
        """Any object exposing is_set() -> bool satisfies CancelSignal."""
        from owlbear_knowledge.cancellation import CancelSignal

        class _MockSignal:
            def is_set(self) -> bool:
                return False

        assert isinstance(_MockSignal(), CancelSignal)

    def test_object_without_is_set_does_not_satisfy_cancel_signal(self) -> None:
        """An object without is_set() does not satisfy CancelSignal."""
        from owlbear_knowledge.cancellation import CancelSignal

        class _NoIsSet:
            pass

        assert not isinstance(_NoIsSet(), CancelSignal)

    def test_object_with_is_set_returning_true_satisfies_protocol(self) -> None:
        """isinstance check works for objects whose is_set() returns True."""
        from owlbear_knowledge.cancellation import CancelSignal

        class _AlwaysSet:
            def is_set(self) -> bool:
                return True

        assert isinstance(_AlwaysSet(), CancelSignal)


# ---------------------------------------------------------------------------
# LinkedCancelSignal — composition contract
# ---------------------------------------------------------------------------


class TestFromAC_LinkedCancelSignal:
    """LinkedCancelSignal(*sources).is_set() returns True when any source is set.

    AC:
    - LinkedCancelSignal(*sources).is_set() returns False when no source is set
    - LinkedCancelSignal(*sources).is_set() returns True when any source is set
    - LinkedCancelSignal composes 3+ CancelSignal sources correctly
    """

    def test_linked_cancel_signal_importable(self) -> None:
        """LinkedCancelSignal can be imported from owlbear_knowledge.cancellation."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal  # noqa: F401

    def test_no_sources_is_never_set(self) -> None:
        """LinkedCancelSignal with no sources always returns False."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        sig = LinkedCancelSignal()
        assert sig.is_set() is False

    def test_single_unset_source_returns_false(self) -> None:
        """LinkedCancelSignal is not set when its one source is not set."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        class _UnsetSignal:
            def is_set(self) -> bool:
                return False

        sig = LinkedCancelSignal(_UnsetSignal())
        assert sig.is_set() is False

    def test_single_set_source_returns_true(self) -> None:
        """LinkedCancelSignal is set when its one source is set."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        class _SetSignal:
            def is_set(self) -> bool:
                return True

        sig = LinkedCancelSignal(_SetSignal())
        assert sig.is_set() is True

    def test_two_sources_all_unset_returns_false(self) -> None:
        """LinkedCancelSignal returns False when all sources are unset."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        class _Unset:
            def is_set(self) -> bool:
                return False

        sig = LinkedCancelSignal(_Unset(), _Unset())
        assert sig.is_set() is False

    def test_two_sources_one_set_returns_true(self) -> None:
        """LinkedCancelSignal returns True when any source is set (first set)."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        class _SetSignal:
            def is_set(self) -> bool:
                return True

        class _UnsetSignal:
            def is_set(self) -> bool:
                return False

        sig = LinkedCancelSignal(_SetSignal(), _UnsetSignal())
        assert sig.is_set() is True

    def test_two_sources_second_set_returns_true(self) -> None:
        """LinkedCancelSignal returns True when any source is set (second set)."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        class _UnsetSignal:
            def is_set(self) -> bool:
                return False

        class _SetSignal:
            def is_set(self) -> bool:
                return True

        sig = LinkedCancelSignal(_UnsetSignal(), _SetSignal())
        assert sig.is_set() is True

    def test_three_sources_none_set_returns_false(self) -> None:
        """LinkedCancelSignal correctly composes 3+ sources — all unset."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        class _Unset:
            def is_set(self) -> bool:
                return False

        sig = LinkedCancelSignal(_Unset(), _Unset(), _Unset())
        assert sig.is_set() is False

    def test_three_sources_middle_set_returns_true(self) -> None:
        """LinkedCancelSignal correctly composes 3+ sources — middle set."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        class _Unset:
            def is_set(self) -> bool:
                return False

        class _Set:
            def is_set(self) -> bool:
                return True

        sig = LinkedCancelSignal(_Unset(), _Set(), _Unset())
        assert sig.is_set() is True

    def test_linked_cancel_signal_satisfies_cancel_signal_protocol(self) -> None:
        """LinkedCancelSignal itself satisfies the CancelSignal protocol."""
        from owlbear_knowledge.cancellation import CancelSignal, LinkedCancelSignal

        sig = LinkedCancelSignal()
        assert isinstance(sig, CancelSignal)

    def test_linked_reflects_live_state_change(self) -> None:
        """LinkedCancelSignal reflects live state changes in sources."""
        from owlbear_knowledge.cancellation import LinkedCancelSignal

        state = {"set": False}

        class _LiveSignal:
            def is_set(self) -> bool:
                return state["set"]

        sig = LinkedCancelSignal(_LiveSignal())
        assert sig.is_set() is False
        state["set"] = True
        assert sig.is_set() is True


# ---------------------------------------------------------------------------
# sandbox_path — path sandboxing contract
# ---------------------------------------------------------------------------


class TestFromAC_SandboxPath:
    """sandbox_path resolves paths safely under a root directory.

    AC:
    - Valid relative path resolves under root
    - Null byte in path raises PermissionError
    - `..` traversal outside root raises PermissionError
    - Absolute path inside root resolves correctly
    - Absolute path outside root raises PermissionError
    """

    def test_sandbox_path_importable(self) -> None:
        """sandbox_path can be imported from owlbear_knowledge._paths."""
        from owlbear_knowledge._paths import sandbox_path  # noqa: F401

    def test_valid_relative_path_resolves_under_root(self, tmp_path: Path) -> None:
        """A valid relative path is resolved under the root."""
        from owlbear_knowledge._paths import sandbox_path

        result = sandbox_path(tmp_path, "subdir/file.txt")
        assert result == (tmp_path / "subdir" / "file.txt").resolve()

    def test_relative_path_single_component(self, tmp_path: Path) -> None:
        """A single-component relative path resolves correctly."""
        from owlbear_knowledge._paths import sandbox_path

        result = sandbox_path(tmp_path, "file.txt")
        assert result == (tmp_path / "file.txt").resolve()

    def test_null_byte_in_path_raises_permission_error(self, tmp_path: Path) -> None:
        """A null byte in the path raises PermissionError."""
        from owlbear_knowledge._paths import sandbox_path

        with pytest.raises(PermissionError):
            sandbox_path(tmp_path, "file\x00.txt")

    def test_null_byte_embedded_raises_permission_error(self, tmp_path: Path) -> None:
        """A null byte embedded anywhere in the path raises PermissionError."""
        from owlbear_knowledge._paths import sandbox_path

        with pytest.raises(PermissionError):
            sandbox_path(tmp_path, "\x00")

    def test_dotdot_traversal_outside_root_raises_permission_error(
        self, tmp_path: Path
    ) -> None:
        """A `..` traversal that escapes root raises PermissionError."""
        from owlbear_knowledge._paths import sandbox_path

        with pytest.raises(PermissionError):
            sandbox_path(tmp_path, "../outside.txt")

    def test_dotdot_deep_traversal_raises_permission_error(self, tmp_path: Path) -> None:
        """Multiple `..` components that escape root raise PermissionError."""
        from owlbear_knowledge._paths import sandbox_path

        with pytest.raises(PermissionError):
            sandbox_path(tmp_path, "subdir/../../outside.txt")

    def test_absolute_path_inside_root_resolves_correctly(self, tmp_path: Path) -> None:
        """An absolute path that resolves inside root is accepted."""
        from owlbear_knowledge._paths import sandbox_path

        target = tmp_path / "subdir" / "file.txt"
        result = sandbox_path(tmp_path, target)
        assert result == target.resolve()

    def test_absolute_path_outside_root_raises_permission_error(
        self, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """An absolute path outside root raises PermissionError."""
        from owlbear_knowledge._paths import sandbox_path

        outside = tmp_path_factory.mktemp("outside") / "file.txt"
        with pytest.raises(PermissionError):
            sandbox_path(tmp_path, outside)

    def test_return_type_is_path(self, tmp_path: Path) -> None:
        """sandbox_path returns a Path object."""
        from owlbear_knowledge._paths import sandbox_path

        result = sandbox_path(tmp_path, "file.txt")
        assert isinstance(result, Path)

    def test_dotdot_within_root_is_allowed(self, tmp_path: Path) -> None:
        """A `..` that still resolves inside root is allowed."""
        from owlbear_knowledge._paths import sandbox_path

        # subdir/../file.txt resolves to tmp_path/file.txt — still inside root
        result = sandbox_path(tmp_path, "subdir/../file.txt")
        assert result == (tmp_path / "file.txt").resolve()
