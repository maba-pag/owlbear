"""HTML content extraction for the shared web-content package."""

from __future__ import annotations

import re
from urllib.parse import urljoin

import trafilatura
from lxml import html as lxml_html

from owlbear_web_content.cleaner import html_to_markdown, normalize, strip_noise

_FENCE_LINE_RE = re.compile(r"^(?P<indent>[ ]*)(?P<marker>`{3,}|~{3,})(?P<rest>.*)$")
_LIST_LINE_RE = re.compile(r"^\s*(?:[-+*]|\d+\.)\s+")
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")


def _can_open_fence(match: re.Match[str] | None) -> bool:
    """Return whether a fence match can start a fenced code block."""
    return match is not None and not (match.group("marker").startswith("`") and "`" in match.group("rest"))


def _fenced_code_ranges(markdown: str) -> list[tuple[int, int, str]]:
    """Return complete fenced code blocks with their source ranges."""
    ranges: list[tuple[int, int, str]] = []
    current: list[str] | None = None
    start: int | None = None
    fence_character: str | None = None
    fence_length = 0
    offset = 0

    for line in markdown.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        match = _FENCE_LINE_RE.match(content)
        if current is None:
            if _can_open_fence(match):
                current = [line]
                start = offset
                marker = match.group("marker")
                fence_character = marker[0]
                fence_length = len(marker)
        else:
            current.append(line)
            if (
                match is not None
                and match.group("marker")[0] == fence_character
                and len(match.group("marker")) >= fence_length
                and not match.group("rest").strip()
            ):
                if start is not None:
                    ranges.append(
                        (
                            start,
                            offset + len(line),
                            "".join(current).rstrip("\r\n"),
                        )
                    )
                current = None
                start = None
                fence_character = None
                fence_length = 0
        offset += len(line)
    return ranges


def _inline_code_spans_in_text(text: str) -> list[str]:
    """Return complete inline code spans from text outside fenced blocks."""
    spans: list[str] = []
    index = 0
    while index < len(text):
        if text[index] != "`":
            index += 1
            continue
        delimiter_start = index
        while index < len(text) and text[index] == "`":
            index += 1
        delimiter = text[delimiter_start:index]
        search = index
        while (closing := text.find(delimiter, search)) != -1:
            closing_end = closing + len(delimiter)
            if (closing == 0 or text[closing - 1] != "`") and (closing_end == len(text) or text[closing_end] != "`"):
                spans.append(text[delimiter_start:closing_end])
                index = closing_end
                break
            search = closing_end
        else:
            index = delimiter_start + len(delimiter)
    return spans


def _inline_code_spans(markdown: str) -> list[str]:
    """Return complete inline code spans without treating fenced blocks as spans."""
    spans: list[str] = []
    cursor = 0
    for start, end, _block in _fenced_code_ranges(markdown):
        spans.extend(_inline_code_spans_in_text(markdown[cursor:start]))
        cursor = end
    spans.extend(_inline_code_spans_in_text(markdown[cursor:]))
    return spans


def _structural_lines(markdown: str) -> list[str]:
    """Return list and table lines outside fenced code blocks."""
    visible_chunks: list[str] = []
    cursor = 0
    for start, end, _block in _fenced_code_ranges(markdown):
        visible_chunks.append(markdown[cursor:start])
        cursor = end
    visible_chunks.append(markdown[cursor:])
    return [
        line
        for chunk in visible_chunks
        for line in chunk.splitlines()
        if _LIST_LINE_RE.match(line) or _TABLE_LINE_RE.match(line)
    ]


def _contains_in_order(actual: list[str], expected: list[str]) -> bool:
    """Return whether every expected value appears in order in the actual values."""
    position = 0
    for value in expected:
        try:
            position = actual.index(value, position) + 1
        except ValueError:
            return False
    return True


def _preserves_structure(
    result: str,
    link_targets: list[str],
    image_targets: list[str],
    image_fragments: list[str],
    fallback: str,
) -> bool:
    """Return whether an extracted result retains structural content."""
    if not all(f"]({target})" in result for target in [*link_targets, *image_targets]):
        return False
    if not all(fragment in result for fragment in image_fragments):
        return False
    fallback_blocks = [block for _start, _end, block in _fenced_code_ranges(fallback)]
    result_blocks = [block for _start, _end, block in _fenced_code_ranges(result)]
    if not _contains_in_order(result_blocks, fallback_blocks):
        return False
    if not _contains_in_order(_inline_code_spans(result), _inline_code_spans(fallback)):
        return False
    return _contains_in_order(_structural_lines(result), _structural_lines(fallback))


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
    link_targets = [
        urljoin(url, target) if url is not None else target
        for link in document.iter("a")
        if (target := link.get("href")) is not None
    ]
    image_targets = [
        urljoin(url, source) if url is not None else source
        for image in document.iter("img")
        if (image.get("alt") or "").strip() and (source := image.get("src"))
    ]
    image_fragments = [
        normalize(
            html_to_markdown(
                lxml_html.tostring(image, encoding="unicode", with_tail=False),
                url=url,
            )
        )
        for image in document.iter("img")
        if (image.get("alt") or "").strip()
    ]
    normalized_result = normalize(result) if result else ""
    if result and _preserves_structure(
        normalized_result,
        link_targets,
        image_targets,
        image_fragments,
        fallback,
    ):
        return normalized_result
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
