# Promoted-Adoption Restart Recovery

> **Owning task:** none - proposed Delivery engine recovery correction
> **Date:** 2026-08-23
> **Question:** How should restart distinguish an unpromoted external Change head from a promoted
> adoption retained as provenance after reviewed authority advances, without weakening fail-closed
> recovery or losing a rejected Builder commit?
> **Status:** Implementation-ready plan after independent architecture challenge; no runtime mutation
> is authorized by this document.

## 1. Context and Question

`ChangeWorkspaceManager.restart()` preserves a rejected Builder head under an attempt ref, restores
the managed Change branch and worktree to `last_reviewed_commit`, and releases exact writer custody.
Before those mutations, `_reject_unpromoted_adoption_restart()` prevents a reset across an adopted
external head that has not gained review authority.

The current guard treats a retained adoption receipt as unpromoted whenever its `adopted_head` no
longer equals `last_reviewed_commit`. That is correct immediately after adoption, but incorrect after
the exact adopted head has been promoted and later reviewed Builder commits advance
`last_reviewed_commit`. In that state the adoption receipt is historical provenance, the current
promotion receipt still binds it to reviewed authority, and a later failed Builder attempt should be
recoverable.

The observed blocked Change had this linear history at the time of investigation:

```text
promoted adopted head 27697519a03b9a70d9800e6bc1ccecdcf2dabac4
    -> reviewed head 9612e7c6caf697a3d5f7a05e81e599f84246b5ce
    -> rejected Builder head fe906fbe2a3adfa283dc7fe51a71d58e1d95702c
```

The worktree was clean, exact writer custody remained active, and the current adoption and promotion
receipts matched. Recovery failed before mutation with `ERR_TARGET_COORDINATION_CONFLICT` because the
guard reported an unpromoted external Change head. These values are a historical investigation
snapshot, not authority to mutate the live Change; they must be re-read before any later recovery.

The required semantic decision is explicit: Git ancestry alone does not grant review authority.
Restart may recognize a promoted adoption only through matching current promotion evidence. Ancestry
then proves that the promoted head remains included in the current reviewed boundary.

## 2. Sources Studied

| Source | Load-bearing fact | Evidence limit |
| --- | --- | --- |
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | Defines adoption and promotion receipts, coordination validation, promotion, writer release, recovery snapshots, and restart. Promotion records `adoption_receipt_id`, advances `last_reviewed_commit`, and retains the adoption receipt. Restart currently applies the adoption guard before attempt-ref preservation and released-restart replay validation. | Current coordination validation checks receipt Change identities and history uniqueness but does not validate the current promotion-to-adoption relationship. |
| [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | Exact claim and Integration repair recovery both call `restart()`. Successful claim recovery removes the runtime claim only after workspace restart succeeds. | Application recovery is an affected caller, not the owner of the faulty predicate. |
| [`delivery_runtime.py`](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) | Normal retry and return transitions also call `restart()`. | Caller-specific logic does not change the restart safety predicate. |
| [`test_change_workspace.py`](../../serve/delivery/tests/test_change_workspace.py) | Already proves that restart rejects an unpromoted adoption and that ordinary restart preserves rejected commits, resets to the reviewed boundary, releases custody, and replays after interruption. | No existing restart test combines retained adoption evidence with promotion and a later reviewed descendant. |
| [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py) | Covers exact clean Build recovery, interruption replay, dirty-byte retention, mismatched custody, and adoption-before-Build promotion. | Its broader fixtures would make the root predicate regression slower and less diagnostic than a workspace-manager test. |
| [`delivery-change-worktree-authority.md`](delivery-change-worktree-authority.md) | Defines `promote_external_head` as the operation that explicitly admits review authority for the exact adopted head and advances the reviewed boundary. | It establishes authority semantics, not the implementation details of the restart guard. |
| Git history, especially `fbe51253e` | Introduced explicit external-head promotion, the restart guard, and the original unpromoted-adoption test together. | History explains the safety intent but does not prove the current guard handles later reviewed descendants. |
| Independent read-only architecture challenge, 2026-08-23 | Identified all four restart callers, released-restart replay risk, and the ancestry-only alternative. Focused source checks confirmed the caller count and that `PortfolioCoordinator.release()` releases both writer custody and the current capacity-ledger slot. | Challenger recommendations were advisory. The ancestry-only proposal was rejected because it would weaken explicit-promotion authority. |

## 3. Analysis

### 3.1 Required invariant

For the current adoption receipt `A`, current promotion receipt `P`, and coordination record `C`, the
adoption is recognized as promoted for restart only when all of the following hold:

1. `P` exists.
2. `P.change_id == C.change_id` and `P.branch == C.branch`.
3. `P.adoption_receipt_id == A.receipt_id`.
4. `P.promoted_head == A.adopted_head`.
5. `P.promoted_head` is equal to or an ancestor of `C.last_reviewed_commit`.

Conditions 2-4 bind the evidence to the current adoption rather than stale promotion history.
Condition 5 proves that later reviewed authority still contains the promoted external work. A
promotion whose head is outside the current reviewed boundary must not authorize a reset.

When this predicate succeeds, `_reject_unpromoted_adoption_restart()` returns and existing restart
logic remains responsible for exact attempt identity, clean worktree validation, ref collision
checks, preservation, reset, and custody release. When it fails, the current unpromoted-adoption
conflict remains unchanged and occurs before any Git or coordination mutation.

### 3.2 Alternatives considered

| Alternative | Benefit | Risk | Decision |
| --- | --- | --- | --- |
| Recognize the matching current promotion receipt and verify reviewed ancestry. | Preserves the explicit-promotion policy while accepting later reviewed descendants and released replay. | Adds one narrowly scoped relationship predicate in restart. | **Selected.** |
| Permit restart whenever `adopted_head` is an ancestor of `last_reviewed_commit`. | Smallest code change and directly proves the reset retains adopted bytes. | Allows reviewed ancestry to substitute for the promotion receipt, weakening the authority rule that external adoption requires explicit promotion. | Reject. |
| Move all cross-receipt validation into `ChangeCoordination` now. | Centralizes promotion-to-adoption integrity for every reader. | Broadens this recovery correction into persisted-model validation and may change how old or inconsistent state loads. | Separate follow-up. |
| Convert the conflict into typed recovery attention. | Improves operator-facing recovery guidance. | Changes application-level error semantics beyond the observed predicate defect. | Defer pending an explicit product decision. |

### 3.3 Implementation scope

The first change is one Delivery-domain task:

1. Add a private predicate beside `_reject_unpromoted_adoption_restart()` that evaluates the five
   matching-promotion conditions.
2. Return from the guard when the current adoption is covered by that evidence.
3. Preserve the existing restart ordering. In particular, do not move attempt-ref validation,
   preservation, reset, worktree restoration, or `PortfolioCoordinator.release()`.
4. Do not change receipt schemas, serialized coordination shape, application recovery orchestration,
   runtime transition orchestration, or the active interrupted Change.

Although four production paths call `restart()`, caller-specific changes are unnecessary. The
workspace-manager predicate is the shared behavioral boundary and therefore the smallest fix that
repairs recovery, repair recovery, retry, and return consistently.

Cross-receipt model validation is not part of this task. The restart predicate must still fail closed
for mismatched current evidence because persisted state can be inconsistent even when public write
operations normally construct matching receipts.

### 3.4 Regression proof

Add focused tests beside the existing unpromoted-adoption restart test in
`serve/delivery/tests/test_change_workspace.py`.

The primary regression must construct this state through public workspace operations:

1. Create and adopt an external descendant.
2. Promote that exact adopted head.
3. Commit and record a later reviewed descendant.
4. Acquire a new exact Builder writer.
5. Commit a clean rejected child.
6. Call `restart()` with the exact attempt and rejected head.
7. Assert the rejected child is stored at `refs/owlbear/attempts/<change-id>/<attempt-id>`.
8. Assert branch and worktree return to the later reviewed descendant, not the older promoted head.
9. Assert writer custody and the current capacity-ledger slot are released.

Replay the same `restart()` after release and assert it returns the same reviewed coordination
without raising. This proves the matching-promotion exception also restores the existing
released-restart idempotence contract.

The existing unpromoted-adoption rejection test must pass unchanged. A hand-built mismatched receipt
test is optional at this layer: if mismatch construction requires bypassing public operations, prefer
a separate `ChangeCoordination` cross-receipt validation change rather than coupling this regression
to invalid fixture internals.

An additional application-level recovery test is not required for the first change. Existing tests
already prove claim removal and recovery ordering once `restart()` succeeds; the new workspace test
directly discriminates the faulty predicate for every caller.

### 3.5 Validation and live recovery sequence

Validate the code change in this order:

1. Run the new promoted-adoption restart test, its replay case, and the existing unpromoted-adoption
   rejection test.
2. Run all restart-related workspace tests.
3. Run `serve/delivery/tests/`.
4. Run Ruff check and format validation for the changed Delivery source and test files.
5. Obtain independent review of the exact implementation commit.

Live recovery is a separate, explicitly gated operation after the correction is integrated and the
running Delivery application has reloaded it. Before invoking recovery:

1. Re-read the exact runtime claim, writer, coordination, branch head, worktree head, cleanliness,
   adoption receipt, promotion receipt, and `last_reviewed_commit`.
2. Confirm the matching-promotion invariant and linear ancestry still hold.
3. Confirm the rejected head is still `fe906fbe2a3adfa283dc7fe51a71d58e1d95702c`, or replace this
   historical expectation with the newly observed exact head.
4. Invoke only the public exact-claim recovery operation. Do not edit runtime JSON, reset refs, or
   manipulate the worktree manually.
5. Verify the attempt ref preserves the rejected commit, branch and worktree equal the reviewed head,
   writer custody and runtime claim are removed, and the capacity slot is available.

Only after those checks should the separate capacity-consolidation Change resume frontier planning.

## 4. Recommendation, Confidence, And Limits

Implement the matching-promotion predicate at the shared restart guard and add the direct
workspace-manager regression plus replay assertion. Keep the existing unpromoted test unchanged.
This is the narrowest change that preserves explicit review authority and repairs all four restart
callers without modifying their orchestration.

**Confidence:** High. The defective branch, receipt relationship, shared caller boundary, release
behavior, and missing regression state were verified from current source. The plan was independently
challenged, and its highest-impact claims were checked against semantic usages and exact source.

**Limits:** This document does not authorize implementation, lifecycle admission, commits, or live
recovery. It does not establish a general cross-receipt model invariant, change recovery conflicts to
typed attention, or prove behavior for manually corrupted coordination files. Runtime state can
drift; all live identities must be observed again immediately before recovery.
