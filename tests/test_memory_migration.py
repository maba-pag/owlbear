"""RED-phase tests for memory score migration — task #1842.

P2-03: Migration — score initialization from confidence.

AC coverage:
- AC1: MemoryEngine.migrate_scores() -> int parses raw YAML, backfills score=confidence
       and counters=0 for entries missing any of the 4 keys; writes via write_entry;
       returns migrated count; skips malformed files; state unchanged.
- AC2: migrate_scores() is idempotent — entries with all 4 keys present produce no
       file writes; returns 0 on fully-migrated directory.
- AC3: compute_score(confidence, 0, 0) == confidence (mathematical identity);
       post-migration sort (state_rank, -score, id) identical to pre-migration
       sort (state_rank, -confidence, id) when all counters are 0.
- AC4: CLI `uv run memory-migrate [--memory-dir PATH] [--dry-run]` calls
       migrate_scores(); directory defaults OWLBEAR_MEMORY_DIR env → .owlbear/memory/;
       --dry-run reports count without writing; prints count to stdout; exits 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TS = "2026-05-25T10:00:00+00:00"

_ID_1 = "550e8400-e29b-41d4-a716-446655441842"
_ID_2 = "550e8400-e29b-41d4-a716-446655441843"
_ID_3 = "550e8400-e29b-41d4-a716-446655441844"
_ID_4 = "550e8400-e29b-41d4-a716-446655441845"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _LegacyEntrySpec:
    """Parameters for writing a legacy memory entry fixture."""

    def __init__(
        self,
        entry_id: str,
        confidence: float = 0.8,
        state: str = "pending",
        *,
        include_score: bool = False,
        include_counters: bool = False,
    ) -> None:
        self.entry_id = entry_id
        self.confidence = confidence
        self.state = state
        self.include_score = include_score
        self.include_counters = include_counters


def _write_legacy_entry(
    directory: Path,
    spec: _LegacyEntrySpec,
) -> None:
    """Write a raw YAML markdown entry without score/counter fields (pre-migration format)."""
    entry_id = spec.entry_id
    confidence = spec.confidence
    state = spec.state
    optional_score = f"score: {confidence}\n" if spec.include_score else ""
    optional_counters = (
        "outstanding_count: 0\nunremarkable_count: 0\ndidnt_use_count: 0\n" if spec.include_counters else ""
    )
    content = (
        "---\n"
        f"id: {entry_id}\n"
        f"title: Entry-{entry_id[:8]}\n"
        "categories:\n"
        "- domain-knowledge\n"
        f"confidence: {confidence}\n"
        f"state: {state}\n"
        f"{optional_score}"
        f"{optional_counters}"
        "scope_agents:\n"
        "- test-agent\n"
        "source_agent: test-agent\n"
        f"created_at: '{_TS}'\n"
        f"updated_at: '{_TS}'\n"
        "approved_at: null\n"
        "---\n\n"
        f"Content for entry {entry_id}.\n"
    )
    (directory / f"{entry_id}.md").write_text(content, encoding="utf-8")


def _write_fully_migrated_entry(
    directory: Path,
    entry_id: str,
    confidence: float = 0.8,
    state: str = "pending",
) -> None:
    """Write an entry that already has all 4 migration keys present."""
    _write_legacy_entry(
        directory,
        _LegacyEntrySpec(entry_id, confidence=confidence, state=state, include_score=True, include_counters=True),
    )


# ---------------------------------------------------------------------------
# AC1 — migrate_scores(): behavior, writes, skips, state preservation
# ---------------------------------------------------------------------------


class TestMigrateScores:
    """AC1: MemoryEngine.migrate_scores() -> int correct behavior."""

    def test_migrate_scores_method_exists(self, tmp_path: Path) -> None:
        """MemoryEngine has a migrate_scores() method."""
        from owlbear_memory import MemoryEngine

        engine = MemoryEngine(memory_dir=tmp_path)
        assert hasattr(engine, "migrate_scores")
        assert callable(engine.migrate_scores)

    def test_migrate_scores_returns_int(self, tmp_path: Path) -> None:
        """migrate_scores() returns an int (migrated count)."""
        from owlbear_memory import MemoryEngine

        engine = MemoryEngine(memory_dir=tmp_path)
        result = engine.migrate_scores()
        assert isinstance(result, int)

    def test_migrate_scores_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        """migrate_scores() returns 0 when directory has no entries."""
        from owlbear_memory import MemoryEngine

        engine = MemoryEngine(memory_dir=tmp_path)
        assert engine.migrate_scores() == 0

    def test_migrate_scores_returns_count_of_migrated_entries(self, tmp_path: Path) -> None:
        """migrate_scores() returns count of entries that were actually updated."""
        from owlbear_memory import MemoryEngine

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_2, confidence=0.9))
        engine = MemoryEngine(memory_dir=tmp_path)
        count = engine.migrate_scores()
        assert count == 2

    def test_migrate_scores_sets_score_to_confidence(self, tmp_path: Path) -> None:
        """After migrate_scores(), score is set equal to the entry's confidence."""
        from owlbear_memory import MemoryEngine
        from ruamel.yaml import YAML

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.85))
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        yaml = YAML(typ="safe")
        raw = (tmp_path / f"{_ID_1}.md").read_text(encoding="utf-8")
        _, frontmatter_raw, _ = raw.split("---", 2)
        data = yaml.load(frontmatter_raw)
        assert data["score"] == pytest.approx(0.85)

    def test_migrate_scores_sets_outstanding_count_to_zero(self, tmp_path: Path) -> None:
        """After migrate_scores(), outstanding_count is 0."""
        from owlbear_memory import MemoryEngine
        from ruamel.yaml import YAML

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        yaml = YAML(typ="safe")
        raw = (tmp_path / f"{_ID_1}.md").read_text(encoding="utf-8")
        _, frontmatter_raw, _ = raw.split("---", 2)
        data = yaml.load(frontmatter_raw)
        assert data["outstanding_count"] == 0

    def test_migrate_scores_sets_unremarkable_count_to_zero(self, tmp_path: Path) -> None:
        """After migrate_scores(), unremarkable_count is 0."""
        from owlbear_memory import MemoryEngine
        from ruamel.yaml import YAML

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        yaml = YAML(typ="safe")
        raw = (tmp_path / f"{_ID_1}.md").read_text(encoding="utf-8")
        _, frontmatter_raw, _ = raw.split("---", 2)
        data = yaml.load(frontmatter_raw)
        assert data["unremarkable_count"] == 0

    def test_migrate_scores_sets_didnt_use_count_to_zero(self, tmp_path: Path) -> None:
        """After migrate_scores(), didnt_use_count is 0."""
        from owlbear_memory import MemoryEngine
        from ruamel.yaml import YAML

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        yaml = YAML(typ="safe")
        raw = (tmp_path / f"{_ID_1}.md").read_text(encoding="utf-8")
        _, frontmatter_raw, _ = raw.split("---", 2)
        data = yaml.load(frontmatter_raw)
        assert data["didnt_use_count"] == 0

    def test_migrate_scores_writes_file(self, tmp_path: Path) -> None:
        """migrate_scores() writes back the updated file (mtime changes)."""
        from owlbear_memory import MemoryEngine

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        path = tmp_path / f"{_ID_1}.md"
        mtime_before = path.stat().st_mtime_ns
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()
        assert path.stat().st_mtime_ns != mtime_before

    def test_migrate_scores_state_unchanged(self, tmp_path: Path) -> None:
        """migrate_scores() does not alter the state field of migrated entries."""
        from owlbear_memory import MemoryEngine
        from ruamel.yaml import YAML

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8, state="curated"))
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        yaml = YAML(typ="safe")
        raw = (tmp_path / f"{_ID_1}.md").read_text(encoding="utf-8")
        _, frontmatter_raw, _ = raw.split("---", 2)
        data = yaml.load(frontmatter_raw)
        assert data["state"] == "curated"

    def test_migrate_scores_skips_malformed_file(self, tmp_path: Path) -> None:
        """migrate_scores() skips malformed files without raising an exception."""
        from owlbear_memory import MemoryEngine

        malformed = tmp_path / "bad.md"
        malformed.write_text("---\nnot: {valid yaml[[\n---\n\nbody\n", encoding="utf-8")
        engine = MemoryEngine(memory_dir=tmp_path)
        result = engine.migrate_scores()
        assert result == 0

    def test_migrate_scores_skips_malformed_not_counted(self, tmp_path: Path) -> None:
        """Malformed files don't contribute to the returned migrated count."""
        from owlbear_memory import MemoryEngine

        malformed = tmp_path / "bad.md"
        malformed.write_text("---\nnot: {valid yaml[[\n---\n\nbody\n", encoding="utf-8")
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.9))
        engine = MemoryEngine(memory_dir=tmp_path)
        count = engine.migrate_scores()
        assert count == 1

    def test_migrate_scores_entry_missing_only_score_is_migrated(self, tmp_path: Path) -> None:
        """Entry missing only 'score' (all counters present) is still migrated."""
        from owlbear_memory import MemoryEngine
        from ruamel.yaml import YAML

        # Write entry with counters but no score
        content = (
            "---\n"
            f"id: {_ID_1}\n"
            "title: Missing-score-entry\n"
            "categories:\n"
            "- domain-knowledge\n"
            "confidence: 0.75\n"
            "state: pending\n"
            "outstanding_count: 0\n"
            "unremarkable_count: 0\n"
            "didnt_use_count: 0\n"
            "scope_agents:\n"
            "- test-agent\n"
            "source_agent: test-agent\n"
            f"created_at: '{_TS}'\n"
            f"updated_at: '{_TS}'\n"
            "approved_at: null\n"
            "---\n\nContent.\n"
        )
        (tmp_path / f"{_ID_1}.md").write_text(content, encoding="utf-8")
        engine = MemoryEngine(memory_dir=tmp_path)
        count = engine.migrate_scores()
        assert count == 1

        yaml = YAML(typ="safe")
        raw = (tmp_path / f"{_ID_1}.md").read_text(encoding="utf-8")
        _, frontmatter_raw, _ = raw.split("---", 2)
        data = yaml.load(frontmatter_raw)
        assert data["score"] == pytest.approx(0.75)

    def test_migrate_scores_entry_missing_only_one_counter_is_migrated(self, tmp_path: Path) -> None:
        """Entry missing only 'outstanding_count' (score and other counters present) is migrated."""
        from owlbear_memory import MemoryEngine

        content = (
            "---\n"
            f"id: {_ID_1}\n"
            "title: Missing-one-counter\n"
            "categories:\n"
            "- domain-knowledge\n"
            "confidence: 0.9\n"
            "state: pending\n"
            "score: 0.9\n"
            "unremarkable_count: 0\n"
            "didnt_use_count: 0\n"
            "scope_agents:\n"
            "- test-agent\n"
            "source_agent: test-agent\n"
            f"created_at: '{_TS}'\n"
            f"updated_at: '{_TS}'\n"
            "approved_at: null\n"
            "---\n\nContent.\n"
        )
        (tmp_path / f"{_ID_1}.md").write_text(content, encoding="utf-8")
        engine = MemoryEngine(memory_dir=tmp_path)
        count = engine.migrate_scores()
        assert count == 1


# ---------------------------------------------------------------------------
# AC2 — Idempotency
# ---------------------------------------------------------------------------


class TestMigrateScoresIdempotency:
    """AC2: migrate_scores() is idempotent."""

    def test_fully_migrated_entry_returns_zero(self, tmp_path: Path) -> None:
        """Entry with all 4 keys present → returns 0, no writes."""
        from owlbear_memory import MemoryEngine

        _write_fully_migrated_entry(tmp_path, _ID_1, confidence=0.8)  # noqa: E501
        path = tmp_path / f"{_ID_1}.md"
        mtime_before = path.stat().st_mtime_ns
        engine = MemoryEngine(memory_dir=tmp_path)
        count = engine.migrate_scores()
        assert count == 0
        assert path.stat().st_mtime_ns == mtime_before

    def test_fully_migrated_directory_returns_zero(self, tmp_path: Path) -> None:
        """Directory where all entries have all 4 keys → returns 0."""
        from owlbear_memory import MemoryEngine

        _write_fully_migrated_entry(tmp_path, _ID_1)
        _write_fully_migrated_entry(tmp_path, _ID_2)
        engine = MemoryEngine(memory_dir=tmp_path)
        assert engine.migrate_scores() == 0

    def test_second_call_returns_zero(self, tmp_path: Path) -> None:
        """Calling migrate_scores() twice: second call returns 0."""
        from owlbear_memory import MemoryEngine

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.9))
        engine = MemoryEngine(memory_dir=tmp_path)
        first = engine.migrate_scores()
        assert first == 1
        second = engine.migrate_scores()
        assert second == 0

    def test_second_call_produces_no_writes(self, tmp_path: Path) -> None:
        """After first migration, second call does not touch files."""
        from owlbear_memory import MemoryEngine

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.9))
        path = tmp_path / f"{_ID_1}.md"
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()
        mtime_after_first = path.stat().st_mtime_ns
        engine.migrate_scores()
        assert path.stat().st_mtime_ns == mtime_after_first

    def test_mixed_directory_migrates_only_legacy_entries(self, tmp_path: Path) -> None:
        """Mix of migrated and legacy entries: only legacy are migrated."""
        from owlbear_memory import MemoryEngine

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        _write_fully_migrated_entry(tmp_path, _ID_2, confidence=0.9)
        already_migrated_path = tmp_path / f"{_ID_2}.md"
        mtime_migrated_before = already_migrated_path.stat().st_mtime_ns

        engine = MemoryEngine(memory_dir=tmp_path)
        count = engine.migrate_scores()
        assert count == 1
        assert already_migrated_path.stat().st_mtime_ns == mtime_migrated_before


# ---------------------------------------------------------------------------
# AC3 — Order-preservation (compute_score mathematical identity)
# ---------------------------------------------------------------------------


class TestOrderPreservation:
    """AC3: post-migration sort (state_rank, -score, id) identical to pre-migration sort.

    AC3 note: compute_score(c, 0, 0) == c is a mathematical identity already satisfied
    by the existing compute_score implementation. The sort-order test verifies the
    migration contract: after migrate_scores(), score==confidence for all entries, so
    sorting by score gives the same ranking as sorting by confidence.
    """

    def test_sort_order_unchanged_after_migration(self, tmp_path: Path) -> None:
        """Post-migration sort (state_rank, -score, id) == pre-migration sort (state_rank, -confidence, id)."""
        from owlbear_memory import MemoryEngine

        # Write 3 entries with different confidence values (no score/counters)
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.75, state="pending"))
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_2, confidence=0.90, state="pending"))
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_3, confidence=0.85, state="pending"))

        # Compute pre-migration sort key using confidence
        entries_before = [
            (_ID_1, 0.75),
            (_ID_2, 0.90),
            (_ID_3, 0.85),
        ]
        state_rank = 0  # all pending
        pre_migration_order = sorted(entries_before, key=lambda e: (state_rank, -e[1], e[0]))

        # Run migration
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.migrate_scores()

        # Reload and compute post-migration sort using score
        engine2 = MemoryEngine(memory_dir=tmp_path)
        loaded = engine2.load()
        post_migration_order = sorted(loaded, key=lambda e: (0, -e.score, e.id))

        # IDs in order must match
        pre_ids = [e[0] for e in pre_migration_order]
        post_ids = [e.id for e in post_migration_order]
        assert pre_ids == post_ids


# ---------------------------------------------------------------------------
# AC4 — CLI `memory-migrate`
# ---------------------------------------------------------------------------


class TestMemoryMigrateCLI:
    """AC4: CLI `uv run memory-migrate` behavior."""

    def test_cli_module_importable(self) -> None:
        """owlbear_memory.migrate module exists."""
        import importlib

        mod = importlib.import_module("owlbear_memory.migrate")
        assert mod is not None

    def test_cli_main_callable(self) -> None:
        """owlbear_memory.migrate.main is a callable entry point."""
        from owlbear_memory.migrate import main

        assert callable(main)

    def test_cli_calls_migrate_scores_and_prints_count(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CLI main() calls migrate_scores() and prints the migrated count to stdout."""
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        from owlbear_memory.migrate import main

        with patch("sys.argv", ["memory-migrate", "--memory-dir", str(tmp_path)]), pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "1" in captured.out

    def test_cli_exits_zero_on_success(self, tmp_path: Path) -> None:
        """CLI main() exits with code 0 on success (no SystemExit, or exits with 0)."""
        from owlbear_memory.migrate import main

        exit_code: int | None = None
        with (
            patch("sys.argv", ["memory-migrate", "--memory-dir", str(tmp_path)]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        exit_code = exc_info.value.code
        assert exit_code in (0, None)

    def test_cli_dry_run_does_not_write_files(self, tmp_path: Path) -> None:
        """--dry-run flag reports count without modifying any files."""
        from owlbear_memory.migrate import main

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        path = tmp_path / f"{_ID_1}.md"
        content_before = path.read_text(encoding="utf-8")

        with (
            patch("sys.argv", ["memory-migrate", "--memory-dir", str(tmp_path), "--dry-run"]),
            pytest.raises(SystemExit),
        ):
            main()

        assert path.read_text(encoding="utf-8") == content_before

    def test_cli_dry_run_prints_count(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """--dry-run reports the would-be migrated count to stdout."""
        from owlbear_memory.migrate import main

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_2, confidence=0.9))

        with (
            patch("sys.argv", ["memory-migrate", "--memory-dir", str(tmp_path), "--dry-run"]),
            pytest.raises(SystemExit),
        ):
            main()

        captured = capsys.readouterr()
        assert "2" in captured.out

    def test_cli_memory_dir_flag_overrides_default(self, tmp_path: Path) -> None:
        """--memory-dir PATH flag controls which directory is migrated."""
        from owlbear_memory.migrate import main

        subdir = tmp_path / "custom-mem"
        subdir.mkdir()
        _write_legacy_entry(subdir, _LegacyEntrySpec(_ID_1, confidence=0.8))

        other = tmp_path / "other-mem"
        other.mkdir()
        _write_legacy_entry(other, _LegacyEntrySpec(_ID_2, confidence=0.9))

        # Only subdir should be migrated
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        with (
            patch("sys.argv", ["memory-migrate", "--memory-dir", str(subdir)]),
            pytest.raises(SystemExit),
        ):  # argparse may call sys.exit(0)
            main()

        raw_id1 = (subdir / f"{_ID_1}.md").read_text(encoding="utf-8")
        _, fm1, _ = raw_id1.split("---", 2)
        data1 = yaml.load(fm1)
        assert "score" in data1

        raw_id2 = (other / f"{_ID_2}.md").read_text(encoding="utf-8")
        _, fm2, _ = raw_id2.split("---", 2)
        data2 = yaml.load(fm2)
        # other dir not migrated — score key should be absent
        assert "score" not in data2

    def test_cli_env_var_owlbear_memory_dir_used_as_default(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """OWLBEAR_MEMORY_DIR env var is used when no --memory-dir flag given."""
        from owlbear_memory.migrate import main

        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))

        env = {**os.environ, "OWLBEAR_MEMORY_DIR": str(tmp_path)}
        with patch("sys.argv", ["memory-migrate"]), patch.dict(os.environ, env, clear=True), pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "1" in captured.out

    def test_cli_subprocess_exits_zero(self, tmp_path: Path) -> None:
        """Subprocess `uv run memory-migrate --memory-dir PATH` exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_memory.migrate", "--memory-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_cli_subprocess_prints_count_to_stdout(self, tmp_path: Path) -> None:
        """Subprocess prints migrated count to stdout, not stderr."""
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_memory.migrate", "--memory-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert "1" in result.stdout
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# AC5 — Packaged console-script proof
# ---------------------------------------------------------------------------

_PROJECT_DIR = Path(__file__).resolve().parent.parent / "serve" / "memory"


class TestConsoleScriptProof:
    """AC5: packaged `memory-migrate` console-script exits 0 and prints migrated count.

    Executes via `uv run --project serve/memory memory-migrate` — fails if the
    [project.scripts] entry in serve/memory/pyproject.toml is removed.
    """

    def test_packaged_script_exits_zero(self, tmp_path: Path) -> None:
        """uv run --project serve/memory memory-migrate exits 0."""
        result = subprocess.run(
            ["uv", "run", "--project", str(_PROJECT_DIR), "memory-migrate", "--memory-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_packaged_script_prints_migrated_count(self, tmp_path: Path) -> None:
        """uv run --project serve/memory memory-migrate prints migrated count to stdout."""
        _write_legacy_entry(tmp_path, _LegacyEntrySpec(_ID_1, confidence=0.8))
        result = subprocess.run(
            ["uv", "run", "--project", str(_PROJECT_DIR), "memory-migrate", "--memory-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "1" in result.stdout


# ---------------------------------------------------------------------------
# AC6 — _resolve_memory_dir fallback branch
# ---------------------------------------------------------------------------


class TestResolveFallbackDir:
    """AC6: _resolve_memory_dir(None) with OWLBEAR_MEMORY_DIR unset returns Path('.owlbear/memory').

    Direct unit assertion on the private helper, independent of CLI integration.
    """

    def test_resolve_memory_dir_returns_default_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_resolve_memory_dir(None) returns Path('.owlbear/memory') when OWLBEAR_MEMORY_DIR is unset."""
        from owlbear_memory.migrate import _resolve_memory_dir

        monkeypatch.delenv("OWLBEAR_MEMORY_DIR", raising=False)
        result = _resolve_memory_dir(None)
        assert result == Path(".owlbear") / "memory"
