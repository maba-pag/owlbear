from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DOC_WRITER_AGENT = REPO_ROOT / "share" / "agents" / "doc-writer.agent.md"


def _extract_section(content: str, tag: str) -> str:
    """Extract content between <tag> and </tag> (exclusive)."""
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, content, re.DOTALL)
    assert match, f"Expected <{tag}> section in doc-writer.agent.md"
    return match.group(1)


class TestFromAC_CriticalRulesChecklist:
    """AC #2 (td:1): critical_rules names the 4-item checklist from w-doc-update v3."""

    def test_critical_rules_names_readme_verification(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert "README Verification" in rules, (
            "critical_rules must explicitly name the 'README Verification' checklist item"
        )

    def test_critical_rules_names_external_attribution(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert "External Attribution" in rules, (
            "critical_rules must explicitly name the 'External Attribution' checklist item"
        )

    def test_critical_rules_names_research_doc(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert "Research Doc" in rules, (
            "critical_rules must explicitly name the 'Research Doc' checklist item"
        )

    def test_critical_rules_names_deletion_detection(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert "Deletion Detection" in rules, (
            "critical_rules must explicitly name the 'Deletion Detection' checklist item"
        )

    def test_critical_rules_all_four_checklist_items_present(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        required = [
            "README Verification",
            "External Attribution",
            "Research Doc",
            "Deletion Detection",
        ]
        missing = [name for name in required if name not in rules]
        assert not missing, (
            f"critical_rules is missing {len(missing)} checklist item name(s): {missing}"
        )


class TestFromAC_CriticalRulesConventionMapping:
    """AC #2 (td:1): critical_rules references the serve/{pkg}/src → serve/{pkg}/README.md mapping."""

    def test_critical_rules_references_serve_pkg_pattern(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert "serve/{pkg}" in rules, (
            "critical_rules must reference the convention-based mapping pattern 'serve/{pkg}'"
        )

    def test_critical_rules_references_readme_destination(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert re.search(r"serve/\{pkg\}.*README|README.*serve/\{pkg\}", rules), (
            "critical_rules must show serve/{pkg} mapping to README.md "
            "(convention-based README assignment)"
        )


class TestFromAC_CriticalRulesTodoMarkers:
    """AC #2 (td:1): critical_rules references TODO marker insertion."""

    def test_critical_rules_references_todo_marker(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert "TODO marker" in rules, (
            "critical_rules must reference TODO marker insertion "
            "(for pre-existing unverified content)"
        )


class TestFromAC_CriticalRulesGateBlocking:
    """AC #2 (td:1): critical_rules documents gate-blocking semantics."""

    def test_critical_rules_task_caused_content_blocks_gate(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert re.search(r"task.caused|task.introduced|task.content", rules, re.IGNORECASE), (
            "critical_rules must state that task-caused unverified content blocks the gate"
        )

    def test_critical_rules_preexisting_content_passes(self) -> None:
        content = DOC_WRITER_AGENT.read_text()
        rules = _extract_section(content, "critical_rules")
        assert re.search(r"pre.existing", rules, re.IGNORECASE), (
            "critical_rules must state that pre-existing unverified content passes the gate "
            "(with a TODO marker)"
        )
