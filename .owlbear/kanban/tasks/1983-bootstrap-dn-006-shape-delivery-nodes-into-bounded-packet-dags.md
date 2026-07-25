---
id: 1983
title: 'Bootstrap DN-006: Plan and reconcile the delivery-node frontier'
status: shape
priority: high
created: 2026-07-22T01:07:22.578615+02:00
updated: 2026-07-25T06:05:36.544373+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-006
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1979
  - 1980
  - 1982
  - 1981
  - 2037
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads current `DN-006` at digest
    `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990` and creates
    one outcome-cohesive packet DAG for a resumable planner that processes engine-selected
    initial and reconciliation `plan` jobs through IF-004/IF-007; task identities
    match the current change, digest, and node by board and authority audit.'
  - 'AC-2: Shaper keeps packet scope within current DN-006 modules, interfaces, risks,
    and PROOF-005; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by modular-authority and task diff inspection.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` only after build-ready
    packet tasks cover PROOF-005 initial frontier order, per-node atomic failure,
    acceptance-triggered reconciliation/fold-in, blocked dependent builds, and predecessor-accept
    invalidation; Collector requires descendant Verify Notes and current-SHA evidence.'
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
- `delivery_node_id`: `DN-006`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990|DN-006|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current DN-006 from `.owlbear/changes/replace-delivery-pipeline/delivery/nodes.yaml` and IF-007/PROOF-005 from `delivery/contracts.yaml`; task prose cannot add, weaken, or supersede those contracts.

- Outcome: One resumable planner processes engine-selected plan-ready nodes while each node independently publishes a complete outcome-cohesive packet plan and build/accept jobs, rejects global delivery expansion, and publishes superseding dependent plans after predecessor acceptance before dependent builds proceed.
- Modules: `MOD-001`, `MOD-003`
- Produces: `IF-007`
- Consumes: `IF-001`, `IF-002`, `IF-003`, `IF-004`, `IF-006`, `IF-010`
- Risks: `RISK-007`, `RISK-011`
- Proof: `PROOF-005`
- Delivery dependencies: `DN-003`, `DN-004`, `DN-005`, `DN-009`

## Shaping Boundary
The planner consumes the engine-side IF-004 reconciliation handoff after corrective task #2037 completes the current plan-only dispatch/MCP chain. Shaper turns this aggregate into the bounded build-packet DAG needed to satisfy current DN-006. Any new delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise the real resumable planner plus engine `finish_plan` transactions across initial frontier planning, independent per-node publication, acceptance-triggered reconciliation/fold-in, blocked dependent builds, and invalidation. Only repository search results may be replaced below the planner boundary.

[[2026-07-25T06:05:36+02:00]]
## Shape Notes

### Projection Repair
Connected non-material repair with #2035 refreshed this stale DN-006 projection from digest `9387...`, `graph.yaml`, `shape`, and `finish_shape` to admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`, modular authority, and plan/reconciliation vocabulary.

### Authority And Dependencies
- Current DN-006 produces IF-007, consumes IF-004, and owns planner publication plus full REQ-025/PROOF-005 closure.
- Added dependency #2037 so the planner cannot shape against interim engine/dispatch/MCP contracts; #2037 transitively depends on #2035 and #2036.
- Retained current delivery-node dependencies through #1979/#1980/#1982/#1981. DN-005 and DN-009 remain unresolved, so this aggregate intentionally stays in `shape` and is not dispatchable.

### Acceptance Refresh
AC now requires current-digest identity, real resumable frontier planning, initial and reconciliation plan jobs, per-node atomicity, fold-in after predecessor acceptance, blocked dependent builds, and invalidation under PROOF-005.

### Challenge And Route
Connected challenge passed after aligning IF-004 producer and DN-006 consumer ownership. Claim released with status unchanged in `shape`; resume only after current dependencies, including #2037, are complete.
