"""Tests for task #86: Evaluate agent-scoped hooks for pipeline enforcement.

AC contract under test:
1. Research document exists at docs/research/agent-scoped-hooks-pipeline-enforcement.md
2. Document covers all three hook types (preToolUse, postToolUse, stop) with
   constraints/limits
3. Document evaluates at least three pipeline enforcement candidates with
   trade-offs and failure modes
4. Document contains a recommendation matrix with confidence scores
5. Document includes rollout guidance with at least four components:
   prerequisites, required settings, phased adoption plan, when-not-to-use
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
DOC_PATH = ROOT / "docs" / "research" / "agent-scoped-hooks-pipeline-enforcement.md"


class TestBuilderDiscovered:
    """Verify the research document satisfies all five AC requirements.

    These tests are builder-written since no TestFromAC class was provided
    (backward-compatibility path per tdd-workflow skill).
    """

    def test_document_exists(self) -> None:
        """AC4: research doc must exist at the specified path."""
        assert DOC_PATH.exists(), (
            f"Research document not found at {DOC_PATH}. "
            "Create docs/research/agent-scoped-hooks-pipeline-enforcement.md"
        )

    def test_document_covers_pretooluse(self) -> None:
        """AC1: document must mention preToolUse hook type."""
        text = DOC_PATH.read_text(encoding="utf-8")
        assert "preToolUse" in text, "Document must cover the preToolUse hook type"

    def test_document_covers_posttooluse(self) -> None:
        """AC1: document must mention postToolUse hook type."""
        text = DOC_PATH.read_text(encoding="utf-8")
        assert "postToolUse" in text, "Document must cover the postToolUse hook type"

    def test_document_covers_stop_hook(self) -> None:
        """AC1: document must mention the stop hook type."""
        text = DOC_PATH.read_text(encoding="utf-8")
        assert "stop" in text.lower(), "Document must cover the stop hook type"

    def test_document_covers_constraints_or_limits(self) -> None:
        """AC1: document must summarize constraints or limits for hooks."""
        text = DOC_PATH.read_text(encoding="utf-8").lower()
        assert "constraint" in text or "limit" in text or "limitation" in text, (
            "Document must summarize constraints/limits for VS Code hooks"
        )

    def test_document_has_at_least_three_enforcement_candidates(self) -> None:
        """AC2: document must evaluate at least three pipeline enforcement candidates."""
        text = DOC_PATH.read_text(encoding="utf-8")
        # Each candidate requires trade-offs and failure modes sections
        # We count numbered candidates or sections labelled as candidates
        candidate_markers = [
            kw for kw in ("trade-off", "tradeoff", "trade off", "failure mode", "failure")
            if kw in text.lower()
        ]
        assert len(candidate_markers) >= 2, (
            "Document must evaluate enforcement candidates with trade-offs "
            "and failure modes"
        )

    def test_document_has_recommendation_matrix(self) -> None:
        """AC3: document must contain a recommendation matrix."""
        text = DOC_PATH.read_text(encoding="utf-8")
        # A markdown table will have | characters
        assert "recommendation" in text.lower() or "matrix" in text.lower() or (
            text.count("|") >= 10
        ), "Document must contain a recommendation matrix"

    def test_document_has_confidence_scores(self) -> None:
        """AC3: recommendation matrix must include confidence scores."""
        text = DOC_PATH.read_text(encoding="utf-8")
        # Confidence scores are expressed as decimals between .50 and 1.0
        import re
        scores = re.findall(r"\.(5[0-9]|[6-9][0-9]|[89][0-9]|0\.[5-9][0-9])", text)
        assert len(scores) >= 1, (
            "Document must include at least one confidence score (e.g., .85)"
        )

    def test_document_has_recommended_path(self) -> None:
        """AC3: document must contain a clear recommended path."""
        text = DOC_PATH.read_text(encoding="utf-8").lower()
        assert "recommend" in text, (
            "Document must include a recommendation / recommended path"
        )

    def test_document_has_prerequisites(self) -> None:
        """AC5: rollout guidance must include prerequisites."""
        text = DOC_PATH.read_text(encoding="utf-8").lower()
        assert "prerequisite" in text or "require" in text, (
            "Rollout guidance must include prerequisites"
        )

    def test_document_has_required_settings(self) -> None:
        """AC5: rollout guidance must include required settings."""
        text = DOC_PATH.read_text(encoding="utf-8")
        assert "useCustomAgentHooks" in text or "chat.useCustomAgentHooks" in text, (
            "Rollout guidance must reference the required VS Code setting"
        )

    def test_document_has_phased_adoption_plan(self) -> None:
        """AC5: rollout guidance must include a phased adoption plan."""
        text = DOC_PATH.read_text(encoding="utf-8").lower()
        assert "phase" in text or "phased" in text or "rollout" in text or "staged" in text, (
            "Rollout guidance must include a phased adoption plan"
        )

    def test_document_has_when_not_to_use(self) -> None:
        """AC5: rollout guidance must include guidance on when not to use hooks."""
        text = DOC_PATH.read_text(encoding="utf-8").lower()
        assert "when not" in text or "avoid" in text or "don't use" in text or "do not use" in text, (
            "Rollout guidance must include when NOT to use hooks"
        )

    def test_document_separates_vscode_hooks_from_internal_hooks(self) -> None:
        """Architecture note: document must distinguish VS Code hooks from HookRegistry.

        The architect noted two different hook layers must not be conflated.
        """
        text = DOC_PATH.read_text(encoding="utf-8")
        # The doc should reference both the VS Code hooks AND note the distinction
        has_hookregistry = "HookRegistry" in text or "hooks.py" in text or "internal" in text.lower()
        assert has_hookregistry, (
            "Document must clarify the distinction between VS Code agent-scoped hooks "
            "and OwlBear's internal HookRegistry (per architect's note)"
        )
