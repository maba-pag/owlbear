"""Protect warning diagnostics for malformed memory files."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from owlbear_memory_mcp.engine import MemoryEngine

# Mined from #1270: malformed files are skipped without raising.
# Mined from #1271: malformed files emit warning diagnostics.


# ---------------------------------------------------------------------------
# Malformed file diagnostics
# ---------------------------------------------------------------------------


class TestMalformedMemoryLogging:
    """load() emits a warning for each malformed file it skips."""

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
        assert len(caplog.records) >= 1, (
            f"Expected at least one WARNING log for empty YAML frontmatter; got {caplog.records!r}"
        )
