---
id: 1989
title: 'Bootstrap DN-012: Atomically cut over setup, stores, ecosystem, and documentation'
status: shape
priority: medium
created: 2026-07-22T01:08:48.177677+02:00
updated: 2026-07-22T01:11:19.300725+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-012
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1982
  - 1983
  - 1984
  - 1985
  - 1981
  - 1987
  - 1988
  - 1986
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-012` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-012` modules, interfaces, risks, and
    `PROOF-009`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-012` and `PROOF-009`, verified
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
- `delivery_node_id`: `DN-012`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-012|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-012` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: A hash-verified legacy snapshot and active-item disposition inventory preserve history while setup, seed, hooks, docs, generated assets, agents, APIs, and stores switch entirely to the native control plane.
- Modules: `MOD-003`, `MOD-006`, `MOD-007`, `MOD-008`, `MOD-009`
- Produces: `IF-013`
- Consumes: `IF-001`, `IF-002`, `IF-003`, `IF-004`, `IF-006`, `IF-007`, `IF-008`, `IF-009`, `IF-010`, `IF-011`, `IF-012`, `IF-014`
- Risks: `RISK-001`, `RISK-005`
- Proof: `PROOF-009`
- Delivery dependencies: `DN-005`, `DN-006`, `DN-007`, `DN-008`, `DN-009`, `DN-010`, `DN-011`, `DN-014`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise public setup and atomic cutover against populated-legacy and fresh-consumer fixtures, including no-overwrite, complete dispositions, hash equality, crash recovery, native-only launch, and old-surface absence under `PROOF-009`.