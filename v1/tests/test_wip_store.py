"""Tests for owlbear.memory.wip — WipStore append-only JSONL for WIP summaries."""

from __future__ import annotations

import json
from pathlib import Path

from owlbear.memory.wip import WipEntry, WipStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(tmp_path: Path) -> WipStore:
    """Create a WipStore pointing at a temp workspace."""
    return WipStore(workspace=tmp_path)


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundtrip:
    """save() then load() returns the saved summary."""

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save(agent="builder", task_id="42", summary="Implemented feature X")
        result = store.load(agent="builder", task_id="42")
        assert result == "Implemented feature X"


# ---------------------------------------------------------------------------
# Load empty
# ---------------------------------------------------------------------------


class TestLoadEmpty:
    """load() on nonexistent file returns None."""

    def test_load_empty_returns_none(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        result = store.load(agent="builder", task_id="999")
        assert result is None


# ---------------------------------------------------------------------------
# Multiple saves
# ---------------------------------------------------------------------------


class TestMultipleSaves:
    """save() three times — load() returns the latest summary."""

    def test_multiple_saves_returns_latest(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save(agent="builder", task_id="10", summary="first")
        store.save(agent="builder", task_id="10", summary="second")
        store.save(agent="builder", task_id="10", summary="third")
        result = store.load(agent="builder", task_id="10")
        assert result == "third"


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------


class TestClear:
    """clear() deletes the file; load() returns None afterward."""

    def test_clear_deletes_file(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save(agent="reviewer", task_id="7", summary="Review notes")
        path = tmp_path / ".owlbear" / "wip" / "reviewer_7.jsonl"
        assert path.exists()
        store.clear(agent="reviewer", task_id="7")
        assert not path.exists()
        assert store.load(agent="reviewer", task_id="7") is None


# ---------------------------------------------------------------------------
# File path structure
# ---------------------------------------------------------------------------


class TestFilePathStructure:
    """Saved file lives at {workspace}/.owlbear/wip/{agent}_{task_id}.jsonl."""

    def test_file_path_structure(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save(agent="builder", task_id="55", summary="checkpoint")
        expected = tmp_path / ".owlbear" / "wip" / "builder_55.jsonl"
        assert expected.exists()


# ---------------------------------------------------------------------------
# Entry model fields
# ---------------------------------------------------------------------------


class TestEntryModelFields:
    """WipEntry has timestamp, agent, task_id, summary — all str."""

    def test_entry_model_fields(self) -> None:
        entry = WipEntry(
            timestamp="2026-03-07T12:00:00Z",
            agent="builder",
            task_id="42",
            summary="test summary",
        )
        assert entry.timestamp == "2026-03-07T12:00:00Z"
        assert entry.agent == "builder"
        assert entry.task_id == "42"
        assert entry.summary == "test summary"


# ---------------------------------------------------------------------------
# Append-only JSONL
# ---------------------------------------------------------------------------


class TestAppendOnlyJsonl:
    """save() three times — file has exactly 3 non-empty lines, each valid JSON."""

    def test_append_only_jsonl(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.save(agent="builder", task_id="20", summary="one")
        store.save(agent="builder", task_id="20", summary="two")
        store.save(agent="builder", task_id="20", summary="three")
        path = tmp_path / ".owlbear" / "wip" / "builder_20.jsonl"
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 3
        for line in lines:
            data = json.loads(line)
            assert "agent" in data
            assert "task_id" in data
            assert "summary" in data
            assert "timestamp" in data
