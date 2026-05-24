"""Dispatch topology authority tests.

These are the topology-constant successors for the old dispatch-rank validation
tests. Runtime board topology is product-owned; config.yml is a next_id
checkpoint and does not override statuses, priorities, or dispatch rank maps.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from owlbear_kanban import KanbanEngine
from owlbear_kanban.topology import PRODUCT_TOPOLOGY

_CONFIG_TEMPLATE = dedent("""\
    schema: grouped
    statuses:
{statuses_yaml}
    priorities:
{priorities_yaml}
    next_id: {next_id}
    pipeline:
      entry_status: research
      terminal_status: done
      wave_size: 0
      claim_timeout: 1h
    agents:
      agent_map: {{}}
      agent_types: {{}}
      agent_compatibility: {{}}
    """)


def _yaml_list(values: list[str]) -> str:
    return "\n".join(f"      - {value}" for value in values)


def _write_config(
    kanban_dir: Path,
    *,
    priorities: list[str],
    statuses: list[str],
    next_id: int = 1,
) -> None:
    config_text = _CONFIG_TEMPLATE.format(
        priorities_yaml=_yaml_list(priorities),
        statuses_yaml=_yaml_list(statuses),
        next_id=next_id,
    )
    (kanban_dir / "config.yml").write_text(config_text, encoding="utf-8")


def _make_board(
    base_dir: Path,
    *,
    priorities: list[str] | None = None,
    statuses: list[str] | None = None,
    next_id: int = 1,
) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    _write_config(
        kanban_dir,
        priorities=priorities or ["galaxy-brain"],
        statuses=statuses or ["waiting", "done"],
        next_id=next_id,
    )
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


class TestFromAC_DispatchTopologyAuthority:
    """Dispatch ranks are valid because PRODUCT_TOPOLOGY owns runtime topology."""

    def test_init_uses_product_priorities_when_config_contains_unknown_priorities(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, priorities=["alpha-tier", "omega-tier"])

        config = KanbanEngine(kanban_dir, activity_log=False).board_config()

        assert config.priorities == list(PRODUCT_TOPOLOGY.priorities)
        assert config.pipeline.priorities == list(PRODUCT_TOPOLOGY.priorities)
        assert "alpha-tier" not in config.priorities
        assert "omega-tier" not in config.priorities

    def test_init_uses_product_statuses_when_config_contains_unknown_statuses(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, statuses=["parked", "shelved", "done"])

        config = KanbanEngine(kanban_dir, activity_log=False).board_config()

        assert config.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert config.pipeline.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert "parked" not in config.statuses
        assert "shelved" not in config.statuses

    def test_refresh_config_keeps_product_priorities_when_config_changes(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)

        _write_config(
            kanban_dir,
            priorities=["hypercritical"],
            statuses=["research", "done"],
            next_id=42,
        )
        engine.refresh_config()
        config = engine.board_config()

        assert config.priorities == list(PRODUCT_TOPOLOGY.priorities)
        assert config.pipeline.priorities == list(PRODUCT_TOPOLOGY.priorities)
        assert config.next_id == 42

    def test_refresh_config_keeps_product_statuses_when_config_changes(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)

        _write_config(
            kanban_dir,
            priorities=["critical"],
            statuses=["waiting", "done"],
            next_id=7,
        )
        engine.refresh_config()
        config = engine.board_config()

        assert config.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert config.pipeline.statuses == list(PRODUCT_TOPOLOGY.statuses)
        assert config.next_id == 7
