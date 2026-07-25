---
id: 1984
title: 'Bootstrap DN-007: Build outcome-cohesive packets with inline adversarial review'
status: archived
priority: medium
created: 2026-07-22T01:07:36.999020+02:00
updated: 2026-07-25T17:05:32.495139+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-007
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1980
  - 1983
  - 1981
  - 2051
  - 2052
  - 2053
  - 2054
ac:
  - 'AC-1: Shaper reads current `DN-007` at digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`
    and creates one packet DAG for an engine-selected builder, inline reviewer, scoped
    commit, and IF-008 completion; task-field and dependency audit against modular
    delivery authority verifies matching identities.'
  - 'AC-2: Shaper keeps packet scope within current DN-007 obligations, modules, interfaces,
    risks, and PROOF-006; modular-authority and task diff inspection verifies no runtime
    operation, public interface, migration, or proof expansion entered the graph.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` only after build-ready
    packet tasks cover workflow, role wiring, success and warm repair, material contradiction,
    commit failure, malformed review, and stale digest; Collector requires descendant
    Verify Notes and current-SHA PROOF-006 evidence.'
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
- `delivery_node_id`: `DN-007`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990|DN-007|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current DN-007 from `.owlbear/changes/replace-delivery-pipeline/delivery/nodes.yaml`, its obligations and workflow from `delivery/obligations.yaml`, and IF-008, risks, modules, and PROOF-006 from `delivery/contracts.yaml`; task prose cannot add, weaken, or supersede those contracts.

- Outcome: The builder consumes exact packet authority, implements required outputs under one writer lease, commits scoped work, resolves mandatory read-only review, and emits a valid build receipt.
- Modules: `MOD-003`, `MOD-009`
- Produces: `IF-008`
- Consumes: `IF-003`, `IF-004`, `IF-007`, `IF-010`
- Risks: `RISK-002`, `RISK-008`, `RISK-011`
- Proof: `PROOF-006`
- Delivery dependencies: `DN-004`, `DN-006`, `DN-009`

## Shaping Boundary
The builder consumes engine-selected, planner-produced packet authority through the existing public native lifecycle. This aggregate installs the builder workflow, independent inline reviewer, orchestrator handoff, and maintained PROOF-006 scenarios. Any new delivery outcome, interface, migration, material risk, proof boundary, runtime mutation, or MCP operation returns to global design and re-admission.

Proof guidance: exercise the real builder from claim through scoped commit, system-generated reviewer context, finding repair, and `finish_build` receipt; only a sample product module and deterministic command runner may replace lower layers below PROOF-006.

[[2026-07-25T16:15:09+02:00]]
## Shape Notes

Approved and committed the current DN-007 packet graph under standing user authorization to complete the admitted delivery. Reconciled the stale monolithic `9387...` projection to modular digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; no OpenSpec package exists for this change, so admitted Delivery YAML and current source are controlling authority.

### Final Graph
- #2051 P8-01: packet-building workflow.
- #2052 P8-02: native builder, read-only build reviewer, and orchestrator routing; depends on #2051.
- #2053 P8-03: assembled success and warm local-repair proof; depends on #2052.
- #2054 P8-04: exhaustive fail-closed and stale-authority proof; depends on #2053.

### Change Module Map
- #2051 owns new `w-packet-building` workflow semantics over existing native schemas and commit governance.
- #2052 owns builder and build-reviewer declarations, orchestration routing, ND3 enforcement, and WIRING synchronization inside MOD-003 and MOD-009.
- #2053 and #2054 own maintained PROOF-006 assembled scenarios; production runtime remains unchanged unless an exact scenario exposes a contract-clear local defect.

### Invariant And Scenario Closure
- #2053 owns one exact packet under one writer lease, mandatory read-only review, scoped commit, warm `implementation-defect` repair, receipt completion, and replay.
- #2054 owns `unforeseeable-discovery`, `planning-omission`, and `scope-change` re-entry; commit failure; malformed reviewer context; stale node-plan digest; release, halt, and no-receipt behavior.
- The four canonical `FindingClass` literals are exhaustive: only `implementation-defect` stays in the warm repair loop; the other three return `SpecificationReentry` without authority mutation.

### Dependency Availability
Current source supplies `StartJobResult`, job and node-plan digests, current change/job/receipt queries, public `finish_build` and `release_job`, DispatchRuntime writer coordination, typed findings, receipt persistence, and stable stale-authority diagnostics. The graph introduces no runtime operation, store mutation, separate lock, or fixture-only contract.

### Proof Boundary
PROOF-006 runs a real builder job from public claim through scoped commit, system-generated reviewer context, repair, and public `finish_build`. Only a sample product module and deterministic command runner may be replaced.

### Challenge And Audit
`shaper-challenger` returned `pass` after the finding taxonomy was made exhaustive and required full replacement of stale digest, receipt, projection key, modular authority references, and AC wording. Board audit confirms #2051 through #2054 are build-ready, parented to #1984, linearly dependent, and included in the aggregate dependency set.

[[2026-07-25T17:05:32+02:00]]
## Collector Notes

DN-007 aggregate closure passed at current implementation SHA `5c340750ac47190be01a8b62a75122c3857c8992`.

- All packet descendants #2051 through #2054 are archived with reason `completed`, mandatory builder/verifier challenges passed, and the sole verifier failure key `malformed-context-causality` was repaired and passed on rechallenge.
- Current-SHA PROOF-006: `serve/mcp-kanban/tests/test_builder_interaction.py` passed all 11 success, warm repair, material re-entry, commit failure, malformed review, and stale-authority cases.
- `.owlbear/scripts/validate_agents.py` reports all 17 agent files conform; all DN-007 workflow, role, reviewer, orchestration, wiring, validator, and proof artifacts are clean at the tested SHA.
- Maintained agent-validator/write-guard suite produced 37 passes and one unrelated failure in dirty `collector.agent.md` live-registry declarations. That file is outside DN-007's envelope and was preserved unchanged.

AC closure: modular digest/projection identities match; the implementation remains within DN-007 modules/interfaces/proof with no runtime operation or authority expansion; all planned packet categories have descendant Verify Notes and current-SHA aggregate proof. All recalled collector memories were assessed. Archive reason: completed.
