---
id: 1983
title: 'Bootstrap DN-006: Shape delivery nodes into bounded packet DAGs'
status: shape
priority: high
created: 2026-07-22T01:07:22.578615+02:00
updated: 2026-07-22T01:11:19.246836+02:00
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
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-006` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-006` modules, interfaces, risks, and
    `PROOF-005`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-006` and `PROOF-005`, verified
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
- `delivery_node_id`: `DN-006`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-006|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-006` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: One shaper job per admitted node creates a complete outcome-cohesive packet plan and build/accept jobs while mechanically rejecting global delivery expansion.
- Modules: `MOD-001`, `MOD-003`
- Produces: `IF-007`
- Consumes: `IF-001`, `IF-002`, `IF-003`, `IF-004`, `IF-006`, `IF-010`
- Risks: `RISK-007`, `RISK-011`
- Proof: `PROOF-005`
- Delivery dependencies: `DN-003`, `DN-004`, `DN-005`, `DN-009`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise the real node shaper and finish_shape transaction, including bounded success, delivery-expansion rejection, independent review, and atomic failure; only repository search results may be replaced below `PROOF-005`.