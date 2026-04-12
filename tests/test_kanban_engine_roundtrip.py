"""Integration tests for the native kanban engine against the live 700-file board (#731, RED phase).

Tests perform a live round-trip against the real .owlbear/kanban/tasks/ directory.
All tests skip automatically if the directory is absent or empty (CI / clean-checkout safety).

AC coverage:
  AC1 - Skip guard: every test calls _require_live_board(); skips if tasks_dir absent or zero *.md files
  AC2 - Parse all: read_task() succeeds for every *.md file without suppressed errors
  AC3 - Semantic round-trip: model_dump() equality after write_task + read_task
  AC4 - Config round-trip: load_config → save_config → load_config → model_dump() equality
  AC5 - Count parity: list_tasks() count (unfiltered) == *.md file count
  AC6 - Body content: result.body == original.body verbatim for every round-tripped file
  AC7 - Module-level pytestmark = pytest.mark.slow
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban.config_loader import load_config, save_config
from owlbear_kanban.engine import KanbanEngine
from owlbear_kanban.task_io import read_task, write_task

pytestmark = pytest.mark.slow

# ---------------------------------------------------------------------------
# Live board paths
# ---------------------------------------------------------------------------

_KANBAN_DIR = Path(__file__).resolve().parent.parent / ".owlbear" / "kanban"
_TASKS_DIR = _KANBAN_DIR / "tasks"


# ---------------------------------------------------------------------------
# Skip guard helper (AC1)
# ---------------------------------------------------------------------------


def _require_live_board() -> list[Path]:
    """Return sorted list of *.md task files; pytest.skip if board is absent or empty."""
    if not _TASKS_DIR.exists():
        pytest.skip("Live board absent: .owlbear/kanban/tasks/ does not exist")
    task_files = sorted(_TASKS_DIR.glob("*.md"))
    if not task_files:
        pytest.skip("Live board empty: zero *.md files in .owlbear/kanban/tasks/")
    return task_files


# ===========================================================================
# TestFromAC_LiveBoardRoundTrip
# ===========================================================================


class TestFromAC_LiveBoardRoundTrip:
    """Integration tests for the native engine against the live 700-file board.

    All tests skip automatically if the board directory is absent or holds zero *.md files.
    """

    # -----------------------------------------------------------------------
    # AC2 — Parse all: read_task() succeeds for every *.md file (no suppressed errors)
    # -----------------------------------------------------------------------

    def test_all_task_files_parse_without_error(self) -> None:
        """read_task() succeeds for ALL *.md files — no errors suppressed.

        Contrasts with list_tasks() which silently drops files via contextlib.suppress.
        Fails if any single file raises ValueError, KeyError, or any unexpected exception.
        """
        task_files = _require_live_board()
        parse_errors: list[str] = []
        for path in task_files:
            try:
                read_task(path)
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
        assert not parse_errors, (
            f"{len(parse_errors)} file(s) failed to parse:\n" + "\n".join(parse_errors[:30])
        )

    def test_all_task_files_yield_non_zero_id(self) -> None:
        """Every parsed Task has id > 0 — no zero or negative IDs in live board."""
        task_files = _require_live_board()
        bad_ids: list[str] = []
        for path in task_files:
            try:
                record = read_task(path)
            except Exception:  # noqa: BLE001, S112
                continue  # parse errors handled separately
            if not isinstance(record.id, int) or record.id <= 0:
                bad_ids.append(f"{path.name}: id={record.id!r}")
        assert not bad_ids, "Records with invalid id in live board:\n" + "\n".join(bad_ids)

    # -----------------------------------------------------------------------
    # AC3 — Semantic round-trip: model_dump() equality
    # -----------------------------------------------------------------------

    def test_semantic_roundtrip_model_dump_equality_all_files(self, tmp_path: Path) -> None:
        """write_task then read_task yields identical model_dump() for every live task file.

        Uses model_dump() comparison (not byte comparison) since PyYAML may reformat YAML.
        Fails if any file's semantic data changes across the round-trip.
        """
        task_files = _require_live_board()
        mismatches: list[str] = []
        for path in task_files:
            try:
                original = read_task(path)
            except Exception:  # noqa: BLE001, S112
                continue  # parse errors caught by test_all_task_files_parse_without_error
            tmp_file = tmp_path / path.name
            write_task(tmp_file, original)
            roundtripped = read_task(tmp_file)
            if original.model_dump() != roundtripped.model_dump():
                original_dump = original.model_dump()
                roundtrip_dump = roundtripped.model_dump()
                diffs = [k for k in original_dump if original_dump[k] != roundtrip_dump.get(k)]
                mismatches.append(f"{path.name}: differing keys={diffs}")
        assert not mismatches, (
            f"model_dump() mismatch after round-trip in {len(mismatches)} file(s):\n"
            + "\n".join(mismatches[:20])
        )

    # -----------------------------------------------------------------------
    # AC4 — Config round-trip: load_config → save_config → load_config → model_dump()
    # -----------------------------------------------------------------------

    def test_config_roundtrip_model_dump_equality(self, tmp_path: Path) -> None:
        """load_config → save_config → load_config produces identical model_dump().

        Uses a tmp_path copy of config.yml so the live board is unmodified.
        """
        if not _KANBAN_DIR.exists():
            pytest.skip("Live board absent")
        original_config = load_config(_KANBAN_DIR)
        # save_config writes to tmp_path/config.yml
        save_config(tmp_path, original_config)
        roundtripped_config = load_config(tmp_path)
        assert original_config.model_dump() == roundtripped_config.model_dump()

    def test_config_roundtrip_preserves_vendor_fields(self, tmp_path: Path) -> None:
        """Config round-trip preserves unknown/vendor fields (tui, defaults.class).

        BoardConfig uses extra='allow'; vendor fields must survive save_config → load_config.
        """
        if not _KANBAN_DIR.exists():
            pytest.skip("Live board absent")
        original_config = load_config(_KANBAN_DIR)
        original_dump = original_config.model_dump()
        save_config(tmp_path, original_config)
        roundtripped_config = load_config(tmp_path)
        roundtripped_dump = roundtripped_config.model_dump()
        # tui is a top-level vendor field in the live .owlbear/kanban/config.yml
        assert roundtripped_dump.get("tui") == original_dump.get("tui"), (
            "Vendor field 'tui' lost in config round-trip"
        )
        # defaults.class is a vendor field set on BoardDefaults
        orig_defaults = original_config.defaults.model_dump()
        rt_defaults = roundtripped_config.defaults.model_dump()
        assert rt_defaults.get("class") == orig_defaults.get("class"), (
            "Vendor field 'class' in defaults lost in config round-trip"
        )

    def test_config_roundtrip_preserves_next_id(self, tmp_path: Path) -> None:
        """Config round-trip preserves next_id exactly — critical for ID allocation."""
        if not _KANBAN_DIR.exists():
            pytest.skip("Live board absent")
        original_config = load_config(_KANBAN_DIR)
        save_config(tmp_path, original_config)
        roundtripped_config = load_config(tmp_path)
        assert roundtripped_config.next_id == original_config.next_id, (
            f"next_id changed: {original_config.next_id} → {roundtripped_config.next_id}"
        )

    # -----------------------------------------------------------------------
    # AC5 — Count parity: list_tasks() count == *.md file count (unfiltered)
    # -----------------------------------------------------------------------

    def test_count_parity_list_tasks_vs_file_count(self) -> None:
        """list_tasks() (unfiltered) returns same count as glob('*.md') in tasks dir.

        Exposes any files silently dropped by contextlib.suppress in list_tasks().
        Fails if the engine drops even one task file without raising an error.
        """
        task_files = _require_live_board()
        engine = KanbanEngine(_KANBAN_DIR)
        loaded_tasks = engine.list_tasks()
        file_count = len(task_files)
        task_count = len(loaded_tasks)
        assert task_count == file_count, (
            f"list_tasks() returned {task_count} tasks but {file_count} *.md files exist. "
            f"Discrepancy of {file_count - task_count} silently suppressed file(s)."
        )

    # -----------------------------------------------------------------------
    # AC6 — Body content: result.body == original.body verbatim
    # -----------------------------------------------------------------------

    def test_body_content_preserved_verbatim_all_files(self, tmp_path: Path) -> None:
        """Round-trip preserves markdown body byte-for-byte for every live task file.

        Verifies that write_task does not trim, escape, or reformat the body section.
        """
        task_files = _require_live_board()
        body_mismatches: list[str] = []
        for path in task_files:
            try:
                original = read_task(path)
            except Exception:  # noqa: BLE001, S112
                continue
            tmp_file = tmp_path / path.name
            write_task(tmp_file, original)
            roundtripped = read_task(tmp_file)
            if roundtripped.body != original.body:
                body_mismatches.append(
                    f"{path.name}: original={len(original.body)}b "
                    f"roundtripped={len(roundtripped.body)}b"
                )
        assert not body_mismatches, (
            f"Body content changed in {len(body_mismatches)} file(s):\n"
            + "\n".join(body_mismatches[:20])
        )

    def test_body_field_is_never_none(self) -> None:
        """Every Task parsed from the live board has body as str, never None.

        Task.body defaults to '' — None would indicate a model validation bug.
        """
        task_files = _require_live_board()
        none_body: list[str] = []
        for path in task_files:
            try:
                record = read_task(path)
            except Exception:  # noqa: BLE001, S112
                continue
            if record.body is None:
                none_body.append(path.name)
        assert not none_body, (
            f"body is None (not '') in {len(none_body)} file(s):\n" + "\n".join(none_body)
        )
