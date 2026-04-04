"""Tests for task #194: Add environment audit step to research-workflow skill.

AC contract under test (.github/skills/w-research/SKILL.md):
1. New mandatory checklist item 2 inserted between item 1 (Theoretical validity)
   and current item 2 (Prior art).
2. Item text contains "Environment audit" and the full IDE/runtime description.
3. Existing items 2-5 renumbered to 3-6; recommended items 6-7 renumbered to 7-8.
4. Mandatory range text updated from "Items 1-5 are mandatory" to "Items 1-6 are mandatory".
5. Trivial-task note updated from "items 1-3" to "items 1-4".
6. Self-critique checklist includes checkbox for "Verified no environment duplication".
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKILL_FILE = ROOT / ".github" / "skills" / "w-research" / "SKILL.md"


def _skill_text() -> str:
    return SKILL_FILE.read_text(encoding="utf-8")


class TestFromAC_EnvironmentAuditItem:
    """AC items 1-2: new item 2 inserted with correct text and position."""

    def test_environment_audit_item_exists(self) -> None:
        """'Environment audit' must appear in the checklist."""
        text = _skill_text()
        assert "Environment audit" in text

    def test_environment_audit_mentions_ide_and_runtime(self) -> None:
        """Item must mention IDE, runtime, installed extensions, and existing tooling."""
        text = _skill_text()
        assert "IDE" in text
        assert "runtime" in text
        assert "installed extensions" in text
        assert "existing tooling" in text

    def test_environment_audit_mentions_vscode_built_in_features(self) -> None:
        """Item must specifically mention VS Code built-in features."""
        text = _skill_text()
        assert "VS Code built-in features" in text

    def test_environment_audit_mentions_extension_provided_servers(self) -> None:
        """Item must mention extension-provided servers."""
        text = _skill_text()
        assert "extension-provided servers" in text

    def test_environment_audit_mentions_installed_packages(self) -> None:
        """Item must mention installed packages."""
        text = _skill_text()
        assert "installed packages" in text

    def test_environment_audit_is_numbered_item_2(self) -> None:
        """'Environment audit' must appear as item 2 in the numbered list."""
        text = _skill_text()
        lines = text.splitlines()
        item2_lines = [line for line in lines if re.match(r"^\s*2\.", line)]
        assert item2_lines, "No line starting with '2.' found in SKILL.md"
        item2_text = " ".join(item2_lines)
        assert "Environment audit" in item2_text, (
            f"Item 2 does not contain 'Environment audit'. Item 2 lines: {item2_lines}"
        )

    def test_environment_audit_after_theoretical_validity(self) -> None:
        """'Environment audit' must appear after 'Theoretical validity' in the file."""
        text = _skill_text()
        pos_theory = text.find("Theoretical validity")
        pos_audit = text.find("Environment audit")
        assert pos_theory != -1, "'Theoretical validity' not found in SKILL.md"
        assert pos_audit != -1, "'Environment audit' not found in SKILL.md"
        assert pos_theory < pos_audit, (
            "'Theoretical validity' must appear before 'Environment audit'"
        )

    def test_environment_audit_before_prior_art(self) -> None:
        """'Environment audit' must appear before 'Prior art' in the file."""
        text = _skill_text()
        pos_audit = text.find("Environment audit")
        pos_prior = text.find("Prior art")
        assert pos_audit != -1, "'Environment audit' not found in SKILL.md"
        assert pos_prior != -1, "'Prior art' not found in SKILL.md"
        assert pos_audit < pos_prior, (
            "'Environment audit' must appear before 'Prior art'"
        )


class TestFromAC_ChecklistRenumbering:
    """AC item 3: existing items 2-5 renumbered to 3-6, recommended 6-7 to 7-8."""

    def test_prior_art_is_item_3(self) -> None:
        """'Prior art' must be renumbered to item 3 (was item 2)."""
        text = _skill_text()
        lines = text.splitlines()
        item3_lines = [line for line in lines if re.match(r"^\s*3\.", line)]
        assert item3_lines, "No line starting with '3.' found in SKILL.md"
        item3_text = " ".join(item3_lines)
        assert "Prior art" in item3_text, (
            f"Item 3 does not contain 'Prior art'. Item 3 lines: {item3_lines}"
        )

    def test_technical_feasibility_is_item_4(self) -> None:
        """'Technical feasibility' must be renumbered to item 4 (was item 3)."""
        text = _skill_text()
        lines = text.splitlines()
        item4_lines = [line for line in lines if re.match(r"^\s*4\.", line)]
        assert item4_lines, "No line starting with '4.' found in SKILL.md"
        item4_text = " ".join(item4_lines)
        assert "Technical feasibility" in item4_text, (
            f"Item 4 does not contain 'Technical feasibility'. Item 4 lines: {item4_lines}"
        )

    def test_architecture_fit_is_item_5(self) -> None:
        """'Architecture fit' must be renumbered to item 5 (was item 4)."""
        text = _skill_text()
        lines = text.splitlines()
        item5_lines = [line for line in lines if re.match(r"^\s*5\.", line)]
        assert item5_lines, "No line starting with '5.' found in SKILL.md"
        item5_text = " ".join(item5_lines)
        assert "Architecture fit" in item5_text, (
            f"Item 5 does not contain 'Architecture fit'. Item 5 lines: {item5_lines}"
        )

    def test_implementation_approach_is_item_6(self) -> None:
        """'Implementation approach' must be renumbered to item 6 (was item 5)."""
        text = _skill_text()
        lines = text.splitlines()
        item6_lines = [line for line in lines if re.match(r"^\s*6\.", line)]
        assert item6_lines, "No line starting with '6.' found in SKILL.md"
        item6_text = " ".join(item6_lines)
        assert "Implementation approach" in item6_text, (
            f"Item 6 does not contain 'Implementation approach'. Item 6 lines: {item6_lines}"
        )

    def test_testing_strategy_is_item_7(self) -> None:
        """'Testing strategy' (recommended) must be renumbered to item 7 (was item 6)."""
        text = _skill_text()
        lines = text.splitlines()
        item7_lines = [line for line in lines if re.match(r"^\s*7\.", line)]
        assert item7_lines, "No line starting with '7.' found in SKILL.md"
        item7_text = " ".join(item7_lines)
        assert "Testing strategy" in item7_text, (
            f"Item 7 does not contain 'Testing strategy'. Item 7 lines: {item7_lines}"
        )

    def test_findings_documented_is_item_8(self) -> None:
        """'Findings documented' (recommended) must be renumbered to item 8 (was item 7)."""
        text = _skill_text()
        lines = text.splitlines()
        item8_lines = [line for line in lines if re.match(r"^\s*8\.", line)]
        assert item8_lines, "No line starting with '8.' found in SKILL.md"
        item8_text = " ".join(item8_lines)
        assert "Findings documented" in item8_text, (
            f"Item 8 does not contain 'Findings documented'. Item 8 lines: {item8_lines}"
        )

    def test_prior_art_not_item_2(self) -> None:
        """Item 2 must no longer be 'Prior art' — it is now 'Environment audit'."""
        text = _skill_text()
        lines = text.splitlines()
        item2_lines = [line for line in lines if re.match(r"^\s*2\.", line)]
        if item2_lines:
            item2_text = " ".join(item2_lines)
            assert "Prior art" not in item2_text, (
                "Item 2 still contains 'Prior art' — it must be renumbered to item 3"
            )


class TestFromAC_MandatoryRangeText:
    """AC item 4: mandatory range text updated from '1-5' to '1-6'."""

    def test_mandatory_range_updated_to_1_6(self) -> None:
        """Mandatory range must reference items 1 through 6 (en-dash or hyphen accepted)."""
        text = _skill_text()
        has_range = (
            "1\u20136 are **mandatory**" in text  # en-dash
            or "1-6 are **mandatory**" in text    # hyphen
        )
        assert has_range, (
            "Mandatory range not updated: expected '1\u20136 are **mandatory**' or '1-6 are **mandatory**'"
        )

    def test_old_mandatory_range_1_5_removed(self) -> None:
        """Old mandatory range '1-5 are mandatory' must no longer appear in the file."""
        text = _skill_text()
        assert "1\u20135 are **mandatory**" not in text, (
            "Old mandatory range '1\u20135 are **mandatory**' still present"
        )
        assert "1-5 are **mandatory**" not in text, (
            "Old mandatory range '1-5 are **mandatory**' still present"
        )

    def test_recommended_range_updated_to_7_8(self) -> None:
        """Recommended range must reference items 7 through 8 (en-dash or hyphen accepted)."""
        text = _skill_text()
        has_range = (
            "7\u20138 are **recommended**" in text  # en-dash
            or "7-8 are **recommended**" in text    # hyphen
        )
        assert has_range, (
            "Recommended range not updated: expected '7\u20138 are **recommended**' or '7-8 are **recommended**'"
        )

    def test_old_recommended_range_6_7_removed(self) -> None:
        """Old recommended range '6-7 are recommended' must no longer appear."""
        text = _skill_text()
        assert "6\u20137 are **recommended**" not in text, (
            "Old recommended range '6\u20137 are **recommended**' still present"
        )
        assert "6-7 are **recommended**" not in text, (
            "Old recommended range '6-7 are **recommended**' still present"
        )


class TestFromAC_TrivialTaskNote:
    """AC item 5: trivial-task note updated from 'items 1-3' to 'items 1-4'."""

    def test_trivial_note_updated_to_items_1_4(self) -> None:
        """Trivial-task note must reference items 1-4 (en-dash or hyphen accepted)."""
        text = _skill_text()
        has_range = "items 1\u20134" in text or "items 1-4" in text  # en-dash or hyphen
        assert has_range, (
            "Trivial-task note not updated: expected 'items 1\u20134' or 'items 1-4'"
        )

    def test_trivial_note_old_range_1_3_removed(self) -> None:
        """The trivial-task paragraph must no longer reference 'items 1-3'."""
        text = _skill_text()
        # Locate the trivial-task paragraph for a scoped check
        trivial_match = re.search(
            r"For trivial tasks.*?(?:\n\n|\Z)", text, re.DOTALL
        )
        assert trivial_match, "Trivial tasks paragraph not found in SKILL.md"
        trivial_para = trivial_match.group(0)
        assert "items 1\u20133" not in trivial_para, (
            "Old range 'items 1-3' (en-dash) still present in trivial-task note"
        )
        assert "items 1-3" not in trivial_para, (
            "Old range 'items 1-3' (hyphen) still present in trivial-task note"
        )


class TestFromAC_SelfCritiqueChecklist:
    """AC item 6: self-critique checklist includes 'Verified no environment duplication'."""

    def test_self_critique_has_environment_duplication_item(self) -> None:
        """Self-critique checklist must include an item about environment duplication."""
        text = _skill_text()
        assert "environment duplication" in text.lower(), (
            "Self-critique checklist does not contain an 'environment duplication' item"
        )

    def test_environment_duplication_item_is_checkbox(self) -> None:
        """The environment duplication item must be formatted as a markdown checkbox (- [ ])."""
        text = _skill_text()
        lines = text.splitlines()
        env_lines = [line for line in lines if "environment duplication" in line.lower()]
        assert env_lines, "No line containing 'environment duplication' found in SKILL.md"
        checkbox_lines = [line for line in env_lines if "[ ]" in line]
        assert checkbox_lines, (
            f"Environment duplication entry is not a checkbox item. Found: {env_lines}"
        )

    def test_environment_duplication_item_in_self_critique_section(self) -> None:
        """The environment duplication checkbox must appear within the Self-critique section."""
        text = _skill_text()
        # Find the self-critique section
        critique_match = re.search(
            r"## Self-critique checklist.*", text, re.DOTALL
        )
        assert critique_match, "'## Self-critique checklist' section not found in SKILL.md"
        critique_section = critique_match.group(0)
        assert "environment duplication" in critique_section.lower(), (
            "'environment duplication' not found inside '## Self-critique checklist' section"
        )
