"""RED-phase tests for tasks #783/#788: owlbear_browser content extractor and HTML-to-MD cleaner.

Covers #783 original AC:
  AC1 - owlbear_browser.extractor: extract(html) returns markdown string with main content
  AC2 - owlbear_browser.cleaner: clean(html) preserves headings, lists, tables, and links
  AC3 - owlbear_browser.cleaner: noise elements stripped (nav, footer, script, style, cookie banners)

Covers #788 refined AC (binding — added by test-writer for #788):
  AC-788-1 - extract_content(html, url=None) -> str: trafilatura-powered with cleaner fallback
  AC-788-2 - strip_noise(html) -> str: noise removal returning cleaned HTML
  AC-788-3 - html_to_markdown(html) -> str: structure-preserving HTML-to-markdown
  AC-788-4 - serve/browser/pyproject.toml: trafilatura>=1.6 in project.dependencies
  AC-788-5 - owlbear_browser.__init__ exports extract_content

All tests MUST FAIL at RED phase — extractor.py and cleaner.py do not exist yet.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# AC1: owlbear_browser.extractor — content extraction from HTML
# ---------------------------------------------------------------------------


class TestFromAC_ContentExtractor:
    """owlbear_browser.extractor.extract() returns a markdown string from HTML (AC1)."""

    def test_extractor_module_importable(self) -> None:
        """owlbear_browser.extractor module is importable."""
        from owlbear_browser import extractor  # type: ignore[import-not-found]  # noqa: F401

    def test_extract_function_importable(self) -> None:
        """extract() function is importable from owlbear_browser.extractor."""
        from owlbear_browser.extractor import extract  # type: ignore[import-not-found]  # noqa: F401

    def test_extract_returns_string(self) -> None:
        """extract() returns a string when given valid HTML."""
        from owlbear_browser.extractor import extract  # type: ignore[import-not-found]

        html = "<html><body><article><p>Hello world</p></article></body></html>"
        result = extract(html)
        assert isinstance(result, str)

    def test_extract_returns_main_content_text(self) -> None:
        """extract() includes text from the page's primary content area."""
        from owlbear_browser.extractor import extract  # type: ignore[import-not-found]

        html = (
            "<html><body>"
            "<article><p>Main article text here.</p></article>"
            "</body></html>"
        )
        result = extract(html)
        assert "Main article text here" in result

    def test_extract_paragraph_text_preserved(self) -> None:
        """Text inside <p> tags appears in the extracted markdown output."""
        from owlbear_browser.extractor import extract  # type: ignore[import-not-found]

        html = "<html><body><p>Paragraph content</p></body></html>"
        result = extract(html)
        assert "Paragraph content" in result

    def test_extract_empty_html_returns_string(self) -> None:
        """extract('') returns a string without raising (empty content is valid input)."""
        from owlbear_browser.extractor import extract  # type: ignore[import-not-found]

        result = extract("")
        assert isinstance(result, str)

    def test_extract_noise_only_page_omits_nav_and_footer(self) -> None:
        """extract() on a page containing only nav/footer does not include those texts."""
        from owlbear_browser.extractor import extract  # type: ignore[import-not-found]

        html = (
            "<html><body>"
            "<nav>Nav link 1 | Nav link 2</nav>"
            "<footer>Footer boilerplate</footer>"
            "</body></html>"
        )
        result = extract(html)
        assert isinstance(result, str)
        assert "Nav link 1" not in result
        assert "Footer boilerplate" not in result

    def test_extract_non_string_raises_type_error(self) -> None:
        """extract(None) raises TypeError — only string inputs are valid."""
        from owlbear_browser.extractor import extract  # type: ignore[import-not-found]

        with pytest.raises(TypeError):
            extract(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC2: owlbear_browser.cleaner — HTML-to-markdown structure preservation
# ---------------------------------------------------------------------------


class TestFromAC_HTMLCleaner:
    """owlbear_browser.cleaner.clean() converts HTML to markdown preserving structure (AC2)."""

    def test_cleaner_module_importable(self) -> None:
        """owlbear_browser.cleaner module is importable."""
        from owlbear_browser import cleaner  # type: ignore[import-not-found]  # noqa: F401

    def test_clean_function_importable(self) -> None:
        """clean() function is importable from owlbear_browser.cleaner."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]  # noqa: F401

    def test_clean_preserves_h1_as_markdown_heading(self) -> None:
        """<h1> is converted to a level-1 markdown heading (# ...)."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<h1>Page Title</h1>"
        result = clean(html)
        assert "# Page Title" in result

    def test_clean_preserves_h2_as_markdown_heading(self) -> None:
        """<h2> is converted to a level-2 markdown heading (## ...)."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<h2>Section Title</h2>"
        result = clean(html)
        assert "## Section Title" in result

    def test_clean_preserves_unordered_list_items(self) -> None:
        """<ul><li> items are preserved as markdown bullet list items."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<ul><li>Alpha</li><li>Beta</li></ul>"
        result = clean(html)
        assert "Alpha" in result
        assert "Beta" in result
        assert re.search(r"[-*]\s+\w", result) is not None, (
            f"Expected bullet marker in result; got: {result!r}"
        )

    def test_clean_preserves_ordered_list_items(self) -> None:
        """<ol><li> items are preserved as markdown numbered list items."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<ol><li>First</li><li>Second</li></ol>"
        result = clean(html)
        assert "First" in result
        assert "Second" in result
        assert re.search(r"\d+\.", result) is not None, (
            f"Expected numbered list marker in result; got: {result!r}"
        )

    def test_clean_preserves_table_cell_content(self) -> None:
        """Table header and cell text is preserved in the markdown output."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = (
            "<table>"
            "<tr><th>Name</th><th>Value</th></tr>"
            "<tr><td>Alpha</td><td>1</td></tr>"
            "</table>"
        )
        result = clean(html)
        assert "Name" in result
        assert "Value" in result
        assert "Alpha" in result

    def test_clean_preserves_hyperlink_text_and_url(self) -> None:
        """<a href> links are preserved in markdown [text](url) format."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = '<a href="https://example.com">Example</a>'
        result = clean(html)
        assert "Example" in result
        assert "https://example.com" in result

    def test_clean_empty_html_returns_string(self) -> None:
        """clean('') returns a string without raising."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        result = clean("")
        assert isinstance(result, str)

    def test_clean_headings_nested_in_divs_preserved(self) -> None:
        """Headings inside <div> wrappers are still converted to markdown headings."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<div><div><h2>Nested Heading</h2></div></div>"
        result = clean(html)
        assert "Nested Heading" in result
        assert "##" in result


# ---------------------------------------------------------------------------
# AC3: owlbear_browser.cleaner — noise element removal
# ---------------------------------------------------------------------------


class TestFromAC_NoiseRemoval:
    """owlbear_browser.cleaner.clean() strips noise elements from HTML (AC3)."""

    def test_clean_strips_nav_content(self) -> None:
        """Text inside <nav> is absent from the cleaned markdown output."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<nav>Home | About | Contact</nav><p>Real content</p>"
        result = clean(html)
        assert "Home | About | Contact" not in result
        assert "Real content" in result

    def test_clean_strips_footer_content(self) -> None:
        """Text inside <footer> is absent from the cleaned markdown output."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<p>Main text</p><footer>\u00a9 2026 OwlBear</footer>"
        result = clean(html)
        assert "\u00a9 2026 OwlBear" not in result
        assert "Main text" in result

    def test_clean_strips_script_tags_and_content(self) -> None:
        """Content of <script> tags is absent from the cleaned markdown output."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<script>var x = 1; doTrack();</script><p>Body text</p>"
        result = clean(html)
        assert "doTrack" not in result
        assert "var x" not in result
        assert "Body text" in result

    def test_clean_strips_style_tags_and_content(self) -> None:
        """Content of <style> tags is absent from the cleaned markdown output."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = "<style>body { color: red; }</style><p>Styled text</p>"
        result = clean(html)
        assert "color: red" not in result
        assert "Styled text" in result

    def test_clean_strips_cookie_banner_by_class(self) -> None:
        """Element with class 'cookie-banner' is stripped from the output."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = (
            '<div class="cookie-banner">We use cookies. Accept?</div>'
            "<p>Article body</p>"
        )
        result = clean(html)
        assert "We use cookies" not in result
        assert "Article body" in result

    def test_clean_strips_cookie_consent_by_id(self) -> None:
        """Element with id 'cookie-consent' is stripped from the output."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = (
            '<div id="cookie-consent">Please accept cookies.</div>'
            "<p>Content here</p>"
        )
        result = clean(html)
        assert "Please accept cookies" not in result
        assert "Content here" in result

    def test_clean_strips_nav_but_preserves_surrounding_content(self) -> None:
        """Nav removed but paragraphs before and after it are preserved."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = (
            "<p>Before nav</p>"
            "<nav>Site navigation links</nav>"
            "<p>After nav</p>"
        )
        result = clean(html)
        assert "Site navigation links" not in result
        assert "Before nav" in result
        assert "After nav" in result

    def test_clean_strips_all_noise_types_simultaneously(self) -> None:
        """All noise types are stripped when combined on a single page."""
        from owlbear_browser.cleaner import clean  # type: ignore[import-not-found]

        html = (
            "<nav>Nav menu items</nav>"
            "<style>.body { margin: 0; }</style>"
            "<script>analyticsInit();</script>"
            '<div class="cookie-banner">Cookie notice text</div>'
            "<p>Actual article content</p>"
            "<footer>Site footer text</footer>"
        )
        result = clean(html)
        assert "Nav menu items" not in result
        assert "analyticsInit" not in result
        assert "Cookie notice text" not in result
        assert "Site footer text" not in result
        assert "Actual article content" in result


# ---------------------------------------------------------------------------
# #788 refined AC constants
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent
_BROWSER_PYPROJECT = _ROOT / "serve" / "browser" / "pyproject.toml"
_MIN_TRAFILATURA_VERSION = (1, 6)

_ARTICLE_HTML = """
<html>
<head><title>Test</title></head>
<body>
  <nav><a href="/">Home</a></nav>
  <main>
    <h1>Article Title</h1>
    <p>This is the main article content that trafilatura should extract.</p>
    <p>A second paragraph with meaningful text for content heuristics.</p>
  </main>
  <footer>Copyright 2026</footer>
</body>
</html>
"""


def _get_browser_deps() -> list[str]:
    """Parse serve/browser/pyproject.toml and return the project.dependencies list."""
    data = tomllib.loads(_BROWSER_PYPROJECT.read_text(encoding="utf-8"))
    return data["project"].get("dependencies", [])


def _find_dep(deps: list[str], name: str) -> str | None:
    """Return the first dep string matching name prefix, or None."""
    for dep in deps:
        if re.match(rf"^{re.escape(name)}", dep, re.IGNORECASE):
            return dep
    return None


# ---------------------------------------------------------------------------
# AC-788-4: serve/browser/pyproject.toml — trafilatura>=1.6
# ---------------------------------------------------------------------------


class TestFromAC_TrafilaturaDep:  # noqa: N801
    """serve/browser/pyproject.toml must declare trafilatura>=1.6."""

    def test_trafilatura_dep_present(self) -> None:
        """trafilatura must appear in serve/browser/pyproject.toml project.dependencies."""
        deps = _get_browser_deps()
        assert _find_dep(deps, "trafilatura") is not None, (
            f"'trafilatura' not found in serve/browser/pyproject.toml dependencies: {deps}"
        )

    def test_trafilatura_dep_uses_lower_bound_operator(self) -> None:
        """trafilatura dep must use >= or ~= operator, not a bare name."""
        deps = _get_browser_deps()
        dep = _find_dep(deps, "trafilatura")
        assert dep is not None, "trafilatura not found — cannot verify version operator"
        assert ">=" in dep or "~=" in dep, (
            f"trafilatura dep must use >= or ~= operator; got: {dep!r}"
        )

    def test_trafilatura_min_version_is_at_least_1_6(self) -> None:
        """trafilatura minimum version must be 1.6 or higher per AC."""
        deps = _get_browser_deps()
        dep = _find_dep(deps, "trafilatura")
        assert dep is not None, "trafilatura not found — cannot verify version"
        m = re.search(r"[>~]=\s*(\d+)\.(\d+)", dep)
        assert m is not None, (
            f"Could not parse '>=X.Y' or '~=X.Y' from trafilatura dep: {dep!r}"
        )
        major, minor = int(m.group(1)), int(m.group(2))
        assert (major, minor) >= _MIN_TRAFILATURA_VERSION, (
            f"trafilatura minimum must be >= {_MIN_TRAFILATURA_VERSION}; "
            f"got ({major}, {minor}) from: {dep!r}"
        )


# ---------------------------------------------------------------------------
# AC-788-5: owlbear_browser.__init__ exports extract_content
# ---------------------------------------------------------------------------


class TestFromAC_ExtractContentExport:  # noqa: N801
    """extract_content must be exported from owlbear_browser top-level package."""

    def test_extract_content_importable_from_package(self) -> None:
        """extract_content is accessible via `from owlbear_browser import extract_content`."""
        from owlbear_browser import extract_content  # type: ignore[attr-defined]  # noqa: F401

    def test_extract_content_in_package_all(self) -> None:
        """extract_content appears in owlbear_browser.__all__."""
        import owlbear_browser

        assert "extract_content" in owlbear_browser.__all__, (
            f"'extract_content' not in owlbear_browser.__all__: {owlbear_browser.__all__}"
        )


# ---------------------------------------------------------------------------
# AC-788-1: extractor.extract_content(html, url=None) -> str
# ---------------------------------------------------------------------------


class TestFromAC_ExtractContent:  # noqa: N801
    """owlbear_browser.extractor.extract_content(html, url=None) -> str contract tests."""

    # --- import / signature ---

    def test_extract_content_function_importable(self) -> None:
        """extract_content is importable from owlbear_browser.extractor."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]  # noqa: F401

    def test_extract_content_returns_str_for_article_html(self) -> None:
        """extract_content returns str for typical article HTML."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        result = extract_content(_ARTICLE_HTML)
        assert isinstance(result, str)

    def test_extract_content_main_content_preserved(self) -> None:
        """extract_content result contains the page's main textual content."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        result = extract_content(_ARTICLE_HTML)
        assert "Article Title" in result or "main article content" in result, (
            f"Main content not found in extraction result: {result!r}"
        )

    def test_extract_content_accepts_optional_url_kwarg(self) -> None:
        """extract_content accepts url keyword argument without raising."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        result = extract_content(_ARTICLE_HTML, url="https://example.com/article")
        assert isinstance(result, str)

    def test_extract_content_url_none_is_valid(self) -> None:
        """extract_content accepts url=None explicitly without raising."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        result = extract_content(_ARTICLE_HTML, url=None)
        assert isinstance(result, str)

    # --- empty / whitespace ---

    def test_extract_content_empty_string_returns_empty(self) -> None:
        """extract_content returns empty string for empty HTML input."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        assert extract_content("") == ""

    def test_extract_content_whitespace_only_returns_empty(self) -> None:
        """extract_content returns empty string for whitespace-only input."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        assert extract_content("   \n\t  ") == ""

    # --- fallback to cleaner ---

    def test_extract_content_falls_back_when_trafilatura_returns_none(self) -> None:
        """When trafilatura.extract returns None, extract_content uses cleaner fallback."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        html = "<div><p>Fallback paragraph text that should survive.</p></div>"
        with patch("owlbear_browser.extractor.trafilatura") as mock_traf:
            mock_traf.extract.return_value = None
            result = extract_content(html)
        assert isinstance(result, str)
        assert "Fallback paragraph text" in result, (
            f"Cleaner fallback content not found in result: {result!r}"
        )

    def test_extract_content_falls_back_when_trafilatura_returns_empty(self) -> None:
        """When trafilatura.extract returns '', extract_content uses cleaner fallback."""
        from owlbear_browser.extractor import extract_content  # type: ignore[import-not-found]

        html = "<div><p>Another fallback text to check.</p></div>"
        with patch("owlbear_browser.extractor.trafilatura") as mock_traf:
            mock_traf.extract.return_value = ""
            result = extract_content(html)
        assert isinstance(result, str)
        assert "Another fallback text" in result, (
            f"Cleaner fallback content not found in result: {result!r}"
        )


# ---------------------------------------------------------------------------
# AC-788-2: cleaner.strip_noise(html) -> str
# ---------------------------------------------------------------------------


class TestFromAC_StripNoise:  # noqa: N801
    """owlbear_browser.cleaner.strip_noise(html) -> str contract tests."""

    # --- import ---

    def test_strip_noise_function_importable(self) -> None:
        """strip_noise is importable from owlbear_browser.cleaner."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]  # noqa: F401

    # --- noise elements removed ---

    def test_strip_noise_removes_nav(self) -> None:
        """strip_noise strips <nav> elements from HTML."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        html = "<html><body><nav><a>Menu</a></nav><p>Content</p></body></html>"
        result = strip_noise(html)
        assert "<nav" not in result, f"<nav> still present after strip_noise: {result!r}"

    def test_strip_noise_removes_footer(self) -> None:
        """strip_noise strips <footer> elements from HTML."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        html = "<html><body><p>Content</p><footer>Copyright 2026</footer></body></html>"
        result = strip_noise(html)
        assert "<footer" not in result, f"<footer> still present after strip_noise: {result!r}"

    def test_strip_noise_removes_script(self) -> None:
        """strip_noise strips <script> elements from HTML."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        html = "<html><body><script>alert('xss')</script><p>Content</p></body></html>"
        result = strip_noise(html)
        assert "<script" not in result, f"<script> still present after strip_noise: {result!r}"

    def test_strip_noise_removes_style(self) -> None:
        """strip_noise strips <style> elements from HTML."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        html = "<html><head><style>body{color:red}</style></head><body><p>Content</p></body></html>"
        result = strip_noise(html)
        assert "<style" not in result, f"<style> still present after strip_noise: {result!r}"

    def test_strip_noise_removes_cookie_banner_by_id(self) -> None:
        """strip_noise strips element with id='cookie-consent'."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        html = (
            "<html><body>"
            "<div id='cookie-consent'>Accept cookies</div>"
            "<p>Main content here</p>"
            "</body></html>"
        )
        result = strip_noise(html)
        assert "Accept cookies" not in result, (
            f"Cookie banner content still present after strip_noise: {result!r}"
        )

    def test_strip_noise_preserves_content_outside_noise(self) -> None:
        """strip_noise preserves main body content after removing noise elements."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        html = (
            "<html><body>"
            "<nav><a>Nav</a></nav>"
            "<main><p>Keep this content</p></main>"
            "<footer>Remove this</footer>"
            "</body></html>"
        )
        result = strip_noise(html)
        assert "Keep this content" in result, (
            f"Main content missing from stripped output: {result!r}"
        )

    def test_strip_noise_returns_str(self) -> None:
        """strip_noise returns a str."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        assert isinstance(strip_noise("<p>hello</p>"), str)

    # --- empty / whitespace ---

    def test_strip_noise_empty_string_returns_empty(self) -> None:
        """strip_noise returns empty string for empty input."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        assert strip_noise("") == ""

    def test_strip_noise_whitespace_only_returns_empty(self) -> None:
        """strip_noise returns empty string for whitespace-only input."""
        from owlbear_browser.cleaner import strip_noise  # type: ignore[import-not-found]

        assert strip_noise("   \n\t  ") == ""


# ---------------------------------------------------------------------------
# AC-788-3: cleaner.html_to_markdown(html) -> str
# ---------------------------------------------------------------------------


class TestFromAC_HtmlToMarkdown:  # noqa: N801
    """owlbear_browser.cleaner.html_to_markdown(html) -> str contract tests."""

    # --- import ---

    def test_html_to_markdown_function_importable(self) -> None:
        """html_to_markdown is importable from owlbear_browser.cleaner."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]  # noqa: F401

    # --- structure preservation ---

    def test_html_to_markdown_preserves_h1(self) -> None:
        """html_to_markdown converts <h1> to a level-1 markdown heading."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        result = html_to_markdown("<h1>Top Heading</h1>")
        assert "# " in result, f"<h1> not converted to # heading: {result!r}"
        assert "Top Heading" in result

    def test_html_to_markdown_preserves_h2(self) -> None:
        """html_to_markdown converts <h2> to a level-2 markdown heading."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        result = html_to_markdown("<h2>Sub Heading</h2>")
        assert "## " in result, f"<h2> not converted to ## heading: {result!r}"
        assert "Sub Heading" in result

    def test_html_to_markdown_preserves_h3(self) -> None:
        """html_to_markdown converts <h3> to a level-3 markdown heading."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        result = html_to_markdown("<h3>Sub-sub Heading</h3>")
        assert "### " in result, f"<h3> not converted to ### heading: {result!r}"
        assert "Sub-sub Heading" in result

    def test_html_to_markdown_preserves_unordered_list(self) -> None:
        """html_to_markdown converts <ul>/<li> to markdown bullet items."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        html = "<ul><li>Alpha</li><li>Beta</li></ul>"
        result = html_to_markdown(html)
        assert "Alpha" in result
        assert "Beta" in result
        assert any(marker in result for marker in ("- ", "* ", "+ ")), (
            f"No markdown bullet markers found in result: {result!r}"
        )

    def test_html_to_markdown_preserves_ordered_list(self) -> None:
        """html_to_markdown converts <ol>/<li> to numbered markdown list items."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        html = "<ol><li>First</li><li>Second</li></ol>"
        result = html_to_markdown(html)
        assert "First" in result
        assert "Second" in result
        assert re.search(r"\d+[.)]\s", result), (
            f"No numbered list markers found in result: {result!r}"
        )

    def test_html_to_markdown_preserves_links(self) -> None:
        """html_to_markdown converts <a href> to markdown [text](url) syntax."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        html = '<a href="https://example.com">Click here</a>'
        result = html_to_markdown(html)
        assert "Click here" in result
        assert "https://example.com" in result, (
            f"Link URL not preserved in markdown output: {result!r}"
        )

    def test_html_to_markdown_preserves_table_structure(self) -> None:
        """html_to_markdown converts <table> to a markdown table with pipe separators."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        html = (
            "<table>"
            "<tr><th>Name</th><th>Value</th></tr>"
            "<tr><td>Row1</td><td>Data1</td></tr>"
            "</table>"
        )
        result = html_to_markdown(html)
        assert "Name" in result
        assert "Value" in result
        assert "Row1" in result
        assert "|" in result, f"Markdown table pipe not found in result: {result!r}"

    def test_html_to_markdown_returns_str(self) -> None:
        """html_to_markdown returns a str."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        assert isinstance(html_to_markdown("<p>hello</p>"), str)

    # --- empty / whitespace ---

    def test_html_to_markdown_empty_string_returns_empty(self) -> None:
        """html_to_markdown returns empty string for empty input."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        assert html_to_markdown("") == ""

    def test_html_to_markdown_whitespace_only_returns_empty(self) -> None:
        """html_to_markdown returns empty string for whitespace-only input."""
        from owlbear_browser.cleaner import html_to_markdown  # type: ignore[import-not-found]

        assert html_to_markdown("   \n\t  ") == ""
