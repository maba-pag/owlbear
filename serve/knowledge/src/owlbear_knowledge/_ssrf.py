"""SSRF preflight checks for outbound knowledge HTTP fetches."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


class SSRFProtectionError(ValueError):
    """Raised when a URL resolves to a blocked network target."""


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        address = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


async def check_url_allowed(url: str) -> None:
    """Raise when *url* targets a non-public HTTP(S) address."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        msg = "URL fetch supports only http and https"
        raise SSRFProtectionError(msg)
    if parsed.hostname is None:
        msg = "URL fetch requires a hostname"
        raise SSRFProtectionError(msg)

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        msg = "URL fetch has an invalid port"
        raise SSRFProtectionError(msg) from exc

    try:
        addrs = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        msg = "URL hostname could not be resolved"
        raise SSRFProtectionError(msg) from exc

    for family, _socktype, _proto, _canonname, sockaddr in addrs:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        ip = sockaddr[0]
        if _is_blocked_ip(ip):
            msg = "URL resolves to a blocked network address"
            raise SSRFProtectionError(msg)
