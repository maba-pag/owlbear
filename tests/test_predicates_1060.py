"""C-15 — predicates CommonMark compliance (GREEN phase).

Task: #1060 (Brief C #1043) — paper-c.md §6, §6.1
AC:   C39, C40, C41

These tests target CommonMark parsing precision gaps in the existing
regex-based ``_has_list_outside_fences`` helper:

* AC-C40 uses AST node terminology (``bullet_list``, ``ordered_list``).
  The ')' delimiter is a valid CommonMark ordered-list marker that the
  current ``\\d+\\.`` regex does not recognise.
* AC-C40 requires CommonMark parsing semantics: 4-space-indented and
  tab-indented lines are indented code blocks per CommonMark, NOT
  bullet_list or ordered_list nodes — even though the current regex
  matches them via ``^[ \\t]*[-*+] ``.

AC-C39 and AC-C41 are already verified by #1051 tests
(``serve/kanban/tests/test_predicates.py``); the "All RED tests from
C-06 (#1051) pass" AC item requires no additional failing tests here.
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
        task = _make_task(
            [_make_section("Items", 2, "99) First\n100) Second\n")]
        )
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
