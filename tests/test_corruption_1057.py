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

from __future__ import annotations


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
            f"ERR_CORRUPT_* has extra codes with no Brief §4.1 authority (must be removed): "
            f"{sorted(extra)}"
        )
        assert not missing, (
            f"ERR_CORRUPT_* is missing Brief §4.1 codes (must be added): {sorted(missing)}"
        )
