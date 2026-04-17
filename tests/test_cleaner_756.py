"""RED-phase tests for HTML→markdown cleaner (#756).

Covers:
  AC1 - strip_noise()/clean() strips header and aside/sidebar elements
  AC2 - clean() removes SharePoint-specific dynamic boilerplate
  AC3 - clean() normalizes whitespace (multiple spaces collapsed, &nbsp; converted)
  AC4 - clean() output is idempotent — same input → identical output for stable hashing

All TestFromAC_* tests MUST FAIL at RED phase:
  - <header> and <aside> are not yet in _NOISE_TAGS
  - No SharePoint boilerplate class/id rules exist in cleaner.py
  - No whitespace normalization is applied in clean() or html_to_markdown()
"""

from __future__ import annotations

import hashlib


# ---------------------------------------------------------------------------
# AC1: strip_noise()/clean() strips header and sidebar (aside) elements
# ---------------------------------------------------------------------------


class TestFromAC_HeaderSidebarStripping:
    """AC1: clean() and strip_noise() remove <header> and <aside>/sidebar elements."""

    def test_clean_strips_header_element(self) -> None:
        """Text inside <header> is absent from the cleaned markdown output."""
        from owlbear_browser.cleaner import clean

        html = "<header>Site Header Login Nav</header><p>Main content</p>"
        result = clean(html)
        assert "Site Header Login Nav" not in result
        assert "Main content" in result

    def test_clean_strips_aside_element(self) -> None:
        """Text inside <aside> is absent from the cleaned markdown output."""
        from owlbear_browser.cleaner import clean

        html = "<p>Main content</p><aside>Sidebar related links</aside>"
        result = clean(html)
        assert "Sidebar related links" not in result
        assert "Main content" in result

    def test_clean_strips_aria_complementary_div(self) -> None:
        """Element with role='complementary' (ARIA sidebar pattern) is stripped."""
        from owlbear_browser.cleaner import clean

        html = '<div role="complementary">Related articles sidebar</div><p>Body text</p>'
        result = clean(html)
        assert "Related articles sidebar" not in result
        assert "Body text" in result

    def test_strip_noise_removes_header_element(self) -> None:
        """strip_noise() removes <header> from the HTML output."""
        from owlbear_browser.cleaner import strip_noise

        html = "<header>Page header text</header><p>Content</p>"
        result = strip_noise(html)
        assert "Page header text" not in result

    def test_strip_noise_removes_aside_element(self) -> None:
        """strip_noise() removes <aside> from the HTML output."""
        from owlbear_browser.cleaner import strip_noise

        html = "<aside>Aside sidebar text</aside><p>Main</p>"
        result = strip_noise(html)
        assert "Aside sidebar text" not in result

    def test_clean_preserves_main_content_with_header_stripped(self) -> None:
        """Headings and paragraphs in main body are preserved when header is removed."""
        from owlbear_browser.cleaner import clean

        html = """<html><body>
            <header>Company Logo | Nav | Login</header>
            <h1>Document Title</h1>
            <p>Document body text is preserved.</p>
            <aside>See also: related links</aside>
        </body></html>"""
        result = clean(html)
        assert "Company Logo" not in result
        assert "See also" not in result
        assert "Document Title" in result
        assert "Document body text is preserved" in result


# ---------------------------------------------------------------------------
# AC2: clean() removes SharePoint-specific dynamic boilerplate
# ---------------------------------------------------------------------------


class TestFromAC_SharePointBoilerplate:
    """AC2: SharePoint-specific boilerplate elements are stripped from clean() output."""

    def test_clean_strips_suite_nav_wrapper_by_id(self) -> None:
        """Element with id='SuiteNavWrapper' (MS365 suite nav) is stripped."""
        from owlbear_browser.cleaner import clean

        html = '<div id="SuiteNavWrapper">Microsoft 365 Suite Navigation</div><p>Doc content</p>'
        result = clean(html)
        assert "Microsoft 365 Suite Navigation" not in result
        assert "Doc content" in result

    def test_clean_strips_ms_command_bar_by_class(self) -> None:
        """Element with class='ms-commandBar' (SharePoint toolbar) is stripped."""
        from owlbear_browser.cleaner import clean

        html = '<div class="ms-commandBar">New | Edit | Share | Follow</div><p>Page text</p>'
        result = clean(html)
        assert "New | Edit | Share | Follow" not in result
        assert "Page text" in result

    def test_clean_strips_ms_header_class(self) -> None:
        """Element with class='ms-header' (SharePoint site header) is stripped."""
        from owlbear_browser.cleaner import clean

        html = '<div class="ms-header">SharePoint Header Navigation Area</div><p>Document body</p>'
        result = clean(html)
        assert "SharePoint Header Navigation Area" not in result
        assert "Document body" in result

    def test_clean_strips_ms_page_edit_bar_class(self) -> None:
        """Element with class='ms-pageEditBar' (SharePoint edit bar) is stripped."""
        from owlbear_browser.cleaner import clean

        html = '<div class="ms-pageEditBar">Modified by: User — Last modified: 2026</div><p>Policy text</p>'
        result = clean(html)
        assert "Modified by: User" not in result
        assert "Policy text" in result

    def test_clean_preserves_document_content_amid_sharepoint_noise(self) -> None:
        """All SharePoint boilerplate stripped while policy document body is preserved."""
        from owlbear_browser.cleaner import clean

        html = """
            <div id="SuiteNavWrapper">MS365 Nav</div>
            <div class="ms-commandBar">SharePoint Actions Bar</div>
            <div class="ms-header">SP Site Header</div>
            <h1>Security Policy v3.1</h1>
            <p>This corporate security policy applies to all employees.</p>
            <div class="ms-pageEditBar">Last reviewed by Admin</div>
        """
        result = clean(html)
        assert "MS365 Nav" not in result
        assert "SharePoint Actions Bar" not in result
        assert "SP Site Header" not in result
        assert "Last reviewed by Admin" not in result
        assert "Security Policy" in result
        assert "corporate security policy" in result


# ---------------------------------------------------------------------------
# AC3: clean() normalizes whitespace and encoding artifacts
# ---------------------------------------------------------------------------


class TestFromAC_ContentNormalization:
    """AC3: clean() normalizes whitespace and converts &nbsp; to regular spaces."""

    def test_clean_collapses_multiple_spaces_in_paragraph(self) -> None:
        """Multiple consecutive spaces inside a paragraph are collapsed to a single space."""
        from owlbear_browser.cleaner import clean

        html = "<p>word1  word2   word3</p>"
        result = clean(html)
        assert "  " not in result, f"Expected no double spaces; got: {result!r}"
        assert "word1 word2 word3" in result

    def test_clean_normalizes_non_breaking_space_to_regular_space(self) -> None:
        """Non-breaking space (U+00A0 / &nbsp;) is converted to a regular space."""
        from owlbear_browser.cleaner import clean

        html = "<p>Hello\u00a0World</p>"
        result = clean(html)
        assert "\u00a0" not in result, f"Expected \\u00a0 absent; got: {result!r}"
        assert "Hello World" in result

    def test_clean_collapses_multiple_consecutive_blank_lines(self) -> None:
        """Three or more consecutive blank lines are reduced to at most one blank line."""
        from owlbear_browser.cleaner import clean

        html = "<p>First paragraph</p><p>Second paragraph</p><p>Third paragraph</p>"
        result = clean(html)
        assert "\n\n\n" not in result, f"Expected at most one consecutive blank line; got: {result!r}"

    def test_clean_semantically_equivalent_html_produces_same_output(self) -> None:
        """Same semantic content with different HTML whitespace → identical clean() output."""
        from owlbear_browser.cleaner import clean

        html_compact = "<p>Hello World</p>"
        html_spaced = "<p>Hello   World</p>"
        assert clean(html_compact) == clean(html_spaced), (
            f"Expected identical output; got:\n  compact: {clean(html_compact)!r}\n  spaced:  {clean(html_spaced)!r}"
        )

    def test_clean_multiple_nbsp_in_single_element(self) -> None:
        """Multiple &nbsp; within an element are each converted to a regular space."""
        from owlbear_browser.cleaner import clean

        html = "<p>A\u00a0B\u00a0C</p>"
        result = clean(html)
        assert "\u00a0" not in result
        assert "A B C" in result


# ---------------------------------------------------------------------------
# AC4: clean() produces stable, idempotent output for content hashing
# ---------------------------------------------------------------------------


class TestFromAC_IdempotentOutput:
    """AC4: clean() output is identical across calls — suitable for stable content hashing."""

    def test_clean_produces_identical_output_on_repeat_calls(self) -> None:
        """Two calls to clean() with the same HTML return exactly the same string."""
        from owlbear_browser.cleaner import clean

        html = "<html><body><h1>Title</h1><p>Body content.</p></body></html>"
        assert clean(html) == clean(html)

    def test_clean_output_hash_is_stable_across_calls(self) -> None:
        """SHA-256 hash of clean() output is identical on every call."""
        from owlbear_browser.cleaner import clean

        html = "<html><body><h2>Docs</h2><p>Full text content here.</p></body></html>"
        h1 = hashlib.sha256(clean(html).encode()).hexdigest()
        h2 = hashlib.sha256(clean(html).encode()).hexdigest()
        assert h1 == h2

    def test_clean_whitespace_normalization_produces_equal_hashes(self) -> None:
        """Semantic whitespace variants hash identically after normalization."""
        from owlbear_browser.cleaner import clean

        html_a = "<p>Same  content  here</p>"
        html_b = "<p>Same content here</p>"
        h_a = hashlib.sha256(clean(html_a).encode()).hexdigest()
        h_b = hashlib.sha256(clean(html_b).encode()).hexdigest()
        assert h_a == h_b, (
            f"Expected equal hashes for semantically equivalent content;\n"
            f"  html_a → {clean(html_a)!r}\n"
            f"  html_b → {clean(html_b)!r}"
        )


# ---------------------------------------------------------------------------
# AC1 (gap): html_to_markdown() conversion — headings, links, lists, tables
# covered by the public API contract  (requested by review #759)
# ---------------------------------------------------------------------------


class TestFromAC_MarkdownConversion:
    """AC1: html_to_markdown() converts headings, links, lists, and tables to markdown."""

    # --- headings -----------------------------------------------------------

    def test_html_to_markdown_h1(self) -> None:
        """<h1> is converted to a level-1 markdown heading (# ...)."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<h1>Top-level Heading</h1>")
        assert "# Top-level Heading" in result

    def test_html_to_markdown_h2(self) -> None:
        """<h2> is converted to a level-2 markdown heading (## ...)."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<h2>Section Heading</h2>")
        assert "## Section Heading" in result

    def test_html_to_markdown_h3_through_h6(self) -> None:
        """<h3>-<h6> each produce the correct number of # markers."""
        from owlbear_browser.cleaner import html_to_markdown

        for level in range(3, 7):
            html = f"<h{level}>Heading {level}</h{level}>"
            result = html_to_markdown(html)
            marker = "#" * level
            assert f"{marker} Heading {level}" in result, (
                f"Expected '{marker} Heading {level}' in html_to_markdown output; got: {result!r}"
            )

    def test_html_to_markdown_all_six_heading_levels_in_document(self) -> None:
        """A document containing h1-h6 renders all six distinct # depths."""
        from owlbear_browser.cleaner import html_to_markdown

        html = "<html><body><h1>H1</h1><h2>H2</h2><h3>H3</h3><h4>H4</h4><h5>H5</h5><h6>H6</h6></body></html>"
        result = html_to_markdown(html)
        for level in range(1, 7):
            marker = "#" * level
            assert f"{marker} H{level}" in result, f"Expected '{marker} H{level}' in result; got:\n{result!r}"

    # --- links --------------------------------------------------------------

    def test_html_to_markdown_anchor_with_href(self) -> None:
        """<a href="url">text</a> is converted to [text](url) markdown syntax."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown('<p><a href="https://example.com">Click here</a></p>')
        assert "[Click here](https://example.com)" in result

    def test_html_to_markdown_anchor_without_href(self) -> None:
        """<a> without href attribute uses empty string for the URL part."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<p><a>Bare link text</a></p>")
        assert "[Bare link text]()" in result

    # --- lists --------------------------------------------------------------

    def test_html_to_markdown_unordered_list_items(self) -> None:
        """<ul><li> items are converted to '- item' bullet syntax."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<ul><li>Alpha</li><li>Beta</li><li>Gamma</li></ul>")
        assert "- Alpha" in result
        assert "- Beta" in result
        assert "- Gamma" in result

    def test_html_to_markdown_ordered_list_numbering(self) -> None:
        """<ol><li> items are converted to '1. ... 2. ...' numbered syntax."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<ol><li>First</li><li>Second</li><li>Third</li></ol>")
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result

    # --- table --------------------------------------------------------------

    def test_html_to_markdown_table_gfm_header_separator(self) -> None:
        """<table> with a header row produces a GFM table with '---' separator after row 0."""
        from owlbear_browser.cleaner import html_to_markdown

        html = "<table><tr><th>Name</th><th>Role</th></tr><tr><td>Alice</td><td>Engineer</td></tr></table>"
        result = html_to_markdown(html)
        assert "| Name | Role |" in result
        assert "| --- | --- |" in result
        assert "| Alice | Engineer |" in result

    def test_html_to_markdown_empty_table_returns_empty(self) -> None:
        """A <table> element with no rows produces no markdown table output."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<table></table>")
        assert "|" not in result

    # --- public API contract ------------------------------------------------

    def test_html_to_markdown_empty_string_returns_empty(self) -> None:
        """html_to_markdown('') returns an empty string (not None or whitespace)."""
        from owlbear_browser.cleaner import html_to_markdown

        assert html_to_markdown("") == ""

    def test_html_to_markdown_whitespace_only_returns_empty(self) -> None:
        """html_to_markdown with only whitespace returns an empty string."""
        from owlbear_browser.cleaner import html_to_markdown

        assert html_to_markdown("   \n\t  ") == ""

    def test_html_to_markdown_returns_str_type(self) -> None:
        """html_to_markdown() always returns a str, never None or bytes."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<p>Some content</p>")
        assert isinstance(result, str)

    def test_html_to_markdown_paragraph_text_preserved(self) -> None:
        """Plain text inside <p> is present in the markdown output."""
        from owlbear_browser.cleaner import html_to_markdown

        result = html_to_markdown("<p>Plain paragraph content</p>")
        assert "Plain paragraph content" in result

    # --- untested _NOISE_TAGS: nav, footer, script, style via clean() -------

    def test_clean_strips_nav_element(self) -> None:
        """Text inside <nav> is absent from clean() output."""
        from owlbear_browser.cleaner import clean

        html = "<nav>Navigation Menu Links Home About</nav><p>Article body</p>"
        result = clean(html)
        assert "Navigation Menu Links" not in result
        assert "Article body" in result

    def test_clean_strips_footer_element(self) -> None:
        """Text inside <footer> is absent from clean() output."""
        from owlbear_browser.cleaner import clean

        html = "<p>Page content</p><footer>Footer Copyright 2026</footer>"
        result = clean(html)
        assert "Footer Copyright 2026" not in result
        assert "Page content" in result

    def test_clean_strips_script_element(self) -> None:
        """JavaScript inside <script> is absent from clean() output."""
        from owlbear_browser.cleaner import clean

        html = '<script>var trackingCode = "secret";</script><p>Visible content</p>'
        result = clean(html)
        assert "trackingCode" not in result
        assert "Visible content" in result

    def test_clean_strips_style_element(self) -> None:
        """CSS inside <style> is absent from clean() output."""
        from owlbear_browser.cleaner import clean

        html = "<style>.hidden { display: none; }</style><p>Body text here</p>"
        result = clean(html)
        assert ".hidden" not in result
        assert "Body text here" in result

    # --- untested _NOISE_IDS: ms-site-actions via clean() -------------------

    def test_clean_strips_ms_site_actions_by_id(self) -> None:
        """Element with id='ms-site-actions' (SharePoint actions bar) is stripped."""
        from owlbear_browser.cleaner import clean

        html = '<div id="ms-site-actions">Like Follow Subscribe Share</div><p>Document body content</p>'
        result = clean(html)
        assert "Like Follow Subscribe Share" not in result
        assert "Document body content" in result
