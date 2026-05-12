---
id: 1491
title: 'Cockpit: Extract CockpitProvider from Shell.tsx'
status: archived
priority: important
created: 2026-05-11T23:14:53.705441+00:00
updated: 2026-05-12T13:41:04.826663+00:00
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
archival_reason: completed
archival_refs: []
---

## Objective
Extract all state management from Shell.tsx into a CockpitProvider context.

## Acceptance Criteria
_Original implementation AC removed — superseded by "Acceptance Criteria (Revised — parent scope)" below. Implementation AC lives on child tasks #1504 and #1505._

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
2026-05-12T09:40:11+00:00
## Builder Notes
- Files changed: none (pass-through scope task)
- Test results: not applicable for this task (`Proof bundle: skip`)
- Lint status: not applicable for this task (`Proof bundle: skip`)
- Coverage: not applicable for this task (`Proof bundle: skip`)
- Evidence summary:
  - Task body explicitly marks `Proof bundle: skip` and `Parent/scope task (tagged research); implementation delegated to children #1504 and #1505`.
  - Acceptance criteria for #1491 are satisfied by research/architecture outputs already present in task notes.
  - No source implementation is required at parent scope; implementation and validation belong to child tasks #1504 (builder) and #1505 (test updates).
2026-05-12T10:03:52+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1491 -> backlog | Parent task contract is self-contradictory: implementation AC remain live while builder claims no implementation is required, and the child-task routing the parent depends on is still unresolved.
- AC evidence map:

| AC Line | Code/Task Evidence | Test Evidence | Status |
|---|---|---|---|
| Original implementation AC (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:26-30) | Parent still requires Shell/CockpitProvider implementation outcomes, but builder notes say no source implementation is required at parent scope (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:123). Child tasks carrying that implementation work remain open in research (.owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md:4, .owlbear/kanban/tasks/1505-cockpit-update-shell-test-suites-for-cockpitprovider-hooks.md:4). | Proof bundle is skip (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:59); no task-local executable proof was expected. | FAIL |
| Revised parent-scope AC (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:51-57) | Research artifact exists and the follow-up tasks were created (.owlbear/research/1491-cockpit-provider-extraction.md:89-94, .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:52-57). | N/A | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:26-30 and :51-57 | The task carries two incompatible contracts. The original AC still require concrete Shell/CockpitProvider changes, while the revised AC and builder notes treat this as a parent research/pass-through task. Reviewer cannot approve a pass-through completion while implementation AC remain on the parent. | Original AC at :26-30; revised AC at :51-57; builder claim at :122-123. | backlog |
| 2 | Parent routing notes | The parent's own notes say children #1504/#1505 still need to move from research to backlog and receive AC/proof-bundle refinement, but both children are still in research. That leaves the parent handoff structurally incomplete at review time. | Parent notes at .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:62-65 and :103-105; child statuses at .owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md:4 and .owlbear/kanban/tasks/1505-cockpit-update-shell-test-suites-for-cockpitprovider-hooks.md:4. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Replace the duplicated implementation AC on the parent with one authoritative parent-scope contract, or move the implementation AC entirely to child tasks #1504/#1505. | .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md | Finding 1 |
| 2 | architect | Advance or recreate child tasks #1504/#1505 into the correct downstream status, refine child AC/proof bundles as already noted, and only then re-send the parent if its scope still requires a pipeline handoff. | .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md, .owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md, .owlbear/kanban/tasks/1505-cockpit-update-shell-test-suites-for-cockpitprovider-hooks.md | Finding 2 |

## Observations
- Research artifact quality is adequate for a parent discovery task: .owlbear/research/1491-cockpit-provider-extraction.md exists and records the recommendation plus both follow-up tasks.
- I did not dispatch quality-runner because the blocking issue is upstream contract/routing ambiguity, not executable proof on changed code.
2026-05-12T10:47:59+00:00
## Architecture Review (Re-review after reviewer rejection)

### Reviewer Findings Addressed
| # | Finding | Fix Applied |
|---|---------|------------|
| 1 | Dual AC contract — original implementation AC conflicts with revised parent-scope AC | Removed original implementation AC (lines 25-30); replaced with supersession note pointing to revised parent-scope AC. Single authoritative contract now. |
| 2 | Children #1504/#1505 still in `research` | Advanced both to `backlog` via start_work + end_work(success). Both ready for independent architecture review. |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: research/scope parent for CockpitProvider extraction |
| Interface clarity | PASS | Sole AC is revised parent-scope contract — no ambiguity |
| Dependency correctness | PASS | Children parent=1491, #1505 depends_on=[1504] |
| TDD compliance | N/A | Parent/scope task — implementation in children |
| KISS/YAGNI | PASS | Minimal parent scope |
| Pattern consistency | PASS | Research parent pattern consistent with pipeline conventions |

### Proof-Bundle Validation
- Final bundle: skip
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Verdict: APPROVE
### Action Taken: Fixed dual AC contract (Finding 1), advanced children to backlog (Finding 2), re-approved backlog → todo
2026-05-12T11:26:06+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Parent/scope task (tagged `research`); implementation delegated to children #1504 and #1505.
- Retry cycle: reviewer findings addressed by architect (dual AC contract fixed, children advanced to backlog). Test-writer role unchanged — still a pass-through.
- Passing through to builder.
2026-05-12T11:52:57+00:00
## Builder Notes
- Files changed: none (non-implementation parent/scope task)
- Test results: not applicable (`Proof bundle: skip`)
- Lint status: not applicable (`Proof bundle: skip`)
- Coverage: not applicable (`Proof bundle: skip`)
- Evidence summary:
  - Task AC is explicitly parent-scope/research-only; implementation AC are delegated to child tasks #1504 and #1505.
  - Test-Writer Notes mark this as pass-through with no new test-writing requirement.
  - No source implementation is required on #1491; builder action is lifecycle advancement only after AC consistency and child routing were already resolved in prior architecture re-review.
2026-05-12T12:39:07+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1491 -> docs | Parent-scope AC are now internally consistent and satisfied by the research artifact plus child-task handoff.
- Builder evidence sufficiency: acceptable for `Proof bundle: skip`; builder changed no implementation files and recorded that no source implementation is required on this parent task (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:184-190). Executable proof is therefore not required at this scope (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:55).
- Blocking findings: none.
- AC evidence map:

| AC Line | Code/Task Evidence | Test Evidence | Status |
|---|---|---|---|
| Research document produced and validated | Research artifact exists and the parent scope was approved in the re-review architecture pass (.owlbear/research/1491-cockpit-provider-extraction.md:71; .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:173) | N/A — `Proof bundle: skip` (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:55) | PASS |
| Recommendation: Single CockpitProvider with 3 consumer hooks (Option A, confidence 0.72) | Recommendation is recorded in the research artifact as Option A at confidence 0.72 (.owlbear/research/1491-cockpit-provider-extraction.md:71) | N/A — `Proof bundle: skip` | PASS |
| Follow-up implementation tasks created: #1504 and #1505 | Parent AC names both child tasks (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:50); both child task records exist and are now in `backlog` (.owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md:4, .owlbear/kanban/tasks/1505-cockpit-update-shell-test-suites-for-cockpitprovider-hooks.md:4) | N/A — parent handoff criterion only | PASS |
| LOC targets revised per challenger | Challenge results record the accepted 60→75 revision and the revised parent AC carries the updated targets (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:41-42, .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:51, .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:82) | N/A — scope/research fact | PASS |
| F11 (useConnectionHealth) confirmed no-op | Parent AC explicitly anchors this fact (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:52); `useBoard` still owns `useConnectionHealth` (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:52; serve/cockpit/web/src/hooks/useBoard.ts:62) | N/A — factual validation only | PASS |
| F10 (lastDecisionsMtime → refetchPendingDRs cross-domain effect) scoped to #1504 | Parent AC delegates the cross-domain effect to child implementation work (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:53); current `Shell.tsx` still contains the effect, confirming this remains downstream implementation scope (serve/cockpit/web/src/Shell.tsx:95-98) | N/A — delegated downstream | PASS |
- Safety/security: no new executable code or dependencies were introduced on #1491; this parent task only records research, scope, and routing decisions.

## Observations
- Historical notes at .owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:58 still describe the pre-fix child status (`research`), but the later re-review note and live child task metadata are consistent and authoritative (.owlbear/kanban/tasks/1491-cockpit-extract-cockpitprovider-from-shell-tsx.md:153-154, .owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md:4, .owlbear/kanban/tasks/1505-cockpit-update-shell-test-suites-for-cockpitprovider-hooks.md:4).
- I did not dispatch `quality-runner` because this is a `skip` proof bundle with no builder-scoped file changes; the blocking issue from the first review cycle was contract/routing quality, and that issue is now resolved.
2026-05-12T13:05:51+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | No source files changed (builder: "Files changed: none"; proof bundle: skip; parent/scope task). Convention mapping finds no README targets. |
| 2. External Attribution | N/A — already recorded | `.owlbear/sources/overview.md` § "CockpitProvider Extraction Research (Task #1491)" already lists all 3 external sources (React docs, wisp.blog, LogRocket) with correct task reference and date. |
| 3. Research Doc | PASS | `.owlbear/research/1491-cockpit-provider-extraction.md` exists; linked from task body in Research section. |
| 4. Deletion Detection | N/A | No files deleted. |

### Files Updated
None — no docs impact.

### Scratch Cleanup
No `.owlbear/scratch/1491-*` files existed or were created.
2026-05-12T13:41:04+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4422 passed, 20 failed (all pre-existing), 4 skipped; vitest 0 failures; ruff clean; eslint clean
- Pre-existing failures: test_cockpit_view (11, FileNotFoundError for deleted task-scoped tests 1132/1067/1068/1071), test_ideation_diagram (1, bridge element name), test_server (1, TypeError in MCP kanban), test_engine_accessor_migration (7, accessor forwarding assertions)
- None in cockpit/frontend domain; task changed no source files
- regression verdict: PASS

### Research Task Verification
- Research doc exists: `.owlbear/research/1491-cockpit-provider-extraction.md` (committed bd676103)
- Follow-up tasks created: #1504 (backlog, parent=1491), #1505 (backlog, depends_on=[1504], parent=1491)
- Follow-ups reference parent correctly; dependency chain intact
- verdict: PASS

### Intent Verification
- scope alignment: PASS (cockpit/frontend research; doc and children in same domain)
- purpose match: PASS (research doc directly addresses CockpitProvider extraction with options analysis and recommendation)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
- Initial dual AC contract (implementation + parent-scope) caused reviewer rejection in cycle 1
- Re-review resolved correctly: removed implementation AC, single parent-scope contract
- Final AC are specific, clear, and appropriate for research parent scope
- Minor gap: architect should have proactively cleaned up AC when task scope changed from implementation to research parent during initial review

### Commit Integrity
- upstream commit presence: PASS (bd676103 — research doc by researcher)
- No source files expected (pass-through scope task, proof bundle: skip)
- kanban commit packaging: pending (this archival)

### Deduction Breakdown
- No task-attributable regressions: 0
- Intent alignment clean: 0
- AC quality 4/5 (>3): 0
- Review evidence present and detailed (two cycles, second PASS): 0
- Commit integrity verified: 0

### Confidence: 1.00
### Action: archive