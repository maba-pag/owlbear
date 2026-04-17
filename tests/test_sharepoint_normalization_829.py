"""Failing RED-phase tests for #829: SharePoint normalization + idempotent output.

Binding AC (from Architecture Review Pass 2):
  AC1 - strip_noise() _NOISE_CLASSES adds: ms-Breadcrumb, ms-Persona, ms-LivePersona,
        ms-DateTimeField. _NOISE_IDS adds: SuiteNavPlaceHolder, O365_NavHeader,
        s4-ribbonrow. Existing patterns preserved.
  AC2 - _normalize_content() additionally strips \\r characters and zero-width Unicode
        (U+200B, U+200C, U+200D, U+FEFF) before existing whitespace normalization.
  AC3 - clean(html) called twice on identical input produces byte-identical output
        (verified by hash). extract_content() on identical input produces identical output.

All TestFromAC_* tests MUST FAIL at RED phase:
  - ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField absent from _NOISE_CLASSES
  - SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow absent from _NOISE_IDS
  - _normalize_content() does not strip zero-width Unicode (U+200B/200C/200D/FEFF)

Note on U+000D (\\r) tests: tested via &#13; HTML entity — character references resolve
AFTER HTML5 input-stream normalization, so &#13; may preserve U+000D in lxml text nodes.
If this test passes trivially (lxml normalises anyway), remove it before commit.
"""

from __future__ import annotations

import hashlib


# ---------------------------------------------------------------------------
# AC1: strip_noise() / clean() remove new SharePoint CSS class patterns
# ---------------------------------------------------------------------------


class TestFromAC_StripNoiseSharePointClasses:
    """AC1: _NOISE_CLASSES must include ms-Breadcrumb, ms-Persona, ms-LivePersona, ms-DateTimeField."""

    def test_strip_noise_removes_ms_breadcrumb(self) -> None:
        """strip_noise() removes element with class ms-Breadcrumb (breadcrumb navigation)."""
        from owlbear_browser.cleaner import strip_noise

        # Use <div> not <nav> — <nav> is already in _NOISE_TAGS and would pass trivially
        html = '<div class="ms-Breadcrumb"><a>Home</a> &gt; <a>Documents</a></div><p>Main text</p>'
        result = strip_noise(html)
        assert "Home</a>" not in result

    def test_strip_noise_removes_ms_persona(self) -> None:
        """strip_noise() removes element with class ms-Persona (user avatar container)."""
        from owlbear_browser.cleaner import strip_noise

        html = '<div class="ms-Persona"><img src="avatar.jpg" /><span>John Doe</span></div><p>Document body</p>'
        result = strip_noise(html)
        assert "John Doe" not in result

    def test_strip_noise_removes_ms_livepersona(self) -> None:
        """strip_noise() removes element with class ms-LivePersona (live persona card)."""
        from owlbear_browser.cleaner import strip_noise

        html = '<div class="ms-LivePersona"><span>Jane Smith</span></div><p>Report text</p>'
        result = strip_noise(html)
        assert "Jane Smith" not in result

    def test_strip_noise_removes_ms_datetimefield(self) -> None:
        """strip_noise() removes element with class ms-DateTimeField (dynamic timestamp)."""
        from owlbear_browser.cleaner import strip_noise

        html = '<span class="ms-DateTimeField">Modified 2026-04-11T08:00:00Z</span><p>Policy text</p>'
        result = strip_noise(html)
        assert "Modified 2026-04-11T08:00:00Z" not in result

    def test_clean_strips_ms_breadcrumb(self) -> None:
        """clean() omits breadcrumb navigation text from the markdown output."""
        from owlbear_browser.cleaner import clean

        # Use <div> not <nav> — <nav> is already in _NOISE_TAGS and would pass trivially
        html = '<div class="ms-Breadcrumb"><a>Home</a> / <a>Team Site</a> / Policies</div><h1>HR Policy</h1>'
        result = clean(html)
        assert "Team Site" not in result
        assert "HR Policy" in result

    def test_clean_strips_ms_persona_and_livepersona(self) -> None:
        """clean() strips both ms-Persona and ms-LivePersona user avatar elements."""
        from owlbear_browser.cleaner import clean

        html = """
            <div class="ms-Persona"><img /><span>Alice Admin</span></div>
            <div class="ms-LivePersona"><span>Bob Builder</span></div>
            <p>Project specification document.</p>
        """
        result = clean(html)
        assert "Alice Admin" not in result
        assert "Bob Builder" not in result
        assert "Project specification document" in result

    def test_clean_strips_ms_datetimefield(self) -> None:
        """clean() strips the dynamic timestamp element from the markdown output."""
        from owlbear_browser.cleaner import clean

        html = """
            <h1>Quarterly Report</h1>
            <span class="ms-DateTimeField">Last modified: 2026-03-15T12:00:00Z</span>
            <p>Revenue increased 12% year over year.</p>
        """
        result = clean(html)
        assert "Last modified: 2026-03-15T12:00:00Z" not in result
        assert "Quarterly Report" in result
        assert "Revenue increased" in result

    def test_element_with_multiple_classes_including_ms_persona_is_stripped(self) -> None:
        """Element with multiple CSS classes including ms-Persona is removed correctly."""
        from owlbear_browser.cleaner import strip_noise

        html = (
            '<div class="sp-webpart-container ms-Persona u-flexItemGrow">'
            "<span>Carol</span></div><p>Main page content</p>"
        )
        result = strip_noise(html)
        assert "Carol" not in result
        assert "Main page content" in result


# ---------------------------------------------------------------------------
# AC1: strip_noise() / clean() remove new SharePoint ID patterns
# ---------------------------------------------------------------------------


class TestFromAC_StripNoiseSharePointIds:
    """AC1: _NOISE_IDS must include SuiteNavPlaceHolder, O365_NavHeader, s4-ribbonrow."""

    def test_strip_noise_removes_suitenavplaceholder(self) -> None:
        """strip_noise() removes element with id=SuiteNavPlaceHolder."""
        from owlbear_browser.cleaner import strip_noise

        html = '<div id="SuiteNavPlaceHolder">Suite nav bar content</div><p>Page content</p>'
        result = strip_noise(html)
        assert "Suite nav bar content" not in result
        assert "Page content" in result

    def test_strip_noise_removes_o365_navheader(self) -> None:
        """strip_noise() removes element with id=O365_NavHeader."""
        from owlbear_browser.cleaner import strip_noise

        html = '<div id="O365_NavHeader">O365 navigation header</div><p>Document body</p>'
        result = strip_noise(html)
        assert "O365 navigation header" not in result
        assert "Document body" in result

    def test_strip_noise_removes_s4_ribbonrow(self) -> None:
        """strip_noise() removes element with id=s4-ribbonrow (SharePoint ribbon row)."""
        from owlbear_browser.cleaner import strip_noise

        html = '<div id="s4-ribbonrow">Ribbon New Edit Delete Share</div><p>List items</p>'
        result = strip_noise(html)
        assert "Ribbon New Edit Delete Share" not in result
        assert "List items" in result

    def test_clean_strips_all_three_new_ids(self) -> None:
        """clean() strips SuiteNavPlaceHolder, O365_NavHeader, and s4-ribbonrow together."""
        from owlbear_browser.cleaner import clean

        html = """
            <div id="SuiteNavPlaceHolder">Microsoft 365 Suite</div>
            <div id="O365_NavHeader">Office 365 Nav</div>
            <div id="s4-ribbonrow">SP Ribbon Actions</div>
            <h1>Annual Plan 2026</h1>
            <p>Strategic objectives for the upcoming fiscal year.</p>
        """
        result = clean(html)
        assert "Microsoft 365 Suite" not in result
        assert "Office 365 Nav" not in result
        assert "SP Ribbon Actions" not in result
        assert "Annual Plan 2026" in result
        assert "Strategic objectives" in result

    def test_comprehensive_sharepoint_page_classes_and_ids_stripped(self) -> None:
        """All new class and ID patterns stripped together; document body preserved."""
        from owlbear_browser.cleaner import clean

        html = """
            <div id="SuiteNavPlaceHolder">MS365 Suite Nav</div>
            <div id="O365_NavHeader">O365 Header Row</div>
            <div id="s4-ribbonrow">Share Edit Delete</div>
            <div class="ms-Breadcrumb"><a>Home</a> / <a>Team Sites</a></div>
            <div class="ms-Persona"><span>Dave Developer</span></div>
            <div class="ms-LivePersona"><span>Eve Engineer</span></div>
            <h1>Security Standards</h1>
            <span class="ms-DateTimeField">Updated: 2026-01-01T00:00:00Z</span>
            <p>All systems must comply with ISO 27001.</p>
        """
        result = clean(html)
        assert "MS365 Suite Nav" not in result
        assert "O365 Header Row" not in result
        assert "Share Edit Delete" not in result
        assert "Team Sites" not in result
        assert "Dave Developer" not in result
        assert "Eve Engineer" not in result
        assert "Updated: 2026-01-01T00:00:00Z" not in result
        assert "Security Standards" in result
        assert "ISO 27001" in result


# ---------------------------------------------------------------------------
# AC2: _normalize_content() strips zero-width Unicode and U+000D (\r)
# ---------------------------------------------------------------------------


class TestFromAC_NormalizeContentZeroWidth:
    """AC2: clean() output must contain no zero-width Unicode or carriage-return artifacts."""

    def test_clean_strips_zero_width_space_u200b(self) -> None:
        """clean() removes U+200B ZERO WIDTH SPACE embedded in paragraph text."""
        from owlbear_browser.cleaner import clean

        html = "<p>Invisible\u200bbreak inside the sentence.</p>"
        result = clean(html)
        assert "\u200b" not in result
        assert "Invisible" in result
        assert "break inside the sentence" in result

    def test_clean_strips_zero_width_non_joiner_u200c(self) -> None:
        """clean() removes U+200C ZERO WIDTH NON-JOINER from paragraph content."""
        from owlbear_browser.cleaner import clean

        html = "<p>Compound\u200cword formation text.</p>"
        result = clean(html)
        assert "\u200c" not in result
        assert "Compound" in result
        assert "word formation text" in result

    def test_clean_strips_zero_width_joiner_u200d(self) -> None:
        """clean() removes U+200D ZERO WIDTH JOINER from output."""
        from owlbear_browser.cleaner import clean

        html = "<p>Sequence\u200djoiner text in paragraph.</p>"
        result = clean(html)
        assert "\u200d" not in result
        assert "Sequence" in result
        assert "joiner text" in result

    def test_clean_strips_bom_ufeff(self) -> None:
        """clean() removes U+FEFF ZERO WIDTH NO-BREAK SPACE / BOM from output."""
        from owlbear_browser.cleaner import clean

        html = "<p>Report\ufeffdata with a BOM artifact.</p>"
        result = clean(html)
        assert "\ufeff" not in result
        assert "Report" in result
        assert "data with a BOM artifact" in result

    def test_clean_strips_all_four_zero_width_chars_in_combination(self) -> None:
        """clean() removes all four zero-width Unicode variants when mixed in content."""
        from owlbear_browser.cleaner import clean

        html = "<p>Text\u200b with\u200c many\u200d zero-width\ufeff chars.</p>"
        result = clean(html)
        assert "\u200b" not in result
        assert "\u200c" not in result
        assert "\u200d" not in result
        assert "\ufeff" not in result
        assert "Text" in result
        assert "zero-width" in result
        assert "chars" in result

    def test_clean_zero_width_only_paragraph_produces_no_visible_artifacts(self) -> None:
        """Paragraph of only zero-width chars produces output free of those chars."""
        from owlbear_browser.cleaner import clean

        html = "<p>\u200b\u200c\u200d\ufeff</p><p>Real content here.</p>"
        result = clean(html)
        assert "\u200b" not in result
        assert "\u200c" not in result
        assert "\u200d" not in result
        assert "\ufeff" not in result
        assert "Real content here" in result

    def test_clean_zero_width_chars_removed_preserving_adjacent_text(self) -> None:
        """Zero-width chars removed without corrupting the text they are embedded in."""
        from owlbear_browser.cleaner import clean

        html = "<p>Word\u200bphrase and another\u200bword in a sentence.</p>"
        result = clean(html)
        assert "\u200b" not in result
        assert "Word" in result
        assert "phrase" in result
        assert "another" in result

    def test_clean_zero_width_in_heading_stripped(self) -> None:
        """Zero-width chars embedded in heading text are removed from markdown output."""
        from owlbear_browser.cleaner import clean

        html = "<h1>Project\u200bCharter\ufeff</h1><p>Scope, timeline, budget.</p>"
        result = clean(html)
        assert "\u200b" not in result
        assert "\ufeff" not in result
        assert "Project" in result
        assert "Charter" in result
        assert "Scope, timeline, budget" in result

    def test_clean_strips_cr_via_html_entity(self) -> None:
        """clean() removes U+000D (\\r) from content injected via &#13; HTML entity.

        &#13; is a character reference resolved after input-stream normalisation,
        which may preserve U+000D in lxml text nodes. If lxml normalises this to
        U+000A too, remove this test and note the gap in the end_work comment.
        """
        from owlbear_browser.cleaner import clean

        html = "<p>Hello&#13;World</p><p>Second paragraph.</p>"
        result = clean(html)
        assert "\r" not in result


# ---------------------------------------------------------------------------
# AC3: Idempotent output — clean() produces stable, artifact-free results
# ---------------------------------------------------------------------------


class TestFromAC_IdempotentOutput:
    """AC3: clean() byte-identical on repeated calls; zero-width artifacts absent from output."""

    def test_clean_hash_stable_and_zero_width_artifacts_absent(self) -> None:
        """clean() twice gives same hash AND output contains no zero-width characters."""
        from owlbear_browser.cleaner import clean

        html = "<p>Data\u200bwith\ufeffartifacts in the content.</p>"
        first = clean(html)
        second = clean(html)
        assert hashlib.sha256(first.encode()).hexdigest() == hashlib.sha256(second.encode()).hexdigest()
        # Zero-width chars must be stripped — these assertions drive the RED failure
        assert "\u200b" not in first
        assert "\ufeff" not in first

    def test_clean_repeated_calls_with_full_sharepoint_page(self) -> None:
        """clean() of a full SharePoint page is byte-identical and artifact-free on repeat."""
        from owlbear_browser.cleaner import clean

        html = """
            <div id="SuiteNavPlaceHolder">Suite</div>
            <div class="ms-Breadcrumb"><a>Home</a></div>
            <div class="ms-Persona"><span>User\u200bName</span></div>
            <h1>Governance Policy\ufeff</h1>
            <p>All teams must follow the established\u200c protocols.</p>
        """
        first = clean(html)
        second = clean(html)
        assert first == second
        # Artifacts must be absent — these are the failing assertions
        assert "\u200b" not in first
        assert "\ufeff" not in first
        assert "\u200c" not in first
        # Document content preserved
        assert "Governance Policy" in first

    def test_clean_output_free_of_all_zero_width_variants_in_full_pipeline(self) -> None:
        """Full pipeline clean() removes all four zero-width variants from mixed input."""
        from owlbear_browser.cleaner import clean

        html = "<h1>Title\u200b</h1><p>Body\u200cwith\u200dencoded\ufeffchars.</p>"
        result = clean(html)
        for char in ("\u200b", "\u200c", "\u200d", "\ufeff"):
            assert char not in result, f"Zero-width char {hex(ord(char))} found in output"
        assert "Title" in result
        assert "Body" in result
        assert "chars" in result
