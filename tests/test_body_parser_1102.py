"""Pass-through hardening tests for body_parser (task #1102).

Task: #1102 (Brief C #1043)
AC:   EOF-unclosed fenced code blocks, tab-indented code block handling,
      and parser fidelity assertions for heading boundaries.
"""

from __future__ import annotations

import pytest

from owlbear_kanban.body_parser import parse_body, render_body


class TestFromAC_EOFUnclosedFence:
    """AC-1: unclosed fenced blocks remain content and preserve fidelity."""

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
            # Setext-style heading content inside unclosed fence (AC-1 refinement):
            # in_fence guard fires before setext detector — both heading variants
            # must remain plain content, not create new sections.
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
        """Heading-like fence content must not become sections; content stays exact."""
        sections = parse_body(markdown)
        headings = [sec.heading for sec in sections if sec.heading]

        assert headings == ["Real Section"]
        assert len(sections) == 1
        assert sections[0].content == expected_content
        assert parse_body(render_body(sections)) == sections


class TestFromAC_TabIndentedCode:
    """AC-2: tab-indented heading-like lines remain plain content."""

    def test_ac2_tab_indented_heading_like_line_is_not_section_and_is_verbatim(self) -> None:
        """Tab-indented heading-like lines must remain content with tab preserved."""
        md = "## Real\n\n\t## Heading-like\n\tline two\n\nafter\n"

        sections = parse_body(md)
        headings = [sec.heading for sec in sections if sec.heading]

        assert headings == ["Real"]
        assert len(sections) == 1
        assert sections[0].content == "\n\t## Heading-like\n\tline two\n\nafter\n"
