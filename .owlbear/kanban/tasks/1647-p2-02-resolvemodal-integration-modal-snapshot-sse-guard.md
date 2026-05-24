---
id: 1647
title: 'P2-02: ResolveModal integration + modal snapshot SSE guard'
status: docs
priority: important
created: 2026-05-18T00:50:17.184817+02:00
updated: 2026-05-20T01:12:00.867228+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1645
ac:
  - Clicking a DR list item in DecisionsPage calls setSelectedDRId with the 
    item's id, which opens the Shell-level ResolveModal with that DR's data — 
    same ResolveModal instance used by DRStatusIndicator
  - DR data is copied into modal-local state when ResolveModal opens; subsequent
    SSE-triggered useDRState() refetches do not update the data displayed in the
    open modal
  - Closing and reopening the modal for the same DR picks up any data changes 
    that occurred while the modal was closed
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-20T01:12:00.867228+02:00
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** DecisionsPage click → ResolveModal wiring via `setSelectedDRId`. Modal snapshot (SSE guard) — DR data copied to modal-local state on open so SSE refetches don't cause involuntary data loss.

**Out:** DR list rendering (P2-01), ResolveModal component changes (minimal — snapshot is modal-local state management).

## Context

ResolveModal currently receives `dr` as a prop from Shell, sourced from `useDRState().selectedDR`. The selectedDR reference updates on SSE refetch. The snapshot guard copies the DR data into component-local state on mount/open, decoupling the modal from live prop updates. Shell already renders ResolveModal at the top level — both DRStatusIndicator and DecisionsPage use `setSelectedDRId` to trigger it.

[[2026-05-20T00:10:11+02:00]]


## Research Summary

See `.owlbear/research/resolve-modal-snapshot-guard.md`

**Key findings:**
- AC1 already implemented (DecisionsPage calls `setSelectedDRId`, shared Shell-level modal)
- AC2+AC3: Use `useState` lazy initializer in ResolveModal — `const [snapshotDR] = useState(() => dr!)` — captures prop at mount, ignores subsequent SSE-driven prop changes. Remount on reopen provides fresh data.
- ~5 LOC change in `ResolveModal.tsx` only. No provider/shell changes needed.
- Confidence: 0.92

[[2026-05-20T00:10:18+02:00]]
## Research

**Findings:** AC1 (DecisionsPage → setSelectedDRId → Shell ResolveModal) already implemented by task #1645. AC2+AC3 require a ~5 LOC snapshot guard in ResolveModal using React's `useState` lazy initializer pattern — captures `dr` prop at mount, ignores SSE-driven prop updates; remount on reopen provides fresh data.

**Approach:** Option A (modal-local useState) selected over provider-level snapshot or useRef. Aligns with brief's "snapshot is modal-local state management" decision. Confidence: 0.92.

**Trade-off matrix:** See `.owlbear/research/resolve-modal-snapshot-guard.md` §3.

**Follow-ups:** None — task is atomic and ready for TDD at backlog. No decomposition needed.

[[2026-05-20T00:20:08+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Snapshot guard in ResolveModal only (~5 LOC) |
| Interface clarity | PASS | AC defines click trigger, snapshot behavior, and reopen behavior |
| Dependency correctness | PASS | #1645 archived/completed; DecisionsPage + setSelectedDRId in place |
| Module layering | PASS | Component-local state, no new imports or upward deps |
| TDD compliance | PASS | Behavioral bundle — test-writer creates RED tests for AC2+AC3 |
| KISS/YAGNI | PASS | useState lazy initializer is simplest solution |
| Premise challenge | PASS | Capability doesn't exist yet; genuine SSE resilience need |
| Pattern consistency | PASS | Standard React useState hook, matches existing component patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend component change only |

### Challenge Results
- Challenger: reconsider (0.69)
- Architect response: rebutted — AC-1 is a single integration flow (B1 pass), proof gaps are for test-writer to fill (behavioral bundle), DR-removal unmount is out of scope (brief frames as form-data loss), snapshot completeness is implementation detail

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Builder Guidance
- Replace ALL `dr` prop reads in ResolveModal with the snapshot (`snapshotDR`), including `handleSubmit`'s `resolveDR(dr.id, ...)` call and the `if (!dr) return null` guard
- The `if (!dr) return null` early return can remain as-is (it fires before useState on first render when Shell passes null) — but after snapshot, rendering should use snapshotDR
- Scope boundary: DR removal from pending list causing modal unmount via Shell conditional rendering is a separate concern — do NOT attempt to solve it in this task

### Verdict: APPROVE
### Action Taken: Approved to todo — AC verifiable, architecture sound, implementation minimal

[[2026-05-20T00:20:12+02:00]]
Architecture review complete. All 10 criteria PASS. Challenger rebutted (0.69 → override). Proof bundle: behavioral confirmed. Advancing to todo.

[[2026-05-20T00:42:17+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx
- Classes: TestFromAC_DecisionsPageModalIntegration, TestFromAC_ModalSnapshotGuard, TestFromAC_ReopenPicksUpChanges
- Tests per category: happy 0, edge 6, error 1, boundary 1 (two AC1+AC2 combined Shell integration, four AC2 unit, one AC3 per-mount boundary)
- Total: 7 tests, all FAIL
- ruff/eslint: clean

**AC coverage:**
| AC | Tests | Status |
|----|-------|--------|
| AC1 (DecisionsPage click → Shell modal) | 2 combined AC1+AC2 Shell integration tests | Covered via combined tests (AC1 path exercised before SSE simulation) |
| AC2 (snapshot SSE guard) | 4 unit + 2 integration = 6 | All FAIL — no snapshot guard in ResolveModal |
| AC3 (reopen picks up changes) | 1 boundary (per-mount snapshot distinctness) | FAILS — combined test: reopen modal, SSE update, still shows mount-time data |

**RED failure reasons:**
- ResolveModal.tsx reads `dr.title` and `dr.body` directly from props (`{dr.title}` in PHeading, `{dr.body ?? ''}` in ReactMarkdown). No `useState(() => dr!)` lazy initializer exists. When the `dr` prop changes (SSE refetch → new selectedDR), the component re-renders with new data, violating AC2.
- Builder must: add `const [snapshotDR] = useState(() => dr!)` in ResolveModal; replace all `dr.` reads in the render body (title, body, submit handler dr.id) with `snapshotDR.`

[[2026-05-20T00:48:59+02:00]]
## Builder Notes
- Files changed: `serve/cockpit/web/src/components/ResolveModal.tsx`
- Implementation summary:
  - Added modal-local snapshot state: `const [snapshotDR] = useState(() => dr)`.
  - Replaced open-modal reads from live prop with snapshot reads (`title`, `body`, submit `id`).
  - Updated submit guard to use snapshot (`if (!snapshotDR || isSubmitting) return`).
  - Snapshot is now per-mount, so SSE prop updates while open do not mutate visible modal data; reopen remount picks up latest DR.

- RED verification (pre-change via quality-runner):
  - `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx`
  - Result: 0 passed / 7 failed (expected), lint clean.

- GREEN verification (post-change via quality-runner):
  - Scoped task proof:
    - Tests: `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx`
    - Result: 7 passed / 0 failed
    - Lint: clean
  - Coverage gate proof (scoped set):
    - Tests: `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx`, `serve/cockpit/web/src/__tests__/PModal.coverage.test.tsx`
    - Result: 69 passed / 0 failed
    - Coverage: `src/components/ResolveModal.tsx` = 100%
    - Lint: clean

- Commit:
  - `eed17cff` — feat: add ResolveModal DR snapshot guard (#1647, builder)

[[2026-05-20T01:10:19+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1647 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: task body includes scoped GREEN proof for `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx` (7 passed), scoped coverage proof across `ResolveModalSnapshot_1647.test.tsx`, `ResolveModal.test.tsx`, and `PModal.coverage.test.tsx` (69 passed, `src/components/ResolveModal.tsx` at 100%), and lint clean. Workspace diagnostics also show no current TypeScript/test-file errors in the changed proof surface.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/pages/DecisionsPage.tsx:39` calls `drState.setSelectedDRId(item.id)` from the DR list item; `serve/cockpit/web/src/Shell.tsx:328` passes `setSelectedDRId` into `DRStatusIndicator`; `serve/cockpit/web/src/Shell.tsx:728-730` renders the shared Shell-level `ResolveModal` with `dr={selectedDR}` and closes via `setSelectedDRId(null)` | Durable click-wiring proof at `serve/cockpit/web/src/__tests__/DecisionsPage_1645.test.tsx:333-345`; task-local integration proof at `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx:229-231` showing click-open of the Shell modal with the selected DR data | PASS |
| AC2 | `serve/cockpit/web/src/components/ResolveModal.tsx:54` snapshots the incoming DR at mount; `serve/cockpit/web/src/components/ResolveModal.tsx:82` submits with `snapshotDR.id`; `serve/cockpit/web/src/components/ResolveModal.tsx:117` guards null snapshot; `serve/cockpit/web/src/components/ResolveModal.tsx:239-240` renders `snapshotDR.title` and `snapshotDR.body`; SSE refetch remains same-id selection via `serve/cockpit/web/src/hooks/CockpitProvider.tsx:68,196` | Integration proof at `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx:249-250` and `:287`; direct modal proof at `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx:319-320`, `:364-365`, and `:384-385` verifies rerenders do not replace the visible snapshot with updated prop data | PASS |
| AC3 | Per-mount snapshot behavior follows from mount-time `useState(() => dr)` at `serve/cockpit/web/src/components/ResolveModal.tsx:54` combined with Shell conditional modal mount at `serve/cockpit/web/src/Shell.tsx:728-730` | Boundary proof at `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx:418-430` verifies reopen picks up the new mount-time DR while ignoring a later in-open rerender | PASS |
- Challenger check required by `behavioral` bundle completed: recommendation was `reconsider`, but only against an initially broader proof-gap theory. After narrowing AC2 to the task’s stated SSE/display contract and same-id selection path, no blocking AC, test-alignment, proof-sufficiency, or safety findings remain.

## Observations
- Non-blocking: `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx:369-385` names the case as preserving the snapshotted id, but the assertions only prove title stability after a different-id prop swap. Current implementation is correct at `serve/cockpit/web/src/components/ResolveModal.tsx:82`; if submit-target stability under broader prop-swap scenarios becomes contractual later, add an explicit post-swap submit assertion to harden that path.
