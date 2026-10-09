---
name: w-frontier-planning
description: "Workflow: Publish one advisory-reviewed Delivery task chain and return its transition"
user-invocable: false
---

# Frontier Planning

Own one Planner launch selected by Delivery acquisition. Consume its bounded context, construct an
executable task chain, publish only after independent advisory pass, and return one schema-valid
transition unchanged for Orchestrator to route through the native Delivery operation.

## Step 0 - Validate Launch And Context

Require one launch reference whose `worker_role` is `planner`, whose `task_id` is null, and whose
`change_id`, `outcome_id`, `attempt_id`, and `claim_id` are present. Call `show_plan_context` with
exactly those IDs; never search for or substitute another claim when it refuses. Use the returned
`DeliveryPlanContext.launch` as the launch for every later step. Require its change, outcome,
attempt, claim, and role identities to equal the reference, its task ID to be absent, and its
outcome ID, plan-scope ID, authority digest, package ID, branch, source head, integration target,
and reviewed boundary to remain unchanged.

Do not infer or repair malformed launch identity. Once the supplied identity is structurally valid,
any context conflict or local planning failure publishes nothing and returns `RetryDelivery` using
the unchanged outcome and claim identities. A normal Planner return with this retry is settled by
Orchestrator through `settle_worker_invocation` using the exact launch identity; Planner returns the
`RetryDelivery` unchanged and never calls the settlement operation itself. Settlement records the
completed attempt without publishing a plan; fresh acquisition owns any later attempt.
Delivery-settled `worker-host-lost` and `worker-released-stuck` predecessors count like other failed
Planner attempts in the same three-attempt episode; only fresh acquisition grants a retry.

## Step 1 - Ground The Task Chain

Load `h-codebase-orientation`, `h-module-design`, and `h-ac-quality` when choosing current source
owners, task boundaries, dependencies, or proof. Use only the context's outcome, commitments,
resolved requests, and return context plus current source. Create the smallest complete ordered task
chain under the context's outcome and plan-scope IDs.

Each `DeliveryTaskDefinition` supplies `task_id`, `outcome_id`, `plan_scope_id`, `title`, `result`,
`commitment_ids`, `dependency_ids`, `required_outputs`, `maintained_surfaces`, `constraints`,
`exclusions`, `acceptance_observations`, and `proof_boundaries`. Dependencies form an acyclic chain
inside the outcome, references stay within supplied authority, and proof names observable maintained
or public boundaries.

`DeliveryPlanContext.acceptance` lists the outcome's criteria by `acceptance_id` (`AC-NNN`, or
`OUT-NNN.NN` in a legacy contract). Cover every criterion: at least one task's
`acceptance_observations` entry cites its ID and the observable that proves it, for example
`AC-002: the CLI exits 2 on an unknown flag`. For a criterion only a person can check, name that
procedure so the Builder can ask the user to confirm it. Bind such evidence by acceptance ID and
exact procedure, which the Builder matches against an answered request's `applies_to`; never name a
request ID in a task, since only the Builder's own pause creates and cites it.

When a task must start from a target-branch commit the Change does not yet contain, name the full
commit in a constraint. The Builder then returns a target-sync block and Delivery merges the target;
never plan a user request or user action to synchronize the target.

Repeat every `DeliveryPlanContext.retained_tasks` entry verbatim (completed work), then plan only the
delta for criteria whose `coverage` status is not `covered` or `waived`, publishing the retained
tasks alone when none remain.

Keep tracked generated outputs with the task that changes the inputs that determine them when the
output is required for a runnable environment or repository validity. For a Python workspace,
adding or removing a `serve/*` member or changing dependency-resolution inputs owns the resulting
`uv.lock` in that same task's `maintained_surfaces` and `required_outputs`; metadata-only project
changes do not require a lockfile diff. Make freshness an exact-candidate acceptance observation
such as `uv lock --check`, rather than requiring every project-file edit to change the lock bytes.

Do not alter outcome, commitment, plan-scope, architecture, or Design meaning. A local task-chain
defect is Planner-owned. A missing or contradictory Design premise is not.

Planner may choose decomposition, order, dependencies, maintained surfaces, and proof only while
preserving the supplied Design meaning and observable outcome authority.

`DeliveryPlanContext.decisions` lists the decisions behind the outcome's commitments with their
origin. Never change one. When a decision, or an answered request, no longer serves the outcome,
`return` to Design with its identity in the locators; the Designer asks the user or supersedes it.

### Requests And Resumed Context

If context contains a request or a request may be needed, load `h-decision-requests` before consuming
or constructing it.

Consume a resolved `DeliveryRequest` only from `DeliveryPlanContext.requests`. Use its structured
`resolution.selected_option_id` or `resolution.response_text`; never reconstruct a response from
conversation or request summary.

Before routing a blocker: choose among authority-equivalent planning alternatives; use a request for
an expressly stakeholder-selectable choice or external action; use `return` for missing,
contradictory, or observably ambiguous Design authority; a local or transient failure returns the
schema-valid `retry` mapping, which Orchestrator settles as described above.

When one bounded request blocks planning, create no side record. Return a
`BlockDelivery` containing reason, unblock condition, expected evidence, locators, and one embedded
`DeliveryRequest` with `request_id`, `kind`, matching outcome ID, summary, bounded options for a
decision, and no resolution. Orchestration forwards that block to `transition_delivery`; Cockpit or
the user resolves it, and a later acquisition supplies fresh context.

## Step 2 - Obtain Advisory Review

Construct one candidate claim containing the unchanged launch identity, supplied plan context,
complete task definitions, dependency order, required outputs, proof, repository evidence, and exact
source head. Dispatch only `launch.policy.reviewer_agent` to `planner-challenger`; the reviewer
agent's frontmatter owns its model.

Require exactly one advisory mapping with disposition `pass | finding` and non-empty evidence. The
review is scoped to the supplied immutable candidate; it never chooses a transition or calls a
Delivery tool.

Repair a bounded local task-chain finding and obtain fresh review for that distinct candidate. A
Design-authority finding, user-owned blocker, invalid review mapping, or local defect that cannot be
repaired in this invocation ends review and routes through one worker-owned transition.

## Step 3 - Publish Pass Or Route Finding

On `pass`, call `publish_delivery_plan` with the unchanged change ID and a `PublishDeliveryPlan`
containing the context outcome ID, claim ID, and reviewed task definitions. Require the returned
`DeliveryPlanCandidate.claim_id` and task chain to match. Return its output directly in
`AdvanceDelivery`:

```yaml
action: advance
outcome_id: <context outcome ID>
claim_id: <launch claim ID>
output: <published DeliveryPlanCandidate.output unchanged>
```

On `finding`, publish nothing. Planner chooses one transition:

- `retry` only for a local task-chain or explicitly transient planning failure. Orchestrator settles
  a normal-return retry through `settle_worker_invocation`; fresh acquisition owns any later attempt.
  A required reviewer-dispatch failure that is not transient is not a retry;
- `return` with target `design`, reason, source locators, and `source_boundary` equal to the supplied
  launch package ID for missing or contradictory Design authority;
- `block` with an embedded bounded request for one user-owned decision or action. When the required
  reviewer cannot be dispatched, use an `action` request naming the reviewer capability, unblock
  condition, expected evidence, and source locators.

Return the selected `DeliveryTransition` directly; Planner does not call `transition_delivery` or
`settle_worker_invocation`. Orchestrator settles a normal-return `retry` through
`settle_worker_invocation` and forwards other supported transitions through `transition_delivery`,
preserving the worker mapping unchanged. Do not call a job, request, or transition lifecycle
operation.

## Known Pitfalls

- **Context reconstruction:** use `show_plan_context`; do not join jobs, receipts, semantic updates,
  or conversation history.
- **Reviewer action:** a finding is evidence, not a selected transition.
- **Premature publication:** only advisory pass permits `publish_delivery_plan`.
- **Detached request:** embed the request in `block`; do not create or resolve it separately.
