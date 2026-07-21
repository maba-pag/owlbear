---
id: 1977
title: 'Bootstrap DN-001: Establish native change authority and semantic identity'
status: shape
priority: medium
created: 2026-07-22T01:05:17.126803+02:00
updated: 2026-07-22T01:11:19.148323+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-001
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on: []
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-001` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-001` modules, interfaces, risks, and
    `PROOF-001`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-001` and `PROOF-001`, verified
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
- `delivery_node_id`: `DN-001`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-001|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-001` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Strict four-file ChangeRevision loading, stable IDs/digests, immutable receipt storage, path safety, and health diagnostics replace OpenSpec artifact resolution.
- Modules: `MOD-001`
- Produces: `IF-001`
- Consumes: none
- Risks: `RISK-004`
- Proof: `PROOF-001`
- Delivery dependencies: none

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: shape from the admitted node and run the cheapest public ChangeRevision loader/receipt-store checks plus downstream path-safety impact; packet proof may replace only the temporary workspace filesystem below `PROOF-001`.