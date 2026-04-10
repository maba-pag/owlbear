"""Domain allowlist for browser MCP navigation."""

from __future__ import annotations

from urllib.parse import urlparse

__all__ = ["DomainAllowlist"]


class DomainAllowlist:
    """Enforces URL navigation to an approved set of domains.

    Args:
        domains: Approved hostname strings (e.g. ``["sharepoint.example.com"]``).
    """

    def __init__(self, domains: list[str]) -> None:
        self._domains: frozenset[str] = frozenset(domains)

    def check(self, url: str) -> None:
        """Raise if *url*'s hostname is not in the allowlist.

        Args:
            url: URL to validate.

        Raises:
            PermissionError: When the URL's hostname is not in the allowlist.
        """
        hostname = urlparse(url).hostname or ""
        if hostname not in self._domains:
            msg = f"Domain not in allowlist: {hostname!r}"
            raise PermissionError(msg)
