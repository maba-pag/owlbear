---
id: 1989
title: 'Bootstrap DN-012: Atomically cut over setup, stores, ecosystem, and documentation'
status: shape
priority: high
created: 2026-07-22T01:08:48.177677+02:00
updated: 2026-07-26T02:02:42.957213+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-012
  - scope:core
  - type:shape
  - rigor:thorough
  - digest:bf5edd67478d
  - corrective-projection
parent: 1968
depends_on:
  - 1988
  - 2073
  - 2074
  - 2075
  - 2076
  - 2077
  - 2078
  - 2079
ac:
  - 'AC-1: Shaper reads DN-012 from the modular authority trio at digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`
    and creates one outcome-cohesive packet DAG whose leaves reference the same change/digest/node;
    Kanban queries verify task fields and dependencies.'
  - 'AC-2: Shaper keeps leaves within DN-012 modules, interfaces, migrations, risks,
    and PROOF-009; material expansion leaves this aggregate in `shape` and routes
    #1968 to Specification, verified by task/artifact diff inspection.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` only after build-ready
    leaves and candidate-bound predecessor evidence exist; Collector archives only
    after descendant Verify Notes and SHA-bound PROOF-009 satisfy DN-012, verified
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
- `delivery_digest`: `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`
- `delivery_node_id`: `DN-012`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357|DN-012|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-bf5edd67478d.yaml`

## Authority Reference
Resolve DN-012 from modular `delivery/nodes.yaml`; resolve REQ-011, REQ-012, REQ-017, NEG-004, NEG-007, KEEP-007 from `delivery/obligations.yaml`; resolve IF-013, MIG-001 through MIG-004, RISK-001/RISK-005, and PROOF-009 from `delivery/contracts.yaml`.

Outcome: A hash-verified legacy snapshot and active-item disposition inventory preserve history while setup, seed, hooks, docs, generated assets, agents, APIs, and stores switch entirely to the native control plane.

## Shaping Boundary
The current shaper turns this aggregate into a bounded build-packet DAG only after candidate-digest predecessor corrections/re-acceptance and DN-011 completion. Any newly discovered product, interface, migration, security, destructive, or proof obligation returns to Specification and re-admission.

Proof guidance: exercise public setup and atomic cutover against populated-legacy and fresh-consumer fixtures, including no-overwrite, complete dispositions, hash equality, crash recovery, native-only launch, and old-surface absence under PROOF-009.

## Shape Notes
Reprojected from stale `9387...`/`graph.yaml` metadata to admitted modular digest `bf5edd...`. This task remains in shape and blocked by candidate-bound DN-005 through DN-011/DN-014 evidence; no DN-012 packet graph has been created yet.

[[2026-07-26T02:02:42+02:00]]
## Shape Notes
PROJECTION REPAIRED: DN-012 now references admitted modular digest `bf5edd...`, current authority files, and candidate-bound predecessor tasks. It remains in `shape`; no packet DAG was created because DN-011 and re-acceptance dependencies are unresolved.
