"""Tests for #1171 — Config sub-models, detection cascade, and forwarding properties.

Phase 1 of 3: Schema Infrastructure (config.yml schema grouping).
All tests must FAIL until #1172 implements the grouped schema.

AC coverage:
  AC1: PathsConfig, PipelineConfig, AgentsConfig, PolicyConfig sub-models
       accept valid fields and reject unknown fields (extra='forbid')
  AC2: BoardConfig root-level extra='allow' permits unknown fields
  AC3: schema: grouped field triggers grouped parsing path
  AC4: Detection cascade: schema field → flat key-set match → legacy keys
  AC5: Mixed flat+grouped WITHOUT schema field raises ConfigError
  AC6: Forwarding properties (config.tasks_dir → config.paths.tasks_dir)
  AC7: defaults.priority → pipeline.default_priority migration path
  AC8: save_config emits grouped format with schema: grouped
  AC9: Round-trip: save_config output can be re-loaded without loss
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

# These imports will fail (ImportError) until #1172 adds the sub-models to models.py.
from owlbear_kanban.models import (
    AgentsConfig,
    PathsConfig,
    PipelineConfig,
    PolicyConfig,
)
from owlbear_kanban.migrate import _migrate_config
from owlbear_kanban.storage import load_config, save_config

# ---------------------------------------------------------------------------
# Shared YAML fixtures
# ---------------------------------------------------------------------------

_GROUPED_YAML = """\
schema: grouped
statuses:
  - research
  - backlog
  - done
priorities:
  - important
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
  default_priority: important
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

_FLAT_YAML = """\
statuses:
  - research
  - backlog
  - done
priorities:
  - important
  - critical
entry_status: research
terminal_status: done
wave_size: 4
claim_timeout: 1h
next_id: 1
tasks_dir: tasks
archive_dir: archive
agent_map:
  research: []
  backlog: []
  done: []
agent_types: {}
agent_compatibility: {}
"""

_LEGACY_YAML = """\
version: 10
board:
  name: TestBoard
statuses:
  - name: research
  - name: backlog
  - name: done
priorities:
  - important
  - critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
tasks_dir: tasks
archive_dir: archive
"""

# Mixed: has both a flat key (tasks_dir at root) AND a grouped sub-section (paths:)
# WITHOUT schema: grouped — detection cascade must raise ConfigError.
_MIXED_NO_SCHEMA_YAML = """\
statuses:
  - research
  - done
priorities:
  - important
entry_status: research
terminal_status: done
claim_timeout: 1h
next_id: 1
agent_map:
  research: []
  done: []
tasks_dir: tasks
paths:
  tasks_dir: tasks
  archive_dir: archive
"""


def _make_board(tmp_path: Path, content: str) -> Path:
    """Create a minimal board directory. Returns kanban_dir."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(content, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1 — sub-model validation: valid fields accepted, unknown fields rejected
# ---------------------------------------------------------------------------


class TestFromAC_SubModels:
    """AC1 — PathsConfig, PipelineConfig, AgentsConfig, PolicyConfig validation."""

    # ── PathsConfig ──────────────────────────────────────────────────────────

    def test_paths_config_accepts_valid_fields(self) -> None:
        """PathsConfig(tasks_dir, archive_dir) must construct without error."""
        cfg = PathsConfig(tasks_dir="tasks", archive_dir="archive")
        assert cfg.tasks_dir == "tasks"
        assert cfg.archive_dir == "archive"

    def test_paths_config_rejects_unknown_fields(self) -> None:
        """PathsConfig with unknown field must raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            PathsConfig(tasks_dir="tasks", archive_dir="archive", bogus_key="x")

    # ── PipelineConfig ───────────────────────────────────────────────────────

    def test_pipeline_config_accepts_valid_fields(self) -> None:
        """PipelineConfig with known fields must construct without error."""
        cfg = PipelineConfig(
            entry_status="research",
            terminal_status="done",
            wave_size=4,
            claim_timeout="1h",
            default_priority="important",
        )
        assert cfg.entry_status == "research"
        assert cfg.default_priority == "important"

    def test_pipeline_config_rejects_unknown_fields(self) -> None:
        """PipelineConfig with unknown field must raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            PipelineConfig(
                entry_status="research",
                terminal_status="done",
                wave_size=4,
                claim_timeout="1h",
                default_priority="important",
                bogus_key="x",
            )

    # ── AgentsConfig ─────────────────────────────────────────────────────────

    def test_agents_config_accepts_valid_fields(self) -> None:
        """AgentsConfig with known fields must construct without error."""
        cfg = AgentsConfig(
            agent_map={"research": [], "done": []},
            agent_types={},
            agent_compatibility={},
        )
        assert cfg.agent_map == {"research": [], "done": []}

    def test_agents_config_rejects_unknown_fields(self) -> None:
        """AgentsConfig with unknown field must raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            AgentsConfig(
                agent_map={},
                agent_types={},
                agent_compatibility={},
                bogus_key="x",
            )

    # ── PolicyConfig ─────────────────────────────────────────────────────────

    def test_policy_config_accepts_valid_fields(self) -> None:
        """PolicyConfig with known fields must construct without error."""
        cfg = PolicyConfig(
            non_impl_tags=["type:test"],
            archival_reasons={"completed", "dropped"},
            status_predicates={},
        )
        assert "completed" in cfg.archival_reasons

    def test_policy_config_rejects_unknown_fields(self) -> None:
        """PolicyConfig with unknown field must raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            PolicyConfig(
                non_impl_tags=[],
                archival_reasons=set(),
                status_predicates={},
                bogus_key="x",
            )


# ---------------------------------------------------------------------------
# AC2 — BoardConfig root-level extra='allow'
# ---------------------------------------------------------------------------


class TestFromAC_BoardConfigRootAllow:
    """AC2 — BoardConfig root must permit unknown vendor fields via extra='allow'."""

    def test_board_config_allows_unknown_root_vendor_field(self) -> None:
        """Unknown key at root level must be preserved, not rejected."""
        from owlbear_kanban.models import BoardConfig

        data: dict = {
            "statuses": ["research", "done"],
            "priorities": ["important"],
            "entry_status": "research",
            "terminal_status": "done",
            "claim_timeout": "1h",
            "next_id": 1,
            "agent_map": {"research": [], "done": []},
            "vendor_custom_field": "keep-me",
        }
        config = BoardConfig.model_validate(data)
        # extra='allow' stores unknown keys in model_extra
        assert config.model_extra.get("vendor_custom_field") == "keep-me"  # type: ignore[union-attr]

    def test_board_config_root_allows_tui_vendor_section(self) -> None:
        """Legacy tui: vendor section at root must not be rejected."""
        from owlbear_kanban.models import BoardConfig

        data: dict = {
            "statuses": ["research", "done"],
            "priorities": ["important"],
            "entry_status": "research",
            "terminal_status": "done",
            "claim_timeout": "1h",
            "next_id": 1,
            "agent_map": {"research": [], "done": []},
            "tui": {"theme": "dark"},
        }
        # Must not raise ValidationError
        config = BoardConfig.model_validate(data)
        assert config is not None


# ---------------------------------------------------------------------------
# ACs 3-5 — Detection cascade
# ---------------------------------------------------------------------------


class TestFromAC_DetectionCascade:
    """ACs 3-5 — schema field → flat key-set → legacy; mixed without schema raises."""

    def test_schema_grouped_field_triggers_grouped_parsing(
        self, tmp_path: Path
    ) -> None:
        """schema: grouped → load_config succeeds and returns config with .paths sub-model."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        # Grouped config must expose .paths sub-model (not just flat tasks_dir)
        assert hasattr(config, "paths")
        assert config.paths.tasks_dir == "tasks"

    def test_flat_key_set_loads_without_schema_field(self, tmp_path: Path) -> None:
        """Flat Brief-C keys without schema field must load successfully (flat path)."""
        kanban_dir = _make_board(tmp_path, _FLAT_YAML)
        config = load_config(kanban_dir)
        assert config.tasks_dir == "tasks"
        assert "research" in config.statuses

    def test_legacy_keys_load_successfully(self, tmp_path: Path) -> None:
        """version/board keys → load_config succeeds (legacy detection path)."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        config = load_config(kanban_dir)
        assert "research" in config.statuses

    def test_mixed_flat_and_grouped_without_schema_raises_config_error(
        self, tmp_path: Path
    ) -> None:
        """Both flat + grouped keys present, no schema: grouped → ConfigError per Q2."""
        from owlbear_kanban.errors import ConfigError

        kanban_dir = _make_board(tmp_path, _MIXED_NO_SCHEMA_YAML)
        with pytest.raises(ConfigError):
            load_config(kanban_dir)

    def test_grouped_schema_detection_does_not_break_flat_loading(
        self, tmp_path: Path
    ) -> None:
        """Flat config without schema field still loads after grouped detection added."""
        kanban_dir = _make_board(tmp_path, _FLAT_YAML)
        config = load_config(kanban_dir)
        assert len(config.statuses) == 3


# ---------------------------------------------------------------------------
# AC6 — Forwarding properties
# ---------------------------------------------------------------------------


class TestFromAC_ForwardingProperties:
    """AC6 — forwarding properties on grouped BoardConfig expose sub-model values."""

    def test_tasks_dir_forwards_to_paths_sub_model(self, tmp_path: Path) -> None:
        """config.tasks_dir must equal config.paths.tasks_dir on grouped config."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert config.tasks_dir == config.paths.tasks_dir

    def test_archive_dir_forwards_to_paths_sub_model(self, tmp_path: Path) -> None:
        """config.archive_dir must equal config.paths.archive_dir on grouped config."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert config.archive_dir == config.paths.archive_dir

    def test_flat_config_tasks_dir_still_accessible(self, tmp_path: Path) -> None:
        """config.tasks_dir must still work on flat config (no regression)."""
        kanban_dir = _make_board(tmp_path, _FLAT_YAML)
        config = load_config(kanban_dir)
        assert config.tasks_dir == "tasks"


# ---------------------------------------------------------------------------
# AC7 — defaults.priority → pipeline.default_priority migration
# ---------------------------------------------------------------------------


class TestFromAC_DefaultsPriorityMigration:
    """AC7 — defaults.priority accessible as pipeline.default_priority."""

    def test_grouped_config_exposes_pipeline_default_priority(
        self, tmp_path: Path
    ) -> None:
        """Grouped config: pipeline.default_priority must be set from grouped input."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert hasattr(config, "pipeline")
        assert config.pipeline.default_priority == "important"

    def test_legacy_defaults_priority_migrates_to_pipeline_default_priority(
        self, tmp_path: Path
    ) -> None:
        """Legacy defaults.priority must be accessible as pipeline.default_priority."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        config = load_config(kanban_dir)
        # After normalisation, pipeline sub-model must expose default_priority
        assert config.pipeline.default_priority == "important"

    def test_migration_path_is_explicit_not_pydantic_default(
        self, tmp_path: Path
    ) -> None:
        """Ruling 2: migration must move the value explicitly, not rely on model default.

        Verifies that a legacy config with defaults.priority='critical' (non-default)
        produces pipeline.default_priority='critical', not the Pydantic field default.
        """
        yaml_with_critical = _LEGACY_YAML.replace(
            "  priority: important", "  priority: critical"
        )
        kanban_dir = _make_board(tmp_path, yaml_with_critical)
        config = load_config(kanban_dir)
        assert config.pipeline.default_priority == "critical"


# ---------------------------------------------------------------------------
# ACs 8-9 — save_config emits grouped format; round-trip preserves data
# ---------------------------------------------------------------------------


class TestFromAC_SaveConfigGrouped:
    """ACs 8-9 — save_config emits schema: grouped; round-trip data intact."""

    def _read_yaml(self, path: Path) -> dict:
        """Parse a YAML file and return a plain dict."""
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def test_save_config_emits_schema_grouped_field(self, tmp_path: Path) -> None:
        """save_config must write schema: grouped to the YAML output."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = self._read_yaml(kanban_dir / "config.yml")
        assert data.get("schema") == "grouped"

    def test_save_config_emits_paths_sub_section(self, tmp_path: Path) -> None:
        """save_config must write nested paths: sub-section, not flat tasks_dir."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = self._read_yaml(kanban_dir / "config.yml")
        assert "paths" in data
        assert data["paths"]["tasks_dir"] == "tasks"

    def test_save_config_emits_pipeline_sub_section(self, tmp_path: Path) -> None:
        """save_config must write nested pipeline: sub-section."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = self._read_yaml(kanban_dir / "config.yml")
        assert "pipeline" in data
        assert data["pipeline"]["default_priority"] == "important"

    def test_round_trip_statuses_preserved(self, tmp_path: Path) -> None:
        """Round-trip: save_config → load_config returns same statuses list."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.statuses == config.statuses

    def test_round_trip_priorities_preserved(self, tmp_path: Path) -> None:
        """Round-trip: save_config → load_config returns same priorities list."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.priorities == config.priorities

    def test_round_trip_paths_sub_model_preserved(self, tmp_path: Path) -> None:
        """Round-trip: paths.tasks_dir and paths.archive_dir survive save → reload."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.paths.tasks_dir == config.paths.tasks_dir
        assert reloaded.paths.archive_dir == config.paths.archive_dir

    def test_round_trip_pipeline_default_priority_preserved(
        self, tmp_path: Path
    ) -> None:
        """Round-trip: pipeline.default_priority survives save → reload cycle."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.pipeline.default_priority == config.pipeline.default_priority

    def test_save_config_no_flat_tasks_dir_at_root(self, tmp_path: Path) -> None:
        """AC8 (negative): grouped save_config must NOT write tasks_dir as flat root key."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert "tasks_dir" not in data, "tasks_dir must not leak as flat root key in grouped output"

    def test_save_config_no_flat_archive_dir_at_root(self, tmp_path: Path) -> None:
        """AC8 (negative): grouped save_config must NOT write archive_dir as flat root key."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert "archive_dir" not in data, "archive_dir must not leak as flat root key in grouped output"

    def test_save_config_grouped_nested_paths_structural(self, tmp_path: Path) -> None:
        """AC8 (structural): YAML-parsed output has nested paths dict with tasks_dir and archive_dir."""
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
    """AC7 — migrate._migrate_config explicitly transfers defaults.priority to default_priority."""

    def test_migrate_config_writes_default_priority_from_legacy(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config on legacy board writes default_priority from defaults.priority."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        # _LEGACY_YAML has defaults.priority: important
        assert data.get("default_priority") == "important" or (
            isinstance(data.get("pipeline"), dict)
            and data["pipeline"].get("default_priority") == "important"
        ), "migrate must write default_priority value from defaults.priority"

    def test_migrate_config_explicit_value_not_pydantic_default(
        self, tmp_path: Path
    ) -> None:
        """_migrate_config uses the actual defaults.priority value, not a model default."""
        legacy_with_critical = """\
version: 10
board:
  name: TestBoard
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
claim_timeout: 1h
next_id: 1
tasks_dir: tasks
archive_dir: archive
"""
        kanban_dir = _make_board(tmp_path, legacy_with_critical)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        actual_priority = data.get("default_priority") or (
            data.get("pipeline") or {}
        ).get("default_priority")
        assert actual_priority == "critical", (
            f"Expected 'critical', got {actual_priority!r} — migration must be explicit"
        )

    def test_migrate_config_round_trip_no_data_loss(
        self, tmp_path: Path
    ) -> None:
        """AC9 (migrate): _migrate_config output can be re-loaded; model_dump matches."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        # After migration, load_config must succeed
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        exclude = {"defaults"}
        assert reloaded.model_dump(exclude=exclude) == config.model_dump(exclude=exclude)
