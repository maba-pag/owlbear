---
id: 1986
title: 'Bootstrap DN-014: Independently audit and close complete changes'
status: archived
priority: high
created: 2026-07-22T01:08:04.826887+02:00
updated: 2026-07-25T22:18:57.628644+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-014
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1980
  - 1985
  - 1981
  - 2060
  - 2061
  - 2062
  - 2063
  - 2064
  - 2065
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-014` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; task-field and dependency audit compares those identities
    with `delivery/nodes.yaml`, `delivery/obligations.yaml`, and `delivery/contracts.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-014` modules, interfaces, risks, and
    `PROOF-008`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-014` and `PROOF-008`, verified
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
- `delivery_node_id`: `DN-014`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990|DN-014|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve DN-014 from modular `delivery/nodes.yaml`; resolve REQ-007, REQ-008, REQ-014, NEG-003, NEG-009, KEEP-004, KEEP-005, KEEP-007, KEEP-008, and WF-005 from `delivery/obligations.yaml`; resolve IF-001, IF-003, IF-004, IF-005, IF-009, IF-010, IF-014, RISK-008, RISK-009, and PROOF-008 from `delivery/contracts.yaml`.

- Outcome: A distinct read-only auditor uses an exact-commit proof checkout to evaluate accepted nodes, Product Promise, decisions, migrations, normal workflows, and receipt validity before closure or typed corrective work.
- Modules: `MOD-001`, `MOD-003`, `MOD-009`
- Produces: `IF-014`
- Consumes: `IF-001`, `IF-003`, `IF-004`, `IF-005`, `IF-009`, `IF-010`
- Risks: `RISK-008`, `RISK-009`
- Proof: `PROOF-008`
- Delivery dependencies: `DN-004`, `DN-008`, `DN-009`

## Shaping Boundary
DN-014 installs the single terminal audit job, typed audit rejection and minimum correction, the independent whole-change auditor workflow, and maintained PROOF-008 scenarios over existing exact-checkout, receipt, finding, invalidation, transaction, dispatch, and MCP foundations. Cockpit consumption remains DN-010/DN-011; setup and atomic cutover remain DN-012; complete native/cutover proof remains DN-013. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise the real read-only auditor over accepted nodes and admitted workflows in one engine-created exact-commit checkout; prove final receipt/closure and typed minimum correction without tracked edits, with replacements only below admitted workflow boundaries under PROOF-008.

[[2026-07-25T19:54:35+02:00]]
## Shape Notes

Approved under the user's standing authorization to complete the admitted delivery. Refreshed the stale `9387...` projection to modular digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990` before graph creation. Current authority is `delivery/nodes.yaml`, `delivery/obligations.yaml`, and `delivery/contracts.yaml` plus design and accepted decisions.

### Brief Readiness
- Product outcome and invocation: WF-005 starts one audit after the declared node set has current accept receipts; a fresh auditor proves the whole change at one exact commit and returns final closure or typed correction.
- Existing-system fit: native finish, dispatch, checkout, receipt, finding, invalidation, transaction, MCP query, and corrective-route owners exist. Source inspection found no production audit-job creation and no audit-rejection operation, agent, or workflow.
- Normal-path proof: real public MCP pick, start, finish, reject, release, and query operations over `DispatchRuntime`, `NativeRuntime`, and the engine checkout; replacements remain below admitted workflow boundaries.
- Completion contract: one terminal audit job, hard-read-only auditor, broad final receipt and archive closure, minimum typed correction, stale/request gates, replay, atomic failure, and cleanup. Cockpit, cutover, and complete-system proof remain DN-010 through DN-013.

### Change Module Map
| Module | Planned change | Owner |
|---|---|---|
| MOD-001 native lifecycle | terminal audit creation and atomic rejection | #2060, #2061 |
| Existing MCP bridge precedent | strict `reject_audit` and query reachability | #2062 |
| MOD-003 and MOD-009 | auditor role, workflow, orchestration, write guard | #2063 |
| MOD-008 maintained proof | PROOF-008 success and rejection matrices | #2064, #2065 |

### Product Invariant Map
| Invariant | Owner | Boundary |
|---|---|---|
| One terminal audit job after final node acceptance | #2060 | native `finish_accept` transaction |
| Atomic findings, invalidation, minimum correction, and cleanup | #2061 | public native `reject_audit` |
| Corrective operation and history are publicly reachable | #2062 | assembled MCP context |
| Distinct read-only exact-checkout auditor | #2063 | shipped role, workflow, and orchestrator |
| Complete exact-SHA pass and mechanical closure | #2064 | public PROOF-008 success lifecycle |
| Rejection, gates, independence, failure atomicity, and replay | #2065 | public PROOF-008 rejection lifecycle |

### Dependency Closure Map
- #2060 consumes current `finish_accept`, graph/node-plan authority, `JobStore.reserve_job_ids`, and shared transaction participants.
- #2061 consumes #2060 audit identity plus current findings, whole-change corrective routes, invalidation, receipts, jobs, attempts, coordination, checkout, and transaction authority.
- #2062 consumes #2061 strict request/result and archived DN-009 #1981 MCP/query conventions.
- #2063 consumes #2062 operations plus current read queries, checkout contract, acceptor precedent, and terminal write guard.
- #2064 consumes #2060 and #2063 through the public lifecycle. #2065 consumes #2061 through #2064.

### Scenario Closure Map
- #2060: final and non-final acceptance, stale predecessor, missing authority, existing identity, replay, and OCC failure.
- #2061/#2062: affected-node correction, design re-entry, ownership, malformed reference, cleanup, coordination, transaction failure, and replay.
- #2064: complete Product Promise, decisions, migrations/removals, workflows, receipts, success, closure, and replay.
- #2065: cross-node integration, migration absence, authority/proof omission, stale acceptance, unresolved request, tracked edit, malformed input, cleanup/OCC failure, and replay.

### Product Promise Coverage
- Independent final audit and final change receipt: #2060, #2063, #2064.
- Typed findings, minimum corrective jobs, and immutable history: #2061, #2062, #2065.
- REQ-007 whole-change fidelity and PROOF-008: #2063 through #2065.
- Cockpit consumption, atomic cutover, and complete-system/cutover proof are explicitly owned by DN-010, DN-011, DN-012, and DN-013.

### Final Graph
#2060 terminal audit creation; #2061 atomic rejection depends on #2060; #2062 MCP rejection depends on #2061 and archived #1981; #2063 auditor workflow depends on #2062; #2064 success proof depends on #2063; #2065 rejection proof depends on #2064. Parent #1986 depends on prerequisites #1980/#1985/#1981 and all six leaves.

Shaper challenge initially failed only on stale projection identity. After digest, admission, modular authority, and AC correction, rechallenge passed with authority, invariant, dependency, scenario, boundary, and fidelity coverage. Concrete read-back verified full bodies, AC, tags, parents, statuses, dependencies, and proof bundles for #2060 through #2065.

### Required Follow-up
None.

[[2026-07-25T22:18:57+02:00]]
## Collect Notes
ARCHIVED

DN-014 aggregate identity remains `replace-delivery-pipeline` at digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`. All six packet descendants #2060-#2065 are archived `completed` under this parent with verifier PASS notes and challenger evidence. Their chain covers terminal audit creation, atomic typed rejection, MCP exposure, the independent hard-read-only workflow, successful exact-commit closure, and required rejection/minimum-correction scenarios.

Aggregate proof at tested revision `18f7fae5fd996f1c19ace47f5f52446ab3a3c971`: 100 combined tests passed across native runtime, dispatch runtime, MCP acceptance, and MCP surface modules. Focused lint/validators passed for `auditor.agent.md`, `orchestrator.agent.md`, `w-whole-change-audit`, `w-orchestration`, and `share/WIRING.md`. Dependencies resolve and no material delivery expansion occurred.
