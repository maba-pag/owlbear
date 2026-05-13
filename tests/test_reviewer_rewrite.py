"""Failing tests for task #1407: B1 reviewer rewrite — batch findings, finding vs opinion,
trust builder evidence, protocol update.

All tests FAIL on the current codebase; they pass once the builder:
  1. Rewrites share/skills/w-code-review/SKILL.md with batch-all-findings approach,
     two-section output (Review Evidence / Observations), 3-item checklist, and removes
     the TestFromAC immutability enforcement rule.
  2. Updates share/skills/r-pipeline-protocol/SKILL.md trust model and reviewer contract
     to reflect the D2 trust-the-builder model.

AC coverage:
  P1-AC1  — batch-all-findings approach:
              test_w_code_review_has_batch_all_findings_approach
  P2-AC2a — "Observations" section distinct from findings:
              test_w_code_review_has_observations_section
  P2-AC2b — Observations opinions never affect verdict:
              test_w_code_review_observations_never_affect_verdict
  P2-AC3  — finding vs opinion rule (no citation → Observations):
              test_w_code_review_finding_vs_opinion_rule_present
  P2-AC4  — PASS case one-line confirmation:
              test_w_code_review_pass_case_one_liner_present
  P2-AC5  — reviewer reads builder's quality-runner output:
              test_w_code_review_reads_builder_quality_runner_output
  P2-AC6  — scoped 3-item checklist (proof sufficiency):
              test_w_code_review_three_item_checklist
  P2-AC7  — TestFromAC immutability rule removed:
              test_w_code_review_testfromac_immutability_removed
  P1-AC8  — r-pipeline-protocol trust model updated:
              test_r_pipeline_protocol_trust_model_updated
  P2-AC9  — r-pipeline-protocol reviewer contract updated (D2 trust-the-builder):
              test_r_pipeline_protocol_reviewer_contract_d2_model
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_CODE_REVIEW_SKILL = _REPO_ROOT / "share" / "skills" / "w-code-review" / "SKILL.md"
_PIPELINE_PROTOCOL = (
    _REPO_ROOT / "share" / "skills" / "r-pipeline-protocol" / "SKILL.md"
)


class TestFromAC_CodeReviewSkillRewrite:
    """Verify w-code-review/SKILL.md is rewritten per AC. Task #1407."""

    # P1-AC1: batch-all-findings approach (no first-failure gating)

    def test_w_code_review_has_batch_all_findings_approach(self) -> None:
        """w-code-review must describe a batch-all-findings approach, not first-failure gating.

        The new skill collects all findings before issuing a verdict rather than
        stopping at the first failing check.
        """
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        has_batch_approach = (
            "batch-all-findings" in content
            or "batch all findings" in content.lower()
            or "no first-failure" in content.lower()
            or "all findings" in content.lower()
        )
        assert has_batch_approach, (
            "w-code-review/SKILL.md must describe a batch-all-findings approach "
            "(e.g. 'batch-all-findings', 'all findings', or 'no first-failure gating') — "
            "not found. Current skill still uses first-failure gating."
        )

    # P2-AC2a: "Observations" section for opinions that never affect verdict

    def test_w_code_review_has_observations_section(self) -> None:
        """w-code-review must contain an 'Observations' section header for non-binding opinions."""
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        has_obs = "## Observations" in content or "### Observations" in content
        assert has_obs, (
            "w-code-review/SKILL.md must contain an '## Observations' or '### Observations' "
            "section for opinions that never affect verdict — not found. "
            "Current skill has no Observations section."
        )

    # P2-AC2b: Observations opinions never affect verdict

    def test_w_code_review_observations_never_affect_verdict(self) -> None:
        """w-code-review must state that Observations (opinions) never affect the verdict."""
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        lower = content.lower()
        # "never affect verdict" near "Observations"
        has_rule = "never affect verdict" in lower or (
            "observations" in lower and "verdict" in lower and "never" in lower
        )
        assert has_rule, (
            "w-code-review/SKILL.md must state that Observations / opinions never affect "
            "the verdict — rule not found. Current skill has no Observations/verdict distinction."
        )

    # P2-AC3: finding vs opinion rule — no citation → Observations

    def test_w_code_review_finding_vs_opinion_rule_present(self) -> None:
        """w-code-review must enforce: Review Evidence items cite AC line or factual deficiency.

        Items without a citation go to Observations, not Review Evidence.
        """
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        lower = content.lower()
        # Rule: no citation → Observations (or equivalent phrasing)
        has_rule = "no citation" in lower or (
            "citation" in lower and "observations" in lower
        )
        assert has_rule, (
            "w-code-review/SKILL.md must define the finding-vs-opinion rule: "
            "Review Evidence items must cite an AC line or factual deficiency; "
            "items without a citation belong in Observations — rule not found."
        )

    # P2-AC4: PASS case one-line confirmation

    def test_w_code_review_pass_case_one_liner_present(self) -> None:
        """w-code-review PASS case must include the exact one-line confirmation text."""
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        # AC specifies the exact string — check each required fragment separately
        assert "Verified: AC" in content, (
            "w-code-review/SKILL.md must include the PASS one-liner starting with "
            "'Verified: AC→code mapping complete ...' — 'Verified: AC' not found."
        )
        assert "Zero findings" in content, (
            "w-code-review/SKILL.md PASS one-liner must end with 'Zero findings.' — not found."
        )

    # P2-AC5: reviewer reads builder's quality-runner output instead of re-executing tests

    def test_w_code_review_reads_builder_quality_runner_output(self) -> None:
        """w-code-review must instruct reviewer to READ builder's quality-runner output.

        The new model: reviewer reads builder evidence rather than re-running tests.
        Uses a specific phrase absent from the current skill.
        Negative: must not contain the legacy 'Tests run independently, not trusting builder
        output' or 'Run tests yourself' guidance that contradicts the trust-the-builder model.
        """
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        lower = content.lower()
        # Require the specific concept as a joined phrase — individual words exist in current skill
        has_read_output = (
            "builder's quality-runner output" in lower
            or "builder's quality-runner report" in lower
            or "quality-runner output" in lower
        )
        assert has_read_output, (
            "w-code-review/SKILL.md must instruct reviewer to read the builder's "
            "quality-runner output (phrase 'quality-runner output' not found). "
            "Current skill says 'Run tests, lint, and coverage yourself via Quality-Runner'."
        )
        # Absence of contradictory legacy guidance (new AC line from arch review)
        assert "Tests run independently, not trusting builder output" not in content, (
            "w-code-review/SKILL.md must NOT contain the legacy rerun guidance "
            "'Tests run independently, not trusting builder output' — "
            "this contradicts the trust-the-builder model."
        )
        assert "Run tests yourself" not in content, (
            "w-code-review/SKILL.md must NOT contain 'Run tests yourself' — "
            "contradicts the trust-the-builder model (reviewer reads builder evidence)."
        )

    # P2-AC6: scoped 3-item checklist (AC→code mapping, test→AC alignment, proof sufficiency)

    def test_w_code_review_three_item_checklist(self) -> None:
        """w-code-review must contain a scoped 3-item checklist with all three named items.

        Negative: the legacy 'Pass 1' section heading must be absent — it signals that the
        old multi-pass review scaffold still governs the workflow instead of the 3-item checklist.
        Note: a stale template placeholder '{Pass 1 check reference}' is acceptable cosmetic
        drift; only the operative section heading '### Pass 1' triggers this assertion.
        """
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        lower = content.lower()
        # All three checklist items must appear
        has_ac_mapping = "ac" in lower and ("mapping" in lower or "→code" in content)
        has_alignment = "alignment" in lower and ("test" in lower or "→ac" in content)
        has_sufficiency = "proof sufficiency" in lower
        assert has_ac_mapping, (
            "w-code-review/SKILL.md 3-item checklist must include AC→code mapping — not found. "
            "Current skill has 8 Pass 1 checks, not a 3-item checklist."
        )
        assert has_alignment, (
            "w-code-review/SKILL.md 3-item checklist must include test→AC alignment — not found."
        )
        assert has_sufficiency, (
            "w-code-review/SKILL.md 3-item checklist must include 'proof sufficiency' — not found."
        )
        # Absence of legacy Pass 1 scaffold (new AC line from arch review)
        # Check the operative section heading; the template placeholder '{Pass 1 check reference}'
        # is tolerated as cosmetic drift and excluded from this assertion.
        assert "### Pass 1" not in content, (
            "w-code-review/SKILL.md must NOT contain the '### Pass 1' section heading — "
            "its presence means the legacy multi-pass scaffold still governs the workflow "
            "instead of the scoped 3-item checklist."
        )

    # P2-AC7: TestFromAC immutability rule removed from reviewer skill

    def test_w_code_review_testfromac_immutability_removed(self) -> None:
        """w-code-review must NOT enforce TestFromAC immutability — rule belongs to test-curator.

        The current skill has Step 5.2 'Test Integrity — TestFromAC Comparison' which
        states 'Any WEAKENED or REMOVED = automatic FAIL'. This must be removed.
        """
        content = _CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        still_has_immutability = (
            "WEAKENED or REMOVED" in content or "TestFromAC immutability" in content
        )
        assert not still_has_immutability, (
            "w-code-review/SKILL.md still contains the TestFromAC immutability enforcement "
            "('WEAKENED or REMOVED = automatic FAIL' or 'TestFromAC immutability') — "
            "this rule must be removed. Immutability is enforced by the test-curator, "
            "not the reviewer."
        )


class TestFromAC_PipelineProtocolUpdate:
    """Verify r-pipeline-protocol/SKILL.md trust model and reviewer contract updates. Task #1407."""

    # P1-AC8: trust model updated with exact quoted text

    def test_r_pipeline_protocol_trust_model_updated(self) -> None:
        """r-pipeline-protocol must contain the new trust model sentence (exact quote from AC)."""
        content = _PIPELINE_PROTOCOL.read_text(encoding="utf-8")
        assert "Upstream evidence is valid input" in content, (
            "r-pipeline-protocol/SKILL.md must contain the trust model: "
            "'Upstream evidence is valid input. Verify through independent checks only when "
            "cost-justified. The auditor serves as the pipeline-end integrity gate.' — "
            "not found. Current protocol says 'Never trust self-reports. Verify deliverables "
            "yourself'."
        )

    # P2-AC9: reviewer contract section updated to match D2 trust-the-builder model

    def test_r_pipeline_protocol_reviewer_contract_d2_model(self) -> None:
        """r-pipeline-protocol reviewer contract must reflect D2 trust-the-builder evidence model.

        The contract should indicate that the reviewer reads / trusts builder evidence
        rather than independently re-running all checks.
        Negative: must not contain 'Never trust self-reports' — the legacy blanket-distrust
        mandate that contradicts the D2 trust-the-builder model for reviewers.
        """
        content = _PIPELINE_PROTOCOL.read_text(encoding="utf-8")
        lower = content.lower()
        has_d2_model = (
            "trust-the-builder" in lower
            or "cost-justified" in lower
            or "d2 trust" in lower
            or ("trust" in lower and "builder evidence" in lower)
        )
        assert has_d2_model, (
            "r-pipeline-protocol/SKILL.md reviewer contract section must reflect the "
            "D2 trust-the-builder model (e.g. 'trust-the-builder', 'cost-justified', "
            "or 'builder evidence') — not found. Current protocol has no D2 trust model."
        )
        # Absence of contradictory legacy blanket-distrust mandate (new AC line from arch review)
        assert "Never trust self-reports" not in content, (
            "r-pipeline-protocol/SKILL.md must NOT contain 'Never trust self-reports' — "
            "this blanket-distrust mandate contradicts the D2 trust-the-builder model "
            "introduced for reviewers."
        )
