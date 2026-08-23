"""HttpxContentFetcher — unauthenticated fetch via httpx."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import httpx

from owlbear_knowledge._ssrf import SSRFProtectionError, check_url_allowed, system_host_resolver
from owlbear_knowledge.protocols.failures import (
    KnowledgeFailure,
    KnowledgeFailureStage,
    KnowledgeOperationError,
)

if TYPE_CHECKING:
    from owlbear_knowledge._ssrf import HostResolver


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Decoded HTTP response content and its declared media type."""

    content: str
    media_type: str


@runtime_checkable
class HttpResponseFetcher(Protocol):
    """Protocol for HTTP fetchers that preserve response metadata."""

    async def fetch_response(self, url: str) -> HttpResponse:
        """Fetch a URL and return its decoded content with media metadata."""
        ...


@runtime_checkable
class ContentFetcher(Protocol):
    """Protocol for HTTP-style source fetchers used by ingest adapters."""

    async def fetch(self, url: str) -> str:
        """Fetch the URL and return response text."""
        ...


REQUEST_TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 5_000_000
RETRYABLE_HTTP_STATUS = 429
SERVER_ERROR_STATUS_MINIMUM = 500


def failure_for_fetch_exception(exc: Exception) -> KnowledgeFailure:
    """Convert a fetch exception to a redacted acquisition failure."""
    if isinstance(exc, KnowledgeOperationError):
        return exc.failure
    if isinstance(exc, SSRFProtectionError):
        return exc.failure
    if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
        return KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="timeout",
            retryable=True,
            message="HTTP request timed out",
        )
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="http_status",
            retryable=status_code == RETRYABLE_HTTP_STATUS or status_code >= SERVER_ERROR_STATUS_MINIMUM,
            message=f"HTTP request returned status {status_code}",
        )
    if isinstance(exc, httpx.TransportError):
        return KnowledgeFailure(
            stage=KnowledgeFailureStage.ACQUISITION,
            code="transport_failure",
            retryable=True,
            message="HTTP transport failed",
        )
    return KnowledgeFailure(
        stage=KnowledgeFailureStage.ACQUISITION,
        code="transport_failure",
        retryable=True,
        message="Content acquisition failed",
    )


class HttpxContentFetcher(ContentFetcher, HttpResponseFetcher):
    """ContentFetcher implementation backed by httpx.AsyncClient."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: HostResolver = system_host_resolver,
    ) -> None:
        self._transport = transport
        self._resolver = resolver

    async def fetch_response(self, url: str) -> HttpResponse:
        """Fetch *url* and return its body with the declared media type.

        Raises:
            KnowledgeOperationError: For status, timeout, transport, or size failures.
        """
        await check_url_allowed(url, resolver=self._resolver)
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except KnowledgeOperationError:
            raise
        except Exception as exc:
            failure = failure_for_fetch_exception(exc)
            raise KnowledgeOperationError(failure) from exc
        if len(response.content) > MAX_RESPONSE_BYTES:
            failure = KnowledgeFailure(
                stage=KnowledgeFailureStage.ACQUISITION,
                code="response_too_large",
                retryable=False,
                message="HTTP response exceeded the maximum allowed size",
            )
            raise KnowledgeOperationError(failure)
        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        return HttpResponse(content=response.text, media_type=media_type)

    async def fetch(self, url: str) -> str:
        """Fetch *url* and return the response body text.

        Raises:
            KnowledgeOperationError: For response acquisition failures.
        """
        response = await self.fetch_response(url)
        return response.content
