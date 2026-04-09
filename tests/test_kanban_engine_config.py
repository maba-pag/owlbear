"""Failing tests for config.yml loader — ruamel.yaml round-trip (#715, RED phase).

AC coverage:
  AC1 - load_config(kanban_dir) returns BoardConfig with correct statuses (list of
        dicts), priorities, defaults, next_id
  AC2 - Round-trip (load, save, reload) produces identical data and preserves
        field order
  AC3 - YAML comments and unknown/vendor fields survive round-trip unchanged
  AC4 - next_id increment: load → mutate → save → reload → new value confirmed
  AC5 - Timestamp resolver disabled: date-like strings remain str, not datetime/timedelta

Import path: owlbear_mcp_kanban.config_loader (module does NOT exist yet).
All tests must FAIL at this stage — GREEN phase is task #716.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_mcp_kanban.config_loader import (  # type: ignore[import-not-found]
    load_config,
    save_config,
)
from owlbear_mcp_kanban.engine_models import BoardConfig  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Shared fixture config content — mirrors real .owlbear/kanban/config.yml
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

_ANNOTATED_CONFIG_YAML = """\
# Board configuration — managed by owlbear
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: research
    - name: backlog
    - name: todo
    - name: in-progress
    - name: done
priorities:
    - someday
    - nice-to-have
    - important  # default priority
    - needed
    - critical
defaults:
    status: research
    priority: important
    class: standard
claim_timeout: 1h  # duration string, must not become timedelta
tui:
    title_lines: 2
    hide_empty_columns: true
extra_vendor_field: preserved-value
next_id: 200
"""

_DATE_STRING_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: backlog
    - name: done
priorities:
    - important
defaults:
    status: backlog
    priority: important
claim_timeout: 1h
snapshot_date: "2026-04-09"
snapshot_ts: "2026-04-09T03:25:03.4706335+02:00"
next_id: 50
"""


# ===========================================================================
# TestFromAC_LoadConfig
# ===========================================================================


class TestFromAC_LoadConfig:
    """Tests for AC1: load_config returns BoardConfig with correct field values."""

    # --- Happy path ---------------------------------------------------------

    def test_load_returns_board_config_instance(self, tmp_path: Path) -> None:
        """load_config(kanban_dir) returns a BoardConfig instance."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        result = load_config(tmp_path)
        assert isinstance(result, BoardConfig)

    def test_statuses_is_list_of_seven_dicts(self, tmp_path: Path) -> None:
        """statuses field has 7 entries (matching real board config)."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert isinstance(config.statuses, list)
        assert len(config.statuses) == 7

    def test_each_status_is_dict_with_name_key(self, tmp_path: Path) -> None:
        """Each entry in statuses is a dict-like object with a 'name' key."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        for entry in config.statuses:
            assert "name" in entry

    def test_priorities_list_contains_expected_values(self, tmp_path: Path) -> None:
        """priorities is a list with the 5 canonical priority strings."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert list(config.priorities) == [
            "someday",
            "nice-to-have",
            "important",
            "needed",
            "critical",
        ]

    def test_defaults_status_is_research(self, tmp_path: Path) -> None:
        """defaults.status equals 'research'."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert config.defaults.status == "research"

    def test_defaults_priority_is_important(self, tmp_path: Path) -> None:
        """defaults.priority equals 'important'."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert config.defaults.priority == "important"

    def test_next_id_is_integer(self, tmp_path: Path) -> None:
        """next_id is an int, not a string."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert isinstance(config.next_id, int)
        assert config.next_id == 100

    def test_version_is_integer(self, tmp_path: Path) -> None:
        """version is an int."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert isinstance(config.version, int)
        assert config.version == 10

    def test_claim_timeout_is_string_not_timedelta(self, tmp_path: Path) -> None:
        """claim_timeout '1h' is loaded as str, not datetime.timedelta."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert isinstance(config.claim_timeout, str)
        assert config.claim_timeout == "1h"

    # --- Error paths --------------------------------------------------------

    def test_missing_config_yml_raises_file_not_found(self, tmp_path: Path) -> None:
        """load_config raises FileNotFoundError when config.yml is absent."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path)

    def test_empty_directory_raises_error(self, tmp_path: Path) -> None:
        """load_config on an empty directory raises FileNotFoundError."""
        empty = tmp_path / "empty_kanban"
        empty.mkdir()
        with pytest.raises(FileNotFoundError):
            load_config(empty)


# ===========================================================================
# TestFromAC_RoundTrip
# ===========================================================================


class TestFromAC_RoundTrip:
    """Tests for AC2: load → save → reload produces identical data and field order."""

    def test_roundtrip_version_unchanged(self, tmp_path: Path) -> None:
        """version is identical after load → save → reload."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert reloaded.version == config.version

    def test_roundtrip_statuses_unchanged(self, tmp_path: Path) -> None:
        """statuses list is identical after load → save → reload."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert list(reloaded.statuses) == list(config.statuses)

    def test_roundtrip_next_id_unchanged(self, tmp_path: Path) -> None:
        """next_id is unchanged after load → save → reload."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert reloaded.next_id == config.next_id

    def test_roundtrip_field_order_preserved_in_yaml(self, tmp_path: Path) -> None:
        """YAML field order is identical before and after round-trip (ruamel.yaml lossless)."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        original_keys = [
            line.split(":")[0].rstrip()
            for line in _BASE_CONFIG_YAML.splitlines()
            if ":" in line and not line.startswith(" ") and not line.startswith("-")
        ]
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        roundtripped_text = config_path.read_text(encoding="utf-8")
        roundtripped_keys = [
            line.split(":")[0].rstrip()
            for line in roundtripped_text.splitlines()
            if ":" in line and not line.startswith(" ") and not line.startswith("-")
        ]
        assert original_keys == roundtripped_keys

    def test_roundtrip_defaults_class_preserved(self, tmp_path: Path) -> None:
        """defaults.class ('standard') survives a round-trip (vendor/extra field)."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        roundtripped_text = (tmp_path / "config.yml").read_text(encoding="utf-8")
        assert "class: standard" in roundtripped_text

    def test_roundtrip_config_is_valid_board_config_instance(self, tmp_path: Path) -> None:
        """Reloaded config is a valid BoardConfig after round-trip."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert isinstance(reloaded, BoardConfig)


# ===========================================================================
# TestFromAC_PreservesCommentsAndUnknownFields
# ===========================================================================


class TestFromAC_PreservesCommentsAndUnknownFields:
    """Tests for AC3: YAML comments and unknown/vendor fields survive round-trip."""

    def test_block_comment_survives_roundtrip(self, tmp_path: Path) -> None:
        """Block comment on first line ('# Board configuration') survives round-trip."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(_ANNOTATED_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        text_after = config_path.read_text(encoding="utf-8")
        assert "# Board configuration" in text_after

    def test_inline_comment_on_priority_survives_roundtrip(self, tmp_path: Path) -> None:
        """Inline comment ('# default priority') on priorities line survives round-trip."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(_ANNOTATED_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        text_after = config_path.read_text(encoding="utf-8")
        assert "# default priority" in text_after

    def test_inline_comment_on_claim_timeout_survives_roundtrip(self, tmp_path: Path) -> None:
        """Inline comment on claim_timeout line survives round-trip."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(_ANNOTATED_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        text_after = config_path.read_text(encoding="utf-8")
        assert "# duration string" in text_after

    def test_tui_section_preserved_after_roundtrip(self, tmp_path: Path) -> None:
        """tui section (unknown vendor block) is preserved after round-trip."""
        (tmp_path / "config.yml").write_text(_ANNOTATED_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        text_after = (tmp_path / "config.yml").read_text(encoding="utf-8")
        assert "tui:" in text_after
        assert "title_lines" in text_after

    def test_extra_vendor_field_preserved_after_roundtrip(self, tmp_path: Path) -> None:
        """Unknown top-level vendor field ('extra_vendor_field') survives round-trip."""
        (tmp_path / "config.yml").write_text(_ANNOTATED_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        text_after = (tmp_path / "config.yml").read_text(encoding="utf-8")
        assert "extra_vendor_field: preserved-value" in text_after

    def test_extra_vendor_field_accessible_in_model(self, tmp_path: Path) -> None:
        """Unknown top-level vendor field is accessible via BoardConfig extra fields."""
        (tmp_path / "config.yml").write_text(_ANNOTATED_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        dumped = config.model_dump()
        assert dumped.get("extra_vendor_field") == "preserved-value"


# ===========================================================================
# TestFromAC_NextIdIncrement
# ===========================================================================


class TestFromAC_NextIdIncrement:
    """Tests for AC4: next_id can be incremented, saved, and reloaded with new value."""

    def test_increment_next_id_persists_after_save_and_reload(self, tmp_path: Path) -> None:
        """Incrementing next_id then saving persists the new value on reload."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        original_next_id = config.next_id
        config.next_id = original_next_id + 1
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert reloaded.next_id == original_next_id + 1

    def test_increment_from_near_zero_persists(self, tmp_path: Path) -> None:
        """next_id incremented from 1 persists as 2 after save/reload."""
        minimal_yaml = _BASE_CONFIG_YAML.replace("next_id: 100", "next_id: 1")
        (tmp_path / "config.yml").write_text(minimal_yaml, encoding="utf-8")
        config = load_config(tmp_path)
        assert config.next_id == 1
        config.next_id = 2
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert reloaded.next_id == 2

    def test_increment_does_not_alter_other_fields(self, tmp_path: Path) -> None:
        """Saving after next_id increment leaves all other fields unchanged."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        config.next_id += 1
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert reloaded.version == 10
        assert reloaded.defaults.status == "research"
        assert list(reloaded.priorities) == [
            "someday",
            "nice-to-have",
            "important",
            "needed",
            "critical",
        ]

    def test_multiple_increments_accumulate_correctly(self, tmp_path: Path) -> None:
        """Multiple save cycles increment next_id cumulatively."""
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        for expected_id in range(101, 104):
            config = load_config(tmp_path)
            config.next_id = expected_id
            save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        assert reloaded.next_id == 103


# ===========================================================================
# TestFromAC_TimestampResolverDisabled
# ===========================================================================


class TestFromAC_TimestampResolverDisabled:
    """Tests for AC5: ruamel.yaml timestamp resolver disabled — no auto type coercion."""

    def test_iso_date_string_remains_str_not_datetime(self, tmp_path: Path) -> None:
        """A date-like field ('2026-04-09') stays as str after load, not datetime.date."""
        import datetime

        (tmp_path / "config.yml").write_text(_DATE_STRING_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        dumped = config.model_dump()
        snapshot_date = dumped.get("snapshot_date")
        assert snapshot_date is not None
        assert not isinstance(snapshot_date, datetime.date)
        assert isinstance(snapshot_date, str)
        assert snapshot_date == "2026-04-09"

    def test_iso_datetime_string_remains_str_not_datetime(self, tmp_path: Path) -> None:
        """A full ISO 8601 datetime field stays as str after load, not datetime.datetime."""
        import datetime

        (tmp_path / "config.yml").write_text(_DATE_STRING_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        dumped = config.model_dump()
        snapshot_ts = dumped.get("snapshot_ts")
        assert snapshot_ts is not None
        assert not isinstance(snapshot_ts, datetime.datetime)
        assert isinstance(snapshot_ts, str)
        assert "2026-04-09" in snapshot_ts

    def test_claim_timeout_duration_string_is_str_not_timedelta(self, tmp_path: Path) -> None:
        """claim_timeout '1h' is a str, not datetime.timedelta, after load."""
        import datetime

        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        assert not isinstance(config.claim_timeout, datetime.timedelta)
        assert isinstance(config.claim_timeout, str)

    def test_date_string_roundtrips_as_str(self, tmp_path: Path) -> None:
        """A date-like extra field round-trips load → save → reload as str."""
        import datetime

        (tmp_path / "config.yml").write_text(_DATE_STRING_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)
        dumped = reloaded.model_dump()
        snapshot_date = dumped.get("snapshot_date")
        assert isinstance(snapshot_date, str)
        assert not isinstance(snapshot_date, datetime.date)


# ===========================================================================
# TestBuilderDiscovered
# ===========================================================================


class TestBuilderDiscovered:
    """Builder-discovered coverage gaps for uncovered branches in config_loader.py."""

    def test_save_config_creates_file_when_not_exists(self, tmp_path: Path) -> None:
        """save_config creates config.yml from scratch when file does not yet exist.

        Covers the ``else: raw = CommentedMap()`` branch in save_config
        (line 78 — config_path.exists() is False).
        """
        from owlbear_mcp_kanban.engine_models import BoardDefaults, BoardInfo

        config = BoardConfig(
            version=1,
            board=BoardInfo(name="NewBoard"),
            tasks_dir="tasks",
            statuses=[{"name": "todo"}, {"name": "done"}],
            priorities=["important"],
            defaults=BoardDefaults(status="todo", priority="important"),
            next_id=1,
            claim_timeout="30m",
        )
        config_path = tmp_path / "config.yml"
        assert not config_path.exists()

        save_config(tmp_path, config)

        assert config_path.exists()
        reloaded = load_config(tmp_path)
        assert reloaded.version == 1
        assert reloaded.next_id == 1

    def test_save_config_updates_changed_scalar_in_same_length_sequence(self, tmp_path: Path) -> None:
        """Changing a scalar item in a same-length sequence persists via save.

        Covers ``elif old_item != new_item: old_value[i] = new_item``
        (lines 119-120) — the priorities list has same length but one item changed.
        """
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        # Mutate one priority in-place (same length, changed scalar value)
        new_priorities = list(config.priorities)
        new_priorities[0] = "asap"
        config.priorities = new_priorities

        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)

        assert reloaded.priorities[0] == "asap"
        assert len(reloaded.priorities) == len(new_priorities)

    def test_save_config_replaces_sequence_on_length_change(self, tmp_path: Path) -> None:
        """Changing sequence length replaces the whole sequence in save_config.

        Covers ``else: target[key] = new_value`` for the length-changed
        sequence branch (line 133).
        """
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        original_count = len(config.statuses)
        # Remove one status entry — length changes
        config.statuses = config.statuses[:-1]

        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)

        assert len(reloaded.statuses) == original_count - 1

    def test_save_config_persists_changed_scalar_field(self, tmp_path: Path) -> None:
        """Changing a top-level scalar field persists via save_config.

        Covers the outer ``else: target[key] = new_value`` branch (line 135)
        — tasks_dir changes from "tasks" to "items".
        """
        (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        config = load_config(tmp_path)
        config.tasks_dir = "items"

        save_config(tmp_path, config)
        reloaded = load_config(tmp_path)

        assert reloaded.tasks_dir == "items"
