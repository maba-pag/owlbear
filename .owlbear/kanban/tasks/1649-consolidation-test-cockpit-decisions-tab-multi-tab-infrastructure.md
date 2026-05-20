---
id: 1649
title: 'Consolidation test: Cockpit Decisions Tab multi-tab infrastructure'
status: review
priority: needed
created: 2026-05-18T00:50:31.900068+02:00
updated: 2026-05-20T11:03:13.713676+02:00
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
archival_reason:
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

