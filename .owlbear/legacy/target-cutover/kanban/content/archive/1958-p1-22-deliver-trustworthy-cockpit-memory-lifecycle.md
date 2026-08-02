---
id: 1958
title: 'P1-22: Deliver trustworthy Cockpit memory lifecycle'
status: archived
priority: high
created: 2026-07-17T04:54:45.298830+02:00
updated: 2026-07-21T10:42:16.423200+02:00
tags:
  - phase-1
  - scope:cockpit
  - aggregate
  - memory
parent:
depends_on:
  - 1952
  - 1953
  - 1954
  - 1955
  - 1956
  - 1957
  - 1960
  - 1967
ac:
  - 'AC-1: At one delivered commit, running Cockpit with approved, contested, disputed,
    stale, and deleted entries shows score-led ordering, seven-state filtering, the
    documented detail and edit context, contested-task navigation, exceptional resolution,
    and no deleted edit action without incoherent overlap at desktop and mobile viewports.'
  - 'AC-2: At that commit or a descendant, real MCP curation rejects contested, disputed,
    and stale entries while Cockpit edit and resolve succeed for those states, proving
    the final caller-authority split.'
  - 'AC-3: Child Verify Notes and maintained documentation account for the requested
    fields and exclusions: no score colors, pinning, confidence marker, raw unremarkable
    or non-use counters, or MCP resolve operation.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Cockpit is the complete human management surface for current memory entries: score-led scanning, complete operator-relevant details, non-deleted editing, active challenge navigation, and explicit exceptional-state recovery, while the final agent surface remains restricted.

## Planning Source
- OpenSpec change: `openspec/changes/expose-memory-lifecycle-in-cockpit`
- Strict validation passed after staged product, architecture, and completion review.

## Scope
- Aggregate closure and assembled proof only.
- No direct implementation; child tasks own domain, adapter, HTTP, frontend, and documentation changes.

Proof guidance: collector uses verified child evidence plus running-Cockpit browser interactions and screenshots at the delivered commit; real MCP and Cockpit adapter checks must prove the authority split at that SHA or a descendant.

## Shape Notes

### Source And Review Mode
- Mode: native OpenSpec shaping.
- Product review: confirmed by user.
- Architecture review: confirmed after source verification.
- Completion/proof review: confirmed by user.

### User Decisions And Artifact Revisions
- Score has no color, pin, or confidence marker; score, scope agents, and categories remain in overview and details.
- Outstanding count is labeled `Outstanding marks` with a star icon and count.
- Exceptional editing and resolution are human-only through Cockpit; MCP has no resolve tool and final exceptional curation remains blocked.
- Stale resolution resets only didnt_use_count.
- Engine-first sequencing was selected, accepting temporary MCP exceptional-edit authority until dependent task #1953 restores the final boundary.
- Proposal and Design record that sequencing trade-off.
- Spec, Design, and advisory Tasks were revised after challenge to require score recomputation whenever confidence changes.

### Brief Readiness
- Product outcome and invocation: Open Cockpit Memory, scan score-ranked entries, expand/edit details, navigate active contest provenance, and explicitly resolve exceptional entries.
- Existing-system fit and authority: canonical MemoryEngine plus distinct MCP-agent and Cockpit-human adapters; existing FastAPI errors and Cockpit task-detail event are reused.
- Normal-path proof: running Cockpit Memory workflow with representative lifecycle states; lower persistence/fetch dependencies may be replaced only below the exercised engine, endpoint, or frontend boundary.
- Completion and change contract: preserve approved-to-curated edits, deleted tombstones, confidence bounds, OCC, score formula, and normal MCP curation; exclude score colors, pinning, raw negative counters, and MCP resolution.

### Contract Authorities
| Claim | Authority | Evidence State | Confidence |
|---|---|---|---|
| Entry fields, seven states, score, edit, resolve, and factual-report transitions | `serve/memory/src/owlbear_memory/models.py`, `engine.py` | observed | 1.0 |
| Agent curation path and registered MCP tools | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py`, `server.py` | observed | 1.0 |
| Operator HTTP projection, mutations, and error envelope | `serve/cockpit/src/owlbear_cockpit/routes/memory.py`, `main.py` | observed | 1.0 |
| Frontend memory type, ordering, filters, detail, and edit owner | `serve/cockpit/web/src/api/memories.ts`, `pages/MemoryTab.tsx` | observed | 1.0 |
| Cross-page task navigation | `serve/cockpit/web/src/utils/openTaskDetail.ts`, Shell listener | observed | 1.0 |
| Product behavior | OpenSpec `cockpit-memory-lifecycle` capability | documented | 1.0 |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|---|---|---|---|---|
| `serve/memory/src/owlbear_memory/engine.py` | Canonical lifecycle and scoring | Exceptional edit, score, provenance, stale recovery | Changed domain behavior | #1952 |
| `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` and server registry | Agent adapter and tool surface | Relocate exceptional guard; retain no resolve tool | Public surface unchanged | #1953 |
| Cockpit memory backend routes and handlers | Operator HTTP contract | Expanded projection and resolve endpoint | Changed/new HTTP contract | #1954 |
| Cockpit memory API type and Memory page | Sorting, filters, details, editing | Score-led seven-state presentation | Changed UI contract | #1955 |
| Memory page, HTTP client, task event/Shell integration | Mutations and cross-page navigation | Resolve and contested-task actions | New interaction | #1956 |
| Memory and MCP README files | Canonical lifecycle/tool documentation | Align shipped behavior and authority | Documentation changed | #1957 |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|---|---|---|---|
| Exceptional correction preserves lifecycle; score and recovery history remain coherent | #1952 | MemoryEngine methods with persisted reload | Focused domain proof; filesystem below engine may be temporary |
| Final agent surface cannot edit or resolve exceptional entries | #1953 | Real MCP curate operation and registry | MCP adapter proof; canonical engine remains real |
| Cockpit projection and OCC resolution match contract | #1954 | FastAPI application endpoints | Route proof; persistence below route may be replaced |
| Overview, details, and edit context match confirmed fields/states | #1955 | Rendered Memory page | Component proof with API-shaped data |
| Contest navigation and resolve feedback work through Cockpit integration | #1956 | Memory page plus Shell event/client boundary | Frontend integration; network below client may be replaced |
| Canonical docs match shipped lifecycle and authority | #1957 | Maintained README artifacts | Artifact inspection |
| Complete human workflow and final caller-authority split | this aggregate | Running Cockpit plus real MCP surface | Browser and adapter evidence tied to delivered SHA |

### Challenger Result
- `shaper-challenger`: pass.
- No approval defect found; full Product Promise, exclusions, domain boundaries, AC quality, and assembled proof were covered.
- Corrective finding incorporated: confidence edits now recompute score.
- Non-blocking over-serialization of #1954 behind #1953 retained to ensure no downstream Cockpit work starts before the final MCP guard is restored.

### Decomposition
- Build leaves: #1952 through #1957.
- Aggregate: this task in collect.
- Dependency layers: core lifecycle, MCP authority, Cockpit HTTP, frontend presentation/interactions, aggregate closure.
- Phase: 1.



### Board Audit
- Audited concrete records with `list_tasks(ids=[1952,1953,1954,1955,1956,1957,1958])`.
- #1952 through #1957 are build-ready leaves in `build`; #1958 is the aggregate in `collect`.
- #1958 depends on all six leaves; each leaf has parent #1958.
- Leaf dependencies match the approved graph: #1953 after #1952; #1954 after #1952 and #1953; #1955 after #1954; #1956 after #1954 and #1955; #1957 after #1952, #1953, and #1954.
- No task is blocked or claimed; dependency status is consistent with the active graph.

[[2026-07-17T18:19:03+02:00]]
## Collect Notes

- Classification: aggregate. Intent source is `## Outcome`, `## Planning Source`, `## Scope`, and the explicit aggregate AC-1 through AC-3 for OpenSpec change `expose-memory-lifecycle-in-cockpit`.
- Invariant map: AC-1 requires one delivered commit proving the assembled running-Cockpit desktop/mobile lifecycle; AC-2 requires real MCP rejection plus Cockpit exceptional edit/resolve at that SHA or a descendant; AC-3 requires child verification and maintained documentation for requested inclusions and exclusions.
- Child coverage: `list_tasks(parent=1958)` returned no active tasks because all six children are archived; direct dependency lookup confirmed #1952 through #1957 each retain `parent: 1958`, are archived with reason `completed`, and have no block. Child Verify Notes cover engine lifecycle, MCP authority, Cockpit HTTP projection/resolve, frontend overview/detail editing, exceptional recovery/navigation, and maintained documentation.
- Dependency gate: parent `depends_on` is exactly #1952 through #1957 and reports `dep_status: ok`.
- Child completion summary: #1952, #1953, #1954, #1955, #1956, and #1957 are archived completed. No pending decision or action request exists for the parent or any child.
- Tested commit and aggregate normal-path proof: missing. Child notes cite component commits and focused package checks, but the aggregate record has no tested delivered commit SHA tied to running-Cockpit browser interactions/screenshots across desktop and mobile, and no command or artifact at that SHA or a descendant jointly proving real MCP exceptional curation rejection with Cockpit exceptional edit and resolve success.
- Residual decisions: none pending.
- Rationale: reject because aggregate AC-1 and AC-2 require SHA-linked assembled proof; archived child evidence alone cannot substitute for that explicit collector proof contract.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | shaper via `/shape` | Restore an executable aggregate closure path that names the delivered commit and requires running-Cockpit desktop/mobile browser evidence plus real MCP and Cockpit authority-split evidence at that SHA or a descendant. | n/a | Aggregate AC-1, AC-2, and Proof guidance lack SHA-tied assembled evidence in the task record. |

[[2026-07-17T20:19:26+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: latest Collect Notes and Required Follow-up on aggregate #1958.
- Classification: prescribed split. Collector supplied a complete non-material requirement: restore an executable aggregate closure path tied to a delivered commit SHA with running-Cockpit desktop/mobile proof and real MCP/Cockpit authority-split proof.
- No product outcome, architecture, compatibility, security boundary, or acceptance meaning changed.

### Facts Checked
- Child tasks #1952 through #1957 are archived completed, retain parent #1958, and satisfy the implementation dependency gate.
- Aggregate AC-1 and AC-2 already require SHA-linked assembled proof; the failure was missing evidence ownership, not missing implementation scope.
- Collectors cannot manufacture the required browser and MCP evidence from archived child notes, so a build/verify leaf is the smallest executable closure path.
- Supported proof routing includes `critical+challenge`, selected because this evidence crosses running browser, Cockpit HTTP/adapter, and real MCP authority boundaries.

### Exact Task And Dependency Changes
- Created #1960 `P1-23: Prove assembled Cockpit memory lifecycle` in build with priority high, parent #1958, and dependencies #1952 through #1957.
- #1960 records one delivered commit SHA, desktop/mobile running-Cockpit interactions and screenshot references, real MCP rejection for contested/disputed/stale entries, real Cockpit exceptional edit/resolve success, and documentation/exclusion coverage.
- #1960 is proof-only by explicit collector requirement; it makes no planned product changes. Concrete defects discovered during proof must be returned with evidence rather than silently expanding scope.
- Added #1960 as a dependency of #1958.

### Change Module Map
| Boundary | Current Responsibility | Planned Proof | Owner |
|---|---|---|---|
| Running Cockpit Memory UI | Delivered score-led lifecycle management | Desktop/mobile assembled workflow at recorded SHA | #1960 |
| Cockpit memory HTTP/adapter | Human exceptional edit and resolution | Real Cockpit boundary success for contested/disputed/stale states | #1960 |
| MCP memory curation | Restricted exceptional-state authority | Real operation rejection for contested/disputed/stale states | #1960 |
| Aggregate lifecycle delivery | Collect child implementation and assembled evidence | Archive only after #1960 verification | #1958 |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof |
|---|---|---|---|
| Complete human memory workflow is usable without desktop/mobile overlap | #1960 | Running Cockpit | Browser interactions and screenshot references tied to SHA |
| Final MCP authority rejects exceptional curation while Cockpit succeeds | #1960 | Real MCP plus real Cockpit adapter/HTTP | Commands and observed responses tied to same SHA or descendant |
| Requested inclusions and exclusions remain documented and delivered | #1960 | Maintained docs plus verified child evidence | SHA-linked inventory check |
| Aggregate product promise closes only with assembled proof | #1958 | Collector review | Verified #1960 evidence plus archived children |

### Resulting Route And Board Audit
- #1960 routes to build and is dependency-ready because #1952 through #1957 are completed.
- #1958 returns to collect and now depends on #1952 through #1957 plus #1960.
- No challenger was required for this complete prescribed split; `critical+challenge` requires the proof task's builder challenger before completion.
- Collector should re-enter #1958 only after #1960 is verified and archived, then inspect its recorded SHA, commands, browser evidence, screenshot references, and authority-split results.

[[2026-07-21T10:42:16+02:00]]
## Collect Notes

Classification: aggregate parent. Intent authority is `## Outcome`, `## Planning Source`, `## Scope`, `## Shape Notes`, and aggregate AC-1 through AC-3 for `expose-memory-lifecycle-in-cockpit`.

Invariant map:
- AC-1 requires one delivered commit proving the assembled desktop/mobile Cockpit lifecycle across approved, contested, disputed, stale, and deleted entries.
- AC-2 requires real MCP exceptional-curation rejection and real Cockpit exceptional edit/resolve success at that commit or a descendant.
- AC-3 requires verified child and maintained documentation coverage for the requested fields and explicit exclusions.

Child and dependency coverage: `list_tasks(parent=1958)` returned no active tasks. Direct lookup confirmed all eight declared children, #1952 through #1957, #1960, and #1967, retain `parent: 1958` and are archived with reason `completed`. Parent `depends_on` lists exactly those eight children and reports `dep_status: ok`.

Child evidence summary: #1952 verifies exceptional engine editing, provenance, resolution, score recomputation, and stale recovery; #1953 verifies final MCP rejection and absence of a resolve operation; #1954 verifies the Cockpit projection, edit, resolve, and error contract; #1955 verifies score-led overview and detail/edit behavior; #1956 verifies task navigation and exceptional recovery interactions; #1957 verifies maintained engine/MCP documentation; #1967 verifies the complete frontend lifecycle client contract; #1960 verifies the assembled cross-boundary workflow.

SHA-linked normal-path proof: archived child #1960 records verifier and verifier-challenger PASS at exact delivered commit `8fbcdb7002d1040242addbc9b3135c1067e7a41f`. Its detached-checkout run passed the production Cockpit plus real MCP stdio plus desktop/mobile Playwright workflow, captured four responsive screenshots, captured real Cockpit edit/resolve responses for contested, disputed, and stale, and produced a receipt showing state-specific real MCP `curate_memory` rejection with no mutation and no resolve operation. Focused backend checks passed 58 tests and focused MCP rejection checks passed 3 tests. Git lineage confirms the current closure commit descends from the tested SHA, and the five proof-harness paths are present in that tested commit.

Residual state: no pending or resolved structured request exists for the parent. All child archive records report no unresolved Required Follow-up or decision state. The earlier parent Collect Notes rejection is superseded because #1960 now supplies precisely the missing SHA-linked aggregate proof.

Archive rationale: the aggregate outcome and AC-1 through AC-3 are satisfied; archive as completed.
