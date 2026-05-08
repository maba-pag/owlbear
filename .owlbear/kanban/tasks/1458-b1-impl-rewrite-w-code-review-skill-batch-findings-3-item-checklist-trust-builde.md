---
id: 1458
title: 'B1-impl: Rewrite w-code-review skill — batch findings, 3-item checklist, trust
  builder evidence'
status: backlog
priority: critical
created: 2026-05-08T19:47:09.269589+00:00
updated: 2026-05-08T19:47:45.823376+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
parent: 1403
depends_on:
- 1407
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Rewrite `share/skills/w-code-review/SKILL.md` per research in `.owlbear/research/1407-reviewer-rewrite.md`. Key changes: (1) replace first-failure gating with batch-all-findings, (2) replace 12-check system with 3-item checklist (AC→code mapping, test→AC alignment, proof sufficiency), (3) read builder quality-runner output instead of re-executing, (4) remove TestFromAC immutability rule, (5) remove security review (CI/SAST handles), (6) output template: Review Evidence (findings) + Observations (opinions), (7) PASS case one-line confirmation. Also update `r-pipeline-protocol` trust model and reviewer contract section. Update code-reader consumer contract within w-code-review.