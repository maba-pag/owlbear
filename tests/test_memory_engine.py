from __future__ import annotations

# --- merged from tests/test_memory_engine_1270.py ---
"""Failing tests for MemoryEngine malformed-file handling — task #1270.

Covers AC: malformed-file test — entries with invalid YAML syntax or missing
required fields must be skipped without raising an exception.

All 4 tests FAIL (RED phase): _load_file() propagates yaml.YAMLError and
pydantic.ValidationError instead of catching and skipping them.

Note: round-trip, slug, cache hit/miss, and empty-dir behaviors are already
implemented on parent task #1266 (tests_mcp_memory_1266.py) and would pass
— excluded here per RED-phase rules (no tests for existing behavior).
"""


from pathlib import Path

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry

_VALID_UUID = "b3c2c30f-1e2f-4a3b-97d6-1234567890ab"
_TS_1271 = "2026-05-02T10:00:00+00:00"


def _make_valid_entry(**kwargs: object) -> MemoryEntry:
    return MemoryEntry(
        id=_VALID_UUID,
        title="Valid Entry",
        categories=["knowledge"],
        confidence=0.9,
        state="pending",
        content="Valid content.",
        created_at=_TS,
        updated_at=_TS,
        **kwargs,
    )


class TestFromAC_FileEngine:
    """Contract tests for MemoryEngine malformed-file handling.

    AC: 'Malformed file test: invalid YAML → entry skipped, no exception raised'
    Scope: 'Handle malformed files gracefully (skip with warning, don't crash)'
    """

    def test_invalid_yaml_syntax_in_frontmatter_skipped(self, tmp_path: Path) -> None:
        """File with invalid YAML syntax in frontmatter is skipped; load() returns []."""
        malformed = tmp_path / "bad-entry-aabb11.md"
        malformed.write_text(
            "---\nkey: {unclosed bracket\n---\n\nsome body\n",
            encoding="utf-8",
        )
        engine = MemoryEngine(tmp_path)
        # Should skip malformed file, not raise yaml.YAMLError
        entries = engine.load()
        assert entries == []

    def test_missing_required_fields_skipped(self, tmp_path: Path) -> None:
        """File with valid YAML but missing required MemoryEntry fields is skipped."""
        partial = tmp_path / "partial-entry-cc2211.md"
        # Valid YAML, but no id / categories / confidence / created_at / updated_at
        partial.write_text(
            "---\ntitle: Some Title\n---\n\nsome body\n",
            encoding="utf-8",
        )
        engine = MemoryEngine(tmp_path)
        # Should skip the entry, not raise pydantic.ValidationError
        entries = engine.load()
        assert entries == []

    def test_empty_frontmatter_skipped(self, tmp_path: Path) -> None:
        """File with empty YAML frontmatter block (parses as None) is skipped."""
        empty_fm = tmp_path / "empty-front-dd3322.md"
        empty_fm.write_text("---\n\n---\n\nsome body\n", encoding="utf-8")
        engine = MemoryEngine(tmp_path)
        # yaml.safe_load("") → None → data={} → MemoryEntry(**{}) raises ValidationError
        entries = engine.load()
        assert entries == []

    def test_valid_entries_alongside_malformed_file_still_returned(self, tmp_path: Path) -> None:
        """Valid entries are returned even when a malformed file exists in the dir."""
        engine = MemoryEngine(tmp_path)

        # Write a valid entry via the engine
        valid_entry = _make_valid_entry()
        engine.write(valid_entry)

        # Inject a malformed file alongside the valid one
        bad = tmp_path / "bad-entry-ee4433.md"
        bad.write_text(
            "---\nkey: {unclosed\n---\n\nbody\n",
            encoding="utf-8",
        )

        # load() should skip the malformed file and return only the valid entry
        entries = engine.load()
        assert len(entries) == 1
        assert entries[0].id == _VALID_UUID

    def test_non_mapping_yaml_frontmatter_skipped(self, tmp_path: Path) -> None:
        """File whose YAML frontmatter is a list or scalar (not a dict) is skipped.

        yaml.safe_load("- item") → ["item"] (truthy non-dict).
        The `or {}` fallback is NOT triggered, so data["content"] raises TypeError.
        AC: non-mapping YAML frontmatter → entry skipped, no exception raised.
        """
        list_fm = tmp_path / "list-front-ff5544.md"
        list_fm.write_text(
            "---\n- list item\n- another item\n---\n\nsome body\n",
            encoding="utf-8",
        )
        engine = MemoryEngine(tmp_path)
        # Should skip the non-dict frontmatter, not raise TypeError
        entries = engine.load()
        assert entries == []


# --- merged from tests/test_memory_engine_1271.py ---
"""Failing tests for MemoryEngine atomic-write, slug generation, and malformed-file
logging — task #1271.

Covers AC lines not addressed by #1266 or #1270 tests:
  AC: "Atomic writes use mkstemp → fsync → rename pattern"
  AC: "Slug is deterministic for same title (excluding random suffix)"
      (corollary: suffix must NOT be derived from entry.id)
  AC: "Malformed files logged and skipped without raising"
      (the #1270 tests verify 'skipped without raising'; these verify 'logged')

All 5 tests FAIL (RED phase):
  - write() does not call os.fsync (uses write_text + replace)
  - write() uses entry.id[:6] as filename suffix, not a random 6-char token
  - _load_file() silently returns None on error — no logging at any level
"""


import logging
from pathlib import Path
from tempfile import mkstemp as _real_mkstemp
from unittest.mock import patch

import pytest

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry

_TS = "2026-05-02T10:00:00+00:00"


def _make_entry(**kwargs: object) -> MemoryEntry:
    defaults: dict[str, object] = {
        "id": "b3c2c30f-1e2f-4a3b-97d6-1234567890ab",
        "title": "Test Entry Title",
        "categories": ["knowledge"],
        "confidence": 0.8,
        "state": "pending",
        "content": "Test content.",
        "scope_agents": None,
        "created_at": _TS_1271,
        "updated_at": _TS_1271,
    }
    defaults.update(kwargs)
    return MemoryEntry(**defaults)


# ---------------------------------------------------------------------------
# AC: Atomic writes use mkstemp → fsync → rename pattern
# ---------------------------------------------------------------------------


class TestFromAC_AtomicWrite:
    """Atomic write contract: mkstemp → fsync → rename.

    The current write() calls write_text() then replace() — no os.fsync,
    no mkstemp.  Both tests below FAIL against the current implementation.
    """

    def test_write_calls_os_fsync(self, tmp_path: Path) -> None:
        """write() must call os.fsync() to flush data to disk before rename.

        FAILS: current write() never calls os.fsync.
        """
        engine = MemoryEngine(tmp_path)
        entry = _make_entry()
        with patch("os.fsync") as mock_fsync:
            engine.write(entry)
        # Verify at least one fsync call occurred during write
        mock_fsync.assert_called()

    def test_write_uses_mkstemp_and_rename(self, tmp_path: Path) -> None:
        """write() must use mkstemp to create a temp file, then rename atomically.

        Proves the full mkstemp → fsync → rename contract, not just fsync.
        """
        engine = MemoryEngine(tmp_path)
        entry = _make_entry()
        with (
            patch("owlbear_mcp_memory.engine.mkstemp", wraps=_real_mkstemp) as mock_mkstemp,
            patch("os.fsync") as mock_fsync,
        ):
            path = engine.write(entry)
        mock_mkstemp.assert_called_once()
        mock_fsync.assert_called()
        assert path.exists(), "Target file was not created after rename"
        assert path.suffix == ".md"


# ---------------------------------------------------------------------------
# AC: Slug is deterministic for same title (excluding random suffix)
#     Corollary: the 6-char suffix must NOT be entry.id[:6]
# ---------------------------------------------------------------------------


class TestFromAC_SlugGeneration:
    """Slug suffix must be a random alphanumeric token, not derived from entry.id.

    Current code: `f"{slug}-{entry.id[:6]}.md"` — the suffix IS the ID prefix.
    AC requires a random 6-char alphanumeric suffix so that:
      - Two entries with the same title do not collide.
      - The suffix cannot be guessed from the entry's metadata.
    """

    def test_slug_suffix_is_not_derived_from_entry_id(self, tmp_path: Path) -> None:
        """The filename suffix must not equal the first 6 chars of entry.id.

        Uses a distinctive all-zero ID prefix so the assertion is deterministic.

        FAILS: current write() uses entry.id[:6] = '000000' as the suffix.
        """
        # Version nibble must be '4' for UUIDv4; variant nibble must be '8'-'b'.
        # First 8 hex chars are all-zero so entry.id[:6] = '000000'.
        distinctive_id = "00000000-0000-4000-8000-000000000000"
        engine = MemoryEngine(tmp_path)
        entry = _make_entry(id=distinctive_id)
        path = engine.write(entry)
        # Current code produces e.g. "test-entry-title-000000.md"
        # After the fix, suffix must be a random token — NOT "000000"
        assert "000000" not in path.stem, f"Slug suffix must not be derived from entry.id[:6]; got: {path.stem}"

    def test_same_title_yields_same_slug_prefix(self, tmp_path: Path) -> None:
        """Two entries with identical titles must share the same slug base prefix.

        AC: "Slug is deterministic for same title (excluding random suffix)".
        Two separate writes with the same title must produce the same leading slug
        so that the only difference is the random suffix.
        """
        engine = MemoryEngine(tmp_path)
        entry_a = _make_entry(
            id="aaaa0001-0000-4000-8000-000000000001",
            title="Determinism Proof Title",
        )
        entry_b = _make_entry(
            id="bbbb0002-0000-4000-8000-000000000002",
            title="Determinism Proof Title",
        )
        path_a = engine.write(entry_a)
        path_b = engine.write(entry_b)
        # Stem format: "<slug-base>-<6-char-suffix>"
        base_a = path_a.stem.rsplit("-", 1)[0]
        base_b = path_b.stem.rsplit("-", 1)[0]
        assert base_a == base_b, f"Slug base differs for same title: {path_a.stem!r} vs {path_b.stem!r}"
        suffix_a = path_a.stem.rsplit("-", 1)[-1]
        suffix_b = path_b.stem.rsplit("-", 1)[-1]
        assert len(suffix_a) == 6, f"Suffix length unexpected: {suffix_a!r}"
        assert len(suffix_b) == 6, f"Suffix length unexpected: {suffix_b!r}"


# ---------------------------------------------------------------------------
# AC: Malformed files logged (not just silently skipped)
# ---------------------------------------------------------------------------


class TestFromAC_MalformedLogging:
    """load() must emit a WARNING-level log for each malformed file it skips.

    The #1270 tests verify that load() returns [] and does not raise.
    These tests verify the 'logged' requirement, which is not yet implemented:
    _load_file() currently returns None silently with no log output.

    All three tests FAIL: caplog records are empty after load().
    """

    def test_invalid_yaml_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """A file with invalid YAML syntax must emit a WARNING log when skipped."""
        malformed = tmp_path / "bad-entry-aa1122.md"
        malformed.write_text(
            "---\nkey: {unclosed bracket\n---\n\nsome body\n",
            encoding="utf-8",
        )
        engine = MemoryEngine(tmp_path)
        with caplog.at_level(logging.WARNING):
            engine.load()
        # FAILS: _load_file() catches yaml.YAMLError and returns None — no log
        assert len(caplog.records) >= 1, (
            f"Expected at least one WARNING log for invalid YAML frontmatter; got {caplog.records!r}"
        )

    def test_missing_required_fields_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """A file with missing required MemoryEntry fields must emit a WARNING log."""
        partial = tmp_path / "partial-entry-bb2233.md"
        partial.write_text(
            "---\ntitle: Some Title\n---\n\nsome body\n",
            encoding="utf-8",
        )
        engine = MemoryEngine(tmp_path)
        with caplog.at_level(logging.WARNING):
            engine.load()
        # FAILS: _load_file() catches ValidationError and returns None — no log
        assert len(caplog.records) >= 1, (
            f"Expected at least one WARNING log for missing required fields; got {caplog.records!r}"
        )

    def test_empty_frontmatter_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """A file with an empty YAML frontmatter block must emit a WARNING log."""
        empty_fm = tmp_path / "empty-front-cc3344.md"
        empty_fm.write_text("---\n\n---\n\nsome body\n", encoding="utf-8")
        engine = MemoryEngine(tmp_path)
        with caplog.at_level(logging.WARNING):
            engine.load()
        # FAILS: empty YAML → safe_load returns None → {} fallback → ValidationError →
        # returns None — no log
        assert len(caplog.records) >= 1, (
            f"Expected at least one WARNING log for empty YAML frontmatter; got {caplog.records!r}"
        )


# ---------------------------------------------------------------------------
# AC: Directory auto-created on first write
# ---------------------------------------------------------------------------


class TestFromAC_DirectoryAutoCreation:
    """MemoryEngine must create the memory directory if it does not exist.

    AC: "Create .owlbear/memory/ on first write if missing"
    All #1266 and #1270 tests instantiate with an existing tmp_path directory.
    These tests exercise the missing-directory code path explicitly.
    """

    def test_directory_created_on_engine_init(self, tmp_path: Path) -> None:
        """MemoryEngine creates memory_dir on instantiation when it does not exist."""
        nonexistent = tmp_path / "new_memory" / "nested"
        assert not nonexistent.exists()
        MemoryEngine(nonexistent)
        assert nonexistent.exists(), "MemoryEngine did not create memory_dir on instantiation"

    def test_write_succeeds_to_auto_created_directory(self, tmp_path: Path) -> None:
        """write() succeeds when memory_dir did not exist before engine init."""
        nonexistent = tmp_path / "auto_created"
        assert not nonexistent.exists()
        engine = MemoryEngine(nonexistent)
        entry = _make_entry()
        written_path = engine.write(entry)
        assert written_path.parent == nonexistent
        assert written_path.exists()
        assert written_path.suffix == ".md"
