"""Content extraction via trafilatura.

Provides :func:`extract_content` — extracts article text and metadata
from raw HTML using `trafilatura <https://github.com/adbar/trafilatura>`_.
Outputs Markdown-formatted text suitable for the knowledge ingestion pipeline.

trafilatura is an **optional** dependency (``owlbear[crawl]``).  When not
installed, :func:`extract_content` raises :class:`ImportError` on first call.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from owlbear.web_extract import extract_markdown

logger = logging.getLogger(__name__)

try:
    import trafilatura
except ImportError:  # pragma: no cover
    trafilatura = None  # type: ignore[assignment]

__all__ = ["ExtractionResult", "extract_content"]


class ExtractionResult(BaseModel, frozen=True):
    """Frozen result of content extraction from HTML.

    Attributes:
        text: Extracted article text in Markdown format.  Empty string
            when extraction fails.
        title: Page/article title, or ``None`` if unavailable.
        author: Author name, or ``None`` if unavailable.
        date: Publication date string, or ``None`` if unavailable.
        metadata: Additional metadata dictionary (title, author, date
            are also stored here for convenience).
    """

    text: str
    title: str | None = None
    author: str | None = None
    date: str | None = None
    metadata: dict[str, Any] = {}


def extract_content(html: str, url: str | None = None) -> ExtractionResult:
    """Extract article content and metadata from raw HTML.

    Uses ``trafilatura.extract`` with Markdown output and
    ``trafilatura.extract_metadata`` for structured metadata.

    Args:
        html: Raw HTML string (typically from ``page.content()``).
        url: Optional source URL — passed to trafilatura for
            resolving relative links in the output.

    Returns:
        An :class:`ExtractionResult` with the extracted text and metadata.
        On any extraction failure, returns a result with ``text=""``
        and ``None`` metadata fields — **never raises**.

    Raises:
        ImportError: If trafilatura is not installed.
    """
    if trafilatura is None:  # pragma: no cover
        msg = (
            "trafilatura is not installed — install with:"
            " uv sync --extra crawl  or  uv sync --extra search"
        )
        raise ImportError(msg)

    # --- Extract text -------------------------------------------------------
    text = extract_markdown(html, url=url)

    # --- Extract metadata ---------------------------------------------------
    title: str | None = None
    author: str | None = None
    date: str | None = None
    meta_dict: dict[str, Any] = {}

    try:
        meta = trafilatura.extract_metadata(html)
        if meta is not None:
            title = meta.title
            author = meta.author
            date = meta.date
            meta_dict = {
                "title": title,
                "author": author,
                "date": date,
            }
    except Exception:  # noqa: BLE001 — trafilatura can raise anything
        logger.debug("trafilatura.extract_metadata failed", exc_info=True)

    extracted = text or ""

    from owlbear.config import OwlBearSettings  # noqa: PLC0415

    if extracted and OwlBearSettings().wrap_web_content:
        from owlbear.core.content_safety import wrap_untrusted_content  # noqa: PLC0415

        extracted = wrap_untrusted_content(extracted, source_url=url)

    return ExtractionResult(
        text=extracted,
        title=title,
        author=author,
        date=date,
        metadata=meta_dict,
    )
