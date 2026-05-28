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
_PIPELINE_PROTOCOL = _REPO_ROOT / "share" / "skills" / "r-pipeline-protocol" / "SKILL.md"




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
