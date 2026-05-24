"""Grouped config and topology contract tests for the kanban engine.

These are the behavior-focused successors to the original accessor migration
source-inspection tests. Runtime topology is product-owned; ``config.yml`` is a
``next_id`` checkpoint, while direct ``BoardConfig`` validation still supports
legacy/grouped migration paths.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.models import (
    AgentsConfig,
    BoardConfig,
    ConfigError,
    PathsConfig,
    PipelineConfig,
    PolicyConfig,
)
from owlbear_kanban.topology import PRODUCT_TOPOLOGY

_STALE_CONFIG = dedent("""\
    schema: grouped
    statuses:
      - waiting
      - shipped
    priorities:
      - whenever
      - urgentish
    next_id: 37
    paths:
      tasks_dir: stale-tasks
      archive_dir: stale-archive
    pipeline:
      entry_status: waiting
      terminal_status: shipped
      wave_size: 1
      claim_timeout: 9h
      default_priority: urgentish
    agents:
      agent_map:
        waiting: stale-agent
        shipped: stale-auditor
      agent_types:
        stale-agent: {}
      agent_compatibility:
        stale-agent:
          - stale-auditor
        stale-auditor:
          - stale-agent
    policy:
      non_impl_tags:
        - stale-tag
      archival_reasons:
        - stale-reason
      status_predicates:
        shipped:
          requires:
            - Proof
    """)


def _make_board(base_dir: Path, config_text: str = _STALE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_text, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _minimal_grouped_config() -> dict[str, object]:
    return {
        "schema": "grouped",
        "statuses": ["research", "review", "done"],
        "priorities": ["important", "critical"],
        "paths": {"tasks_dir": "tasks", "archive_dir": "archive"},
        "pipeline": {
            "entry_status": "research",
            "terminal_status": "done",
            "wave_size": 2,
            "claim_timeout": "2h",
            "default_priority": "important",
        },
        "agents": {
            "agent_map": {"research": "researcher", "review": "reviewer", "done": "auditor"},
            "agent_types": {},
            "agent_compatibility": {},
        },
        "policy": {
            "non_impl_tags": ["docs"],
            "archival_reasons": ["completed"],
            "status_predicates": {},
        },
    }


class TestFromAC_ProductTopologyProjection:
    """Runtime config uses PRODUCT_TOPOLOGY, not topology fields from config.yml."""

    def test_load_config_projects_product_topology_into_root_and_submodels(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)

        config = load_config(kanban_dir)

        assert config.next_id == 37
        assert config.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert config.priorities == list(PRODUCT_TOPOLOGY.priorities)
        assert config.paths.tasks_dir == PRODUCT_TOPOLOGY.tasks_dir
        assert config.paths.archive_dir == PRODUCT_TOPOLOGY.archive_dir
        assert config.pipeline.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert config.pipeline.priorities == list(PRODUCT_TOPOLOGY.priorities)
        assert config.pipeline.entry_status == PRODUCT_TOPOLOGY.entry_status
        assert config.pipeline.terminal_status == PRODUCT_TOPOLOGY.terminal_status
        assert config.pipeline.default_priority == PRODUCT_TOPOLOGY.default_priority
        assert config.pipeline.claim_timeout == PRODUCT_TOPOLOGY.claim_timeout
        assert config.pipeline.wave_size == PRODUCT_TOPOLOGY.wave_size
        assert config.agents.agent_map == dict(PRODUCT_TOPOLOGY.agent_map)
        assert config.agents.agent_types == dict(PRODUCT_TOPOLOGY.agent_types)
        assert config.agents.agent_compatibility == dict(PRODUCT_TOPOLOGY.agent_compatibility)
        assert config.policy.non_impl_tags == sorted(PRODUCT_TOPOLOGY.non_impl_tags)
        assert config.policy.archival_reasons == PRODUCT_TOPOLOGY.archival_reasons
        assert config.policy.status_predicates == PRODUCT_TOPOLOGY.status_predicates

    def test_board_config_returns_grouped_submodel_instances(self, tmp_path: Path) -> None:
        config = KanbanEngine(_make_board(tmp_path), activity_log=False).board_config()

        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.pipeline, PipelineConfig)
        assert isinstance(config.agents, AgentsConfig)
        assert isinstance(config.policy, PolicyConfig)

    def test_refresh_config_reloads_next_id_without_accepting_stale_topology(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)

        (kanban_dir / "config.yml").write_text(_STALE_CONFIG.replace("next_id: 37", "next_id: 91"), encoding="utf-8")
        engine.refresh_config()
        config = engine.board_config()

        assert config.next_id == 91
        assert config.pipeline.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert config.pipeline.priorities == list(PRODUCT_TOPOLOGY.priorities)
        assert config.agents.agent_map == dict(PRODUCT_TOPOLOGY.agent_map)
        assert config.policy.status_predicates == PRODUCT_TOPOLOGY.status_predicates

    def test_create_task_uses_product_paths_and_defaults(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)

        task = engine.create_task("Topology backed task")

        assert task.status == PRODUCT_TOPOLOGY.entry_status
        assert task.priority == PRODUCT_TOPOLOGY.default_priority
        assert list((kanban_dir / PRODUCT_TOPOLOGY.tasks_dir).glob(f"{task.id}-*.md"))
        assert not (kanban_dir / "stale-tasks").exists()

    def test_create_task_rejects_status_and_priority_from_ignored_config(self, tmp_path: Path) -> None:
        engine = KanbanEngine(_make_board(tmp_path), activity_log=False)

        with pytest.raises(ValueError, match="Invalid status"):
            engine.create_task("Bad status", status="waiting")

        with pytest.raises(ValueError, match="Invalid priority"):
            engine.create_task("Bad priority", priority="urgentish")


class TestFromAC_GroupedBoardConfigValidation:
    """Direct BoardConfig validation keeps grouped migration behavior honest."""

    def test_pipeline_config_exposes_statuses_and_priorities_fields(self) -> None:
        assert "statuses" in PipelineConfig.model_fields
        assert "priorities" in PipelineConfig.model_fields

    def test_grouped_input_copies_root_statuses_and_priorities_into_pipeline(self) -> None:
        config = BoardConfig.model_validate(_minimal_grouped_config())

        assert config.pipeline.statuses == config.statuses
        assert config.pipeline.priorities == config.priorities

    def test_grouped_input_accepts_matching_pipeline_statuses_and_priorities(self) -> None:
        data = _minimal_grouped_config()
        data["pipeline"] = {
            **data["pipeline"],  # type: ignore[dict-item]
            "statuses": data["statuses"],
            "priorities": data["priorities"],
        }

        config = BoardConfig.model_validate(data)

        assert config.pipeline.statuses == ["research", "review", "done"]
        assert config.pipeline.priorities == ["important", "critical"]

    def test_grouped_input_rejects_pipeline_status_conflict(self) -> None:
        data = _minimal_grouped_config()
        data["pipeline"] = {
            **data["pipeline"],  # type: ignore[dict-item]
            "statuses": ["research", "done"],
        }

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)

        assert exc_info.value.code == "ERR_CONFLICT_STATUS"
        assert "pipeline.statuses conflicts" in exc_info.value.user_message

    def test_grouped_input_rejects_pipeline_priority_conflict(self) -> None:
        data = _minimal_grouped_config()
        data["pipeline"] = {
            **data["pipeline"],  # type: ignore[dict-item]
            "priorities": ["someday"],
        }

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)

        assert exc_info.value.code == "ERR_CONFLICT_STATUS"
        assert "pipeline.priorities conflicts" in exc_info.value.user_message

    def test_flat_legacy_input_is_normalized_to_grouped_submodels(self) -> None:
        config = BoardConfig.model_validate(
            {
                "statuses": ["research", "done"],
                "priorities": ["important", "critical"],
                "tasks_dir": "work-items",
                "archive_dir": "cold-storage",
                "entry_status": "research",
                "terminal_status": "done",
                "wave_size": 3,
                "claim_timeout": "3h",
                "default_priority": "critical",
                "agent_map": {"research": "researcher", "done": "auditor"},
                "agent_types": {"researcher": {}, "auditor": {}},
                "agent_compatibility": {"researcher": ["auditor"], "auditor": ["researcher"]},
                "non_impl_tags": ["docs"],
                "archival_reasons": ["completed"],
                "status_predicates": {"done": {"requires": ["Proof"]}},
            }
        )

        assert config.paths.tasks_dir == "work-items"
        assert config.paths.archive_dir == "cold-storage"
        assert config.pipeline.statuses == ["research", "done"]
        assert config.pipeline.priorities == ["important", "critical"]
        assert config.pipeline.wave_size == 3
        assert config.pipeline.claim_timeout == "3h"
        assert config.pipeline.default_priority == "critical"
        assert config.agents.agent_map == {"research": "researcher", "done": "auditor"}
        assert config.policy.non_impl_tags == ["docs"]
        assert config.policy.status_predicates == {"done": {"requires": ["Proof"]}}

    def test_mixed_flat_and_grouped_input_requires_grouped_schema_marker(self) -> None:
        data = {
            "statuses": ["research", "done"],
            "priorities": ["important"],
            "entry_status": "research",
            "pipeline": {"entry_status": "research", "terminal_status": "done"},
        }

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig.model_validate(data)

        assert exc_info.value.code == "ERR_INVALID_STATUS"
        assert "mixes flat and grouped keys" in exc_info.value.user_message
