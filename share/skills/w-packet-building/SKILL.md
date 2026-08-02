---
name: w-packet-building
description: "Workflow: Implement and independently review one target build or assembly claim"
user-invocable: false
---

# Target Building

Own one started `build` or `assembly` attempt in its assigned per-change worktree. Produce one exact
candidate commit and independent review. Orchestration persists the decision and owns correction
routing.

## Step 0 - Validate Dispatch And Workspace

Require one active target job with matching attempt, claim, owner, reviewer, process, authority
digest, candidate commit, and change coordination. Call `show_job`, `show_attempt`, `show_work_item`,
and relevant receipts. In the supplied `worktree_path`, verify the checked-out branch and HEAD equal
the coordination `branch` and expected reviewed boundary. Use the recorded `integration_target`;
never assume a branch name or write in the caller's checkout.

Return `BuildExecutionBlocked` before edits for stale identity, ambiguous custody, dirty owned paths,
or mismatched coordination.

## Step 1 - Fix The Claim Boundary

For `build`, rehydrate the accepted task under `plan_scope_id`: outcome, admitted paths and
interfaces, required outputs, exclusions, dependencies, acceptance observations, and proof.

For `assembly`, rehydrate the declared `composition_claim`, reviewed task receipts, exact task
commits, merge ancestry, and change-level proof. Assembly may integrate only with merge commits;
task SHAs remain unchanged ancestors. A conflict or interaction returns `solution-plan` through
review instead of local history rewriting.

Do not edit plan authority, solution authority, design authority, jobs, receipts, requests, or
coordination records.

## Step 2 - Implement And Commit

Make the minimum complete change inside the admitted boundary. Run focused proof, record commands
or observations and relevant results, then load `r-workspace-governance` and create one scoped
commit from explicit owned paths. Require a clean owned state and exact candidate commit. Never
rebase, squash, cherry-pick, amend a reviewed commit, or create a per-task worktree.

On a repair redispatch, retain the same worktree, branch, attempt, and reviewer. Preserve the
rejected commit, create a new bounded repair commit on the change branch, rerun affected proof, and
include the persisted review and resolution in the next review context.

## Step 3 - Review One Distinct Claim

Dispatch only the assigned `reviewer_id` to `build-reviewer` with execution identity, admitted
claim, complete diff, changed paths, exact candidate commit, proof, custody, ancestry, and prior
review evidence. Require matching reviewer and commit identities, a non-empty claim and evidence,
and one runtime disposition.

Return that decision immediately. `repair` can remain in the same attempt; `restart`, `task-plan`,
`solution-plan`, and `design` end local work. Do not create replacement jobs or revise authority.

## Step 4 - Return

On a structurally complete review, return:

```yaml
kind: BuildClaimResult
job_id: <started job>
attempt_id: <started attempt>
claim_id: <started claim>
owner_id: <assigned owner>
reviewer_id: <assigned reviewer>
candidate_commit: <exact reviewed commit>
review:
  review_id: <review identity>
  reviewer_id: <assigned reviewer>
  candidate_commit: <exact reviewed commit>
  disposition: acceptable|repair|restart|task-plan|solution-plan|design
  claim: <specific implementation or composition claim>
  evidence: [<proof and source-grounded observations>]
```

For invalid execution, workspace, commit, or review evidence, return:

```yaml
kind: BuildExecutionBlocked
target: <execution, authority, workspace, candidate, or review>
finding: <specific fail-closed condition>
```

Do not call a finish operation, select another job, or privately repeat review.

## Known Pitfalls

- **Wrong checkout:** all writes belong in the assigned change worktree.
- **History rewrite:** reviewed and rejected commits are immutable evidence.
- **Reviewer churn:** repair retains the same reviewer; restart receives a fresh one.
- **Scope repair:** upstream contradictions return to the selected earlier authority level.
