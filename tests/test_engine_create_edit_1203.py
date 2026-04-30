"""RED-phase tests for AgentView.create_task empty-title error code fix (task #1203).

Covers:
  AC1 → TestFromAC_EmptyTitleErrorCode.test_err_invalid_title_in_kanban_error_codes
  AC2 → TestFromAC_EmptyTitleErrorCode.test_create_task_empty_title_raises_err_invalid_title
  AC2 → TestFromAC_EmptyTitleErrorCode.test_create_task_whitespace_title_raises_err_invalid_title
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.errors import KANBAN_ERROR_CODES
from owlbear_kanban.models import ValidationError

# ---------------------------------------------------------------------------
# Minimal board setup helpers (mirrors test_engine_create_edit_1070.py)
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
schema: grouped
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
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map:
        research: researcher
        backlog: architect
        todo: builder
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""


def _make_view(base_dir: Path) -> AgentView:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine)


# ---------------------------------------------------------------------------
# TestFromAC_EmptyTitleErrorCode
# ---------------------------------------------------------------------------


class TestFromAC_EmptyTitleErrorCode:
    """AC1: ERR_INVALID_TITLE in KANBAN_ERROR_CODES.
    AC2: create_task raises ValidationError(code="ERR_INVALID_TITLE") for empty/whitespace titles.
    """

    def test_err_invalid_title_in_kanban_error_codes(self) -> None:
        """AC1: 'ERR_INVALID_TITLE' must be a member of the KANBAN_ERROR_CODES frozenset."""
        assert "ERR_INVALID_TITLE" in KANBAN_ERROR_CODES

    def test_create_task_empty_title_raises_err_invalid_title(
        self, tmp_path: Path
    ) -> None:
        """AC2: create_task with empty title raises ValidationError with code ERR_INVALID_TITLE."""
        view = _make_view(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="")
        assert exc_info.value.code == "ERR_INVALID_TITLE"
        assert exc_info.value.user_message == "title must not be empty"

    def test_create_task_whitespace_title_raises_err_invalid_title(
        self, tmp_path: Path
    ) -> None:
        """AC2: create_task with whitespace-only title raises ValidationError(ERR_INVALID_TITLE)."""
        view = _make_view(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="   ")
        assert exc_info.value.code == "ERR_INVALID_TITLE"
        assert exc_info.value.user_message == "title must not be empty"
