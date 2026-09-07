"""Protect canonical MemoryEngine malformed-file accounting."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from owlbear_memory import LifecycleRecoveryError, MemoryEngine, storage
from owlbear_memory.models import MemoryEntry

_VALID_ID = "550e8400-e29b-41d4-a716-446655440000"


def _valid_entry_data() -> dict:
    return {
        "id": _VALID_ID,
        "title": "Test Entry",
        "content": "Some content",
        "categories": ["domain-knowledge"],
        "confidence": 0.9,
        "state": "pending",
        "scope_agents": [],
        "source_agent": "test-agent",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "approved_at": None,
    }


def test_load_counts_malformed_files_without_raising(tmp_path: Path) -> None:
    """Canonical loading skips malformed files and reports their count."""
    (tmp_path / "bad-yaml.md").write_text(
        "---\nkey: {unclosed bracket\n---\n\nsome body\n",
        encoding="utf-8",
    )
    (tmp_path / "missing-fields.md").write_text(
        "---\ntitle: Some Title\n---\n\nsome body\n",
        encoding="utf-8",
    )

    engine = MemoryEngine(tmp_path)

    assert engine.load() == []
    assert engine.parse_errors == 2


@pytest.mark.parametrize(
    ("title", "content", "source_agent"),
    [
        ("x" * 7819, "Some content", "test-agent"),
        ("é" * 3909 + "x", "Some content", "test-agent"),
        ("x" * 3735, "😀" * 1024, "test-agent"),
        ("Test Entry", "Some content", "é" * 3909 + "x"),
    ],
    ids=["ascii-title", "multibyte-title", "multibyte-content", "multibyte-metadata"],
)
def test_fresh_engine_reads_each_successful_boundary_write(
    tmp_path: Path,
    title: str,
    content: str,
    source_agent: str,
) -> None:
    """Successful boundary writes remain readable by a fresh MemoryEngine."""
    entry = MemoryEntry(
        **{
            **_valid_entry_data(),
            "title": title,
            "content": content,
            "source_agent": source_agent,
        }
    )
    target = tmp_path / "boundary.md"
    storage.write_entry(target, entry, memory_dir=tmp_path)

    fresh_engine = MemoryEngine(tmp_path)

    entries = fresh_engine.load()
    assert entries == [entry]
    assert fresh_engine.parse_errors == 0


def test_rejected_engine_edit_preserves_previous_file(tmp_path: Path) -> None:
    """An oversized edit fails before replacement and leaves the prior entry readable."""
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Original title",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    target = tmp_path / f"{entry.id}.md"
    original_bytes = target.read_bytes()

    with pytest.raises(ValueError, match=r"serialized entry exceeds 8192 bytes \(got \d+\)"):
        engine.edit(
            entry.id,
            {"title": "x" * 9000},
            expected_updated_at=entry.updated_at,
        )

    assert target.read_bytes() == original_bytes
    fresh_engine = MemoryEngine(tmp_path)
    loaded = fresh_engine.get_entry(entry.id)
    assert loaded.title == "Original title"
    assert fresh_engine.parse_errors == 0


def test_lifecycle_rollback_failure_preserves_both_errors_and_reloads_cache(tmp_path: Path) -> None:
    """A partial lifecycle recovery reports both failures and reflects disk state."""
    engine = MemoryEngine(tmp_path)
    engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    rollback_error = OSError("rollback write failed")
    calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise initial_error
        if calls == 3:
            raise rollback_error
        original_write(*args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "partial"
    assert error.operation_error is initial_error
    assert len(error.rollback_errors) == 1
    assert error.rollback_errors[0].error is rollback_error
    assert error.rollback_errors[0].entry_id in str(error)
    assert str(error.rollback_errors[0].path) in str(error)
    assert error.cache_error is None
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",), ("new",)}
    health = engine.health()
    assert health.healthy is True
    assert health.unreadable_paths == []
    assert health.duplicate_paths == {}


def test_lifecycle_recovery_status_uses_reloaded_originals(tmp_path: Path) -> None:
    """A rollback error does not imply partial disk state when reload finds originals."""
    engine = MemoryEngine(tmp_path)
    for title in ("First", "Second"):
        engine.save(
            title=title,
            content=f"Original {title.lower()}",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="source",
            scope_agents=["old"],
        )

    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    rollback_error = OSError("rollback write failed")
    calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise initial_error
        if calls == 2:
            raise rollback_error
        original_write(*args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "complete"
    assert error.operation_error is initial_error
    assert len(error.rollback_errors) == 1
    assert error.rollback_errors[0].error is rollback_error
    assert error.cache_error is None
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",)}
    assert engine.health().healthy is True


def test_lifecycle_recovery_status_uses_partial_reload_when_all_rollbacks_fail(tmp_path: Path) -> None:
    """A successful reload identifies partial disk state even when no rollback call succeeds."""
    engine = MemoryEngine(tmp_path)
    for title in ("First", "Second"):
        engine.save(
            title=title,
            content=f"Original {title.lower()}",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="source",
            scope_agents=["old"],
        )

    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    rollback_errors = (OSError("first rollback failed"), OSError("second rollback failed"))
    calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise initial_error
        if calls in (3, 4):
            raise rollback_errors[calls - 3]
        original_write(*args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "partial"
    assert error.operation_error is initial_error
    assert tuple(failure.error for failure in error.rollback_errors) == rollback_errors
    assert error.cache_error is None
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",), ("new",)}
    assert engine.health().healthy is True


def test_lifecycle_cache_reload_failure_resets_cache_until_subsequent_reload(tmp_path: Path) -> None:
    """A failed recovery reload clears the cache and permits a later reload from disk."""
    engine = MemoryEngine(tmp_path)
    engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.get_entries()

    original_write = storage.write_entry
    original_load = engine._load  # noqa: SLF001
    initial_error = OSError("initial write failed")
    reload_error = OSError("cache reload failed")
    calls = 0
    load_calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise initial_error
        original_write(*args, **kwargs)

    def failing_load() -> list[MemoryEntry]:
        nonlocal load_calls
        load_calls += 1
        if load_calls in (1, 2):
            raise reload_error
        return original_load()

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        patch.object(engine, "_load", side_effect=failing_load),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "uncertain"
    assert error.operation_error is initial_error
    assert error.rollback_errors == ()
    assert error.cache_error is reload_error
    assert engine._entries == []  # noqa: SLF001
    assert engine._id_to_path == {}  # noqa: SLF001
    health = engine.health()
    assert health.healthy is True
    assert health.unreadable_paths == []
    assert health.duplicate_paths == {}

    with (
        patch.object(engine, "_load", side_effect=failing_load),
        pytest.raises(
            OSError,
            match="cache reload failed",
        ) as second_reload,
    ):
        engine.get_entries()
    assert second_reload.value is reload_error

    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",)}
    assert load_calls == 2
    assert engine.parse_errors == 0


def test_lifecycle_operation_failure_with_successful_rollback_reraises_original_error(tmp_path: Path) -> None:
    """A fully successful rollback preserves the ordinary operation exception."""
    engine = MemoryEngine(tmp_path)
    engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )

    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise initial_error
        original_write(*args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(OSError, match="initial write failed") as exc_info,
    ):
        engine.rename_agent("old", "new")

    assert exc_info.value is initial_error
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",)}
    assert engine.health().healthy is True


def test_delete_lifecycle_rollback_failure_restores_only_recoverable_files(tmp_path: Path) -> None:
    """A failed delete rollback reports the missing entry and reloads the remaining files."""
    engine = MemoryEngine(tmp_path)
    first = engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    second = engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.get_entries()

    first_path = tmp_path / f"{first.id}.md"
    second_path = tmp_path / f"{second.id}.md"
    original_delete = storage.delete_entry
    original_write = storage.write_entry
    initial_error = OSError("delete failed")
    rollback_error = OSError("rollback write failed")
    delete_calls = 0

    def failing_delete(path: Path, *, memory_dir: Path) -> None:
        nonlocal delete_calls
        delete_calls += 1
        original_delete(path, memory_dir=memory_dir)
        if delete_calls == 2:
            raise initial_error

    def failing_write(path: Path, *args: object, **kwargs: object) -> None:
        if path == second_path:
            raise rollback_error
        original_write(path, *args, **kwargs)

    with (
        patch.object(storage, "delete_entry", side_effect=failing_delete),
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.delete_agent("old")

    error = exc_info.value
    assert error.recovery_status == "partial"
    assert error.operation_error is initial_error
    assert len(error.rollback_errors) == 1
    assert error.rollback_errors[0].entry_id == second.id
    assert error.rollback_errors[0].path == second_path
    assert error.rollback_errors[0].error is rollback_error
    assert error.cache_error is None
    assert first_path.is_file()
    assert not second_path.exists()
    assert [entry.id for entry in engine.get_entries()] == [first.id]
    assert str(initial_error) in str(error)
    assert str(rollback_error) in str(error)
    assert str(second_path) in str(error)
    assert engine.health().healthy is True
