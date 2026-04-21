"""TDD RED: C-02 — body_parser edge-case boundary tests (task #1047).

Task: #1047 (Brief C #1043) — paper-c.md §8.2, §8.11
AC:   C5 (round-trip boundary: no trailing LF), C10 (fence-length boundary)
All tests FAIL (RED phase).
"""

from __future__ import annotations

from owlbear_kanban.body_parser import parse_body, render_body
from owlbear_kanban.storage import Section  # noqa: F401 — imported for type clarity


class TestFromAC_BodyParserEdgeCases:
    """Boundary / edge-case tests for AC-C5 and AC-C10.

    The base test suite (test_body_parser.py) covers the happy paths.
    This class covers stricter boundary conditions not exercised there.
    """

    # --- AC-C5: round-trip identity — no trailing newline boundary ---

    def test_ac_c5_roundtrip_atx_no_trailing_newline(self) -> None:
        """AC-C5: round-trip identity holds when ATX body has no trailing LF.

        render_body adds a trailing \\n; parse_body then sees it and produces
        content ending in \\n, which differs from the original.  The round-trip
        guarantee must hold regardless of whether the source text ends in \\n.
        """
        md = "## Heading\n\nContent line"  # deliberately no trailing \n
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections

    def test_ac_c5_roundtrip_preamble_no_trailing_newline(self) -> None:
        """AC-C5: round-trip identity holds for preamble-only body without trailing LF.

        Same root cause: render always appends \\n when content lacks it,
        so the re-parsed preamble section acquires a trailing \\n.
        """
        md = "Preamble only — no trailing newline"  # deliberately no trailing \n
        sections = parse_body(md)
        assert parse_body(render_body(sections)) == sections

    # --- AC-C10: fence-length boundary — shorter close must not end longer fence ---

    def test_ac_c10_five_backtick_fence_not_closed_by_three(self) -> None:
        """AC-C10: a 5-backtick opening fence is NOT closed by a 3-backtick line.

        CommonMark §4.5: the closing fence must be at least as long as the
        opening fence.  The current implementation uses ``{3,}`` for the
        closing pattern regardless of opening length, so ``` closes ````` and
        the content following the premature close is parsed as headings.
        """
        md = (
            "## Real Section\n\n"
            "`````\n"
            "## inside-long-fence\n"
            "```\n"        # 3-backtick must NOT close the 5-backtick fence
            "## still-inside\n"
            "`````\n"      # 5-backtick is the legitimate close
            "\nafter fence\n"
        )
        sections = parse_body(md)
        headings = [s.heading for s in sections if s.heading]
        assert "still-inside" not in headings

    def test_ac_c10_five_tilde_fence_not_closed_by_three(self) -> None:
        """AC-C10: a 5-tilde opening fence is NOT closed by a 3-tilde line.

        Same fence-length rule applies to tilde (~~~) fences.
        """
        md = (
            "## Real Section\n\n"
            "~~~~~\n"
            "## inside-long-tilde-fence\n"
            "~~~\n"        # 3-tilde must NOT close the 5-tilde fence
            "## still-inside-tilde\n"
            "~~~~~\n"      # 5-tilde is the legitimate close
            "\nafter fence\n"
        )
        sections = parse_body(md)
        headings = [s.heading for s in sections if s.heading]
        assert "still-inside-tilde" not in headings


class TestBuilderDiscovered:
    """Precision assertions added from reviewer feedback on weak checks."""

    def test_ac_c6_crlf_normalises_to_exact_lf_content(self) -> None:
        """AC-C6: CRLF becomes LF while preserving exact line boundaries."""
        md = "## Notes\r\n\r\nLine one.\r\nLine two.\r\n"
        sections = parse_body(md)

        notes_sections = [s for s in sections if s.heading == "Notes"]
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
