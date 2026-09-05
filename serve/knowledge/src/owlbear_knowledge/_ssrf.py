"""SSRF preflight checks for outbound knowledge HTTP fetches."""

from __future__ import annotations

import asyncio
import inspect
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable
from typing import Any
from urllib.parse import urlparse

from owlbear_knowledge.protocols.failures import KnowledgeFailure, KnowledgeFailureStage

type AddressInfo = tuple[int, int, int, str, tuple[Any, ...]]
type HostResolver = Callable[
    [str, int],
    Awaitable[Iterable[AddressInfo]] | Iterable[AddressInfo],
]


class SSRFProtectionError(ValueError):
    """Raised when a URL resolves to a blocked network target."""

    def __init__(self, failure: KnowledgeFailure) -> None:
        self.failure = failure
        super().__init__(failure.message)


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


async def system_host_resolver(hostname: str, port: int) -> list[AddressInfo]:
    """Resolve a hostname through the system resolver without blocking the event loop."""
    return await asyncio.to_thread(socket.getaddrinfo, hostname, port, type=socket.SOCK_STREAM)


async def _resolve_addresses(resolver: HostResolver, hostname: str, port: int) -> tuple[AddressInfo, ...]:
    result = resolver(hostname, port)
    if inspect.isawaitable(result):
        result = await result
    return tuple(result)


async def check_url_allowed(  # noqa: C901
    url: str, *, resolver: HostResolver = system_host_resolver
) -> None:
    """Raise when *url* targets a non-public HTTP(S) address."""
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="url_rejected",
            retryable=False,
            message="URL authority is malformed",
        )
        raise SSRFProtectionError(failure) from exc
    if parsed.scheme not in {"http", "https"}:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="url_rejected",
            retryable=False,
            message="URL fetch supports only http and https",
        )
        raise SSRFProtectionError(failure)
    try:
        hostname = parsed.hostname
        has_credentials = parsed.username is not None or parsed.password is not None
    except ValueError as exc:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="url_rejected",
            retryable=False,
            message="URL authority is malformed",
        )
        raise SSRFProtectionError(failure) from exc
    if hostname is None:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="url_rejected",
            retryable=False,
            message="URL fetch requires a hostname",
        )
        raise SSRFProtectionError(failure)
    if has_credentials:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="url_rejected",
            retryable=False,
            message="URL credentials are not allowed",
        )
        raise SSRFProtectionError(failure)

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="url_rejected",
            retryable=False,
            message="URL fetch has an invalid port",
        )
        raise SSRFProtectionError(failure) from exc

    try:
        addrs = await _resolve_addresses(resolver, hostname, port)
    except Exception as exc:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="dns_failure",
            retryable=True,
            message="URL hostname could not be resolved",
        )
        raise SSRFProtectionError(failure) from exc

    has_ip_address = False
    for family, _socktype, _proto, _canonname, sockaddr in addrs:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        try:
            ip = str(sockaddr[0])
        except (IndexError, TypeError):
            continue
        has_ip_address = True
        if _is_blocked_ip(ip):
            failure = KnowledgeFailure(
                stage=KnowledgeFailureStage.ACQUISITION,
                code="url_rejected",
                retryable=False,
                message="URL resolves to a blocked network address",
            )
            raise SSRFProtectionError(failure)

    if not has_ip_address:
        failure = KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="dns_failure",
            retryable=True,
            message="URL hostname did not resolve to an IP address",
        )
        raise SSRFProtectionError(failure)
