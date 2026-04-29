"""Tests for #1171 — P1-01: Config sub-models, detection cascade, forwarding properties.

Tests cover:
- PathsConfig, PipelineConfig, AgentsConfig, PolicyConfig sub-models (AC1)
- BoardConfig root-level extra='allow' with grouped format (AC2)
- schema: grouped field triggers grouped parsing path (AC3)
- Detection cascade: schema field → flat key-set → legacy keys (AC4)
- Mixed flat+grouped WITHOUT schema field raises ConfigError (AC5)
- Forwarding properties (config.tasks_dir → config.paths.tasks_dir) (AC6)
- defaults.priority → pipeline.default_priority migration (AC7)
- save_config emits grouped format with schema: grouped; round-trip (AC8, AC9)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import pydantic

from owlbear_kanban.errors import ConfigError
from owlbear_kanban.migrate import _migrate_config
from owlbear_kanban.models import (
    AgentsConfig,
    PathsConfig,
    PipelineConfig,
    PolicyConfig,
)
from owlbear_kanban.storage import load_config, save_config


# ---------------------------------------------------------------------------
# YAML fixtures
# ---------------------------------------------------------------------------

# AC10: identical to _GROUPED_YAML in test_config_schema_1171.py
# Nondefault values prove value extraction, not Pydantic defaults.
_GROUPED_YAML = """\
schema: grouped
statuses:
  - research
  - backlog
  - done
priorities:
  - someday
  - important
  - critical
next_id: 1
activity_log: true
paths:
  tasks_dir: custom-tasks
  archive_dir: custom-archive
pipeline:
  entry_status: research
  terminal_status: done
  wave_size: 4
  claim_timeout: 1h
  default_priority: someday
agents:
  agent_map:
    research: []
    backlog: []
    done: []
  agent_types: {}
  agent_compatibility: {}
policy:
  non_impl_tags: []
  archival_reasons:
    - completed
    - deprecated
    - dropped
    - duplicate
    - wontfix
  status_predicates: {}
"""

# Nondefault tasks_dir/archive_dir prove flat key extraction, not Pydantic defaults.
_FLAT_YAML = """\
statuses:
  - research
  - backlog
  - done
priorities:
  - someday
  - important
  - critical
entry_status: research
terminal_status: done
wave_size: 4
claim_timeout: 1h
next_id: 1
tasks_dir: custom-tasks
archive_dir: custom-archive
agent_map:
  research: []
  backlog: []
  done: []
agent_types: {}
agent_compatibility: {}
"""

# Nondefault priority/paths prove explicit migrate value transfer, not Pydantic defaults.
_LEGACY_YAML = """\
version: 10
board:
  name: Test Board
statuses:
  - name: research
  - name: backlog
  - name: done
priorities:
  - someday
  - important
  - critical
defaults:
  status: research
  priority: someday
tasks_dir: custom-tasks
archive_dir: custom-archive
"""


def _make_board(tmp_path: Path, config_yaml: str = _FLAT_YAML) -> Path:
    """Create a minimal kanban board directory with the given config YAML."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1: Sub-model validation — valid fields accepted, unknown fields rejected
# ---------------------------------------------------------------------------


class TestFromAC_SubModelValidation:
    """AC1 — PathsConfig, PipelineConfig, AgentsConfig, PolicyConfig validate correctly."""

    # PathsConfig

    def test_paths_config_accepts_valid_fields(self) -> None:
        """PathsConfig instantiates with tasks_dir and archive_dir."""
        cfg = PathsConfig(tasks_dir="tasks", archive_dir="archive")
        assert cfg.tasks_dir == "tasks"
        assert cfg.archive_dir == "archive"

    def test_paths_config_rejects_unknown_fields(self) -> None:
        """PathsConfig rejects unknown fields — extra='forbid' catches typos."""
        with pytest.raises(pydantic.ValidationError):
            PathsConfig(tasks_dir="tasks", archive_dir="archive", typo_field="x")

    # PipelineConfig

    def test_pipeline_config_accepts_valid_fields(self) -> None:
        """PipelineConfig instantiates with all pipeline fields including default_priority."""
        cfg = PipelineConfig(
            entry_status="research",
            terminal_status="done",
            claim_timeout="1h",
            wave_size=4,
            default_priority="important",
        )
        assert cfg.entry_status == "research"
        assert cfg.default_priority == "important"

    def test_pipeline_config_rejects_unknown_fields(self) -> None:
        """PipelineConfig rejects unknown fields — extra='forbid' catches typos."""
        with pytest.raises(pydantic.ValidationError):
            PipelineConfig(entry_status="research", unknown_key="oops")

    # AgentsConfig

    def test_agents_config_accepts_valid_fields(self) -> None:
        """AgentsConfig instantiates with agent_map, agent_types, and agent_compatibility."""
        cfg = AgentsConfig(
            agent_map={"research": [], "done": []},
            agent_types={},
            agent_compatibility={},
        )
        assert cfg.agent_map == {"research": [], "done": []}

    def test_agents_config_rejects_unknown_fields(self) -> None:
        """AgentsConfig rejects unknown fields — extra='forbid' catches typos."""
        with pytest.raises(pydantic.ValidationError):
            AgentsConfig(agent_map={}, unexpected_key="bad")

    # PolicyConfig

    def test_policy_config_accepts_valid_fields(self) -> None:
        """PolicyConfig instantiates with non_impl_tags, archival_reasons, status_predicates."""
        cfg = PolicyConfig(
            non_impl_tags=["type:test"],
            archival_reasons={"completed", "dropped"},
            status_predicates={},
        )
        assert "completed" in cfg.archival_reasons

    def test_policy_config_rejects_unknown_fields(self) -> None:
        """PolicyConfig rejects unknown fields — extra='forbid' catches typos."""
        with pytest.raises(pydantic.ValidationError):
            PolicyConfig(non_impl_tags=[], archival_reasons={"completed"}, bad_field=True)


# ---------------------------------------------------------------------------
# AC2: BoardConfig root-level extra='allow' preserves vendor fields
# ---------------------------------------------------------------------------


class TestFromAC_BoardConfigRootExtraAllow:
    """AC2 — BoardConfig extra='allow' permits unknown top-level fields in grouped format."""

    def test_grouped_config_preserves_vendor_field_at_root(self, tmp_path: Path) -> None:
        """Grouped config with unknown root field is loadable — extra='allow' on BoardConfig."""
        yaml_with_vendor = _GROUPED_YAML + "vendor_integration: true\n"
        kanban_dir = _make_board(tmp_path, yaml_with_vendor)
        config = load_config(kanban_dir)
        # vendor_integration is preserved as extra field
        vendor_val = config.model_extra.get("vendor_integration") or getattr(
            config, "vendor_integration", None
        )
        assert vendor_val is True

    def test_grouped_config_preserves_tui_section(self, tmp_path: Path) -> None:
        """Grouped config with tui: section is loadable — tui is a known vendor section."""
        yaml_with_tui = _GROUPED_YAML + "tui:\n  theme: dark\n"
        kanban_dir = _make_board(tmp_path, yaml_with_tui)
        # Must not raise — extra='allow' accepts tui at root
        config = load_config(kanban_dir)
        tui_val = config.model_extra.get("tui") or getattr(config, "tui", None)
        assert tui_val is not None

    def test_vendor_field_survives_save_reload_round_trip(
        self, tmp_path: Path
    ) -> None:
        """AC2: vendor field must survive save_config → load_config round-trip."""
        yaml_with_vendor = _GROUPED_YAML + "vendor_custom: keep-me\n"
        kanban_dir = _make_board(tmp_path, yaml_with_vendor)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.model_extra.get("vendor_custom") == "keep-me"


# ---------------------------------------------------------------------------
# AC3: schema: grouped field triggers grouped parsing path
# ---------------------------------------------------------------------------


class TestFromAC_GroupedSchemaDetection:
    """AC3 — schema: grouped field causes sub-model instances on the loaded config."""

    def test_grouped_schema_produces_paths_sub_model(self, tmp_path: Path) -> None:
        """Grouped config yields config.paths as PathsConfig instance."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert isinstance(config.paths, PathsConfig)

    def test_grouped_schema_produces_all_sub_models(self, tmp_path: Path) -> None:
        """Grouped config yields PathsConfig, PipelineConfig, AgentsConfig, PolicyConfig."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.pipeline, PipelineConfig)
        assert isinstance(config.agents, AgentsConfig)
        assert isinstance(config.policy, PolicyConfig)

    def test_grouped_schema_field_identifies_format(self, tmp_path: Path) -> None:
        """Grouped config preserves schema field value so consumers can identify format."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        schema_val = config.model_extra.get("schema") or getattr(config, "schema", None)
        assert schema_val == "grouped"


# ---------------------------------------------------------------------------
# AC4: Detection cascade — schema field → flat key-set → legacy keys
# ---------------------------------------------------------------------------


class TestFromAC_DetectionCascade:
    """AC4 — Detection cascade routes each YAML format to correct parsing path."""

    def test_cascade_schema_grouped_field_triggers_sub_models(self, tmp_path: Path) -> None:
        """schema: grouped field → grouped parsing → PathsConfig present."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert isinstance(config.paths, PathsConfig)

    def test_cascade_flat_keyset_loads_without_sub_model_sections(
        self, tmp_path: Path
    ) -> None:
        """Flat Brief-C config (no schema field) loads and forwarding properties work."""
        kanban_dir = _make_board(tmp_path, _FLAT_YAML)
        config = load_config(kanban_dir)
        # BOTH nondefault values prove flat key extraction, not Pydantic defaults
        assert config.tasks_dir == "custom-tasks"
        assert config.archive_dir == "custom-archive"

    def test_cascade_legacy_keys_load_correctly(self, tmp_path: Path) -> None:
        """Legacy config (version + board keys) is detected and normalised correctly."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        config = load_config(kanban_dir)
        # _LEGACY_YAML has 3 statuses: research, backlog, done
        assert config.statuses == ["research", "backlog", "done"]
        # BOTH nondefault values prove legacy key extraction, not Pydantic defaults
        assert config.tasks_dir == "custom-tasks"
        assert config.archive_dir == "custom-archive"

    def test_cascade_grouped_takes_precedence_over_flat_detection(
        self, tmp_path: Path
    ) -> None:
        """schema: grouped takes precedence — sub-models parsed from sections, not flat keys."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        # Nondefault value proves paths.tasks_dir comes from the paths: section
        assert config.paths.tasks_dir == "custom-tasks"


# ---------------------------------------------------------------------------
# AC5: Mixed flat+grouped without schema field raises ConfigError
# ---------------------------------------------------------------------------


class TestFromAC_MixedShapeError:
    """AC5 — Mixed flat and grouped keys without schema: grouped raises ConfigError."""

    def test_flat_plus_grouped_sections_raises_config_error(
        self, tmp_path: Path
    ) -> None:
        """Flat keys (entry_status) + paths: section without schema: grouped → ConfigError."""
        mixed_yaml = """\
statuses:
  - research
  - done
priorities:
  - important
entry_status: research
terminal_status: done
claim_timeout: 1h
agent_map:
  research: []
  done: []
paths:
  tasks_dir: tasks
  archive_dir: archive
"""
        kanban_dir = _make_board(tmp_path, mixed_yaml)
        with pytest.raises(ConfigError):
            load_config(kanban_dir)

    def test_schema_grouped_suppresses_mixed_shape_error(self, tmp_path: Path) -> None:
        """Explicit schema: grouped suppresses ConfigError for extra flat-style keys."""
        yaml_with_explicit_schema = """\
schema: grouped
statuses:
  - research
  - done
priorities:
  - important
entry_status: research
paths:
  tasks_dir: tasks
  archive_dir: archive
pipeline:
  entry_status: research
  terminal_status: done
  claim_timeout: 1h
  wave_size: 4
  default_priority: important
agents:
  agent_map:
    research: []
    done: []
  agent_types: {}
  agent_compatibility: {}
policy:
  non_impl_tags: []
  archival_reasons:
    - completed
  status_predicates: {}
"""
        kanban_dir = _make_board(tmp_path, yaml_with_explicit_schema)
        # schema: grouped is authoritative — must not raise
        config = load_config(kanban_dir)
        assert isinstance(config.paths, PathsConfig)


# ---------------------------------------------------------------------------
# AC6: Forwarding properties
# ---------------------------------------------------------------------------


class TestFromAC_ForwardingProperties:
    """AC6 — BoardConfig exposes tasks_dir and archive_dir via forwarding properties."""

    def test_tasks_dir_forwards_to_paths_sub_model(self, tmp_path: Path) -> None:
        """config.tasks_dir returns the same value as config.paths.tasks_dir."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert config.tasks_dir == config.paths.tasks_dir

    def test_archive_dir_forwards_to_paths_sub_model(self, tmp_path: Path) -> None:
        """config.archive_dir returns the same value as config.paths.archive_dir."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert config.archive_dir == config.paths.archive_dir

    def test_forwarding_property_nondefault_value_matches_yaml(self, tmp_path: Path) -> None:
        """Forwarding properties return nondefault values from the paths: section."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        # Must match fixture values, not Pydantic defaults "tasks"/"archive"
        assert config.tasks_dir == "custom-tasks"
        assert config.archive_dir == "custom-archive"

    def test_tasks_dir_forwarding_works_on_flat_config(self, tmp_path: Path) -> None:
        """config.tasks_dir works on flat config via forwarding property (backward compat)."""
        kanban_dir = _make_board(tmp_path, _FLAT_YAML)
        config = load_config(kanban_dir)
        # Flat config: normaliser builds PathsConfig from flat keys
        assert config.tasks_dir == config.paths.tasks_dir
        # Nondefault value proves extraction from flat key, not Pydantic default
        assert config.tasks_dir == "custom-tasks"


# ---------------------------------------------------------------------------
# AC7: defaults.priority → pipeline.default_priority migration
# ---------------------------------------------------------------------------


class TestFromAC_DefaultsPriorityMigration:
    """AC7 — Legacy defaults.priority is explicitly migrated to pipeline.default_priority."""

    def test_legacy_defaults_priority_migrated_to_pipeline(self, tmp_path: Path) -> None:
        """Legacy config defaults.priority value appears in pipeline.default_priority."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        config = load_config(kanban_dir)
        # _LEGACY_YAML has defaults.priority: someday (nondefault) — proves explicit migration
        assert config.pipeline.default_priority == "someday"

    def test_migration_uses_actual_value_not_pydantic_default(
        self, tmp_path: Path
    ) -> None:
        """Non-default defaults.priority value is explicitly migrated, not substituted.

        Uses 'critical' — differs from _LEGACY_YAML's 'someday' AND Pydantic default
        'important' — ruling out all coincidental passes.
        """
        yaml_non_default = """\
version: 10
board:
  name: Test Board
statuses:
  - name: research
  - name: done
priorities:
  - important
  - critical
defaults:
  status: research
  priority: critical
tasks_dir: custom-tasks
archive_dir: custom-archive
"""
        kanban_dir = _make_board(tmp_path, yaml_non_default)
        config = load_config(kanban_dir)
        # Must be "critical" (the actual value), not the PipelineConfig model default
        assert config.pipeline.default_priority == "critical"

    def test_grouped_config_pipeline_default_priority_accessible(
        self, tmp_path: Path
    ) -> None:
        """Grouped config exposes pipeline.default_priority from pipeline: section."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        # Nondefault value proves grouped pipeline: section is read, not Pydantic default
        assert config.pipeline.default_priority == "someday"


# ---------------------------------------------------------------------------
# AC8 + AC9: save_config emits grouped format; round-trip preserves data
# ---------------------------------------------------------------------------


class TestFromAC_SaveConfigGroupedFormat:
    """AC8+AC9 — save_config writes grouped format; output is re-loadable without loss."""

    def test_save_config_emits_schema_grouped_field(self, tmp_path: Path) -> None:
        """save_config writes schema: grouped to config.yml."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        written = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        assert "schema: grouped" in written

    def test_save_config_emits_paths_section(self, tmp_path: Path) -> None:
        """save_config writes a paths: sub-section containing tasks_dir and archive_dir."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert isinstance(data.get("paths"), dict), "paths: must be nested dict in grouped output"
        # Nondefault values prove values are written, not Pydantic defaults
        assert data["paths"]["tasks_dir"] == "custom-tasks"
        assert data["paths"]["archive_dir"] == "custom-archive"

    def test_save_config_emits_pipeline_section(self, tmp_path: Path) -> None:
        """save_config writes a pipeline: sub-section."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert isinstance(data.get("pipeline"), dict), "pipeline: must be nested dict"
        # Nondefault value proves pipeline section values are written, not Pydantic defaults
        assert data["pipeline"]["default_priority"] == "someday"

    def test_save_config_emits_agents_and_policy_sub_sections(
        self, tmp_path: Path
    ) -> None:
        """AC8: save_config must emit agents: and policy: as nested sub-sections."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert isinstance(data.get("agents"), dict), "agents: must be nested dict in grouped output"
        assert isinstance(data.get("policy"), dict), "policy: must be nested dict in grouped output"
        assert "agent_map" in data["agents"]
        assert "non_impl_tags" in data["policy"]

    def test_round_trip_statuses_preserved(self, tmp_path: Path) -> None:
        """save_config output can be re-loaded and statuses are unchanged."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.statuses == config.statuses

    def test_round_trip_priorities_preserved(self, tmp_path: Path) -> None:
        """save_config output can be re-loaded and priorities are unchanged."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.priorities == config.priorities

    def test_round_trip_paths_preserved(self, tmp_path: Path) -> None:
        """Round-trip: paths sub-model survives save → load without data loss."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert isinstance(reloaded.paths, PathsConfig)
        assert reloaded.paths.tasks_dir == config.paths.tasks_dir
        assert reloaded.paths.archive_dir == config.paths.archive_dir

    def test_round_trip_pipeline_default_priority_preserved(
        self, tmp_path: Path
    ) -> None:
        """Round-trip: pipeline.default_priority survives save → load without loss."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.pipeline.default_priority == config.pipeline.default_priority

    def test_save_config_no_flat_tasks_dir_at_root(self, tmp_path: Path) -> None:
        """AC8 (negative): save_config must NOT write tasks_dir as a flat root key."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert "tasks_dir" not in data, "tasks_dir must not leak as a flat root key in grouped output"

    def test_save_config_no_flat_archive_dir_at_root(self, tmp_path: Path) -> None:
        """AC8 (negative): save_config must NOT write archive_dir as a flat root key."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert "archive_dir" not in data, "archive_dir must not leak as a flat root key in grouped output"

    def test_save_config_grouped_output_has_nested_paths_keys(
        self, tmp_path: Path
    ) -> None:
        """AC8 (structural): YAML output has paths.tasks_dir and paths.archive_dir as nested keys."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert isinstance(data.get("paths"), dict)
        assert "tasks_dir" in data["paths"]
        assert "archive_dir" in data["paths"]

    def test_round_trip_full_model_dump_equality(self, tmp_path: Path) -> None:
        """AC9: save_config → load_config model_dump equals original for all persisted fields."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        # Exclude legacy 'defaults' field — not preserved in grouped round-trip
        exclude = {"defaults"}
        assert reloaded.model_dump(exclude=exclude) == config.model_dump(exclude=exclude)


# ---------------------------------------------------------------------------
# AC7 (extend): migrate._migrate_config converts defaults.priority → default_priority
# ---------------------------------------------------------------------------


class TestFromAC_MigrateConfigDefaultsPriority:
    """AC7+AC9 — _migrate_config must produce grouped output; paths preserved.

    ALL tests in this class MUST FAIL until #1172 implements grouped migration output.
    Current _migrate_config writes flat Brief-C keys (default_priority, entry_status
    at root) — NOT the grouped pipeline: section; also drops tasks_dir/archive_dir.
    """

    def test_migrate_config_writes_default_priority_grouped(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config must write default_priority nested under pipeline: section.

        MUST FAIL until #1172: current migrate writes flat new_cfg["default_priority"].
        'someday' differs from Pydantic default 'important' — proves explicit transfer.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        # Require GROUPED format strictly — flat root-level default_priority NOT acceptable
        assert isinstance(data.get("pipeline"), dict), (
            f"migrate must write pipeline as nested section; got keys={list(data.keys())!r}"
        )
        assert data["pipeline"].get("default_priority") == "someday", (
            f"migrate must write default_priority='someday' in pipeline section, "
            f"got pipeline={data.get('pipeline')!r}"
        )

    def test_migrate_config_explicit_value_not_pydantic_default(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config uses the actual defaults.priority value, not a model default.

        MUST FAIL until #1172. Uses 'critical' — differs from both fixture 'someday'
        and Pydantic default 'important' — ruling out all coincidental passes.
        """
        legacy_with_critical = """\
version: 10
board:
  name: Test Board
statuses:
  - name: research
  - name: backlog
  - name: done
priorities:
  - important
  - critical
defaults:
  status: research
  priority: critical
tasks_dir: custom-tasks
archive_dir: custom-archive
"""
        kanban_dir = _make_board(tmp_path, legacy_with_critical)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        # Require GROUPED format only
        assert isinstance(data.get("pipeline"), dict), (
            "migrate must write pipeline as nested section"
        )
        assert data["pipeline"].get("default_priority") == "critical", (
            f"Expected 'critical' in pipeline.default_priority, got {data.get('pipeline')!r}"
        )

    def test_migrate_config_preserves_custom_tasks_dir(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config must preserve tasks_dir and archive_dir from legacy config.

        MUST FAIL until #1172: current migrate.py new_cfg does not include tasks_dir or
        archive_dir, causing silent data loss for boards with custom directory paths.
        Reload DIRECTLY without save_config to avoid masking the data loss.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        # Reload DIRECTLY — no save_config (save_config would normalize and mask loss)
        config = load_config(kanban_dir)
        assert config.paths.tasks_dir == "custom-tasks", (
            f"migrate must preserve tasks_dir='custom-tasks', got {config.paths.tasks_dir!r}"
        )
        assert config.paths.archive_dir == "custom-archive", (
            f"migrate must preserve archive_dir='custom-archive', got {config.paths.archive_dir!r}"
        )

    def test_migrate_config_round_trip_no_data_loss(
        self, tmp_path: Path
    ) -> None:
        """AC9 (migrate): _migrate_config output loads without data loss.

        MUST FAIL until #1172: tasks_dir not preserved; default_priority not in grouped section.
        Reload DIRECTLY without save_config to avoid masking lossy/noncanonical writes.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        # Load DIRECTLY without calling save_config in between
        config = load_config(kanban_dir)
        # Nondefault values prove explicit preservation, not Pydantic defaults
        assert config.paths.tasks_dir == "custom-tasks"
        assert config.paths.archive_dir == "custom-archive"
        assert config.pipeline.default_priority == "someday"
        assert config.statuses == ["research", "backlog", "done"]
