"""HttpxContentFetcher — unauthenticated fetch via httpx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import httpx

from owlbear_knowledge._ssrf import check_url_allowed, system_host_resolver

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
            httpx.HTTPStatusError: On non-2xx HTTP responses.
        """
        await check_url_allowed(url, resolver=self._resolver)
        async with httpx.AsyncClient(transport=self._transport) as client:
            response = await client.get(url)
            response.raise_for_status()
        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        return HttpResponse(content=response.text, media_type=media_type)

    async def fetch(self, url: str) -> str:
        """Fetch *url* and return the response body text.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP responses.
        """
        response = await self.fetch_response(url)
        return response.content
