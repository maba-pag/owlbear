"""RED-phase tests for dispatch-constant validation at engine init and refresh_config (#1209).

AC coverage:
  AC1 (td:2): __init__ validates config.priorities against dispatch.PRIORITY_RANK →
      TestFromAC_InitDispatchValidation.test_unknown_priority_raises_with_correct_code
      TestFromAC_InitDispatchValidation.test_priority_error_message_lists_unranked_values
      TestFromAC_InitDispatchValidation.test_multiple_unknown_priorities_all_in_message

  AC2 (td:2): __init__ validates config.statuses against dispatch.STATUS_RANK →
      TestFromAC_InitDispatchValidation.test_unknown_status_raises_with_correct_code
      TestFromAC_InitDispatchValidation.test_status_error_message_lists_unranked_values
      TestFromAC_InitDispatchValidation.test_multiple_unknown_statuses_all_in_message

  AC3 (td:1): refresh_config runs same validation →
      TestFromAC_RefreshConfigValidation.test_refresh_config_raises_on_dispatch_mismatch

  AC4 (td:0): error codes in KANBAN_ERROR_CODES — no test (td:0 skip).
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ConfigError

# ---------------------------------------------------------------------------
# Board setup helpers
# ---------------------------------------------------------------------------

_CONFIG_TEMPLATE = dedent("""\
    schema: grouped
    statuses:
    {statuses_yaml}
    priorities:
    {priorities_yaml}
    next_id: 1
    paths:
        tasks_dir: tasks
        archive_dir: archive
    pipeline:
        entry_status: research
        terminal_status: done
        wave_size: 4
        claim_timeout: 1h
    agents:
        agent_map:
            research: researcher
            backlog: architect
            todo: builder
            in-progress: builder
            review: reviewer
            done: auditor
        agent_types: {{}}
        agent_compatibility: {{}}
    policy:
        non_impl_tags: [research, docs]
        archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
        status_predicates: {{}}
    """)

_STANDARD_STATUSES = [
    "research", "backlog", "todo", "in-progress", "review", "done",
]
_STANDARD_PRIORITIES = [
    "someday", "nice-to-have", "important", "needed", "critical",
]

# Statuses with one unknown inserted in the middle (keeps "done" as last = terminal_status).
_STATUSES_WITH_WAITING = [
    "research", "backlog", "todo", "waiting", "in-progress", "review", "done",
]
_STATUSES_WITH_PARKED_AND_SHELVED = [
    "research", "backlog", "parked", "todo", "shelved", "in-progress", "review", "done",
]


def _make_board(
    base: Path,
    priorities: list[str] | None = None,
    statuses: list[str] | None = None,
) -> Path:
    """Create a minimal kanban board and return its directory."""
    prios = priorities if priorities is not None else _STANDARD_PRIORITIES
    stats = statuses if statuses is not None else _STANDARD_STATUSES
    kanban_dir = base / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    prios_yaml = "\n".join(f"  - {p}" for p in prios)
    stats_yaml = "\n".join(f"  - {s}" for s in stats)
    config_text = _CONFIG_TEMPLATE.format(
        priorities_yaml=prios_yaml,
        statuses_yaml=stats_yaml,
    )
    (kanban_dir / "config.yml").write_text(config_text, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_InitDispatchValidation
# ---------------------------------------------------------------------------


class TestFromAC_InitDispatchValidation:
    """Covers AC1 and AC2 — startup validation of dispatch constants."""

    # -- AC1: priority validation -------------------------------------------

    def test_unknown_priority_raises_with_correct_code(self, tmp_path: Path) -> None:
        """Unknown priority in config → ConfigError code ERR_DISPATCH_PRIORITY_MISMATCH."""
        kanban_dir = _make_board(
            tmp_path, priorities=[*_STANDARD_PRIORITIES, "galaxy-brain"]
        )
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir, activity_log=False)
        assert exc_info.value.code == "ERR_DISPATCH_PRIORITY_MISMATCH"

    def test_priority_error_message_lists_unranked_values(self, tmp_path: Path) -> None:
        """Error message for priority mismatch must include the unranked value name."""
        kanban_dir = _make_board(
            tmp_path, priorities=[*_STANDARD_PRIORITIES, "ultra-critical"]
        )
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir, activity_log=False)
        assert "ultra-critical" in exc_info.value.user_message

    def test_multiple_unknown_priorities_all_in_message(self, tmp_path: Path) -> None:
        """All unranked priority values appear in the error message (boundary: plural)."""
        kanban_dir = _make_board(
            tmp_path, priorities=[*_STANDARD_PRIORITIES, "alpha-tier", "omega-tier"]
        )
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir, activity_log=False)
        assert exc_info.value.code == "ERR_DISPATCH_PRIORITY_MISMATCH"
        assert "alpha-tier" in exc_info.value.user_message
        assert "omega-tier" in exc_info.value.user_message

    # -- AC2: status validation ---------------------------------------------

    def test_unknown_status_raises_with_correct_code(self, tmp_path: Path) -> None:
        """Unknown status in config → ConfigError code ERR_DISPATCH_STATUS_MISMATCH.

        'waiting' is inserted in the middle so 'done' remains the last element
        (satisfying the existing terminal_status == statuses[-1] constraint).
        """
        kanban_dir = _make_board(tmp_path, statuses=_STATUSES_WITH_WAITING)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir, activity_log=False)
        assert exc_info.value.code == "ERR_DISPATCH_STATUS_MISMATCH"

    def test_status_error_message_lists_unranked_values(self, tmp_path: Path) -> None:
        """Error message for status mismatch must include the unranked value name."""
        kanban_dir = _make_board(tmp_path, statuses=_STATUSES_WITH_WAITING)
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir, activity_log=False)
        assert "waiting" in exc_info.value.user_message

    def test_multiple_unknown_statuses_all_in_message(self, tmp_path: Path) -> None:
        """All unranked status values appear in the error message (boundary: plural)."""
        kanban_dir = _make_board(
            tmp_path, statuses=_STATUSES_WITH_PARKED_AND_SHELVED
        )
        with pytest.raises(ConfigError) as exc_info:
            KanbanEngine(kanban_dir, activity_log=False)
        assert exc_info.value.code == "ERR_DISPATCH_STATUS_MISMATCH"
        assert "parked" in exc_info.value.user_message
        assert "shelved" in exc_info.value.user_message


# ---------------------------------------------------------------------------
# TestFromAC_RefreshConfigValidation
# ---------------------------------------------------------------------------


class TestFromAC_RefreshConfigValidation:
    """Covers AC3 — refresh_config runs the same dispatch-constant validation."""

    def test_refresh_config_raises_on_dispatch_mismatch(self, tmp_path: Path) -> None:
        """Init with valid config; update config.yml to add unknown priority; refresh raises."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)

        # Overwrite config.yml with an unknown priority
        bad_priorities = [*_STANDARD_PRIORITIES, "hypercritical"]
        prios_yaml = "\n".join(f"  - {p}" for p in bad_priorities)
        stats_yaml = "\n".join(f"  - {s}" for s in _STANDARD_STATUSES)
        new_config = _CONFIG_TEMPLATE.format(
            priorities_yaml=prios_yaml,
            statuses_yaml=stats_yaml,
        )
        (kanban_dir / "config.yml").write_text(new_config, encoding="utf-8")

        with pytest.raises(ConfigError) as exc_info:
            engine.refresh_config()
        assert exc_info.value.code in {
            "ERR_DISPATCH_PRIORITY_MISMATCH",
            "ERR_DISPATCH_STATUS_MISMATCH",
        }
