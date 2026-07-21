---
id: 1979
title: 'Bootstrap DN-003: Replace task runtime with graph-linked jobs and receipts'
status: shape
priority: high
created: 2026-07-22T01:05:46.251445+02:00
updated: 2026-07-22T01:11:19.210914+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-003
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1977
  - 1978
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-003` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-003` modules, interfaces, risks, and
    `PROOF-003`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-003` and `PROOF-003`, verified
    through Kanban queries and artifact inspection.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-003|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-003` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Purpose-specific job, attempt, finding, receipt, request, supersession, invalidation, transaction, recovery, and health models provide one graph-aware runtime with no copied specification truth.
- Modules: `MOD-001`, `MOD-009`
- Produces: `IF-003`
- Consumes: `IF-001`, `IF-002`
- Risks: `RISK-002`, `RISK-003`, `RISK-006`
- Proof: `PROOF-003`
- Delivery dependencies: `DN-001`, `DN-002`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise public job, claim, completion, invalidation, transaction, recovery, and health operations with focused downstream impact; only clock, process identity, and temporary filesystem may replace layers below `PROOF-003`.