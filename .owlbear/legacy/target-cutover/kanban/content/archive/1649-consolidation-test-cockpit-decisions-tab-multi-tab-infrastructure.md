---
id: 1649
title: 'Consolidation test: Cockpit Decisions Tab multi-tab infrastructure'
status: archived
priority: medium
created: 2026-05-18T00:50:31.900068+02:00
updated: 2026-05-20T11:45:49.205172+02:00
tags:
  - consolidation-test
  - scope:cockpit-web
  - scope:cockpit
parent: 1638
depends_on:
  - 1639
  - 1640
  - 1641
  - 1642
  - 1643
  - 1644
  - 1645
  - 1646
  - 1647
  - 1648
ac:
  - 'Route rendering: Shell at `/` mounts KanbanBoard (`[data-region="workspace"]`
    contains board); Shell at `/decisions` mounts DecisionsPage (`[data-testid="decisions-page"]`
    present); `[data-region="sidecar"]` and `[slot="sidebar-end"]` absent from DOM
    on both routes (retirement invariant)'
  - 'Nav-rail integration: nav button for active route carries `aria-current="page"`;
    decisions button badge renders pending DR count when > 0 and is absent when count
    is 0'
  - 'Entry path convergence: DecisionsPage list-item click and DRStatusIndicator popover-item
    click both call `setSelectedDRId(id)` causing Shell-level ResolveModal to render
    with the targeted DR; ResolveModal snapshots DR data on mount via `useState(()
    => dr)` preventing SSE-driven parent mutations during open modal'
  - 'Post-resolve integration: after ResolveModal `onResolved` fires, Shell calls
    `refetchPendingDRs()`, calls `refetchTasks()`, and calls `setSelectedDRId(null)`
    clearing the modal'
  - 'Backend contract (full-stack): GET /api/decisions/pending returns PendingDRResponse
    with `count` and `items` validated by Pydantic; POST /api/decisions/{id}/resolve
    with notes exceeding 10,000 characters returns HTTP 422 with validation error'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

Integration verification across all P1 + P2 subtasks. Ensures the tab system, decisions content, entry path convergence, and backend contracts work together.

## Sibling Tasks

- #1639 P1-01 routing infra
- #1642 P1-02 nav-rail
- #1643 P1-03 sidecar conditional
- #1644 P1-04 lazy loading
- #1645 P2-01 decisions list
- #1646 P2-03 badge
- #1647 P2-02 ResolveModal + SSE guard
- #1648 P2-04 sidecar DR removal
- #1640 P2-05 Pydantic response model
- #1641 P2-06 notes cap

[[2026-05-20T10:30:01+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Integration verification only — no implementation |
| Interface clarity | PASS (after refinement) | AC split from 3 bundled lines to 5 focused lines; each names concrete observables |
| Dependency correctness | PASS | All 10 deps archived/completed |
| Module layering | PASS | Test-only task; no module creation |
| TDD compliance | PASS | This IS the test task — test-writer writes integration tests |
| KISS/YAGNI | PASS | Consolidation tests are the standard completion gate pattern |
| Premise challenge | PASS | Parent #1638 depends on this as completion gate; cross-task integration not covered by individual task tests |
| Pattern consistency | PASS | Matches consolidation-test pattern used elsewhere (cf. #1673) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit frontend + backend integration (single product domain) |

### AC Refinements Applied
1. Split AC1 bundled targets (route render + sidecar retirement + nav-state + badge) into AC1 + AC2
2. Fixed convergence point: `setSelectedDRId(id)` is the contract, not the derived `selectedDR` value
3. Added post-resolve integration AC (Shell refetch/clear seam — challenger blind-spot finding)
4. Reframed backend AC as full-stack integration rather than isolated re-proof of #1640/#1641
5. Replaced stale \"with/without sidecar\" language with precise DOM selectors

### Proof-Bundle Validation
- Planner assignment: critical
- Final bundle: behavioral (de-escalated)
- De-escalation rationale: comparable consolidation task #1673 uses behavioral; critical requires cross-cutting public API or high-blast-radius codepaths per proof-bundle taxonomy — consolidation tests verify integration, not critical surfaces
- Test-writer: PROCEED

### Challenge Results
- Challenger: reconsider (confidence 0.46)
- Findings addressed: AC bundling (split), convergence precision (fixed), post-resolve blind spot (added AC4), proof-bundle policy mismatch (de-escalated), scope skew (reframed AC5)
- Findings considered but not adopted: tab extensibility verification (already proven by /memories route existence), sibling regression suite requirement (individual task tests are archived proof; consolidation purpose is cross-task integration)
- Architect response: revised — all major challenger findings incorporated

### Verdict: APPROVE
### Action Taken: AC refined (5 focused lines), proof bundle de-escalated critical→behavioral, advanced to todo

[[2026-05-20T10:42:25+02:00]]
test-writer crashed once (no output); releasing claim before retry

[[2026-05-20T10:59:04+02:00]]
## Test-Writer Notes
- Frontend test file: `serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx`
- Backend test file: `serve/cockpit/tests/test_decisions_integration.py`
- Classes (frontend): `DecisionsTabRoutesDurable` (AC1), `DecisionsTabNavBadgeDurable` (AC2), `DecisionsTabEntryPathDurable` (AC3), `DecisionsTabPostResolveDurable` (AC4)
- Classes (backend): `TestDecisionsBackendIntegrationDurable` (AC5)
- Tests per category: happy 29, edge 0, error 0, boundary 5
- Total: 34 tests written
- ruff: clean, ESLint: clean

**All 34 tests PASS** — all 10 dependency subtasks are archived/implemented. This consolidation test serves as a durable integration backstop verifying that all pieces work together end-to-end. Builder job: run tests to confirm green, advance to review.

**AC coverage:**
| AC | Tests | File |
|----|-------|------|
| AC1: Route rendering + sidecar retirement | 7 (2 routes × 3 invariants + workspace) | frontend |
| AC2: Nav-rail aria-current + badge | 6 (aria-current tracking + badge count/absent) | frontend |
| AC3: Entry path convergence (DRStatusIndicator + DecisionsPage clicks) + SSE prop wiring | 7 | frontend |
| AC4: Post-resolve callbacks (refetchPendingDRs, refetchTasks, modal clear, onClose) | 4 | frontend |
| AC5: Backend PendingDRResponse shape + notes cap 422 | 10 | backend |

**Note on AC3 snapshot guard:** The `useState(() => dr)` snapshot behaviour is already verified at Shell integration level by the durable `ResolveModalSnapshot_1647.test.tsx` (tests `ac1+ac2 edge: modal keeps original DR title after SSE-driven pendingDRItems update`). AC3 here adds the DRStatusIndicator click path (not covered by #1647) and the Shell prop-passing wiring test (that Shell passes updated selectedDR to ResolveModal after SSE mutation).

[[2026-05-20T11:03:13+02:00]]
## Builder Notes
- Implementation: no source changes required (consolidation verification pass-through task)
- Files changed: none
- Tests: 34 passed, 0 failed, 0 skipped
- Coverage: not requested for this test-only consolidation gate
- Lint: clean (ESLint + ruff)
- Evidence summary: quality-runner scoped execution over `serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx` and `serve/cockpit/tests/test_decisions_integration.py` returned all green with exit codes 0 for vitest, pytest, eslint, and ruff.
- Fixes applied: none (verification-only builder step)

[[2026-05-20T11:29:43+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1649 -> docs | AC mapped to code and evidence sufficient.
- AC1: routing and sidecar-retirement behavior map to [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L4), [serve/cockpit/web/src/routes.ts](serve/cockpit/web/src/routes.ts#L27), and [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L507); direct proof is in [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L250-L293).
- AC2: nav active-state and badge behavior map to [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L475-L489); direct proof is in [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L312-L346).
- AC3: selected-DR convergence maps to [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L68), [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L196), [serve/cockpit/web/src/pages/DecisionsPage.tsx](serve/cockpit/web/src/pages/DecisionsPage.tsx#L54-L65), [serve/cockpit/web/src/components/DRStatusIndicator.tsx](serve/cockpit/web/src/components/DRStatusIndicator.tsx#L145-L164), [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L54), and [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L579-L586). Task-local Shell convergence proof is in [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L370-L449). Because that file explicitly defers snapshot proof to the durable #1647 suite at [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L23) and [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L425-L427), I independently re-verified the production popover path in [serve/cockpit/web/src/__tests__/DRStatusIndicator.test.tsx](serve/cockpit/web/src/__tests__/DRStatusIndicator.test.tsx#L232-L248) and the snapshot guard in [serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx#L213-L323); both suites were green.
- AC4: Shell post-resolve wiring maps to [serve/cockpit/web/src/Shell.tsx](serve/cockpit/web/src/Shell.tsx#L582-L586). Task-local callback wiring is proved in [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L469-L516). Because the task-local file uses a ResolveModal double, I independently re-verified the real submit-success callback path in [serve/cockpit/web/src/__tests__/ResolveModal.test.tsx](serve/cockpit/web/src/__tests__/ResolveModal.test.tsx#L180-L196); that suite was green.
- AC5: backend contract maps to [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L33), [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L95-L131), and is proved by [serve/cockpit/tests/test_decisions_integration.py](serve/cockpit/tests/test_decisions_integration.py#L146-L248); reviewer rerun was green.
- Independent verification summary: quality-runner reran [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L250-L516), [serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx](serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx#L213-L323), and [serve/cockpit/tests/test_decisions_integration.py](serve/cockpit/tests/test_decisions_integration.py#L146-L248) with 41 tests passing and lint clean; it also reran [serve/cockpit/web/src/__tests__/DRStatusIndicator.test.tsx](serve/cockpit/web/src/__tests__/DRStatusIndicator.test.tsx#L232-L248) and [serve/cockpit/web/src/__tests__/ResolveModal.test.tsx](serve/cockpit/web/src/__tests__/ResolveModal.test.tsx#L180-L196) with 34 tests passing and lint clean.

## Observations
- The current 1649 frontend suite uses DRStatusIndicator and ResolveModal doubles at [serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx](serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx#L64-L113), so the final proof is composite rather than self-contained. That is acceptable here because the complementary durable suites were independently re-verified.
- The current backend suite strongly proves response shape and notes-cap validation, but not every possible Pydantic coercion branch. That is non-blocking because the exercised API contract is green and the route enforces [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py#L95-L131).

[[2026-05-20T11:32:11+02:00]]
## Docs Gate

**Verdict: PASS**

### Checklist

1. **README Verification** — N/A (no docs impact). Task created only test files (`serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx`, `serve/cockpit/tests/test_decisions_integration.py`). Builder confirmed: "Files changed: none" (consolidation verification pass-through). Layer 1: neither `#1649` nor comparable consolidation task `#1673` appear in `serve/cockpit/README.md`; README documents feature implementations, not test-only verification gates. Layer 2: editorial review confirms no new public API, CLI flag, or user-facing behavior was introduced. No README update required.

2. **External Attribution** — N/A. No external sources cited in builder or reviewer notes.

3. **Research Doc** — N/A. No research artifact created for this task.

4. **Deletion Detection** — N/A. No files deleted (Builder Notes confirm "Files changed: none").

### Scratch Cleanup

No `.owlbear/scratch/1649-*` files found — nothing to clean.

[[2026-05-20T11:45:49+02:00]]
## Audit

### Regression Detection
Quality-runner full run: 5202 passed, vitest exit 0, ruff clean. Pytest failures (232+) are pre-existing background debt in unrelated domains (test_cockpit_view.py referencing archived task files, test_server.py MCP kanban, test_engine_accessor_migration.py engine patterns, mcp-knowledge import errors). None involve the cockpit decisions tab domain. Task-scoped tests (34 frontend + backend) all green.

### Intent Verification
Changed files: `serve/cockpit/web/src/__tests__/DecisionsTab.integration.test.tsx` and `serve/cockpit/tests/test_decisions_integration.py`. Both in cockpit domain, matching stated purpose (consolidation integration tests for decisions tab multi-tab infrastructure). No extraneous scope — test-only, no source changes.

### Architect Quality
Score: 4/5. AC has 5 focused lines naming concrete observables (DOM selectors, function calls, HTTP status codes). Challenger findings were incorporated (AC split, convergence precision, post-resolve blind spot, proof-bundle de-escalation). Minor: AC3 is complex enough it could have been 2 lines, but was adequately testable as-is.

### Commit Integrity
Test-writer commit `77f686f6`: properly formatted (`test: add consolidation integration tests for decisions tab (#1649, test-writer)`), scoped to exactly 2 test files (793 insertions). Builder: no commit expected (verification-only pass-through). Review evidence section present and detailed with PASS verdict and independent reruns.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
