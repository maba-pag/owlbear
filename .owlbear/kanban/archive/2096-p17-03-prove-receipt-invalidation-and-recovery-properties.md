---
id: 2096
title: 'P17-03: Prove receipt, invalidation, and recovery properties'
status: archived
priority: high
created: 2026-07-27T19:45:12.555886+02:00
updated: 2026-07-27T21:50:59.715968+02:00
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
  - 'AC-2: Given an acceptance finding classified as `implementation-defect` and targeted
    at `packet-implementation`, public rejection creates one `build-repair` job; given
    an acceptance finding classified as `planning-omission` and targeted at `packet-dependency`,
    public rejection creates one `node-plan-revision` job with `through_plan_correction=False`;
    both routes freeze original attempt, receipt, and finding history, and only a
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
archival_reason: completed
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

[[2026-07-27T20:55:29+02:00]]
## Shape Notes

Local task repair of builder follow-up key `AC-2/finding-class-route-contract`; approved intent, parent, dependencies, scope, authority, proof bundle, AC-1, and AC-3 are unchanged.

### Repair Closure Map
| Failure Key | Claimed Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof Or Negative Control | Executor Availability |
|---|---|---|---|---|---|
| AC-2/finding-class-route-contract | Public finding validation is separate from corrective-target routing and rejection publication. | `finding.py`, `invalidation.py::plan_corrective_route`, invalidation runtime, maintained invalidation proof. | Validate canonical class literals and invoke rejection for `packet-implementation` and `packet-dependency`. | Returned target route must select the job kind and correction flag; unsupported `packet-boundary-defect` remains rejected. | Installed pytest through `uv`. |

- AC-2 replaces the invented `packet-boundary-defect` class with admitted classes and explicit targets.
- `implementation-defect` plus `packet-implementation` requires one `build-repair`; `planning-omission` plus `packet-dependency` requires one `node-plan-revision` with `through_plan_correction=False`.
- Original history freezing and superseding-chain release remain part of the public rejection proof.
- Shaper challenger: `pass`; it confirmed canonical literals, orthogonal class/target semantics, test-only scope, and closure-map causality.
- Board audit before release: task remains child of #1990, has no dependencies, retains `existing+challenge`, and routes to `build`.

[[2026-07-27T21:37:54+02:00]]
## Builder Notes

DONE. Added generic durable proof over the maintained public runtime and transaction boundaries; production source is unchanged.

- AC-1: `test_start_job_accepts_only_current_unsuperseded_receipt_history_without_mutation` covers current, stale node-plan digest, superseded, intersecting-descendant, and proven-nonintersecting-descendant histories through `NativeRuntime.start_job`; rejected histories return stable lower diagnostics and preserve work bytes.
- AC-2 and `AC-2/finding-class-route-contract`: `test_reject_accept_routes_class_and_target_orthogonally_without_rewriting_history` proves `implementation-defect` plus `packet-implementation` creates one build repair and `planning-omission` plus `packet-dependency` creates one node-plan revision with `through_plan_correction=False`. Replay is idempotent and original attempt, receipt, and finding history remains immutable. Maintained reconciliation proof confirms only a successful replacement chain releases the new build; an invalidated chain remains blocked without mutation. No `packet-boundary-defect` class was added.
- AC-3: `test_recovery_converges_graph_job_receipt_activity_and_invalidation_participants` covers interruption before publication, after participant replacement, before cleanup, and during replay across graph, job move, receipt, activity, and invalidation participants; repeated recovery converges to one complete state without active/archive split and preserves prior history.
- Changed files: `serve/kanban/tests/test_native_runtime.py`; `serve/kanban/tests/test_runtime_transaction.py`.
- Focused proof: 11 passed. Successful-chain gate: 1 passed. Kanban package: 376 passed with 4 existing Python fork deprecation warnings. Focused `uv run lint` passed; VS Code diagnostics clean.
- Builder challenger: pass. All 20 recalled memories assessed.

[[2026-07-27T21:47:25+02:00]]
## Verify Notes

PASS. Independently reviewed builder SHA `a019085f601d2248dd34605d3284ead6c6d584e1`, current source, and the exact two-test diff. Production source is unchanged.

- AC-1: `NativeRuntime.start_job` delegates predecessor checks to persisted `ReceiptStore.evaluate_currentness`. The five-case matrix proves exact current, stale node-plan digest, explicit supersession, intersecting descendant, and proven nonintersecting descendant behavior with exact lower diagnostics and complete work-root snapshot equality on every rejection. Verifier repaired the `current` row to use the receipt SHA so it no longer duplicated the nonintersecting-descendant setup.
- AC-2 and `AC-2/finding-class-route-contract`: public `reject_accept` now proves both required routes plus both cross-pairs, so finding class and corrective target vary independently. Every row proves replay equality, one exact corrective job, `through_plan_correction=False`, frozen original attempt/finding/receipt history, and preserved finding class. Maintained reconciliation coverage proves stale/invalidated chains remain blocked without mutation while the successful replacement chain starts and releases. `packet-boundary-defect` is absent.
- AC-3: real `RuntimeTransaction` participants cover job move, graph, receipt, activity, and invalidation publication across before-publication, after-first-publication, before-cleanup, and interrupted replay. Active/archive XOR, repeated `recover_all`, complete final participants, immutable prior bytes, and manifest cleanup prove convergence.
- Verifier patch: `serve/kanban/tests/test_native_runtime.py` only; two tiny test-discrimination repairs, no production changes.
- Proof: corrected AC-1 matrix 5 passed; corrected AC-2 public matrix 4 passed; consolidated AC selection 14 passed; full `serve/kanban/tests` 378 passed with four existing Python 3.14 fork deprecation warnings. Scoped `uv run lint` passed, `git diff --check` passed, and VS Code diagnostics report no errors in either builder-changed test.
- Verifier challenger: `pass`; tests exercise public/runtime persistence boundaries rather than independently scripting expected outputs.
- Memory: all 20 recalled entries assessed; one pending verifier-scoped orthogonality-test lesson saved.

[[2026-07-27T21:50:59+02:00]]
## Collect Notes
ARCHIVED. Closure audit accepted builder SHA `a019085f601d2248dd34605d3284ead6c6d584e1` and descendant verifier SHA `d1431e4f7c7b873b40b9e213fd4c31d882d9c307`.

- AC-1: fresh public-runtime receipt-history matrix proved current-chain acceptance plus stable stale-digest, superseded, intersecting-descendant, and proven-nonintersecting diagnostics without rejected-work mutation.
- AC-2 and repaired failure key `AC-2/finding-class-route-contract`: fresh public rejection matrix proved finding class and corrective target vary independently, produce the required exact jobs, preserve immutable history, and retain `through_plan_correction=False`; accepted verifier evidence ties successful superseding-chain release and stale/invalidated-chain blocking to maintained reconciliation coverage.
- AC-3: fresh real-transaction matrix proved graph, job, receipt, activity, and invalidation recovery converges across publication/replacement/replay interruptions without partial receipt publication or active/archive job splits, while preserving prior history.
- Focused closure proof at verifier HEAD: 13 passed. Commit ancestry check passed; verifier SHA descends from builder SHA.
- Scope audit: supplied commits changed only this task record and `serve/kanban/tests/test_native_runtime.py` plus `serve/kanban/tests/test_runtime_transaction.py`; no product behavior or live carrier mutation entered scope.
- Parent #1990 remains the unclaimed `collect` aggregate owner and continues to depend on #2096 for DN-013/PROOF-013 closure.
- No resolved requests remain. All six recalled memories were assessed.
