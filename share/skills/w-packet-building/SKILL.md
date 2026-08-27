---
name: w-packet-building
description: "Workflow: Implement one acquired Delivery task and publish its reviewed exact-commit result"
user-invocable: false
---

# Packet Building

Own one mechanically acquired Builder launch in its assigned change worktree. Implement the supplied
task, obtain independent exact-commit evidence, publish only a passing compact result, and return one
worker-owned transition for orchestration to forward unchanged.

## Step 0 - Validate Launch, Context, And Custody

Require one serialized `DeliveryLaunchPackage` whose policy and claim roles are `builder`, whose
task IDs match, and whose writer identity matches the claim attempt, claim, owner, and process. Call
`show_build_context` with the launch change, outcome, attempt, and claim IDs. Require the returned
`DeliveryBuildContext.launch` to equal the supplied launch and the context task to match its task,
outcome, and plan-scope identities.

Before edits, enter only `launch.worktree_path` and require:

- its current branch equals `launch.branch`;
- `HEAD` equals `launch.source_head` and descends from `launch.last_reviewed_commit`;
- writer custody still matches the active claim;
- the worktree state has been triaged under the rules below; the final candidate must leave the entire
  managed worktree clean;
- any predecessor results, resolved requests, return context, and recovery attention come only from
  this fresh Build context.

Do not infer malformed identity or edit under recovery attention. A structurally valid claim that
cannot establish fresh Build context or custody returns this non-transition result to Orchestrator
for fail-closed claim recovery; it does not fabricate a lifecycle decision or mutate a checkout:

```yaml
kind: dispatch_failure
change_id: <launch change ID>
outcome_id: <launch outcome ID>
attempt_id: <launch attempt ID>
claim_id: <launch claim ID>
failed_operation: show_build_context
reason: <recorded prerequisite failure>
```

### Triage An Unclean Worktree

Inspect the assigned worktree before editing with `git status --short`, `git diff`,
`git diff --cached`, and `git ls-files --others --exclude-standard`. Compare every changed path and
hunk with `DeliveryBuildContext.task.maintained_surfaces`, constraints, exclusions, and the exact
launch identity.

- **Reuse:** When every change is compatible with this exact task, keep it, validate it, and include
  it in the eventual explicit scoped commit. Do not infer ownership from file timestamps or from the
  fact that another session ended.
- **Preserve for handoff:** When changes are useful but incomplete for this invocation, preserve them
  with a task-scoped WIP commit using explicit owned paths, then return `retry` with that exact clean
  commit as `abandoned_commit`. The WIP commit is recoverable predecessor evidence; it is not a
  successful task result and does not release the claim by itself.
- **Reset:** When changes are clearly disposable artifacts from this exact task and every tracked or
  untracked path is within the task boundary, the Builder may discard them. Prefer a reversible
  `git stash push -u -m <claim-id> -- <explicit paths>` before removal. For disposable untracked
  artifacts, preview removal with `git clean -nd -- <explicit paths>`, then remove only the reviewed
  paths with `git clean -f -- <explicit paths>`. Never use broad `git clean -fd`, reset another branch,
  or remove paths outside the task boundary.
- **Escalate:** If any path is foreign or ambiguous, staged state exists outside the task boundary,
  branch/HEAD/custody is not exact, recovery attention is present, or the current HEAD contains an
  unreviewed commit whose provenance is unclear, do not reset or adopt it. Return the claim-bound
  `dispatch_failure` above for exact recovery.

Before returning `retry`, `return`, or `block`, the Builder must leave the managed worktree clean and
make any required commit identity equal the current exact HEAD. A dirty worktree cannot produce one of
those transitions: resolve it through reuse, a WIP handoff, or an explicit scoped reset first. Use
`dispatch_failure` only when that triage cannot be completed safely, not as a substitute for ordinary
task failure handling.

This authority covers working-tree artifacts. A committed predecessor head is immutable evidence: the
Builder may inspect and reuse a compatible exact-task commit, but does not silently erase committed
history. A Git commit also does not release the Delivery claim or writer custody; the normal published
result and transition still close the work.

## Step 1 - Fix The Task Boundary

Treat `DeliveryBuildContext.task` as executable authority. Its result, commitment IDs, dependency
IDs, required outputs, maintained surfaces, constraints, exclusions, acceptance observations, and
proof boundaries bound the implementation. Predecessor results prove only their exact task digests
and commits. Resolved requests constrain work through structured resolution fields; conversation is
not authority.

Do not edit Design, task definitions, Delivery runtime, package internals, coordination records, or
unlisted surfaces. A missing task premise belongs to Planning or Design, not local implementation.
Builder may choose internal implementation details only when their alternatives are not observable
at the supplied task boundary.

If context contains a request or a request may be needed, load `h-decision-requests` before consuming
or constructing it. Choose among authority-equivalent implementation alternatives; use a request
for an expressly stakeholder-selectable choice or external action; use `return` for missing,
contradictory, or observably ambiguous earlier authority; use `retry` for local failure and
`dispatch_failure` for context, custody, or tool failure.

## Step 2 - Implement And Commit

Make the minimum complete change inside the admitted boundary. Run enough pre-commit proof to shape
the implementation, then load `r-workspace-governance` and create one scoped commit from explicit
owned paths. Require a clean owned state and exact candidate commit. Never rebase, squash,
cherry-pick, amend a reviewed commit, or create a per-task worktree.

When the task changes an input that determines a tracked generated output, regenerate that output
before the scoped commit and include it in the same `commit-owned` path set. Do this conditionally
from the task's `required_outputs` and `maintained_surfaces`; do not regenerate unrelated outputs for
every task. For Python workspace resolution changes, run `uv lock` before the commit and `uv lock
--check` against the exact candidate afterward. Use locked or otherwise non-mutating proof commands
after generation so post-commit checks cannot silently rewrite the candidate.

Rerun every Task-required observation against that exact candidate commit; pre-commit proof does
not bind a commit and cannot support publication. For each passing observation, construct
`DeliveryObservationReceipt.create(DeliveryObservation(...))` with the launch change ID, context
task ID, candidate commit, observation kind, exact command or procedure, exit status or artifact
locator, runner identity, and timezone-aware observation time. Serialize the returned receipt with
`model_dump(mode="json")`; never calculate, copy, or invent `observation_id`. Any post-commit change
invalidates the receipts and requires a successor commit plus fresh proof.

For a local review finding, retain the same launch, worktree, and configured reviewer. Preserve the
rejected commit, create a bounded repair commit, rerun affected proof, and supply prior evidence to
fresh review. Never amend or erase a reviewed head.

## Step 3 - Obtain Advisory Exact-Commit Review

Dispatch only `launch.policy.reviewer_agent` to `build-reviewer`; the reviewer agent's frontmatter
owns its model.
Supply the unchanged launch identity, full Build context, source and exact candidate commits, changed
paths, focused proof, custody, ancestry, and prior evidence. The reviewer must independently resolve
the candidate and inspect its complete diff with read-only Git; a caller summary or mutable worktree
read does not satisfy exact-commit evidence. Require the reviewer to echo the exact commit and return
disposition `pass | finding`, matching `finding_boundary`, and non-empty evidence.

On `pass`, construct `DeliveryReviewReceipt.create(DeliveryReview(...))` with the echoed candidate
commit, `launch.claim.owner_id` as author, `launch.policy.reviewer_agent` as reviewer, the returned
review evidence unchanged, and a timezone-aware review time. Serialize the returned receipt with
`model_dump(mode="json")`; never calculate, copy, or invent `review_id`. Reject a pass that echoes a
different commit, lacks evidence, or cannot produce an independent canonical receipt.

### Triage Review Findings Before Repair

Treat a review finding as input to a Builder decision, not as an automatic work order. Before
touching the reviewed head, classify the concrete finding against the admitted task:

| Finding classification | Builder action |
| --- | --- |
| Fix now: implementation defect inside the task boundary | Repair one finding at a time, preserve the rejected commit, rerun affected proof, and obtain fresh exact-commit review. |
| Return to authority: missing, contradictory, or observably ambiguous Planning or Design | Publish nothing and return with the owning locator, clean preserved commit, and the required source boundary. |
| Block for user-owned input: one bounded decision, action, or manual validation is required | Publish nothing and use `BlockDelivery` with a bounded request and clean resume commit. |
| No repair: style preference or unsupported concern without a concrete defect | Do not expand the task or silently alter code; the review evidence does not satisfy the challenger contract until it names a concrete boundary and evidence. |

Only the first classification creates a repair commit. A deferred or out-of-scope concern is routed
through the native return or block path when its resolution is required; it is not logged as a second
Builder backlog or converted into an unrelated change.

Repair an `implementation` finding when it remains inside the task and obtain fresh review of the new
commit. A `planning` or `design` finding is evidence for Builder's return choice, not a reviewer-owned
transition. Invalid review evidence publishes nothing.

## Step 4 - Publish Pass Or Route Finding

On `pass`, construct one `DeliveryTaskResult` with a stable result ID, launch change and authority
digest, exact task ID, `DeliveryBuildContext.task_digest`, reviewed commit, the non-empty tuple of
canonical observation receipts, and the canonical review receipt. Require every receipt to bind the
same Change, Task, and exact commit represented by the result. Require the context digest to be
present and use it unchanged; never reconstruct `DeliveryTaskDefinition` from MCP JSON or
reimplement task or receipt hashing. Call `publish_delivery_result` with the unchanged change ID and
a `PublishDeliveryResult` containing the outcome ID, claim ID, and result.

Require the returned `DeliveryResultCandidate` to preserve the claim and exact result. Return its
output directly in `AdvanceDelivery`:

```yaml
action: advance
outcome_id: <context outcome ID>
claim_id: <launch claim ID>
output: <published DeliveryResultCandidate.output unchanged>
```

On a finding or safe local failure, publish nothing. Builder chooses one schema-valid transition:

```yaml
action: retry
outcome_id: <context outcome ID>
claim_id: <launch claim ID>
attempt_id: <launch attempt ID>
abandoned_commit: <exact clean current head>
```

Use `retry` for an implementation failure that cannot be repaired in this invocation.

`retry` abandons the current attempt and resets the managed worktree to the reviewed boundary through
Delivery. It is valid only after the Builder has supplied a clean exact `abandoned_commit`; it does not
preserve uncommitted work. Preserve useful incomplete work with the WIP handoff in Step 0 before
returning `retry`.

```yaml
action: return
outcome_id: <context outcome ID>
claim_id: <launch claim ID>
target: planning | design
reason: <missing or contradictory earlier authority>
locators: [<owning authority locator>]
attempt_id: <launch attempt ID>
preserved_commit: <exact clean current head>
```

Use `return` only for a Planning or Design authority defect.

```yaml
action: block
outcome_id: <context outcome ID>
claim_id: <launch claim ID>
block_id: <stable block identity>
reason: <user-owned blocker>
unblock_condition: <observable resolution>
expected_evidence: [<required evidence>]
locators: [<relevant authority locator>]
resume_commit: <exact clean current head>
request:
  request_id: <stable request identity>
  kind: decision | action
  outcome_id: <context outcome ID>
  summary: <one bounded user request>
  options: [{option_id: <stable option identity>, label: <bounded choice label>}]
```

Use `block` only when user-owned input is required. Never substitute `unblock_evidence` for the
required `unblock_condition` and `expected_evidence` fields. Every Build block includes one bounded
`request`; a missing tool, unavailable context, custody mismatch, or other pre-execution failure is
`dispatch_failure`, not `block`.

Return the selected `DeliveryTransition` or pre-execution `dispatch_failure` directly. Do not call
`transition_delivery` or `recover_claim`; orchestration validates the launch identity and applies the
matching route. Do not call job, receipt, request, or other lifecycle operations.

## Optional Process Observation

When a reviewed result exposes a trigger from `h-process-observations`, load that handbook for a
sidecar note. Keep the note outside `DeliveryTaskResult`, receipts, and the returned transition; it
captures process learning only and cannot change the worker-owned lifecycle result. Do not create a
note for an ordinary successful task with no material process signal.

## Known Pitfalls

- **Context reconstruction:** use `show_build_context`; do not join jobs, activity, semantic updates,
  receipts, or conversation history.
- **Wrong checkout:** all writes belong in the launch's assigned change worktree.
- **History rewrite:** reviewed and rejected commits are immutable evidence.
- **Pre-commit proof:** rerun required observations after commit so every receipt binds the candidate.
- **Reviewer action:** findings name an owning boundary; Builder selects the transition.
- **Premature publication:** only exact-commit advisory pass permits `publish_delivery_result`.
