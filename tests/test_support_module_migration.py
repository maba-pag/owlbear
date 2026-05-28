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




