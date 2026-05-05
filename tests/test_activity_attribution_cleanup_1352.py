"""Failing tests for task #1352: activity attribution cleanup.

AC coverage:
- AC1 (td:0): canonical schema check — test-writer skip.
- AC2 (td:1): activity_log.py deleted; no production module imports it.
- AC3 (td:1): source vocabulary (engine|agent|cockpit) documented in activity_store docstring.
- AC4 (td:1): cockpit README audit-trail section uses source contract, not actor.
- AC5 (td:1): backward-compat for actor-keyed JSONL rows — already covered by
              test_engine_activity.py::test_ac_c43_legacy_format_events_accepted_by_session_derivation
              (currently green; test-writer skip to avoid duplicate green test).
- AC6 (td:2): structural AST scan — no production module imports activity_log.
- AC7 (td:0): skill/instruction doc update — test-writer skip.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# AST scanner helper (AC6) — module-level for reuse and clarity
# ---------------------------------------------------------------------------

def _scan_for_activity_log_imports(pkg_dir: Path) -> list[str]:  # noqa: C901
    """Return violation strings for any activity_log import found in *pkg_dir*.

    Scans all top-level ``*.py`` files via AST, skipping files with syntax errors.
    Catches three import forms:
      - ``import owlbear_kanban.activity_log``
      - ``from owlbear_kanban import activity_log``
      - ``from owlbear_kanban.activity_log import <name>``
    """
    violations: list[str] = []
    for py_file in sorted(pkg_dir.glob("*.py")):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "activity_log" in alias.name:
                        violations.append(
                            f"{py_file.name}: import {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "activity_log" in module:
                    violations.append(
                        f"{py_file.name}: from {module} import ..."
                    )
                for alias in node.names:
                    if alias.name == "activity_log":
                        violations.append(
                            f"{py_file.name}: from {module} import activity_log"
                        )
    return violations


# ---------------------------------------------------------------------------
# AC2 — activity_log module deleted
# ---------------------------------------------------------------------------

class TestFromAC_ActivityLogDeletion:
    """AC2 — activity_log.py deleted; importing it raises ImportError."""

    def test_activity_log_module_not_importable(self) -> None:
        """AC2: importing owlbear_kanban.activity_log raises ImportError after file deletion.

        RED: the file still exists — import succeeds — pytest.raises fails.
        """
        # Evict any cached import so the test reflects disk state.
        sys.modules.pop("owlbear_kanban.activity_log", None)

        with pytest.raises(ImportError):
            importlib.import_module("owlbear_kanban.activity_log")


# ---------------------------------------------------------------------------
# AC3 — source vocabulary documented in activity_store module docstring
# ---------------------------------------------------------------------------

class TestFromAC_SourceVocabularyDocumented:
    """AC3 — source vocabulary 'engine'|'agent'|'cockpit' in activity_store.__doc__."""

    def test_source_vocab_engine_in_docstring(self) -> None:
        """AC3: 'engine' appears in activity_store module docstring.

        RED: current docstring has no source vocabulary.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        assert "engine" in doc, (
            "'engine' source vocabulary must be documented in "
            "owlbear_kanban.activity_store module docstring (AC3)"
        )

    def test_source_vocab_agent_in_docstring(self) -> None:
        """AC3: 'agent' appears in activity_store module docstring.

        RED: current docstring has no source vocabulary.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        assert "agent" in doc, (
            "'agent' source vocabulary must be documented in "
            "owlbear_kanban.activity_store module docstring (AC3)"
        )

    def test_source_vocab_cockpit_in_docstring(self) -> None:
        """AC3: 'cockpit' appears in activity_store module docstring.

        RED: current docstring has no source vocabulary.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        assert "cockpit" in doc, (
            "'cockpit' source vocabulary must be documented in "
            "owlbear_kanban.activity_store module docstring (AC3)"
        )


# ---------------------------------------------------------------------------
# AC4 — cockpit README audit-trail section uses source, not actor
# ---------------------------------------------------------------------------

class TestFromAC_CockpitReadmeAuditTrail:
    """AC4 — cockpit README audit-trail section uses source contract, not actor."""

    def test_audit_trail_no_actor_cockpit_field(self, project_root: Path) -> None:
        """AC4: README must not reference 'actor: \"cockpit\"' in audit-trail section.

        RED: current README still has the old actor: "cockpit" heading and body.
        """
        readme = (project_root / "serve/cockpit/README.md").read_text(encoding="utf-8")
        assert 'actor: "cockpit"' not in readme, (
            'serve/cockpit/README.md still contains \'actor: "cockpit"\' — '
            "update audit-trail section to use source vocabulary per AC4"
        )


# ---------------------------------------------------------------------------
# AC6 — structural AST import-inspection guard
# ---------------------------------------------------------------------------

class TestFromAC_ImportGuard:
    """AC6 — structural AST scan: no module in owlbear_kanban/ imports activity_log."""

    def test_file_deleted_and_no_imports_remain(self, project_root: Path) -> None:
        """AC6: activity_log.py absent AND AST scan finds no remaining imports.

        Two-phase check:
        1. File-existence guard — fails RED until builder deletes the file.
        2. AST guard — runs after deletion and catches any stale import added later.

        RED: activity_log.py still exists — first assertion fails.
        """
        pkg_dir = project_root / "serve/kanban/src/owlbear_kanban"

        # Phase 1: file must be gone (RED now — file still exists)
        assert not (pkg_dir / "activity_log.py").exists(), (
            "serve/kanban/src/owlbear_kanban/activity_log.py must be deleted (AC2/AC6)"
        )

        # Phase 2: AST walk — no surviving module imports the deleted module
        violations = _scan_for_activity_log_imports(pkg_dir)
        assert not violations, (
            "AC6 violation — modules still importing activity_log:\n"
            + "\n".join(f"  {v}" for v in violations)
        )
