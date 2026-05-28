"""Tests for AgentView.start_work dep-status guidance feature (task #1527).

Covers AC1-AC3 of the dep-status guidance contract in start_work() from
complementary angles not present in test_agent_view_start_work_1526.py:

  AC1 → dep_status="blocked" (active non-archived dep) fires guidance with exact string
  AC2 → dep_status resolved (no deps / archived / null depends_on) → guidance==[]
  AC3 → dep lookup exceptions silently skipped; mixed exception+active → guidance fires

AC coverage table:
  AC1 → test_dep_in_inprogress_status_triggers_guidance
         test_dep_in_review_status_triggers_guidance
         test_three_deps_two_active_one_archived_guidance_lists_both_active
  AC2 → test_dep_archived_wontfix_returns_no_guidance
         test_two_completed_deps_return_no_guidance
         test_dep_archived_dropped_returns_no_guidance
  AC3 → test_exception_dep_skipped_active_dep_still_triggers_guidance
         test_all_key_error_deps_guidance_is_empty_list
         test_response_type_after_corruption_error_dep
         test_task_is_claimed_after_exception_dep_lookup
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from owlbear_kanban import KanbanEngine
from owlbear_kanban.agent_view import AgentView
from owlbear_kanban.corruption import CorruptionError
from owlbear_kanban.models import SingleTaskResponse

# ---------------------------------------------------------------------------
# Board and task fixtures
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  in-progress: builder
  review: reviewer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: {tags}
parent: {parent}
depends_on: {depends_on}
blocked: {blocked}
block_reason: {block_reason}
claimed_at: {claimed_at}
archival_reason: {archival_reason}
archival_refs: {archival_refs}
---
{body}
"""

_GUIDANCE_TEMPLATE = (
    "⚠️ This task has unresolved dependencies (IDs: {dep_ids}). "
    "Review and confirm with the user that starting this work is intentional."
)


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    tags: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    depends_on: str = "[]",
    body: str = "Body.",
    subdir: str = "tasks",
    parent: str = "null",
    archival_reason: str = "null",
    archival_refs: str = "[]",
    claimed_at: str = "null",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        tags=tags,
        blocked=blocked,
        block_reason=block_reason,
        depends_on=depends_on,
        body=body,
        parent=parent,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
        claimed_at=claimed_at,
    )
    dest_dir = kanban_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_view(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> tuple[AgentView, Path]:
    kanban_dir = _make_board(base_dir, config_yaml)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_StartWorkDepStatusGuidance
#
# AC1: active non-archived dep → guidance string fires with exact value
# AC2: null depends_on / archived deps / empty → guidance == []
# AC3: dep lookup exceptions silently skipped; mixed exception+active → guidance fires
# ---------------------------------------------------------------------------


class TestStartWorkDepStatusGuidance:
    """Dep-status guidance in AgentView.start_work — AC1, AC2, AC3 (1527 angles)."""

    # --- AC1: blocked dep → exact guidance string, non-"todo" active dep statuses ---

    def test_dep_in_inprogress_status_triggers_guidance(self, tmp_path: Path) -> None:
        """AC1: dep in "in-progress" (not "todo") is active → guidance fires.

        Any non-archived dep is active regardless of its pipeline status.
        This verifies the blocked check is not limited to "todo" status deps.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="in-progress")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        expected = _GUIDANCE_TEMPLATE.format(dep_ids="2")
        assert result.guidance == [expected], f"Expected guidance for in-progress dep 2, got {result.guidance!r}"

    def test_dep_in_review_status_triggers_guidance(self, tmp_path: Path) -> None:
        """AC1: dep in "review" status is active → guidance fires.

        "review" status is not archived; the dep is still unresolved.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="review")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        expected = _GUIDANCE_TEMPLATE.format(dep_ids="2")
        assert result.guidance == [expected], f"Expected guidance for review-status dep 2, got {result.guidance!r}"

    def test_three_deps_two_active_one_archived_guidance_lists_both_active(self, tmp_path: Path) -> None:
        """AC1: three deps, two active, one archived-completed → guidance lists only the two active.

        Verifies that the comma-separated IDs in the guidance string include
        exactly the active deps (in depends_on order), excluding the archived one.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="todo")
        _write_task(
            kanban_dir,
            task_id=3,
            status="archived",
            archival_reason='"completed"',
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=4, status="in-progress")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2, 3, 4]")

        result = view.start_work(1)

        expected = _GUIDANCE_TEMPLATE.format(dep_ids="2, 4")
        assert result.guidance == [expected], f"Expected guidance listing deps 2 and 4, got {result.guidance!r}"

    # --- AC2: no guidance for null / empty / archived deps ---

    def test_dep_archived_wontfix_returns_no_guidance(self, tmp_path: Path) -> None:
        """AC2 boundary: dep archived with reason 'wontfix' → guidance==[].

        'wontfix' produces dep_effect 'blocked' inside _compute_dep_status,
        but the dep is already archived (not in active_ids).  Because the
        guidance trigger requires non-empty active_ids, no guidance fires.
        This mirrors the 'dropped' boundary and confirms the gate holds for
        all archived reasons with a 'blocked' dep_effect.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason='"wontfix"',
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        assert result.guidance == [], f"Expected guidance == [] for archived-wontfix dep, got {result.guidance!r}"

    def test_two_completed_deps_return_no_guidance(self, tmp_path: Path) -> None:
        """AC2: two deps both archived-completed → guidance==[].

        All deps are in a resolved state; dep_status is 'ok', no warning fires.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason='"completed"',
            subdir="archive",
        )
        _write_task(
            kanban_dir,
            task_id=3,
            status="archived",
            archival_reason='"completed"',
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2, 3]")

        result = view.start_work(1)

        assert result.guidance == [], f"Expected guidance == [] for two completed deps, got {result.guidance!r}"

    def test_dep_archived_dropped_returns_no_guidance(self, tmp_path: Path) -> None:
        """AC2 boundary: dep archived with reason 'dropped' → guidance==[].

        'dropped' produces dep_effect 'blocked' inside _compute_dep_status,
        but the dep is already archived (not in active_ids).  The guidance
        trigger requires dep_status=='blocked' AND non-empty active_ids — so
        no guidance fires when the only blocked dep is archived.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason='"dropped"',
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        assert result.guidance == [], f"Expected guidance == [] for archived-dropped dep, got {result.guidance!r}"

    # --- AC3: exception handling during dep iteration ---

    def test_exception_dep_skipped_active_dep_still_triggers_guidance(self, tmp_path: Path) -> None:
        """AC3: one dep raises ValueError (skipped), one dep is active → guidance fires.

        The 'continue' inside the exception handler must not prevent subsequent
        active deps from being detected.  This proves that silently skipping
        one dep does not suppress the warning for other unresolved deps.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=3, status="todo")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2, 3]")

        real_show_task = view.engine.show_task

        def _fake_show_task(task_id_str: str) -> object:
            if task_id_str == "2":
                msg = "simulated dep lookup failure"
                raise ValueError(msg)
            return real_show_task(task_id_str)

        with patch.object(view.engine, "show_task", side_effect=_fake_show_task):
            result = view.start_work(1)

        expected = _GUIDANCE_TEMPLATE.format(dep_ids="3")
        assert result.guidance == [expected], (
            f"Expected guidance for active dep 3 even though dep 2 raised ValueError, got {result.guidance!r}"
        )

    def test_all_key_error_deps_guidance_is_empty_list(self, tmp_path: Path) -> None:
        """AC3: all dep lookups raise KeyError → guidance is [] (not None, not missing).

        When every dep lookup fails, dep_status computation sees empty active_ids
        and guidance must be an empty list — not None or omitted from the response.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[10, 20]")

        def _always_key_error(task_id_str: str) -> object:
            if task_id_str in {"10", "20"}:
                raise KeyError(task_id_str)
            return view.engine.show_task.__wrapped__(  # type: ignore[attr-defined]
                view.engine, task_id_str
            )

        real_show_task = view.engine.show_task

        def _fake_show_task(task_id_str: str) -> object:
            if task_id_str in {"10", "20"}:
                raise KeyError(task_id_str)
            return real_show_task(task_id_str)

        with patch.object(view.engine, "show_task", side_effect=_fake_show_task):
            result = view.start_work(1)

        assert result.guidance == [], (
            f"Expected guidance == [] (empty list) when all KeyErrors, got {result.guidance!r}"
        )

    def test_response_type_after_corruption_error_dep(self, tmp_path: Path) -> None:
        """AC3: CorruptionError during dep lookup → result is a valid SingleTaskResponse.

        No exception propagates; the returned object must be a full
        SingleTaskResponse (not a partial dict or an error envelope).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[5]")

        real_show_task = view.engine.show_task

        def _fake_show_task(task_id_str: str) -> object:
            if task_id_str == "5":
                raise CorruptionError(
                    code="ERR_CORRUPT_YAML",
                    detail="simulated corruption in dep",
                )
            return real_show_task(task_id_str)

        with patch.object(view.engine, "show_task", side_effect=_fake_show_task):
            result = view.start_work(1)

        assert isinstance(result, SingleTaskResponse), f"Expected SingleTaskResponse, got {type(result)!r}"
        assert result.id == 1, f"Expected task id 1, got {result.id!r}"

    def test_task_is_claimed_after_exception_dep_lookup(self, tmp_path: Path) -> None:
        """AC3: after FileNotFoundError during dep iteration, the task IS claimed.

        engine.start_work() must still execute and the returned task record
        must have claimed_at set — proving the exception did not abort the claim.
        """
        view, kanban_dir = _make_view(tmp_path)
        # dep 999 does not exist → FileNotFoundError silently skipped
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[999]")

        result = view.start_work(1)

        assert result.claimed_at is not None, "Expected claimed_at to be set after start_work, got None"
        assert result.id == 1, f"Expected task id 1, got {result.id!r}"
