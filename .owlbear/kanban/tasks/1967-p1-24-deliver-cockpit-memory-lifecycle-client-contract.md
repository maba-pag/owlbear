---
id: 1967
title: 'P1-24: Deliver Cockpit memory lifecycle client contract'
status: verify
priority: high
created: 2026-07-20T02:52:46.061518+02:00
updated: 2026-07-20T08:59:58.551164+02:00
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
archival_reason:
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
