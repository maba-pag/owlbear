"""Tests for #1175 — Harden storage.save_config for grouped config output.

AC1: Replace hardcoded pop-loop with model_dump(exclude=...) denylist of dead-only
     keys (board, version); new model fields are emitted automatically (td:2)
AC2: Nested dict values (e.g. defaults sub-model) survive save/load round-trip (td:2)
AC3: frozenset-to-list conversion works at nested depth via recursive walker (td:2)
AC4: defaults.priority and activity_log are preserved through save_config → load_config (td:1)
"""

from __future__ import annotations

from pathlib import Path

import yaml

from owlbear_kanban.storage import load_config, save_config

# Legacy schema config — has 'board'/'version' (dead) and 'defaults'/'activity_log' (live)
_LEGACY_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
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
claim_timeout: 1h
next_id: 10
archive_dir: archive
activity_log: false
"""



def _make_board(tmp_path: Path, yaml_content: str = _LEGACY_CONFIG_YAML) -> Path:
    """Create a minimal board directory. Returns kanban_dir."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(yaml_content, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


def _read_yaml(path: Path) -> dict:
    """Parse a YAML file and return a plain dict."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class TestFromAC_SaveConfigHardening:
    """Tests for #1175 — save_config hardened to use model_dump(exclude=denylist)."""

    # -------------------------------------------------------------------------
    # AC1: denylist limited to dead keys — live keys emitted automatically
    # -------------------------------------------------------------------------

    def test_ac1_defaults_present_in_yaml_output(self, tmp_path: Path) -> None:
        """AC1: 'defaults' is not in the denylist → must appear in saved YAML.

        Fails currently: save_config pops 'defaults' via hardcoded loop.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert "defaults" in data

    def test_ac1_activity_log_present_in_yaml_output(self, tmp_path: Path) -> None:
        """AC1: 'activity_log' is not in the denylist → must appear in saved YAML.

        Fails currently: save_config pops 'activity_log' via hardcoded loop.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert "activity_log" in data

    def test_ac1_denylist_limited_to_board_and_version_only(self, tmp_path: Path) -> None:
        """AC1: only 'board' and 'version' are excluded; all live keys are present.

        Fails currently: defaults and activity_log are also stripped.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        # Dead keys must be absent
        assert "board" not in data
        assert "version" not in data
        # Live keys must be present
        assert "defaults" in data
        assert "activity_log" in data

    # -------------------------------------------------------------------------
    # AC2: nested dict values (defaults sub-model) survive round-trip
    # -------------------------------------------------------------------------

    def test_ac2_defaults_priority_non_default_survives_roundtrip(
        self, tmp_path: Path
    ) -> None:
        """AC2: non-default defaults.priority survives save_config → load_config.

        Fails currently: save_config strips 'defaults', so reloaded config reverts
        defaults.priority to model default "important".
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.defaults.priority = "critical"
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.defaults.priority == "critical"

    def test_ac2_defaults_status_non_default_survives_roundtrip(
        self, tmp_path: Path
    ) -> None:
        """AC2: non-default defaults.status survives save_config → load_config.

        Fails currently: save_config strips 'defaults', so reloaded config reverts
        defaults.status to model default "research".
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.defaults.status = "backlog"
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.defaults.status == "backlog"

    def test_ac2_defaults_is_dict_with_expected_keys_in_yaml_output(
        self, tmp_path: Path
    ) -> None:
        """AC2: parsed YAML contains 'defaults' as a dict with 'priority' and 'status'.

        Fails currently: save_config strips 'defaults' entirely.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        defaults_val = data.get("defaults")
        assert isinstance(defaults_val, dict)
        assert "priority" in defaults_val
        assert "status" in defaults_val

    # -------------------------------------------------------------------------
    # AC3: frozenset-to-list conversion at nested depth (recursive walker)
    # -------------------------------------------------------------------------

    def test_ac3_nested_frozenset_in_extra_field_saves_without_error(
        self, tmp_path: Path
    ) -> None:
        """AC3: frozenset inside a top-level extra field (not in denylist) must not raise.

        Injects a nested frozenset into a top-level extra field. The current code
        only converts archival_reasons — the extra field's nested frozenset is left
        as-is, causing ruamel.yaml to raise a RepresenterError on dump.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        # Inject nested frozenset at top-level extra field (NOT in the pop denylist)
        if config.__pydantic_extra__ is None:
            config.__pydantic_extra__ = {}
        config.__pydantic_extra__["extra_section"] = {"nested_frozen": frozenset({"x", "y"})}
        # Must not raise ruamel.yaml.representer.RepresenterError
        save_config(config, kanban_dir)

    def test_ac3_nested_frozenset_converted_to_sorted_list(
        self, tmp_path: Path
    ) -> None:
        """AC3: frozenset inside nested sub-model is serialized as a sorted list.

        Fails currently: nested frozenset causes RepresenterError before reaching
        any assertion (or is not converted if the error is suppressed).
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        if config.defaults.__pydantic_extra__ is None:
            config.defaults.__pydantic_extra__ = {}
        config.defaults.__pydantic_extra__["nested_frozen"] = frozenset({"c", "a", "b"})
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        nested_val = data.get("defaults", {}).get("nested_frozen")
        assert nested_val == ["a", "b", "c"]

    def test_ac3_deeply_nested_frozenset_recursive_conversion(
        self, tmp_path: Path
    ) -> None:
        """AC3: frozenset two levels deep in a top-level extra field is recursively converted.

        Injects a two-level nested dict with a frozenset via __pydantic_extra__.
        The current code's top-level-only archival_reasons handler misses it;
        the recursive walker in the new implementation must convert it.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        if config.__pydantic_extra__ is None:
            config.__pydantic_extra__ = {}
        config.__pydantic_extra__["level_one"] = {
            "level_two": {"deep_frozen": frozenset({"z", "m", "a"})}
        }
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        deep_val = data.get("level_one", {}).get("level_two", {}).get("deep_frozen")
        assert deep_val == ["a", "m", "z"]

    def test_ac3_frozenset_in_list_container_is_converted(
        self, tmp_path: Path
    ) -> None:
        """AC3: frozenset elements inside a list container are recursively converted.

        Exercises the list-branch of _yaml_safe_value(). Removing that branch
        leaves the frozensets unconverted inside the list, causing ruamel.yaml
        to raise a RepresenterError on dump (no frozenset representer).
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        if config.__pydantic_extra__ is None:
            config.__pydantic_extra__ = {}
        config.__pydantic_extra__["list_of_frozen"] = [
            frozenset({"b", "a"}),
            frozenset({"d", "c"}),
        ]
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert data.get("list_of_frozen") == [["a", "b"], ["c", "d"]]

    def test_ac3_frozenset_in_tuple_container_is_converted(
        self, tmp_path: Path
    ) -> None:
        """AC3: frozenset element inside a tuple container is recursively converted.

        Exercises the tuple-branch of _yaml_safe_value(). Without that branch the
        frozenset inside the tuple is passed to ruamel.yaml unmodified and raises
        a RepresenterError. With it, the tuple becomes a list and the inner
        frozenset becomes a sorted list.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        if config.__pydantic_extra__ is None:
            config.__pydantic_extra__ = {}
        # Tuple with one frozenset element — targets tuple recursion branch.
        config.__pydantic_extra__["tuple_of_frozen"] = (frozenset({"z", "m", "a"}),)
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        # Tuple → list; frozenset element → sorted list.
        assert data.get("tuple_of_frozen") == [["a", "m", "z"]]

    def test_ac1_new_field_not_in_denylist_is_emitted_automatically(
        self, tmp_path: Path
    ) -> None:
        """AC1: model_dump(exclude=denylist) emits unknown fields automatically.

        Proves the denylist mechanism: a field not in _CONFIG_WRITE_EXCLUDE
        survives save_config() without any changes to the denylist.  An
        allowlist-based implementation would silently drop this field.
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        if config.__pydantic_extra__ is None:
            config.__pydantic_extra__ = {}
        config.__pydantic_extra__["canary_future_field"] = "canary_value"
        save_config(config, kanban_dir)
        data = _read_yaml(kanban_dir / "config.yml")
        assert "canary_future_field" in data
        assert data["canary_future_field"] == "canary_value"

    # -------------------------------------------------------------------------
    # AC4: defaults.priority and activity_log preserved through cycle (td:1)
    # -------------------------------------------------------------------------

    def test_ac4_defaults_priority_and_activity_log_preserved_through_cycle(
        self, tmp_path: Path
    ) -> None:
        """AC4: both defaults.priority and activity_log survive save_config → load_config.

        Fails currently: save_config strips both 'defaults' and 'activity_log'.
        After reload, defaults.priority reverts to "important" (model default)
        and activity_log reverts to True (model default).
        """
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.defaults.priority = "needed"
        config.activity_log = False
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.defaults.priority == "needed"
        assert reloaded.activity_log is False
