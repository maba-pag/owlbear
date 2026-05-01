"""RED-phase tests for KanbanEngine init and BoardConfig validation (task #1067).

Covers:
  - AC-NEW-14: entry_status not in statuses → ConfigError(ERR_ENTRY_STATUS_INVALID)
  - AC-NEW-23: terminal_status not in statuses or not statuses[-1]
                → ConfigError(ERR_TERMINAL_STATUS_INVALID)
  - D24: agent_map missing a declared status → ConfigError at init
  - D29: claim_timeout extended format — Ns and Nd accepted without error
  - D33: engine constructor has no agent_name parameter
  - D63: agent_compatibility not symmetric → ConfigError at init
    - Role views: AgentView constructable from a valid engine

All tests FAIL in RED phase — validation logic and role-view classes are not yet
implemented in owlbear_kanban.engine.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ConfigError

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - done
priorities:
  - someday
  - needed
  - critical
claim_timeout: 1h
next_id: 1
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# AC-NEW-14 — entry_status not in statuses → ConfigError(ERR_ENTRY_STATUS_INVALID)
# ---------------------------------------------------------------------------


class TestFromAC_EntryStatusValidation:
    """AC-NEW-14: entry_status not in statuses → ConfigError(ERR_ENTRY_STATUS_INVALID)."""

    def test_entry_status_not_in_statuses_raises_config_error(self, tmp_path: Path) -> None:
        config = _BASE_CONFIG.replace("entry_status: research", "entry_status: missing")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"

    def test_entry_status_wrong_case_raises_config_error(self, tmp_path: Path) -> None:
        # "RESEARCH" is not in statuses which contains "research" — case-sensitive check
        config = _BASE_CONFIG.replace("entry_status: research", "entry_status: RESEARCH")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"

    def test_entry_status_empty_string_raises_config_error(self, tmp_path: Path) -> None:
        config = _BASE_CONFIG.replace("entry_status: research", "entry_status: ''")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"


# ---------------------------------------------------------------------------
# AC-NEW-23 — terminal_status not in statuses or not statuses[-1]
#              → ConfigError(ERR_TERMINAL_STATUS_INVALID)
# ---------------------------------------------------------------------------


class TestFromAC_TerminalStatusValidation:
    """AC-NEW-23: invalid terminal_status → ConfigError(ERR_TERMINAL_STATUS_INVALID)."""

    def test_terminal_status_not_in_statuses_raises_config_error(
        self, tmp_path: Path
    ) -> None:
        # "nonexistent" is not in statuses at all
        config = _BASE_CONFIG.replace("terminal_status: done", "terminal_status: nonexistent")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"

    def test_terminal_status_in_statuses_but_not_last_raises_config_error(
        self, tmp_path: Path
    ) -> None:
        # "todo" is in statuses but is not the last element ("done" is)
        config = _BASE_CONFIG.replace("terminal_status: done", "terminal_status: todo")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"

    def test_terminal_status_first_element_raises_config_error(
        self, tmp_path: Path
    ) -> None:
        # "research" is statuses[0], not statuses[-1]
        config = _BASE_CONFIG.replace("terminal_status: done", "terminal_status: research")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"


# ---------------------------------------------------------------------------
# D24 — agent_map must cover all declared statuses
# ---------------------------------------------------------------------------


class TestFromAC_AgentMapCoverage:
    """D24: agent_map missing a declared status → ConfigError at init."""

    def test_agent_map_missing_one_status_raises(self, tmp_path: Path) -> None:
        # Remove the "done" entry — agent_map no longer covers all statuses
        config = _BASE_CONFIG.replace("  done: auditor\n", "")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError):
            KanbanEngine(kanban_dir)

    def test_agent_map_empty_with_nonempty_statuses_raises(self, tmp_path: Path) -> None:
        config = _BASE_CONFIG.replace(
            "agent_map:\n  research: researcher\n  backlog: architect\n  todo: builder\n  done: auditor",
            "agent_map: {}",
        )
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError):
            KanbanEngine(kanban_dir)


# ---------------------------------------------------------------------------
# D29 — claim_timeout extended format: Ns and Nd accepted without error
# ---------------------------------------------------------------------------


class TestFromAC_ClaimTimeoutFormat:
    """D29: claim_timeout accepts Ns/Nm/Nh/Nd; new Ns and Nd units must not raise."""

    def test_claim_timeout_seconds_unit_accepted(self, tmp_path: Path) -> None:
        # "30s" is valid per D29 — must not raise ConfigError
        config = _BASE_CONFIG.replace("claim_timeout: 1h", "claim_timeout: 30s")
        kanban_dir = _make_board(tmp_path, config)
        KanbanEngine(kanban_dir)  # must not raise

    def test_claim_timeout_days_unit_accepted(self, tmp_path: Path) -> None:
        # "2d" is valid per D29 — must not raise ConfigError
        config = _BASE_CONFIG.replace("claim_timeout: 1h", "claim_timeout: 2d")
        kanban_dir = _make_board(tmp_path, config)
        KanbanEngine(kanban_dir)  # must not raise

    def test_claim_timeout_unknown_unit_raises_config_error(self, tmp_path: Path) -> None:
        # "30x" has an unrecognised unit — must raise ERR_INVALID_CLAIM_TIMEOUT
        config = _BASE_CONFIG.replace("claim_timeout: 1h", "claim_timeout: 30x")
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_claim_timeout_bare_number_raises_config_error(self, tmp_path: Path) -> None:
        # "30" (quoted string, no unit) is ambiguous and must raise ERR_INVALID_CLAIM_TIMEOUT.
        # Use a quoted YAML value so Pydantic receives a string and _parse_duration does the check.
        config = _BASE_CONFIG.replace("claim_timeout: 1h", 'claim_timeout: "30"')
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"


# ---------------------------------------------------------------------------
# D63 — agent_compatibility must be symmetric
# ---------------------------------------------------------------------------


class TestFromAC_AgentCompatibilitySymmetry:
    """D63: agent_compatibility not symmetric → ConfigError at init."""

    def test_single_direction_compatibility_raises(self, tmp_path: Path) -> None:
        # builder lists reviewer but reviewer has empty list (no builder)
        config = _BASE_CONFIG.replace(
            "agent_compatibility: {}",
            "agent_compatibility:\n  builder: [reviewer]\n  reviewer: []",
        )
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError):
            KanbanEngine(kanban_dir)

    def test_missing_reverse_key_raises(self, tmp_path: Path) -> None:
        # builder lists reviewer but reviewer key is absent entirely
        config = _BASE_CONFIG.replace(
            "agent_compatibility: {}",
            "agent_compatibility:\n  builder: [reviewer]",
        )
        kanban_dir = _make_board(tmp_path, config)
        with pytest.raises(ConfigError):
            KanbanEngine(kanban_dir)


# ---------------------------------------------------------------------------
# Role views — AgentView constructable from a valid engine
# ---------------------------------------------------------------------------


class TestFromAC_ValidConfigAndRoleViews:
    """Valid config constructs engine + AgentView without error."""

    def test_agent_view_constructable_from_valid_engine(self, tmp_path: Path) -> None:
        from owlbear_kanban.engine import AgentView  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        agent_view = AgentView(engine)
        assert agent_view is not None


# ---------------------------------------------------------------------------
# D33 — engine constructor has no agent_name parameter
# ---------------------------------------------------------------------------


class TestFromAC_NoAgentNameParam:
    """D33: KanbanEngine.__init__ must not accept an agent_name constructor parameter."""

    def test_constructor_signature_excludes_agent_name(self) -> None:
        sig = inspect.signature(KanbanEngine.__init__)
        assert "agent_name" not in sig.parameters

    def test_constructor_rejects_agent_name_kwarg_at_runtime(self, tmp_path: Path) -> None:
        """Passing agent_name at runtime must raise TypeError per D33 behavioral contract.

        D33 states the constructor no longer accepts agent_name.  A hidden **kwargs
        path that silently absorbs the argument violates that contract even when it
        is absent from the explicit parameter list.
        """
        kanban_dir = _make_board(tmp_path)
        with pytest.raises(TypeError):
            KanbanEngine(kanban_dir, agent_name="some-agent")
