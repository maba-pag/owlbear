---
id: 1407
title: 'B1: Reviewer rewrite — batch findings, finding vs opinion, trust builder evidence,
  protocol update'
status: in-progress
priority: critical
created: 2026-05-07T23:16:25.214918+00:00
updated: 2026-05-08T21:26:41.202049+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
parent: 1403
depends_on:
- 1404
- 1413
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `w-code-review` skill rewritten with batch-all-findings approach (no first-failure gating)
P2: Reviewer output has two sections: "Review Evidence" (findings citing AC lines or factual deficiencies, ≥1 = FAIL) and "Observations" (opinions, never affect verdict)
P2: Finding vs opinion rule enforced: every Review Evidence item must cite an AC line or factual deficiency; no citation = Observations
P2: PASS case includes one-line confirmation: "Verified: AC→code mapping complete, test→AC alignment confirmed, proof sufficiency met. Zero findings."
P2: Reviewer reads builder's quality-runner output instead of re-executing tests
P2: Scoped 3-item checklist: AC→code mapping, test→AC alignment, proof sufficiency with boundary examples
P2: TestFromAC immutability rule removed from reviewer skill
P1: `r-pipeline-protocol` trust model updated: "Upstream evidence is valid input. Verify through independent checks only when cost-justified. The auditor serves as the pipeline-end integrity gate."
P2: `r-pipeline-protocol` reviewer contract section updated to match new evidence model (D2 trust-the-builder)
P3: Verification by diff comparison of modified skill and protocol files

## Scope

**In scope:** `w-code-review` skill rewrite, `r-pipeline-protocol` trust model and reviewer contract updates
**Out of scope:** Auditor changes (C1), loop-breaker threshold (B2), CI/SAST setup (D2)
[[2026-05-08]]
## Planning

Created 3 follow-up tasks under parent #1403:

| ID | Title | Priority | Depends on | Status |
|----|-------|----------|------------|--------|
| #1458 | B1-impl: Rewrite w-code-review skill — batch findings, 3-item checklist, trust builder evidence | critical | #1407 | backlog |
| #1459 | B1-agent: Update code-reader agent to match new w-code-review contract | needed | #1458 | backlog |
| #1460 | B1-agent: Update reviewer agent file to match new w-code-review model | needed | #1458 | backlog |

Dependency graph: #1407 → #1458 → {#1459, #1460}
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1407-reviewer-rewrite.md
- Sources: 8 studied, 5 high-relevance (.85+)
- Recommendation: Proceed with B1 as specified in brief (confidence: .90)

Key findings:
1. Current 386-line skill collapses to ~120-150 lines via 3-item checklist replacing 12 checks
2. CI/SAST (#1413 archived) makes reviewer cognitive security scanning redundant — safe to remove
3. Trust model shift validated: builder evidence → reviewer reads → auditor verifies independently
4. Code-reader 8-section contract must update within w-code-review rewrite (defined there)
5. TestFromAC immutability removal is clean — test-curator handles post-archive cleanup

Follow-up tasks created:
- #1458: B1-impl — w-code-review rewrite + r-pipeline-protocol updates (critical, depends on #1407)
- #1459: code-reader agent update (needed, depends on #1458)
- #1460: reviewer agent file update (needed, depends on #1458)

Challenge: FALLBACK — T1 skill rewrite with explicit brief backing, no challenger needed.
[[2026-05-08]]
## Test-Writer Notes
- Test file: tests/test_reviewer_rewrite_1407.py
- Classes: TestFromAC_CodeReviewSkillRewrite, TestFromAC_PipelineProtocolUpdate
- Tests per category: happy 10, edge 0, error 0, boundary 0
- Total: 10 tests, all FAIL
- ruff: clean

### AC Coverage

| AC Line | Mapped Test(s) | Status |
|---------|---------------|--------|
| P1: w-code-review batch-all-findings approach (no first-failure gating) | test_w_code_review_has_batch_all_findings_approach | COVERED |
| P2: Output has "Review Evidence" and "Observations" sections | test_w_code_review_has_observations_section, test_w_code_review_observations_never_affect_verdict | COVERED |
| P2: Finding vs opinion rule (no citation → Observations) | test_w_code_review_finding_vs_opinion_rule_present | COVERED |
| P2: PASS one-liner "Verified: AC→code mapping complete … Zero findings." | test_w_code_review_pass_case_one_liner_present (2 assertions) | COVERED |
| P2: Reviewer reads builder's quality-runner output | test_w_code_review_reads_builder_quality_runner_output | COVERED |
| P2: Scoped 3-item checklist (AC→code mapping, test→AC alignment, proof sufficiency) | test_w_code_review_three_item_checklist (3 assertions) | COVERED |
| P2: TestFromAC immutability rule removed from reviewer skill | test_w_code_review_testfromac_immutability_removed | COVERED |
| P1: r-pipeline-protocol trust model updated (exact quoted sentence) | test_r_pipeline_protocol_trust_model_updated | COVERED |
| P2: r-pipeline-protocol reviewer contract updated (D2 trust-the-builder) | test_r_pipeline_protocol_reviewer_contract_d2_model | COVERED |
| P3: Verification by diff comparison | (process AC — no testable assertion; verified transitively by the 9 content tests) | N/A |

### Notes
- Tests read markdown files directly; all 10 FAIL against current unmodified skill files.
- Commit: f4cbf9b4