"""Failing tests for actor field in activity log (#811, RED phase).

AC coverage:
  AC1 - new JSONL entries include "actor" field
  AC2 - old entries without actor load without error (backward compat)
  AC3 - default actor is "engine" when not specified
  AC4 - actor field appears in all action types (create, edit, move, claim,
        release, block, unblock — all 7 engine call sites per arch review)
  AC5 - tests fail RED before implementation (#812 is GREEN pair)

All tests must FAIL at this stage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.activity_log import log_activity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_entries(log_path: Path) -> list[dict]:
    """Parse a JSONL file into a list of dicts. Returns [] if file is missing."""
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _reset_log(kanban_dir: Path) -> None:
    """Remove activity.jsonl to start each sub-operation with a clean slate."""
    (kanban_dir / "activity.jsonl").unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Fixtures (mirrored from test_kanban_engine_activity_wiring_728.py)
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
next_id: 100
"""


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine wired to temp kanban_dir with fixed agent_name."""
    return KanbanEngine(kanban_dir, agent_name="test-agent", activity_log=True)


# ===========================================================================
# TestFromAC_ActorFieldPresent — AC1: new entries include "actor" field
# ===========================================================================


class TestFromAC_ActorFieldPresent:
    """Tests for AC1: log_activity writes an 'actor' field in every new JSONL entry."""

    def test_actor_field_present_in_new_entry(self, tmp_path: Path) -> None:
        """log_activity writes an 'actor' key in the JSONL entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "new task", actor="engine")
        entry = _read_entries(log_path)[0]
        assert "actor" in entry

    def test_actor_field_value_matches_kwarg(self, tmp_path: Path) -> None:
        """actor field value matches the actor kwarg passed to log_activity."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "edit", 5, "changed title", actor="builder")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == "builder"

    def test_actor_field_is_string_type(self, tmp_path: Path) -> None:
        """actor field is stored as a string."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail", actor="engine")
        entry = _read_entries(log_path)[0]
        assert isinstance(entry["actor"], str)

    def test_actor_field_non_empty_when_provided(self, tmp_path: Path) -> None:
        """actor field is a non-empty string when explicitly provided."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail", actor="planner")
        entry = _read_entries(log_path)[0]
        assert len(entry["actor"]) > 0

    def test_existing_fields_still_present_alongside_actor(
        self, tmp_path: Path
    ) -> None:
        """Adding actor does not drop timestamp, action, task_id, or detail."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 7, "task title", actor="engine")
        entry = _read_entries(log_path)[0]
        assert {"timestamp", "action", "task_id", "detail", "actor"} <= set(
            entry.keys()
        )


# ===========================================================================
# TestFromAC_BackwardCompat — AC2: old entries without actor load without error
# ===========================================================================


class TestFromAC_BackwardCompat:
    """Tests for AC2: legacy JSONL entries (no actor field) load without errors.

    Each test also calls log_activity with the new actor kwarg so it fails RED
    (TypeError) and validates the coexistence of old and new entries.
    """

    def test_old_and_new_entries_coexist_in_same_log(self, tmp_path: Path) -> None:
        """Old-format entry followed by new actor-carrying entry both parse OK."""
        log_path = tmp_path / "activity.jsonl"
        old_entry = json.dumps({
            "timestamp": "2025-01-01T00:00:00+00:00",
            "action": "create",
            "task_id": 1,
            "detail": "pre-actor entry",
        })
        log_path.write_text(old_entry + "\n", encoding="utf-8")
        # Append new entry — fails RED because log_activity lacks actor kwarg
        log_activity(log_path, "edit", 2, "post-actor entry", actor="engine")
        entries = _read_entries(log_path)
        assert len(entries) == 2

    def test_old_entry_actor_key_absent_not_key_error(self, tmp_path: Path) -> None:
        """Old entry has no actor key while new entry has one — both parse fine."""
        log_path = tmp_path / "activity.jsonl"
        old_entry = json.dumps({
            "timestamp": "2025-06-01T12:00:00+00:00",
            "action": "move",
            "task_id": 10,
            "detail": "todo -> in-progress",
        })
        log_path.write_text(old_entry + "\n", encoding="utf-8")
        # Append new entry — fails RED: TypeError
        log_activity(log_path, "create", 11, "new entry", actor="orchestrator")
        entries = _read_entries(log_path)
        assert "actor" not in entries[0]   # old entry: no actor
        assert "actor" in entries[1]       # new entry: actor present

    def test_bulk_legacy_entries_followed_by_new_entry(self, tmp_path: Path) -> None:
        """Many old-format entries followed by one new-format entry all load fine."""
        log_path = tmp_path / "activity.jsonl"
        lines = [
            json.dumps({
                "timestamp": "2025-01-01T00:00:00+00:00",
                "action": "edit",
                "task_id": i,
                "detail": f"legacy detail {i}",
            })
            for i in range(5)
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Append new entry — fails RED: TypeError
        log_activity(log_path, "create", 99, "brand new", actor="engine")
        entries = _read_entries(log_path)
        assert len(entries) == 6
        for legacy in entries[:5]:
            assert "actor" not in legacy

    def test_legacy_entry_actor_get_returns_none(self, tmp_path: Path) -> None:
        """Old entries where actor is absent: .get('actor') returns None gracefully."""
        log_path = tmp_path / "activity.jsonl"
        old_entry = json.dumps({
            "timestamp": "2024-12-31T00:00:00+00:00",
            "action": "claim",
            "task_id": 42,
            "detail": "test-agent",
        })
        log_path.write_text(old_entry + "\n", encoding="utf-8")
        # Append new entry — fails RED: TypeError
        log_activity(log_path, "release", 42, "test-agent", actor="engine")
        entries = _read_entries(log_path)
        # Old entry: actor absent — .get() must not raise
        assert entries[0].get("actor") is None
        # New entry: actor present
        assert entries[1].get("actor") == "engine"


# ===========================================================================
# TestFromAC_DefaultActorEngine — AC3: default actor is "engine"
# ===========================================================================


class TestFromAC_DefaultActorEngine:
    """Tests for AC3: omitting the actor kwarg produces actor='engine' in entry."""

    def test_default_actor_is_engine_when_kwarg_omitted(
        self, tmp_path: Path
    ) -> None:
        """Calling log_activity without actor kwarg produces actor='engine'."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "no actor kwarg")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == "engine"

    def test_default_actor_exact_string_engine(self, tmp_path: Path) -> None:
        """Default actor is exactly 'engine' — not 'Engine', 'AGENT', or None."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "edit", 5, "some change")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == "engine"

    def test_default_actor_is_not_none(self, tmp_path: Path) -> None:
        """Default actor value is the string 'engine', not None."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "move", 3, "todo -> in-progress")
        entry = _read_entries(log_path)[0]
        assert entry.get("actor") is not None
        assert entry["actor"] == "engine"

    def test_explicit_actor_kwarg_overrides_default(self, tmp_path: Path) -> None:
        """Passing actor='planner' stores 'planner', not 'engine'."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "explicit actor", actor="planner")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == "planner"

    @pytest.mark.parametrize(
        "verb",
        ["create", "edit", "move", "claim", "release", "block", "unblock"],
    )
    def test_default_actor_engine_for_all_verbs(
        self, tmp_path: Path, verb: str
    ) -> None:
        """Default actor='engine' applies regardless of action verb."""
        log_path = tmp_path / f"activity_{verb}.jsonl"
        log_activity(log_path, verb, 10, f"{verb} detail")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == "engine"


# ===========================================================================
# TestFromAC_ActorInAllActionTypes — AC4: actor in all 7 action types
# ===========================================================================


class TestFromAC_ActorInAllActionTypes:
    """Tests for AC4: actor field present for all 7 action types.

    Covers both direct log_activity() calls (unit) and KanbanEngine calls
    (integration) to verify wiring at the engine layer.
    """

    # --- Unit-level: log_activity() with explicit actor kwarg ---

    @pytest.mark.parametrize(
        "verb",
        ["create", "edit", "move", "claim", "release", "block", "unblock"],
    )
    def test_actor_field_present_for_verb(
        self, tmp_path: Path, verb: str
    ) -> None:
        """Actor field present in log entry for every supported action verb."""
        log_path = tmp_path / f"activity_{verb}.jsonl"
        log_activity(log_path, verb, 10, f"{verb} detail", actor="engine")
        entry = _read_entries(log_path)[0]
        assert "actor" in entry

    @pytest.mark.parametrize(
        "verb",
        ["create", "edit", "move", "claim", "release", "block", "unblock"],
    )
    def test_actor_value_correct_for_verb(
        self, tmp_path: Path, verb: str
    ) -> None:
        """Actor value matches kwarg for every supported action verb."""
        log_path = tmp_path / f"activity_{verb}.jsonl"
        log_activity(log_path, verb, 10, f"{verb} detail", actor="test-agent")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == "test-agent"

    # --- Integration-level: KanbanEngine wiring ---

    def test_engine_create_logs_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """KanbanEngine.create_task produces a log entry with actor field."""
        engine.create_task(title="Actor test task")
        log_path = kanban_dir / "activity.jsonl"
        entries = _read_entries(log_path)
        create_entries = [e for e in entries if e["action"] == "create"]
        assert len(create_entries) >= 1
        assert "actor" in create_entries[0]

    def test_engine_edit_logs_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """KanbanEngine.edit_task produces a log entry with actor field."""
        task = engine.create_task(title="Task to edit")
        _reset_log(kanban_dir)
        engine.edit_task(str(task.id), title="Edited title")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        edit_entries = [e for e in entries if e["action"] == "edit"]
        assert len(edit_entries) >= 1
        assert "actor" in edit_entries[0]

    def test_engine_move_logs_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """KanbanEngine.move_task produces a log entry with actor field."""
        task = engine.create_task(title="Task to move")
        _reset_log(kanban_dir)
        engine.move_task(str(task.id), "backlog")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        move_entries = [e for e in entries if e["action"] == "move"]
        assert len(move_entries) >= 1
        assert "actor" in move_entries[0]

    def test_engine_claim_logs_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """KanbanEngine.claim_task produces a log entry with actor field."""
        task = engine.create_task(title="Task to claim")
        _reset_log(kanban_dir)
        engine.claim_task(str(task.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        claim_entries = [e for e in entries if e["action"] == "claim"]
        assert len(claim_entries) >= 1
        assert "actor" in claim_entries[0]

    def test_engine_release_logs_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """KanbanEngine.release_task produces a log entry with actor field."""
        task = engine.create_task(title="Task to release")
        engine.claim_task(str(task.id))
        _reset_log(kanban_dir)
        engine.release_task(str(task.id))
        entries = _read_entries(kanban_dir / "activity.jsonl")
        release_entries = [e for e in entries if e["action"] == "release"]
        assert len(release_entries) >= 1
        assert "actor" in release_entries[0]

    def test_engine_block_logs_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """KanbanEngine.edit_task(blocked=True) produces a log entry with actor field."""
        task = engine.create_task(title="Task to block")
        _reset_log(kanban_dir)
        engine.edit_task(str(task.id), blocked=True, block_reason="waiting for #999")
        entries = _read_entries(kanban_dir / "activity.jsonl")
        block_entries = [e for e in entries if e["action"] == "block"]
        assert len(block_entries) >= 1
        assert "actor" in block_entries[0]

    def test_engine_unblock_logs_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """KanbanEngine.edit_task(blocked=False) from blocked state logs actor."""
        task = engine.create_task(title="Task to unblock")
        engine.edit_task(str(task.id), blocked=True, block_reason="blocked")
        _reset_log(kanban_dir)
        engine.edit_task(str(task.id), blocked=False)
        entries = _read_entries(kanban_dir / "activity.jsonl")
        unblock_entries = [e for e in entries if e["action"] == "unblock"]
        assert len(unblock_entries) >= 1
        assert "actor" in unblock_entries[0]
