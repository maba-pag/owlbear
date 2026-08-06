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
- the task-owned paths are clean and no unrelated staged state is adopted;
- any predecessor results, resolved requests, return context, and recovery attention come only from
  this fresh Build context.

Do not infer malformed identity or edit under recovery attention. A structurally valid claim that
cannot safely proceed returns to Orchestrator for fail-closed claim recovery; it does not fabricate
a result or mutate another checkout.

## Step 1 - Fix The Task Boundary

Treat `DeliveryBuildContext.task` as executable authority. Its result, commitment IDs, dependency
IDs, required outputs, maintained surfaces, constraints, exclusions, acceptance observations, and
proof boundaries bound the implementation. Predecessor results prove only their exact task digests
and commits. Resolved requests constrain work through structured resolution fields; conversation is
not authority.

Do not edit Design, task definitions, Delivery runtime, package internals, coordination records, or
unlisted surfaces. A missing task premise belongs to Planning or Design, not local implementation.

## Step 2 - Implement And Commit

Make the minimum complete change inside the admitted boundary. Run focused proof, record commands
or observations and relevant results, then load `r-workspace-governance` and create one scoped
commit from explicit owned paths. Require a clean owned state and exact candidate commit. Never
rebase, squash, cherry-pick, amend a reviewed commit, or create a per-task worktree.

For a local review finding, retain the same launch, worktree, and configured reviewer. Preserve the
rejected commit, create a bounded repair commit, rerun affected proof, and supply prior evidence to
fresh review. Never amend or erase a reviewed head.

## Step 3 - Obtain Advisory Exact-Commit Review

Dispatch only `launch.policy.reviewer_agent` to `build-reviewer`; the reviewer agent's frontmatter
owns its model.
Supply the unchanged launch identity, full Build context, complete diff, changed paths, exact commit,
focused proof, custody, ancestry, and prior evidence. Require the reviewer to echo the exact commit
and return disposition `pass | finding`, matching `finding_boundary`, and non-empty evidence.

Repair an `implementation` finding when it remains inside the task and obtain fresh review of the new
commit. A `planning` or `design` finding is evidence for Builder's return choice, not a reviewer-owned
transition. Invalid review evidence publishes nothing.

## Step 4 - Publish Pass Or Route Finding

On `pass`, construct one `DeliveryTaskResult` with a stable result ID, launch change and authority
digest, exact task ID, `DeliveryBuildContext.task_digest`, and reviewed commit. Require the context
digest to be present and use it unchanged; never reconstruct `DeliveryTaskDefinition` from MCP JSON
or reimplement its canonical hashing. Call `publish_delivery_result` with the unchanged change ID
and a `PublishDeliveryResult` containing the outcome ID, claim ID, and result.

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
```

Use `block` only when user-owned input is required. Never substitute `unblock_evidence` for the
required `unblock_condition` and `expected_evidence` fields, and never emit a requestless Build
block for a local execution failure.

Return the selected `DeliveryTransition` directly. Do not call `transition_delivery`; orchestration
validates its outcome, claim, attempt, and commit identity and forwards it byte-for-structure
unchanged. Do not call job, receipt, request, recovery, or transition lifecycle operations.

## Known Pitfalls

- **Context reconstruction:** use `show_build_context`; do not join jobs, activity, semantic updates,
  receipts, or conversation history.
- **Wrong checkout:** all writes belong in the launch's assigned change worktree.
- **History rewrite:** reviewed and rejected commits are immutable evidence.
- **Reviewer action:** findings name an owning boundary; Builder selects the transition.
- **Premature publication:** only exact-commit advisory pass permits `publish_delivery_result`.
