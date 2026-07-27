---
id: 1989
title: 'Bootstrap DN-012: Atomically cut over setup, stores, ecosystem, and documentation'
status: shape
priority: high
created: 2026-07-22T01:08:48.177677+02:00
updated: 2026-07-27T03:59:33.017891+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-012
  - scope:core
  - type:shape
  - rigor:thorough
  - corrective-projection
  - digest:6c95c70c81a1
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
  - 'AC-1: Shaper reads DN-012 from the modular authority trio at digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`
    and creates one outcome-cohesive packet DAG whose leaves reference the same change/digest/node;
    Kanban queries verify task fields and dependencies.'
  - 'AC-2: Shaper keeps leaves within DN-012 modules, interfaces, migrations, risks,
    and PROOF-009; material expansion leaves this aggregate in `shape` and routes
    #1968 to Specification, verified by task/artifact diff inspection.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` only after build-ready
    leaves and corrected-authority predecessor evidence exist; Collector archives
    only after descendant Verify Notes and SHA-bound PROOF-009 satisfy DN-012, verified
    through Kanban queries and artifact inspection. Real-board retirement remains
    owned exclusively by non-projected DN-015/PROOF-016.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at: 2026-07-27T01:14:41.165217+02:00
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`
- `delivery_node_id`: `DN-012`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9|DN-012|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-6c95c70c81a1.yaml`

## Authority Reference
Resolve DN-012 from modular `delivery/nodes.yaml`; resolve REQ-011, REQ-012, REQ-017, NEG-004, NEG-007, KEEP-007 from `delivery/obligations.yaml`; resolve IF-013, IF-016, MIG-001 through MIG-004, RISK-001/RISK-005, and PROOF-009 from `delivery/contracts.yaml`.

Outcome: A hash-verified legacy snapshot and active-item disposition inventory preserve history while setup, seed, hooks, docs, generated assets, agents, APIs, and stores switch entirely to the native control plane in shipped source and consumer distribution. DN-012 also produces the fixture-proved IF-016 finalizer consumed only by native terminal node DN-015.

## Shaping Boundary
The current shaper turns this aggregate into a bounded build-packet DAG after completed predecessor corrections and DN-011 closure. Any newly discovered product, interface, migration, security, destructive, or proof obligation returns to Specification and re-admission.

Proof guidance: exercise public setup and cutover against populated-legacy and fresh-consumer fixtures, including no-overwrite, complete dispositions, hash equality, crash recovery, native-only launch, and old-surface absence under PROOF-009. The real bootstrap-board retirement is excluded from this aggregate and owned by non-projected DN-015/PROOF-016.

## Shape Notes
Historical projection repairs to `bf5edd...` and `8cd277...` remain evidence of earlier admitted revisions.

[[2026-07-27]]
## Shape Notes
FINAL AUTHORITY REPROJECTED: User approved DEC-036 and terminal DN-015 after independent challenge resolved bootstrap ordering, ownership, and builder/acceptor separation. Canonical loading passed with no diagnostics; focused loader/admission tests passed 37/37; append-only receipt `admission-6c95c70c81a1` admits digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`. DN-015 is intentionally not projected into the legacy board it destroys. This DN-012 aggregate remains in `shape` pending approval of its seven-leaf packet DAG.
