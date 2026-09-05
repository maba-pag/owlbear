"""HTML noise stripping and Markdown conversion for web content."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lxml import html as lxml_html

if TYPE_CHECKING:
    from collections.abc import Callable

    from lxml.html import HtmlElement

_NOISE_TAGS: frozenset[str] = frozenset({"nav", "header", "footer", "aside", "script", "style"})
_NOISE_CLASSES: frozenset[str] = frozenset(
    {
        "cookie-banner",
        "cookie-notice",
        "cookie-popup",
        "cookie-bar",
        "ms-header",
        "ms-commandBar",
        "ms-commandbar",
        "ms-pageEditBar",
        "ms-Breadcrumb",
        "ms-Persona",
        "ms-LivePersona",
        "ms-DateTimeField",
    }
)
_NOISE_IDS: frozenset[str] = frozenset(
    {
        "cookie-consent",
        "cookie-banner",
        "SuiteNavWrapper",
        "ms-site-actions",
        "SuiteNavPlaceHolder",
        "O365_NavHeader",
        "s4-ribbonrow",
    }
)
_NOISE_ROLES: frozenset[str] = frozenset({"complementary"})
_HEADING_TAGS: frozenset[str] = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


def _remove_noise_tags(doc: HtmlElement, tags: frozenset[str]) -> None:
    """Remove all elements whose tag is in ``tags`` from ``doc`` in place."""
    for tag_name in tags:
        for element in list(doc.iter(tag_name)):
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)


def _remove_cookie_elements(doc: HtmlElement) -> None:
    """Remove elements identified as noise by class, ID, or ARIA role."""
    for element in list(doc.iter()):
        if not isinstance(element.tag, str):
            continue
        classes: set[str] = set((element.get("class") or "").split())
        if classes & _NOISE_CLASSES:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
            continue
        if (element.get("id") or "") in _NOISE_IDS:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
            continue
        if (element.get("role") or "") in _NOISE_ROLES:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)


def strip_noise(html_str: str) -> str:
    """Remove navigation, page chrome, scripts, styles, and cookie elements from HTML."""
    if not html_str or not html_str.strip():
        return ""
    document = lxml_html.document_fromstring(html_str)
    _remove_noise_tags(document, _NOISE_TAGS)
    _remove_cookie_elements(document)
    return lxml_html.tostring(document, encoding="unicode")


def _inner(element: HtmlElement) -> str:
    """Render an element's inner content without its own tag or tail text."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    parts.extend(_element_to_markdown(child) for child in element)  # type: ignore[arg-type]
    return "".join(parts)


def _table_to_markdown(table: HtmlElement) -> str:
    """Convert an HTML table to a GitHub-style Markdown table."""
    rows = table.findall(".//tr")
    if not rows:
        return ""
    lines: list[str] = []
    for index, row in enumerate(rows):
        cells = [cell for cell in row if isinstance(cell.tag, str) and cell.tag in ("th", "td")]
        cell_texts = [_inner(cell).strip() for cell in cells]  # type: ignore[arg-type]
        lines.append("| " + " | ".join(cell_texts) + " |")
        if index == 0:
            lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n" + "\n".join(lines) + "\n"


def _heading_to_markdown(element: HtmlElement, tail: str) -> str:
    """Convert a heading element to a Markdown heading line."""
    level = int(element.tag.lower()[1])
    return f"\n{'#' * level} {_inner(element).strip()}\n" + tail


def _paragraph_to_markdown(element: HtmlElement, tail: str) -> str:
    """Convert a paragraph element to a Markdown paragraph."""
    return f"\n{_inner(element).strip()}\n" + tail


def _unordered_list_to_markdown(element: HtmlElement, tail: str) -> str:
    """Convert an unordered list to Markdown bullet items."""
    items = [
        f"- {_inner(child).strip()}"  # type: ignore[arg-type]
        for child in element
        if isinstance(child.tag, str) and child.tag == "li"
    ]
    return "\n" + "\n".join(items) + "\n" + tail


def _ordered_list_to_markdown(element: HtmlElement, tail: str) -> str:
    """Convert an ordered list to Markdown numbered items."""
    list_items = [child for child in element if isinstance(child.tag, str) and child.tag == "li"]
    items = [f"{index}. {_inner(child).strip()}" for index, child in enumerate(list_items, 1)]  # type: ignore[arg-type]
    return "\n" + "\n".join(items) + "\n" + tail


def _link_to_markdown(element: HtmlElement, tail: str) -> str:
    """Convert a hyperlink to Markdown link syntax."""
    return f"[{_inner(element)}]({element.get('href', '')})" + tail


def _table_markdown_dispatch(element: HtmlElement, tail: str) -> str:
    """Dispatch table conversion while preserving following text."""
    return _table_to_markdown(element) + tail


_TAG_MARKDOWN_DISPATCH: dict[str, Callable[[HtmlElement, str], str]] = {
    **dict.fromkeys(_HEADING_TAGS, _heading_to_markdown),
    "p": _paragraph_to_markdown,
    "ul": _unordered_list_to_markdown,
    "ol": _ordered_list_to_markdown,
    "a": _link_to_markdown,
    "table": _table_markdown_dispatch,
}


def _element_to_markdown(element: HtmlElement) -> str:
    """Recursively convert an lxml HTML element to a Markdown snippet."""
    tag = element.tag
    if not isinstance(tag, str):
        return element.tail or ""  # type: ignore[union-attr]
    tag = tag.lower()
    tail = element.tail or ""
    if tag == "head":
        return ""
    handler = _TAG_MARKDOWN_DISPATCH.get(tag)
    if handler is not None:
        return handler(element, tail)
    return _inner(element) + tail


def html_to_markdown(html_str: str) -> str:
    """Convert HTML to Markdown while preserving headings, lists, tables, and links."""
    if not html_str or not html_str.strip():
        return ""
    root = lxml_html.fromstring(html_str)
    return _element_to_markdown(root).strip()  # type: ignore[arg-type]


def normalize(text: str) -> str:
    """Normalize whitespace and remove zero-width characters from Markdown."""
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    text = text.replace("\r", "").replace("\u00a0", " ")
    lines = [re.sub(r" {2,}", " ", line.rstrip()) for line in text.split("\n")]
    result: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and previous_blank:
            continue
        result.append(line)
        previous_blank = is_blank
    return "\n".join(result).strip()


def clean(html_str: str) -> str:
    """Strip noise, convert HTML to Markdown, and normalize the result."""
    if not html_str or not html_str.strip():
        return ""
    return normalize(html_to_markdown(strip_noise(html_str)))
