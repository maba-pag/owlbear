"""Failing tests for #1212 — Remove storage.py re-exports.

AC1: storage.__all__ no longer lists body_parser/activity_store/corruption pure re-exports.
AC2: engine.py imports migrated from owlbear_kanban.storage to source modules.
AC3: serve/kanban/tests/ consumers updated to import from source modules.
AC4: Root-level test patch targets updated to match engine.py's new import paths.
"""

from __future__ import annotations

import re
from pathlib import Path

_SERVE_KANBAN_SRC = (
    Path(__file__).parent.parent / "serve" / "kanban" / "src" / "owlbear_kanban"
)
_SERVE_KANBAN_TESTS = Path(__file__).parent.parent / "serve" / "kanban" / "tests"
_ROOT_TESTS = Path(__file__).parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _imports_from_storage(source: str, symbol: str) -> bool:
    """Return True if *symbol* is imported from owlbear_kanban.storage in *source*."""
    # Multi-line: from owlbear_kanban.storage import (...)
    block_pattern = re.compile(
        r"from\s+owlbear_kanban\.storage\s+import\s+\(([^)]*)\)",
        re.DOTALL,
    )
    escaped = re.escape(symbol)
    if any(
        re.search(rf"\b{escaped}\b", m.group(1)) for m in block_pattern.finditer(source)
    ):
        return True
    # Single-line: from owlbear_kanban.storage import X, Y
    single_pattern = re.compile(r"from\s+owlbear_kanban\.storage\s+import\s+([^(\n]+)")
    return any(
        re.search(rf"\b{escaped}\b", m.group(1))
        for m in single_pattern.finditer(source)
    )


# ---------------------------------------------------------------------------
# AC1: storage.__all__ cleanup
# ---------------------------------------------------------------------------


class TestFromAC_StorageAllCleanup:
    """AC1: storage.__all__ must not list pure re-export symbols from body_parser,
    activity_store, or corruption."""

    def test_parse_body_not_in_storage_all(self) -> None:
        """body_parser.parse_body must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "parse_body" not in storage.__all__

    def test_render_body_not_in_storage_all(self) -> None:
        """body_parser.render_body must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "render_body" not in storage.__all__

    def test_append_activity_event_not_in_storage_all(self) -> None:
        """activity_store.append_activity_event must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "append_activity_event" not in storage.__all__

    def test_compact_activity_log_not_in_storage_all(self) -> None:
        """activity_store.compact_activity_log must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "compact_activity_log" not in storage.__all__

    def test_list_activity_events_not_in_storage_all(self) -> None:
        """activity_store.list_activity_events must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "list_activity_events" not in storage.__all__

    def test_scan_and_fix_not_in_storage_all(self) -> None:
        """corruption.scan_and_fix must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "scan_and_fix" not in storage.__all__

    def test_attempt_repair_not_in_storage_all(self) -> None:
        """corruption.attempt_repair must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "attempt_repair" not in storage.__all__

    def test_repair_outcome_not_in_storage_all(self) -> None:
        """corruption.RepairOutcome must be removed from storage.__all__."""
        from owlbear_kanban import storage

        assert "RepairOutcome" not in storage.__all__


# ---------------------------------------------------------------------------
# AC2: engine.py import migration
# ---------------------------------------------------------------------------


class TestFromAC_EngineImportMigration:
    """AC2: engine.py must not import detect_corruption/list_activity_events/
    compact_activity_log via owlbear_kanban.storage."""

    def test_no_inline_storage_detect_corruption_import(self) -> None:
        """engine.py must not inline-import detect_corruption from storage (2 sites)."""
        source = (_SERVE_KANBAN_SRC / "engine.py").read_text(encoding="utf-8")
        assert "from owlbear_kanban.storage import detect_corruption" not in source, (
            "Inline 'from owlbear_kanban.storage import detect_corruption' still present"
        )

    def test_no_storage_dot_detect_corruption_call_site(self) -> None:
        """engine.py must not access detect_corruption via storage module attribute."""
        source = (_SERVE_KANBAN_SRC / "engine.py").read_text(encoding="utf-8")
        assert "storage.detect_corruption" not in source, (
            "storage.detect_corruption call site still present"
        )

    def test_no_storage_dot_list_activity_events_call_site(self) -> None:
        """engine.py must not access list_activity_events via storage module attribute."""
        source = (_SERVE_KANBAN_SRC / "engine.py").read_text(encoding="utf-8")
        assert "storage.list_activity_events" not in source, (
            "storage.list_activity_events call site still present"
        )

    def test_no_storage_dot_compact_activity_log_call_site(self) -> None:
        """engine.py must not access compact_activity_log via storage module attribute."""
        source = (_SERVE_KANBAN_SRC / "engine.py").read_text(encoding="utf-8")
        assert "storage.compact_activity_log" not in source, (
            "storage.compact_activity_log call site still present"
        )


# ---------------------------------------------------------------------------
# AC3: package-local test import sources
# ---------------------------------------------------------------------------


class TestFromAC_PackageTestImportSources:
    """AC3: serve/kanban/tests/ consumers must import body_parser/corruption/
    activity_store symbols from their source modules, not from storage."""

    def test_test_corruption_scan_and_fix_not_from_storage(self) -> None:
        """test_corruption.py: scan_and_fix must not be imported from owlbear_kanban.storage."""
        source = (_SERVE_KANBAN_TESTS / "test_corruption.py").read_text(
            encoding="utf-8"
        )
        assert not _imports_from_storage(source, "scan_and_fix"), (
            "test_corruption.py still imports scan_and_fix from owlbear_kanban.storage"
        )

    def test_test_engine_activity_list_activity_events_not_from_storage(self) -> None:
        """test_engine_activity.py: list_activity_events must not come from storage."""
        source = (_SERVE_KANBAN_TESTS / "test_engine_activity.py").read_text(
            encoding="utf-8"
        )
        assert not _imports_from_storage(source, "list_activity_events"), (
            "test_engine_activity.py still imports list_activity_events from owlbear_kanban.storage"
        )

    def test_test_engine_archived_edit_corruption_error_not_from_storage(self) -> None:
        """test_engine_archived_edit_1120.py: CorruptionError must not come from storage."""
        source = (_SERVE_KANBAN_TESTS / "test_engine_archived_edit_1120.py").read_text(
            encoding="utf-8"
        )
        assert not _imports_from_storage(source, "CorruptionError"), (
            "test_engine_archived_edit_1120.py still imports CorruptionError from owlbear_kanban.storage"
        )

    def test_test_storage_1050_corruption_error_not_from_storage(self) -> None:
        """test_storage_1050.py: CorruptionError must not be imported from storage."""
        source = (_SERVE_KANBAN_TESTS / "test_storage_1050.py").read_text(
            encoding="utf-8"
        )
        assert not _imports_from_storage(source, "CorruptionError"), (
            "test_storage_1050.py still imports CorruptionError from owlbear_kanban.storage"
        )

    def test_test_storage_1050_detect_corruption_not_from_storage(self) -> None:
        """test_storage_1050.py: detect_corruption must not be imported from storage."""
        source = (_SERVE_KANBAN_TESTS / "test_storage_1050.py").read_text(
            encoding="utf-8"
        )
        assert not _imports_from_storage(source, "detect_corruption"), (
            "test_storage_1050.py still imports detect_corruption from owlbear_kanban.storage"
        )

    def test_test_storage_detect_corruption_not_from_storage(self) -> None:
        """test_storage.py: detect_corruption must not be imported from storage."""
        source = (_SERVE_KANBAN_TESTS / "test_storage.py").read_text(encoding="utf-8")
        assert not _imports_from_storage(source, "detect_corruption"), (
            "test_storage.py still imports detect_corruption from owlbear_kanban.storage"
        )


# ---------------------------------------------------------------------------
# AC4: root-level test patch target updates
# ---------------------------------------------------------------------------


class TestFromAC_RootTestPatchTargets:
    """AC4: root-level tests must use updated patch targets matching engine.py's
    new import paths (not owlbear_kanban.storage.*)."""

    def test_ble001_no_storage_detect_corruption_patch(self) -> None:
        """test_engine_ble001.py: patch target 'owlbear_kanban.storage.detect_corruption'
        must be replaced with the engine's new import path."""
        source = (_ROOT_TESTS / "test_engine_ble001.py").read_text(encoding="utf-8")
        assert "owlbear_kanban.storage.detect_corruption" not in source, (
            "test_engine_ble001.py still patches owlbear_kanban.storage.detect_corruption"
        )

    def test_cockpit_view_no_storage_compact_activity_log_patch(self) -> None:
        """test_engine_cockpit_view.py: patch target 'owlbear_kanban.storage.compact_activity_log'
        must be replaced with the source module's path."""
        source = (_ROOT_TESTS / "test_engine_cockpit_view.py").read_text(
            encoding="utf-8"
        )
        assert "owlbear_kanban.storage.compact_activity_log" not in source, (
            "test_engine_cockpit_view.py still patches owlbear_kanban.storage.compact_activity_log"
        )


# ---------------------------------------------------------------------------
# Helper for positive import assertions
# ---------------------------------------------------------------------------


def _imports_from_source(source: str, module: str, symbol: str) -> bool:
    """Return True if *symbol* is imported from *module* in *source*."""
    block_pattern = re.compile(
        rf"from\s+{re.escape(module)}\s+import\s+\(([^)]*)\)",
        re.DOTALL,
    )
    escaped = re.escape(symbol)
    if any(
        re.search(rf"\b{escaped}\b", m.group(1)) for m in block_pattern.finditer(source)
    ):
        return True
    single_pattern = re.compile(rf"from\s+{re.escape(module)}\s+import\s+([^(\n]+)")
    return any(
        re.search(rf"\b{escaped}\b", m.group(1))
        for m in single_pattern.finditer(source)
    )


# ---------------------------------------------------------------------------
# AC1 (positive): storage.py source contains no import lines for removed symbols
# ---------------------------------------------------------------------------


class TestFromAC_StorageSourceImportLineRemoval:
    """AC1 positive: storage.py source must have NO import lines for body_parser or
    activity_store (the pure re-export modules were entirely removed)."""

    def test_storage_source_no_body_parser_import_line(self) -> None:
        """storage.py must have no 'from owlbear_kanban.body_parser' import line."""
        source = (_SERVE_KANBAN_SRC / "storage.py").read_text(encoding="utf-8")
        assert "from owlbear_kanban.body_parser" not in source, (
            "storage.py still contains a 'from owlbear_kanban.body_parser' import line"
        )

    def test_storage_source_no_activity_store_import_line(self) -> None:
        """storage.py must have no 'from owlbear_kanban.activity_store' import line."""
        source = (_SERVE_KANBAN_SRC / "storage.py").read_text(encoding="utf-8")
        assert "from owlbear_kanban.activity_store" not in source, (
            "storage.py still contains a 'from owlbear_kanban.activity_store' import line"
        )

    def test_storage_corruption_import_still_present_for_internal_use(self) -> None:
        """storage.py must still import from owlbear_kanban.corruption for internal use
        (CorruptionError etc. are used by storage's own functions — not re-exported)."""
        source = (_SERVE_KANBAN_SRC / "storage.py").read_text(encoding="utf-8")
        assert "from owlbear_kanban.corruption import" in source, (
            "storage.py lost its internal owlbear_kanban.corruption import — "
            "migration was too aggressive"
        )


# ---------------------------------------------------------------------------
# AC2 (positive): engine.py imports migrated symbols from source modules
# ---------------------------------------------------------------------------


class TestFromAC_EngineNewImportTargets:
    """AC2 positive: engine.py must import detect_corruption, list_activity_events,
    and compact_activity_log from their source modules, not from storage."""

    def test_engine_imports_detect_corruption_from_corruption(self) -> None:
        """engine.py must import detect_corruption from owlbear_kanban.corruption."""
        source = (_SERVE_KANBAN_SRC / "engine.py").read_text(encoding="utf-8")
        assert _imports_from_source(
            source, "owlbear_kanban.corruption", "detect_corruption"
        ), "engine.py does not import detect_corruption from owlbear_kanban.corruption"

    def test_engine_imports_list_activity_events_from_activity_store(self) -> None:
        """engine.py must import list_activity_events from owlbear_kanban.activity_store."""
        source = (_SERVE_KANBAN_SRC / "engine.py").read_text(encoding="utf-8")
        assert _imports_from_source(
            source, "owlbear_kanban.activity_store", "list_activity_events"
        ), (
            "engine.py does not import list_activity_events from owlbear_kanban.activity_store"
        )

    def test_engine_imports_compact_activity_log_from_activity_store(self) -> None:
        """engine.py must import compact_activity_log from owlbear_kanban.activity_store."""
        source = (_SERVE_KANBAN_SRC / "engine.py").read_text(encoding="utf-8")
        assert _imports_from_source(
            source, "owlbear_kanban.activity_store", "compact_activity_log"
        ), (
            "engine.py does not import compact_activity_log from owlbear_kanban.activity_store"
        )


# ---------------------------------------------------------------------------
# AC3 (positive): package-local tests import from source modules
# ---------------------------------------------------------------------------


class TestFromAC_PackageTestSourceModuleImports:
    """AC3 positive: serve/kanban/tests/ files must import the migrated symbols
    from source modules (owlbear_kanban.corruption / owlbear_kanban.activity_store)."""

    def test_test_corruption_imports_scan_and_fix_from_corruption(self) -> None:
        """test_corruption.py must import scan_and_fix from owlbear_kanban.corruption."""
        source = (_SERVE_KANBAN_TESTS / "test_corruption.py").read_text(
            encoding="utf-8"
        )
        assert _imports_from_source(
            source, "owlbear_kanban.corruption", "scan_and_fix"
        ), (
            "test_corruption.py does not import scan_and_fix from owlbear_kanban.corruption"
        )

    def test_test_engine_activity_imports_list_activity_events_from_activity_store(
        self,
    ) -> None:
        """test_engine_activity.py must import list_activity_events from activity_store."""
        source = (_SERVE_KANBAN_TESTS / "test_engine_activity.py").read_text(
            encoding="utf-8"
        )
        assert _imports_from_source(
            source, "owlbear_kanban.activity_store", "list_activity_events"
        ), (
            "test_engine_activity.py does not import list_activity_events "
            "from owlbear_kanban.activity_store"
        )

    def test_test_engine_archived_edit_imports_corruption_error_from_corruption(
        self,
    ) -> None:
        """test_engine_archived_edit_1120.py must import CorruptionError from corruption."""
        source = (_SERVE_KANBAN_TESTS / "test_engine_archived_edit_1120.py").read_text(
            encoding="utf-8"
        )
        assert _imports_from_source(
            source, "owlbear_kanban.corruption", "CorruptionError"
        ), (
            "test_engine_archived_edit_1120.py does not import CorruptionError "
            "from owlbear_kanban.corruption"
        )

    def test_test_storage_1050_imports_corruption_error_from_corruption(self) -> None:
        """test_storage_1050.py must import CorruptionError from owlbear_kanban.corruption."""
        source = (_SERVE_KANBAN_TESTS / "test_storage_1050.py").read_text(
            encoding="utf-8"
        )
        assert _imports_from_source(
            source, "owlbear_kanban.corruption", "CorruptionError"
        ), (
            "test_storage_1050.py does not import CorruptionError from owlbear_kanban.corruption"
        )

    def test_test_storage_1050_imports_detect_corruption_from_corruption(self) -> None:
        """test_storage_1050.py must import detect_corruption from owlbear_kanban.corruption."""
        source = (_SERVE_KANBAN_TESTS / "test_storage_1050.py").read_text(
            encoding="utf-8"
        )
        assert _imports_from_source(
            source, "owlbear_kanban.corruption", "detect_corruption"
        ), (
            "test_storage_1050.py does not import detect_corruption from owlbear_kanban.corruption"
        )

    def test_test_storage_imports_detect_corruption_from_corruption(self) -> None:
        """test_storage.py must import detect_corruption from owlbear_kanban.corruption."""
        source = (_SERVE_KANBAN_TESTS / "test_storage.py").read_text(encoding="utf-8")
        assert _imports_from_source(
            source, "owlbear_kanban.corruption", "detect_corruption"
        ), (
            "test_storage.py does not import detect_corruption from owlbear_kanban.corruption"
        )


# ---------------------------------------------------------------------------
# AC4 (positive): root-level tests use exact replacement patch target strings
# ---------------------------------------------------------------------------


class TestFromAC_RootTestNewPatchTargets:
    """AC4 positive: root-level tests must patch the migrated symbols at their
    new engine-module path (owlbear_kanban.engine.*), not via storage."""

    def test_ble001_patches_engine_detect_corruption(self) -> None:
        """test_engine_ble001.py must patch owlbear_kanban.engine.detect_corruption."""
        source = (_ROOT_TESTS / "test_engine_ble001.py").read_text(encoding="utf-8")
        assert "owlbear_kanban.engine.detect_corruption" in source, (
            "test_engine_ble001.py does not patch owlbear_kanban.engine.detect_corruption"
        )

    def test_cockpit_view_patches_engine_compact_activity_log(self) -> None:
        """test_engine_cockpit_view.py must patch owlbear_kanban.engine.compact_activity_log."""
        source = (_ROOT_TESTS / "test_engine_cockpit_view.py").read_text(
            encoding="utf-8"
        )
        assert "owlbear_kanban.engine.compact_activity_log" in source, (
            "test_engine_cockpit_view.py does not patch owlbear_kanban.engine.compact_activity_log"
        )
