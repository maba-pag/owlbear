"""Failing tests for task #1443 — scan-based ID allocation and activity logging defaults.

Task:   #1443 — P4-06: Replace next_id config allocation and hard-code activity logging
AC-1:   allocate_next_id (or replacement) scans active+archive dirs, computes max+1 (or 1
        if empty), and keeps the lock held while create_task writes the new task file.
AC-2:   create_task no longer reads or writes config.next_id; scratch board works without
        config.yml.
AC-3:   Active prefixes 1, 3 and archive prefixes 2, 5 → create_task writes task with ID 6.
AC-4:   Concurrent create_task calls produce distinct task filename prefixes; config.yml
        is absent or unchanged.
AC-5:   KanbanEngine activity logging defaults to enabled (True) without reading
        config.activity_log; create_task appends one ActivityEvent with all six model
        fields: timestamp, task_id, action, source, detail, task_status_at_start.
AC-6:   (td:0) — test-writer skipped.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.activity_store import list_activity_events
from owlbear_kanban.config_loader import load_config


# ---------------------------------------------------------------------------
# Minimal board fixtures
# ---------------------------------------------------------------------------


def _make_scratch_board(base: Path) -> Path:
    """Minimal scratch board — no config.yml, just the required directories."""
    kanban_dir = base / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _place_task_stubs(
    kanban_dir: Path,
    *,
    active_ids: list[int],
    archive_ids: list[int],
) -> None:
    """Write minimal stub task files with the given numeric prefixes."""
    for id_ in active_ids:
        (kanban_dir / "tasks" / f"{id_}-stub.md").write_text("\n", encoding="utf-8")
    for id_ in archive_ids:
        (kanban_dir / "archive" / f"{id_}-stub.md").write_text("\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# AC-1 through AC-5 tests
# ---------------------------------------------------------------------------


class TestScanBasedIdAllocation:
    """AC-1 through AC-5 for #1443 — scan-based ID allocation and activity logging defaults."""

    # ------------------------------------------------------------------
    # AC-1: scan-based allocation with lock held through write
    # ------------------------------------------------------------------

    def test_ac1_empty_board_returns_id_1_ignoring_config_next_id(self, tmp_path: Path) -> None:
        """AC-1: no task files → first create_task allocates ID 1 regardless of config.next_id.

        Board has config.yml with next_id=500 but no task files. Scan-based allocation
        ignores config.next_id and returns max_from_scan+1 = 1. Config-based returns 500.
        """
        kanban_dir = _make_scratch_board(tmp_path)
        (kanban_dir / "config.yml").write_text("next_id: 500\n", encoding="utf-8")
        engine = KanbanEngine(kanban_dir, activity_log=False)

        task = engine.create_task("first-task")

        assert task.id == 1, (
            f"Empty board (config.next_id=500): scan finds no files → ID must be 1; "
            f"got {task.id}. create_task is reading config.next_id=500 instead of "
            "scanning files for max prefix."
        )

    def test_ac1_scans_active_dir_prefix_for_max(self, tmp_path: Path) -> None:
        """AC-1: active task file with prefix 7 → next create_task gets ID 8."""
        kanban_dir = _make_scratch_board(tmp_path)
        _place_task_stubs(kanban_dir, active_ids=[7], archive_ids=[])
        engine = KanbanEngine(kanban_dir, activity_log=False)

        task = engine.create_task("after-active-7")

        assert task.id == 8, (
            f"Active prefix 7 → max=7 → next ID must be 8; got {task.id}. "
            "Active directory is not scanned for max prefix."
        )

    def test_ac1_scans_archive_dir_prefix_for_max(self, tmp_path: Path) -> None:
        """AC-1: archive task file with prefix 9 → next create_task gets ID 10."""
        kanban_dir = _make_scratch_board(tmp_path)
        _place_task_stubs(kanban_dir, active_ids=[], archive_ids=[9])
        engine = KanbanEngine(kanban_dir, activity_log=False)

        task = engine.create_task("after-archive-9")

        assert task.id == 10, (
            f"Archive prefix 9 → max=9 → next ID must be 10; got {task.id}. "
            "Archive directory is not scanned for max prefix."
        )

    def test_ac1_lock_scope_covers_write_crash_does_not_burn_id_via_scan(self, tmp_path: Path) -> None:
        """AC-1 (lock scope via crash probe): write crash → no ID burned → same ID on retry.

        Lock held through write: if write fails, the lock is released but no file was
        created. The next scan recomputes the same max+1 — same ID, no burning.
        Config-based behavior: allocate_next_id saves config BEFORE releasing lock and
        BEFORE write_task, so config.next_id is already incremented when write crashes.
        The next allocate_next_id reads the incremented config → gets next_id+1 (burned).

        Observable difference: retry returns ID 1 (scan-based) vs ID 2 (config-based).
        """
        kanban_dir = _make_scratch_board(tmp_path)
        # Start with a non-default config.next_id to verify scan ignores it
        (kanban_dir / "config.yml").write_text("next_id: 500\n", encoding="utf-8")
        engine = KanbanEngine(kanban_dir, activity_log=False)

        from owlbear_kanban.storage import write_task as _real_write_task  # noqa: PLC0415

        calls: list[int] = []

        def _crash_first(task: object, kd: Path) -> None:
            calls.append(1)
            if len(calls) == 1:
                msg = "simulated disk failure"
                raise OSError(msg)
            _real_write_task(task, kd)

        with (
            patch("owlbear_kanban.engine.write_task", side_effect=_crash_first),
            pytest.raises(OSError, match="simulated disk failure"),
        ):
            engine.create_task("crash-victim")

        # Retry: scan finds no files → same ID (1), not 501 from config or 2 from burn
        retry = engine.create_task("after-crash")
        assert retry.id == 1, (
            f"Retry on empty board must get ID 1 (scan-based, no burn); "
            f"got {retry.id}. Config-based burned-ID semantics still active — "
            "allocate_next_id wrote config before write_task crashed."
        )

    def test_ac1_failed_write_does_not_burn_id(self, tmp_path: Path) -> None:
        """AC-1: OSError during file write → no file on disk → same ID recomputed on retry.

        Scan-based allocation: if write_task raises, no file is created.
        The next scan recomputes the same max+1 — no ID is consumed (no burn).
        """
        kanban_dir = _make_scratch_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=False)

        from owlbear_kanban.storage import write_task as _real_write_task  # noqa: PLC0415

        calls: list[int] = []

        def _crash_first(task: object, kd: Path) -> None:
            calls.append(1)
            if len(calls) == 1:
                msg = "simulated disk failure"
                raise OSError(msg)
            _real_write_task(task, kd)

        with (
            patch("owlbear_kanban.engine.write_task", side_effect=_crash_first),
            pytest.raises(OSError, match="simulated disk failure"),
        ):
            engine.create_task("crash-victim")

        task_files = list((kanban_dir / "tasks").glob("*.md"))
        assert task_files == [], (
            f"No task file must exist after a failed write; found {task_files}. Partial state was persisted."
        )

        # Retry: scan still finds no files → same ID, not the next one
        retry_task = engine.create_task("after-crash")
        assert retry_task.id == 1, (
            f"After failed write on empty board, scan finds no files → ID must be 1 (no burn); "
            f"got {retry_task.id}. ID was consumed despite no file being written — "
            "scan-based allocation not yet implemented."
        )

    # ------------------------------------------------------------------
    # AC-2: create_task does not read or write config.next_id
    # ------------------------------------------------------------------

    def test_ac2_create_task_succeeds_without_config_yml(self, tmp_path: Path) -> None:
        """AC-2: scratch board with no config.yml — create_task must succeed WITHOUT creating config.yml."""
        kanban_dir = _make_scratch_board(tmp_path)
        assert not (kanban_dir / "config.yml").exists(), "Pre-condition: no config.yml"

        engine = KanbanEngine(kanban_dir, activity_log=False)
        task = engine.create_task("scratch-task")

        assert task.id == 1
        assert task.title == "scratch-task"
        task_files = list((kanban_dir / "tasks").glob("1-*.md"))
        assert len(task_files) == 1, "Task file must be written to tasks/ on scratch board"
        assert not (kanban_dir / "config.yml").exists(), (
            "create_task must not create config.yml on a scratch board "
            "(scan-based allocation must not call save_config)."
        )

    def test_ac2_create_task_does_not_create_config_yml(self, tmp_path: Path) -> None:
        """AC-2: create_task on scratch board must NOT create config.yml."""
        kanban_dir = _make_scratch_board(tmp_path)
        config_path = kanban_dir / "config.yml"
        assert not config_path.exists(), "Pre-condition: no config.yml"

        engine = KanbanEngine(kanban_dir, activity_log=False)
        engine.create_task("no-config-please")

        assert not config_path.exists(), (
            "create_task must not create config.yml (scan-based allocation does not write config). "
            "allocate_next_id is still calling save_config — replace with scan-based logic."
        )

    def test_ac2_config_next_id_unchanged_after_create_task(self, tmp_path: Path) -> None:
        """AC-2: config.next_id must not be incremented by create_task."""
        kanban_dir = _make_scratch_board(tmp_path)
        (kanban_dir / "config.yml").write_text("next_id: 999\n", encoding="utf-8")
        initial_next_id = load_config(kanban_dir).next_id

        engine = KanbanEngine(kanban_dir, activity_log=False)
        engine.create_task("leave-config-alone")

        after_next_id = load_config(kanban_dir).next_id
        assert after_next_id == initial_next_id, (
            f"config.next_id must be unchanged after create_task (scan-based allocation); "
            f"was {initial_next_id}, got {after_next_id}. "
            "allocate_next_id is still incrementing and saving config.next_id."
        )

    def test_ac2_high_config_next_id_does_not_affect_allocated_id(self, tmp_path: Path) -> None:
        """AC-2: config.next_id=999 with empty task dirs → allocated ID is 1 (scan wins)."""
        kanban_dir = _make_scratch_board(tmp_path)
        (kanban_dir / "config.yml").write_text("next_id: 999\n", encoding="utf-8")

        engine = KanbanEngine(kanban_dir, activity_log=False)
        task = engine.create_task("ignore-config")

        assert task.id == 1, (
            f"Empty task dirs → scan max=0 → ID must be 1, not config.next_id=999; "
            f"got {task.id}. create_task is still reading config.next_id for allocation."
        )

    # ------------------------------------------------------------------
    # AC-3: specific scenario with mixed active and archive prefixes
    # ------------------------------------------------------------------

    def test_ac3_active_1_3_archive_2_5_yields_id_6(self, tmp_path: Path) -> None:
        """AC-3: active prefixes [1, 3] + archive prefixes [2, 5] → create_task produces ID 6."""
        kanban_dir = _make_scratch_board(tmp_path)
        _place_task_stubs(kanban_dir, active_ids=[1, 3], archive_ids=[2, 5])

        engine = KanbanEngine(kanban_dir, activity_log=False)
        task = engine.create_task("scenario-task")

        assert task.id == 6, (
            f"Active prefixes [1,3] + archive prefixes [2,5] → global max=5 → next ID=6; "
            f"got {task.id}. "
            "Scan-based allocation does not combine active+archive for global max."
        )

    # ------------------------------------------------------------------
    # AC-4: concurrent create_task → distinct IDs, config.yml absent/unchanged
    # ------------------------------------------------------------------

    def test_ac4_concurrent_creates_produce_distinct_scan_based_ids(self, tmp_path: Path) -> None:
        """AC-4: 10 concurrent create_task calls on one scratch board -> 10 distinct IDs 1-10.

        Board has config.yml with next_id=500 but no task files. Scan-based allocation
        must produce IDs 1-10 (from file scan). Config-based would produce IDs 500-509.
        This proves both scan-based allocation AND concurrent correctness.
        """
        kanban_dir = _make_scratch_board(tmp_path)
        # High config.next_id distinguishes scan-based (1-10) from config-based (500-509)
        (kanban_dir / "config.yml").write_text("next_id: 500\n", encoding="utf-8")
        n = 10
        results: list[int] = []
        errors: list[Exception] = []
        mutex = threading.Lock()

        def _create_one() -> None:
            try:
                eng = KanbanEngine(kanban_dir, activity_log=False)
                task = eng.create_task("concurrent-task")
                with mutex:
                    results.append(task.id)
            except Exception as exc:  # noqa: BLE001
                with mutex:
                    errors.append(exc)

        threads = [threading.Thread(target=_create_one) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent create_task raised unexpected errors: {errors}"
        assert len(results) == n, f"Expected {n} tasks created; got {len(results)}"
        assert len(set(results)) == n, (
            f"All {n} concurrent creates must have distinct IDs; "
            f"duplicates detected in {sorted(results)}. "
            "Lock scope does not cover the file write — ID collision under concurrency."
        )
        assert max(results) <= n, (
            f"Scan-based IDs on empty board must be 1-{n}; got max={max(results)}. "
            "create_task is reading config.next_id=500 instead of scanning files."
        )

    def test_ac4_config_yml_absent_after_concurrent_creates_on_scratch_board(self, tmp_path: Path) -> None:
        """AC-4: concurrent create_task on scratch board must not create config.yml."""
        kanban_dir = _make_scratch_board(tmp_path)
        config_path = kanban_dir / "config.yml"
        n = 5

        def _create_one() -> None:
            eng = KanbanEngine(kanban_dir, activity_log=False)
            eng.create_task("no-config-concurrent")

        threads = [threading.Thread(target=_create_one) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not config_path.exists(), (
            f"Concurrent create_task on scratch board must not create config.yml; "
            f"found: {config_path}. scan-based allocate_next_id must not write config."
        )

    def test_ac4_config_yml_unchanged_after_concurrent_creates(self, tmp_path: Path) -> None:
        """AC-4: concurrent creates on board with config.yml leave config.next_id unchanged."""
        kanban_dir = _make_scratch_board(tmp_path)
        (kanban_dir / "config.yml").write_text("next_id: 42\n", encoding="utf-8")
        initial_next_id = load_config(kanban_dir).next_id
        n = 5

        def _create_one() -> None:
            eng = KanbanEngine(kanban_dir, activity_log=False)
            eng.create_task("concurrent-config-check")

        threads = [threading.Thread(target=_create_one) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        after_next_id = load_config(kanban_dir).next_id
        assert after_next_id == initial_next_id, (
            f"Concurrent create_task must not modify config.next_id; was {initial_next_id}, got {after_next_id}."
        )

    # ------------------------------------------------------------------
    # AC-5: activity logging defaults and create_task event emission
    # ------------------------------------------------------------------

    def test_ac5_activity_log_default_none_enables_logging(self, tmp_path: Path) -> None:
        """AC-5: KanbanEngine(kanban_dir) with no activity_log arg → logging enabled.

        The default must be True, applied directly — not via reading config.activity_log.
        Observable proof: create_task (the new emission) writes to activity.jsonl.
        """
        kanban_dir = _make_scratch_board(tmp_path)
        engine = KanbanEngine(kanban_dir)  # activity_log=None (default)
        engine.create_task("activity-default-task")

        activity_file = kanban_dir / "activity.jsonl"
        assert activity_file.exists(), (
            "KanbanEngine with default activity_log=None must enable logging "
            "(default must be True, not read from config.activity_log). "
            "create_task does not emit ActivityEvent — not yet implemented."
        )

    def test_ac5_create_task_appends_exactly_one_activity_event(self, tmp_path: Path) -> None:
        """AC-5: a single create_task call appends exactly one ActivityEvent to activity.jsonl."""
        kanban_dir = _make_scratch_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=True)
        engine.create_task("event-count-check")

        events = list_activity_events(kanban_dir)
        assert len(events) == 1, (
            f"create_task must append exactly 1 ActivityEvent; got {len(events)}. "
            "create_task does not yet call _emit_event."
        )

    def test_ac5_activity_event_has_all_six_required_fields(self, tmp_path: Path) -> None:
        """AC-5: ActivityEvent from create_task contains all 6 required model fields."""
        kanban_dir = _make_scratch_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=True)
        task = engine.create_task("field-check-task")

        events = list_activity_events(kanban_dir)
        assert len(events) == 1, f"Expected 1 ActivityEvent from create_task; got {len(events)}"
        evt = events[0]

        # All six required fields must be present and non-trivially set
        assert evt.timestamp, "ActivityEvent.timestamp must be a non-empty string"
        assert evt.task_id == task.id, f"ActivityEvent.task_id must equal created task id {task.id}; got {evt.task_id}"
        assert evt.action, "ActivityEvent.action must be a non-empty string"
        assert evt.source, "ActivityEvent.source must be a non-empty string"
        assert evt.detail is not None, "ActivityEvent.detail must be present (empty string is acceptable)"
        assert evt.task_status_at_start is not None, (
            "ActivityEvent.task_status_at_start must be set for create_task events. "
            "The field is absent — create_task _emit_event call missing task_status_at_start."
        )

    def test_ac5_task_status_at_start_equals_entry_status(self, tmp_path: Path) -> None:
        """AC-5: task_status_at_start in create_task ActivityEvent equals the task entry status."""
        kanban_dir = _make_scratch_board(tmp_path)
        engine = KanbanEngine(kanban_dir, activity_log=True)
        task = engine.create_task("entry-status-task")

        events = list_activity_events(kanban_dir)
        assert len(events) == 1, f"Expected 1 ActivityEvent from create_task; got {len(events)}"
        evt = events[0]

        assert evt.task_status_at_start == task.status, (
            f"ActivityEvent.task_status_at_start must equal the created task's status "
            f"(entry status = {task.status!r}); got {evt.task_status_at_start!r}. "
            "create_task must pass task_status_at_start=entry_status to _emit_event."
        )
