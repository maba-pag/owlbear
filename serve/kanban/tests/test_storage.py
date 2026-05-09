from __future__ import annotations
from datetime import UTC, datetime
from pathlib import Path
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import detect_corruption
from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    move_to_quarantine,
    read_task,
    write_task,
)
from owlbear_kanban.models import Task
import ast
from unittest.mock import patch
import pytest
from owlbear_kanban.corruption import ERR_CORRUPT_INVALID_STATUS, CorruptionError
from owlbear_kanban.models import BoardConfig
import owlbear_kanban.storage as storage_mod

"""TDD RED: C-05 — storage surface tests.

Task: #1050 (Brief C #1043) — paper-c.md §8.3, §8.6, §8.11
AC:   C13, C14, C15, C16, C28, C29, C30, C48
All tests FAIL (RED phase — storage.py not yet implemented).
"""




# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
wave_size: 4
agent_map: {}
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs, type:config, type:docs, test, type:test, agent, quality, type:user-action]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""

_CANONICAL_FRONTMATTER_KEYS = [
    "id",
    "title",
    "status",
    "priority",
    "created",
    "updated",
    "tags",
    "parent",
    "depends_on",
    "blocked",
    "block_reason",
    "claimed_at",
    "archival_reason",
    "archival_refs",
]


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_task(task_id: int = 1001) -> Task:
    now = datetime.now(tz=UTC).isoformat()
    return Task(
        id=task_id,
        title="Surface test",
        status="todo",
        priority="needed",
        created=now,
        updated=now,
    )


# ---------------------------------------------------------------------------
# TestFromAC_Frontmatter — AC-C13, AC-C14, AC-C15
# ---------------------------------------------------------------------------


class TestFromAC_Frontmatter:
    """AC-C13, AC-C14, AC-C15: frontmatter shape, extra fields, timestamp format."""

    def test_ac_c13_canonical_frontmatter_key_order(self, tmp_path: Path) -> None:
        """AC-C13: written file follows canonical C8.6 frontmatter key order."""
        kanban_dir = _make_board(tmp_path)
        task = _make_task(1001)
        path = write_task(task, kanban_dir)
        content = path.read_text(encoding="utf-8")

        # Extract frontmatter block
        lines = content.split("\n")
        assert lines[0] == "---"
        end_idx = lines.index("---", 1)
        fm_keys = [
            line.split(":")[0].strip()
            for line in lines[1:end_idx]
            if ":" in line and not line.startswith(" ")
        ]

        for i, expected_key in enumerate(_CANONICAL_FRONTMATTER_KEYS):
            pos = next((j for j, k in enumerate(fm_keys) if k == expected_key), None)
            assert pos is not None, f"Key '{expected_key}' missing from frontmatter"
            if i > 0:
                prev_key = _CANONICAL_FRONTMATTER_KEYS[i - 1]
                prev_pos = next((j for j, k in enumerate(fm_keys) if k == prev_key), -1)
                assert prev_pos < pos, (
                    f"Key '{expected_key}' appears before '{prev_key}' — wrong order"
                )

    def test_ac_c14_task_model_extra_allow_vendor_fields_survive(
        self, tmp_path: Path
    ) -> None:
        """AC-C14: Task model has extra='allow' — vendor fields survive round-trip."""
        kanban_dir = _make_board(tmp_path)
        # Write a task file with vendor fields (class, started, completed — legacy archive shape)
        task_content = """\
---
id: 1001
title: Archive task
status: done
priority: needed
created: "2026-04-21T10:00:00+00:00"
updated: "2026-04-21T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: completed
archival_refs: []
class: tier-1
started: "2026-01-01T00:00:00+00:00"
completed: "2026-04-21T09:00:00+00:00"
---

## Notes

content
"""
        task_file = kanban_dir / "archive" / "1001-archive.md"
        task_file.write_text(task_content, encoding="utf-8")

        task = read_task(task_file)
        # Vendor fields preserved via extra='allow'
        assert getattr(task, "class", None) == "tier-1"
        assert getattr(task, "started", None) is not None

    def test_ac_c15_timestamps_utc_plus_00_00(self, tmp_path: Path) -> None:
        """AC-C15: created and updated timestamps written with explicit +00:00 suffix."""
        kanban_dir = _make_board(tmp_path)
        task = _make_task(1001)
        path = write_task(task, kanban_dir)
        content = path.read_text(encoding="utf-8")

        # Both created and updated must end with +00:00
        for field in ("created", "updated"):
            matching = [
                line for line in content.splitlines() if line.startswith(f"{field}:")
            ]
            assert matching, f"Field '{field}' not found in frontmatter"
            assert "+00:00" in matching[0], (
                f"Field '{field}' is not UTC+00:00: {matching[0]}"
            )

    def test_ac_c15_claimed_at_utc_when_set(self, tmp_path: Path) -> None:
        """AC-C15: claimed_at timestamp also uses +00:00 when not null."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC).isoformat()
        task = Task(
            id=1002,
            title="Claimed task",
            status="in-progress",
            priority="needed",
            created=now,
            updated=now,
            claimed_at=now,
        )
        path = write_task(task, kanban_dir)
        content = path.read_text(encoding="utf-8")

        matching = [
            line for line in content.splitlines() if line.startswith("claimed_at:")
        ]
        assert matching
        assert "+00:00" in matching[0]


# ---------------------------------------------------------------------------
# TestFromAC_ClaimedByDetection — AC-C16, AC-C48
# ---------------------------------------------------------------------------


class TestFromAC_ClaimedByDetection:
    """AC-C16, AC-C48: claimed_by in tasks/ is corruption; in archive/ silently stripped."""

    def test_ac_c16_tasks_file_with_claimed_by_reports_mode3(
        self, tmp_path: Path
    ) -> None:
        """AC-C16: detect_corruption on tasks/ file with claimed_by → ERR_CORRUPT_MISSING_FIELD, mode 3."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1001-legacy.md"
        bad_file.write_text(
            "---\nid: 1001\ntitle: legacy\nstatus: todo\npriority: needed\n"
            "claimed_by: some-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_MISSING_FIELD"
        assert "claimed_by" in (err.detail or "").lower()

    def test_ac_c48_archive_file_with_claimed_by_reads_successfully(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: archive file with claimed_by is read without CorruptionError; field stripped."""
        kanban_dir = _make_board(tmp_path)
        archive_file = kanban_dir / "archive" / "1001-old.md"
        archive_file.write_text(
            "---\nid: 1001\ntitle: old task\nstatus: done\npriority: needed\n"
            "claimed_by: some-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "archival_reason: completed\narchival_refs: []\n---\n",
            encoding="utf-8",
        )

        # Must not raise CorruptionError
        task = read_task(archive_file)
        assert task is not None
        # claimed_by stripped from model
        assert not hasattr(task, "claimed_by") or task.claimed_by is None  # type: ignore[union-attr]

    def test_ac_c48_archive_with_claimed_by_no_migration_required_error(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: KanbanEngine init does NOT raise MigrationRequiredError when claimed_by is only in archive/."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "archive" / "1001-old.md").write_text(
            "---\nid: 1001\ntitle: old\nstatus: done\npriority: needed\n"
            "claimed_by: agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "archival_reason: completed\narchival_refs: []\n---\n",
            encoding="utf-8",
        )

        # Engine instantiation must succeed — archive claimed_by must not trigger migration gate
        engine = KanbanEngine(kanban_dir)
        assert engine is not None


# ---------------------------------------------------------------------------
# TestFromAC_Quarantine — AC-C28, AC-C29, AC-C30
# ---------------------------------------------------------------------------


class TestFromAC_Quarantine:
    """AC-C28, AC-C29, AC-C30: move_to_quarantine contract."""

    def test_ac_c28_creates_quarantine_dir_if_absent(self, tmp_path: Path) -> None:
        """AC-C28: move_to_quarantine creates quarantine/ directory lazily if absent."""
        kanban_dir = _make_board(tmp_path)
        quarantine_dir = kanban_dir / "quarantine"
        assert not quarantine_dir.exists()

        task_file = kanban_dir / "tasks" / "1001-corrupt.md"
        task_file.write_text(
            "---\nid: 1001\ntitle: corrupt\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )

        move_to_quarantine(task_file, kanban_dir)

        assert quarantine_dir.exists()

    def test_ac_c29_quarantined_file_at_expected_path(self, tmp_path: Path) -> None:
        """AC-C29: quarantined file ends up at quarantine/{original-filename}."""
        kanban_dir = _make_board(tmp_path)
        original_name = "1001-corrupt.md"
        task_file = kanban_dir / "tasks" / original_name
        task_file.write_text(
            "---\nid: 1001\ntitle: c\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\n'
            'updated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )

        quarantined_path = move_to_quarantine(task_file, kanban_dir)

        assert quarantined_path == kanban_dir / "quarantine" / original_name
        assert quarantined_path.exists()
        assert not task_file.exists()

    def test_ac_c30_ar_task_has_type_user_action_tag(self, tmp_path: Path) -> None:
        """AC-C30: AR task created by repair_storage() carries tag type:user-action."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1001-bad.md"
        corrupt_file.write_text("no frontmatter delimiters\n", encoding="utf-8")

        engine = KanbanEngine(kanban_dir)
        outcomes = engine.repair_storage()

        quarantined = [o for o in outcomes if o.action in ("quarantined", "failed")]
        assert quarantined, "Expected at least one quarantined outcome"

        # AR task created
        all_tasks = engine.list_tasks()
        ar_tasks = [t for t in all_tasks if "type:user-action" in (t.tags or [])]
        assert ar_tasks, "Expected an AR task with type:user-action tag"

    def test_ac_c30_ar_task_body_has_quarantined_file_section(
        self, tmp_path: Path
    ) -> None:
        """AC-C30: AR task body contains '## Quarantined file' section with code, path, detail."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1001-bad.md"
        corrupt_file.write_text("no frontmatter delimiters\n", encoding="utf-8")

        engine = KanbanEngine(kanban_dir)
        engine.repair_storage()

        all_tasks = engine.list_tasks()
        ar_tasks = [t for t in all_tasks if "type:user-action" in (t.tags or [])]
        assert ar_tasks
        ar_body = engine.show_task(ar_tasks[0].id).body
        assert "## Quarantined file" in ar_body
        assert "code" in ar_body

"""RED-phase tests for threading cached config through read_task hot path (#1205).

AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_accepts_config_keyword_arg
AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_config_provided_skips_load_config_call
AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_config_param_is_keyword_only
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_happy_valid_task_no_config_yml_config_provided
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_edge_corrupt_task_no_config_yml_config_provided_raises
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_error_corrupt_task_config_yml_present_config_provided_raises
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_boundary_detection_runs_even_when_config_yml_absent
AC3 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac3_explicit_none_returns_task
AC3 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac3_explicit_none_calls_load_config
AC3 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac3_corrupt_task_config_yml_present_none_raises
AC3 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac3_corrupt_task_no_config_yml_config_none_returns_task
AC4 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac4_engine_all_call_sites_pass_config
AC4 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac4_engine_call_sites_value_is_self_config
"""





# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUSES = ["research", "backlog", "todo", "in-progress", "review", "done"]
_PRIORITIES = ["someday", "nice-to-have", "important", "needed", "critical"]

_CONFIG_YAML = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
next_id: 2
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map: {}
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

_VALID_TASK_YAML = """\
---
id: 1
title: Test Task
status: todo
priority: important
created: 2026-01-01 00:00:00+00:00
updated: 2026-01-01 00:00:00+00:00
tags: []
depends_on: []
blocked: false
---
"""

_CORRUPT_TASK_YAML = """\
---
id: 1
title: Corrupt Task
status: invalid-status
priority: important
created: 2026-01-01 00:00:00+00:00
updated: 2026-01-01 00:00:00+00:00
tags: []
depends_on: []
blocked: false
---
"""


def _make_config() -> BoardConfig:
    """Return an in-memory BoardConfig with standard statuses/priorities."""
    return BoardConfig(statuses=_STATUSES, priorities=_PRIORITIES, next_id=1)


def _make_board_with_task(tmp_path: Path) -> tuple[Path, Path]:
    """Create a board dir with config.yml and a valid task file.

    Returns (board_dir, task_path).
    """
    board_dir = tmp_path / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (board_dir / "archive").mkdir()
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    task_path = tasks_dir / "1-test-task.md"
    task_path.write_text(_VALID_TASK_YAML, encoding="utf-8")
    return board_dir, task_path


def _make_task_no_config_yml(tmp_path: Path, *, corrupt: bool = False) -> Path:
    """Create a board dir WITHOUT config.yml, with a task file.

    Returns task_path. Used to test that config= param bypasses the
    config_path.exists() guard.
    """
    board_dir = tmp_path / "board_no_cfg"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (board_dir / "archive").mkdir()
    # Deliberately NO config.yml
    task_content = _CORRUPT_TASK_YAML if corrupt else _VALID_TASK_YAML
    task_path = tasks_dir / "1-test-task.md"
    task_path.write_text(task_content, encoding="utf-8")
    return task_path


# ---------------------------------------------------------------------------
# TestFromAC_ReadTaskCachedConfig
# ---------------------------------------------------------------------------


class TestFromAC_ReadTaskCachedConfig:
    """Tests for AC1-AC4: read_task optional cached-config parameter."""

    # ------------------------------------------------------------------
    # AC1 — read_task accepts keyword-only config=BoardConfig|None
    # ------------------------------------------------------------------

    def test_ac1_accepts_config_keyword_arg(self, tmp_path: Path) -> None:
        """AC1: read_task(path, config=...) must accept a BoardConfig without error."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        # Will TypeError pre-impl: "got an unexpected keyword argument 'config'"
        task = read_task(task_path, config=config)
        assert task.id == 1

    def test_ac1_config_provided_skips_load_config_call(self, tmp_path: Path) -> None:
        """AC1: when config is provided, load_config must NOT be called."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        with patch("owlbear_kanban.config_loader.load_config") as mock_load:
            # Will TypeError pre-impl before the assertion is reached
            read_task(task_path, config=config)
        mock_load.assert_not_called()

    def test_ac1_config_param_is_keyword_only(self, tmp_path: Path) -> None:
        """AC1: config= must be keyword-only — positional use raises TypeError."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        # Post-impl: passing config positionally must raise TypeError.
        # Pre-impl: TypeError for unknown argument — still fails, different message.
        with pytest.raises(TypeError):
            read_task(task_path, config)  # type: ignore[call-arg]

        # After impl, calling with the keyword must NOT raise TypeError.
        # This assertion fails pre-impl because the line above raises TypeError
        # and does NOT advance past the raises block to reach this assertion.
        _ = read_task(task_path, config=config)  # Will TypeError pre-impl

    # ------------------------------------------------------------------
    # AC2 — when config provided, detection runs unconditionally
    # ------------------------------------------------------------------

    def test_ac2_happy_valid_task_no_config_yml_config_provided(
        self, tmp_path: Path
    ) -> None:
        """AC2: valid task + config provided + no config.yml → task returned cleanly."""
        task_path = _make_task_no_config_yml(tmp_path, corrupt=False)
        config = _make_config()
        # Without config= the function would skip detection (no config.yml).
        # With config= the function runs detection; valid task → returns successfully.
        task = read_task(task_path, config=config)  # TypeError pre-impl
        assert task.id == 1

    def test_ac2_edge_corrupt_task_no_config_yml_config_provided_raises(
        self, tmp_path: Path
    ) -> None:
        """AC2 edge: corrupt task + config provided + no config.yml → CorruptionError.

        The config.yml absence guard is skipped because config is pre-resolved.
        Detection runs unconditionally and must surface the corrupt status.
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        config = _make_config()
        # Pre-impl: TypeError for unexpected config= kwarg
        # Post-impl: CorruptionError for invalid status
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_path, config=config)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac2_error_corrupt_task_config_yml_present_config_provided_raises(
        self, tmp_path: Path
    ) -> None:
        """AC2 error: corrupt task + config.yml present + config provided → CorruptionError."""
        board_dir, _ = _make_board_with_task(tmp_path)
        tasks_dir = board_dir / "tasks"
        corrupt_path = tasks_dir / "1-corrupt.md"
        corrupt_path.write_text(_CORRUPT_TASK_YAML, encoding="utf-8")
        config = _make_config()
        with pytest.raises(CorruptionError) as exc_info:
            read_task(corrupt_path, config=config)  # TypeError pre-impl
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac2_boundary_detection_runs_even_when_config_yml_absent(
        self, tmp_path: Path
    ) -> None:
        """AC2 boundary: config.yml absent + config provided → CorruptionError, not silent skip.

        Without the guard bypass, missing config.yml would silently skip detection
        and return the (corrupt) task. With config provided, the guard is bypassed
        and detection runs unconditionally, raising CorruptionError.
        Pre-impl: TypeError (unexpected kwarg) — test fails.
        Post-impl: CorruptionError (invalid status surfaced without config.yml).
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        config = _make_config()
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_path, config=config)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    # ------------------------------------------------------------------
    # AC3 — config=None preserves existing behavior: guard + load_config
    # ------------------------------------------------------------------

    def test_ac3_explicit_none_returns_task(self, tmp_path: Path) -> None:
        """AC3: read_task(path, config=None) must return task identical to read_task(path)."""
        _, task_path = _make_board_with_task(tmp_path)
        # Pre-impl: TypeError for unknown kwarg config=None
        task = read_task(task_path, config=None)
        assert task.id == 1

    def test_ac3_explicit_none_calls_load_config(self, tmp_path: Path) -> None:
        """AC3: when config=None, load_config is still called from disk."""
        _, task_path = _make_board_with_task(tmp_path)
        with patch(
            "owlbear_kanban.config_loader.load_config", wraps=load_config
        ) as mock_load:
            # Pre-impl: TypeError before mock can capture the call
            read_task(task_path, config=None)
        mock_load.assert_called_once()

    # ------------------------------------------------------------------
    # AC3 (td:2 strengthened) — config=None: detection fires on corrupt input;
    # absent config.yml guard skips detection
    # ------------------------------------------------------------------

    def test_ac3_corrupt_task_config_yml_present_none_raises(
        self, tmp_path: Path
    ) -> None:
        """AC3 td:2: corrupt task + config.yml present + config=None → CorruptionError.

        Proves detect_corruption fires on corrupt input in the config=None path.
        Would silently pass if detection were removed from that branch.
        """
        board_dir, _ = _make_board_with_task(tmp_path)
        tasks_dir = board_dir / "tasks"
        corrupt_content = _CORRUPT_TASK_YAML.replace("id: 1", "id: 2")
        corrupt_path = tasks_dir / "2-corrupt.md"
        corrupt_path.write_text(corrupt_content, encoding="utf-8")
        with pytest.raises(CorruptionError) as exc_info:
            read_task(corrupt_path, config=None)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac3_corrupt_task_no_config_yml_config_none_returns_task(
        self, tmp_path: Path
    ) -> None:
        """AC3 td:2: corrupt task + no config.yml + config=None → task returned.

        Proves the config_path.exists() guard works: when config.yml is absent
        and config=None, corruption detection is skipped and the task is returned
        (even with an invalid status field).
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        # config=None + no config.yml → guard fires, detection skipped → task returned
        task = read_task(task_path, config=None)
        assert task.id == 1

    # ------------------------------------------------------------------
    # AC4 — all engine.py call sites pass config=self._config
    # ------------------------------------------------------------------

    def test_ac4_engine_all_call_sites_pass_config(self) -> None:
        """AC4: every read_task() call in engine.py must include config= keyword arg."""
        engine_py = (
            Path(__file__).parent.parent / "src/owlbear_kanban/engine.py"
        )
        source = engine_py.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(engine_py))

        violations: list[int] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "read_task"
            ):
                kwarg_names = [kw.arg for kw in node.keywords]
                if "config" not in kwarg_names:
                    violations.append(node.lineno)

        assert not violations, (
            f"read_task() calls in engine.py missing config= keyword argument "
            f"at lines: {violations}. All engine call sites must pass "
            f"config=self._config per AC4."
        )

    def test_ac4_engine_call_sites_value_is_self_config(self) -> None:
        """AC4 (strengthened): config= value at every engine.py call site must be
        self._config (Attribute access: Name('self')._config), not just a keyword.

        Catches cases like config=None or config=load_config(...) which would pass
        test_ac4_engine_all_call_sites_pass_config but violate the contract.
        """
        engine_py = (
            Path(__file__).parent.parent / "src/owlbear_kanban/engine.py"
        )
        source = engine_py.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(engine_py))

        violations: list[int] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "read_task"
            ):
                for kw in node.keywords:
                    if kw.arg == "config":
                        val = kw.value
                        is_self_config = (
                            isinstance(val, ast.Attribute)
                            and val.attr == "_config"
                            and isinstance(val.value, ast.Name)
                            and val.value.id == "self"
                        )
                        if not is_self_config:
                            violations.append(node.lineno)

        assert not violations, (
            f"read_task() calls in engine.py have config= but value is not "
            f"self._config at lines: {violations}. Per AC4 the value must be "
            f"self._config (attribute access on self)."
        )

"""Tests for #1206: Remove storage.load_config wrapper / clean up double-validation.

AC coverage:
  AC1: storage.py no longer defines or exports load_config (td:1)
       — symbol absent from __all__, module attributes, and module docstring
  AC5: No double _validate_claim_timeout call in any load path (td:1)
       — config_loader.load_config invokes _validate_claim_timeout exactly once
"""




# ---------------------------------------------------------------------------
# Shared board fixture
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - done
priorities:
  - someday
  - important
  - critical
entry_status: research
claim_timeout: 1h
next_id: 1
agent_map:
  research: []
  backlog: []
  done: []
"""


def _make_board(tmp_path: Path, config_yaml: str = _CONFIG_YAML) -> Path:
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1: storage.py no longer defines or exports load_config
# ---------------------------------------------------------------------------


class TestFromAC_StorageDropsLoadConfig:
    """Verify load_config is fully removed from storage.py public surface (AC1)."""

    def test_load_config_absent_from_dunder_all(self) -> None:
        """load_config must not appear in owlbear_kanban.storage.__all__."""
        assert "load_config" not in storage_mod.__all__

    def test_load_config_not_an_attribute_on_storage_module(self) -> None:
        """storage module must not define a load_config attribute at all."""
        assert not hasattr(storage_mod, "load_config")

    def test_load_config_absent_from_module_docstring(self) -> None:
        """Module docstring (Public API section) must not list load_config."""
        docstring = storage_mod.__doc__ or ""
        assert "load_config" not in docstring


# ---------------------------------------------------------------------------
# AC5: No double _validate_claim_timeout call in any load path
# ---------------------------------------------------------------------------


class TestFromAC_NoDoubleValidation:
    """storage.py must not contain a redundant _validate_claim_timeout call (AC5).

    The double-call exists because storage.load_config re-invokes
    _validate_claim_timeout after delegating to config_loader.load_config.
    After the wrapper is removed, storage.py must not reference
    _validate_claim_timeout at all.
    """

    def test_storage_does_not_reference_validate_claim_timeout(self) -> None:
        """storage.py source must not contain _validate_claim_timeout (no re-call)."""
        import inspect

        source = inspect.getsource(storage_mod)
        assert "_validate_claim_timeout" not in source, (
            "storage.py still references _validate_claim_timeout — "
            "the double-validation wrapper has not been removed"
        )


# ---------------------------------------------------------------------------
# load_config defaults when config.yml is absent
# ---------------------------------------------------------------------------


class TestFromAC_LoadConfigDefaultsWhenMissing:
    """AC1 (topology-constant refactor): load_config() returns PRODUCT_TOPOLOGY-derived
    config and does not raise when config.yml is absent from kanban_dir.

    The reviewer identified that existing tests only cover the config=None path
    indirectly via read_task; this class provides direct load_config proof.
    """

    def _make_board_no_config(self, tmp_path: Path) -> Path:
        """Create kanban_dir with tasks/ and archive/ but without config.yml."""
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir(parents=True)
        (kanban_dir / "tasks").mkdir()
        (kanban_dir / "archive").mkdir()
        return kanban_dir

    def test_load_config_no_config_yml_does_not_raise(self, tmp_path: Path) -> None:
        """load_config(kanban_dir) must not raise when config.yml is absent."""
        kanban_dir = self._make_board_no_config(tmp_path)
        config_path = kanban_dir / "config.yml"
        assert not config_path.exists(), "Precondition: config.yml must be absent"

        cfg = load_config(kanban_dir)  # must not raise
        assert cfg is not None

    def test_load_config_no_config_yml_returns_product_statuses(
        self, tmp_path: Path
    ) -> None:
        """load_config() with no config.yml returns statuses from PRODUCT_TOPOLOGY."""
        from owlbear_kanban.topology import PRODUCT_TOPOLOGY  # noqa: PLC0415

        kanban_dir = self._make_board_no_config(tmp_path)
        cfg = load_config(kanban_dir)
        assert cfg.statuses == list(PRODUCT_TOPOLOGY.statuses), (
            f"Expected PRODUCT_TOPOLOGY statuses {list(PRODUCT_TOPOLOGY.statuses)!r}; "
            f"got {cfg.statuses!r}"
        )

    def test_load_config_no_config_yml_returns_product_entry_status(
        self, tmp_path: Path
    ) -> None:
        """load_config() with no config.yml returns pipeline.entry_status from PRODUCT_TOPOLOGY."""
        from owlbear_kanban.topology import PRODUCT_TOPOLOGY  # noqa: PLC0415

        kanban_dir = self._make_board_no_config(tmp_path)
        cfg = load_config(kanban_dir)
        assert cfg.pipeline.entry_status == PRODUCT_TOPOLOGY.entry_status, (
            f"Expected entry_status={PRODUCT_TOPOLOGY.entry_status!r}; "
            f"got {cfg.pipeline.entry_status!r}"
        )

    def test_load_config_no_config_yml_next_id_defaults_to_one(
        self, tmp_path: Path
    ) -> None:
        """load_config() with no config.yml defaults next_id to 1."""
        kanban_dir = self._make_board_no_config(tmp_path)
        cfg = load_config(kanban_dir)
        assert cfg.next_id == 1, (
            f"Expected next_id=1 when config.yml is absent; got {cfg.next_id!r}"
        )
