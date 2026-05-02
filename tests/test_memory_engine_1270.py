"""Failing tests for MemoryEngine malformed-file handling — task #1270.

Covers AC: malformed-file test — entries with invalid YAML syntax or missing
required fields must be skipped without raising an exception.

All 4 tests FAIL (RED phase): _load_file() propagates yaml.YAMLError and
pydantic.ValidationError instead of catching and skipping them.

Note: round-trip, slug, cache hit/miss, and empty-dir behaviors are already
implemented on parent task #1266 (tests_mcp_memory_1266.py) and would pass
— excluded here per RED-phase rules (no tests for existing behavior).
"""

from __future__ import annotations

from pathlib import Path

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry

_VALID_UUID = "b3c2c30f-1e2f-4a3b-97d6-1234567890ab"
_TS = "2026-05-02T10:00:00+00:00"


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

    def test_invalid_yaml_syntax_in_frontmatter_skipped(
        self, tmp_path: Path
    ) -> None:
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

    def test_valid_entries_alongside_malformed_file_still_returned(
        self, tmp_path: Path
    ) -> None:
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
