---
id: 2098
title: 'P17-05: Verify the assembled Cockpit release journey'
status: build
priority: high
created: 2026-07-27T19:45:20.808938+02:00
updated: 2026-07-27T19:45:20.808938+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T5
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on:
  - 2097
ac:
  - "AC-1: Given #2097's completed temporary consumer, the built Cockpit SPA over
    the real FastAPI backend displays admitted specification, plan/build/accept/audit
    history, supersession/corrective chain, current receipts, evidence, activity,
    and immutable legacy inventory through Specification, Delivery, Evidence, Activity,
    and Legacy routes without mocked HTTP."
  - 'AC-2: Given desktop and mobile viewports, the representative journey resolves
    its maintained request interaction, reaches final-audit/current-chain state, emits
    no page exception, renders nonblank content, and has neither horizontal overflow
    nor overlap among the inspected route header, navigation, controls, and primary
    content bounds.'
  - 'AC-3: Given successful public setup, assembled MCP workflow, native launch, and
    browser journey, durable PROOF-013 output records invoked commands, tested Git
    revision, delivery/node-plan digests, admission/plan/build/accept/audit receipts,
    corrective finding/supersession identities, allowed replacements, native health,
    and active legacy-surface absence for DN-015; it does not invoke live carrier
    finalization.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Built Cockpit observes the actual completed and corrective state from #2097 in the temporary consumer on desktop and mobile and records the durable PROOF-013 release evidence.

## Scope
In scope: MOD-008 Playwright/FastAPI proof over #2097 scenario state. Out of scope: mocked HTTP, product fixes, live carrier mutation, and DN-015 execution.

## Authority
DN-013, REQ-018, PROOF-013, IF-011/012/013/014, RISK-005/RISK-009/RISK-010/RISK-012 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a dedicated serial Playwright desktop/mobile project plus focused API/proof-output assertions; the #2097 fixture repository is allowed, but HTTP and UI are not replaced.