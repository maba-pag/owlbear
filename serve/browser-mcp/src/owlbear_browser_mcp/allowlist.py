"""Domain allowlist for browser MCP navigation."""

from __future__ import annotations

from urllib.parse import urlparse

__all__ = ["DomainAllowlist"]


class DomainAllowlist:
    """Enforces URL navigation to an approved set of domains.

    Args:
        domains: Approved hostname strings (e.g. ``["sharepoint.example.com"]``).
            ``"*"`` permits every hostname and is intended only for local testing.
    """

    def __init__(self, domains: list[str]) -> None:
        self._domains: frozenset[str] = frozenset(domain.casefold() for domain in domains)

    def check(self, url: str) -> None:
        """Raise if *url*'s hostname is not in the allowlist.

        Args:
            url: URL to validate.

        Raises:
            PermissionError: When the URL's hostname is not in the allowlist.
        """
        hostname = (urlparse(url).hostname or "").casefold()
        if "*" not in self._domains and hostname not in self._domains:
            msg = f"Domain not in allowlist: {hostname!r}"
            raise PermissionError(msg)

    def allows_exact_hostname(self, hostname: str) -> bool:
        """Return whether *hostname* is explicitly allowlisted, excluding wildcard mode."""
        return "*" not in self._domains and hostname.casefold() in self._domains
