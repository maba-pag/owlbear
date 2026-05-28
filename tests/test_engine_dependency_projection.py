from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.agent_view import AgentView

_BASE_CONFIG = """\
next_id: 1
"""

_TASK_TEMPLATE = """\
---
id: {task_id}
title: {title}
status: {status}
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: {depends_on}
blocked: false
block_reason: null
claimed_at: null
archival_reason: {archival_reason}
archival_refs: []
---
Body.
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


def _write_task(
    kanban_dir: Path,
    *,
    task_id: int = 1,
    title: str = "Task",
    **overrides: str,
) -> None:
    task_data = {
        "status": "todo",
        "depends_on": "[]",
        "archival_reason": "null",
        "subdir": "tasks",
    } | overrides
    task_path = kanban_dir / task_data["subdir"] / f"{task_id}-task.md"
    task_path.write_text(
        _TASK_TEMPLATE.format(
            task_id=task_id,
            title=title,
            status=task_data["status"],
            depends_on=task_data["depends_on"],
            archival_reason=task_data["archival_reason"],
        ),
        encoding="utf-8",
    )


def _write_case(kanban_dir: Path, case_name: str) -> None:
    if case_name == "no-deps":
        _write_task(kanban_dir, task_id=1, title="NoDeps")
        return

    _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
    if case_name == "active-dep":
        _write_task(kanban_dir, task_id=2, title="ActiveDep")
        return

    if case_name == "archived-completed-dep":
        _write_task(
            kanban_dir,
            task_id=2,
            title="CompletedDep",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        return

    raise AssertionError(f"unknown projection case {case_name!r}")


@pytest.mark.parametrize(
    ("case_name", "expected_dep_status"),
    [
        ("active-dep", "blocked"),
        ("archived-completed-dep", "ok"),
        ("no-deps", None),
    ],
)
def test_list_and_show_task_use_same_dep_status_projection_cases(
    tmp_path: Path,
    case_name: str,
    expected_dep_status: str | None,
) -> None:
    kanban_dir = _make_board(tmp_path)
    _write_case(kanban_dir, case_name)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    view = AgentView(engine)

    listed_task = next(task for task in engine.list_tasks() if task.id == 1)
    shown_task = view.show_task(1)

    assert listed_task.dep_status == expected_dep_status
    assert shown_task.dep_status == expected_dep_status


def test_list_tasks_uses_named_dep_status_projection_contract(tmp_path: Path) -> None:
    kanban_dir = _make_board(tmp_path)
    _write_case(kanban_dir, "active-dep")
    engine = KanbanEngine(kanban_dir, activity_log=False)

    with mock.patch.object(engine, "project_dep_status", wraps=engine.project_dep_status) as projection:
        listed_tasks = engine.list_tasks()

    assert {task.id for task in listed_tasks} == {1, 2}
    projected_task_ids = {call.args[0].id for call in projection.call_args_list}
    assert projected_task_ids == {1, 2}
    assert all("active_ids" in call.kwargs for call in projection.call_args_list)
    assert all("archived_reasons" in call.kwargs for call in projection.call_args_list)


def test_show_task_uses_named_dep_status_projection_contract(tmp_path: Path) -> None:
    kanban_dir = _make_board(tmp_path)
    _write_case(kanban_dir, "active-dep")
    view = AgentView(KanbanEngine(kanban_dir, activity_log=False))

    with mock.patch.object(view.engine, "project_dep_status", wraps=view.engine.project_dep_status) as projection:
        shown_task = view.show_task(1)

    assert shown_task.dep_status == "blocked"
    projection.assert_called_once()
    assert projection.call_args.args[0].id == 1
    assert projection.call_args.kwargs == {}
