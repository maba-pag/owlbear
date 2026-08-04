# Target Delivery Information Flow — Step 11: Plan Target Scope

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-03
> **Question:** How should one active read-only Plan claim become the smallest independently reviewed
> task graph that runtime can schedule and Builder can execute without recovering hidden Planner
> meaning?

## 1. Status Quo And Evidence

Current Planner receives an active plan job, exact authority and source commit, resolves outcome and
commitment context, proposes tasks, and invokes one assigned `planner-challenger`. The workflow asks
each task to name admitted boundary, dependencies, required outputs, acceptance observations, and
proof. Orchestration forwards the review and tasks through `finish_plan`.

Current `TargetTask` persists only task identity, work item, plan scope, title, mutable status, and
build receipt. Dependencies, outputs, commitments, acceptance, and proof survive only inside
free-form plan claim or review evidence. `_publish_accepted_plan` consequently creates every build
job with only the plan job as predecessor, making all tasks ready together regardless of the
reviewed dependency order.

## 2. Decision D1 — Typed Self-Contained Task Authority

An accepted task is the durable executable plan contract, not a title pointing back to Planner
prose. Persist exactly the meaning runtime and Builder consume:

- stable task, outcome, and plan-scope identities;
- one bounded result and applicable admitted commitment identities;
- dependency task identities within the plan; cross-outcome ordering remains derived from the
  Delivery Contract;
- required outputs and owned or maintained surfaces, without prescribing private implementation;
- concrete acceptance and proof observations independently verifiable under `h-ac-quality`;
- task-specific constraints and exclusions needed to prevent silent scope expansion.

Separate this immutable task definition from mutable runtime state such as pending, active,
reviewed, superseded, and build receipt. Runtime validates unique identities, reference closure,
acyclic task dependencies, scope ownership, commitment links, and at least one ready task. It creates
each build job with predecessor jobs derived from task dependencies and the admitted outcome graph.

Builder receives the exact task definition directly through `show_planned_task`; it does not parse a
plan receipt or review transcript to discover its assignment. The accepted task graph is sufficient
for replanning to keep, revise, or drop unreviewed work while preserving reviewed tasks.

Reviewer observations remain inside the active Planning cycle only. Once Planner publishes the final
task chain and issues `advance`, that graph and board transition are the result; do not retain review
prose merely to demonstrate that review occurred.

## 3. Decision D2 — One Exact Plan Context

After validating its launch identities, Planner calls one `show_plan_context(change_id, job_id,
attempt_id)` projection. It returns only:

- the active job, attempt, authority digest, exact source root and head, and plan scope;
- the owning outcome's promise, acceptance, dependencies, and linked commitment definitions;
- architecture-defined task, interface, constraint, and proof boundaries carried by the contract;
- the complete relevant request and resolution, when resuming a blocked Planning item;
- for replanning, preserved reviewed tasks and results, invalidated task-result commit bindings and
  supersession or removal requirement, superseded unreviewed tasks, and the typed return finding.

This replaces Planner's normal sequence of `show_job`, `show_attempt`, `show_work_item`,
`resolve_commitments`, activity traversal, receipt lookup, and semantic-update joins. Keep those
general tools for Cockpit, diagnostics, and roles that genuinely need their individual information
classes. Exclude unrelated outcomes, full portfolio state, Design rationale, raw attempts, review
history, and receipt prose.

Planner inspects source directly in the exact read-only warm workspace and may use the owned
`source-researcher` for one bounded factual question. Remove required `Explore`. The Delivery
Contract remains semantic authority; source establishes feasibility and current ownership, not new
product meaning.

Planner hands the complete candidate task graph and exact identities to the assigned challenger.
The challenger independently calls `show_plan_context` and inspects decisive source; it does not
receive Planner's narrative, confidence, or selected evidence as authority. This preserves a fresh
comparison while avoiding duplicate context assembly.

## 4. Decision D3 — Planner Owns The Transition

Planner Challenger returns source-grounded feedback over the complete candidate graph inside the
active Planning cycle. Planner considers every material observation, applies useful corrections,
and rejects speculative scope or overcorrection. Material graph changes receive fresh review.
Planner alone chooses the transition, including `retry` when the attempt is wrongly anchored or
unsafe to continue.

After review, Planner issues exactly one transition instruction:

- `advance` after separately publishing one valid final task chain;
- `retry` to leave the item in `planning` for a fresh attempt;
- `return(target="design")` when admitted meaning is insufficient or contradictory;
- `block` with reason, unblock condition, expected evidence, exact locators, and an optional request.

Runtime receives no review output. Persist the typed task chain and transition only. Review feedback,
Planner dispositions, commands, and debate remain inside the active work cycle.

## 5. Decision D4 — Cohesive Build Claims

Choose task boundaries by ownership and proof, not size targets. One task produces one cohesive
result that one Builder can implement in the warm change branch, commit without unrelated work, and
prove at a maintained boundary. Split only when results have distinct owners, can be independently
accepted, require real ordering, or a combined diff would prevent focused review and correction.

Do not create tasks per file, module touched, test type, implementation step, or agent convenience.
Proof belongs with the behavior it distinguishes; never create a separate "add tests" task. One task
is correct when the full outcome remains one coherent reviewable claim. Dependencies express only
required result ordering, not preferred narration order.

Planner uses the architecture's proof boundaries and `h-ac-quality`, then takes an evidence-backed
position. It may adapt source-reading depth to uncertainty and coupling but may not omit a task field
or weaken observable acceptance because a change appears small.

## 6. Decision D5 — Fresh Invisible Review

The assigned `planner-challenger` is a fresh high-capability invocation for each Planning attempt. It
is independent of Planner and prior Specification review. Within that attempt, materially changed
candidates receive another fresh invocation of the same role and model; no conversational continuity
or persisted reviewer identity is required. A later `retry` starts a wholly fresh work cycle.

The challenger checks intent and contract fidelity, task completeness and cohesion, source
feasibility, dependency closure, proof validity and proportionality, preserved accepted work during
replanning, and whether a defect belongs to Design. It does not rewrite tasks, prescribe private
implementation, assign priorities, issue scores, or call runtime. Ordinary feedback is advisory;
it may identify attempt-level risk but issues no lifecycle command.

## 7. Decision D6 — Separate Task Publication And Advance

After internal review, Planner publishes the complete typed task chain through its owning operation.
Runtime validates and hashes it as a claim-scoped candidate without moving status; identical replay
returns the same candidate identity and digest. Planner issues `advance` referencing that identity.
Runtime atomically promotes the exact active-claim candidate, moves to `implementation`, and exposes
dependency-ready tasks. Implementation claims bind authority and promoted task-definition digests.

For a new plan, publication requires at least one task and one dependency-ready Build job. For
replanning, reviewed task definitions and Build receipts remain immutable; apply explicit keep,
revise, or drop rulings only to superseded unreviewed tasks, validate replacement references, and
publish one coherent replacement graph. Stale candidate, authority, source head, or task identity
or transition reference fails before movement.

A crash after publication leaves an unpromoted candidate, never task authority. Exact-claim replay
may finish its transition; claim recovery exposes the candidate as retry context to the next Planner,
which must review and republish before promotion. Superseded candidates have no scheduling consumer.

Retain only the task chain and identities later needed to bind implementation claims. Do not persist
Planning claim prose, reviewer narrative, commands, or review evidence. `retry`, `return`, and
`block` publish no task chain unless a later consumer genuinely needs the partial output.

## 8. Step Completion

Planner may refine admitted scope into implementation-sized results but may not change Product
Promise, architecture, outcome dependencies, planning scope, or protected commitments. A
contradiction returns to its earliest owning authority.

Step 11 is decided. One exact context supports a read-only Planner and invisible independent
Challenger; one published typed task chain plus `advance` becomes digest-bound Implementation
authority. Step 12 receives one active Implementation claim or optional Assembly claim with exact
authority, source, and proof boundaries.