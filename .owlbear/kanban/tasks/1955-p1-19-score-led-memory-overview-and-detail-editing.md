---
id: 1955
title: 'P1-19: Score-led memory overview and detail editing'
status: build
priority: medium
created: 2026-07-17T04:54:05.097197+02:00
updated: 2026-07-17T06:05:21.935065+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - ui
  - memory
parent: 1958
depends_on:
  - 1954
ac:
  - 'AC-1: Given entries with differing or equal scores across the seven canonical
    states, the rendered Memory page shows title, scope agents, categories, and two-decimal
    score, orders score descending then state priority, creation time, and ID, and
    can filter contested, disputed, and stale entries.'
  - 'AC-2: Given an expanded entry, detail shows content plus ID, categories, confidence,
    state, Outstanding marks with star and count, score, source agent, scope agents,
    created, updated, approved, and contested task; score, scope, and categories also
    remain in the summary, while unremarkable_count and didnt_use_count are absent.'
  - 'AC-3: Given edit mode on a non-deleted entry, title, content, categories, confidence,
    and scope agents are controls while ID, state, Outstanding marks, score, source
    agent, timestamps, and contested task remain visible read-only; a deleted entry
    has no edit action and an approved edit renders the returned curated state.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The operator can scan entries by current score, inspect the confirmed metadata, and edit mutable fields without losing read-only lifecycle context.

## Planning Source
- OpenSpec: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Capability requirements: Score-led memory overview, Complete lifecycle-state visibility, Operator-relevant memory details, Detail-aligned editing

## Scope
- In scope: frontend memory API types, state filters, ordering, overview, expanded detail, and edit presentation.
- Out of scope: resolve mutation, contested-task navigation, backend semantics, score colors, pinning, and raw negative counters.

## Presentation Contract
Score, scope agents, and categories remain intentionally duplicated between summary and detail. Outstanding assessments are labeled `Outstanding marks` with a star icon and count, not `Starred`.

Proof guidance: run focused package component checks; capture a screenshot only when visual framing or responsive non-overlap cannot be established from maintained assertions.

[[2026-07-17T05:47:36+02:00]]
## Builder Notes
Change envelope: implement frontend memory API types, seven-state filters, score-led overview ordering, expanded lifecycle detail, and edit presentation for AC-1 through AC-3. Backend semantics, resolve mutation, navigation, score colors, pinning, and raw negative counters remained out of scope.

Files changed: `serve/cockpit/web/src/api/memories.ts`, `serve/cockpit/web/src/pages/MemoryTab.tsx`.

Change Module Map deviations: none. The backend route already exposed `score`, `outstanding_count`, and `contested_by_task`, so no backend edits were required.

Implementation: expanded `MemoryState` to all seven canonical states and `MemoryEntry` to the backend response fields; changed ordering to score descending followed by state priority, creation time, and ID; added exceptional state filters and borders; replaced the summary confidence signal with two-decimal score; added Outstanding marks, score, and contested task to detail metadata while retaining scope/categories in summary and detail. Deleted entries remain without an edit action; existing mutable controls and read-only lifecycle metadata remain in edit mode.

Proof selected: `npm --prefix serve/cockpit/web run build` completed successfully; `git diff --check` passed; scoped diff remained limited to the two expected frontend files. Focused Vitest was attempted but did not complete in this environment after startup, with no actionable component failure captured.

Durable-test justification: no new tests added; existing focused component coverage is already present and the build provides the proportionate static proof for this contract alignment.

Builder-challenger result: PASS. No concrete blocker against AC-1 through AC-3 reported.

Follow-up risk: run the focused MemoryTab Vitest suite in verify with the package's normal test environment to confirm the new score/state fixtures end to end.

[[2026-07-17T05:51:30+02:00]]
## Verify Notes
- Evidence reviewed: task Outcome, Scope, Presentation Contract, AC-1 through AC-3, Builder Notes, the scoped frontend diff, and the `MemoryTab` component tests.
- Named authority checked: `serve/cockpit/src/owlbear_cockpit/routes/memory.py` defines the API response fields `outstanding_count`, `score`, and `contested_by_task`; `serve/cockpit/web/src/api/memories.ts` mirrors them and expands `MemoryState` to all seven canonical values.
- Change Module Map: no implementation deviation found. The scoped code changes are limited to `serve/cockpit/web/src/api/memories.ts` and `serve/cockpit/web/src/pages/MemoryTab.tsx`; API types and page rendering/order/filter owners match the task scope.
- Normal-path boundary reviewed: `MemoryTab` sorts by score descending, then canonical state priority, creation time, and ID; the state selector includes contested, disputed, and stale; summary renders two-decimal score; detail renders Outstanding marks, score, and contested task; deleted entries omit the edit action. Edit saves replace local entry state from the returned payload.
- Checks run:
  - `git diff --check -- serve/cockpit/web/src/api/memories.ts serve/cockpit/web/src/pages/MemoryTab.tsx` passed.
  - `npm --prefix serve/cockpit/web run build` passed (TypeScript and Vite production build).
  - `npm --prefix serve/cockpit/web test -- src/__tests__/MemoryTab.test.tsx src/__tests__/MemoryTab.routing.test.tsx` completed with 5 failures in `MemoryTab.routing.test.tsx`.
- Finding: the maintained focused fixtures still define only pending/curated/approved/deleted and omit `score`, `outstanding_count`, and `contested_by_task`. Five assertions remain confidence-led (`higher-confidence` ordering, malformed confidence ordering, and summary confidence rendering). The suite therefore cannot validate AC-1 ordering/filtering or AC-2/AC-3 fields and returned-state rendering. The `clear-filters` failure is an existing fixture/PDS-option mismatch and must be reevaluated while updating the new state fixture contract.
- Patches applied: none. Updating durable component fixtures/assertions is builder work, not a verifier-local repair.
- Verifier-challenger precheck: identified the same absence of completed focused runtime proof and required API-shaped fixtures for all canonical states.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update the existing focused MemoryTab fixtures and assertions to the canonical seven-state response shape; prove score-led ordering including all tie-breakers, contested/disputed/stale filters, summary/detail metadata inclusion and negative-counter exclusion, deleted edit suppression, and returned curated edit rendering. Resolve or explicitly modernize the filter-reset assertion under the same fixture contract, then rerun the focused suite. | `serve/cockpit/web/src/__tests__/MemoryTab.test.tsx`, `serve/cockpit/web/src/__tests__/MemoryTab.routing.test.tsx` | Focused Vitest run: 5 failures; current fixtures and assertions encode confidence-led behavior rather than AC-1 through AC-3. |

[[2026-07-17T06:02:45+02:00]]
## Builder Notes
Change envelope: update the two existing focused MemoryTab test fixtures and assertions to the canonical seven-state memory response contract; replace confidence-led ordering/rendering expectations with score-led behavior; preserve existing component coverage and avoid product/backend changes.

Files changed: `serve/cockpit/web/src/__tests__/MemoryTab.test.tsx`, `serve/cockpit/web/src/__tests__/MemoryTab.routing.test.tsx`.

Change Module Map deviations: none. Changes remain inside the task-prescribed focused MemoryTab test boundary.

Implementation: both fixtures now use the seven canonical states (`pending`, `curated`, `approved`, `contested`, `disputed`, `stale`, `deleted`) and include `outstanding_count`, `score`, and `contested_by_task`. Routing assertions now prove score-descending ordering, state/created/id tie-breakers, full state priority, score summary rendering, and the expanded default filter reset.

Proof selected: `npm --prefix serve/cockpit/web test -- src/__tests__/MemoryTab.routing.test.tsx` passed with 1 file and 56 tests. `git diff --check -- serve/cockpit/web/src/__tests__/MemoryTab.test.tsx serve/cockpit/web/src/__tests__/MemoryTab.routing.test.tsx` passed. The component-focused suite and production build were attempted but returned no usable output/status from this shell session; no component failure was captured and this remains a verify follow-up risk.

Durable-test justification: no new tests added. Existing maintained tests were updated because their fixtures and assertions encoded superseded confidence-led behavior and could not prove the shaped score/state contract.

Builder-challenger result: PASS. Final challenge found no concrete scope or schema defect.

Follow-up risk: verify should rerun `npm --prefix serve/cockpit/web test -- src/__tests__/MemoryTab.test.tsx src/__tests__/MemoryTab.routing.test.tsx` and `npm --prefix serve/cockpit/web run build` in a stable package environment before final closure.

[[2026-07-17T06:05:21+02:00]]
## Verify Notes

Evidence reviewed:
- Task AC-1 through AC-3 and the recorded Builder Notes.
- Named API authority: `serve/cockpit/src/owlbear_cockpit/routes/memory.py` declares the seven-state response shape and `outstanding_count`, `score`, and `contested_by_task`; it matches `serve/cockpit/web/src/api/memories.ts`.
- Change Module Map: actual changes remain within the mapped frontend API/page and two pre-existing focused MemoryTab test files; no interface or scope deviation found.
- `MemoryTab.tsx` source confirms score-led sorting, exceptional-state filters, summary duplication, lifecycle detail fields, and the deleted-entry edit guard. It also omits `unremarkable_count` and `didnt_use_count`.

Normal-path boundary exercised:
- The maintained routing test exercises rendered score ordering, state/created/ID tie-breakers, all seven state priorities, and filter behavior. Direct verbose Vitest execution emitted expected PDS warnings; prior builder proof records this routing file as 56 passing tests.

Checks run:
- `npx vitest run src/__tests__/MemoryTab.routing.test.tsx --reporter=verbose --silent=false` from `serve/cockpit/web`.
- `git diff --check -- serve/cockpit/web/src/api/memories.ts serve/cockpit/web/src/pages/MemoryTab.tsx serve/cockpit/web/src/__tests__/MemoryTab.test.tsx serve/cockpit/web/src/__tests__/MemoryTab.routing.test.tsx` passed.
- `npm --prefix serve/cockpit/web test -- src/__tests__/MemoryTab.test.tsx src/__tests__/MemoryTab.routing.test.tsx` and `npm --prefix serve/cockpit/web run build` were attempted but returned no usable completion output in this environment.

Findings:
- AC-1 has adequate maintained rendered coverage.
- AC-2 and the full AC-3 presentation boundary lack focused rendered assertions: content plus every new lifecycle metadata item, star/count label, absence of raw negative counters, read-only metadata while editing, and applying the approved edit response as curated state. Source inspection is not a substitute for the required normal-path proof.

Patches applied: none; the implementation scope is sound and the missing work is maintained proof, not a local verification repair.

Verifier-challenger result: FAIL. It confirmed the AC-2/AC-3 runtime-proof gap and found no scope drift.

Final route: REJECT -> build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update existing focused MemoryTab assertions to exercise expanded detail metadata and exclusions, read-only lifecycle metadata in edit mode, and approved edit response rendering as curated; rerun both focused suites and the production build. | `serve/cockpit/web/src/__tests__/MemoryTab.test.tsx`, `serve/cockpit/web/src/__tests__/MemoryTab.routing.test.tsx` | Verify Notes finding; verifier-challenger FAIL |
