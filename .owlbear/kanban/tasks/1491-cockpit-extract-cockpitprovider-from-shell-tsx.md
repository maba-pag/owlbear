---
id: 1491
title: 'Cockpit: Extract CockpitProvider from Shell.tsx'
status: in-progress
priority: important
created: 2026-05-11T23:14:53.705441+00:00
updated: 2026-05-12T09:12:05.167177+00:00
tags:
  - cockpit
  - frontend
  - refactor
  - research
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract all state management from Shell.tsx into a CockpitProvider context.

## Acceptance Criteria
- Shell.tsx becomes ~60 LOC layout-only (CSS grid + component composition)
- CockpitProvider (~150 LOC) owns: board/tasks state, selected task lifecycle, DR state, cross-domain effects
- Children consume via hooks: useBoardState(), useTaskSelection(), useDRState()
- No prop drilling through Shell
- Also fold in F10 (useSSERefetch extraction) and F11 (inline useConnectionHealth)

## Source
Cockpit audit 2026-05-11, Finding F1 (+ F10, F11)
2026-05-12T03:00:37+00:00

## Research
- Research doc: .owlbear/research/1491-cockpit-provider-extraction.md
- Sources: 11 studied, 6 high-relevance
- Recommendation: Single CockpitProvider with 3 consumer hooks (confidence: 0.72)
- Follow-up tasks created: #1504 (implement provider), #1505 (update tests)
- Decision requests: none (T1 — autonomous refactor)

## Challenge Results
- Challenger: reconsider (confidence in original: 0.44)
- Key challenges: render fan-out real but bounded, LOC targets need adjustment (60→75), callback identity churn needs explicit attention, test blast radius significant (8 Shell + 4 hook files)
- Researcher response: revised — accepted LOC adjustment, callback stabilization requirement, test scope documentation. Rebutted HIGH risk (moderate) and "narrow boundaries" claim. Confidence: 0.72
2026-05-12T03:00:52+00:00
Research complete. Single CockpitProvider recommended (confidence: 0.72). Challenger pushed back (0.44) — accepted LOC adjustment (60→75), callback stabilization, test blast radius. Two follow-ups created: #1504 (implement), #1505 (tests). Doc: .owlbear/research/1491-cockpit-provider-extraction.md


## Acceptance Criteria (Revised — parent scope)
- Research document produced and validated: `.owlbear/research/1491-cockpit-provider-extraction.md`
- Recommendation: Single CockpitProvider with 3 consumer hooks (Option A, confidence: 0.72)
- Follow-up implementation tasks created: #1504 (implement provider), #1505 (update tests)
- LOC targets revised per challenger: Shell ~75 LOC (was ~60), CockpitProvider ~150 LOC
- F11 (useConnectionHealth) confirmed no-op — already co-located inside useBoard.ts (line 62)
- F10 (lastDecisionsMtime → refetchPendingDRs cross-domain effect) scoped to #1504

Proof bundle: skip

## Architecture Review Notes (for children)
Children #1504 and #1505 are in `research` with full AC — they need to advance to `backlog` for independent architecture review. Key items for those reviews:
- #1504 AC needs B1/B2 refinement (LOC targets are soft constraints, several lines are implementation details not behavior)
- #1504 needs proof bundle assignment (recommend `behavioral` — significant refactor with 10 Shell test files)
- #1505 depends_on #1504 correctly; needs proof bundle `existing` (mock path updates, parity check)
2026-05-12T08:24:40+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: extract state management from Shell into CockpitProvider |
| Interface clarity | PASS | Parent scope clear; implementation AC delegated to #1504/#1505 |
| Dependency correctness | PASS | Children set parent=1491, #1505 depends_on=[1504] |
| Module layering | PASS | CockpitProvider wraps at App level, follows EventSourceProvider precedent |
| TDD compliance | N/A | Parent/scope task — implementation in children |
| KISS/YAGNI | PASS | Option A (single provider) is simplest; rejected split providers and use-context-selector |
| Premise challenge | PASS | Shell at 305 LOC mixes 7 useState + 5 useEffect with 200 LOC layout — extraction justified |
| Pattern consistency | PASS | Follows existing EventSourceProvider pattern in same hooks/ directory |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend/cockpit only |

### Refinements Applied
1. Added `research` pass-through tag (parent/scope task produces no testable code)
2. Appended revised AC reflecting parent scope role (original AC duplicated #1504)
3. LOC target corrected: ~60 → ~75 (per accepted challenger revision)
4. F11 confirmed no-op: useConnectionHealth already called inside useBoard.ts (line 62)
5. Proof bundle: skip (scope/research parent)

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Design Diverge
- Trigger: skipped — single viable approach (Option A) already validated by research challenger

### Action Items for Children
- #1504 and #1505 need to advance from `research` → `backlog` for independent arch review
- #1504 AC needs B1/B2 quality refinement (LOC-as-AC is soft, implementation details ≠ behavior)
- Both children need proof bundle assignments (recommend: #1504=behavioral, #1505=existing)

### Verdict: APPROVE
### Action Taken: Refined AC to parent scope, tagged research, advanced backlog → todo
2026-05-12T09:12:05+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Parent/scope task (tagged `research`); implementation delegated to children #1504 and #1505.
- Passing through to builder.