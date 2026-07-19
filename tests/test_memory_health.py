from __future__ import annotations

from pathlib import Path

from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage

_DUPLICATE_ID = "550e8400-e29b-41d4-a716-446655440001"
_STATES = tuple(MemoryState)
_TIMESTAMP = "2026-07-17T10:00:00+00:00"


def _entry(entry_id: str, state: MemoryState, updated_at: str = _TIMESTAMP) -> MemoryEntry:
    return MemoryEntry(
        id=entry_id,
        title=f"Entry {state}",
        content="Health check content",
        categories=["domain-knowledge"],
        confidence=0.9,
        state=state,
        source_agent="test-agent",
        created_at=_TIMESTAMP,
        updated_at=updated_at,
    )


def test_health_reports_corruption_duplicates_and_preserves_loading(tmp_path: Path) -> None:
    malformed_path = tmp_path / "malformed.md"
    malformed_path.write_text("not markdown", encoding="utf-8")
    duplicate_paths = [tmp_path / f"duplicate-{index}.md" for index in range(3)]
    for index, path in enumerate(duplicate_paths):
        storage.write_entry(
            path,
            _entry(_DUPLICATE_ID, MemoryState.PENDING, f"2026-07-17T10:0{index}:00+00:00"),
            memory_dir=tmp_path,
        )

    engine = MemoryEngine(tmp_path)
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in tmp_path.iterdir()}

    health = engine.health()

    after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in tmp_path.iterdir()}
    assert health.healthy is False
    assert health.unreadable_paths == [malformed_path.name]
    assert health.duplicate_paths == {_DUPLICATE_ID: [path.name for path in sorted(duplicate_paths)]}
    assert before == after
    assert engine.parse_errors == 0

    loaded = engine.load()
    assert len(loaded) == 1
    assert loaded[0].updated_at == "2026-07-17T10:02:00+00:00"


def test_health_accepts_every_memory_state(tmp_path: Path) -> None:
    for index, state in enumerate(_STATES):
        entry_id = f"550e8400-e29b-41d4-a716-44665544{index + 10:04d}"
        storage.write_entry(
            tmp_path / f"{state}.md",
            _entry(entry_id, state),
            memory_dir=tmp_path,
        )

    health = MemoryEngine(tmp_path).health()

    assert health.healthy is True
    assert health.unreadable_paths == []
    assert health.duplicate_paths == {}
