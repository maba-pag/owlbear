"""Config authority and validation regression tests.

Behavioral coverage:
  AC1 (td:1): ERR_CONFLICT_STATUS registered in KANBAN_ERROR_CODES in errors.py
  AC2 (td:2): _normalise_legacy grouped branch rejects pipeline.statuses/priorities
              that differ from root-level statuses/priorities — raises ConfigError
              with code ERR_CONFLICT_STATUS
  AC3 (td:1): absent or identical pipeline.statuses/priorities normalise unchanged
              (backward compat regression guard)
  AC4 (td:1): save_config writes only next_id — topology fields and pipeline
              sub-sections are product-owned and not persisted to config.yml
              (regression guard)
  AC5 (td:1): round-trip load -> save -> reload -> config.pipeline.statuses and
              config.pipeline.priorities equal product-topology values
              (regression guard)
  AC6 (td:0): docstring on _normalise_legacy -- skip
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from owlbear_kanban.config_loader import load_config
from owlbear_kanban.errors import KANBAN_ERROR_CODES, ConfigError
from owlbear_kanban.models import BoardConfig
from owlbear_kanban.storage import save_config
from owlbear_kanban.topology import PRODUCT_TOPOLOGY

# Provenance: promoted from task-scoped suite for task #1177.

# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

_STATUSES: list[str] = ["research", "backlog", "done"]
_PRIORITIES: list[str] = ["important", "critical"]


def _grouped_data(
    *,
    root_statuses: list[str] | None = None,
    root_priorities: list[str] | None = None,
    extra_pipeline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a minimal valid grouped-schema BoardConfig input dict.

    ``extra_pipeline`` keys are merged into the pipeline section, which lets
    callers inject explicit statuses/priorities to trigger conflict detection.
    """
    statuses = root_statuses if root_statuses is not None else _STATUSES
    priorities = root_priorities if root_priorities is not None else _PRIORITIES

    pipeline: dict[str, Any] = {
        "entry_status": statuses[0],
        "terminal_status": statuses[-1],
        "wave_size": 4,
        "claim_timeout": "1h",
        "default_priority": priorities[0],
    }
    if extra_pipeline:
        pipeline.update(extra_pipeline)

    return {
        "schema": "grouped",
        "statuses": statuses,
        "priorities": priorities,
        "next_id": 1,
        "paths": {"tasks_dir": "tasks", "archive_dir": "archive"},
        "pipeline": pipeline,
        "agents": {
            "agent_map": {s: [] for s in statuses},
            "agent_types": {},
            "agent_compatibility": {},
        },
        "policy": {
            "non_impl_tags": [],
            "archival_reasons": ["completed", "dropped"],
            "status_predicates": {},
        },
    }


def _make_kanban_dir(tmp_path: Path) -> Path:
    """Create a minimal kanban directory with a tasks/ subdirectory."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "tasks").mkdir()
    return kanban_dir


def _write_grouped_config(kanban_dir: Path) -> None:
    """Write a canonical grouped config.yml with root-only statuses/priorities."""
    raw: dict[str, Any] = {
        "schema": "grouped",
        "statuses": _STATUSES,
        "priorities": _PRIORITIES,
        "next_id": 1,
        "activity_log": True,
        "paths": {"tasks_dir": "tasks", "archive_dir": "archive"},
        "pipeline": {
            "entry_status": "research",
            "terminal_status": "done",
            "wave_size": 4,
            "claim_timeout": "1h",
            "default_priority": "important",
        },
        "agents": {
            "agent_map": {s: [] for s in _STATUSES},
            "agent_types": {},
            "agent_compatibility": {},
        },
        "policy": {
            "non_impl_tags": [],
            "archival_reasons": ["completed", "dropped"],
            "status_predicates": {},
        },
    }
    (kanban_dir / "config.yml").write_text(
        yaml.dump(raw, default_flow_style=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# AC1 -- Error catalog registration
# ---------------------------------------------------------------------------


class TestFromAC_ErrorCatalog:
    """AC1 -- ERR_CONFLICT_STATUS must be registered in KANBAN_ERROR_CODES."""

    def test_err_conflict_status_in_kanban_error_codes(self) -> None:
        """ERR_CONFLICT_STATUS is a valid error code in the kanban error catalog."""
        assert "ERR_CONFLICT_STATUS" in KANBAN_ERROR_CODES


# ---------------------------------------------------------------------------
# AC2 -- Conflict detection in _normalise_legacy grouped branch
# ---------------------------------------------------------------------------


class TestFromAC_ConflictValidation:
    """AC2 -- BoardConfig rejects grouped configs where pipeline.statuses/priorities
    diverge from root-level statuses/priorities."""

    def test_grouped_pipeline_statuses_differ_raises_config_error(self) -> None:
        """pipeline.statuses that differ from root statuses must raise ConfigError."""
        data = _grouped_data(extra_pipeline={"statuses": ["todo", "done"]})
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(data)

    def test_grouped_pipeline_statuses_conflict_error_code(self) -> None:
        """ConfigError raised for statuses conflict must carry ERR_CONFLICT_STATUS."""
        data = _grouped_data(extra_pipeline={"statuses": ["todo", "done"]})
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)
        assert exc_info.value.code == "ERR_CONFLICT_STATUS"

    def test_grouped_pipeline_priorities_differ_raises_config_error(self) -> None:
        """pipeline.priorities that differ from root priorities must raise ConfigError."""
        data = _grouped_data(extra_pipeline={"priorities": ["someday", "needed"]})
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(data)

    def test_grouped_pipeline_priorities_conflict_error_code(self) -> None:
        """ConfigError raised for priorities conflict must carry ERR_CONFLICT_STATUS."""
        data = _grouped_data(extra_pipeline={"priorities": ["someday", "needed"]})
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)
        assert exc_info.value.code == "ERR_CONFLICT_STATUS"

    def test_statuses_reorder_is_a_conflict(self) -> None:
        """Same status elements in different order counts as a conflict.

        Order encodes the pipeline progression; reordering breaks semantics.
        """
        reversed_statuses = list(reversed(_STATUSES))
        data = _grouped_data(extra_pipeline={"statuses": reversed_statuses})
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)
        assert exc_info.value.code == "ERR_CONFLICT_STATUS"

    def test_only_statuses_conflict_raises(self) -> None:
        """Conflict on statuses alone (priorities matching root) raises ConfigError."""
        data = _grouped_data(
            extra_pipeline={
                "statuses": ["todo", "done"],
                "priorities": _PRIORITIES,  # same as root -- no conflict
            }
        )
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)
        assert exc_info.value.code == "ERR_CONFLICT_STATUS"

    def test_only_priorities_conflict_raises(self) -> None:
        """Conflict on priorities alone (statuses matching root) raises ConfigError."""
        data = _grouped_data(
            extra_pipeline={
                "statuses": _STATUSES,  # same as root -- no conflict
                "priorities": ["someday", "needed"],
            }
        )
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)
        assert exc_info.value.code == "ERR_CONFLICT_STATUS"

    def test_both_conflict_raises(self) -> None:
        """Conflict on both statuses and priorities raises ConfigError."""
        data = _grouped_data(
            extra_pipeline={
                "statuses": ["todo", "done"],
                "priorities": ["someday", "needed"],
            }
        )
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(data)

    def test_flat_schema_no_conflict_check(self) -> None:
        """Flat schema always rebuilds pipeline from root -- no conflict validation.

        The flat else-branch in _normalise_legacy overwrites data['pipeline']
        entirely from root values, so any stray pipeline input is irrelevant.
        """
        data: dict[str, Any] = {
            "statuses": _STATUSES,
            "priorities": _PRIORITIES,
            "next_id": 1,
            "entry_status": "research",
            "terminal_status": "done",
            "wave_size": 4,
            "claim_timeout": "1h",
            "default_priority": "important",
            "agent_map": {s: [] for s in _STATUSES},
            "agent_types": {},
            "agent_compatibility": {},
        }
        # Must not raise -- flat schema is not subject to conflict validation
        config = BoardConfig.model_validate(data)
        assert config.pipeline.statuses == _STATUSES


# ---------------------------------------------------------------------------
# AC3 -- Backward compat: absent or matching pipeline.statuses/priorities
#        These are regression guards -- they PASS today and must stay green.
# ---------------------------------------------------------------------------


class TestFromAC_BackwardCompat:
    """AC3 -- Regression guard: absent or identical pipeline.statuses/priorities
    normalise without error after the builder adds conflict detection."""

    def test_pipeline_statuses_absent_normalization_succeeds(self) -> None:
        """Grouped config without an explicit pipeline.statuses key succeeds."""
        data = _grouped_data()  # pipeline has no statuses key
        config = BoardConfig.model_validate(data)
        assert config is not None

    def test_pipeline_statuses_absent_equals_root(self) -> None:
        """When pipeline.statuses is absent, setdefault copies root statuses."""
        data = _grouped_data()
        config = BoardConfig.model_validate(data)
        assert config.pipeline.statuses == config.statuses

    def test_pipeline_statuses_identical_to_root_succeeds(self) -> None:
        """Grouped config where pipeline.statuses exactly equals root statuses succeeds."""
        data = _grouped_data(extra_pipeline={"statuses": list(_STATUSES)})
        config = BoardConfig.model_validate(data)
        assert config.pipeline.statuses == config.statuses

    def test_pipeline_priorities_absent_normalization_succeeds(self) -> None:
        """Grouped config without an explicit pipeline.priorities key succeeds."""
        data = _grouped_data()
        config = BoardConfig.model_validate(data)
        assert config is not None

    def test_pipeline_priorities_absent_equals_root(self) -> None:
        """When pipeline.priorities is absent, setdefault copies root priorities."""
        data = _grouped_data()
        config = BoardConfig.model_validate(data)
        assert config.pipeline.priorities == config.priorities

    def test_pipeline_priorities_identical_to_root_succeeds(self) -> None:
        """Grouped config where pipeline.priorities exactly equals root priorities succeeds."""
        data = _grouped_data(extra_pipeline={"priorities": list(_PRIORITIES)})
        config = BoardConfig.model_validate(data)
        assert config.pipeline.priorities == config.priorities


# ---------------------------------------------------------------------------
# AC4 -- save_config writes next_id-only checkpoint (regression guard)
# ---------------------------------------------------------------------------


class TestFromAC_SaveConfigRootOnly:
    """AC4 -- Regression guard: save_config writes only next_id to config.yml;
    all topology fields and pipeline sub-sections are product-owned and not persisted."""

    def test_save_config_writes_next_id_only(self, tmp_path: Path) -> None:
        """save_config writes only next_id at the root level."""
        kanban_dir = _make_kanban_dir(tmp_path)
        _write_grouped_config(kanban_dir)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)

        raw = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert set(raw.keys()) == {"next_id"}

    def test_save_config_persists_current_next_id(self, tmp_path: Path) -> None:
        """save_config persists the current next_id value."""
        kanban_dir = _make_kanban_dir(tmp_path)
        _write_grouped_config(kanban_dir)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)

        raw = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        assert raw == {"next_id": config.next_id}

    def test_save_config_omits_pipeline_statuses(self, tmp_path: Path) -> None:
        """save_config must not write pipeline.statuses -- root is the sole location."""
        kanban_dir = _make_kanban_dir(tmp_path)
        _write_grouped_config(kanban_dir)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)

        raw = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        pipeline_section = raw.get("pipeline", {})
        assert "statuses" not in pipeline_section

    def test_save_config_omits_pipeline_priorities(self, tmp_path: Path) -> None:
        """save_config must not write pipeline.priorities -- root is the sole location."""
        kanban_dir = _make_kanban_dir(tmp_path)
        _write_grouped_config(kanban_dir)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)

        raw = yaml.safe_load((kanban_dir / "config.yml").read_text(encoding="utf-8"))
        pipeline_section = raw.get("pipeline", {})
        assert "priorities" not in pipeline_section


# ---------------------------------------------------------------------------
# AC5 -- Round-trip regression guard
# ---------------------------------------------------------------------------


class TestFromAC_RoundTrip:
    """AC5 -- Regression guard: load -> save -> reload preserves
    pipeline.statuses == config.statuses and pipeline.priorities == config.priorities."""

    def test_round_trip_pipeline_statuses_match_root(self, tmp_path: Path) -> None:
        """After save -> reload, config.pipeline.statuses equals config.statuses."""
        kanban_dir = _make_kanban_dir(tmp_path)
        _write_grouped_config(kanban_dir)

        config1 = load_config(kanban_dir)
        save_config(config1, kanban_dir)
        config2 = load_config(kanban_dir)

        assert config2.pipeline.statuses == config2.statuses
        assert config2.statuses == list(PRODUCT_TOPOLOGY.statuses)

    def test_round_trip_pipeline_priorities_match_root(self, tmp_path: Path) -> None:
        """After save -> reload, config.pipeline.priorities equals config.priorities."""
        kanban_dir = _make_kanban_dir(tmp_path)
        _write_grouped_config(kanban_dir)

        config1 = load_config(kanban_dir)
        save_config(config1, kanban_dir)
        config2 = load_config(kanban_dir)

        assert config2.pipeline.priorities == config2.priorities
        assert config2.priorities == list(PRODUCT_TOPOLOGY.priorities)
