"""Memory's public schema and independent raw-file storage boundaries."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum
from pathlib import Path
from tempfile import mkstemp as _real_mkstemp
from unittest.mock import patch

import pytest
from owlbear_memory import storage
from owlbear_memory.errors import ConcurrencyError, NotFoundError, TransitionError
from owlbear_memory.errors import ValidationError as MemValidationError
from owlbear_memory.models import ChallengeRecord, MemoryCategory, MemoryEntry, MemoryState
from pydantic import ValidationError as PydanticValidationError

from owlbear_memory_mcp.tools import MemoryState as McpState

_VALID_ID = "550e8400-e29b-41d4-a716-446655440000"
_VALID_FRONTMATTER = """\
---
id: 550e8400-e29b-41d4-a716-446655440000
title: Test Entry
categories:
- domain-knowledge
confidence: 0.9
state: pending
scope_agents: []
source_agent: test-agent
created_at: '2026-01-01T00:00:00+00:00'
updated_at: '2026-01-01T00:00:00+00:00'
approved_at: null
---

"""
_8KB = 8192


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


def _make_valid_entry() -> MemoryEntry:
    return MemoryEntry(**_valid_entry_data())


def _write_valid_file(path: Path, body: str = "Some content") -> None:
    path.write_text(_VALID_FRONTMATTER + body + "\n", encoding="utf-8")


def test_a_recommended_scope_round_trips_and_an_entry_without_one_keeps_its_bytes(tmp_path: Path) -> None:
    plain, recommended = tmp_path / "plain.md", tmp_path / "recommended.md"
    storage.write_entry(plain, _make_valid_entry(), memory_dir=tmp_path)
    storage.write_entry(
        recommended, _make_valid_entry().model_copy(update={"recommended": "global"}), memory_dir=tmp_path
    )
    assert "recommended" not in plain.read_text(encoding="utf-8")
    assert (storage.read_entry(plain).recommended, storage.read_entry(recommended).recommended) == (None, "global")
    with pytest.raises(PydanticValidationError):
        MemoryEntry(**_valid_entry_data(), recommended="team")


def test_concurrent_reads_and_writes_parse_every_entry(tmp_path: Path) -> None:
    previous_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-5)
    entry = _make_valid_entry().model_copy(update={"content": "c" * 500})
    paths = [tmp_path / f"{index}.md" for index in range(8)]
    for path in paths:
        storage.write_entry(path, entry, memory_dir=tmp_path)

    def exercise(worker: int) -> int:
        unreadable = 0
        for _ in range(40):
            for path in paths:
                unreadable += storage.read_entry(path) is None
            storage.write_entry(paths[worker], entry, memory_dir=tmp_path)
        return unreadable

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            assert sum(executor.map(exercise, range(8))) == 0
    finally:
        sys.setswitchinterval(previous_interval)


def test_public_memory_types() -> None:
    assert {v.value for v in MemoryCategory} == {
        "domain-knowledge",
        "behaviour",
        "pitfall",
        "process",
        "tool-usage",
        "goal",
        "personality",
        "preference",
        "env-context",
    }
    assert {v.value for v in MemoryState} == {
        "pending",
        "curated",
        "approved",
        "contested",
        "disputed",
        "stale",
        "deleted",
    }
    assert McpState is MemoryState
    assert issubclass(MemoryCategory, StrEnum)
    assert issubclass(MemoryState, StrEnum)
    assert {
        "id",
        "title",
        "content",
        "categories",
        "confidence",
        "state",
        "scope_agents",
        "source_agent",
        "created_at",
        "updated_at",
        "approved_at",
    } <= MemoryEntry.model_fields.keys()
    errors = {NotFoundError, ConcurrencyError, MemValidationError, TransitionError}
    assert len(errors) == 4
    for error in errors:
        assert issubclass(error, Exception)
        message = "public failure"
        with pytest.raises(error, match="public failure"):
            raise error(message)


@pytest.mark.parametrize(
    ("fields", "valid"),
    [
        ({}, True),
        ({"approved_at": "2026-06-01T12:00:00+00:00"}, True),
        ({"content": "x" * 1024}, True),
        ({"content": "x" * 1025}, False),
        ({"id": "not-a-uuid"}, False),
        ({"id": "a3bb189e-8bf9-3888-9912-ace4e6543002"}, False),
        ({"created_at": "2026-01-01T00:00:00"}, False),
        ({"updated_at": "2026-01-01"}, False),
        ({"scope_agents": ["builder", "reviewer"]}, True),
    ],
)
def test_memory_model_schema(fields: dict, *, valid: bool) -> None:
    data = {**_valid_entry_data(), **fields}
    if not valid:
        with pytest.raises(PydanticValidationError):
            MemoryEntry(**data)
        return
    entry = MemoryEntry(**data)
    assert all(getattr(entry, field) == value for field, value in data.items())
    assert entry.challenges == []
    assert "contested_by_task" not in MemoryEntry.model_fields


def test_source_agent_is_frozen_after_creation() -> None:
    entry = _make_valid_entry()
    with pytest.raises(PydanticValidationError):
        entry.source_agent = "new-agent"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("raw", "body"),
    [
        (_VALID_FRONTMATTER + "Some content\n", "Some content"),
        (_VALID_FRONTMATTER + "Hello from body\n", "Hello from body"),
        ("---\n: invalid: yaml: [unbalanced\n---\n\nContent\n", None),
        ("No frontmatter here\n", None),
        (
            (
                "---\nid: not-a-uuid\ntitle: Bad\ncategories: [domain-knowledge]\n"
                "confidence: 0.9\nstate: pending\nsource_agent: agent\n"
                "created_at: '2026-01-01T00:00:00+00:00'\n"
                "updated_at: '2026-01-01T00:00:00+00:00'\n---\n\nContent\n"
            ),
            None,
        ),
        ("", None),
        ("---\n---\n", None),
        ("---\n}{invalid yaml\n---\n\nbody\n", None),
        ("---\ntitle: Only title\n---\n\nbody\n", None),
        ("---\n- item1\n- item2\n---\n\nbody\n", None),
    ],
    ids=[
        "valid",
        "body",
        "unbalanced-yaml",
        "no-frontmatter",
        "invalid-uuid",
        "empty",
        "empty-frontmatter",
        "invalid-yaml",
        "missing-fields",
        "non-object",
    ],
)
def test_raw_memory_reader_contract(tmp_path: Path, raw: str, body: str | None) -> None:
    path = tmp_path / "raw.md"
    path.write_text(raw, encoding="utf-8")
    result = storage.read_entry(path)
    if body is None:
        assert result is None
    else:
        assert isinstance(result, MemoryEntry)
        assert (result.id, result.content) == (_VALID_ID, body)


def test_read_entry_symlink_returns_none(tmp_path: Path) -> None:
    real_file = tmp_path / "real.md"
    _write_valid_file(real_file)
    link = tmp_path / "link.md"
    link.symlink_to(real_file)
    assert storage.read_entry(link) is None


@pytest.mark.parametrize("size", [8192, 8193])
def test_read_entry_exact_byte_boundary(tmp_path: Path, size: int) -> None:
    base = _VALID_FRONTMATTER + "A\n"
    padding = size - len(base.encode("utf-8")) - 3
    assert padding > 0
    content = "---\n# " + "x" * padding + "\n" + _VALID_FRONTMATTER[4:] + "A\n"
    path = tmp_path / "boundary.md"
    path.write_text(content, encoding="utf-8")
    assert path.stat().st_size == size
    result = storage.read_entry(path)
    if size == 8192:
        assert result is not None
        assert result.content == "A"
    else:
        assert result is None


def test_write_entry_produces_file_parseable_by_read_entry(tmp_path: Path) -> None:
    entry = MemoryEntry(
        **{
            **_valid_entry_data(),
            "score": 0.93,
            "outstanding_count": 7,
            "unremarkable_count": 12,
            "didnt_use_count": 3,
            "challenges": [
                ChallengeRecord(
                    task_id="task-123", revision="0123456789abcdef", recorded_at="2026-01-01T00:00:00+00:00"
                )
            ],
        }
    )
    path = tmp_path / "memory" / "entry.md"
    storage.write_entry(path, entry, memory_dir=tmp_path / "memory")
    assert storage.read_entry(path) == entry
    serialized = path.read_text(encoding="utf-8")
    assert "challenges:" in serialized
    assert "contested_by_task" not in serialized


@pytest.mark.parametrize(
    ("title", "content"),
    [("x" * 7828, "Some content"), ("é" * 3909 + "x" * 10, "Some content"), ("x" * 3744, "😀" * 1024)],
    ids=["ascii-title", "multibyte-title", "multibyte-content"],
)
def test_write_entry_accepts_exact_utf8_serialized_size(tmp_path: Path, title: str, content: str) -> None:
    target = tmp_path / "entry.md"
    entry = MemoryEntry(**{**_valid_entry_data(), "title": title, "content": content})
    storage.write_entry(target, entry, memory_dir=tmp_path)
    assert target.stat().st_size == _8KB
    assert storage.read_entry(target) == entry


def test_write_entry_rejects_8193_byte_serialization_before_replacement(tmp_path: Path) -> None:
    target = tmp_path / "entry.md"
    original = _make_valid_entry()
    storage.write_entry(target, original, memory_dir=tmp_path)
    before = target.read_bytes()
    oversized = MemoryEntry(**{**_valid_entry_data(), "title": "x" * 7829})
    with pytest.raises(ValueError, match=rf"serialized entry exceeds {_8KB} bytes \(got 8193\).*metadata"):
        storage.write_entry(target, oversized, memory_dir=tmp_path)
    assert target.read_bytes() == before
    assert storage.read_entry(target) == original


@pytest.mark.parametrize(
    ("source_agent", "expected_size"),
    [("é" * 3909 + "x" * 10, _8KB), ("é" * 3909 + "x" * 11, _8KB + 1)],
    ids=["accepted", "rejected"],
)
def test_write_entry_enforces_exact_multibyte_metadata_boundary(
    tmp_path: Path, source_agent: str, expected_size: int
) -> None:
    target = tmp_path / "entry.md"
    entry = MemoryEntry(**{**_valid_entry_data(), "source_agent": source_agent})
    if expected_size > _8KB:
        with pytest.raises(ValueError, match=rf"serialized entry exceeds {_8KB} bytes \(got {expected_size}\)"):
            storage.write_entry(target, entry, memory_dir=tmp_path)
        assert not target.exists()
    else:
        storage.write_entry(target, entry, memory_dir=tmp_path)
        assert target.stat().st_size == expected_size
        assert storage.read_entry(target) == entry


def test_write_entry_rejects_content_that_cannot_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "entry.md"
    storage.write_entry(target, _make_valid_entry(), memory_dir=tmp_path)
    before = target.read_bytes()
    lossy = MemoryEntry(**{**_valid_entry_data(), "content": " padded "})
    with pytest.raises(ValueError, match="does not round-trip unchanged"):
        storage.write_entry(target, lossy, memory_dir=tmp_path)
    assert target.read_bytes() == before


@pytest.mark.parametrize(
    ("overrides", "serialized_size"),
    [
        ({"source_agent": "x" * 9000}, 9364),
        ({"scope_agents": ["x" * 9000]}, 9376),
        ({"title": "x" * 3745, "content": "😀" * 1024}, 8193),
    ],
    ids=["provenance", "scope", "body-content"],
)
def test_write_entry_rejects_oversized_yaml_or_body_content(
    tmp_path: Path, overrides: dict, serialized_size: int
) -> None:
    target = tmp_path / "entry.md"
    entry = MemoryEntry(**{**_valid_entry_data(), **overrides})
    with pytest.raises(ValueError, match=rf"serialized entry exceeds {_8KB} bytes \(got {serialized_size}\)"):
        storage.write_entry(target, entry, memory_dir=tmp_path)
    assert not target.exists()


def test_write_entry_path_outside_memory_dir_raises(tmp_path: Path) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    outside = tmp_path / "outside" / "entry.md"
    with pytest.raises(ValueError, match="Path escapes memory_dir"):
        storage.write_entry(outside, _make_valid_entry(), memory_dir=memory_dir)


def test_write_entry_symlink_target_raises(tmp_path: Path) -> None:
    real = tmp_path / "real.md"
    real.write_text("placeholder", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="Symlink paths are not allowed"):
        storage.write_entry(link, _make_valid_entry(), memory_dir=tmp_path)


def test_write_entry_invalid_object_raises(tmp_path: Path) -> None:
    with pytest.raises(PydanticValidationError):
        storage.write_entry(tmp_path / "entry.md", "not-a-memory-entry", memory_dir=tmp_path)  # type: ignore[arg-type]


def test_write_entry_uses_mkstemp_and_replace_atomically(tmp_path: Path) -> None:
    target = tmp_path / "entry.md"
    captured: list[tuple[int, str]] = []

    def _capturing_mkstemp(*args: object, **kwargs: object) -> tuple[int, str]:
        fd, name = _real_mkstemp(*args, **kwargs)  # type: ignore[arg-type]
        captured.append((fd, name))
        return fd, name

    with (
        patch("owlbear_memory.storage.mkstemp", side_effect=_capturing_mkstemp) as mock_mkstemp,
        patch("os.fsync") as mock_fsync,
    ):
        storage.write_entry(target, _make_valid_entry(), memory_dir=tmp_path)
    mock_mkstemp.assert_called_once()
    mock_fsync.assert_called()
    assert target.exists()
    assert not Path(captured[0][1]).exists()


def test_delete_entry_removes_file_from_disk(tmp_path: Path) -> None:
    target = tmp_path / "entry.md"
    storage.write_entry(target, _make_valid_entry(), memory_dir=tmp_path)
    assert target.exists()
    storage.delete_entry(target, memory_dir=tmp_path)
    assert not target.exists()


def test_delete_entry_nonexistent_file_raises_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(NotFoundError):
        storage.delete_entry(tmp_path / "missing.md", memory_dir=tmp_path)


def test_delete_entry_path_outside_memory_dir_raises(tmp_path: Path) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("placeholder", encoding="utf-8")
    with pytest.raises(ValueError, match="Path escapes memory_dir"):
        storage.delete_entry(outside, memory_dir=memory_dir)


def test_delete_entry_symlink_raises(tmp_path: Path) -> None:
    real = tmp_path / "real.md"
    _write_valid_file(real)
    link = tmp_path / "link.md"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="Symlink paths are not allowed"):
        storage.delete_entry(link, memory_dir=tmp_path)
