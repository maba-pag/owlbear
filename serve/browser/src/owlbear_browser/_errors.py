"""Shared error types for the owlbear_browser package."""

from __future__ import annotations


class EdgeNotFoundError(RuntimeError):
    """Raised when the Edge binary cannot be located."""


class CDPConnectionError(Exception):
    """Raised when a CDP connection attempt fails."""


class AuthenticationRequired(Exception):
    """Raised when an SSO redirect or login form is detected on a page."""
