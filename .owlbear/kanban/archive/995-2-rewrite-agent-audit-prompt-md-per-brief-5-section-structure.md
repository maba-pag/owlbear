---
id: 995
title: '2: Rewrite agent-audit.prompt.md per Brief 5-section structure'
status: backlog
priority: important
created: 2026-04-18T21:23:39.614381+00:00
updated: 2026-04-18T21:23:39.614381+00:00
tags:
- type:docs
- scope:prompt
parent: 984
depends_on:
- 992
- 993
- 994
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #984

## Objective
Rewrite `.github/prompts/agent-audit.prompt.md` as a maximum-quality ecosystem audit prompt following the 5-section structure defined in the Brief.

## Structure (5 sections)
1. **Preamble** — role, stakes, behavioral contract, trust signals
2. **Audit Surface and Standards** — two surfaces with weighting, standards loading order, references-not-restates
3. **Seven Audit Dimensions** — Structural (with boundary-fitness), Duplication, Content Placement, Quality, Pipeline Integrity, SNR, Memory Governance and Content — each with negative-space probes
4. **Process** — scan-first, severity-first, continuous one-finding-at-a-time loop with finding cards, confidence scores, conditional phase breaks, queue re-evaluation
5. **Verification** — pipeline trace, rejection-routing, SNR spot-check, coverage summary, "run from the top?"

## Carry Forward
- Pipeline-integrity routing tables from current prompt
- Dynamic file discovery via `file_search`
- Standards-first loading order

## Drop
- Static FINDINGS / REMEDIATION PLAN batch output template

## Acceptance Criteria
- [ ] Single self-contained `.prompt.md` under `.github/prompts/`.
- [ ] All 7 dimensions x both surfaces covered (with MCP-unavailable degradation path).
- [ ] Continuous loop without silent stalls; uses `askQuestions` literal at every user-facing turn.
- [ ] Re-scan prompted on queue exhaustion.
- [ ] Each finding card includes confidence on recommendation AND each option.
- [ ] References (does not duplicate) rules in `h-agent-structure`, `h-memory-structure`, `r-pipeline-protocol`, `r-project-standards`.
- [ ] Pipeline routing tables carried forward from current prompt.

## Files
- `.github/prompts/agent-audit.prompt.md`