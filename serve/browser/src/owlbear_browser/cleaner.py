"""HTML noise stripper and markdown converter for owlbear_browser.

Provides three public functions:
  - strip_noise(html)      → HTML string with nav, header, footer, aside, script, style,
                             cookie banners, and SharePoint boilerplate removed
  - html_to_markdown(html) → Markdown string preserving headings, lists, tables, links
  - clean(html)            → strip_noise + html_to_markdown + whitespace normalization
"""

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
        # Cookie notices
        "cookie-banner",
        "cookie-notice",
        "cookie-popup",
        "cookie-bar",
        # SharePoint boilerplate
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
        # Cookie consent
        "cookie-consent",
        "cookie-banner",
        # SharePoint boilerplate
        "SuiteNavWrapper",
        "ms-site-actions",
        "SuiteNavPlaceHolder",
        "O365_NavHeader",
        "s4-ribbonrow",
    }
)
_NOISE_ROLES: frozenset[str] = frozenset({"complementary"})
_HEADING_TAGS: frozenset[str] = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


# ---------------------------------------------------------------------------
# Noise removal
# ---------------------------------------------------------------------------


def _remove_noise_tags(doc: HtmlElement, tags: frozenset[str]) -> None:
    """Remove all elements whose tag is in *tags* from *doc* in-place."""
    for tag_name in tags:
        for el in list(doc.iter(tag_name)):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)


def _remove_cookie_elements(doc: HtmlElement) -> None:
    """Remove elements identified as noise by class, id, or ARIA role."""
    for el in list(doc.iter()):
        if not isinstance(el.tag, str):
            continue
        classes: set[str] = set((el.get("class") or "").split())
        if classes & _NOISE_CLASSES:
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
            continue
        if (el.get("id") or "") in _NOISE_IDS:
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
            continue
        if (el.get("role") or "") in _NOISE_ROLES:
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)


def strip_noise(html_str: str) -> str:
    """Remove noise elements from HTML, returning a cleaned HTML string.

    Noise elements: nav, header, footer, aside, script, style tags; cookie-banner/consent
    divs; and SharePoint boilerplate (breadcrumbs, web-part chrome, timestamp fields,
    user avatar containers identified by ms-* Fluent UI classes and SharePoint IDs).
    """
    if not html_str or not html_str.strip():
        return ""
    doc = lxml_html.document_fromstring(html_str)
    _remove_noise_tags(doc, _NOISE_TAGS)
    _remove_cookie_elements(doc)
    return lxml_html.tostring(doc, encoding="unicode")


# ---------------------------------------------------------------------------
# HTML → Markdown conversion helpers
# ---------------------------------------------------------------------------


def _inner(el: HtmlElement) -> str:
    """Render the inner content of an element (without its own tag or tail text)."""
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    parts.extend(_elem_to_md(c) for c in el)  # type: ignore[arg-type]
    return "".join(parts)


def _table_to_md(table: HtmlElement) -> str:
    """Convert an lxml table element to a GitHub-style markdown table."""
    rows = table.findall(".//tr")
    if not rows:
        return ""
    lines: list[str] = []
    for i, row in enumerate(rows):
        cells = [c for c in row if isinstance(c.tag, str) and c.tag in ("th", "td")]
        cell_texts = [_inner(c).strip() for c in cells]  # type: ignore[arg-type]
        lines.append("| " + " | ".join(cell_texts) + " |")
        if i == 0:
            lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n" + "\n".join(lines) + "\n"


def _heading_md(el: HtmlElement, tail: str) -> str:
    """Convert a heading element to a markdown heading line."""
    level = int(el.tag.lower()[1])
    return f"\n{'#' * level} {_inner(el).strip()}\n" + tail


def _p_md(el: HtmlElement, tail: str) -> str:
    """Convert a paragraph element to a markdown paragraph."""
    return f"\n{_inner(el).strip()}\n" + tail


def _ul_md(el: HtmlElement, tail: str) -> str:
    """Convert an unordered list element to markdown bullet list items."""
    items = [
        f"- {_inner(c).strip()}"  # type: ignore[arg-type]
        for c in el
        if isinstance(c.tag, str) and c.tag == "li"
    ]
    return "\n" + "\n".join(items) + "\n" + tail


def _ol_md(el: HtmlElement, tail: str) -> str:
    """Convert an ordered list element to markdown numbered list items."""
    lis = [c for c in el if isinstance(c.tag, str) and c.tag == "li"]
    items = [f"{i}. {_inner(c).strip()}" for i, c in enumerate(lis, 1)]  # type: ignore[arg-type]
    return "\n" + "\n".join(items) + "\n" + tail


def _a_md(el: HtmlElement, tail: str) -> str:
    """Convert a hyperlink element to markdown [text](url) syntax."""
    return f"[{_inner(el)}]({el.get('href', '')})" + tail


def _table_md_dispatch(el: HtmlElement, tail: str) -> str:
    """Dispatch entry-point for table-to-markdown conversion."""
    return _table_to_md(el) + tail


_TAG_MD_DISPATCH: dict[str, Callable[[HtmlElement, str], str]] = {
    **dict.fromkeys(_HEADING_TAGS, _heading_md),
    "p": _p_md,
    "ul": _ul_md,
    "ol": _ol_md,
    "a": _a_md,
    "table": _table_md_dispatch,
}


def _elem_to_md(el: HtmlElement) -> str:
    """Recursively convert an lxml HTML element to a markdown snippet."""
    tag = el.tag
    if not isinstance(tag, str):
        return el.tail or ""  # type: ignore[union-attr]
    tag = tag.lower()
    tail: str = el.tail or ""
    if tag == "head":
        return ""
    handler = _TAG_MD_DISPATCH.get(tag)
    if handler is not None:
        return handler(el, tail)
    return _inner(el) + tail  # transparent / unknown tags


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def html_to_markdown(html_str: str) -> str:
    """Convert an HTML string to markdown, preserving headings, lists, tables, and links."""
    if not html_str or not html_str.strip():
        return ""
    root = lxml_html.fromstring(html_str)
    return _elem_to_md(root).strip()  # type: ignore[arg-type]


def _normalize_content(text: str) -> str:
    """Normalize whitespace in the markdown output.

    - Removes zero-width Unicode characters (U+200B, U+200C, U+200D, U+FEFF).
    - Removes carriage returns (U+000D).
    - Converts non-breaking spaces (U+00A0) to regular spaces.
    - Collapses multiple consecutive spaces within a line to a single space.
    - Collapses more than one consecutive blank line to a single blank line.
    """
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    text = text.replace("\r", "")
    text = text.replace("\u00a0", " ")
    lines = [re.sub(r" {2,}", " ", line.rstrip()) for line in text.split("\n")]
    result: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank
    return "\n".join(result).strip()


def clean(html_str: str) -> str:
    """Strip noise from HTML then convert the remaining content to normalized markdown."""
    if not html_str or not html_str.strip():
        return ""
    return _normalize_content(html_to_markdown(strip_noise(html_str)))
