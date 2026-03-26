"""Contract tests for #945: .github/prompts/frontend-normalize.prompt.md.

Tests verify structural and content requirements of the prompt file without
assuming any specific prose wording beyond what the AC mandates.
"""

from __future__ import annotations

import re
from pathlib import Path

PROMPT_PATH = Path(".github/prompts/frontend-normalize.prompt.md")


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


class TestFromAC_FrontendNormalizePrompt:
    """Contract tests for the frontend-normalize prompt file (#945)."""

    # -- AC1: file exists + description-only frontmatter + optional scope input --

    def test_prompt_file_exists(self) -> None:
        """AC1: File must exist at .github/prompts/frontend-normalize.prompt.md."""
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

    def test_design_context_read_is_conditional(self) -> None:
        """AC2: The docs/design-context.md read must be conditional (if-it-exists guard).

        docs/design-context.md may not exist in fresh workspaces (user hasn't run
        /design-context yet). Sibling prompts frontend-audit and frontend-polish both
        use 'if it exists' to handle this gracefully. frontend-normalize must do the same.
        """
        content = _read_prompt()
        ref_pos = content.find("docs/design-context.md")
        assert ref_pos != -1, "Prompt must reference docs/design-context.md"
        # Check a window around the reference for conditional wording
        window = content[max(0, ref_pos - 60) : ref_pos + 100]
        assert re.search(
            r"if it exists|if it is present|if available|if found", window, re.IGNORECASE
        ), (
            "The docs/design-context.md read must be conditional ('if it exists' or similar). "
            "Sibling prompts guard this with 'if it exists'."
        )

    def test_references_frontend_design_skill_by_relative_path(self) -> None:
        """AC2: Prompt must reference the frontend-design skill by relative path."""
        content = _read_prompt()
        # Relative path must contain 'frontend-design' and 'SKILL.md'
        has_ref = re.search(
            r"(\.\.?/[\w\-./]*frontend-design[\w\-./]*SKILL\.md)",
            content,
        )
        assert has_ref, (
            "Prompt must reference the frontend-design skill by relative path "
            "(e.g., '../../skills/frontend-design/SKILL.md')"
        )

    def test_skill_reference_is_not_absolute_path(self) -> None:
        """AC2: Skill path reference must be relative, not absolute."""
        content = _read_prompt()
        # An absolute Unix path starts with / not preceded by . (which would be a relative ../)
        # An absolute Windows path starts with a drive letter followed by :\
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

    # -- AC3: plan-before-edit gate + all 6 normalization dimensions --

    def test_plan_step_present(self) -> None:
        """AC3: Prompt must require a short plan before making edits."""
        content = _read_prompt()
        assert re.search(r"\bplan\b", content, re.IGNORECASE), (
            "Prompt must include a plan step before edits"
        )

    def test_plan_precedes_dimension_list(self) -> None:
        """AC3: Plan step must appear before the normalization dimensions."""
        content = _read_prompt()
        plan_match = re.search(r"\bplan\b", content, re.IGNORECASE)
        dim_match = re.search(
            r"\btypography\b|\bcolor\b|\blayout\b|\bspacing\b",
            content,
            re.IGNORECASE,
        )
        assert plan_match is not None, "Prompt must contain a plan step"
        assert dim_match is not None, "Prompt must contain normalization dimensions"
        assert plan_match.start() < dim_match.start(), (
            "Plan step must appear before normalization dimensions"
        )

    def test_dimension_typography(self) -> None:
        """AC3: Prompt must address typography as a normalization dimension."""
        content = _read_prompt()
        assert re.search(r"\btypography\b", content, re.IGNORECASE), (
            "Prompt must address 'typography' as a normalization dimension"
        )

    def test_dimension_color(self) -> None:
        """AC3: Prompt must address color as a normalization dimension."""
        content = _read_prompt()
        assert re.search(r"\bcolor\b", content, re.IGNORECASE), (
            "Prompt must address 'color' as a normalization dimension"
        )

    def test_dimension_layout(self) -> None:
        """AC3: Prompt must address layout as a normalization dimension."""
        content = _read_prompt()
        assert re.search(r"\blayout\b", content, re.IGNORECASE), (
            "Prompt must address 'layout' as a normalization dimension"
        )

    def test_dimension_spacing(self) -> None:
        """AC3: Prompt must address spacing as a normalization dimension."""
        content = _read_prompt()
        assert re.search(r"\bspacing\b", content, re.IGNORECASE), (
            "Prompt must address 'spacing' as a normalization dimension"
        )

    def test_dimension_component_usage(self) -> None:
        """AC3: Prompt must address component usage as a normalization dimension."""
        content = _read_prompt()
        assert re.search(r"\bcomponent\b", content, re.IGNORECASE), (
            "Prompt must address 'component usage' as a normalization dimension"
        )

    def test_dimension_token_usage(self) -> None:
        """AC3: Prompt must address token usage as a normalization dimension."""
        content = _read_prompt()
        assert re.search(r"\btoken\b", content, re.IGNORECASE), (
            "Prompt must address 'token usage' as a normalization dimension"
        )

    def test_all_six_dimensions_present(self) -> None:
        """AC3: All six normalization dimensions must be present in the prompt body."""
        content = _read_prompt()
        dimensions = {
            "typography": r"\btypography\b",
            "color": r"\bcolor\b",
            "layout": r"\blayout\b",
            "spacing": r"\bspacing\b",
            "component usage": r"\bcomponent\b",
            "token usage": r"\btoken\b",
        }
        missing = [
            dim
            for dim, pattern in dimensions.items()
            if not re.search(pattern, content, re.IGNORECASE)
        ]
        assert not missing, f"Prompt is missing required normalization dimensions: {missing}"

    # -- AC4: post-change verification steps --

    def test_verification_accessibility(self) -> None:
        """AC4: Post-change verification must cover accessibility."""
        content = _read_prompt()
        assert re.search(r"\baccessib|\ba11y\b", content, re.IGNORECASE), (
            "Prompt must include a post-change accessibility verification step"
        )

    def test_verification_responsive_behavior(self) -> None:
        """AC4: Post-change verification must cover responsive behavior."""
        content = _read_prompt()
        assert re.search(r"\bresponsive\b", content, re.IGNORECASE), (
            "Prompt must include a post-change responsive-behavior verification step"
        )

    def test_verification_remove_one_off_styling(self) -> None:
        """AC4: Post-change verification must check for removal of unnecessary one-off styling."""
        content = _read_prompt()
        assert re.search(r"one.off|ad.hoc|unnecessary", content, re.IGNORECASE), (
            "Prompt must include a verification step for removing unnecessary one-off styling"
        )

    def test_verification_step_appears_after_plan(self) -> None:
        """AC4: Verification steps must appear after the plan/execute sections."""
        content = _read_prompt()
        plan_match = re.search(r"\bplan\b", content, re.IGNORECASE)
        verify_match = re.search(r"\baccessib|\bresponsive\b|one.off", content, re.IGNORECASE)
        assert plan_match is not None, "Prompt must contain a plan step"
        assert verify_match is not None, "Prompt must contain verification steps"
        assert verify_match.start() > plan_match.start(), (
            "Verification steps must appear after the plan step"
        )
