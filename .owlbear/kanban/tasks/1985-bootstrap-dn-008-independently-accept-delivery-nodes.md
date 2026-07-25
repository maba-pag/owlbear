---
id: 1985
title: 'Bootstrap DN-008: Independently accept delivery nodes'
status: collect
priority: high
created: 2026-07-22T01:07:49.392051+02:00
updated: 2026-07-25T17:20:35.352536+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-008
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1980
  - 1983
  - 1984
  - 1981
  - 2055
  - 2056
  - 2057
  - 2058
  - 2059
ac:
  - 'AC-1: Shaper reads modular `DN-008` at digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`
    and publishes one dependency-closed packet DAG for atomic rejection, MCP reachability,
    read-only acceptance, success, and rejection proof; task-field and dependency
    audit verifies matching identities.'
  - 'AC-2: Shaper keeps scope within DN-008 obligations, IF-009, risks, and PROOF-007
    plus the corrective MCP reachability required by WF-004; module and task inspection
    proves no new finding taxonomy, delivery outcome, Cockpit behavior, setup, or
    seed work entered the graph.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` after #2055 through
    #2059 exist in dependency order; Collector requires descendant Verify Notes and
    current-SHA PROOF-007 evidence covering success, rejection, minimum correction,
    independence, failure atomicity, replay, reconciliation, and cleanup.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`
- `delivery_node_id`: `DN-008`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990|DN-008|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve DN-008 from modular `delivery/nodes.yaml`; resolve REQ-006, WF-004, NEG-003, NEG-009, and KEEP-005 from `delivery/obligations.yaml`; resolve IF-009, RISK-008, RISK-009, and PROOF-007 from `delivery/contracts.yaml`.

## Shaping Boundary
DN-008 installs independent exact-commit node acceptance over engine proof checkout, current packet receipts, typed findings, minimum corrective work, and read-only agent enforcement. Current source supplies success completion, checkout/reader coordination, findings, routes, invalidation, jobs, attempts, receipts, and transactions. The approved graph adds the missing atomic rejection composition and MCP reachability, then installs the acceptor and maintained PROOF-007 scenarios. New finding taxonomy, delivery outcomes, Cockpit behavior, setup, and seed propagation remain outside this node.

Proof guidance: exercise the real shipped acceptor through public start, finish, reject, and release operations over an engine-created checkout. Only dependencies explicitly below each fixture proof boundary may be replaced.

## Shape Notes

Approved under the user's standing authorization to complete the admitted delivery. No OpenSpec package exists for this change; admitted modular authority and current source control. Replaced the stale `9387...` projection with digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

### Final Graph
- #2055 P9-01: atomic core accept-rejection transaction.
- #2056 P9-02: corrective MCP `reject_accept`, `list_findings`, and `show_finding`; depends on #2055 and archived DN-009.
- #2057 P9-03: read-only acceptor workflow, role, and orchestrator routing; depends on #2056.
- #2058 P9-04: successful exact-commit acceptance proof; depends on #2057.
- #2059 P9-05: rejection, minimal correction, independence, failure atomicity, and cleanup proof; depends on #2058.

### Change Module Map
- #2055 owns MOD-001 changes in native finding, invalidation, attempt, job, receipt, dispatch, coordination, checkout, and transaction owners.
- #2056 owns the MOD-002 MCP slice required to make WF-004 and PROOF-007 reachable to an acceptor. It corrects an admitted control-plane omission without changing semantic authority.
- #2057 owns MOD-003 acceptor workflow/role/orchestrator declarations and derived WIRING; existing MOD-009 write guard is reused unless proof exposes a local defect.
- #2058 and #2059 own MOD-008 maintained assembled scenarios.

### Product Invariant Map
- Atomic findings, supersession, terminal attempt, minimum jobs, reader release, and cleanup: #2055.
- Public rejection and finding reachability: #2056.
- Independent tracked-read-only acceptance: #2057.
- Exact-SHA complete-node pass and dependent reconciliation: #2058.
- Local defect, missing harness, boundary bypass, stale receipt, and tracked edit cannot pass: #2059.

### Dependency Closure Map
- #2055 consumes current `Finding`, `CorrectiveRouteRequest`, `plan_corrective_route`, `InvalidationRuntime`, attempt/job/receipt stores, writer coordination, proof checkout, and `RuntimeTransaction`; it owns missing finding participants and composable invalidation preparation.
- #2056 consumes #2055's typed request/result and current MCP runtime/error conventions.
- #2057 consumes #2056 public operations plus current change/job/receipt queries and checkout-bearing start result.
- #2058 consumes #2057 shipped role and current admission, plan, build, accept, and reconciliation lifecycle.
- #2059 consumes #2055 through #2057 rejection/result/route contracts and #2058 assembled fixture.

### Scenario And Promise Closure
REQ-006 is jointly proved by #2058 success and #2059 rejection. NEG-003, NEG-009, KEEP-005, RISK-008, and RISK-009 are owned by #2057 and #2059. IF-009 spans #2055 through #2059. PROOF-007's complete-node pass is #2058; local defect, missing harness, boundary bypass, stale receipt, tracked acceptor edit, minimum correction, transaction failure, replay, and cleanup are #2059.

### Challenge And Audit
`shaper-challenger` returned `pass` after confirming source symbols, atomic composition gaps, five-task dependency closure, and scenario coverage. It requested two traceability corrections now applied: cite WF-004/PROOF-007 rather than overstate IF-010, and map REQ-006 to both success and rejection proof. Concrete board audit follows creation.

[[2026-07-25T17:20:35+02:00]]
## Shape Completion

Created and audited #2055 through #2059 in the challenged dependency order. All five leaves are `build`, parented to #1985, tagged with digest-bound change/node/packet identities, and included in this aggregate's dependency set. #2056 explicitly depends on core rejection #2055 and archived DN-009 #1981; later packets form a linear acceptor/proof chain. The aggregate identity, authority references, AC, module/invariant/dependency/scenario maps, and proof guidance now use modular digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`. Shaper challenge: pass with both requested traceability refinements applied.
