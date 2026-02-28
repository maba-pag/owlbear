"""Tests for owlbear.memory.session — JSONL session persistence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from owlbear.memory.session import SessionStore


def _sample_messages() -> list[ModelMessage]:
    """Two-turn conversation for testing."""
    return [
        ModelRequest(parts=[UserPromptPart(content="Hello")]),
        ModelResponse(parts=[TextPart(content="Hi there!")]),
    ]


# ---------------------------------------------------------------------------
# SessionStore creation
# ---------------------------------------------------------------------------


class TestSessionStoreCreate:
    """SessionStore manages a JSONL file."""

    def test_create_new_session(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        assert store.path.suffix == ".jsonl"

    def test_path_property(self, tmp_path: Path) -> None:
        p = tmp_path / "sess.jsonl"
        store = SessionStore(p)
        assert store.path == p


# ---------------------------------------------------------------------------
# Append + Load round-trip
# ---------------------------------------------------------------------------


class TestSessionStoreRoundTrip:
    """Messages survive a save ↔ load cycle."""

    def test_append_and_load(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        msgs = _sample_messages()
        store.append(msgs[0])
        store.append(msgs[1])
        loaded = store.load()
        assert len(loaded) == 2
        assert isinstance(loaded[0], ModelRequest)
        assert isinstance(loaded[1], ModelResponse)

    def test_load_preserves_content(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.append(ModelRequest(parts=[UserPromptPart(content="ping")]))
        loaded = store.load()
        part = loaded[0].parts[0]  # type: ignore[union-attr]
        assert part.content == "ping"

    def test_load_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "sess.jsonl"
        p.write_text("")
        store = SessionStore(p)
        assert store.load() == []

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "nope.jsonl")
        assert store.load() == []


# ---------------------------------------------------------------------------
# Save (bulk write)
# ---------------------------------------------------------------------------


class TestSessionStoreSave:
    """save() overwrites the entire file with the given messages."""

    def test_save_overwrites(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.append(ModelRequest(parts=[UserPromptPart(content="old")]))
        new_msgs = [ModelRequest(parts=[UserPromptPart(content="new")])]
        store.save(new_msgs)
        loaded = store.load()
        assert len(loaded) == 1
        assert loaded[0].parts[0].content == "new"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# JSONL format verification
# ---------------------------------------------------------------------------


class TestSessionStoreFormat:
    """Each message is a single JSON line."""

    def test_one_line_per_message(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        for msg in _sample_messages():
            store.append(msg)
        lines = store.path.read_text().strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            json.loads(line)  # each line must be valid JSON


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


class TestSessionStoreBackup:
    """backup() copies current JSONL to a .bak file."""

    def test_backup_creates_bak_file(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.append(_sample_messages()[0])
        bak = store.backup()
        assert bak is not None
        assert bak.exists()
        assert bak.suffix == ".bak"

    def test_backup_content_matches(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.append(_sample_messages()[0])
        bak = store.backup()
        assert bak is not None
        assert bak.read_text() == store.path.read_text()

    def test_backup_nonexistent_returns_none(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "nope.jsonl")
        assert store.backup() is None


# ---------------------------------------------------------------------------
# last_consolidated metadata (.meta file)
# ---------------------------------------------------------------------------


class TestSessionStoreLastConsolidated:
    """last_consolidated tracks the consolidation pointer via a .meta file."""

    def test_default_is_none(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        assert store.last_consolidated is None

    def test_setter_and_getter(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.last_consolidated = 42
        assert store.last_consolidated == 42

    def test_save_persists_meta(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.last_consolidated = 10
        store.save(_sample_messages())
        meta_path = tmp_path / "sess.meta"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        assert data["last_consolidated"] == 10

    def test_load_restores_meta(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.last_consolidated = 15
        store.save(_sample_messages())

        store2 = SessionStore(tmp_path / "sess.jsonl")
        store2.load()
        assert store2.last_consolidated == 15

    def test_load_without_meta_file_keeps_none(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.save(_sample_messages())
        # Delete the meta file
        meta_path = tmp_path / "sess.meta"
        if meta_path.exists():
            meta_path.unlink()

        store2 = SessionStore(tmp_path / "sess.jsonl")
        store2.load()
        assert store2.last_consolidated is None

    def test_save_none_meta(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "sess.jsonl")
        store.last_consolidated = None
        store.save(_sample_messages())
        meta_path = tmp_path / "sess.meta"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        assert data["last_consolidated"] is None
