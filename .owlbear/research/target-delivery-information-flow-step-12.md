# Target Delivery Information Flow — Step 12: Build Or Assemble

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-03
> **Question:** How should one active Build or Assembly claim produce an independently reviewed exact
> commit, advance warm workspace custody, and retain only state later Delivery decisions consume?

## 1. Status Quo And Evidence

Current Builder rehydrates a started job through multiple generic reads, edits the assigned warm
worktree, runs focused proof, commits, and invokes `build-reviewer`. The reviewer is instructed to
inspect the exact commit but has no production proof-checkout integration. `ProofCheckoutManager`
already materializes a detached read-only worktree plus frozen admitted authority and validates that
neither changed during review; current agents and adapters do not use it.

Runtime `finish_build` can complete the job and mark its task reviewed, but no production caller
advances `ChangeWorkspaceManager.last_reviewed_commit` or releases writer custody. Those methods are
used only in tests. Current receipts retain claim prose, reviewer evidence, timestamps, and identity
fields even when no later runtime decision consumes them.

## 2. Decision D1 — One Exact Build Context

After launch validation, Builder calls one `show_build_context(change_id, job_id, attempt_id)` that
returns the exact immutable task definition, authority and task digests, applicable commitments,
predecessor result commits, current return or resume boundary, complete relevant request and
resolution when resuming a blocked item, and
writer coordination: source root, branch, head, integration target, last-reviewed commit, and claim
custody.

This replaces normal joins across job, attempt, work item, planned task, commitments, receipts, and
coordination. Keep those individual tools for diagnostics and Cockpit. Exclude portfolio state,
unrelated tasks, Design prose, prior review history, and generated summaries.
Builder verifies the warm branch and head before editing and remains inside the typed task contract.

## 3. Decision D2 — Detached Exact-Commit Review

For Build, Builder implements the smallest complete task result, runs the task-defined focused proof, and
creates one clean scoped commit without rewriting reviewed history. The system then uses
`ProofCheckoutManager` to materialize that exact candidate commit in a detached read-only worktree
with the frozen admitted contract. Proof-checkout setup or identity mismatch blocks review.

The Build transition cycle owns one deterministic proof-checkout operation that materializes,
validates, and cleans up the checkout. A setup or identity diagnostic prevents `advance` and never
falls back to the live worktree; Builder chooses `retry` or `block` from the diagnostic and retry
condition. Cleanup failure remains operational health work after the candidate decision.

The assigned Reviewer receives the active claim identity, complete typed task or composition
contract, exact candidate commit, changed-path/diff locators, and detached checkout roots. It
independently inspects source and executes only the distinguishing checks needed to verify acceptance,
preserved behavior, proof boundaries, and scope. Builder-provided command output is a locator or
useful clue, never proof by assertion.

Validate that checkout commit, tracked content, and authority remained unchanged before the worker
acts on the feedback, then delete the transient checkout. Do not archive the checkout, command transcript,
passing proof output, or review narrative. A failed cleanup is operational health work and does not
change the worker's transition instruction.

## 4. Decision D3 — Minimal Durable Implementation Result

An advanced Implementation result needs only what later scheduling, Assembly, integration, revision,
or correction consumes: change, authority, task definition, and exact completed-commit identities.
Assembly binds its composition contract to the exact completed branch head without creating another
commit. Runtime may derive a compact result identity from those fields when another record needs a
stable reference.

Do not persist reviewer prose, proof commands or output, actor names, model identity, or timestamps
merely to demonstrate review. Task definition already owns required behavior and proof. Internal
feedback remains inside the active work cycle; the exact commit and subsequent board status are the
pipeline result.

## 5. Decision D4 — Builder Owns The Transition

Build Reviewer returns feedback to Builder inside the active Implementation cycle. Builder applies
useful corrections, rejects overcorrection, and obtains fresh review after material commit changes.
Builder alone decides whether findings require correction, `retry`, `return`, or `block`.

Builder then issues one transition instruction:

- `advance` referencing the separately created exact final commit;
- `retry` to abandon the attempt and leave the item in `implementation`;
- `return(target="planning")` when the accepted task chain is incomplete or wrongly scoped;
- `return(target="design")` when admitted meaning is insufficient or contradictory;
- `block` with reason, unblock condition, expected evidence, exact locators, and an optional request.

Runtime receives no reviewer output or Builder disposition of it. Remove `repair`, `restart`,
`task-plan`, `solution-plan`, persisted disagreement response, and arbitration from the pipeline
contract.

## 6. Decision D5 — Strong Fresh Invisible Review

Use one owned `build-reviewer` with a high-capability Claude Opus model, providing model-family
diversity from Builder. Every Implementation attempt receives a fresh reviewer invocation. A
materially changed commit receives another fresh invocation of the same role and model within the
cycle; a later `retry` starts a fresh work cycle without persisted reviewer identity or feedback.

Reviewer checks the typed contract, complete exact-commit diff, source ownership, acceptance and
preserved behavior, proof validity and proportionality, scope, generated or assembled boundaries,
and commit ancestry. It does not rewrite code, prescribe private implementation, rerun broad tests
without a named risk, or issue scores. One review of a complete candidate is enough unless the worker
materially changes that candidate. Observations remain advisory and carry no lifecycle command.

## 7. Decision D6 — Separate Commit And Transition

Builder creates its exact scoped commit before issuing a transition; code and commit are not fields
inside the transition instruction. One recoverable transition operation validates the active claim,
referenced commit and workspace state, changes board status, and reconciles writer custody:

- `advance`: bind the exact commit to task authority, move forward when all required implementation
  work is complete, update the completed branch boundary, and release the writer;
- `retry`: preserve the abandoned head for recovery, reset to the last completed boundary, close the
  claim, and release the writer;
- `return`: preserve the head, reset and release the writer, then expose the exact earlier-column
  context;
- `block`: bind a clean resume commit, close the claim, release the writer, and make the item
  unclaimable until request resolution or explicit manual unblock satisfies its recorded condition.

The operation is idempotent and recoverable rather than dependent on an external atomic launch or
audit ledger. If interruption occurs after one owner changed, replay derives the missing workspace or
runtime transition from the exact claim, transition instruction, branch head, and commit binding.
Conflicting state fails closed for Cockpit repair. Cleanup of the detached proof checkout follows
every applied decision.

## 8. Decision D7 — Optional Read-Only Assembled Verification

Assembly is not a writing or merge phase. The Delivery Contract declares a composition contract on
one owning outcome only when its acceptance requires proof across multiple accepted task or outcome
results. Cross-outcome composition requires that owner's outcome dependencies to name every result
it verifies. Runtime schedules its one `assembly` job after those dependencies complete; ordinary
outcomes with sufficient task proof skip it. No change-level claim or status carrier exists.

Route the item directly to `build-reviewer` in Assembly-worker mode. It receives the exact
composition contract, completed task/result bindings, and current branch head in a detached proof
checkout. It is the sole independent verifier and receives no second review.

The verifier's `advance` carries the composition contract, verified head, and result identities;
runtime validates and binds them atomically with status movement. A crash before movement requires
fresh deterministic verification. No candidate record, commit, writer custody, or Builder invocation is created. Return to
`planning` when a result must be redone or task authority is missing, and to `design` for insufficient
admitted meaning. Operational inability uses `retry` or `block`.

Assembly never edits code or invokes a Builder subagent. Planner creates an explicit final
integration implementation task when wiring, migration, generation, or cross-result composition
requires code; it does not add one when independently implemented results already compose.

## 9. Step Completion

Step 12 is decided. Implementation produces one internally reviewed exact commit and issues its
transition; optional Assembly independently verifies declared cross-result behavior read-only. Step
13 owns mechanical transition behavior, and Step 14 decides integration and completion from
completed commit and composition bindings.