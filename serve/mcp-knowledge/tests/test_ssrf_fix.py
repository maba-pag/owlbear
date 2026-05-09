"""Failing tests for task #946: SSRF fix in _web_read — CWE-918 blocklist.

All tests in this file must FAIL with the current _web_read (no IP blocklist).
They will pass once the builder adds async DNS resolution + IP blocklist.

DNS is mocked via ``socket.getaddrinfo``.  The implementation must use
``asyncio.to_thread(socket.getaddrinfo, ...)`` so this patch intercepts it.
For IPv4 literal-IP URLs the real resolver is used (trivially deterministic).
"""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import _web_read


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


class TestFromAC_WebReadSSRF:
    """Contract tests for _web_read SSRF protection (AC #946).

    Every test below fails with the current code because the current code
    makes the HTTP request without any IP-range check.
    """

    # ------------------------------------------------------------------
    # Blocked — loopback 127.0.0.0/8  (boundary)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_0_0_1(self) -> None:
        """http://127.0.0.1/ is loopback — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            result = await _web_read("http://127.0.0.1/")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_x_non_zero(self) -> None:
        """127.0.0.100 is still in 127.0.0.0/8 — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            result = await _web_read("http://127.0.0.100/secret")
        assert result is None
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — private RFC-1918 ranges  (boundary)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_private_10_x(self) -> None:
        """10.0.0.1 (RFC-1918) — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            result = await _web_read("http://10.0.0.1/admin")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_private_172_16_x(self) -> None:
        """172.16.0.1 (RFC-1918) — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            result = await _web_read("http://172.16.0.1/")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_private_192_168_x(self) -> None:
        """192.168.1.1 (RFC-1918) — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            result = await _web_read("http://192.168.1.1/")
        assert result is None
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — link-local / AWS IMDS  (boundary)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_link_local_169_254_169_254(self) -> None:
        """169.254.169.254 (AWS IMDS link-local) — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            result = await _web_read("http://169.254.169.254/latest/meta-data/")
        assert result is None
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — IPv6 loopback and link-local  (edge)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_ipv6_loopback_1(self) -> None:
        """::1 (IPv6 loopback) — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            result = await _web_read("http://[::1]/")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_ipv6_link_local_fe80(self) -> None:
        """fe80::1 (IPv6 link-local) — must return None, httpx never called."""
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("fe80::1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            result = await _web_read("http://[fe80::1]/")
        assert result is None
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Blocked — IPv4-mapped IPv6 bypass vector  (edge)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_ipv4_mapped_ipv6_loopback(self) -> None:
        """::ffff:127.0.0.1 (IPv4-mapped loopback) — must return None, httpx never called.

        Without an explicit .ipv4_mapped check the ipaddress library marks this
        address as *not* loopback (it's an IPv6Address), bypassing the blocklist.
        """
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::ffff:127.0.0.1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            result = await _web_read("http://[::ffff:127.0.0.1]/")
        assert result is None
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Error contract — blocked returns None, never raises  (error)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocked_url_returns_none_not_exception(self) -> None:
        """A blocked private URL returns None — must not raise any exception."""
        mock_client = _make_mock_client("secret content")
        with patch("httpx.AsyncClient", return_value=mock_client):
            try:
                result = await _web_read("http://10.10.10.10/secret")
            except Exception as exc:  # noqa: BLE001
                pytest.fail(
                    f"_web_read raised {exc!r} for blocked IP instead of returning None"
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_dns_resolution_failure_returns_none_httpx_not_called(self) -> None:
        """DNS failure (socket.gaierror) returns None; httpx.AsyncClient never instantiated."""
        with (
            patch(
                "socket.getaddrinfo", side_effect=OSError("Name or service not known")
            ),
            patch("httpx.AsyncClient") as mock_cls,
        ):
            result = await _web_read("http://nonexistent.invalid/")
        assert result is None
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # DNS rebinding mitigation  (edge)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_dns_rebinding_hostname_resolving_to_private_ip_is_blocked(
        self,
    ) -> None:
        """A public-looking hostname whose DNS resolves to a private IP must be blocked.

        This is the core DNS-rebinding scenario: the attacker controls DNS and
        returns an internal IP for their domain.  The implementation must check
        the IP *returned by DNS* — not just the raw hostname — before requesting.
        """
        mock_client = _make_mock_client("stolen metadata")
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.0.0.50")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            result = await _web_read("http://legitimate-looking.example.com/")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_dns_rebinding_httpx_receives_resolved_ip_not_original_hostname(
        self,
    ) -> None:
        """After safe DNS resolution httpx must connect to the resolved IP directly.

        Passing the original hostname URL to httpx lets httpx re-resolve the
        hostname — a second DNS lookup that the attacker can answer differently
        (DNS rebinding / TOCTOU).  The implementation must either rewrite the
        URL to the resolved IP or use a custom transport that bypasses httpx DNS.
        """
        mock_client = _make_mock_client("page content")
        mock_get = mock_client.__aenter__.return_value.get
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await _web_read("http://example.com/page")
        assert result == "page content", "safe IP should allow the fetch"
        assert mock_get.called, "httpx.get must be called for a safe resolved IP"
        # The URL passed to httpx must NOT contain the original hostname;
        # it must be rewritten to the resolved IP to prevent a second DNS lookup.
        call_url: str = (
            mock_get.call_args.args[0]
            if mock_get.call_args.args
            else mock_get.call_args.kwargs.get("url", repr(mock_get.call_args))
        )
        assert "example.com" not in call_url, (
            f"httpx was called with original hostname URL {call_url!r}; "
            "expected the URL to be rewritten to the resolved IP (93.184.216.34) "
            "to prevent DNS rebinding"
        )

    # ------------------------------------------------------------------
    # Retry additions (reviewer FAIL — missing AC coverage)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_localhost_hostname(self) -> None:
        """http://localhost/ resolves to 127.0.0.1 (loopback) — must return None.

        AC6 explicitly names 'localhost' as a required test case.  A literal-IP
        check would miss this; the implementation must resolve the hostname first.
        """
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            result = await _web_read("http://localhost/")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_broadcast_255_255_255_255(self) -> None:
        """255.255.255.255 (broadcast / reserved) — must return None, httpx never called.

        AC2 names 'broadcast' as a blocked range.  Python's ipaddress marks
        255.255.255.255 as is_reserved; the test validates that property is checked.
        """
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("255.255.255.255")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            result = await _web_read("http://255.255.255.255/")
        assert result is None
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_httpx_exception_returns_none(self) -> None:
        """An httpx exception during a safe fetch returns None — must not propagate.

        The except-Exception handler at the bottom of _web_read must catch
        network errors and return None so callers are never exposed to exceptions.
        """
        import httpx

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            try:
                result = await _web_read("http://example.com/page")
            except Exception as exc:  # noqa: BLE001
                pytest.fail(
                    f"_web_read raised {exc!r} on httpx error instead of returning None"
                )
        assert result is None
