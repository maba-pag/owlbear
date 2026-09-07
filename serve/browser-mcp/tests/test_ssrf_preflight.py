"""SSRF pre-flight regression tests for navigate().

The security boundary requires:
  - _check_ssrf(url) called BEFORE allowlist.check(url) in navigate()
  - Scheme check: non-http/https schemes raise ToolError
  - DNS resolution via asyncio.to_thread(socket.getaddrinfo, hostname, port)
  - Exact allowlisted hostnames may use private/internal IPs; other hosts are blocked
  - IP blocklist: loopback / private / link-local / reserved / unspecified → ToolError
  - IPv4-mapped IPv6 unwrapping before blocklist check
    - DNS failure (OSError from getaddrinfo) → ToolError with hostname in message

DNS is mocked via ``socket.getaddrinfo``.  The implementation must use
``asyncio.to_thread(socket.getaddrinfo, ...)`` so this patch intercepts it.
"""

# ruff: noqa: N801

from __future__ import annotations

import socket
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_browser_mcp.allowlist import DomainAllowlist
from owlbear_browser_mcp.server import navigate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_HOST = "target.example.com"
_UNALLOWLISTED_HOST = "blocked.example.com"


def _make_ctx(domains: list[str] | None = None) -> MagicMock:
    """Return a mock ctx backed by a real DomainAllowlist.

    Uses SimpleNamespace without a ``page`` attribute so navigate() reaches
    the dry-run return path when the SSRF check passes.
    """
    allowlist = DomainAllowlist(domains=domains if domains is not None else [_ALLOWED_HOST])
    app_ctx = SimpleNamespace(allowlist=allowlist)
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _addr4(ip: str, port: int = 80) -> list:
    """Minimal socket.getaddrinfo return value for an IPv4 address."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


def _addr6(ip: str, port: int = 80) -> list:
    """Minimal socket.getaddrinfo return value for an IPv6 address."""
    return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, port, 0, 0))]


# ---------------------------------------------------------------------------
# AC2 — Scheme rejection
# ---------------------------------------------------------------------------


class TestFromAC_NavigateSchemeCheck:
    """AC2: navigate() rejects non-http/https schemes with ToolError.

    These cases guard the MCP SSRF preflight contract against scheme bypasses.
    """

    @pytest.mark.asyncio
    async def test_javascript_scheme_rejected(self) -> None:
        """javascript://allowed-host/ bypasses DomainAllowlist — scheme check must catch it.

        javascript://target.example.com/ currently passes allowlist (valid hostname) and
        returns the URL.  After the fix, _check_ssrf raises ToolError before allowlist runs.
        """
        ctx = _make_ctx([_ALLOWED_HOST])
        with pytest.raises(ToolError):
            await navigate(ctx, f"javascript://{_ALLOWED_HOST}/alert(1)")

    @pytest.mark.asyncio
    async def test_file_scheme_rejected(self) -> None:
        """file://allowed-host/etc/passwd must be caught by scheme check."""
        ctx = _make_ctx([_ALLOWED_HOST])
        with pytest.raises(ToolError):
            await navigate(ctx, f"file://{_ALLOWED_HOST}/etc/passwd")

    @pytest.mark.asyncio
    async def test_data_scheme_rejected(self) -> None:
        """data://allowed-host/... must be caught by scheme check."""
        ctx = _make_ctx([_ALLOWED_HOST])
        with pytest.raises(ToolError):
            await navigate(ctx, f"data://{_ALLOWED_HOST}/text/html,<script>alert(1)</script>")

    @pytest.mark.asyncio
    async def test_ftp_scheme_rejected(self) -> None:
        """ftp:// is not http/https — must raise ToolError."""
        ctx = _make_ctx([_ALLOWED_HOST])
        with pytest.raises(ToolError):
            await navigate(ctx, f"ftp://{_ALLOWED_HOST}/pub/file.txt")

    @pytest.mark.asyncio
    async def test_wildcard_allowlist_allows_a_public_hostname(self) -> None:
        """Wildcard testing mode permits public hosts after SSRF validation."""
        url = "https://another.example.com/"
        ctx = _make_ctx(["*"])
        with patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")):
            assert await navigate(ctx, url) == url


# ---------------------------------------------------------------------------
# Trusted internal destinations
# ---------------------------------------------------------------------------


class TestFromAC_NavigateTrustedInternal:
    """Exact allowlist entries may opt into private/internal DNS results."""

    @pytest.mark.asyncio
    async def test_exact_allowlisted_hostname_allows_private_ip(self) -> None:
        """An exact hostname approval permits a synthetic private destination."""
        url = f"https://{_ALLOWED_HOST}/internal"
        ctx = _make_ctx([_ALLOWED_HOST])
        with patch("socket.getaddrinfo", return_value=_addr4("10.0.0.7")):
            assert await navigate(ctx, url) == url

    @pytest.mark.asyncio
    async def test_exact_allowlisted_hostname_allows_mapped_private_ip(self) -> None:
        """IPv4-mapped private results use the same exact-host approval."""
        url = f"https://{_ALLOWED_HOST}/internal"
        ctx = _make_ctx([_ALLOWED_HOST])
        with patch("socket.getaddrinfo", return_value=_addr6("::ffff:10.0.0.7")):
            assert await navigate(ctx, url) == url

    @pytest.mark.asyncio
    async def test_empty_allowlist_does_not_allow_private_ip(self) -> None:
        """The default empty allowlist does not trust private destinations."""
        ctx = _make_ctx([])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.0.0.7")),
            pytest.raises(ToolError, match="blocked IP address"),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/internal")

    @pytest.mark.asyncio
    async def test_wildcard_does_not_allow_private_ip(self) -> None:
        """Wildcard testing mode does not become a trusted-internal policy."""
        ctx = _make_ctx(["*"])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.0.0.7")),
            pytest.raises(ToolError, match="blocked IP address"),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/internal")


# ---------------------------------------------------------------------------
# AC1 — IP blocklist
# ---------------------------------------------------------------------------


class TestFromAC_NavigateIPBlocklist:
    """AC1: navigate() blocks private/loopback/link-local IPs for unapproved hosts."""

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_0_0_1(self) -> None:
        """An unallowlisted hostname resolving to 127.0.0.1 must raise ToolError."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_x_non_zero(self) -> None:
        """127.0.0.100 is still in 127.0.0.0/8 — unallowlisted hosts must raise ToolError."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.100")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/path")

    @pytest.mark.asyncio
    async def test_blocks_private_10_x(self) -> None:
        """10.0.0.1 (RFC-1918 /8) must raise ToolError for an unallowlisted host."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.0.0.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_private_172_16_x(self) -> None:
        """172.16.0.1 (RFC-1918 /12) must raise ToolError for an unallowlisted host."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("172.16.0.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_private_192_168_x(self) -> None:
        """192.168.1.1 (RFC-1918 /16) must raise ToolError for an unallowlisted host."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("192.168.1.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/admin")

    @pytest.mark.asyncio
    async def test_blocks_link_local_169_254_x(self) -> None:
        """169.254.0.1 (link-local / AWS IMDS range) must raise ToolError for an unallowlisted host."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("169.254.169.254")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_ipv4_mapped_ipv6_loopback(self) -> None:
        """An unallowlisted host resolving to mapped loopback must raise ToolError.

        The implementation must unwrap the IPv4-mapped address before checking
        properties — ipaddress.IPv6Address.ipv4_mapped returns the inner IPv4Address.
        """
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::ffff:127.0.0.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_ipv4_mapped_ipv6_private(self) -> None:
        """An unallowlisted host resolving to mapped private IP must raise ToolError."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::ffff:10.0.0.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_all_ips_when_multi_blocked(self) -> None:
        """Multiple blocked addresses must raise ToolError for an unallowlisted host."""
        ctx = _make_ctx([_UNALLOWLISTED_HOST])
        addrs = _addr4("10.0.0.1") + _addr4("192.168.1.1")
        with (
            patch("socket.getaddrinfo", return_value=addrs),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_literal_ip_loopback_in_url(self) -> None:
        """http://127.0.0.1/ must remain blocked even when the IP is allowlisted.

        The trusted-internal policy applies to exact hostnames, not literal IPs.
        """
        ctx = _make_ctx(["127.0.0.1"])
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, "http://127.0.0.1/")

    @pytest.mark.asyncio
    async def test_blocks_backslash_authority_before_allowlist(self) -> None:
        """A backslash must not turn a loopback URL into an allowlisted hostname."""
        ctx = _make_ctx([_ALLOWED_HOST])
        url = f"http://127.0.0.1\\@{_ALLOWED_HOST}/"
        with (
            patch("socket.getaddrinfo") as mock_dns,
            pytest.raises(ToolError, match="Backslashes"),
        ):
            await navigate(ctx, url)
        mock_dns.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_reserved_ip(self) -> None:
        """240.0.0.1 (class E / is_reserved=True) must raise ToolError.

        AC1 explicitly requires blocking reserved addresses.  Removing
        ``check.is_reserved`` from ``_is_blocked_ip`` would let this IP through.
        """
        ctx = _make_ctx()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("240.0.0.1")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_blocks_unspecified_ip(self) -> None:
        """0.0.0.0 (is_unspecified=True) must raise ToolError.

        AC1 explicitly requires blocking unspecified addresses.  Removing
        ``check.is_unspecified`` from ``_is_blocked_ip`` would let this IP through.
        """
        ctx = _make_ctx()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("0.0.0.0")),  # noqa: S104
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")


# ---------------------------------------------------------------------------
# DNS failure — binding guidance §2
# ---------------------------------------------------------------------------


class TestFromAC_NavigateDNSFailure:
    """Binding guidance §2: DNS failures must become ToolError, not raw OSError.

    The preflight resolves the hostname and translates resolver failures into a
    stable MCP tool error.
    """

    @pytest.mark.asyncio
    async def test_dns_failure_raises_tool_error(self) -> None:
        """socket.getaddrinfo raises OSError → must raise ToolError (not propagate OSError)."""
        ctx = _make_ctx()
        with (
            patch("socket.getaddrinfo", side_effect=OSError("Name or service not known")),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")

    @pytest.mark.asyncio
    async def test_dns_failure_message_contains_hostname(self) -> None:
        """ToolError message must include the hostname to aid diagnostics."""
        ctx = _make_ctx()
        with (
            patch("socket.getaddrinfo", side_effect=OSError("NXDOMAIN")),
            pytest.raises(ToolError, match=_ALLOWED_HOST),
        ):
            await navigate(ctx, f"https://{_ALLOWED_HOST}/")


# ---------------------------------------------------------------------------
# AC5 — Allowed domain pass-through (DNS must be resolved)
# ---------------------------------------------------------------------------


class TestFromAC_NavigatePassthrough:
    """AC5: Allowed domain with public IP passes the SSRF check; DNS is resolved.

    The pass-through test verifies the contract that DNS resolution IS performed
    even for allowlisted domains (not bypassed).
    """

    @pytest.mark.asyncio
    async def test_allowed_domain_dns_is_resolved(self) -> None:
        """Public IP for an allowed domain: SSRF check passes and DNS was called."""
        ctx = _make_ctx()
        with patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")) as mock_dns:
            result = await navigate(ctx, f"https://{_ALLOWED_HOST}/page")
        mock_dns.assert_called()
        assert result is not None

    @pytest.mark.asyncio
    async def test_allowed_domain_https_returns_url(self) -> None:
        """navigate() returns a non-empty result for an allowed HTTPS URL with public IP.

        This also acts as a regression guard: the SSRF check must not block public IPs.
        """
        ctx = _make_ctx()
        with patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")) as mock_dns:
            result = await navigate(ctx, f"https://{_ALLOWED_HOST}/index.html")
        mock_dns.assert_called()
        assert result == f"https://{_ALLOWED_HOST}/index.html"
