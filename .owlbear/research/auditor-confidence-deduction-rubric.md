# Auditor Confidence Deduction Rubric

> **Owning task:** #197 — Calibrate auditor confidence scoring with deduction rubric
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The auditor's confidence scoring is performative: 34/58 archived tasks (59%) score .97, 12 (21%) score .95, and 80% cluster in .95–.97 (pipeline-quality-audit.md §3.2). Only 1 task scored below .90. This narrow band provides no meaningful differentiation. The question: will a deduction-from-max rubric fix this, and are the proposed deduction values well-calibrated?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | OwlBear pipeline-quality-audit.md (task #192) | Internal | 1.0 |
| S2 | OwlBear archived task audit sections (#7, #10, #4) | Internal | 0.9 |
| S3 | Popham 1997 — What's Wrong and What's Right with Rubrics | External | 0.8 |
| S4 | Wikipedia — Inter-rater reliability (Cohen 1960, Fleiss 1971) | External | 0.8 |
| S5 | Du et al. 2023 — Multi-agent Debate (arXiv:2305.14325) | External | 0.7 |
| S6 | Wang et al. 2024 — Rethinking Bounds of LLM Reasoning (arXiv:2402.18272) | External | 0.7 |

## 3. Analysis

### 3.1 Why Scoring Drifts to .97

Without explicit deduction criteria, the auditor picks from a narrow mental range (.95–.97) based on gestalt impression [S4 — rater drift without explicit guidelines]. Sequential pipeline framing compounds this: by the time the auditor sees a task, upstream agents all said "PASS" or "DONE," which anchors the auditor toward high scores [S5 — anchoring in sequential pipelines]. Wang et al. [S6] confirm that structured prompts are more effective than adding agents — a rubric addresses the root cause.

### 3.2 Rubric Type: Analytic Deduction-from-Max

Analytic rubrics evaluate dimensions separately (vs. holistic) [S3]. Deduction-from-max (start at 1.0, subtract per criterion) is a standard pattern that:

- Forces dimension-by-dimension evaluation rather than gestalt
- Makes the score reproducible — same inputs yield same score
- Creates audit trail — the deduction breakdown IS the evidence

### 3.3 Proposed Deduction Values — Evaluation

| Criterion | Proposed | Assessment | Refined |
|-----------|----------|------------|---------|
| AC line with no specific evidence | -.02 | Too low: 5 unverified lines barely crosses .90 | -.03 |
| Lint/ruff issues found | -.05 | Appropriate: should have been caught at 2nd line | -.05 |
| AC quality score ≤ 3 | -.03 | Too low: ≤ 3 signals architect failure, auditor's unique domain | -.05 |
| Missing reviewer evidence section | -.02 | Too low: signals 2nd-line defense failed entirely | -.05 |
| Full-suite test failures in scope | -.05 | Appropriate: functional failures are critical | -.05 |

**Why refine?** Applying original values to archived tasks: task #7 (all AC verified, quality 5/5, no issues) would score 1.0. Task #4 (quality 4/5, reviewer needed retry) would score .97 — still clustering. With refined values, #4 would score .95, which is meaningfully different.

### 3.4 Additional Deductions to Consider

| Criterion | Value | Rationale |
|-----------|-------|-----------|
| Scope creep: changed files outside task domain | -.03 | Auditor already checks this (Step 2) but no score impact |
| Builder notes indicate AC workaround/deviation | -.02 | Signals architect's AC led builder astray |

### 3.5 Risk Analysis

| Risk | Likelihood | Mitigation |
|------|:----------:|------------|
| Over-rejection: too many deductions push below .95 | Medium | This is the desired outcome — it means the scoring is actually differentiating |
| Gaming: auditor claims "no deductions" without checking | Low | Require deduction breakdown in output format — absence of breakdown = red flag |
| Calibration needed after deployment | High | Review first 10 scored tasks, adjust values if distribution is still clustered |

## 4. Recommendation (.85 confidence)

The deduction rubric approach is well-supported by rubric literature [S3] and inter-rater reliability research [S4]. Approve the task's AC with two refinements:

1. **Increase deduction values** for AC-quality (-.03 to -.05) and missing-reviewer-evidence (-.02 to -.05) — these represent upstream defense failures, the auditor's primary unique value
2. **Add red-flag for missing breakdown** — "Score reported without deduction breakdown" should trigger self-correction, not just "score is between .95 and .97"

The AC's core approach (start at 1.0, deduct per criterion, require breakdown) is sound. Builder implementation is markdown-only (skill + agent files), no code changes.

## 5. Follow-up Tasks

Task #197 itself is the implementation vehicle. No additional follow-ups needed — the AC is concrete and scoped to two files. The architect should evaluate the refined deduction values from §3.3 and decide whether to adopt them or keep the originals.
