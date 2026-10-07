"""Protect MemoryEngine's per-file freshness detection."""

from __future__ import annotations

import multiprocessing
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest
from owlbear_memory import MemoryEngine


def _rewrite_in_place(memory_dir: str, entry_id: str, content: bytes, mtime_ns: int) -> None:
    memory_dir_path = Path(memory_dir)
    entry = MemoryEngine(memory_dir_path).get_entry(entry_id)
    target = memory_dir_path / f"{entry.id}.md"
    with target.open("r+b") as entry_file:
        entry_file.write(content)
        entry_file.truncate()
    os.utime(target, ns=(mtime_ns, mtime_ns))


def test_get_entries_refreshes_after_external_in_place_rewrite(tmp_path: Path) -> None:
    """A spawned same-inode edit is visible without an explicit force refresh."""
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Freshness test",
        content="Before",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    entry_path = tmp_path / f"{entry.id}.md"
    assert engine.get_entries() == [entry]
    original_stat = entry_path.stat()
    directory_mtime_ns = tmp_path.stat().st_mtime_ns
    original_bytes = entry_path.read_bytes()
    content = original_bytes.rsplit(b"\n\n", 1)[0] + b"\n\nAfter external rewrite\n"
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=_rewrite_in_place,
        args=(str(tmp_path), entry.id, content, original_stat.st_mtime_ns + 2_000_000_000),
    )

    process.start()
    process.join(timeout=15)
    if process.is_alive():
        process.terminate()
        process.join()
    assert process.exitcode == 0

    rewritten_stat = entry_path.stat()
    assert rewritten_stat.st_ino == original_stat.st_ino
    assert rewritten_stat.st_size == len(content)
    assert rewritten_stat.st_mtime_ns != original_stat.st_mtime_ns
    assert tmp_path.stat().st_mtime_ns == directory_mtime_ns
    with patch.object(engine, "load", side_effect=AssertionError("unexpected force refresh")):
        assert engine.get_entries()[0].content == "After external rewrite"
        assert engine.get_entry(entry.id).content == "After external rewrite"


def test_get_entries_reuses_cached_entries_when_file_becomes_unreadable(tmp_path: Path) -> None:
    """Unchanged file signatures let reads reuse entries without reparsing."""
    if os.geteuid() == 0:
        pytest.skip("Permission-based no-reparse proof is invalid when running as root")

    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Cached entry",
        content="Cached content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    entry_path = tmp_path / f"{entry.id}.md"
    assert engine.get_entries() == [entry]
    original_stat = entry_path.stat()

    try:
        entry_path.chmod(0)
        unreadable_stat = entry_path.stat()
        assert unreadable_stat.st_ino == original_stat.st_ino
        assert unreadable_stat.st_size == original_stat.st_size
        assert unreadable_stat.st_mtime_ns == original_stat.st_mtime_ns
        with pytest.raises(PermissionError):
            entry_path.read_bytes()

        assert engine.get_entries() == [entry]
        assert engine.get_entries() == [entry]
        assert engine.parse_errors == 0
    finally:
        entry_path.chmod(stat.S_IMODE(original_stat.st_mode))
