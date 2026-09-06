"""HTML content extraction for the shared web-content package."""

from __future__ import annotations

import re

import trafilatura
from lxml import html as lxml_html

from owlbear_web_content.cleaner import html_to_markdown, normalize, strip_noise


def _preserves_structure(result: str, fallback: str, image_alternatives: list[str]) -> bool:
    """Return whether an extracted result retains structural content."""
    targets = re.findall(r"\]\(([^)]*)\)", fallback)
    code_spans = [match.group() for match in re.finditer(r"(?P<delimiter>`+).*?(?P=delimiter)", fallback)]
    return (
        all(f"]({target})" in result for target in targets)
        and all(alternative in result for alternative in image_alternatives)
        and all(code_span in result for code_span in code_spans)
    )


def _extract_markdown(html: str, url: str | None = None) -> str:
    """Extract Markdown and retain structural links through the cleaner fallback."""
    noise_free = strip_noise(html)
    result = trafilatura.extract(
        noise_free,
        url=url,
        output_format="markdown",
        include_links=True,
        include_tables=True,
    )
    fallback = normalize(html_to_markdown(noise_free, url=url))
    document = lxml_html.fromstring(noise_free)
    image_alternatives = [alt for image in document.iter("img") if (alt := (image.get("alt") or "").strip())]
    if result and _preserves_structure(result, fallback, image_alternatives):
        return normalize(result)
    return fallback


def extract(html: str) -> str:
    """Extract main content from HTML as Markdown.

    Args:
        html: HTML string to extract content from.

    Returns:
        Extracted content as Markdown, or an empty string when no content is found.

    Raises:
        TypeError: If ``html`` is not a string.
    """
    if not isinstance(html, str):
        msg = f"html must be str, got {type(html).__name__}"
        raise TypeError(msg)
    if not html or not html.strip():
        return ""
    return _extract_markdown(html)


def extract_content(html: str, url: str | None = None) -> str:
    """Extract main content with a cleaner fallback.

    Args:
        html: HTML string to extract content from.
        url: Optional source URL passed to the extraction library.

    Returns:
        Extracted content as Markdown, or an empty string for empty input.
    """
    if not html or not html.strip():
        return ""
    return _extract_markdown(html, url=url)
