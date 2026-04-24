"""C-15 — predicates CommonMark compliance (GREEN phase).

Task: #1060 (Brief C #1043) — paper-c.md §6, §6.1
AC:   C39, C40, C41

These tests target CommonMark parsing precision gaps that require
``markdown-it-py`` AST parsing (AC-C40/C41 refined by arch review cycle 5).

Earlier tests (rounds 1-4) fixed specific regex edge cases.  The
remaining substrate contract requires that the implementation uses
``markdown-it-py`` and checks for ``bullet_list_open`` /
``ordered_list_open`` tokens — not a hand-rolled regex.  Three cases
prove this:

* CommonMark thematic breaks (``* * *``, ``- - -``) emit ``hr`` tokens;
  no regex matching ``^[-*+] `` can distinguish them from list items.
* A list inside a blockquote (``> - item``) emits ``bullet_list_open``
  inside a ``blockquote_open`` in the flat token stream; a line-start
  regex anchored at ``^ {0,3}`` cannot match the ``>`` prefix.

AC-C39 is verified by #1051 tests (``serve/kanban/tests/test_predicates.py``).
"""

from __future__ import annotations

from owlbear_kanban.models import Section, Task
from owlbear_kanban.predicates import require_list_in_section


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_section(heading: str | None, level: int, content: str) -> Section:
    return Section(heading=heading, level=level, content=content)


def _make_task(sections: list[Section]) -> Task:
    return Task(
        id=1060,
        title="predicate-commonmark-test",
        status="todo",
        priority="important",
        created="2026-04-23T00:00:00+00:00",
        updated="2026-04-23T00:00:00+00:00",
        body=sections,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# TestFromAC_PredicateCommonMarkSubstrate
# ---------------------------------------------------------------------------


class TestFromAC_PredicateCommonMarkSubstrate:
    """AC-C40: require_list_in_section parses to a CommonMark bullet_list or ordered_list.

    The AC uses CommonMark AST node names which require a proper CommonMark
    parser (e.g. markdown-it-py) rather than a hand-rolled regex.  The tests
    below expose cases where the current regex-based helper diverges from the
    CommonMark spec.
    """

    # ------------------------------------------------------------------
    # Happy path: ')' delimiter ordered list
    # ------------------------------------------------------------------

    def test_ac_c40_ordered_paren_delimiter_is_ordered_list(self) -> None:
        """AC-C40: '1) item' is a CommonMark ordered_list — must return True.

        CommonMark spec §5.3: an ordered list marker is one or more digits
        followed by '.' OR ')'.  The current regex ``\\d+\\.`` only matches
        '.'.  A CommonMark parser (markdown-it-py) emits an ``ordered_list``
        token for '1) First', satisfying AC-C40.
        """
        task = _make_task(
            [_make_section("Steps", 2, "1) First step\n2) Second step\n")]
        )
        assert require_list_in_section(task, "Steps") is True

    def test_ac_c40_ordered_paren_delimiter_multi_digit_is_ordered_list(self) -> None:
        """AC-C40: multi-digit '99) item' with ')' delimiter is still ordered_list.

        Boundary: CommonMark allows 1-9 digits before the list delimiter.
        The ')' delimiter path must be handled regardless of digit count.
        """
        task = _make_task([_make_section("Items", 2, "99) First\n100) Second\n")])
        # Note: 100 is 3 digits — still within CommonMark 1-9 digit limit.
        # Main failure driver is ')' delimiter not matching current regex.
        assert require_list_in_section(task, "Items") is True

    def test_ac_c40_paren_ordered_list_after_fenced_block(self) -> None:
        """AC-C40: fenced content excluded; ')' ordered list after fence counts.

        Existing fence-exclusion logic is correct, but '1) real item' after
        the closing fence is missed by the current ``\\d+\\.`` regex.  A
        CommonMark parser would emit an ordered_list token for it.
        """
        content = "```\n1. fake inside fence\n```\n1) real item after fence\n"
        task = _make_task([_make_section("Steps", 2, content)])
        assert require_list_in_section(task, "Steps") is True

    # ------------------------------------------------------------------
    # Edge: indented code blocks masquerading as lists
    # ------------------------------------------------------------------

    def test_ac_c40_four_space_indent_is_indented_code_block_not_list(self) -> None:
        """AC-C40: four-space-indented line is a CommonMark indented code block, not bullet_list.

        CommonMark spec §4.4: four or more spaces of indentation create an
        indented code block.  '    - item' is therefore a code block
        containing '- item' verbatim — no bullet_list node is emitted.
        The current regex ``^[ \\t]*[-*+] `` matches the leading spaces and
        falsely returns True.
        """
        task = _make_task(
            [_make_section("Steps", 2, "    - item inside indented code block\n")]
        )
        assert require_list_in_section(task, "Steps") is False

    def test_ac_c40_tab_indent_is_indented_code_block_not_list(self) -> None:
        """AC-C40: tab-indented line equals 4-space indent — indented code block, not bullet_list.

        CommonMark spec §2.2: a Tab at the start of a line expands to the
        next 4-space tab stop, so '\\t- item' is equivalent to '    - item'
        and must be treated as an indented code block, not a list item.
        The current regex ``^[ \\t]*[-*+] `` matches the leading tab and
        falsely returns True.
        """
        task = _make_task(
            [_make_section("Steps", 2, "\t- item inside tab-indented code block\n")]
        )
        assert require_list_in_section(task, "Steps") is False

    def test_ac_c40_four_space_indent_ordered_is_code_block_not_list(self) -> None:
        """AC-C40: four-space-indented ordered-list-like line is also a code block.

        '    1. item' looks like an ordered list but is a CommonMark indented
        code block.  The current regex matches leading spaces before '\\d+\\.' .
        A CommonMark parser must return False.
        """
        task = _make_task(
            [_make_section("Steps", 2, "    1. item inside indented code block\n")]
        )
        assert require_list_in_section(task, "Steps") is False

    # ------------------------------------------------------------------
    # Edge: fence variants — indented fences and longer opening lengths
    # ------------------------------------------------------------------

    def test_ac_c40_three_space_indented_fence_excludes_content(self) -> None:
        """AC-C40: 3-space-indented fences are valid CommonMark fences; content is excluded.

        CommonMark spec §4.5: a fenced code block may be indented up to 3
        spaces.  '   ```' is therefore a valid fence opener and its content
        must not be treated as a list.  The current ``_FENCE_RE`` is anchored
        at column 0 only and does not recognise a 3-space-indented opener, so
        the list-like line inside the fence leaks into list detection and the
        predicate incorrectly returns True.
        """
        content = "   ```\n- fake inside 3-space-indented fence\n   ```\n"
        task = _make_task([_make_section("Steps", 2, content)])
        assert require_list_in_section(task, "Steps") is False

    def test_ac_c40_four_backtick_fence_not_closed_by_three_backtick(self) -> None:
        """AC-C40: a 4-backtick fence opener must only close with 4+ backticks.

        CommonMark spec §4.5: the closing fence must consist of at least as
        many backticks as the opening fence.  A ``` line does not close a
        ```` fence.  The current ``_remove_fenced_blocks`` stores only the
        fence character (not length) and therefore closes a ```` opener on
        any ``` line, leaking the subsequent content into list detection and
        producing a spurious True result.
        """
        content = "````\n- hidden inside 4-backtick fence\n```\n- still inside fence (not leaked)\n````\n"
        task = _make_task([_make_section("Steps", 2, content)])
        assert require_list_in_section(task, "Steps") is False

    def test_ac_c40_four_tilde_fence_not_closed_by_three_tilde(self) -> None:
        """AC-C40: a 4-tilde fence opener must only close with 4+ tildes.

        CommonMark spec §4.5: same minimum-length rule applies to tilde
        fences.  The current ``_remove_fenced_blocks`` prematurely closes a
        ~~~~ opener on a ~~~ line, causing list items after the premature
        close to leak into detection.
        """
        content = "~~~~\n- hidden inside 4-tilde fence\n~~~\n- still inside fence (not leaked)\n~~~~\n"
        task = _make_task([_make_section("Steps", 2, content)])
        assert require_list_in_section(task, "Steps") is False

    def test_ac_c40_three_space_indented_fence_close_resumes_list_detection(
        self,
    ) -> None:
        """AC-C40: list detection resumes after a valid 3-space-indented fence closes.

        CommonMark spec §4.5: both opener and closer may be indented up to 3
        spaces.  Content after the closing fence is ordinary paragraph/list
        content and must be classified normally.  This proves the
        indented-fence close + post-fence resume branch:
        ``require_list_in_section`` must return True when a real list item
        follows a matched 3-space-indented close.

        Regression guard: ``_FENCE_RE`` accepts 0-3 indent on the opener and
        the closing regex in ``_remove_fenced_blocks`` also accepts 0-3
        indent, so the fence is stripped and the post-fence list item is
        detected.
        """
        content = (
            "   ```\n- inside fence (excluded)\n   ```\n- real list item after close\n"
        )
        task = _make_task([_make_section("Steps", 2, content)])
        assert require_list_in_section(task, "Steps") is True

    # ------------------------------------------------------------------
    # Substrate rejection: cases that prove markdown-it-py is required
    # (AC-C41 refined: regex-based list detection is prohibited)
    # ------------------------------------------------------------------

    def test_ac_c41_substrate_thematic_break_asterisks_is_not_list(self) -> None:
        """AC-C41 substrate: '* * *' is a CommonMark thematic break, not a list.

        CommonMark spec §4.1: three or more matching *, -, or _ characters
        (each optionally followed by spaces/tabs) form a thematic break.
        ``markdown-it-py`` emits an ``hr`` token — no ``bullet_list_open``.

        A regex matching ``^[-*+] `` at column 0 returns True for ``* * *``
        because ``* `` appears at the start; AST parsing returns False.
        This proves the implementation substrate must be ``markdown-it-py``.
        """
        task = _make_task([_make_section("Steps", 2, "* * *\n")])
        assert require_list_in_section(task, "Steps") is False

    def test_ac_c41_substrate_thematic_break_dashes_is_not_list(self) -> None:
        """AC-C41 substrate: '- - -' is a CommonMark thematic break, not a list.

        CommonMark spec §4.1: ``- - -`` (three dashes separated by spaces)
        is a thematic break, not a bullet list item.  ``markdown-it-py``
        emits ``hr``, not ``bullet_list_open``.

        A regex matching ``^[-*+] `` at column 0 returns True for ``- - -``
        because ``- `` appears at the start; AST parsing returns False.
        This proves the implementation substrate must be ``markdown-it-py``.
        """
        task = _make_task([_make_section("Steps", 2, "- - -\n")])
        assert require_list_in_section(task, "Steps") is False

    def test_ac_c41_substrate_list_in_blockquote_is_detected(self) -> None:
        """AC-C41 substrate: a list inside a blockquote emits bullet_list_open.

        CommonMark spec §5.1: a blockquote can contain a bullet list.
        ``markdown-it-py`` emits ``blockquote_open`` then ``bullet_list_open``
        in the flat token stream, so the predicate must return True.

        A line-start regex anchored at ``^ {0,3}[-*+] `` does not match
        ``> - item`` because ``>`` is not a space; regex returns False.
        AST parsing returns True, proving the substrate must be
        ``markdown-it-py``.
        """
        task = _make_task([_make_section("Steps", 2, "> - item inside blockquote\n")])
        assert require_list_in_section(task, "Steps") is True
