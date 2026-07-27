---
id: 1990
title: 'Bootstrap DN-013: Prove the complete native delivery system and cutover'
status: shape
priority: high
created: 2026-07-22T01:09:02.449610+02:00
updated: 2026-07-27T03:59:41.892701+02:00
tags:
  - bootstrap-projection
  - change:replace-delivery-pipeline
  - node:DN-013
  - scope:core
  - type:shape
  - rigor:thorough
  - corrective-projection
  - digest:6c95c70c81a1
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
  - 'AC-1: Shaper reads DN-013 from the modular authority trio at digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`
    and creates one outcome-cohesive proof DAG whose leaves reference the same change/digest/node;
    Kanban queries verify task fields and dependencies.'
  - 'AC-2: Shaper keeps leaves within DN-013 consumed interfaces, risks, and PROOF-013;
    product defects route to their owning nodes and task/artifact diff inspection
    verifies no final-auditor implementation scope is introduced.'
  - 'AC-3: Shaper moves this aggregate from `shape` to `collect` only after build-ready
    proof leaves and corrected-authority predecessor evidence exist; Collector archives
    only after descendant Verify Notes and SHA-bound PROOF-013 satisfy DN-013. Real
    bootstrap-board retirement remains exclusively DN-015/PROOF-016.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`
- `delivery_node_id`: `DN-013`
- `packet_id`: `aggregate`
- `projection_key`: `replace-delivery-pipeline|6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9|DN-013|aggregate`
- Admission receipt: `.owlbear/changes/replace-delivery-pipeline/receipts/admission-6c95c70c81a1.yaml`

## Authority Reference
Resolve DN-013 from modular `delivery/nodes.yaml`; resolve REQ-018, NEG-003, NEG-005, NEG-009, KEEP-005 from `delivery/obligations.yaml`; resolve consumed interfaces, RISK-003/RISK-005/RISK-006/RISK-009 through RISK-012, and PROOF-013 from `delivery/contracts.yaml`.

Outcome: Historical/generic fixtures and a fresh-consumer scenario prove admission, frontier planning, build review, acceptance, correction, audit, Cockpit, setup, snapshot integrity, and absence of legacy execution in shipped product before terminal DN-015 retires the external bootstrap carrier.

## Shaping Boundary
The current shaper turns this aggregate into a bounded complete-system proof DAG only after corrected-authority DN-012 closure. New product implementation discovered here routes to its owning node rather than being patched by final audit.

Proof guidance: exercise public native validation over incident/generic fixtures, then one fresh-consumer design-to-audit workflow through real MCP, engine, writer policy, proof checkout, Cockpit, setup, and legacy snapshot under PROOF-013. Do not execute DN-015's real bootstrap-board finalization here.

## Shape Notes
Historical projection repairs to `bf5edd...` and `8cd277...` remain evidence of earlier admitted revisions.

[[2026-07-27]]
## Shape Notes
FINAL AUTHORITY REPROJECTED: DN-013 now follows append-only admission `admission-6c95c70c81a1` at digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`. DN-015 is a separate non-projected terminal node that consumes DN-013 proof and owns the real carrier retirement through builder mutation plus independent exact-commit acceptance.
