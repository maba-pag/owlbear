---
name: w-orchestration
description: "Workflow: Dispatch and finalize reviewed target transformations across the portfolio"
user-invocable: false
---

# Target Orchestration

Run the portfolio until no ready target transformations remain. The runtime owns readiness,
attempt state, receipts, typed correction, and recovery. Orchestration owns reviewer assignment,
cross-change capacity, exact dispatch context, and identity-preserving lifecycle calls.

## Step 1 - Discover Current Frontiers

If target tools are deferred, load them once with `tool_search` using:

`OwlBear Kanban target portfolio list_work_items list_frontier start_job finish_plan finish_build finish_assembly respond_to_review arbitrate_attempt recover_interrupted_task`

Call `list_work_items` to discover current changes, then `list_frontier(change_id)` for each change.
From the returned frontiers, dispatch stable topology/creation order while admitting at most one
writer per change and respecting the configured global limit. Do not infer readiness from agent
output or cached portfolio state.

## Step 2 - Start One Distinct Claim

For each selected job, create fresh `attempt_id`, `claim_id`, `owner_id`, `reviewer_id`, and
`process_id` values plus orchestrator-owned RFC 3339 `started_at` and `lease_expires_at`. The owner
and reviewer must differ, and a restarted job's `excluded_reviewer_ids` cannot be reused.

Call `start_job(change_id, request)` with all fields above and the selected `job_id`. Combine its
complete successful result with the change coordination supplied by the dispatch boundary:
`branch`, `worktree_path`, `integration_target`, `target_head`, and `last_reviewed_commit`. This is
the immutable dispatch context. Never substitute a familiar branch or workspace.

Dispatch `planner` for `plan`; dispatch `builder` for `build` or `assembly`. Each agent receives only
that serialized context. A build or assembly owner writes only in `worktree_path`; a planner is
hard read-only. Keep the assigned reviewer available for the attempt's review and repair rounds.

## Step 3 - Persist One Review Decision

Require the agent result to preserve the started job, attempt, claim, owner, reviewer, candidate
commit, claim text, and non-empty evidence. Call the finish operation matching the job kind:

- `finish_plan(change_id, request)` for `plan`;
- `finish_build(change_id, request)` for `build`;
- `finish_assembly(change_id, request)` for `assembly`.

The request contains `job_id`, `attempt_id`, `claim_id`, `owner_id`, `reviewer_id`, `review_id`,
`candidate_commit`, `reviewed_at`, `disposition`, `claim`, `evidence`, and a fresh `receipt_id` only
for `acceptable`. Forward owner/reviewer evidence unchanged; never reconstruct it.

Disposition handling is finite:

| Disposition | Runtime result | Next action |
|-------------|----------------|-------------|
| `acceptable` | Receipt closes the job | Query fresh frontiers |
| `repair` | Same attempt awaits correction | Redispatch same owner, reviewer, claim, and worktree with persisted review evidence |
| `restart` | Attempt closes; job becomes pending | Preserve rejected head; restart from last reviewed commit with a fresh reviewer |
| `task-plan` | Job returns to task planning | Query fresh authority/frontiers |
| `solution-plan` | Job returns to solution planning | Query fresh authority/frontiers |
| `design` | Protected meaning needs collaboration | Stop affected work and report its design re-entry briefing |

Every materially changed candidate is a distinct claim and receives exactly one review decision.
Repair is not permission for an informal review loop.

## Step 4 - Resolve One Disagreement

When an owner disputes a persisted `repair`, allow exactly one evidence response. Call
`respond_to_review(change_id, request)` with the unchanged `job_id`, `attempt_id`, `claim_id`, and
`owner_id`, plus a fresh `response_id`, `responded_at`, and non-empty `evidence`.

Then dispatch `claim-arbiter` with the immutable claim, review, and response. The arbiter must differ
from owner and reviewer. Call `arbitrate_attempt(change_id, request)` with fresh `arbiter_id` and
`decision_id`, `decided_at`, one terminal disposition (`acceptable`, `restart`, `task-plan`,
`solution-plan`, or `design`), rationale, and a fresh `receipt_id` only for `acceptable`. Arbitration
is final for the attempt. A second response, review negotiation, or arbitration is forbidden.

## Step 5 - Recover A Dead Owner

Use `recover_interrupted_task` only when the recorded process is known dead. Pass unchanged
`job_id`, `attempt_id`, `claim_id`, and `process_id` plus `recovered_at`. Never use recovery to
preempt a live owner, rebalance capacity, or abandon an inconvenient review.

## Step 6 - Continue

After every transition, discard cached frontier state and query again. Continue independent changes
when another change returns earlier. Stop only when current frontiers are empty, a collaboration
boundary requires the user, or a fail-closed diagnostic prevents safe progress.

## Output

Report completed receipt identities, returned work items and levels, active blockers, and cycle
count. Do not report a claim as complete without its runtime receipt.

## Known Pitfalls

- **Stale dispatch:** every transition requires fresh frontiers.
- **Reviewer substitution:** repair retains the assigned reviewer; restart excludes it.
- **Workspace assumption:** dispatch uses recorded coordination, never a hard-coded target.
- **Owner impersonation:** there is no owner-style claim release.
- **Open review:** one review, one optional evidence response, and one final arbitration is the limit.
