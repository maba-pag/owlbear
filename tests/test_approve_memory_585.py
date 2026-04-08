"""Tests for task #585: approve_memory CLI wrapper (TDD RED phase).

Contract-level tests for owlbear_mcp_memory.approve CLI tool that manages
pending memory entries via approve/reject/skip workflow.

All tests FAIL in RED phase — ImportError expected until builder creates
owlbear_mcp_memory/approve.py (#531).

AC coverage:
  AC1:  Import: from owlbear_mcp_memory.approve import main
  AC2:  --interactive, --approve, --reject mutually exclusive (argparse error)
  AC3:  --db-path resolution: CLI arg > OWLBEAR_MEMORY_DB_PATH env var > default
  AC4:  Bare invocation: lists pending entries as numbered table, exits 0
  AC5:  Interactive mode: approve/reject/skip choices call set_approval_state correctly
  AC6:  Interactive mode: summary line (N approved, N rejected, N skipped)
  AC7:  Batch --approve: calls set_approval_state with new_state=approved per ID
  AC8:  Batch --reject: calls set_approval_state with new_state=deleted per ID
  AC9:  Error path A: ToolError on nonexistent ID → stderr, continues to next entry
  AC10: Error path B: error-prefixed string on disallowed transition → stderr, continues
  AC11: Curation report present: recommendation column shown in table
  AC12: Curation report absent: warning to stderr, table without recommendation, no crash
  AC13: MCP integration: in-memory transport list_entries + set_approval_state roundtrip
  AC14: Exit code 0 on full success
  AC15: Exit code 1 if any operation failed
  AC16: main(argv: list[str] | None = None) -> int signature
"""

from __future__ import annotations

import inspect
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

# ---------------------------------------------------------------------------
# Import under test — will raise ImportError in RED phase (module not exists)
# ---------------------------------------------------------------------------
from owlbear_mcp_memory.approve import main  # type: ignore[import]
from owlbear_mcp_memory.server import AppContext
from owlbear_mcp_memory.tools import list_entries, set_approval_state

pytestmark = pytest.mark.slow

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

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
    row = conn.execute(
        "SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)
    ).fetchone()
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
# AC1 + AC16: Module exists, importable, main signature
# ===========================================================================


class TestFromAC_ModuleImport:
    """approve.py exists, is importable, and exposes main with correct signature."""

    def test_approve_py_file_exists(self) -> None:
        """AC1: approve.py is present at the expected path."""
        assert _APPROVE_PY.is_file(), f"approve.py not found at {_APPROVE_PY}"

    def test_module_importable(self) -> None:
        """AC1: module is importable as owlbear_mcp_memory.approve."""
        import owlbear_mcp_memory.approve  # noqa: F401

    def test_main_signature_argv_none_default(self) -> None:
        """AC16: main accepts argv with default None."""
        sig = inspect.signature(main)
        assert "argv" in sig.parameters, "main must have an 'argv' parameter"
        assert sig.parameters["argv"].default is None, (
            "argv default must be None (None means read sys.argv)"
        )

    def test_main_return_annotation_is_int(self) -> None:
        """AC16: main return annotation is int."""
        sig = inspect.signature(main)
        ret = sig.return_annotation
        assert ret is int or ret == "int", (
            f"main return annotation must be int, got {ret!r}"
        )

    def test_main_is_callable(self) -> None:
        """AC1: main is callable after import."""
        assert callable(main), "main must be callable"


# ===========================================================================
# AC2: --interactive, --approve, --reject mutually exclusive
# ===========================================================================


class TestFromAC_CLIMutualExclusion:
    """--interactive, --approve, and --reject are mutually exclusive."""

    def test_interactive_and_approve_together_is_error(self, tmp_path: Path) -> None:
        """AC2: --interactive + --approve together causes argparse error (exit != 0)."""
        db = tmp_path / "test.db"
        _make_db(db)
        eid = str(uuid.uuid4())
        result = _run_approve("--interactive", "--approve", eid, db_path=db)
        assert result.returncode != 0, (
            "--interactive and --approve together should exit non-zero (argparse error)"
        )

    def test_interactive_and_reject_together_is_error(self, tmp_path: Path) -> None:
        """AC2: --interactive + --reject together causes argparse error (exit != 0)."""
        db = tmp_path / "test.db"
        _make_db(db)
        eid = str(uuid.uuid4())
        result = _run_approve("--interactive", "--reject", eid, db_path=db)
        assert result.returncode != 0, (
            "--interactive and --reject together should exit non-zero (argparse error)"
        )

    def test_approve_and_reject_together_is_error(self, tmp_path: Path) -> None:
        """AC2: --approve + --reject together causes argparse error (exit != 0)."""
        db = tmp_path / "test.db"
        _make_db(db)
        eid = str(uuid.uuid4())
        result = _run_approve("--approve", eid, "--reject", eid, db_path=db)
        assert result.returncode != 0, (
            "--approve and --reject together should exit non-zero (argparse error)"
        )

    def test_mutual_exclusion_error_goes_to_stderr(self, tmp_path: Path) -> None:
        """AC2: argparse writes the mutual-exclusion error to stderr."""
        db = tmp_path / "test.db"
        _make_db(db)
        eid = str(uuid.uuid4())
        result = _run_approve("--interactive", "--approve", eid, db_path=db)
        assert result.stderr.strip() != "", (
            "Mutual exclusion error must be printed to stderr"
        )


# ===========================================================================
# AC3: --db-path resolution order: CLI arg > env var > default
# ===========================================================================


class TestFromAC_DBPathResolution:
    """DB path resolves in order: CLI --db-path, then env var, then default."""

    def test_cli_arg_db_path_used(self, tmp_path: Path) -> None:
        """AC3: --db-path CLI arg takes precedence over env var and default."""
        eid = str(uuid.uuid4())
        cli_db = tmp_path / "cli.db"
        env_db = tmp_path / "env.db"
        _make_db(cli_db, [{"id": eid, "content": "cli-entry"}])
        _make_db(env_db)  # empty
        result = _run_approve(
            db_path=cli_db,
            env_overrides={"OWLBEAR_MEMORY_DB_PATH": str(env_db)},
        )
        assert result.returncode == 0
        # The CLI-arg DB has one entry, env DB is empty —
        # output should contain the cli-entry content
        assert eid[:8] in result.stdout, (
            "Bare invocation should display entry from --db-path, not env var DB"
        )

    def test_env_var_db_path_used_when_no_cli_arg(self, tmp_path: Path) -> None:
        """AC3: OWLBEAR_MEMORY_DB_PATH env var is used when --db-path is absent."""
        eid = str(uuid.uuid4())
        env_db = tmp_path / "env.db"
        _make_db(env_db, [{"id": eid, "content": "env-entry"}])
        result = _run_approve(
            env_overrides={"OWLBEAR_MEMORY_DB_PATH": str(env_db)},
        )
        assert result.returncode == 0
        assert eid[:8] in result.stdout, (
            "Bare invocation should use env DB when no --db-path is given"
        )

    def test_default_db_path_is_data_memory_memory_db(self, tmp_path: Path) -> None:
        """AC3: default DB path is data/memory/memory.db (relative to cwd)."""
        default_db = tmp_path / "data" / "memory" / "memory.db"
        eid = str(uuid.uuid4())
        _make_db(default_db, [{"id": eid, "content": "default-entry"}])
        # Run with no --db-path and no env var, cwd=tmp_path so the default
        # path resolves to tmp_path/data/memory/memory.db
        result = _run_approve(env_overrides={"OWLBEAR_MEMORY_DB_PATH": ""}, cwd=tmp_path)
        assert result.returncode == 0
        assert eid[:8] in result.stdout, (
            "Bare invocation should fall back to data/memory/memory.db default"
        )


# ===========================================================================
# AC4: Bare invocation lists pending entries as numbered table, exits 0
# ===========================================================================


class TestFromAC_BareInvocation:
    """Bare invocation (no flags) lists pending entries and exits 0."""

    def test_bare_invocation_exits_0(self, tmp_path: Path) -> None:
        """AC4: bare invocation with empty DB exits 0."""
        db = tmp_path / "test.db"
        _make_db(db)
        result = _run_approve(db_path=db)
        assert result.returncode == 0, f"Bare invocation should exit 0; got {result.returncode}"

    def test_bare_invocation_shows_truncated_id(self, tmp_path: Path) -> None:
        """AC4: table row contains first 8 chars of entry ID."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "some content here"}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        assert eid[:8] in result.stdout, (
            f"First 8 chars of ID ({eid[:8]!r}) must appear in table output"
        )

    def test_bare_invocation_shows_category(self, tmp_path: Path) -> None:
        """AC4: table row contains entry category."""
        db = tmp_path / "test.db"
        _make_db(db, [{"content": "entry", "category": "behavior"}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        assert "behavior" in result.stdout, "Category must appear in table output"

    def test_bare_invocation_shows_content_preview(self, tmp_path: Path) -> None:
        """AC4: table row contains first 80 chars of content."""
        long_content = "x" * 120
        db = tmp_path / "test.db"
        _make_db(db, [{"content": long_content}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        preview = long_content[:80]
        assert preview in result.stdout, (
            "First 80 chars of content must appear in table output"
        )

    def test_bare_invocation_content_truncated_at_80(self, tmp_path: Path) -> None:
        """AC4: content preview is truncated to 80 chars (full 120-char string absent)."""
        long_content = "a" * 120
        db = tmp_path / "test.db"
        _make_db(db, [{"content": long_content}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        assert long_content not in result.stdout, (
            "Full 120-char content must NOT appear; table shows only first 80 chars"
        )

    def test_bare_invocation_row_has_numeric_index(self, tmp_path: Path) -> None:
        """AC4: table rows are numbered starting from 1."""
        db = tmp_path / "test.db"
        _make_db(db, [{"content": "first"}, {"content": "second"}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        assert "1" in result.stdout, "Table must have a numeric index column starting at 1"
        assert "2" in result.stdout, "Second row must be labeled 2"

    def test_bare_invocation_only_shows_pending_entries(self, tmp_path: Path) -> None:
        """AC4: bare invocation shows only pending entries, not approved/deleted."""
        pending_eid = str(uuid.uuid4())
        approved_eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [
            {"id": pending_eid, "content": "pending entry", "approval_state": "pending"},
            {"id": approved_eid, "content": "approved entry", "approval_state": "approved"},
        ])
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        assert pending_eid[:8] in result.stdout, "Pending entry must be shown"
        assert approved_eid[:8] not in result.stdout, (
            "Approved entry must NOT appear in bare invocation (only pending)"
        )


# ===========================================================================
# AC5 + AC6: Interactive mode — approve/reject/skip, summary line
# ===========================================================================


class TestFromAC_InteractiveMode:
    """Interactive mode prompts the user and processes each entry, prints a summary."""

    def test_interactive_approve_choice_sets_approved(self, tmp_path: Path) -> None:
        """AC5: 'a' input in interactive mode calls set_approval_state(new_state=approved)."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "approve me"}])
        result = _run_approve("--interactive", db_path=db, stdin="a\n")
        assert result.returncode == 0, f"--interactive with approve should exit 0: {result.stderr}"
        assert _get_state(db, eid) == "approved", (
            "'a' choice must result in approval_state=approved in DB"
        )

    def test_interactive_reject_choice_sets_deleted(self, tmp_path: Path) -> None:
        """AC5: 'r' input in interactive mode calls set_approval_state(new_state=deleted)."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "reject me"}])
        result = _run_approve("--interactive", db_path=db, stdin="r\n")
        assert result.returncode == 0, f"--interactive with reject should exit 0: {result.stderr}"
        assert _get_state(db, eid) == "deleted", (
            "'r' choice must result in approval_state=deleted in DB"
        )

    def test_interactive_skip_choice_leaves_pending(self, tmp_path: Path) -> None:
        """AC5: 's' input in interactive mode skips the entry (no state change)."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "skip me"}])
        result = _run_approve("--interactive", db_path=db, stdin="s\n")
        assert result.returncode == 0
        assert _get_state(db, eid) == "pending", (
            "'s' choice must leave approval_state=pending (no change)"
        )

    def test_interactive_processes_all_entries_in_sequence(self, tmp_path: Path) -> None:
        """AC5: interactive mode processes each pending entry in sequence."""
        eids = [str(uuid.uuid4()) for _ in range(3)]
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": f"entry {i}"} for i, eid in enumerate(eids)])
        # approve, reject, skip for 3 entries
        result = _run_approve("--interactive", db_path=db, stdin="a\nr\ns\n")
        assert result.returncode == 0
        assert _get_state(db, eids[0]) == "approved"
        assert _get_state(db, eids[1]) == "deleted"
        assert _get_state(db, eids[2]) == "pending"

    def test_interactive_summary_approved_count(self, tmp_path: Path) -> None:
        """AC6: interactive mode prints the count of approved entries in summary."""
        db = tmp_path / "test.db"
        _make_db(db, [{"content": "e1"}, {"content": "e2"}, {"content": "e3"}])
        result = _run_approve("--interactive", db_path=db, stdin="a\na\ns\n")
        assert result.returncode == 0
        # Summary must mention 2 approved entries
        output = result.stdout.lower()
        assert "2" in output, "Summary must contain the count 2"
        assert "approved" in output, "Summary must show number of approved entries"

    def test_interactive_summary_rejected_count(self, tmp_path: Path) -> None:
        """AC6: interactive mode prints the count of rejected entries in summary."""
        db = tmp_path / "test.db"
        _make_db(db, [{"content": "e1"}, {"content": "e2"}])
        result = _run_approve("--interactive", db_path=db, stdin="r\na\n")
        assert result.returncode == 0
        output = result.stdout.lower()
        assert "1" in output, "Summary must contain the count 1"
        assert "rejected" in output, "Summary must show number of rejected entries"

    def test_interactive_summary_skipped_count(self, tmp_path: Path) -> None:
        """AC6: interactive mode prints the count of skipped entries in summary."""
        db = tmp_path / "test.db"
        _make_db(db, [{"content": "e1"}, {"content": "e2"}])
        result = _run_approve("--interactive", db_path=db, stdin="s\ns\n")
        assert result.returncode == 0
        output = result.stdout.lower()
        assert "2" in output, "Summary must contain the count 2"
        assert "skipped" in output, "Summary must show number of skipped entries"

    def test_interactive_summary_present_after_all_entries(self, tmp_path: Path) -> None:
        """AC6: summary line is printed after all entries are processed."""
        db = tmp_path / "test.db"
        _make_db(db, [{"content": "only entry"}])
        result = _run_approve("--interactive", db_path=db, stdin="a\n")
        assert result.returncode == 0
        # Summary must appear in stdout
        assert "approved" in result.stdout.lower(), (
            "Summary must be present after all entries are processed"
        )


# ===========================================================================
# AC7 + AC8: Batch --approve and --reject
# ===========================================================================


class TestFromAC_BatchMode:
    """--approve and --reject flags process IDs in batch without prompting."""

    def test_batch_approve_sets_approved_state(self, tmp_path: Path) -> None:
        """AC7: --approve <id> sets approval_state=approved in the DB."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "to approve"}])
        result = _run_approve("--approve", eid, db_path=db)
        assert result.returncode == 0
        assert _get_state(db, eid) == "approved", (
            "--approve must set approval_state=approved"
        )

    def test_batch_approve_multiple_ids(self, tmp_path: Path) -> None:
        """AC7: --approve accepts multiple IDs and approves each one."""
        eids = [str(uuid.uuid4()) for _ in range(3)]
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": f"entry {i}"} for i, eid in enumerate(eids)])
        result = _run_approve("--approve", *eids, db_path=db)
        assert result.returncode == 0
        for eid in eids:
            assert _get_state(db, eid) == "approved", (
                f"Entry {eid[:8]} must be approved after --approve"
            )

    def test_batch_reject_sets_deleted_state(self, tmp_path: Path) -> None:
        """AC8: --reject <id> sets approval_state=deleted in the DB."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "to reject"}])
        result = _run_approve("--reject", eid, db_path=db)
        assert result.returncode == 0
        assert _get_state(db, eid) == "deleted", (
            "--reject must set approval_state=deleted"
        )

    def test_batch_reject_multiple_ids(self, tmp_path: Path) -> None:
        """AC8: --reject accepts multiple IDs and deletes each one."""
        eids = [str(uuid.uuid4()) for _ in range(2)]
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": f"entry {i}"} for i, eid in enumerate(eids)])
        result = _run_approve("--reject", *eids, db_path=db)
        assert result.returncode == 0
        for eid in eids:
            assert _get_state(db, eid) == "deleted", (
                f"Entry {eid[:8]} must be deleted after --reject"
            )


# ===========================================================================
# AC9 + AC10: Error handling — ToolError and error-prefixed string
# ===========================================================================


class TestFromAC_ErrorHandling:
    """Error paths print to stderr and continue processing remaining entries."""

    def test_error_path_a_nonexistent_id_printed_to_stderr(self, tmp_path: Path) -> None:
        """AC9: ToolError for nonexistent entry is printed to stderr."""
        nonexistent_id = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db)  # empty DB — no entries
        result = _run_approve("--approve", nonexistent_id, db_path=db)
        assert result.stderr.strip() != "", (
            "ToolError on nonexistent entry must be printed to stderr"
        )
        # stderr should mention the entry ID or 'not found'
        assert nonexistent_id[:8] in result.stderr or "not found" in result.stderr.lower(), (
            "stderr must reference the nonexistent entry"
        )

    def test_error_path_a_processing_continues_after_tool_error(self, tmp_path: Path) -> None:
        """AC9: after ToolError for nonexistent ID, processing continues to next entry."""
        valid_eid = str(uuid.uuid4())
        nonexistent_id = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": valid_eid, "content": "valid entry"}])
        # nonexistent first, then valid — valid should still be approved
        _run_approve("--approve", nonexistent_id, valid_eid, db_path=db)
        assert _get_state(db, valid_eid) == "approved", (
            "Processing must continue to next entry after ToolError for nonexistent ID"
        )

    def test_error_path_b_disallowed_transition_printed_to_stderr(self, tmp_path: Path) -> None:
        """AC10: error-prefixed string for disallowed transition is printed to stderr."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        # Pre-approve the entry so pending→approved already done
        _make_db(db, [{"id": eid, "content": "already approved", "approval_state": "approved"}])
        # Trying to approve an already-approved entry is a disallowed transition
        result = _run_approve("--approve", eid, db_path=db)
        assert result.stderr.strip() != "", (
            "Disallowed transition error must be printed to stderr"
        )
        assert "error" in result.stderr.lower(), (
            "stderr must contain 'error' for disallowed transition"
        )

    def test_error_path_b_processing_continues_after_disallowed_transition(
        self, tmp_path: Path
    ) -> None:
        """AC10: processing continues to next entry after a disallowed transition error."""
        already_approved_eid = str(uuid.uuid4())
        valid_pending_eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [
            {"id": already_approved_eid, "content": "already done", "approval_state": "approved"},
            {"id": valid_pending_eid, "content": "still pending"},
        ])
        # First ID causes disallowed transition; second should still be approved
        _run_approve("--approve", already_approved_eid, valid_pending_eid, db_path=db)
        assert _get_state(db, valid_pending_eid) == "approved", (
            "Processing must continue after disallowed transition for second entry"
        )


# ===========================================================================
# AC11 + AC12: Curation report — recommendation column
# ===========================================================================


class TestFromAC_CurationReport:
    """Curation report presence/absence controls recommendation column display."""

    def test_curation_report_recommendation_column_shown(self, tmp_path: Path) -> None:
        """AC11: when curation-report.json exists, recommendation column is shown."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "curated entry", "category": "knowledge"}])
        report_path = tmp_path / "data" / "memory" / "curation-report.json"
        report = {"entries": [{"id": eid, "recommendation": "approve"}]}
        report_path.write_text(json.dumps(report), encoding="utf-8")
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        # Output must include "recommendation" column header or value "approve"
        output = result.stdout.lower()
        assert "recommendation" in output or "approve" in output, (
            "Table must include recommendation column when curation-report.json is present"
        )

    def test_curation_report_absent_warning_to_stderr(self, tmp_path: Path) -> None:
        """AC12: when curation-report.json is absent, a warning is printed to stderr."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "no report entry"}])
        # Do NOT create curation-report.json
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        assert result.stderr.strip() != "", (
            "A warning must be printed to stderr when curation-report.json is absent"
        )

    def test_curation_report_absent_no_recommendation_column(self, tmp_path: Path) -> None:
        """AC12: when curation-report.json is absent, table renders without recommendation."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "no report entry"}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0
        assert "recommendation" not in result.stdout.lower(), (
            "Table must NOT include recommendation column when curation-report.json is absent"
        )

    def test_curation_report_absent_no_crash(self, tmp_path: Path) -> None:
        """AC12: absent curation-report.json causes no crash; CLI completes normally."""
        eid = str(uuid.uuid4())
        db = tmp_path / "data" / "memory" / "test.db"
        _make_db(db, [{"id": eid, "content": "still works"}])
        result = _run_approve(db_path=db)
        assert result.returncode == 0, (
            "CLI must not crash when curation-report.json is absent"
        )
        assert eid[:8] in result.stdout, (
            "Entry must still be displayed when curation-report.json is absent"
        )


# ===========================================================================
# AC13: MCP integration — in-memory transport roundtrip
# ===========================================================================


class TestFromAC_MCPIntegration:
    """list_entries + set_approval_state roundtrip via in-memory MCP transport."""

    @pytest.mark.asyncio
    async def test_list_entries_roundtrip_via_in_memory_transport(self) -> None:
        """AC13: list_entries returns pending entry via in-memory MCP session."""
        eid = str(uuid.uuid4())
        target_conn: sqlite3.Connection | None = None

        @asynccontextmanager
        async def _test_lifespan(
            _server: FastMCP,
        ) -> AsyncGenerator[AppContext, None]:
            nonlocal target_conn
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Required per AC13
            conn.execute(_DDL)
            conn.commit()
            conn.execute(
                """INSERT INTO memory_entries
                   (id, content, category, confidence, created_at, updated_at,
                    source, scope_agent, scope_project, approval_state, deleted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL)""",
                (
                    eid, "mcp-test content", "knowledge", 0.8,
                    "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00",
                    "test", None, None,
                ),
            )
            conn.commit()
            target_conn = conn
            yield AppContext(conn=conn, project_name=None)

        server = FastMCP("test-memory", lifespan=_test_lifespan)
        server.add_tool(list_entries)
        server.add_tool(set_approval_state)

        async with create_connected_server_and_client_session(server) as client:
            list_result = await client.call_tool("list_entries", {"status": "pending"})

        text = list_result.content[0].text
        assert eid in text, (
            "list_entries must return the pending entry by ID via in-memory MCP transport"
        )

    @pytest.mark.asyncio
    async def test_set_approval_state_roundtrip_via_in_memory_transport(self) -> None:
        """AC13: set_approval_state approves entry; list_entries no longer shows it as pending."""
        eid = str(uuid.uuid4())

        @asynccontextmanager
        async def _test_lifespan(
            _server: FastMCP,
        ) -> AsyncGenerator[AppContext, None]:
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Required per AC13
            conn.execute(_DDL)
            conn.commit()
            conn.execute(
                """INSERT INTO memory_entries
                   (id, content, category, confidence, created_at, updated_at,
                    source, scope_agent, scope_project, approval_state, deleted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL)""",
                (
                    eid, "to be approved", "knowledge", 0.8,
                    "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00",
                    "test", None, None,
                ),
            )
            conn.commit()
            yield AppContext(conn=conn, project_name=None)

        server = FastMCP("test-memory", lifespan=_test_lifespan)
        server.add_tool(list_entries)
        server.add_tool(set_approval_state)

        async with create_connected_server_and_client_session(server) as client:
            approve_result = await client.call_tool(
                "set_approval_state",
                {"entry_id": eid, "new_state": "approved"},
            )
            pending_after = await client.call_tool("list_entries", {"status": "pending"})

        approve_text = approve_result.content[0].text
        assert "approved" in approve_text.lower(), (
            "set_approval_state must confirm the transition to approved"
        )
        pending_text = pending_after.content[0].text
        assert eid not in pending_text, (
            "After approval, entry must no longer appear in pending list_entries result"
        )

    @pytest.mark.asyncio
    async def test_custom_lifespan_uses_row_factory(self) -> None:
        """AC13: custom test lifespan must set conn.row_factory = sqlite3.Row."""
        row_factory_set: bool = False

        @asynccontextmanager
        async def _verifying_lifespan(
            _server: FastMCP,
        ) -> AsyncGenerator[AppContext, None]:
            nonlocal row_factory_set
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            conn.row_factory = sqlite3.Row
            row_factory_set = conn.row_factory is sqlite3.Row
            conn.execute(_DDL)
            conn.commit()
            yield AppContext(conn=conn, project_name=None)

        server = FastMCP("test-memory-rf", lifespan=_verifying_lifespan)
        server.add_tool(list_entries)

        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("list_entries", {})

        assert row_factory_set, (
            "Custom test lifespan must set conn.row_factory = sqlite3.Row "
            "(required per AC13 for dict-keyed row access)"
        )


# ===========================================================================
# AC14 + AC15: Exit codes — 0 on success, 1 if any operation failed
# ===========================================================================


class TestFromAC_ExitCodes:
    """Exit code is 0 on full success and 1 if any operation failed."""

    def test_exit_code_0_bare_invocation_empty_db(self, tmp_path: Path) -> None:
        """AC14: bare invocation with empty DB exits 0."""
        db = tmp_path / "test.db"
        _make_db(db)
        result = _run_approve(db_path=db)
        assert result.returncode == 0, (
            "Bare invocation on empty DB must exit 0"
        )

    def test_exit_code_0_batch_approve_success(self, tmp_path: Path) -> None:
        """AC14: --approve with valid IDs exits 0."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "entry to approve"}])
        result = _run_approve("--approve", eid, db_path=db)
        assert result.returncode == 0, (
            "--approve with valid IDs must exit 0"
        )

    def test_exit_code_0_interactive_no_errors(self, tmp_path: Path) -> None:
        """AC14: --interactive with valid choices exits 0."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "content": "entry"}])
        result = _run_approve("--interactive", db_path=db, stdin="a\n")
        assert result.returncode == 0

    def test_exit_code_1_on_tool_error(self, tmp_path: Path) -> None:
        """AC15: exit code 1 when any operation fails (ToolError for nonexistent ID)."""
        nonexistent_id = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db)  # empty DB
        result = _run_approve("--approve", nonexistent_id, db_path=db)
        assert result.returncode == 1, (
            "Must exit 1 when any operation fails (ToolError for nonexistent ID)"
        )

    def test_exit_code_1_on_disallowed_transition(self, tmp_path: Path) -> None:
        """AC15: exit code 1 when any operation fails (disallowed transition)."""
        eid = str(uuid.uuid4())
        db = tmp_path / "test.db"
        _make_db(db, [{"id": eid, "approval_state": "approved"}])
        # Trying to approve an already-approved entry is a disallowed transition
        result = _run_approve("--approve", eid, db_path=db)
        assert result.returncode == 1, (
            "Must exit 1 when any operation results in a disallowed transition error"
        )
