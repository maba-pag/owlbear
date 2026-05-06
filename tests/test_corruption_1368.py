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

from __future__ import annotations

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

    def test_non_utf8_in_tasks_dir_does_not_raise_unicode_error(
        self, tmp_path: Path
    ) -> None:
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

    def test_non_utf8_in_tasks_dir_returns_corruption_error(
        self, tmp_path: Path
    ) -> None:
        """AC-2: detect_corruption must return CorruptionError for non-UTF8 tasks/ file.

        RED: current code raises UnicodeDecodeError instead of returning CorruptionError.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "tasks" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError), (
            f"Expected CorruptionError instance, got {type(result).__name__!r}"
        )

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
        assert result.code == ERR_CORRUPT_ENCODING, (
            f"Expected code ERR_CORRUPT_ENCODING, got {result.code!r}"
        )

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
        assert any(
            kw in result.detail.lower()
            for kw in ("encoding", "decode", "utf-8", "utf8", "unicode")
        ), (
            f"detail must reference the encoding/decode failure, got {result.detail!r}"
        )

    # -----------------------------------------------------------------
    # archive/ directory — AC-1 (no UnicodeDecodeError raised)
    # -----------------------------------------------------------------

    def test_non_utf8_in_archive_dir_does_not_raise_unicode_error(
        self, tmp_path: Path
    ) -> None:
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

    def test_non_utf8_in_archive_dir_returns_corruption_error(
        self, tmp_path: Path
    ) -> None:
        """AC-2: detect_corruption must return CorruptionError for non-UTF8 archive/ file.

        RED: current code raises UnicodeDecodeError instead.
        """
        board_dir = _make_board(tmp_path)
        bad_file = board_dir / "archive" / "1001-broken.md"
        bad_file.write_bytes(_NON_UTF8_BYTES)
        config = load_config(board_dir)

        result = detect_corruption(bad_file, config)
        assert isinstance(result, CorruptionError), (
            f"Expected CorruptionError instance, got {type(result).__name__!r}"
        )

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
        assert result.code == ERR_CORRUPT_ENCODING, (
            f"Expected code ERR_CORRUPT_ENCODING, got {result.code!r}"
        )

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
        assert any(
            kw in result.detail.lower()
            for kw in ("encoding", "decode", "utf-8", "utf8", "unicode")
        ), (
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
        assert result is None, (
            f"Expected None for clean UTF-8 file, got {result!r}"
        )
