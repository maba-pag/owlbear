---
id: 1379
title: 'P2-04: Implement Cockpit task detail edit validation and dirty state'
status: todo
priority: critical
created: 2026-05-06T01:04:34.112524+00:00
updated: 2026-05-08T20:29:13.753072+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-detail
- validation
parent: 1363
depends_on:
- 1378
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement explicit parent/dependency validation and dirty-state handling for the task detail editor.

## Problem Evidence
- parseDependsOn silently drops invalid dependency entries.
- parseParent turns invalid input into null, risking accidental parent clearing.
- Detail fields are mostly hidden-label or raw controls with no dirty-state model.

## Acceptance Criteria
- Invalid parent input is preserved, shown to the user, and never sent as an accidental clearing update.
- Invalid dependency entries are preserved, shown to the user, and never silently dropped from the intended edit.
- Save controls reflect validation and dirty state so unchanged, invalid, and intentionally changed forms are distinct.
- Validation errors use the frontend error-contract behavior from #1375.
- Existing valid parent and dependency edits continue to save correctly.
- The implementation satisfies #1378 without adding action-gating or conflict-resolution behavior owned by later tasks.

## Scope
- In scope: Cockpit frontend task detail editor validation, dirty-state, and save intent.
- Out of scope: task-detail model expansion from #1377, action gating, conflict resolution, backend lifecycle work, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1378.

[[2026-05-08]]

## Architecture Review

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: Invalid parent preserved, shown, never sent | PASS — verifiable, td:2 | No change |
| AC2: Invalid depends_on preserved, shown, never dropped | PASS — verifiable, td:2 | No change |
| AC3: Save controls reflect validation and dirty state (original) | FAIL — "unchanged, invalid, and intentionally changed forms are distinct" is not testable as written; save button doesn't consult dirty state | **Refined** to match #1378 test contract |
| AC4: Validation errors use error-contract from #1375 | PASS — verifiable via same DOM element, td:1 | No change |
| AC5: Valid parent/dependency edits continue to save | PASS — regression guard, td:1 | No change |
| AC6: No action-gating or conflict-resolution added | PASS — scope guard, td:1 | No change |

### Refined Acceptance Criteria
- Invalid parent input is preserved, shown to the user, and never sent as an accidental clearing update. (td:2)
- Invalid dependency entries are preserved, shown to the user, and never silently dropped from the intended edit. (td:2)
- A dirty-state indicator is visible when form values differ from the loaded task state and absent when all values match. Client-side validation errors prevent save from submitting to the server. (td:2)
- Validation errors use the frontend error-contract behavior from #1375 — both client-side and server-side validation errors render through the same DOM element. (td:1)
- Existing valid parent and dependency edits continue to save correctly. (td:1)
- The implementation satisfies #1378 without adding action-gating or conflict-resolution behavior owned by later tasks. (td:1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Validation + dirty state for task detail editor — single concern |
| Interface clarity | PASS | After AC3 refinement, all AC lines are testable against #1378 tests |
| Dependency correctness | PASS | #1378 (test task) archived/done; #1375 (error-contract) archived/done |
| Module layering | PASS | Client-side validation in DetailTab.tsx, server errors via errorMessage.ts — no upward imports |
| TDD compliance | PASS | #1378 wrote 20 RED phase tests covering all AC lines |
| KISS/YAGNI | PASS | No new abstractions — validation in existing parse functions, dirty state via string comparison |
| Premise challenge | CONDITIONAL | Implementation may already exist from #1378 builder cycle (commit e6feb8ac). Builder should verify tests pass; if GREEN is trivial, that confirms prior work. Task remains valid as the formal implementation record. |
| Pattern consistency | PASS | Uses existing error-contract pattern from #1375; dirty indicator follows existing data-testid conventions |
| Security surface | PASS | Client-side only; no new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Provenance Note
Challenger identified that #1378 builder (not #1377) implemented the production changes (commit e6feb8ac). The current DetailTab.tsx already contains parseDependsOn/parseParent with error returns, clientValidationMessage, isDirty, dirty indicator, and validation message display. The builder's GREEN phase may confirm tests already pass — this is acceptable and validates the TDD cycle.

### Challenge Results
- Challenger verdict: reconsider (confidence 0.57)
- Key finding: AC3 was vague ("distinct" not testable) — addressed via refinement
- Provenance correction: implementation attributed to #1378 builder, not #1377 — noted
- Lexical dirty check concern: accepted as minor; raw string comparison is appropriate for this scope
- Architect response: AC3 refined, provenance noted, APPROVE sustained

### Test Depth
- Max depth: 2
- Test-writer: tests already written by #1378

### Verdict: APPROVE → todo
AC3 refined for testability. All criteria pass. Implementation may already exist from #1378 builder cycle — builder verifies.

[[2026-05-08]]
Architecture review complete. AC3 refined from vague "distinct" to testable: dirty indicator + validation-blocks-save. All 10 criteria pass. Challenger raised AC3 vagueness (addressed) and provenance correction (#1378 builder implemented, not #1377). Implementation may already exist — builder verifies via GREEN phase.