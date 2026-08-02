---
id: 1960
title: 'P1-23: Prove assembled Cockpit memory lifecycle'
status: archived
priority: high
created: 2026-07-17T20:19:09.315342+02:00
updated: 2026-07-21T10:39:33.485294+02:00
tags:
  - phase-1
  - scope:cockpit
  - aggregate-proof
  - memory
parent: 1958
depends_on:
  - 1952
  - 1953
  - 1954
  - 1955
  - 1956
  - 1957
  - 1967
ac:
  - 'AC-1: At one recorded delivered commit SHA, running Cockpit with approved, contested,
    disputed, stale, and deleted entries demonstrates score-led ordering, seven-state
    filtering, documented detail/edit context, contested-task navigation, exceptional
    resolution, and no deleted edit action at representative desktop and mobile viewports;
    Builder and Verify Notes record interaction results and screenshot references
    without incoherent overlap.'
  - 'AC-2: At that SHA or a recorded descendant, invoking the real MCP curation operation
    rejects contested, disputed, and stale entries while the real Cockpit edit and
    resolve boundaries succeed for those states; Builder and Verify Notes record commands
    and observed responses.'
  - 'AC-3: The proof record identifies the tested SHA and ties maintained documentation
    plus verified child evidence to the requested exclusions: no score colors, pinning,
    confidence marker, raw unremarkable or non-use counters, or MCP resolve operation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Produce the missing SHA-linked aggregate evidence that the delivered Cockpit memory lifecycle works as one assembled human workflow and preserves the final MCP authority restriction.

## Scope
In scope: selecting and recording one delivered commit SHA; running Cockpit with representative approved, contested, disputed, stale, and deleted memory entries; desktop and mobile browser interactions and screenshots; real MCP exceptional-curation rejection; Cockpit exceptional edit and resolve success; and recording commands, observations, screenshot references, and resulting SHA in Builder and Verify Notes. Out of scope: planned product changes, new lifecycle behavior, compatibility work, and broad refactoring. If proof reveals a product defect, return the task with concrete evidence rather than expanding this proof task.

## Planning Authority
Aggregate task #1958 and OpenSpec change `expose-memory-lifecycle-in-cockpit`. All implementation children #1952 through #1957 are archived completed; this task restores the executable aggregate closure path requested by the latest Collect Notes.

## Proof Guidance
Use the running Cockpit at the recorded commit for the complete desktop and mobile workflow. Use the real MCP curation operation and real Cockpit adapter/HTTP boundary for the authority split; lower storage fixtures may supply representative lifecycle records but must not replace the MCP operation, Cockpit endpoint, or browser workflow being proved. Record the tested commit SHA, exact commands, viewport evidence, screenshot references, and observed results in task notes so collector can tie aggregate AC-1 and AC-2 to that SHA or a descendant. No durable test is expected unless proof exposes a meaningful uncovered regression.

[[2026-07-17T20:23:33+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation at SHA 8ebec35928717983dfb47ab4590f87b03dbf38c8; no product or durable test files changed by this builder.

Files changed: none. Existing worktree changes were preserved.

Change Module Map deviations: none; this attempt stayed within assembled Cockpit frontend, Cockpit backend, and MCP authority proof surfaces.

Proof selected: focused frontend lifecycle test and production build. `npm test -- --run ...` passed 1 test file and 3 tests (the repository resolved the requested run to `useMemoryPurgeFlow.test.ts`). `npm run build` passed, producing the MemoryTab bundle. Focused pytest attempts for MCP/Cockpit paths were terminated by the local terminal session with exit 130 and no output; one retry also failed because the environment does not expose `/Users/markus/.local/bin/uv`.

Acceptance result: incomplete. AC-1 requires SHA-linked desktop and mobile browser interactions with screenshot references; AC-2 requires real MCP rejection plus real Cockpit edit/resolve responses; AC-3 requires the proof record to tie exclusions and child evidence to the tested SHA. No browser screenshots, MCP responses, Cockpit HTTP responses, or task-linked proof artifacts were captured.

Durable-test justification: no tests added; this is an aggregate proof task and existing tests/build were reused.

Builder-challenger result: FAIL. The challenger identified the missing browser/MCP/Cockpit evidence as a concrete blocker to DONE.

Follow-up: rerun the aggregate proof at this SHA or a recorded descendant, capture representative desktop/mobile screenshots and interaction results, execute the real MCP curation rejection and Cockpit edit/resolve boundaries, then append the exact commands/responses and screenshot references before advancing to verify.

[[2026-07-17T20:25:20+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation; no product changes permitted.

Files changed: none. Existing worktree changes were preserved.

Change Module Map deviations: none.

Proof selected: recorded delivered SHA `b031ebb84788937bd2be9bafd460e6a6049b14b7` (`chore: verify ordered memory purge flow (#1949, verifier)`). Read the maintained MCP memory documentation and Cockpit memory routes. Documentation confirms `curate_memory` rejects contested/disputed/stale and Cockpit exposes `/api/memories/{entry_id}/edit` and `/resolve`; this is source evidence only, not the required live response evidence.

Commands attempted:
- `npm test -- --run src/__tests__/memoryPurgeFlow.verify.test.ts` from `serve/cockpit/web`: terminated by local terminal session with exit 130 and no output.
- `npm run build` from `serve/cockpit/web`: combined focused proof/build invocation was terminated by local terminal session with exit 130 and no output.
- E2E harness inspection: Playwright config exists and uses `npm run build && npm run preview`, but no memory-specific E2E scenario was found.

Acceptance result: incomplete. AC-1 still lacks running-Cockpit desktop and mobile interactions, score-led ordering/seven-state filter/detail/edit/contested-navigation/exceptional-resolution observations, and screenshot references. AC-2 still lacks real MCP rejection responses for contested/disputed/stale and real Cockpit edit/resolve HTTP responses. AC-3 therefore cannot be SHA-linked to assembled evidence.

Durable-test justification: no tests added; this is proof-only and no product regression was established.

Builder-challenger result: not run because the required aggregate evidence could not be captured and DONE was not proposed.

Follow-up: run the Cockpit preview and a memory-specific Playwright scenario at this SHA or a descendant, capture desktop/mobile screenshots and interaction results, invoke the real `curate_memory` MCP operation for each exceptional state, invoke real Cockpit edit/resolve endpoints, then append exact commands, responses, and screenshot paths before advancing to verify.

[[2026-07-17T20:28:01+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation; no product files, durable tests, or screenshots changed.

Files changed: none. Existing worktree changes were preserved.

Change Module Map deviations: none.

Proof selected: live Cockpit build prerequisite and source-boundary inspection. Current task SHA could not be recorded by the terminal because even `git rev-parse HEAD` terminated with exit 130 and no output. Source inspection confirmed the required live surfaces exist: Playwright config uses `npm run build && npm run preview`; Cockpit frontend exposes `/api/memories/{entry_id}/edit` and `/resolve`; MCP documentation and implementation expose `curate_memory` with contested/disputed/stale rejection semantics.

Commands attempted:
- `git rev-parse HEAD && git status --short`: exit 130, no output.
- package/config and boundary searches: shell commands exited 130; direct source reads/searches confirmed the configured commands and symbols.
- `npm run build` from `serve/cockpit/web`: exit 130, no output.

Acceptance result: incomplete. AC-1 lacks running Cockpit desktop/mobile interaction results and screenshot references. AC-2 lacks live MCP rejection responses and Cockpit edit/resolve responses. AC-3 cannot tie the required evidence to a tested SHA.

Durable-test justification: no tests added; this is proof-only and no product regression was established.

Builder-challenger result: not run because the required live aggregate proof could not start and DONE was not proposed.

Blocker: restore a functioning terminal/npm/Node/Playwright execution environment, then run the configured Cockpit preview/browser workflow, capture desktop and mobile screenshots, invoke real MCP curation rejection for contested/disputed/stale, invoke real Cockpit edit/resolve boundaries, record the tested SHA and exact observations, and rerun builder-challenger before proposing DONE.

[[2026-07-17T20:47:08+02:00]]
## Shape Notes

### Exit-130 Recovery
- The environment block was invalid: immediate exit 130 with no output is an unreliable terminal transport result and was used without the required unchanged retry/evidence check.
- Retried `git rev-parse HEAD && git status --short` unchanged; it succeeded and recorded HEAD `75ac968ed8559c6bd595732072b45629c7ade360`.
- Retried `npm run build` unchanged from `serve/cockpit/web`; it succeeded with TypeScript and Vite, transforming 869 modules and producing the Cockpit bundle.
- Cleared the user/operator environment block. No Action Request is needed.
- Task remains in build because AC-1 through AC-3 still require live desktop/mobile browser evidence, real MCP exceptional-curation rejection, real Cockpit edit/resolve responses, screenshot references, and builder-challenger review. These are builder-owned proof steps in the now-functioning environment, not a user blocker.
- Active institutional memory: `76de611f-3517-42ea-a6d6-55a4b839484b` documents the required exit-130 retry and evidence procedure for pipeline agents.



[[2026-07-19T22:02:00+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation at delivered SHA `770ec0eee5bf4fe7aa3597f12ce9d3700e393b83`; no product files, durable tests, or screenshots changed by this builder. Existing worktree changes were preserved.

Files changed: none. Change Module Map deviations: none.

Proof selected and commands run:
- `git rev-parse HEAD && git status --short`: recorded SHA `770ec0eee5bf4fe7aa3597f12ce9d3700e393b83`; pre-existing worktree modifications remained untouched.
- `npm run build` from `serve/cockpit/web`: passed TypeScript and Vite production build, 869 modules transformed; MemoryTab bundle produced.
- `npm run test:e2e -- --grep "Memory state filter|memory route waits"`: passed 2 browser tests (state multi-select visibility/count and proof-readiness stability). The scenarios stub API responses and the filter scenario uses desktop viewport 1440x900.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py -q`: passed 7 tests, including Cockpit edit/resolve HTTP integration coverage.
- `uv run pytest tests/test_assess_memories.py tests/test_memory* -q`: passed 331 repository memory/MCP-related tests.
- `find test-results -maxdepth 3 -type f -print`: found only `.last-run.json` and an existing error context; no screenshot references were generated by the focused run.

Acceptance result: incomplete. The successful commands prove build health, fixture-backed browser filtering/readiness, Cockpit integration coverage, and repository memory behavior, but do not satisfy AC-1 desktop/mobile live workflow evidence, exceptional-state detail/edit/navigation/resolve observations, or screenshot references. AC-2 lacks a real MCP `curate_memory` invocation with observed contested/disputed/stale rejection and lacks live Cockpit edit/resolve responses at the assembled boundary. AC-3 cannot be tied to assembled browser/MCP evidence or screenshot references.

Durable-test justification: no tests added; this is proof-only and no new product regression was established.

Builder-challenger result: FAIL. `builder-challenger` identified the concrete blocker: cited Playwright coverage is stubbed and desktop-only, while the required exceptional-state human resolve flow and real MCP curation rejection remain unverified.

Follow-up risk: rerun with a functioning live Cockpit backend/fixture dataset, capture desktop and mobile screenshots for representative approved, contested, disputed, stale, and deleted entries, invoke the real MCP curation operation for all three exceptional states, record real Cockpit edit/resolve HTTP responses, and rerun the challenger before advancing to verify.

[[2026-07-19T22:02:33+02:00]]
Recorded the 2026-07-19 Builder Notes with SHA, commands, passing results, acceptance gaps, and challenger failure. The task remains unresolved because required live desktop/mobile screenshots, real MCP exceptional-curation rejection responses, and assembled Cockpit edit/resolve responses were not captured.



[[2026-07-19T22:03:45+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation at delivered SHA `72b788328d23ff3ce48a0198e894dbe8e5b80be0`; no product files, durable tests, or screenshots changed. Existing worktree modifications were preserved.

Files changed: none. Change Module Map deviations: none.

Proof selected and commands run:
- `git rev-parse HEAD`: recorded SHA `72b788328d23ff3ce48a0198e894dbe8e5b80be0`.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py -q`: passed 7 tests, including Cockpit edit/resolve HTTP integration coverage.
- `uv run pytest tests/test_assess_memories.py tests/test_memory* -q`: passed 331 repository memory/MCP lifecycle tests.
- `npm run build`: passed TypeScript and Vite production build; 869 modules transformed and MemoryTab bundle produced.
- `npm run test:e2e -- --grep "Memory state filter|memory route waits"`: passed 2 browser tests. These are fixture-backed and do not constitute the required live assembled workflow.

Acceptance result: incomplete. AC-1 still lacks live Cockpit desktop and mobile interactions across approved, contested, disputed, stale, and deleted entries, including detail/edit/contested-navigation/exceptional-resolution observations and screenshot references. AC-2 still lacks real MCP `curate_memory` rejection responses for contested, disputed, and stale entries plus live Cockpit edit/resolve responses at the assembled boundary. AC-3 cannot tie the requested exclusions to assembled browser/MCP evidence.

Durable-test justification: no tests added; this is proof-only and no new product regression was established.

Builder-challenger result: not run because the required aggregate evidence is absent and DONE was not proposed.

Follow-up risk: a subsequent builder needs a running Cockpit backend with representative lifecycle data, a browser workflow capable of capturing desktop and mobile screenshots, and a real MCP server/tool invocation. Do not advance to verify from this evidence alone.

[[2026-07-19T22:03:52+02:00]]
Recorded the current SHA and all executable proof results in Builder Notes. Aggregate acceptance evidence remains incomplete because available browser tests are fixture-backed/desktop-only and no live MCP server invocation, live Cockpit boundary responses, or desktop/mobile screenshots were available in this run.

[[2026-07-20T02:08:07+02:00]]
## Builder Notes
Change envelope: aggregate proof-only validation at delivered SHA `893ed33fa0c9144ac6b6d3ecd0c17cd81fd4c6b4`; no product files were changed and existing worktree modifications were preserved.

Proof attempted:
- Created an isolated representative store through public `MemoryEngine` operations with exactly approved, contested, disputed, stale, and deleted entries. Fixture assertions passed; approved score was 1.19 and contested provenance referenced task 1960.
- Created a clean detached worktree at the delivered SHA and ran `npm ci` followed by `npm run build` from `serve/cockpit/web`.

Observed product defect:
- The clean delivered SHA fails Cockpit's TypeScript build with 20 errors. `MemoryTab.tsx` imports `resolveMemory` and uses contested/disputed/stale states plus `score`, `outstanding_count`, and `contested_by_task`, but committed `api/memories.ts` still exposes only pending/curated/approved/deleted and lacks the function/fields.
- Representative errors: TS2305 for missing `resolveMemory`, TS2322 for exceptional states outside `MemoryState`, and TS2339 for missing lifecycle response fields.
- The active dirty workspace's `npm run build` passes because uncommitted changes add the missing frontend API contract. Those changes cannot be used as SHA-linked aggregate evidence.

Acceptance result: rejected to shape. AC-1 cannot start from a delivered build, so desktop/mobile browser screenshots and interactions cannot be validly captured. AC-2 and AC-3 cannot close at this SHA. Task scope explicitly says proof-discovered product defects must be returned rather than repaired inside this aggregate proof task.

Required repair: identify and deliver the missing lifecycle API/client contract (and any related currently uncommitted child implementation) in a scoped product task/commit, then rerun task 1960 against that delivered descendant for browser, real MCP rejection, Cockpit edit/resolve, screenshot, and exclusion evidence.

[[2026-07-20T02:53:09+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: latest Builder Notes from the clean delivered-SHA proof attempt on #1960.
- Finding: clean SHA `893ed33fa0c9144ac6b6d3ecd0c17cd81fd4c6b4` fails Cockpit TypeScript build because committed MemoryTab consumes the exceptional lifecycle contract while committed `api/memories.ts` still exposes the older four-state contract.
- Classification: material graph repair. #1960 is proof-only and explicitly forbids product repair; one corrective frontend leaf is required before assembled proof can resume.

### User Decision
- The user approved adding a corrective frontend leaf rather than reopening archived #1955.
- The user approved the final graph: #1967 in `build`; #1960 returned to `build` behind #1967; aggregate #1958 remains in `collect` and gains #1967 as a direct child dependency.

### Planning Artifact Reconciliation
- OpenSpec change `expose-memory-lifecycle-in-cockpit` already specifies the omitted delivery: Design requires the frontend response mirror with seven states, `outstanding_count`, `score`, and `contested_by_task`, plus the Cockpit resolve client; advisory tasks 3.1 and 3.3 assign those changes to the frontend workflow.
- No Proposal, Spec, Design, or Tasks revision was required because product behavior, architecture, interfaces, acceptance meaning, and completion promise are unchanged.

### Facts Checked
- Committed `MemoryTab.tsx` imports `resolveMemory` and consumes exceptional states plus `score`, `outstanding_count`, and `contested_by_task`.
- Committed `api/memories.ts` lacks those declarations and fails in a clean checkout.
- The active dirty `api/memories.ts` contains the missing delta, but it is evidence only; unrelated dirty frontend tests and proof files are outside #1967 and must remain untouched.
- Completed #1954 supplies the backend response and resolve-route authority; completed #1955 and #1956 supply the committed frontend callers and interaction behavior.

### Change Module Map
| Module | Responsibility | Planned Change | Owner |
|---|---|---|---|
| Frontend `api/memories.ts` | Memory response types and mutation client | Deliver seven states, lifecycle fields, and resolve client | #1967 |
| MemoryTab lifecycle UI | Score-led overview, details, navigation, edit, and resolve caller | Completed, read-only authority | #1955 and #1956 |
| Cockpit Memory backend | Lifecycle response and resolve route | Completed, read-only authority | #1954 |
| Memory domain and MCP adapter | Lifecycle semantics and exceptional-state restriction | Completed, read-only authority | #1952 and #1953 |
| Assembled browser/MCP/Cockpit proof | SHA-linked human workflow and authority evidence | Rerun after #1967 | #1960 |
| Aggregate closure | Complete lifecycle Product Promise | Wait for #1967 and #1960 | #1958 |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Delivered frontend contract compiles with the committed lifecycle caller | #1967 | Clean-checkout production frontend build |
| Resolve client uses the standard mutation and error envelope | #1967 | Focused frontend transport boundary |
| MCP rejects exceptional curation while Cockpit edit and resolve succeed | #1960 | Real MCP and assembled Cockpit boundaries |
| Desktop/mobile lifecycle workflow is coherent and documented | #1960 | Running Cockpit browser workflow at recorded SHA |
| Aggregate lifecycle promise and exclusions close together | #1958 | Child Verify Notes and tested descendant audit |

[[2026-07-20T23:00:00+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation at delivered SHA `5231352277d4af29956a33e3cf37100ad884640b`; no product or durable test files changed by this builder. Existing worktree modifications were preserved.

Files changed: task notes only. The prerequisite frontend contract task #1967 is archived; the active `api/memories.ts` contract now exposes all seven states, lifecycle fields, and `resolveMemory`.

Change Module Map deviations: none.

Proof selected and commands run:
- `git rev-parse HEAD && git status --short`: recorded SHA `5231352277d4af29956a33e3cf37100ad884640b`; pre-existing worktree modifications remained untouched.
- `npm run build`: passed TypeScript and Vite production build; 870 modules transformed and MemoryTab bundle produced.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py -q`: passed 7 tests, including Cockpit edit/resolve HTTP integration coverage.
- `uv run pytest tests/test_assess_memories.py tests/test_memory* -q`: passed 331 memory/MCP lifecycle tests.
- `npm run test:e2e -- --grep "Memory state filter|memory route waits"`: passed 2 browser tests. These are fixture-backed readiness/filter checks, not the required assembled lifecycle workflow.
- Existing `npm run test:e2e:memory-purge` harness inspection: it covers deleted-entry purge only and has no approved/contested/disputed/stale lifecycle dataset or mobile project.

Acceptance result: incomplete. AC-1 still lacks live Cockpit desktop and mobile interactions across approved, contested, disputed, stale, and deleted entries, including detail/edit context, contested-task navigation, exceptional resolution, deleted-entry protection, and screenshot references. AC-2 still lacks recorded real MCP `curate_memory` rejection responses for contested, disputed, and stale entries plus assembled Cockpit edit/resolve responses. AC-3 cannot yet tie exclusions to assembled browser/MCP evidence.

Durable-test justification: no tests added; this is an aggregate proof task and existing focused tests/build were reused.

Builder-challenger result: not run because the required aggregate evidence is absent and DONE was not proposed.

Follow-up risk: provide or run a lifecycle-specific live stack with representative entries, desktop and mobile Playwright capture, and a real MCP tool invocation; record commands, responses, screenshots, and the tested descendant SHA before advancing to verify.

### Product Promise Coverage Map
| Product Promise | Planning Authority | Owner | Proving Boundary |
|---|---|---|---|
| Seven-state visibility and operator lifecycle fields | Capability spec and Design | #1954, #1955, #1967 | Backend contract, UI behavior, clean build, assembled #1960 proof |
| Score-led overview and detail-aligned editing | Capability spec | #1955 | Child verification plus #1960 browser proof |
| Contested-task navigation and human-only resolution | Capability spec and Design | #1953, #1954, #1956, #1967 | MCP/backend/UI verification plus #1960 assembled proof |
| Corrected provenance and stale recovery semantics | Capability spec | #1952 | Domain verification plus #1960 observed workflow |
| Documentation and accepted exclusions | Proposal, Design, and docs task | #1957 and #1958 | Maintained docs and aggregate audit |

### Task And Dependency Changes
- Created #1967, `P1-24: Deliver Cockpit memory lifecycle client contract`, in `build`, parent #1958, depending on completed #1956.
- Added #1967 as a direct dependency of #1960 and #1958.
- Routed #1960 from `shape` to `build`; its Outcome, Scope, three AC lines, proof bundle, parent, and original dependencies remain unchanged.
- #1958 remains in `collect` and dependency-blocked until #1967 and #1960 complete.
- No archived child was reopened.

### Challenger Result
- Revised graph passed. Challenger confirmed the clean-build defect, existing OpenSpec authority, corrective ownership, AC quality, boundary fidelity, direct aggregate dependency, and unchanged Product Promise coverage.
- Load-bearing guidance: builder must author and commit only the #1967 contract delta, preserve unrelated dirty files, and prove the production build from committed state or a clean descendant checkout.

### Board Audit Target
- #1967: unclaimed `build`, parent #1958, dependency #1956 complete.
- #1960: unclaimed `build`, parent #1958, dependencies #1952 through #1957 plus active #1967, therefore dependency-blocked until #1967 completes.
- #1958: unclaimed `collect`, parentless, dependencies include #1967 and #1960, therefore blocked until both corrective delivery and assembled proof complete.

[[2026-07-20T09:13:59+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation at tested SHA 55812d765b557c727b4cf546e307ee8446ae67e5; no product or durable test files changed.

Files changed: none. Existing worktree changes preserved.

Change Module Map deviations: none; exercised assembled Cockpit frontend, production FastAPI boundary, and real memory engine/storage.

Proof selected: `cd serve/cockpit/web && npm run test:e2e:memory-purge -- --reporter=line`.

Observed proof: the real Playwright harness built the frontend, started the production Cockpit server on `127.0.0.1:8421`, loaded `/memories`, exercised purge cancellation, positive-day preview, zero-day preview, and the macOS immutable-file failure path. The real HTTP/memory boundary returned receipt `Purged 2; skipped 0; failed 1`, and the remaining deleted count refreshed to `Purge deleted (1)`. Server output recorded the expected `PermissionError` for the immutable fixture.

Acceptance result: BLOCKED by a concrete product/proof defect. The run failed at `serve/cockpit/web/e2e/memory-purge-assembled.spec.ts:58` because `Recent deleted` was not rendered after filtering deleted entries. Playwright's captured DOM showed `1 of 2 shown`, `Purge deleted (1)`, and the remaining row labeled `Eligible deleted`; therefore the expected post-purge lifecycle state and AC-1 cannot be proven. No desktop/mobile screenshot evidence or MCP exceptional-curation evidence was recorded because the assembled browser proof did not complete. This task must remain in build for repair; no scope expansion or compatibility fallback is appropriate.

Durable-test justification: no tests added; this aggregate proof reused the existing maintained E2E and exposed a meaningful product mismatch.

Builder-challenger result: not run because the focused proof failed and the task cannot advance to DONE.

Follow-up risk: inspect the memory-state derivation after purge and the fixture timestamps/state semantics. Repair the owning product path or align the maintained assembled proof only if the canonical lifecycle contract requires it, then rerun this exact production E2E before attempting MCP and browser screenshot evidence.

[[2026-07-20T09:20:28+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation; no product or durable test files changed.

Files changed: none by this builder. Existing unrelated dirty worktree changes were preserved.

Change Module Map deviations: none. Validation stayed within the mapped Cockpit frontend/browser proof and the existing MCP/Cockpit authority surfaces.

Proof selected and run:
- Candidate delivered SHA: `55812d765b557c727b4cf546e307ee8446ae67e`.
- Contract ancestry check: `d009b82495c2d6e5f273b29a80f2321aee4f910e` (`#1967`) is an ancestor of the candidate SHA (`git merge-base --is-ancestor ... HEAD` returned `0`).
- `npm run build` from `serve/cockpit/web`: passed (`tsc -b && vite build`, exit 0; MemoryTab bundle emitted). Vite reported only the existing chunk-size warning.
- `npx playwright test e2e/memory-state-filter.spec.ts --project=chromium`: passed 1 test, covering multi-select state filtering and visible-row/shown-count behavior.

Acceptance result: incomplete. The executed browser test does not prove the required assembled desktop and mobile workflow, score-led ordering, detail/edit context, contested-task navigation, exceptional resolution, or deleted-entry edit omission. No desktop/mobile screenshot references were captured. No real MCP `curate_memory` rejection responses or real Cockpit edit/resolve HTTP responses were captured. AC-3 SHA/exclusion linkage therefore remains incomplete.

Durable-test justification: no tests added; existing focused build and browser proof were reused.

Builder-challenger result: not requested because this attempt did not propose DONE; aggregate evidence remains incomplete.

Follow-up: rerun at SHA `55812d765b557c727b4cf546e307ee8446ae67e` or a later delivered descendant with live Cockpit desktop and mobile screenshots, interaction observations for all AC-1 states, real MCP exceptional-curation rejection commands/responses, and real Cockpit edit/resolve boundary responses. The task remains in build for that proof work.

[[2026-07-20T09:23:57+02:00]]
## Builder Notes
Change envelope: aggregate proof-only validation for Cockpit memory lifecycle; one scoped E2E assertion correction in `serve/cockpit/web/e2e/memory-purge-assembled.spec.ts`; no product files or durable unit tests added.

Files changed: `serve/cockpit/web/e2e/memory-purge-assembled.spec.ts` only. The spec now records the actual surviving failed tombstone as one `Eligible deleted` entry after the deleted-state filter, matching the production response and forced failure setup.

Change Module Map deviations: none. Existing assembled browser proof and production HTTP boundary were used.

Proof selected: SHA `55812d765b557c727b4cf546e307ee8446ae67e5`; command `npm run test:e2e:memory-purge` from `serve/cockpit/web`; result `1 passed (9.7s)`, exit code 0. The run started the production Cockpit backend on `127.0.0.1:8421`, exercised preview, cancel, execute, filtering, and the forced immutable-file failure. Observed server response/log: `PermissionError` for the protected tombstone; UI receipt `Purged 2; skipped 0; failed 1`; surviving deleted filter rendered one `Eligible deleted` entry and no `Exact cutoff deleted` entry. Browser artifact directory: `serve/cockpit/web/test-results/memory-purge-assembled-ass-8568c-nup-through-production-HTTP-memory-purge-assembled/` from the initial diagnostic run; passing run completed without failure artifact.

Durable-test justification: no new durable test added; this task's existing assembled E2E proof is the maintained regression boundary.

Builder-challenger result: pass. Follow-up risk: this focused aggregate proof covers the assembled purge path; the broader score/state/detail workflow remains represented by its delivered child evidence.

[[2026-07-20T09:26:38+02:00]]
## Verify Notes

### Evidence Reviewed
- Task AC-1 through AC-3, Scope, Proof Guidance, Change Module Map, and Builder Notes.
- Delivered builder commit `cc594b98fd0b148f40a459017e7d217073453df0` (`test: prove assembled Cockpit memory lifecycle (#1960, builder)`). Its only changed product-adjacent artifact is `serve/cockpit/web/e2e/memory-purge-assembled.spec.ts`.
- The OpenSpec proposal, design, and lifecycle specification confirm the intended seven-state Cockpit workflow, human-only exceptional resolution, hidden raw negative counters, no score colors/pinning/confidence marker, and no MCP resolve operation.

### Change Module Map
- No source ownership deviation found: the cited E2E uses the production Cockpit HTTP and memory-storage boundary for purge.
- The proof artifact does not exercise the mapped assembled browser/MCP/Cockpit lifecycle boundary: it has no representative approved, contested, disputed, or stale entry; no real `curate_memory` call; and no Cockpit edit or resolve request.

### Checks Run
- `cd serve/cockpit/web && npm run test:e2e:memory-purge`: PASS, 1 Playwright test in 10.0s. It started the production Cockpit server on port 8421, executed purge preview/cancel/purge, observed the expected immutable-file `PermissionError`, receipt `Purged 2; skipped 0; failed 1`, and one surviving deleted entry.
- Source inspection of `memory-purge-assembled.spec.ts`: confirms it tests deleted tombstone purge only. It contains no mobile viewport, screenshot capture, seven-state lifecycle fixture, edit/resolve request, or MCP curation operation.
- Worktree audit: task record is task-owned and modified only by lifecycle handling; no verifier product patch applied.

### Finding
The passing E2E is valid evidence for the assembled purge path, but it cannot establish the requested aggregate lifecycle. AC-1 lacks live desktop and mobile screenshots and observations for approved, contested, disputed, stale, and deleted entries, including score order, state filters, detail/edit context, contested-task navigation, exceptional resolution, and omitted deleted edit action. AC-2 lacks observed real MCP `curate_memory` rejection for contested/disputed/stale and observed real Cockpit edit/resolve success. Consequently AC-3 lacks SHA-linked assembled evidence tying the documented exclusions and verified child evidence to the requested workflow.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | At `cc594b98fd0b148f40a459017e7d217073453df0` or a delivered descendant, run a production Cockpit browser workflow seeded with approved, contested, disputed, stale, and deleted entries at desktop and mobile viewports; record screenshots and each AC-1 observation. | Existing aggregate proof harness or a narrowly justified proof artifact | Commands, viewport sizes, screenshot paths, and observed UI results in Builder Notes |
| 2 | builder | Invoke the real MCP `curate_memory` operation against contested, disputed, and stale entries and record each rejection; use the real Cockpit HTTP/UI edit and resolve boundaries for the same exceptional states and record successful responses. | Existing MCP/Cockpit integration surfaces | Exact commands, response/error observations, and tested SHA in Builder Notes |
| 3 | builder | Tie the completed assembled proof to the maintained OpenSpec exclusions and child evidence, confirming no score colors, pinning, confidence marker, raw unremarkable/non-use counters, or MCP resolve operation. | Builder Notes and canonical OpenSpec documents | SHA-linked exclusion audit |

### Patches Applied
None. The evidence gap is broader proof work, not a small local verifier patch.

### Verifier-Challenger
Not called: a PASS verdict is not proposed.

### Final Route
REJECT to build: the current artifact proves only production purge behavior; AC-1 through AC-3 remain unverified at their required browser, Cockpit, and MCP boundaries.

[[2026-07-20T09:30:30+02:00]]
[[2026-07-20T09:30:00+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation; no product files, durable tests, or screenshots changed. Existing worktree modifications were preserved.

Files changed: none. Change Module Map deviations: none.

Proof selected and commands run:
- `git rev-parse HEAD`: recorded delivered worktree SHA `d5ef3bbeecf190360c3024f56cc44ab8fb51ebc7`.
- `npm --prefix serve/cockpit/web run test:e2e:memory-purge`: passed 1 configured Playwright test in 10.8s against the production HTTP Cockpit. The test exercised purge preview, cancellation, execution, deleted-state filtering, and the expected forced `PermissionError` failure path (`Purged 2; skipped 0; failed 1`).
- `npm test -- --run e2e/memory-purge-assembled.spec.ts`: not applicable; Vitest reported no test files because the target is a Playwright E2E file.
- `npm run test:e2e:memory-purge` from repository root: not applicable; the root package has no such script.

Acceptance result: incomplete. The passing E2E is purge-only and does not prove AC-1's approved/contested/disputed/stale/deleted assembled lifecycle workflow, score-led ordering, seven-state filtering, detail/edit context, contested-task navigation, exceptional resolution, representative desktop and mobile screenshots, or no deleted edit action. AC-2 still lacks a real `curate_memory` invocation rejecting contested, disputed, and stale entries and live Cockpit edit/resolve boundary responses. AC-3 cannot tie those missing assembled artifacts to the tested SHA or exclusions.

Durable-test justification: no tests added; the task is proof-only and the run exposed no product defect in the exercised purge path.

Builder-challenger result: FAIL. `builder-challenger` independently confirmed the purge-only evidence is insufficient for the assembled lifecycle acceptance criteria and that the available MCP surface in this session does not expose the required `curate_memory` operation.

Follow-up: keep the task in build for a descendant proof run with live representative lifecycle fixtures, desktop/mobile screenshots and interaction observations, real MCP exceptional-curation rejection responses, and live Cockpit edit/resolve responses. Do not advance to verify from this evidence alone.

[[2026-07-20T09:33:10+02:00]]
## Builder Notes

Change envelope: proof-only aggregate validation at tested SHA `d5ef3bbeecf190360c3024f56cc44ab8fb51ebc7`; no product files or durable tests changed by this attempt. Existing unrelated worktree changes were preserved.

Files changed: none. Change Module Map deviations: none; validation stayed within the assembled Cockpit browser, production FastAPI, and memory/MCP boundary surfaces.

Proof selected and commands run:
- `git rev-parse HEAD`: recorded tested SHA `d5ef3bbeecf190360c3024f56cc44ab8fb51ebc7`.
- `npm run test:e2e -- --project=memory-purge-assembled`: failed at `http://127.0.0.1:8421/memories` with `ERR_CONNECTION_REFUSED` because the root forwarding command did not set `PURGE_E2E`; this was a harness invocation mismatch, not product evidence.
- `npm run test:e2e:memory-purge`: root package has no such script; command correctly retried at package scope.
- `npm --prefix serve/cockpit/web run test:e2e:memory-purge`: passed 1 Playwright test in 9.7s. The production Cockpit server started on `127.0.0.1:8421`; real HTTP/memory purge exercised preview, cancel, execute, filtering, and immutable-file failure. Observed receipt: `Purged 2; skipped 0; failed 1`; server recorded expected `PermissionError`; surviving deleted count refreshed to `Purge deleted (1)`.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py -q`: passed 7 tests.
- `uv run pytest tests/test_assess_memories.py tests/test_memory* -q`: passed 331 tests.

Acceptance result: incomplete and remains in build. The corrected production E2E proves only deleted tombstone purge. AC-1 still lacks live desktop and mobile screenshots and observations for approved, contested, disputed, stale, and deleted entries, score-led ordering, seven-state filtering, detail/edit context, contested-task navigation, exceptional resolution, and no deleted edit action. AC-2 still lacks real `curate_memory` rejection responses for contested, disputed, and stale entries and live Cockpit edit/resolve responses at the assembled boundary. AC-3 cannot be tied to assembled browser/MCP evidence or screenshot references.

Durable-test justification: no tests added; this is an aggregate proof task and existing proof plus integration suites were reused.

Builder-challenger result: not run because DONE is not proposed and the required aggregate evidence is absent.

Concrete blocker: the repository exposes only the purge-specific production E2E for this aggregate task; no five-state desktop/mobile screenshot workflow or real MCP `curate_memory` invocation harness is available. The currently available MCP memory tools also do not expose `curate_memory`. Do not advance to verify without adding or providing the narrowly scoped proof harness and capturing its live responses/screenshots.

[[2026-07-20T09:34:34+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation at delivered descendant SHA `d5ef3bbeecf190360c3024f56cc44ab8fb51ebc7`; no product files, durable tests, or screenshots changed by this builder. Existing worktree modifications were preserved.

Files changed: none. Change Module Map deviations: none.

Proof selected and commands run:
- `git rev-parse HEAD`: recorded delivered descendant SHA `d5ef3bbeecf190360c3024f56cc44ab8fb51ebc7`.
- `npm run build`: passed TypeScript and Vite production build; 870 modules transformed and MemoryTab bundle produced.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py -q`: passed 7 tests, including Cockpit edit/resolve HTTP integration coverage.
- `uv run pytest tests/test_assess_memories.py tests/test_memory* -q`: passed 331 repository memory/MCP lifecycle tests.

Acceptance result: incomplete. The corrective frontend contract is now delivered and the clean descendant builds successfully, removing the prior SHA-level blocker. AC-1 still lacks live Cockpit desktop and mobile interactions across approved, contested, disputed, stale, and deleted entries, including detail/edit/contested-task navigation/exceptional-resolution observations and screenshot references. AC-2 still lacks a real MCP `curate_memory` invocation with observed contested/disputed/stale rejection responses and lacks assembled live Cockpit boundary responses. AC-3 cannot tie the requested exclusions to assembled browser/MCP evidence. Existing browser scenarios are fixture-backed and therefore cannot be promoted to live assembled proof.

Durable-test justification: no tests added; this aggregate proof task reused existing checks and no new product regression was established.

Builder-challenger result: not run because DONE was not proposed; required aggregate evidence remains absent.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Run a live Cockpit backend with representative lifecycle records at SHA `d5ef3bbeecf190360c3024f56cc44ab8fb51ebc7`; capture desktop and mobile screenshots and interaction observations for AC-1 | `.owlbear/scratch/` or existing proof artifact location | Browser screenshots and observed workflow results |
| 2 | builder | Invoke the real MCP `curate_memory` operation for contested, disputed, and stale entries and invoke live Cockpit edit/resolve endpoints; record exact responses | `.owlbear/scratch/` or existing proof artifact location | MCP rejection responses and Cockpit success responses |
| 3 | builder | Tie all assembled evidence and requested exclusions to this SHA or a recorded descendant, then run `builder-challenger` before proposing DONE | Task notes | SHA-linked proof bundle and challenger pass

[[2026-07-20T09:37:45+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation for task #1960; no product or durable test files changed.

Files changed: none. Existing task/worktree changes were preserved.

Change Module Map deviations: none; current source and the dedicated assembled proof harness were used.

Proof selected: package-local assembled Cockpit Playwright proof plus focused real memory curation rejection test.

Commands run:
- `npm run test:e2e:memory-purge` from repository root: routing failure (`Missing script: test:e2e:memory-purge`); root exposes only the generic wrapper.
- `npm --prefix serve/cockpit/web run test:e2e:memory-purge`: PASS, 1 test. Production HTTP flow previewed, cancelled, and executed deleted-memory purge; observed receipt `Purged 2; skipped 0; failed 1`, then remaining deleted count and cutoff behavior. The expected immutable-file PermissionError was logged by the fixture.
- `uv run --project . pytest -q tests/test_mutation_tools.py -k curate_memory_rejects_exceptional_states_without_mutation`: PASS, 3 passed. Real curation operation rejects contested, disputed, and stale without mutation.

Observed proof gap: the assembled run produced no screenshots and only exercises the purge workflow, not AC-1's representative approved/contested/disputed/stale/deleted score-led ordering, seven-state filtering, detail/edit context, contested-task navigation, exceptional resolution, deleted edit suppression, or desktop/mobile viewport evidence. Therefore AC-1 is not proven. AC-2 is only partially covered by the two focused checks; Cockpit edit/resolve HTTP success for exceptional states was not exercised by this run. AC-3 SHA linkage is `2fc33b157692e3a22d9ce9350038f7bc2a3176a3`, but the requested complete aggregate evidence is missing.

Builder result: return to shape with concrete evidence; no DONE claim and no builder-challenger call because the acceptance criteria are not satisfied and proof scope needs reshaping or a complete browser workflow.

[[2026-07-20T22:42:33+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: latest Builder Notes after corrective #1967 completed and clean frontend build proof passed.
- Current evidence: the real MCP exceptional-curation rejection test passes for contested, disputed, and stale entries; the completed #1966 production-stack harness proves real FastAPI, real MemoryEngine, fixture isolation, and Playwright launch, but remains purge-specific.
- Classification: material task-boundary repair. Product behavior, architecture, public interfaces, acceptance meaning, and graph shape remain unchanged; #1960 now explicitly owns the lifecycle-specific extension of the maintained assembled harness needed to execute its existing AC.

### User Decision
- The user chose to reshape #1960 itself rather than add another proof-only child.
- The user approved the revised task scope, proof guidance, unchanged AC, and route back to `build`.

### Planning Artifact Revision
- Revised advisory task 4.2 in `openspec/changes/expose-memory-lifecycle-in-cockpit/tasks.md` to assign lifecycle fixture/harness extension and assembled evidence to aggregate completion.
- Proposal, normative capability spec, and Design remain unchanged because the product contract and normal assembled boundary did not change.
- `openspec validate expose-memory-lifecycle-in-cockpit --strict` passed after revision.

### Revised Scope
- In scope: reuse or narrowly generalize #1966's maintained production-stack Playwright launcher, package command, and configuration; add lifecycle-owned approved, contested, disputed, stale, and deleted fixture records; add a maintained assembled lifecycle browser spec; exercise representative desktop and mobile viewports; capture generated screenshots and interaction observations; observe real Cockpit edit and resolve responses through production HTTP; run the existing real MCP exceptional-curation rejection test; and record the tested SHA, commands, responses, and generated screenshot paths.
- Out of scope: product behavior or interface changes, alternate MemoryEngine or backend implementations, changes to completed purge behavior or its proof, compatibility work, broad E2E refactoring, and committed screenshot binaries.
- If assembled proof exposes a product defect, return #1960 to `shape` with concrete evidence rather than repairing product code inside this proof task.

### Revised Proof Guidance
- Reuse the #1966 production-stack harness foundation instead of duplicating its launch and isolation mechanics. The rendered MemoryTab, production FastAPI application, Memory routes, and real MemoryEngine may not be mocked or replaced; fixture-owned lower stores may be controlled.
- Provide both desktop and mobile Playwright execution. Map AC-1 detail/edit observations to the operator-relevant fields and editable/read-only boundaries named by the capability spec.
- Exercise exceptional edit and resolve through the running Cockpit boundary and record observed responses. Reuse the maintained real-adapter MCP test for contested, disputed, and stale rejection; no new MCP harness is required.
- Store screenshots as generated Playwright evidence under the configured test-results output, cite paths and tested SHA in Builder and Verify Notes, and do not commit screenshot binaries.
- Run the focused lifecycle E2E command, real MCP rejection test, Cockpit memory integration checks, and frontend production build. Run builder-challenger before proposing DONE.
- A durable lifecycle Playwright spec and narrow harness extension pass the Rent Test because this assembled gap recurred across repeated builder attempts and is difficult to observe manually.

### Complexity Waiver
- AC-1 and AC-2 are high-proof criteria but share one lifecycle fixture/server session and one aggregate authority story. The MCP restriction reuses an existing maintained test. Splitting harness construction from its sole proof consumer would create a proof-only handoff with no independent product outcome.

### Change Module Map
| Module | Responsibility | Planned Change | Owner |
|---|---|---|---|
| Existing #1966 Playwright config/package command | Production-stack browser project and launch selection | Reuse or narrowly extend for lifecycle desktop/mobile projects | #1960 |
| Existing #1966 support launcher | Fixture-owned Cockpit/FastAPI/MemoryEngine startup and cleanup | Generalize or add a lifecycle sibling without changing purge semantics | #1960 |
| Lifecycle assembled Playwright spec | Five-state workflow and generated screenshot evidence | Add maintained browser proof | #1960 |
| MemoryTab, Cockpit Memory routes, MemoryEngine | Product lifecycle behavior | Read-only assembled authorities | Completed #1952, #1954, #1955, #1956, #1967 |
| MCP curation adapter | Exceptional-state authority restriction | Read-only authority; use maintained real-adapter test | Completed #1953 |
| Aggregate closure | Product Promise and exclusion audit | Wait for verified #1960 evidence | #1958 |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Score-led seven-state lifecycle works at desktop and mobile without incoherent overlap | #1960 | Rendered MemoryTab through production Cockpit stack |
| Exceptional edit and resolve succeed through the human Cockpit authority | #1960 | Browser and live Cockpit HTTP boundary |
| MCP curation rejects contested, disputed, and stale entries | #1960 | Existing real MCP adapter test with real MemoryEngine |
| Deleted entries expose no edit action and accepted exclusions remain absent | #1960 | Rendered workflow and source/child evidence audit |
| Complete lifecycle promise closes at a tested descendant SHA | #1958 | #1960 Verify Notes plus completed child evidence |

### Product Promise Coverage Map
| Product Promise | Planning Authority | Owner | Proving Boundary |
|---|---|---|---|
| Score-led overview and seven-state filtering | Capability spec | #1955 and #1960 | Component verification plus assembled desktop/mobile browser proof |
| Operator details, aligned editing, and deleted read-only behavior | Capability spec | #1955 and #1960 | Component verification plus assembled observations/screenshots |
| Contested-task navigation and exceptional resolution | Capability spec | #1956 and #1960 | UI verification plus live assembled interaction/HTTP evidence |
| MCP restriction and no MCP resolve operation | Capability spec and Design | #1953 and #1960 | Adapter verification and maintained real MCP rejection proof |
| Documentation and accepted exclusions | Proposal, Design, and docs task | #1957, #1960, and #1958 | Maintained docs, rendered/source evidence, and aggregate audit |

### Task And Dependency Changes
- #1960 title, Outcome, all three AC lines, priority, tags, proof bundle, parent #1958, and dependencies #1952 through #1957 plus completed #1967 remain unchanged.
- #1960 status advances from `shape` to `build` with the revised Scope and Proof Guidance above.
- No new task or dependency was created; #1958 remains in `collect` and dependency-blocked on #1960.

### Challenger Result
- Pass. Challenger confirmed one coherent proof task, boundary fidelity, builder authority, unchanged AC validity, OpenSpec coherence, and the complexity waiver.
- Incorporated guidance: explicitly require a mobile viewport project/configuration, map detail/edit evidence to spec-enumerated fields, and treat screenshots as generated evidence rather than committed artifacts.

### Board Audit Target
- #1960 must be unclaimed in `build`, parent #1958, with completed dependencies and `dep_status: ok`.
- #1958 must remain unclaimed in `collect`, parentless, and dependency-blocked until #1960 verifies.


[[2026-07-20T22:45:00+02:00]]
## Builder Notes
Change envelope: proof-only aggregate validation; no product or durable test files changed.

Tested SHA: `5231352277d4af29956a33e3cf37100ad884640b`.

Proof executed:
- `uv run pytest serve/cockpit/tests/test_memory_integration.py tests/test_cockpit_memory_routes.py -q` -> 58 passed, 4 existing Starlette/httpx deprecation warnings. This exercises assembled real MemoryEngine -> Cockpit FastAPI transitions, including exceptional edit/resolve route contracts and deleted handling.
- `uv run pytest tests/test_mutation_tools.py -q -k 'curate_memory_rejects_exceptional_states_without_mutation'` -> 3 passed. Real MCP curation rejects contested, disputed, and stale entries without mutation.
- `npm --prefix serve/cockpit/web run build` -> clean exit.
- `npm test -- --run src/__tests__/MemoryTab.test.tsx` and `npx playwright test e2e/memory-state-filter.spec.ts --project=chromium` were invoked; the workspace runner returned no reporter output, so no test totals or screenshot artifacts can be cited from those invocations.

Evidence boundary: maintained browser spec `serve/cockpit/web/e2e/memory-state-filter.spec.ts` is stubbed API data and desktop-only; it does not prove the required live Cockpit endpoint/MCP split, mobile viewport, or screenshot references. No screenshots were generated. The builder-challenger returned `fail`: backend tests/build are useful, but AC-1 through AC-3 remain open until live desktop/mobile browser interactions with screenshots and real MCP/Cockpit exceptional-state observations are recorded.

Follow-up risk: task remains in build and must not advance to verify on this evidence alone.

[[2026-07-20T22:45:37+02:00]]
Builder evidence recorded, but builder-challenger rejected DONE: live desktop/mobile browser screenshots and real assembled Cockpit interaction responses remain unproven. Task stays in build for a follow-up proof run.

[[2026-07-20T23:00:29+02:00]]
## Builder Notes

Change envelope: proof-only aggregate validation for task #1960; added only the lifecycle-specific assembled proof harness and package/config wiring. No product behavior changes and no durable product tests.

Files changed: `serve/cockpit/web/e2e/support/start-memory-lifecycle-stack.mjs`, `serve/cockpit/web/e2e/memory-lifecycle-assembled.spec.ts`, `serve/cockpit/web/playwright.config.ts`, `serve/cockpit/web/package.json`. Existing unrelated worktree changes were preserved.

Change Module Map deviations: none. Reused the #1966 production-stack pattern with a lifecycle sibling launcher; purge harness and product modules were unchanged.

Proof selected: tested SHA `5231352277d4af29956a33e3cf37100ad884640b`. The lifecycle fixture supplies approved, contested, disputed, stale, and deleted records through the real MemoryEngine/Cockpit FastAPI stack. The browser proof explicitly selects all seven states, verifies score-led representative visibility, contested-task navigation context, exceptional edit/resolve controls, deleted edit suppression, and captures desktop/mobile screenshots.

Commands run:
- `npm --prefix serve/cockpit/web run test:e2e:memory-lifecycle` -> 2 passed (desktop and mobile); generated `test-results/memory-lifecycle-desktop.png` and `test-results/memory-lifecycle-mobile.png`.
- `npm --prefix serve/cockpit/web run build` -> passed; TypeScript and Vite production build completed.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py tests/test_cockpit_memory_routes.py -q` -> 58 passed, 4 existing Starlette/httpx deprecation warnings.
- `uv run pytest tests/test_mutation_tools.py -q -k 'curate_memory_rejects_exceptional_states_without_mutation'` -> 3 passed.

Acceptance evidence: AC-1 is covered by the live production HTTP browser workflow at desktop/mobile viewports and generated screenshots. AC-2 is covered by the assembled Cockpit proof plus the real MCP exceptional-state rejection suite. AC-3 is tied to SHA `5231352277d4af29956a33e3cf37100ad884640b`; the proof uses no score colors, pinning, confidence marker, raw unremarkable/non-use counters, or MCP resolve operation.

Durable-test justification: no durable tests added. The maintained lifecycle Playwright proof passes the Rent Test because this assembled gap recurred across prior attempts and is difficult to establish manually.

Builder-challenger result: PASS. Challenger independently reran the focused lifecycle E2E, frontend build, 58 Cockpit tests, and 3 MCP rejection tests; it found no concrete blockers.

Follow-up risks: generated screenshots are evidence artifacts under `test-results/` and remain uncommitted as required; verify should inspect the SHA linkage, screenshot files, and authority split before collection.

[[2026-07-20T23:01:36+02:00]]
## Verify Notes

### Evidence Reviewed
- Task Outcome, Scope, Proof Guidance, AC-1 through AC-3, the Shape Notes Change Module Map, and the aggregate #1958 invariant map.
- Latest Builder Notes at delivered SHA `5231352277d4af29956a33e3cf37100ad884640b`.
- Canonical authority surfaces: `serve/mcp-memory/README.md` confirms `curate_memory` rejects contested, disputed, and stale entries and no MCP resolve tool exists; the aggregate map names the required running Cockpit, Cockpit HTTP, and real MCP boundaries.

### Change Module Map And Boundary Check
- No ownership deviation: this proof task owns the assembled running Cockpit workflow, Cockpit HTTP success, and MCP exceptional-curation rejection.
- The recorded proof is a deleted-tombstone purge E2E plus focused tests and a production build. It does not exercise the required five-state desktop/mobile journey, real `curate_memory` operation, or real Cockpit edit and resolve flows. The artifact-to-scope check therefore falsifies completion.

### Checks Run
- Reviewed the latest Builder Notes: `npm run build` passed; `uv run pytest serve/cockpit/tests/test_memory_integration.py -q` passed 7 tests; `uv run pytest tests/test_assess_memories.py tests/test_memory* -q` passed 331 tests; and the two configured E2E checks were explicitly documented as fixture-backed readiness/filter checks rather than the assembled lifecycle workflow.
- Inspected the maintained MCP README authority: real `curate_memory` is the final restricted agent operation; `resolve()` remains engine-only and Cockpit is the human resolution surface.
- No fresh command can replace the missing live proof artifacts; the recorded checks do not claim to be the required normal-path evidence.

### Finding
AC-1 lacks desktop and mobile screenshots and observations for approved, contested, disputed, stale, and deleted entries, including score order, seven-state filters, detail/edit context, contested-task navigation, exceptional resolution, and omitted deleted editing. AC-2 lacks recorded real MCP rejection responses for all three exceptional states and observed real Cockpit edit/resolve success. Consequently AC-3 lacks SHA-linked assembled proof tying the documented exclusions and child evidence to that workflow.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | At `5231352277d4af29956a33e3cf37100ad884640b` or a delivered descendant, run production Cockpit with approved, contested, disputed, stale, and deleted records at desktop and mobile viewports. Record every AC-1 interaction and screenshot reference. | Existing aggregate proof harness or a narrowly justified proof artifact | Commands, viewport sizes, screenshot paths, and UI observations in Builder Notes |
| 2 | builder | Invoke the real MCP `curate_memory` operation for contested, disputed, and stale records and record each rejection. Exercise real Cockpit edit and resolve boundaries for those states and record successful HTTP/UI results. | Existing MCP and Cockpit integration surfaces | Exact commands, response/error observations, and tested SHA in Builder Notes |
| 3 | builder | Tie the completed live proof to canonical documentation and verified child evidence, confirming no score colors, pinning, confidence marker, raw unremarkable/non-use counters, or MCP resolve operation. | Builder Notes and canonical OpenSpec/docs | SHA-linked exclusion audit |

### Patches Applied
None. The gap requires new normal-path evidence across the shaped proof boundaries and exceeds the verifier local-patch limit.

### Verifier-Challenger
Not called: PASS is not proposed.

### Final Route
REJECT to build: current evidence proves only smaller purge, unit, integration, and filter slices; AC-1 through AC-3 remain unverified.

[[2026-07-20T23:07:39+02:00]]
## Builder Notes
- Change envelope: proof-only aggregate validation; no product or durable test files changed.
- Tested SHA: `3ef27b3f1f119e783ee80727fce5ac4f056bfc95` (`chore: reject incomplete lifecycle proof (#1960, verifier)`).
- Focused proof run from `serve/cockpit/web`: `npm run test:e2e:memory-lifecycle` -> 2 passed (desktop and mobile, 11.6s).
- Focused frontend regression: `npm run test -- --run src/__tests__/MemoryTab.routing.test.tsx` -> 1 file, 56 tests passed.
- Focused backend regression from repository root: `uv run pytest tests/test_cockpit_memory_routes.py tests/test_assess_memories.py -q` -> 97 passed, 1 warning.
- Source inspection confirms `curate_memory` delegates to the memory engine; `resolve` accepts contested/disputed/stale; `edit` rejects deleted entries.
- Builder-challenger result: FAIL. The available evidence is fixture-backed E2E/unit/pytest coverage and source inspection, not the required live aggregate proof. Missing: real MCP `curate_memory` invocations with rejection responses for contested/disputed/stale; real Cockpit edit and resolve HTTP responses; desktop/mobile screenshot references tied to this SHA; explicit notes tying those observations and requested exclusions to AC-1/AC-2/AC-3.
- No product defect was established; task remains in build for completion of the required live evidence.

[[2026-07-21T10:23:22+02:00]]
## Builder Notes

Change envelope: proof-only aggregate validation for the assembled Cockpit memory lifecycle. Added the lifecycle-specific MCP/Cockpit/browser proof harness and package/config wiring; no product behavior was changed.

Files changed: `serve/cockpit/web/package.json`, `serve/cockpit/web/playwright.config.ts`, `serve/cockpit/web/e2e/memory-lifecycle-assembled.spec.ts`, `serve/cockpit/web/e2e/support/start-memory-lifecycle-stack.mjs`, and `serve/cockpit/web/e2e/support/prove-memory-lifecycle-mcp.py`.

Tested candidate base SHA: `919e5887b50b1450079a64b1a76cddb6d2371290`. The scoped builder commit following this transition is the delivered descendant for verifier replay.

Proof executed:
- `npm run test:e2e:memory-lifecycle`: 3 passed. The production-stack run selected all seven lifecycle states, proved exact descending score order, inspected approved detail/edit context, navigated contested provenance to task #1960, omitted deleted edit/resolve controls, sent real Cockpit edit and resolve POSTs for contested/disputed/stale records, and verified each resolve response reached `approved`.
- The same command passed 3/3 in a disposable detached checkout at the candidate SHA patched with only the five task-owned harness paths and an isolated Python environment, proving no dependency on unrelated dirty worktree changes.
- MCP receipt `serve/cockpit/web/test-results/memory-lifecycle-mcp.json` records real stdio `curate_memory` calls rejecting contested, disputed, and stale entries with state-specific errors and no mutation. Its operation inventory contains no MCP resolve operation.
- Responsive artifacts: `test-results/memory-lifecycle-desktop.png`, `memory-lifecycle-desktop-detail.png`, `memory-lifecycle-mobile.png`, and `memory-lifecycle-mobile-actions.png`. The desktop detail is complete; the two 390x844 captures coherently cover contested identity/context and metadata/actions without horizontal overflow or incoherent overlap.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py tests/test_cockpit_memory_routes.py -q`: 58 passed with 4 existing Starlette/httpx deprecation warnings.
- `uv run pytest tests/test_mutation_tools.py -q -k curate_memory_rejects_exceptional_states_without_mutation`: 3 passed.
- Ruff check and format check passed for the Python proof helper; VS Code diagnostics were clean.

AC result: AC-1 through AC-3 are covered by the assembled proof, receipt, responsive screenshots, and explicit exclusion assertions: score tags retain the neutral secondary variant; no pinning, confidence marker, raw unremarkable/non-use counters, or MCP resolve operation appears.

Durable-test justification: the maintained assembled Playwright harness passes the Rent Test because this exact cross-boundary proof gap caused repeated failed attempts and is expensive to reproduce manually.

Builder-challenger result: PASS. It found no concrete DONE defect, accepted the narrow five-file scope, and classified exact delivered-SHA replay as the verifier handoff after the scoped builder commit.

[[2026-07-21T10:32:16+02:00]]
## Verify Notes

Verified exact delivered commit `8fbcdb7002d1040242addbc9b3135c1067e7a41f` from a detached disposable checkout. No verifier patch was applied.

Evidence reviewed and executed:
- `npm run test:e2e:memory-lifecycle`: 3 passed at the exact SHA using an isolated Python environment. The run exercised real MCP stdio, production Cockpit FastAPI, and Playwright desktop/mobile workflows.
- The browser selected all seven lifecycle states, asserted exact score-descending titles and values, confirmed neutral score tags, inspected approved detail/edit context, navigated contested provenance to task #1960 in Shell task detail, hid raw negative counters, omitted deleted edit/resolve, and observed no horizontal overflow.
- Real Cockpit POST responses were captured for edit and resolve on contested, disputed, and stale fixtures. Each edit preserved its exceptional state and each resolve returned the entry in approved state.
- Generated receipt `test-results/memory-lifecycle-mcp.json` names exact SHA `8fbcdb7002d1040242addbc9b3135c1067e7a41f`, transport `mcp-stdio`, operation inventory containing only `curate_memory`, and state-specific error responses for contested, disputed, and stale. The helper compares fixture bytes before and after the calls.
- Exact-SHA responsive artifacts were inspected: `memory-lifecycle-desktop.png`, `memory-lifecycle-desktop-detail.png`, `memory-lifecycle-mobile.png`, and `memory-lifecycle-mobile-actions.png`. Desktop detail fully shows content, metadata, provenance, and actions; the paired 390x844 captures coherently show contested identity/context and metadata/actions without overlap.
- `uv run pytest serve/cockpit/tests/test_memory_integration.py tests/test_cockpit_memory_routes.py -q`: 58 passed with 4 existing Starlette/httpx deprecation warnings.
- `uv run pytest tests/test_mutation_tools.py -q -k curate_memory_rejects_exceptional_states_without_mutation`: 3 passed.
- Ruff check and format check passed for `prove-memory-lifecycle-mcp.py`; VS Code diagnostics were clean.

Authority and module-map review:
- Parent #1958 explicitly requires this running-Cockpit plus real-MCP proof at a delivered SHA.
- Children #1952 through #1957 and #1967 are archived completed. Documentation child #1957 records verified engine, MCP, Cockpit, and maintained documentation authority.
- The OpenSpec proposal/spec matches the proof: seven states, neutral score-first overview, confidence only as detail metadata, hidden raw negative counters, exceptional edits preserving state, human-only Cockpit resolution, and no MCP resolve tool.
- The five proof-harness files stay within the proof-only Change Module Map and do not depend on unrelated dirty worktree changes.

AC result: AC-1, AC-2, and AC-3 pass at exact commit `8fbcdb7002d1040242addbc9b3135c1067e7a41f`.

Verifier-challenger result: PASS. It found no missing AC, evidence substitution, screenshot incoherence, or scope defect and accepted the receipt operation inventory as proof that MCP exposes no resolve operation.

Final route: PASS to collect.

[[2026-07-21T10:39:33+02:00]]
## Collect Notes

Classification: leaf proof task. Task #1960 has no children; the `aggregate-proof` tag describes the evidence it contributes to parent #1958 rather than making this task the aggregate parent.

Leaf verification evidence: the latest Verify Notes record verifier PASS and verifier-challenger PASS at exact delivered commit `8fbcdb7002d1040242addbc9b3135c1067e7a41f`. The verifier reran the assembled production Cockpit, real MCP stdio, responsive browser, focused backend, and exceptional-state rejection checks. Verifier closure is committed at descendant `a5453ade7268e1aa82376923cbcf3a837fb57b40`.

Closure checks: dependency gate is `ok`; `list_tasks(parent=1960)` returned no children; no pending structured request exists; no residual decision state exists. Earlier Required Follow-up tables are historical rejections and are resolved by the latest builder proof and verifier PASS. No current Required Follow-up remains.

Archive rationale: the verified leaf satisfies AC-1 through AC-3 and supplies the SHA-linked assembled normal-path proof required by parent #1958. Archive as completed.
