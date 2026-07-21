---
id: 1988
title: 'Bootstrap DN-011: Build the graph-aware Cockpit Changes and Kanban experience'
status: shape
priority: medium
created: 2026-07-22T01:08:34.349450+02:00
updated: 2026-07-22T01:11:19.291247+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-011
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1987
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-011` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-011` modules, interfaces, risks, and
    `PROOF-012`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-011` and `PROOF-012`, verified
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
- `delivery_node_id`: `DN-011`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-011|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-011` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Cockpit keeps Kanban central and adds accessible scalable change, graph/list, request, evidence, invalidation, proof, and legacy-inventory experiences across desktop and mobile.
- Modules: `MOD-005`, `MOD-008`
- Produces: `IF-012`
- Consumes: `IF-011`
- Risks: `RISK-010`, `RISK-012`
- Proof: `PROOF-012`
- Delivery dependencies: `DN-010`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise the built Cockpit SPA against the real FastAPI backend with desktop/mobile, keyboard, scale, conflict, corrective-history, and nonoverlap proof; fixture stores are allowed but HTTP may not be mocked under `PROOF-012`.