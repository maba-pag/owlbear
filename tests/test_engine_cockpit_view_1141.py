"""Failing tests for #1141: Extend CockpitView.edit_task to accept title param.

AC coverage:
  ac1-sig      — CockpitView.edit_task accepts title: str | None = None parameter
  ac1-default  — title parameter default is None
  ac2-forward  — title not-None is forwarded to engine.edit_task (title changes)
  ac2-none     — title=None (explicit) does NOT change the task title
  ac4-e2e      — CockpitView.edit_task(task_id, expected_updated=..., title="New") updates title

All tests FAIL (RED phase).
"""

from __future__ import annotations

import inspect
from pathlib import Path

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import CockpitView
from owlbear_kanban.models import SingleTaskResponse

# ---------------------------------------------------------------------------
# Board / task helpers (minimal — mirrors test_engine_cockpit_view_1078.py)
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
next_id: 100
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: important
created: "2026-01-01T10:00:00+00:00"
updated: "{updated}"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Task body.
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(
    kanban_dir: Path,
    task_id: int,
    title: str = "Original Title",
    status: str = "research",
    updated: str = "2026-01-01T10:00:00+00:00",
) -> Path:
    safe_title = title.lower().replace(" ", "-")
    filename = f"{task_id}-{safe_title}.md"
    path = kanban_dir / "tasks" / filename
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        updated=updated,
    )
    path.write_text(content, encoding="utf-8")
    return path


def _make_cockpit_view(kanban_dir: Path) -> CockpitView:
    engine = KanbanEngine(kanban_dir)
    return CockpitView(engine)


# ---------------------------------------------------------------------------
# AC1: CockpitView.edit_task accepts title: str | None = None
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewEditTaskTitle:
    """Tests for CockpitView.edit_task title parameter (#1141)."""

    # -- ac1-sig: title param exists in signature --

    def test_edit_task_signature_has_title_param(self, tmp_path: Path) -> None:
        """CockpitView.edit_task must declare a 'title' keyword parameter."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        assert "title" in sig.parameters, (
            "CockpitView.edit_task must accept a 'title' parameter"
        )

    # -- ac1-default: title default is None --

    def test_edit_task_title_param_default_is_none(self, tmp_path: Path) -> None:
        """CockpitView.edit_task title parameter must have default value None."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        param = sig.parameters.get("title")
        assert param is not None, "title param missing from CockpitView.edit_task"
        assert param.default is None, (
            "CockpitView.edit_task title must default to None, "
            f"got {param.default!r}"
        )

    # -- ac2-forward: non-None title is forwarded to engine --

    def test_edit_task_with_title_updates_task_title(self, tmp_path: Path) -> None:
        """edit_task with title='New Title' updates the task's title."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, title="Original Title", updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        result = cv.edit_task(
            1,
            expected_updated="2026-01-01T10:00:00+00:00",
            title="New Title",
        )
        assert isinstance(result, SingleTaskResponse)
        assert result.task.title == "New Title", (
            f"Expected title 'New Title' after edit, got {result.task.title!r}"
        )

    # -- ac2-none: explicit title=None does not change the task title --

    def test_edit_task_title_none_preserves_original_title(self, tmp_path: Path) -> None:
        """edit_task with title=None must NOT change the task's existing title."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, title="Original Title", updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        result = cv.edit_task(
            1,
            expected_updated="2026-01-01T10:00:00+00:00",
            title=None,
            append_body="minor note",
        )
        assert isinstance(result, SingleTaskResponse)
        assert result.task.title == "Original Title", (
            f"title=None must preserve original title, got {result.task.title!r}"
        )

    # -- ac4-e2e: literal AC4 scenario --

    def test_edit_task_with_title_returns_response_with_updated_title(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.edit_task(task_id, expected_updated=..., title='New') -> title updated."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 42, title="Old Name", updated="2026-03-15T08:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        result = cv.edit_task(
            42,
            expected_updated="2026-03-15T08:00:00+00:00",
            title="New Name",
        )
        assert result.task.title == "New Name"

    # -- boundary: title param is keyword-only --

    def test_edit_task_title_is_keyword_only(self, tmp_path: Path) -> None:
        """CockpitView.edit_task title must be keyword-only (not positional)."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        param = sig.parameters.get("title")
        assert param is not None, "title param missing"
        assert param.kind in (
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_KEYWORD,  # would not happen in practice
        ), (
            f"CockpitView.edit_task title must be keyword-only, got kind={param.kind}"
        )
