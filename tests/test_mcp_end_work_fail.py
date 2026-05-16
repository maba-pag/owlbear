"""RED phase tests — MCP end_work fail outcome and lifecycle contract reconciliation (#1339).

Acceptance Criteria coverage:
  AC1: end_work handler accepts outcome="fail" and routes to engine.end_work(outcome="fail")
  AC2: end_work handler still accepts outcome="release"
  AC3: h-mcp-kanban/SKILL.md Tool Summary table lists 9 tools (add create_dr row)
       NOTE: AC3 was pre-satisfied — SKILL.md already says '9 tools' and has create_dr row.
             No RED tests; builder has no work for AC3.
  AC4: h-mcp-kanban/SKILL.md outcome documentation lists all 5 outcomes
  AC5: mcp-kanban/README.md matches (9 tools, 5 outcomes documented)
  AC8: _patch_params descriptions use 'JSON array', not 'comma-separated strings'
  AC9: schema-light — no hard-coded _STATUSES/_PRIORITIES enum constraints on list_tasks
  AC10: end_work.outcome description mentions all 5 lifecycle outcomes including 'release'
"""

from __future__ import annotations

import typing
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import owlbear_mcp_kanban.server as _server_module
from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, end_work

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
            f"outcome type hint is missing outcomes: {sorted(missing)}. Current resolved args: {sorted(actual_args)!r}"
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
            f"outcome type hint must include both 'fail' and 'release'. Current resolved args: {sorted(actual_args)!r}"
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
            f"SKILL.md end_work Outcome table is missing rows for: {missing_rows}.\nSection:\n{section!r}"
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
            f"| `fail` | row not found in SKILL.md end_work Outcome table.\nSection:\n{section!r}"
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
        assert not missing, f"README.md end_work Outcomes section is missing: {missing}.\nSection:\n{section!r}"

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
        has_structure = "|" in surrounding or "-" in surrounding or "record" in surrounding
        assert has_structure, (
            f"'fail' in README.md end_work section has no associated description.\nContext: {surrounding!r}"
        )


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _get_tool_props(tool_name: str) -> dict:
    """Return the JSON Schema 'properties' dict for a FastMCP tool."""
    import owlbear_mcp_kanban.server as _srv

    tool = next(t for t in _srv.mcp._tool_manager._tools.values() if t.name == tool_name)
    return tool.parameters.get("properties", {})


# ---------------------------------------------------------------------------
# TestFromAC_PatchParamsJsonArrayDoc
# AC8: _patch_params descriptions must NOT say "Comma-separated" for parameters
#      that accept JSON arrays (list[int] / list[str]).
# Currently create_task and edit_task _patch_params carry "Comma-separated" text
# even though MCP transports JSON; agents must send arrays, not string scalars.
# ---------------------------------------------------------------------------


class TestFromAC_PatchParamsJsonArrayDoc:
    """AC8: patch_params descriptions use 'JSON array', not 'comma-separated'."""

    def test_create_task_depends_on_description_not_comma_separated(self) -> None:
        """create_task.depends_on description must not say 'Comma-separated'.

        Currently: 'Comma-separated dependency task IDs'.
        After fix: description uses 'JSON array' (matches list[int] type).
        """
        props = _get_tool_props("create_task")
        desc = props.get("depends_on", {}).get("description", "")
        assert "comma" not in desc.lower(), (
            f"create_task.depends_on still says 'comma-separated': {desc!r}. "
            "Must use 'JSON array' to match actual parameter type (list[int])."
        )

    def test_create_task_tags_description_not_comma_separated(self) -> None:
        """create_task.tags description must not say 'Comma-separated'.

        Currently: 'Comma-separated tags'.
        After fix: description uses 'JSON array' (matches list[str] type).
        """
        props = _get_tool_props("create_task")
        desc = props.get("tags", {}).get("description", "")
        assert "comma" not in desc.lower(), (
            f"create_task.tags still says 'comma-separated': {desc!r}. "
            "Must use 'JSON array' to match actual parameter type (list[str])."
        )

    def test_edit_task_add_dep_description_not_comma_separated(self) -> None:
        """edit_task.add_dep description must not say 'comma-separated'.

        Currently: "Add dependency task IDs (comma-separated, e.g. '601,602')".
        After fix: description uses 'JSON array' (matches list[int] type).
        """
        props = _get_tool_props("edit_task")
        desc = props.get("add_dep", {}).get("description", "")
        assert "comma" not in desc.lower(), (
            f"edit_task.add_dep still says 'comma-separated': {desc!r}. "
            "Must use 'JSON array' to match actual parameter type (list[int])."
        )

    def test_edit_task_remove_dep_description_not_comma_separated(self) -> None:
        """edit_task.remove_dep description must not say 'comma-separated'.

        Currently: "Remove dependency task IDs (comma-separated, e.g. '601,602')".
        After fix: description uses 'JSON array' (matches list[int] type).
        """
        props = _get_tool_props("edit_task")
        desc = props.get("remove_dep", {}).get("description", "")
        assert "comma" not in desc.lower(), (
            f"edit_task.remove_dep still says 'comma-separated': {desc!r}. "
            "Must use 'JSON array' to match actual parameter type (list[int])."
        )


# ---------------------------------------------------------------------------
# TestFromAC_SchemaLight
# AC9: _STATUSES/_PRIORITIES must not appear as hard-coded enum constraints
#      in the tool parameter schemas. The live board config is the authority;
#      hard-coded lists drift silently when config changes.
# Currently list_tasks.status and list_tasks.priority expose enum arrays.
# After fix (schema-light): no enum key; engine validates invalid values.
# ---------------------------------------------------------------------------


class TestFromAC_SchemaLight:
    """AC9: schema-light — no hard-coded _STATUSES/_PRIORITIES enums on list_tasks."""

    def test_list_tasks_status_has_no_enum_constraint(self) -> None:
        """list_tasks.status schema must not have a hard-coded enum constraint.

        Currently: enum: ['research', 'backlog', 'todo', 'in-progress', ...].
        After fix: no enum key — engine validates; agents use board config values.
        """
        status_schema = _get_tool_props("list_tasks").get("status", {})
        assert "enum" not in status_schema, (
            f"list_tasks.status still has hard-coded enum: {status_schema.get('enum')!r}. "
            "Remove enum to prevent drift from live board config (AC9 schema-light)."
        )

    def test_list_tasks_priority_has_no_enum_constraint(self) -> None:
        """list_tasks.priority schema must not have a hard-coded enum constraint.

        Currently: enum: ['someday', 'nice-to-have', 'important', 'needed', 'critical'].
        After fix: no enum key — engine validates; agents use board config values.
        """
        priority_schema = _get_tool_props("list_tasks").get("priority", {})
        assert "enum" not in priority_schema, (
            f"list_tasks.priority still has hard-coded enum: {priority_schema.get('enum')!r}. "
            "Remove enum to prevent drift from live board config (AC9 schema-light)."
        )


# ---------------------------------------------------------------------------
# TestFromAC_OutcomeDescriptionConsistency
# AC10: The lifecycle parameter matrix must be explicit and consistent.
# end_work.outcome _patch_params description currently reads:
#   "success = advance, fail = stay, block = mark blocked, reject = move back"
# — 'release' is absent. After the 5-outcome reconciliation, the description
# must mention all 5 outcomes so agents understand the full contract.
# ---------------------------------------------------------------------------


class TestFromAC_OutcomeDescriptionConsistency:
    """AC10: end_work.outcome description mentions all 5 lifecycle outcomes."""

    @staticmethod
    def _outcome_description() -> str:
        return _get_tool_props("end_work").get("outcome", {}).get("description", "")

    def test_end_work_outcome_description_includes_release(self) -> None:
        """end_work.outcome description must mention 'release'.

        Currently: 'success = advance, fail = stay, block = mark blocked, reject = move back'
        — 'release' is absent. After fix: all 5 outcomes appear in the description.
        """
        desc = self._outcome_description()
        assert "release" in desc.lower(), (
            f"end_work.outcome description does not mention 'release'.\n"
            f"Current description: {desc!r}\n"
            "Expected all 5 outcomes: success, fail, reject, block, release."
        )

    def test_end_work_outcome_description_includes_all_five_outcomes(self) -> None:
        """end_work.outcome description must mention all 5 lifecycle outcomes (AC10).

        Currently 'release' is absent from the description string.
        After fix: success, fail, reject, block, release are all present.
        """
        desc = self._outcome_description().lower()
        required = ["success", "fail", "reject", "block", "release"]
        missing = [o for o in required if o not in desc]
        assert not missing, (
            f"end_work.outcome description is missing outcomes: {missing}.\n"
            f"Current description: {self._outcome_description()!r}\n"
            "Update _patch_params for end_work to cover all 5 outcomes."
        )


# ---------------------------------------------------------------------------
# Runtime test infrastructure
# ---------------------------------------------------------------------------

_RUNTIME_CONFIG_YAML = """\
next_id: 1
"""


def _make_rt_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_RUNTIME_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_rt_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


@pytest.fixture()
def claimed_task_ctx(tmp_path: Path) -> AppContext:
    """AppContext with a single claimed task in 'in-progress'."""
    kanban_dir = _make_rt_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Runtime test task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_ReadmeOutcomeStructured
# AC11: README end_work Outcomes section must use bullet-list entries per outcome.
# Bare substring "fail" matches "failure" in prose — false-green risk.
# Structured "- `fail`" only matches a deliberate bullet-list entry.
# After builder fix: README uses "- `fail`: ..." bullet, so these tests PASS.
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeOutcomeStructured:
    """AC11 guard: README Outcomes section uses structured '- `outcome`' bullets."""

    def _outcomes_section(self) -> str:
        assert _README_MD.exists(), f"README.md not found at {_README_MD}"
        text = _README_MD.read_text(encoding="utf-8")
        idx = text.lower().find("end_work outcomes")
        assert idx != -1, "'end_work Outcomes' section not found in README.md"
        next_section = text.find("\n## ", idx + 10)
        return text[idx:next_section] if next_section != -1 else text[idx:]

    def test_readme_fail_is_bullet_entry_not_bare_substring(self) -> None:
        """'fail' must appear as '- `fail`' bullet, not generic prose (AC11 guard).

        '- `fail`' only matches a deliberate outcome bullet.
        'fail' (bare) would also match 'failure', 'failing', or any error prose.
        This test enforces the structured format the AC11 false-green guard requires.
        """
        section = self._outcomes_section()
        assert "- `fail`" in section, (
            f"'- `fail`' bullet entry not found in README end_work Outcomes section.\n"
            f"AC11: bare substring 'fail' would match 'failure' in prose — too loose.\n"
            f"Section:\n{section!r}"
        )

    def test_readme_all_five_outcomes_are_bullet_entries(self) -> None:
        """All 5 outcomes must appear as '- `outcome`' bullets in README (AC11 guard).

        Structured matching prevents false greens where 'reject' in a URL or
        'block' in a paragraph satisfies a bare-substring check.
        """
        section = self._outcomes_section()
        required = ["success", "fail", "reject", "block", "release"]
        missing = [o for o in required if f"- `{o}`" not in section]
        assert not missing, (
            f"README end_work Outcomes section missing '- `outcome`' bullets for: {missing}.\n"
            f"AC11: structured bullet format required to prevent false-green matches.\n"
            f"Section:\n{section!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkReleaseRuntime
# AC2 runtime proof: MCP end_work handler executes outcome='release' end-to-end.
# Proves the runtime path is reachable, not just the type hint.
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkReleaseRuntime:
    """AC2 runtime proof: end_work(outcome='release') executes without error."""

    @pytest.mark.asyncio
    async def test_end_work_release_returns_task_response(self, claimed_task_ctx: AppContext) -> None:
        """end_work(outcome='release') must return a task response on a claimed task.

        Proves the runtime path for 'release' is reachable end-to-end through
        the MCP handler → _invoke_view_end_work → engine.release_task().
        """
        result = await end_work(
            _make_rt_ctx(claimed_task_ctx),
            id="1",
            outcome="release",
            note=None,
        )
        assert result is not None
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_end_work_release_does_not_advance_status(self, claimed_task_ctx: AppContext) -> None:
        """end_work(outcome='release') must leave the task status unchanged.

        The task starts in 'in-progress'. Release unclaims it without advancing.
        """
        result = await end_work(
            _make_rt_ctx(claimed_task_ctx),
            id="1",
            outcome="release",
            note=None,
        )
        assert result.status == "in-progress"


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkSuccessMoveTo
# AC10 runtime proof: MCP end_work handler accepts outcome='success' + move_to.
# Proves the accepted 'success + move_to' path is reachable at runtime,
# consistent with the handbook/README documentation and the engine contract.
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkSuccessMoveTo:
    """AC10 runtime proof: end_work(outcome='success', move_to=...) executes correctly."""

    @pytest.mark.asyncio
    async def test_end_work_success_with_move_to_returns_task_response(self, claimed_task_ctx: AppContext) -> None:
        """end_work(outcome='success', move_to='done') must return a task response.

        Proves the runtime path for success+move_to is accepted end-to-end
        through the MCP handler → _invoke_view_end_work → engine.end_work().
        """
        result = await end_work(
            _make_rt_ctx(claimed_task_ctx),
            id="1",
            outcome="success",
            move_to="done",
            note=None,
        )
        assert result is not None
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_end_work_success_move_to_advances_to_specified_status(self, claimed_task_ctx: AppContext) -> None:
        """end_work(outcome='success', move_to='done') advances to 'done', not 'review'.

        Task starts in 'in-progress'. Default next is 'review'.
        With move_to='done', the task skips to 'done' directly.
        """
        result = await end_work(
            _make_rt_ctx(claimed_task_ctx),
            id="1",
            outcome="success",
            move_to="done",
            note=None,
        )
        assert result.status == "done"


# ---------------------------------------------------------------------------
# TestFromAC_BlockMoveToMatrix
# AC10 (refined): The move_to parameter matrix must be explicit and consistent.
# Specifically, the SKILL.md 'block' outcome row and the README 'block' bullet
# must document that move_to is optional on 'block'.
# Currently both omit any mention of move_to for 'block'.
# Builder fix: add "Optionally move to `move_to` status." to SKILL.md block row,
# and "optionally move to `move_to`" to README block bullet.
# ---------------------------------------------------------------------------


class TestFromAC_BlockMoveToMatrix:
    """AC10: SKILL.md and README 'block' outcome entries mention optional move_to."""

    def _skill_block_row(self) -> str:
        """Return the 'block' table row from the SKILL.md end_work Outcome table."""
        assert _SKILL_MD.exists(), f"SKILL.md not found at {_SKILL_MD}"
        text = _SKILL_MD.read_text(encoding="utf-8")
        idx = text.find("### end_work")
        assert idx != -1, "'### end_work' section not found in SKILL.md"
        section = text[idx:]
        for line in section.splitlines():
            if "| `block`" in line or "| block |" in line.lower():
                return line
        return ""

    def _readme_block_bullet(self) -> str:
        """Return the 'block' bullet line from the README end_work Outcomes section."""
        assert _README_MD.exists(), f"README.md not found at {_README_MD}"
        text = _README_MD.read_text(encoding="utf-8")
        idx = text.lower().find("end_work outcomes")
        assert idx != -1, "'end_work Outcomes' section not found in README.md"
        section = text[idx:]
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith(("- `block`", "- block:")):
                return line
        return ""

    def test_skill_md_block_row_mentions_move_to(self) -> None:
        """SKILL.md end_work 'block' table row must mention optional 'move_to'.

        Current row: '| `block` | Mark blocked with `block_reason`, release claim. |'
        — no mention of move_to. After builder fix: row must include 'move_to'
        to document that move_to is optional on block, consistent with the
        code at agent_view.py:1000, :1107, :1162.
        """
        row = self._skill_block_row()
        assert row, "| `block` | row not found in SKILL.md end_work Outcome table."
        assert "move_to" in row, (
            f"SKILL.md 'block' outcome row does not mention 'move_to'.\n"
            f"Current row: {row!r}\n"
            "AC10 (refined): block row must document that move_to is optional "
            "(required on reject, optional on success/block, forbidden on fail/release)."
        )

    def test_readme_block_bullet_mentions_move_to(self) -> None:
        """README end_work 'block' bullet must mention optional 'move_to'.

        Current bullet: '- `block`: Mark task blocked (requires `block_reason`), then release claim.'
        — no mention of move_to. After builder fix: bullet must include 'move_to'
        to document that move_to is optional on block, consistent with the
        engine implementation and the full lifecycle matrix.
        """
        bullet = self._readme_block_bullet()
        assert bullet, "- `block` bullet not found in README.md end_work Outcomes section."
        assert "move_to" in bullet, (
            f"README 'block' outcome bullet does not mention 'move_to'.\n"
            f"Current bullet: {bullet!r}\n"
            "AC10 (refined): block bullet must document that move_to is optional "
            "(required on reject, optional on success/block, forbidden on fail/release)."
        )


# ---------------------------------------------------------------------------
# TestFromAC_SkillDocReleaseRowExactWording
# AC5 (refined, Cycle 4): The SKILL.md end_work 'release' row behavior cell must
# read exactly: 'Release claim, no status change (note appended if provided;
# no-op when unclaimed)' — no trailing period.
#
# Current text: 'Release claim, keep status unchanged.'
# Adjacent contract suite: tests/test_engine_end_work_fail_1125.py::
#   TestFromAC_SkillDocReleaseRow::test_skill_doc_release_row_exact_behavior_text
# ---------------------------------------------------------------------------


class TestFromAC_SkillDocReleaseRowExactWording:
    """AC5 refined: SKILL.md end_work 'release' row uses the exact established behavior text."""

    def _skill_release_row(self) -> str:
        """Return the 'release' table row from the SKILL.md end_work Outcome table."""
        assert _SKILL_MD.exists(), f"SKILL.md not found at {_SKILL_MD}"
        text = _SKILL_MD.read_text(encoding="utf-8")
        idx = text.find("### end_work")
        assert idx != -1, "'### end_work' section not found in SKILL.md"
        section = text[idx:]
        for line in section.splitlines():
            if "| `release`" in line or "| release |" in line.lower():
                return line
        return ""

    def test_skill_md_release_row_exact_behavior_text(self) -> None:
        """SKILL.md end_work 'release' behavior cell must match the established contract.

        Refined AC5: the behavior cell must read exactly:
          'Release claim, no status change (note appended if provided; no-op when unclaimed)'
        — no trailing period.

        Current text: 'Release claim, keep status unchanged.'
        This is the task-local pin for the same contract that
        tests/test_engine_end_work_fail_1125.py::TestFromAC_SkillDocReleaseRow
        ::test_skill_doc_release_row_exact_behavior_text validates in the adjacent
        lifecycle suite. Both must agree.
        """
        row = self._skill_release_row()
        assert row, "| `release` | row not found in SKILL.md end_work Outcome table."
        expected = "Release claim, no status change (note appended if provided; no-op when unclaimed)"
        assert expected in row, (
            f"SKILL.md 'release' row behavior text does not match the established contract.\n"
            f"Current row: {row!r}\n"
            f"Expected behavior cell to contain: {expected!r}\n"
            "Refined AC5: no trailing period; includes note-appended and unclaimed semantics."
        )
