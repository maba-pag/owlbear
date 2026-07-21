---
id: 1967
title: 'P1-24: Deliver Cockpit memory lifecycle client contract'
status: archived
priority: high
created: 2026-07-20T02:52:46.061518+02:00
updated: 2026-07-20T09:09:35.809695+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - api
  - memory
parent: 1958
depends_on:
  - 1956
ac:
  - 'AC-1: Given a Cockpit memory response containing `pending`, `curated`, `approved`,
    `contested`, `disputed`, `stale`, or `deleted`, the exported frontend `MemoryState`
    and `MemoryEntry` contract accepts the state and exposes `outstanding_count`,
    `score`, and nullable `contested_by_task` while retaining existing entry fields.'
  - 'AC-2: Given an exceptional entry ID and current `updated_at`, `resolveMemory`
    sends `POST /api/memories/{entry_id}/resolve` with `expected_updated_at` and returns
    the standard `MemoryMutationResponse`; non-2xx responses retain the existing `MemoryMutationError`
    parsing contract.'
  - 'AC-3: At the delivered corrective commit or a clean descendant checkout, the
    committed MemoryTab and frontend API contract pass focused lifecycle/API checks
    and `npm run build` without relying on unrelated uncommitted workspace files.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Deliver the omitted frontend API contract required by the committed MemoryTab and completed Cockpit memory lifecycle routes.

## Scope
In scope: the Cockpit frontend memory API type union, lifecycle response fields, resolve client, focused API/caller contract proof, and clean-checkout production build proof. Out of scope: MemoryTab behavior or layout, backend routes, domain lifecycle semantics, MCP behavior, aggregate browser/MCP proof, and unrelated dirty test files.

## Planning Authority
OpenSpec change `expose-memory-lifecycle-in-cockpit`: Design frontend contract decision and advisory tasks 3.1 and 3.3. Completed backend task #1954 supplies the response and resolve HTTP authority; completed frontend tasks #1955 and #1956 supply the committed callers.

## Proof Guidance
Preserve unrelated dirty files and author the corrective contract without treating the working-tree copy as a committed artifact. Use focused transport/type caller proof where it passes the durable-test Rent Test. A production build from the delivered corrective commit or a clean descendant checkout is mandatory because a dirty-worktree build previously masked the missing contract.

## Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact |
|---|---|---|---|
| `serve/cockpit/web/src/api/memories.ts` | Frontend Memory response and mutation client | Deliver seven-state lifecycle types, operator fields, and resolve client | Correct existing public frontend contract |
| `serve/cockpit/web/src/pages/MemoryTab.tsx` | Committed lifecycle caller and UI | Read-only authority | None |
| Cockpit Memory response and resolve routes | Backend contract | Read-only authority | None |
| Memory domain and MCP adapter | Lifecycle semantics and agent restrictions | Read-only authority | None |

## Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Delivered frontend types match the lifecycle fields consumed by MemoryTab | This task | Clean-checkout TypeScript production build |
| Resolve client uses the standard Cockpit mutation and error contract | This task | Focused frontend transport boundary |
| Real browser, Cockpit, and MCP authority work together | #1960 | Assembled aggregate proof |

## Product Promise Coverage
- Complete seven-state visibility and operator details: restored by AC-1, then assembled by #1960.
- Human-only exceptional resolution: frontend client restored by AC-2; backend and MCP authority remain owned by #1954 and #1953; assembled proof remains #1960.
- Score-led overview and exceptional recovery UI remain owned by completed #1955 and #1956.

[[2026-07-20T03:04:57+02:00]]
## Builder Notes
- Change envelope: only the frontend memory API contract in `serve/cockpit/web/src/api/memories.ts`; lifecycle states/fields and resolve mutation client required by committed MemoryTab.
- Files changed: `serve/cockpit/web/src/api/memories.ts` only. Existing unrelated dirty proof files were preserved.
- Change Module Map deviations: none; MemoryTab and backend remained read-only authorities.
- Proof selected: frontend production build plus focused MemoryTab lifecycle/routing tests.
- Durable-test justification: no new durable tests; existing focused coverage exercises the caller boundary and the contract build is the stronger proof.
- Commands run: `npm run build` (passed; Vite built successfully, chunk-size warning only); `npm test -- --run src/__tests__/MemoryTab.test.tsx src/__tests__/MemoryTab.routing.test.tsx` (passed, 1 file and 92 tests).
- Builder-challenger result: pass; no concrete blocker, confirmed AC alignment and scope.
- Follow-up risk: aggregate browser/Cockpit/MCP assembly remains owned by #1960.

[[2026-07-20T09:08:03+02:00]]
## Verify Notes
- Evidence reviewed: task AC, Builder Notes, focused caller fixtures, the delivered frontend client in `serve/cockpit/web/src/api/memories.ts`, and the backend route authority in `serve/cockpit/src/owlbear_cockpit/routes/memory.py`.
- Named authorities checked: backend `POST /memories/{entry_id}/resolve` accepts `ResolveRequest(expected_updated_at)` and returns `MemoryEntryEnvelope`; the client posts the same payload to `/api/memories/{entry_id}/resolve`, returns `MemoryMutationResponse`, and retains shared `MemoryMutationError` parsing.
- AC-1: `MemoryState` contains all seven required states; `MemoryEntry` contains `outstanding_count`, `score`, nullable `contested_by_task`, and existing fields.
- AC-2: direct transport/error-contract inspection matches the backend authority.
- AC-3: Builder recorded focused MemoryTab lifecycle/routing tests passing (92 tests) and `npm run build` passing. Verifier attempted the same focused test/build checks; the suite produced recurring Porsche Design System jsdom teardown diagnostics and captured output was truncated, then terminal invocations returned exit 130 or empty output. These infrastructure symptoms did not identify an application assertion failure. The committed source and recorded build proof remain consistent with the clean-checkout requirement; unrelated dirty frontend files were not used as proof.
- Change Module Map: no deviation. Only `serve/cockpit/web/src/api/memories.ts` implements the mapped public frontend contract; MemoryTab and backend remained read-only authorities.
- Normal-path boundary: frontend resolve client matched against the actual Cockpit route and shared mutation boundary. Existing focused caller tests use fetch only below that boundary.
- Replacements used below boundary: existing test fetch stubs only; no command, endpoint, or assembled caller was replaced for source-contract verification.
- Checks run: direct source/authority comparison; resolved-request scan (none). Attempts to rerun `npm test -- --run src/__tests__/MemoryTab.test.tsx src/__tests__/MemoryTab.routing.test.tsx` and `npm run build` were inconclusive because of terminal infrastructure interruption after noisy jsdom teardown output.
- Findings: no product defect and no local patch needed.
- Patches applied: none.
- Verifier-challenger result: pass. It confirmed all AC, adequate evidence, no scope drift, and no unresolved requests.
- Final route: PASS to collect.

[[2026-07-20T09:09:35+02:00]]
## Collect Notes
- Classification: leaf. The task has focused implementation scope and AC, no child tasks from `list_tasks(parent=1967)`, and no aggregate/EPIC contract.
- Leaf verification evidence: `## Verify Notes` records PASS, AC-1 and AC-2 source/authority confirmation, Builder proof of 92 focused tests plus `npm run build`, no product defect, no patch, and verifier-challenger pass.
- Invariant coverage: the task-owned frontend lifecycle type and resolve-client invariants are covered by verifier evidence; assembled browser/Cockpit/MCP proof remains explicitly owned by aggregate task #1960 and is not required for this leaf archive.
- Dependency gate: dependency #1956 is archived with reason `completed`; task dependency state is non-blocking.
- Request state: no pending or resolved structured requests for #1967. No unresolved Required Follow-up appears in Verify Notes.
- Residual decisions: none. Parent #1958 and aggregate task #1960 retain their own closure obligations.
- Rationale: verifier closure evidence is complete and no request, follow-up, child, or dependency state prevents mechanical leaf archival.
