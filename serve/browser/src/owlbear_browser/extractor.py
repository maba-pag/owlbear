"""HTML content extractor for owlbear_browser.

Provides two public functions:
  - extract(html)              → markdown string (raises TypeError on non-str input)
  - extract_content(html, url) → markdown string with trafilatura + cleaner fallback
"""

from __future__ import annotations

import trafilatura

from owlbear_browser.cleaner import html_to_markdown, strip_noise


def extract(html: str) -> str:
    """Extract main content from an HTML string, returning markdown.

    Noise elements (nav, footer, scripts, cookie banners) are stripped before
    extraction so they do not contaminate the result.

    Args:
        html: HTML string to extract content from.

    Returns:
        Extracted content as a markdown string, or empty string if no content found.

    Raises:
        TypeError: If html is not a str.
    """
    if not isinstance(html, str):
        msg = f"html must be str, got {type(html).__name__}"
        raise TypeError(msg)
    if not html or not html.strip():
        return ""
    noise_free = strip_noise(html)
    result = trafilatura.extract(
        noise_free,
        output_format="markdown",
        include_links=True,
        include_tables=True,
    )
    if result:
        return result
    return html_to_markdown(noise_free)


def extract_content(html: str, url: str | None = None) -> str:
    """Extract main content using trafilatura with a cleaner fallback.

    Noise elements are stripped before extraction. Falls back to the cleaner's
    html_to_markdown converter when trafilatura returns no content.

    Args:
        html: HTML string to extract content from.
        url:  Optional source URL passed to trafilatura for relative-link resolution
              and extraction heuristics. Defaults to None.

    Returns:
        Extracted content as a markdown string, or empty string for empty input.
    """
    if not html or not html.strip():
        return ""
    noise_free = strip_noise(html)
    result = trafilatura.extract(
        noise_free,
        url=url,
        output_format="markdown",
        include_links=True,
        include_tables=True,
    )
    if result:
        return result
    return html_to_markdown(noise_free)
