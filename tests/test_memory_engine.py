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

from owlbear_memory_mcp.engine import MemoryEngine
from owlbear_memory_mcp.models import MemoryEntry

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

import pytest

from owlbear_memory_mcp.engine import MemoryEngine
from owlbear_memory_mcp.models import MemoryEntry

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
