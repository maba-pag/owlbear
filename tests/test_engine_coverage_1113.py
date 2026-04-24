"""Coverage-uplift tests for owlbear_kanban.engine (task #1113).

Targets genuinely uncovered code paths identified from architecture review:
  - edit_task field mutations: title, body, priority, status, parent
  - edit_task tag operations: add_tags (with dedup), remove_tags
  - edit_task dep operations: add_deps (with dedup), remove_deps
  - edit_task validation: invalid status, invalid priority
  - edit_task append_body without timestamp (no date prefix)
  - engine.agent_name property: non-empty str, stable across calls
  - engine.board_config(): returns defensive deep copy
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Board helpers (mirrored from test_engine_coverage_1110.py conventions)
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
wave_size: 4
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
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
claimed_at: null
archival_reason: null
archival_refs: []
---
{body}
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
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
    parent: str = "null",
    depends_on: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    body: str = "Body.",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        tags=tags,
        parent=parent,
        depends_on=depends_on,
        blocked=blocked,
        block_reason=block_reason,
        body=body,
    )
    path = kanban_dir / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# edit_task field mutations
# ---------------------------------------------------------------------------


class TestFromAC_EngineEditTaskFieldMutations:
    """AC: edit_task field mutations each verified on the returned Task."""

    def test_title_mutation_reflected_on_returned_task(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Original")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", title="Updated")
        assert result.title == "Updated"

    def test_body_mutation_reflected_on_returned_task(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="Old body")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", body="New body")
        assert result.body == "New body"

    def test_priority_mutation_reflected_on_returned_task(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, priority="someday")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", priority="critical")
        assert result.priority == "critical"

    def test_status_mutation_reflected_on_returned_task(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="backlog")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", status="in-progress")
        assert result.status == "in-progress"

    def test_parent_mutation_reflected_on_returned_task(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, parent="null")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", parent=99)
        assert result.parent == 99

    def test_add_tags_merges_with_existing(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, tags='["alpha"]')
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", add_tags=["beta"])
        assert set(result.tags) == {"alpha", "beta"}

    def test_add_tags_dedup_is_idempotent(self, tmp_path: Path) -> None:
        """Adding a tag that already exists must not duplicate it."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, tags='["alpha"]')
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", add_tags=["alpha"])
        assert result.tags.count("alpha") == 1

    def test_remove_tags_drops_specified_tag(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, tags='["alpha", "beta"]')
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", remove_tags=["alpha"])
        assert "alpha" not in result.tags
        assert "beta" in result.tags

    def test_add_deps_merges_with_existing(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[2]")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", add_deps=[3])
        assert set(result.depends_on) == {2, 3}

    def test_add_deps_dedup_is_idempotent(self, tmp_path: Path) -> None:
        """Adding a dep that already exists must not duplicate it."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[2]")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", add_deps=[2])
        assert result.depends_on.count(2) == 1

    def test_remove_deps_drops_specified_dep(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[2, 3]")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", remove_deps=[2])
        assert 2 not in result.depends_on
        assert 3 in result.depends_on

    def test_invalid_status_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.edit_task("1", status="not-a-real-status")

    def test_invalid_priority_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid priority"):
            engine.edit_task("1", priority="ultra-mega-high")

    def test_append_body_without_timestamp_has_no_date_prefix(self, tmp_path: Path) -> None:
        """append_body with timestamp=False (default) must not prepend [[YYYY-MM-DD]]."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="Initial.")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", append_body="Appended text.")
        # Body should contain the appended text but NO [[date]] bracket prefix
        assert "Appended text." in str(result.body)
        assert "[[" not in str(result.body)


# ---------------------------------------------------------------------------
# Engine properties
# ---------------------------------------------------------------------------


class TestFromAC_EngineProperties:
    """AC: agent_name and board_config() property contracts."""

    def test_agent_name_is_non_empty_string(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        name = engine.agent_name
        assert isinstance(name, str)
        assert len(name) > 0

    def test_agent_name_is_stable_across_calls(self, tmp_path: Path) -> None:
        """agent_name must return the same value for the lifetime of one engine instance."""
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        assert engine.agent_name == engine.agent_name

    def test_board_config_returns_deep_copy(self, tmp_path: Path) -> None:
        """Mutating the returned BoardConfig must not affect engine internal state."""
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        original_statuses = list(engine.board_config().statuses)

        config_copy = engine.board_config()
        config_copy.statuses.append("INJECTED")

        # Engine's next board_config() call must still return unmodified statuses
        assert engine.board_config().statuses == original_statuses
