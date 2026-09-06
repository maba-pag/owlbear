"""HTML noise stripping and Markdown conversion for web content."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin

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
_NOISE_ROLES: frozenset[str] = frozenset({"complementary", "contentinfo", "navigation"})
_HEADING_TAGS: frozenset[str] = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_LIST_TAGS: frozenset[str] = frozenset({"ol", "ul"})
_HIDDEN_STYLE_RE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)(?:\s*!important)?\s*(?:;|$)",
    re.IGNORECASE,
)
_LANGUAGE_CLASS_RE = re.compile(r"(?:^|\s)(?:language|lang)-([A-Za-z0-9_.+-]+)(?:\s|$)")
_FENCE_RE = re.compile(r"^(?P<indent>[ ]*)(?P<marker>`{3,}|~{3,})(?P<rest>.*)$")
_CODE_SPAN_RE = re.compile(r"(?P<delimiter>`+).*?(?P=delimiter)")


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
        if (element.get("role") or "").strip().lower() in _NOISE_ROLES:
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)


def _is_hidden(element: HtmlElement) -> bool:
    """Return whether an element has an explicit presentation-only hidden state."""
    if "hidden" in element.attrib:
        return True
    if (element.get("aria-hidden") or "").strip().lower() == "true":
        return True
    return bool(_HIDDEN_STYLE_RE.search(element.get("style") or ""))


def _remove_hidden_elements(doc: HtmlElement) -> None:
    """Remove explicitly hidden elements without attempting to evaluate external CSS."""
    for element in list(doc.iter()):
        if not isinstance(element.tag, str) or not _is_hidden(element):
            continue
        parent = element.getparent()
        if parent is not None:
            element.drop_tree()


def strip_noise(html_str: str) -> str:
    """Remove page chrome and explicit presentation-only content from HTML.

    ``hidden``, ``aria-hidden="true"``, and inline ``display: none`` /
    ``visibility: hidden`` are treated as presentation. Class names backed by an
    external stylesheet are intentionally not evaluated by this HTML-only package.
    """
    if not html_str or not html_str.strip():
        return ""
    document = lxml_html.document_fromstring(html_str)
    _remove_noise_tags(document, _NOISE_TAGS)
    _remove_cookie_elements(document)
    _remove_hidden_elements(document)
    return lxml_html.tostring(document, encoding="unicode")


def _resolve_url(value: str, url: str | None) -> str:
    """Resolve a document-relative URL when the source URL is available."""
    if not value or url is None:
        return value
    return urljoin(url, value)


def _inner(element: HtmlElement, url: str | None = None) -> str:
    """Render an element's inner content without its own tag or tail text."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    parts.extend(_element_to_markdown(child, url) for child in element)  # type: ignore[arg-type]
    return "".join(parts)


def _table_cell_text(cell: HtmlElement, url: str | None) -> str:
    """Render one table cell as a single Markdown-table-safe value."""
    text = _inner(cell, url).strip()
    text = re.sub(r"\s*\n\s*", "<br>", text)
    return text.replace("|", r"\|")


def _table_to_markdown(table: HtmlElement, url: str | None = None) -> str:
    """Convert an HTML table to a GitHub-style Markdown table.

    Markdown has no row-span or column-span syntax. Spanning cells are therefore
    flattened in source order and short rows are padded so their text remains
    searchable without inventing duplicate values.
    """
    rows = [
        [cell for cell in row if isinstance(cell.tag, str) and cell.tag in ("th", "td")]
        for row in table.findall(".//tr")
    ]
    rows = [row for row in rows if row]
    if not rows:
        return ""
    column_count = max(len(row) for row in rows)
    lines: list[str] = []
    for index, row in enumerate(rows):
        cell_texts = [_table_cell_text(cell, url) for cell in row]
        cell_texts.extend([""] * (column_count - len(cell_texts)))
        lines.append("| " + " | ".join(cell_texts) + " |")
        if index == 0:
            lines.append("| " + " | ".join(["---"] * column_count) + " |")
    return "\n" + "\n".join(lines) + "\n"


def _heading_to_markdown(element: HtmlElement, tail: str, url: str | None = None) -> str:
    """Convert a heading element to a Markdown heading line."""
    level = int(element.tag.lower()[1])
    return f"\n{'#' * level} {_inner(element, url).strip()}\n" + tail


def _paragraph_to_markdown(element: HtmlElement, tail: str, url: str | None = None) -> str:
    """Convert a paragraph element to a Markdown paragraph."""
    return f"\n{_inner(element, url).strip()}\n" + tail


def _list_item_to_markdown(element: HtmlElement, url: str | None) -> str:
    """Render an item's non-list children while leaving nested lists separate."""
    parts: list[str] = [element.text or ""]
    for child in element:
        if isinstance(child.tag, str) and child.tag.lower() in _LIST_TAGS:
            parts.append(child.tail or "")
        else:
            parts.append(_element_to_markdown(child, url))  # type: ignore[arg-type]
    return "".join(parts).strip()


def _list_lines(element: HtmlElement, url: str | None, indent: str = "") -> list[str]:
    """Render nested ordered and unordered lists with valid marker-width indents."""
    ordered = element.tag.lower() == "ol"
    lines: list[str] = []
    item_number = 1
    for child in element:
        if not isinstance(child.tag, str) or child.tag.lower() != "li":
            continue
        marker = f"{item_number}. " if ordered else "- "
        content = _list_item_to_markdown(child, url)
        lines.append(f"{indent}{marker}{content}".rstrip())
        for nested in child:
            if isinstance(nested.tag, str) and nested.tag.lower() in _LIST_TAGS:
                lines.extend(_list_lines(nested, url, indent + " " * len(marker)))
        item_number += 1
    return lines


def _list_to_markdown(element: HtmlElement, tail: str, url: str | None = None) -> str:
    """Convert an ordered or unordered list, retaining nested-list structure."""
    return "\n" + "\n".join(_list_lines(element, url)) + "\n" + tail


def _link_to_markdown(element: HtmlElement, tail: str, url: str | None = None) -> str:
    """Convert a hyperlink to Markdown link syntax."""
    href = _resolve_url(element.get("href", ""), url)
    return f"[{_inner(element, url)}]({href})" + tail


def _image_to_markdown(element: HtmlElement, tail: str, url: str | None = None) -> str:
    """Preserve non-decorative image alternatives as searchable Markdown."""
    alt = (element.get("alt") or "").strip()
    if not alt:
        return tail
    src = _resolve_url(element.get("src", ""), url)
    if not src:
        return f"[Image: {alt}]" + tail
    return f"![{alt}]({src})" + tail


def _inline_code_to_markdown(element: HtmlElement, tail: str, _url: str | None = None) -> str:
    """Convert inline code while selecting a delimiter that cannot close early."""
    text = "".join(element.itertext())
    longest_backtick_run = max((len(run) for run in re.findall(r"`+", text)), default=0)
    delimiter = "`" * max(1, longest_backtick_run + 1)
    has_boundary_spaces = bool(text.strip()) and text.startswith(" ") and text.endswith(" ")
    padding = " " if text.startswith("`") or text.endswith("`") or has_boundary_spaces else ""
    return f"{delimiter}{padding}{text}{padding}{delimiter}" + tail


def _code_language(element: HtmlElement) -> str:
    """Return a language hint from a code element's conventional class name."""
    for code in element.iter("code"):
        match = _LANGUAGE_CLASS_RE.search(code.get("class") or "")
        if match:
            return match.group(1)
    return ""


def _code_block_to_markdown(element: HtmlElement, tail: str, _url: str | None = None) -> str:
    """Convert a preformatted block to a fenced Markdown code block."""
    text = "".join(element.itertext()).strip("\n")
    longest_backtick_run = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest_backtick_run + 1)
    return f"\n{fence}{_code_language(element)}\n{text}\n{fence}\n" + tail


def _break_to_markdown(_element: HtmlElement, tail: str, _url: str | None = None) -> str:
    """Preserve an explicit HTML line break inside Markdown text."""
    return "<br>" + tail


def _table_markdown_dispatch(element: HtmlElement, tail: str, url: str | None = None) -> str:
    """Dispatch table conversion while preserving following text."""
    return _table_to_markdown(element, url) + tail


_TAG_MARKDOWN_DISPATCH: dict[str, Callable[[HtmlElement, str, str | None], str]] = {
    **dict.fromkeys(_HEADING_TAGS, _heading_to_markdown),
    "p": _paragraph_to_markdown,
    "ul": _list_to_markdown,
    "ol": _list_to_markdown,
    "a": _link_to_markdown,
    "img": _image_to_markdown,
    "code": _inline_code_to_markdown,
    "pre": _code_block_to_markdown,
    "br": _break_to_markdown,
    "table": _table_markdown_dispatch,
}


def _element_to_markdown(element: HtmlElement, url: str | None = None) -> str:
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
        return handler(element, tail, url)
    return _inner(element, url) + tail


def html_to_markdown(html_str: str, url: str | None = None) -> str:
    """Convert HTML to Markdown while preserving document structure and URLs."""
    if not html_str or not html_str.strip():
        return ""
    root = lxml_html.fromstring(html_str)
    return _element_to_markdown(root, url).strip()  # type: ignore[arg-type]


def _collapse_spaces_outside_code_spans(text: str) -> str:
    """Collapse repeated spaces without changing inline code delimiters or content."""
    parts: list[str] = []
    previous_end = 0
    for match in _CODE_SPAN_RE.finditer(text):
        parts.append(re.sub(r" {2,}", " ", text[previous_end : match.start()]))
        parts.append(match.group())
        previous_end = match.end()
    parts.append(re.sub(r" {2,}", " ", text[previous_end:]))
    return "".join(parts)


def normalize(text: str) -> str:
    """Normalize Markdown whitespace without changing fenced code contents."""
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    text = text.replace("\r", "")
    lines = text.split("\n")
    result: list[str] = []
    previous_blank = False
    fence_character: str | None = None
    fence_length = 0
    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_character is not None:
            result.append(line)
            if (
                fence_match
                and fence_match.group("marker")[0] == fence_character
                and len(fence_match.group("marker")) >= fence_length
                and not fence_match.group("rest").strip()
            ):
                fence_character = None
                fence_length = 0
            continue
        if fence_match:
            result.append(line.rstrip())
            marker = fence_match.group("marker")
            fence_character = marker[0]
            fence_length = len(marker)
            previous_blank = False
            continue
        normalized_line = line.replace("\u00a0", " ")
        leading_spaces = re.match(r"^ *", normalized_line).group()
        content = _collapse_spaces_outside_code_spans(normalized_line[len(leading_spaces) :].rstrip())
        normalized_line = leading_spaces + content if content else ""
        is_blank = normalized_line == ""
        if is_blank and previous_blank:
            continue
        result.append(normalized_line)
        previous_blank = is_blank
    return "\n".join(result).strip()


def clean(html_str: str) -> str:
    """Strip noise, convert HTML to Markdown, and normalize the result."""
    if not html_str or not html_str.strip():
        return ""
    return normalize(html_to_markdown(strip_noise(html_str)))
