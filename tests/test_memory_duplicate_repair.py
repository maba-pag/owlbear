from __future__ import annotations

import multiprocessing
import os
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from owlbear_memory import (
    DuplicateEntryError,
    MemoryEngine,
    MemoryEntry,
    MemoryState,
    repair_duplicate_ids,
    storage,
    writer_lock,
)

_DUPLICATE_ID = "550e8400-e29b-41d4-a716-446655440001"
_TARGET_ID = "550e8400-e29b-41d4-a716-446655440002"
_REUSE_ID = "550e8400-e29b-41d4-a716-446655440003"


def _entry(*, title: str, content: str, updated_at: str, **overrides: object) -> MemoryEntry:
    state = overrides.get("state", MemoryState.PENDING)
    data: dict[str, object] = {
        "id": _DUPLICATE_ID,
        "title": title,
        "content": content,
        "categories": ["domain-knowledge"],
        "confidence": 0.9,
        "state": state,
        "outstanding_count": 2,
        "unremarkable_count": 1,
        "didnt_use_count": 3,
        "score": 1.0,
        "scope_agents": ["test-agent"],
        "source_agent": "test-agent",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": updated_at,
        "approved_at": "2026-01-01T00:00:00+00:00" if state == MemoryState.APPROVED else None,
    }
    data.update(overrides)
    return MemoryEntry.model_validate(data)


def _snapshot(memory_dir: Path) -> tuple[tuple[str, bytes, int], ...]:
    return tuple((path.name, path.read_bytes(), path.stat().st_mtime_ns) for path in sorted(memory_dir.glob("*.md")))


def _join_processes(processes: list[multiprocessing.Process]) -> None:
    for process in processes:
        process.join(timeout=20)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
    assert all(process.exitcode == 0 for process in processes)


def _save_after_duplicate_barrier(memory_dir: str, barrier: Any, results: Any, label: str) -> None:
    engine = MemoryEngine(memory_dir)
    assert engine.health().duplicate_paths
    barrier.wait(timeout=15)
    entry = engine.save(
        title=f"Concurrent {label}",
        content=label,
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    results.put(entry.id)


def test_edit_repairs_differing_duplicate_before_applying_change(tmp_path: Path) -> None:
    older = _entry(
        title="Older entry",
        content="older copy",
        updated_at="2026-01-01T00:00:00+00:00",
        state=MemoryState.APPROVED,
    )
    newest = _entry(
        title="Newest entry",
        content="newest copy",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", older, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "newest-copy.md", newest, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)

    edited = engine.edit(_DUPLICATE_ID, {"content": "edited newest copy"}, newest.updated_at)

    entries = [entry for path in tmp_path.glob("*.md") if (entry := storage.read_entry(path)) is not None]
    original_id_entries = [entry for entry in entries if entry.id == _DUPLICATE_ID]
    repaired_entries = [entry for entry in entries if entry.id != _DUPLICATE_ID]

    assert edited.content == "edited newest copy"
    assert len(original_id_entries) == 1
    assert original_id_entries[0].content == "edited newest copy"
    assert len(repaired_entries) == 1
    assert repaired_entries[0].state == MemoryState.PENDING
    assert _DUPLICATE_ID in repaired_entries[0].title
    assert repaired_entries[0].content == "older copy"
    assert repaired_entries[0].approved_at is None
    assert repaired_entries[0].outstanding_count == 0
    assert repaired_entries[0].unremarkable_count == 0
    assert repaired_entries[0].didnt_use_count == 0
    assert repaired_entries[0].score == repaired_entries[0].confidence


def test_reads_and_health_do_not_write_before_an_unrelated_mutation_repairs_identical_copies(
    tmp_path: Path,
) -> None:
    identical = _entry(
        title="Identical entry",
        content="same content",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    unrelated = _entry(
        title="Unrelated entry",
        content="unrelated content",
        updated_at="2026-01-02T00:00:00+00:00",
        id=_TARGET_ID,
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", identical, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "identical-copy.md", identical, memory_dir=tmp_path)
    storage.write_entry(tmp_path / f"{_TARGET_ID}.md", unrelated, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    before = _snapshot(tmp_path)

    assert engine.get_entries()
    assert engine.get_entry(_DUPLICATE_ID) == identical
    health = engine.health()

    assert health.duplicate_paths == {_DUPLICATE_ID: sorted([f"{_DUPLICATE_ID}.md", "identical-copy.md"])}
    assert _snapshot(tmp_path) == before

    edited = engine.edit(_TARGET_ID, {"content": "updated unrelated content"}, unrelated.updated_at)

    assert edited.content == "updated unrelated content"
    assert not (tmp_path / "identical-copy.md").exists()
    assert engine.health().duplicate_paths == {}


@pytest.mark.parametrize(
    "operation",
    [
        "save",
        "approve",
        "resolve",
        "edit",
        "delete",
        "purge",
        "record_assessment",
        "record_factually_wrong",
        "try_stale_transition",
        "rename_agent",
        "delete_agent",
    ],
)
def test_every_mutator_repairs_duplicates_before_its_own_change(tmp_path: Path, operation: str) -> None:
    older = _entry(
        title="Older duplicate",
        content="older content",
        updated_at="2026-01-01T00:00:00+00:00",
        state=MemoryState.APPROVED,
    )
    newest = _entry(
        title="Newest duplicate",
        content="newest content",
        updated_at="2026-01-02T00:00:00+00:00",
        state=MemoryState.APPROVED,
    )
    target_states = {
        "approve": MemoryState.CURATED,
        "resolve": MemoryState.DISPUTED,
        "record_assessment": MemoryState.APPROVED,
        "record_factually_wrong": MemoryState.APPROVED,
        "try_stale_transition": MemoryState.CURATED,
        "delete_agent": MemoryState.APPROVED,
    }
    target_updated_at = "2020-01-01T00:00:00+00:00" if operation == "purge" else "2026-01-02T00:00:00+00:00"
    target_created_at = "2020-01-01T00:00:00+00:00" if operation == "purge" else "2026-01-01T00:00:00+00:00"
    target = _entry(
        title="Mutation target",
        content="target content",
        updated_at=target_updated_at,
        created_at=target_created_at,
        state=target_states.get(operation, MemoryState.PENDING),
        id=_TARGET_ID,
    )
    if operation == "try_stale_transition":
        target = target.model_copy(update={"outstanding_count": 0, "unremarkable_count": 0, "didnt_use_count": 51})

    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", newest, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    storage.write_entry(tmp_path / f"{_TARGET_ID}.md", target, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)

    operations = {
        "save": partial(
            engine.save,
            title="Saved entry",
            content="saved content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        ),
        "approve": partial(engine.approve, _TARGET_ID, target.updated_at),
        "resolve": partial(engine.resolve, _TARGET_ID, target.updated_at),
        "edit": partial(engine.edit, _TARGET_ID, {"content": "edited target"}, target.updated_at),
        "delete": partial(engine.delete, _TARGET_ID, target.updated_at),
        "purge": partial(engine.purge, min_age_days=0),
        "record_assessment": partial(engine.record_assessment, _TARGET_ID, "outstanding", target.updated_at),
        "record_factually_wrong": partial(engine.record_factually_wrong, _TARGET_ID, "task-1", target.updated_at),
        "try_stale_transition": partial(engine.try_stale_transition, target),
        "rename_agent": partial(engine.rename_agent, "test-agent", "renamed-agent"),
        "delete_agent": partial(engine.delete_agent, "test-agent"),
    }
    operations[operation]()

    assert engine.health().duplicate_paths == {}
    if operation == "delete_agent":
        canonical = storage.read_entry(tmp_path / f"{_DUPLICATE_ID}.md")
        assert canonical is not None
        assert canonical.state == MemoryState.DELETED
        assert canonical.scope_agents == []
        assert not any(
            entry is not None and _DUPLICATE_ID in entry.title
            for path in tmp_path.glob("*.md")
            if (entry := storage.read_entry(path)) is not None
        )


def test_equal_timestamps_prefer_id_filename_and_rename_applies_after_repair(tmp_path: Path) -> None:
    older = _entry(
        title="Older path entry",
        content="older path content",
        updated_at="2026-01-02T00:00:00+00:00",
        state=MemoryState.APPROVED,
    )
    named = _entry(
        title="ID path entry",
        content="ID path content",
        updated_at="2026-01-02T00:00:00+00:00",
        state=MemoryState.APPROVED,
    )
    storage.write_entry(tmp_path / "a-copy.md", older, memory_dir=tmp_path)
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", named, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)

    result = engine.rename_agent("test-agent", "renamed-agent")

    entries = [entry for path in tmp_path.glob("*.md") if (entry := storage.read_entry(path)) is not None]
    canonical = next(entry for entry in entries if entry.id == _DUPLICATE_ID)
    repaired = next(entry for entry in entries if entry.id != _DUPLICATE_ID)
    assert result["entries_updated"] == 2
    assert canonical.content == "ID path content"
    assert canonical.source_agent == "renamed-agent"
    assert repaired.content == "older path content"
    assert repaired.state == MemoryState.PENDING
    assert repaired.source_agent == "renamed-agent"


def test_equal_timestamps_without_id_filename_choose_lexicographically_first_path(tmp_path: Path) -> None:
    later = _entry(
        title="Later path entry",
        content="later path content",
        updated_at="2026-01-02T00:00:00+00:00",
        state=MemoryState.APPROVED,
        id=_TARGET_ID,
    )
    first = _entry(
        title="First path entry",
        content="first path content",
        updated_at="2026-01-02T00:00:00+00:00",
        state=MemoryState.APPROVED,
        id=_TARGET_ID,
    )
    storage.write_entry(tmp_path / "z-copy.md", later, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "a-copy.md", first, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)

    assert engine.get_entry(_TARGET_ID).content == "first path content"
    edited = engine.edit(_TARGET_ID, {"content": "edited first path"}, first.updated_at)

    entries = [entry for path in tmp_path.glob("*.md") if (entry := storage.read_entry(path)) is not None]
    assert edited.content == "edited first path"
    assert next(entry for entry in entries if entry.id == _TARGET_ID).content == "edited first path"
    assert any(entry.id != _TARGET_ID and entry.content == "later path content" for entry in entries)


def test_purge_repairs_approved_copy_before_removing_newer_deleted_tombstone(tmp_path: Path) -> None:
    approved = _entry(
        title="Approved copy",
        content="preserved approved content",
        updated_at="2025-01-01T00:00:00+00:00",
        state=MemoryState.APPROVED,
        created_at="2025-01-01T00:00:00+00:00",
    )
    tombstone = _entry(
        title="Deleted copy",
        content="deleted content",
        updated_at="2025-01-02T00:00:00+00:00",
        state=MemoryState.DELETED,
        created_at="2025-01-01T00:00:00+00:00",
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", approved, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "deleted-copy.md", tombstone, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)

    result = engine.purge(min_age_days=0)

    entries = [entry for path in tmp_path.glob("*.md") if (entry := storage.read_entry(path)) is not None]
    assert result.purged == 1
    assert all(entry.id != _DUPLICATE_ID for entry in entries)
    assert len(entries) == 1
    assert entries[0].state == MemoryState.PENDING
    assert _DUPLICATE_ID in entries[0].title
    assert entries[0].content == "preserved approved content"


def test_repair_write_failure_preserves_all_sources_and_names_relative_paths(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("real permission behavior cannot be verified as root")

    older = _entry(
        title="Older entry",
        content="older content",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    newest = _entry(
        title="Newest entry",
        content="newest content",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", newest, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    before = _snapshot(tmp_path)
    original_mode = tmp_path.stat().st_mode & 0o777

    try:
        tmp_path.chmod(original_mode & ~0o222)
        with pytest.raises(DuplicateEntryError) as exc_info:
            engine.edit(_DUPLICATE_ID, {"content": "must not apply"}, newest.updated_at)
    finally:
        tmp_path.chmod(original_mode)

    error = exc_info.value
    assert error.entry_id == _DUPLICATE_ID
    assert error.paths == tuple(sorted([f"{_DUPLICATE_ID}.md", "older-copy.md"]))
    assert _snapshot(tmp_path) == before


def test_public_repair_routine_can_run_under_the_caller_writer_lock(tmp_path: Path) -> None:
    older = _entry(
        title="Older entry",
        content="older content",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    newest = _entry(
        title="Newest entry",
        content="newest content",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", newest, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)

    with writer_lock(tmp_path):
        repair_duplicate_ids(tmp_path)

    assert engine.health().duplicate_paths == {}
    assert len(list(tmp_path.glob("*.md"))) == 2


def test_spawned_mutations_repair_one_duplicate_once_under_the_real_writer_lock(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    older = _entry(
        title="Older entry",
        content="older content",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    newest = _entry(
        title="Newest entry",
        content="newest content",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", newest, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    barrier = context.Barrier(2)
    results = context.Queue()
    workers = [
        context.Process(
            target=_save_after_duplicate_barrier,
            args=(str(tmp_path), barrier, results, f"worker-{index}"),
        )
        for index in range(2)
    ]

    try:
        for worker in workers:
            worker.start()
        _join_processes(workers)
        saved_ids = [results.get(timeout=5) for _ in workers]
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join()
        results.close()
        results.join_thread()

    entries = [entry for path in tmp_path.glob("*.md") if (entry := storage.read_entry(path)) is not None]
    repaired = [entry for entry in entries if _DUPLICATE_ID in entry.title]
    assert len(set(saved_ids)) == 2
    assert sum(entry.id == _DUPLICATE_ID for entry in entries) == 1
    assert len(repaired) == 1
    assert MemoryEngine(tmp_path).health().duplicate_paths == {}


def test_repair_reuses_matching_pending_copy_without_creating_another(tmp_path: Path) -> None:
    older = _entry(
        title="Older entry",
        content="older content",
        updated_at="2026-01-01T00:00:00+00:00",
        state=MemoryState.APPROVED,
    )
    newest = _entry(
        title="Newest entry",
        content="newest content",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    marked = _entry(
        title=f"[Recovered duplicate ID {_DUPLICATE_ID}] Older entry",
        content=older.content,
        updated_at="2026-10-01T00:00:00+00:00",
        state=MemoryState.PENDING,
        id=_REUSE_ID,
        created_at=older.created_at,
        source_agent=older.source_agent,
        scope_agents=older.scope_agents,
    ).model_copy(update={"outstanding_count": 0, "unremarkable_count": 0, "didnt_use_count": 0, "score": 0.9})
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", newest, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    marked_path = tmp_path / f"{_REUSE_ID}.md"
    storage.write_entry(marked_path, marked, memory_dir=tmp_path)
    marked_before = marked_path.read_bytes()
    engine = MemoryEngine(tmp_path)

    engine.save(
        title="Unrelated mutation",
        content="mutation content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )

    assert not (tmp_path / "older-copy.md").exists()
    assert marked_path.read_bytes() == marked_before
    assert [entry.id for entry in engine.get_entries() if _DUPLICATE_ID in entry.title] == [_REUSE_ID]
    assert engine.health().duplicate_paths == {}


def test_repair_does_not_reuse_pending_copy_with_unreset_assessments(tmp_path: Path) -> None:
    older = _entry(
        title="Older entry",
        content="older content",
        updated_at="2026-01-01T00:00:00+00:00",
        state=MemoryState.APPROVED,
    )
    newest = _entry(
        title="Newest entry",
        content="newest content",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    marked = _entry(
        title=f"[Recovered duplicate ID {_DUPLICATE_ID}] Older entry",
        content=older.content,
        updated_at="2026-10-01T00:00:00+00:00",
        state=MemoryState.PENDING,
        id=_REUSE_ID,
        created_at=older.created_at,
        source_agent=older.source_agent,
        scope_agents=older.scope_agents,
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", newest, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    marked_path = tmp_path / f"{_REUSE_ID}.md"
    storage.write_entry(
        marked_path,
        marked.model_copy(update={"outstanding_count": 1, "score": 1.0}),
        memory_dir=tmp_path,
    )
    marked_before = marked_path.read_bytes()
    engine = MemoryEngine(tmp_path)

    engine.save(
        title="Unrelated mutation",
        content="mutation content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )

    entries = [entry for path in tmp_path.glob("*.md") if (entry := storage.read_entry(path)) is not None]
    repaired = [entry for entry in entries if _DUPLICATE_ID in entry.title]
    assert len(repaired) == 2
    assert marked_path.read_bytes() == marked_before
    new_copy = next(entry for entry in repaired if entry.id != _REUSE_ID)
    assert new_copy.outstanding_count == 0
    assert new_copy.unremarkable_count == 0
    assert new_copy.didnt_use_count == 0
    assert new_copy.score == new_copy.confidence


def test_repair_does_not_reuse_pending_copy_with_different_scope(tmp_path: Path) -> None:
    older = _entry(
        title="Older entry",
        content="older content",
        updated_at="2026-01-01T00:00:00+00:00",
        state=MemoryState.APPROVED,
        scope_agents=["source-agent"],
    )
    newest = _entry(
        title="Newest entry",
        content="newest content",
        updated_at="2026-01-02T00:00:00+00:00",
        scope_agents=["source-agent"],
    )
    other_scope = _entry(
        title=f"[Recovered duplicate ID {_DUPLICATE_ID}] Older entry",
        content=older.content,
        updated_at="2026-10-01T00:00:00+00:00",
        state=MemoryState.PENDING,
        id=_REUSE_ID,
        created_at=older.created_at,
        source_agent=older.source_agent,
        scope_agents=["other-agent"],
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", newest, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "older-copy.md", older, memory_dir=tmp_path)
    storage.write_entry(tmp_path / f"{_REUSE_ID}.md", other_scope, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)

    engine.save(
        title="Unrelated mutation",
        content="mutation content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )

    entries = [entry for path in tmp_path.glob("*.md") if (entry := storage.read_entry(path)) is not None]
    repaired = [entry for entry in entries if _DUPLICATE_ID in entry.title]
    assert len(repaired) == 2
    assert next(entry for entry in repaired if entry.id == _REUSE_ID).scope_agents == ["other-agent"]
    new_copy = next(entry for entry in repaired if entry.id != _REUSE_ID)
    assert new_copy.scope_agents == ["source-agent"]

    engine.delete_agent("other-agent")

    assert storage.read_entry(tmp_path / f"{_REUSE_ID}.md") is None
    remaining_copy = storage.read_entry(tmp_path / f"{new_copy.id}.md")
    assert remaining_copy is not None
    assert remaining_copy.scope_agents == ["source-agent"]
