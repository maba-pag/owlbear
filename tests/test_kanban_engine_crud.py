"""Failing tests for KanbanEngine CRUD — create_task, edit_task, move_task (#721, RED phase).

AC coverage:
  AC1 - create_task: allocates next_id, creates file with slug, increments
        next_id in config
  AC2 - create_task with all optional params (body, tags, priority, status,
        parent, depends_on)
  AC3 - edit_task: update title, body, priority, status, tags (add/remove),
        deps (add/remove), parent, block/unblock
  AC4 - edit_task append_body with timestamp prefix [[YYYY-MM-DD]]
  AC5 - move_task to valid status
  AC6 - move_task to archived
  AC7 - move_task rejects invalid status

Import path: owlbear_mcp_kanban.engine (module does NOT exist yet — #720/722 create it).
All tests must FAIL at this stage — GREEN phase is task #722.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import Task

# ---------------------------------------------------------------------------
# Shared config content — mirrors real .owlbear/kanban/config.yml
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: research
    - name: backlog
    - name: todo
    - name: in-progress
    - name: review
    - name: docs
    - name: done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
defaults:
    status: research
    priority: important
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 100
"""


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine instance wired to the temp kanban_dir."""
    return KanbanEngine(kanban_dir)


# ===========================================================================
# TestFromAC_CreateTask — AC1 + AC2
# ===========================================================================


class TestFromAC_CreateTask:
    """Tests for AC1/AC2: create_task allocates IDs, creates files, handles options."""

    # --- Happy path ---------------------------------------------------------

    def test_create_returns_task_record(self, engine: KanbanEngine) -> None:
        """create_task returns a Task instance."""
        record = engine.create_task("My new task")
        assert isinstance(record, Task)

    def test_create_task_id_equals_next_id(self, engine: KanbanEngine) -> None:
        """Returned Task.id equals next_id from config before the call."""
        record = engine.create_task("Allocate me")
        assert record.id == 100

    def test_create_task_creates_file_in_tasks_dir(self, kanban_dir: Path, engine: KanbanEngine) -> None:
        """A task file is created inside the tasks directory."""
        engine.create_task("File creation test")
        tasks_dir = kanban_dir / "tasks"
        files = list(tasks_dir.glob("*.md"))
        assert len(files) == 1

    def test_create_task_filename_contains_id_and_slug(self, kanban_dir: Path, engine: KanbanEngine) -> None:
        """Task filename starts with the task id followed by a hyphen and slug."""
        engine.create_task("File Slug Test")
        tasks_dir = kanban_dir / "tasks"
        (filename,) = tasks_dir.glob("*.md")
        # Must start with id-<slug>.md
        assert filename.name.startswith("100-")
        assert "file-slug-test" in filename.name

    def test_create_task_increments_next_id_in_config(self, kanban_dir: Path, engine: KanbanEngine) -> None:
        """next_id in config.yml is incremented to 101 after one create."""
        engine.create_task("Increment me")
        config_text = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        assert "next_id: 101" in config_text

    def test_create_two_tasks_use_sequential_ids(self, engine: KanbanEngine) -> None:
        """Two consecutive creates use 100 and 101."""
        first = engine.create_task("First task")
        second = engine.create_task("Second task")
        assert first.id == 100
        assert second.id == 101

    def test_create_task_title_stored_on_record(self, engine: KanbanEngine) -> None:
        """Returned record.title matches the supplied title."""
        record = engine.create_task("My precise title")
        assert record.title == "My precise title"

    def test_create_task_default_status_is_research(self, engine: KanbanEngine) -> None:
        """Default status is 'research' (from config defaults)."""
        record = engine.create_task("Default status task")
        assert record.status == "research"

    def test_create_task_default_priority_is_important(self, engine: KanbanEngine) -> None:
        """Default priority is 'important' (from config defaults)."""
        record = engine.create_task("Default priority task")
        assert record.priority == "important"

    def test_create_task_default_body_is_empty(self, engine: KanbanEngine) -> None:
        """Body defaults to empty string when not supplied."""
        record = engine.create_task("Empty body")
        assert record.body == "" or record.body.strip() == ""

    # --- AC2: optional params -----------------------------------------------

    def test_create_task_with_body(self, engine: KanbanEngine) -> None:
        """body param is stored in task record and file."""
        record = engine.create_task("With body", body="## Context\nHello world")
        assert "Hello world" in record.body

    def test_create_task_with_tags(self, engine: KanbanEngine) -> None:
        """tags param is stored on returned record."""
        record = engine.create_task("Tagged task", tags=["phase-3", "kanban"])
        assert "phase-3" in record.tags
        assert "kanban" in record.tags

    def test_create_task_with_priority(self, engine: KanbanEngine) -> None:
        """priority param overrides default."""
        record = engine.create_task("Critical task", priority="critical")
        assert record.priority == "critical"

    def test_create_task_with_status(self, engine: KanbanEngine) -> None:
        """status param overrides default 'research'."""
        record = engine.create_task("Backlog task", status="backlog")
        assert record.status == "backlog"

    def test_create_task_with_parent(self, engine: KanbanEngine) -> None:
        """parent param stored on returned record."""
        record = engine.create_task("Child task", parent=50)
        assert record.parent == 50

    def test_create_task_with_depends_on(self, engine: KanbanEngine) -> None:
        """depends_on list stored on returned record."""
        record = engine.create_task("Dependent task", depends_on=[10, 20])
        assert 10 in record.depends_on
        assert 20 in record.depends_on

    def test_create_task_persisted_to_disk_and_readable(self, kanban_dir: Path, engine: KanbanEngine) -> None:
        """Task file written to disk can be parsed back to a Task."""
        from owlbear_kanban.task_io import read_task
        engine.create_task("Persistence check", body="## AC\n- [ ] AC line")
        tasks_dir = kanban_dir / "tasks"
        (path,) = tasks_dir.glob("*.md")
        loaded = read_task(path)
        assert loaded.id == 100
        assert loaded.title == "Persistence check"

    # --- Boundary conditions ------------------------------------------------

    def test_create_task_next_id_after_two_creates_is_102(self, kanban_dir: Path, engine: KanbanEngine) -> None:
        """After two creates, config.yml next_id is 102."""
        engine.create_task("First")
        engine.create_task("Second")
        config_text = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        assert "next_id: 102" in config_text

    def test_create_task_empty_depends_on_stored_as_empty_list(self, engine: KanbanEngine) -> None:
        """Omitting depends_on stores empty list, not None."""
        record = engine.create_task("No deps")
        assert record.depends_on == []

    def test_create_task_empty_tags_stored_as_empty_list(self, engine: KanbanEngine) -> None:
        """Omitting tags stores empty list, not None."""
        record = engine.create_task("No tags")
        assert record.tags == []


# ===========================================================================
# TestFromAC_EditTask — AC3 + AC4
# ===========================================================================


class TestFromAC_EditTask:
    """Tests for AC3/AC4: edit_task updates fields, appends body with timestamp."""

    @pytest.fixture()
    def task_id(self, engine: KanbanEngine) -> str:
        """Create one task and return its id as a string for edit_task calls."""
        record = engine.create_task(
            "Original title",
            body="## Original\nOriginal body text",
            tags=["original-tag"],
            priority="important",
            status="backlog",
            parent=None,
            depends_on=[5],
        )
        return str(record.id)

    # --- Happy path: field updates ------------------------------------------

    def test_edit_title(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with title= updates the title field."""
        result = engine.edit_task(task_id, title="Updated title")
        assert result.title == "Updated title"

    def test_edit_body_replace(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with body= replaces the task body."""
        result = engine.edit_task(task_id, body="## New body\nReplaced content")
        assert "Replaced content" in result.body

    def test_edit_priority(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with priority= updates the priority field."""
        result = engine.edit_task(task_id, priority="critical")
        assert result.priority == "critical"

    def test_edit_status(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with status= updates the status field."""
        result = engine.edit_task(task_id, status="todo")
        assert result.status == "todo"

    def test_edit_parent(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with parent= updates the parent field."""
        result = engine.edit_task(task_id, parent=99)
        assert result.parent == 99

    # --- Tags: add / remove -------------------------------------------------

    def test_edit_tags_add(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with add_tags= adds the new tag without removing existing."""
        result = engine.edit_task(task_id, add_tags=["new-tag"])
        assert "new-tag" in result.tags
        assert "original-tag" in result.tags

    def test_edit_tags_remove(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with remove_tags= removes the specified tag."""
        result = engine.edit_task(task_id, remove_tags=["original-tag"])
        assert "original-tag" not in result.tags

    def test_edit_tags_add_and_remove_in_same_call(self, engine: KanbanEngine, task_id: str) -> None:
        """add_tags and remove_tags may be applied in a single edit call."""
        result = engine.edit_task(task_id, add_tags=["brand-new"], remove_tags=["original-tag"])
        assert "brand-new" in result.tags
        assert "original-tag" not in result.tags

    # --- Depends_on: add / remove -------------------------------------------

    def test_edit_add_deps(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with add_deps= appends to depends_on list."""
        result = engine.edit_task(task_id, add_deps=[7, 8])
        assert 5 in result.depends_on
        assert 7 in result.depends_on
        assert 8 in result.depends_on

    def test_edit_remove_deps(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with remove_deps= removes from depends_on list."""
        result = engine.edit_task(task_id, remove_deps=[5])
        assert 5 not in result.depends_on

    # --- Block / unblock ----------------------------------------------------

    def test_edit_block_task(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with blocked=True sets blocked field and stores reason."""
        result = engine.edit_task(task_id, blocked=True, block_reason="Waiting on dep 5")
        assert result.blocked is True
        assert result.block_reason == "Waiting on dep 5"

    def test_edit_unblock_task(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with blocked=False clears blocked and nulls block_reason."""
        engine.edit_task(task_id, blocked=True, block_reason="some reason")
        result = engine.edit_task(task_id, blocked=False)
        assert result.blocked is False
        assert result.block_reason is None

    # --- AC4: append_body with timestamp prefix -----------------------------

    def test_append_body_adds_content_to_body(self, engine: KanbanEngine, task_id: str) -> None:
        """append_body= appends text to the existing body."""
        result = engine.edit_task(task_id, append_body="## Appended section\nNew text")
        assert "## Appended section" in result.body
        assert "## Original" in result.body  # original body preserved

    def test_append_body_timestamp_prefix_format(self, engine: KanbanEngine, task_id: str) -> None:
        """append_body with timestamp=True prepends a [[YYYY-MM-DD]] date line."""
        result = engine.edit_task(task_id, append_body="Note added", timestamp=True)
        # The brief specifies [[YYYY-MM-DD]] format prefix
        pattern = r"\[\[\d{4}-\d{2}-\d{2}\]\]"
        assert re.search(pattern, result.body), f"Expected [[YYYY-MM-DD]] timestamp in body, got:\n{result.body}"

    def test_append_body_timestamp_appears_before_appended_text(self, engine: KanbanEngine, task_id: str) -> None:
        """Timestamp prefix appears before the appended content in the body."""
        result = engine.edit_task(task_id, append_body="Appended note text", timestamp=True)
        timestamp_match = re.search(r"\[\[\d{4}-\d{2}-\d{2}\]\]", result.body)
        assert timestamp_match is not None
        ts_pos = timestamp_match.start()
        appended_pos = result.body.find("Appended note text")
        assert ts_pos < appended_pos

    # --- Persistence --------------------------------------------------------

    def test_edit_persists_to_disk(self, kanban_dir: Path, engine: KanbanEngine, task_id: str) -> None:
        """Changes made by edit_task survive a reload from disk."""
        from owlbear_kanban.task_io import read_task  # noqa: PLC0415

        engine.edit_task(task_id, title="Persisted title")
        tasks_dir = kanban_dir / "tasks"
        files = list(tasks_dir.glob("*.md"))
        assert files, "No task files found after edit"
        loaded = read_task(files[0])
        assert loaded.title == "Persisted title"

    # --- Edge cases ---------------------------------------------------------

    def test_edit_no_changes_returns_unchanged_record(self, engine: KanbanEngine, task_id: str) -> None:
        """Calling edit_task with no change params returns the existing record."""
        before = engine.show_task(task_id)
        after = engine.edit_task(task_id)
        assert after.id == before.id
        assert after.title == before.title
        assert after.status == before.status

    # --- AC: updated timestamp changes on edit ------------------------------

    def test_edit_task_updated_timestamp_changes(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task must write a new 'updated' timestamp — it must differ from before."""
        import time

        before_updated = engine.show_task(task_id).updated
        time.sleep(0.01)  # ensure wall-clock advances before write
        result = engine.edit_task(task_id, title="Timestamp change probe")
        assert result.updated is not None
        assert result.updated != before_updated, (
            "edit_task must update the 'updated' field to a newer timestamp"
        )

    # --- AC: slug frozen at creation — filename unchanged after title edit --

    def test_edit_title_does_not_rename_task_file(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Slug frozen at creation: editing the title must not rename the task file."""
        record = engine.create_task("Slug Freeze Original")
        tasks_dir = kanban_dir / "tasks"
        original_name = next(tasks_dir.glob("*.md")).name

        engine.edit_task(str(record.id), title="Completely Different New Title")

        remaining = list(tasks_dir.glob("*.md"))
        assert len(remaining) == 1, "File count changed — edit_task must not create/delete files"
        assert remaining[0].name == original_name, (
            f"Slug frozen: filename must not change on title edit. "
            f"Expected {original_name!r}, got {remaining[0].name!r}"
        )


# ===========================================================================
# TestFromAC_MoveTask — AC5 + AC6 + AC7
# ===========================================================================


class TestFromAC_MoveTask:
    """Tests for AC5/AC6/AC7: move_task advances status, archives, rejects invalid."""

    @pytest.fixture()
    def task_id(self, engine: KanbanEngine) -> str:
        """Create one task at default status 'research' and return its id."""
        record = engine.create_task("Move me", status="research")
        return str(record.id)

    # --- AC5: move to valid status ------------------------------------------

    def test_move_task_to_todo(self, engine: KanbanEngine, task_id: str) -> None:
        """move_task('todo') changes status to 'todo'."""
        result = engine.move_task(task_id, "todo")
        assert result.status == "todo"

    def test_move_task_returns_task_record(self, engine: KanbanEngine, task_id: str) -> None:
        """move_task returns a Task."""
        result = engine.move_task(task_id, "backlog")
        assert isinstance(result, Task)

    def test_move_task_persists_status_change(self, kanban_dir: Path, engine: KanbanEngine, task_id: str) -> None:
        """Status change is written to disk and readable after move."""
        from owlbear_kanban.task_io import read_task  # noqa: PLC0415

        engine.move_task(task_id, "in-progress")
        tasks_dir = kanban_dir / "tasks"
        files = list(tasks_dir.glob("*.md"))
        assert files
        loaded = read_task(files[0])
        assert loaded.status == "in-progress"

    def test_move_task_from_todo_to_in_progress(self, engine: KanbanEngine, task_id: str) -> None:
        """move_task advances status correctly from todo to in-progress."""
        engine.move_task(task_id, "todo")
        result = engine.move_task(task_id, "in-progress")
        assert result.status == "in-progress"

    # --- AC6: move to archived ----------------------------------------------

    def test_move_task_to_archived(self, engine: KanbanEngine, task_id: str) -> None:
        """move_task('archived') succeeds — returns Task with archived marker."""
        result = engine.move_task(task_id, "archived")
        # Either status == "archived" or blocked-equivalent marker acceptable,
        # but the call must not raise.
        assert result is not None
        assert isinstance(result, Task)

    def test_move_task_archived_not_in_active_tasks(self, engine: KanbanEngine, task_id: str) -> None:
        """After archiving, the task does not appear in plain list_tasks()."""
        engine.move_task(task_id, "archived")
        active = engine.list_tasks()
        active_ids = [t.id for t in active]
        assert int(task_id) not in active_ids

    # --- AC7: invalid status rejected --------------------------------------

    def test_move_task_invalid_status_raises(self, engine: KanbanEngine, task_id: str) -> None:
        """move_task with a status not in config.statuses and not 'archived' raises."""
        with pytest.raises((ValueError, KeyError, LookupError)):
            engine.move_task(task_id, "nonexistent-status")

    def test_move_task_empty_string_status_raises(self, engine: KanbanEngine, task_id: str) -> None:
        """move_task with empty string status raises."""
        with pytest.raises((ValueError, KeyError, LookupError)):
            engine.move_task(task_id, "")

    def test_move_task_garbage_status_raises(self, engine: KanbanEngine, task_id: str) -> None:
        """move_task with completely arbitrary garbage string raises."""
        with pytest.raises((ValueError, KeyError, LookupError)):
            engine.move_task(task_id, "DEFINITELY_NOT_A_STATUS_🐻")

    # --- Boundary conditions ------------------------------------------------

    def test_move_task_to_done_valid_status(self, engine: KanbanEngine, task_id: str) -> None:
        """'done' is a valid status (last in the list) and should not raise."""
        result = engine.move_task(task_id, "done")
        assert result.status == "done"

    def test_move_task_to_review_valid_status(self, engine: KanbanEngine, task_id: str) -> None:
        """'review' is a valid status and should not raise."""
        result = engine.move_task(task_id, "review")
        assert result.status == "review"
