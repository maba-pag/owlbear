---
id: 1988
title: 'Bootstrap DN-011: Build the graph-aware Cockpit Changes and Kanban experience'
status: archived
priority: high
created: 2026-07-22T01:08:34.349450+02:00
updated: 2026-07-27T01:14:20.211796+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-011
  - scope:core
  - type:shape
  - rigor:thorough
  - digest:bf5edd67478d
  - corrective-projection
parent: 1968
depends_on:
  - 2079
  - 2080
  - 2081
  - 2082
  - 2083
  - 2084
  - 2085
ac:
  - 'AC-1: Shaper replaces the stale `9387...` projection with change `replace-delivery-pipeline`,
    digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`, node
    `DN-011`, and six build-ready DN-011 leaves; Kanban queries verify their identity,
    parent, status, and dependency fields.'
  - 'AC-2: Shaper keeps leaves within MOD-005/MOD-008, IF-012, RISK-010/RISK-012,
    and PROOF-012; task/artifact diff inspection verifies #2071/#2079 separately own
    core/backend corrections and DN-012 snapshot/cutover plus DN-013 complete-system
    proof remain absent from leaf scope.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` after #2071-#2085
    exist with concrete dependency closure; Collector archives only after descendant
    Verify Notes and SHA-bound PROOF-012 evidence satisfy DN-011, verified through
    Kanban queries and artifact inspection.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`
- `delivery_node_id`: `DN-011`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357|DN-011|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-bf5edd67478d.yaml`

## Authority Reference
Resolve DN-011 from modular `delivery/nodes.yaml`; resolve REQ-010, REQ-016, REQ-026, KEEP-006, and KEEP-010 from `delivery/obligations.yaml`; resolve IF-012, RISK-010, RISK-012, and PROOF-012 from `delivery/contracts.yaml`.

Outcome: Cockpit presents peer accessible scalable Specification and Delivery surfaces with change authority, graph/list/plans, immutable-purpose jobs, requests, evidence/current and corrective history, exact commits, legacy inventory, and unchanged Memory/Ideas continuity across desktop and mobile.

## Shaping Boundary
DN-011 owns frontend IF-012 and assembled browser PROOF-012. Corrective core priority/cancel work is #2071 under DN-003; corrective HTTP work is #2079 under DN-010. DN-012 owns snapshot/setup/global cutover; DN-013 owns complete-system proof. Memory and Ideas are continuity-only under DEC-035/KEEP-010 and receive no feature expansion.

## Shape Notes
Replaced stale `9387...`/`graph.yaml` projection with admitted modular digest `bf5edd...` and receipt `admission-bf5edd67478d`. The authority amendment assigns already-designed prioritize/cancel behavior through DEC-034/REQ-026/IF-003/IF-011/IF-012 and preserves Memory/Ideas route continuity through DEC-035/KEEP-010/IF-012/PROOF-012. Production admission evaluation returned zero findings; canonical revision/admission tests passed 37; exact digest approval was recorded through VS Code.

### Change Module Map
- #2080: typed native clients/hooks, error/page/SSE data boundary.
- #2081: routes, shell/provider, change selection, Specification authority surface.
- #2082: scalable graph outline/optional visualization, filters, plans, virtualization.
- #2083: immutable-purpose Delivery board/cards/detail/actions; replaces task mutation UI.
- #2084: native Requests and conflict-preserving resolver; replaces Decisions flow.
- #2085: Activity/Evidence/Legacy, route retirement, retained Memory/Ideas continuity, real-stack PROOF-012.
- Prerequisites #2071/#2079 own core/backend administrative controls outside MOD-005.

### Product Invariant Map
- Typed retained native data: #2080 over IF-011.
- Peer Specification/Delivery: #2081.
- Graph/list/plan navigation at hundreds scale: #2082.
- Immutable operational board and intent-specific actions: #2083.
- User-resolved native requests: #2084.
- Current/full evidence, legacy, preserved utilities, desktop/mobile assembled workflow: #2085 under PROOF-012.

### Dependency Closure Map
`#2071 -> #2072 -> #2073 -> #2074 -> #2075 -> #2076 -> #2077 -> #2078 -> #2079 -> #2080 -> #2081`, then `#2081 -> #2082` and `#2081 + #2079 -> #2083`, `#2083 -> #2084`, and `#2082 + #2083 + #2084 -> #2085`. #1988 depends on #2079 and #2080-#2085. Frontend sends explicit candidate revision `HEAD`; no new backend revision default is invented.

### Scenario Closure Map
#2080 covers success/error/page/stale cursor/SSE disconnect. #2081 covers loaded/invalid/missing and desktop/mobile shell. #2082 covers planned/unplanned/filter/no-match/14-vs-300 nodes/constrained viewports. #2083 covers four kinds plus ready/blocked/claimed/request/current/stale and control conflicts. #2084 covers decision/action, pending/resolved, local/material, and authority conflicts. #2085 covers current/full/stale/superseded history, missing evidence, truncated legacy, preserved utilities, scale, keyboard, desktop/mobile blank/overlap geometry.

### Product Promise Coverage
Product Promise item 8 is owned across #2081-#2085. DEC-034/REQ-026 controls are prerequisites #2071/#2079 consumed by #2083. DEC-035/KEEP-010 continuity is owned and proven by #2085 without expanding Memory/Ideas. Product Promise item 9 remains DN-012.

### Final Graph
Six DN-011 leaves: `#2080 -> #2081 -> {#2082,#2083} -> #2084 -> #2085`, where #2085 joins #2082/#2083/#2084. Corrective prerequisite chain terminates at #2079. Independent shaper challenge passed after stale authority, ownership, candidate-impact, and preservation findings were resolved. User approved the exact candidate digest and the concrete graph.

[[2026-07-26T02:02:38+02:00]]
## Shape Notes
APPROVED GRAPH: Reconciled DN-011 to admitted digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357` and created six build-ready leaves #2080-#2085. Corrective core/backend prerequisites #2071/#2079 plus graph-ordered candidate re-acceptance #2072-#2078 are separately parented to #1968. Concrete audit confirmed statuses, parents, digest tags, dependencies, proof bundles, and blocked ordering. Memory/Ideas continuity is preservation-only under DEC-035/KEEP-010/PROOF-012. Independent challenge passed after stale projection, obligation ownership, impact closure, and proof-boundary findings were resolved. User approved the exact digest; admission receipt and jobs were atomically published. Shaper memories were assessed before closure.

[[2026-07-27T01:14:20+02:00]]
## Collect Notes
ARCHIVED

Collected DN-011 against admitted digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`. Prerequisite #2079 and leaves #2080 through #2085 are archived with `completed`; their recorded dependencies and ownership preserve the approved graph and keep DN-012 cutover plus DN-013 complete-system proof outside this aggregate.

PROOF-012 is SHA-bound to builder commit `6e96b61d124d20b8c9d33e15c3d9369463bc9f8c`, verifier evidence commit `82b6ce2ce04cb75217e2345d45e46c18d5d8b482`, and packet archive commit `ddee0ca000b1af31e87453532cccf97f13e44ea3`; all are ancestors of the collection snapshot. The proof covers the peer Specification/Delivery experience, native requests and immutable history, final routes and legacy retirement, unchanged Memory/Ideas, desktop/mobile geometry and keyboard behavior, and the 300-node bounded scale case.

DN-011 AC-1 through AC-3 are satisfied; aggregate archived completed.
