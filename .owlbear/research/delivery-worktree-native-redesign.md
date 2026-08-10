# Delivery Worktree-Native Redesign

> **Status:** Superseded research and decision record
> **Canonical authority:** `delivery-change-worktree-authority.md`
> **Notice:** This document preserves the debate and evidence that led to the canonical authority. Its
> common-Git/alternative local state-store choice, private Task branch, Assembly, local-acceptance,
> and workflow-gate language is not normative. `[LOCKED]` markers below are historical only.
>
> **Owning task:** Delivery safety redesign following destructive target-checkout publication
> **Date:** 2026-08-10
> **Question:** How should OwlBear develop, review, preserve, and offer a Change for user acceptance
> using Git's native branch/worktree model without automated target mutation?
> **Supersedes for product direction:** `delivery-draft-pr-checkpoint-redesign.md` and
> `delivery-proposal-acceptance-redesign.md`. Those documents remain records of rejected alternatives.

## 1. Decision Markers

- **[LOCKED]** Binding product or safety requirement.
- **[REQUIRED]** Behavior necessary to implement the locked model.
- **[DIRECTION]** Preferred implementation detail that may change without revisiting the product model.
- **[DEFERRED]** Deliberately outside the first implementation.
- **[REJECTED]** Considered and not selected.

## 2. Executive Decision

**[LOCKED] OwlBear continues to use Git branches and managed worktrees.** A managed worktree is a
normal linked Git worktree registered in the user's repository and owned by one active Delivery claim.
It intentionally shares the repository's object database, refs, configuration, hooks, stash,
reflogs, and maintenance state. It has its own checked-out files, `HEAD`, and index.

**[LOCKED] Shared repository state is a feature, not an isolation failure.** Commits and refs produced
by one worktree are immediately available to the user and other managed worktrees. OwlBear does not
create per-Change clones, mirrors, object alternates, clone synchronization, or a second Git universe.
A worktree is a concurrency boundary, not a security sandbox.

**[LOCKED] The original incident is prevented by deleting its causes:**

1. Delivery never writes the configured target ref.
2. Delivery never refreshes, resets, checks out, cleans, rebases, or otherwise mutates another
   worktree after publication.
3. Delivery publishes only the OwlBear-owned Change branch.
4. The user alone merges the pull request.

**[LOCKED] When GitHub publication is configured, OwlBear creates a draft pull request early.**
Meaningful reviewed Task and Outcome checkpoints advance one Change branch and its draft PR. OwlBear
does not push every transient edit. Local-only Changes use the same branch/checkpoint/finalization
model without a PR.

**[LOCKED] Local typed Delivery state remains lifecycle authority.** Git commits, branches, the PR,
reviews, and checks are execution artifacts and evidence. They do not independently declare a Task,
Outcome, or Change complete.

**[LOCKED] Delivery's typed state is repository-local but not tracked product content.** It lives under
the repository common Git directory (or an equivalently configured ignored local store), never rides
Task/Change branches, and never dirties the user's checkout. Existing tracked
`.owlbear/target/**` and `.owlbear/completed/**` data are migrated once into that receipt store.

**[LOCKED] Normal engineering capability remains available.** Builders use terminal, Git, project
tools, development servers, browser automation, and the repository's established workflows in their
claimed managed worktree. The design does not claim to contain arbitrary terminal commands.

**[LOCKED] Validation follows the work; tests do not define the development loop.** Each Task states
what observations prove its result. Those may include tests, builds, type checks, lint, browser use,
screenshots, logs, API behavior, generated artifacts, or manual inspection. Required local validation
must pass before a result is promoted as a checkpoint.

**[LOCKED] GitHub Actions remain repository-owned behavior.** OwlBear does not invent risk classes,
budget classes, or an Actions-selection engine. Branch/PR pushes may naturally trigger configured
workflows. OwlBear observes required checks and reports prior-run duration/cost; it does not rely on
Actions as Delivery lifecycle authority.

The normal path is:

```text
design
  -> plan Tasks and Outcomes
  -> build in managed worktrees
  -> review + task-specific local validation
  -> publish meaningful checkpoints to the Change branch/draft PR
  -> final review + validation of exact Change head
   -> mark PR ready when a GitHub publication exists
   -> user merges through GitHub or performs the configured local target merge
   -> OwlBear observes that user-performed acceptance read-only
  -> completion receipt
```

No target checkout refresh, mandatory VM, managed clone, post-merge test rerun, or second happy-path
confirmation exists in this model. GitHub is the normal collaboration path, not a prerequisite for
local/offline Change completion.

## 3. Evidence and Product Constraints

| Source | Finding | Design consequence |
|---|---|---|
| Current `ChangeWorkspace` implementation and incident analysis | Automated target CAS plus checked-out-target refresh caused destructive user-worktree mutation | Remove target CAS and checkout refresh rather than replacing Git's workspace model |
| Current repository practice | OwlBear already uses branches and linked worktrees for concurrent Delivery work | Preserve and tighten the native model |
| Git worktree semantics | Worktrees have separate files, `HEAD`, and index while sharing repository-wide Git state | Treat shared state as intentional; do not claim isolation |
| User product feedback | Clones, mandatory VM proof, abstract CI risk routing, and test-first language are unacceptable complexity | Delete those mechanisms and assumptions |
| GitHub API behavior | PR creation permission may technically include merge capability | Expose only create/update/read operations; omit merge operations; user merge remains the acceptance fact |
| Repository workflow behavior | Pushes and PR updates can automatically trigger Actions | Control cost through meaningful checkpoint frequency and repository workflow configuration, not an OwlBear risk taxonomy |

## 4. Vocabulary

| Term | Meaning |
|---|---|
| **Repository** | The one Git repository shared by the user's checkout and OwlBear worktrees. |
| **User checkout** | The worktree opened and controlled by the user. It may be clean, dirty, staged, conflicted, detached, or mid-operation. |
| **Managed worktree** | A linked Git worktree created, registered, and claimed by OwlBear for bounded Delivery work. |
| **Private task branch** | A local branch/ref used by a worker before its result is assembled into the Change branch. It may be rewritten while unpublished. |
| **Change branch** | The single OwlBear-owned branch published to GitHub and used as the draft PR head. |
| **Checkpoint** | A reviewed Task or Outcome result incorporated into the Change branch and optionally pushed to the draft PR. |
| **Finalized Change** | The exact reviewed and validated Change-branch head offered for user merge. |
| **Acceptance** | The user merges the PR whose head still equals the finalized Change head. |
| **Completion receipt** | Local typed record binding the Change, finalized head, PR, user merge fact, and accepted target commit. |

Use **user checkout** when referring to the directory the user is working in. Use **worktree** for the
Git concept. Do not call the user checkout a security boundary.

## 5. Authority Model

### 5.1 Canonical Local State

**[LOCKED] Delivery's typed event/state store owns lifecycle decisions.** At minimum it records:

- Change, Outcome, Task, attempt, and claim identities;
- planned authority and dependencies;
- exact result commits and reviews;
- required validation observations and results;
- checkpoint incorporation/publication receipts;
- draft PR identity and observed head;
- exact finalized Change head;
- observed user acceptance and completion receipt;
- attention, retry, rejection, deferral, and abandonment decisions.

Git and GitHub can reconstruct useful evidence after a crash, but neither silently advances local
state. External writes use stable operation IDs and reconcile read-only before retry.

### 5.2 Git Authority

Git owns code/history facts:

- commit and tree identity;
- ancestry and merge structure;
- worktree registration;
- branch/ref values;
- remote Change-branch value.

The shared repository means refs and objects are immediately visible across worktrees. Typed Delivery
operations use expected old values for lifecycle-significant ref changes, but ordinary Git inspection
remains ordinary Git.

**[LOCKED] The base for a new Change and all target synchronization is the freshly fetched
`refs/remotes/<remote>/<target>` when a remote is configured.** Delivery never advances or uses a stale
local target branch as its base. Without a remote, the configured local target ref is observed
read-only; the user advances it outside Delivery.

### 5.3 GitHub Authority

GitHub owns external collaboration/acceptance facts:

- repository and PR identity;
- draft/open/closed/merged state;
- observed head and base;
- reviews and required checks;
- merge actor, method, time, and accepted target commit.

Webhooks are wake-up hints. OwlBear reads the provider's current typed state before changing its own.
Laptop operation may poll/reconcile while Cockpit is active and reconcile on explicit resume; no
always-on webhook receiver is assumed.

### 5.4 Completed History

Completion receipts live in the local typed receipt store and are the sole completed-history
authority. Search/show projections are rebuilt from those receipts and may index the accepted commit
for display. Existing in-target `.owlbear/completed/**` packages are migrated once and retained only as
legacy read-only evidence; new Changes do not commit completion packages into product history.

## 6. Managed Worktree Model

### 6.1 What Is Shared

Managed worktrees intentionally share:

- commits and object storage;
- local branches and refs;
- remote-tracking refs;
- repository configuration;
- hooks;
- stash and reflogs;
- worktree registry and repository maintenance.

This provides cheap creation, immediate commit visibility, normal Git tooling, and one source of truth.

### 6.2 What Is Per Worktree

Each worktree has its own:

- checked-out directory;
- `HEAD` attachment/detachment;
- index/staging area;
- in-progress checkout/merge/rebase state where Git stores it per worktree.

OwlBear may mutate these only for the exact claimed managed worktree.

### 6.3 Managed Worktree Identity

Every typed filesystem or worktree mutation validates:

```text
change_id
claim_id
worktree_id
canonical_path
repository_common_dir
expected_head
expected_owned_ref
creation_receipt
```

Admission requires:

1. the claim is active and owns the worktree;
2. canonical path and Git common directory match the receipt;
3. Git still registers that worktree;
4. current `HEAD` and owned branch/ref match expected values;
5. the path is not the user checkout or another claimed worktree;
6. the requested filesystem effect remains under the claimed path;
7. cleanup targets only that exact registered worktree after claim release.

Repository-wide shared state is not denied. Lifecycle-significant shared-ref mutation goes through
specific expected-value operations.

## 7. Safety Boundary

### 7.1 Forbidden Delivery Effects

**[LOCKED] The following do not exist as Delivery operations:**

- update, force-update, delete, merge into, or rebase the configured target ref;
- reset/clean/checkout/switch/restore/rebase/merge in the user checkout or another worktree;
- refresh a checked-out target after remote or local publication;
- generic arbitrary-ref push;
- provider merge, auto-merge, update-branch, or arbitrary provider request;
- cleanup of an unowned, dirty, moved, or identity-mismatched worktree.
- repository-global config writes or hook installation/modification (use per-invocation configuration);
- `git stash` as worker storage (commit on an owned private ref instead);
- reflog/object pruning, `git gc`, or repository maintenance that can discard recovery history;
- deletion of refs outside the exact claim-owned namespace;
- worktree prune/force-remove except exact cleanup of the released owned worktree.

These prohibitions apply to Delivery application code, MCP tools, agent assignments, Cockpit commands,
hooks owned by OwlBear, and provider clients. Structural tests fail if such routes reappear.

### 7.2 Allowed Delivery Effects

Delivery may:

- read repository history and status;
- edit, stage, commit, amend, rebase, merge, and resolve conflicts in the claimed managed worktree;
- create/update OwlBear-owned private task and Change refs with expected values;
- create/remove exact owned worktrees;
- fetch only into remote-tracking refs through fixed refspecs; explicit local-branch destinations and
   `--update-head-ok` are rejected;
- push only the exact Change branch through a destination-constrained publication operation;
- create/update/read the draft PR through fixed provider operations;
- run project tools in the claimed managed worktree.

### 7.3 Honest Terminal Boundary

A general terminal is not a sandbox. An agent process with the user's OS permissions could explicitly
`cd` to another path and cause damage. Separate clones would not prevent that either.

The product guarantee is narrower:

- OwlBear does not design, expose, or call destructive cross-worktree/target operations;
- generated commands are rooted in the claimed worktree;
- agent instructions prohibit mutation outside the claim;
- provider/ref writers accept only typed destinations;
- review and tests cover OwlBear-owned effects.

Transient shared-repository lock contention (`refs`, `packed-refs`, config locks) uses bounded retry
with identity revalidation. It never turns into a forced write.

Malicious or arbitrary host-shell containment is **[DEFERRED]** and would require a separately approved
OS sandbox. The plan does not smuggle that threat model into normal Delivery work.

### 7.4 User Checkout

The user's checkout may be dirty, staged, untracked, conflicted, detached, or mid-rebase/merge. Those
states do not block work in a managed worktree and are never normalized by Delivery.

No mandatory whole-checkout fingerprint or snapshot is introduced. Existing Git history/reflogs and
the user's backup practices remain normal recovery mechanisms. The structural prevention is absence
of target/cross-worktree mutation, not post-hoc recovery theater.

## 8. Task, Outcome, and Checkpoint Flow

### 8.1 Task Work

A Task is a bounded implementation result under one Outcome. Its plan states:

- required output;
- maintained surfaces;
- dependencies;
- constraints/exclusions;
- acceptance observations;
- proof boundary.

A worker uses a claimed managed worktree and private task branch/ref. Private unpublished history may
be rewritten normally.

### 8.2 Task Result

A Task result is eligible for assembly when:

1. the implementation commit is exact;
2. required acceptance observations pass;
3. an independent review accepts that exact result or an explicitly defined equivalent patch after
   rebasing;
4. dependencies are satisfied;
5. no active worker can still mutate the result claim.

Every required observation has a minimal typed record:

```text
observation_id
task_or_finalization_id
exact_commit
observation_kind
command_or_procedure
exit_status_or_artifact_locator
observer_or_runner_identity
observed_at
```

Promotion fails when an observation binds a different commit. Manual/browser observations are valid
when they state the exact procedure and durable artifact/result; they are not reduced to agent prose.

Validation is proportional to the Task. A documentation task may need rendering/link checks; a Python
change may need focused pytest/type/lint checks; a frontend change may need browser interaction,
screenshots, Vitest, or Playwright. The plan does not force every task through every test suite.

Patch-equivalent review carry uses stable patch identity against the old/new parent. Any content
difference, merge commit, or conflict resolution requires review of the new exact commit.

### 8.3 Change Assembly

Accepted Task results are incorporated into the Change branch in dependency order inside an
OwlBear-managed assembly worktree. Conflicts are resolved there, validated, reviewed when semantic,
and committed as normal Change history.

A per-Change assembly/publication lease serializes Change-branch updates. Claims and leases carry a
monotonically increasing fence token recorded in ref-update and checkpoint receipts; stale holders
cannot update refs or append receipts after recovery. Concurrent workers may continue on private task
branches while assembly proceeds.

Dependent Changes serialize on acceptance by default: a Change that requires an unaccepted Change is
not admitted to implementation until that dependency is accepted. Explicit stacked Change PRs are
**[DEFERRED]** rather than implied through unstable branch bases.

### 8.4 Checkpoint Publication

A checkpoint is published when it is useful for durability, collaboration, review, or recovery.

**[DIRECTION] Publish:**

- the first meaningful reviewed result, creating the draft PR;
- verified Outcome boundaries;
- long-running or independently reviewable Task boundaries;
- the final exact Change head.

Do not publish every edit. Once remote, Change history is fast-forward-only. Corrections use successor
commits. If history truly must be rewritten, explicitly supersede the branch/PR rather than force-push.

Checkpoint publication:

1. acquires the Change publication lease;
2. verifies the checkpoint review/validation and current claim fence token;
3. fetches and compares the expected remote Change head;
4. performs a normal fast-forward push of only the Change branch; rejection triggers reconciliation;
5. reads back the exact remote head;
6. records the checkpoint receipt;
7. creates the draft PR if this is the first publication;
8. updates only OwlBear's delimited generated PR summary.

Lost responses reconcile remote branch/PR state before retry. No blind repeat and no force-push.

## 9. Draft Pull Request

### 9.1 Creation

OwlBear creates one draft PR from the Change branch to the configured target after the first meaningful
checkpoint. Creation is idempotent by repository, target, Change branch, and a machine-readable Change
marker.

The PR is a collaboration surface, not lifecycle authority. User comments and prose outside OwlBear's
generated block are preserved.

### 9.2 During Delivery

The generated block shows:

- Change intent and Outcomes;
- published checkpoints;
- current review/validation evidence;
- incomplete work and blockers;
- whether repository checks were triggered;
- exact final head when ready;
- a clear statement that only the user merges.

User- or automation-authored commits on the Change branch are not silently discarded. OwlBear
classifies the author as user, known repository automation, or unknown; adoption always binds the
exact commit and reruns required local validation. Independent semantic review is required unless a
known automation result is mechanically verified and configured as review-carry eligible. Finalization
waits for one stable provider check/head cycle so known writeback automation cannot create an
unbounded ready/adopt/retry loop.

### 9.3 Target Advancement

If the target advances and the Change needs synchronization, OwlBear fetches it and merges it into the
Change branch in a managed worktree. Conflicts are resolved as normal reviewed Change work and pushed
as a successor checkpoint. The target ref and target checkout are never updated by this operation.

Merge-commit acceptance is the concurrency-friendly default because Change ancestry remains present.
If the repository/user chooses squash or rebase merge, the completion receipt records that graph
translation. An unpublished in-flight Change may rebase onto the accepted remote target before its
first checkpoint. A published Change preserves fast-forward history by merging the accepted target as
a reviewed successor checkpoint; if repository policy requires a linear rewrite, it explicitly
supersedes its branch/PR rather than force-pushing. Semantic conflict resolution is re-reviewed.

## 10. Finalization and User Acceptance

### 10.1 Finalization

When all Outcomes are verified:

1. no mutation claim remains active on the Change head;
2. the Change worktree is exact and clean;
3. final Task/Outcome authority matches the Change history;
4. required task-specific local validation passes on the exact head;
5. independent final review accepts the exact head;
6. Delivery records a `FinalizedChangeReceipt` binding these facts.

When GitHub publication exists, readiness additionally requires the remote Change branch and PR head
to equal that commit and repository-required reviews/checks to be known. Local finalization has no
remote prerequisite.

No synthetic Proposal commit, in-tree manifest, immutable Proposal ref, deterministic commit rewrite,
or second Git object identity is required. The reviewed Change head is the offered identity.

### 10.2 Ready State

OwlBear updates the generated PR summary and marks the PR ready. If the head changes afterward, the
finalization receipt becomes stale and the PR returns to draft until the successor is validated,
reviewed, and finalized.

OwlBear never invokes merge or enables auto-merge. Provider protections and required checks remain
normal GitHub defense in depth, not prerequisites for personal-repository usability.

### 10.3 Acceptance

The user's merge is the acceptance decision. Two first-class read-only observations can establish it:

1. **GitHub acceptance:** the provider reports the finalized PR merged into the configured target.
2. **Local acceptance:** the configured local target was advanced by a user-performed Git operation and
   now contains the finalized Change head under the configured merge contract.

For GitHub acceptance, OwlBear proves:

- the exact repository and PR identity;
- the PR was merged to the configured target;
- the PR head at merge equals the finalized Change head;
- GitHub identifies the accepted target commit and merge method;
- repository-required checks/reviews were satisfied as represented by the provider at merge.

Merge actor is recorded. It discriminates user from automation only when OwlBear uses a distinct App/
bot identity. With user credentials, user-only merge is enforced by absence of merge/auto-merge routes
and structural tests; actor data is corroborating, not a false guarantee.

For local acceptance, OwlBear proves the target's prior/current values and configured ancestry/tree
relationship to the finalized head. Delivery never performs that target update itself.

OwlBear records the actual merge method rather than initially forbidding squash, rebase, or merge
commits. Acceptance means the user accepted the finalized work; it does not falsely claim every merge
method preserves the Change commit graph.

If head, base, actor, or merge evidence is ambiguous, the Change enters acceptance attention. It never
fabricates completion.

### 10.4 Completion

A completion receipt binds:

```text
change_id
finalized_change_head
finalization_receipt_id
acceptance_kind             github | local
repository_and_pr_identity  nullable for local acceptance
accepted_target_ref
accepted_target_commit
merge_method
accepted_by
acceptance_evidence_digest
completed_at
```

The receipt is the sole local `completed` authority. The successful user merge needs no second
confirmation and no mandatory post-merge local test rerun.

## 11. Validation and GitHub Actions

### 11.1 Development and Validation

OwlBear's development loop is not prescribed as test-first. The normal shape is:

```text
understand -> implement -> inspect/use -> review -> validate -> promote
```

The exact loop varies by work. Browser work may iterate through a running app before automated tests;
backend work may use focused tests and logs; configuration work may use generated output and linting.

A Task's acceptance observations decide what must be seen before its result is promoted. Finalization
runs the repository's established validation route appropriate to the changed surfaces, using existing
project commands and mappings rather than a new Delivery risk engine.

### 11.2 GitHub Actions

GitHub Actions are external repository behavior:

1. A checkpoint push or PR update may automatically trigger configured workflows.
2. OwlBear reports which checks ran, their exact commit, outcome, and whether GitHub requires them.
3. OwlBear does not normally dispatch extra workflows or rerun them automatically.
4. Required checks gate merge through repository policy and are observed during finalization/acceptance.
5. Actions never complete a Task, Outcome, or Change by themselves.
6. Browser/local-host validation may remain local when Actions cannot provide the needed environment.

Cost control is concrete:

- publish fewer, meaningful checkpoints;
- show which workflows the prior checkpoint triggered and their duration/cost;
- let repository owners configure workflow branch/path filters;
- require explicit user action before any exceptional manual workflow dispatch.

There are no generic `low`/`standard`/`exceptional` budget classes, changed-surface risk classes, or
OwlBear CI-selection policy.

### 11.3 Workflow Changes

Workflow files and composite actions are normal reviewed repository changes. OwlBear does not invent a
separate security approval taxonomy for them. GitHub's own event/permission model and the user's final
PR review remain authoritative. Because same-repository pushes can execute changed automation before
final review, the first checkpoint publication touching `.github/workflows/**` or configured composite
action paths requires one explicit user confirmation and the PR summary plainly shows the change.
This is a concrete path gate and must not expand into generic risk classes.

## 12. Failure and Recovery

| Failure | Recovery |
|---|---|
| Worker or OwlBear process crashes | Expire/recover the exact claim; preserve managed worktree and refs for inspection |
| Assembly crashes before ref update | Retry from unchanged expected Change ref |
| Assembly crashes after ref update | Reconcile exact local ref and event receipt before continuing |
| Push response is lost | Fetch/read exact remote Change head; record matching receipt or enter attention |
| PR creation response is lost | Reconcile by branch/base/Change marker; never create blindly |
| Remote head differs | Do not force-push; adopt reviewed successor, merge, or supersede explicitly |
| User adds a commit | Validate/review and adopt, or ask for explicit disposition |
| PR closes unmerged | Resume with successor, defer, abandon, or close unaccepted |
| PR head changes after finalization | Invalidate finalization and return PR to draft |
| Target advances | Merge target into Change branch in a managed worktree if needed |
| User checkout is dirty/conflicted/detached | Continue in managed worktree; never touch or normalize user checkout |
| Managed worktree identity mismatches | Stop mutation; preserve for explicit recovery/cleanup |
| Managed worktree moved/deleted or registration pruned | Recreate from the exact owned branch/ref after user confirmation; branch/state is authority, not directory survival |
| Remote Change branch deleted while PR is open | Publication attention; recreate only from the exact recorded checkpoint with user-visible reconciliation |
| PR base renamed/deleted | Publication attention; select/reconcile configured successor base before further publication |
| Network is offline | Continue local work/review/validation; queue ordered publication for later |
| GitHub merge evidence is ambiguous | Acceptance attention; no completion receipt |
| Duplicate operation | Return prior receipt or reconcile exact effect idempotently |

## 13. API and Ownership Direction

### 13.1 Keep or Add

```text
create_managed_worktree(change_id, claim_id)
release_managed_worktree(change_id, claim_id)
publish_checkpoint(change_id, checkpoint_id, expected_remote_head, operation_id)
create_or_reconcile_draft_pr(change_id, checkpoint_id, operation_id)
adopt_external_commit(change_id, expected_head, adopted_head, review_id, operation_id)
sync_change_with_target(change_id, expected_target, operation_id)
finalize_change(change_id, expected_head, operation_id)
mark_pr_ready(change_id, finalization_receipt_id, operation_id)
return_pr_to_draft(change_id, finalization_receipt_id, operation_id)
supersede_publication(change_id, successor_branch, operation_id)
observe_required_checks(change_id, exact_head)
observe_acceptance(change_id, finalization_receipt_id)
record_local_acceptance(change_id, finalization_receipt_id, observed_target)
close_unaccepted_publication(change_id, operation_id)
resolve_publication_attention(...)
resolve_acceptance_attention(...)
defer_change(...)
resume_change(...)
abandon_change(...)
```

### 13.2 Remove

- target CAS and target-ref publication;
- checked-out-target refresh;
- automated Integration/integrate-ready mutation;
- managed-clone/mirror/object-alternate infrastructure;
- typed private-remote fetch service created solely for clone isolation;
- whole-user-checkout fingerprint/snapshot machinery;
- mandatory VM/proof-image infrastructure;
- synthetic Proposal commit/manifest/record-ref machinery;
- CI risk/budget selection engine;
- mandatory post-merge validation and second confirmation;
- provider merge/auto-merge/update-branch operations.

### 13.3 Ownership

| Component | Owns | Must not own |
|---|---|---|
| `DeliveryRuntime` | Typed lifecycle, claims, receipts, attention | Git/provider effects |
| `ChangeWorkspace` | Managed worktrees, private/Change refs, exact cleanup | Target publication or other-worktree mutation |
| `ChangeAssembler` | Ordered incorporation and conflict resolution | Remote publication or target mutation |
| `CheckpointPublisher` | Exact expected-head Change-branch push | Arbitrary refs, force-push, target push |
| `GitHubPullRequestClient` | Fixed draft PR create/update/read/ready operations | Merge, auto-merge, update-branch, generic provider writes |
| `ValidationRunner` | Execute task-defined observations in claimed worktree | Define lifecycle or user acceptance |
| `AcceptanceObserver` | Read-only merged-PR evidence | Provider writes |
| `CompletedHistory` | Receipt-backed summaries | Infer completion from target history alone |

## 14. Cutover

No compatibility layer is required.

### Phase 1: Remove the Dangerous Path

1. Delete target CAS/update operations.
2. Delete checked-out-target refresh/reset.
3. In the same release, retarget the existing completion transition to record read-only local
   user-acceptance evidence; it must not update the target.
4. Remove/replace Integration tools, Cockpit routes, agents, and skills that assume automated target
   mutation. Drain active target-mutation attempts before the release boundary.
5. Migrate tracked Delivery/completed authority into the local receipt store.
6. Add structural tests proving destructive symbols/routes are absent.
7. Add adversarial tests proving user checkout files, index, `HEAD`, and untracked content remain
   unchanged across publication success, failure, timeout, retry, and cleanup.

This phase directly prevents recurrence while preserving a local user-completion path. Later phases
add GitHub collaboration/evidence without becoming prerequisites for completion.

### Phase 2: Worktree and Change-Branch Discipline

1. Keep linked managed worktrees and formalize claim/path/ref identity checks.
2. Add per-Change assembly/publication lease and expected-value ref updates.
3. Add exact Change-branch-only publisher.
4. Prove private task concurrency, assembly, conflict resolution, and cleanup.

### Phase 3: Early Draft PR and Checkpoints

1. Add idempotent first-checkpoint branch publication and draft PR creation.
2. Add meaningful Task/Outcome checkpoint receipts.
3. Add generated PR status block while preserving user prose.
4. Add crash/network reconciliation.

### Phase 4: Finalization and Acceptance

1. Replace synthetic Proposal sealing with exact Change-head finalization.
2. Add ready-state invalidation on head drift.
3. Add read-only user-merge observation for configured merge methods.
4. Add completion receipts and receipt-backed history.

### Phase 5: Product Surfaces and Deletion

1. Replace MCP tools, agents, skills, prompts, and Cockpit Integration UI.
2. Delete obsolete states, clone/VM/proof/CI-selection designs, APIs, and tests.
3. Run focused, domain, adversarial, and end-to-end validation.

## 15. Verification Strategy

### 15.1 Original Incident Regression

For user checkouts that are clean, dirty, staged, untracked, conflicted, detached, and mid-rebase or
merge, run publication success/failure/timeout/retry and prove:

- user checkout files are byte-identical;
- index and `HEAD` are unchanged;
- untracked content is unchanged;
- target local ref is unchanged;
- no reset/clean/checkout/refresh command targets the user checkout;
- remote publication touches only the Change branch.

### 15.2 Worktree Semantics

Prove:

- managed worktrees share objects, refs, config, hooks, stash, reflogs, and maintenance as intended;
- per-worktree files, `HEAD`, index, and operation state remain independent;
- a dirty user checkout does not block managed work;
- exact claim/path/ref guards reject the user checkout and another managed worktree;
- cleanup removes only the exact released managed worktree;
- commits made in managed worktrees are immediately visible repository-wide;
- two Changes can assemble/publish concurrently despite shared ref/packed-ref lock contention, using
   bounded retry without forced writes;
- forbidden config/hook/stash/prune/maintenance and unconstrained-fetch effects have no Delivery route.

### 15.3 Checkpoint and PR Transactions

Cover concurrent workers, dependency ordering, assembly lease, exact ref CAS, review after semantic
conflict resolution, first publication, later fast-forward publication, lost responses, stale remote
head, user commits, PR duplicate/reconciliation, offline queueing, and supersession without force-push.

### 15.4 Validation and Actions

Cover exact observation-to-commit binding, task-specific acceptance observations, existing
changed-path validation routing, browser/local server workflows, required GitHub checks, checks on
wrong/stale commits, automatic Actions triggers, known writeback automation/quiescence, the explicit
workflow-file publication gate, and user-visible prior-run cost. Prove no generic risk/budget taxonomy
is required for correctness.

### 15.5 Acceptance

Cover final head stability, draft/ready transitions, GitHub and local user acceptance, each configured
merge method, squash/rebase effects on in-flight Changes, wrong head/base/repository, actor evidence
with distinct and user credentials, closed-unmerged PR, ambiguous provider evidence, idempotent
observation, and one completion receipt.

## 16. Explicitly Rejected Complexity

| Mechanism | Decision | Reason |
|---|---|---|
| Per-Change managed clones | **[REJECTED]** | Duplicates repository administration and creates synchronization/mirror/fetch machinery while not containing arbitrary host-terminal access |
| Treat shared Git state as a defect | **[REJECTED]** | Immediate shared refs/objects/config/hooks are the purpose of worktrees and valuable to OwlBear |
| Whole-checkout fingerprint/snapshot per claim | **[REJECTED]** | Post-hoc recovery machinery does not replace deleting the destructive Delivery path and is disproportionate to normal work |
| Mandatory VM or sandbox | **[REJECTED]** | Breaks normal browser/host workflows and imports an unapproved malicious-code threat model |
| CI risk classes and budget taxonomy | **[REJECTED]** | Hand-wavy policy machinery with no repository-specific operational meaning |
| No special handling for executable workflow changes | **[REJECTED]** | Same-repository publication can execute changed automation before final review; one explicit path gate is proportionate |
| Tests as the primary development loop | **[REJECTED]** | OwlBear uses task-appropriate implementation, inspection, review, and validation loops |
| User-created PR | **[REJECTED]** | Adds ceremony; OwlBear can create/update the collaboration surface while leaving merge to the user |
| Automated merge or target publication | **[REJECTED]** | Reintroduces the authority responsible for the incident |
| Synthetic Proposal commit/manifest/record ref | **[REJECTED]** | The exact reviewed Change head already provides a sufficient Git identity |
| Mandatory post-merge rerun and second confirmation | **[REJECTED]** | Adds latency after the user's authenticated acceptance without changing the accepted fact |

## 17. Definition of Done

1. No Delivery code, tool, agent, provider client, or UI route can update the target ref or merge a PR.
2. Checked-out-target refresh/reset is deleted.
3. Managed linked worktrees remain the execution model and shared Git state is explicitly supported.
4. Typed mutations validate exact claimed worktree/path/ref identities.
5. Shared repository state remains available, while Delivery exposes no unrelated config/hook/stash/
   prune/maintenance writes or unconstrained fetch destinations.
6. User-checkout adversarial tests prove no mutation across publication and recovery paths.
7. One Change branch and, when configured, an early draft PR preserve meaningful reviewed checkpoints.
8. Published history is fast-forward-only; correction and supersession never silently rewrite it.
9. Task-defined observations bind exact commits, and independent review binds exact or mechanically
   patch-equivalent promoted results.
10. GitHub Actions remain repository-owned checks with concrete prior-run cost visibility, one explicit
   workflow-publication gate, and no OwlBear
   risk/budget selection engine.
11. Finalization binds the exact reviewed and validated Change head without synthetic Proposal objects.
12. Only the user accepts; exact GitHub or local read-only observation binds that user action to
    finalization.
13. One local receipt store and completion receipt are the sole completed authority/history substrate.
14. Dirty/staged/untracked/conflicted/detached user checkouts remain untouched.
15. Clone, mirror, VM proof, broad snapshot, CI taxonomy, target Integration, and post-merge ceremony
    surfaces are absent.
16. Dependent Changes serialize by default; claim/publication fence tokens reject stale workers.
17. Focused, domain, adversarial, and end-to-end tests pass.

## 18. Recommendation and Limits

**Recommendation:** adopt this worktree-native model as the new planning authority. Implement the
incident fix first by removing target mutation and checkout refresh, then add early PR/checkpoint and
receipt-backed acceptance in bounded phases.

**Why this exits the corner:** it stops trying to manufacture a security boundary around normal local
development. It uses Git's native concurrency model, removes the exact dangerous authority, and keeps
only mechanisms that directly support collaboration, review, durability, acceptance, or recovery.

**Limits:** worktrees share repository-wide Git state by design. General terminal access can misuse
that state or another path; this design does not claim otherwise. Preventing malicious same-user host
commands requires a separate sandbox decision. The present product instead prevents OwlBear-owned
Delivery routes from performing the destructive target/cross-worktree effects that caused the
incident.
