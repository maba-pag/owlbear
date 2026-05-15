"""HttpxContentFetcher — unauthenticated fetch via httpx."""

from __future__ import annotations

import httpx


class HttpxContentFetcher:
    """ContentFetcher implementation backed by httpx.AsyncClient."""

    async def fetch(self, url: str) -> str:
        """Fetch *url* and return the response body text.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP responses.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
        return response.text
