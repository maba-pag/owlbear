---
id: 1987
title: 'Bootstrap DN-010: Provide graph-aware Cockpit backend contracts and events'
status: archived
priority: high
created: 2026-07-22T01:08:21.141570+02:00
updated: 2026-07-26T00:15:14.166930+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-010
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1979
  - 1980
  - 1985
  - 1986
  - 2066
  - 2067
  - 2068
  - 2069
  - 2070
ac:
  - 'AC-1: Shaper replaced the stale projection with five build-ready packet tasks
    whose records reference change `replace-delivery-pipeline`, digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`,
    and node `DN-010`; Kanban field and dependency queries verify the DAG against
    modular authority.'
  - 'AC-2: Packet scope remains within DN-010 modules, IF-011, MIG-003, RISK-005,
    and PROOF-015; artifact and task diff inspection verifies frontend rendering,
    immutable snapshot generation, repository cutover, and complete-system proof remain
    assigned to DN-011 through DN-013.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` after #2066-#2070
    exist in `build` with concrete dependency closure; Collector archives only after
    descendant Verify Notes and SHA-bound PROOF-015 evidence satisfy DN-010.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`
- `delivery_node_id`: `DN-010`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990|DN-010|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`

## Authority Reference
Resolve DN-010 from modular `delivery/nodes.yaml`; resolve REQ-010, REQ-015, REQ-016, REQ-021, KEEP-006, and KEEP-007 from `delivery/obligations.yaml`; resolve IF-011, MIG-003, RISK-005, and PROOF-015 from `delivery/contracts.yaml`.

Outcome: FastAPI exposes typed change, graph, job, request, attempt, finding, receipt, invalidation, health, legacy, conflict, and SSE resources over the real graph-aware engine without arbitrary task transitions.

## Shaping Boundary
DN-010 owns the Cockpit backend HTTP/SSE adapter and backend task-route cutover. Core native models and runtimes remain canonical. DN-011 owns peer Specification/Delivery rendering; DN-012 owns immutable legacy snapshot generation and repository-wide cutover; DN-013 owns complete-system proof.

## Shape Notes
The prior `9387...` monolithic projection is replaced by the admitted modular digest above. The stock OpenSpec CLI does not discover `.owlbear/changes`; canonical modular files and admission receipt were inspected directly. Current source verifies `load_change`, `NativeRuntime`, `DispatchRuntime`, `NativeRequestRuntime`, runtime pages/stores, proof checkouts, FastAPI, SSE, and legacy reads.

### Change Module Map
- #2066: Cockpit dependencies plus cohesive native context/models/change routes; new IF-011 change/graph reads.
- #2067: native work/evidence/health routes; reuses core projections and stores.
- #2068: request-resolution and claim-release routes plus centralized diagnostic HTTP mapping.
- #2069: SSE, legacy read projection, and assembled router registration/removal.
- #2070: maintained FastAPI integration proof only.

### Product Invariant Map
- REQ-021 and PROOF-015: #2070 owns assembled HTTP/SSE proof; #2066-#2069 provide prerequisites.
- REQ-015: #2068 owns request-resolution visibility and conflicts.
- REQ-016 and KEEP-007: #2067 health plus #2068 atomic conflict proof.
- REQ-010 and KEEP-006 backend prerequisites: #2067 and #2070; frontend remains DN-011.

### Dependency Closure Map
#2066 consumes current change/runtime/context types. #2067 consumes #2066 context and current native query/store APIs. #2068 consumes #2067 identities plus current request and dispatch controls. #2069 consumes #2066-#2068 routes, canonical path layout, current SSE library, and legacy reads. #2070 consumes the assembled public outputs of #2066-#2069. PROOF-015 permits only a temporary engine store replacement.

### Scenario Closure Map
#2066 covers loaded, malformed, missing, changed digest, and assembly failure. #2067 covers empty/populated pages, stale cursor, missing identities, supersession, and health findings. #2068 covers success, replay, changed/non-owner/terminal identity, malformed input, and transaction failure. #2069 covers create/modify/delete/mixed events, noise, disconnect, missing roots, legacy inventory, and old-route absence. #2070 covers the assembled normal journey plus malformed, missing, stale, core-failure, and retired-route classes.

### Final Graph
`#2066 -> #2067 -> #2068 -> #2069 -> #2070`, with #2069 also directly depending on #2067. Five build-ready packets stay within MOD-004/MOD-008 and IF-011. Shaper challenger: pass. Standing user direction to finish the admitted research plan authorizes this unchanged-authority graph.

[[2026-07-25T22:32:06+02:00]]
## Shape Notes
APPROVED GRAPH

Replaced the stale `9387...` monolithic projection with admitted modular digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`. Grounded DN-010, REQ-021, IF-011, MIG-003, RISK-005, and PROOF-015 in canonical authority and verified current Cockpit/core owners.

Created five build-ready packets: #2066 native context and change/graph reads; #2067 paged work/evidence/invalidation/health reads; #2068 request resolution and claim release conflicts; #2069 native SSE, read-only legacy inventory, and backend route cutover; #2070 assembled PROOF-015. Concrete dependency audit matches `#2066 -> #2067 -> #2068 -> #2069 -> #2070`, with #2069 also depending on #2067. Frontend, immutable snapshot/global deletion, and complete-system proof remain DN-011 through DN-013. Shaper challenger: pass.

[[2026-07-26T00:15:14+02:00]]
## Collect Notes
ARCHIVED: DN-010 aggregate is complete at admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

Aggregate closure:
- Descendants #2066-#2070 are all archived completed with builder, verifier, challenger, and collector evidence.
- Final tested verifier SHA `fcfc2e72991ec6d3045e27ccb6e89a5fa5aa4870` is an ancestor of HEAD.
- Fresh aggregate execution of maintained `tests/test_cockpit_native_integration.py`: 3 passed, covering complete IF-011/PROOF-015 assembled HTTP/SSE journey, controls, strict schemas, stable errors including real core assembly failure, non-mutation, legacy inventory, and old-route absence.
- Scope remained within DN-010: frontend rendering, immutable snapshot/global cutover, and complete-system proof remain DN-011 through DN-013.
- No descendant, request, block, or follow-up remains open.

Collector memories were assessed before archive.
