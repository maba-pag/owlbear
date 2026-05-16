"""TDD RED: C-02 — body_parser round-trip tests.

Task: #1047 (Brief C #1043) — paper-c.md §8.2, §8.11
AC:   C5, C6, C7, C8, C9, C10, C11, C12, C53
All tests FAIL (RED phase — body_parser not yet implemented).
"""

from __future__ import annotations

import owlbear_kanban.body_parser as _bp
import pytest

from owlbear_kanban.body_parser import (
    parse_body,
    render_body,
)  # NEW module — ImportError in RED
from owlbear_kanban.storage import Section  # NEW type — ImportError in RED


# ---------------------------------------------------------------------------
# TestFromAC_BodyParserRoundTrip — AC-C5 through AC-C12, AC-C53
# ---------------------------------------------------------------------------


class TestFromAC_BodyParserRoundTrip:
    """AC-C5 through AC-C12, AC-C53: parse_body / render_body contract."""

    # --- AC-C5: round-trip identity ---

    def test_ac_c5_roundtrip_empty_body(self) -> None:
        """AC-C5: parse_body(render_body([])) == []."""
        sections: list[Section] = []
        assert parse_body(render_body(sections)) == sections

    def test_ac_c5_roundtrip_preamble_only(self) -> None:
        """AC-C5: preamble-only body round-trips to identical Section."""
        md = "Some intro text\nwith two lines.\n"
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections

    def test_ac_c5_roundtrip_single_heading(self) -> None:
        """AC-C5: single ATX heading with content round-trips identically."""
        md = "## Acceptance Criteria\n\n- item one\n- item two\n"
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections

    def test_ac_c5_roundtrip_multi_section(self) -> None:
        """AC-C5: multi-section body round-trips identically."""
        md = "Preamble text.\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B.\n"
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections

    # --- AC-C6: CRLF normalisation ---

    def test_ac_c6_crlf_normalised_to_lf_in_content(self) -> None:
        """AC-C6: CRLF in input is normalised to LF in Section.content."""
        md = "## Notes\r\n\r\nLine one.\r\nLine two.\r\n"
        sections = parse_body(md)
        assert len(sections) >= 1
        matching = [s for s in sections if s.heading and "Notes" in s.heading]
        assert len(matching) == 1
        content = matching[0].content
        assert "\r" not in content

    def test_ac_c6_crlf_entire_body_normalised(self) -> None:
        """AC-C6: CRLF in preamble is also normalised to LF."""
        md = "First line.\r\nSecond line.\r\n"
        sections = parse_body(md)
        for sec in sections:
            assert "\r" not in sec.content

    # --- AC-C7: ##Heading (no space) is content, not a section boundary ---

    def test_ac_c7_no_space_heading_is_content(self) -> None:
        """AC-C7: '##Heading' (no space after #) is content, not a new section."""
        md = "## Real Section\n\n##FakeHeading should be content\n\nMore text.\n"
        sections = parse_body(md)
        headings = [s.heading for s in sections if s.heading]
        assert "FakeHeading should be content" not in headings
        assert not any("FakeHeading" in (h or "") for h in headings)

    def test_ac_c7_no_space_heading_preserved_verbatim_in_content(self) -> None:
        """AC-C7: '##Heading' string appears verbatim inside its parent section's content."""
        md = "## Parent\n\n##NotASection\n\nfollowing\n"
        sections = parse_body(md)
        parent_sections = [s for s in sections if s.heading == "Parent"]
        assert len(parent_sections) == 1
        assert "##NotASection" in parent_sections[0].content

    # --- AC-C8: ## Heading (with space) creates a Section ---

    def test_ac_c8_atx_h2_creates_section(self) -> None:
        """AC-C8: '## Heading' creates Section(heading='Heading', level=2)."""
        md = "## My Section\n\ncontent here\n"
        sections = parse_body(md)
        h2 = [s for s in sections if s.heading == "My Section"]
        assert len(h2) == 1
        assert h2[0].level == 2

    def test_ac_c8_atx_h1_creates_level1_section(self) -> None:
        """AC-C8: '# Heading' creates Section(heading='Heading', level=1)."""
        md = "# Top Level\n\ncontent\n"
        sections = parse_body(md)
        h1 = [s for s in sections if s.heading == "Top Level"]
        assert len(h1) == 1
        assert h1[0].level == 1

    def test_ac_c8_atx_h6_creates_level6_section(self) -> None:
        """AC-C8: '###### Deep' creates Section(level=6)."""
        md = "###### Deep Section\n\ncontent\n"
        sections = parse_body(md)
        h6 = [s for s in sections if s.heading == "Deep Section"]
        assert len(h6) == 1
        assert h6[0].level == 6

    # --- AC-C9: Setext headings create sections ---

    def test_ac_c9_setext_equals_creates_level1(self) -> None:
        """AC-C9: 'Heading\\n===' creates Section(heading='Heading', level=1)."""
        md = "Setext One\n===========\n\ncontent here\n"
        sections = parse_body(md)
        setext = [s for s in sections if s.heading and "Setext One" in s.heading]
        assert len(setext) == 1
        assert setext[0].level == 1

    def test_ac_c9_setext_dashes_creates_level2(self) -> None:
        """AC-C9: 'Heading\\n---' creates Section(level=2)."""
        md = "Setext Two\n-----------\n\ncontent here\n"
        sections = parse_body(md)
        setext = [s for s in sections if s.heading and "Setext Two" in s.heading]
        assert len(setext) == 1
        assert setext[0].level == 2

    # --- AC-C10: code-fenced content is not a section boundary ---

    def test_ac_c10_code_fenced_heading_not_a_section(self) -> None:
        """AC-C10: '## Looks-like-heading' inside a fenced code block is NOT a section."""
        md = "## Real Section\n\n```\n## Looks-like-heading\ncode content\n```\n\nafter code\n"
        sections = parse_body(md)
        headings = [s.heading for s in sections if s.heading]
        assert "Looks-like-heading" not in headings

    def test_ac_c10_indented_code_heading_not_a_section(self) -> None:
        """AC-C10: heading-like line inside indented code block is NOT a section."""
        md = "## Real\n\n    ## indented heading line\n\nafter\n"
        sections = parse_body(md)
        headings = [s.heading for s in sections if s.heading]
        assert "indented heading line" not in headings

    # --- AC-C11: trailing whitespace preserved ---

    def test_ac_c11_trailing_space_preserved(self) -> None:
        """AC-C11: trailing whitespace within section content is preserved verbatim."""
        # Two trailing spaces = line break in Markdown
        md = "## Notes\n\nLine with trailing spaces  \nNext line.\n"
        sections = parse_body(md)
        notes = [s for s in sections if s.heading == "Notes"]
        assert len(notes) == 1
        assert "  \n" in notes[0].content

    # --- AC-C12: inter-section blank lines preserved ---

    def test_ac_c12_inter_section_blank_lines_preserved(self) -> None:
        """AC-C12: blank lines between sections survive the round-trip."""
        md = "## Section A\n\nContent A.\n\n\n## Section B\n\nContent B.\n"
        sections = parse_body(md)
        rendered = render_body(sections)
        # The double blank between sections must survive
        assert "\n\n\n" in rendered or parse_body(rendered) == sections

    def test_ac_c12_blank_lines_within_content_preserved(self) -> None:
        """AC-C12: blank lines inside a section's content survive round-trip."""
        md = "## Notes\n\nParagraph one.\n\nParagraph two.\n"
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections
        notes = [s for s in sections if s.heading == "Notes"]
        assert "\n\n" in notes[0].content

    # --- AC-C53: setext headings round-trip as ATX headings ---

    def test_ac_c53_setext_renders_as_atx(self) -> None:
        """AC-C53: setext heading read → render → ATX heading output (same Section model)."""
        setext_md = "My Heading\n==========\n\nsome content\n"
        sections = parse_body(setext_md)
        rendered = render_body(sections)
        # ATX form: starts with '# My Heading' (one # for level 1)
        assert "# My Heading" in rendered
        assert "===========" not in rendered

    def test_ac_c53_setext_section_model_unchanged(self) -> None:
        """AC-C53: the Section object from setext and equivalent ATX are equal."""
        setext_md = "My Heading\n==========\n\ncontent\n"
        atx_md = "# My Heading\n\ncontent\n"
        setext_sections = parse_body(setext_md)
        atx_sections = parse_body(atx_md)
        assert setext_sections == atx_sections

    # --- AC-C5: preamble section ---

    def test_ac_c5_preamble_section_heading_none_level_zero(self) -> None:
        """AC-C5: content before first heading → Section(heading=None, level=0)."""
        md = "Intro line.\n\n## First Heading\n\ncontent\n"
        sections = parse_body(md)
        preamble = [s for s in sections if s.heading is None]
        assert len(preamble) == 1
        assert preamble[0].level == 0
        assert "Intro line" in preamble[0].content


class TestFromAC_BodyParserEdgeCases:
    """Boundary coverage promoted from archived task tests."""

    def test_ac_c5_roundtrip_atx_no_trailing_newline(self) -> None:
        """AC-C5: round-trip identity holds when ATX body has no trailing LF."""
        md = "## Heading\n\nContent line"
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections

    def test_ac_c5_roundtrip_preamble_no_trailing_newline(self) -> None:
        """AC-C5: preamble-only body without trailing LF round-trips exactly."""
        md = "Preamble only — no trailing newline"
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections

    def test_ac_c10_five_backtick_fence_not_closed_by_three(self) -> None:
        """AC-C10: a longer backtick fence is not closed by a shorter fence."""
        md = "## Real Section\n\n`````\n## inside-long-fence\n```\n## still-inside\n`````\n\nafter fence\n"
        sections = parse_body(md)
        headings = [section.heading for section in sections if section.heading]
        assert "still-inside" not in headings

    def test_ac_c10_five_tilde_fence_not_closed_by_three(self) -> None:
        """AC-C10: a longer tilde fence is not closed by a shorter fence."""
        md = "## Real Section\n\n~~~~~\n## inside-long-tilde-fence\n~~~\n## still-inside-tilde\n~~~~~\n\nafter fence\n"
        sections = parse_body(md)
        headings = [section.heading for section in sections if section.heading]
        assert "still-inside-tilde" not in headings

    def test_ac_c5_roundtrip_preserves_fenced_and_indented_content_verbatim(
        self,
    ) -> None:
        """AC-C5: fenced and indented code content survives round-trip byte-exactly."""
        md = (
            "## Section\n\n```\nline in fence\n## not-a-heading\n```\n\n    indented line\n    ## still-not-a-heading\n"
        )

        sections = parse_body(md)
        assert len(sections) == 1
        assert sections[0].heading == "Section"
        assert sections[0].content == (
            "\n```\nline in fence\n## not-a-heading\n```\n\n    indented line\n    ## still-not-a-heading\n"
        )
        assert parse_body(render_body(sections)) == sections

    def test_ac_c10_three_backtick_fence_accepts_five_backtick_close(self) -> None:
        """AC-C10: a longer closing backtick fence closes a shorter opening fence."""
        md = "## Real\n\n```\n## inside\n`````\n## After\n\noutside\n"

        sections = parse_body(md)
        headings = [section.heading for section in sections if section.heading]
        assert "inside" not in headings
        assert "After" in headings

    def test_ac_c10_three_tilde_fence_accepts_five_tilde_close(self) -> None:
        """AC-C10: a longer closing tilde fence closes a shorter opening fence."""
        md = "## Real\n\n~~~\n## inside-tilde\n~~~~~\n## After Tilde\n\noutside\n"

        sections = parse_body(md)
        headings = [section.heading for section in sections if section.heading]
        assert "inside-tilde" not in headings
        assert "After Tilde" in headings

    def test_ac_c6_crlf_normalises_to_exact_lf_content(self) -> None:
        """AC-C6: CRLF becomes LF while preserving exact line boundaries."""
        md = "## Notes\r\n\r\nLine one.\r\nLine two.\r\n"
        sections = parse_body(md)

        notes_sections = [section for section in sections if section.heading == "Notes"]
        assert len(notes_sections) == 1
        assert notes_sections[0].content == "\nLine one.\nLine two.\n"

    def test_ac_c12_preserves_exact_triple_blank_between_sections(self) -> None:
        """AC-C12: render preserves the exact blank-line count at section boundaries."""
        md = "## Section A\n\nContent A.\n\n\n## Section B\n\nContent B.\n"
        rendered = render_body(parse_body(md))

        assert rendered == md
        assert "Content A.\n\n\n## Section B" in rendered
        assert "Content A.\n\n\n\n## Section B" not in rendered

    def test_ac_c53_setext_level_one_renders_exact_atx_h1(self) -> None:
        """AC-C53: setext level-1 heading renders to exact ATX H1 form."""
        setext_md = "My Heading\n==========\n\nsome content\n"
        rendered = render_body(parse_body(setext_md))

        assert rendered == "# My Heading\n\nsome content\n"
        assert rendered.startswith("# My Heading\n")
        assert not rendered.startswith("## My Heading\n")


class TestFromAC_BodyParserRewrite:
    """Closing-hash and export coverage promoted from archived task tests."""

    def test_ac_c8_closing_hashes_stripped_h2(self) -> None:
        """AC-C8: closing hashes are stripped from H2 headings."""
        md = "## Heading ##\n\ncontent\n"
        sections = parse_body(md)
        headings = [section for section in sections if section.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == "Heading"

    def test_ac_c8_closing_hashes_stripped_different_count(self) -> None:
        """AC-C8: closing hash count may differ from the opening count."""
        md = "# Title ###\n\ncontent\n"
        sections = parse_body(md)
        headings = [section for section in sections if section.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == "Title"
        assert headings[0].level == 1

    def test_ac_c53_render_excludes_closing_hash(self) -> None:
        """AC-C53: rendered ATX headings exclude parsed closing hashes."""
        md = "## My Heading ##\n\nsome content\n"
        sections = parse_body(md)
        rendered = render_body(sections)
        heading_lines = [line for line in rendered.splitlines() if line.startswith("#")]
        assert len(heading_lines) == 1
        assert heading_lines[0] == "## My Heading"

    def test_ac_c8_closing_hash_with_trailing_space(self) -> None:
        """AC-C8: trailing space after closing hashes is stripped too."""
        md = "## Heading ## \n\ncontent\n"
        sections = parse_body(md)
        headings = [section for section in sections if section.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == "Heading"

    def test_ac_c8_closing_hash_produces_same_section_as_no_closing(self) -> None:
        """AC-C8: equivalent ATX headings parse to identical Section objects."""
        sections_with = parse_body("## Heading ##\n\ncontent\n")
        sections_without = parse_body("## Heading\n\ncontent\n")
        assert sections_with == sections_without

    def test_ac_c8_all_levels_strip_closing_hashes(self) -> None:
        """AC-C8: closing hash stripping applies to all ATX levels 1-6."""
        for level in range(1, 7):
            opening = "#" * level
            md = f"{opening} LevelText {opening}\n\ncontent\n"
            sections = parse_body(md)
            headings = [section for section in sections if section.heading is not None]
            assert len(headings) == 1, f"level {level}: expected 1 heading section"
            assert headings[0].heading == "LevelText", (
                f"level {level}: expected 'LevelText', got '{headings[0].heading}'"
            )

    def test_ac_c8_single_closing_hash_only_yields_empty_heading(self) -> None:
        """AC-C8: a lone closing hash after a space yields an empty heading."""
        md = "## #\n\ncontent\n"
        sections = parse_body(md)
        headings = [section for section in sections if section.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == ""
        assert headings[0].level == 2

    def test_body_parser_defines_all(self) -> None:
        """body_parser exposes an explicit __all__ public API."""
        assert hasattr(_bp, "__all__"), "body_parser must define __all__"

    def test_body_parser_all_contains_public_api(self) -> None:
        """body_parser.__all__ lists the supported public API symbols."""
        all_exports = getattr(_bp, "__all__", [])
        assert "Section" in all_exports
        assert "parse_body" in all_exports
        assert "render_body" in all_exports


class TestFromAC_EOFUnclosedFence:
    """EOF-unclosed fenced code blocks remain content and preserve fidelity."""

    @pytest.mark.parametrize(
        ("markdown", "expected_content"),
        [
            (
                "## Real Section\n\n```\n## inside-unclosed\nstill in fence",
                "\n```\n## inside-unclosed\nstill in fence",
            ),
            (
                "## Real Section\n\n```\n## inside-unclosed\nstill in fence\n",
                "\n```\n## inside-unclosed\nstill in fence\n",
            ),
            (
                "## Real Section\n\n~~~\n## inside-unclosed\nstill in fence",
                "\n~~~\n## inside-unclosed\nstill in fence",
            ),
            (
                "## Real Section\n\n~~~\n## inside-unclosed\nstill in fence\n",
                "\n~~~\n## inside-unclosed\nstill in fence\n",
            ),
            (
                "## Real Section\n\n```\nsetext-like\n===\nstill in fence",
                "\n```\nsetext-like\n===\nstill in fence",
            ),
            (
                "## Real Section\n\n```\nsetext-like\n---\nstill in fence",
                "\n```\nsetext-like\n---\nstill in fence",
            ),
        ],
    )
    def test_ac1_unclosed_fence_preserves_content_and_not_section(
        self,
        markdown: str,
        expected_content: str,
    ) -> None:
        """Heading-like content inside an unclosed fence remains plain content."""
        sections = parse_body(markdown)
        headings = [section.heading for section in sections if section.heading]

        assert headings == ["Real Section"]
        assert len(sections) == 1
        assert sections[0].content == expected_content
        assert parse_body(render_body(sections)) == sections


class TestFromAC_TabIndentedCode:
    """Tab-indented heading-like lines remain plain content."""

    def test_ac2_tab_indented_heading_like_line_is_not_section_and_is_verbatim(
        self,
    ) -> None:
        """Tab-indented heading-like lines must remain content with the tab preserved."""
        md = "## Real\n\n\t## Heading-like\n\tline two\n\nafter\n"

        sections = parse_body(md)
        headings = [section.heading for section in sections if section.heading]

        assert headings == ["Real"]
        assert len(sections) == 1
        assert sections[0].content == "\n\t## Heading-like\n\tline two\n\nafter\n"
