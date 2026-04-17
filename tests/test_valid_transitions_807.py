"""Tests for valid_transitions() on KanbanEngine (#807, RED phase).

NOTE: GREEN-on-arrival. The valid_transitions() implementation already exists in
engine.py at the time these tests were written. Tests are written such that they
would fail in the absence of the implementation. This situation is documented in
the architecture review and research doc; paired task #808 (GREEN) acknowledges it.

AC coverage:
  AC1 - returns set of all configured statuses except the given one
  AC2 - invalid status input raises ValueError
  AC3 - transitions match config-defined statuses (config-driven, not hardcoded)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Config constants
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
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
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 1
"""

_CUSTOM_CONFIG_YAML = """\
version: 10
board:
    name: TestBoard
tasks_dir: tasks
statuses:
    - name: open
    - name: closed
priorities:
    - low
    - high
defaults:
    status: open
    priority: low
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 1
"""

_ALL_DEFAULT_STATUSES = [
    "research",
    "backlog",
    "todo",
    "in-progress",
    "review",
    "docs",
    "done",
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with standard 7-status config."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine wired to the 7-status kanban_dir."""
    return KanbanEngine(kanban_dir)


@pytest.fixture()
def custom_kanban_dir(tmp_path: Path) -> Path:
    """Kanban directory with a minimal 2-status config for config-driven tests."""
    d = tmp_path / "custom"
    d.mkdir()
    (d / "config.yml").write_text(_CUSTOM_CONFIG_YAML, encoding="utf-8")
    (d / "tasks").mkdir()
    return d


@pytest.fixture()
def custom_engine(custom_kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine wired to the 2-status custom_kanban_dir."""
    return KanbanEngine(custom_kanban_dir)


# ===========================================================================
# TestFromAC_ValidTransitions
# ===========================================================================


class TestFromAC_ValidTransitions:
    """Contract tests for KanbanEngine.valid_transitions(status)."""

    # -------------------------------------------------------------------
    # AC1: returns set of all configured statuses except the given one
    # -------------------------------------------------------------------

    @pytest.mark.parametrize("status", _ALL_DEFAULT_STATUSES)
    def test_returns_all_statuses_except_given(self, engine: KanbanEngine, status: str) -> None:
        """Each of the 7 configured statuses returns the other 6 as a set."""
        result = engine.valid_transitions(status)
        expected = set(_ALL_DEFAULT_STATUSES) - {status}
        assert result == expected

    @pytest.mark.parametrize("status", _ALL_DEFAULT_STATUSES)
    def test_given_status_excluded_from_result(self, engine: KanbanEngine, status: str) -> None:
        """The current status is never included in the returned transition set."""
        result = engine.valid_transitions(status)
        assert status not in result

    def test_return_type_is_set(self, engine: KanbanEngine) -> None:
        """Return value is a set, not a list, tuple, or other iterable."""
        result = engine.valid_transitions("research")
        assert isinstance(result, set)

    def test_hyphenated_status_returns_correct_set(self, engine: KanbanEngine) -> None:
        """Hyphenated status 'in-progress' is handled the same as any other status."""
        result = engine.valid_transitions("in-progress")
        assert "in-progress" not in result
        assert len(result) == len(_ALL_DEFAULT_STATUSES) - 1

    # -------------------------------------------------------------------
    # AC2: invalid status raises ValueError
    # -------------------------------------------------------------------

    def test_unknown_status_raises_value_error(self, engine: KanbanEngine) -> None:
        """An unrecognised status string raises ValueError."""
        with pytest.raises(ValueError, match="nonexistent"):
            engine.valid_transitions("nonexistent")

    def test_empty_string_raises_value_error(self, engine: KanbanEngine) -> None:
        """Empty string is not a valid status and raises ValueError."""
        with pytest.raises(ValueError):
            engine.valid_transitions("")

    def test_case_mismatch_raises_value_error(self, engine: KanbanEngine) -> None:
        """Status names are case-sensitive — 'RESEARCH' is not 'research'."""
        with pytest.raises(ValueError):
            engine.valid_transitions("RESEARCH")

    def test_value_error_message_names_invalid_status(self, engine: KanbanEngine) -> None:
        """ValueError message identifies the offending status value."""
        with pytest.raises(ValueError, match="Invalid status"):
            engine.valid_transitions("bogus")

    # -------------------------------------------------------------------
    # AC3: transitions match config-defined statuses (config-driven)
    # -------------------------------------------------------------------

    def test_custom_config_two_statuses_returns_one(self, custom_engine: KanbanEngine) -> None:
        """With a 2-status config, each status yields exactly {the other one}."""
        result = custom_engine.valid_transitions("open")
        assert result == {"closed"}

    def test_custom_config_result_is_subset_of_configured_names(self, custom_engine: KanbanEngine) -> None:
        """All returned transitions are names actually defined in config."""
        result = custom_engine.valid_transitions("open")
        configured = {"open", "closed"}
        assert result.issubset(configured)

    def test_custom_config_excludes_default_status_names(self, custom_engine: KanbanEngine) -> None:
        """Default status names (e.g. 'research') never appear in a custom-config result."""
        result = custom_engine.valid_transitions("open")
        assert result.isdisjoint(set(_ALL_DEFAULT_STATUSES))

    def test_result_count_is_total_statuses_minus_one_custom(self, custom_engine: KanbanEngine) -> None:
        """Result size equals (number of configured statuses - 1) for custom config."""
        result = custom_engine.valid_transitions("closed")
        assert len(result) == 1

    def test_result_count_is_total_statuses_minus_one_default(self, engine: KanbanEngine) -> None:
        """Result size equals (number of configured statuses - 1) across all defaults."""
        for status in _ALL_DEFAULT_STATUSES:
            result = engine.valid_transitions(status)
            assert len(result) == len(_ALL_DEFAULT_STATUSES) - 1
