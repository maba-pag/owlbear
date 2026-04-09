"""Tests for task #531: approve_memory CLI wrapper — MCP transport & AC gaps.

Tests covering AC items not satisfied by approve.py as first implemented:
  AC-T:   Uses create_connected_server_and_client_session (not direct SQL)
  AC-B:   Batch mode prints per-entry confirmation to stdout on success
  AC-IE:  Interactive mode: blank Enter treated as skip (not EOFError crash)
  AC-CR:  Curation report: top-level JSON array format with entry_id key
  AC-MJ:  Malformed curation-report.json → stderr warning + exit 0, not crash
  AC-EL:  Content preview >80 chars ends with "..." truncation marker

All tests FAIL until builder (#531) addresses these AC items.

AC coverage (new items not covered by test_approve_memory_585.py):
  AC-T:   approve.py imports/uses create_connected_server_and_client_session
  AC-B:   batch --approve / --reject print per-entry confirmation to stdout
  AC-IE:  blank Enter in --interactive mode counts as skip, does not crash
  AC-CR:  curation-report.json consumed as top-level JSON array with entry_id key
  AC-MJ:  json.JSONDecodeError from malformed report is caught; warning to stderr
  AC-EL:  content preview is first 80 chars + "...", not bare truncation
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_PACKAGE_DIR = _REPO_ROOT / "serve" / "mcp-memory"
_APPROVE_PY = _PACKAGE_DIR / "src" / "owlbear_mcp_memory" / "approve.py"

# ---------------------------------------------------------------------------
# DDL — mirrors server.py to keep tests self-contained
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL,
    scope_agent TEXT,
    scope_project TEXT,
    approval_state TEXT NOT NULL DEFAULT 'pending',
    deleted_at TEXT
)
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(path: Path, entries: list[dict] | None = None) -> None:
    """Create a SQLite DB with the memory_entries schema and optional rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(_DDL)
    for e in entries or []:
        eid = e.get("id") or str(uuid.uuid4())
        conn.execute(
            """INSERT INTO memory_entries
               (id, content, category, confidence, created_at, updated_at, source,
                scope_agent, scope_project, approval_state, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                eid,
                e.get("content", "test content"),
                e.get("category", "knowledge"),
                e.get("confidence", 0.8),
                e.get("created_at", "2026-01-01T00:00:00+00:00"),
                e.get("updated_at", "2026-01-01T00:00:00+00:00"),
                e.get("source", "test"),
                e.get("scope_agent"),
                e.get("scope_project"),
                e.get("approval_state", "pending"),
                e.get("deleted_at"),
            ),
        )
    conn.commit()
    conn.close()


def _get_state(db: Path, entry_id: str) -> str | None:
    """Return the approval_state for an entry, or None if not found."""
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
    conn.close()
    return row[0] if row else None


def _run_approve(
    *args: str,
    db_path: Path | None = None,
    stdin: str | None = None,
    env_overrides: dict | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run owlbear_mcp_memory.approve as a subprocess."""
    cmd = [sys.executable, "-m", "owlbear_mcp_memory.approve"]
    if db_path is not None:
        cmd.extend(["--db-path", str(db_path)])
    cmd.extend(args)
    run_env = {**os.environ, **(env_overrides or {})}
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=stdin,
        env=run_env,
        cwd=str(cwd or _REPO_ROOT),
    )


# ===========================================================================
# AC-T: MCP transport — approve CLI must use create_connected_server_and_client_session
# ===========================================================================


class TestFromAC_MCPTransport:
    """approve.py must use MCP in-memory transport, not direct SQL for tool calls."""

    def test_approve_imports_create_connected_server_and_client_session(self) -> None:
        """AC-T: approve.py source contains create_connected_server_and_client_session."""
        source = _APPROVE_PY.read_text(encoding="utf-8")
        assert "create_connected_server_and_client_session" in source, (
            "approve.py must import and use create_connected_server_and_client_session "
            "from mcp.shared.memory per AC (MCP in-memory transport, not direct SQL)"
        )

    def test_approve_imports_from_mcp_shared_memory(self) -> None:
        """AC-T: approve.py source imports from mcp.shared.memory."""
        source = _APPROVE_PY.read_text(encoding="utf-8")
        assert "mcp.shared.memory" in source, (
            "approve.py must import from mcp.shared.memory to satisfy the in-memory MCP transport AC requirement"
        )


# ===========================================================================
# AC-B: Batch mode prints per-entry confirmation to stdout on success
# ===========================================================================


class TestFromAC_BatchConfirmation:
    """--approve and --reject print a confirmation message per entry to stdout."""

    def test_batch_approve_prints_confirmation_to_stdout(self, tmp_path: Path) -> None:
        """AC-B: --approve prints a per-entry confirmation line to stdout."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "to approve"}])
        result = _run_approve("--approve", eid, db_path=db)
        assert result.returncode == 0, f"Unexpected non-zero exit: {result.stderr!r}"
        assert result.stdout.strip() != "", "--approve must print a per-entry confirmation to stdout on success"

    def test_batch_reject_prints_confirmation_to_stdout(self, tmp_path: Path) -> None:
        """AC-B: --reject prints a per-entry confirmation line to stdout."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "to reject"}])
        result = _run_approve("--reject", eid, db_path=db)
        assert result.returncode == 0, f"Unexpected non-zero exit: {result.stderr!r}"
        assert result.stdout.strip() != "", "--reject must print a per-entry confirmation to stdout on success"

    def test_batch_approve_confirmation_mentions_entry_id(self, tmp_path: Path) -> None:
        """AC-B: confirmation output contains the short entry ID (first 8 chars)."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "confirm me"}])
        result = _run_approve("--approve", eid, db_path=db)
        assert result.returncode == 0, f"Unexpected non-zero exit: {result.stderr!r}"
        assert eid[:8] in result.stdout, "Per-entry confirmation must mention the entry ID (first 8 chars)"


# ===========================================================================
# AC-IE: Interactive mode — blank Enter treated as skip
# ===========================================================================


class TestFromAC_InteractiveEnterSkip:
    """Blank Enter (empty line, no 's') is treated as skip in interactive mode."""

    def test_interactive_blank_enter_no_crash(self, tmp_path: Path) -> None:
        """AC-IE: blank Enter for one entry does not crash — exits 0."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "skip me via enter key"}])
        result = _run_approve("--interactive", db_path=db, stdin="\n")
        assert result.returncode == 0, (
            f"Blank Enter (empty line) must be treated as skip, not raise EOFError; stderr: {result.stderr!r}"
        )

    def test_interactive_blank_enter_skips_entry_stays_pending(self, tmp_path: Path) -> None:
        """AC-IE: blank Enter leaves entry in pending state (same as 's')."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "should stay pending"}])
        result = _run_approve("--interactive", db_path=db, stdin="\n")
        assert result.returncode == 0, f"Exit code must be 0 after skip-via-Enter; stderr: {result.stderr!r}"
        assert _get_state(db, eid) == "pending", "Entry must remain pending after blank-Enter skip"


# ===========================================================================
# AC-CR / AC-MJ: Curation report format and malformed JSON handling
# ===========================================================================


class TestFromAC_CurationReportFormat:
    """Curation report is a top-level JSON array with entry_id key.

    Malformed JSON triggers stderr warning, not a crash.
    """

    def test_curation_report_top_level_array_works(self, tmp_path: Path) -> None:
        """AC-CR: top-level JSON array curation report is supported without crash."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "array-format entry", "category": "knowledge"}])
        report_path = db.parent / "curation-report.json"
        report = [{"entry_id": eid, "recommendation": "approve", "reason": "high relevance"}]
        report_path.write_text(json.dumps(report), encoding="utf-8")
        result = _run_approve(db_path=db)
        assert result.returncode == 0, (
            f"Curation report as top-level JSON array must not crash the CLI; stderr: {result.stderr!r}"
        )

    def test_curation_report_entry_id_key_used_for_matching(self, tmp_path: Path) -> None:
        """AC-CR: recommendation is matched via 'entry_id' field (not 'id')."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "rec lookup entry", "category": "knowledge"}])
        report_path = db.parent / "curation-report.json"
        # AC format: top-level array, entry_id key
        report = [{"entry_id": eid, "recommendation": "keep-this-visible", "reason": "test"}]
        report_path.write_text(json.dumps(report), encoding="utf-8")
        result = _run_approve(db_path=db)
        assert result.returncode == 0, f"Unexpected crash: {result.stderr!r}"
        assert "keep-this-visible" in result.stdout, (
            "Recommendation from curation-report.json (matched via 'entry_id' key) must appear in the table output"
        )

    def test_malformed_curation_report_prints_warning_to_stderr(self, tmp_path: Path) -> None:
        """AC-MJ: malformed curation-report.json prints a warning to stderr."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "entries still shown"}])
        report_path = db.parent / "curation-report.json"
        report_path.write_text("{ not valid json }", encoding="utf-8")
        result = _run_approve(db_path=db)
        assert result.returncode == 0, (
            f"Malformed curation-report.json must not crash the CLI (exit 0); stderr: {result.stderr!r}"
        )
        assert result.stderr.strip() != "", "Malformed curation-report.json must produce a warning on stderr"

    def test_malformed_curation_report_entries_still_shown(self, tmp_path: Path) -> None:
        """AC-MJ: pending entries are still listed when curation-report.json is malformed."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "visible entry"}])
        report_path = db.parent / "curation-report.json"
        report_path.write_text("[ invalid }", encoding="utf-8")
        result = _run_approve(db_path=db)
        assert result.returncode == 0, f"Unexpected crash: {result.stderr!r}"
        assert eid[:8] in result.stdout, "Entries must still be displayed when curation-report.json is malformed"


# ===========================================================================
# AC-EL: Content preview ends with "..." when truncated at 80 chars
# ===========================================================================


class TestFromAC_ContentEllipsis:
    """Content preview of >80 chars must end with '...' (truncation marker)."""

    def test_content_preview_ends_with_ellipsis_when_truncated(self, tmp_path: Path) -> None:
        """AC-EL: content >80 chars: preview ends with '...' in table output."""
        long_content = "x" * 120
        db = tmp_path / "test.db"
        _make_db(db, [{"content": long_content}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0, f"Unexpected non-zero exit: {result.stderr!r}"
        assert ("x" * 80) + "..." in result.stdout, (
            "Content >80 chars must be truncated to 80 chars followed by '...' in table"
        )

    def test_content_preview_exactly_80_chars_plus_ellipsis(self, tmp_path: Path) -> None:
        """AC-EL boundary: 81-char content is truncated to 80 chars + '...'."""
        content_80 = "a" * 80
        content_81 = content_80 + "z"  # just over the 80-char limit
        db = tmp_path / "test.db"
        _make_db(db, [{"content": content_81}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0, f"Unexpected non-zero exit: {result.stderr!r}"
        assert content_80 + "..." in result.stdout, (
            "81-char content must be truncated to 80 chars + '...' (boundary case)"
        )
