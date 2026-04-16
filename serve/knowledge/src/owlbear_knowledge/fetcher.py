"""HttpxContentFetcher — unauthenticated fetch via httpx."""

from __future__ import annotations

import urllib.parse

import httpx

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _check_url_scheme(url: str) -> None:
    """Raise ValueError if the URL has a scheme that is not http or https.

    Empty-string URLs are allowed through so httpx can produce its own error.
    """
    if not url:
        return
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        msg = f"URL scheme not allowed: {scheme!r}. Only http and https are permitted."
        raise ValueError(msg)


class HttpxContentFetcher:
    """ContentFetcher implementation backed by httpx.AsyncClient."""

    async def fetch(self, url: str) -> str:
        _check_url_scheme(url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
