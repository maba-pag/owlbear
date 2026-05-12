"""SSRF-safe HTTP fetch utility (CWE-918).

Exported interface:
- ``_is_blocked_ip(ip_str)``   — True if IP is private/loopback/link-local/reserved/unspecified.
- ``safe_async_fetch(url)``    — Full resolve → check → rewrite → fetch pipeline.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse, urlunparse


def _is_blocked_ip(ip_str: str) -> bool:
    """Return True if *ip_str* is a private/loopback/link-local/reserved/unspecified address."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable → block
    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) before checking properties.
    # IPv6Address.ipv4_mapped is None for pure IPv6 addresses.
    check: ipaddress.IPv4Address | ipaddress.IPv6Address
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        check = addr.ipv4_mapped
    else:
        check = addr
    return (
        check.is_loopback
        or check.is_private
        or check.is_link_local
        or check.is_reserved
        or check.is_unspecified
    )


async def safe_async_fetch(url: str) -> str:
    """Fetch *url* with SSRF protection (CWE-918). Returns the response body as text.

    Raises:
        ValueError: If the scheme is not http/https, DNS resolution fails, or any
                    resolved IP is private/loopback/link-local/reserved/unspecified.
        httpx.HTTPStatusError: On non-2xx HTTP responses.
    """
    import httpx  # noqa: PLC0415  # optional dep — only required at call time

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        msg = f"URL scheme {scheme!r} is not allowed; only http and https are permitted"
        raise ValueError(msg)

    hostname = parsed.hostname
    if not hostname:
        msg = "URL has no hostname"
        raise ValueError(msg)

    port = parsed.port or (443 if scheme == "https" else 80)

    try:
        addrs = await asyncio.to_thread(
            socket.getaddrinfo, hostname, port, 0, socket.AF_UNSPEC
        )
    except OSError as exc:
        msg = f"DNS resolution failed for {hostname!r}: {exc}"
        raise ValueError(msg) from exc

    for _family, _socktype, _proto, _canon, sockaddr in addrs:
        if _is_blocked_ip(sockaddr[0]):
            msg = (
                f"URL {url!r} is blocked: resolved IP {sockaddr[0]!r} is "
                "private, loopback, link-local, or reserved (SSRF protection)"
            )
            raise ValueError(msg)

    # Rewrite request URL to the resolved IP to prevent DNS-rebinding TOCTOU.
    first_ip = ipaddress.ip_address(addrs[0][4][0])
    ip_host = (
        f"[{first_ip}]"
        if isinstance(first_ip, ipaddress.IPv6Address)
        else str(first_ip)
    )
    netloc = f"{ip_host}:{parsed.port}" if parsed.port else ip_host
    ip_url = urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )

    async with httpx.AsyncClient(follow_redirects=False, timeout=30) as client:
        resp = await client.get(ip_url, headers={"Host": hostname})
        resp.raise_for_status()
        return resp.text
