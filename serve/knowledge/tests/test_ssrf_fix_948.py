"""Failing tests for task #948: SSRF fix in HttpxContentFetcher.fetch — CWE-918 blocklist.

All tests in this file must FAIL with the current HttpxContentFetcher.fetch()
implementation (which has only scheme validation — no IP blocklist, no DNS
pre-resolution, no redirect control).

They will pass once the builder adds:
  - async DNS resolution via asyncio.to_thread(socket.getaddrinfo, ...)
  - IP blocklist check (loopback / private / link-local / reserved / unspecified)
  - IPv4-mapped IPv6 unwrap before check
  - URL rewrite to resolved IP with Host header (DNS rebinding mitigation)
  - follow_redirects=False
  - ValueError on any blocked URL (not None — contrast with _web_read)

DNS is mocked via ``socket.getaddrinfo``.  The implementation must use
``asyncio.to_thread(socket.getaddrinfo, ...)`` so this patch intercepts it.
"""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.fetcher import HttpxContentFetcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client(text: str = "fetched content") -> AsyncMock:
    """Return a mock httpx.AsyncClient async-CM that returns *text* on success."""
    response = MagicMock()
    response.text = text
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.__aenter__.return_value.get = AsyncMock(return_value=response)
    return client


def _addr4(ip: str, port: int = 80) -> list:
    """Minimal socket.getaddrinfo return value for an IPv4 address."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


def _addr6(ip: str, port: int = 80) -> list:
    """Minimal socket.getaddrinfo return value for an IPv6 address."""
    return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, port, 0, 0))]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_HttpxContentFetcherSSRF:
    """Contract tests for HttpxContentFetcher.fetch() SSRF protection (AC #948).

    Every test below fails with the current code because the current code
    makes the HTTP request without any IP-range check or DNS pre-resolution.

    Unlike _web_read (which returns None for blocked URLs), fetch() must raise
    ValueError — any blocked URL is a caller error, not a silent skip.
    """

    # ------------------------------------------------------------------
    # Blocked — loopback 127.0.0.0/8  (boundary)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_0_0_1(self) -> None:
        """127.0.0.1 (loopback) — must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://127.0.0.1/")
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_x_non_zero(self) -> None:
        """127.0.0.100 is still in 127.0.0.0/8 — must raise ValueError."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.100")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://127.0.0.100/secret")
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_localhost_hostname(self) -> None:
        """http://localhost/ resolves to 127.0.0.1 (loopback) — must raise ValueError.

        A literal-IP check would miss this; the implementation must resolve
        the hostname via DNS before checking the IP.
        """
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://localhost/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — private RFC-1918 ranges  (boundary)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_private_10_x(self) -> None:
        """10.0.0.1 (RFC-1918) — must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.0.0.1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://10.0.0.1/admin")
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_private_172_16_x(self) -> None:
        """172.16.0.1 (RFC-1918) — must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("172.16.0.1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://172.16.0.1/")
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_private_192_168_x(self) -> None:
        """192.168.1.1 (RFC-1918) — must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("192.168.1.1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://192.168.1.1/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — link-local / AWS IMDS  (boundary)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_link_local_169_254_169_254(self) -> None:
        """169.254.169.254 (AWS IMDS / link-local) — must raise ValueError."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("169.254.169.254")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://169.254.169.254/latest/meta-data/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — unspecified addresses  (boundary)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_unspecified_0_0_0_0(self) -> None:
        """0.0.0.0 (unspecified) — must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("0.0.0.0")),  # noqa: S104
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://0.0.0.0/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — IPv6 loopback and link-local  (edge)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_ipv6_loopback(self) -> None:
        """::1 (IPv6 loopback) — must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://[::1]/")
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_ipv6_link_local_fe80(self) -> None:
        """fe80::1 (IPv6 link-local) — must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("fe80::1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://[fe80::1]/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — IPv4-mapped IPv6 bypass vector  (edge)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_ipv4_mapped_ipv6_loopback(self) -> None:
        """::ffff:127.0.0.1 (IPv4-mapped loopback) — must raise ValueError.

        Without an explicit .ipv4_mapped check, ipaddress marks this address
        as *not* loopback (it's IPv6Address, not IPv4Address), bypassing the
        blocklist entirely.
        """
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::ffff:127.0.0.1")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://[::ffff:127.0.0.1]/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Error contract — blocked raises ValueError, httpx never invoked  (error)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocked_ip_raises_value_error_not_returns_none(self) -> None:
        """A blocked private URL must raise ValueError — not silently return None.

        fetch() contract differs from _web_read: it raises on all error
        conditions rather than returning a sentinel.
        """
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.10.10.10")),
            patch("httpx.AsyncClient"),
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://internal.corp/secret")

    @pytest.mark.asyncio
    async def test_blocked_ip_error_message_contains_ip(self) -> None:
        """ValueError message for a blocked IP must include the resolved IP address."""
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("192.168.0.1")),
            patch("httpx.AsyncClient"),
            pytest.raises(ValueError, match=r"192\.168\.0\.1"),
        ):
            await fetcher.fetch("http://internal.example.com/")

    @pytest.mark.asyncio
    async def test_dns_failure_raises_value_error(self) -> None:
        """DNS resolution failure must raise ValueError; httpx never called."""
        fetcher = HttpxContentFetcher()
        with (
            patch(
                "socket.getaddrinfo", side_effect=OSError("Name or service not known")
            ),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://nonexistent.invalid/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # DNS rebinding mitigation — hostname resolving to private IP  (edge)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_dns_rebinding_hostname_resolving_to_private_ip_is_blocked(
        self,
    ) -> None:
        """A public-looking hostname whose DNS resolves to a private IP must raise ValueError.

        This is the core DNS-rebinding scenario: the attacker controls DNS and
        returns an internal IP for their domain.  The implementation must check
        the IP *returned by DNS* — not just the raw hostname — before requesting.
        """
        fetcher = HttpxContentFetcher()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.0.0.50")),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await fetcher.fetch("http://legitimate-looking.example.com/")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Redirects disabled — defense-in-depth  (security)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_follow_redirects_disabled(self) -> None:
        """httpx.AsyncClient must be instantiated with follow_redirects=False."""
        fetcher = HttpxContentFetcher()
        mock_client = _make_mock_client("ok")
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            await fetcher.fetch("http://example.com/")
        call_kwargs = mock_cls.call_args
        assert call_kwargs is not None
        kwargs = call_kwargs.kwargs
        assert kwargs.get("follow_redirects") is False

    # ------------------------------------------------------------------
    # DNS rebinding — URL rewrite + Host header  (security / edge)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_request_url_rewritten_to_resolved_ip(self) -> None:
        """The URL passed to httpx.get must use the resolved IP, not the hostname.

        Passing the original hostname URL to httpx lets httpx re-resolve it —
        a second DNS lookup the attacker can answer differently (TOCTOU).
        """
        fetcher = HttpxContentFetcher()
        mock_client = _make_mock_client("response")
        mock_get = mock_client.__aenter__.return_value.get
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            await fetcher.fetch("http://example.com/page")
        assert mock_get.called, "httpx.get must be called for a safe resolved IP"
        called_url: str = (
            mock_get.call_args.args[0]
            if mock_get.call_args.args
            else mock_get.call_args.kwargs.get("url", repr(mock_get.call_args))
        )
        assert "example.com" not in called_url, (
            f"httpx was called with original hostname {called_url!r}; "
            "expected the URL rewritten to the resolved IP (93.184.216.34)"
        )
        assert "93.184.216.34" in called_url

    @pytest.mark.asyncio
    async def test_host_header_set_to_original_hostname(self) -> None:
        """The Host header must be the original hostname on the IP-rewritten request.

        Required for virtual-hosted servers and TLS SNI — without it an
        IP-rewritten request returns 404 or fails certificate validation.
        """
        fetcher = HttpxContentFetcher()
        mock_client = _make_mock_client("response")
        mock_get = mock_client.__aenter__.return_value.get
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            await fetcher.fetch("http://example.com/page")
        assert mock_get.called
        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("Host") == "example.com", (
            f"Expected Host: example.com, got headers={headers!r}"
        )

    # ------------------------------------------------------------------
    # DNS resolution happens before HTTP  (happy / security)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_dns_resolution_called_before_http_request(self) -> None:
        """socket.getaddrinfo must be called for every hostname URL.

        The implementation must not rely on httpx to resolve the hostname —
        that would allow a second DNS lookup after the IP check (TOCTOU).
        """
        fetcher = HttpxContentFetcher()
        mock_client = _make_mock_client("hello world")
        with (
            patch(
                "socket.getaddrinfo", return_value=_addr4("93.184.216.34")
            ) as mock_dns,
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await fetcher.fetch("http://example.com/")
        assert result == "hello world"
        mock_dns.assert_called_once()
