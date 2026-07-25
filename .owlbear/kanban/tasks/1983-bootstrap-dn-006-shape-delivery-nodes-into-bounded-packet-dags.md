---
id: 1983
title: 'Bootstrap DN-006: Plan and reconcile the delivery-node frontier'
status: collect
priority: high
created: 2026-07-22T01:07:22.578615+02:00
updated: 2026-07-25T15:10:06.060580+02:00
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
  - 2036
  - 2047
  - 2048
  - 2049
  - 2050
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
The planner consumes the engine-side IF-004 reconciliation handoff after #2036, gated behind #2039's core-completion fix and #2037's strict MCP bridge, completes the plan-only dispatch/orchestrator chain. Shaper turns this aggregate into the bounded build-packet DAG needed to satisfy current DN-006. Any new delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise the real resumable planner plus engine `finish_plan` transactions across initial frontier planning, independent per-node publication, acceptance-triggered reconciliation/fold-in, blocked dependent builds, and invalidation. Only repository search results may be replaced below the planner boundary.

[[2026-07-25T06:05:36+02:00]]
## Shape Notes

### Projection Repair
Connected non-material repair refreshed this stale DN-006 projection from digest `9387...`, `graph.yaml`, `shape`, and `finish_shape` to admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`, modular authority, and plan/reconciliation vocabulary.

### Authority And Dependencies
- Current DN-006 produces IF-007, consumes IF-004, and owns planner publication plus full REQ-025/PROOF-005 closure.
- Dependency #2036 keeps the planner from shaping against interim contracts; #2036 transitively depends on #2037 and #2039.
- Retained current delivery-node dependencies through #1979/#1980/#1982/#1981. DN-005 and DN-009 remain unresolved, so this aggregate intentionally stays in `shape` and is not dispatchable.

### Acceptance Refresh
AC requires current-digest identity, real resumable frontier planning, initial and reconciliation plan jobs, per-node atomicity, fold-in after predecessor acceptance, blocked dependent builds, and invalidation under PROOF-005.

### Challenge And Route
The connected graph repair preserves IF-004 producer and DN-006 consumer ownership while correcting the executable prerequisite order to `#2039 -> #2037 -> #2036 -> #1983`. Status remains `shape`; resume only after current dependencies, including #2036, are complete.

[[2026-07-25T08:08:56+02:00]]
## Shape Notes
- Connected repair updated the live prerequisite chain to `#2039 -> #2037 -> #2036 -> #1983` after #2036's assembled proof exposed independent core-completion and strict-MCP failure domains.
- Replaced direct dependency #2037 with #2036 so DN-006 shaping still waits for the complete core completion, MCP bridge, and engine/orchestrator chain.
- Preserved delivery dependencies #1979/#1980/#1982/#1981, current digest authority, scope, and AC1-AC3. Task remains intentionally parked in shape.
- Shaper-challenger passed after executable Python 3.14.6 import/compile evidence corrected an erroneous syntax concern and the assembled test reproduced #2039's exact tuple-versus-callable defect.

[[2026-07-25T15:10:06+02:00]]
## Shape Notes
Completed DN-006 decomposition from admitted modular authority at digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990` after all delivery and executable prerequisites archived.

### Source Grounding And Change Module Map
Current source already owns public `pick_jobs`, `start_job`, `finish_plan`, `finish_accept`, atomic node-plan publication, reconciliation jobs, stale-build blocking, and corrective invalidation. No engine schema or MCP expansion is required. The missing product layer is the installed frontier planner.

- #2047 owns new `share/skills/w-frontier-planning/SKILL.md`: warm-session target-bounded procedure and structured result.
- #2048 owns `planner` and hard-read-only `planner-challenger` agents plus orchestrator allowlist, `w-orchestration` native planner handoff, and `share/WIRING.md`.
- #2049 owns the initial-frontier and per-node atomicity half of durable `PROOF-005` through public native tools.
- #2050 owns acceptance-triggered reconciliation, stale dependent-build blocking, accepted-evidence fold-in, and invalidation closure over the real runtime.

### Product Invariant And Promise Coverage
- REQ-004 warm engine-selected frontier with target-bounded atomic node outputs: #2047, assembled proof #2049.
- REQ-024, RISK-011, KEEP-004 outcome cohesion and bounded context: #2047, observed in #2049 packet scenarios.
- REQ-025 acceptance-triggered reconciliation: #2050.
- NEG-008 and RISK-007 expansion refusal: #2047 workflow, #2048 independent reviewer, and #2049 mechanical public rejection.
- NEG-005 remains satisfied by outcome-cohesive packet jobs rather than artifact-specific statuses.
- WF-002 and the complete six-part PROOF-005 method split across #2049 initial/atomic classes and #2050 reconciliation/invalidation classes. No active DN-006 obligation is deferred.

### Dependency And Scenario Closure
The executable chain is `#2047 -> #2048 -> #2049 -> #2050`. #2047 consumes current admitted/query/completion contracts. #2048 consumes its structured result. #2049 consumes shipped planner artifacts and current public tools. #2050 consumes that assembled fixture plus current acceptance/reconciliation/invalidation owners. Independent risk axes are split: initial topology/success/replay/invalid authority in #2049; acceptance/reconciliation/blocked build/invalidation/disjoint preservation in #2050.

### Challenge And Board Audit
`shaper-challenger` passed after verifying the admission receipt, all DN-006 obligations and risks, current FinishPlan/FinishAccept fields, `ERR_FINISH_NODE_PLAN_INVALID`, and the real `InvalidationRuntime.apply` mutation boundary. Its non-blocking note confirms PROOF-005 requires assembled mechanical expansion rejection while reviewer judgment may remain declaration-inspected.

Created build-ready packets #2047 through #2050 with current change/digest/node/packet identities and the intended linear dependencies. The aggregate now depends on all four descendants and moves to collect; only #2047 is initially dependency-ready.
