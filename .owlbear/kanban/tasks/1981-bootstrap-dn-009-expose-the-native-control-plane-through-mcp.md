---
id: 1981
title: 'Bootstrap DN-009: Expose the native control plane through MCP'
status: shape
priority: high
created: 2026-07-22T01:06:55.160360+02:00
updated: 2026-07-22T01:11:19.227948+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-009
  - scope:core
  - type:shape
  - rigor:thorough
parent: 1968
depends_on:
  - 1980
ac:
  - 'AC-1: Shaper, while this task is in `shape`, reads `DN-009` at the recorded digest
    and creates one outcome-cohesive packet DAG whose task records reference the same
    change, digest, and node; verify by task-field and dependency audit against `graph.yaml`.'
  - 'AC-2: Shaper keeps packet scope within `DN-009` modules, interfaces, risks, and
    `PROOF-011`; material delivery expansion leaves this aggregate in `shape` and
    routes #1968 to design re-entry, verified by graph/task diff inspection.'
  - 'AC-3: Shaper moves this node aggregate from `shape` to `collect` only after build-ready
    packet tasks and their dependencies exist; Collector archives it only after descendant
    Verify Notes and tested-revision evidence satisfy `DN-009` and `PROOF-011`, verified
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
- `delivery_node_id`: `DN-009`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8|DN-009|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-9387dea789fb.yaml`

## Authority Reference
This task is a non-authoritative bootstrap projection. Resolve current obligations from `DN-009` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; task prose cannot add, weaken, or supersede that contract.

- Outcome: Strict MCP tools expose change admission, graph reads, job dispatch/completion, requests, evidence, and health while generic task mutation and old lifecycle tools disappear.
- Modules: `MOD-002`, `MOD-008`
- Produces: `IF-010`
- Consumes: `IF-001`, `IF-002`, `IF-003`, `IF-004`
- Risks: `RISK-005`
- Proof: `PROOF-011`
- Delivery dependencies: `DN-004`

## Shaping Boundary
The current shaper turns this aggregate into the bounded build-packet DAG needed to satisfy the referenced node. Any newly discovered delivery outcome, interface, migration, material risk, or proof boundary returns to global design and re-admission.

Proof guidance: exercise public MCP tools over the real graph-aware engine and prove old generic task mutation/lifecycle tools are absent; only a temporary engine store may replace a lower layer below `PROOF-011`.