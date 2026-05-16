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

    def test_checklist_exactly_four_items(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        items = re.findall(r"### Item \d+:", content)
        assert len(items) == 4, (
            f"SKILL.md must have exactly 4 checklist items under '### Item N:' headings, found {len(items)}: {items}"
        )

    def test_checklist_has_no_diagram_maintenance_item(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "Diagram Maintenance" not in content, "SKILL.md must not have a 'Diagram Maintenance' checklist item"

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
        assert "TODO marker" in content, "SKILL.md must contain TODO marker insertion rules"

    def test_todo_marker_blockquote_format_documented(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "> **TODO:**" in content, "SKILL.md must document the TODO marker visible blockquote format: > **TODO:**"

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
        diagram_lines = [line for line in content.splitlines() if "diagram" in line.lower()]
        assert len(diagram_lines) == 0, (
            f"doc-writer.agent.md must have zero 'diagram' references, found {len(diagram_lines)}: {diagram_lines[:3]}"
        )

    def test_no_excalidraw_file_references(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        assert ".excalidraw" not in content, "doc-writer.agent.md must not reference .excalidraw files"

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
        ), "doc-audit.prompt.md must include a TODO marker batch resolution dimension"

    def test_diagram_ownership_section_present(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(
            r"[Dd]iagram.*owner|[Dd]iagram.*responsib|[Dd]iagram.*full.*responsib",
            content,
        ), "doc-audit.prompt.md must include a diagram ownership / full responsibility section"

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
            "w-doc-update/SKILL.md must not contain '### Item 5' (removed: old Diagram Maintenance item)"
        )

    def test_no_item_6_section_heading(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 6" not in content, (
            "w-doc-update/SKILL.md must not contain '### Item 6' (removed: old Explicit Diagram Creation item)"
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

    def test_no_item5_prose_reference(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert not re.search(r"\bItem 5\b", content), (
            "SKILL.md must not contain any 'Item 5' reference in prose or headings "
            "(old Diagram Maintenance item removed in v3 — ban extends beyond just heading format)"
        )

    def test_no_item6_prose_reference(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert not re.search(r"\bItem 6\b", content), (
            "SKILL.md must not contain any 'Item 6' reference in prose or headings "
            "(old Explicit Diagram Creation item removed in v3 — ban extends beyond just heading format)"
        )


class TestFromAC_TodoMarkerFormat:
    """AC5: TODO marker format grep pattern works: > **TODO:** {category} — {description} [#{id}]"""

    def test_todo_marker_format_verbatim_in_skill(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "> **TODO:**" in content, "w-doc-update/SKILL.md must document the exact TODO marker format: > **TODO:**"

    def test_four_todo_categories_documented(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        for category in ("stale", "inaccurate", "missing", "unverified"):
            assert category in content, f"w-doc-update/SKILL.md must document the '{category}' TODO marker category"

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

    def test_todo_marker_complete_template(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        complete_template = "> **TODO:** {category} — {description} [#{id}]"
        assert complete_template in content, (
            f"SKILL.md must contain the exact complete TODO marker template: {complete_template!r}"
        )


class TestFromAC_ChecklistItemNames:
    """AC1 (tightened, td:2): exact brief-defined item names and required per-item behaviors."""

    def test_item1_name_is_readme_verification(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 1: README Verification" in content, (
            "SKILL.md Item 1 must be named 'README Verification' per refined AC1 (brief §checklist)"
        )

    def test_item2_name_is_external_attribution(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 2: External Attribution" in content, (
            "SKILL.md Item 2 must be named 'External Attribution' per refined AC1"
        )

    def test_item3_name_is_research_doc(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "### Item 3: Research Doc" in content, "SKILL.md Item 3 must be named 'Research Doc' per refined AC1"

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
            f"SKILL.md must not have a docstring checklist item (out of scope per brief); found: {docstring_items}"
        )

    def test_no_diagram_in_any_checklist_heading(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        item_headings = re.findall(r"### Item \d+:.*", content)
        diagram_items = [h for h in item_headings if re.search(r"[Dd]iagram", h)]
        assert len(diagram_items) == 0, (
            f"SKILL.md must not have any diagram-related checklist item heading "
            f"(any 'Diagram*' word banned per refined AC1 — not just 'Diagram Maintenance'); "
            f"found: {diagram_items}"
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
            "Item 1 (README Verification) must include Layer 1 grep structural check for removed symbols"
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

    def test_item3_research_doc_mentions_verification_language(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 3:.*?(?=### Item 4:)", content, re.DOTALL)
        assert match, "Could not find Item 3 section in SKILL.md"
        item3 = match.group(0)
        assert re.search(r"verif|linked from", item3, re.IGNORECASE), (
            "Item 3 (Research Doc) must describe verifying the research file "
            "linked from the task body — discriminator per refined AC1"
        )

    def test_no_impact_fast_path_present(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        assert "no docs impact" in content, (
            "SKILL.md must include a no-impact fast path that outputs 'no docs impact' "
            "with evidence when all changed files map to no READMEs"
        )


class TestFromAC_ConventionMappingTable:
    """AC1 (R3 tightened): convention mapping must be a markdown table with all 5 brief rows."""

    def _step1_section(self) -> str:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"## Step 1.*?## Step 2", content, re.DOTALL)
        assert match, "Could not find Step 1 (Convention Mapping) section in SKILL.md"
        return match.group(0)

    def test_convention_mapping_is_table(self) -> None:
        step1 = self._step1_section()
        table_rows = [line for line in step1.splitlines() if line.strip().startswith("|")]
        assert len(table_rows) >= 2, (
            f"Convention mapping must use a markdown table (at least 2 pipe-delimited rows), "
            f"found {len(table_rows)} table rows — not just bullets"
        )

    def test_convention_mapping_has_setup_row(self) -> None:
        step1 = self._step1_section()
        assert "setup/**" in step1, (
            "Convention mapping table must include a row for 'setup/**' "
            "(maps to setup/setup-guide.md, setup/sharing-guide.md per brief)"
        )

    def test_convention_mapping_has_share_row(self) -> None:
        step1 = self._step1_section()
        assert "share/**" in step1, (
            "Convention mapping table must include a row for 'share/**' "
            "(maps to share/README.md, share/WIRING.md per brief)"
        )

    def test_convention_mapping_has_pyproject_tests_row(self) -> None:
        step1 = self._step1_section()
        assert "pyproject.toml" in step1, (
            "Convention mapping table must include 'pyproject.toml' (maps to serve/{pkg}/README.md per brief row 2)"
        )
        assert "tests/**" in step1, (
            "Convention mapping table must include 'tests/**' (maps to serve/{pkg}/README.md per brief row 2)"
        )

    def test_convention_mapping_has_public_interface_row(self) -> None:
        step1 = self._step1_section()
        assert re.search(r"public interface|README-consumer", step1), (
            "Convention mapping table must include a row for public interface changes "
            "(maps to README.md, README-consumer.md per brief row 5)"
        )

    def test_convention_mapping_has_src_selector(self) -> None:
        step1 = self._step1_section()
        assert "src/**" in step1, (
            "Convention mapping table must contain the literal 'src/**' selector "
            "(first table row is 'serve/{pkg}/src/**' → 'serve/{pkg}/README.md' per AC1 refined) — "
            "generic 'serve/{pkg}' presence does not prove this row exists"
        )

    def test_gate_rule_task_caused_blocks(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        gate_match = re.search(r"Gate rules:.*?(?=## )", content, re.DOTALL)
        assert gate_match, "SKILL.md must have a 'Gate rules:' section"
        gate_lines = gate_match.group(0).splitlines()
        assert any("task-caused" in line and "unverified" in line and "blocks" in line for line in gate_lines), (
            "SKILL.md Gate rules section must have a single line binding "
            "'task-caused' + 'unverified' + 'blocks' — section-scoped to prevent "
            "false-green via checklist duplicate lines (R6 gap)"
        )

    def test_gate_rule_preexisting_passes(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        gate_match = re.search(r"Gate rules:.*?(?=## )", content, re.DOTALL)
        assert gate_match, "SKILL.md must have a 'Gate rules:' section"
        gate_lines = gate_match.group(0).splitlines()
        assert any("pre-existing" in line and "unverified" in line and "passes" in line for line in gate_lines), (
            "SKILL.md Gate rules section must have a single line binding "
            "'pre-existing' + 'unverified' + 'passes' — section-scoped to prevent "
            "false-green via checklist duplicate lines (R6 gap)"
        )

    def test_no_impact_fast_path_advances(self) -> None:
        step1 = self._step1_section()
        assert re.search(r"no README", step1, re.IGNORECASE), (
            "Step 1 fast-path trigger must reference 'no READMEs' — "
            "proves the trigger condition (changed files map to no READMEs), "
            "not just the output phrase (R6 gap)"
        )
        assert "no docs impact" in step1, "Step 1 must include the no-impact fast path phrase 'no docs impact'"
        assert "with evidence" in step1, (
            "Step 1 no-impact fast path must require 'with evidence' — "
            "AC1 refined specifies output is 'no docs impact with evidence', not bare phrase"
        )
        assert "advance" in step1, "Step 1 no-impact fast path must say to 'advance' after writing 'no docs impact'"

    def test_convention_mapping_exact_src_row_coupled(self) -> None:
        step1 = self._step1_section()
        assert any("serve/{pkg}/src/**" in line and "serve/{pkg}/README.md" in line for line in step1.splitlines()), (
            "Convention mapping table must have a single row coupling "
            "'serve/{pkg}/src/**' to 'serve/{pkg}/README.md' — "
            "split checks on each token independently false-green when the src row "
            "points to a different destination (R5 gap)"
        )


class TestFromAC_AttributionRules:
    """AC7: Item 1 must specify attribution rules: task-caused issues fixed inline,
    pre-existing unresolved issues get a visible TODO marker.

    These tests are discriminating: a mutation that removes or weakens
    SKILL.md lines 'Fix task-caused issues inline.' and
    'For pre-existing unresolved issues, insert a visible TODO marker.'
    from Item 1 must fail these assertions even if the gate rules and
    global TODO marker section remain intact.
    """

    def _item1_section(self) -> str:
        content = SKILL_DOC_UPDATE.read_text()
        match = re.search(r"### Item 1:.*?(?=### Item 2:)", content, re.DOTALL)
        assert match, "Could not find Item 1 section in SKILL.md"
        return match.group(0)

    def test_item1_fix_task_caused_inline(self) -> None:
        item1 = self._item1_section()
        assert re.search(r"[Ff]ix\s+task.caused\s+issues\s+inline", item1), (
            "Item 1 (README Verification) must explicitly state 'Fix task-caused issues inline' "
            "as a per-item instruction — AC7 attribution rule: task-caused issues → fix inline; "
            "the gate rules section alone does not satisfy this requirement"
        )

    def test_item1_preexisting_issues_insert_todo_marker(self) -> None:
        item1 = self._item1_section()
        assert re.search(
            r"pre.existing.*insert.*TODO\s+marker",
            item1,
            re.IGNORECASE,
        ), (
            "Item 1 (README Verification) must state that pre-existing unresolved issues "
            "get a visible TODO marker — AC7 attribution rule: pre-existing → TODO marker; "
            "this instruction must appear in Item 1 body, not only in the gate rules section"
        )

    def test_item1_has_both_attribution_rules(self) -> None:
        item1 = self._item1_section()
        has_task_caused_inline = bool(re.search(r"[Ff]ix\s+task.caused\s+issues\s+inline", item1))
        has_preexisting_todo = bool(
            re.search(
                r"pre.existing.*insert.*TODO\s+marker",
                item1,
                re.IGNORECASE,
            )
        )
        assert has_task_caused_inline, (
            "Item 1 must contain AC7 attribution rule (1): 'Fix task-caused issues inline' — "
            "removing this rule from Item 1 must fail even if the Gate rules section is intact"
        )
        assert has_preexisting_todo, (
            "Item 1 must contain AC7 attribution rule (2): "
            "'pre-existing unresolved issues → insert a visible TODO marker' — "
            "removing this rule from Item 1 must fail even if the Gate rules section is intact"
        )

    def test_item1_attribution_rules_scoped_to_item1_not_only_gate(self) -> None:
        content = SKILL_DOC_UPDATE.read_text()
        item1_match = re.search(r"### Item 1:.*?(?=### Item 2:)", content, re.DOTALL)
        assert item1_match, "Could not find Item 1 section"
        item1 = item1_match.group(0)
        # Both attribution keywords must appear in Item 1 itself — not rely on
        # the Gate rules section being found after removing them from Item 1.
        assert "task-caused" in item1, (
            "The phrase 'task-caused' must appear inside Item 1 body — "
            "AC7 requires the per-item attribution rule, not just the global gate policy; "
            "removing it from Item 1 while keeping the Gate rules must still fail"
        )
        assert re.search(r"pre.existing", item1, re.IGNORECASE), (
            "The phrase 'pre-existing' must appear inside Item 1 body — "
            "AC7 requires the per-item attribution rule, not just the global gate policy; "
            "removing it from Item 1 while keeping the Gate rules must still fail"
        )
