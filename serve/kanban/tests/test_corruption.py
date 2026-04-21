"""TDD RED: C-03 — corruption detection & auto-fix tests.

Task: #1048 (Brief C #1043) — paper-c.md §8.4
AC:   C17, C18, C21, C22
All tests FAIL (RED phase — corruption module not yet implemented).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban.corruption import (  # NEW module — ImportError in RED
    CorruptionError,
    detect_corruption,
    attempt_repair,
)
from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    read_task,
    scan_and_fix,
    load_config,
)

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
# TestFromAC_CorruptionShape — AC-C21
# ---------------------------------------------------------------------------


class TestFromAC_CorruptionShape:
    """AC-C21: CorruptionError shape and subclassing contract."""

    def test_ac_c21_corruption_error_has_code_attribute(self) -> None:
        """AC-C21: CorruptionError instances carry a .code attribute."""
        err = CorruptionError(
            code="ERR_CORRUPT_DELIMITERS",
            user_message="missing delimiters",
            file_path=None,
        )
        assert err.code == "ERR_CORRUPT_DELIMITERS"

    def test_ac_c21_corruption_error_has_user_message(self) -> None:
        """AC-C21: CorruptionError carries .user_message."""
        err = CorruptionError(
            code="ERR_CORRUPT_YAML_PARSE",
            user_message="yaml parse failed",
            file_path="/kanban/tasks/1001-foo.md",
        )
        assert err.user_message == "yaml parse failed"
        assert err.file_path == "/kanban/tasks/1001-foo.md"

    def test_ac_c21_corruption_error_is_exception(self) -> None:
        """AC-C21: CorruptionError is a subclass of Exception (via KanbanError)."""
        assert issubclass(CorruptionError, Exception)

    def test_ac_c21_file_path_none_allowed(self) -> None:
        """AC-C21: file_path=None is valid (pre-parse failures)."""
        err = CorruptionError(code="ERR_CORRUPT_DELIMITERS", user_message="msg", file_path=None)
        assert err.file_path is None

    def test_ac_c21_each_err_corrupt_code_is_subclass_of_corruption_error(self) -> None:
        """AC-C21: every ERR_CORRUPT_* exported name is a Python subclass of CorruptionError."""
        import owlbear_kanban.corruption as m  # noqa: PLC0415

        expected_codes = [
            "ERR_CORRUPT_DELIMITERS",
            "ERR_CORRUPT_DUPLICATE_ID",
            "ERR_CORRUPT_MISSING_FIELD",
            "ERR_CORRUPT_TYPE_MISMATCH",
            "ERR_CORRUPT_YAML_PARSE",
            "ERR_CORRUPT_ID_FILENAME_MISMATCH",
            "ERR_CORRUPT_DUPLICATE_LOCATION",
            "ERR_CORRUPT_INVALID_STATUS",
            "ERR_CORRUPT_INVALID_PRIORITY",
        ]
        for name in expected_codes:
            cls = getattr(m, name, None)
            assert cls is not None, f"{name} not exported from corruption module"
            assert isinstance(cls, type), f"{name} is not a class — expected subclass of CorruptionError"
            assert issubclass(cls, CorruptionError), f"{name} is not a subclass of CorruptionError"


# ---------------------------------------------------------------------------
# TestFromAC_CorruptionDetection — AC-C17, AC-C18: all 9 modes
# ---------------------------------------------------------------------------


class TestFromAC_CorruptionDetection:
    """AC-C17, AC-C18: detect all 9 corruption modes; read_task raises."""

    def test_ac_c17_mode1_missing_delimiters_detected(self, tmp_path: Path) -> None:
        """AC-C17/C18: mode 1 (ERR_CORRUPT_DELIMITERS) — file missing --- delimiters."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1001-bad.md"
        _write(bad_file, "id: 1001\ntitle: no delimiters\n")
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_DELIMITERS"

    def test_ac_c18_mode1_read_task_raises(self, tmp_path: Path) -> None:
        """AC-C18: read_task raises CorruptionError for mode 1."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1001-bad.md"
        _write(bad_file, "no frontmatter delimiters at all\n")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)
        assert exc_info.value.code == "ERR_CORRUPT_DELIMITERS"

    def test_ac_c17_mode2_duplicate_id_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 2 (ERR_CORRUPT_DUPLICATE_ID) detected when two files share an id."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        _write(tasks_dir / "1001-original.md", _VALID_TASK)
        _write(tasks_dir / "1001-duplicate.md", _VALID_TASK.replace("1001-original", "1001-dup"))
        config = load_config(kanban_dir)

        outcomes = scan_and_fix(kanban_dir, config)
        codes = [o.code for o in outcomes]
        assert "ERR_CORRUPT_DUPLICATE_ID" in codes

    def test_ac_c17_mode3_missing_required_field_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 3 (ERR_CORRUPT_MISSING_FIELD) — required field absent."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1002-notitle.md"
        _write(
            bad_file,
            "---\nid: 1002\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_MISSING_FIELD"

    def test_ac_c18_mode3_read_task_raises(self, tmp_path: Path) -> None:
        """AC-C18: read_task raises CorruptionError for mode 3 (missing required field)."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1002-notitle.md"
        _write(
            bad_file,
            "---\nid: 1002\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)
        assert exc_info.value.code == "ERR_CORRUPT_MISSING_FIELD"

    def test_ac_c17_mode4_type_mismatch_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 4 (ERR_CORRUPT_TYPE_MISMATCH) — id field is a string."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1003-badtype.md"
        _write(
            bad_file,
            '---\nid: "notanint"\ntitle: bad type\nstatus: todo\npriority: needed\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_TYPE_MISMATCH"

    def test_ac_c17_mode5_yaml_parse_error_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 5 (ERR_CORRUPT_YAML_PARSE) — invalid YAML frontmatter."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1004-badyaml.md"
        _write(bad_file, "---\n: bad yaml: [unclosed\n---\n")
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_YAML_PARSE"

    def test_ac_c17_mode6_id_filename_mismatch_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 6 (ERR_CORRUPT_ID_FILENAME_MISMATCH) — filename id ≠ frontmatter id."""
        kanban_dir = _make_board(tmp_path)
        # File named 9999-... but frontmatter has id: 1001
        bad_file = kanban_dir / "tasks" / "9999-mismatch.md"
        _write(bad_file, _VALID_TASK)
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_ID_FILENAME_MISMATCH"

    def test_ac_c17_mode7_duplicate_location_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 7 (ERR_CORRUPT_DUPLICATE_LOCATION) — same ID in tasks/ and archive/."""
        kanban_dir = _make_board(tmp_path)
        _write(kanban_dir / "tasks" / "1001-active.md", _VALID_TASK)
        _write(kanban_dir / "archive" / "1001-active.md", _VALID_TASK)
        config = load_config(kanban_dir)

        outcomes = scan_and_fix(kanban_dir, config)
        codes = [o.code for o in outcomes]
        assert "ERR_CORRUPT_DUPLICATE_LOCATION" in codes

    def test_ac_c17_mode8_invalid_status_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 8 (ERR_CORRUPT_INVALID_STATUS) — status not in BoardConfig.statuses."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1005-badstatus.md"
        _write(
            bad_file,
            "---\nid: 1005\ntitle: bad status\nstatus: nonexistent_status\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_INVALID_STATUS"

    def test_ac_c17_mode9_invalid_priority_detected(self, tmp_path: Path) -> None:
        """AC-C17: mode 9 (ERR_CORRUPT_INVALID_PRIORITY) — priority not in BoardConfig.priorities."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1006-badpriority.md"
        _write(
            bad_file,
            "---\nid: 1006\ntitle: bad priority\nstatus: todo\npriority: not_a_real_priority\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_INVALID_PRIORITY"

    def test_ac_c17_all_9_codes_covered(self, _tmp_path: Path) -> None:
        """AC-C17: verify all 9 ERR_CORRUPT_* codes exist as constants/attributes."""
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
        from owlbear_kanban import corruption as corr_module  # noqa: PLC0415
        exported = {name for name in dir(corr_module) if name.startswith("ERR_CORRUPT_")}
        assert expected.issubset(exported), f"Missing codes: {expected - exported}"

    def test_ac_c17_valid_task_no_corruption(self, tmp_path: Path) -> None:
        """AC-C17: detect_corruption returns None for a well-formed task file."""
        kanban_dir = _make_board(tmp_path)
        good_file = kanban_dir / "tasks" / "1001-good.md"
        _write(good_file, _VALID_TASK)
        config = load_config(kanban_dir)

        err = detect_corruption(good_file, config)
        assert err is None

    def test_ac_c18_mode4_read_task_raises(self, tmp_path: Path) -> None:
        """AC-C18: read_task raises CorruptionError for mode 4 (type mismatch — string id)."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "notanint-strid.md"
        _write(
            bad_file,
            '---\nid: "notanint"\ntitle: bad type\nstatus: todo\npriority: needed\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)
        assert exc_info.value.code == "ERR_CORRUPT_TYPE_MISMATCH"

    def test_ac_c18_mode5_read_task_raises(self, tmp_path: Path) -> None:
        """AC-C18: read_task raises CorruptionError for mode 5 (YAML parse error)."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1099-badyaml.md"
        _write(bad_file, "---\n: bad yaml: [unclosed\n---\n")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)
        assert exc_info.value.code == "ERR_CORRUPT_YAML_PARSE"

    def test_ac_c18_mode6_read_task_raises(self, tmp_path: Path) -> None:
        """AC-C18: read_task raises CorruptionError for mode 6 (ID/filename mismatch)."""
        kanban_dir = _make_board(tmp_path)
        # File named 9999-... but frontmatter has id: 1001
        bad_file = kanban_dir / "tasks" / "9999-wrongid.md"
        _write(bad_file, _VALID_TASK)

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)
        assert exc_info.value.code == "ERR_CORRUPT_ID_FILENAME_MISMATCH"


# ---------------------------------------------------------------------------
# TestFromAC_AutoFixMatrix — AC-C22
# ---------------------------------------------------------------------------


class TestFromAC_AutoFixMatrix:
    """AC-C22: auto-fix matrix — (mode, field, default) triples for mode 3 and mode 4."""

    def test_ac_c22_mode3_missing_priority_defaults_to_first_config_priority(
        self, tmp_path: Path
    ) -> None:
        """AC-C22: mode 3, priority field absent → auto-fixed to config.priorities[0]."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1010-noprio.md"
        _write(
            bad_file,
            "---\nid: 1010\ntitle: no prio\nstatus: todo\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_tags_defaults_to_empty_list(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, tags field absent → auto-fixed to []."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1011-notags.md"
        _write(
            bad_file,
            "---\nid: 1011\ntitle: no tags\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_depends_on_defaults_to_empty_list(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, depends_on absent → auto-fixed to []."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1012-nodeps.md"
        _write(
            bad_file,
            "---\nid: 1012\ntitle: no deps\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_blocked_defaults_to_false(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, blocked absent → auto-fixed to false."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1013-noblocked.md"
        _write(
            bad_file,
            "---\nid: 1013\ntitle: no blocked\nstatus: todo\npriority: needed\n"
            "tags: []\ndepends_on: []\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_block_reason_defaults_to_null(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, block_reason absent → auto-fixed to null."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1014-nobr.md"
        _write(
            bad_file,
            "---\nid: 1014\ntitle: no br\nstatus: todo\npriority: needed\n"
            "tags: []\ndepends_on: []\nblocked: false\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_claimed_at_defaults_to_null(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, claimed_at absent → auto-fixed to null."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1015-noclaim.md"
        _write(
            bad_file,
            "---\nid: 1015\ntitle: no claim\nstatus: todo\npriority: needed\n"
            "tags: []\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_archival_reason_defaults_to_null(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, archival_reason absent → auto-fixed to null."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1016-noar.md"
        _write(
            bad_file,
            "---\nid: 1016\ntitle: no ar\nstatus: todo\npriority: needed\n"
            "tags: []\ndepends_on: []\nblocked: false\nblock_reason: null\nclaimed_at: null\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_archival_refs_defaults_to_empty_list(
        self, tmp_path: Path
    ) -> None:
        """AC-C22: mode 3, archival_refs absent → auto-fixed to []."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1017-noarr.md"
        _write(
            bad_file,
            "---\nid: 1017\ntitle: no arr\nstatus: todo\npriority: needed\n"
            "tags: []\ndepends_on: []\nblocked: false\nblock_reason: null\nclaimed_at: null\n"
            "archival_reason: null\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_parent_defaults_to_null(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, parent absent → auto-fixed to null."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1018-noparent.md"
        _write(
            bad_file,
            "---\nid: 1018\ntitle: no parent\nstatus: todo\npriority: needed\n"
            "tags: []\ndepends_on: []\nblocked: false\nblock_reason: null\nclaimed_at: null\n"
            "archival_reason: null\narchival_refs: []\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_id_quarantines(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, id absent (no safe default) → quarantined, not fixed."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "noid-file.md"
        _write(
            bad_file,
            "---\ntitle: no id\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "quarantined"

    def test_ac_c22_mode3_missing_title_quarantines(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, title absent (no safe default) → quarantined."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1019-notitle.md"
        _write(
            bad_file,
            "---\nid: 1019\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "quarantined"

    def test_ac_c22_mode4_string_id_coerced_to_int(self, tmp_path: Path) -> None:
        """AC-C22: mode 4, id='1003' (string digit) → coerced to int, action='fixed'."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1003-strid.md"
        _write(
            bad_file,
            '---\nid: "1003"\ntitle: string id\nstatus: todo\npriority: needed\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_TYPE_MISMATCH", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode4_non_digit_string_id_quarantines(self, tmp_path: Path) -> None:
        """AC-C22: mode 4, id='abc' (non-digit) → cannot coerce → quarantined."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "abc-badid.md"
        _write(
            bad_file,
            '---\nid: "abc"\ntitle: bad id\nstatus: todo\npriority: needed\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_TYPE_MISMATCH", config)
        assert outcome.action == "quarantined"

    def test_ac_c22_mode4_string_bool_true_coerced(self, tmp_path: Path) -> None:
        """AC-C22: mode 4, blocked='true' (string) → coerced to True, action='fixed'."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1020-strbool.md"
        _write(
            bad_file,
            "---\nid: 1020\ntitle: str bool\nstatus: todo\npriority: needed\n"
            'blocked: "true"\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_TYPE_MISMATCH", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode9_invalid_priority_coerced_to_first(self, tmp_path: Path) -> None:
        """AC-C22: mode 9 (ERR_CORRUPT_INVALID_PRIORITY) → auto-fixed to config.priorities[0]."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1021-badprio.md"
        _write(
            bad_file,
            "---\nid: 1021\ntitle: bad prio\nstatus: todo\npriority: not_valid\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_INVALID_PRIORITY", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode3_missing_created_quarantines(self, tmp_path: Path) -> None:
        """AC-C22: mode 3, created absent (no safe default) → quarantined."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1023-nocreated.md"
        _write(
            bad_file,
            "---\nid: 1023\ntitle: no created\nstatus: todo\npriority: needed\n"
            'updated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_MISSING_FIELD", config)
        assert outcome.action == "quarantined"

    def test_ac_c22_mode4_string_bool_false_coerced(self, tmp_path: Path) -> None:
        """AC-C22: mode 4, blocked='false' (string) → coerced to False, action='fixed'."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1024-strboolfalse.md"
        _write(
            bad_file,
            "---\nid: 1024\ntitle: str bool false\nstatus: todo\npriority: needed\n"
            'blocked: "false"\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_TYPE_MISMATCH", config)
        assert outcome.action == "fixed"

    def test_ac_c22_mode4_ambiguous_bool_quarantines(self, tmp_path: Path) -> None:
        """AC-C22: mode 4, blocked='maybe' (non-true/false string) → cannot coerce → quarantined."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1025-ambiguousbool.md"
        _write(
            bad_file,
            "---\nid: 1025\ntitle: ambiguous bool\nstatus: todo\npriority: needed\n"
            'blocked: "maybe"\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_TYPE_MISMATCH", config)
        assert outcome.action == "quarantined"

    def test_ac_c22_repair_outcome_shape(self, tmp_path: Path) -> None:
        """AC-C22: RepairOutcome has task_id, file_path, code, action, detail attributes."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1022-badprio2.md"
        _write(
            bad_file,
            "---\nid: 1022\ntitle: t\nstatus: todo\npriority: not_valid\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
        )
        config = load_config(kanban_dir)
        outcome = attempt_repair(bad_file, "ERR_CORRUPT_INVALID_PRIORITY", config)

        assert hasattr(outcome, "task_id")
        assert hasattr(outcome, "file_path")
        assert hasattr(outcome, "code")
        assert hasattr(outcome, "action")
        assert hasattr(outcome, "detail")
        assert outcome.action in {"fixed", "quarantined", "failed"}
