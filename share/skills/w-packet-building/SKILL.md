---
name: w-packet-building
description: "Workflow: Implement one acquired Delivery task and publish its reviewed exact-commit result"
user-invocable: false
---

# Packet Building

Own one mechanically acquired Builder launch in its assigned change worktree. Implement the supplied
task, obtain independent exact-commit evidence, publish only a passing compact result, and return one
worker-owned transition unchanged for Orchestrator to settle or forward through the native Delivery
route.

## Step 0 - Validate Launch, Context, And Custody

A normal Builder settlement preserves the managed worktree. An `ended-without-result` settlement
does too. `worker-host-lost` and `worker-released-stuck` settlements do too; after any settled
predecessor, the next same-task Builder must triage its work before edits. Use fresh
`builder_handoff_context`, Build context, and its `prior_attempts` projection, including when the
predecessor crashed or its chat was stopped without returning a transition. An unsettled dispatch or
owned mutator that may still run remains contained and does not permit a replacement claim.

Require one serialized `DeliveryLaunchPackage` whose policy and claim roles are `builder`, whose
task IDs match, and whose writer identity matches the claim attempt, claim, owner, and process. Call
`show_build_context` with the launch change, outcome, attempt, and claim IDs. Require the returned
`DeliveryBuildContext.launch` to equal the supplied launch and the context task to match its task,
outcome, and plan-scope identities.

For this custody read, inspect the actual callable tool definitions before declaring a capability
failure. Use a directly bound `show_build_context` as granted even if a separate discovery inventory
also lists its name as deferred. If no direct binding exists, load it through callable tool search;
if neither route exists, return `dispatch_failure`. A name in prose alone is never a callable binding.

Before edits, enter only `launch.worktree_path` and require:

- its current branch equals `launch.branch`;
- `HEAD` equals `launch.source_head` and descends from `launch.last_reviewed_commit`;
- writer custody still matches the active claim;
- the worktree state has been triaged under the rules below; the final candidate must leave the entire
  managed worktree clean;
- any predecessor results, prior attempts, resolved requests, return context, and recovery attention
  come only from this fresh Build context.

The branch, `HEAD`, ancestry, writer custody, and worktree-cleanliness observations must come from the
Builder's own direct tool calls in the assigned worktree. A delegated execution report or caller prose
summary is not admissible identity or custody evidence; if a required observation is delegated or
unavailable, return `dispatch_failure` instead of inferring the result. Delegated execution remains
available for ordinary read-only proof after custody is established.

Do not infer malformed identity or edit under recovery attention. A structurally valid claim that
cannot establish fresh Build context or custody returns this non-transition result to Orchestrator,
not a fabricated lifecycle decision or a local checkout mutation. Orchestrator settles a returned
`dispatch_failure` as `ended-without-result` only after the dispatch call returned and its owned
mutating work is settled; otherwise custody remains contained:

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

A same-task Builder claim may start with dirty, staged, or committed predecessor work, including
work left by a `dispatch_failure`, a crash, or a settled `worker-host-lost` or
`worker-released-stuck` attempt. Each settled no-result receipt preserves that material and records
the failed attempt; fresh Build context supplies `prior_attempts`. The new Builder must inspect and
triage this state under the rules below before editing. Orchestrator does not clean the worktree or
ask the user to do Git recovery. A dispatch that has not returned or whose owned mutator may still
run remains contained and does not authorize this handoff.

Inspect the assigned worktree before editing with `git status --short`, `git diff`,
`git diff --cached`, and `git ls-files --others --exclude-standard`. Compare every changed path and
hunk with `DeliveryBuildContext.task.maintained_surfaces`, constraints, exclusions, and the exact
launch identity.

- **Reuse:** When every change is compatible with this exact task, keep it, validate it, and include
  it in the eventual explicit scoped commit. Do not infer ownership from file timestamps or from the
  fact that another session ended.
- **Preserve for handoff:** Keep useful incomplete changes for the same task's next claim. A
  task-scoped WIP commit with explicit owned paths is optional when it improves predecessor clarity;
  it is not a successful task result and does not release the claim by itself.
- **Reset:** When changes are clearly disposable artifacts from this exact task and every tracked or
  untracked path is within the task boundary, the Builder may discard them. Prefer a reversible
  `git stash push -u -m <claim-id> -- <explicit paths>` before removal. For disposable untracked
  artifacts, preview removal with `git clean -nd -- <explicit paths>`, then remove only the reviewed
  paths with `git clean -f -- <explicit paths>`. Never use broad `git clean -fd`, reset another branch,
  or remove paths outside the task boundary.
- **Preserve and retry:** If paths are foreign or ambiguous, staged state exists outside the task
  boundary, or an unreviewed commit's provenance is unclear, do not reset or adopt that material.
  When the current branch, HEAD and writer custody are independently established, preserve all
  bytes and return an exact `RetryDelivery` with `failure_code: unsafe-worktree`. Orchestrator
  settles the normally ended attempt under the same bounded budget; repeated failure becomes
  agent-owned attention, not permission to discard the material.
  Keep foreign, private, or ambiguous material intact; name affected paths and attribution gaps
  without exposing private contents.
- **Unknown custody:** If current branch, HEAD, or writer custody cannot be established, or fresh
  context shows the predecessor may still be active, do not edit, adopt, or discard. Return the
  claim-bound `dispatch_failure` above; Orchestrator settles the returned attempt only after the call
  returned and owned work settled. An unreturned dispatch or live job remains contained. A settled
  `ended-without-result` receipt permits this same-task claim to triage, not automatic adoption.

Before returning `retry`, `return`, or `block`, bind any required commit field to the exact current
branch HEAD and preserve the launch attempt identity. A successful implementation result still
requires a clean owned state and exact candidate commit. A normally returned local tool or context
failure may use a counted retry only while current branch, HEAD and writer custody are established.
Uncertain identity or an unavailable global host remains `dispatch_failure`. Before any ordinary
return, finish or stop and join owned mutating terminals and asynchronous jobs; do not leave a
background writer beside the successor. If that completion cannot be established, report unknown
execution rather than a settled retry.

This authority covers working-tree artifacts. A committed predecessor head is immutable evidence: the
Builder may inspect and reuse a compatible exact-task commit, but does not silently erase committed
history. A Git commit alone does not release the Delivery claim or writer custody; the normal
published result or a supported settlement closes the worker invocation.

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
contradictory, or observably ambiguous earlier authority; use `retry` for a local implementation
failure that cannot be repaired in this invocation, and `dispatch_failure` for context, custody, or
tool failure.

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
| Return to authority: missing, contradictory, or observably ambiguous Planning or Design | Publish nothing and return with the owning locator, exact current branch HEAD, and required source boundary; do not clean or reset the worktree before normal settlement. |
| Block for user-owned input: one bounded decision, action, or manual validation is required | Publish nothing and use `BlockDelivery` with a bounded request and the exact current branch HEAD. |
| No repair: style preference, unsupported concern, or a trigger outside the operating context in `intent.md` | Do not expand the task or silently alter code; record the reason and dispute the finding under `r-challenger-protocol` when it blocks publication. A real defect whose proposed fix is oversized stays a finding: choose the smallest effective repair or authority route. |

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
reimplement task or receipt hashing. Call `submit_result` with the unchanged Change, Outcome, claim,
and exact result. Require the returned `kind: submitted` result to preserve those identities and the
exact result ID. Return that applied result directly; Orchestrator must not forward it to
`transition_delivery` a second time.

On a finding or safe local failure, publish nothing. Builder chooses one schema-valid transition:

```yaml
action: retry
outcome_id: <context outcome ID>
claim_id: <launch claim ID>
attempt_id: <launch attempt ID>
abandoned_commit: <exact current branch HEAD>
```

Use `retry` for an implementation failure that cannot be repaired in this invocation.

```yaml
action: return
outcome_id: <context outcome ID>
claim_id: <launch claim ID>
target: planning | design
reason: <missing or contradictory earlier authority>
locators: [<owning authority locator>]
attempt_id: <launch attempt ID>
preserved_commit: <exact current branch HEAD>
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
resume_commit: <exact current branch HEAD>
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

For a normal Builder return, Orchestrator uses `settle_worker_invocation` for `retry`, `block`, or
`return` to Planning or Design; it validates exact workspace custody and persists any bounded request
or return context. A Design return creates only a passive handoff and human-owned `/design` attention;
it does not approve or admit a revision. Do not use a raw `transition_delivery` fallback.

On a passing Build result, call `submit_result` with the unchanged `change_id`, `outcome_id`,
`claim_id`, and exact `DeliveryTaskResult`. Require the returned `kind: submitted` result to preserve
those identities and the exact `result_id`; return that result directly. The operation publishes and
promotes the result, so do not also construct or return an `advance` transition. On a finding or safe
local failure, return the selected `DeliveryTransition` (`retry`, `return`, or `block`) unchanged.
Orchestrator routes the result under `w-orchestration`. Builder does not call `transition_delivery`,
`settle_worker_invocation`, or `recover_claim`; it does not call job, receipt, request, or other
lifecycle operations.

## Memory assessment policy

The sampled assessment policy is authoritative in `h-mcp-memory`. This workflow
intentionally does not schedule or require a post-task assessment, make missing
feedback a transition failure, or add a retry/receipt path. If Builder elects
to assess recalled entries, it does so at the terminal boundary of the
substantive attempt, including eligible partial or failed attempts; a
pre-execution `dispatch_failure` is not an assessment boundary.

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
- **Premature publication:** only exact-commit advisory pass permits `submit_result`.
