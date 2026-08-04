# Target Delivery Cutover

> Source concept: `.owlbear/research/target-delivery-information-flow-walkthrough.md` and Steps 01-14
> Frozen source digest: `0819b50a4fd34d8a4b42b4cd4900c325ed3b39948c7b697f6fba3aa2a05f561e`

## Problem

OwlBear's current target runtime proves several useful primitives, but its end-to-end delivery flow
still makes agents reconstruct context, lets reviewer dispositions mutate lifecycle state, stores
execution evidence inside semantic authority, and lacks deterministic package completion. The frozen
walkthrough defines a coherent replacement; this change implements it without preserving the retired
execution model.

## Actors

- The user owns Product Promise, material consequences, authorization, bounded requests, and manual
  recovery decisions.
- Designer owns authored Specification and finding resolution.
- Forward and Reverse Specification Reviewers advise independently before admission.
- Planner and Builder own their work-cycle transition choice after advisory review.
- Runtime owns derivation, validation, scheduling, transition mechanics, recovery, and Integration.
- Orchestrator launches runtime-selected work and forwards typed results without interpreting them.
- Cockpit exposes current state, attention, bounded controls, and completed-history lookup.

## Product Promise

A user can take one change from rough intent through reviewed autonomous delivery and deterministic
Integration while each actor receives only the authority needed for its decision, failures return to
the earliest responsible owner, and completion preserves a recoverable package beside the integrated
product result.

## Normal Workflow

1. Designer creates or resumes one change-owned package and authors `intent.md` and `design.md`.
2. Runtime deterministically derives the Delivery Contract from readable normative blocks.
3. Forward and Reverse Specification Reviewers independently challenge the same source-bound revision.
4. After user authorization, admission atomically publishes the contract and initial Planning frontier.
5. Runtime acquires ready claims; Planner or Builder receives one role-specific context projection.
6. The worker publishes its output, evaluates advisory review, and chooses `advance`, `retry`, `return`,
   or `block`; runtime applies the mechanical transition.
7. Runtime integrates the reviewed change head and completed package in one target commit, then performs
   replayable active-package and warm-worktree cleanup.

## Scope

Included:

- change-owned active packages and semantic checkpoint history;
- deterministic contract derivation and source binding;
- admission, revision carry-forward, runtime statuses, typed transitions, requests, and recovery;
- portfolio acquisition and role-specific Plan/Build context;
- deterministic Integration, completed history, attention, lookup, and cleanup replay;
- MCP, Cockpit, and agent-workflow cutover to the new contracts;
- canonical operator documentation and practical normal-boundary proof.

Excluded:

- compatibility with legacy target runtime records or retired tools;
- automatic reopen, branch/ref pruning, retention compaction, or destructive history cleanup;
- a persistent Integration claim, clean-path Integration agent, or completion reviewer;
- priority scoring, model scheduling, daemonized orchestration, or lease-based claim expiry;
- durable review prose, transcripts, command logs, passing reports, or authorization history;
- tests whose only purpose is pinning agent wording, documentation wording, or one acceptance line per
  requirement.

## Preserved Behavior

- VS Code remains the agent runtime; Python remains the deterministic control plane.
- Direct transport-free composition through Kanban core managers remains supported.
- Product changes use warm per-change worktrees and scoped commits.
- MCP adapters remain thin and return typed diagnostics.
- The configured integration target advances through compare-and-swap.
- Existing project test-domain mapping selects proportionate proof.

## Testing Policy

The default durable-test delta for prose and agent configuration is zero. Add or retain a durable test
when it protects observable runtime behavior, a public tool contract, a persisted schema or transition,
a Git safety invariant, data-loss recovery, or an assembled user workflow that is credible to regress
and difficult to notice. Prefer one normal-boundary scenario covering several requirements over
one-test-per-criterion. Validate prose and agent changes through structural inspection and focused
review unless they alter executable loading or tool availability.

## Success

The cutover succeeds when a representative change completes the normal workflow using only the new
contracts; blocked and returned work resumes with its owning context; a semantic-only revision can
create a package-only completion; Integration rejects an unreviewed branch head; interrupted
publication replays without duplicate authority; and completed history supports bounded lookup and
manual recovery.

## Technically Done But Wrong

- Agents appear updated but still reconstruct authority through broad portfolio reads.
- Reviewers still command lifecycle transitions or their prose remains scheduling authority.
- Generated authority can diverge from authored Specification without deterministic failure.
- Product code integrates before the completed package, or cleanup requires a second commit.
- Integration publishes commits beyond the recorded reviewed boundary.
- A semantic-only revision remains permanently Integration-ineligible.
- Test volume grows by asserting agent prose rather than protecting behavior.

## Normative Commitments

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: frozen walkthrough Steps 1-9
statement: Authored Specification is the sole semantic source; the Delivery Contract is a deterministic source-bound projection.
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
provenance: frozen walkthrough Steps 10-13
statement: Workers alone choose advance, retry, return, or block; reviewers remain advisory and runtime applies transitions mechanically.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: frozen walkthrough Step 14
statement: Integration publishes reviewed product state and the completed change package together through one compare-and-swap target update.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: user instruction 2026-08-04
statement: Durable tests protect credible functionality and safety risks; agent or documentation wording alone does not require a test.
```

```yaml target-contract
kind: commitment
id: COM-005
class: important-reviewed
provenance: frozen walkthrough cross-step information classes
statement: Each actor receives the lowest information class sufficient for its decision and does not reconstruct authority from conversation.
```

```yaml target-contract
kind: commitment
id: COM-006
class: important-reviewed
provenance: frozen walkthrough correction loop
statement: Failure and changed meaning return to the earliest responsible owner with typed successor context rather than an interpretation coordinator.
```

```yaml target-contract
kind: commitment
id: COM-007
class: agreed-path
provenance: frozen walkthrough migration decisions
statement: The cutover removes retired runtime contracts instead of maintaining dual behavior.
```

## User-Facing Outcomes

```yaml target-contract
kind: outcome
id: OUT-001
title: Change-owned package foundation
promise: One active package contains the authored Specification and change-owned delivery material from session creation onward.
acceptance:
  - Creating a new Design session atomically exposes one package containing initialized intent, design, and generated-contract destination; divergent replay fails without replacing bytes.
  - Publishing a semantic checkpoint records authored package state on the dedicated package-history ref without modifying the product branch.
commitments: [COM-001, COM-005, COM-007, COM-009, COM-011]
dependencies: []
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Deterministic contract and admission
promise: Runtime derives, validates, revises, and admits execution authority from the authored Specification without semantic re-authoring.
acceptance:
  - Given source bytes with readable commitment and outcome blocks, derivation returns one canonical semantic contract, deterministic outcome scopes, and source hashes; malformed, missing, duplicate, unknown, or unresolved definitions return typed diagnostics and publish nothing.
  - Given an authorized source-bound candidate, admission re-derives under lock, idempotently checkpoints the package, then publishes contract and runtime frontier with the receipt becoming visible last; interruption replays from the checkpoint or transaction identity.
  - Given a quiescent revision, carry-forward preserves only byte-identical outcome projections closed over linked commitment bodies and invalidates the changed dependent closure.
commitments: [COM-001, COM-005, COM-006, COM-007, COM-009, COM-011, COM-012]
dependencies: [OUT-001]
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Mechanical delivery state
promise: Delivery status and correction are governed by worker instructions and runtime invariants rather than reviewer commands.
acceptance:
  - Given an active Planning, Implementation, or Assembly claim with its required output, the transition boundary accepts advance, retry, return to an allowed earlier stage, or block and exposes the resulting canonical stage.
  - Given advisory review feedback, no runtime state changes until the active worker submits a transition instruction.
  - Resolving a bounded request persists a selected option or response text and makes the unchanged blocked item claimable with that resolution in its role context.
  - An authorized backward move records its operator reason, invalidates later authority and the completed dependent closure of each invalidated result, and retains only results deterministically proven unaffected.
commitments: [COM-002, COM-005, COM-006, COM-007, COM-010, COM-011, COM-012]
dependencies: [OUT-002]
```

```yaml target-contract
kind: outcome
id: OUT-004
title: Typed planning and result authority
promise: Planner and Builder consume and produce compact typed authority sufficient for independent execution and recovery.
acceptance:
  - Plan publication records task identity, outcome and scope, dependencies, required outputs, maintained surfaces, constraints, acceptance observations, and proof boundaries before advance can promote it.
  - Build advance binds the task to a reviewed commit and updates the completed branch boundary; retry, return, and block preserve only successor context consumed by the next cycle.
  - Runtime persistence excludes closed reviewer prose, model identity, command transcripts, and passing reports.
commitments: [COM-002, COM-004, COM-005, COM-006, COM-010, COM-012]
dependencies: [OUT-003]
```

```yaml target-contract
kind: outcome
id: OUT-005
title: Deterministic portfolio acquisition
promise: Ready work becomes bounded launch packages under separate execution and writer capacity without Orchestrator scheduling judgment.
acceptance:
  - Acquisition selects stable dependency-ready work with no more than one active claim per change, starts the attempt before writer custody, and reserves writer capacity only for Build.
  - A Plan or Build launch package contains identity and source locators required by its role while excluding portfolio inventory, Specification prose, and prior review history.
  - Exact-claim removal recovers failed launches; a dirty or ambiguous Build workspace retains custody and exposes repair attention.
commitments: [COM-002, COM-005, COM-006, COM-010, COM-011, COM-012]
dependencies: [OUT-003, OUT-004]
```

```yaml target-contract
kind: outcome
id: OUT-006
title: Deterministic Integration and completed history
promise: A completed change enters its target with a recoverable package and no separate cleanup commit.
acceptance:
  - Integration under portfolio and package locks rejects revision-pending state, target-identity mismatch, package mutation, sibling completed-history mutation, and a branch head that differs from its reviewed boundary.
  - A product change publishes the reviewed merge tree and package snapshot in one target commit; a semantic-only revision retains the target product tree and replaces only its completed package path.
  - Replaying an already-published package identity completes matching active-package and warm-worktree cleanup without another target commit.
  - Conflict or candidate-proof failure preserves completed outcomes and publishes typed Integration attention containing unchanged heads and retry condition.
  - A bounded Integration repair can clear its attention only after independent review advances the recorded reviewed boundary to the additive repair commit, making deterministic Integration retry eligible.
commitments: [COM-003, COM-004, COM-005, COM-006, COM-010, COM-011, COM-012]
dependencies: [OUT-001, OUT-003, OUT-004, OUT-005]
```

```yaml target-contract
kind: outcome
id: OUT-007
title: MCP delivery surface
promise: MCP exposes the new deterministic operations and bounded projections without duplicating Kanban decisions.
acceptance:
  - Agent-callable MCP operations validate request schemas, delegate acquisition, context, transition, request creation, recovery, admission, Integration, and completed lookup to Kanban core, and translate domain failures into typed tool diagnostics.
  - Answer-bearing request resolution and requestless unblock remain user/Cockpit-owned operations and are absent from the agent-callable MCP registry.
  - Retired semantic-update, completion-summary, review-disposition, arbitration, process-liveness recovery, and generic returned-state tools are absent from the assembled MCP registry after cutover.
commitments: [COM-002, COM-005, COM-007, COM-010, COM-012]
dependencies: [OUT-002, OUT-003, OUT-004, OUT-005, OUT-006]
```

```yaml target-contract
kind: outcome
id: OUT-008
title: Cockpit delivery controls
promise: The user can observe and resolve actionable delivery conditions without interpreting internal execution records.
acceptance:
  - Cockpit presents current outcome stages, blocks and requests, long-idle claims, revision attention, Integration attention, and bounded completed-history lookup from the new API projections.
  - User controls can answer a request, clear a satisfied requestless block, remove a confirmed-dead claim, retry Integration, and select an invariant-checked backward move with typed failure feedback.
  - Work-item projections and views omit retired generic semantic-update and completion-summary records; typed current attention, successor context, and completed lookup remain the user-visible sources.
commitments: [COM-005, COM-006, COM-010, COM-012]
dependencies: [OUT-007]
```

```yaml target-contract
kind: outcome
id: OUT-009
title: Agent workflow cutover
promise: Designer, Orchestrator, Planner, Builder, and reviewers use the new authority and transition boundaries without compensating manual joins.
acceptance:
  - Agent and skill artifacts name only tools present in the assembled registry, omit retired semantic-update and completion-summary joins, and preserve Designer, worker, reviewer, runtime, and user authority boundaries by inspection.
  - Orchestration acquires launch packages, invokes named workers, forwards worker transitions unchanged, and invokes Integration-ready IDs without portfolio interpretation.
  - A user-invoked Integration repair prompt supplies the bounded conflict context to a capable repair worker and Build Reviewer, then records only a passing additive repair commit and reviewed-boundary advance.
  - Agent wording changes receive structural validation and focused review; no durable wording assertion is introduced unless executable loading or tool availability changes.
commitments: [COM-002, COM-004, COM-005, COM-007, COM-010, COM-012]
dependencies: [OUT-007, OUT-008]
```

```yaml target-contract
kind: outcome
id: OUT-010
title: Canonical lifecycle guidance
promise: Maintainers and operators have one current explanation of the implemented lifecycle, recovery controls, and known manual boundaries.
acceptance:
  - Canonical documentation describes the implemented Specification, Delivery, Correction, and Integration loops and links to public commands, tools, and recovery procedures that exist after cutover.
  - Frozen research remains comparison evidence rather than competing operational authority.
commitments: [COM-004, COM-005, COM-007]
dependencies: [OUT-006, OUT-007, OUT-008, OUT-009]
```
