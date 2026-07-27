---
id: 2096
title: 'P17-03: Prove receipt, invalidation, and recovery properties'
status: shape
priority: high
created: 2026-07-27T19:45:12.555886+02:00
updated: 2026-07-27T20:37:02.649218+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T3
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on: []
ac:
  - 'AC-1: Given histories containing current, stale-digest, superseded, intersecting-descendant,
    and proven-nonintersecting-descendant receipts, runtime dependency checks accept
    only the current unsuperseded chain and return the declared stable diagnostic
    for each rejected class without mutating jobs or receipts.'
  - 'AC-2: Given an acceptance finding classified as `implementation-defect` or `packet-boundary-defect`,
    public rejection creates respectively the minimum corrective build job or through-plan
    corrective route, freezes original attempt/receipt/finding history, and only the
    successful superseding chain releases dependencies.'
  - 'AC-3: Given interruption before transaction publication, after participant replacement,
    or during replay for graph, job, receipt, activity, and invalidation participants,
    recovery exposes neither a published receipt without its complete participant
    set nor a job split across active/archive stores; correction plus replay commits
    one state and preserves immutable prior history.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Generic generated histories prove current receipt selection, minimum correction, and transaction recovery independently of bootstrap identities.

## Scope
In scope: MOD-008 generic tests over IF-003/IF-009 and current transaction/invalidation stores. Out of scope: browser behavior, live carrier mutation, and product fixes.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, RISK-003/RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a deterministic generated receipt/invalidation/transaction matrix using public runtime operations and the shared transaction boundary.

[[2026-07-27T20:37:02+02:00]]
## Builder Notes

REJECT: AC-2 cannot be instantiated through the accepted public contract, so no production or test behavior was invented.

- AC-1 admission check: supported. `NativeRuntime._predecessor_check` calls `ReceiptStore.evaluate_currentness`; the store scans persisted supersession receipts and `_CompleteCurrentnessEvaluator` returns `ERR_RECEIPT_SUPERSEDED` before local/code/predecessor traversal. The local-only `evaluate_receipt_currentness` is not the runtime dependency boundary.
- AC-2 contradiction: `FindingClass` admits only `implementation-defect`, `unforeseeable-discovery`, `planning-omission`, and `scope-change`. A public `TypeAdapter(FindingClass)` probe accepted `implementation-defect` and rejected `packet-boundary-defect` with `literal_error`.
- Authority evidence: design section 10 separates late-work finding classes from corrective target categories. `packet-dependency` is a `CorrectiveRouteRequest.target` producing `node-plan-revision`; its job has `through_plan_correction=False`. Only `node-integration` and `whole-change-integration` produce jobs with `through_plan_correction=True`. The maintained route matrix asserts the same contract.
- AC-3 source inspection found existing transaction/invalidation participant and replay boundaries, but proof edits were stopped because AC-2 is materially unsupported.
- Changed files: no product or test files; task record only.
- Focused evidence: public finding-class probe; exact source/authority inspection. Builder challenger decision: `reconsider`.
- Memory: all 20 recalled entries assessed.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC-2/finding-class-route-contract | shaper via `/shape` | Rewrite AC-2 to use an admitted `FindingClass` separately from the corrective target/route, and state whether packet boundary proof expects `packet-dependency` with `through_plan_correction=False` or an integration target with `through_plan_correction=True`. Do not add `packet-boundary-defect` as a public class unless the accepted design and interface are intentionally changed. | `serve/kanban/src/owlbear_kanban/finding.py`; `serve/kanban/src/owlbear_kanban/invalidation.py`; `serve/kanban/tests/test_invalidation.py`; `.owlbear/changes/replace-delivery-pipeline/design.md` | Public validator rejects the AC literal; builder challenger returned `reconsider`. |
