"""Failing tests for task #145: planner gate checker and task selector (TDD RED).

Covers the interface contract from AC:
  - gates.py: check_atomicity, check_tdd, check_clarity, check_gates
  - selector.py: PRIORITY_RANK, STATUS_RANK, STATUS_AGENT_MAP, DISPATCH_CAP, select_tasks
  - __init__.py: public exports for gates and selector symbols

All tests FAIL in RED phase — ImportError expected until builder implements #145.
"""

from __future__ import annotations

from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Import targets — will raise ImportError until builder implements #145 (RED)
# ---------------------------------------------------------------------------
from owlbear.planner.models import DispatchPlan, Task  # already exists from #144
from owlbear.planner.gates import (  # type: ignore[import]
    check_atomicity,
    check_clarity,
    check_gates,
    check_tdd,
)
from owlbear.planner.selector import (  # type: ignore[import]
    DISPATCH_CAP,
    PRIORITY_RANK,
    STATUS_AGENT_MAP,
    STATUS_RANK,
    select_tasks,
)

# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC).isoformat()


def _make_task(  # noqa: PLR0913
    *,
    task_id: int = 1,
    title: str = "Do something",
    status: str = "todo",
    priority: str = "important",
    body: str = "- [ ] item",
    tags: list[str] | None = None,
) -> Task:
    return Task.model_validate(
        {
            "id": task_id,
            "title": title,
            "status": status,
            "priority": priority,
            "created": _EPOCH,
            "updated": _EPOCH,
            "tags": tags or [],
            "depends_on": [],
            "class": "standard",
            "body": body,
            "file": f"/kanban/tasks/{task_id}-task.md",
        }
    )


# ---------------------------------------------------------------------------
# TestFromAC_GateChecker
# ---------------------------------------------------------------------------


class TestFromAC_GateChecker:
    """Contract tests for gates.py functions derived from #145 AC."""

    # -- check_atomicity happy path ----------------------------------------

    def test_check_atomicity_clean_title_returns_true(self) -> None:
        task = _make_task(title="Implement feature")
        assert check_atomicity(task) is True

    def test_check_atomicity_and_inside_word_not_matched(self) -> None:
        """'and' inside 'sandbox' is not a word-boundary match."""
        task = _make_task(title="Implement sandbox feature")
        assert check_atomicity(task) is True

    def test_check_atomicity_and_inside_standby_not_matched(self) -> None:
        """'and' inside 'standby' is not a word-boundary match."""
        task = _make_task(title="standby mode implementation")
        assert check_atomicity(task) is True

    def test_check_atomicity_and_inside_command_not_matched(self) -> None:
        """'and' inside 'command' is not a word-boundary match."""
        task = _make_task(title="Run command handler")
        assert check_atomicity(task) is True

    # -- check_atomicity error path ----------------------------------------

    def test_check_atomicity_word_and_in_title_returns_false(self) -> None:
        task = _make_task(title="Fix auth and authorization")
        assert check_atomicity(task) is False

    def test_check_atomicity_and_at_start_of_title_returns_false(self) -> None:
        task = _make_task(title="and also do this")
        assert check_atomicity(task) is False

    def test_check_atomicity_and_at_end_of_title_returns_false(self) -> None:
        task = _make_task(title="research and")
        assert check_atomicity(task) is False

    def test_check_atomicity_and_surrounded_by_spaces_returns_false(self) -> None:
        task = _make_task(title="parse and validate")
        assert check_atomicity(task) is False

    # -- check_tdd happy path -----------------------------------------------

    def test_check_tdd_todo_status_returns_true(self) -> None:
        task = _make_task(status="todo", body="- [ ] item")
        assert check_tdd(task) is True

    def test_check_tdd_in_progress_with_notes_returns_true(self) -> None:
        task = _make_task(status="in-progress", body="## Test-Writer Notes\n- tests written")
        assert check_tdd(task) is True

    def test_check_tdd_review_without_notes_returns_true(self) -> None:
        """Non-in-progress statuses always pass the TDD gate."""
        task = _make_task(status="review", body="- [ ] item")
        assert check_tdd(task) is True

    def test_check_tdd_backlog_without_notes_returns_true(self) -> None:
        task = _make_task(status="backlog", body="")
        assert check_tdd(task) is True

    def test_check_tdd_done_without_notes_returns_true(self) -> None:
        task = _make_task(status="done", body="")
        assert check_tdd(task) is True

    def test_check_tdd_ideation_without_notes_returns_true(self) -> None:
        task = _make_task(status="ideation", body="")
        assert check_tdd(task) is True

    # -- check_tdd error path -----------------------------------------------

    def test_check_tdd_in_progress_without_notes_returns_false(self) -> None:
        task = _make_task(status="in-progress", body="- [ ] item")
        assert check_tdd(task) is False

    def test_check_tdd_in_progress_empty_body_returns_false(self) -> None:
        task = _make_task(status="in-progress", body="")
        assert check_tdd(task) is False

    def test_check_tdd_in_progress_prose_only_returns_false(self) -> None:
        task = _make_task(status="in-progress", body="Some description without TW marker.")
        assert check_tdd(task) is False

    # -- check_clarity happy path -------------------------------------------

    def test_check_clarity_todo_with_bullet_ac_returns_true(self) -> None:
        task = _make_task(status="todo", body="- [ ] item one\n- [ ] item two")
        assert check_clarity(task) is True

    def test_check_clarity_todo_with_numbered_list_returns_true(self) -> None:
        task = _make_task(status="todo", body="1. do this\n2. do that")
        assert check_clarity(task) is True

    def test_check_clarity_in_progress_with_bullets_returns_true(self) -> None:
        task = _make_task(
            status="in-progress",
            body="## Test-Writer Notes\n- tests written\n- [ ] item",
        )
        assert check_clarity(task) is True

    def test_check_clarity_review_with_bullets_returns_true(self) -> None:
        task = _make_task(status="review", body="- item")
        assert check_clarity(task) is True

    def test_check_clarity_docs_with_bullets_returns_true(self) -> None:
        task = _make_task(status="docs", body="- item")
        assert check_clarity(task) is True

    def test_check_clarity_done_with_bullets_returns_true(self) -> None:
        task = _make_task(status="done", body="- item")
        assert check_clarity(task) is True

    def test_check_clarity_ideation_empty_body_returns_true(self) -> None:
        """ideation status: AC not required yet."""
        task = _make_task(status="ideation", body="")
        assert check_clarity(task) is True

    def test_check_clarity_ideation_prose_only_returns_true(self) -> None:
        task = _make_task(status="ideation", body="Just an idea with no bullets")
        assert check_clarity(task) is True

    def test_check_clarity_backlog_empty_body_returns_true(self) -> None:
        """backlog status: AC not required yet."""
        task = _make_task(status="backlog", body="")
        assert check_clarity(task) is True

    def test_check_clarity_backlog_prose_only_returns_true(self) -> None:
        task = _make_task(status="backlog", body="Just prose no bullets")
        assert check_clarity(task) is True

    # -- check_clarity error path -------------------------------------------

    def test_check_clarity_todo_empty_body_returns_false(self) -> None:
        task = _make_task(status="todo", body="")
        assert check_clarity(task) is False

    def test_check_clarity_todo_prose_only_returns_false(self) -> None:
        task = _make_task(status="todo", body="This is a description with no bullets or lists.")
        assert check_clarity(task) is False

    def test_check_clarity_in_progress_no_bullets_returns_false(self) -> None:
        task = _make_task(status="in-progress", body="No structured AC here")
        assert check_clarity(task) is False

    def test_check_clarity_done_empty_body_returns_false(self) -> None:
        task = _make_task(status="done", body="")
        assert check_clarity(task) is False

    # -- check_gates composite -----------------------------------------------

    def test_check_gates_all_pass_returns_true(self) -> None:
        task = _make_task(title="Implement feature", status="todo", body="- [ ] item")
        assert check_gates(task) is True

    def test_check_gates_atomicity_fails_returns_false(self) -> None:
        task = _make_task(title="Fix auth and caching", status="todo", body="- [ ] item")
        assert check_gates(task) is False

    def test_check_gates_tdd_fails_returns_false(self) -> None:
        task = _make_task(title="Implement feature", status="in-progress", body="- [ ] item")
        assert check_gates(task) is False

    def test_check_gates_clarity_fails_returns_false(self) -> None:
        task = _make_task(title="Implement feature", status="todo", body="No bullets here")
        assert check_gates(task) is False

    def test_check_gates_multiple_failures_returns_false(self) -> None:
        task = _make_task(
            title="Fix auth and caching",
            status="in-progress",
            body="no bullets",
        )
        assert check_gates(task) is False


# ---------------------------------------------------------------------------
# TestFromAC_TaskSelector
# ---------------------------------------------------------------------------


class TestFromAC_TaskSelector:
    """Contract tests for selector.py constants and select_tasks() derived from #145 AC."""

    # -- PRIORITY_RANK constant ---------------------------------------------

    def test_priority_rank_critical_is_zero(self) -> None:
        assert PRIORITY_RANK["critical"] == 0

    def test_priority_rank_has_five_keys(self) -> None:
        assert set(PRIORITY_RANK.keys()) == {"critical", "needed", "important", "nice-to-have", "someday"}

    def test_priority_rank_order_critical_to_someday(self) -> None:
        """Lower rank dispatched first: critical(0) < needed(1) < important(2) < nice-to-have(3) < someday(4)."""
        assert (
            PRIORITY_RANK["critical"]
            < PRIORITY_RANK["needed"]
            < PRIORITY_RANK["important"]
            < PRIORITY_RANK["nice-to-have"]
            < PRIORITY_RANK["someday"]
        )

    # -- STATUS_RANK constant -----------------------------------------------

    def test_status_rank_done_is_zero(self) -> None:
        assert STATUS_RANK["done"] == 0

    def test_status_rank_has_seven_keys(self) -> None:
        expected = {"done", "docs", "review", "in-progress", "todo", "backlog", "ideation"}
        assert set(STATUS_RANK.keys()) == expected

    def test_status_rank_order_done_to_ideation(self) -> None:
        """Pipeline proximity: done(0) < docs(1) < review(2) < in-progress(3) < todo(4) < backlog(5) < ideation(6)."""
        assert (
            STATUS_RANK["done"]
            < STATUS_RANK["docs"]
            < STATUS_RANK["review"]
            < STATUS_RANK["in-progress"]
            < STATUS_RANK["todo"]
            < STATUS_RANK["backlog"]
            < STATUS_RANK["ideation"]
        )

    # -- STATUS_AGENT_MAP constant ------------------------------------------

    def test_status_agent_map_has_seven_entries(self) -> None:
        expected = {"ideation", "backlog", "todo", "in-progress", "review", "docs", "done"}
        assert set(STATUS_AGENT_MAP.keys()) == expected

    def test_status_agent_map_all_correct_agents(self) -> None:
        assert STATUS_AGENT_MAP["ideation"] == "researcher"
        assert STATUS_AGENT_MAP["backlog"] == "architect"
        assert STATUS_AGENT_MAP["todo"] == "test-writer"
        assert STATUS_AGENT_MAP["in-progress"] == "builder"
        assert STATUS_AGENT_MAP["review"] == "reviewer"
        assert STATUS_AGENT_MAP["docs"] == "writer"
        assert STATUS_AGENT_MAP["done"] == "auditor"

    # -- DISPATCH_CAP constant ----------------------------------------------

    def test_dispatch_cap_is_20(self) -> None:
        assert DISPATCH_CAP == 20

    # -- select_tasks happy path --------------------------------------------

    def test_select_tasks_returns_dispatch_plan_instance(self) -> None:
        tasks = [_make_task(title="Feature", status="todo", body="- [ ] item")]
        result = select_tasks(tasks)
        assert isinstance(result, DispatchPlan)

    def test_select_tasks_empty_list_returns_empty_dispatch_plan(self) -> None:
        result = select_tasks([])
        assert isinstance(result, DispatchPlan)
        assert result.entries == []

    def test_select_tasks_includes_task_id_in_entries(self) -> None:
        task = _make_task(task_id=99, title="Feature", status="todo", body="- [ ] item")
        result = select_tasks([task])
        assert result.entries[0].task_id == 99

    def test_select_tasks_maps_todo_to_test_writer(self) -> None:
        task = _make_task(title="Feature", status="todo", body="- [ ] item")
        result = select_tasks([task])
        assert result.entries[0].agent == "test-writer"

    def test_select_tasks_maps_in_progress_to_builder(self) -> None:
        task = _make_task(
            title="Feature",
            status="in-progress",
            body="## Test-Writer Notes\n- done\n- [ ] item",
        )
        result = select_tasks([task])
        assert result.entries[0].agent == "builder"

    def test_select_tasks_maps_review_to_reviewer(self) -> None:
        task = _make_task(title="Feature", status="review", body="- [ ] item")
        result = select_tasks([task])
        assert result.entries[0].agent == "reviewer"

    def test_select_tasks_entries_have_target_status(self) -> None:
        task = _make_task(title="Feature", status="todo", body="- [ ] item")
        result = select_tasks([task])
        assert result.entries[0].target_status is not None
        assert isinstance(result.entries[0].target_status, str)

    # -- select_tasks gate filtering ----------------------------------------

    def test_select_tasks_excludes_gate_failing_tasks(self) -> None:
        good = _make_task(task_id=1, title="Implement feature", status="todo", body="- [ ] item")
        bad = _make_task(task_id=2, title="Fix auth and caching", status="todo", body="- [ ] item")
        result = select_tasks([good, bad])
        task_ids = [e.task_id for e in result.entries]
        assert 1 in task_ids
        assert 2 not in task_ids

    def test_select_tasks_all_fail_gates_returns_empty_entries(self) -> None:
        tasks = [
            _make_task(task_id=1, title="Fix auth and logging", status="todo", body="no bullets"),
            _make_task(task_id=2, title="Refactor and migrate", status="in-progress", body=""),
        ]
        result = select_tasks(tasks)
        assert result.entries == []

    # -- select_tasks sorting -----------------------------------------------

    def test_select_tasks_critical_sorted_before_important(self) -> None:
        important = _make_task(task_id=1, title="Feature A", status="todo", priority="important", body="- item")
        critical = _make_task(task_id=2, title="Feature B", status="todo", priority="critical", body="- item")
        result = select_tasks([important, critical])
        assert result.entries[0].task_id == 2  # critical dispatched first

    def test_select_tasks_review_sorted_before_todo_same_priority(self) -> None:
        """Pipeline proximity: review(2) < todo(4) — review dispatched first."""
        todo_task = _make_task(task_id=1, title="Feature A", status="todo", priority="important", body="- item")
        review_task = _make_task(task_id=2, title="Feature B", status="review", priority="important", body="- item")
        result = select_tasks([todo_task, review_task])
        assert result.entries[0].task_id == 2  # review closer to done

    def test_select_tasks_priority_dominates_status_in_sort(self) -> None:
        """A critical/todo task sorts before an important/review task."""
        important_review = _make_task(task_id=1, title="A", status="review", priority="important", body="- item")
        critical_todo = _make_task(task_id=2, title="B", status="todo", priority="critical", body="- item")
        result = select_tasks([important_review, critical_todo])
        assert result.entries[0].task_id == 2  # critical priority wins

    # -- select_tasks dispatch cap ------------------------------------------

    def test_select_tasks_caps_result_at_dispatch_cap(self) -> None:
        tasks = [
            _make_task(task_id=i, title=f"Task {i}", status="todo", priority="important", body="- item")
            for i in range(1, 30)
        ]
        result = select_tasks(tasks)
        assert len(result.entries) <= DISPATCH_CAP

    def test_select_tasks_exactly_dispatch_cap_tasks_all_returned(self) -> None:
        tasks = [
            _make_task(task_id=i, title=f"Task {i}", status="todo", priority="important", body="- item")
            for i in range(1, DISPATCH_CAP + 1)
        ]
        result = select_tasks(tasks)
        assert len(result.entries) == DISPATCH_CAP

    # -- select_tasks DECOMP routing override ------------------------------

    def test_decomp_override_routes_agent_to_kanban_planner(self) -> None:
        task = _make_task(
            title="Feature",
            status="todo",
            body="- [ ] item\nNeeds decomposition: too many concerns",
        )
        result = select_tasks([task])
        assert len(result.entries) == 1
        assert result.entries[0].agent == "planner"

    def test_decomp_override_applies_for_backlog_status(self) -> None:
        task = _make_task(
            title="Feature",
            status="backlog",
            body="- [ ] item\nNeeds decomposition: complex scope",
        )
        result = select_tasks([task])
        if result.entries:
            assert result.entries[0].agent == "planner"

    def test_decomp_override_applies_for_in_progress_status(self) -> None:
        task = _make_task(
            title="Feature",
            status="in-progress",
            body="## Test-Writer Notes\n- done\n- [ ] item\nNeeds decomposition: too broad",
        )
        result = select_tasks([task])
        if result.entries:
            assert result.entries[0].agent == "planner"

    def test_decomp_override_does_not_affect_other_tasks(self) -> None:
        """DECOMP override must not bleed into non-DECOMP tasks in the same batch."""
        normal = _make_task(task_id=1, title="Normal", status="todo", body="- [ ] item")
        decomp = _make_task(
            task_id=2, title="Decomp", status="todo",
            body="- [ ] item\nNeeds decomposition: too broad",
        )
        result = select_tasks([normal, decomp])
        for entry in result.entries:
            if entry.task_id == 1:
                assert entry.agent == "test-writer"
            elif entry.task_id == 2:
                assert entry.agent == "planner"

    # -- select_tasks unknown priority/status fallback ---------------------

    def test_select_tasks_unknown_priority_sorts_to_end(self) -> None:
        normal = _make_task(task_id=1, title="A", status="todo", priority="important", body="- item")
        unknown = _make_task(task_id=2, title="B", status="todo", priority="exotic-priority", body="- item")
        result = select_tasks([normal, unknown])
        ids = [e.task_id for e in result.entries]
        assert ids.index(1) < ids.index(2)

    def test_select_tasks_unknown_status_still_included_in_plan(self) -> None:
        """Unknown status: fallback rank applied, task still dispatched (sorts to end)."""
        task = _make_task(task_id=1, title="A", status="exotic-status", priority="important", body="- item")
        result = select_tasks([task])
        assert any(e.task_id == 1 for e in result.entries)

    def test_select_tasks_unknown_status_sorts_after_known_statuses(self) -> None:
        known = _make_task(task_id=1, title="A", status="ideation", priority="important", body="")
        unknown = _make_task(task_id=2, title="B", status="exotic-status", priority="important", body="- item")
        result = select_tasks([known, unknown])
        ids = [e.task_id for e in result.entries]
        assert ids.index(1) < ids.index(2)


# ---------------------------------------------------------------------------
# TestFromAC_PlannerInit
# ---------------------------------------------------------------------------


class TestFromAC_PlannerInit:
    """Contract tests for owlbear.planner __init__.py public exports from #145 AC."""

    def test_check_gates_importable_from_owlbear_planner(self) -> None:
        from owlbear.planner import check_gates as _cg  # type: ignore[import]

        assert callable(_cg)

    def test_check_atomicity_importable_from_owlbear_planner(self) -> None:
        from owlbear.planner import check_atomicity as _ca  # type: ignore[import]

        assert callable(_ca)

    def test_check_tdd_importable_from_owlbear_planner(self) -> None:
        from owlbear.planner import check_tdd as _ct  # type: ignore[import]

        assert callable(_ct)

    def test_check_clarity_importable_from_owlbear_planner(self) -> None:
        from owlbear.planner import check_clarity as _cc  # type: ignore[import]

        assert callable(_cc)

    def test_select_tasks_importable_from_owlbear_planner(self) -> None:
        from owlbear.planner import select_tasks as _st  # type: ignore[import]

        assert callable(_st)

    def test_status_agent_map_importable_from_owlbear_planner(self) -> None:
        from owlbear.planner import STATUS_AGENT_MAP  # type: ignore[import]

        assert isinstance(STATUS_AGENT_MAP, dict)

    def test_dispatch_cap_importable_from_owlbear_planner(self) -> None:
        from owlbear.planner import DISPATCH_CAP  # type: ignore[import]

        assert isinstance(DISPATCH_CAP, int)

