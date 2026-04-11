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
        assert "\n\n\n" not in result, (
            f"Expected at most one consecutive blank line; got: {result!r}"
        )

    def test_clean_semantically_equivalent_html_produces_same_output(self) -> None:
        """Same semantic content with different HTML whitespace → identical clean() output."""
        from owlbear_browser.cleaner import clean

        html_compact = "<p>Hello World</p>"
        html_spaced = "<p>Hello   World</p>"
        assert clean(html_compact) == clean(html_spaced), (
            f"Expected identical output; got:\n  compact: {clean(html_compact)!r}\n"
            f"  spaced:  {clean(html_spaced)!r}"
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
