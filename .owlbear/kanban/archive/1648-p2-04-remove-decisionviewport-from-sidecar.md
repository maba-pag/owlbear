---
id: 1648
title: 'P2-04: Remove DecisionViewport from sidecar'
status: archived
priority: medium
created: 2026-05-18T00:50:17.215196+02:00
updated: 2026-05-20T05:02:22.772840+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1645
ac:
  - DecisionViewport is no longer rendered inside the sidecar aside element — 
    import removed from Shell.tsx, component no longer appears in sidecar DOM
  - 'DRStatusIndicator in the status bar continues to render and its onItemClick callback
    triggers ResolveModal via setSelectedDRId (route-independent Shell-level component;
    parametric multi-route proof deferred to consolidation #1649)'
  - Shell renders without failure when DecisionViewport import is removed — 
    task-scoped test suite passes with no missing-import or render errors
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Remove `DecisionViewport` rendering from the sidecar in Shell.tsx (both mobile and desktop branches). Verify DRStatusIndicator continues working as the secondary entry path.

**Out:** DecisionViewport component file itself is retained (may be reused or deleted later). DR list page (P2-01).

## Context

Shell.tsx currently renders `<DecisionViewport>` inside the sidecar `<aside>` in both the mobile `<p-sheet>` and desktop branches. With the decisions tab providing a dedicated full-page list (P2-01), the sidecar DR list is redundant. DRStatusIndicator in the status bar remains as the secondary entry path — it calls `setSelectedDRId` to open ResolveModal from any route.

[[2026-05-20T01:22:09+02:00]]
## Builder Notes
- Implementation: removed obsolete legacy test file `serve/cockpit/web/src/__tests__/Shell.decision-viewport.test.tsx` that asserted pre-removal DecisionViewport behavior.
- Reason: reviewer required follow-up to align checked-in proof surface with AC-1 after DecisionViewport sidecar removal.
- Tests (quality-runner, scoped): 27 passed, 0 failed, 0 skipped.
  - `src/__tests__/Shell.remove-decision-viewport_1648.test.tsx`
  - `src/__tests__/Shell.callbacks.test.tsx`
- Lint (quality-runner): eslint clean for `src/Shell.tsx` and both scoped test files.
- Coverage (scoped run): `Shell.tsx` 81.93% (no source changes in this retry; change is test cleanup only).
- Additional verification note: first quality-runner rerun mis-scoped to broad suite; reran with explicit frontend/cwd hint and obtained scoped clean result above.
- Commit: `2c7a81ed` — `test: remove obsolete DecisionViewport shell suite (#1648, builder)`.
- Evidence summary: review blocker cleared by deleting contradictory legacy proof file; AC-targeted task test and callback regression proof are green.

[[2026-05-20T01:37:59+02:00]]
## Review Evidence
- Verdict: FAIL
- AC map:
| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | `serve/cockpit/web/src/Shell.tsx:1-28` removes the `DecisionViewport` import and `serve/cockpit/web/src/Shell.tsx:544-734` shows no `DecisionViewport` callsite in either sidecar branch. | `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:178-222` proves no `DecisionViewport` render and zero component calls under default, pending, loading, and error states. | PASS |
| 2 | `serve/cockpit/web/src/Shell.tsx:416` keeps `DRStatusIndicator` wired to `setSelectedDRId`, and `serve/cockpit/web/src/Shell.tsx:611-612` still gates `ResolveModal` from `selectedDR`. | `serve/cockpit/web/src/__tests__/Shell.callbacks.test.tsx:175,214-215` proves the callback chain only at `/`; the task-local AC2 section is comments only at `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:226-230`; the live route set still includes `/`, `/decisions`, and `/memories` at `serve/cockpit/web/src/routes.ts:17,23,30`. | FAIL |
| 3 | `serve/cockpit/web/src/Shell.tsx:1-28` and repeated Shell renders show the sidecar no longer references `DecisionViewport`. | Builder evidence reports scoped frontend tests green and eslint clean in `.owlbear/kanban/tasks/1648-p2-04-remove-decisionviewport-from-sidecar.md:45-52`, and the 1648 suite repeatedly renders Shell. | PASS |
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC-2 | Proof does not lock the explicit `all routes` contract. The task-local 1648 suite leaves AC2 as comments only, the Shell integration proof hardcodes `/`, and the current route table still includes `/memories`, so a route-specific regression could pass the reviewed proof surface. | `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:226-230`; `serve/cockpit/web/src/__tests__/Shell.callbacks.test.tsx:175,214-215`; `serve/cockpit/web/src/routes.ts:17,23,30`; `.owlbear/kanban/tasks/1648-p2-04-remove-decisionviewport-from-sidecar.md:44,52` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC-2 proof so the remaining route contract is explicit, then hand off a follow-up that adds executable Shell-level route coverage for the unproved DRStatusIndicator path instead of relying on comment-only AC2 notes. | `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx`; `serve/cockpit/web/src/__tests__/Shell.callbacks.test.tsx`; `serve/cockpit/web/src/routes.ts`; `.owlbear/kanban/tasks/1648-p2-04-remove-decisionviewport-from-sidecar.md` | `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:226-230`; `serve/cockpit/web/src/__tests__/Shell.callbacks.test.tsx:175,214-215`; `serve/cockpit/web/src/routes.ts:17,23,30`; `.owlbear/kanban/tasks/1648-p2-04-remove-decisionviewport-from-sidecar.md:44,52` |

## Observations
- Adjacent checked-in proof already covers the `/decisions` variant of the Shell-level modal-open path in `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx:178,219,224,229`. The blocker is the remaining route contract, not the core callback chain.
- AC1 implementation looks correct and the prior contradictory legacy suite is gone from `serve/cockpit/web/src/__tests__`.
- No safety or security issues surfaced in this scope.

[[2026-05-20T04:40:58+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Removal of one component from one location |
| Interface clarity | PASS | AC-1 verifies removal, AC-2 verifies preservation of adjacent path |
| Dependency correctness | PASS | #1645 (decisions list page) is archived/completed |
| Module layering | PASS | Shell.tsx owns both rendering paths; no cross-module concerns |
| TDD compliance | PASS | Task-scoped test exists; prior builder cycle completed |
| KISS/YAGNI | PASS | Pure removal — minimal change surface |
| Premise challenge | PASS | DecisionViewport in sidecar is redundant now decisions tab exists |
| Pattern consistency | PASS | Follows Shell component management patterns |
| Security surface | PASS | No new boundaries introduced |
| Single domain | PASS | Frontend/cockpit-web only |

### AC Assessment (Reviewer Follow-up Resolution)
| AC | Original Issue | Resolution |
|---|---|---|
| 1 | None (PASS) | Unchanged |
| 2 | \"all routes\" language was unprovable within task scope | Refined: removed naked quantifier. DRStatusIndicator + ResolveModal render at Shell level outside Routes outlet (Shell.tsx:410-416, 611-612) — route-independent by construction. Shell.callbacks.test.tsx:175,214-215 proves callback chain. Parametric multi-route coverage explicitly deferred to consolidation #1649 AC-2 (\"Entry path convergence\"). |
| 3 | \"no runtime errors\" was broad | Tightened to: task-scoped test suite passes with no missing-import or render errors — mechanically verifiable by test-runner output |

### Architectural Justification for AC-2 Route-Independence
- `Shell.tsx:410-416` renders DRStatusIndicator unconditionally in status bar div
- `Shell.tsx:611-612` renders ResolveModal gated on `selectedDR` state
- Both are outside the `<Routes>` outlet — they do not participate in route matching
- DR state (`selectedDRId`, `setSelectedDRId`) lives in CockpitProvider — route-agnostic
- `Shell.test.tsx:111` shows generic Shell persistence at arbitrary routes
- Consolidation #1649 explicitly tests: \"both DecisionsPage list item click and DRStatusIndicator popover item click open the same Shell-level ResolveModal\"

### Challenge Results
- Challenger: reconsider (0.74)
- Findings: (1) AC-2 proof is partly inferential; (2) AC-3 was broad; (3) pipeline record shows prior FAIL
- Architect response: Rebutted/addressed:
  - (1) Route-independence is topological fact — DRStatusIndicator renders outside Routes outlet. Architectural proof is appropriate for structural assertions. Consolidation #1649 provides the integration backstop.
  - (2) Tightened AC-3 to concrete pass/fail (test suite completes without errors)
  - (3) This review supersedes prior reviewer FAIL by resolving the blocker (AC-2 scoping)
- No consolidation-test-gap: #1649 exists and depends on #1648

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design-diverge: skipped (single-approach removal task)

### Verdict: APPROVE (REFINE + APPROVE)
### Action Taken: Refined AC-2 (removed unprovable \"all routes\" quantifier, documented route-independence), tightened AC-3 (concrete test-runner pass/fail), advanced to todo.

[[2026-05-20T04:46:16+02:00]]
## Test-Writer Notes
- Retry: added AC-2 (7 tests) and AC-3 (2 tests) to `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx`
- Builder skip: test-only retry — all 15 tests pass against current implementation; no source changes needed.
- Commit: `feeab72c` — `test: add AC-2 and AC-3 retry tests for Shell DRStatusIndicator (#1648, test-writer)`

**Test file:** `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx`
**Class:** `TestFromAC_DecisionViewportRemoval`

**Tests per category:**
| Category | Count |
|----------|-------|
| Happy | 3 (AC-2: indicator renders, count reflects DRs, click opens modal) |
| Edge | 3 (AC-2: /decisions route, /memories route; AC-3: pending DRs + no sidecar) |
| Error | 0 (no error paths in refined AC-2/AC-3) |
| Boundary | 3 (AC-2: inside status-bar div, modal absent before click; AC-3: render smoke) |
| Total | 15 (including 6 existing AC-1 tests, all PASS) |

**AC coverage:**
| AC | Tests | Status |
|----|-------|--------|
| AC-1 | ac1 happy ×2, ac1 edge ×2, ac1 error ×1, ac1 boundary ×1 | COVERED |
| AC-2 | ac2 happy ×3, ac2 edge ×2, ac2 boundary ×2 | COVERED (new) |
| AC-3 | ac3 smoke ×2 | COVERED (new) |

**Quality-runner (scoped):** 15 passed, 0 failed, 0 skipped · eslint clean

[[2026-05-20T04:53:05+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1648 -> docs | AC mapped to code and evidence sufficient.
- Builder/test-writer evidence reviewed first: test-only retry with builder skip, scoped quality-runner evidence reports 15 passed, 0 failed, 0 skipped, and eslint clean.
- AC map:
| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | `serve/cockpit/web/src/Shell.tsx:20-23` imports `DRStatusIndicator` and `ResolveModal` with no `DecisionViewport` import, and `serve/cockpit/web/src/Shell.tsx:355-361` marks the canvas `data-no-sidecar` with no sidecar render path. | `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:183-186`, `:194-205`, `:208-216`, and `:219-221` prove no sidecar DOM, no `decision-viewport` DOM, and zero `DecisionViewport` calls across default, loading, pending, and error states; obsolete legacy suite `serve/cockpit/web/src/__tests__/Shell.decision-viewport.test.tsx` is removed. | PASS |
| 2 | `serve/cockpit/web/src/Shell.tsx:368-412` renders `DRStatusIndicator` inside the Shell status bar and wires `onItemClick={setSelectedDRId}`; `serve/cockpit/web/src/hooks/CockpitProvider.tsx:194-196` resolves `selectedDR` from `selectedDRId`; `serve/cockpit/web/src/Shell.tsx:614-621` gates `ResolveModal` on `selectedDR`; route content renders separately under `serve/cockpit/web/src/Shell.tsx:482-514`. | `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:229-231` proves indicator presence at `/`; `:234-237` proves count wiring; `:240-246` proves click-to-open modal at `/`; `:249-251` proves indicator presence at `/decisions`; `:254-260` proves click-to-open modal at `/memories`; `:263-267` proves placement inside the status-bar container; `:270-273` proves the modal is absent before interaction. | PASS |
| 3 | `serve/cockpit/web/src/Shell.tsx:355-621` renders cleanly without any `DecisionViewport` import path, and diagnostics are clean in `Shell.tsx`, the 1648 task test, `routes.ts`, and `CockpitProvider.tsx`. | `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:280-289` provides task-scoped render smoke with and without pending DRs, and the scoped quality-runner result is green (15 passed, 0 failed, 0 skipped; eslint clean). | PASS |
- Blocking findings: none.
- Safety/security: no input-handling, auth, storage, or dependency-risk issues surfaced in this scope.

## Observations
- Challenger result: `proceed` (0.86). The only issues raised were non-blocking: stale header comments in `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx:1-9` still reflect superseded AC wording, and the task-local proof is intentionally Shell-integration-focused with mocked `DRStatusIndicator`/`ResolveModal`.
- The stale AC wording in the test header is proof-artifact drift only; executable assertions align with the refined AC.
- Editor diagnostics are clean for `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx`, `serve/cockpit/web/src/routes.ts`, and `serve/cockpit/web/src/hooks/CockpitProvider.tsx`.

[[2026-05-20T04:56:14+02:00]]
## Docs Gate

**Verdict: PASS**

### Item 1: README Verification
- Mapped `serve/cockpit/web/src/**` changes → `serve/cockpit/README.md`
- Layer 1 grep: no `#1648` entry existed; found two stale references:
  - Missing changelog entry for DecisionViewport sidecar removal
  - "Decision behavior" bullet in Product Boundary section still described the sidecar viewport as the primary DR UX path (pre-#1645/#1648 wording)
- Layer 2 editorial: #1607 historical entry references `PDivider separates sidecar-header from DecisionViewport` — this is a historical task record, not current-state prose; no update needed.
- Fixes applied:
  - Added `- #1648` entry after `#1646` block documenting the removal, retained paths, deleted test suite, and 15-test verification
  - Updated "Decision behavior" bullet to reflect current architecture: `/decisions` tab as primary path, `DRStatusIndicator` → `ResolveModal` as secondary route-independent path
- Commit: `d80d9f0c` — `docs: update cockpit README for DecisionViewport sidecar removal (#1648, doc-writer)`

### Item 2: External Attribution
N/A — no external sources influenced this removal task.

### Item 3: Research Doc
N/A — no research artifact for this task.

### Item 4: Deletion Detection
- Deleted: `serve/cockpit/web/src/__tests__/Shell.decision-viewport.test.tsx` — obsolete legacy proof suite, not referenced in README or any docs target.
- No orphaned references found.

### Scratch Cleanup
No `.owlbear/scratch/1648-*` files found — nothing to clean.

[[2026-05-20T05:02:22+02:00]]
## Audit

### Regression Detection
Quality-runner full report: 2214 passed, 0 failed, 11 skipped. ESLint exit 0. Two pre-existing unused-var warnings in Shell.tsx:75 and SidecarUX.test.tsx:116 — both present before task and not introduced by #1648 commits. Clean.

### Intent Verification
Changed files: Shell.tsx (source removal), task-scoped test, deleted obsolete test suite, cockpit README update. All within `scope:cockpit-web` / frontend domain. No extraneous scope. Implementation matches stated purpose (remove DecisionViewport from sidecar).

### Architect Quality
Score: 3/5 — Original AC-2 used \"all routes\" quantifier that was unprovable within task scope, causing a reviewer FAIL and full pipeline recycle. Architect refined effectively on second pass (route-independence by construction, deferred parametric proof to #1649). Initial gap cost pipeline efficiency.

### Commit Integrity
5 commits in chain: 86fffb60 (test-writer), f9c9f773 (builder feat), 2c7a81ed (builder test cleanup), feeab72c (test-writer retry), d80d9f0c (doc-writer). All deliverables committed. No uncommitted task-scoped files.

### Deductions
| Criterion | Deduction |
|---|---|
| AC quality score = 3 | -.03 |

### Confidence: 0.97 — ARCHIVE
