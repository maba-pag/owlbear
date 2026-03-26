"""Contract tests for #944: .github/prompts/frontend-audit.prompt.md.

Tests verify structural and content requirements of the prompt file without
assuming any specific prose wording beyond what the AC mandates.
"""

from __future__ import annotations

import re
from pathlib import Path

PROMPT_PATH = Path(".github/prompts/frontend-audit.prompt.md")


def _read_prompt() -> str:
    """Read the prompt file content.  Fails with FileNotFoundError if absent."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def _extract_frontmatter(content: str) -> str:
    """Return the YAML frontmatter block (between the two ``---`` fences)."""
    if not content.startswith("---"):
        return ""
    close = content.find("---", 3)
    if close == -1:
        return ""
    return content[3:close]


class TestFromAC_FrontendAuditPrompt:
    """Contract tests for the frontend-audit prompt file (#944)."""

    # -- AC1: file exists + description-only frontmatter + optional scope input --

    def test_prompt_file_exists(self) -> None:
        """AC1: File must exist at .github/prompts/frontend-audit.prompt.md."""
        assert PROMPT_PATH.exists(), f"Missing required file: {PROMPT_PATH}"

    def test_frontmatter_has_description(self) -> None:
        """AC1: Frontmatter must contain a description: key."""
        content = _read_prompt()
        assert content.startswith("---"), "File must open with YAML frontmatter (---)"
        fm = _extract_frontmatter(content)
        assert "description:" in fm, "Frontmatter must contain a 'description:' key"

    def test_frontmatter_no_mode_key(self) -> None:
        """AC1: Frontmatter must be description-only - no 'mode:' key."""
        content = _read_prompt()
        fm = _extract_frontmatter(content)
        assert "mode:" not in fm, (
            "Frontmatter must not contain 'mode:' - description-only is required"
        )

    def test_frontmatter_no_agent_key(self) -> None:
        """AC1: Frontmatter must be description-only - no 'agent:' key."""
        content = _read_prompt()
        fm = _extract_frontmatter(content)
        assert "agent:" not in fm, (
            "Frontmatter must not contain 'agent:' - description-only is required"
        )

    def test_frontmatter_no_applyto_key(self) -> None:
        """AC1: Frontmatter must be description-only - no 'applyTo:' key."""
        content = _read_prompt()
        fm = _extract_frontmatter(content)
        assert "applyTo:" not in fm, (
            "Frontmatter must not contain 'applyTo:' - description-only is required"
        )

    def test_scope_input_variable_present(self) -> None:
        """AC1: Prompt must include an optional scope input using VS Code input syntax."""
        content = _read_prompt()
        assert re.search(r"\$\{input:scope", content), (
            "Prompt must contain a ${input:scope...} variable for optional scope"
        )

    # -- AC2: reads docs/design-context.md + references skill by relative path --

    def test_references_design_context_md(self) -> None:
        """AC2: Prompt must reference docs/design-context.md."""
        content = _read_prompt()
        assert "docs/design-context.md" in content, "Prompt must reference 'docs/design-context.md'"

    def test_references_frontend_design_skill_by_relative_path(self) -> None:
        """AC2: Prompt must reference the frontend-design skill by relative path."""
        content = _read_prompt()
        has_ref = re.search(
            r"(\.\.?/[\w\-./]*frontend-design[\w\-./]*SKILL\.md)",
            content,
        )
        assert has_ref, (
            "Prompt must reference the frontend-design skill by relative path "
            "(e.g., '../skills/frontend-design/SKILL.md')"
        )

    def test_skill_reference_is_not_absolute_path(self) -> None:
        """AC2: Skill path reference must be relative, not absolute."""
        content = _read_prompt()
        absolute_ref = re.search(
            r"(?<!\.)(/[A-Za-z][^\s]*frontend-design)|([A-Za-z]:\\[^\s]*frontend-design)",
            content,
        )
        assert not absolute_ref, "Skill reference must be a relative path, not an absolute path"

    def test_skill_reference_resolves_to_existing_file(self) -> None:
        """AC2: The relative skill path in the prompt must resolve to an actual existing file."""
        content = _read_prompt()
        match = re.search(r"(\.\.?/[\w\-./]*frontend-design[\w\-./]*SKILL\.md)", content)
        assert match, (
            "Prompt must contain a relative skill path reference to frontend-design/SKILL.md"
        )
        relative_path = match.group(1)
        resolved = (PROMPT_PATH.parent / relative_path).resolve()
        assert resolved.exists(), (
            f"Skill path '{relative_path}' in the prompt resolves to '{resolved}', "
            "which does not exist. Expected path: '../skills/frontend-design/SKILL.md'."
        )

    # -- AC3: severity-ranked audit using two-tier taxonomy across four categories --

    def test_blocker_tier_mentioned(self) -> None:
        """AC3: Prompt must reference the 'blocker' tier from anti-patterns.md taxonomy."""
        content = _read_prompt()
        assert re.search(r"\bblocker\b", content, re.IGNORECASE), (
            "Prompt must reference the 'blocker' severity tier from the two-tier taxonomy"
        )

    def test_heuristic_tier_mentioned(self) -> None:
        """AC3: Prompt must reference the 'heuristic' tier from anti-patterns.md taxonomy."""
        content = _read_prompt()
        assert re.search(r"\bheuristic\b", content, re.IGNORECASE), (
            "Prompt must reference the 'heuristic' severity tier from the two-tier taxonomy"
        )

    def test_references_anti_patterns_file(self) -> None:
        """AC3: Prompt must reference references/anti-patterns.md for the taxonomy."""
        content = _read_prompt()
        assert re.search(r"anti.patterns\.md", content, re.IGNORECASE), (
            "Prompt must reference the anti-patterns.md file for the severity taxonomy"
        )

    def test_audit_output_is_severity_ranked(self) -> None:
        """AC3: Prompt must instruct that findings be severity-ranked."""
        content = _read_prompt()
        assert re.search(r"\bseverit\w+\b|\branked?\b|\brank\b", content, re.IGNORECASE), (
            "Prompt must instruct that audit findings be severity-ranked"
        )

    def test_category_accessibility(self) -> None:
        """AC3: Prompt must include accessibility as an audit category."""
        content = _read_prompt()
        assert re.search(r"\baccessib|\ba11y\b", content, re.IGNORECASE), (
            "Prompt must include 'accessibility' as an audit category"
        )

    def test_category_responsive_behavior(self) -> None:
        """AC3: Prompt must include responsive behavior as an audit category."""
        content = _read_prompt()
        assert re.search(r"\bresponsive\b", content, re.IGNORECASE), (
            "Prompt must include 'responsive behavior' as an audit category"
        )

    def test_category_design_system_consistency(self) -> None:
        """AC3: Prompt must include design-system consistency as an audit category."""
        content = _read_prompt()
        assert re.search(r"\bdesign.system\b|\bconsistency\b", content, re.IGNORECASE), (
            "Prompt must include 'design-system consistency' as an audit category"
        )

    def test_category_anti_patterns(self) -> None:
        """AC3: Prompt must include anti-patterns as an audit category."""
        content = _read_prompt()
        assert re.search(r"\banti.pattern", content, re.IGNORECASE), (
            "Prompt must include 'anti-patterns' as an audit category"
        )

    def test_all_four_categories_present(self) -> None:
        """AC3: All four required audit categories must appear in the prompt."""
        content = _read_prompt()
        categories = {
            "accessibility": r"\baccessib|\ba11y\b",
            "responsive behavior": r"\bresponsive\b",
            "design-system consistency": r"\bdesign.system\b|\bconsistency\b",
            "anti-patterns": r"\banti.pattern",
        }
        missing = [
            cat
            for cat, pattern in categories.items()
            if not re.search(pattern, content, re.IGNORECASE)
        ]
        assert not missing, f"Prompt is missing required audit categories: {missing}"

    # -- AC4: no code edits; reports findings and recommends next commands --

    def test_does_not_edit_code(self) -> None:
        """AC4: Prompt must explicitly state it does not edit code."""
        content = _read_prompt()
        # Must contain a 'do not edit' or 'does not edit' instruction
        pattern = r"do not edit|does not edit|not edit.*file|not.*modif"
        assert re.search(pattern, content, re.IGNORECASE), (
            "Prompt must explicitly state it does not edit code files"
        )

    def test_recommends_frontend_normalize_command(self) -> None:
        """AC4: Prompt must recommend /frontend-normalize as a next command."""
        content = _read_prompt()
        assert re.search(r"frontend.normalize", content, re.IGNORECASE), (
            "Prompt must recommend '/frontend-normalize' as a follow-up command"
        )

    def test_recommends_frontend_polish_command(self) -> None:
        """AC4: Prompt must recommend /frontend-polish as a next command."""
        content = _read_prompt()
        assert re.search(r"frontend.polish", content, re.IGNORECASE), (
            "Prompt must recommend '/frontend-polish' as a follow-up command"
        )

    def test_mentions_follow_up_tasks_or_next_commands(self) -> None:
        """AC4: Prompt must recommend next commands or follow-up tasks, not just report findings."""
        content = _read_prompt()
        assert re.search(r"\bnext command|\bfollow.up|\brecommend", content, re.IGNORECASE), (
            "Prompt must recommend next commands or follow-up tasks, not just report findings"
        )

    # -- AC5: four-step structure matching sibling prompts --

    def test_step_load_context_present(self) -> None:
        """AC5: Prompt must have a 'Load context' step."""
        content = _read_prompt()
        assert re.search(r"\bload context\b", content, re.IGNORECASE), (
            "Prompt must have a 'Load context' step matching the sibling prompt structure"
        )

    def test_step_plan_or_scope_present(self) -> None:
        """AC5: Prompt must have a 'Plan' or 'Plan/scope' step."""
        content = _read_prompt()
        pattern = r"\bstep\s+\d.*plan|\bplan\b.*step\s+\d|\bplan.*scope"
        assert re.search(pattern, content, re.IGNORECASE), (
            "Prompt must have a 'Plan' or 'Plan/scope' step"
        )

    def test_step_execute_audit_present(self) -> None:
        """AC5: Prompt must have an 'Execute' step covering the audit."""
        content = _read_prompt()
        pattern = r"\bexecute\b|\bauditing\b|\brun.*audit|\baudit.*step"
        assert re.search(pattern, content, re.IGNORECASE), (
            "Prompt must have an 'Execute audit' step"
        )

    def test_step_verify_or_guardrails_present(self) -> None:
        """AC5: Prompt must have a 'Verify' or 'Guardrails' step."""
        content = _read_prompt()
        assert re.search(r"\bverif|\bguardrail", content, re.IGNORECASE), (
            "Prompt must have a 'Verify' or 'Guardrails' step"
        )

    def test_four_steps_in_order(self) -> None:
        """AC5: Four steps must appear in load-context, plan, execute, verify order."""
        content = _read_prompt()
        load_match = re.search(r"\bload context\b", content, re.IGNORECASE)
        plan_match = re.search(r"\bplan\b", content, re.IGNORECASE)
        execute_match = re.search(r"\bexecute\b|\bauditing\b", content, re.IGNORECASE)
        verify_match = re.search(r"\bverif|\bguardrail", content, re.IGNORECASE)

        assert load_match is not None, "Prompt must contain a 'Load context' step"
        assert plan_match is not None, "Prompt must contain a 'Plan' step"
        assert execute_match is not None, "Prompt must contain an 'Execute' step"
        assert verify_match is not None, "Prompt must contain a 'Verify/Guardrails' step"

        assert load_match.start() < plan_match.start(), (
            "Load context step must appear before Plan step"
        )
        assert plan_match.start() < execute_match.start(), (
            "Plan step must appear before Execute step"
        )
        assert execute_match.start() < verify_match.start(), (
            "Execute step must appear before Verify/Guardrails step"
        )
