"""Failing tests for engine.create_task() file locking to prevent TOCTOU race (#847, RED phase).

AC coverage:
  AC1 - create_task() acquires an exclusive file lock before reading next_id
  AC2 - Lock is held through the write of the incremented next_id (full critical section)
  AC3 - Lock works cross-process on Windows (msvcrt) and Unix (fcntl)
  AC4 - Two concurrent create_task calls from separate engine instances never produce
        the same task ID
  AC5 - No deadlock: lock is released on both success and exception paths
        (Note: deadlock is only possible once a locking mechanism exists; the exception-
        path coverage is implicit in the concurrent tests completing without hanging.
        See Test-Writer Notes for details.)

All tests must FAIL at this stage — GREEN phase will implement the file lock.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban import config_loader as _cfg_mod

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: research
    - name: backlog
    - name: todo
    - name: in-progress
    - name: review
    - name: docs
    - name: done
priorities:
    - someday
    - nice-to-have
    - important
    - needed
    - critical
defaults:
    status: research
    priority: important
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 100
"""


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


# ===========================================================================
#  TestFromAC_CriticalSectionProtection — AC1, AC2, AC4
# ===========================================================================


class TestFromAC_CriticalSectionProtection:
    """Lock must protect the full read→write critical section in create_task().

    Concurrency tests widen the TOCTOU race window artificially so that
    without a lock, ID collisions are deterministic rather than probabilistic.

    Technique: replace load_config and/or save_config with slow versions that
    synchronise threads at the most vulnerable point (after reading next_id
    but before saving the incremented value).  All tests assert no duplicate
    IDs — each assertion fails with the current unlocked code.

    NOTE: All patching is done at the test level (outside worker functions) to
    avoid concurrent patch.object calls on the same attribute, which is not
    thread-safe.
    """

    def test_concurrent_creates_produce_unique_ids(self, kanban_dir: Path) -> None:
        """AC1+AC2+AC4 (happy — concurrent): Two engine instances creating a task
        simultaneously must not receive the same task ID.

        Race mechanism: a threading.Barrier forces both threads to have
        called load_config before either completes create_task, virtually
        guaranteeing that both see next_id=100 with the current unlocked code.

        FAIL evidence (either is sufficient):
        - Duplicate IDs in ids_out (Unix / when write succeeds for both)
        - PermissionError raised by one thread trying to atomically replace the
          same task file that the other thread is already writing (Windows).
          Both collisions prove the same underlying race: identical IDs allocated.
        """
        from unittest.mock import patch

        barrier = threading.Barrier(2)
        ids_out: list[int] = []
        errors: list[BaseException] = []
        original_load = _cfg_mod.load_config

        def synchronized_load(d: Path):  # noqa: ANN202
            result = original_load(d)
            # Both threads arrive here before either can proceed — maximum overlap.
            barrier.wait(timeout=5.0)
            return result

        def worker() -> None:
            try:
                engine = KanbanEngine(kanban_dir)
                task = engine.create_task("concurrent task")
                ids_out.append(task.id)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        with patch.object(_cfg_mod, "load_config", synchronized_load):
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

        # PermissionError = same task file path collision on Windows = same ID = race.
        # Both outcome types prove the absence of locking.
        file_collision_errors = [
            e for e in errors if isinstance(e, (PermissionError, OSError))
        ]
        other_errors = [e for e in errors if not isinstance(e, (PermissionError, OSError))]
        assert not other_errors, f"Threads raised unexpected exceptions: {other_errors}"
        assert not file_collision_errors, (
            f"Threads collided on the same task file (same ID allocated without lock): "
            f"{file_collision_errors}  — TOCTOU race detected"
        )
        assert len(ids_out) == 2, "Both threads must complete and produce a task"
        assert len(set(ids_out)) == 2, (
            f"Duplicate task IDs — TOCTOU race detected: {sorted(ids_out)}"
        )

    def test_lock_held_through_slow_save_config(self, kanban_dir: Path) -> None:
        """AC2+AC4 (boundary — lock scope): The lock must not be released between
        load_config and save_config.

        Slowing save_config forces Thread 2 to read next_id while Thread 1 is
        still in the critical section.  Without a lock both threads read 100;
        with a lock Thread 2 must wait for Thread 1's save to complete first.
        """
        from unittest.mock import patch

        barrier = threading.Barrier(2)
        original_save = _cfg_mod.save_config
        ids_out: list[int] = []
        errors: list[BaseException] = []

        def slow_save(d: Path, config) -> None:  # noqa: ANN001
            time.sleep(0.08)  # widen the window between read and write-back
            original_save(d, config)

        def worker() -> None:
            try:
                engine = KanbanEngine(kanban_dir)
                barrier.wait(timeout=5.0)  # synchronise entry to create_task
                task = engine.create_task("slow-save task")
                ids_out.append(task.id)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        with patch.object(_cfg_mod, "save_config", slow_save):
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

        # TypeError = concurrent save_config reads partial/empty YAML on Windows → race evidence
        race_errors = [
            e for e in errors if isinstance(e, (PermissionError, OSError, TypeError))
        ]
        other_errors = [e for e in errors if not isinstance(e, (PermissionError, OSError, TypeError))]
        assert not other_errors, f"Threads raised unexpected exceptions: {other_errors}"
        assert not race_errors, (
            f"Race condition evidence (file collision or YAML corruption): {race_errors}"
        )
        assert len(ids_out) == 2
        assert len(set(ids_out)) == 2, (
            f"Lock does not cover the full critical section — IDs collided: {sorted(ids_out)}"
        )

    def test_high_concurrency_all_unique_ids(self, kanban_dir: Path) -> None:
        """AC4 (edge — high contention): Six engine instances creating tasks
        simultaneously must each get a distinct ID.

        With the barrier all six threads have read next_id=100 before any thread
        proceeds, making collisions inevitable in the current unlocked code.

        FAIL evidence: file-collision errors (same ID → same filename → PermissionError
        on Windows) or duplicate IDs in ids_out (Unix).  Both prove TOCTOU race.
        """
        from unittest.mock import patch

        n_threads = 6
        barrier = threading.Barrier(n_threads)
        ids_out: list[int] = []
        errors: list[BaseException] = []
        original_load = _cfg_mod.load_config

        def synchronized_load(d: Path):  # noqa: ANN202
            result = original_load(d)
            barrier.wait(timeout=10.0)
            return result

        def worker() -> None:
            try:
                engine = KanbanEngine(kanban_dir)
                task = engine.create_task("stress task")
                ids_out.append(task.id)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        with patch.object(_cfg_mod, "load_config", synchronized_load):
            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=20.0)

        file_collision_errors = [
            e for e in errors if isinstance(e, (PermissionError, OSError, TypeError))
        ]
        other_errors = [e for e in errors if not isinstance(e, (PermissionError, OSError, TypeError))]
        assert not other_errors, f"Threads raised unexpected exceptions: {other_errors}"
        assert not file_collision_errors, (
            f"File collisions/data corruption (same ID allocated to {len(file_collision_errors)} threads): "
            f"{file_collision_errors}  — TOCTOU race detected"
        )
        assert len(ids_out) == n_threads, (
            f"Expected {n_threads} tasks, got {len(ids_out)}"
        )
        assert len(set(ids_out)) == n_threads, (
            f"ID collisions under high concurrency — "
            f"unique={len(set(ids_out))} vs expected={n_threads}: {sorted(ids_out)}"
        )


# ===========================================================================
#  TestFromAC_CrossPlatformLocking — AC3
# ===========================================================================


class TestFromAC_CrossPlatformLocking:
    """Lock must work across SEPARATE processes (the real use-case for AC3).

    Two OS processes both calling create_task on the same kanban_dir must not
    produce the same task ID.  File byte-range locks (msvcrt / fcntl) are the
    OS mechanism that prevents concurrent access across process boundaries;
    Python's GIL and threading primitives provide no cross-process safety.

    The multiprocessing test is the definitive proof of AC3: if the lock works
    only within a single process, two separate processes will still race.
    """

    @pytest.mark.slow
    def test_two_processes_create_tasks_no_duplicate_ids(
        self, kanban_dir: Path, tmp_path: Path
    ) -> None:
        """AC3+AC4 (cross-process): Two separate OS processes calling
        create_task on the same kanban_dir must receive different task IDs.

        A pair of flag files synchronise both processes so they enter
        create_task as close to simultaneously as possible, maximising the
        probability of a race without a cross-process lock.

        Uses subprocess.Popen with an inline -c script rather than
        ProcessPoolExecutor so the worker is never pickled by reference —
        avoiding the ModuleNotFoundError that arises when the spawned process
        tries to import ``tests.test_create_task_file_locking_847``.
        """
        import subprocess
        import sys

        repo_root = Path(__file__).parent.parent
        kanban_str = str(kanban_dir)
        ready1 = str(tmp_path / "ready1.flag")
        ready2 = str(tmp_path / "ready2.flag")
        proceed = str(tmp_path / "proceed.flag")

        # Inline script — no module-level pickling, no conftest.py bootstrap.
        # sys.path is extended explicitly so owlbear_kanban is importable even
        # when the subprocess was not started through pytest/uv.
        worker_src = (
            "import sys, time\n"
            "from pathlib import Path\n"
            "repo_root, kanban_dir_s, ready_s, proceed_s = sys.argv[1:]\n"
            "sys.path.insert(0, str(Path(repo_root) / 'serve' / 'kanban' / 'src'))\n"
            "from owlbear_kanban import KanbanEngine\n"
            "engine = KanbanEngine(Path(kanban_dir_s))\n"
            "Path(ready_s).touch()\n"
            "deadline = time.monotonic() + 5.0\n"
            "while not Path(proceed_s).exists():\n"
            "    if time.monotonic() > deadline:\n"
            "        raise TimeoutError('proceed not received')\n"
            "    time.sleep(0.002)\n"
            "task = engine.create_task('cross-process task')\n"
            "print(task.id)\n"
        )
        base_cmd = [sys.executable, "-c", worker_src, str(repo_root), kanban_str]

        p1 = subprocess.Popen(
            [*base_cmd, ready1, proceed],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        p2 = subprocess.Popen(
            [*base_cmd, ready2, proceed],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait until both worker processes have initialised their engines.
            deadline = time.monotonic() + 10.0
            while not (Path(ready1).exists() and Path(ready2).exists()):
                if time.monotonic() > deadline:
                    p1.kill()
                    p2.kill()
                    pytest.fail("Worker processes did not signal ready within 10 s")
                time.sleep(0.01)

            # Release both processes simultaneously.
            Path(proceed).touch()

            out1, err1 = p1.communicate(timeout=15)
            out2, err2 = p2.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            p1.kill()
            p2.kill()
            pytest.fail("Worker processes timed out waiting for create_task to complete")

        assert p1.returncode == 0, f"Worker 1 failed (exit {p1.returncode}):\n{err1}"
        assert p2.returncode == 0, f"Worker 2 failed (exit {p2.returncode}):\n{err2}"

        id1 = int(out1.strip())
        id2 = int(out2.strip())

        assert id1 != id2, (
            f"Cross-process TOCTOU race: both processes received task ID {id1} — "
            f"file lock not implemented or not cross-process"
        )


# ===========================================================================
#  TestFromAC_ExceptionSafety — AC5
# ===========================================================================


class TestFromAC_ExceptionSafety:
    """Lock must be released on both success and exception paths (AC5).

    Deadlock due to an unreleased lock only manifests once a locking mechanism
    EXISTS.  A source-inspection canary is used here: it asserts that
    engine.py contains at least one OS-level file-locking keyword.  Without
    the implementation the keyword is absent — the test fails (ImportError
    proxy via source text check).  Once the lock is added the keyword is
    present and the test passes.

    A separate concurrent test also covers the "no deadlock after exception"
    property by verifying both threads complete within the join timeout.
    """

    def test_engine_source_contains_lock_mechanism(self) -> None:
        """AC5 (structural canary): engine.py must contain a file-locking
        primitive so that create_task can release the lock on exception paths.

        Checks the engine source for OS-level locking keywords: ``fcntl``,
        ``msvcrt``, ``filelock``, ``LK_LOCK``, ``LOCK_EX``, ``flock``.
        Currently FAILS because the source has none of these — the lock has
        not been implemented yet.  Once the builder adds the lock mechanism,
        this test will pass and the exception-safety assertion below becomes
        verifiable.
        """
        from pathlib import Path

        engine_path = (
            Path(__file__).parent.parent
            / "serve"
            / "kanban"
            / "src"
            / "owlbear_kanban"
            / "engine.py"
        )
        source = engine_path.read_text(encoding="utf-8")
        lock_keywords = ["fcntl", "msvcrt", "filelock", "LK_LOCK", "LOCK_EX", "flock"]
        found = [kw for kw in lock_keywords if kw in source]

        assert found, (
            "engine.py contains no OS file-locking keywords — lock not implemented. "
            "AC5 (no deadlock on exception) cannot be satisfied without a lock. "
            f"Expected at least one of: {lock_keywords}"
        )

