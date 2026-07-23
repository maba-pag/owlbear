---
id: 1968
title: Replace OwlBear delivery pipeline with admitted change graphs
status: collect
priority: high
created: 2026-07-21T01:46:53.257501+02:00
updated: 2026-07-23T18:16:46.704872+02:00
tags:
  - pipeline-redesign
  - architecture
  - scope:core
  - admitted-change
  - digest:9387dea789fb
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
