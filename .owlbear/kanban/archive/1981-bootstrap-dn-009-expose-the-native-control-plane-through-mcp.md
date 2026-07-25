---
id: 1981
title: 'Bootstrap DN-009: Expose the native control plane through MCP'
status: archived
priority: high
created: 2026-07-22T01:06:55.160360+02:00
updated: 2026-07-25T13:57:10.336104+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-009
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1980
  - 2027
  - 2028
  - 2029
  - 2030
  - 2031
  - 2040
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-009` at the recorded digest
    from modular delivery authority and publishes six outcome-cohesive packet tasks
    whose records share the change, digest, and node; verify by task-field and dependency
    audit.'
  - 'AC-2: Shaper keeps packet scope within `DN-009` modules, interfaces, risks, and
    `PROOF-011`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-009` and `PROOF-011`, verified
    through Kanban queries and artifact inspection.'
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
- `delivery_node_id`: `DN-009`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990|DN-009|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-009` in `.owlbear/changes/replace-delivery-pipeline/delivery/nodes.yaml` and referenced contracts in `delivery/contracts.yaml` and `delivery/obligations.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Strict MCP tools expose change admission, graph reads, plan/build/accept/audit dispatch and completion, requests, evidence, and health while `finish_shape`, generic task mutation, and old lifecycle tools disappear.
- Modules: `MOD-002`, `MOD-008`
- Produces: `IF-010`
- Consumes: `IF-001`, `IF-002`, `IF-003`, `IF-004`, `IF-015`
- Risks: `RISK-005`
- Proof: `PROOF-011`
- Delivery dependencies: `DN-004`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise public MCP tools over the real graph-aware engine and prove old generic task mutation/lifecycle tools and `finish_shape` are absent; only a temporary engine store may replace a lower layer below `PROOF-011`.

[[2026-07-24T23:22:58+02:00]]
## Shape Notes

Partial graph commit containment: the user approved the six-packet DN-009 graph and shaper-challenger passed after AC-boundary and `show_job` availability corrections. Created approved packets #2027 through #2031. Creation of final packet #2032 was rejected before write with `ERR_AC_ITEM_TOO_LONG`; effect check confirmed #2032 was absent at that time. Per decomposition containment, #2027-#2031 were blocked and no retry or parent projection mutation was attempted. Recovery owner: shaper. The later corrective graph used numeric #2032 for DN-001 work, so recovery must use a fresh identity for the approved sixth DN-009 packet.

[[2026-07-25T09:17:05+02:00]]
## Shape Notes

Recovered the connected `PARTIAL_GRAPH_COMMIT` for #1981 and #2027-#2031 as a prescribed local repair. Numeric #2032 had since been allocated to archived DN-001 corrective work, so the approved sixth packet was recreated under fresh identity #2040. Each recovered AC is at most 475 characters.

Refreshed the aggregate and six packets to admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`, modular delivery authority, IF-015 consumption, and plan-only vocabulary. #2028 now owns initial plan-job generation. #2040 requires the 22-tool IF-010 registry, retained eight-tool IF-015 bridge with `finish_plan`, public PROOF-011, and absence of legacy task tools and `finish_shape`.

Current-source checks found `load_change`, `evaluate_admission`, `AdmissionTransaction`, `JobGeneration`, `NativeRuntime` job/attempt/history/health queries, receipt/change health, `NativeRequestRuntime`, and all eight IF-015 operations. No resolved requests applied.

Repair Closure Map: `PARTIAL_GRAPH_COMMIT/T6-missing` closes through #2040 creation plus exact child/AC audit; `MIG-004/stale-shape-contract` closes through current `finish_plan` source and forbidden-`finish_shape` inventory; `containment/blocked-claim` closes through one-at-a-time unblock/claim and final unblocked audit. PROOF-011 must causally invoke the public MCP boundary over the real engine; registry and legacy-absence controls detect bypass.

Change Module Map: T1-T6 own `serve/mcp-kanban` models/server/tests and consume current `serve/kanban` public APIs; no core semantic changes are shaped. Product invariants: T1 authority reads, T2 atomic admission, T3 job/history reads, T4 evidence/health, T5 native request blocking, T6 assembled IF-010 and legacy absence. Dependency closure is `#2027` feeding #2028-#2031, which feed #2040; #1981 retains admitted DN-004 edge #1980 only. Scenario closure covers malformed/missing authority, admission failure/replay/recovery, paging/cursors, receipt corruption/orphan health, request reference/conflict/status, exact registry, public journey, and stable error/no-partial-mutation families.

First challenger found and corrected an invalid proposal to add child dependencies to #1981 and identified IF-010/IF-015 plus PROOF-014 as the 22-tool literal authority. Concrete graph re-challenge passed. Board audit found exactly six unblocked build children #2027-#2031/#2040 with current digest, parent links, dependencies, proof bundles, and one PK-006 identity. Aggregate routes to `collect`; descendants route through normal build/verify/collect.

[[2026-07-25T09:21:58+02:00]]
## Shape Notes

Post-route executable validation corrected the aggregate gate. `pick_tasks` selected collector #1981 in the same wave as unfinished builder #2027 when the aggregate depended only on admitted predecessor #1980. This falsified the earlier challenger recommendation and contradicted `w-task-decomposition` Step 11.

Added #2027-#2031 and #2040 as aggregate completion dependencies while preserving #1980 as the admitted DN-004 prerequisite. The child DAG is unchanged. Re-challenge passed: active child IDs make #1981 dependency-blocked, while archived-completed #1980 remains satisfied. The earlier note describing child dependencies as invalid is superseded by this executable picker evidence. Required negative control after commit: fresh `pick_tasks` must select #2027 and exclude #1981 until all six descendants archive.

[[2026-07-25T13:57:10+02:00]]
## Collect Notes
ARCHIVED. DN-009 aggregate closure is complete at admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.

- All six packets #2027-#2031 and #2040 are archived with `archival_reason=completed` and the approved parent/dependency graph.
- #2027 verifier evidence proves native authority inspection; #2028 proves atomic admission; #2029 committed record proves query/history at verifier commit `b5db52e2ecc90896c2b64b92ff66686d45da1026`; #2030 committed record proves receipt/health at verifier commit `8c6ff83ff5b9714b494d359233a0a4121fe262ed`; #2031 proves native requests at `32067bc869559930d362309b1091e0a73ef9b73f`; #2040 proves assembled PROOF-011 and exact source/API removal at `1dc1a09f0ce2a3dced0b06c1d39c10180ef232f5` with verify descendant `53aee657f27c620e560154420c17a65ee08ce70b`.
- #2029 and #2030 use historical verifier headings rather than exact `## Verify Notes`, but their immutable committed archive bodies contain explicit verifier PASS evidence, AC mappings, test counts, and challenger passes.
- Latest integrated control-plane proof: 117 passed across allocator, admission transaction, runtime transaction, and native MCP; focused exact registry/absence/PROOF-011 contract 11 passed.
