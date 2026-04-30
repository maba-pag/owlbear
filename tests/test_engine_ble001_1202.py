"""RED-phase tests for narrow exception handling (BLE001) in engine.py (task #1202).

AC coverage:
- AC1 (line 697): list_tasks archive scan — except CorruptionError: replaces except Exception: (td:2)
- AC2 (line 733): list_tasks main scan — except CorruptionError: replaces except Exception as _exc: (td:2)
- AC3 (line 1589): sweep — except (FileNotFoundError, ValueError, KeyError, CorruptionError): (td:2)
- AC4 (line 1676): repair_storage quarantine — except (ValueError, KanbanError, OSError): (td:2)
- AC5 (line 2342): pick_tasks — split ImportError/else/(KanbanError, OSError, ValueError) (td:2)
- AC6: no # noqa: BLE001 suppressions remain in engine.py (td:1)
- AC7: ruff check serve/kanban exits clean (td:1)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import RepairOutcome

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ENGINE_PY = (
    Path(__file__).parents[1] / "serve" / "kanban" / "src" / "owlbear_kanban" / "engine.py"
)
_SERVE_KANBAN = Path(__file__).parents[1] / "serve" / "kanban"
_PROJECT_ROOT = Path(__file__).parents[1]

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
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
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map:
        research: researcher
        backlog: architect
        todo: builder
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# Minimal placeholder — only needs to exist on disk; read_task is mocked in these tests
_PLACEHOLDER = "placeholder"


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_engine(base_dir: Path) -> KanbanEngine:
    return KanbanEngine(_make_board(base_dir), activity_log=False)


def _make_view(base_dir: Path) -> AgentView:
    return AgentView(_make_engine(base_dir))


# ---------------------------------------------------------------------------
# AC1: list_tasks archive scan (line 697) — except CorruptionError:
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksArchiveScanExceptions:
    """AC1: Non-CorruptionError from read_task in archive scan must propagate after narrowing."""

    def test_archive_scan_non_narrowed_exception_propagates(self, tmp_path: Path) -> None:
        """Error path: RuntimeError from read_task is NOT caught by except CorruptionError:.

        Currently: caught by broad except Exception: -> list_tasks returns normally.
        After fix: propagates -> list_tasks raises RuntimeError.
        """
        board = _make_board(tmp_path)
        (board / "archive" / "1-task.md").write_text(_PLACEHOLDER, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        with (
            patch("owlbear_kanban.engine.read_task", side_effect=RuntimeError("unexpected")),
            pytest.raises(RuntimeError, match="unexpected"),
        ):
            engine.list_tasks()

    def test_archive_scan_attribute_error_propagates(self, tmp_path: Path) -> None:
        """Boundary: AttributeError (distinct type) also propagates after narrowing."""
        board = _make_board(tmp_path)
        (board / "archive" / "2-task.md").write_text(_PLACEHOLDER, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        with (
            patch("owlbear_kanban.engine.read_task", side_effect=AttributeError("attr")),
            pytest.raises(AttributeError),
        ):
            engine.list_tasks()


# ---------------------------------------------------------------------------
# AC2: list_tasks main task scan (line 733) — except CorruptionError:
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksMainScanExceptions:
    """AC2: Non-CorruptionError from read_task in main scan must propagate after narrowing.

    The redundant isinstance check is also removed: before, both branches of the
    isinstance check did continue (swallowing all exceptions); after, only
    CorruptionError triggers continue -- anything else propagates.
    """

    def test_main_scan_non_narrowed_exception_propagates(self, tmp_path: Path) -> None:
        """Error path: RuntimeError from read_task propagates from main task scan.

        Currently: caught by except Exception as _exc: -> silently skipped.
        After fix: except CorruptionError: does not match -> propagates.
        """
        board = _make_board(tmp_path)
        (board / "tasks" / "1-task.md").write_text(_PLACEHOLDER, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        with (
            patch("owlbear_kanban.storage.detect_corruption", return_value=None),
            patch("owlbear_kanban.engine.read_task", side_effect=RuntimeError("scan-err")),
            pytest.raises(RuntimeError, match="scan-err"),
        ):
            engine.list_tasks()

    def test_main_scan_oserror_propagates(self, tmp_path: Path) -> None:
        """Boundary: OSError is not in the narrowed tuple -- must propagate.

        Currently: broad except Exception: catches OSError silently.
        After fix: except CorruptionError: does not match OSError -> propagates.
        """
        board = _make_board(tmp_path)
        (board / "tasks" / "1-task.md").write_text(_PLACEHOLDER, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        with (
            patch("owlbear_kanban.storage.detect_corruption", return_value=None),
            patch("owlbear_kanban.engine.read_task", side_effect=OSError("io")),
            pytest.raises(OSError),
        ):
            engine.list_tasks()


# ---------------------------------------------------------------------------
# AC3: sweep (line 1589) -- except (FileNotFoundError, ValueError, KeyError, CorruptionError):
# ---------------------------------------------------------------------------


class TestFromAC_SweepExceptions:
    """AC3: Exceptions outside the narrow tuple must propagate from KanbanEngine.sweep()."""

    def test_sweep_non_narrowed_exception_propagates(self, tmp_path: Path) -> None:
        """Error path: RuntimeError from read_task propagates from sweep loop.

        Currently: except Exception: -> continue (silently swallowed).
        After fix: RuntimeError not in (FileNotFoundError, ValueError, KeyError, CorruptionError)
        -> propagates.
        """
        board = _make_board(tmp_path)
        (board / "tasks" / "1-task.md").write_text(_PLACEHOLDER, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        with (
            patch("owlbear_kanban.engine.read_task", side_effect=RuntimeError("sweep-err")),
            pytest.raises(RuntimeError, match="sweep-err"),
        ):
            engine.sweep()

    def test_sweep_oserror_propagates(self, tmp_path: Path) -> None:
        """Boundary: PermissionError (OSError subclass, not FileNotFoundError) is not in the narrow tuple.

        Currently: broad except Exception: swallows it.
        After fix: PermissionError not in (FileNotFoundError, ValueError, KeyError, CorruptionError)
        -> propagates.
        """
        board = _make_board(tmp_path)
        (board / "tasks" / "1-task.md").write_text(_PLACEHOLDER, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        with (
            patch("owlbear_kanban.engine.read_task", side_effect=PermissionError("no-access")),
            pytest.raises(PermissionError),
        ):
            engine.sweep()


# ---------------------------------------------------------------------------
# AC4: repair_storage quarantine create_task (line 1676) -- except (ValueError, KanbanError, OSError):
# ---------------------------------------------------------------------------


class TestFromAC_RepairStorageExceptions:
    """AC4: Exceptions outside (ValueError, KanbanError, OSError) from create_task propagate."""

    def _fake_quarantine_outcome(self) -> RepairOutcome:
        return RepairOutcome(
            task_id=1,
            file_path="/fake/1-task.md",
            code="ERR_CORRUPT_DELIMITERS",
            action="quarantined",
            detail="test delimiter missing",
        )

    def test_repair_storage_runtime_error_from_create_task_propagates(
        self, tmp_path: Path
    ) -> None:
        """Error path: RuntimeError from create_task propagates.

        Currently: except Exception as _exc: -> creates failure RepairOutcome (no propagation).
        After fix: RuntimeError not in (ValueError, KanbanError, OSError) -> propagates.
        """
        engine = _make_engine(tmp_path)
        outcome = self._fake_quarantine_outcome()

        with (
            patch("owlbear_kanban.corruption.scan_and_fix", return_value=[outcome]),
            patch.object(KanbanEngine, "create_task", side_effect=RuntimeError("ct-err")),
            pytest.raises(RuntimeError, match="ct-err"),
        ):
            engine.repair_storage()

    def test_repair_storage_type_error_from_create_task_propagates(
        self, tmp_path: Path
    ) -> None:
        """Boundary: TypeError also propagates -- not in (ValueError, KanbanError, OSError).

        Currently: absorbed into failure RepairOutcome.
        After fix: propagates.
        """
        engine = _make_engine(tmp_path)
        outcome = self._fake_quarantine_outcome()

        with (
            patch("owlbear_kanban.corruption.scan_and_fix", return_value=[outcome]),
            patch.object(KanbanEngine, "create_task", side_effect=TypeError("type-err")),
            pytest.raises(TypeError, match="type-err"),
        ):
            engine.repair_storage()


# ---------------------------------------------------------------------------
# AC5: pick_tasks decisions import restructuring (line 2342)
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksImportRestructuring:
    """AC5: pick_tasks try-block split -- except ImportError for import failure;
    except (KanbanError, OSError, ValueError) for resolve_pending_drs failures;
    exceptions outside each set propagate.
    """

    def test_pick_tasks_import_runtime_error_propagates(self, tmp_path: Path) -> None:
        """Error path: RuntimeError from importlib.import_module propagates.

        Currently: broad except Exception: catches and logs -> pick_tasks continues.
        After fix: except ImportError: does not match RuntimeError -> propagates.
        """
        view = _make_view(tmp_path)

        with (
            patch("importlib.import_module", side_effect=RuntimeError("import-crash")),
            pytest.raises(RuntimeError, match="import-crash"),
        ):
            view.pick_tasks()

    def test_pick_tasks_resolve_pending_drs_import_error_propagates(
        self, tmp_path: Path
    ) -> None:
        """Edge: ImportError from resolve_pending_drs propagates after restructuring.

        In the restructured code the outer except ImportError catches only failures of
        importlib.import_module itself. The inner except (KanbanError, OSError, ValueError)
        does NOT match ImportError, so ImportError from resolve_pending_drs propagates.

        Currently: single broad except Exception: swallows it.
        After fix: propagates.
        """
        view = _make_view(tmp_path)
        mock_decisions = MagicMock()
        mock_decisions.resolve_pending_drs.side_effect = ImportError("no inner module")

        with (
            patch("importlib.import_module", return_value=mock_decisions),
            pytest.raises(ImportError, match="no inner module"),
        ):
            view.pick_tasks()

    def test_pick_tasks_resolve_pending_drs_runtime_error_propagates(
        self, tmp_path: Path
    ) -> None:
        """Boundary: RuntimeError from resolve_pending_drs is not in (KanbanError, OSError, ValueError).

        Currently: broad except Exception: swallows it.
        After fix: inner except (KanbanError, OSError, ValueError) does not match -> propagates.
        """
        view = _make_view(tmp_path)
        mock_decisions = MagicMock()
        mock_decisions.resolve_pending_drs.side_effect = RuntimeError("dr-crash")

        with (
            patch("importlib.import_module", return_value=mock_decisions),
            pytest.raises(RuntimeError, match="dr-crash"),
        ):
            view.pick_tasks()


# ---------------------------------------------------------------------------
# AC6: no # noqa: BLE001 suppressions remain in engine.py (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_NoBleSuppressions:
    """AC6: All # noqa: BLE001 suppression comments must be removed from engine.py."""

    def test_engine_py_has_no_ble001_noqa(self) -> None:
        """engine.py must contain no # noqa: BLE001 suppression comments.

        Currently: 5 sites have # noqa: BLE001 (lines 697, 733, 1589, 1676, 2342).
        After fix: all broad except clauses replaced -> suppressions no longer needed.
        """
        content = _ENGINE_PY.read_text(encoding="utf-8")
        assert "# noqa: BLE001" not in content, (
            "engine.py still contains # noqa: BLE001 suppressions -- "
            "all 5 BLE001 sites must be narrowed before suppressions are removed"
        )


# ---------------------------------------------------------------------------
# AC7: ruff check serve/kanban exits clean (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_RuffClean:
    """AC7: ruff check serve/kanban must exit 0 -- no BLE001 violations."""

    def test_ruff_ble001_check_passes(self) -> None:
        """ruff check with --ignore-noqa on serve/kanban must exit 0.

        --ignore-noqa forces ruff to report actual violations regardless of noqa comments,
        so this test fails while engine.py still has the 5 broad except clauses.
        After fix: all handlers narrowed -> ruff exits 0 even without noqa suppressions.
        """
        result = subprocess.run(
            [
                "uv",
                "run",
                "ruff",
                "check",
                str(_SERVE_KANBAN),
                "--select",
                "BLE001",
                "--ignore-noqa",
            ],
            capture_output=True,
            text=True,
            cwd=_PROJECT_ROOT,
        )
        assert result.returncode == 0, (
            f"ruff BLE001 check (--no-noqa) failed:\n{result.stdout}\n{result.stderr}"
        )
