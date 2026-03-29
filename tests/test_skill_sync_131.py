"""Tests for task #131: Sync drifted skill content before .github/skills/ deletion.

Verifies that skills/ copies contain the vscode_listCodeUsages guidance
added by #103 (post-copy drift), and that existing skills/-authoritative
content is still present.

Note: Tests for AC lines 3 and 4 (kanban-md pitfalls, research-workflow cross-ref)
pass immediately — they guard already-correct baseline state per task #131 AC.
Tests for AC lines 1, 2, and 5 (parity) fail until the builder syncs the content.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GITHUB_SKILLS = REPO_ROOT / ".github" / "skills"
SKILLS = REPO_ROOT / "skills"


class TestFromAC_CodeReviewSync:
    """AC line 1: Copy vscode_listCodeUsages guidance to skills/code-review/SKILL.md."""

    def test_code_review_contains_vscode_list_code_usages(self) -> None:
        """skills/code-review/SKILL.md must mention vscode_listCodeUsages."""
        content = (SKILLS / "code-review" / "SKILL.md").read_text(encoding="utf-8")
        assert "vscode_listCodeUsages" in content, (
            "skills/code-review/SKILL.md is missing vscode_listCodeUsages guidance "
            "(added by #103 to .github/skills/code-review/SKILL.md, not yet synced to skills/)"
        )

    def test_code_review_contains_trace_all_callers(self) -> None:
        """skills/code-review/SKILL.md must contain 'trace all callers' guidance."""
        content = (SKILLS / "code-review" / "SKILL.md").read_text(encoding="utf-8")
        assert "trace all callers" in content, (
            "skills/code-review/SKILL.md is missing the 'trace all callers' phrase "
            "that accompanies the vscode_listCodeUsages guidance"
        )

    def test_code_review_vscode_line_matches_github_source_exactly(self) -> None:
        """The vscode_listCodeUsages line in skills/ must match the .github/ source exactly."""
        github_content = (GITHUB_SKILLS / "code-review" / "SKILL.md").read_text(encoding="utf-8")
        skills_content = (SKILLS / "code-review" / "SKILL.md").read_text(encoding="utf-8")
        marker = "vscode_listCodeUsages"
        github_line = next(
            ln.strip() for ln in github_content.splitlines() if marker in ln
        )
        skills_lines = {ln.strip() for ln in skills_content.splitlines() if marker in ln}
        assert github_line in skills_lines, (
            f"skills/code-review/SKILL.md is missing the exact vscode_listCodeUsages line.\n"
            f"Expected: {github_line!r}\n"
            f"Found in skills/: {skills_lines!r}"
        )


class TestFromAC_TddWorkflowSync:
    """AC line 2: Copy vscode_listCodeUsages guidance to skills/tdd-workflow/SKILL.md."""

    def test_tdd_workflow_contains_vscode_list_code_usages(self) -> None:
        """skills/tdd-workflow/SKILL.md must mention vscode_listCodeUsages."""
        content = (SKILLS / "tdd-workflow" / "SKILL.md").read_text(encoding="utf-8")
        assert "vscode_listCodeUsages" in content, (
            "skills/tdd-workflow/SKILL.md is missing vscode_listCodeUsages guidance "
            "(added by #103 to .github/skills/tdd-workflow/SKILL.md, not yet synced to skills/)"
        )

    def test_tdd_workflow_contains_before_modifying_signatures(self) -> None:
        """skills/tdd-workflow/SKILL.md must contain 'Before modifying function signatures' bullet."""
        content = (SKILLS / "tdd-workflow" / "SKILL.md").read_text(encoding="utf-8")
        assert "Before modifying function signatures or interfaces" in content, (
            "skills/tdd-workflow/SKILL.md is missing the 'Before modifying function signatures' "
            "bullet that accompanies the vscode_listCodeUsages guidance"
        )

    def test_tdd_workflow_vscode_line_matches_github_source_exactly(self) -> None:
        """The vscode_listCodeUsages line in skills/ must match the .github/ source exactly."""
        github_content = (GITHUB_SKILLS / "tdd-workflow" / "SKILL.md").read_text(encoding="utf-8")
        skills_content = (SKILLS / "tdd-workflow" / "SKILL.md").read_text(encoding="utf-8")
        marker = "vscode_listCodeUsages"
        github_line = next(
            ln.strip() for ln in github_content.splitlines() if marker in ln
        )
        skills_lines = {ln.strip() for ln in skills_content.splitlines() if marker in ln}
        assert github_line in skills_lines, (
            f"skills/tdd-workflow/SKILL.md is missing the exact vscode_listCodeUsages line.\n"
            f"Expected: {github_line!r}\n"
            f"Found in skills/: {skills_lines!r}"
        )


class TestFromAC_KanbanMdPitfalls:
    """AC line 3: Verify skills/kanban-md/SKILL.md already has 3 extra pitfall lines.

    These tests pass immediately — they guard existing authoritative content that
    must not be removed when syncing other skills.
    """

    def test_kanban_md_has_claim_release_separate_pitfall(self) -> None:
        """skills/kanban-md/SKILL.md has the --claim/--release separate calls pitfall."""
        content = (SKILLS / "kanban-md" / "SKILL.md").read_text(encoding="utf-8")
        assert "--claim` and `--release` must be separate calls" in content, (
            "skills/kanban-md/SKILL.md is missing the claim/release separate-calls pitfall"
        )

    def test_kanban_md_has_body_append_claim_pitfall(self) -> None:
        """skills/kanban-md/SKILL.md has the body-append --claim requirement pitfall."""
        content = (SKILLS / "kanban-md" / "SKILL.md").read_text(encoding="utf-8")
        assert "Body-append requires `--claim" in content, (
            "skills/kanban-md/SKILL.md is missing the body-append --claim pitfall"
        )

    def test_kanban_md_has_lf_line_endings_pitfall(self) -> None:
        """skills/kanban-md/SKILL.md has the LF line endings pitfall."""
        content = (SKILLS / "kanban-md" / "SKILL.md").read_text(encoding="utf-8")
        assert "LF line endings" in content, (
            "skills/kanban-md/SKILL.md is missing the LF line endings pitfall"
        )


class TestFromAC_ResearchWorkflowCrossRef:
    """AC line 4: Verify skills/research-workflow/SKILL.md cross-ref uses skills/ path.

    These tests pass immediately — they guard the update already applied by #116.
    """

    def test_research_workflow_cross_ref_uses_skills_path(self) -> None:
        """skills/research-workflow/SKILL.md must reference skills/decision-requests/SKILL.md."""
        content = (SKILLS / "research-workflow" / "SKILL.md").read_text(encoding="utf-8")
        assert "skills/decision-requests/SKILL.md" in content, (
            "skills/research-workflow/SKILL.md is missing the skills/ path for decision-requests"
        )

    def test_research_workflow_cross_ref_not_github_path(self) -> None:
        """skills/research-workflow/SKILL.md must NOT reference the old .github/ path."""
        content = (SKILLS / "research-workflow" / "SKILL.md").read_text(encoding="utf-8")
        assert ".github/skills/decision-requests/SKILL.md" not in content, (
            "skills/research-workflow/SKILL.md still contains the old .github/ path; "
            "expected it to have been updated by #116"
        )
