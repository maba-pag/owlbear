"""TDD RED: C-11 — body_parser rewrite (CommonMark ATX closing-hash + module export).

Task:  #1056 (Brief C #1043) — paper-c.md §2, §8.2
AC:    C5, C8, C53, Section export from body_parser
Scope: ATX closing-hash stripping (CommonMark §4.2) and __all__ export contract.
All tests FAIL (RED phase — rewrite not yet applied).
"""

from __future__ import annotations

import owlbear_kanban.body_parser as _bp
from owlbear_kanban.body_parser import parse_body, render_body


class TestFromAC_BodyParserRewrite:
    """AC-C8 (ATX closing hash), AC-C5 (round-trip), AC-C53 (render), Section export."""

    # ------------------------------------------------------------------ #
    # Happy path — ATX closing-hash stripping (AC-C8, CommonMark §4.2)   #
    # ------------------------------------------------------------------ #

    def test_ac_c8_closing_hashes_stripped_h2(self) -> None:
        """AC-C8: '## Heading ##' creates Section(heading='Heading'), not 'Heading ##'.

        CommonMark §4.2: an optional closing sequence of '#' preceded by a space
        and followed only by spaces is stripped from the heading text.
        Current hand-rolled regex captures group(2)='Heading ##' verbatim.
        """
        md = "## Heading ##\n\ncontent\n"
        sections = parse_body(md)
        headings = [s for s in sections if s.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == "Heading"

    def test_ac_c8_closing_hashes_stripped_different_count(self) -> None:
        """AC-C8: closing hash count may differ from opening (e.g. '# Title ###').

        CommonMark: closing sequence does not have to match the opening count.
        Current impl returns 'Title ###'.
        """
        md = "# Title ###\n\ncontent\n"
        sections = parse_body(md)
        headings = [s for s in sections if s.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == "Title"
        assert headings[0].level == 1

    def test_ac_c53_render_excludes_closing_hash(self) -> None:
        """AC-C53 + AC-C8: rendered ATX line must not include the closing hash sequence.

        After a correct parse 'My Heading ##' → Section(heading='My Heading'),
        render_body produces '## My Heading', not '## My Heading ##'.
        Current impl emits the un-stripped heading, so the rendered line is wrong.
        """
        md = "## My Heading ##\n\nsome content\n"
        sections = parse_body(md)
        rendered = render_body(sections)
        heading_lines = [ln for ln in rendered.splitlines() if ln.startswith("#")]
        assert len(heading_lines) == 1
        assert heading_lines[0] == "## My Heading"

    # ------------------------------------------------------------------ #
    # Edge cases — ATX closing-hash variants                              #
    # ------------------------------------------------------------------ #

    def test_ac_c8_closing_hash_with_trailing_space(self) -> None:
        """AC-C8: trailing space after closing '#' sequence is stripped too.

        '## Heading ## ' → heading='Heading', not 'Heading ##'.
        Current impl strips only whitespace: group(2)='Heading ## ' → 'Heading ##'.
        """
        md = "## Heading ## \n\ncontent\n"
        sections = parse_body(md)
        headings = [s for s in sections if s.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == "Heading"

    def test_ac_c8_closing_hash_produces_same_section_as_no_closing(self) -> None:
        """AC-C8 + AC-C5: '## Heading ##' and '## Heading' must parse to identical Sections.

        Both represent the same CommonMark heading text.
        Current impl produces Section(heading='Heading ##') vs Section(heading='Heading').
        """
        sections_with = parse_body("## Heading ##\n\ncontent\n")
        sections_without = parse_body("## Heading\n\ncontent\n")
        assert sections_with == sections_without

    def test_ac_c8_all_levels_strip_closing_hashes(self) -> None:
        """AC-C8: closing hash stripping applies to all ATX heading levels 1-6.

        Each '#{level} Text #{level}' → heading='Text'.
        Current impl returns 'Text #{level}' for every level.
        """
        for level in range(1, 7):
            opening = "#" * level
            md = f"{opening} LevelText {opening}\n\ncontent\n"
            sections = parse_body(md)
            headings = [s for s in sections if s.heading is not None]
            assert len(headings) == 1, f"level {level}: expected 1 heading section"
            assert headings[0].heading == "LevelText", (
                f"level {level}: expected 'LevelText', got '{headings[0].heading}'"
            )

    # ------------------------------------------------------------------ #
    # Boundary — single closing hash leaves empty heading text            #
    # ------------------------------------------------------------------ #

    def test_ac_c8_single_closing_hash_only_yields_empty_heading(self) -> None:
        """AC-C8 boundary: '## #' — the '#' IS the closing sequence; heading text is empty.

        CommonMark: '## #' → level-2 heading with empty text, because the lone '#'
        is preceded by a space and followed by EOL, making it a valid closing sequence.
        Current impl returns heading='#' (not stripped).
        """
        md = "## #\n\ncontent\n"
        sections = parse_body(md)
        headings = [s for s in sections if s.heading is not None]
        assert len(headings) == 1
        assert headings[0].heading == ""
        assert headings[0].level == 2

    # ------------------------------------------------------------------ #
    # Section export — body_parser __all__ contract                       #
    # ------------------------------------------------------------------ #

    def test_body_parser_defines_all(self) -> None:
        """Section export AC: body_parser must define __all__ (explicit public API).

        Currently body_parser.py has no __all__, so consumers rely on implicit
        namespace leakage from the models import.
        """
        assert hasattr(_bp, "__all__"), "body_parser must define __all__"

    def test_body_parser_all_contains_public_api(self) -> None:
        """Section export AC: __all__ must list Section, parse_body, and render_body.

        Without __all__, getattr returns [] and all membership assertions fail.
        """
        all_exports = getattr(_bp, "__all__", [])
        assert "Section" in all_exports
        assert "parse_body" in all_exports
        assert "render_body" in all_exports
