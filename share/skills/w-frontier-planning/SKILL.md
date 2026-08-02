---
name: w-frontier-planning
description: "Workflow: Produce one independently reviewed target task-plan claim"
user-invocable: false
---

# Frontier Planning

Own one started `plan` attempt. Refine its admitted scope into tasks and proof without changing
protected authority. The planner returns exact reviewer evidence; orchestration persists it.

## Step 0 - Validate Dispatch

Require the serialized context to contain one active `plan` job and matching attempt, claim, owner,
reviewer, process, authority digest, and candidate commit. Call `show_job` and `show_attempt`; use
`show_work_item`, activity, semantic updates, and receipts to rehydrate the semantic scope. Any
stale, missing, or contradictory identity returns `PlanExecutionBlocked` before further work.

## Step 1 - Ground The Claim

Load `h-codebase-orientation`, `h-module-design`, and `h-ac-quality` when choosing current source
owners, task boundaries, dependencies, or proof. Create the smallest complete task set under the
admitted `plan_scope_id`. Each task names its outcome, admitted boundary, dependencies, required
outputs, maintained or public proof, and concrete acceptance observations.

Do not alter commitments, outcomes, task-plan scope, composition claim, solution architecture, or
design meaning. One unresolved material question may use `create_request` with exact `change_id`,
authority digest, work item, commitment, optional task, timestamp, and summary; then return blocked
until it is resolved.

## Step 2 - Build Immutable Review Context

Construct one candidate claim containing execution identity, admitted semantic scope, proposed task
set, dependency order, required outputs, proof, repository evidence, and exact candidate commit.
Dispatch only the assigned `reviewer_id` to `planner-challenger`. One invocation returns one review
mapping with matching reviewer and commit identities, a non-empty claim and evidence, and one
runtime disposition.

Do not repair before returning the decision. When orchestration later redispatches a persisted
`repair`, keep the same attempt and reviewer, correct only the reviewed plan claim, and submit the
new candidate as one distinct claim. `restart`, `task-plan`, `solution-plan`, or `design` ends local
planning immediately.

## Step 3 - Return

On a structurally complete review, return:

```yaml
kind: PlanClaimResult
job_id: <started job>
attempt_id: <started attempt>
claim_id: <started claim>
owner_id: <assigned owner>
reviewer_id: <assigned reviewer>
candidate_commit: <exact candidate commit>
plan_claim: <complete task set and proof claim>
review:
  review_id: <review identity>
  reviewer_id: <assigned reviewer>
  candidate_commit: <exact candidate commit>
  disposition: acceptable|repair|restart|task-plan|solution-plan|design
  claim: <specific reviewed claim>
  evidence: [<source-grounded observations>]
```

For invalid execution or malformed review evidence, return:

```yaml
kind: PlanExecutionBlocked
target: <execution, authority, candidate, or review>
finding: <specific fail-closed condition>
```

Do not call a finish operation, select another job, or privately repeat review.

## Known Pitfalls

- **Authority repair:** a planning return level is evidence, not permission to edit upstream meaning.
- **Self-review:** only the assigned independent reviewer closes the claim.
- **Hidden loop:** every distinct candidate returns to orchestration for immutable recording.
