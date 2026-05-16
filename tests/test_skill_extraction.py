"""Failing tests for task #1286: P2-02 — Extract file-placement and layout sections.

All tests must FAIL on the current codebase; they pass once the builder task (#1286) is done.

AC coverage:
  AC1 (td:1) — test_r_project_standards_file_placement_extracted
  AC2 (td:1) — test_h_python_conventions_project_layout_extracted
  AC3 (td:1) — test_copilot_instructions_has_file_placement_section,
                test_copilot_instructions_has_project_layout_section
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILLS_ROOT = _REPO_ROOT / "share" / "skills"
_COPILOT_INSTRUCTIONS = _REPO_ROOT / ".github" / "copilot-instructions.md"

# Heading that must be ABSENT after extraction from r-project-standards
_FILE_PLACEMENT_HEADING = "## 2. File Placement"

# Heading that must be ABSENT after extraction from h-python-conventions
_PROJECT_LAYOUT_HEADING = "## Project Layout"


class TestFromAC_FilePlacementExtraction:
    """Verification tests for P2-02 skill content extraction. Task #1286."""

    # ---- AC1 (td:1): r-project-standards §2 File Placement extracted ------------------

    def test_r_project_standards_file_placement_extracted(self) -> None:
        """§2 File Placement must be absent from r-project-standards/SKILL.md.

        The skill must retain commit discipline, attribution, priority scheme,
        and tag taxonomy sections per AC1.
        """
        skill_file = _SKILLS_ROOT / "r-project-standards" / "SKILL.md"
        assert skill_file.exists(), f"Expected {skill_file.relative_to(_REPO_ROOT)} to exist"
        content = skill_file.read_text(encoding="utf-8")

        # AC1 extraction: File Placement section heading must be gone
        assert _FILE_PLACEMENT_HEADING not in content, (
            f"r-project-standards/SKILL.md still contains '{_FILE_PLACEMENT_HEADING}'; "
            "the §2 File Placement table must be extracted to .github/copilot-instructions.md"
        )

        # AC1 retention: commit format, attribution, priority, tags sections must remain
        for heading_fragment in (
            "Commit Discipline",
            "Attribution",
            "Priority Scheme",
            "Tag Taxonomy",
        ):
            assert heading_fragment in content, (
                f"r-project-standards/SKILL.md must still contain '{heading_fragment}' after File Placement extraction"
            )

    # ---- AC2 (td:1): h-python-conventions Project Layout extracted --------------------

    def test_h_python_conventions_project_layout_extracted(self) -> None:
        """## Project Layout must be absent from h-python-conventions/SKILL.md.

        The skill must retain Package Management, Code Style, Testing, and other
        coding convention sections per AC2.
        """
        skill_file = _SKILLS_ROOT / "h-python-conventions" / "SKILL.md"
        assert skill_file.exists(), f"Expected {skill_file.relative_to(_REPO_ROOT)} to exist"
        content = skill_file.read_text(encoding="utf-8")

        # AC2 extraction: Project Layout section heading must be gone
        assert _PROJECT_LAYOUT_HEADING not in content, (
            f"h-python-conventions/SKILL.md still contains '{_PROJECT_LAYOUT_HEADING}'; "
            "this section must be extracted to .github/copilot-instructions.md"
        )

        # AC2 retention: coding conventions must remain
        for heading_fragment in ("Package Management", "Code Style", "Testing"):
            assert heading_fragment in content, (
                f"h-python-conventions/SKILL.md must still contain '{heading_fragment}' after Project Layout extraction"
            )

    # ---- AC3 (td:1): extracted content added to .github/copilot-instructions.md ------

    def test_copilot_instructions_has_file_placement_section(self) -> None:
        """copilot-instructions.md must contain a File Placement section.

        The section must use concrete serve/ paths (not workspace/ placeholders)
        per builder guidance from the architecture review.
        """
        assert _COPILOT_INSTRUCTIONS.exists(), f"Expected {_COPILOT_INSTRUCTIONS.relative_to(_REPO_ROOT)} to exist"
        content = _COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

        assert "File Placement" in content, (
            "copilot-instructions.md must contain a 'File Placement' section (extracted from r-project-standards §2)"
        )
        # Builder guidance: extracted table must use concrete serve/ paths, not workspace/
        section_text = content.split("File Placement", 1)[1].split("\n## ", 1)[0]
        assert "serve/" in section_text, (
            "File Placement section in copilot-instructions.md must use concrete 'serve/' "
            "paths, not 'workspace/' placeholders (per architecture review builder guidance)"
        )

    def test_copilot_instructions_has_project_layout_section(self) -> None:
        """copilot-instructions.md must contain a Project Layout section.

        The section must document concrete source paths (serve/*/src/) per builder guidance.
        """
        assert _COPILOT_INSTRUCTIONS.exists(), f"Expected {_COPILOT_INSTRUCTIONS.relative_to(_REPO_ROOT)} to exist"
        content = _COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

        assert "Project Layout" in content, (
            "copilot-instructions.md must contain a 'Project Layout' section (extracted from h-python-conventions)"
        )
        # Builder guidance: layout section must use concrete serve/ paths
        section_text = content.split("Project Layout", 1)[1].split("\n## ", 1)[0]
        assert "serve/" in section_text, (
            "Project Layout section in copilot-instructions.md must use concrete 'serve/' "
            "paths, not 'workspace/' placeholders (per architecture review builder guidance)"
        )
