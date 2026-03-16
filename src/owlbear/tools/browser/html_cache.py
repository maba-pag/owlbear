"""Raw-HTML cache layer for WebCrawler.

Provides :class:`HtmlCache` — a simple file-based cache keyed by
``SHA-256(normalize_url(url))`` with ``.html`` extension.  Cache I/O
errors are caught internally and never propagate to the caller.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import TYPE_CHECKING

from owlbear.tools.browser.url_utils import normalize_url

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["HtmlCache"]


class HtmlCache:
    """File-based raw-HTML cache.

    Stores HTML responses on disk, keyed by SHA-256 hex digest of the
    normalized URL.  All I/O errors are caught internally (logged at
    DEBUG) and never propagate — the cache is advisory only.

    Args:
        cache_dir: Absolute path to the cache directory.  Created
            (with parents) if it does not exist.

    Raises:
        ValueError: If *cache_dir* is not an absolute path.
    """

    def __init__(self, cache_dir: Path) -> None:
        if not cache_dir.is_absolute():
            msg = f"cache_dir must be absolute, got: {cache_dir}"
            raise ValueError(msg)
        self._cache_dir = cache_dir.resolve()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, url: str, ttl_seconds: int) -> str | None:
        """Return cached HTML for *url*, or ``None`` on miss/expired/error.

        Args:
            url: The URL to look up (normalized internally).
            ttl_seconds: Maximum age in seconds.  ``0`` means no expiry.

        Returns:
            The cached HTML string, or ``None``.
        """
        filepath = self._path_for(url)
        try:
            if not filepath.is_file():
                return None
            if ttl_seconds > 0:
                age = time.time() - filepath.stat().st_mtime
                if age > ttl_seconds:
                    return None
            return filepath.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            logger.debug("Cache read failed for %s", url, exc_info=True)
            return None

    def put(self, url: str, html: str) -> None:
        """Store *html* for *url*.  Silently ignores write errors.

        Args:
            url: The URL to cache (normalized internally).
            html: Raw HTML string to store.
        """
        filepath = self._path_for(url)
        try:
            filepath.write_text(html, encoding="utf-8")
        except Exception:  # noqa: BLE001
            logger.debug("Cache write failed for %s", url, exc_info=True)

    # -- private helpers --

    def _path_for(self, url: str) -> Path:
        """Return the cache file path for *url*."""
        normalized = normalize_url(url)
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        return self._cache_dir / f"{digest}.html"
