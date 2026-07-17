---
id: 1945
title: 'P1-09: Deliver trustworthy workspace health'
status: shape
priority: high
created: 2026-07-17T02:33:28.872345+02:00
updated: 2026-07-17T08:43:31.758781+02:00
tags:
  - phase-1
  - scope:cockpit
  - aggregate
  - health
parent:
depends_on:
  - 1937
  - 1938
  - 1939
  - 1940
  - 1941
  - 1942
  - 1943
  - 1944
ac:
  - In running Cockpit, initial Workspace Status is gray then shows independent 
    task/request/memory/ideas results from GET /health; a module check failure 
    is visible without suppressing sibling results.
  - In running Cockpit with deterministic and unresolved task fixtures, one 
    repair invocation fixes deterministic conditions including conflict-free 
    archive drift, preserves unresolved records, returns post-repair task health
    without an immediate GET, and leaves a receipt visible after overlay 
    closure.
  - Board/package evidence confirms generic Cleanup and old task scan/repair 
    routes are removed, claim sweep/activity compaction remain explicit, memory 
    lifecycle states and absent/empty ideas do not produce failure status, 
    unreadable ideas produce unhealthy status, and matched 
    Kanban/memory/Cockpit/frontend checks pass at one tested commit.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Collect the verified child work into one trustworthy Workspace Status journey covering independent module diagnostics, deterministic task repair, ordered frontend state, retained feedback, and maintenance separation.

## Scope
In scope: aggregate verification of the approved `redesign-workspace-health` Product Promise at one tested commit. Out of scope: direct implementation, memory purge, task-ID renumbering, per-file comparison UI, server-side repair history, background repair jobs, and global transaction guarantees.

## Proof Guidance
Collector inspects verified child evidence and observes the assembled normal path in the running Cockpit through the VS Code integrated browser. Aggregate proof records the tested commit and matched package checks; lower dependencies may be controlled only where a child criterion explicitly permits it.

## Shape Notes

### Source And Mode
- Source: OpenSpec change `redesign-workspace-health`.
- Mode: spec shaping and approved graph commit; this is not an existing-task repair.
- Review: product/scope, architecture/interfaces, and trade-offs/completion were separately reviewed and approved by the user.

### User Decisions
- Workspace health covers frequently mutated task, request, memory, and ideas storage.
- Root resources are `GET /health/live`, `GET /health`, four focused module reads, and synchronous `POST /health/tasks/repair`.
- Frontend transient states are gray; terminal severity is unhealthy/check-failed, then attention, then healthy. Connection failure remains explicit context rather than task-storage health.
- Duplicate repair operates on complete same-ID sets, applies only deterministic delete/quarantine rules, never renumbers IDs, and exposes unresolved conditions.
- Repair returns terminal outcomes and post-repair task health; the client does not issue an immediate follow-up health GET. The receipt remains in frontend session state until dismissal or replacement.
- Generic Cleanup is removed. Claim/session sweep and activity compaction stay explicit and outside health. Memory purge is excluded.

### Planning Artifact Revisions
- Proposal, workspace-health spec, design, and advisory tasks were created and reconciled under `openspec/changes/redesign-workspace-health/`.
- Strict OpenSpec validation passed before decomposition.
- Graph challenge added explicit archive-drift detection and successful repair, the two omitted unresolved duplicate classes, and unreadable ideas behavior. A second full challenge passed. Final wording also records ideas non-mutation, replaces ambiguous `valid` wording, and names deterministic repair actions.

### Brief Readiness
- Product outcome and invocation: the Cockpit Workspace Status opens gray, resolves four module results, offers deterministic task repair, and retains a dismissible receipt.
- Existing-system fit and authority: Kanban owns task/request evidence and repair; memory owns memory evidence; Cockpit backend owns aggregate/ideas HTTP contracts; Cockpit web provider owns ordering and receipt state; Workspace Status components own presentation.
- Normal-path proof: assembled FastAPI routes and running Cockpit in the VS Code integrated browser, supported by domain public-boundary checks.
- Completion and change contract: old task scan/repair/cleanup routes and generic Cleanup UI are removed; explicit claim sweep and activity compaction remain; listed exclusions remain unbuilt.

### Contract Authorities
| Claim | Authority | Evidence State | Confidence |
|-------|-----------|----------------|------------|
| Product behavior and exclusions | OpenSpec proposal and workspace-health spec | documented | high |
| Route family, synchronous repair, duplicate matrix, concurrency | OpenSpec design reconciled with current owners | documented and observed | high |
| Current task/request/cleanup ownership | `serve/kanban/src/owlbear_kanban/corruption.py` and `engine.py` | observed | high |
| Memory lifecycle literals and duplicate canonicalization | `serve/memory/src/owlbear_memory/models.py` and `engine.py` | observed | high |
| Root route assembly and current mutation forwarding | `serve/cockpit/src/owlbear_cockpit/main.py`, routes, and `view.py` | observed | high |
| Current frontend scan/connection/status ownership | Cockpit web provider, hooks, Shell, and status components | observed | high |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|--------|------------------------|----------------|------------------|-------------|
| Kanban corruption/task-health owner and engine | Per-file corruption plus task public behavior | Add normalized multi-finding task/graph/location health | new public diagnostic boundary | #1937 |
| Kanban request storage and engine | Parse/list request records, currently skipping malformed records | Add request integrity, duplicate, owner, and location evidence | new public diagnostic boundary | #1939 |
| Kanban repair owner and engine | Existing corruption repair and duplicate pre-pass | Replace with complete-set, revalidated, convergent repair and post-scan | changed public repair contract | #1940 |
| Kanban maintenance surface | Generic cleanup plus sweep/compaction | Remove generic cleanup and retain explicit lease/session/activity operations | removed and retained public APIs | #1941 |
| Memory engine | Lenient loading, parse count, canonical duplicate selection | Add non-mutating unreadable-path and duplicate-set evidence | new public diagnostic boundary | #1938 |
| Cockpit Python main/routes/view | Root liveness and `/api` task maintenance forwarding | Add root health family, ideas check, aggregate isolation, synchronous repair; remove obsolete forwards | changed HTTP surface | #1942 |
| Cockpit web API/provider/hooks | Split task scan and connection freshness state | Add ordered aggregate module state, refresh triggers, repair merge, receipt lifetime | changed provider contract | #1943 |
| Cockpit web status components and Shell | Task findings, Repair, generic Cleanup | Render module status and retained receipt; remove Cleanup/task-only scan path | changed user workflow | #1944 |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|-------------------|-------------|----------------------|-----------------------------|
| Complete read-only task/file/graph/location health | #1937 | Kanban public task-health method on real storage | real-filesystem behavior check; no scanner replacement |
| Invalid, duplicate, orphaned, and drifted requests remain observable | #1939 | Kanban public request-health method | real-filesystem behavior check; no parser replacement |
| Complete-set repair converges, fixes archive drift, and preserves ambiguity | #1940 | Kanban public repair method on real storage | data-safety behavior check; no mutation-layer replacement |
| Claims and activity remain outside health repair | #1941 | Kanban maintenance and repair public surfaces | real engine behavior/API inventory |
| Memory unreadable/duplicate evidence does not judge lifecycle states | #1938 | Memory public health method | real-filesystem behavior plus lifecycle regression |
| Root aggregate/focused HTTP, ideas semantics, and synchronous repair | #1942 | Assembled FastAPI application | inject at most one lower checker failure |
| Gray transient state, ordered refresh, and no repair follow-up GET | #1943 | Real provider/hooks at fetch boundary | controlled fetch responses only |
| Four module indicators and retained repair receipt | #1944 | Assembled Workspace Status and running Cockpit | package checks plus integrated browser |
| Complete normal user journey | #1945 | Running Cockpit at one tested commit | verified child evidence plus integrated-browser observation |

### Decomposition: Trustworthy Workspace Health
- Tasks created: 8 build leaves plus this collect parent.
- Dependency layers: 6.
- Phase: 1.
- Fragmentation rationale: eight leaves are required by distinct owners, failure domains, and proof boundaries: Kanban task analysis, request integrity, destructive repair, lease maintenance, memory diagnostics, Cockpit HTTP assembly, frontend concurrency state, and browser-visible interaction. Combining them would cross package or safety boundaries; splitting further would create forwarding-only work.

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| #1937 | Kanban task and graph health evidence | high | none | phase-1, scope:kanban, integrity |
| #1939 | Kanban request storage health | medium | #1937 | phase-1, scope:kanban, requests |
| #1940 | Deterministic Kanban task repair | medium | #1937 | phase-1, scope:kanban, repair, data-safety |
| #1941 | Separate Kanban lease maintenance | medium | #1940 | phase-1, scope:kanban, maintenance |
| #1938 | Memory storage health | medium | none | phase-1, scope:memory, integrity |
| #1942 | Cockpit health and repair HTTP contracts | high | #1937, #1938, #1939, #1940, #1941 | phase-1, scope:cockpit-backend, api, health |
| #1943 | Ordered Cockpit health state | medium | #1942 | phase-1, scope:cockpit-web, state, concurrency |
| #1944 | Module-aware Workspace Status and repair feedback | medium | #1943 | phase-1, scope:cockpit-web, ui, health |

### Dependency Graph
- #1937 is prerequisite to #1939 and #1940; #1940 is prerequisite to #1941.
- #1937, #1938, #1939, #1940, and #1941 are prerequisites to #1942.
- #1942 is prerequisite to #1943; #1943 is prerequisite to #1944.
- #1937 through #1944 are prerequisites to this collect parent.

### Challenger Result
- First challenge: failed for four omitted acceptance outcomes: archive drift detection, successful archive reconciliation, two unresolved duplicate-set classes, and unreadable ideas.
- Corrections: added within #1937, #1940, and #1942 without changing scope, architecture, tasks, or dependencies.
- Second full challenge: passed product/spec coverage, authority grounding, invariant ownership, proof boundaries, dependencies, task sizing, and fragmentation review.

### Board Audit
- Pending concrete parent-link and metadata audit after parent creation.

[[2026-07-17T02:34:30+02:00]]
## Shape Notes

### Board Commit Closure
- Source and mode: OpenSpec `redesign-workspace-health`; spec-shaping commit after staged user review, not task repair.
- User decisions: health covers tasks, requests, memory, and ideas; the API is the root health family with synchronous task repair; transient state is gray; repair works on complete duplicate sets and never renumbers IDs; the response includes post-repair task health; the frontend retains the receipt; generic Cleanup is removed; claim/session sweep and activity compaction remain explicit; memory purge is excluded.
- Planning revisions: proposal, workspace-health spec, design, and advisory tasks under `openspec/changes/redesign-workspace-health/` were reconciled and passed strict validation. Challenger corrections added archive-drift detection and successful movement, both omitted unresolved duplicate classes, unreadable ideas behavior, ideas non-mutation, and explicit deterministic repair actions.

### Readiness And Authorities
- Product invocation: open Workspace Status, observe gray then four module results, invoke deterministic task repair when offered, and retain or dismiss its receipt.
- Current owners were observed in Kanban corruption/engine/request storage, memory models/engine, Cockpit FastAPI main/routes/view, and Cockpit web provider/hooks/status components. OpenSpec proposal/spec/design remain product and technical planning authority; `MemoryState` is canonical for lifecycle literals.
- Normal proof boundaries are real-filesystem domain methods, the assembled FastAPI app, provider/hooks with only fetch controlled, and the running Cockpit in the VS Code integrated browser.
- Completion removes old task scan/repair/cleanup routes and generic Cleanup while retaining explicit maintenance and the accepted exclusions.

### Change Module Map
- #1937 owns Kanban task/file/graph/location evidence; #1939 owns request evidence; #1940 owns destructive task repair; #1941 owns lease/session/activity maintenance separation.
- #1938 owns memory diagnostics; #1942 owns root HTTP aggregation, ideas integrity, synchronous repair, and obsolete-route removal.
- #1943 owns ordered frontend state and receipt lifetime; #1944 owns the module-aware Workspace Status and repair interaction.

### Product Invariant Map
- #1937 proves complete non-mutating task evidence; #1939 proves malformed/duplicate/orphan/drifted requests remain observable.
- #1940 proves convergent complete-set repair and archive movement while preserving ambiguity; #1941 proves claims/activity remain outside health.
- #1938 proves memory evidence without lifecycle judgment; #1942 proves aggregate/focused HTTP, ideas semantics, and synchronous repair.
- #1943 proves gray ordered refresh and no immediate repair follow-up GET; #1944 proves four module indicators and retained feedback; #1945 collects the complete running-Cockpit journey at one tested commit.

### Final Graph And Challenger
- Build leaves: #1937, #1938, #1939, #1940, #1941, #1942, #1943, #1944. Collect parent: #1945.
- Dependency order: #1937 precedes #1939 and #1940; #1940 precedes #1941; #1937-#1941 including independent #1938 precede #1942; #1942 precedes #1943; #1943 precedes #1944; the eight leaves precede #1945.
- Eight leaves are justified by separate package owners, destructive-versus-read-only safety boundaries, HTTP assembly, frontend concurrency, and browser interaction. Combining them would cross failure/proof domains.
- First challenger run failed on four omitted outcomes. They were corrected without changing graph shape. The second full run passed coverage, authority, invariant ownership, proof boundaries, dependencies, task sizing, and fragmentation.

### Board Audit
- MCP audit found nine records with no missing IDs.
- #1937-#1944 are in `build`; #1945 remains in `collect`.
- Each leaf has parent #1945. Parent #1945 depends on the eight leaf IDs.
- Leaf dependencies exactly match the approved graph. #1937 and #1938 are initially dispatchable; dependent leaves and the parent report dependency blocking as intended.
- Every task has three persisted AC lines, explicit scope, proof guidance, priority, and phase/scope/category tags. Product Promise coverage matches the invariant map; no material post-approval scope was introduced.

[[2026-07-17T07:22:28+02:00]]
## Verify Notes
- Task was claimed for verification dispatch.
- Routing check: task 1945 is an aggregate in `collect`, while verifier authority is restricted to `verify` tasks.
- Dependency check: child tasks 1939 through 1944 remain unresolved; aggregate AC cannot yet be verified at a tested commit.
- Evidence reviewed: authoritative task record and declared dependencies.
- Named authorities checked: task Outcome, Scope, Proof Guidance, Shape Notes, and AC.
- Change Module Map deviations: not evaluated because no collect-stage aggregate proof is available and verifier cannot process this status.
- Normal-path boundary: not exercised; task must remain available for collector once child work closes.
- Replacements used below boundary: none.
- Checks run: task status/dependency state; task-record worktree path inspection.
- Findings: no product patch applied. This was an invalid verifier dispatch rather than a verification result.
- Verifier-challenger: not invoked because no PASS verdict is proposed.
- Final route: released unchanged in `collect` for collector processing after dependencies resolve.

[[2026-07-17T08:39:58+02:00]]

[[2026-07-17T08:43:31+02:00]]
## Collect Notes

- Verdict: REJECT
- Classification: aggregate (`aggregate` tag, explicit aggregate Outcome/Scope, and eight child tasks).
- Aggregate intent source: `## Outcome`, `## Scope`, and `## Shape Notes`, sourced from OpenSpec change `redesign-workspace-health`.
- Invariant map coverage: not closable because the required assembled Workspace Status journey and single-commit aggregate proof depend on unfinished children.
- Child coverage (`parent=1945`): #1937, #1938, #1939, and #1940 are archived with reason `completed`; #1941, #1942, #1943, and #1944 remain in `shape`.
- Parent dependency gate: incomplete. Required dependencies #1941 through #1944 are unresolved; #1942 is blocked by #1941, #1943 by #1942, and #1944 by #1943. The claim response also reported these four unresolved dependencies.
- Tested commit and normal-path proof: unavailable because the child/dependency gate is incomplete; no SHA-linked assembled proof can yet satisfy the aggregate AC.
- Residual decisions: no pending request exists for #1945, and there is no recorded decision intentionally dropping the unfinished child scope.
- Rationale: aggregate archival requires every required child to be complete and parent intent to be proven or explicitly dropped. Those conditions are not met.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | shaper via `/shape` | Reconcile the aggregate graph: route and complete required children #1941 through #1944, or record an approved scope decision that explicitly drops them; return the parent to collect only with a complete dependency gate and SHA-linked assembled normal-path proof. | n/a | Child lookup and parent dependency gate show #1941-#1944 remain in shape, with #1942-#1944 dependency-blocked. |
