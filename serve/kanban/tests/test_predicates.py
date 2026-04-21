"""TDD RED: C-06 — predicate tests.

Task: #1051 (Brief C #1043) — paper-c.md §8.8
AC:   C39, C40, C41
All tests FAIL (RED phase — predicates module not yet implemented with Section-based substrate).
"""

from __future__ import annotations

import pytest

from owlbear_kanban.predicates import (  # NEW module — ImportError in RED
    required_sections,
    require_list_in_section,
)
from owlbear_kanban.storage import Section  # NEW type — ImportError in RED
from owlbear_kanban.models import Task, BoardConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sections(*args: tuple[str | None, int, str]) -> list[Section]:
    """Build a list[Section] from (heading, level, content) tuples."""
    return [Section(heading=h, level=lv, content=c) for h, lv, c in args]


def _make_task_with_sections(sections: list[Section]) -> Task:
    """Return a minimal Task with the given Section list as its body."""
    return Task(
        id=1,
        title="test",
        status="todo",
        priority="needed",
        created="2026-04-21T10:00:00+00:00",
        updated="2026-04-21T10:00:00+00:00",
        body=sections,  # type: ignore[arg-type]  # brief C Task.body = list[Section]
    )


# ---------------------------------------------------------------------------
# TestFromAC_RequiredSections — AC-C39, AC-C41
# ---------------------------------------------------------------------------


class TestFromAC_RequiredSections:
    """AC-C39, AC-C41: required_sections predicate — case-insensitive, whitespace-stripped."""

    def test_ac_c39_exact_match_returns_true(self) -> None:
        """AC-C39: exact heading match passes."""
        task = _make_task_with_sections(
            _make_sections(("Acceptance Criteria", 2, "- item\n"))
        )
        assert required_sections(task, ["Acceptance Criteria"]) is True

    def test_ac_c39_case_insensitive_match(self) -> None:
        """AC-C39: heading match is case-insensitive."""
        task = _make_task_with_sections(
            _make_sections(("ACCEPTANCE CRITERIA", 2, "- item\n"))
        )
        assert required_sections(task, ["acceptance criteria"]) is True

    def test_ac_c39_mixed_case_match(self) -> None:
        """AC-C39: 'Tests' matches 'tests', 'TESTS', '  Tests  '."""
        task = _make_task_with_sections(
            _make_sections(("Tests", 2, "- test one\n"))
        )
        assert required_sections(task, ["tests"]) is True
        assert required_sections(task, ["TESTS"]) is True
        assert required_sections(task, ["  Tests  "]) is True

    def test_ac_c39_whitespace_stripped_from_query(self) -> None:
        """AC-C39: surrounding whitespace stripped from the required section name."""
        task = _make_task_with_sections(
            _make_sections(("Notes", 2, "some notes\n"))
        )
        assert required_sections(task, ["  Notes  "]) is True

    def test_ac_c39_whitespace_stripped_from_section_heading(self) -> None:
        """AC-C39: surrounding whitespace stripped from Section.heading in comparison."""
        task = _make_task_with_sections(
            _make_sections(("  Notes  ", 2, "some notes\n"))
        )
        assert required_sections(task, ["Notes"]) is True

    def test_ac_c39_missing_section_returns_false(self) -> None:
        """AC-C39: required section not present → returns False."""
        task = _make_task_with_sections(
            _make_sections(("Other Section", 2, "content\n"))
        )
        assert required_sections(task, ["Tests"]) is False

    def test_ac_c39_multiple_required_all_present(self) -> None:
        """AC-C39: all required sections present → True."""
        task = _make_task_with_sections([
            Section(heading="Acceptance Criteria", level=2, content="- ac\n"),
            Section(heading="Tests", level=2, content="- test\n"),
        ])
        assert required_sections(task, ["Acceptance Criteria", "Tests"]) is True

    def test_ac_c39_multiple_required_one_missing(self) -> None:
        """AC-C39: one required section absent → False."""
        task = _make_task_with_sections(
            _make_sections(("Acceptance Criteria", 2, "- ac\n"))
        )
        assert required_sections(task, ["Acceptance Criteria", "Tests"]) is False

    def test_ac_c39_empty_required_list_returns_true(self) -> None:
        """AC-C39: no required sections → always passes."""
        task = _make_task_with_sections([])
        assert required_sections(task, []) is True

    def test_ac_c39_preamble_section_heading_none_not_matched(self) -> None:
        """AC-C39: preamble (heading=None) does not satisfy any named required section."""
        task = _make_task_with_sections(
            _make_sections((None, 0, "intro text"))
        )
        assert required_sections(task, ["intro text"]) is False

    def test_ac_c41_no_space_heading_is_content_not_matched(self) -> None:
        """AC-C41: '##NotASection' in content is NOT a section heading; predicate fails."""
        # A Section whose content includes ##NotASection verbatim (per AC-C7)
        task = _make_task_with_sections([
            Section(
                heading="Parent",
                level=2,
                content="##NotASection\nsome text\n",
            )
        ])
        # Looking for 'NotASection' as a heading should fail
        assert required_sections(task, ["NotASection"]) is False


# ---------------------------------------------------------------------------
# TestFromAC_RequireListInSection — AC-C40, AC-C41
# ---------------------------------------------------------------------------


class TestFromAC_RequireListInSection:
    """AC-C40, AC-C41: require_list_in_section contract."""

    def test_ac_c40_bullet_list_in_section_returns_true(self) -> None:
        """AC-C40: section with bullet list content → True."""
        task = _make_task_with_sections(
            _make_sections(("Tests", 2, "- test one\n- test two\n"))
        )
        assert require_list_in_section(task, "Tests") is True

    def test_ac_c40_ordered_list_in_section_returns_true(self) -> None:
        """AC-C40: section with ordered list content → True."""
        task = _make_task_with_sections(
            _make_sections(("Steps", 2, "1. first\n2. second\n"))
        )
        assert require_list_in_section(task, "Steps") is True

    def test_ac_c40_section_with_prose_only_returns_false(self) -> None:
        """AC-C40: section with prose content (no list) → False."""
        task = _make_task_with_sections(
            _make_sections(("Notes", 2, "Just some prose text.\nAnother line.\n"))
        )
        assert require_list_in_section(task, "Notes") is False

    def test_ac_c40_empty_section_content_returns_false(self) -> None:
        """AC-C40: empty section content → False."""
        task = _make_task_with_sections(
            _make_sections(("Tests", 2, ""))
        )
        assert require_list_in_section(task, "Tests") is False

    def test_ac_c40_section_lookup_case_insensitive(self) -> None:
        """AC-C40: heading lookup for require_list_in_section is case-insensitive."""
        task = _make_task_with_sections(
            _make_sections(("TESTS", 2, "- item\n"))
        )
        assert require_list_in_section(task, "tests") is True
        assert require_list_in_section(task, "Tests") is True

    def test_ac_c40_section_lookup_whitespace_stripped(self) -> None:
        """AC-C40: whitespace stripped in require_list_in_section heading lookup."""
        task = _make_task_with_sections(
            _make_sections(("Tests", 2, "- item\n"))
        )
        assert require_list_in_section(task, "  Tests  ") is True

    def test_ac_c40_section_not_present_returns_false(self) -> None:
        """AC-C40: section name not found → False (not an error)."""
        task = _make_task_with_sections(
            _make_sections(("Other", 2, "- item\n"))
        )
        assert require_list_in_section(task, "Tests") is False

    def test_ac_c40_list_inside_code_fence_not_counted(self) -> None:
        """AC-C40: list-like lines inside code fence are NOT a CommonMark list."""
        content = "```\n- fake list\n1. also fake\n```\n"
        task = _make_task_with_sections(
            _make_sections(("Code", 2, content))
        )
        assert require_list_in_section(task, "Code") is False

    def test_ac_c41_no_space_heading_does_not_satisfy_require_list(self) -> None:
        """AC-C41: '##ListSection' in content (not a heading) can't satisfy require_list_in_section."""
        task = _make_task_with_sections([
            Section(
                heading="Parent",
                level=2,
                content="##ListSection\n- item\n",
            )
        ])
        # 'ListSection' is NOT a heading (no space after ##)
        assert require_list_in_section(task, "ListSection") is False

    def test_ac_c41_semantic_equivalence_to_brief_b_d64(self) -> None:
        """AC-C41: structured predicate matches the Brief B D64 regex semantics."""
        # Under the old regex, '## Tests' heading + a list item satisfied the gate.
        # Under the new substrate, the same logical structure must satisfy the gate.
        task = _make_task_with_sections([
            Section(heading=None, level=0, content=""),
            Section(heading="Acceptance Criteria", level=2, content="- ac line\n"),
            Section(heading="Tests", level=2, content="- test case 1\n- test case 2\n"),
        ])
        assert required_sections(task, ["Acceptance Criteria", "Tests"]) is True
        assert require_list_in_section(task, "Tests") is True
