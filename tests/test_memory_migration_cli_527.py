"""Tests for task #527: Build memory migration CLI tool.

Contract-level verification that the memory migration CLI tool is correct per the
AC acceptance criteria.

AC coverage summary:
  - AC1:  Module at packages/mcp-memory/src/owlbear_mcp_memory/migrate.py
  - AC2:  --source-dir required, no default
  - AC3:  --db-path optional, defaults from OWLBEAR_MEMORY_DB_PATH then data/memory/memory.db
  - AC4:  --dry-run flag: prints entries + summary, no DB writes
  - AC5:  Inbox parsing: reads inbox/*.md, heading extracts agent/date, bullets → entries
  - AC6:  Inbox entries: confidence=0.7, approval_state=pending, source=migration:inbox/{filename}
  - AC7:  Established-file parsing: top-level *.md, splits on ## sections
  - AC8:  Established entries: confidence=0.7, approval_state=approved, source=migration:{file}[#slug]
  - AC9:  All entries: uuid4 id, MemoryEntry validation, scope_project=NULL
  - AC10: Idempotent: skips entries whose source already exists in DB
  - AC11: Opens SQLite directly; runs CREATE TABLE IF NOT EXISTS DDL; no server.py dependency
  - AC12: File encoding: utf-8-sig (BOM transparent)
  - AC13: Unparseable files: log warning to stderr, continue processing
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_PACKAGE_DIR = _REPO_ROOT / "serve" / "mcp-memory"
_MIGRATE_PY = _PACKAGE_DIR / "src" / "owlbear_mcp_memory" / "migrate.py"
_PYTHON = sys.executable


def _run_migrate(
    *args: str,
    env: dict | None = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the migration CLI via python -m owlbear_mcp_memory.migrate."""
    return subprocess.run(
        [_PYTHON, "-m", "owlbear_mcp_memory.migrate", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_REPO_ROOT) if cwd is None else cwd,
    )


@pytest.fixture()
def source_dir(tmp_path: Path) -> Path:
    """Create a minimal source directory with an empty inbox/ subdirectory."""
    (tmp_path / "inbox").mkdir()
    return tmp_path


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Provide a temp DB path (does not create the file)."""
    return tmp_path / "test_memory.db"


# ===========================================================================
# AC1: Module at packages/mcp-memory/src/owlbear_mcp_memory/migrate.py
# ===========================================================================


class TestFromAC_ModuleExistence:
    """migrate.py module exists and is importable."""

    def test_module_file_exists(self) -> None:
        assert _MIGRATE_PY.is_file(), f"migrate.py not found at {_MIGRATE_PY}"

    def test_module_importable(self) -> None:
        import owlbear_mcp_memory.migrate  # noqa: F401

    def test_module_invocable_as_main(self, source_dir: Path, db_path: Path) -> None:
        """python -m owlbear_mcp_memory.migrate --source-dir ... exits 0."""
        result = _run_migrate(
            "--source-dir", str(source_dir),
            "--db-path", str(db_path),
            "--dry-run",
        )
        assert result.returncode == 0, f"CLI crashed: {result.stderr}"


# ===========================================================================
# AC2-AC3: CLI argument contract
# ===========================================================================


class TestFromAC_CLIInterface:
    """CLI argument contract: required / optional args, env var default."""

    def test_source_dir_required_exit_nonzero(self, db_path: Path) -> None:
        """Exits non-zero when --source-dir is missing (argparse error, not import error)."""
        result = _run_migrate("--db-path", str(db_path))
        assert result.returncode != 0
        # Must be an argparse error — the module must be importable for this to work
        assert "owlbear_mcp_memory.migrate" not in result.stderr, (
            f"Module not found — migrate.py must exist for this test to pass: {result.stderr!r}"
        )

    def test_source_dir_required_stderr_mentions_source_dir(self, db_path: Path) -> None:
        """stderr must reference --source-dir / source_dir (argparse error, not ModuleNotFoundError)."""
        result = _run_migrate("--db-path", str(db_path))
        assert "source" in result.stderr.lower(), (
            f"Expected argparse error about --source-dir; got: {result.stderr!r}"
        )

    def test_db_path_uses_env_var(self, source_dir: Path, tmp_path: Path) -> None:
        """OWLBEAR_MEMORY_DB_PATH env var sets the DB path when --db-path is absent."""
        custom_db = tmp_path / "env_custom.db"
        env = {**os.environ, "OWLBEAR_MEMORY_DB_PATH": str(custom_db)}
        result = _run_migrate("--source-dir", str(source_dir), env=env)
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert custom_db.exists(), "DB should have been created at OWLBEAR_MEMORY_DB_PATH"

    def test_db_path_fallback_to_data_memory_db(self, source_dir: Path, tmp_path: Path) -> None:
        """Without env var or --db-path, DB is created at store/memory/memory.db relative to cwd."""
        env = {k: v for k, v in os.environ.items() if k != "OWLBEAR_MEMORY_DB_PATH"}
        result = _run_migrate("--source-dir", str(source_dir), env=env, cwd=str(tmp_path))
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert (tmp_path / "store" / "memory" / "memory.db").exists()

    def test_unknown_argument_rejected_with_specific_error(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """Unknown CLI args → non-zero exit with the unknown flag mentioned in stderr."""
        result = _run_migrate(
            "--source-dir", str(source_dir),
            "--db-path", str(db_path),
            "--nonexistent-flag-xyz",
        )
        assert result.returncode != 0
        assert "nonexistent-flag-xyz" in result.stderr, (
            f"Expected argparse to name the unknown flag; got: {result.stderr!r}"
        )


# ===========================================================================
# AC5: Inbox parsing — reads inbox/*.md, heading → agent/date, bullets → entries
# ===========================================================================


class TestFromAC_InboxParsing:
    """Inbox file parsing contract."""

    INBOX_CONTENT = textwrap.dedent("""\
        # Lessons: #123 (myagent, 2026-01-15)

        - problems_faced: Could not connect to DB
        - workarounds_applied: Used in-memory fallback
        - patterns_discovered: Always use retry with backoff
        - time_sinks: Debugging async deadlocks
        - quality_gaps: Missing test coverage for error paths
    """)

    def test_each_bullet_produces_one_entry(self, source_dir: Path, db_path: Path) -> None:
        (source_dir / "inbox" / "test.md").write_text(self.INBOX_CONTENT, encoding="utf-8")
        result = _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        assert result.returncode == 0, result.stderr
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT * FROM memory_entries WHERE source LIKE 'migration:inbox/%'"
        ).fetchall()
        conn.close()
        assert len(rows) == 5

    def test_heading_extracts_agent_name_as_scope_agent(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "agent.md").write_text(self.INBOX_CONTENT, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        agents = {
            r[0]
            for r in conn.execute(
                "SELECT scope_agent FROM memory_entries WHERE source LIKE 'migration:inbox/agent.md'"
            ).fetchall()
        }
        conn.close()
        assert "myagent" in agents

    def test_heading_extracts_date_for_created_at(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "dated.md").write_text(self.INBOX_CONTENT, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        dates = conn.execute(
            "SELECT created_at FROM memory_entries WHERE source LIKE 'migration:inbox/dated.md'"
        ).fetchall()
        conn.close()
        assert any("2026-01-15" in (d[0] or "") for d in dates)

    def test_problems_faced_maps_to_knowledge(self, source_dir: Path, db_path: Path) -> None:
        (source_dir / "inbox" / "pf.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: Some problem\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT category FROM memory_entries WHERE source = 'migration:inbox/pf.md'"
        ).fetchall()
        conn.close()
        assert rows == [("knowledge",)]

    def test_workarounds_applied_maps_to_knowledge(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "wa.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- workarounds_applied: A workaround\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT category FROM memory_entries WHERE source = 'migration:inbox/wa.md'"
        ).fetchall()
        conn.close()
        assert rows == [("knowledge",)]

    def test_patterns_discovered_maps_to_behavior(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "pd.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- patterns_discovered: A pattern\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT category FROM memory_entries WHERE source = 'migration:inbox/pd.md'"
        ).fetchall()
        conn.close()
        assert rows == [("behavior",)]

    def test_time_sinks_maps_to_context(self, source_dir: Path, db_path: Path) -> None:
        (source_dir / "inbox" / "ts.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- time_sinks: A time sink\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT category FROM memory_entries WHERE source = 'migration:inbox/ts.md'"
        ).fetchall()
        conn.close()
        assert rows == [("context",)]

    def test_quality_gaps_maps_to_context(self, source_dir: Path, db_path: Path) -> None:
        (source_dir / "inbox" / "qg.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- quality_gaps: A quality gap\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT category FROM memory_entries WHERE source = 'migration:inbox/qg.md'"
        ).fetchall()
        conn.close()
        assert rows == [("context",)]

    def test_unrecognized_label_maps_to_knowledge(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "unk.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- weird_label: Some content\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT category FROM memory_entries WHERE source = 'migration:inbox/unk.md'"
        ).fetchall()
        conn.close()
        assert rows == [("knowledge",)]

    def test_unrecognized_label_warns_to_stderr(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "unkw.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- weird_label: Some content\n",
            encoding="utf-8",
        )
        result = _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        assert result.returncode == 0, result.stderr
        assert "weird_label" in result.stderr, (
            f"Expected warning about unrecognized label; got stderr: {result.stderr!r}"
        )

    def test_inbox_entry_confidence_is_0_7(self, source_dir: Path, db_path: Path) -> None:
        (source_dir / "inbox" / "conf.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: Content\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT confidence FROM memory_entries WHERE source = 'migration:inbox/conf.md'"
        ).fetchall()
        conn.close()
        assert rows == [(0.7,)]

    def test_inbox_entry_approval_state_is_pending(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "appr.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: Content\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT approval_state FROM memory_entries WHERE source = 'migration:inbox/appr.md'"
        ).fetchall()
        conn.close()
        assert rows == [("pending",)]

    def test_inbox_entry_source_format_is_migration_inbox_filename(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "mysrc.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: Content\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT source FROM memory_entries").fetchall()
        conn.close()
        assert any(r[0] == "migration:inbox/mysrc.md" for r in rows)

    def test_inbox_entry_scope_project_is_null(
        self, source_dir: Path, db_path: Path
    ) -> None:
        (source_dir / "inbox" / "proj.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: Content\n",
            encoding="utf-8",
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT scope_project FROM memory_entries WHERE source = 'migration:inbox/proj.md'"
        ).fetchall()
        conn.close()
        assert rows == [(None,)]


# ===========================================================================
# AC7-AC8: Established-file parsing (top-level *.md)
# ===========================================================================


class TestFromAC_EstablishedFileParsing:
    """Established (top-level) file parsing contract."""

    def test_sections_split_on_double_hash(self, source_dir: Path, db_path: Path) -> None:
        content = "# My Tool\n\n## Usage Notes\n\nUse carefully.\n\n## Gotchas\n\nBe wary.\n"
        (source_dir / "tool-notes.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE 'migration:tool-notes.md%'"
        ).fetchall()
        conn.close()
        sources = {r[0] for r in rows}
        assert "migration:tool-notes.md#usage-notes" in sources
        assert "migration:tool-notes.md#gotchas" in sources

    def test_pre_heading_content_captured_as_separate_entry(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """Content before the first ## heading is not silently dropped."""
        content = "# My Tool\n\nIntroductory paragraph.\n\n## Section1\n\nSection content.\n"
        (source_dir / "intro.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source, content FROM memory_entries WHERE source LIKE 'migration:intro.md%'"
        ).fetchall()
        conn.close()
        # Should have an entry that contains the introductory text
        all_content = " ".join(r[1] for r in rows)
        assert "Introductory paragraph" in all_content, (
            f"Pre-heading content not captured. Entries: {rows}"
        )

    def test_file_with_no_hash_headings_produces_single_entry(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# My Notes\n\nJust some flat notes without any sections.\n"
        (source_dir / "flat-notes.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE 'migration:flat-notes.md%'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "migration:flat-notes.md"

    def test_no_heading_entry_excludes_title_line(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """For no-## files, the # title line is excluded from the stored content."""
        content = "# My Notes\n\nActual content to store.\n"
        (source_dir / "notitle.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT content FROM memory_entries WHERE source = 'migration:notitle.md'"
        ).fetchall()
        conn.close()
        assert rows
        assert "# My Notes" not in rows[0][0]

    def test_inbox_subdir_not_parsed_as_established(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """inbox/ subdirectory files are not re-parsed as established top-level files."""
        inbox_content = "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: Content\n"
        (source_dir / "inbox" / "lessons.md").write_text(inbox_content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        # All entries from inbox/lessons.md must use the inbox source format (prefix migration:inbox/)
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE '%lessons.md%'"
        ).fetchall()
        conn.close()
        for (src,) in rows:
            assert src.startswith("migration:inbox/"), (
                f"Inbox file was parsed as established: {src!r}"
            )

    def test_established_entry_approval_state_is_approved(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# Notes\n\n## Section\n\nEstablished knowledge.\n"
        (source_dir / "est.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT approval_state FROM memory_entries WHERE source LIKE 'migration:est.md%'"
        ).fetchall()
        conn.close()
        assert rows
        assert all(r[0] == "approved" for r in rows)

    def test_established_entry_source_has_lowercased_section_slug(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# File\n\n## My Important Section\n\nContent.\n"
        (source_dir / "slugtest.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE 'migration:slugtest.md%'"
        ).fetchall()
        conn.close()
        sources = {r[0] for r in rows}
        assert "migration:slugtest.md#my-important-section" in sources

    def test_established_entry_source_slug_uses_lowercase(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# File\n\n## UPPERCASE HEADING\n\nContent.\n"
        (source_dir / "casetest.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE 'migration:casetest.md%'"
        ).fetchall()
        conn.close()
        sources = {r[0] for r in rows}
        assert "migration:casetest.md#uppercase-heading" in sources

    def test_established_entry_confidence_is_0_7(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "est_conf.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT confidence FROM memory_entries WHERE source LIKE 'migration:est_conf.md%'"
        ).fetchall()
        conn.close()
        assert rows
        assert all(r[0] == 0.7 for r in rows)

    def test_established_entry_scope_project_is_null(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "est_scope.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT scope_project FROM memory_entries WHERE source LIKE 'migration:est_scope.md%'"
        ).fetchall()
        conn.close()
        assert rows
        assert all(r[0] is None for r in rows)


# ===========================================================================
# AC9: All entries — uuid4 id, MemoryEntry validation, scope_project=NULL
# ===========================================================================


class TestFromAC_EntryMetadata:
    """Entry-level metadata contract."""

    def test_entry_id_is_valid_uuid4(self, source_dir: Path, db_path: Path) -> None:
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "uid_test.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT id FROM memory_entries WHERE source LIKE 'migration:uid_test.md%'"
        ).fetchall()
        conn.close()
        assert rows
        for (entry_id,) in rows:
            parsed = uuid.UUID(entry_id)
            assert parsed.version == 4

    def test_create_table_ddl_creates_memory_entries_table(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """DDL runs before insert — table exists after migration even on a fresh DB."""
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "ddl_test.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_entries'"
        ).fetchall()
        conn.close()
        assert tables == [("memory_entries",)]

    def test_no_server_py_import_in_migrate(self) -> None:
        """migrate.py must not import server.py (no runtime server dependency)."""
        source = _MIGRATE_PY.read_text(encoding="utf-8")
        assert "from owlbear_mcp_memory.server import" not in source
        assert "from owlbear_mcp_memory import server" not in source
        assert "import server" not in source

    def test_entry_updated_at_is_migration_timestamp(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """updated_at field reflects a valid ISO 8601 UTC timestamp set at migration time."""
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "ts_test.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT updated_at FROM memory_entries WHERE source LIKE 'migration:ts_test.md%'"
        ).fetchall()
        conn.close()
        assert rows
        for (updated_at,) in rows:
            # Must be non-empty ISO datetime string
            assert updated_at, "updated_at must not be empty"
            # Basic ISO 8601 check: contains date separator
            assert "2026" in updated_at or "-" in updated_at


# ===========================================================================
# AC10: Idempotent — skips entries whose source already exists in DB
# ===========================================================================


class TestFromAC_Idempotency:
    """Idempotency contract."""

    def test_existing_source_not_duplicated_on_second_run(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "idem.md").write_text(content, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE 'migration:idem.md%'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1, f"Expected 1 row; got {len(rows)} (duplicate inserted)"

    def test_second_run_inserts_new_files(self, source_dir: Path, db_path: Path) -> None:
        """New files added between runs are still imported on the second run."""
        content1 = "# Notes\n\n## Section1\n\nFirst content.\n"
        (source_dir / "first.md").write_text(content1, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))

        content2 = "# Notes\n\n## Section2\n\nSecond content.\n"
        (source_dir / "second.md").write_text(content2, encoding="utf-8")
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE 'migration:second.md%'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1


# ===========================================================================
# AC4: --dry-run — prints entries + summary counts by category, no DB writes
# ===========================================================================


class TestFromAC_DryRun:
    """Dry-run mode contract."""

    def test_dry_run_does_not_create_db_file(self, source_dir: Path, db_path: Path) -> None:
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "drytest.md").write_text(content, encoding="utf-8")
        result = _run_migrate(
            "--source-dir", str(source_dir), "--db-path", str(db_path), "--dry-run"
        )
        assert result.returncode == 0, result.stderr
        assert not db_path.exists(), "DB must NOT be created when --dry-run is used"

    def test_dry_run_prints_source_field(self, source_dir: Path, db_path: Path) -> None:
        content = "# Notes\n\n## My Section\n\nContent.\n"
        (source_dir / "dryfile.md").write_text(content, encoding="utf-8")
        result = _run_migrate(
            "--source-dir", str(source_dir), "--db-path", str(db_path), "--dry-run"
        )
        assert "dryfile.md" in result.stdout

    def test_dry_run_prints_category(self, source_dir: Path, db_path: Path) -> None:
        content = "# Notes\n\n## Section\n\nContent.\n"
        (source_dir / "dry_cat.md").write_text(content, encoding="utf-8")
        result = _run_migrate(
            "--source-dir", str(source_dir), "--db-path", str(db_path), "--dry-run"
        )
        assert "knowledge" in result.stdout

    def test_dry_run_content_preview_truncated_at_80_chars(
        self, source_dir: Path, db_path: Path
    ) -> None:
        long_content = "X" * 200
        content = f"# Notes\n\n## Section\n\n{long_content}\n"
        (source_dir / "dry_preview.md").write_text(content, encoding="utf-8")
        result = _run_migrate(
            "--source-dir", str(source_dir), "--db-path", str(db_path), "--dry-run"
        )
        lines = result.stdout.splitlines()
        # Find any line with the long content preview
        preview_parts = [part for line in lines for part in line.split() if "X" in part]
        assert preview_parts, "No content preview found in dry-run output"
        # The longest X-run in the output must not exceed 80 chars
        max_x_run = max(len(p) for p in preview_parts if set(p) == {"X"})
        assert max_x_run <= 80, f"Preview exceeded 80 chars: {max_x_run}"

    def test_dry_run_prints_summary_counts_by_category(
        self, source_dir: Path, db_path: Path
    ) -> None:
        inbox = "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: C1\n- patterns_discovered: C2\n"
        (source_dir / "inbox" / "sum.md").write_text(inbox, encoding="utf-8")
        result = _run_migrate(
            "--source-dir", str(source_dir), "--db-path", str(db_path), "--dry-run"
        )
        output = result.stdout
        # Summary must list both categories present in the input
        assert "knowledge" in output
        assert "behavior" in output


# ===========================================================================
# AC12: File encoding — utf-8-sig (handles Windows BOM transparently)
# ===========================================================================


class TestFromAC_FileEncoding:
    """File encoding contract."""

    def test_reads_utf8_bom_file_without_bom_artifact_in_content(
        self, source_dir: Path, db_path: Path
    ) -> None:
        content = "# Notes\n\n## Section\n\nContent with BOM marker.\n"
        # Write with BOM (utf-8-sig)
        (source_dir / "bom_test.md").write_bytes(content.encode("utf-8-sig"))
        result = _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        assert result.returncode == 0, result.stderr
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT content FROM memory_entries WHERE source LIKE 'migration:bom_test.md%'"
        ).fetchall()
        conn.close()
        assert rows
        for (content_val,) in rows:
            assert "\ufeff" not in content_val, "BOM artifact found in stored content"


# ===========================================================================
# AC13: Unparseable files — log warning to stderr, continue processing
# ===========================================================================


class TestFromAC_ErrorHandling:
    """Error handling contract."""

    def test_unparseable_file_does_not_crash_migration(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """A file with non-UTF-8 bytes does not abort the migration (exit 0)."""
        (source_dir / "bad_bytes.md").write_bytes(b"\xff\xfe\x00\x01bad binary content")
        result = _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        assert result.returncode == 0

    def test_unparseable_file_logs_to_stderr(self, source_dir: Path, db_path: Path) -> None:
        """A file that cannot be read logs a warning to stderr."""
        (source_dir / "bad_bytes2.md").write_bytes(b"\xff\xfe\x00\x01bad binary content")
        result = _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        assert result.returncode == 0, "Migration must not crash on unparseable file"
        assert result.stderr, "Expected warning on stderr for unparseable file"

    def test_unparseable_file_does_not_prevent_valid_files(
        self, source_dir: Path, db_path: Path
    ) -> None:
        """Valid files are still imported even when a bad file is present."""
        (source_dir / "bad_bytes3.md").write_bytes(b"\xff\xfe\x00\x01bad binary content")
        (source_dir / "good.md").write_text(
            "# Notes\n\n## Good Section\n\nValid content.\n", encoding="utf-8"
        )
        _run_migrate("--source-dir", str(source_dir), "--db-path", str(db_path))
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT source FROM memory_entries WHERE source LIKE 'migration:good.md%'"
        ).fetchall()
        conn.close()
        assert len(rows) > 0, "Valid file was not imported after encountering bad file"


# ===========================================================================
# Builder-discovered: in-process coverage of internal functions
# ===========================================================================


class TestBuilderDiscovered:
    """In-process tests for internal helpers — ensures coverage ≥ 90% on migrate.py."""

    # --- _resolve_db_path ---

    def test_resolve_db_path_uses_explicit_arg(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _resolve_db_path

        result = _resolve_db_path(str(tmp_path / "explicit.db"))
        assert result == tmp_path / "explicit.db"

    def test_resolve_db_path_uses_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from owlbear_mcp_memory.migrate import _resolve_db_path

        monkeypatch.setenv("OWLBEAR_MEMORY_DB_PATH", str(tmp_path / "env.db"))
        result = _resolve_db_path(None)
        assert result == tmp_path / "env.db"

    def test_resolve_db_path_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from owlbear_mcp_memory.migrate import _resolve_db_path
        from pathlib import Path

        monkeypatch.delenv("OWLBEAR_MEMORY_DB_PATH", raising=False)
        result = _resolve_db_path(None)
        assert result == Path("store/memory/memory.db")

    # --- _slugify ---

    def test_slugify_lowercases(self) -> None:
        from owlbear_mcp_memory.migrate import _slugify

        assert _slugify("## UPPER CASE") == "upper-case"

    def test_slugify_replaces_spaces(self) -> None:
        from owlbear_mcp_memory.migrate import _slugify

        assert _slugify("## My Section") == "my-section"

    def test_slugify_strips_hashes(self) -> None:
        from owlbear_mcp_memory.migrate import _slugify

        assert _slugify("## Simple") == "simple"

    def test_slugify_removes_special_chars(self) -> None:
        from owlbear_mcp_memory.migrate import _slugify

        assert _slugify("## Hello, World!") == "hello-world"

    # --- _parse_inbox_file ---

    def test_parse_inbox_file_returns_entries(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _parse_inbox_file

        f = tmp_path / "task.md"
        f.write_text(
            "# Lessons: #42 (builder, 2026-02-01)\n\n- problems_faced: DB timeout\n",
            encoding="utf-8",
        )
        entries = _parse_inbox_file(f, "2026-02-01T00:00:00+00:00")
        assert len(entries) == 1
        assert entries[0]["content"] == "DB timeout"
        assert entries[0]["category"] == "knowledge"
        assert entries[0]["scope_agent"] == "builder"
        assert entries[0]["approval_state"] == "pending"

    def test_parse_inbox_file_empty_bullet_skipped(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _parse_inbox_file

        f = tmp_path / "empty.md"
        f.write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: \n",
            encoding="utf-8",
        )
        assert _parse_inbox_file(f, "now") == []

    def test_parse_inbox_file_bad_bytes_returns_empty(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _parse_inbox_file

        f = tmp_path / "bad.md"
        f.write_bytes(b"\xff\xfe bad binary")
        result = _parse_inbox_file(f, "now")
        assert result == []

    # --- _extract_created_at ---

    def test_extract_created_at_from_title(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _extract_created_at

        f = tmp_path / "dated.md"
        f.write_text("# Notes (2026-03-15)\n\nContent.\n", encoding="utf-8")
        lines = f.read_text(encoding="utf-8").splitlines()
        result = _extract_created_at(lines, f)
        assert result == "2026-03-15"

    def test_extract_created_at_falls_back_to_mtime(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _extract_created_at

        f = tmp_path / "nodated.md"
        f.write_text("# Notes\n\nContent.\n", encoding="utf-8")
        lines = f.read_text(encoding="utf-8").splitlines()
        result = _extract_created_at(lines, f)
        assert "-" in result  # ISO 8601 contains hyphens

    # --- _make_established_entry ---

    def test_make_established_entry_fields(self) -> None:
        from owlbear_mcp_memory.migrate import _make_established_entry

        entry = _make_established_entry("body", "migration:f.md#sec", "2026-01-01", "2026-02-01")
        assert entry["content"] == "body"
        assert entry["source"] == "migration:f.md#sec"
        assert entry["category"] == "knowledge"
        assert entry["confidence"] == 0.7
        assert entry["approval_state"] == "approved"
        assert entry["scope_agent"] is None
        assert entry["scope_project"] is None

    # --- _split_into_sections ---

    def test_split_empty_sections_not_included(self) -> None:
        from owlbear_mcp_memory.migrate import _split_into_sections

        lines = ["# File", "", "## Empty Section", "", "## Real Section", "", "Content."]
        entries = _split_into_sections(lines, "f.md", "2026-01-01", "now")
        sources = {e["source"] for e in entries}
        assert "migration:f.md#real-section" in sources
        assert "migration:f.md#empty-section" not in sources

    def test_split_multiple_sections(self) -> None:
        from owlbear_mcp_memory.migrate import _split_into_sections

        lines = ["# File", "## A", "Alpha.", "## B", "Beta."]
        entries = _split_into_sections(lines, "f.md", "2026-01-01", "now")
        sources = {e["source"] for e in entries}
        assert "migration:f.md#a" in sources
        assert "migration:f.md#b" in sources

    # --- _parse_established_file ---

    def test_parse_established_single_no_sections(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _parse_established_file

        f = tmp_path / "flat.md"
        f.write_text("# Title\n\nSome flat notes.\n", encoding="utf-8")
        entries = _parse_established_file(f, "now")
        assert len(entries) == 1
        assert entries[0]["source"] == "migration:flat.md"
        assert "Title" not in entries[0]["content"]

    def test_parse_established_empty_content_returns_empty(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _parse_established_file

        f = tmp_path / "empty.md"
        f.write_text("# Title\n", encoding="utf-8")
        assert _parse_established_file(f, "now") == []

    def test_parse_established_bad_bytes_returns_empty(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _parse_established_file

        f = tmp_path / "bad.md"
        f.write_bytes(b"\xff\xfe bad binary")
        assert _parse_established_file(f, "now") == []

    # --- _collect_entries ---

    def test_collect_entries_combines_inbox_and_established(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _collect_entries

        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "i.md").write_text(
            "# Lessons: #1 (a, 2026-01-01)\n\n- problems_faced: X\n", encoding="utf-8",
        )
        (tmp_path / "e.md").write_text("# Notes\n\n## Sec\n\nY.\n", encoding="utf-8")
        entries = _collect_entries(tmp_path, "now")
        sources = {str(e["source"]) for e in entries}
        assert any("inbox/i.md" in s for s in sources)
        assert any("e.md" in s for s in sources)

    def test_collect_entries_no_inbox_dir(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _collect_entries

        (tmp_path / "e.md").write_text("# Notes\n\nContent.\n", encoding="utf-8")
        entries = _collect_entries(tmp_path, "now")
        assert len(entries) == 1

    # --- _dry_run ---

    def test_dry_run_outputs_to_stdout(self, capsys: pytest.CaptureFixture) -> None:
        from owlbear_mcp_memory.migrate import _dry_run

        entries = [
            {"source": "migration:f.md#s", "category": "knowledge", "content": "Hello world"},
        ]
        _dry_run(entries)
        out = capsys.readouterr().out
        assert "f.md" in out
        assert "knowledge" in out
        assert "Hello world" in out

    def test_dry_run_truncates_preview(self, capsys: pytest.CaptureFixture) -> None:
        from owlbear_mcp_memory.migrate import _dry_run

        long = "X" * 200
        entries = [{"source": "migration:f.md", "category": "knowledge", "content": long}]
        _dry_run(entries)
        out = capsys.readouterr().out
        x_runs = [part for part in out.split() if set(part) == {"X"}]
        assert x_runs
        assert max(len(r) for r in x_runs) <= 80

    # --- _insert_entry + main() ---

    def test_insert_entry_writes_to_db(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import _DDL, _insert_entry
        import sqlite3

        db = tmp_path / "t.db"
        conn = sqlite3.connect(str(db))
        conn.execute(_DDL)
        entry = {
            "id": "00000000-0000-4000-8000-000000000001",
            "content": "test",
            "category": "knowledge",
            "confidence": 0.7,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
            "source": "migration:test.md",
            "scope_agent": None,
            "scope_project": None,
            "approval_state": "approved",
            "deleted_at": None,
        }
        _insert_entry(conn, entry)
        conn.commit()
        rows = conn.execute("SELECT content FROM memory_entries").fetchall()
        conn.close()
        assert rows == [("test",)]

    def test_main_missing_source_dir_returns_nonzero(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import main

        result = main(["--source-dir", str(tmp_path / "nonexistent")])
        assert result == 1

    def test_main_dry_run_returns_zero(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import main

        (tmp_path / "inbox").mkdir()
        result = main(["--source-dir", str(tmp_path), "--dry-run"])
        assert result == 0

    def test_main_writes_db(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import main

        (tmp_path / "inbox").mkdir()
        (tmp_path / "n.md").write_text("# Notes\n\n## Sec\n\nContent.\n", encoding="utf-8")
        db = tmp_path / "out.db"
        result = main(["--source-dir", str(tmp_path), "--db-path", str(db)])
        assert result == 0
        assert db.exists()

    def test_main_idempotent_in_process(self, tmp_path: Path) -> None:
        from owlbear_mcp_memory.migrate import main
        import sqlite3

        (tmp_path / "inbox").mkdir()
        (tmp_path / "n.md").write_text("# Notes\n\n## Sec\n\nContent.\n", encoding="utf-8")
        db = tmp_path / "idem.db"
        main(["--source-dir", str(tmp_path), "--db-path", str(db)])
        main(["--source-dir", str(tmp_path), "--db-path", str(db)])
        conn = sqlite3.connect(str(db))
        count = conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
        conn.close()
        assert count == 1
