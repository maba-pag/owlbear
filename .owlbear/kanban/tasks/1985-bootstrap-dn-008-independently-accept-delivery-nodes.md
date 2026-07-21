---
id: 1985
title: 'Bootstrap DN-008: Independently accept delivery nodes'
status: shape
priority: high
created: 2026-07-22T01:07:49.392051+02:00
updated: 2026-07-22T01:11:19.264752+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-008
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1980
  - 1983
  - 1984
  - 1981
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-008` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-008` modules, interfaces, risks, and
    `PROOF-007`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-008` and `PROOF-007`, verified
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
- `delivery_node_id`: `DN-008`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-008|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-008` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: A read-only acceptor uses exact-commit proof checkouts, evaluates each delivery node against its contract and descendant receipts, and routes typed findings into minimum corrective work without self-patching.
- Modules: `MOD-001`, `MOD-003`, `MOD-009`
- Produces: `IF-009`
- Consumes: `IF-001`, `IF-003`, `IF-004`, `IF-005`, `IF-007`, `IF-008`, `IF-010`
- Risks: `RISK-008`, `RISK-009`
- Proof: `PROOF-007`
- Delivery dependencies: `DN-004`, `DN-006`, `DN-007`, `DN-009`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise the real read-only acceptor over engine-created proof checkout, node contract, and descendant receipts; prove pass, typed rejection, minimum correction, boundary integrity, tracked-edit denial, and cleanup under `PROOF-007`.