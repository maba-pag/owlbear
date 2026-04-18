---
id: 1003
title: 'Rewrite agent-audit.prompt.md per Brief #984'
status: backlog
priority: needed
created: 2026-04-18T21:35:10.131608+00:00
updated: 2026-04-18T21:35:10.131608+00:00
tags:
- prompt
- agent-ecosystem
parent: 984
depends_on:
- 1000
- 1001
- 1002
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Rewrite `.github/prompts/agent-audit.prompt.md` as the maximum-quality ecosystem audit prompt per the Brief in parent task #984.

## Context

The current audit prompt works but was a quick-shot. The rewrite sharpens coverage to 7 audit dimensions x 2 surfaces (definitions + memory), replaces the batch output template with a continuous one-finding-at-a-time loop, and references (not restates) the standards formalized in sibling tasks #1000, #1001, #1002.

## Acceptance Criteria

- [ ] Single self-contained `.prompt.md` at `.github/prompts/agent-audit.prompt.md`.
- [ ] Five sections in order:
  1. **Preamble** — role, stakes, behavioral contract; trust signals ("rejection is safe", "all evidence inline").
  2. **Audit Surface and Standards** — two surfaces with explicit weighting (Definitions >80%, Memory <20%); standards loading order (`h-agent-structure` first, then `r-pipeline-protocol`, then `r-project-standards`); references-not-restates principle; graceful MCP degradation path when `owlbear-memory` tools unavailable.
  3. **Seven Audit Dimensions** — Structural (incl. boundary-fitness sub-probe from #1000) / Duplication / Content Placement / Quality / Pipeline Integrity / SNR / Memory Governance and Content (referencing #1001). Each dimension has at least one negative-space probe (what's missing, not just what's wrong).
  4. **Process** — scan-first; severity-first ordering (HIGH then MED then LOW); one-finding-at-a-time loop using finding card (Header / Evidence / Options-when-ambiguous / Recommendation / askQuestions approval); confidence on every finding AND every option; conditional phase breaks (3+ in next tier); queue re-evaluation after each fix; pause/bail any time.
  5. **Verification** — pipeline trace (impl + non-impl paths); rejection-routing consistency (no BLOCK verdicts); SNR spot-check; coverage summary; askQuestions "run from the top again?"
- [ ] All 7 dimensions x both surfaces (definitions + memory) covered, with explicit MCP-unavailable degradation path for memory surface.
- [ ] Loop runs continuously; uses literal `askQuestions` at every user-facing turn.
- [ ] Re-scan prompted via askQuestions on queue exhaustion.
- [ ] Each finding card includes confidence on the recommendation AND each option.
- [ ] References (does not duplicate) rules from `h-agent-structure`, `h-memory-structure`, `r-pipeline-protocol`, `r-project-standards`.
- [ ] Carries forward from current prompt: pipeline-routing tables, dynamic `file_search` discovery, standards-first loading order.
- [ ] Drops from current prompt: static FINDINGS / REMEDIATION PLAN batch output template.

## Files

- `.github/prompts/agent-audit.prompt.md`
