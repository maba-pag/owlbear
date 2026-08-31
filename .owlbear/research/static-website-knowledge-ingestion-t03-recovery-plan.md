# Static Website Knowledge Ingestion T03 Recovery Plan

> **Owning task:** `static-website-knowledge-ingestion / OUT-004-T03` - Prove the assembled
> Knowledge lifecycle
> **Date:** 2026-08-23
> **Question:** How should Delivery resume OUT-004-T03 from its preserved interrupted candidate
> without laundering commit authority, losing useful work, or carrying unbound proof into the new
> claim?
> **Status:** Implementation-ready after recovery and independent architecture challenge. This
> document does not authorize lifecycle mutation by itself.
> **Canonical location:** `.owlbear/research/static-website-knowledge-ingestion-t03-recovery-plan.md`.
> A root convenience copy may exist but must remain uncommitted.

## 1. Context and Question

OUT-004-T03 was interrupted after task-owned changes were made in the managed Change worktree. The
initial exact-claim recovery retained the dirty bytes and writer custody as designed. The changes
were then committed as `fe906fbe2a3adfa283dc7fe51a71d58e1d95702c`, but recovery failed because
the Delivery restart guard incorrectly treated a previously promoted external head as unpromoted.

Commit `d1977a47d169927cd5ee42b0031979029385a0ea` corrected that restart predicate. Exact recovery then
succeeded on 2026-08-23:

- OUT-004 has no active claim or recovery attention.
- The coordination record has no writer.
- The Change branch and managed worktree are clean at reviewed commit
  `9612e7c6caf697a3d5f7a05e81e599f84246b5ce`.
- `refs/owlbear/attempts/static-website-knowledge-ingestion/e2bee6c8-a8af-4e23-bfc1-42beb3273b9b`
  preserves `fe906fbe2a3adfa283dc7fe51a71d58e1d95702c`.
- The preserved commit changes only `tests/test_mcp_knowledge_static_refresh.py`.

These are historical observations, not durable mutation authority. Every live identity and
precondition must be re-read before acquisition.

The remaining question is how to reuse the useful test implementation without treating the
preserved commit as reviewed work. The selected route is normal Builder reacquisition followed by
source-level reconstruction, exact-candidate proof, independent review, result publication, and an
Orchestrator-forwarded transition.

## 2. Sources Studied

| Source | Load-bearing fact | Evidence limit |
| --- | --- | --- |
| `serve/delivery/src/owlbear_delivery/portfolio_application.py` | `recover_claim` removes a clean failed claim only after workspace restart succeeds; `show_build_context` reconstructs fresh claim-bound authority. | Runtime state can change after inspection. |
| `serve/delivery/src/owlbear_delivery/change_workspace.py` | Restart preserves a rejected head under an attempt ref, restores the reviewed boundary, and releases custody. Result publication validates the current writer-owned clean branch head. | It does not make a preserved attempt commit publishable under a future claim. |
| `serve/delivery/src/owlbear_delivery/delivery_runtime.py` | Result publication requires the active claim, exact task digest, exact completed commit, and writer-head validation. Implementation advance records the reviewed result and releases custody. | Mechanical validation does not replace required observations or independent review. |
| `share/skills/w-packet-building/SKILL.md` | Builder requires fresh Build context, may not edit under recovery attention, must create a scoped commit, rerun proof at that commit, and must never cherry-pick. | Workflow authority applies only after Orchestrator supplies a valid launch package. |
| `share/skills/r-workspace-governance/SKILL.md` | Interrupted task-owned bytes may be inspected and explicitly adopted, but only owned paths may be committed with `commit-owned`. | Byte provenance does not carry observation or review receipts. |
| `.owlbear/delivery/runtime/changes/static-website-knowledge-ingestion/frontier.json` | T03 maintains one test file and requires deterministic assembled proof plus one opt-in real BGE-M3/filesystem-Qdrant proof. | The frontier is mutable Delivery state and must not be hand-edited. |
| `.owlbear/delivery/runtime/coordination/changes/static-website-knowledge-ingestion.json` | Recovery restored the branch to `9612e7c6` and released writer custody while retaining reviewed authority. | The coordination record may drift before implementation begins. |
| `.owlbear/research/delivery-promoted-adoption-restart-recovery.md` | Records the original restart defect, matching-promotion invariant, correction scope, and recovery gate. | It addresses engine restart, not completion of T03. |
| Preserved commit `fe906fbe2a3adfa283dc7fe51a71d58e1d95702c` | Contains a one-file candidate implementation: an SSRF resolver observation and a model-marked BGE-M3/Qdrant assembled smoke test. | It has no T03 observation receipt, review receipt, or result candidate. |
| Fresh Claude Opus 5 architecture challenge, 2026-08-23 | Identified proof working-directory sensitivity, model-runtime risk, target drift, stale recovery text, and the danger of misusing external-head adoption. | Recommendations were advisory and were reconciled against current workflow contracts. |

No external sources or externally derived implementation patterns were used.

## 3. Analysis

### 3.1 Authority boundary

The attempt ref preserves bytes and history only. It does not preserve an active claim, writer
custody, task result, observation receipt, or review receipt. `fe906fbe2` therefore must not be:

- published under a new claim;
- moved directly back onto the Change branch;
- cherry-picked by Builder;
- adopted or promoted as an external Change head; or
- described as reviewed or supported runtime evidence.

The preserved diff may be read as candidate implementation evidence. A newly acquired Builder may
recreate equivalent edits inside the fresh task boundary, inspect every hunk against current task
authority, and commit the resulting owned path normally. That new commit receives entirely fresh
proof and review.

### 3.2 Reconciled challenger findings

The challenge changed the plan in four material ways:

1. Recovery steps were removed because recovery completed while the challenge was running.
2. Proof commands must run from the managed Change worktree. The root `dev` checkout and the Change
   branch can have different pytest marker and timeout configuration.
3. The prior `13 passed, 1 deselected` report is diagnostic history only. No canonical T03 receipt
   exists, so it supports no publication claim.
4. External-head adoption and promotion are rejected as a recovery route. They reconcile a genuine
   external branch advance; using them for an engine-preserved attempt would manufacture the wrong
   provenance.

Two challenger recommendations were rejected:

- Running acceptance proof before the completed recovery was not a legitimate route. Fresh Build
  context had failed at `fe906fbe2`, and Builder may not continue under recovery attention.
- Cherry-picking the preserved commit after reacquisition violates the packet-building workflow.
  Reconstruction must occur at the source level and produce a new scoped commit.

### 3.3 Acceptance mapping that must be proved

Before the new commit is reviewed, Builder must map each T03 acceptance observation to concrete
assertions in `tests/test_mcp_knowledge_static_refresh.py`:

| Observation | Required discriminating evidence |
| --- | --- |
| Deterministic registration, refresh, and search | Resolver invocation through SSRF validation; one persisted SQLite document and chunk; a positive QueryFacade-backed snippet; normal adapter `store` then `search` events. |
| Unchanged and changed refresh | Stable source/document/chunk counts for normalized unchanged content; changed-content replacement; no stale search evidence; ordered adapter `delete`, replacement `store`, then `search` events. |
| Typed failures | Redacted `stage`, `code`, `retryable`, and `message` for acquisition, extraction, persistence, indexing, and query; successful and partial refresh projections retain source, count, and error fields. |
| Routine proof boundary | The focused deterministic command passes and reports the model smoke deselected. |
| Real-model support boundary | The isolated model command runs the 600-second test without skip or deselection, uses real BGE-M3 and filesystem Qdrant, reads a non-empty embedding through public `get_embedding`, and returns fixture content from assembled search. |

If the reviewed baseline already supplies an observation, Builder should preserve it and record the
specific assertion. If an observation is absent or nondiscriminating, Builder must strengthen the
same maintained test file before committing. The preserved diff is not presumed complete.

### 3.4 Alternatives

| Alternative | Benefit | Risk | Decision |
| --- | --- | --- | --- |
| Fresh claim plus source-level reconstruction from the attempt diff. | Preserves useful work while retaining normal claim, commit, proof, and review authority. | Requires a new commit and complete proof. | **Selected.** |
| Reimplement T03 without consulting the attempt ref. | Avoids accidental trust in interrupted work. | Discards a small, coherent, task-owned implementation and increases divergence risk. | Fallback only if the preserved diff materially under-delivers. |
| Cherry-pick `fe906fbe2`. | Recreates the exact tree quickly. | Explicitly prohibited by packet-building authority and obscures the new claim's authored work. | Reject. |
| Adopt and promote `fe906fbe2`. | Restores the old commit identity. | Misstates external provenance and bypasses the intended interrupted-attempt route. | Reject. |
| Add a resume-clean-candidate engine operation first. | Could preserve commit identity in future incidents. | Broadens this task into engine design after existing recovery already succeeded. | Separate future Design question. |
| Synchronize the Change with `dev` before T03. | Reduces later target drift. | Mixes unrelated target changes into the T03 proof boundary. | Defer to finalization preparation. |

## 4. Implementation Plan

### 4.1 Operator and state gate

Before any claim acquisition:

1. Confirm no other user or agent session is intentionally operating on
   `static-website-knowledge-ingestion`.
2. Re-read OUT-004 and retained-worktree state.
3. Require no active claim, no recovery attention, no writer, a clean managed worktree, and branch
   and worktree head equal to `9612e7c6caf697a3d5f7a05e81e599f84246b5ce`.
4. Resolve the exact attempt ref and require it still names
   `fe906fbe2a3adfa283dc7fe51a71d58e1d95702c`.
5. Stop if any identity differs. Diagnose the new state rather than substituting these historical
   values.

The engine serializes acquisition and prevents simultaneous active claims. Human confirmation is
still required to avoid two sessions sequentially competing for the newly claimable task.

### 4.2 Orchestrator acquisition

1. Let the owning Orchestrator call `acquire_frontier_work`; do not create or target a claim through
   raw runtime edits.
2. Require the returned Builder launch to name this Change, OUT-004, and OUT-004-T03. If another
   ready work item is selected first, route that launch normally and do not appropriate it for T03.
3. Call `show_build_context` with the new attempt and claim identities.
4. Require launch equality, task digest equality, exact writer custody, source head and reviewed head
   `9612e7c6`, a clean worktree, and no recovery attention.
5. On any context or custody failure, return the workflow's structured `dispatch_failure`; do not
   edit.

### 4.3 Reconstruct the candidate

1. Inspect the complete diff from `9612e7c6` to the preserved attempt ref, limited to
   `tests/test_mcp_knowledge_static_refresh.py`.
2. Verify each hunk is still inside T03's maintained surface and compatible with the fresh Build
   context.
3. Recreate the useful behavior with normal source edits. Do not cherry-pick, merge, move refs, use
   `git reset`, or use the adoption APIs.
4. Complete the acceptance mapping in section 3.3. Add only missing discriminating assertions in the
   maintained test file.
5. Preserve the task constraints: use `server.build_app_context`; keep real SQLite, SSRF,
   ContentStore, QueryFacade, coordinator, registration, refresh, and MCP search on the assembled
   path; do not change production code, dependencies, shared fixtures, or `uv.lock`.

### 4.4 Shape and commit

Run enough pre-commit proof from the managed worktree to shape the implementation. At minimum, run
the deterministic focused command once. Run the model command before commit when needed to resolve
test implementation failures, but do not treat any pre-commit run as publication evidence.

Commit only the maintained test file with the scoped helper:

```text
uv --project <owlbear-root> run commit-owned \
  -m "test: prove assembled Knowledge lifecycle (#OUT-004-T03, builder)" \
  -- tests/test_mcp_knowledge_static_refresh.py
```

Require the new commit to descend from the fresh launch source head, change only the maintained
surface, and leave the entire managed worktree clean.

### 4.5 Exact-candidate proof

Run both commands from the managed Change worktree against the exact new commit:

```text
uv run --locked pytest tests/test_mcp_knowledge_static_refresh.py -n 0 -q --tb=short
uv run --locked pytest tests/test_mcp_knowledge_static_refresh.py -m model -n 0 -q --tb=short
```

The first command must pass the deterministic scenarios and report the model test deselected. The
second must execute the model test with zero skips and zero deselections. A model download failure,
missing runtime prerequisite, timeout, skip, or deselection is not support evidence.

Also run touched-file Ruff check and format validation. After every passing command, construct a
canonical `DeliveryObservationReceipt` bound to the new exact commit. Never reuse the prior terminal
report or calculate receipt identities manually.

If `uv run --locked` fails because the admitted lock/configuration premise is inconsistent, do not
change `uv.lock`: return to Planning with the exact missing premise. If a user-owned model download
or machine action is required, use one bounded Action Request. If the model test exposes an in-scope
test defect, repair it under the same claim, create a successor commit, and rerun affected proof.

### 4.6 Review, publication, and transition

1. Dispatch the configured `build-reviewer` with the unchanged launch, fresh Build context, source
   commit, exact candidate, one-file diff, proof output, custody evidence, and no receipts from
   `fe906fbe2`.
2. Require an independent pass bound to the exact new commit and non-empty evidence covering all
   acceptance observations and task constraints.
3. Construct the canonical review receipt and `DeliveryTaskResult` with the fresh task digest,
   exact candidate, and fresh observation receipts.
4. Builder calls `publish_delivery_result` with the active claim and returns the published output in
   `AdvanceDelivery`.
5. Builder does not call `transition_delivery`. The owning Orchestrator forwards the unchanged
   transition, then re-reads OUT-004 and verifies T03 is the third reviewed result and T04 is next.

### 4.7 Follow-up boundaries

The following work does not belong in T03:

- target synchronization and finalization preparation;
- stale recovery-attention invalidation;
- first-class clean-candidate resume semantics;
- attempt-ref retention or garbage collection policy;
- broader model quality, performance, or hardware validation; and
- runtime support documentation, which belongs to OUT-004-T04 after T03 passes.

## 5. Verification Checklist

- [ ] No competing operator session is intentionally working on the Change.
- [ ] Fresh claim, context, custody, source head, and task digest are exact.
- [ ] The attempt ref is inspected only as source-level candidate evidence.
- [ ] No cherry-pick, external-head adoption, raw reset, or runtime JSON edit occurs.
- [ ] Only `tests/test_mcp_knowledge_static_refresh.py` changes.
- [ ] Every T03 acceptance observation maps to a discriminating assertion.
- [ ] A new scoped candidate commit exists and the worktree is clean.
- [ ] Deterministic exact-candidate proof passes with the model test deselected.
- [ ] Real-model exact-candidate proof passes with zero skips and deselections.
- [ ] Ruff check and formatting pass for the maintained test file.
- [ ] All observation and review receipts bind the new exact commit.
- [ ] Independent review passes the exact candidate.
- [ ] Builder publishes the result; Orchestrator alone forwards the transition.
- [ ] OUT-004 records T03 reviewed and exposes T04 as the next task.

## 6. Recommendation, Confidence, and Limits

**Recommendation:** Reacquire OUT-004-T03 through normal Orchestration, reconstruct the useful
one-file implementation from the preserved attempt diff without cherry-picking, close any
acceptance-assertion gaps, and earn entirely fresh exact-commit proof and review before publication.

**Confidence:** High for the recovery and authority sequence. Current source, persisted Delivery
state, the preserved commit, the completed restart correction, and an independent architecture
challenge all support this route.

**Limits:** Model-runtime feasibility remains unproved until the exact task command executes. The
current work-item and coordination observations can become stale. This document neither acquires a
claim nor authorizes manual state repair, target synchronization, or publication.
