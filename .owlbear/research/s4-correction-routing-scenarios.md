# S4 Correction Routing Scenarios

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** When a reviewer rejects work, what may agents repair or redesign, and what must return to the user?
> **Status:** Evidence base for the S4 resolution in `correction-authority-policy.md`.

## 1. Context and Question

S3 established four implementation-review dispositions: acceptable, needs repair, restart the task,
or return the task for redesign/replanning. Those labels are useful only if they route by the earliest
invalid assumption rather than by reviewer preference or finding severity.

S4 must preserve S1's graded commitments and S2's localized blocking. A correction should invalidate
the smallest affected dependency chain without letting agents silently change protected meaning.

## 2. Sources Studied

| Source | Relevant fact |
|---|---|
| `design.md` sections 9-10 | Records two DN-003 bootstrap corrections and the current finding routes |
| `design.md` sections 13-14 | Records the breaking `shape` to `plan` lifecycle correction |
| `decisions.yaml` DEC-021 | Receipt currency changes both evidence guarantees and repeated-proof cost |
| `decisions.yaml` DEC-033 | Lifecycle vocabulary correction made completed DN-003/DN-004 work stale |
| `plan-dn-003-d241933d.yaml` | Candidate behavior existed; remaining work was durable public-boundary proof repair |
| `plan-dn-003-720eb6f605cc.yaml` | Later planning added one causal dependency resolver and caller/projection proof |
| `delivery-operating-model-reframe.md` | Quantifies amendment radius across runtime, MCP, agents, UI, tests, and cutover |
| S1-S3 policies | Protect user-requested meaning, localize blocking, and require staged independent review |

## 3. Routing Rule Under Test

Find the earliest statement made false by the review evidence:

1. If only code or focused proof is false, repair or restart implementation.
2. If the task's method, boundary, dependency, or proof plan is false, redesign the task.
3. If several tasks cannot compose into their deliverable, redesign that deliverable's plan.
4. If the plan can no longer preserve user-reviewed meaning, return to collaborative Specification.
5. Ask the user only when correction changes a dealbreaker, protected request, important reviewed
   commitment, or requires an action only the user can perform.

The reviewer supplies evidence and identifies the earliest contradicted claim. The engine computes
affected dependents. Neither the reviewer nor the engine may promote a technical defect into a broad
redesign without naming the invalid parent claim.

## 4. Actual Scenarios

### A. Proof code is wrong; task remains sound

At candidate `b55867f`, the admitted runtime behavior already existed. Review found remaining defects
in durable public-boundary tests, including persisted-receipt and non-monotonic-order cases.

**Route under test:** `needs repair`. Keep the task and deliverable. The same builder repairs tests and
the independent reviewer rechecks the changed code and affected proof.

**User consequence:** None. Intended behavior, acceptance meaning, and implementation strategy remain
unchanged. A user interruption would expose test mechanics without enabling a meaningful decision.

### B. Execution method fails; proof claim remains sound

The 283-case DN-003 proof exceeded one runner process limit. The correction used bounded partitions at
the same revision and recorded every collected case identity, aggregate coverage, selector, and exit
status.

**Route under test:** revise the task's proof procedure and review it. Do not weaken or deselect cases.
Do not return to the user unless the full accepted behavior can no longer be proven economically or
reliably.

**User consequence:** None while proof strength is preserved. This is a method change, not acceptance
change.

### C. Implementation is unusable; task design remains sound

Suppose a builder implements the right task against the right interfaces, but the diff is pervasively
incorrect, mixed with unrelated edits, or cannot be repaired with confidence.

**Route under test:** `restart task`. Discard or supersede that implementation attempt, retain the
reviewed task, and invoke a fresh builder. Re-review the new exact commit.

**User consequence:** Delay and compute cost only. Surface the restart in progress history; do not
request a semantic decision.

### D. The task boundary omitted necessary work

At candidate `2578367`, DN-001's planned implementation and tests were already present, so its builder
had no scoped delta to produce. Source inspection located the missing carrier capability under
DN-003/IF-003 and its proof instead.

**Route under test:** `redesign/replan`. Stop the invalid task, move work to the owning runtime task,
review the revised plan, and invalidate only tasks that depend on the old boundary.

**User consequence:** Report that implementation ownership changed. Do not block for approval while
the same reviewed outcome, constraints, and acceptance remain intact.

### E. Later evidence requires a cross-task strategy correction

DN-003 planning found that runtime and query callers independently evaluated accepted dependencies.
The revised strategy introduced one internal causal-set resolver and added projection/reconciliation
proof across both callers.

**Route under test:** return the affected deliverable to planning. Revise task boundaries and proof,
independently review the changed plan, then resume implementation. Preserve unaffected accepted work
whose assumptions remain current.

**User consequence:** Notify at the next semantic summary. Request input only if the correction changes
observable behavior, a protected boundary, or an important accepted tradeoff.

### F. Evidence guarantees materially change

Receipt currency could have required the exact tested commit forever or reused exact proof at later
commits whose changed paths do not intersect a frozen impact closure. The alternatives change repeated
proof cost and the risk that an incomplete closure preserves stale evidence.

**Route under test:** collaborative Specification. The agent explains the proof-strength, cost, and
failure consequences; the user establishes the acceptable guarantee. Architecture and plans are then
revised and independently challenged.

**User consequence:** Real decision. This changes how much confidence completion evidence provides,
not merely how code is organized.

### G. Correct terminology changes phase behavior and public contracts

The pipeline first implemented a `shape` job after admission. Later correction established that
Specification ends at admission and Delivery begins with `plan`. This made completed DN-003/DN-004
work stale and required changes across runtime, MCP, agents, UI, tests, and cutover with no alias.

**Route under test:** collaborative Specification followed by broad replanning. This is not a local
rename because it changes agent authority and what each phase means.

**User consequence:** Real decision. The correction changes the workflow the user relies on and the
authority granted to post-admission agents.

### H. Assembled review finds interaction failure

If task commits are correct alone but fail together, return to the lowest deliverable whose composition
claim is false. Add or revise integration tasks, then repeat affected task and deliverable review. If
all deliverables pass alone but the full pipeline fails its user workflow, correct the owning
deliverables and repeat whole-plan review.

**User consequence:** No request while protected meaning remains achievable. Return to the user if the
only credible repair weakens that meaning or requires a new material consequence.

## 5. Review Disagreement

A builder may answer a finding with source or proof showing that the reviewed claim still holds. The
reviewer then either withdraws the finding or identifies the exact unresolved contradiction. Repeating
a complete review without narrowing that contradiction recreates the DN-003 review loop.

Still unresolved for user guidance: whether one challenger should retain the finding through repair,
when a third independent judgment is warranted, and when persistent disagreement should conservatively
route backward instead of consuming another review round.

## 6. Technical Assessment, Confidence, and Limits

**Assessment:** Route to the earliest invalid claim and smallest affected dependency closure. Agents
autonomously repair, restart, or replan while reviewed meaning is preserved. Return to the user for
changes to protected meaning or material evidence/workflow guarantees, not for technical severity.

**Confidence:** High for scenarios A, B, D, F, and G because they are grounded in recorded DN-003
history. Medium for restart and disagreement handling because the current history demonstrates churn
but not a clean restart/arbitration protocol.

**Limits:** Exact invalidation algorithms, retry budgets, and finding schemas remain engineering work.
The historical decision records were recommendation-anchored, so they evidence consequences and
amendment radius rather than informed user preference.