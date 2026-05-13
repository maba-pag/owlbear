"""Failing tests for kanban config path-escape validation (#1351).

All tests must be RED (failing) until the builder implements:
  - ERR_PATH_ESCAPE in errors.KANBAN_ERROR_CODES
  - PathsConfig field_validator rejecting absolute / parent-traversing paths
  - validate_config_path_containment() string-level helper in _naming.py
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from owlbear_kanban._naming import validate_path_containment
from owlbear_kanban.errors import KANBAN_ERROR_CODES, ConfigError
from owlbear_kanban.models import PathsConfig

# ---------------------------------------------------------------------------
# Shared board config YAML used by storage-level and engine-level tests
# Uses standard statuses/priorities so KanbanEngine can init without error.
# ---------------------------------------------------------------------------

_STORAGE_BOARD_CONFIG_YAML = """\
next_id: 1
"""


# ---------------------------------------------------------------------------
# AC1 — Error code must be registered in the error catalogue
# ---------------------------------------------------------------------------


class TestFromAC_ErrorCodeRegistration:
    """AC1 — ERR_PATH_ESCAPE must exist in KANBAN_ERROR_CODES before use."""

    def test_err_path_escape_in_kanban_error_codes(self) -> None:
        """ERR_PATH_ESCAPE is a registered error code in the kanban error catalogue."""
        assert "ERR_PATH_ESCAPE" in KANBAN_ERROR_CODES


# ---------------------------------------------------------------------------
# AC1, AC4 — PathsConfig validator rejects absolute / parent-traversing paths
# ---------------------------------------------------------------------------


class TestFromAC_PathsConfigValidation:
    """AC1, AC4 — PathsConfig rejects dangerous path strings at parse time."""

    # --- error paths (AC1, AC4) ---

    def test_rejects_tasks_dir_parent_traversal(self) -> None:
        """'../outside' in tasks_dir must raise ConfigError (ERR_PATH_ESCAPE)."""
        with pytest.raises(ConfigError) as exc_info:
            PathsConfig(tasks_dir="../outside")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_rejects_archive_dir_parent_traversal(self) -> None:
        """'../outside' in archive_dir must raise ConfigError (ERR_PATH_ESCAPE)."""
        with pytest.raises(ConfigError) as exc_info:
            PathsConfig(archive_dir="../outside")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_rejects_tasks_dir_absolute_posix(self) -> None:
        """'/etc/shadow' in tasks_dir (absolute POSIX path) must raise ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            PathsConfig(tasks_dir="/etc/shadow")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_rejects_archive_dir_absolute_posix(self) -> None:
        """'/etc/shadow' in archive_dir (absolute POSIX path) must raise ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            PathsConfig(archive_dir="/etc/shadow")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_rejects_tasks_dir_absolute_windows(self) -> None:
        r"""'C:\Windows' (Windows absolute path) in tasks_dir must raise ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            PathsConfig(tasks_dir="C:\\Windows")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_rejects_tasks_dir_deep_traversal(self) -> None:
        """'tasks/../../escape' (embedded '..') must raise ConfigError (ERR_PATH_ESCAPE)."""
        with pytest.raises(ConfigError) as exc_info:
            PathsConfig(tasks_dir="tasks/../../escape")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_rejects_archive_dir_deep_traversal(self) -> None:
        """'archive/../../../etc' must raise ConfigError (ERR_PATH_ESCAPE)."""
        with pytest.raises(ConfigError) as exc_info:
            PathsConfig(archive_dir="archive/../../../etc")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_empty_string_tasks_dir_is_boundary(self) -> None:
        """Empty tasks_dir string must be rejected at config-time with ERR_PATH_ESCAPE.

        An empty string resolves to kanban_dir itself, which is not a valid relative
        subdirectory name. The config-time helper must reject it explicitly.
        """
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            validate_config_path_containment("")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    # --- happy paths (depend on new helper existing — fail in RED via ImportError) ---

    def test_valid_relative_tasks_dir_accepted(self) -> None:
        """AC4, AC5 — 'custom-tasks' must be accepted by both helper and PathsConfig."""
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        validate_config_path_containment("custom-tasks")  # must not raise
        config = PathsConfig(tasks_dir="custom-tasks")
        assert config.tasks_dir == "custom-tasks"

    def test_valid_relative_archive_subpath_accepted(self) -> None:
        """AC5 — 'sub/archive' (multi-segment relative path) must be accepted."""
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        validate_config_path_containment("sub/archive")  # must not raise
        config = PathsConfig(archive_dir="sub/archive")
        assert config.archive_dir == "sub/archive"


# ---------------------------------------------------------------------------
# AC3 — String-level helper must live in _naming.py
# ---------------------------------------------------------------------------


class TestFromAC_NamingHelper:
    """AC3 — validate_config_path_containment() must be importable from _naming."""

    def test_helper_exists_in_naming_module(self) -> None:
        """validate_config_path_containment is importable from owlbear_kanban._naming."""
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        assert callable(validate_config_path_containment)

    def test_helper_rejects_absolute_posix_path(self) -> None:
        """Helper raises ConfigError for an absolute POSIX path string."""
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            validate_config_path_containment("/absolute/path")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_helper_rejects_parent_traversal(self) -> None:
        """Helper raises ConfigError for a string containing '..' component."""
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            validate_config_path_containment("../escape")
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_helper_accepts_plain_relative_name(self) -> None:
        """Helper accepts a plain relative directory name without raising."""
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        validate_config_path_containment("custom-tasks")  # must not raise
        validate_config_path_containment("tasks")  # must not raise
        validate_config_path_containment("archive")  # must not raise


# ---------------------------------------------------------------------------
# AC2 — Runtime defense-in-depth via existing validate_path_containment()
# ---------------------------------------------------------------------------


class TestFromAC_RuntimeDefense:
    """AC2, AC4 — validate_path_containment() remains the runtime resolve-level guard."""

    def test_runtime_rejects_path_outside_kanban_dir(self, tmp_path: Path) -> None:
        """AC2 — runtime validate_path_containment() rejects escape after config validation.

        Config-time helper verifies 'tasks' is safe; runtime layer then provides
        defense-in-depth by rejecting resolved paths that escape the board directory.
        """
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        (kanban_dir / "tasks").mkdir()
        outside = tmp_path / "secret.md"
        outside.touch()

        # Config-time: 'tasks' is valid
        validate_config_path_containment("tasks")  # must not raise
        # Runtime: path that resolves outside must be rejected
        with pytest.raises(PermissionError):
            validate_path_containment(kanban_dir / "tasks", outside)

    def test_symlink_pointing_outside_rejected_at_runtime(self, tmp_path: Path) -> None:
        """AC4 — symlink in tasks_dir pointing outside kanban_dir is rejected at runtime.

        Config-time validation accepts 'tasks' (valid relative name) but resolve-level
        validate_path_containment() catches the symlink escape — defense-in-depth.
        """
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # "tasks" looks valid at config-time (relative, no '..')
        validate_config_path_containment("tasks")  # must not raise

        # At runtime, tasks_dir is a symlink that escapes the board directory
        tasks_link = kanban_dir / "tasks"
        tasks_link.symlink_to(outside_dir)
        outside_file = outside_dir / "leaked.md"
        outside_file.touch()

        # Runtime resolve-level check must catch the symlinked directory escape.
        # Assert against tasks_link (the derived directory itself) — not a file inside it.
        with pytest.raises(PermissionError):
            validate_path_containment(kanban_dir, tasks_link)

    def test_refresh_config_rejects_symlink_escape(self, tmp_path: Path) -> None:
        """AC2 — refresh_config validates derived paths after rebinding.

        After refresh_config rebinds _tasks_dir to a symlinked directory that resolves
        outside kanban_dir, PermissionError must be raised — not silently accepted.
        This proves that the runtime resolve-level defense is active after a config reload,
        not only at engine construction time.
        """
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (kanban_dir / "tasks").mkdir()
        (kanban_dir / "archive").mkdir()
        (kanban_dir / "config.yml").write_text(
            _STORAGE_BOARD_CONFIG_YAML, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir, activity_log=False)

        # Precondition: engine constructed successfully with valid config.
        assert engine.tasks_dir == kanban_dir / "tasks"

        # Create a symlink "alt-tasks" inside kanban_dir that resolves outside the board.
        alt_tasks_link = kanban_dir / "alt-tasks"
        alt_tasks_link.symlink_to(outside_dir)

        # Update config.yml so tasks_dir names the symlink.
        updated_config = _STORAGE_BOARD_CONFIG_YAML.replace(
            "  tasks_dir: tasks", "  tasks_dir: alt-tasks"
        )
        (kanban_dir / "config.yml").write_text(updated_config, encoding="utf-8")

        # refresh_config must detect that alt-tasks resolves outside kanban_dir.
        with pytest.raises(PermissionError):
            engine.refresh_config()


# ---------------------------------------------------------------------------
# AC5 — BoardConfig integration: valid relative configs load without regression
# ---------------------------------------------------------------------------


class TestFromAC_BoardConfigIntegration:
    """AC5 — Full BoardConfig loading with config-validated paths works end-to-end."""

    _BASE: ClassVar[dict] = {
        "schema": "grouped",
        "statuses": ["research", "backlog", "done"],
        "priorities": ["someday", "important", "critical"],
        "next_id": 1,
        "activity_log": True,
        "pipeline": {
            "entry_status": "research",
            "terminal_status": "done",
            "wave_size": 4,
            "claim_timeout": "1h",
            "default_priority": "important",
        },
        "agents": {
            "agent_map": {"research": [], "backlog": [], "done": []},
            "agent_types": {},
            "agent_compatibility": {},
        },
        "policy": {
            "non_impl_tags": [],
            "archival_reasons": ["completed", "dropped"],
            "status_predicates": {},
        },
    }

    def test_board_config_with_default_relative_paths_loads(self) -> None:
        """AC5 — BoardConfig with tasks='tasks', archive='archive' still loads."""
        from owlbear_kanban._naming import validate_config_path_containment  # noqa: PLC0415
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        data = {**self._BASE, "paths": {"tasks_dir": "tasks", "archive_dir": "archive"}}
        # Precondition: helper accepts these paths
        validate_config_path_containment("tasks")
        validate_config_path_containment("archive")
        config = BoardConfig(**data)
        assert config.paths.tasks_dir == "tasks"
        assert config.paths.archive_dir == "archive"

    def test_board_config_with_traversal_in_tasks_dir_rejects(self) -> None:
        """AC1 — BoardConfig with '../tasks' in paths.tasks_dir raises ConfigError."""
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        data = {
            **self._BASE,
            "paths": {"tasks_dir": "../tasks", "archive_dir": "archive"},
        }
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(**data)
        assert exc_info.value.code == "ERR_PATH_ESCAPE"

    def test_list_task_files_with_nondefault_relative_path(
        self, tmp_path: Path
    ) -> None:
        """AC5 — list_task_files works end-to-end when tasks_dir is a nested relative subdir.

        Proves path derivation for non-default relative subdirectories: list_task_files
        resolves the configured sub/tasks directory and returns an empty list when the
        directory does not yet exist (graceful empty-directory handling).
        """
        from owlbear_kanban.storage import list_task_files  # noqa: PLC0415

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        config_yaml = _STORAGE_BOARD_CONFIG_YAML.replace(
            "  tasks_dir: tasks", "  tasks_dir: sub/tasks"
        ).replace("  archive_dir: archive", "  archive_dir: sub/archive")
        (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
        # sub/tasks is intentionally absent — list_task_files must return [] not raise.

        result = list_task_files(kanban_dir)

        assert result == []

    def test_move_to_archive_with_nested_subdir(self, tmp_path: Path) -> None:
        """AC5 — move_to_archive places task files in a nested archive subdirectory.

        Proves that the archive_dir path derivation works for non-default relative
        subdirectories: a task file is moved to kanban_dir/sub/archive/ and the
        directory is created automatically.
        """
        from owlbear_kanban.storage import move_to_archive  # noqa: PLC0415

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        config_yaml = _STORAGE_BOARD_CONFIG_YAML.replace(
            "  archive_dir: archive", "  archive_dir: sub/archive"
        )
        (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")

        tasks_dir = kanban_dir / "tasks"
        tasks_dir.mkdir()
        task_file = tasks_dir / "1-test-task.md"
        task_file.write_text(
            "---\nid: 1\nstatus: done\n---\nTest task.\n", encoding="utf-8"
        )

        archived_path = move_to_archive(1, kanban_dir)

        expected_archive_dir = kanban_dir / "sub" / "archive"
        assert archived_path.parent == expected_archive_dir
        assert archived_path.name == "1-test-task.md"
        assert archived_path.exists()
