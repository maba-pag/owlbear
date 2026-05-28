"""HttpxContentFetcher — unauthenticated fetch via httpx."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx

from owlbear_knowledge._ssrf import check_url_allowed


@runtime_checkable
class ContentFetcher(Protocol):
    """Protocol for HTTP-style source fetchers used by ingest adapters."""

    async def fetch(self, url: str) -> str:
        """Fetch the URL and return response text."""
        ...


class HttpxContentFetcher(ContentFetcher):
    """ContentFetcher implementation backed by httpx.AsyncClient."""

    async def fetch(self, url: str) -> str:
        """Fetch *url* and return the response body text.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP responses.
        """
        await check_url_allowed(url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
        return response.text
