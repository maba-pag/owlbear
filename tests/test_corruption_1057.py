"""C-12: GREEN — corruption detection & auto-fix failing tests.

Task: #1057 (Brief C #1043) — paper-c.md §4, §8.4
AC:   C17, C18, C21, C22

The C-12 AC names 9 modes:
  missing-frontmatter, duplicate-id, forbidden-field, id-mismatch,
  missing-required-field, invalid-field-type, status-out-of-range,
  duplicate-location, orphan-archive-ref

The existing C-03 implementation covers 9 codes but uses ERR_CORRUPT_MISSING_FIELD
for BOTH "forbidden-field" and "missing-required-field" (no dedicated code for each).
The 9th C-12 mode ("orphan-archive-ref") has no corresponding ERR_CORRUPT_* code at all.

These tests target the AC gaps:
  1. ERR_CORRUPT_FORBIDDEN_FIELD dedicated code (C-12 names it as a distinct mode)
  2. detect_corruption returns ERR_CORRUPT_FORBIDDEN_FIELD for claimed_by present
  3. scan_corruption() read-only scan function (needed for engine.scan_corruption per §4.3)
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban.storage import load_config

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
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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


# ---------------------------------------------------------------------------
# TestFromAC_ForbiddenFieldCode — AC-C17 (forbidden-field as distinct mode)
# ---------------------------------------------------------------------------


class TestFromAC_ForbiddenFieldCode:
    """AC-C17: C-12 lists 'forbidden-field' as a distinct mode from 'missing-required-field'.

    Per C-12 AC, these are two of the named 9 modes and should map to two distinct
    ERR_CORRUPT_* codes. The builder must export ERR_CORRUPT_FORBIDDEN_FIELD and
    update detect_corruption to return it (not ERR_CORRUPT_MISSING_FIELD) when
    claimed_by is present in a tasks/ file.
    """

    def test_ac_c17_err_corrupt_forbidden_field_exported(self) -> None:
        """AC-C17: ERR_CORRUPT_FORBIDDEN_FIELD must be exported from corruption.py."""
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        assert hasattr(m, "ERR_CORRUPT_FORBIDDEN_FIELD"), (
            "C-12 AC names 'forbidden-field' as a distinct mode from 'missing-required-field'. "
            "Expected ERR_CORRUPT_FORBIDDEN_FIELD to be exported from corruption.py."
        )

    def test_ac_c17_forbidden_field_code_is_corruption_error_subclass(self) -> None:
        """AC-C21: ERR_CORRUPT_FORBIDDEN_FIELD must be a subclass of CorruptionError."""
        import owlbear_kanban.corruption as m  # noqa: PLC0415
        from owlbear_kanban.corruption import CorruptionError  # noqa: PLC0415

        cls = getattr(m, "ERR_CORRUPT_FORBIDDEN_FIELD", None)
        assert cls is not None, "ERR_CORRUPT_FORBIDDEN_FIELD not exported from corruption.py"
        assert issubclass(cls, CorruptionError), (
            "ERR_CORRUPT_FORBIDDEN_FIELD must be a CorruptionError subclass per AC-C21"
        )

    def test_ac_c17_detect_corruption_returns_forbidden_field_for_claimed_by(
        self, tmp_path: Path
    ) -> None:
        """AC-C17: detect_corruption on tasks/ with non-null claimed_by returns ERR_CORRUPT_FORBIDDEN_FIELD.

        C-12 names 'forbidden-field' as its own distinct mode; the returned code must be
        ERR_CORRUPT_FORBIDDEN_FIELD (not ERR_CORRUPT_MISSING_FIELD).
        """
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1040-claimed-by.md"
        _write(
            bad_file,
            "---\nid: 1040\ntitle: legacy claim\nstatus: todo\npriority: needed\n"
            "claimed_by: old-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)

        err = m.detect_corruption(bad_file, config)

        assert err is not None
        assert err.code == "ERR_CORRUPT_FORBIDDEN_FIELD", (
            f"Expected ERR_CORRUPT_FORBIDDEN_FIELD for forbidden claimed_by, got {err.code!r}. "
            "C-12 distinguishes 'forbidden-field' from 'missing-required-field'."
        )

    def test_ac_c22_attempt_repair_forbidden_field_quarantines(
        self, tmp_path: Path
    ) -> None:
        """AC-C22: attempt_repair for ERR_CORRUPT_FORBIDDEN_FIELD → quarantine (migration path).

        ERR_CORRUPT_FORBIDDEN_FIELD must be a recognized, explicitly handled code —
        not just a fall-through quarantine. The repair handler must set code in the
        RepairOutcome to "ERR_CORRUPT_FORBIDDEN_FIELD" (the builder cannot rely on the
        unknown-code fall-through path for a first-class mode).
        """
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        # Precondition: ERR_CORRUPT_FORBIDDEN_FIELD must exist
        assert hasattr(m, "ERR_CORRUPT_FORBIDDEN_FIELD"), (
            "ERR_CORRUPT_FORBIDDEN_FIELD must be exported before attempt_repair can handle it"
        )
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1041-repair-claimed.md"
        _write(
            bad_file,
            "---\nid: 1041\ntitle: repair claimed\nstatus: todo\npriority: needed\n"
            "claimed_by: old-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)

        outcome = m.attempt_repair(bad_file, "ERR_CORRUPT_FORBIDDEN_FIELD", config)

        assert outcome.action == "quarantined"
        assert outcome.code == "ERR_CORRUPT_FORBIDDEN_FIELD"


# ---------------------------------------------------------------------------
# TestFromAC_NineC12ModesExported — AC-C17: all 9 C-12 named mode codes must exist
# ---------------------------------------------------------------------------


class TestFromAC_NineC12ModesExported:
    """AC-C17: all 9 mode codes named in C-12 AC must be exported from corruption.py.

    C-12 names 9 modes including ERR_CORRUPT_FORBIDDEN_FIELD (distinct from
    MISSING_FIELD) and ERR_CORRUPT_ORPHAN_ARCHIVE_REF (no current counterpart).
    """

    def test_ac_c17_all_nine_c12_mode_codes_exported(self) -> None:
        """AC-C17: all 9 C-12 mode codes must be importable from corruption.py."""
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        # Mapping of C-12 AC mode names → expected ERR_CORRUPT_* constant names:
        # missing-frontmatter    → ERR_CORRUPT_DELIMITERS
        # duplicate-id           → ERR_CORRUPT_DUPLICATE_ID
        # forbidden-field        → ERR_CORRUPT_FORBIDDEN_FIELD   (new, split from MISSING_FIELD)
        # id-mismatch            → ERR_CORRUPT_ID_FILENAME_MISMATCH
        # missing-required-field → ERR_CORRUPT_MISSING_FIELD
        # invalid-field-type     → ERR_CORRUPT_TYPE_MISMATCH
        # status-out-of-range    → ERR_CORRUPT_INVALID_STATUS
        # duplicate-location     → ERR_CORRUPT_DUPLICATE_LOCATION
        # orphan-archive-ref     → ERR_CORRUPT_ORPHAN_ARCHIVE_REF (new, 9th mode)
        required = [
            "ERR_CORRUPT_DELIMITERS",
            "ERR_CORRUPT_DUPLICATE_ID",
            "ERR_CORRUPT_FORBIDDEN_FIELD",
            "ERR_CORRUPT_ID_FILENAME_MISMATCH",
            "ERR_CORRUPT_MISSING_FIELD",
            "ERR_CORRUPT_TYPE_MISMATCH",
            "ERR_CORRUPT_INVALID_STATUS",
            "ERR_CORRUPT_DUPLICATE_LOCATION",
            "ERR_CORRUPT_ORPHAN_ARCHIVE_REF",
        ]
        missing = [name for name in required if not hasattr(m, name)]
        assert not missing, (
            f"C-12 AC requires these ERR_CORRUPT_* codes not yet exported: {missing}"
        )

    def test_ac_c21_c12_new_codes_are_corruption_error_subclasses(self) -> None:
        """AC-C21: new C-12 codes ERR_CORRUPT_FORBIDDEN_FIELD and ERR_CORRUPT_ORPHAN_ARCHIVE_REF
        must each be a CorruptionError subclass."""
        import owlbear_kanban.corruption as m  # noqa: PLC0415
        from owlbear_kanban.corruption import CorruptionError  # noqa: PLC0415

        for name in ("ERR_CORRUPT_FORBIDDEN_FIELD", "ERR_CORRUPT_ORPHAN_ARCHIVE_REF"):
            cls = getattr(m, name, None)
            assert cls is not None, f"{name} not exported from corruption.py"
            assert issubclass(cls, CorruptionError), (
                f"{name} must be a CorruptionError subclass per AC-C21"
            )
