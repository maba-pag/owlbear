---
id: 2092
title: 'P16-06: Align native distribution, generated assets, and documentation'
status: build
priority: medium
created: 2026-07-27T08:40:04.276149+02:00
updated: 2026-07-27T08:40:04.276149+02:00
tags:
  - phase-16
  - scope:distribution
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T6
  - module:MOD-006
  - module:MOD-007
  - module:MOD-009
parent: 1989
depends_on:
  - 2090
  - 2091
  - 2088
  - 2089
ac:
  - 'AC-1: Given the built and installed consumer artifact after #2088 through #2091,
    its public inventory contains the required native source, setup, seed, MCP, Cockpit,
    and ecosystem assets and contains no active OpenSpec command, legacy task runtime,
    retired route, retired role, or compatibility artifact.'
  - 'AC-2: Given the maintained setup, consumer, sharing, security, and ecosystem
    documentation and configuration, they describe the native design and delivery
    workflow and identify immutable legacy inventory as history rather than execution
    authority.'
  - 'AC-3: Given a fresh distribution diff against the canonical package and seed
    manifests, each shipped generated path has a current native owner and no unowned
    compatibility path remains.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The built and installed consumer distribution contains the native control plane, setup, seed, Cockpit, and ecosystem assets while maintained documentation and generated configuration describe no active legacy workflow.

## Scope
In scope: MOD-006, MOD-007, and MOD-009 distribution manifests, generated assets, checked-in consumer configuration, public setup/consumer documentation, and immutable-history references.

Out of scope: implementing snapshot/finalizer/setup behavior, deleting runtime or agent execution paths, assembled cutover behavior, and live-board retirement.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; REQ-011, REQ-017, IF-013/IF-016 public surfaces, MIG-001 through MIG-004 consumer inventories, RISK-005, and outputs from #2088 through #2091.

Proof guidance: build and install the consumer artifact in a temporary workspace, inspect the resulting artifact/config inventory, and run maintained documentation/config validators; do not add source-string absence tests.