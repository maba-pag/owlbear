"""Agent-map behavior under product-owned topology (#1221/#1816).

Config-file agent_map entries are no longer runtime authority. KanbanEngine and
pick_tasks use PRODUCT_TOPOLOGY.agent_map, while config.yml remains a next_id
checkpoint.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ValidationError
from owlbear_kanban.topology import PRODUCT_TOPOLOGY

_CONFIG_TEMPLATE = dedent("""\
    schema: grouped
    statuses:
      - research
      - backlog
      - todo
      - in-progress
      - review
      - done
    priorities:
      - critical
      - needed
      - important
      - nice-to-have
      - someday
    next_id: {next_id}
    pipeline:
      entry_status: research
      terminal_status: done
      wave_size: {wave_size}
      claim_timeout: 1h
    agents:
      agent_map:{agent_map_body}
      agent_types: {{}}
      agent_compatibility: {{}}
    """)

_EMPTY_AGENT_MAP = " {}"
_PARTIAL_AGENT_MAP = "\n        research: researcher\n        backlog: architect"


def _make_board(
    base_dir: Path,
    *,
    agent_map_body: str = _EMPTY_AGENT_MAP,
    wave_size: int = 4,
    next_id: int = 1,
) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    config_text = _CONFIG_TEMPLATE.format(
        agent_map_body=agent_map_body,
        wave_size=wave_size,
        next_id=next_id,
    )
    (kanban_dir / "config.yml").write_text(config_text, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


class TestFromAC_InitUsesProductAgentMap:
    """KanbanEngine init uses PRODUCT_TOPOLOGY regardless of config agent_map."""

    def test_init_accepts_empty_config_agent_map(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, agent_map_body=_EMPTY_AGENT_MAP)

        config = KanbanEngine(kanban_dir).board_config()

        assert config.agents.agent_map == dict(PRODUCT_TOPOLOGY.agent_map)

    def test_init_accepts_partial_config_agent_map(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, agent_map_body=_PARTIAL_AGENT_MAP)

        config = KanbanEngine(kanban_dir).board_config()

        assert config.agents.agent_map == dict(PRODUCT_TOPOLOGY.agent_map)


class TestFromAC_PickTasksUsesProductAgentMap:
    """pick_tasks validates explicit params, then dispatches with product agent_map."""

    def test_pick_tasks_succeeds_with_empty_config_agent_map(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, agent_map_body=_EMPTY_AGENT_MAP)
        response = KanbanEngine(kanban_dir).agent_view().pick_tasks()

        assert response.waves == []
        assert response.guidance == []

    def test_pick_tasks_succeeds_with_partial_config_agent_map(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, agent_map_body=_PARTIAL_AGENT_MAP)
        response = KanbanEngine(kanban_dir).agent_view().pick_tasks()

        assert response.waves == []
        assert response.guidance == []

    def test_pick_tasks_ignores_config_wave_size_but_validates_explicit_wave_size(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, agent_map_body=_EMPTY_AGENT_MAP, wave_size=0)
        view = KanbanEngine(kanban_dir).agent_view()

        assert view.pick_tasks().waves == []
        with pytest.raises(ValidationError) as exc_info:
            view.pick_tasks(wave_size=0)

        assert exc_info.value.code == "ERR_INVALID_WAVE_PARAM"

    def test_pick_tasks_uses_product_agent_map_after_refresh_config(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path, agent_map_body=_PARTIAL_AGENT_MAP)
        engine = KanbanEngine(kanban_dir)

        (kanban_dir / "config.yml").write_text(
            _CONFIG_TEMPLATE.format(agent_map_body=_EMPTY_AGENT_MAP, wave_size=0, next_id=99),
            encoding="utf-8",
        )
        engine.refresh_config()

        assert engine.board_config().agents.agent_map == dict(PRODUCT_TOPOLOGY.agent_map)
        assert engine.board_config().next_id == 99
        assert engine.agent_view().pick_tasks().waves == []


class TestFromAC_McpPickTasksUsesProductAgentMap:
    """MCP pick_tasks returns a normal response when config agent_map is incomplete."""

    @pytest.mark.asyncio
    async def test_mcp_pick_tasks_returns_response_for_empty_config_agent_map(self, tmp_path: Path) -> None:
        from owlbear_mcp_kanban.server import AppContext, pick_tasks

        kanban_dir = _make_board(tmp_path, agent_map_body=_EMPTY_AGENT_MAP)
        app_ctx = AppContext(engine=KanbanEngine(kanban_dir), kanban_dir=kanban_dir)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        response = await pick_tasks(ctx)

        assert response.waves == []
        assert response.guidance == []

    @pytest.mark.asyncio
    async def test_mcp_pick_tasks_validates_explicit_wave_size(self, tmp_path: Path) -> None:
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_kanban.server import AppContext, pick_tasks

        kanban_dir = _make_board(tmp_path, agent_map_body=_PARTIAL_AGENT_MAP)
        app_ctx = AppContext(engine=KanbanEngine(kanban_dir), kanban_dir=kanban_dir)
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(ctx, wave_size=0)

        assert "ERR_INVALID_WAVE_PARAM" in str(exc_info.value)
