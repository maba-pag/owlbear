---
id: 1951
title: 'P1-15: Deliver deliberate memory tombstone cleanup'
status: archived
priority: high
created: 2026-07-17T03:04:38.474076+02:00
updated: 2026-07-20T22:12:15.762820+02:00
tags:
  - phase-1
  - scope:memory
  - aggregate
  - maintenance
parent:
depends_on:
  - 1946
  - 1947
  - 1948
  - 1949
  - 1950
  - 1966
ac:
  - 'AC-1: At a verified descendant commit, the assembled Cockpit workflow previews
    and purges cutoff-eligible tombstones for positive and zero-day thresholds while
    preserving newer tombstones and non-deleted entries.'
  - 'AC-2: With restrictive Memory filters active, the assembled confirmation states
    project-wide scope, uses project-wide counts, and execution returns a visible
    purged/skipped/failed receipt followed by refreshed entries and Purge deleted
    (N).'
  - 'AC-3: The completed change preserves pending hard-delete, non-pending soft-delete,
    default exclusion of deleted entries, and the primary Memory metric hierarchy,
    while adding no persisted threshold, timer polling, health signal, restore workflow,
    or MCP purge operation.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Collector verifies the complete deliberate tombstone-cleanup promise across the integrated Memory workflow.

## Scope
Aggregate closure only. This task owns no direct implementation and introduces no scope beyond its child tasks.

## Planning Authority
- OpenSpec change: `openspec/changes/purge-deleted-memories/`.
- Product decisions: Proposal Decision Register.
- Normative behavior: `memory-tombstone-purge` capability spec.
- Architecture and proof boundaries: Design decisions and invariant map.

Proof guidance: inspect child Verify Notes and use assembled Cockpit evidence tied to a tested descendant commit; lower filesystem and network dependencies may be controlled, but the MemoryTab, FastAPI, and MemoryEngine path may not be bypassed.

## Shape Notes

### Source And Review
- Mode: OpenSpec shaping with staged user review.
- Planning source: `openspec/changes/purge-deleted-memories/` Proposal, `memory-tombstone-purge` Spec, Design, and advisory Tasks.
- User approved product behavior, architecture, completion boundary, and this concrete graph.
- Reconciled revisions: preview endpoint is `POST /api/memories/purge/preview`; execution is `POST /api/memories/purge`; deleted count refreshes on complete Memory loads and successful mutations, never filter changes or polling. Strict OpenSpec validation passed after revision.

### Readiness And Authorities
- Invocation: compact `Purge deleted (N)` Memory action, PDS threshold preview, irreversible confirmation, result receipt, and refresh.
- Authorities: `MemoryEngine` owns state/timestamps/cache/indexes; `storage.delete_entry` owns protected unlink; Cockpit memory routes own HTTP; frontend Memory API and headless flow own request state; `MemoryTab` owns presentation; installed PDS types own `PInputNumber`; `usePollingFetch` owns load cadence.
- Preserved: pending hard-delete, non-pending soft-delete, default deleted filtering, and primary Memory metric hierarchy.
- Excluded: persisted settings, polling, automation, restore, health signal, and MCP purge.

### Change Module Map
| Module | Planned Change | Interface Impact | Owner |
|---|---|---|---|
| `serve/memory/.../engine.py` | purge authority and coherent shared state | new methods/contracts | #1946, #1947 |
| `serve/memory/.../storage.py` | reuse protected unlink | none | #1946 |
| Cockpit `routes/memory.py` | preview and execute actions | new HTTP schemas/routes | #1948 |
| Web `api/memories.ts` and headless purge flow | typed calls and ordered transient state | new client/flow contract | #1949 |
| `pages/MemoryTab.tsx` | action, dialog, receipt, count cadence | changed rendered workflow | #1950 |
| `WorkspaceHeader.tsx` | reuse actions slot | none | #1950 |

### Product Invariant Map
| Invariant | Owner | Normal Boundary |
|---|---|---|
| Only cutoff-eligible tombstones are removed and outcomes reconcile | #1946 | public engine plus filesystem |
| Reload and mutation interleavings preserve coherent state and delete behavior | #1947 | public engine operations |
| Strict filter-free project-wide HTTP contract | #1948 | assembled FastAPI route |
| Current-threshold gating, validation, execution, and receipt state | #1949 | public headless flow plus real client contract |
| Subordinate count, warning, receipt visibility, and refresh cadence | #1950 | rendered MemoryTab and browser |
| Complete irreversible workflow fulfills the Product Promise | #1951 | assembled MemoryTab, FastAPI, and MemoryEngine |

### Final Graph And Challenge
- Dependency chain: #1946, #1947, #1948, #1949, #1950; each task depends on its predecessor. Aggregate #1951 depends on #1946 through #1950.
- Challenger initially rejected ambiguous rendered behavior ownership between #1949 and #1950. Draft was repaired so #1949 owns headless state and #1950 owns presentation; re-challenge passed with full Product Promise coverage and no orphaned invariant.
- Board audit: #1946-#1950 are unblocked `build` children of #1951; #1951 is unblocked `collect` with all five dependencies. Priorities and tags match the approved graph.

[[2026-07-20T02:20:04+02:00]]
## Collect Notes

Classification: aggregate.

Intent source: `## Outcome`, `## Planning Authority`, and `## Shape Notes`, grounded in `openspec/changes/purge-deleted-memories/`. The Product Invariant Map assigns core eligibility/reconciliation to #1946, cache coherence and preserved deletion semantics to #1947, strict project-wide HTTP behavior to #1948, ordered headless state to #1949, rendered workflow and refresh cadence to #1950, and the assembled MemoryTab/FastAPI/MemoryEngine promise to #1951.

Child coverage: the parent gate declares #1946 through #1950. All five task summaries project `parent: 1951`; each is archived with reason `completed`, and their dependency chain is intact (#1946, then #1947, #1948, #1949, #1950). `list_tasks(parent=1951)` unexpectedly returned no rows, so coverage was cross-checked against the parent `depends_on` gate and each child's projected parent. Child Verify Notes contain final PASS evidence for every child invariant. #1949 retains an earlier rejected Verify Notes occurrence followed by a later PASS occurrence; its archived completed state and final notes establish closure.

Dependency gate: the authoritative parent read before claim reported `dep_status: ok` with `depends_on: [1946, 1947, 1948, 1949, 1950]`. All dependencies are completed archives.

Normal-path aggregate proof: not established. #1950's fresh browser proof exercised the real rendered MemoryTab but replaced API responses below it. #1948's assembled FastAPI proof replaced `get_memory_engine`. #1946 exercised the public MemoryEngine separately. No durable full-stack purge proof was found in Cockpit E2E, repository tests, or package tests. The available proof therefore does not exercise the required assembled MemoryTab, FastAPI, and MemoryEngine path in one normal-path run. It is also not tied to a tested commit SHA or later descendant; a read-only HEAD lookup was interrupted twice with exit 130 and no output, and child Verify Notes record commands but no tested SHA.

Residual decisions and requests: no pending or resolved structured request exists for #1951, and no pending structured request exists for #1946 through #1950.

Rationale: reject to shape because aggregate AC-1 and AC-2 explicitly require SHA-linked assembled proof, and the aggregate proof boundary and commit linkage remain incomplete. Code-level child AC are not remapped or reopened.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | Shaper | Restore an executable aggregate proof plan that exercises the assembled MemoryTab, FastAPI, and MemoryEngine path without replacing any of those three layers, covering positive and zero-day thresholds, restrictive active filters, project-wide preview/count messaging, visible purged/skipped/failed receipt, refreshed entries/count, preservation of newer tombstones and non-deleted entries, and the stated exclusions. Route implementation/proof work through child ownership rather than assigning code changes to this aggregate. | `openspec/changes/purge-deleted-memories/` and the appropriate Cockpit E2E/proof owner selected during reshaping | Record the exact tested commit SHA and a passing command or retained artifact run at that SHA or a later descendant; a SHA alone or separate layer proofs are insufficient. |

Final route: REJECT to shape.

[[2026-07-20T02:44:45+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: collector rejection recorded on #1951 after all five original children completed.
- Initial finding: child proof covered the real MemoryEngine, FastAPI routes, and rendered MemoryTab separately, but no one run crossed the required assembled MemoryTab, production FastAPI, and real MemoryEngine boundary at a recorded commit.
- Classification: material graph repair. Existing tooling could not execute the parent-owned runbook because Cockpit Playwright served Vite only and mocked backend APIs; a build-owned proof mechanism was required.

### User Decisions
- The user first preferred parent-owned collector proof to preserve the graph.
- Shaper-challenger found that option non-executable without new durable harness infrastructure.
- After focused review, the user approved preserving the assembled completion promise and adding one build leaf rather than weakening OpenSpec and parent acceptance.
- The user approved the final graph: new proof leaf #1966 in `build`; #1951 in `collect` behind #1946 through #1950 and #1966.

### Planning Artifact Revisions
- Revised `openspec/changes/purge-deleted-memories/tasks.md` only.
- Advisory task 4.1 now owns an isolated full-stack browser harness; task 4.2 owns SHA-linked aggregate execution through that harness.
- Proposal, normative capability spec, and Design remain unchanged because product behavior, architecture, endpoints, and the assembled proof boundary did not change.
- `openspec validate purge-deleted-memories --strict` passed after revision.

### Readiness And Authorities
- Production Cockpit `run()` already accepts `KANBAN_DIR`, `MEMORY_DIR`, `COCKPIT_PORT`, and `COCKPIT_NO_OPEN`, initializes real engines, serves the built frontend, and launches uvicorn.
- Existing Playwright configuration starts Vite preview only; current Memory browser proof mocks API transport and cannot satisfy the assembled boundary.
- Installed Playwright configuration, production Cockpit entry point, completed child contracts, and OpenSpec Design are the implementation authorities for #1966.

### Change Module Map
| Module | Responsibility | Planned Change | Owner |
|---|---|---|---|
| MemoryEngine purge and cache/index behavior | Eligibility, physical purge, reconciliation, and coherent indexes | Completed, read-only dependency | #1946 and #1947 |
| Cockpit Memory HTTP routes | Strict project-wide preview and purge contract | Completed, read-only dependency | #1948 |
| Frontend purge state and API | Ordered preview, execution, receipt, and refresh state | Completed, read-only dependency | #1949 |
| MemoryTab purge presentation | Action, warning, confirmation, receipt, and responsive interaction | Completed, read-only dependency | #1950 |
| Cockpit Playwright support and production launch fixture | Isolated assembled browser proof | Add maintained harness and workflow evidence | #1966 |
| Aggregate closure | Child evidence, tested SHA, OpenSpec validation, and Product Promise audit | No implementation | #1951 |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Only age-eligible tombstones are physically removed | #1946 | Core behavior plus #1966 assembled workflow |
| Cache/index state and ordinary deletion semantics remain coherent | #1947 | Core concurrency proof plus #1951 audit |
| Preview and execution remain strict and project-wide | #1948 | HTTP contract plus #1966 assembled workflow |
| Threshold preview and execution state remain ordered | #1949 | Headless flow plus #1966 assembled workflow |
| Warning, receipt, and refresh remain visible through MemoryTab | #1950 | Rendered component plus #1966 assembled workflow |
| The real rendered, HTTP, and engine layers work together without mutating workspace stores | #1966 | Isolated production-stack Playwright run |
| The complete deliberate cleanup promise closes at one tested descendant commit | #1951 | Aggregate collector audit |

### Product Promise Coverage Map
| Product Promise | Planning Authority | Owner | Proving Boundary |
|---|---|---|---|
| Permanently remove only cutoff-eligible deleted memories | Capability spec | #1946 and #1966 | Engine proof and assembled AC-2 |
| Preview and purge use server-owned project-wide scope | Capability spec and Design | #1948 and #1966 | HTTP proof and assembled AC-2/AC-3 |
| Ephemeral non-negative whole-day threshold with ordered preview | Capability spec and Design | #1949 and #1966 | Headless proof and assembled AC-2/AC-3 |
| Compact deleted-count action, irreversible warning, receipt, and refresh | Capability spec and Design | #1950 and #1966 | Rendered proof and assembled AC-3 |
| Preserve pending hard-delete, ordinary soft-delete, default filtering, and metric hierarchy | Proposal and Design | #1947, #1950, and #1951 | Child Verify Notes and parent AC-3 audit |
| No persisted threshold, timer polling, health signal, restore workflow, or MCP purge | Proposal exclusions | #1951 | Aggregate source/diff and child evidence audit |

### Task And Dependency Changes
- Created #1966, `P1-16: Establish assembled Memory purge browser proof`, in `build` with parent #1951 and dependency #1950.
- Added #1966 to #1951 dependencies; existing dependencies #1946 through #1950 remain unchanged.
- Routed #1951 from `shape` to `collect`; its three AC lines remain unchanged.
- #1966 owns only proof infrastructure and assembled evidence, not product behavior or endpoint changes.

### Challenger Result
- Initial parent-owned runbook graph: fail because no executable assembled harness existed and collector lacked authority to create it.
- Revised one-leaf graph: pass. Challenger confirmed non-redundancy, production-entry-point feasibility, boundary fidelity, AC quality, invariant ownership, complexity waiver, and Product Promise coverage.
- Incorporated non-blocking guidance by naming #1947's cache/index invariant explicitly and requiring post-write dependency-gate audit.

### Board Audit Target
- #1966 must be unclaimed in `build`, parent #1951, depending on completed #1950.
- #1951 must be unclaimed in `collect`, parentless, depending on #1946 through #1950 and #1966, and dependency-blocked until #1966 completes.
- Collector must not close #1951 without #1966 Verify Notes tied to the tested commit SHA and strict OpenSpec validation.

[[2026-07-20T22:12:15+02:00]]
## Collect Notes

- Classification: aggregate. The `aggregate` tag, Outcome/Scope, Planning Authority, and aggregate AC define parent-only closure with no direct implementation.
- Intent source: OpenSpec `openspec/changes/purge-deleted-memories/`, including the Proposal Decision Register, `memory-tombstone-purge` capability spec, Design decisions, and the parent Shape Notes.
- Invariant map coverage: #1946 covers cutoff eligibility, zero-day behavior, protected deletion, reconciliation, and counts; #1947 covers coherent cache/index mutation and preserved deletion semantics; #1948 covers strict FastAPI preview/execution contracts; #1949 covers ordered threshold validation, stale-preview invalidation, exact execution, and receipt state; #1950 covers rendered Memory action, project-wide count/confirmation, receipt, and refresh cadence; #1966 covers the assembled production browser path across MemoryTab, FastAPI routes, real MemoryEngine, and protected filesystem deletion.
- Child coverage: the six declared dependencies #1946, #1947, #1948, #1949, #1950, and #1966 each project `parent: 1951` and are archived with reason `completed`. `list_tasks(parent=1951)` unexpectedly returned no rows, so coverage was cross-checked through the explicit dependency set and each child record.
- Dependency gate: parent `dep_status` is `ok`; all declared dependencies are complete and none is blocked.
- Completion evidence: each child has a final PASS Verify Notes record. Earlier rejected attempts in #1949 and #1966 are superseded by their later PASS records and completed archive state.
- SHA-linked aggregate proof: #1966 records builder evidence commit `72249ca934d80d91ad859791fc17e4f48de1cc13` as an ancestor of tested HEAD `16de282f65f17441388db7c55bbaf8df109d68c7`. At that tested HEAD, `npm run test:e2e:memory-purge` passed one Playwright test in 10.9 seconds after building the frontend and launching production Cockpit FastAPI with fixture-owned Kanban and Memory stores.
- Aggregate normal path: the assembled browser proof used restrictive approved-only filtering while retaining project-wide `Purge deleted (3)`, proved cancellation without mutation, one-day preview with eligible 2 / too recent 1, a controlled unlink-failure receipt `Purged 1; skipped 1; failed 1`, preservation of failed and recent tombstones, exact-cutoff removal, zero-day preview with eligible 2 / too recent 0, final receipt `Purged 2; skipped 0; failed 0`, refreshed `Purge deleted (0)`, and absence of all deleted fixture entries. This satisfies parent AC-1 and AC-2 through the required assembled boundary.
- Preserved/excluded behavior: child verification confirms pending hard-delete, non-pending soft-delete, default deleted exclusion, and primary Memory metric hierarchy. No child introduced persisted threshold, timer polling, health signal, restore workflow, or MCP purge operation, satisfying AC-3.
- Structured requests and residual decisions: no pending or resolved parent requests; no pending request exists for any child. No unresolved Required Follow-up remains after the final child PASS records.
- Rationale: the earlier Collect Notes rejection identified missing full-stack SHA-linked proof. Child #1966 now supplies that proof, all required children are complete, and the aggregate promise is satisfied. Archive as completed.
