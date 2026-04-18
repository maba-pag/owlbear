"""HttpxContentFetcher — unauthenticated fetch via httpx."""

from __future__ import annotations

from owlbear_knowledge._ssrf import safe_async_fetch


class HttpxContentFetcher:
    """ContentFetcher implementation backed by httpx.AsyncClient."""

    async def fetch(self, url: str) -> str:
        return await safe_async_fetch(url)
