from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SKILL_DOC_UPDATE = REPO_ROOT / "share" / "skills" / "w-doc-update" / "SKILL.md"
DOC_WRITER_AGENT = REPO_ROOT / "share" / "agents" / "doc-writer.agent.md"
DOC_AUDIT_PROMPT = REPO_ROOT / ".owlbear" / "prompts" / "doc-audit.prompt.md"


class TestFromAC_DocUpdateSkillContent:
    """AC1: w-doc-update/SKILL.md contains required content for the redesign."""

    def test_convention_mapping_serve_pkg_pattern(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "serve/{pkg}" in content, (
            "SKILL.md must contain convention-based README mapping with 'serve/{pkg}' pattern"
        )

    def test_convention_mapping_serve_pkg_to_readme(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        # Table must map serve/{pkg} paths to serve/{pkg}/README.md
        assert re.search(r"serve/\{pkg\}.*README", content), (
            "Convention mapping must show serve/{pkg} → serve/{pkg}/README.md relationship"
        )

    def test_checklist_has_exactly_four_items(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        items = re.findall(r"### Item \d+", content)
        assert len(items) == 4, (
            f"Checklist must have exactly 4 items, found {len(items)}: {items}"
        )

    def test_checklist_has_no_diagram_maintenance_item(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "Diagram Maintenance" not in content, (
            "SKILL.md must not have a 'Diagram Maintenance' checklist item"
        )

    def test_checklist_has_no_explicit_diagram_creation_item(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "Explicit Diagram Creation" not in content, (
            "SKILL.md must not have an 'Explicit Diagram Creation' checklist item"
        )

    def test_verification_procedure_layer1_grep_present(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert re.search(r"[Ll]ayer 1|Layer 1 —|grep.*structural|structural.*grep", content), (
            "SKILL.md must document Layer 1 (grep-based structural) verification"
        )

    def test_verification_procedure_layer2_editorial_present(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert re.search(r"[Ll]ayer 2|Layer 2 —|LLM.*editorial|editorial.*LLM", content), (
            "SKILL.md must document Layer 2 (LLM editorial) verification"
        )

    def test_todo_marker_insertion_rules_present(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "TODO marker" in content, (
            "SKILL.md must contain TODO marker insertion rules"
        )

    def test_todo_marker_blockquote_format_documented(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "> **TODO:**" in content, (
            "SKILL.md must document the TODO marker visible blockquote format: > **TODO:**"
        )

    def test_gate_rule_task_caused_content_blocks(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert re.search(r"task.caused|task.introduced|task.content", content, re.IGNORECASE), (
            "SKILL.md must document that task-caused unverified content blocks the gate"
        )

    def test_gate_rule_preexisting_content_passes(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert re.search(r"pre.existing", content, re.IGNORECASE), (
            "SKILL.md must document that pre-existing unverified content passes the gate"
        )


class TestFromAC_DocWriterAgentNoDiagrams:
    """AC2: doc-writer.agent.md contains NO references to diagrams, Excalidraw, or .excalidraw files."""

    def test_no_diagram_references_anywhere(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        diagram_lines = [
            line for line in content.splitlines() if "diagram" in line.lower()
        ]
        assert len(diagram_lines) == 0, (
            f"doc-writer.agent.md must have zero 'diagram' references, "
            f"found {len(diagram_lines)}: {diagram_lines[:3]}"
        )

    def test_no_excalidraw_file_references(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        assert ".excalidraw" not in content, (
            "doc-writer.agent.md must not reference .excalidraw files"
        )

    def test_no_excalidraw_brand_references(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        assert "excalidraw" not in content.lower(), (
            "doc-writer.agent.md must not reference Excalidraw in any form (case-insensitive)"
        )


class TestFromAC_DocAuditPromptContent:
    """AC3: doc-audit.prompt.md includes TODO marker batch resolution, diagram ownership, describes-based verification."""

    def test_todo_marker_batch_resolution_dimension_present(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(
            r"TODO.*marker.*resol|resol.*TODO.*marker|TODO marker.*batch|batch.*TODO marker",
            content,
            re.IGNORECASE,
        ), (
            "doc-audit.prompt.md must include a TODO marker batch resolution dimension"
        )

    def test_diagram_ownership_section_present(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(
            r"[Dd]iagram.*owner|[Dd]iagram.*responsib|[Dd]iagram.*full.*responsib",
            content,
        ), (
            "doc-audit.prompt.md must include a diagram ownership / full responsibility section"
        )

    def test_describes_based_diagram_verification_present(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(
            r"`describes`.*diagram|diagram.*`describes`|describes.*\.excalidraw|\.excalidraw.*describes",
            content,
            re.IGNORECASE,
        ), (
            "doc-audit.prompt.md must include describes-based diagram verification "
            "(matching diagrams to changed files via doc-index 'describes' globs)"
        )


class TestFromAC_NoOldDiagramItems:
    """AC4: No references to old 'item 5' or 'item 6' (diagram maintenance/creation) remain in w-doc-update."""

    def test_no_item_5_section_heading(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 5" not in content, (
            "w-doc-update/SKILL.md must not contain '### Item 5' "
            "(removed: old Diagram Maintenance item)"
        )

    def test_no_item_6_section_heading(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 6" not in content, (
            "w-doc-update/SKILL.md must not contain '### Item 6' "
            "(removed: old Explicit Diagram Creation item)"
        )

    def test_output_template_no_diagram_row_5(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert not re.search(r"\|\s*5\s*\|.*[Dd]iagram", content), (
            "Output template in w-doc-update must not contain a row 5 for diagram maintenance"
        )

    def test_output_template_no_diagram_row_6(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert not re.search(r"\|\s*6\s*\|.*[Dd]iagram", content), (
            "Output template in w-doc-update must not contain a row 6 for diagram creation"
        )


class TestFromAC_TodoMarkerFormat:
    """AC5: TODO marker format grep pattern works: > **TODO:** {category} — {description} [#{id}]"""

    def test_todo_marker_format_verbatim_in_skill(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "> **TODO:**" in content, (
            "w-doc-update/SKILL.md must document the exact TODO marker format: > **TODO:**"
        )

    def test_four_todo_categories_documented(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        for category in ("stale", "inaccurate", "missing", "unverified"):
            assert category in content, (
                f"w-doc-update/SKILL.md must document the '{category}' TODO marker category"
            )

    def test_todo_marker_includes_task_ref_placeholder(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        # Format must show the [#{id}] task reference component
        assert re.search(r"\[#\{id\}\]|\[#\d+\]", content), (
            "w-doc-update/SKILL.md must document the [#{id}] task reference in the TODO marker format"
        )

    def test_todo_marker_format_is_greppable(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        # The skill must show that the format is greppable (> **TODO:** prefix is consistent)
        # A concrete example like "> **TODO:** stale — ..." must appear
        assert re.search(r"> \*\*TODO:\*\* (stale|inaccurate|missing|unverified)", content), (
            "w-doc-update/SKILL.md must include a concrete TODO marker example with a category"
        )


class TestFromAC_ChecklistItemNames:
    """AC1 (tightened, td:2): exact brief-defined item names and required per-item behaviors."""

    def test_item1_name_is_readme_verification(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 1: README Verification" in content, (
            "SKILL.md Item 1 must be named 'README Verification' per refined AC1 "
            "(brief §checklist)"
        )

    def test_item2_name_is_external_attribution(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 2: External Attribution" in content, (
            "SKILL.md Item 2 must be named 'External Attribution' per refined AC1"
        )

    def test_item3_name_is_research_doc(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 3: Research Doc" in content, (
            "SKILL.md Item 3 must be named 'Research Doc' per refined AC1"
        )

    def test_item4_name_is_deletion_detection(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 4: Deletion Detection" in content, (
            "SKILL.md Item 4 must be named 'Deletion Detection' per refined AC1"
        )

    def test_no_docstring_checklist_item(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        item_headings = re.findall(r"### Item \d+:.*", content)
        docstring_items = [h for h in item_headings if re.search(r"[Dd]ocstring", h)]
        assert len(docstring_items) == 0, (
            f"SKILL.md must not have a docstring checklist item (out of scope per brief); "
            f"found: {docstring_items}"
        )

    def test_item1_mentions_convention_mapping(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 1:.*?(?=### Item 2:)", content, re.DOTALL)
        assert match, "Could not find Item 1 section in SKILL.md"
        item1 = match.group(0)
        assert re.search(r"convention.map|convention map", item1, re.IGNORECASE), (
            "Item 1 (README Verification) must describe convention-mapped full-file read"
        )

    def test_item1_has_layer1_grep_structural_check(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 1:.*?(?=### Item 2:)", content, re.DOTALL)
        assert match, "Could not find Item 1 section in SKILL.md"
        item1 = match.group(0)
        assert re.search(r"[Ll]ayer 1", item1), (
            "Item 1 (README Verification) must include Layer 1 grep structural check "
            "for removed symbols"
        )

    def test_item1_has_layer2_editorial(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 1:.*?(?=### Item 2:)", content, re.DOTALL)
        assert match, "Could not find Item 1 section in SKILL.md"
        item1 = match.group(0)
        assert re.search(r"[Ll]ayer 2", item1), (
            "Item 1 (README Verification) must include Layer 2 LLM editorial comparison"
        )

    def test_item2_external_attribution_mentions_sources_overview(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 2:.*?(?=### Item 3:)", content, re.DOTALL)
        assert match, "Could not find Item 2 section in SKILL.md"
        item2 = match.group(0)
        assert "sources/overview.md" in item2, (
            "Item 2 (External Attribution) must reference .owlbear/sources/overview.md"
        )

    def test_item4_deletion_detection_mentions_child_task(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 4:.*?(?=## |\Z)", content, re.DOTALL)
        assert match, "Could not find Item 4 section in SKILL.md"
        item4 = match.group(0)
        assert re.search(r"child.task|child task", item4, re.IGNORECASE), (
            "Item 4 (Deletion Detection) must describe the child-task creation protocol"
        )

    def test_item4_deletion_detection_mentions_dr_protocol(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 4:.*?(?=## |\Z)", content, re.DOTALL)
        assert match, "Could not find Item 4 section in SKILL.md"
        item4 = match.group(0)
        assert re.search(r"\bDR\b|[Dd]ecision [Rr]equest", item4), (
            "Item 4 (Deletion Detection) must reference the DR (decision request) protocol"
        )

    def test_no_impact_fast_path_present(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "no docs impact" in content, (
            "SKILL.md must include a no-impact fast path that outputs 'no docs impact' "
            "with evidence when all changed files map to no READMEs"
        )
