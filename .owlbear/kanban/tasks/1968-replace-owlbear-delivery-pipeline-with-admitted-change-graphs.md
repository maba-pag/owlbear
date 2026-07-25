---
id: 1968
title: Replace OwlBear delivery pipeline with admitted change graphs
status: collect
priority: high
created: 2026-07-21T01:46:53.257501+02:00
updated: 2026-07-25T02:48:10.051561+02:00
tags:
  - pipeline-redesign
  - architecture
  - scope:core
  - admitted-change
  - digest:3f6c65628991
  - corrective-projection
parent:
depends_on:
  - 1975
  - 1976
  - 1977
  - 1978
  - 1979
  - 1980
  - 1981
  - 1982
  - 1983
  - 1984
  - 1985
  - 1986
  - 1987
  - 1988
  - 1989
  - 1990
  - 2021
  - 2032
  - 2033
  - 2034
  - 2035
  - 2036
  - 2037
ac:
  - The bootstrap native change package records the approved intent, 
    architecture decisions, complete delivery-node graph, admission 
    requirements, atomic migration, and end-to-end replay proof before 
    implementation decomposition.
  - The implementation cutover removes OpenSpec and the current 
    shape/build/verify/collect task-authoritative path while preserving the 
    healthy capabilities enumerated in the planning-workflow authority.
  - The replacement rejects all four historical defective plans before Kanban 
    execution and accepts their corrected forms through executable scenario 
    tests.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Replace the OpenSpec and task-authoritative planning pipeline with the native, graph-authoritative delivery control plane defined by `.owlbear/research/planning-workflow-root-cause-and-redesign.md` and the user decisions recorded on 2026-07-21.

## Scope
This is the bootstrap intake for an atomic cutover. The durable native change package will own intent, design, decisions, and the complete delivery-node graph. Do not decompose this intake into implementation tasks until that package is complete, independently challenged, and explicitly admitted.

## Required outcome
- Native four-file change authority replaces OpenSpec.
- Global delivery graph is complete before Kanban execution.
- Each delivery node is shaped once into outcome-cohesive build packets.
- Kanban jobs have purpose-specific statuses: shape, build, accept, audit.
- Builders use an inline read-only review loop; acceptors and auditors remain independent and cannot edit tracked files.
- Corrective work is append-only through new jobs and superseding receipts.
- Shared-worktree writes are serialized by orchestration.
- Existing pipeline, OpenSpec integration, and legacy behavior are removed in the same atomic cutover.

## Planning authority
`.owlbear/research/planning-workflow-root-cause-and-redesign.md`



## Admission Projection
- Change: `replace-delivery-pipeline`
- Delivery digest: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`
- Tested baseline: `e27786f3b9e76c3f44f08c807f9035018f0c6cb4`
- Projected delivery-node aggregates: #1977 through #1990, mapped by each task's `delivery_node_id` rather than numeric order.
- Projection policy: non-authoritative reference records; authority edits require re-admission and stale projections must not dispatch.

[[2026-07-22T01:13:04+02:00]]
## Shape Notes
### Admission
- Change authority: `.owlbear/changes/replace-delivery-pipeline/{intent.md,design.md,decisions.yaml,graph.yaml}`.
- Approved delivery digest: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`.
- Immutable receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`.
- Tested baseline: clean detached `e27786f3b9e76c3f44f08c807f9035018f0c6cb4`; nine gates passed and verifier-challenger returned `pass`.
- Carrier source: clean sibling `e6ff4b28dc815cf6d0bd314305a46f6b64670a39`, synced from development revision `32d41b6500d88ce46c5a82770458e1befe0310f8` in the baseline lineage.
- Graph challenge: fresh shaper-challenger returned `pass` for this digest with 88 entity dispositions and no blocking finding.
- User approval: the user authorized the presented digest when independent subagent review was confirmed; the fresh challenge reconfirmed that condition before mutation.
- Requests: no pending or resolved structured request changes this revision.

### Canonical Audit
- Delivery-v1 recomputation after admission metadata mutation remained `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8` over 124194 canonical bytes.
- Receipt parse found 88 unique passing dispositions, twelve passing deterministic diagnostics, nine zero-exit baseline gates, explicit approval, and projection lock policy.
- Admission metadata and receipt fields are excluded from delivery-v1; any edit to intent, design, accepted decisions, or delivery sections requires renewed challenge and approval.

### Projected Graph
| Node | Task | Depends on tasks |
|---|---:|---|
| DN-001 | #1977 | none |
| DN-002 | #1978 | #1977 |
| DN-003 | #1979 | #1977, #1978 |
| DN-004 | #1980 | #1979 |
| DN-005 | #1982 | #1978, #1981 |
| DN-006 | #1983 | #1979, #1980, #1982, #1981 |
| DN-007 | #1984 | #1980, #1983, #1981 |
| DN-008 | #1985 | #1980, #1983, #1984, #1981 |
| DN-009 | #1981 | #1980 |
| DN-010 | #1987 | #1979, #1980, #1985, #1986 |
| DN-011 | #1988 | #1987 |
| DN-012 | #1989 | #1982, #1983, #1984, #1985, #1981, #1987, #1988, #1986 |
| DN-013 | #1990 | #1978, #1979, #1985, #1981, #1987, #1988, #1989, #1986 |
| DN-014 | #1986 | #1980, #1985, #1981 |

### Projection Audit
- Created fourteen `shape` aggregates with parent #1968, one stable `(change_id, delivery_digest, delivery_node_id, aggregate)` key each, and `existing+challenge` proof bundles.
- Construction used an operational audit block on each task. Before unlock, read-back found fourteen tasks, fourteen node IDs, fourteen unique keys, no dispatchable projection, and dependency lists identical to the admitted DAG.
- The dependency graph is acyclic. Its order is DN-001, DN-002, DN-003, DN-004, DN-009, DN-005, DN-006, DN-007, DN-008, DN-014, DN-010, DN-011, DN-012, DN-013.
- After audit, the temporary blocks were removed. #1977 is the sole dependency-free root; the other thirteen projections remain dependency-gated.
- Current carrier selection intentionally leaves `shape` work for the user-facing `/shape` workflow rather than unattended dispatch.
- #1968 depends on archived baseline repairs #1975 and #1976 plus projected tasks #1977 through #1990, so aggregate collection cannot outrun a delivery node.

### Limits
- Packet boundaries remain unshaped until each delivery-node shape job runs.
- Admission proves delivery completeness and starting feasibility, not implementation correctness.
- Projected task prose is non-authoritative and cannot supersede the graph.
- The current pipeline is a one-time stable sibling carrier; no compatibility path survives cutover.
- DN-013 and DN-014 must re-prove the native assembled system and whole change at committed revisions before closure.

## Draft Authority Amendment
- User-approved DEC-021 and the revised receipt-currency design changed semantic delivery authority; `graph.yaml` is intentionally `draft` with `admission: null`, and the prior `9387dea789fb...` receipt is historical rather than current authority.
- Task #2021 repairs DN-002 admission receipt fidelity by persisting validated challenge, baseline, approval, and limits. It does not publish the live revision.
- Root aggregate #1968 depends on #2021 so cutover closure cannot outrun admission evidence fidelity. DN-013/DN-014 retain whole-change re-proof and re-admission ownership after the assembled replacement is complete.

[[2026-07-23T18:16:46+02:00]]
## Shape Notes
- Material repair: user accepted DEC-021 typed descendant impact closure and ratified DN-002 follow-up #2021.
- Authority state: `replace-delivery-pipeline` is intentionally `draft` with `admission: null`; the prior digest/receipt is historical. DN-013/DN-014 retain whole-change re-proof and re-admission ownership.
- Graph change: root #1968 now depends on #2021 so closure cannot outrun admission evidence fidelity.
- Challenge: final concrete board/authority audit passed. Root remains `collect` and dependency-blocked.

[[2026-07-25T00:33:51+02:00]]
## Collect Notes — Material Operating-Model Re-entry

Aggregate closure is not currently valid. Implementation of DN-001 through DN-004 and subsequent DN-009 shaping exposed a material design issue: the admitted model makes Kanban the default center, requires one shaping session per node, and stores delivery authority plus mutable node plans in one monolithic `graph.yaml`. User-directed analysis concluded that Definition/Specification and Delivery should be peer phases; delivery nodes belong to admitted specification, implementation packets begin Delivery, and eligible nodes may be batch-planned while retaining separate per-node validation, digests, reviews, transactions, and receipts.

Durable evidence: `.owlbear/research/delivery-operating-model-reframe.md` records sources, observed cost proxies, preserved invariants, amendment radius, effort, limits, and the recommended recovery sequence. No authority or contained DN-009 task was changed by that analysis.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | aggregate/operating-model-reframe | shaper | Re-enter global design for #1968. Resolve peer Definition/Delivery phases, delivery-node versus packet boundary, batch frontier planning, physical separation of delivery authority and node plans, native-change YAML line-length policy, and the deferred adaptive direct-execution contract. Reconcile and re-admit the complete authority before refreshing projections. Preserve #1981/#2027-#2031 partial-graph containment and do not resume DN-009 dispatch against the stale digest. | `.owlbear/changes/replace-delivery-pipeline/{intent.md,design.md,decisions.yaml,graph.yaml}`; `.editorconfig`; affected bootstrap projections | `.owlbear/research/delivery-operating-model-reframe.md`; current `graph.yaml` is 1,415 lines/57 KB; `NativeRuntime` rewrites it for node plans; #2025 independent verification history; #1981 containment |

Route: `shape` for user-facing material design review, authority reconciliation, independent challenge, approval, and re-admission.

[[2026-07-25T02:48:10+02:00]]
## Shape Notes

### Admitted Authority
- User approved exact digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.
- Immutable receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-3f6c65628991.yaml`.
- Production loader plus persisted evidence returned zero admission findings. Focused clean baseline at `e6d229b5e7915189e8d65fe0aa7437154ec5e4ac`: 22 tests passed.
- Independent shaper challenge passed after MOD-005 was corrected from Kanban-centered to peer Specification/Delivery wording.

### Approved Model
- Specification ends with admitted delivery nodes; Delivery begins with `plan` jobs.
- Every admitted node is initially plan-eligible and processed in stable topology order.
- Dependent build separately requires a current plan, authored packet dependencies, and predecessor accept receipts.
- Predecessor acceptance triggers mandatory dependent-plan reconciliation; invalidation stales the reconciled closure.
- Modular delivery authority and isolated plans replace `graph.yaml`; no fallback or `shape` alias survives.
- Engine `pick_jobs` owns scheduling; one fresh invocation handles one selected job; final audit is read-only.

### Corrective Graph
- #2032 C1 modular package/plan-store primitives.
- #2033 C2 modular authority and isolated-plan cutover; depends #2032.
- #2034 C3 plan-only identities and admission generation; depends #2032.
- #2035 C4 acceptance-triggered reconciliation; depends #2033/#2034.
- #2036 C5 engine topology/profile dispatch and production orchestrator consumers; depends #2035.
- #2037 C6 IF-015 `finish_plan` MCP cutover; depends #2036.
- Dependency shape: `2032 -> {2033,2034} -> 2035 -> 2036 -> 2037`.

### Challenge And Audit
- First corrective-graph challenge found omitted production orchestrator consumers. C5 AC5 now covers `orchestrator.agent.md` and `w-orchestration` plan/planner cutover.
- Re-challenge: pass across readiness, authority, invariant ownership, dependency closure, scenarios, boundary proof, and fidelity.
- Board read-back confirmed six unblocked `build` children, exact parent/dependency links, and #2032 as the sole ready root.
- #1981 and #2027-#2031 remain blocked under `PARTIAL_GRAPH_COMMIT`; no containment field was changed.

### Limits
- C4 supplies engine-side REQ-025 reconciliation behavior; DN-006 still owns planner publication and full REQ-025 closure.
- Bootstrap projection dispatch remains locked until the digest-bound corrective graph passes completion audit.
- Direct Ruff on unchanged admission modules still reports five pre-existing findings; `yamllint` is unavailable.
