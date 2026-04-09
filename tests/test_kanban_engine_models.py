"""Failing tests for BoardConfig and TaskRecord Pydantic models (#713, RED phase).

AC coverage:
  AC1 - BoardConfig: version (int), board name (string), tasks_dir (string),
        statuses list (list of dicts with `name` key), priorities list,
        defaults (status, priority, class preserved), next_id,
        claim_timeout (duration string), tui section preserved via extra-fields,
        unknown-field preservation
  AC2 - TaskRecord: all frontmatter fields (id, title, status, priority, created,
        updated, tags, parent, depends_on, blocked, block_reason, claimed_by,
        claimed_at), markdown body, unknown-field round-trip
  AC3 - ISO 8601 timestamps stored as strings (not datetime objects)
  AC4 - All tests fail (no implementation yet)

Import path: owlbear_mcp_kanban.engine_models (module does not exist yet).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear_mcp_kanban.engine_models import (  # type: ignore[import-not-found]
    BoardConfig,
    TaskRecord,
)

# ---------------------------------------------------------------------------
# Sample data — mirrors .owlbear/kanban/config.yml structure
# ---------------------------------------------------------------------------

_MINIMAL_BOARD: dict = {
    "version": 10,
    "board": {"name": "OwlBear"},
    "tasks_dir": "tasks",
    "statuses": [
        {"name": "research"},
        {"name": "backlog"},
        {"name": "todo"},
        {"name": "in-progress"},
        {"name": "done"},
    ],
    "priorities": ["someday", "nice-to-have", "important", "needed", "critical"],
    "defaults": {"status": "research", "priority": "important"},
    "claim_timeout": "1h",
    "next_id": 734,
}

_FULL_BOARD: dict = {
    **_MINIMAL_BOARD,
    "defaults": {
        "status": "research",
        "priority": "important",
        "class": "standard",
    },
    "tui": {
        "title_lines": 2,
        "hide_empty_columns": True,
    },
    "extra_vendor_field": "preserved",
}

# mirrors task frontmatter (required fields only + empty body)
_MINIMAL_TASK: dict = {
    "id": 42,
    "title": "Test task title",
    "status": "todo",
    "priority": "important",
    "created": "2026-04-09T03:24:26.6974428+02:00",
    "updated": "2026-04-09T04:00:00.0000000+02:00",
    "body": "",
}

# mirrors a real claimed task file with all optional fields
_FULL_TASK: dict = {
    "id": 713,
    "title": "P3-01: RED — Pydantic models for BoardConfig and TaskRecord",
    "status": "todo",
    "priority": "needed",
    "created": "2026-04-09T03:24:26.6974428+02:00",
    "updated": "2026-04-09T04:51:06.0077929+02:00",
    "tags": ["kanban", "phase-3", "type:test"],
    "parent": 712,
    "depends_on": [711, 710],
    "blocked": False,
    "block_reason": None,
    "claimed_by": "river-port",
    "claimed_at": "2026-04-09T04:51:06.00674+02:00",
    "class": "standard",
    "started": "2026-04-09T04:55:00.0000000+02:00",
    "body": "## Objective\nSome markdown content here.\n\n- item 1\n- item 2\n",
}


# ===========================================================================
# TestFromAC_BoardConfig
# ===========================================================================


class TestFromAC_BoardConfig:
    """Tests for AC1: BoardConfig Pydantic model covering all config.yml fields."""

    # --- Happy path ---------------------------------------------------------

    def test_full_config_parses_without_error(self) -> None:
        """Full config.yml data round-trips through BoardConfig without ValidationError."""
        config = BoardConfig.model_validate(_FULL_BOARD)
        assert config is not None

    def test_minimal_config_parses_without_error(self) -> None:
        """Minimal config (no tui or extra fields) parses successfully."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert config is not None

    def test_version_is_int(self) -> None:
        """version field is an int, not a string."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.version, int)
        assert config.version == 10

    def test_board_name_is_str(self) -> None:
        """board.name is a str and equals the configured board name."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.board.name, str)
        assert config.board.name == "OwlBear"

    def test_tasks_dir_is_str(self) -> None:
        """tasks_dir field is a str pointing to the task directory."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.tasks_dir, str)
        assert config.tasks_dir == "tasks"

    def test_statuses_is_list_of_dicts_with_name_key(self) -> None:
        """statuses is a list of dicts; each entry has a 'name' key."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.statuses, list)
        assert len(config.statuses) > 0
        for status in config.statuses:
            assert "name" in status or hasattr(status, "name")

    def test_priorities_is_list_of_strings(self) -> None:
        """priorities is a non-empty list of strings."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.priorities, list)
        assert all(isinstance(p, str) for p in config.priorities)

    def test_next_id_is_int(self) -> None:
        """next_id field is an int used for task ID generation."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.next_id, int)
        assert config.next_id == 734

    def test_claim_timeout_is_str(self) -> None:
        """claim_timeout is a duration string (e.g. '1h'), not a timedelta."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.claim_timeout, str)
        assert config.claim_timeout == "1h"

    # --- Defaults sub-object ------------------------------------------------

    def test_defaults_status_accessible(self) -> None:
        """defaults.status is a string with the default task status."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.defaults.status, str)
        assert config.defaults.status == "research"

    def test_defaults_priority_accessible(self) -> None:
        """defaults.priority is a string with the default task priority."""
        config = BoardConfig.model_validate(_MINIMAL_BOARD)
        assert isinstance(config.defaults.priority, str)
        assert config.defaults.priority == "important"

    def test_defaults_class_preserved_via_extra_fields(self) -> None:
        """defaults.class is a Python reserved word but preserved via extra-fields round-trip."""
        config = BoardConfig.model_validate(_FULL_BOARD)
        dumped = config.model_dump()
        assert dumped["defaults"]["class"] == "standard"

    # --- Extra/unknown field preservation -----------------------------------

    def test_tui_section_preserved_in_dump(self) -> None:
        """tui section is preserved when model is dumped back to dict."""
        config = BoardConfig.model_validate(_FULL_BOARD)
        dumped = config.model_dump()
        assert "tui" in dumped
        assert dumped["tui"]["title_lines"] == 2
        assert dumped["tui"]["hide_empty_columns"] is True

    def test_unknown_top_level_field_preserved(self) -> None:
        """Unknown top-level fields survive BoardConfig round-trip unchanged."""
        config = BoardConfig.model_validate(_FULL_BOARD)
        dumped = config.model_dump()
        assert dumped.get("extra_vendor_field") == "preserved"

    # --- Error paths --------------------------------------------------------

    def test_missing_version_raises_validation_error(self) -> None:
        """Omitting version raises Pydantic ValidationError."""
        data = {k: v for k, v in _MINIMAL_BOARD.items() if k != "version"}
        with pytest.raises(ValidationError):
            BoardConfig.model_validate(data)

    def test_missing_statuses_raises_validation_error(self) -> None:
        """Omitting statuses raises Pydantic ValidationError."""
        data = {k: v for k, v in _MINIMAL_BOARD.items() if k != "statuses"}
        with pytest.raises(ValidationError):
            BoardConfig.model_validate(data)


# ===========================================================================
# TestFromAC_TaskRecord
# ===========================================================================


class TestFromAC_TaskRecord:
    """Tests for AC2/AC3: TaskRecord Pydantic model covering all task frontmatter fields."""

    # --- Happy path ---------------------------------------------------------

    def test_full_task_parses_without_error(self) -> None:
        """Full task data with all optional fields parses without ValidationError."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert task is not None

    def test_minimal_task_parses_without_error(self) -> None:
        """Minimal task (required fields only) parses successfully."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task is not None

    def test_all_required_frontmatter_fields_accessible(self) -> None:
        """id, title, status, priority, created, updated all accessible on parsed task."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.id == 42
        assert task.title == "Test task title"
        assert task.status == "todo"
        assert task.priority == "important"
        assert task.created == _MINIMAL_TASK["created"]
        assert task.updated == _MINIMAL_TASK["updated"]

    def test_body_stored_as_str(self) -> None:
        """body field stores the markdown content as a plain string."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.body, str)
        assert "## Objective" in task.body

    def test_empty_body_accepted(self) -> None:
        """body='' (no markdown content) is valid."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.body == ""

    def test_tags_populated_from_data(self) -> None:
        """tags field stores a list of strings from YAML frontmatter."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert task.tags == ["kanban", "phase-3", "type:test"]

    def test_parent_stored_as_int(self) -> None:
        """parent field is an int when set."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.parent, int)
        assert task.parent == 712

    def test_depends_on_is_list_of_ints(self) -> None:
        """depends_on field is a list of int task IDs."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.depends_on, list)
        assert task.depends_on == [711, 710]

    def test_blocked_stored_as_bool(self) -> None:
        """blocked field is a bool."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.blocked, bool)

    def test_claimed_by_stored_as_str(self) -> None:
        """claimed_by field is a str when a claim is present."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.claimed_by, str)
        assert task.claimed_by == "river-port"

    # --- Default values for optional fields ---------------------------------

    def test_tags_default_to_empty_list(self) -> None:
        """tags defaults to [] when not present in frontmatter."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.tags == []

    def test_depends_on_defaults_to_empty_list(self) -> None:
        """depends_on defaults to [] when not present in frontmatter."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.depends_on == []

    def test_parent_defaults_to_none(self) -> None:
        """parent defaults to None when not present in frontmatter."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.parent is None

    def test_blocked_defaults_to_false(self) -> None:
        """blocked defaults to False when not present in frontmatter."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.blocked is False

    def test_block_reason_defaults_to_none(self) -> None:
        """block_reason defaults to None when not present in frontmatter."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.block_reason is None

    def test_claimed_by_defaults_to_none(self) -> None:
        """claimed_by defaults to None when no claim is active."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.claimed_by is None

    def test_claimed_at_defaults_to_none(self) -> None:
        """claimed_at defaults to None when no claim is active."""
        task = TaskRecord.model_validate(_MINIMAL_TASK)
        assert task.claimed_at is None

    # --- AC3: ISO 8601 timestamps must be strings, not datetime objects ------

    def test_created_is_str_not_datetime(self) -> None:
        """created is stored as a str, not coerced to datetime (avoids precision drift)."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.created, str)

    def test_updated_is_str_not_datetime(self) -> None:
        """updated is stored as a str, not coerced to datetime."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.updated, str)

    def test_claimed_at_is_str_not_datetime(self) -> None:
        """claimed_at is stored as a str, not coerced to datetime."""
        task = TaskRecord.model_validate(_FULL_TASK)
        assert isinstance(task.claimed_at, str)

    def test_go_nanosecond_precision_preserved_verbatim(self) -> None:
        """7-digit nanosecond timestamp string is stored verbatim (no truncation to microseconds)."""
        go_timestamp = "2026-04-09T03:24:26.6974428+02:00"  # 7 decimal places (Go format)
        data = {**_MINIMAL_TASK, "created": go_timestamp}
        task = TaskRecord.model_validate(data)
        assert task.created == go_timestamp  # Must not be truncated to 6 decimal places

    # --- Unknown-field round-trip preservation --------------------------------

    def test_class_field_preserved_in_round_trip(self) -> None:
        """class (standard Python reserved word in YAML) survives TaskRecord round-trip."""
        task = TaskRecord.model_validate(_FULL_TASK)
        dumped = task.model_dump()
        assert dumped.get("class") == "standard"

    def test_started_field_preserved_in_round_trip(self) -> None:
        """started timestamp (set by kanban-md on claim) preserved in round-trip."""
        task = TaskRecord.model_validate(_FULL_TASK)
        dumped = task.model_dump()
        assert dumped.get("started") == _FULL_TASK["started"]

    def test_completed_field_preserved_in_round_trip(self) -> None:
        """completed timestamp survives round-trip when present."""
        data = {**_FULL_TASK, "completed": "2026-04-09T06:00:00.0000000+02:00"}
        task = TaskRecord.model_validate(data)
        dumped = task.model_dump()
        assert dumped.get("completed") == "2026-04-09T06:00:00.0000000+02:00"

    # --- Error paths --------------------------------------------------------

    def test_missing_id_raises_validation_error(self) -> None:
        """Omitting id raises Pydantic ValidationError."""
        data = {k: v for k, v in _MINIMAL_TASK.items() if k != "id"}
        with pytest.raises(ValidationError):
            TaskRecord.model_validate(data)

    def test_missing_title_raises_validation_error(self) -> None:
        """Omitting title raises Pydantic ValidationError."""
        data = {k: v for k, v in _MINIMAL_TASK.items() if k != "title"}
        with pytest.raises(ValidationError):
            TaskRecord.model_validate(data)

    def test_missing_status_raises_validation_error(self) -> None:
        """Omitting status raises Pydantic ValidationError."""
        data = {k: v for k, v in _MINIMAL_TASK.items() if k != "status"}
        with pytest.raises(ValidationError):
            TaskRecord.model_validate(data)

    def test_missing_priority_raises_validation_error(self) -> None:
        """Omitting priority raises Pydantic ValidationError."""
        data = {k: v for k, v in _MINIMAL_TASK.items() if k != "priority"}
        with pytest.raises(ValidationError):
            TaskRecord.model_validate(data)
