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

### Requests And Resumed Context

If context contains a request or a request may be needed, load `h-decision-requests` before consuming
or constructing it.

Consume a resolved `DeliveryRequest` only from `DeliveryPlanContext.requests`. Use its structured
`resolution.selected_option_id` or `resolution.response_text`; never reconstruct a response from
conversation or request summary.

Before routing a blocker: choose among authority-equivalent planning alternatives; use a request for
an expressly stakeholder-selectable choice or external action; use `return` for missing,
contradictory, or observably ambiguous Design authority; use `retry` for local or transient failure.

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

- `retry` only for a local task-chain or explicitly transient planning failure. A required reviewer-dispatch failure that is not transient is not a retry;
- `return` with target `design`, reason, source locators, and `source_boundary` equal to the supplied
  launch package ID for missing or contradictory Design authority;
- `block` with an embedded bounded request for one user-owned decision or action. When the required
  reviewer cannot be dispatched, use an `action` request naming the reviewer capability, unblock
  condition, expected evidence, and source locators.

Return the selected `DeliveryTransition` directly. Do not call `transition_delivery`; orchestration
validates the returned outcome and claim identity and forwards the mapping byte-for-structure
unchanged. Do not call a job, request, or transition lifecycle operation.

## Known Pitfalls

- **Context reconstruction:** use `show_plan_context`; do not join jobs, receipts, semantic updates,
  or conversation history.
- **Reviewer action:** a finding is evidence, not a selected transition.
- **Premature publication:** only advisory pass permits `publish_delivery_plan`.
- **Detached request:** embed the request in `block`; do not create or resolve it separately.
