"""Tests for #1176 — P3-02: Migrate support modules, cleanup compat layer, and live config.

AC coverage:
  AC1 (8 corruption.py access sites use sub-model paths):
    Source inspection — corruption.py must contain config.pipeline.statuses/priorities
    patterns and must NOT contain flat config.statuses/config.priorities at code level.
    Behavioral — detect_corruption/attempt_repair use pipeline sub-model, not root fields.
  AC2 (9 storage.py non-save_config sites use sub-model paths):
    Source inspection — storage.py must contain config.paths.tasks_dir/archive_dir patterns.
  AC4 (live .owlbear/kanban/config.yml migrated to grouped format):
    Live YAML file has no flat duplicate root-level keys (tasks_dir, archive_dir,
    entry_status, wave_size, claim_timeout, agent_map, non_impl_tags, etc.)
  AC6 (forwarding properties removed from BoardConfig):
    Loaded live config exposes no flat forwarding attributes via model_extra.

Tests for AC1 source-inspection and AC4/AC6 MUST FAIL until the builder:
  - Changes corruption.py to access config.pipeline.statuses and config.pipeline.priorities
    instead of the flat root fields config.statuses and config.priorities.
  - Cleans up .owlbear/kanban/config.yml to remove flat duplicate keys at root level.

Tests for AC1 behavioral MUST FAIL until the builder changes corruption.py:
  - Verified with a split-config where root statuses/priorities differ from pipeline
    sub-model values (model_construct bypasses validation so they can diverge).
    The correct sub-model path is the pipeline one; detect_corruption must use it.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import yaml

import owlbear_kanban.corruption as _corruption_mod
import owlbear_kanban.storage as _storage_mod
from owlbear_kanban.corruption import (
    ERR_CORRUPT_INVALID_PRIORITY,
    ERR_CORRUPT_MISSING_FIELD,
    detect_corruption,
    attempt_repair,
)
from owlbear_kanban.models import (
    AgentsConfig,
    BoardConfig,
    BoardDefaults,
    PathsConfig,
    PipelineConfig,
    PolicyConfig,
)

# ---------------------------------------------------------------------------
# Module source — loaded once for all source-inspection tests
# ---------------------------------------------------------------------------

_CORRUPTION_SOURCE = inspect.getsource(_corruption_mod)
_STORAGE_SOURCE = inspect.getsource(_storage_mod)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_LIVE_CONFIG_PATH = _REPO_ROOT / ".owlbear" / "kanban" / "config.yml"

# The set of flat root-level keys that are forbidden after config migration.
# Each of these keys belongs exclusively inside a sub-model section (paths/pipeline/
# agents/policy) and must NOT appear as a top-level key in a grouped config.
_FORBIDDEN_FLAT_KEYS: frozenset[str] = frozenset(
    {
        "tasks_dir",
        "archive_dir",
        "entry_status",
        "wave_size",
        "claim_timeout",
        "agent_map",
        "agent_types",
        "agent_compatibility",
        "non_impl_tags",
        "archival_reasons",
        "status_predicates",
    }
)


def _strip_comments_and_strings(src: str) -> str:
    """Remove Python string literals and line comments from source.

    Used to avoid false-positive matches inside docstrings or user_message
    strings when scanning for banned code-level accessor patterns.
    """
    # Remove triple-quoted strings first (docstrings, multi-line)
    out = re.sub(r'""".*?"""', '""""""', src, flags=re.DOTALL)
    out = re.sub(r"'''.*?'''", "''''''", out, flags=re.DOTALL)
    # Remove single-line strings
    out = re.sub(r'"(?:[^"\\]|\\.)*"', '""', out)
    out = re.sub(r"'(?:[^'\\]|\\.)*'", "''", out)
    # Remove Python line comments (also strips inline comments like # → config.priorities)
    return re.sub(r"#[^\n]*", "", out)


# Code-level source with comments and string literals stripped.
_CORRUPTION_CODE = _strip_comments_and_strings(_CORRUPTION_SOURCE)


def _make_split_config(tmp_path: Path) -> tuple[Path, BoardConfig]:
    """Build a board dir and a split BoardConfig where root != pipeline values.

    Root statuses/priorities are different from pipeline sub-model values.
    This lets tests distinguish which path the implementation actually uses:
    - Uses config.statuses      → validates against root list ("root-status")
    - Uses config.pipeline.statuses → validates against pipeline list ("pipeline-status")

    The task .md file is placed in tasks/ with status="pipeline-status" and
    priority="pipeline-priority", which are INVALID per root but VALID per pipeline.

    After corruption.py migration: detect_corruption returns None (valid).
    Before migration:             detect_corruption returns ERR_CORRUPT_INVALID_STATUS.
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tmp_path / "archive").mkdir()

    # Write a task with status and priority that are valid only via pipeline sub-model
    task_path = tasks_dir / "1-split-test.md"
    task_path.write_text(
        "---\n"
        "id: 1\n"
        "title: Split Test\n"
        "status: pipeline-status\n"
        "priority: pipeline-priority\n"
        "created: 2026-01-01T00:00:00+00:00\n"
        "updated: 2026-01-01T00:00:00+00:00\n"
        "tags: []\n"
        "depends_on: []\n"
        "blocked: false\n"
        "block_reason: null\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )

    pipeline = PipelineConfig.model_construct(
        statuses=["pipeline-status"],
        priorities=["pipeline-priority"],
        entry_status="pipeline-status",
        terminal_status="pipeline-status",
        wave_size=4,
        claim_timeout="1h",
        default_priority="pipeline-priority",
    )
    config = BoardConfig.model_construct(
        statuses=["root-status"],
        priorities=["root-priority"],
        paths=PathsConfig(tasks_dir="tasks", archive_dir="archive"),
        pipeline=pipeline,
        next_id=2,
        agents=AgentsConfig(),
        policy=PolicyConfig(),
        defaults=BoardDefaults(),
        activity_log=False,
    )
    return task_path, config


def _make_invalid_priority_task(tmp_path: Path) -> Path:
    """Write a task with an invalid priority for attempt_repair mode 9 tests."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tmp_path / "archive").mkdir(exist_ok=True)
    task_path = tasks_dir / "2-bad-priority.md"
    task_path.write_text(
        "---\n"
        "id: 2\n"
        "title: Bad Priority\n"
        "status: root-status\n"  # valid in root list
        "priority: invalid-priority\n"  # neither root nor pipeline
        "created: 2026-01-01T00:00:00+00:00\n"
        "updated: 2026-01-01T00:00:00+00:00\n"
        "tags: []\n"
        "depends_on: []\n"
        "blocked: false\n"
        "block_reason: null\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )
    return task_path


# ---------------------------------------------------------------------------
# AC1 — corruption.py sub-model migration (source inspection)
# ---------------------------------------------------------------------------


class TestFromAC_CorruptionSubmodelMigration:
    """AC1 — corruption.py must use config.pipeline.statuses / config.pipeline.priorities.

    All source-inspection tests FAIL until the builder migrates the 4 flat-access
    sites in corruption.py (detect_corruption and attempt_repair) to use
    config.pipeline.statuses and config.pipeline.priorities.
    """

    # -- Source-presence checks (positive) -----------------------------------

    def test_corruption_source_contains_pipeline_statuses(self) -> None:
        """AC1: corruption.py must contain 'pipeline.statuses' after migration.

        Currently FAILS: corruption.py uses config.statuses (flat root field).
        """
        assert "pipeline.statuses" in _CORRUPTION_SOURCE, (
            "corruption.py must use config.pipeline.statuses for status validation — "
            "currently uses flat root config.statuses"
        )

    def test_corruption_source_contains_pipeline_priorities(self) -> None:
        """AC1: corruption.py must contain 'pipeline.priorities' after migration.

        Currently FAILS: corruption.py uses config.priorities (flat root field).
        """
        assert "pipeline.priorities" in _CORRUPTION_SOURCE, (
            "corruption.py must use config.pipeline.priorities for priority validation — "
            "currently uses flat root config.priorities"
        )

    # -- Source-absence checks at code level (negative) ----------------------

    def test_corruption_no_flat_config_statuses_at_code_level(self) -> None:
        """AC1: corruption.py must not access config.statuses at code level after migration.

        Checks code with comments and string literals stripped to avoid false positives
        from inline comments like '# → config.priorities[0]'.

        Currently FAILS: code has set(config.statuses) | {"archived"} in detect_corruption.
        """
        assert "config.statuses" not in _CORRUPTION_CODE, (
            "corruption.py still uses flat 'config.statuses' at code level — "
            "migrate all 4 sites to 'config.pipeline.statuses' / 'config.pipeline.priorities'"
        )

    def test_corruption_no_flat_config_priorities_at_code_level(self) -> None:
        """AC1: corruption.py must not access config.priorities at code level after migration.

        Checks code with comments and string literals stripped.

        Currently FAILS: code has config.priorities in detect_corruption and attempt_repair
        (lines 325, 484, 522).
        """
        assert "config.priorities" not in _CORRUPTION_CODE, (
            "corruption.py still uses flat 'config.priorities' at code level — "
            "migrate all 4 sites to 'config.pipeline.priorities'"
        )

    # -- Behavioral checks (split-config) ------------------------------------

    def test_detect_corruption_uses_pipeline_statuses_not_root(self, tmp_path: Path) -> None:
        """AC1: detect_corruption must validate status against config.pipeline.statuses.

        Split-config: root.statuses=['root-status'], pipeline.statuses=['pipeline-status'].
        Task has status='pipeline-status' — valid in pipeline, invalid in root.

        After migration: detect_corruption returns None (no corruption).
        Currently FAILS: returns ERR_CORRUPT_INVALID_STATUS (uses root.statuses).
        """
        task_path, config = _make_split_config(tmp_path)
        result = detect_corruption(task_path, config)
        assert result is None, (
            f"detect_corruption must use config.pipeline.statuses after migration; "
            f"got {result!r} (still using root config.statuses)"
        )

    def test_detect_corruption_uses_pipeline_priorities_not_root(self, tmp_path: Path) -> None:
        """AC1: detect_corruption must validate priority against config.pipeline.priorities.

        Split-config: root.priorities=['root-priority'], pipeline.priorities=['pipeline-priority'].
        Task has priority='pipeline-priority' — valid in pipeline, invalid in root.

        After migration: detect_corruption returns None (no corruption).
        Currently FAILS: returns ERR_CORRUPT_INVALID_PRIORITY (uses root.priorities).
        """
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tmp_path / "archive").mkdir()
        task_path = tasks_dir / "3-priority-split.md"
        task_path.write_text(
            "---\n"
            "id: 3\n"
            "title: Priority Split\n"
            "status: root-status\n"  # valid in root
            "priority: pipeline-priority\n"  # valid in pipeline only
            "created: 2026-01-01T00:00:00+00:00\n"
            "updated: 2026-01-01T00:00:00+00:00\n"
            "tags: []\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "---\n"
            "Body.\n",
            encoding="utf-8",
        )
        pipeline = PipelineConfig.model_construct(
            statuses=["root-status"],
            priorities=["pipeline-priority"],
            entry_status="root-status",
            terminal_status="root-status",
            wave_size=4,
            claim_timeout="1h",
            default_priority="pipeline-priority",
        )
        config = BoardConfig.model_construct(
            statuses=["root-status"],
            priorities=["root-priority"],
            paths=PathsConfig(tasks_dir="tasks", archive_dir="archive"),
            pipeline=pipeline,
            next_id=4,
            agents=AgentsConfig(),
            policy=PolicyConfig(),
            defaults=BoardDefaults(),
            activity_log=False,
        )
        result = detect_corruption(task_path, config)
        assert result is None, (
            f"detect_corruption must use config.pipeline.priorities after migration; "
            f"got {result!r} (still using root config.priorities)"
        )

    def test_attempt_repair_mode9_uses_pipeline_priorities_first(self, tmp_path: Path) -> None:
        """AC1: attempt_repair mode9 must coerce priority to config.pipeline.priorities[0].

        Split-config: root.priorities=['root-priority'], pipeline.priorities=['pipeline-priority'].
        Repair of ERR_CORRUPT_INVALID_PRIORITY should set priority to 'pipeline-priority'.

        After migration: repaired file has priority='pipeline-priority'.
        Currently FAILS: sets priority='root-priority' (uses root config.priorities[0]).
        """
        task_path = _make_invalid_priority_task(tmp_path)
        pipeline = PipelineConfig.model_construct(
            statuses=["root-status"],
            priorities=["pipeline-priority", "other"],
            entry_status="root-status",
            terminal_status="root-status",
            wave_size=4,
            claim_timeout="1h",
            default_priority="pipeline-priority",
        )
        config = BoardConfig.model_construct(
            statuses=["root-status"],
            priorities=["root-priority", "other"],
            paths=PathsConfig(tasks_dir="tasks", archive_dir="archive"),
            pipeline=pipeline,
            next_id=3,
            agents=AgentsConfig(),
            policy=PolicyConfig(),
            defaults=BoardDefaults(),
            activity_log=False,
        )

        outcome = attempt_repair(task_path, ERR_CORRUPT_INVALID_PRIORITY, config)

        assert outcome.action == "fixed", f"repair failed: {outcome.detail}"
        repaired_content = task_path.read_text(encoding="utf-8")
        # The repaired task must use the pipeline.priorities first value
        assert "priority: pipeline-priority" in repaired_content, (
            f"attempt_repair mode9 must set priority from config.pipeline.priorities[0]; "
            f"expected 'pipeline-priority', repaired content:\n{repaired_content}"
        )

    def test_attempt_repair_mode3_default_priority_uses_pipeline_priorities(self, tmp_path: Path) -> None:
        """AC1: attempt_repair mode3 must fill missing priority from config.pipeline.priorities[0].

        A task missing the 'priority' field triggers mode3. The repair fills it with
        config.pipeline.priorities[0] (not config.priorities[0]).

        After migration: repaired file has priority='pipeline-priority'.
        Currently FAILS: sets priority='root-priority' (uses root config.priorities[0]).
        """
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tmp_path / "archive").mkdir(exist_ok=True)
        task_path = tasks_dir / "4-no-priority.md"
        task_path.write_text(
            "---\n"
            "id: 4\n"
            "title: No Priority\n"
            "status: root-status\n"
            "created: 2026-01-01T00:00:00+00:00\n"
            "updated: 2026-01-01T00:00:00+00:00\n"
            "---\n"
            "Body.\n",
            encoding="utf-8",
        )
        pipeline = PipelineConfig.model_construct(
            statuses=["root-status"],
            priorities=["pipeline-priority", "other"],
            entry_status="root-status",
            terminal_status="root-status",
            wave_size=4,
            claim_timeout="1h",
            default_priority="pipeline-priority",
        )
        config = BoardConfig.model_construct(
            statuses=["root-status"],
            priorities=["root-priority", "other"],
            paths=PathsConfig(tasks_dir="tasks", archive_dir="archive"),
            pipeline=pipeline,
            next_id=5,
            agents=AgentsConfig(),
            policy=PolicyConfig(),
            defaults=BoardDefaults(),
            activity_log=False,
        )

        outcome = attempt_repair(task_path, ERR_CORRUPT_MISSING_FIELD, config)

        assert outcome.action == "fixed", f"repair failed: {outcome.detail}"
        repaired_content = task_path.read_text(encoding="utf-8")
        assert "priority: pipeline-priority" in repaired_content, (
            f"attempt_repair mode3 must fill priority from config.pipeline.priorities[0]; "
            f"expected 'pipeline-priority', repaired content:\n{repaired_content}"
        )


# ---------------------------------------------------------------------------
# AC2 — storage.py (non-save_config) source inspection
# ---------------------------------------------------------------------------


class TestFromAC_StorageSubmodelPaths:
    """AC2 — storage.py non-save_config access sites must use config.paths sub-model.

    These are regression guards confirming storage.py already uses sub-model paths
    for the 7 paths-based access sites (write_task, list_tasks, and related functions).
    All tests PASS now and must continue to pass after the builder's fixture updates.
    """

    def test_storage_source_contains_paths_tasks_dir(self) -> None:
        """AC2: storage.py must access tasks_dir via config.paths.tasks_dir."""
        assert "paths.tasks_dir" in _STORAGE_SOURCE, (
            "storage.py must contain 'paths.tasks_dir' — all 7 paths-based access sites must use the sub-model"
        )

    def test_storage_source_contains_paths_archive_dir(self) -> None:
        """AC2: storage.py must access archive_dir via config.paths.archive_dir."""
        assert "paths.archive_dir" in _STORAGE_SOURCE, (
            "storage.py must contain 'paths.archive_dir' — all paths-based access sites must use the sub-model"
        )


# ---------------------------------------------------------------------------
# AC4 — Live config.yml has no flat duplicate keys
# ---------------------------------------------------------------------------


class TestFromAC_LiveConfigFlatKeyCleanup:
    """AC4 — .owlbear/kanban/config.yml must be clean grouped format (no flat duplicates).

    The live config currently has flat duplicate keys at root level (tasks_dir,
    archive_dir, entry_status, wave_size, claim_timeout, agent_map, etc.) left
    over from before the grouped schema migration. These MUST be removed.

    All tests FAIL until the builder rewrites the live config.yml to remove flat keys.
    """

    def _load_live_yaml(self) -> dict:
        """Return the live config.yml as a plain dict (top-level keys only)."""
        assert _LIVE_CONFIG_PATH.exists(), (
            f"Live config not found at {_LIVE_CONFIG_PATH}; cannot validate flat key cleanup"
        )
        return yaml.safe_load(_LIVE_CONFIG_PATH.read_text(encoding="utf-8")) or {}

    def test_live_config_no_flat_tasks_dir(self) -> None:
        """AC4: live config.yml must not have 'tasks_dir' at root level.

        Currently FAILS: file has 'tasks_dir: tasks' as a flat duplicate.
        After migration: only paths.tasks_dir is present.
        """
        data = self._load_live_yaml()
        assert "tasks_dir" not in data, (
            "live config.yml still has flat 'tasks_dir' at root — remove it; the canonical location is paths.tasks_dir"
        )

    def test_live_config_no_flat_archive_dir(self) -> None:
        """AC4: live config.yml must not have 'archive_dir' at root level.

        Currently FAILS: file has 'archive_dir: archive' as a flat duplicate.
        """
        data = self._load_live_yaml()
        assert "archive_dir" not in data, (
            "live config.yml still has flat 'archive_dir' at root — "
            "remove it; the canonical location is paths.archive_dir"
        )

    def test_live_config_no_flat_entry_status(self) -> None:
        """AC4: live config.yml must not have 'entry_status' at root level.

        Currently FAILS: file has 'entry_status: research' as a flat duplicate.
        """
        data = self._load_live_yaml()
        assert "entry_status" not in data, (
            "live config.yml still has flat 'entry_status' at root — "
            "remove it; the canonical location is pipeline.entry_status"
        )

    def test_live_config_no_flat_wave_size(self) -> None:
        """AC4: live config.yml must not have 'wave_size' at root level.

        Currently FAILS: file has 'wave_size: 4' as a flat duplicate.
        """
        data = self._load_live_yaml()
        assert "wave_size" not in data, (
            "live config.yml still has flat 'wave_size' at root — "
            "remove it; the canonical location is pipeline.wave_size"
        )

    def test_live_config_no_flat_claim_timeout(self) -> None:
        """AC4: live config.yml must not have 'claim_timeout' at root level.

        Currently FAILS: file has 'claim_timeout: 1h' as a flat duplicate.
        """
        data = self._load_live_yaml()
        assert "claim_timeout" not in data, (
            "live config.yml still has flat 'claim_timeout' at root — "
            "remove it; the canonical location is pipeline.claim_timeout"
        )

    def test_live_config_no_flat_agent_map(self) -> None:
        """AC4: live config.yml must not have 'agent_map' at root level.

        Currently FAILS: file has 'agent_map: {}' as a flat duplicate.
        """
        data = self._load_live_yaml()
        assert "agent_map" not in data, (
            "live config.yml still has flat 'agent_map' at root — remove it; the canonical location is agents.agent_map"
        )

    def test_live_config_no_flat_non_impl_tags(self) -> None:
        """AC4: live config.yml must not have 'non_impl_tags' at root level.

        Currently FAILS: file has 'non_impl_tags: []' as a flat duplicate.
        """
        data = self._load_live_yaml()
        assert "non_impl_tags" not in data, (
            "live config.yml still has flat 'non_impl_tags' at root — "
            "remove it; the canonical location is policy.non_impl_tags"
        )

    def test_live_config_no_flat_archival_reasons(self) -> None:
        """AC4: live config.yml must not have 'archival_reasons' at root level.

        Currently FAILS: file has 'archival_reasons: [...]' as a flat duplicate.
        """
        data = self._load_live_yaml()
        assert "archival_reasons" not in data, (
            "live config.yml still has flat 'archival_reasons' at root — "
            "remove it; the canonical location is policy.archival_reasons"
        )

    def test_live_config_no_forbidden_flat_keys(self) -> None:
        """AC4: live config.yml must have none of the forbidden flat duplicate keys.

        Comprehensive check covering all keys in _FORBIDDEN_FLAT_KEYS.
        Currently FAILS: multiple forbidden keys present.
        """
        data = self._load_live_yaml()
        present = _FORBIDDEN_FLAT_KEYS & set(data.keys())
        assert not present, (
            f"live config.yml has {len(present)} forbidden flat keys at root: {sorted(present)}. "
            "These must be removed — they belong inside paths/pipeline/agents/policy sub-sections."
        )


# ---------------------------------------------------------------------------
# AC6 — Forwarding properties removed from BoardConfig
# ---------------------------------------------------------------------------


class TestFromAC_ForwardingPropertiesRemoved:
    """AC6 — BoardConfig must not expose flat forwarding attributes after compat removal.

    When the live config.yml is cleaned up (AC4), loading it must not populate
    model_extra with flat duplicate keys. After cleanup, accessing config.tasks_dir
    or other flat keys should raise AttributeError (no forwarding via model_extra).

    Tests load the live config and verify that formerly-flat keys are absent from
    model_extra. All tests FAIL until the builder cleans up the live config.yml.
    """

    def _load_live_config(self) -> BoardConfig:
        """Load the live config from .owlbear/kanban/config.yml."""
        from owlbear_kanban.config_loader import load_config  # noqa: PLC0415

        assert _LIVE_CONFIG_PATH.exists(), f"Live config not found at {_LIVE_CONFIG_PATH}"
        return load_config(_LIVE_CONFIG_PATH.parent)

    def test_loaded_live_config_no_tasks_dir_forwarding(self) -> None:
        """AC6: loaded live config must not have 'tasks_dir' in model_extra.

        Currently FAILS: live config.yml has flat 'tasks_dir: tasks' → ends up in model_extra
        and makes config.tasks_dir accessible as an attribute via Pydantic extra='allow'.
        After AC4 cleanup: flat key absent from YAML → not in model_extra.
        """
        config = self._load_live_config()
        assert "tasks_dir" not in (config.model_extra or {}), (
            "loaded live config still has 'tasks_dir' in model_extra — "
            "clean up .owlbear/kanban/config.yml to remove flat duplicates"
        )

    def test_loaded_live_config_no_entry_status_forwarding(self) -> None:
        """AC6: loaded live config must not have 'entry_status' in model_extra.

        Currently FAILS: flat 'entry_status: research' in YAML → model_extra → accessible attr.
        """
        config = self._load_live_config()
        assert "entry_status" not in (config.model_extra or {}), (
            "loaded live config still has 'entry_status' in model_extra — "
            "clean up .owlbear/kanban/config.yml to remove flat duplicates"
        )

    def test_loaded_live_config_no_forbidden_forwarding_attrs(self) -> None:
        """AC6: loaded live config must not expose any forbidden flat keys via model_extra.

        After compat removal, all forbidden flat keys must be absent from model_extra.
        Currently FAILS: multiple forbidden keys present in model_extra.
        """
        config = self._load_live_config()
        model_extra = config.model_extra or {}
        present = _FORBIDDEN_FLAT_KEYS & set(model_extra.keys())
        assert not present, (
            f"loaded live config still has {len(present)} forbidden forwarding attrs "
            f"in model_extra: {sorted(present)}. "
            "Remove flat duplicate keys from .owlbear/kanban/config.yml."
        )
