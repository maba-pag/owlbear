"""RED phase tests — MCP end_work fail outcome and lifecycle contract reconciliation (#1339).

Acceptance Criteria coverage:
  AC1: end_work handler accepts outcome="fail" and routes to engine.end_work(outcome="fail")
  AC2: end_work handler still accepts outcome="release"
  AC3: h-mcp-kanban/SKILL.md Tool Summary table lists 9 tools (add create_dr row)
  AC4: h-mcp-kanban/SKILL.md outcome documentation lists all 5 outcomes
  AC5: mcp-kanban/README.md matches (9 tools, 5 outcomes documented)
"""

from __future__ import annotations

import typing
from pathlib import Path

import pytest
import owlbear_mcp_kanban.server as _server_module

# ---------------------------------------------------------------------------
# Paths to doc files under test
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_MD = _REPO_ROOT / "share" / "skills" / "h-mcp-kanban" / "SKILL.md"
_README_MD = _REPO_ROOT / "serve" / "mcp-kanban" / "README.md"


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkFailOutcome
# AC1: MCP server end_work handler accepts outcome="fail" and routes correctly.
#
# The outcome parameter is currently typed as
# Literal["success", "block", "reject", "release"] — "fail" is absent.
# The MCP schema exposes this Literal as an enum to clients, blocking "fail".
# Tests verify that after the fix:
#   - the type annotation includes "fail" (evaluated via get_type_hints)
#   - the FastMCP tool JSON schema exposes "fail" as a valid enum value
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkFailOutcome:
    """end_work handler accepts outcome='fail' — annotation and schema (AC1)."""

    def test_end_work_outcome_type_hint_includes_fail(self) -> None:
        """outcome parameter's resolved type hint must include 'fail'.

        server.py uses ``from __future__ import annotations``, so annotations
        are stored as strings (PEP 563).  ``typing.get_type_hints()`` evaluates
        them in the module's globals, restoring the live Literal type.
        Currently Literal["success", "block", "reject", "release"] — "fail" absent.
        After builder fix: 'fail' is in the Literal args.
        """
        # get_type_hints resolves PEP 563 string annotations
        try:
            hints = typing.get_type_hints(_server_module.end_work)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"get_type_hints(end_work) raised: {exc}")
        outcome_hint = hints.get("outcome")
        assert outcome_hint is not None, "'outcome' not found in end_work type hints"
        args = typing.get_args(outcome_hint)
        assert "fail" in args, (
            f"'fail' not in end_work outcome hint. "
            f"Current Literal args: {args!r}. "
            f"Expected all 5: success, fail, reject, block, release."
        )

    def test_end_work_outcome_type_hint_has_exactly_five_valid_values(
        self,
    ) -> None:
        """outcome type hint must enumerate exactly 5 values including 'fail'.

        The count provides an additional guard: if the builder forgets to add
        'fail' but happens to have 4 other values, this test fails independently.
        Currently 4 values \u2014 adding 'fail' brings it to 5.
        """
        try:
            hints = typing.get_type_hints(_server_module.end_work)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"get_type_hints(end_work) raised: {exc}")
        outcome_hint = hints.get("outcome")
        args = typing.get_args(outcome_hint) if outcome_hint else ()
        expected_count = 5
        assert len(args) == expected_count, (
            f"outcome Literal must have {expected_count} values (currently {len(args)}). "
            f"Current args: {args!r}. "
            f"After fix: ('success', 'fail', 'reject', 'block', 'release')."
        )


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkOutcomeSpec
# AC1 (boundary) + AC2 (regression): The resolved type hint must include BOTH
# "fail" AND "release". Currently "fail" is absent.
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkOutcomeSpec:
    """outcome type hint contains all 5 outcomes: success, fail, reject, block, release."""

    def test_end_work_outcome_type_hint_includes_all_five_outcomes(self) -> None:
        """Resolved type hint must include all 5 outcomes (AC1 + AC2 regression).

        Currently missing 'fail'. Also verifies 'release' is not accidentally
        removed when 'fail' is added (AC2 regression guard).
        """
        try:
            hints = typing.get_type_hints(_server_module.end_work)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"get_type_hints(end_work) raised: {exc}")
        outcome_hint = hints.get("outcome")
        actual_args = set(typing.get_args(outcome_hint)) if outcome_hint else set()
        expected = {"success", "fail", "reject", "block", "release"}
        missing = expected - actual_args
        assert not missing, (
            f"outcome type hint is missing outcomes: {sorted(missing)}. "
            f"Current resolved args: {sorted(actual_args)!r}"
        )

    def test_end_work_outcome_type_hint_retains_release_after_fail_added(self) -> None:
        """'release' must remain in the outcome type hint after 'fail' is added (AC2).

        Regression guard: adding 'fail' to the Literal must not remove 'release'.
        This test currently fails because 'fail' is absent — asserting the full
        set of 5 means the presence of 'release' alone is insufficient.
        """
        try:
            hints = typing.get_type_hints(_server_module.end_work)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"get_type_hints(end_work) raised: {exc}")
        outcome_hint = hints.get("outcome")
        actual_args = set(typing.get_args(outcome_hint)) if outcome_hint else set()
        # Require that BOTH are present — absence of 'fail' causes this to fail
        assert {"fail", "release"}.issubset(actual_args), (
            f"outcome type hint must include both 'fail' and 'release'. "
            f"Current resolved args: {sorted(actual_args)!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SkillDocToolCount
# AC3: h-mcp-kanban/SKILL.md Tool Summary table lists 9 tools (add create_dr).
# Currently: "Exactly 8 tools" — create_dr row is missing.
# ---------------------------------------------------------------------------


class TestFromAC_SkillDocToolCount:
    """SKILL.md Tool Summary must declare 9 tools and include create_dr (AC3)."""

    def _skill_text(self) -> str:
        assert _SKILL_MD.exists(), f"SKILL.md not found at {_SKILL_MD}"
        return _SKILL_MD.read_text(encoding="utf-8")

    def test_skill_md_tool_summary_declares_nine_tools(self) -> None:
        """SKILL.md must state '9 tools', not '8 tools', in the Tool Summary section.

        Currently reads 'Exactly 8 tools are exposed:'.
        """
        text = self._skill_text()
        # Find the Tool Summary section
        tool_summary_idx = text.lower().find("## tool summary")
        assert tool_summary_idx != -1, "Tool Summary section not found in SKILL.md"
        # Look in the section for a tool count
        section_text = text[tool_summary_idx : tool_summary_idx + 500]
        assert "9" in section_text, (
            f"Expected '9' in Tool Summary section, but found:\n{section_text!r}\n"
            "SKILL.md still says '8 tools' — create_dr row not yet added."
        )
        assert "8" not in section_text or "9" in section_text, (
            "SKILL.md still declares '8 tools' instead of '9'."
        )

    def test_skill_md_tool_table_includes_create_dr_row(self) -> None:
        """SKILL.md Tool Summary table must include a row for create_dr.

        Currently the table has 8 rows (list_tasks through end_work) but
        omits create_dr. After the fix, create_dr must appear in the table.
        """
        text = self._skill_text()
        tool_summary_idx = text.lower().find("## tool summary")
        assert tool_summary_idx != -1, "Tool Summary section not found in SKILL.md"
        # Look for the table region (ends at the next ## heading)
        next_section = text.find("\n## ", tool_summary_idx + 10)
        table_text = (
            text[tool_summary_idx:next_section]
            if next_section != -1
            else text[tool_summary_idx:]
        )
        assert "`create_dr`" in table_text or "create_dr" in table_text, (
            f"'create_dr' not found in SKILL.md Tool Summary table.\n"
            f"Table region:\n{table_text!r}\n"
            "The create_dr row is missing from the 9-tool table."
        )


# ---------------------------------------------------------------------------
# TestFromAC_SkillDocEndWorkOutcomes
# AC4: h-mcp-kanban/SKILL.md end_work section documents all 5 outcomes.
# Currently the 'end_work' compound-tool section lists 4 outcomes:
# success, reject, release, block — "fail" is absent.
# ---------------------------------------------------------------------------


class TestFromAC_SkillDocEndWorkOutcomes:
    """SKILL.md end_work section must document all 5 outcomes including 'fail' (AC4)."""

    def _skill_text(self) -> str:
        assert _SKILL_MD.exists(), f"SKILL.md not found at {_SKILL_MD}"
        return _SKILL_MD.read_text(encoding="utf-8")

    def _end_work_section(self) -> str:
        text = self._skill_text()
        # Find the "### end_work" compound-tool heading specifically
        idx = text.find("### end_work")
        if idx == -1:
            # Fall back to any end_work heading
            idx = text.find("## end_work")
        assert idx != -1, "'### end_work' heading not found in SKILL.md"
        # Capture from the heading onward until the next heading at same or higher level
        next_section = text.find("\n## ", idx + 10)
        next_subsection = text.find("\n### ", idx + 10)
        # Stop at whichever comes first
        end = (
            min(x for x in [next_section, next_subsection] if x != -1)
            if (next_section != -1 or next_subsection != -1)
            else len(text)
        )
        return text[idx:end]

    def test_skill_md_end_work_section_documents_fail_outcome(self) -> None:
        """SKILL.md end_work Outcome table must have 'fail' as a table-row entry.

        Currently the table has 4 rows (success, reject, release, block) but
        omits 'fail'. After the fix, '`fail`' must appear as a Markdown table
        cell in the Outcome table within the ### end_work section.
        """
        section = self._end_work_section()
        # Look for 'fail' as a Markdown table row cell (| `fail` | or | fail |)
        # Plain substring "fail" would match "On failure: raises ToolError" — too loose.
        has_fail_row = "| `fail`" in section or "| fail " in section
        assert has_fail_row, (
            f"'| `fail`' table row not found in SKILL.md end_work Outcome table.\n"
            f"Only substring check for raw 'fail' would wrongly match 'failure'.\n"
            f"Section:\n{section!r}\n"
            "Expected an explicit | `fail` | row in the Outcome table."
        )

    def test_skill_md_end_work_section_documents_all_five_outcomes(self) -> None:
        """SKILL.md end_work Outcome table must have all 5 outcome rows (AC4).

        Each outcome must appear as a Markdown table row (| `outcome` |).
        Currently 'fail' is absent as a row — matching 'failure' text is insufficient.
        """
        section = self._end_work_section()

        def _has_row(outcome: str) -> bool:
            return f"| `{outcome}`" in section or f"| {outcome} |" in section

        required = ["success", "fail", "reject", "block", "release"]
        missing_rows = [o for o in required if not _has_row(o)]
        assert not missing_rows, (
            f"SKILL.md end_work Outcome table is missing rows for: {missing_rows}.\n"
            f"Section:\n{section!r}"
        )

    def test_skill_md_fail_outcome_has_use_when_guidance(self) -> None:
        """'fail' row in SKILL.md must include actionable use-when guidance.

        The 5-outcome table row for 'fail' must carry a non-empty behaviour
        description — not just the word 'fail' from surrounding prose.
        """
        section = self._end_work_section()
        # Find a table row starting with | `fail`
        fail_row_idx = section.find("| `fail`")
        assert fail_row_idx != -1, (
            "| `fail` | row not found in SKILL.md end_work Outcome table.\n"
            f"Section:\n{section!r}"
        )
        # The row should have at least one more cell with content
        row_line = section[fail_row_idx : section.find("\n", fail_row_idx)]
        cells = [c.strip() for c in row_line.split("|") if c.strip()]
        assert len(cells) >= 2, (  # noqa: PLR2004
            f"'fail' table row has only one cell. Row: {row_line!r}"
        )
        behaviour_cell = cells[1] if len(cells) > 1 else ""
        assert len(behaviour_cell) > 5, (  # noqa: PLR2004
            f"'fail' table row has no meaningful behaviour description. Row: {row_line!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ReadmeEndWorkOutcomes
# AC5: mcp-kanban/README.md end_work Outcomes section must document all 5 outcomes.
# Currently lists 4: success, reject, release, block — "fail" absent.
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeEndWorkOutcomes:
    """mcp-kanban README.md end_work outcomes must document all 5 outcomes (AC5)."""

    def _readme_text(self) -> str:
        assert _README_MD.exists(), f"README.md not found at {_README_MD}"
        return _README_MD.read_text(encoding="utf-8")

    def _outcomes_section(self) -> str:
        text = self._readme_text()
        # Find "end_work Outcomes" section
        idx = text.lower().find("end_work outcomes")
        if idx == -1:
            idx = text.lower().find("## end_work")
        assert idx != -1, "'end_work Outcomes' section not found in README.md"
        next_section = text.find("\n## ", idx + 10)
        return text[idx:next_section] if next_section != -1 else text[idx:]

    def test_readme_end_work_outcomes_section_includes_fail(self) -> None:
        """README.md end_work Outcomes section must include 'fail'.

        Currently lists: success, reject, release, block.
        'fail' is missing. After builder fix: all 5 must be present.
        """
        section = self._outcomes_section()
        assert "fail" in section.lower(), (
            f"'fail' not found in README.md end_work Outcomes section.\n"
            f"Section:\n{section!r}\n"
            "Expected all 5: success, fail, reject, block, release."
        )

    def test_readme_end_work_documents_all_five_outcomes(self) -> None:
        """README.md end_work Outcomes section must document all 5 outcomes (AC5)."""
        section = self._outcomes_section()
        required = {"success", "fail", "reject", "block", "release"}
        missing = [o for o in sorted(required) if o not in section.lower()]
        assert not missing, (
            f"README.md end_work Outcomes section is missing: {missing}.\n"
            f"Section:\n{section!r}"
        )

    def test_readme_end_work_fail_outcome_has_description(self) -> None:
        """'fail' in README.md end_work section must be a documented entry.

        Not just a mention — it must appear as a distinct outcome with at least
        a brief use-case description, consistent with the other outcomes.
        """
        section = self._outcomes_section()
        fail_idx = section.lower().find("fail")
        assert fail_idx != -1, "'fail' not in README.md end_work section at all"
        # After the token, expect some prose or table structure
        surrounding = section[fail_idx : fail_idx + 150].lower()
        has_structure = (
            "|" in surrounding or "-" in surrounding or "record" in surrounding
        )
        assert has_structure, (
            f"'fail' in README.md end_work section has no associated description.\n"
            f"Context: {surrounding!r}"
        )
