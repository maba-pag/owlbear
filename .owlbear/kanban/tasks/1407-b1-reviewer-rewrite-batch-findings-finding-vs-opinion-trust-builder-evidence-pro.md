---
id: 1407
title: 'B1: Reviewer rewrite — batch findings, finding vs opinion, trust builder evidence,
  protocol update'
status: research
priority: critical
created: 2026-05-07T23:16:25.214918+00:00
updated: 2026-05-07T23:18:14.502778+00:00
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