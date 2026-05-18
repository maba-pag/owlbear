"""RED-phase tests for owlbear-memory package primitives (task #1667).

AC coverage:
- AC1: models.py — MemoryEntry, MemoryCategory, MemoryState with all required fields,
       validators (UUIDv4, tz-aware timestamps, frozen source_agent), content ≤1024 constraint
- AC2: errors.py — NotFoundError, ConcurrencyError, ValidationError, TransitionError
       as distinct Exception subclasses
- AC3: storage.read_entry — symlink/size rejection, YAML parsing, lenient (returns None, never raises)
- AC4: storage.write_entry — containment, symlink rejection, atomic write;
       storage.delete_entry — containment, symlink rejection, NotFoundError
"""

from __future__ import annotations

from pathlib import Path
from tempfile import mkstemp as _real_mkstemp
from unittest.mock import patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from owlbear_memory.errors import (
    ConcurrencyError,
    NotFoundError,
    TransitionError,
    ValidationError as MemValidationError,
)
from owlbear_memory.models import MemoryCategory, MemoryEntry, MemoryState
from owlbear_memory import storage

# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

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
    """Write a syntactically and semantically valid memory markdown file."""
    path.write_text(_VALID_FRONTMATTER + body + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# AC1: models.py — MemoryEntry, MemoryCategory, MemoryState
# ---------------------------------------------------------------------------


class TestFromAC_Models:
    """AC1: models.py exports correct Pydantic models with required fields and validators."""

    # --- MemoryCategory ---

    def test_memory_category_has_nine_values(self) -> None:
        """MemoryCategory StrEnum must have exactly 9 members."""
        assert len(list(MemoryCategory)) == 9

    def test_memory_category_values(self) -> None:
        """MemoryCategory must contain exactly the 9 documented string values."""
        expected = {
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
        actual = {v.value for v in MemoryCategory}
        assert actual == expected

    # --- MemoryState ---

    def test_memory_state_has_four_values(self) -> None:
        """MemoryState StrEnum must have exactly 4 members."""
        assert len(list(MemoryState)) == 4

    def test_memory_state_values(self) -> None:
        """MemoryState must contain exactly: pending, curated, approved, deleted."""
        expected = {"pending", "curated", "approved", "deleted"}
        actual = {v.value for v in MemoryState}
        assert actual == expected

    # --- MemoryEntry construction ---

    def test_memory_entry_valid_instantiation(self) -> None:
        """Happy: MemoryEntry instantiates from valid data without error."""
        entry = _make_valid_entry()
        assert entry.id == _VALID_ID
        assert entry.title == "Test Entry"
        assert entry.content == "Some content"

    def test_memory_entry_has_all_required_fields(self) -> None:
        """MemoryEntry must expose all 11 documented fields."""
        entry = _make_valid_entry()
        required = (
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
        )
        for field in required:
            assert hasattr(entry, field), f"MemoryEntry missing field: {field}"

    # --- approved_at ---

    def test_approved_at_nullable(self) -> None:
        """approved_at field accepts None."""
        entry = MemoryEntry(**{**_valid_entry_data(), "approved_at": None})
        assert entry.approved_at is None

    def test_approved_at_accepts_tz_aware_timestamp(self) -> None:
        """approved_at field accepts a valid timezone-aware ISO timestamp string."""
        ts = "2026-06-01T12:00:00+00:00"
        entry = MemoryEntry(**{**_valid_entry_data(), "approved_at": ts})
        assert entry.approved_at == ts

    # --- content ≤1024 constraint ---

    def test_content_at_max_length_is_valid(self) -> None:
        """Boundary: content of exactly 1024 characters is accepted."""
        entry = MemoryEntry(**{**_valid_entry_data(), "content": "x" * 1024})
        assert len(entry.content) == 1024

    def test_content_over_max_length_is_rejected(self) -> None:
        """Boundary: content of 1025 characters is rejected at construction."""
        with pytest.raises(PydanticValidationError):
            MemoryEntry(**{**_valid_entry_data(), "content": "x" * 1025})

    # --- id UUIDv4 validator ---

    def test_id_non_uuid_string_is_rejected(self) -> None:
        """Error: a non-UUID id string is rejected at construction."""
        with pytest.raises(PydanticValidationError):
            MemoryEntry(**{**_valid_entry_data(), "id": "not-a-uuid"})

    def test_id_uuid_v3_is_rejected(self) -> None:
        """Error: UUIDv3 id is rejected (version 4 required)."""
        uuid_v3 = "a3bb189e-8bf9-3888-9912-ace4e6543002"
        with pytest.raises(PydanticValidationError):
            MemoryEntry(**{**_valid_entry_data(), "id": uuid_v3})

    def test_id_valid_uuid_v4_is_accepted(self) -> None:
        """Happy: a canonical UUIDv4 id is accepted."""
        entry = MemoryEntry(**_valid_entry_data())
        assert entry.id == _VALID_ID

    # --- timezone-aware timestamp validators ---

    def test_timestamps_require_timezone_info(self) -> None:
        """Error: a timezone-naive created_at timestamp is rejected."""
        with pytest.raises(PydanticValidationError):
            MemoryEntry(**{**_valid_entry_data(), "created_at": "2026-01-01T00:00:00"})

    def test_timestamps_must_include_time_component(self) -> None:
        """Error: a date-only updated_at value (no time) is rejected."""
        with pytest.raises(PydanticValidationError):
            MemoryEntry(**{**_valid_entry_data(), "updated_at": "2026-01-01"})

    # --- source_agent frozen ---

    def test_source_agent_is_frozen_after_creation(self) -> None:
        """Error: mutating source_agent after construction raises an error (frozen field)."""
        entry = _make_valid_entry()
        with pytest.raises(PydanticValidationError):
            entry.source_agent = "new-agent"  # type: ignore[misc]

    # --- scope_agents ---

    def test_scope_agents_accepts_empty_list(self) -> None:
        """Edge: scope_agents field accepts an empty list."""
        entry = MemoryEntry(**{**_valid_entry_data(), "scope_agents": []})
        assert entry.scope_agents == []

    def test_scope_agents_accepts_agent_name_list(self) -> None:
        """Happy: scope_agents accepts a non-empty list of agent name strings."""
        agents = ["builder", "reviewer"]
        entry = MemoryEntry(**{**_valid_entry_data(), "scope_agents": agents})
        assert "builder" in entry.scope_agents
        assert "reviewer" in entry.scope_agents


# ---------------------------------------------------------------------------
# AC2: errors.py — NotFoundError, ConcurrencyError, ValidationError, TransitionError
# ---------------------------------------------------------------------------


class TestFromAC_Errors:
    """AC2: errors.py exports 4 distinct Exception subclasses."""

    def test_not_found_error_is_exception_subclass(self) -> None:
        """NotFoundError must subclass Exception."""
        assert issubclass(NotFoundError, Exception)

    def test_concurrency_error_is_exception_subclass(self) -> None:
        """ConcurrencyError must subclass Exception."""
        assert issubclass(ConcurrencyError, Exception)

    def test_validation_error_is_exception_subclass(self) -> None:
        """ValidationError must subclass Exception."""
        assert issubclass(MemValidationError, Exception)

    def test_transition_error_is_exception_subclass(self) -> None:
        """TransitionError must subclass Exception."""
        assert issubclass(TransitionError, Exception)

    def test_error_classes_are_distinct_types(self) -> None:
        """All 4 error classes must be distinct types, not aliases of each other."""
        classes = {NotFoundError, ConcurrencyError, MemValidationError, TransitionError}
        assert len(classes) == 4

    def test_not_found_error_can_be_raised_and_caught_as_exception(self) -> None:
        """NotFoundError can be raised and caught as a plain Exception."""
        msg = "entry not found"
        with pytest.raises(NotFoundError):
            raise NotFoundError(msg)

    def test_concurrency_error_can_be_raised_and_caught_as_exception(self) -> None:
        """ConcurrencyError can be raised and caught as a plain Exception."""
        msg = "concurrent modification"
        with pytest.raises(ConcurrencyError):
            raise ConcurrencyError(msg)

    def test_transition_error_can_be_raised_and_caught_as_exception(self) -> None:
        """TransitionError can be raised and caught as a plain Exception."""
        msg = "invalid state transition"
        with pytest.raises(TransitionError):
            raise TransitionError(msg)


# ---------------------------------------------------------------------------
# AC3: storage.read_entry — lenient reads, symlink/size rejection
# ---------------------------------------------------------------------------


class TestFromAC_StorageRead:
    """AC3: read_entry rejects symlinks and >8KB files, parses YAML, never raises."""

    def test_read_entry_valid_file_returns_memory_entry(self, tmp_path: Path) -> None:
        """Happy: a well-formed markdown+frontmatter file returns a MemoryEntry."""
        entry_file = tmp_path / "entry.md"
        _write_valid_file(entry_file)
        result = storage.read_entry(entry_file)
        assert isinstance(result, MemoryEntry)
        assert result.id == _VALID_ID

    def test_read_entry_content_comes_from_markdown_body(self, tmp_path: Path) -> None:
        """Happy: the content field is taken from the text after the frontmatter delimiter."""
        entry_file = tmp_path / "entry.md"
        _write_valid_file(entry_file, body="Hello from body")
        result = storage.read_entry(entry_file)
        assert result is not None
        assert result.content == "Hello from body"

    def test_read_entry_symlink_returns_none(self, tmp_path: Path) -> None:
        """Error: read_entry returns None for a symlink path (symlink rejected before parsing)."""
        real_file = tmp_path / "real.md"
        _write_valid_file(real_file)
        link = tmp_path / "link.md"
        link.symlink_to(real_file)
        result = storage.read_entry(link)
        assert result is None

    def test_read_entry_file_over_8kb_returns_none(self, tmp_path: Path) -> None:
        """Error: a file with st_size > 8192 bytes returns None."""
        entry_file = tmp_path / "large.md"
        # Pad with 9000 'x' chars in body to push total size well over 8192
        _write_valid_file(entry_file, body="x" * 9000)
        assert entry_file.stat().st_size > _8KB
        result = storage.read_entry(entry_file)
        assert result is None

    def test_read_entry_malformed_yaml_returns_none(self, tmp_path: Path) -> None:
        """Error: a file with malformed YAML frontmatter returns None (lenient)."""
        entry_file = tmp_path / "bad-yaml.md"
        entry_file.write_text(
            "---\n: invalid: yaml: [unbalanced\n---\n\nContent\n",
            encoding="utf-8",
        )
        result = storage.read_entry(entry_file)
        assert result is None

    def test_read_entry_missing_frontmatter_returns_none(self, tmp_path: Path) -> None:
        """Error: a plain markdown file without frontmatter delimiters returns None."""
        entry_file = tmp_path / "no-frontmatter.md"
        entry_file.write_text("No frontmatter here\n", encoding="utf-8")
        result = storage.read_entry(entry_file)
        assert result is None

    def test_read_entry_invalid_pydantic_data_returns_none(self, tmp_path: Path) -> None:
        """Error: valid YAML but data failing Pydantic validation returns None."""
        entry_file = tmp_path / "bad-data.md"
        # id is not a valid UUIDv4
        entry_file.write_text(
            "---\nid: not-a-uuid\ntitle: Bad\ncategories: [domain-knowledge]\n"
            "confidence: 0.9\nstate: pending\nsource_agent: agent\n"
            "created_at: '2026-01-01T00:00:00+00:00'\n"
            "updated_at: '2026-01-01T00:00:00+00:00'\n---\n\nContent\n",
            encoding="utf-8",
        )
        result = storage.read_entry(entry_file)
        assert result is None

    def test_read_entry_never_raises_for_any_malformed_file(self, tmp_path: Path) -> None:
        """Error: read_entry must never raise an exception for malformed file content."""
        bad_files = [
            ("empty.md", ""),
            ("only-dashes.md", "---\n---\n"),
            ("bad-yaml.md", "---\n}{invalid yaml\n---\n\nbody\n"),
            ("missing-required-fields.md", "---\ntitle: Only title\n---\n\nbody\n"),
            ("non-object-frontmatter.md", "---\n- item1\n- item2\n---\n\nbody\n"),
        ]
        for name, content in bad_files:
            f = tmp_path / name
            f.write_text(content, encoding="utf-8")
            try:
                result = storage.read_entry(f)
                assert result is None, f"{name}: expected None for malformed file, got {result!r}"
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"{name}: read_entry raised {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# AC4: storage.write_entry — containment, symlink rejection, atomic write
# ---------------------------------------------------------------------------


class TestFromAC_StorageWrite:
    """AC4: write_entry creates files atomically with containment and symlink guards."""

    def test_write_entry_creates_file_at_path(self, tmp_path: Path) -> None:
        """Happy: write_entry creates the target file on disk."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        target = memory_dir / "entry.md"
        entry = _make_valid_entry()
        storage.write_entry(target, entry, memory_dir=memory_dir)
        assert target.exists()
        assert target.is_file()

    def test_write_entry_produces_file_parseable_by_read_entry(self, tmp_path: Path) -> None:
        """Happy: file written by write_entry is parseable back to a MemoryEntry."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        target = memory_dir / "entry.md"
        entry = _make_valid_entry()
        storage.write_entry(target, entry, memory_dir=memory_dir)
        result = storage.read_entry(target)
        assert result is not None
        assert result.id == entry.id
        assert result.title == entry.title
        assert result.content == entry.content

    def test_write_entry_path_outside_memory_dir_raises(self, tmp_path: Path) -> None:
        """Error: path outside memory_dir raises ValueError (containment assertion)."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside = outside_dir / "entry.md"
        entry = _make_valid_entry()
        with pytest.raises(ValueError):
            storage.write_entry(outside, entry, memory_dir=memory_dir)

    def test_write_entry_path_traversal_raises(self, tmp_path: Path) -> None:
        """Error: path traversal (/../) that escapes memory_dir raises ValueError (containment)."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        # Resolved path escapes memory_dir via ..
        escape = (memory_dir / ".." / "escaped.md").resolve()
        entry = _make_valid_entry()
        with pytest.raises(ValueError):
            storage.write_entry(escape, entry, memory_dir=memory_dir)

    def test_write_entry_symlink_target_raises(self, tmp_path: Path) -> None:
        """Error: writing to a symlink path raises ValueError (symlink rejected)."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        real_target = memory_dir / "real.md"
        real_target.write_text("placeholder", encoding="utf-8")
        link = memory_dir / "link.md"
        link.symlink_to(real_target)
        entry = _make_valid_entry()
        with pytest.raises(ValueError):
            storage.write_entry(link, entry, memory_dir=memory_dir)

    def test_write_entry_invalid_object_raises(self, tmp_path: Path) -> None:
        """Error: passing a non-MemoryEntry object raises PydanticValidationError (strict validation)."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        target = memory_dir / "entry.md"
        with pytest.raises(PydanticValidationError):
            storage.write_entry(target, "not-a-memory-entry", memory_dir=memory_dir)  # type: ignore[arg-type]

    def test_write_entry_uses_mkstemp_and_replace_atomically(self, tmp_path: Path) -> None:
        """AC4: write_entry must use mkstemp to create a temp file, then replace atomically.

        Proves the full mkstemp → fsync → replace contract. Would fail if write_entry
        used write_text() or any non-atomic approach. The temp-file-consumed assertion
        specifically fails when replace is skipped (e.g. direct write leaves temp on disk).
        """
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        target = memory_dir / "entry.md"
        entry = _make_valid_entry()
        _mkstemp_results: list[tuple[int, str]] = []

        def _capturing_mkstemp(*args: object, **kwargs: object) -> tuple[int, str]:
            fd, name = _real_mkstemp(*args, **kwargs)  # type: ignore[arg-type]
            _mkstemp_results.append((fd, name))
            return fd, name

        with (
            patch("owlbear_memory.storage.mkstemp", side_effect=_capturing_mkstemp) as mock_mkstemp,
            patch("os.fsync") as mock_fsync,
        ):
            storage.write_entry(target, entry, memory_dir=memory_dir)
        mock_mkstemp.assert_called_once()
        mock_fsync.assert_called()
        assert target.exists(), "Target file was not created after atomic replace"
        assert len(_mkstemp_results) == 1, "mkstemp capturing function was not called"
        tmp_path_used = Path(_mkstemp_results[0][1])
        assert not tmp_path_used.exists(), "Temp file should be consumed by atomic replace (os.replace/Path.replace)"


# ---------------------------------------------------------------------------
# AC4: storage.delete_entry — containment, symlink rejection, NotFoundError
# ---------------------------------------------------------------------------


class TestFromAC_StorageDelete:
    """AC4: delete_entry removes files and raises NotFoundError for missing paths."""

    def test_delete_entry_removes_file_from_disk(self, tmp_path: Path) -> None:
        """Happy: delete_entry removes the target file so it no longer exists."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        target = memory_dir / "entry.md"
        entry = _make_valid_entry()
        storage.write_entry(target, entry, memory_dir=memory_dir)
        assert target.exists()
        storage.delete_entry(target, memory_dir=memory_dir)
        assert not target.exists()

    def test_delete_entry_nonexistent_file_raises_not_found_error(self, tmp_path: Path) -> None:
        """Error: deleting a nonexistent file raises NotFoundError specifically."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        missing = memory_dir / "missing.md"
        with pytest.raises(NotFoundError):
            storage.delete_entry(missing, memory_dir=memory_dir)

    def test_delete_entry_path_outside_memory_dir_raises(self, tmp_path: Path) -> None:
        """Error: path outside memory_dir raises ValueError on containment check before deletion."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "entry.md"
        outside_file.write_text("placeholder", encoding="utf-8")
        with pytest.raises(ValueError):
            storage.delete_entry(outside_file, memory_dir=memory_dir)

    def test_delete_entry_symlink_raises(self, tmp_path: Path) -> None:
        """Error: deleting a symlink raises ValueError (symlink rejected)."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        real_file = memory_dir / "real.md"
        real_file.write_text("placeholder", encoding="utf-8")
        link = memory_dir / "link.md"
        link.symlink_to(real_file)
        with pytest.raises(ValueError):
            storage.delete_entry(link, memory_dir=memory_dir)
