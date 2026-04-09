"""Tests for OwlBearError base exception hierarchy (RED phase).

Task: #791 - Tests for #539 (OwlBearError base exception hierarchy).
Design: docs/research/exception-hierarchy.md

Every test here MUST fail until the builder implements the hierarchy.
The import of ``OwlBearError`` from ``owlbear.core.exceptions`` will raise
``ModuleNotFoundError`` because the module does not exist yet.
"""

from __future__ import annotations

from owlbear.core.errors import BlockedCommandError, ErrorCategory, classify_error
from owlbear.core.exceptions import OwlBearError
from owlbear.tools.ask_user import AskUserTimeoutError
from owlbear.tools.browser.safety import BlockedURLError


def _raise_runtime_error() -> None:
    msg = "unrelated"
    raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# AC 1-3: issubclass assertions
# ---------------------------------------------------------------------------


class TestFromAC_IsSubclass:
    """Each custom exception must be a subclass of OwlBearError."""

    def test_blocked_command_error_is_subclass(self) -> None:
        assert issubclass(BlockedCommandError, OwlBearError)

    def test_blocked_url_error_is_subclass(self) -> None:
        assert issubclass(BlockedURLError, OwlBearError)

    def test_ask_user_timeout_error_is_subclass(self) -> None:
        assert issubclass(AskUserTimeoutError, OwlBearError)

    def test_owlbear_error_is_subclass_of_exception(self) -> None:
        """Root base must inherit from Exception."""
        assert issubclass(OwlBearError, Exception)

    def test_owlbear_error_is_not_base_exception_directly(self) -> None:
        """OwlBearError should NOT bypass Exception (no BaseException tricks)."""
        assert issubclass(OwlBearError, Exception)
        assert OwlBearError is not Exception


# ---------------------------------------------------------------------------
# AC 4: except OwlBearError catches instances of all 3 exception classes
# ---------------------------------------------------------------------------


class TestFromAC_BlanketCatch:
    """``except OwlBearError`` must catch all 3 custom exceptions."""

    def test_catches_blocked_command_error(self) -> None:
        caught = False
        try:
            raise BlockedCommandError(command="rm -rf /", pattern="rm")
        except OwlBearError:
            caught = True
        assert caught

    def test_catches_blocked_url_error(self) -> None:
        caught = False
        try:
            raise BlockedURLError(url="http://evil.com", pattern="evil")
        except OwlBearError:
            caught = True
        assert caught

    def test_catches_ask_user_timeout_error(self) -> None:
        caught = False
        try:
            msg = "timed out"
            raise AskUserTimeoutError(msg)
        except OwlBearError:
            caught = True
        assert caught

    def test_does_not_catch_plain_exception(self) -> None:
        """Boundary: OwlBearError should NOT catch unrelated exceptions."""
        with_owlbear = False
        with_runtime = False
        try:
            _raise_runtime_error()
        except OwlBearError:
            with_owlbear = True
        except RuntimeError:
            with_runtime = True
        assert not with_owlbear
        assert with_runtime

    def test_isinstance_blocked_command_error(self) -> None:
        exc = BlockedCommandError(command="del *", pattern="del")
        assert isinstance(exc, OwlBearError)

    def test_isinstance_blocked_url_error(self) -> None:
        exc = BlockedURLError(url="ftp://bad", pattern="ftp")
        assert isinstance(exc, OwlBearError)

    def test_isinstance_ask_user_timeout_error(self) -> None:
        exc = AskUserTimeoutError()
        assert isinstance(exc, OwlBearError)


# ---------------------------------------------------------------------------
# AC 5: AskUserTimeoutError still caught by except TimeoutError
# ---------------------------------------------------------------------------


class TestFromAC_TimeoutErrorCompat:
    """AskUserTimeoutError must remain catchable as TimeoutError (MI)."""

    def test_is_subclass_of_timeout_error(self) -> None:
        assert issubclass(AskUserTimeoutError, TimeoutError)

    def test_caught_by_except_timeout_error(self) -> None:
        caught = False
        try:
            msg = "timed out"
            raise AskUserTimeoutError(msg)
        except TimeoutError:
            caught = True
        assert caught

    def test_is_both_owlbear_error_and_timeout_error(self) -> None:
        """Edge: MI means it belongs to both hierarchies."""
        exc = AskUserTimeoutError()
        assert isinstance(exc, OwlBearError)
        assert isinstance(exc, TimeoutError)


# ---------------------------------------------------------------------------
# AC 6: classify_error(BlockedURLError(...)) returns PERMANENT
# ---------------------------------------------------------------------------


class TestFromAC_ClassifyBlockedURL:
    """classify_error must explicitly handle BlockedURLError as PERMANENT."""

    def test_classify_blocked_url_error_returns_permanent(self) -> None:
        exc = BlockedURLError(url="http://bad.com", pattern="bad")
        assert classify_error(exc) is ErrorCategory.PERMANENT

    def test_classify_blocked_url_error_with_allowlist_pattern(self) -> None:
        """Edge: the pattern string doesn't affect the category."""
        exc = BlockedURLError(url="http://x.com", pattern="<not in allowlist>")
        assert classify_error(exc) is ErrorCategory.PERMANENT
