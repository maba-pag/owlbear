"""Shared error types for the owlbear_browser package."""

from __future__ import annotations


class AuthenticationRequired(Exception):
    """Raised when an SSO redirect or login form is detected on a page."""


class SSOExtensionNotFoundError(RuntimeError):
    """Raised when the Microsoft SSO extension cannot be located."""
