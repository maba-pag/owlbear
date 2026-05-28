"""Tests for AgentView.start_work dep-status guidance feature (task #1526).

Covers AC1-AC3 of the dep-status guidance feature in start_work():

  AC1 → dep_status="blocked" (active non-archived dep) fires guidance with exact string
  AC2 → dep_status resolved (no deps, all archived-completed, redirect deps) → guidance==[]
  AC3 → dep lookup exceptions silently skipped; all-fail case → guidance==[]

AC coverage table:
  AC1 → test_start_work_active_dep_returns_guidance_exact_string
         test_start_work_multiple_active_deps_guidance_lists_all_ids
         test_start_work_guidance_has_exactly_one_entry
         test_start_work_dep_ids_in_guidance_match_blocked_set_only
  AC2 → test_start_work_no_depends_on_returns_empty_guidance
         test_start_work_dep_archived_completed_returns_empty_guidance
         test_start_work_dep_archived_deprecated_returns_empty_guidance
         test_start_work_dep_archived_duplicate_returns_empty_guidance
  AC3 → test_start_work_dep_lookup_file_not_found_silently_continues
         test_start_work_dep_lookup_corruption_error_silently_continues
         test_start_work_dep_lookup_value_error_silently_continues
         test_start_work_dep_lookup_key_error_silently_continues
         test_start_work_all_dep_lookups_fail_guidance_is_empty
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
# TestFromAC_DepStatusGuidance
#
# AC1: active non-archived dep → guidance string fires with exact value
# AC2: no-dep / archived-completed / redirect deps → guidance == []
# AC3: dep lookup exceptions silently skipped; all-fail → guidance == []
# ---------------------------------------------------------------------------


class TestDepStatusGuidance:
    """Dep-status guidance in AgentView.start_work — AC1, AC2, AC3."""

    # --- AC1: blocked dep → exact guidance string ---

    def test_start_work_active_dep_returns_guidance_exact_string(self, tmp_path: Path) -> None:
        """AC1: start_work on task with one active dep returns guidance with exact string.

        The guidance list must contain exactly one string equal to the
        canonical warning with the dep ID as a comma-separated integer list.
        This is dependency-derived guidance (not the manual blocked=true path).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="todo")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        expected = _GUIDANCE_TEMPLATE.format(dep_ids="2")
        assert result.guidance == [expected], f"Expected guidance == [{expected!r}], got {result.guidance!r}"

    def test_start_work_multiple_active_deps_guidance_lists_all_ids(self, tmp_path: Path) -> None:
        """AC1: start_work with two active deps → guidance lists both IDs comma-separated.

        The dep IDs in the guidance string must be the comma-separated integers
        of the active (non-archived) deps, in depends_on order.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="todo")
        _write_task(kanban_dir, task_id=3, status="in-progress")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2, 3]")

        result = view.start_work(1)

        expected = _GUIDANCE_TEMPLATE.format(dep_ids="2, 3")
        assert result.guidance == [expected], f"Expected guidance == [{expected!r}], got {result.guidance!r}"

    def test_start_work_guidance_has_exactly_one_entry(self, tmp_path: Path) -> None:
        """AC1: guidance list has exactly one entry — not zero, not multiple.

        A single blocked dep triggers exactly one guidance string. The list
        must not be empty and must not contain duplicates.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="todo")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        assert len(result.guidance) == 1, (
            f"Expected exactly one guidance entry, got {len(result.guidance)}: {result.guidance!r}"
        )

    def test_start_work_dep_ids_in_guidance_match_blocked_set_only(self, tmp_path: Path) -> None:
        """AC1: guidance dep IDs list only the active (blocked) deps, not archived ones.

        When one dep is active and one is archived-completed, only the active
        dep's ID appears in the guidance string. Archived resolved deps are excluded.
        """
        view, kanban_dir = _make_view(tmp_path)
        # dep 2: archived-completed (resolved)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason='"completed"',
            subdir="archive",
        )
        # dep 3: active (blocked)
        _write_task(kanban_dir, task_id=3, status="todo")
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2, 3]")

        result = view.start_work(1)

        expected = _GUIDANCE_TEMPLATE.format(dep_ids="3")
        assert result.guidance == [expected], f"Expected only active dep 3 in guidance, got {result.guidance!r}"

    # --- AC2: no guidance for resolved/empty deps ---

    def test_start_work_no_depends_on_returns_empty_guidance(self, tmp_path: Path) -> None:
        """AC2: start_work on task with depends_on==[] returns guidance==[].

        No deps means no dep-status computation and no guidance.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[]")

        result = view.start_work(1)

        assert result.guidance == [], f"Expected guidance == [] for task with no deps, got {result.guidance!r}"

    def test_start_work_dep_archived_completed_returns_empty_guidance(self, tmp_path: Path) -> None:
        """AC2: start_work with dep archived archival_reason='completed' returns guidance==[].

        A completed dep is fully resolved — dep_status is 'ok', no guidance fires.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason='"completed"',
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        assert result.guidance == [], f"Expected guidance == [] for completed dep, got {result.guidance!r}"

    def test_start_work_dep_archived_deprecated_returns_empty_guidance(self, tmp_path: Path) -> None:
        """AC2: start_work with dep archived archival_reason='deprecated' returns guidance==[].

        A deprecated dep is a redirect — dep_status is 'redirect', not 'blocked'.
        Redirect deps do NOT trigger guidance. This directly proves the redirect
        branch through start_work() does not fire the warning.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason='"deprecated"',
            archival_refs="[99]",
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        assert result.guidance == [], f"Expected guidance == [] for redirect (deprecated) dep, got {result.guidance!r}"

    def test_start_work_dep_archived_duplicate_returns_empty_guidance(self, tmp_path: Path) -> None:
        """AC2: start_work with dep archived archival_reason='duplicate' returns guidance==[].

        A duplicate dep is a redirect — dep_status is 'redirect', not 'blocked'.
        Redirect deps do NOT trigger guidance (non-goal of this feature).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason='"duplicate"',
            archival_refs="[99]",
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        result = view.start_work(1)

        assert result.guidance == [], f"Expected guidance == [] for redirect (duplicate) dep, got {result.guidance!r}"

    # --- AC3: dep lookup exceptions silently skipped ---

    def test_start_work_dep_lookup_file_not_found_silently_continues(self, tmp_path: Path) -> None:
        """AC3: dep lookup raises FileNotFoundError → silently skipped, valid response.

        The failing dep is not counted as blocked (no active_ids entry).
        The response is a valid SingleTaskResponse with guidance==[].
        """
        view, kanban_dir = _make_view(tmp_path)
        # task 1 depends on task 999, which does not exist on disk
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[999]")

        # Must not raise; FileNotFoundError from show_task(999) is silently skipped
        result = view.start_work(1)

        assert isinstance(result, SingleTaskResponse), f"Expected SingleTaskResponse, got {type(result)!r}"
        assert result.guidance == [], (
            f"Expected guidance == [] when all dep lookups fail (conservative), got {result.guidance!r}"
        )

    def test_start_work_dep_lookup_corruption_error_silently_continues(self, tmp_path: Path) -> None:
        """AC3: dep lookup raises CorruptionError → silently skipped, valid response.

        No exception propagates. The response is a valid SingleTaskResponse.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        real_show_task = view.engine.show_task

        def _fake_show_task(task_id_str: str) -> object:
            if task_id_str == "2":
                raise CorruptionError(
                    code="ERR_CORRUPT_YAML",
                    detail="simulated corruption",
                )
            return real_show_task(task_id_str)

        with patch.object(view.engine, "show_task", side_effect=_fake_show_task):
            result = view.start_work(1)

        assert isinstance(result, SingleTaskResponse), f"Expected SingleTaskResponse, got {type(result)!r}"
        assert result.guidance == [], (
            f"Expected guidance == [] when dep lookup raises CorruptionError, got {result.guidance!r}"
        )

    def test_start_work_dep_lookup_value_error_silently_continues(self, tmp_path: Path) -> None:
        """AC3: dep lookup raises ValueError → silently skipped, valid response.

        No exception propagates. The response is a valid SingleTaskResponse.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        real_show_task = view.engine.show_task

        def _fake_show_task(task_id_str: str) -> object:
            if task_id_str == "2":
                msg = "simulated value error in dep lookup"
                raise ValueError(msg)
            return real_show_task(task_id_str)

        with patch.object(view.engine, "show_task", side_effect=_fake_show_task):
            result = view.start_work(1)

        assert isinstance(result, SingleTaskResponse), f"Expected SingleTaskResponse, got {type(result)!r}"
        assert result.guidance == [], (
            f"Expected guidance == [] when dep lookup raises ValueError, got {result.guidance!r}"
        )

    def test_start_work_dep_lookup_key_error_silently_continues(self, tmp_path: Path) -> None:
        """AC3: dep lookup raises KeyError → silently skipped, valid response.

        No exception propagates. The response is a valid SingleTaskResponse.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[2]")

        real_show_task = view.engine.show_task

        def _fake_show_task(task_id_str: str) -> object:
            if task_id_str == "2":
                msg = "simulated key error in dep lookup"
                raise KeyError(msg)
            return real_show_task(task_id_str)

        with patch.object(view.engine, "show_task", side_effect=_fake_show_task):
            result = view.start_work(1)

        assert isinstance(result, SingleTaskResponse), f"Expected SingleTaskResponse, got {type(result)!r}"
        assert result.guidance == [], (
            f"Expected guidance == [] when dep lookup raises KeyError, got {result.guidance!r}"
        )

    # --- AC3 boundary: all dep lookups fail → conservative no-guidance ---

    def test_start_work_all_dep_lookups_fail_guidance_is_empty(self, tmp_path: Path) -> None:
        """AC3 boundary: all dep lookups fail → guidance == [] (conservative no-guidance).

        When EVERY dep lookup raises an exception, no blocked deps can be detected.
        The conservative behavior is to not raise a warning (guidance == []).
        This prevents false-positive warnings when the board is in a degraded state.
        """
        view, kanban_dir = _make_view(tmp_path)
        # Task depends on two deps, neither exists on disk
        _write_task(kanban_dir, task_id=1, status="todo", depends_on="[997, 998]")
        # tasks 997 and 998 do not exist → both lookups raise FileNotFoundError

        result = view.start_work(1)

        assert isinstance(result, SingleTaskResponse), f"Expected SingleTaskResponse, got {type(result)!r}"
        assert result.guidance == [], (
            f"Expected guidance == [] when ALL dep lookups fail (conservative), got {result.guidance!r}"
        )
