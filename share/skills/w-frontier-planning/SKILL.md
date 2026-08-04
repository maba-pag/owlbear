---
name: w-frontier-planning
description: "Workflow: Publish one advisory-reviewed Delivery task chain and return its transition"
user-invocable: false
---

# Frontier Planning

Own one Planner launch selected by Delivery acquisition. Consume its bounded context, construct an
executable task chain, publish only after independent advisory pass, and return one schema-valid
transition for orchestration to forward unchanged.

## Step 0 - Validate Launch And Context

Require one serialized `DeliveryLaunchPackage` whose policy role is `planner`, whose task ID is
absent, and whose claim role and identities match the launch. Call `show_plan_context` with its
change ID, outcome ID, attempt ID, and claim ID. Require the returned `DeliveryPlanContext.launch`
to equal the supplied launch and its outcome ID, plan-scope ID, authority digest, package ID, branch,
source head, integration target, and reviewed boundary to remain unchanged.

Do not infer or repair malformed launch identity. Once the supplied identity is structurally valid,
any context conflict or local planning failure publishes nothing and returns `RetryDelivery` using
the unchanged outcome and claim identities.

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

Do not alter outcome, commitment, plan-scope, architecture, or Design meaning. A local task-chain
defect is Planner-owned. A missing or contradictory Design premise is not.

### Requests And Resumed Context

Consume a resolved `DeliveryRequest` only from `DeliveryPlanContext.requests`. Use its structured
`resolution.selected_option_id` or `resolution.response_text`; never reconstruct a response from
conversation or request summary.

When one bounded user-owned decision or action blocks planning, create no side record. Return a
`BlockDelivery` containing reason, unblock condition, expected evidence, locators, and one embedded
`DeliveryRequest` with `request_id`, `kind`, matching outcome ID, summary, bounded options for a
decision, and no resolution. Orchestration forwards that block to `transition_delivery`; Cockpit or
the user resolves it, and a later acquisition supplies fresh context.

## Step 2 - Obtain Advisory Review

Construct one candidate claim containing the unchanged launch identity, supplied plan context,
complete task definitions, dependency order, required outputs, proof, repository evidence, and exact
source head. Dispatch only `launch.policy.reviewer_agent` to `planner-challenger` using the configured
reviewer model.

Require exactly one advisory mapping with disposition `pass | finding` and non-empty evidence. The
review is scoped to the supplied immutable candidate; it never chooses a transition or calls a
Kanban tool.

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

- `retry` for a local task-chain or transient planning failure;
- `return` with target `design`, reason, source locators, and `source_boundary` equal to the supplied
  launch package ID for missing or contradictory Design authority;
- `block` with an embedded bounded request for one user-owned decision or action.

Return the selected `DeliveryTransition` directly. Do not call `transition_delivery`; orchestration
validates the returned outcome and claim identity and forwards the mapping byte-for-structure
unchanged. Do not call a job, request, or transition lifecycle operation.

## Known Pitfalls

- **Context reconstruction:** use `show_plan_context`; do not join jobs, receipts, semantic updates,
  or conversation history.
- **Reviewer action:** a finding is evidence, not a selected transition.
- **Premature publication:** only advisory pass permits `publish_delivery_plan`.
- **Detached request:** embed the request in `block`; do not create or resolve it separately.
