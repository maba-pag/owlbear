"""Failing tests for task #869 — Playwright launcher: error type and package exports.

Covers AC2 (SSOExtensionNotFoundError added to _errors.py) and AC3 (owlbear_browser
__init__.py exports PlaywrightLauncher, find_sso_extension, SSOExtensionNotFoundError).

AC1 (playwright_launcher.py interfaces) is covered by the sibling RED task #868.

All tests FAIL at RED phase:
- SSOExtensionNotFoundError does not exist in owlbear_browser._errors
- playwright_launcher.py does not exist, so __init__.py cannot export from it
"""

from __future__ import annotations

import owlbear_browser
from owlbear_browser import _errors


# ---------------------------------------------------------------------------
# TestFromAC_SSOError  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_SSOError:  # noqa: N801
    """SSOExtensionNotFoundError must be defined in _errors.py as RuntimeError subclass."""

    def test_ssoe_defined_in_errors_module(self) -> None:
        """SSOExtensionNotFoundError must exist in owlbear_browser._errors."""
        assert hasattr(_errors, "SSOExtensionNotFoundError"), (
            "SSOExtensionNotFoundError not found in owlbear_browser._errors — "
            "builder must add it to serve/browser/src/owlbear_browser/_errors.py"
        )

    def test_ssoe_is_runtime_error_subclass(self) -> None:
        """SSOExtensionNotFoundError must subclass RuntimeError (not bare Exception)."""
        assert issubclass(_errors.SSOExtensionNotFoundError, RuntimeError), (
            f"SSOExtensionNotFoundError must subclass RuntimeError; "
            f"got bases: {_errors.SSOExtensionNotFoundError.__bases__}"
        )

    def test_ssoe_accepts_string_message(self) -> None:
        """SSOExtensionNotFoundError must be raiseable with a plain string message."""
        exc = _errors.SSOExtensionNotFoundError("extension dir missing")
        assert str(exc) == "extension dir missing"


# ---------------------------------------------------------------------------
# TestFromAC_PackageExports  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_PackageExports:  # noqa: N801
    """owlbear_browser __init__.py must export the three new names from the launcher module."""

    # -- Accessibility (hasattr) -------------------------------------------

    def test_playwright_launcher_exported_from_package(self) -> None:
        """PlaywrightLauncher must be accessible as owlbear_browser.PlaywrightLauncher."""
        assert hasattr(owlbear_browser, "PlaywrightLauncher"), (
            "PlaywrightLauncher not exported from owlbear_browser — "
            "add 'from owlbear_browser.playwright_launcher import PlaywrightLauncher' "
            "to serve/browser/src/owlbear_browser/__init__.py"
        )

    def test_find_sso_extension_exported_from_package(self) -> None:
        """find_sso_extension must be accessible as owlbear_browser.find_sso_extension."""
        assert hasattr(owlbear_browser, "find_sso_extension"), (
            "find_sso_extension not exported from owlbear_browser — "
            "add 'from owlbear_browser.playwright_launcher import find_sso_extension' "
            "to serve/browser/src/owlbear_browser/__init__.py"
        )

    def test_sso_error_exported_from_package(self) -> None:
        """SSOExtensionNotFoundError must be accessible as owlbear_browser.SSOExtensionNotFoundError."""
        assert hasattr(owlbear_browser, "SSOExtensionNotFoundError"), (
            "SSOExtensionNotFoundError not exported from owlbear_browser — add it to __init__.py imports and __all__"
        )

    # -- __all__ membership -----------------------------------------------

    def test_playwright_launcher_in_dunder_all(self) -> None:
        """'PlaywrightLauncher' must appear in owlbear_browser.__all__."""
        assert "PlaywrightLauncher" in owlbear_browser.__all__, (
            f"'PlaywrightLauncher' missing from owlbear_browser.__all__; current __all__: {owlbear_browser.__all__}"
        )

    def test_find_sso_extension_in_dunder_all(self) -> None:
        """'find_sso_extension' must appear in owlbear_browser.__all__."""
        assert "find_sso_extension" in owlbear_browser.__all__, (
            f"'find_sso_extension' missing from owlbear_browser.__all__; current __all__: {owlbear_browser.__all__}"
        )

    def test_sso_error_in_dunder_all(self) -> None:
        """'SSOExtensionNotFoundError' must appear in owlbear_browser.__all__."""
        assert "SSOExtensionNotFoundError" in owlbear_browser.__all__, (
            f"'SSOExtensionNotFoundError' missing from owlbear_browser.__all__; "
            f"current __all__: {owlbear_browser.__all__}"
        )
