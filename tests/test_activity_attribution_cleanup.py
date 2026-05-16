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
import re
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
                        violations.append(f"{py_file.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "activity_log" in module:
                    violations.append(f"{py_file.name}: from {module} import ...")
                for alias in node.names:
                    if alias.name == "activity_log":
                        violations.append(f"{py_file.name}: from {module} import activity_log")
    return violations


# ---------------------------------------------------------------------------
# README section extractor helper (AC4)
# ---------------------------------------------------------------------------


def _extract_audit_trail_section(readme_text: str) -> str:
    """Return the body text of the Audit Trail section in serve/cockpit/README.md.

    Extracts everything between the ``## Audit Trail`` heading and the next ``##``
    heading (or end of file), excluding the heading line itself. Returns an empty
    string when the section is absent.
    """
    match = re.search(
        r"##[^\n]*Audit Trail[^\n]*\n(.*?)(?=\n##|\Z)",
        readme_text,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1) if match else ""


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
            "'engine' source vocabulary must be documented in owlbear_kanban.activity_store module docstring (AC3)"
        )

    def test_source_vocab_agent_in_docstring(self) -> None:
        """AC3: 'agent' appears in activity_store module docstring.

        RED: current docstring has no source vocabulary.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        assert "agent" in doc, (
            "'agent' source vocabulary must be documented in owlbear_kanban.activity_store module docstring (AC3)"
        )

    def test_source_vocab_cockpit_in_docstring(self) -> None:
        """AC3: 'cockpit' appears in activity_store module docstring.

        RED: current docstring has no source vocabulary.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        assert "cockpit" in doc, (
            "'cockpit' source vocabulary must be documented in owlbear_kanban.activity_store module docstring (AC3)"
        )

    def test_source_vocab_docstring_has_vocabulary_section(self) -> None:
        """AC3 (strengthened): docstring contains a dedicated source vocabulary section.

        A vocabulary header proves the three words appear as a canonical contract,
        not as incidental prose.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        assert "source vocabulary" in doc.lower(), (
            "activity_store module docstring must contain a 'source vocabulary' "
            "section that documents the canonical enum-like contract (AC3)"
        )

    def test_source_vocab_engine_purpose_documented(self) -> None:
        """AC3 (binding): ``engine`` declaration line also contains 'internal'.

        Locates the line that explicitly declares ``engine`` as a source value
        (using RST double-backtick markup) and asserts that 'internal' appears on
        that SAME line.  A purpose swap — e.g. ``engine`` mapped to
        'agent-initiated' — passes a plain token check but fails here.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        engine_decl_lines = [ln for ln in doc.splitlines() if "``engine``" in ln]
        assert engine_decl_lines, "activity_store docstring has no line declaring '``engine``' as a source value (AC3)"
        assert any("internal" in ln for ln in engine_decl_lines), (
            "activity_store docstring: the ``engine`` declaration line must also "
            "contain 'internal' on the same line, binding the source value to its "
            "purpose (AC3). Purpose swaps or relocations are not accepted."
        )

    def test_source_vocab_agent_purpose_documented(self) -> None:
        """AC3 (binding): ``agent`` declaration line also contains 'agent-initiated'.

        Locates the line that explicitly declares ``agent`` as a source value and
        asserts 'agent-initiated' appears on that SAME line.  A purpose swap —
        e.g. ``agent`` mapped to 'internal' — passes a plain token check (because
        'agent-initiated' still appears elsewhere) but fails here.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        agent_decl_lines = [ln for ln in doc.splitlines() if "``agent``" in ln]
        assert agent_decl_lines, "activity_store docstring has no line declaring '``agent``' as a source value (AC3)"
        assert any("agent-initiated" in ln for ln in agent_decl_lines), (
            "activity_store docstring: the ``agent`` declaration line must also "
            "contain 'agent-initiated' on the same line, binding the source value "
            "to its purpose (AC3). Purpose swaps or relocations are not accepted."
        )

    def test_source_vocab_cockpit_purpose_documented(self) -> None:
        """AC3 (binding): ``cockpit`` declaration line also contains a UI marker.

        Locates the line that explicitly declares ``cockpit`` as a source value and
        asserts 'UI' appears on that SAME line.  A purpose swap — e.g. ``cockpit``
        mapped to 'internal' — passes a plain token check but fails here.
        """
        import owlbear_kanban.activity_store as store_mod  # noqa: PLC0415

        doc = store_mod.__doc__ or ""
        cockpit_decl_lines = [ln for ln in doc.splitlines() if "``cockpit``" in ln]
        assert cockpit_decl_lines, (
            "activity_store docstring has no line declaring '``cockpit``' as a source value (AC3)"
        )
        assert any("ui" in ln.lower() for ln in cockpit_decl_lines), (
            "activity_store docstring: the ``cockpit`` declaration line must also "
            "contain 'UI' on the same line, binding cockpit to its UI-initiated "
            "purpose (AC3). Purpose swaps or relocations are not accepted."
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
            "serve/cockpit/README.md still contains 'actor: \"cockpit\"' — "
            "update audit-trail section to use source vocabulary per AC4"
        )

    def test_audit_trail_section_present(self, project_root: Path) -> None:
        """AC4 (strengthened): README must contain an audit-trail section heading.

        Without this, a removal of the section would false-green the absence test.
        """
        readme = (project_root / "serve/cockpit/README.md").read_text(encoding="utf-8")
        # Accept both the old and new heading styles (case-insensitive check)
        has_section = "## Audit Trail" in readme or "## audit trail" in readme.lower()
        assert has_section, (
            "serve/cockpit/README.md must contain an 'Audit Trail' section "
            "documenting the source attribution contract (AC4)"
        )

    def test_audit_trail_source_cockpit_mapping_present(self, project_root: Path) -> None:
        """AC4 (section-scoped, binding): Audit Trail section maps source="cockpit" to UI-initiated.

        Scopes the search to the Audit Trail section body only — tokens outside the
        section do not satisfy this assertion.  Also asserts the purpose appears on
        the SAME line as the source token, preventing false-greens from purpose swaps
        or cross-section token migrations.
        """
        readme = (project_root / "serve/cockpit/README.md").read_text(encoding="utf-8")
        section = _extract_audit_trail_section(readme)
        assert section, "Audit Trail section body not found in serve/cockpit/README.md (AC4)"
        cockpit_lines = [ln for ln in section.splitlines() if 'source="cockpit"' in ln]
        assert cockpit_lines, (
            'Audit Trail section must contain source="cockpit" mapping (AC4 — UI-initiated mutation attribution)'
        )
        assert any("ui-initiated" in ln.lower() for ln in cockpit_lines), (
            'Audit Trail section: the line containing source="cockpit" must also '
            'contain "UI-initiated" on the same line, binding the mapping to its '
            "purpose (AC4). Purpose swaps or relocations to other sections are not accepted."
        )

    def test_audit_trail_source_agent_mapping_present(self, project_root: Path) -> None:
        """AC4 (section-scoped, binding): Audit Trail section maps source="agent" to agent-initiated.

        Scopes the search to the Audit Trail section only and asserts the purpose
        appears on the SAME line as the source token.
        """
        readme = (project_root / "serve/cockpit/README.md").read_text(encoding="utf-8")
        section = _extract_audit_trail_section(readme)
        assert section, "Audit Trail section body not found in serve/cockpit/README.md (AC4)"
        agent_lines = [ln for ln in section.splitlines() if 'source="agent"' in ln]
        assert agent_lines, (
            'Audit Trail section must contain source="agent" mapping (AC4 — agent-initiated mutation attribution)'
        )
        assert any("agent-initiated" in ln for ln in agent_lines), (
            'Audit Trail section: the line containing source="agent" must also '
            'contain "agent-initiated" on the same line, binding the mapping to its '
            "purpose (AC4). Purpose swaps or relocations are not accepted."
        )

    def test_audit_trail_source_engine_mapping_present(self, project_root: Path) -> None:
        """AC4 (section-scoped, binding): Audit Trail section maps source="engine" to internal.

        Scopes the search to the Audit Trail section only and asserts the purpose
        appears on the SAME line as the source token.
        """
        readme = (project_root / "serve/cockpit/README.md").read_text(encoding="utf-8")
        section = _extract_audit_trail_section(readme)
        assert section, "Audit Trail section body not found in serve/cockpit/README.md (AC4)"
        engine_lines = [ln for ln in section.splitlines() if 'source="engine"' in ln]
        assert engine_lines, (
            'Audit Trail section must contain source="engine" mapping (AC4 — internal engine operation attribution)'
        )
        assert any("internal" in ln for ln in engine_lines), (
            'Audit Trail section: the line containing source="engine" must also '
            'contain "internal" on the same line, binding the mapping to its '
            "purpose (AC4). Purpose swaps or relocations are not accepted."
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
        assert not violations, "AC6 violation — modules still importing activity_log:\n" + "\n".join(
            f"  {v}" for v in violations
        )
