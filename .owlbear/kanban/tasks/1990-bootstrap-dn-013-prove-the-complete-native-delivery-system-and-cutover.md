---
id: 1990
title: 'Bootstrap DN-013: Prove the complete native delivery system and cutover'
status: shape
priority: high
created: 2026-07-22T01:09:02.449610+02:00
updated: 2026-07-27T01:31:54.929460+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-013
  - scope:core
  - type:shape
  - rigor:thorough
  - corrective-projection
  - digest:8cd27726f86d
parent: 1968
depends_on:
  - 1978
  - 1988
  - 1989
  - 2071
  - 2073
  - 2077
  - 2078
  - 2079
ac:
  - 'AC-1: Shaper reads DN-013 from the modular authority trio at digest `8cd27726f86df8428ab3dc586d2be3af4678accaca1706dece98c7357bb2b3e1`
    and creates one outcome-cohesive proof DAG whose leaves reference the same change/digest/node;
    Kanban queries verify task fields and dependencies.'
  - 'AC-2: Shaper keeps leaves within DN-013 consumed interfaces, risks, and PROOF-013;
    product defects route to their owning nodes and task/artifact diff inspection
    verifies no final-auditor implementation scope is introduced.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` only after build-ready
    proof leaves and candidate-bound predecessor evidence exist; Collector archives
    only after descendant Verify Notes and SHA-bound PROOF-013 satisfy DN-013, verified
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
- `delivery_digest`: `8cd27726f86df8428ab3dc586d2be3af4678accaca1706dece98c7357bb2b3e1`
- `delivery_node_id`: `DN-013`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|8cd27726f86df8428ab3dc586d2be3af4678accaca1706dece98c7357bb2b3e1|DN-013|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-8cd27726f86d.yaml`

## Authority Reference
Resolve DN-013 from modular `delivery/nodes.yaml`; resolve REQ-018, NEG-003, NEG-005, NEG-009, KEEP-005 from `delivery/obligations.yaml`; resolve consumed interfaces, RISK-003/RISK-005/RISK-006/RISK-009 through RISK-012, and PROOF-013 from `delivery/contracts.yaml`.

Outcome: Historical/generic fixtures and a fresh-consumer scenario prove admission, planning, build review, acceptance, correction, audit, Cockpit, setup, snapshot integrity, and absence of legacy execution.

## Shaping Boundary
The current shaper turns this aggregate into a bounded complete-system proof DAG only after corrected-authority DN-012 closure. Any new product implementation discovered here routes to its owning node rather than being patched by final audit.

Proof guidance: exercise public native validation over incident/generic fixtures, then one fresh-consumer design-to-audit workflow through real MCP, engine, writer policy, proof checkout, Cockpit, setup, and legacy snapshot under PROOF-013.

## Shape Notes
Reprojected from stale `9387...`/`graph.yaml` metadata to admitted modular digest `bf5edd...`. This task remains in shape and blocked by candidate-bound predecessor evidence plus DN-011/DN-012 completion; no DN-013 packet graph has been created yet.

[[2026-07-26T02:02:50+02:00]]
## Shape Notes
PROJECTION REPAIRED: DN-013 now references admitted modular digest `bf5edd...`, current authority files, and candidate-bound predecessor tasks. It remains in `shape`; no complete-system proof DAG was created because DN-011/DN-012 and re-acceptance dependencies are unresolved.

[[2026-07-27]]
## Shape Notes
AUTHORITY REPROJECTED: DN-013 now follows append-only admission `admission-8cd27726f86d` at digest `8cd27726f86df8428ab3dc586d2be3af4678accaca1706dece98c7357bb2b3e1`. Product intent is unchanged; the correction grants DN-012 the modules required to perform its already-owned cutover before DN-013 complete-system proof.
