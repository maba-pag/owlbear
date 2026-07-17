---
id: 1958
title: 'P1-22: Deliver trustworthy Cockpit memory lifecycle'
status: collect
priority: high
created: 2026-07-17T04:54:45.298830+02:00
updated: 2026-07-17T04:55:03.609524+02:00
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
archival_reason:
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
