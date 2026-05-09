"""Failing tests for task #947: SSRF fix in read_url — CWE-918 blocklist.

All tests must FAIL with the current read_url (no scheme check, no IP
validation, no DNS pre-resolution).  They will pass once the builder extracts
``_ssrf.py`` and wires ``read_url`` to delegate to ``safe_async_fetch``.

Patch strategy mirrors test_ssrf_fix_946.py:
- ``socket.getaddrinfo`` — intercepted because the implementation must use
  ``asyncio.to_thread(socket.getaddrinfo, ...)``
- ``httpx.AsyncClient`` — used by the implementation for the actual HTTP call

Key behavioural differences from _web_read (#946):
- ``read_url`` RAISES ``ValueError`` on blocked URLs (does not return None)
- ``read_url`` RAISES ``ValueError`` on unsupported schemes
- ``read_url`` RAISES ``ValueError`` on DNS failure
- On success, returns ``IntakeResult`` (not a bare string)
"""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge.intake import read_url


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
# Tests: read_url SSRF protection
# ---------------------------------------------------------------------------


class TestFromAC_ReadUrlSSRF:
    """Contract tests for read_url SSRF protection (revised AC #947).

    Every test below fails with the current code because read_url:
    - does not validate the URL scheme
    - does not resolve DNS before fetching
    - does not block private/loopback/reserved IP ranges
    - does not raise ValueError for any of the above
    """

    # ------------------------------------------------------------------
    # AC1: Non-http(s) schemes raise ValueError before DNS resolution
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rejects_file_scheme_raises_valueerror(self) -> None:
        """file:// URL must raise ValueError before any DNS or HTTP call."""
        with (
            patch("socket.getaddrinfo") as mock_dns,
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await read_url("file:///etc/passwd")
        mock_dns.assert_not_called()
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_ftp_scheme_raises_valueerror(self) -> None:
        """ftp:// URL must raise ValueError before any DNS or HTTP call."""
        with (
            patch("socket.getaddrinfo") as mock_dns,
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await read_url("ftp://example.com/file.txt")
        mock_dns.assert_not_called()
        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_gopher_scheme_raises_valueerror(self) -> None:
        """gopher:// URL must raise ValueError — scheme bypasses DNS entirely."""
        with (
            patch("socket.getaddrinfo") as mock_dns,
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await read_url("gopher://example.com/1/path")
        mock_dns.assert_not_called()
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # AC3 + AC6 + AC8: Blocked IPv4 literals — must raise ValueError
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_0_0_1_raises_valueerror(self) -> None:
        """http://127.0.0.1/ is loopback — must raise ValueError, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with pytest.raises(ValueError):
                await read_url("http://127.0.0.1/")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_x_non_zero_raises_valueerror(self) -> None:
        """127.0.0.100 is still in 127.0.0.0/8 — must raise ValueError."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with pytest.raises(ValueError):
                await read_url("http://127.0.0.100/secret")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_private_10_x_raises_valueerror(self) -> None:
        """10.0.0.1 (RFC-1918) — must raise ValueError, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with pytest.raises(ValueError):
                await read_url("http://10.0.0.1/admin")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_private_172_16_x_raises_valueerror(self) -> None:
        """172.16.0.1 (RFC-1918) — must raise ValueError, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with pytest.raises(ValueError):
                await read_url("http://172.16.0.1/")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_private_192_168_x_raises_valueerror(self) -> None:
        """192.168.1.1 (RFC-1918) — must raise ValueError, httpx never called."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with pytest.raises(ValueError):
                await read_url("http://192.168.1.1/")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_link_local_169_254_169_254_raises_valueerror(self) -> None:
        """169.254.169.254 (AWS IMDS / link-local) — must raise ValueError."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with pytest.raises(ValueError):
                await read_url("http://169.254.169.254/latest/meta-data/")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_unspecified_0_0_0_0_raises_valueerror(self) -> None:
        """0.0.0.0 (INADDR_ANY / unspecified) — must raise ValueError."""
        mock_client = _make_mock_client()
        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with pytest.raises(ValueError):
                await read_url("http://0.0.0.0/")
            mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # AC3 + AC6 + AC8: Blocked IPv6 literals — must raise ValueError
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_ipv6_loopback_1_raises_valueerror(self) -> None:
        """::1 (IPv6 loopback) — must raise ValueError, httpx never called."""
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            with pytest.raises(ValueError):
                await read_url("http://[::1]/")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_ipv6_unspecified_raises_valueerror(self) -> None:
        """:: (IPv6 unspecified / all-zeros) — must raise ValueError."""
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            with pytest.raises(ValueError):
                await read_url("http://[::]/")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_ipv6_link_local_fe80_raises_valueerror(self) -> None:
        """fe80::1 (IPv6 link-local) — must raise ValueError, httpx never called."""
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("fe80::1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            with pytest.raises(ValueError):
                await read_url("http://[fe80::1]/")
            mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_ipv4_mapped_loopback_raises_valueerror(self) -> None:
        """::ffff:127.0.0.1 (IPv4-mapped loopback) — must raise ValueError.

        Without an explicit ``.ipv4_mapped`` unwrap, IPv6Address('::ffff:127.0.0.1')
        is NOT reported as loopback — this is the IPv6 bypass vector (CWE-918).
        """
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr6("::ffff:127.0.0.1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            with pytest.raises(ValueError):
                await read_url("http://[::ffff:127.0.0.1]/")
            mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # AC8: localhost hostname (requires DNS pre-resolution)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocks_localhost_hostname_raises_valueerror(self) -> None:
        """http://localhost/ resolves to 127.0.0.1 — must raise ValueError.

        A literal-IP-only check would pass localhost through; the implementation
        must resolve the hostname via DNS before checking the resulting IP.
        """
        mock_client = _make_mock_client()
        with (
            patch("socket.getaddrinfo", return_value=_addr4("127.0.0.1")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            with pytest.raises(ValueError):
                await read_url("http://localhost/")
            mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # AC6: ValueError message is descriptive
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_blocked_ip_valueerror_has_descriptive_message(self) -> None:
        """The ValueError for a blocked URL must carry a human-readable message."""
        with pytest.raises(
            ValueError, match=r"(?i)(block|ssrf|private|loopback|forbidden|not allow)"
        ):
            await read_url("http://192.168.99.1/secret")

    # ------------------------------------------------------------------
    # AC2 + failure-mode-map: DNS failure raises ValueError
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_dns_failure_raises_valueerror(self) -> None:
        """Unresolvable hostname raises ValueError — not silently returns None/content."""
        with (
            patch(
                "socket.getaddrinfo", side_effect=OSError("Name or service not known")
            ),
            patch("httpx.AsyncClient") as mock_cls,
            pytest.raises(ValueError),
        ):
            await read_url("http://nonexistent.invalid/path")
        mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # AC4: DNS rebinding — hostname resolving to private IP is blocked
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_dns_rebinding_private_resolution_raises_valueerror(self) -> None:
        """A hostname whose DNS resolves to 10.0.0.50 must raise ValueError.

        This is the DNS-rebinding attack: the attacker controls DNS to return an
        internal IP for a legitimate-looking domain.  The check must happen on
        the IP *returned by DNS*, not on the hostname string.
        """
        mock_client = _make_mock_client("stolen data")
        with (
            patch("socket.getaddrinfo", return_value=_addr4("10.0.0.50")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            with pytest.raises(ValueError):
                await read_url("http://legitimate-looking.example.com/")
            mock_cls.assert_not_called()

    # ------------------------------------------------------------------
    # AC4: DNS rebinding TOCTOU — httpx must receive resolved IP, not hostname
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_dns_rebinding_httpx_receives_resolved_ip_not_hostname(self) -> None:
        """After safe DNS resolution, httpx must connect to the resolved IP directly.

        Passing the original hostname to httpx causes a second DNS lookup — the
        TOCTOU window an attacker can exploit by giving a different answer the
        second time (DNS rebinding).
        """
        mock_client = _make_mock_client("page content")
        mock_get = mock_client.__aenter__.return_value.get
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await read_url("http://example.com/page")
        assert result is not None, "safe public IP must allow the fetch"
        assert mock_get.called, "httpx.get must be called for a safe resolved IP"
        call_url: str = (
            mock_get.call_args.args[0]
            if mock_get.call_args.args
            else mock_get.call_args.kwargs.get("url", repr(mock_get.call_args))
        )
        assert "example.com" not in call_url, (
            f"httpx was called with original hostname URL {call_url!r}; "
            "expected URL rewritten to resolved IP (93.184.216.34) to prevent DNS rebinding"
        )

    # ------------------------------------------------------------------
    # AC4: Host header set to original hostname for TLS/virtual-host routing
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_host_header_set_to_original_hostname(self) -> None:
        """httpx request must include Host header set to the original hostname.

        Required for TLS SNI and virtual-host routing when the request URL has
        been rewritten to the resolved IP address.
        """
        mock_client = _make_mock_client("content")
        mock_get = mock_client.__aenter__.return_value.get
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            await read_url("http://example.com/")
        assert mock_get.called
        headers = mock_get.call_args.kwargs.get("headers", {})
        assert "Host" in headers or "host" in headers, (
            f"Expected 'Host' header in httpx call, got headers={headers!r}"
        )
        host_value = headers.get("Host") or headers.get("host")
        assert host_value == "example.com", (
            f"Host header should be 'example.com', got {host_value!r}"
        )

    # ------------------------------------------------------------------
    # AC5: follow_redirects=False
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_follow_redirects_is_disabled(self) -> None:
        """AsyncClient must be constructed with follow_redirects=False.

        Defense-in-depth: a redirect chain can lead to a private IP, bypassing
        the pre-fetch IP blocklist entirely.
        """
        mock_client = _make_mock_client("content")
        with (
            patch("socket.getaddrinfo", return_value=_addr4("93.184.216.34")),
            patch("httpx.AsyncClient", return_value=mock_client) as mock_cls,
        ):
            await read_url("http://example.com/")
        assert mock_cls.called
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs.get("follow_redirects") is False, (
            f"AsyncClient must be created with follow_redirects=False, "
            f"got follow_redirects={call_kwargs.get('follow_redirects')!r}"
        )

    # ------------------------------------------------------------------
    # Happy path: safe public IP — DNS must be resolved (current code skips this)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_allows_safe_public_ip_dns_resolved_before_fetch(self) -> None:
        """A URL resolving to a safe IP returns IntakeResult; DNS must be called.

        The current code does NOT call socket.getaddrinfo — it fetches directly.
        ``mock_dns.assert_called_once()`` verifies DNS pre-resolution is wired up.
        """
        from owlbear_knowledge.intake import IntakeResult

        mock_client = _make_mock_client("public page content")
        with (
            patch(
                "socket.getaddrinfo", return_value=_addr4("93.184.216.34")
            ) as mock_dns,
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await read_url("http://example.com/")
        assert isinstance(result, IntakeResult)
        assert result.content == "public page content"
        # This is the assertion that fails in RED: current code never calls getaddrinfo.
        mock_dns.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _ssrf utility module extraction (AC7)
# ---------------------------------------------------------------------------


class TestFromAC_SsrfUtility:
    """Verify owlbear_knowledge._ssrf is extracted with the required interface (AC7).

    Each test imports the module inside the test body via ``importlib`` so that
    a missing module causes an individual ``ModuleNotFoundError`` (FAIL) rather
    than a collection-time error that would shadow all other tests in this file.

    All tests below fail in RED because ``_ssrf.py`` does not yet exist.
    """

    def test_ssrf_module_is_importable(self) -> None:
        """owlbear_knowledge._ssrf must be importable as a standalone module."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert mod is not None

    def test_is_blocked_ip_is_exported(self) -> None:
        """_is_blocked_ip must be a callable exported from owlbear_knowledge._ssrf."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert callable(getattr(mod, "_is_blocked_ip", None)), (
            "_ssrf._is_blocked_ip is missing or not callable"
        )

    def test_safe_async_fetch_is_exported(self) -> None:
        """safe_async_fetch must be a callable exported from owlbear_knowledge._ssrf."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert callable(getattr(mod, "safe_async_fetch", None)), (
            "_ssrf.safe_async_fetch is missing or not callable"
        )

    def test_is_blocked_ip_blocks_loopback_127_0_0_1(self) -> None:
        """_is_blocked_ip('127.0.0.1') must return True."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert mod._is_blocked_ip("127.0.0.1") is True

    def test_is_blocked_ip_blocks_private_10_x(self) -> None:
        """_is_blocked_ip('10.0.0.1') must return True."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert mod._is_blocked_ip("10.0.0.1") is True

    def test_is_blocked_ip_blocks_unspecified_0_0_0_0(self) -> None:
        """_is_blocked_ip('0.0.0.0') must return True (is_unspecified)."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert mod._is_blocked_ip("0.0.0.0") is True  # noqa: S104

    def test_is_blocked_ip_blocks_ipv6_unspecified(self) -> None:
        """_is_blocked_ip('::') must return True (IPv6 unspecified)."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert mod._is_blocked_ip("::") is True

    def test_is_blocked_ip_blocks_ipv4_mapped_loopback(self) -> None:
        """_is_blocked_ip('::ffff:127.0.0.1') must return True.

        Without an explicit ``.ipv4_mapped`` unwrap, IPv6Address('::ffff:127.0.0.1')
        reports is_loopback=False — the IPv4-mapped bypass vector.
        """
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert mod._is_blocked_ip("::ffff:127.0.0.1") is True

    def test_is_blocked_ip_allows_safe_public_ip(self) -> None:
        """_is_blocked_ip('93.184.216.34') must return False (safe public IP)."""
        import importlib

        mod = importlib.import_module("owlbear_knowledge._ssrf")
        assert mod._is_blocked_ip("93.184.216.34") is False


# --- merged from serve/knowledge/tests/test_ssrf_fix_ipv6.py ---
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

