"""GREEN tests for actor field addition to activity log (#812).

AC coverage:
  AC1 - log_activity() gains actor parameter (default: "engine")
  AC2 - All engine call sites pass actor param
  AC3 - New JSONL entries include "actor" field
  AC4 - Old entries without actor remain readable (backward compatible — no migration)

All tests pass GREEN against the 5-param log_activity() implemented in task #812.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.activity_log import log_activity

# ---------------------------------------------------------------------------
# Config + fixtures
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
    """Minimal kanban directory with config.yml and tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine wired to temp kanban_dir with fixed agent_name."""
    return KanbanEngine(kanban_dir, agent_name="test-agent", activity_log=True)


def _read_entries(log_path: Path) -> list[dict]:
    """Parse a JSONL file into a list of dicts. Returns [] if missing."""
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _activity_log(kanban_dir: Path) -> Path:
    """Return path to activity.jsonl in a kanban_dir."""
    return kanban_dir / "activity.jsonl"


def _reset_log(kanban_dir: Path) -> None:
    """Remove activity.jsonl so subsequent assertions start with a clean slate."""
    (kanban_dir / "activity.jsonl").unlink(missing_ok=True)


# ===========================================================================
# TestFromAC_LogActivityActorParam — AC1: log_activity() signature
# ===========================================================================


class TestFromAC_LogActivityActorParam:
    """Tests for AC1: log_activity() accepts actor kwarg with default 'engine'."""

    def test_log_activity_accepts_actor_keyword_arg(self, tmp_path: Path) -> None:
        """log_activity() accepts actor= keyword without raising TypeError."""
        log_path = tmp_path / "activity.jsonl"
        # Must not raise TypeError: unexpected keyword argument 'actor'
        log_activity(log_path, "create", 1, "test", actor="bot")

    def test_log_activity_default_actor_is_engine(self, tmp_path: Path) -> None:
        """Calling log_activity() without actor= writes 'engine' as actor value."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "test")
        entry = _read_entries(log_path)[0]
        assert entry.get("actor") == "engine"

    def test_log_activity_explicit_actor_stored_verbatim(self, tmp_path: Path) -> None:
        """Explicit actor value is stored verbatim in the JSONL entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "test", actor="my-agent")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == "my-agent"

    def test_log_activity_actor_empty_string_accepted(self, tmp_path: Path) -> None:
        """actor='' is accepted as a valid value and stored in the entry."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "edit", 5, "detail", actor="")
        entry = _read_entries(log_path)[0]
        assert entry["actor"] == ""

    def test_log_activity_actor_arbitrary_string_round_trips(
        self, tmp_path: Path
    ) -> None:
        """Multiple actor values round-trip through JSONL correctly."""
        log_path = tmp_path / "activity.jsonl"
        actors = ["user", "mcp", "test-agent", "orchestrator"]
        for actor_val in actors:
            log_activity(log_path, "create", 1, "detail", actor=actor_val)
        entries = _read_entries(log_path)
        stored = [e["actor"] for e in entries]
        assert stored == actors


# ===========================================================================
# TestFromAC_EntryIncludesActorField — AC3: JSONL entries have "actor" key
# ===========================================================================


class TestFromAC_EntryIncludesActorField:
    """Tests for AC3: new JSONL entries include 'actor' field."""

    def test_entry_has_actor_key(self, tmp_path: Path) -> None:
        """JSONL entry written by log_activity() includes 'actor' key."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail")
        entry = _read_entries(log_path)[0]
        assert "actor" in entry

    def test_entry_has_exactly_five_keys(self, tmp_path: Path) -> None:
        """Log entry contains exactly: timestamp, action, task_id, detail, actor."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail")
        entry = _read_entries(log_path)[0]
        assert set(entry.keys()) == {"timestamp", "action", "task_id", "detail", "actor"}

    def test_actor_field_is_string_type(self, tmp_path: Path) -> None:
        """actor field value in the JSONL entry is a str."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "create", 1, "detail")
        entry = _read_entries(log_path)[0]
        assert isinstance(entry["actor"], str)

    def test_entry_still_valid_json_with_actor(self, tmp_path: Path) -> None:
        """The JSONL line written with actor field is still valid parseable JSON."""
        log_path = tmp_path / "activity.jsonl"
        log_activity(log_path, "move", 7, "todo -> in-progress", actor="agent")
        line = log_path.read_text(encoding="utf-8").strip()
        parsed = json.loads(line)  # must not raise
        assert "actor" in parsed


# ===========================================================================
# TestFromAC_EngineCallSitesPassActor — AC2: engine wiring covers all 7 verbs
# ===========================================================================


class TestFromAC_EngineCallSitesPassActor:
    """Tests for AC2: every engine operation produces a JSONL entry with 'actor' field.

    Indirectly verifies all 7 call sites in engine.py pass actor to log_activity().
    """

    def test_create_task_entry_has_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """create_task produces a JSONL entry with 'actor' field."""
        engine.create_task("Actor Test Task")
        entries = _read_entries(_activity_log(kanban_dir))
        create_entries = [e for e in entries if e["action"] == "create"]
        assert len(create_entries) == 1
        assert create_entries[0]["actor"] == "test-agent"

    def test_edit_task_entry_has_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """edit_task produces a JSONL entry with 'actor' field."""
        record = engine.create_task("Edit Me")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), title="Edited Title")
        entries = _read_entries(_activity_log(kanban_dir))
        edit_entries = [e for e in entries if e["action"] == "edit"]
        assert len(edit_entries) == 1
        assert edit_entries[0]["actor"] == "test-agent"

    def test_move_task_entry_has_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """move_task produces a JSONL entry with 'actor' field."""
        record = engine.create_task("Move Me")
        _reset_log(kanban_dir)
        engine.move_task(str(record.id), "backlog")
        entries = _read_entries(_activity_log(kanban_dir))
        move_entries = [e for e in entries if e["action"] == "move"]
        assert len(move_entries) == 1
        assert move_entries[0]["actor"] == "test-agent"

    def test_claim_task_entry_has_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """claim_task produces a JSONL entry with 'actor' field."""
        record = engine.create_task("Claim Me")
        engine.move_task(str(record.id), "todo")
        _reset_log(kanban_dir)
        engine.claim_task(str(record.id))
        entries = _read_entries(_activity_log(kanban_dir))
        claim_entries = [e for e in entries if e["action"] == "claim"]
        assert len(claim_entries) == 1
        assert claim_entries[0]["actor"] == "test-agent"

    def test_release_task_entry_has_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """release_task produces a JSONL entry with 'actor' field."""
        record = engine.create_task("Release Me")
        engine.move_task(str(record.id), "todo")
        engine.claim_task(str(record.id))
        _reset_log(kanban_dir)
        engine.release_task(str(record.id))
        entries = _read_entries(_activity_log(kanban_dir))
        release_entries = [e for e in entries if e["action"] == "release"]
        assert len(release_entries) == 1
        assert release_entries[0]["actor"] == "test-agent"

    def test_block_task_entry_has_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """block transition via edit_task produces a JSONL entry with 'actor' field."""
        record = engine.create_task("Block Me")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=True, block_reason="waiting for dep")
        entries = _read_entries(_activity_log(kanban_dir))
        block_entries = [e for e in entries if e["action"] == "block"]
        assert len(block_entries) == 1
        assert block_entries[0]["actor"] == "test-agent"

    def test_unblock_task_entry_has_actor(
        self, engine: KanbanEngine, kanban_dir: Path
    ) -> None:
        """unblock transition via edit_task produces a JSONL entry with 'actor' field."""
        record = engine.create_task("Unblock Me")
        engine.edit_task(str(record.id), blocked=True, block_reason="dep")
        _reset_log(kanban_dir)
        engine.edit_task(str(record.id), blocked=False)
        entries = _read_entries(_activity_log(kanban_dir))
        unblock_entries = [e for e in entries if e["action"] == "unblock"]
        assert len(unblock_entries) == 1
        assert unblock_entries[0]["actor"] == "test-agent"


# ===========================================================================
# TestFromAC_BackwardCompatibility — AC4: legacy entries coexist with new ones
# ===========================================================================


class TestFromAC_BackwardCompatibility:
    """Tests for AC4: JSONL files mixing old (4-key) and new (5-key) entries stay valid."""

    def test_new_entry_appended_to_legacy_file_has_actor(
        self, tmp_path: Path
    ) -> None:
        """When log_activity() appends to a legacy file, the new entry has 'actor'."""
        log_path = tmp_path / "activity.jsonl"
        old_entry = json.dumps({
            "timestamp": "2026-01-01T00:00:00+00:00",
            "action": "create",
            "task_id": 1,
            "detail": "legacy entry",
        })
        log_path.write_text(old_entry + "\n", encoding="utf-8")
        # Append a new entry without explicit actor (uses default)
        log_activity(log_path, "edit", 1, "new entry")
        entries = _read_entries(log_path)
        assert len(entries) == 2
        # New entry must carry the actor field
        assert "actor" in entries[1]

    def test_old_entry_unmodified_after_new_append(self, tmp_path: Path) -> None:
        """The legacy entry's keys are unchanged after a new entry is appended."""
        log_path = tmp_path / "activity.jsonl"
        old_payload = {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "action": "create",
            "task_id": 1,
            "detail": "legacy entry",
        }
        log_path.write_text(json.dumps(old_payload) + "\n", encoding="utf-8")
        log_activity(log_path, "edit", 1, "new entry")
        entries = _read_entries(log_path)
        # Old entry must NOT have actor added retrospectively
        assert set(entries[0].keys()) == {"timestamp", "action", "task_id", "detail"}
        # New entry must have actor
        assert "actor" in entries[1]

    def test_mixed_file_with_explicit_actor_appended(self, tmp_path: Path) -> None:
        """Old entries plus a new entry with explicit actor= all parse correctly."""
        log_path = tmp_path / "activity.jsonl"
        old_lines = "\n".join(
            json.dumps({
                "timestamp": "2026-01-01T00:00:00+00:00",
                "action": "create",
                "task_id": i,
                "detail": "old",
            })
            for i in range(3)
        )
        log_path.write_text(old_lines + "\n", encoding="utf-8")
        # Append a new entry with explicit actor — raises TypeError currently
        log_activity(log_path, "edit", 1, "new entry", actor="test-agent")
        entries = _read_entries(log_path)
        assert len(entries) == 4
        assert entries[3]["actor"] == "test-agent"
