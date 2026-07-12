"""Config schema grouping, detection cascade, and forwarding regression tests.

Promoted from the task-scoped suite for task #1171.

AC coverage:
  AC1: PathsConfig, PipelineConfig, AgentsConfig, PolicyConfig sub-models
       accept valid fields and reject unknown fields (extra='forbid')
  AC2: BoardConfig root-level extra='allow' permits unknown fields
  AC3: schema: grouped field triggers grouped parsing path
  AC4: Detection cascade: schema field → flat key-set match → legacy keys;
       all formats return product-topology values via load_config
  AC5: Mixed flat+grouped WITHOUT schema field raises ConfigError when passed
       directly to BoardConfig.model_validate(); load_config ignores YAML shape
       and returns product-topology values regardless
  AC6: Forwarding properties (config.tasks_dir → config.paths.tasks_dir)
  AC7: defaults.priority → pipeline.default_priority migration path
  AC8: save_config emits next_id-only checkpoint; schema, topology fields, and
       sub-sections are product-owned and not written to disk
  AC9: Round-trip: save_config → load_config returns same product-topology values
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
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.migrate import _migrate_config
from owlbear_kanban.storage import save_config
from owlbear_kanban.topology import PRODUCT_TOPOLOGY

# Provenance: promoted from task-scoped suite for task #1171.

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
  name: TestBoard
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
claim_timeout: 1h
next_id: 1
tasks_dir: custom-tasks
archive_dir: custom-archive
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

    def test_vendor_field_survives_save_reload_round_trip(self, tmp_path: Path) -> None:
        """AC2: load/save path drops vendor fields in topology-constant mode."""
        yaml_with_vendor = _GROUPED_YAML + "vendor_custom: keep-me\n"
        kanban_dir = _make_board(tmp_path, yaml_with_vendor)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.model_extra.get("vendor_custom") is None


# ---------------------------------------------------------------------------
# ACs 3-5 — Detection cascade
# ---------------------------------------------------------------------------


class TestFromAC_DetectionCascade:
    """ACs 3-5 — schema field → flat key-set → legacy; mixed without schema raises."""

    def test_schema_grouped_field_triggers_grouped_parsing(self, tmp_path: Path) -> None:
        """schema: grouped → load_config succeeds and returns config with .paths sub-model."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert hasattr(config, "paths")
        assert config.paths.tasks_dir == PRODUCT_TOPOLOGY.tasks_dir

    def test_flat_key_set_loads_without_schema_field(self, tmp_path: Path) -> None:
        """Flat YAML still loads and returns product topology values."""
        kanban_dir = _make_board(tmp_path, _FLAT_YAML)
        config = load_config(kanban_dir)
        assert config.paths.tasks_dir == PRODUCT_TOPOLOGY.tasks_dir
        assert config.paths.archive_dir == PRODUCT_TOPOLOGY.archive_dir
        assert config.statuses == list(PRODUCT_TOPOLOGY.statuses)

    def test_legacy_keys_load_successfully(self, tmp_path: Path) -> None:
        """Legacy YAML still loads and returns product topology values."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        config = load_config(kanban_dir)
        assert config.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert config.paths.tasks_dir == PRODUCT_TOPOLOGY.tasks_dir
        assert config.paths.archive_dir == PRODUCT_TOPOLOGY.archive_dir

    def test_load_config_mixed_flat_and_grouped_without_schema_returns_product_topology(self, tmp_path: Path) -> None:
        """load_config ignores mixed YAML shape and returns product topology regardless."""
        kanban_dir = _make_board(tmp_path, _MIXED_NO_SCHEMA_YAML)
        config = load_config(kanban_dir)
        assert config.statuses == list(PRODUCT_TOPOLOGY.statuses)

    def test_model_validate_mixed_flat_and_grouped_without_schema_raises_config_error(
        self,
    ) -> None:
        """BoardConfig.model_validate rejects mixed flat+grouped input without schema: grouped."""
        import yaml as _yaml
        from owlbear_kanban.errors import ConfigError
        from owlbear_kanban.models import BoardConfig

        data = _yaml.safe_load(_MIXED_NO_SCHEMA_YAML)
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)
        assert exc_info.value.code == "ERR_INVALID_STATUS"

    def test_grouped_schema_detection_does_not_break_flat_loading(self, tmp_path: Path) -> None:
        """Flat config without schema field still loads after grouped detection added."""
        kanban_dir = _make_board(tmp_path, _FLAT_YAML)
        config = load_config(kanban_dir)
        assert len(config.statuses) == len(PRODUCT_TOPOLOGY.statuses)


# ---------------------------------------------------------------------------
# AC6 — Forwarding properties
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AC7 — defaults.priority → pipeline.default_priority migration
# ---------------------------------------------------------------------------


class TestFromAC_DefaultsPriorityMigration:
    """AC7 — defaults.priority accessible as pipeline.default_priority."""

    def test_grouped_config_exposes_pipeline_default_priority(self, tmp_path: Path) -> None:
        """Grouped config resolves pipeline.default_priority from product topology."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        assert hasattr(config, "pipeline")
        assert config.pipeline.default_priority == PRODUCT_TOPOLOGY.default_priority

    def test_legacy_defaults_priority_migrates_to_pipeline_default_priority(self, tmp_path: Path) -> None:
        """Legacy defaults.priority does not override product default_priority."""
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        config = load_config(kanban_dir)
        assert config.pipeline.default_priority == PRODUCT_TOPOLOGY.default_priority

    def test_migration_path_is_explicit_not_pydantic_default(self, tmp_path: Path) -> None:
        """Legacy default priority in YAML does not affect loaded product topology."""
        yaml_with_critical = _LEGACY_YAML.replace("  priority: someday", "  priority: critical")
        kanban_dir = _make_board(tmp_path, yaml_with_critical)
        config = load_config(kanban_dir)
        assert config.pipeline.default_priority == PRODUCT_TOPOLOGY.default_priority


# ---------------------------------------------------------------------------
# ACs 8-9 — save_config writes next_id-only checkpoint; round-trip preserves data
# ---------------------------------------------------------------------------


class TestFromAC_SaveConfigCheckpointOnly:
    """ACs 8-9 — save_config writes next_id-only checkpoint; round-trip data intact."""

    def _read_yaml(self, path: Path) -> dict:
        """Parse a YAML file and return a plain dict."""
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def test_save_config_writes_next_id_checkpoint_only(self, tmp_path: Path) -> None:
        """save_config writes only next_id checkpoint data."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = self._read_yaml(kanban_dir / "config.yml")
        assert data == {"next_id": config.next_id}

    def test_save_config_omits_paths_sub_section(self, tmp_path: Path) -> None:
        """save_config does not persist paths.* fields."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = self._read_yaml(kanban_dir / "config.yml")
        assert "paths" not in data
        assert data == {"next_id": config.next_id}

    def test_save_config_omits_pipeline_sub_section(self, tmp_path: Path) -> None:
        """save_config does not persist pipeline.* fields."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = self._read_yaml(kanban_dir / "config.yml")
        assert "pipeline" not in data
        assert data == {"next_id": config.next_id}

    def test_save_config_omits_agents_and_policy_sub_sections(self, tmp_path: Path) -> None:
        """save_config does not persist agents/policy sections."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = self._read_yaml(kanban_dir / "config.yml")
        assert "agents" not in data
        assert "policy" not in data
        assert data == {"next_id": config.next_id}

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

    def test_round_trip_pipeline_default_priority_preserved(self, tmp_path: Path) -> None:
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
        """save_config output remains minimal and omits grouped sections."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert "paths" not in data
        assert data == {"next_id": config.next_id}

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

    def test_migrate_config_writes_default_priority_grouped(self, tmp_path: Path) -> None:
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
            f"migrate must write default_priority='someday' in pipeline section, got pipeline={data.get('pipeline')!r}"
        )

    def test_migrate_config_explicit_value_not_pydantic_default(self, tmp_path: Path) -> None:
        """_migrate_config uses the actual defaults.priority value, not a model default.

        MUST FAIL until #1172. Uses 'critical' — differs from both fixture 'someday'
        and Pydantic default 'important' — ruling out all coincidental passes.
        """
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
tasks_dir: custom-tasks
archive_dir: custom-archive
"""
        kanban_dir = _make_board(tmp_path, legacy_with_critical)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        data = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        # Require GROUPED format only
        assert isinstance(data.get("pipeline"), dict), "migrate must write pipeline as nested section"
        assert data["pipeline"].get("default_priority") == "critical", (
            f"Expected 'critical' in pipeline.default_priority, got {data.get('pipeline')!r}"
        )

    def test_migrate_config_preserves_custom_tasks_dir(self, tmp_path: Path) -> None:
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
        assert config.paths.tasks_dir == PRODUCT_TOPOLOGY.tasks_dir
        assert config.paths.archive_dir == PRODUCT_TOPOLOGY.archive_dir

    def test_migrate_config_round_trip_no_data_loss(self, tmp_path: Path) -> None:
        """AC9 (migrate): _migrate_config output loads without data loss.

        MUST FAIL until #1172: tasks_dir not preserved; default_priority not in grouped section.
        Reload DIRECTLY without save_config to avoid masking lossy/noncanonical writes.
        """
        kanban_dir = _make_board(tmp_path, _LEGACY_YAML)
        result, _ = _migrate_config(kanban_dir)
        assert result == "migrated"
        # Load DIRECTLY without calling save_config in between
        config = load_config(kanban_dir)
        assert config.paths.tasks_dir == PRODUCT_TOPOLOGY.tasks_dir
        assert config.paths.archive_dir == PRODUCT_TOPOLOGY.archive_dir
        assert config.pipeline.default_priority == PRODUCT_TOPOLOGY.default_priority
        assert config.statuses == list(PRODUCT_TOPOLOGY.statuses)


class TestFromAC_ModelValidationBoundary:
    """AC11: BoardConfig model construction must not raise ConfigError for empty agent_map.

    The _validate_agent_map call in _validate_semantics is a duplicate of
    engine.py:_validate_engine_config. It must be removed from the model layer
    so that minimal/test fixtures with explicit agent_map={} can be constructed.
    """

    def test_board_config_empty_agent_map_no_exception(self) -> None:
        """BoardConfig with statuses and explicit empty agent_map must not raise.

        MUST FAIL until _validate_agent_map is removed from _validate_semantics.
        Currently raises ConfigError: agent_map missing status entries.
        """
        from owlbear_kanban.models import BoardConfig

        # Explicit agent_map={} — bypasses auto-fill logic
        cfg = BoardConfig(
            schema="grouped",
            statuses=["research", "done"],
            priorities=["important"],
            pipeline={"entry_status": "research", "terminal_status": "done"},
            agents={"agent_map": {}, "agent_types": {}, "agent_compatibility": {}},
        )
        assert cfg.statuses == ["research", "done"]
        assert cfg.agents.agent_map == {}
