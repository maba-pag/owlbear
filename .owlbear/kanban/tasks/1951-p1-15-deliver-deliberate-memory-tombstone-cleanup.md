---
id: 1951
title: 'P1-15: Deliver deliberate memory tombstone cleanup'
status: collect
priority: high
created: 2026-07-17T03:04:38.474076+02:00
updated: 2026-07-17T03:05:02.143384+02:00
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
archival_reason:
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
