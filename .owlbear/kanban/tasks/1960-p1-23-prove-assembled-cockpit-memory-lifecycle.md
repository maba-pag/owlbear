---
id: 1960
title: 'P1-23: Prove assembled Cockpit memory lifecycle'
status: build
priority: high
created: 2026-07-17T20:19:09.315342+02:00
updated: 2026-07-17T20:47:08.105486+02:00
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
archival_reason:
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

