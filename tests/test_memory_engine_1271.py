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

from __future__ import annotations

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
        "created_at": _TS,
        "updated_at": _TS,
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
            patch(
                "owlbear_mcp_memory.engine.mkstemp", wraps=_real_mkstemp
            ) as mock_mkstemp,
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
        assert "000000" not in path.stem, (
            f"Slug suffix must not be derived from entry.id[:6]; got: {path.stem}"
        )

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
        assert base_a == base_b, (
            f"Slug base differs for same title: {path_a.stem!r} vs {path_b.stem!r}"
        )
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

    def test_invalid_yaml_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
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
            "Expected at least one WARNING log for invalid YAML frontmatter; "
            f"got {caplog.records!r}"
        )

    def test_missing_required_fields_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
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
            "Expected at least one WARNING log for missing required fields; "
            f"got {caplog.records!r}"
        )

    def test_empty_frontmatter_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A file with an empty YAML frontmatter block must emit a WARNING log."""
        empty_fm = tmp_path / "empty-front-cc3344.md"
        empty_fm.write_text("---\n\n---\n\nsome body\n", encoding="utf-8")
        engine = MemoryEngine(tmp_path)
        with caplog.at_level(logging.WARNING):
            engine.load()
        # FAILS: empty YAML → safe_load returns None → {} fallback → ValidationError →
        # returns None — no log
        assert len(caplog.records) >= 1, (
            "Expected at least one WARNING log for empty YAML frontmatter; "
            f"got {caplog.records!r}"
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
        assert nonexistent.exists(), (
            "MemoryEngine did not create memory_dir on instantiation"
        )

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
