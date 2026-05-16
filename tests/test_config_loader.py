"""Config loader cleanup and grouped-load regression tests.

Promoted from archived task-scoped suites for tasks #1171 and #1174.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import owlbear_kanban.config_loader as config_loader_mod
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.models import (
    AgentsConfig,
    BoardConfig,
    PathsConfig,
    PipelineConfig,
    PolicyConfig,
)

# Provenance: promoted from task-scoped suites for tasks #1171 and #1174.

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

_SCHEMA_GROUPED_MIXED_YAML = """\
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
claim_timeout: 1h
next_id: 1001
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
"""


def _make_board(tmp_path: Path, config_yaml: str = _CONFIG_YAML) -> Path:
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    return kanban_dir


class TestFromAC_ConfigLoaderGroupedLoad:
    """Loader-specific grouped-format regression coverage from #1171."""

    def test_load_config_ignores_grouped_vendor_field_at_root(self, tmp_path: Path) -> None:
        """load_config ignores vendor keys from YAML in topology-constant mode."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML + "vendor_integration: true\n")

        config = load_config(kanban_dir)

        vendor_val = (config.model_extra or {}).get("vendor_integration") or getattr(config, "vendor_integration", None)
        assert vendor_val is None

    def test_load_config_ignores_grouped_tui_section_at_root(self, tmp_path: Path) -> None:
        """load_config ignores vendor tui sections from YAML in topology-constant mode."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML + "tui:\n  theme: dark\n")

        config = load_config(kanban_dir)

        tui_val = (config.model_extra or {}).get("tui") or getattr(config, "tui", None)
        assert tui_val is None

    def test_grouped_load_exposes_all_sub_models_and_schema(self, tmp_path: Path) -> None:
        """Grouped load must hydrate every sub-model and preserve schema metadata."""
        kanban_dir = _make_board(tmp_path, _GROUPED_YAML)

        config = load_config(kanban_dir)

        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.pipeline, PipelineConfig)
        assert isinstance(config.agents, AgentsConfig)
        assert isinstance(config.policy, PolicyConfig)
        schema_val = (config.model_extra or {}).get("schema") or getattr(config, "schema", None)
        assert schema_val == "grouped"

    def test_explicit_schema_grouped_allows_mixed_style_input(self, tmp_path: Path) -> None:
        """schema: grouped must suppress mixed-shape rejection for legacy flat keys."""
        kanban_dir = _make_board(tmp_path, _SCHEMA_GROUPED_MIXED_YAML)

        config = load_config(kanban_dir)

        assert isinstance(config.paths, PathsConfig)


class TestFromAC_ConfigLoaderCleanup:
    """Cleanup regression coverage from #1174."""

    def test_save_config_not_in_module_attrs(self) -> None:
        """config_loader must not export save_config after the cleanup."""
        assert not hasattr(config_loader_mod, "save_config")

    def test_merge_into_not_in_module_attrs(self) -> None:
        """config_loader must not export _merge_into after the cleanup."""
        assert not hasattr(config_loader_mod, "_merge_into")

    def test_source_has_no_save_config_reference(self) -> None:
        """config_loader.py must contain no save_config reference after the cleanup."""
        source = Path(inspect.getfile(config_loader_mod)).read_text(encoding="utf-8")
        assert "save_config" not in source

    def test_source_has_no_merge_into_reference(self) -> None:
        """config_loader.py must contain no _merge_into reference after the cleanup."""
        source = Path(inspect.getfile(config_loader_mod)).read_text(encoding="utf-8")
        assert "_merge_into" not in source


class TestFromAC_LoadConfigRegression:
    """Basic load_config regressions retained with the cleanup."""

    def test_load_config_returns_board_config(self, tmp_path: Path) -> None:
        """load_config must still return a BoardConfig for a valid config file."""
        kanban_dir = _make_board(tmp_path)

        result = load_config(kanban_dir)

        assert isinstance(result, BoardConfig)

    def test_load_config_statuses_parsed(self, tmp_path: Path) -> None:
        """load_config must still parse the configured statuses list."""
        kanban_dir = _make_board(tmp_path)

        config = load_config(kanban_dir)

        assert "todo" in config.statuses
        assert "done" in config.statuses

    def test_load_config_returns_defaults_on_missing_file(self, tmp_path: Path) -> None:
        """load_config returns topology defaults when config.yml is absent."""
        config = load_config(tmp_path / "nonexistent")
        assert isinstance(config, BoardConfig)
        assert config.next_id == 1

    def test_load_config_reads_persisted_next_id(self, tmp_path: Path) -> None:
        """load_config must return the next_id value written to config.yml, not always 1."""
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        (kanban_dir / "config.yml").write_text("next_id: 42\n", encoding="utf-8")

        config = load_config(kanban_dir)

        assert config.next_id == 42
