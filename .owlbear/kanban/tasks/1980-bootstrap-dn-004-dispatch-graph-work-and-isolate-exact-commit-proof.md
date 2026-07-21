---
id: 1980
title: 'Bootstrap DN-004: Dispatch graph work and isolate exact-commit proof'
status: shape
priority: high
created: 2026-07-22T01:06:00.529389+02:00
updated: 2026-07-22T01:11:19.219621+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-004
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1979
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-004` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-004` modules, interfaces, risks, and
    `PROOF-014`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-004` and `PROOF-014`, verified
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
- `delivery_node_id`: `DN-004`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-004|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-004` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Graph-aware dispatch and orchestrator contracts release engine-selected jobs, serialize shared-worktree writers, recover attempts, replan from current state, and provide crash-safe disposable proof checkouts.
- Modules: `MOD-001`, `MOD-003`, `MOD-009`
- Produces: `IF-004`, `IF-005`
- Consumes: `IF-003`
- Risks: `RISK-002`, `RISK-004`
- Proof: `PROOF-014`
- Delivery dependencies: `DN-003`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise real engine-selected waves, writer leases, claims, structured completion, and disposable proof checkouts; replacements are limited to clock, subagent runner, and temporary repository below `PROOF-014`.