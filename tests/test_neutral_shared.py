"""Tests for P1 completion conditions: system instruction neutrality and init.py scaffold.

Verifies that:
- share/instructions/ files contain no `serve/` references (AC2)
- .github/copilot-instructions.md has a ## Directory Structure section (AC3)
- init() generates a copilot-instructions.md with path-mapping scaffold (AC4)
- No dangling cross-references in key files to owlbear-system.instructions.md sections (AC5)
"""

from __future__ import annotations

import importlib.util
import re
import types
from pathlib import Path

_OWLBEAR_SYSTEM_REL = "share/instructions/owlbear-system.instructions.md"
_INIT_PY_REL = "setup/init.py"


def _load_init(project_root: Path) -> types.ModuleType:
    init_path = project_root / _INIT_PY_REL
    spec = importlib.util.spec_from_file_location("owlbear_init", init_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# AC2 — No serve/ references in share/instructions/
# ---------------------------------------------------------------------------


class TestFromAC_SystemInstructionNeutrality:
    """AC2: share/instructions/**/*.md must not contain serve/ path references."""

    def test_mcp_exemption_is_token_scoped(self, tmp_path: Path) -> None:
        """Token-scoped mcp- exclusion catches serve/ violations on the same line.

        A line containing both 'mcp-kanban' and 'serve/foo/' must still be flagged:
        only the mcp-* token is exempt, not the whole line. Uses re.sub to strip
        mcp-\\S+ tokens before checking for serve/.
        """
        instructions_dir = tmp_path / "share" / "instructions"
        instructions_dir.mkdir(parents=True)
        md = instructions_dir / "synthetic.md"
        # Line that has BOTH an mcp- name token AND a serve/ path reference
        md.write_text("See mcp-kanban and also serve/tools/ for details.\n")

        violations: list[str] = []
        for md_file in sorted(instructions_dir.rglob("*.md")):
            for lineno, line in enumerate(md_file.read_text(encoding="utf-8").splitlines(), start=1):
                if line.strip().startswith("applyTo:"):
                    continue
                sanitized = re.sub(r"mcp-\S+", "", line)
                if "serve/" in sanitized:
                    violations.append(f"{md_file.name}:{lineno}: {line.strip()!r}")

        # With token-scoped logic, serve/ is still caught when mcp- appears on the same line.
        assert violations, (
            "Token-scoped mcp- exclusion failed to catch serve/ on the same line as mcp-*.\n"
            "Line: 'See mcp-kanban and also serve/tools/ for details.'\n"
            "After stripping mcp-\\S+ tokens, serve/ should still be present."
        )

    def test_instructions_have_no_serve_refs(self, project_root: Path) -> None:
        """All instruction files are free of serve/ path references.

        Excludes:
        - Lines whose stripped content starts with 'applyTo:' (P2 scope, task #1290)
        - mcp-* tokens (e.g. mcp-kanban) are stripped before checking; a serve/
          reference on the same line as mcp-* is still a violation.
        """
        instructions_dir = project_root / "share" / "instructions"
        violations: list[str] = []
        for md_file in sorted(instructions_dir.rglob("*.md")):
            for lineno, line in enumerate(md_file.read_text(encoding="utf-8").splitlines(), start=1):
                if line.strip().startswith("applyTo:"):
                    continue
                sanitized = re.sub(r"mcp-\S+", "", line)
                if "serve/" in sanitized:
                    rel = md_file.relative_to(project_root)
                    violations.append(f"{rel}:{lineno}: {line.strip()!r}")
        assert not violations, f"Found {len(violations)} serve/ reference(s) in share/instructions/:\n" + "\n".join(
            violations
        )


# ---------------------------------------------------------------------------
# AC3 — .github/copilot-instructions.md has ## Directory Structure
# ---------------------------------------------------------------------------


class TestFromAC_CopilotInstructionsDirectoryStructure:
    """AC3: .github/copilot-instructions.md must have a Directory Structure section."""

    def test_has_directory_structure_heading(self, project_root: Path) -> None:
        """copilot-instructions.md contains a '## Directory Structure' heading."""
        content = (project_root / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        headings = [line.strip() for line in content.splitlines() if line.startswith("## ")]
        assert any("Directory Structure" in h for h in headings), (
            f"No '## Directory Structure' heading found. Headings present: {headings}"
        )

    def test_has_table_row_in_directory_section(self, project_root: Path) -> None:
        """copilot-instructions.md has at least one table row under Directory Structure."""
        content = (project_root / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        lines = content.splitlines()
        in_dir_section = False
        table_rows: list[str] = []
        for line in lines:
            if line.startswith("## ") and "Directory Structure" in line:
                in_dir_section = True
                continue
            if in_dir_section:
                if line.startswith("## "):
                    break
                if line.startswith("|") and not set(line.strip()) <= set("|-: "):
                    table_rows.append(line)
        assert table_rows, "No Markdown table rows found under '## Directory Structure' section."


# ---------------------------------------------------------------------------
# AC4 — init() generates copilot-instructions.md with path-mapping scaffold
# ---------------------------------------------------------------------------


class TestFromAC_InitScaffold:
    """AC4: init() generates .github/copilot-instructions.md with directory section."""

    def test_generates_copilot_instructions(self, project_root: Path, tmp_path: Path) -> None:
        """init() creates .github/copilot-instructions.md in target_dir."""
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        generated = tmp_path / ".github" / "copilot-instructions.md"
        assert generated.exists(), f".github/copilot-instructions.md was not created in {tmp_path}"

    def test_has_directory_section_heading(self, project_root: Path, tmp_path: Path) -> None:
        """Generated copilot-instructions.md has a directory/path-mapping heading."""
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        headings = [line.strip() for line in content.splitlines() if line.startswith("#")]
        has_dir_heading = any(any(kw in h.lower() for kw in ("directory", "path", "structure")) for h in headings)
        assert has_dir_heading, f"No directory/path-mapping section heading found. Found headings: {headings}"

    def test_has_path_entry(self, project_root: Path, tmp_path: Path) -> None:
        """Generated copilot-instructions.md has at least one path entry (table row)."""
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        table_rows = [
            line for line in content.splitlines() if line.startswith("|") and not set(line.strip()) <= set("|-: ")
        ]
        assert table_rows, "Generated copilot-instructions.md has no Markdown table rows with path entries."

    def test_idempotent(self, project_root: Path, tmp_path: Path) -> None:
        """init() called twice produces identical copilot-instructions.md content."""
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        first = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        module.init(tmp_path, project_root)
        second = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        assert first == second, "copilot-instructions.md content changed on second init() call."

    def test_path_entry_within_directory_section(self, project_root: Path, tmp_path: Path) -> None:
        """Generated file has path-entry table rows inside the directory section.

        The heading check and path-entry check must be section-local: at least one
        non-separator table row must appear between the directory/path-mapping heading
        and the next section heading. A table row anywhere else in the file is not
        sufficient evidence that the directory section contains path entries.
        """
        module = _load_init(project_root)
        module.init(tmp_path, project_root)
        content = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        lines = content.splitlines()
        in_dir_section = False
        section_table_rows: list[str] = []
        for line in lines:
            if line.startswith("## ") and any(kw in line.lower() for kw in ("directory", "path", "structure")):
                in_dir_section = True
                continue
            if in_dir_section:
                if line.startswith("## "):
                    break
                if line.startswith("|") and not set(line.strip()) <= set("|-: "):
                    section_table_rows.append(line)

        assert section_table_rows, (
            "Generated copilot-instructions.md must have path-entry table rows "
            "within the directory/path-mapping section. A table row anywhere else "
            "in the file is not sufficient. Check that the directory section heading "
            "is present and followed immediately by a path-entry table."
        )


# ---------------------------------------------------------------------------
# AC5 — No dangling cross-refs to owlbear-system.instructions.md (regression)
# ---------------------------------------------------------------------------


class TestFromAC_NoDanglingCrossRefs:
    """AC5: § Section references to owlbear-system.instructions.md must be valid."""

    def test_section_refs_exist_in_owlbear_system(self, project_root: Path) -> None:
        """Every '§ SectionName' reference to owlbear-system.instructions.md exists."""
        owlbear_system = project_root / _OWLBEAR_SYSTEM_REL
        system_text = owlbear_system.read_text(encoding="utf-8")
        headings = {line.lstrip("#").strip() for line in system_text.splitlines() if line.startswith("#")}

        # Match: owlbear-system.instructions.md (optional punctuation) § SectionName
        ref_pattern = re.compile(r"owlbear-system\.instructions\.md[`'\" ]*§\s*([^(\n\]`]+)")
        cross_ref_files = [
            project_root / "share" / "README.md",
            project_root / "share" / "WIRING.md",
            project_root / "share" / "skills" / "h-agent-structure" / "SKILL.md",
            project_root / "share" / "skills" / "h-memory-structure" / "SKILL.md",
        ]

        missing: list[str] = []
        for ref_file in cross_ref_files:
            if not ref_file.exists():
                continue
            file_text = ref_file.read_text(encoding="utf-8")
            for match in ref_pattern.finditer(file_text):
                section_name = match.group(1).strip().rstrip(")(,. ")
                if not any(section_name in h for h in headings):
                    rel = ref_file.relative_to(project_root)
                    missing.append(f"{rel}: § {section_name!r} not found in owlbear-system.instructions.md")

        assert not missing, "Dangling section references found:\n" + "\n".join(missing)
