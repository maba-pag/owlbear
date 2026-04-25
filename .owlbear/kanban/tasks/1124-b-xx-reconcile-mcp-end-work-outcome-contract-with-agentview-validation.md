---
id: 1124
title: 'B-XX: Reconcile MCP end_work outcome contract with AgentView validation'
status: research
priority: important
created: '2026-04-25 17:19:08.063026+00:00'
updated: '2026-04-25T20:54:03.386033+00:00'
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-25]]
## Research
- Research doc: .owlbear/research/reconcile-end-work-outcome-contract.md
- Sources: 9 studied, 9 high-relevance (all codebase-internal)
- Recommendation: Restore `fail` to AgentView.end_work valid_outcomes (confidence: 0.82)
- Follow-up tasks created: #1125 (restore fail + align model, needed), #1126 (remove dead fallback chain, nice-to-have)
- Decision requests: none (T1 — bug fix restoring documented pipeline behavior)

## Challenge Results
- Challenger: reconsider (confidence in original: 0.34)
- Rebuttal: (a) #1077 architect explicitly deferred MCP alignment to this task; (b) `release` drops notes — not a substitute for `fail`; (c) pipeline protocol is authoritative and mandates `fail` for 3 active use cases
- Post-challenge confidence: 0.82

## Key Finding
`release` does NOT append timestamped notes (goes through `release_task`), while `fail` DOES (goes through raw `engine.end_work`). Pipeline protocol's 3 `fail` use cases (TOOL_UNAVAILABLE, prerequisite handoff, agent handoff) all require note appending. Replacing `fail` with `release` would silently drop agent diagnostic notes — a data-loss gap.
[[2026-04-25]]
## Architecture Review

### Verdict: REJECT → research

### AC Assessment
No implementation AC present (research umbrella task). Research quality assessed instead.

### Critical Gaps Found

**1. Brief B D52 authority conflict — not addressed**
Brief B `decisions.md` D52 explicitly dropped `fail` as a deliberate design choice ("orphan-claim foot-gun"), not a bug. The research doc doesn't reference D52 at all. This transforms the recommendation from T1 (bug fix) to T3 (authority reversal) which requires a Decision Request per `w-arch-review` criterion 12.

**2. The "data loss" finding is actually a `release` implementation bug**
Brief B D52 specifies: "`release`: clears claim, no status change, `note` appended if set." The current code routes `release` through `release_task()` which does NOT append notes — contradicting D52. The research doc treats this as evidence that `fail` must be restored, but the correct reading is that `release` has an unimplemented D52 requirement. If `release` is fixed to append notes (as D52 intended), the semantic gap between `fail` and `release` disappears, and the pipeline protocol use cases could work with `release`.

**3. Two-option analysis needed**
The research should present both paths:
- **Option X**: Fix `release` to append notes per D52 + update pipeline protocol/agents to use `release` instead of `fail`
- **Option Y**: Restore `fail` (override D52) — the current recommendation

Each needs: diff size, authority implications, test impact, and migration cost.

**4. Follow-up tasks lack AC**
#1125 and #1126 have empty bodies. Pipeline protocol requires concrete acceptance criteria on all follow-ups.

### Evaluation (partial — research quality)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research scope is focused |
| Premise challenge | FAIL | Missed Brief B D52 — the authoritative design source for end_work outcomes |
| Pattern consistency | FAIL | Recommendation overrides Brief B without acknowledging the override |
| KISS/YAGNI | DEFERRED | Cannot assess until both options are analyzed |

### Challenge Results
- Challenger: block (confidence in original: 0.32)
- Key concerns: (1) T1/T3 misclassification, (2) Brief B authority not consulted, (3) selective reading of #1077 deferral, (4) follow-up AC gaps
- Architect response: accepted concerns 1, 2, 3, 4. The Brief B D52 gap is material — it invalidates the core "data loss" argument that underpins the recommendation.

### Action Required for Re-research
1. Read `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/decisions.md` D52 and `paper-integration.md` §outcome matrix
2. Analyze both options (fix release vs restore fail) with trade-off matrix
3. Resolve T1/T3 classification — if T3, create a DR via scribe
4. Populate #1125 and #1126 with concrete AC
5. Address the `release` note-appending implementation gap (is it a separate bug or part of this reconciliation?)
[[2026-04-25]]
## Research (v2 — post-rejection revision)

### Summary
Revised research addressing all 5 architect feedback items. Brief B D52 deliberately dropped `fail`; the original research missed this authority source.

### Key Findings
1. **`fail` ≠ `release` semantically.** Session analytics classify `fail` as `completed-fail` and `release` as `released`. Cockpit UI has distinct filters. Merging them breaks observability.
2. **D52 `release` note gap is a separate bug.** D52 says `release` appends notes; current impl doesn't. This is defect D2, independent of the `fail` question.
3. **Only 2 of 11 layers reject `fail`.** Raw engine, MCP server.py, guidance, pipeline protocol, agent files, skill docs, session analytics, cockpit UI all expect it.

### Recommendation: Option Y — Restore `fail` + fix `release` notes (confidence: 0.72)
Rationale: D52's consolidation overlooked the observability distinction. 9 layers already use `fail`. Lower risk than removing `fail` from everywhere.

### Two-option trade-off matrix
- **Option X (complete D52):** Aligned with brief authority but high risk — requires changes to engine, session classifier, cockpit UI, 5+ test files. KISS: 0.35.
- **Option Y (restore fail + fix release):** Deviates from D52 but aligns with live contract. 2-3 code files changed. KISS: 0.80.

### Tier: T2 (advisory DR created)
D52 deviation doesn't add new capabilities or change architecture — ratifies de facto contract.

### Challenge Results (v2)
- Challenger: `reconsider` (confidence in Option X: 0.36)
- Critical finding: `fail` and `release` carry distinct session/activity/cockpit semantics — not equivalent
- Post-challenge: revised from Option X to Option Y

### Follow-up Tasks
- #1125: Restore `fail` to AgentView + EndWorkParams (already approved, in todo, has AC)
- #1126: Remove dead TypeError fallback chains (already researched, in backlog)
- #1127: Fix `release` note-appending per D52 (new — defect D2, has AC)

### Research doc
`.owlbear/research/reconcile-end-work-outcome-contract-v2.md`

### Attribution
- Sources: 16 studied (Brief B decisions, paper-integration, engine code, MCP code, pipeline protocol, session tests, cockpit tests)
- DR: `.owlbear/decisions/pending/1124-end-work-outcome-authority.md` (T2 advisory, 5-day auto-resolve)
[[2026-04-25]]
## Decision Resolution

**DR:** `.owlbear/decisions/resolved/1124-end-work-outcome-authority.md`
**Decision:** A: Ratify the live 5-outcome contract
**Authority:** User (via scribe)

Approved — restore `fail` to AgentView and EndWorkParams valid_outcomes, overriding Brief B D52 based on system-wide observability evidence. Follow-up tasks #1125, #1126, #1127 approved to proceed.
