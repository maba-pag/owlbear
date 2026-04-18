"""HttpxContentFetcher — unauthenticated fetch via httpx."""

from __future__ import annotations

from owlbear_knowledge._ssrf import safe_async_fetch


class HttpxContentFetcher:
    """ContentFetcher implementation backed by httpx.AsyncClient."""

    async def fetch(self, url: str) -> str:
        """Fetch *url* with SSRF protection (CWE-918).

        Delegates to :func:`owlbear_knowledge._ssrf.safe_async_fetch`.

        Raises:
            ValueError: If the scheme is not http/https, DNS resolution fails,
                        or any resolved IP is private/loopback/link-local/reserved/unspecified.
            httpx.HTTPStatusError: On non-2xx HTTP responses.
        """
        return await safe_async_fetch(url)
