from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOC_AUDIT_PROMPT = REPO_ROOT / ".owlbear" / "prompts" / "doc-audit.prompt.md"


class TestFromAC_FindingLoopOneAtATime:
    """AC4: §4 Finding Loop restores one-at-a-time default + batch exception for TODO marker."""

    def test_finding_loop_one_at_a_time_default(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(
            r"one.at.a.time|one finding at a time",
            content,
            re.IGNORECASE,
        ), (
            "§4 Finding Loop must specify one-finding-at-a-time as the default processing mode"
        )

    def test_finding_loop_control_points_present(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        # Must describe the present → approval → apply → next cycle
        assert re.search(
            r"present.*finding.*approv|approv.*apply|apply.*fix.*next",
            content,
            re.IGNORECASE | re.DOTALL,
        ), (
            "§4 Finding Loop must specify the control points: "
            "present finding → collect approval → apply fix → next finding"
        )

    def test_finding_loop_batch_exception_for_todo(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        # §4 must note the batch exception that defers to §5 for TODO markers
        assert re.search(
            r"batch.exception|exception.*batch|TODO.*batch.*except|except.*TODO.*batch|§5.*applies|applies.*§5",
            content,
            re.IGNORECASE,
        ), (
            "§4 Finding Loop must include an explicit batch exception for TODO marker resolution "
            "(§5 batch workflow applies instead)"
        )


class TestFromAC_DimensionReferenceTable:
    """AC5: Dimension reference table D1-D8, rule families, empirical notes for D4/D5/D6."""

    def test_all_eight_dimensions_referenced(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        missing = [
            dim for dim in ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"]
            if dim not in content
        ]
        assert not missing, (
            f"Dimension reference table must include all D1-D8; missing: {missing}"
        )

    def test_dimension_table_maps_name_and_rule_family(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        # D1 → Structural is the clearest anchor; STR-* is the rule family
        assert re.search(r"D1.*Structural|Structural.*D1", content, re.IGNORECASE), (
            "Dimension table must map D1 → 'Structural' with associated rule family (STR-*)"
        )

    def test_d4_accuracy_marked_empirical(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(r"D4.*empirical|empirical.*D4", content, re.IGNORECASE), (
            "D4 (Accuracy) must be noted as 'empirical' in the dimension reference table "
            "instead of a rule ID"
        )

    def test_d5_coverage_integrity_marked_empirical(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(r"D5.*empirical|empirical.*D5", content, re.IGNORECASE), (
            "D5 (Coverage Integrity) must be noted as 'empirical' in the dimension reference "
            "table instead of a rule ID"
        )

    def test_d6_currency_marked_empirical(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert re.search(r"D6.*empirical|empirical.*D6", content, re.IGNORECASE), (
            "D6 (Currency/Staleness) must be noted as 'empirical' in the dimension reference "
            "table instead of a rule ID"
        )

    def test_r_doc_standards_referenced_as_canonical_source(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert "r-doc-standards" in content, (
            "Dimension table must reference r-doc-standards as the canonical source — "
            "table references the skill rather than duplicating full probes"
        )

    def test_d7_name_is_cross_reference_integrity(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        # D7 row must name "Cross-reference Integrity" (not "Audience Fitness" or "Link Integrity")
        assert re.search(
            r"\|\s*D7\s*\|[^|\n]*Cross.reference\s+Integrity",
            content,
            re.IGNORECASE,
        ), (
            "D7 row in the dimension table must map to 'Cross-reference Integrity' "
            "(canonical: r-doc-standards DIM-7); live prompt incorrectly maps D7 to 'Audience Fitness'"
        )

    def test_d7_rule_family_is_xref(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        # D7 row must specify XREF-* as the rule family
        assert re.search(
            r"\|\s*D7\s*\|[^|\n]*\|[^|\n]*XREF",
            content,
            re.IGNORECASE,
        ), (
            "D7 row must specify XREF-* as the source rule family "
            "(canonical: r-doc-standards DIM-7 uses XREF-1, XREF-2, XREF-3); "
            "live prompt incorrectly maps D7 to AUD-*"
        )

    def test_d8_name_is_audience_fitness(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        # D8 row must name "Audience Fitness" (not "Link Integrity")
        assert re.search(
            r"\|\s*D8\s*\|[^|\n]*Audience\s+Fitness",
            content,
            re.IGNORECASE,
        ), (
            "D8 row in the dimension table must map to 'Audience Fitness' "
            "(canonical: r-doc-standards DIM-8); live prompt incorrectly maps D8 to 'Link Integrity'"
        )

    def test_d8_rule_family_is_aud(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        # D8 row must specify AUD-* as the rule family
        assert re.search(
            r"\|\s*D8\s*\|[^|\n]*\|[^|\n]*AUD-\*",
            content,
            re.IGNORECASE,
        ), (
            "D8 row must specify AUD-* as the source rule family "
            "(canonical: r-doc-standards DIM-8 uses AUD-*); "
            "live prompt incorrectly maps D8 to LNK-*"
        )


class TestFromAC_PreAuditGate:
    """AC6: Pre-audit gate — agent must load r-doc-standards + doc-types.instructions.md
    before scanning files (restores pre-rewrite standards chain)."""

    def test_pre_audit_gate_loads_r_doc_standards(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert "r-doc-standards" in content, (
            "Pre-audit gate must instruct the agent to load the r-doc-standards skill "
            "before scanning files"
        )

    def test_pre_audit_gate_loads_doc_types_instructions(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        assert "doc-types.instructions.md" in content, (
            "Pre-audit gate must instruct the agent to load doc-types.instructions.md "
            "before scanning files"
        )

    def test_pre_audit_gate_appears_before_scope_section(self) -> None:
        content = DOC_AUDIT_PROMPT.read_text()
        gate_pos = content.find("r-doc-standards")
        scope_pos = content.find("## 3. Scope")
        assert gate_pos != -1, (
            "r-doc-standards load instruction must be present in doc-audit.prompt.md"
        )
        assert scope_pos != -1, "§3 Scope section must exist"
        assert gate_pos < scope_pos, (
            "Pre-audit gate (r-doc-standards loading) must appear before the §3 Scope / "
            "scan section — gate runs before any file scanning begins"
        )
