from __future__ import annotations

# --- merged from tests/test_corruption_1057.py ---
"""C-12: GREEN — corruption detection & auto-fix failing tests (revised after arch review).

Task: #1057 (Brief C #1043) — paper-c.md §4
AC:   CLEANUP-EXPORTS, EXACT-SET, REG

Architecture review (2026-04-22) corrected the original AC:
  - 'forbidden-field' and 'orphan-archive-ref' are NOT Brief §4.1 modes.
  - Brief §4.1 row 3 explicitly covers both missing required fields AND the
    forbidden claimed_by field (detail="forbidden field claimed_by present"),
    both returning ERR_CORRUPT_MISSING_FIELD.
  - The 9 §4.1 codes are: DELIMITERS, DUPLICATE_ID, MISSING_FIELD, TYPE_MISMATCH,
    YAML_PARSE, ID_FILENAME_MISMATCH, DUPLICATE_LOCATION, INVALID_STATUS, INVALID_PRIORITY.

C-03 tests (serve/kanban/tests/test_corruption.py) cover:
  - AC-C17: positive detection for all 9 modes (modes 1-9)
  - AC-C18: read_task raises CorruptionError(code=...) for every single-file detectable mode
    (modes 1, 3-9); modes 2 and 7 are board-level, covered by scan_and_fix / list_tasks
  - AC-C21: CorruptionError subclass shape (code, user_message, file_path)
  - AC-C22: auto-fix matrix per (mode, field, default) triple including claimed_by
    quarantine via ERR_CORRUPT_MISSING_FIELD + detail="forbidden field claimed_by present"

This file covers the gap the C-03 suite does not:
  - AC-CLEANUP: Two dead codes added by the prior builder pass
    (ERR_CORRUPT_FORBIDDEN_FIELD, ERR_CORRUPT_ORPHAN_ARCHIVE_REF) must be removed.
    The C-03 taxonomy check uses issubset (permits extra codes); this file enforces
    the exact Brief §4.1 set with no extras.
"""


# ---------------------------------------------------------------------------
# TestFromAC_CleanupDeadCodes — AC-CLEANUP: remove codes with no Brief §4.1 authority
# ---------------------------------------------------------------------------


class TestFromAC_CleanupDeadCodes:
    """AC-CLEANUP: ERR_CORRUPT_FORBIDDEN_FIELD and ERR_CORRUPT_ORPHAN_ARCHIVE_REF must be
    removed from corruption.py.  Neither appears in Brief C §4.1.  They were added by the
    prior builder pass based on an incorrect AC, and must be deleted together with:
      - The FORBIDDEN_FIELD type definition (corruption.py ~line 85)
      - The ORPHAN_ARCHIVE_REF type definition (corruption.py ~line 92)
      - The storage.py compatibility shim that rewrites FORBIDDEN_FIELD → MISSING_FIELD
      - The explicit FORBIDDEN_FIELD branch in attempt_repair
    """

    def test_ac_cleanup_forbidden_field_not_exported(self) -> None:
        """AC-CLEANUP: ERR_CORRUPT_FORBIDDEN_FIELD must NOT be exported from corruption module.

        Brief C §4.1 has no 'forbidden-field' error code.  claimed_by detection is
        mode 3 (ERR_CORRUPT_MISSING_FIELD, detail='forbidden field claimed_by present')
        per §4.1 row 3 and §4.2.
        """
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        assert not hasattr(m, "ERR_CORRUPT_FORBIDDEN_FIELD"), (
            "ERR_CORRUPT_FORBIDDEN_FIELD is a dead code with no Brief §4.1 authority. "
            "Remove it from corruption.py per AC-CLEANUP."
        )

    def test_ac_cleanup_orphan_archive_ref_not_exported(self) -> None:
        """AC-CLEANUP: ERR_CORRUPT_ORPHAN_ARCHIVE_REF must NOT be exported from corruption module.

        Brief C §4.1 defines exactly 9 modes; 'orphan-archive-ref' is not among them.
        It was invented by the original (incorrect) AC and must be removed per AC-CLEANUP.
        """
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        assert not hasattr(m, "ERR_CORRUPT_ORPHAN_ARCHIVE_REF"), (
            "ERR_CORRUPT_ORPHAN_ARCHIVE_REF is a dead code with no Brief §4.1 authority. "
            "Remove it from corruption.py per AC-CLEANUP."
        )

    def test_ac_cleanup_exact_brief_c41_code_set(self) -> None:
        """AC-CLEANUP + AC-C17: ERR_CORRUPT_* exports must be exactly the 9 Brief §4.1 codes.

        The prior builder pass added two extra codes.  The C-03 taxonomy check uses
        issubset (allows extras); this test enforces the exact Brief §4.1 set — no
        more, no less.

        Expected set per §4.1:
          DELIMITERS, DUPLICATE_ID, MISSING_FIELD, TYPE_MISMATCH, YAML_PARSE,
          ID_FILENAME_MISMATCH, DUPLICATE_LOCATION, INVALID_STATUS, INVALID_PRIORITY
        """
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        expected = {
            "ERR_CORRUPT_DELIMITERS",
            "ERR_CORRUPT_DUPLICATE_ID",
            "ERR_CORRUPT_MISSING_FIELD",
            "ERR_CORRUPT_TYPE_MISMATCH",
            "ERR_CORRUPT_YAML_PARSE",
            "ERR_CORRUPT_ID_FILENAME_MISMATCH",
            "ERR_CORRUPT_DUPLICATE_LOCATION",
            "ERR_CORRUPT_INVALID_STATUS",
            "ERR_CORRUPT_INVALID_PRIORITY",
        }
        actual = {name for name in dir(m) if name.startswith("ERR_CORRUPT_")}
        extra = actual - expected
        missing = expected - actual
        assert not extra, (
            f"ERR_CORRUPT_* has extra codes with no Brief §4.1 authority (must be removed): {sorted(extra)}"
        )
        assert not missing, f"ERR_CORRUPT_* is missing Brief §4.1 codes (must be added): {sorted(missing)}"


# --- merged from tests/test_corruption_1368.py ---
"""P1-05: Kanban corruption scanner encoding hardening — failing tests (RED phase).

Task: #1368 — test_corruption_1368
AC: detect_corruption() must handle non-UTF8 binary files by returning
    CorruptionError(code=ERR_CORRUPT_ENCODING) instead of raising UnicodeDecodeError.

Bug: detect_corruption() calls path.read_text(encoding='utf-8') but only catches
OSError, not UnicodeDecodeError — archived files with non-UTF8 bytes produce a 500.

RED phase: ERR_CORRUPT_ENCODING does not exist yet (added by #1369), so tests
that import it fail with ImportError. The remaining tests fail because the current
code raises UnicodeDecodeError instead of returning CorruptionError.
"""


from pathlib import Path

from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import CorruptionError, detect_corruption

# ---------------------------------------------------------------------------
# Board helpers (mirrors serve/kanban/tests/test_corruption.py)
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
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""

# Non-UTF8 bytes wrapped in valid-looking --- delimiters.
# The delimiters are ASCII-safe; the UnicodeDecodeError fires during
# read_text(encoding='utf-8') before any delimiter parsing occurs.
_NON_UTF8_BYTES = b"---\nid: 1001\ntitle: broken\n---\n\x80\x81\x82\x83 bad bytes"

_VALID_TASK = """\
---
id: 1001
title: Valid task
status: todo
priority: needed
created: "2026-04-21T10:00:00+00:00"
updated: "2026-04-21T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

## Notes

Some content.
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory structure under *base_dir*."""
    board_dir = base_dir / "board"
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board_dir / "tasks").mkdir(exist_ok=True)
    (board_dir / "archive").mkdir(exist_ok=True)
    return board_dir


# ---------------------------------------------------------------------------
# TestFromAC_EncodingHardening
# ---------------------------------------------------------------------------


class TestFromAC_EncodingHardening:
    """AC: detect_corruption() encoding hardening for non-UTF8 task and archive files.

    AC lines covered:
    - AC-1 (td:2): binary fixture in tasks/ and archive/ does not propagate UnicodeDecodeError
    - AC-2 (td:2): returns CorruptionError with code=ERR_CORRUPT_ENCODING, file_path set,
      detail non-empty
    - AC-3 (td:1): valid UTF-8 task returns None (regression guard)
    """

    # -----------------------------------------------------------------
    # tasks/ directory — AC-1 (no UnicodeDecodeError raised)
    # -----------------------------------------------------------------

    def test_non_utf8_in_tasks_dir_does_not_raise_unicode_error(self, tmp_path: Path) -> None:
        """AC-1: Non-UTF8 file under tasks/ must not propagate UnicodeDecodeError.

        RED: current code raises UnicodeDecodeError from read_text(encoding='utf-8').
        The test fails because the exception propagates instead of being caught.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "tasks" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        # Must return normally — not raise UnicodeDecodeError
        result = detect_corruption(bad_file, config)
        assert result is not None, "Expected CorruptionError return, got None"

    # -----------------------------------------------------------------
    # tasks/ directory — AC-2 (CorruptionError shape)
    # -----------------------------------------------------------------

    def test_non_utf8_in_tasks_dir_returns_corruption_error(self, tmp_path: Path) -> None:
        """AC-2: detect_corruption must return CorruptionError for non-UTF8 tasks/ file.

        RED: current code raises UnicodeDecodeError instead of returning CorruptionError.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "tasks" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError), f"Expected CorruptionError instance, got {type(result).__name__!r}"

    def test_non_utf8_in_tasks_dir_code_is_encoding(self, tmp_path: Path) -> None:
        """AC-2: CorruptionError for non-UTF8 tasks/ file has .code == ERR_CORRUPT_ENCODING.

        RED: ImportError — ERR_CORRUPT_ENCODING not yet defined (#1369 adds it).
        Also fails because UnicodeDecodeError propagates instead of CorruptionError returned.
        """
        from owlbear_kanban.corruption import ERR_CORRUPT_ENCODING  # noqa: PLC0415

        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "tasks" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError)
        assert result.code == ERR_CORRUPT_ENCODING, f"Expected code ERR_CORRUPT_ENCODING, got {result.code!r}"

    def test_non_utf8_in_tasks_dir_file_path_is_set(self, tmp_path: Path) -> None:
        """AC-2: CorruptionError for non-UTF8 tasks/ file has .file_path set.

        RED: UnicodeDecodeError propagates — CorruptionError never constructed.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "tasks" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError)
        assert result.file_path is not None, "file_path must be set on the CorruptionError"
        assert result.file_path == str(bad_file)

    def test_non_utf8_in_tasks_dir_detail_is_non_empty(self, tmp_path: Path) -> None:
        """AC-2: CorruptionError for non-UTF8 tasks/ file has a non-empty .detail string.

        RED: UnicodeDecodeError propagates — CorruptionError never constructed.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "tasks" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError)
        assert isinstance(result.detail, str), "detail must be a string"
        assert any(kw in result.detail.lower() for kw in ("encoding", "decode", "utf-8", "utf8", "unicode")), (
            f"detail must reference the encoding/decode failure, got {result.detail!r}"
        )

    # -----------------------------------------------------------------
    # archive/ directory — AC-1 (no UnicodeDecodeError raised)
    # -----------------------------------------------------------------

    def test_non_utf8_in_archive_dir_does_not_raise_unicode_error(self, tmp_path: Path) -> None:
        """AC-1: Non-UTF8 file under archive/ must not propagate UnicodeDecodeError.

        RED: current code raises UnicodeDecodeError from read_text(encoding='utf-8').
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "archive" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert result is not None, "Expected CorruptionError return, got None"

    # -----------------------------------------------------------------
    # archive/ directory — AC-2 (CorruptionError shape)
    # -----------------------------------------------------------------

    def test_non_utf8_in_archive_dir_returns_corruption_error(self, tmp_path: Path) -> None:
        """AC-2: detect_corruption must return CorruptionError for non-UTF8 archive/ file.

        RED: current code raises UnicodeDecodeError instead.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "archive" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError), f"Expected CorruptionError instance, got {type(result).__name__!r}"

    def test_non_utf8_in_archive_dir_code_is_encoding(self, tmp_path: Path) -> None:
        """AC-2: CorruptionError for non-UTF8 archive/ file has .code == ERR_CORRUPT_ENCODING.

        RED: ImportError — ERR_CORRUPT_ENCODING not yet defined (#1369 adds it).
        """
        from owlbear_kanban.corruption import ERR_CORRUPT_ENCODING  # noqa: PLC0415

        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "archive" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError)
        assert result.code == ERR_CORRUPT_ENCODING, f"Expected code ERR_CORRUPT_ENCODING, got {result.code!r}"

    def test_non_utf8_in_archive_dir_file_path_is_set(self, tmp_path: Path) -> None:
        """AC-2: CorruptionError for non-UTF8 archive/ file has .file_path set.

        RED: UnicodeDecodeError propagates — CorruptionError never constructed.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "archive" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError)
        assert result.file_path is not None, "file_path must be set on the CorruptionError"
        assert result.file_path == str(bad_file)

    def test_non_utf8_in_archive_dir_detail_is_non_empty(self, tmp_path: Path) -> None:
        """AC-2: CorruptionError for non-UTF8 archive/ file has a non-empty .detail string.

        RED: UnicodeDecodeError propagates — CorruptionError never constructed.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "archive" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError)
        assert isinstance(result.detail, str), "detail must be a string"
        assert any(kw in result.detail.lower() for kw in ("encoding", "decode", "utf-8", "utf8", "unicode")), (
            f"detail must reference the encoding/decode failure, got {result.detail!r}"
        )

    # -----------------------------------------------------------------
    # Regression guard — AC-3
    # -----------------------------------------------------------------

    def test_valid_utf8_task_returns_none(self, tmp_path: Path) -> None:
        """AC-3: detect_corruption returns None for a well-formed UTF-8 task file.

        Regression guard: encoding hardening must not break processing of valid files.
        RED: ImportError — ERR_CORRUPT_ENCODING not yet defined; import below fails.
        """
        from owlbear_kanban.corruption import ERR_CORRUPT_ENCODING  # noqa: PLC0415, F401

        board_dir = _make_board(tmp_path)
        task_file = board_dir / "tasks" / "1001-valid.md"
        task_file.write_text(_VALID_TASK, encoding="utf-8")
        config = load_config(board_dir)

        result = detect_corruption(task_file, config)
        assert result is None, f"Expected None for clean UTF-8 file, got {result!r}"
