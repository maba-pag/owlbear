# Delivery Change Worktree Authority

> **Owning task:** Delivery safety redesign following destructive target-checkout publication
> **Status:** Proposed canonical design authority
> **Date:** 2026-08-10
> **Question:** What exact authority, lifecycle, operations, and acceptance model prevents Delivery
> from mutating the target or user checkout while preserving practical automated development?
> **Scope:** Delivery execution, publication, acceptance, and completion
> **Normative body:** Sections 1-12
> **Non-normative appendices:** A-E

## 1. Intent

Delivery turns an admitted Change into one exact, reviewed, validated pull request that the user may
accept by merging. OwlBear performs implementation and publication without updating the target branch,
mutating the user's checkout, or merging the pull request.

The design serves a laptop-resident, single-user development system. It uses Git's native linked
worktrees and shared repository state. It prioritizes a small, deterministic execution model over
intra-Change implementation parallelism.

### 1.1 Non-Goals

- Containing arbitrary same-user terminal commands or malicious repository code.
- Supporting more than one writable worktree for a Change.
- Supporting Tasks that execute concurrently within one Change.
- Completing a Change without a merged GitHub pull request.
- Automating pull-request merge or target-branch updates.
- Selecting, dispatching, or budgeting GitHub Actions workflows.
- Prescribing test-first development.

## 2. Outcomes and Suboutcomes

### OUT-01 — Deterministic Change Execution

One Change has one branch and exactly one managed linked worktree for its full nonterminal lifetime.
Tasks execute sequentially in dependency order in that worktree.

- **OUT-01.1:** A Change never has two registered managed worktrees.
- **OUT-01.2:** At most one mutation claim is active for a Change.
- **OUT-01.3:** Task commits advance the Change branch directly; there is no assembly stage.
- **OUT-01.4:** Concurrent Delivery execution occurs only across different Changes.

### OUT-02 — Safe Publication

OwlBear publishes reviewed Change checkpoints to one draft pull request without changing the target.

- **OUT-02.1:** The first reviewed Task result creates the Change branch publication and draft PR.
- **OUT-02.2:** Verified Outcome boundaries and finalization publish checkpoints.
- **OUT-02.3:** Published Change history advances only by fast-forward push.
- **OUT-02.4:** Delivery has no target-ref, cross-worktree, merge, auto-merge, or update-branch operation.

### OUT-03 — Exact Finalization

One exact Change head is the offered product identity.

- **OUT-03.1:** Required Task authority, observations, review, and final validation bind that head.
- **OUT-03.2:** The remote Change branch and PR head equal that head.
- **OUT-03.3:** Any later head movement invalidates finalization and returns the PR to draft.

### OUT-04 — User-Owned Acceptance

Only a merged GitHub pull request completes a Change.

- **OUT-04.1:** The user performs the merge.
- **OUT-04.2:** OwlBear observes provider evidence read-only.
- **OUT-04.3:** Completion binds the merged PR to the exact finalized head and the accepted merge
  commit GitHub reports.
- **OUT-04.4:** A finalized but unpublished or unmerged Change waits, defers, or is abandoned; it never
  completes through another path.

### OUT-05 — Receipt-Backed History

Typed local receipts, not target-history packages, own Delivery lifecycle and completed history.

- **OUT-05.1:** Delivery artifacts remain under workspace-root `.owlbear/**`, with tracking policy
  determined by artifact ownership.
- **OUT-05.2:** Completion history projects from completion receipts.
- **OUT-05.3:** External writes reconcile before retry and remain idempotent.

### OUT-06 — Proportionate Validation and CI

Validation follows the work, and GitHub Actions remain repository-owned behavior.

- **OUT-06.1:** Each required observation binds an exact commit.
- **OUT-06.2:** Tests, browser interaction, builds, logs, rendering, and inspection are all valid
  observation forms when specified by the Task.
- **OUT-06.3:** OwlBear observes Actions checks but does not select, dispatch, rerun, or classify them.
- **OUT-06.4:** Workflow and composite-action changes publish normally without a Delivery approval gate.

## 3. Concepts and Vocabulary

| Concept | Definition |
|---|---|
| **Repository** | The one Git repository shared by the user's checkout and all Change worktrees. |
| **User checkout** | The worktree opened and controlled by the user. Its state is never normalized by Delivery. |
| **Change** | The unit of Delivery intent and user acceptance. |
| **Change branch** | The single OwlBear-owned branch containing the complete evolving Change. |
| **Change worktree** | The single linked worktree owned by a Change for its nonterminal lifetime. |
| **Task** | A sequential bounded implementation result within an Outcome. |
| **Outcome** | A verifiable portion of the Change's promised result. |
| **Mutation claim** | A fenced lease granting one worker temporary write authority over the Change worktree. |
| **Checkpoint** | An exact reviewed Change-branch head published for durability and collaboration. |
| **Finalized Change** | The exact reviewed and validated Change head offered through the PR. |
| **Acceptance** | GitHub reports that the finalized PR was merged into the configured target. |
| **Completion receipt** | Typed local record binding finalization, PR merge evidence, and the provider-reported accepted merge commit. |
| **Attention** | Durable nonterminal state requiring reconciliation or an explicit user disposition. |

### 3.1 Shared and Per-Worktree Git State

Change worktrees intentionally share objects, refs, configuration, hooks, stash, reflogs, worktree
registration, and repository maintenance. Each worktree has separate checked-out files, `HEAD`, index,
and per-worktree operation state.

Shared state is part of Git's concurrency model, not a security boundary. Delivery narrows its own
shared-state writes through the safety requirements in Section 7.

## 4. Authority Model

### 4.1 Delivery State Authority

The typed Delivery state store is authoritative for:

- Change, Outcome, Task, claim, attempt, and fence identities;
- Task dependencies and execution order;
- exact implementation commits;
- required observation and review receipts;
- checkpoint and publication receipts;
- PR identity and observed head;
- finalization, attention, deferral, abandonment, acceptance, and completion;
- completed-history projections.

**R-AUTH-01:** All Delivery-authored product artifacts reside under the canonical workspace root's
`.owlbear/**` tree. Delivery never stores product policy, source authority, mutable lifecycle state,
receipts, history, or worktree content under `$GIT_DIR`, `$GIT_COMMON_DIR`, `.git/worktrees/**`, or
another Git administration path. Git-owned linked-worktree registration under
`$GIT_COMMON_DIR/worktrees/**`, created and removed only through fixed `git worktree` operations, is
Git administration rather than Delivery-authored product state.

**R-AUTH-02:** Artifact placement and tracking are fixed by ownership:

| Path | Owner and content | Tracking policy |
|---|---|---|
| `.owlbear/delivery/config.json` | Project Delivery policy, including target, remote, and provider repository identity | Tracked |
| `.owlbear/delivery/packages/**` | Authored Design and admitted contract source authority | Tracked |
| `.owlbear/delivery/runtime/changes/<change-id>/**` | Per-Change lifecycle events, claims, attempts, finalization, and acceptance state | Host-local and ignored |
| `.owlbear/delivery/runtime/claims/**` | Shared fenced mutation-claim coordination | Host-local and ignored |
| `.owlbear/delivery/runtime/transactions/**` | Append-only transaction journals and recovery state | Host-local and ignored |
| `.owlbear/delivery/runtime/publications/**` | Checkpoint, remote-head, PR, check-observation, and acceptance-observation receipts | Host-local and ignored |
| `.owlbear/delivery/runtime/completions/**` | Receipt-backed completion history plus non-authoritative display metadata captured atomically from admitted Change authority | Host-local and ignored |
| `.owlbear/delivery/runtime/host.json` | Host-local configured writer and execution capacities | Host-local and ignored |
| `.owlbear/delivery/runtime/capacity.json` | Host-local derived writer ledger and active holders | Host-local and ignored |
| `.owlbear/delivery/worktrees/<change-id>/` | The one linked Change worktree | Host-local and ignored |
| `.owlbear/legacy/briefs/**` | Retired ideation-blackboard artifacts | Tracked, read-only legacy evidence; no new writes |
| `.owlbear/legacy/completed/**` | Legacy in-target completion packages | Tracked, read-only legacy evidence; no new writes |
| `.owlbear/legacy/target-cutover/**` | Preserved pre-Delivery cutover authority | Tracked, read-only legacy evidence; no new writes |

The canonical workspace root is the explicitly selected repository worktree passed at application
startup. Runtime owners keep that root; they do not derive state paths from a worker's current working
directory or from the Change worktree.

Startup rejects a canonical root that is itself a registered linked worktree, lies within any
`.owlbear/delivery/worktrees/**` tree, or has a symlinked `.owlbear` entry. The application receives
the canonical workspace root directly; no tracked adapter pointer or activation receipt selects a
second state root.

**R-AUTH-03:** One append-only event stream per Change commits lifecycle transitions by expected
sequence and prior-event digest.

**R-AUTH-04:** External artifacts are evidence until a typed operation validates them and appends the
corresponding local receipt.

Tracked policy, source authority, and legacy history are backed up by normal Git publication. Ignored
mutable state and new completion receipts under `.owlbear/delivery/runtime/**` are not; backing them
up is the user's operational responsibility.

### 4.2 Git Authority

Git is authoritative for commits, trees, ancestry, refs, worktree registration, and remote-tracking
observations.

**R-GIT-01:** New Changes and target synchronization use a freshly fetched
`refs/remotes/<remote>/<target>`.

**R-GIT-02:** The local target branch is display-only and may be stale. Delivery neither bases work on
it nor updates it.

**R-GIT-03:** Lifecycle-significant Change-ref updates bind an expected old commit and current claim
fence.

**R-GIT-04:** `.owlbear/delivery/config.json` names the remote, target branch, and GitHub repository
identity. Credentials never appear in this tracked file.

**R-GIT-05:** The initial local and remote Change branch name is exactly
`owlbear/change/<change-id>` (`refs/heads/owlbear/change/<change-id>` locally). A necessary published
history supersession uses exactly `owlbear/change/<change-id>+s<n>`, where `n` is the next monotonic
supersession index in typed state. The sibling suffix is required because Git cannot store a branch
and a child branch beneath that branch at the same time; `+` is valid in a Git ref and outside the
ChangeId grammar, so it cannot collide with another canonical Change branch. No operation accepts a
caller-supplied branch namespace or name.

The tracked configuration schema uses the fields `schema_version`, `remote`, `target_branch`, and
`github_repository`. `remote` is a configured Git remote name, `target_branch` is an unqualified branch
name, and `github_repository` is the exact `owner/name` identity reconciled against that remote before
publication. Schema migration renames the current `integration_target` field to `target_branch`.
Host-local writer and execution limits are optionally configured in the ignored
`.owlbear/delivery/runtime/host.json`; the coordinator derives its active writer ledger in
`.owlbear/delivery/runtime/capacity.json`. Tracked project policy does not prescribe laptop capacity.

### 4.3 GitHub Authority

GitHub is authoritative for repository and PR identity, PR head/base, draft/open/closed/merged state,
reviews, checks, merge actor evidence, and the merge commit it reports for a merged pull request.

**R-GH-01:** Webhooks are wake-up hints. Provider state is read back before a local transition.

**R-GH-02:** A laptop session reconciles on Cockpit activation, explicit resume, and bounded polling
while an awaiting-merge Change is actively observed. No always-on webhook receiver is required.

**R-GH-03:** Merge actor is corroborating evidence unless OwlBear uses a distinct App/bot identity.
With user credentials, user-only merge is enforced by the absence of merge routes and structural tests.

**R-GH-04:** GitHub's merged-PR read response has no completed historical merge-method field. Its
`auto_merge.merge_method`, when present, describes configured auto-merge behavior rather than the
completed acceptance fact. Delivery records no merge method and infers none from commit shape.

### 4.4 User Authority

The user owns:

- whether and when to merge the PR;
- disposition of rejected, deferred, abandoned, or irreconcilable Changes;
- repository Actions permissions, triggers, filters, secrets, and environment protections;
- operational backup of the local Delivery receipt store.

## 5. Lifecycle

### 5.1 States

```text
admitted
  -> building
  -> finalized
  -> awaiting-merge
  -> completed
```

Exception and user-disposition states:

```text
building | finalized | awaiting-merge
  -> publication-attention
  -> acceptance-attention
  -> deferred
  -> abandoned
```

`completed` and `abandoned` are terminal.

### 5.2 Normative State Table

| State | Invariant | Allowed exits |
|---|---|---|
| `admitted` | Change authority exists; worktree may not yet exist | `building`, `abandoned` |
| `building` | One Change worktree and branch exist; zero or one active mutation claim | `finalized`, `publication-attention`, `deferred`, `abandoned` |
| `finalized` | Exact head is reviewed and locally validated; PR may be absent or draft | `awaiting-merge`, `building` on head drift, `publication-attention`, `deferred`, `abandoned` |
| `awaiting-merge` | PR is ready and head equals finalized head | `completed`, `building` on head drift, `acceptance-attention`, `deferred`, `abandoned` |
| `publication-attention` | Branch/PR/checkpoint state is ambiguous or cannot progress | resume prior state, `deferred`, `abandoned` |
| `acceptance-attention` | Merge evidence is ambiguous or mismatched | `completed` after exact reconciliation, `deferred`, `abandoned` |
| `deferred` | No active claim; worktree and state are retained | named prior state, `abandoned` |
| `completed` | One completion receipt exists | none |
| `abandoned` | User terminated the uncompleted Change | none |

### 5.3 Task Lifecycle

Tasks execute sequentially in declared dependency order.

```text
planned -> active -> reviewed -> promoted
```

**R-LIFE-01:** A Change has at most one active Task and one active mutation claim.

**R-LIFE-02:** A Task commits directly onto the Change branch in the Change worktree.

**R-LIFE-03:** A promoted Task commit is never rebased for intra-Change assembly because no assembly
stage exists.

**R-LIFE-04:** Target synchronization may create a merge commit. Semantic conflict resolution requires
review of the resulting exact commit.

Outcome progress and Change lifecycle are distinct layers. Outcomes retain `design`, `planning`,
`implementation`, and `completed` progress; `assembly` is absent. The Change is `building` while any
Outcome remains before `completed`. Finalization requires every Outcome completed and verified.
`finalized`, `awaiting-merge`, attention, deferred, abandoned, and completed are explicit Change-level
states rather than values derived only from Outcome progress. Administrative returns remain available
within Outcome design/planning/implementation; crossing a Change-level finalization or terminal
boundary requires the named lifecycle operation in this authority.

### 5.4 Worktree Lifetime

**R-WT-01:** Exactly one managed linked worktree exists for each Change from first entry into
`building` until `completed` or user-confirmed `abandoned` cleanup.

**R-WT-02:** Worktree creation is idempotent and keyed by `change_id`.

**R-WT-02A:** The exact worktree path is
`<canonical-workspace-root>/.owlbear/delivery/worktrees/<change-id>/`. The root is ignored and contains no
non-Delivery user content.

**R-WT-03:** Claims grant fenced mutation authority over the existing Change worktree; claim release
does not remove it.

**R-WT-04:** Attention, deferral, finalization, and awaiting merge retain the worktree.

**R-WT-05:** If the directory or registration is lost, recovery recreates it from the exact Change
branch after explicit user confirmation.

The product exposes a list of retained Change worktrees and their states. Disk use grows linearly with
nonterminal Changes.

### 5.5 Publication and Checkpoints

Required checkpoint triggers are:

1. first promoted Task result, creating the draft PR;
2. each verified Outcome boundary;
3. finalization;
4. explicit user-requested publication.

**R-PUB-01:** Publication uses a normal fast-forward push of only the Change branch.

**R-PUB-02:** Push rejection triggers read-only reconciliation. Publication never force-pushes.

**R-PUB-03:** Published-history correction uses a successor commit. A necessary linear rewrite creates
an explicitly superseding branch/PR.

**R-PUB-04:** Publication frequency is the Delivery-controlled lever for Actions cost.

### 5.6 Finalization

Finalization requires:

- no active mutation claim;
- clean exact Change worktree;
- every Outcome verified;
- every promoted Task commit present in dependency order;
- required observations and independent final review bound to the exact Change head.

A `FinalizedChangeReceipt` binds those facts. When publication is available, Delivery publishes the
final checkpoint and verifies that the remote Change branch and draft PR head equal the finalized
head. Only then does it mark the PR ready and enter `awaiting-merge`. Any later PR-head movement
invalidates the receipt and returns the Change to `building`; the PR returns to draft.

A Change may reach `finalized` before publication is possible. It waits normally. Completion still
requires creating and merging the PR. The other exits are head drift, defer, and abandon.

### 5.7 Acceptance and Completion

Completion requires read-only provider evidence that:

- the exact repository and PR identity match the Change publication;
- the PR base is the configured target;
- the merged PR head equals the finalized Change head;
- one current provider payload reports the PR closed and merged, with a non-null merge timestamp and
  non-null merge commit;
- no earlier merged observation for the bound PR disagrees on its head, merge timestamp, or reported
  merge commit;
- provider-required review/check evidence is recorded for the exact head.

`observe_acceptance` persists the validated current provider payload as a content-addressed
`AcceptanceObservationReceipt` before it may append completion. The first merged receipt establishes
an immutable merged-state latch for the bound PR. Later reads compare against that latch: identical
merged evidence is idempotent, while unmerged or changed evidence enters acceptance attention and
cannot overwrite it. The latch is conflict evidence only; completion always requires a fresh current
merged payload and never proceeds from the latch alone when the provider is unavailable or regresses.

A `CompletionReceipt` binds:

```text
completion_id
change_id
finalization_receipt_id
finalized_change_head
repository_identity
pull_request_identity
accepted_target_ref
accepted_merge_commit
merged_at
acceptance_observation_id
check_observation_ids
review_receipt_ids
acceptance_evidence_digest
completed_at
```

The evidence identities bind content-addressed provider, check, and review receipts. GitHub may
translate the Change graph when accepting a pull request. Completed-history projections show the
finalized Change head and accepted merge commit as separate exact identities, assert no ancestry or
target reachability between them, and record no merge method.

Because acceptance evidence intentionally contains no presentation text, completion atomically stores
content-validated display metadata beside the receipt. That sidecar contains the Change title and
Outcome titles captured from the admitted contract. It is not acceptance evidence, does not contribute
to `completion_id` or `acceptance_evidence_digest`, and cannot authorize completion. Missing or invalid
display metadata makes the completed-history record malformed; projections never invent replacement
text or read mutable active-package state to repair it.

## 6. Operations

Every external-write operation accepts a stable `operation_id`, reconciles before retry, and returns
the existing matching receipt after a lost response.

| Operation | Preconditions | Effects | Receipt / Failure |
|---|---|---|---|
| `ensure_change_worktree(change_id)` | admitted/nonterminal Change | Idempotently creates or verifies the one linked Change worktree and branch | worktree receipt / worktree attention |
| `list_retained_change_worktrees()` | workspace activated | Lists exact owned path, branch, head, lifecycle state, and cleanup eligibility | read-only projection |
| `claim_change_worktree(change_id, claim_id)` | no active claim; expected state | Issues monotonically increasing fence token | claim receipt / claim conflict |
| `release_change_worktree(change_id, claim_id, fence)` | exact active claim | Ends mutation authority; retains worktree | release event / stale-fence rejection |
| `activate_task(change_id, task_id, claim_id, fence)` | dependencies promoted; exact claim | Marks one Task active | task event / dependency conflict |
| `publish_task_result(change_id, task_id, commit, evidence, review)` | exact active Task/commit; evidence/review bind commit | Promotes Task on Change branch | Task result receipt / evidence mismatch |
| `verify_outcome(change_id, outcome_id)` | required Tasks promoted | Marks Outcome verified | Outcome receipt / incomplete Outcome |
| `publish_checkpoint(change_id, expected_remote_head, operation_id)` | required checkpoint trigger; no stale fence | Fast-forward pushes Change branch; read-back | checkpoint receipt / publication attention |
| `create_or_reconcile_draft_pr(change_id, operation_id)` | first checkpoint; provider configured | Creates or binds one draft PR | publication receipt / publication attention |
| `update_generated_pr_summary(change_id, expected_pr_head, operation_id)` | bound PR and exact observed head | Updates only the generated summary region and reports automation-file changes | summary receipt / publication attention |
| `sync_change_with_target(change_id, expected_target, operation_id)` | provider target advanced and sync trigger satisfied | Fetches remote-tracking target and merges it into Change branch in the same worktree | sync receipt / conflict attention |
| `adopt_external_head(change_id, expected_head, adopted_head, operation_id)` | exact descendant head from user/automation | Validates provenance and records the exact adopted head without moving the reviewed boundary | adoption receipt / publication attention |
| `promote_external_head(change_id, expected_head, operation_id)` | reconciled adopted head; no active claim; mutable Change | Explicitly admits review authority for the exact adopted head and advances the reviewed boundary | promotion receipt / authority conflict |
| `finalize_change(change_id, exact_head, operation_id)` | local finalization guards pass | Writes finalization receipt; queues required final checkpoint | finalization receipt |
| `mark_pr_ready(change_id, finalization_id, operation_id)` | exact finalized PR head | Updates PR draft state; reads back | ready receipt / publication attention |
| `return_pr_to_draft(change_id, finalization_id, operation_id)` | finalized head drifted | Returns PR to draft; invalidates finalization | invalidation event / publication attention |
| `observe_required_checks(change_id, exact_head)` | PR exists | Reads check/review evidence; never dispatches or reruns | observation record / provider unavailable |
| `observe_acceptance(change_id, finalization_id)` | `awaiting-merge` or reconciliation | Reads one current PR payload, persists its acceptance observation, validates bound publication/finalization identities, and applies the monotonic merged-state latch | acceptance observation plus completion receipt / acceptance attention |
| `cleanup_completed_change_worktree(change_id, completion_id)` | exact durable completion receipt; no active claim | Removes only the registered Change worktree directory/registration; retains branch and receipts | cleanup receipt / cleanup attention |
| `defer_change(change_id)` | no active claim | Retains worktree and state | defer event |
| `resume_change(change_id)` | deferred | Returns to named prior state | resume event |
| `abandon_change(change_id)` | uncompleted; no active claim; user disposition | Terminal event, then exact owned-worktree cleanup | abandonment receipt / cleanup attention |
| `supersede_publication(change_id, expected_publication_id, operation_id)` | rewrite required; user-visible disposition | Derives the next `owlbear/change/<change-id>+s<n>` branch and creates its PR without force-push | supersession receipt / publication attention |

### 6.1 Target Synchronization Trigger

Target synchronization occurs only when:

- GitHub reports the PR unmergeable;
- repository-required checks require an up-to-date base; or
- the user explicitly requests synchronization.

It never runs on a schedule. It fetches into remote-tracking refs and never advances the local target
branch.

### 6.2 Validation Observation

Every required observation is persisted as:

```text
observation_id
change_id
task_or_finalization_id
exact_commit
observation_kind
command_or_procedure
exit_status_or_artifact_locator
observer_or_runner_identity
observed_at
```

Promotion fails when evidence binds a different commit. Observation forms include tests, builds,
linters, type checks, browser interaction, screenshots, logs, API behavior, rendering, generated
artifacts, and specified manual inspection.

Acceptance observations are a distinct provider-evidence receipt rather than validation evidence.
An `AcceptanceObservationReceipt` content-addresses the exact normalized PR payload, including
repository and PR identity, base, head, state, merged state, merge timestamp, reported merge commit,
nullable merge actor, and observation time. Missing provider response keys are invalid; a present
nullable actor is observed absence. The receipt is appended under
`.owlbear/delivery/runtime/publications/**` before latch or completion state changes.

Completed-history records use an explicitly versioned discriminated schema. Legacy-package records
retain their historical package, target-commit, and ancestry semantics. Completion-receipt records
bind the receipt and its display sidecar, expose finalized Change head and provider-reported accepted
merge commit as separate identities, and make no ancestry, reachability, topology, or merge-method
claim. A receipt suppresses a legacy record with the same `change_id`. Any malformed source record
fails the bounded query rather than silently omitting history.

Completed-history cursors are versioned and bind the query, exact legacy target snapshot, and digest of
the ordered receipt identities. Target movement remains stale-cursor evidence; append-only receipt-set
growth has its own typed cursor-advanced diagnostic so callers can restart pagination intentionally.

### 6.3 GitHub Actions

Delivery:

- reports check identity, exact head, status, conclusion, duration, and provider-required status;
- does not dispatch, rerun, select, classify, or budget workflows;
- does not gate PR ready-state on a green result;
- records failing provider-required checks as publication attention for the exact head;
- relies on GitHub branch protection to block merge while required checks are pending or failing.

Workflow and composite-action files publish through the same checkpoint operation as other files.
Publishing may execute changed repository automation under repository-configured permissions. Delivery
adds no special approval or risk class. The PR summary reports that automation files changed.

### 6.4 Provider Boundary

`serve/delivery` remains provider-transport-free. It owns fixed local Git subprocess execution,
including `git push <remote> refs/heads/owlbear/change/<change-id>`, using host Git credential-helper
authentication. It also owns the `PublicationProvider` protocol, request/response models, validation,
and lifecycle decisions, but no HTTP client or GitHub token. A dedicated `serve/delivery-github`
adapter implements only fixed GitHub API operations for Delivery MCP and Cockpit composition. The
adapter uses the authenticated GitHub CLI (`gh api`) with fixed endpoint templates and argument
vectors; it does not accept arbitrary endpoints or commands and does not read a token from Delivery
configuration. Missing executable/authentication, timeout, rate limit, offline behavior, and response
loss map to typed provider failures and reconciliation. Tests inject an in-memory provider double and
never require network access.

## 7. Safety Boundary

### 7.1 Forbidden Effects

**R-SAFE-01:** No Delivery operation updates, force-updates, deletes, merges into, or rebases the
configured target ref.

**R-SAFE-02:** No Delivery operation resets, cleans, checks out, restores, switches, rebases, or merges
inside the user checkout or another Change worktree.

**R-SAFE-03:** No Delivery operation refreshes a checked-out target after publication.

**R-SAFE-04:** No Delivery, MCP, agent, Cockpit, or provider-client operation merges a PR, enables
auto-merge, or invokes provider update-branch.

**R-SAFE-05:** No publication operation pushes an arbitrary ref, force-pushes, or deletes a remote ref.

**R-SAFE-06:** No Delivery operation writes repository-global config, installs/modifies hooks, uses
stash for worker state, prunes reflogs/objects, runs repository maintenance, or deletes unowned refs.
Per-invocation configuration is allowed.

**R-SAFE-07:** Fetch uses fixed remote-tracking refspecs. Explicit local-branch destinations and
`--update-head-ok` are rejected.

**R-SAFE-08:** Worktree registry mutation is limited to idempotent creation and exact cleanup/recovery
of the one worktree owned by the Change.

**R-SAFE-09:** Delivery writes workspace metadata only within the owned paths in R-AUTH-02. It never
writes product state into Git administration directories or follows a symlinked `.owlbear` state or
worktree root.

### 7.2 Allowed Effects

Delivery may read repository history/status; edit, stage, commit, amend, and resolve Task work in the
claimed Change worktree; create/update claim-owned Change refs by expected value; fetch remote-tracking
refs; fast-forward push the Change branch; create/update/read draft PR metadata; and execute project
tools in the Change worktree.

Publication is the rewrite boundary: private unpublished Change history may be amended or rebased;
once a checkpoint is remote, correction uses successor commits or explicit supersession.

### 7.3 Honest Terminal Boundary

A terminal is not a sandbox. An agent with the user's OS permissions can deliberately navigate to
another path and cause damage. This design guarantees that OwlBear-owned Delivery routes, generated
operations, provider clients, and lifecycle tools do not perform the forbidden effects above. Host
containment requires a separate OS-sandbox decision.

### 7.4 User Checkout

The user checkout may be clean, dirty, staged, untracked, conflicted, detached, or mid-operation. It
does not block work in a Change worktree and is never normalized by Delivery. Execution, publication,
acceptance, and cleanup operations may change only the explicitly owned ignored paths
`.owlbear/delivery/runtime/**` and `.owlbear/delivery/worktrees/**`. Admission intentionally creates
tracked content under `.owlbear/delivery/packages/**`; that user-visible change requires normal user
review and commit. Outside each operation's declared owned paths, user-owned files and untracked
content, the index, `HEAD`, operation state, stash, configuration, hooks, and refs remain unchanged.

## 8. Failure Behavior and Recovery

| Failure | Durable behavior |
|---|---|
| Process crashes with active claim | Fence expires; stale holder cannot write; worktree and branch remain for recovery |
| Claim expires with uncommitted work | Preserve worktree; enter worktree attention; never reset or discard |
| Worktree directory/registration is missing | Recreate from exact Change branch only after explicit user confirmation |
| Shared Git lock contention | Bounded retry with state/ref identity revalidation; never force |
| Target-sync conflict | Preserve conflict state in Change worktree; enter attention; resolve, validate, and review exact result |
| Push rejected | Fetch/read remote head; adopt, merge, supersede, or enter publication attention; never force-push |
| Push response lost | Read exact remote head before retry; append matching receipt when effect already occurred |
| PR creation response lost | Reconcile by repository/base/Change branch/Change marker; never create blindly |
| PR cannot be created | Finalized Change waits or enters publication attention; completion remains unavailable |
| User/automation advances PR head | Classify actor; validate exact head; adopt or reject; finalized Change returns to building |
| Known writeback automation loops | Wait for one stable head/check cycle before re-finalization; attention after configured bounded attempts |
| Required check fails | Record exact check/head and publication attention; do not dispatch/rerun automatically |
| PR is closed unmerged | User defers, resumes with successor, or abandons; never completes |
| Remote Change branch is deleted | Recreate only from exact checkpoint after visible reconciliation |
| PR base is renamed/deleted | Publication attention until configured successor base is reconciled |
| Network/provider unavailable | Continue local Task work and validation; queue publication; finalized state may wait |
| Finalized head changes | Invalidate finalization, return PR to draft, resume building |
| Merge evidence mismatches finalized head/base/repository | Acceptance attention; no completion receipt |
| Translating acceptance | Record finalized head and accepted merge commit separately without an ancestry claim |
| PR reports merged without merge timestamp or merge commit | Acceptance attention; no completion receipt |
| Previously observed merged PR later reads unmerged or reports different head/merge evidence | Acceptance attention; merged-state latch is never overwritten or used to complete without a fresh current merged payload |
| Duplicate operation | Return existing matching receipt or reconcile exact external effect |

## 9. Acceptance Criteria

| ID | Criterion | Traces to |
|---|---|---|
| AC-01 | Runtime and structural tests prove exactly one managed worktree per nonterminal Change | OUT-01.1, R-WT-01 |
| AC-02 | No worktree-add route exists outside `ensure_change_worktree` | OUT-01.1, R-WT-02 |
| AC-03 | Tasks execute sequentially and commit directly to the Change branch; Assembly states/roles/jobs are absent | OUT-01.2-3, R-LIFE-01-03 |
| AC-04 | Two different Changes can execute concurrently with bounded shared-ref lock retry | OUT-01.4 |
| AC-05 | For dirty/staged/untracked/conflicted/detached/mid-operation user checkouts, execution/publication/acceptance/cleanup change only owned ignored `.owlbear/delivery/runtime/**` and `.owlbear/delivery/worktrees/**`; admission changes only its declared tracked `.owlbear/delivery/packages/**` paths; all other user content, index, `HEAD`, and operation state remain identical | OUT-02.4, R-SAFE-01-09 |
| AC-06 | Delivery never updates `refs/heads/<target>` or the remote target branch; fetch may advance only `refs/remotes/<remote>/**`, and explicit local-branch destinations plus `--update-head-ok` are rejected | OUT-02.4, R-GIT-01-02, R-SAFE-01, R-SAFE-07 |
| AC-07 | Publication can update only the exact Change branch by fast-forward | OUT-02.1-3, R-PUB-01-03 |
| AC-08 | First Task, each Outcome, finalization, and explicit user request produce the required checkpoint behavior | OUT-02.1-2 |
| AC-09 | Observation and review receipts reject a promoted/finalized commit mismatch | OUT-03.1, OUT-06.1-2 |
| AC-10 | Finalization binds one exact remote PR head and invalidates on head drift | OUT-03.1-3 |
| AC-11 | No API/tool/client can merge, auto-merge, update-branch, or complete without merged-PR evidence | OUT-04.1-4, R-SAFE-04 |
| AC-12 | A finalized Change with no PR or unmerged PR never reaches completed | OUT-04.4 |
| AC-13 | Acceptance receipts preserve the exact finalized head and provider-reported accepted merge commit as distinct identities, record no merge method, and no projection asserts ancestry or target reachability between them | OUT-04.3 |
| AC-14 | Workflow files publish normally and no Delivery workflow-risk gate/classifier exists | OUT-06.3-4 |
| AC-15 | Actions checks are observed but never selected, dispatched, rerun, or used as sole lifecycle authority | OUT-06.3 |
| AC-16 | Completed history rebuilds from local completion receipts; new product commits contain no Delivery completion package | OUT-05.1-2 |
| AC-17 | Lost-response, stale-fence, stale-head, offline, automation-writeback, duplicate-operation, repeated acceptance observation, and merged-state regression scenarios reconcile idempotently | OUT-05.3 |
| AC-18 | Finalized Changes may wait/defer/abandon without alternate completion | OUT-04.4 |
| AC-19 | No Delivery-authored product artifact is created under `$GIT_DIR`, `$GIT_COMMON_DIR`, or `.git/worktrees/**`; expected Git-owned linked-worktree registration is allowed, and every Delivery `.owlbear/**` artifact obeys R-AUTH-02 | OUT-05.1, R-AUTH-01-02 |

## 10. Modules and Interfaces

### 10.1 Delivery Package

| Module / symbol | Target responsibility |
|---|---|
| `delivery_application_loader.py` | Derives only canonical workspace-root `.owlbear/**` paths; loads remote/target/provider identity; composes state, worktree, provider, and history owners; permits capacity across Changes |
| `delivery_runtime.py` | Outcome progress without Assembly/Integration carriers; consumes the Change-level mutation claim and fence owned by the coordinator |
| `work_items.py` | Projects admitted/building/finalized/awaiting-merge/attention/completed states; no Assembly progress kind |
| `target_runtime.py` | Schedules sequential Task jobs per Change; no Assembly job kind |
| `target_authority.py` | Task/Change authority without `CHANGE_ASSEMBLY` scope |
| `change_workspace.py` / `PortfolioCoordinator` | Own exactly one Change worktree and one monotonically fenced mutation claim per Change; capacity is per Change; no target CAS, checked-out-target cleanliness gate/refresh/reset, Integration repair, or extra proof worktree |
| `portfolio_application.py` | Orchestrates Task promotion, checkpoint publication, finalization, and read-only acceptance observation |
| `attempts.py`, `runtime_transaction.py`, `storage_io.py` | Persist append-only events and transactions under `.owlbear/delivery/runtime/**`; reject symlinked roots and stale sequence/digest/fence writes |
| `target_admission.py` | Admits source authority under tracked `.owlbear/delivery/packages/**` and runtime authority under ignored `.owlbear/delivery/runtime/changes/**` without deriving paths from a Change worktree |
| `completed_history.py` | Projects new completion receipts from `.owlbear/delivery/runtime/completions/**` and legacy `.owlbear/legacy/completed/**` packages through one explicitly versioned record/cursor model |
| `design_package.py` | Retains design/contract authority models; excludes new in-target completion-package writes |
| `proof_checkout.py` | Not present in target architecture |
| `integration_verification.py` | Not present in target architecture |
| `snapshot.py` | Retains source-bound admission snapshot validation without selecting a second workspace state root |
| `target_cutover.py` | Removed after one-way migration; no runtime adapter or activation pointer remains |
| `__init__.py` | Exports the new lifecycle/publication contracts and removes obsolete Assembly/Integration exports |

The Assembly schema removal covers `DeliveryStage.ASSEMBLY`, `DeliveryOutputKind.ASSEMBLY`,
`DeliveryWorkerRole.ASSEMBLY_REVIEWER`, `assembly_required`, `TargetJobKind = "assembly"`,
`PlanScopeKind.CHANGE_ASSEMBLY`, `WorkItemStage.ASSEMBLY`, `WorkItemProgressKind.ASSEMBLY`, and the
workspace coordination `kind = "assembly"` literal.

### 10.2 New Delivery Interfaces

```text
ChangeWorktreeStore
  ensure(change_id)
  list_retained()
  recover(change_id, expected_branch)
  cleanup(change_id)

PublicationProvider
  publish_checkpoint(...)
  create_or_reconcile_draft_pr(...)
  update_generated_summary(...)
  set_draft_state(...)
  observe_checks(...)
  observe_acceptance(...)

CompletionReceiptStore
  append(...)
  list(...)
  search(...)
  get(...)
```

`CompletionReceiptStore` writes under `.owlbear/delivery/runtime/completions/**` in the canonical
workspace root. Its completion transaction also writes the non-authoritative display sidecar described
in Section 5.7. `ChangeWorktreeStore` writes only under `.owlbear/delivery/worktrees/**`. Provider write
implementations expose fixed operations only; no generic provider request or merge method is part of
the interface.

### 10.3 Delivery MCP

Target interfaces expose worktree claim/release, Task promotion, checkpoint publication, PR
reconciliation, target synchronization, finalization, ready/draft state, check observation, acceptance
observation, attention resolution, deferral, resume, and abandonment.

New Integration production and mutation interfaces are absent, including:

```text
admit_reviewed_integration_repair
publish_integration_repair_authority_attention
show_integration_repair_context
create_integration_repair_candidate
```

Compatibility visibility and recovery remain available for persisted legacy state:

```text
show_integration_attention
recover_integration_repair_claim
```

### 10.4 Cockpit

| Surface | Target responsibility |
|---|---|
| `routes/target_work.py` | Replaces Integration attempt registry/routes with publication, finalization, retained-worktree, check, and acceptance observation routes |
| Backend/HTTP models | Carry the explicit Change lifecycle and versioned completion-history records |
| `api/workItems.ts` | Mirrors the new lifecycle/action/progress/attention unions and removes Assembly/Integration carriers |
| `WorkItemDetail.tsx`, `WorkPortfolioTable.tsx`, `workItemPresentation.ts` | Present Task progress, checkpoint/PR timeline, finalization/drift, checks, and awaiting-merge/acceptance attention |
| `CompletedHistoryWorkspace.tsx` | Shows finalized head and accepted merge commit as separate identities for new records, with explicit legacy semantics for old records |
| `useWorkItems.ts`, `WorkPortfolioPage.tsx` | Invoke and reconcile the new fixed operations |
| E2E seed/support | Seed the new persisted schema without Assembly/Integration authority |

The Python-to-TypeScript lifecycle and record changes are coordinated breaking schema changes.
Cockpit has no Integration retry/run controls and no merge control.

### 10.5 Other Workspace Surfaces

| Surface | Required change |
|---|---|
| `serve/delivery-github/` | New fixed GitHub publication adapter and offline test double |
| `serve/delivery-mcp/target_server.py`, `target_models.py`, `server.py` | Replace Integration tools/models; compose provider; preserve workspace-root path authorization |
| `serve/tools/project.py`, `doc_index.py`, `source_index.py` | Read new state projections and preserve `.owlbear/**` index exclusions |
| `setup/init.py`, `seed/.gitignore` | Scaffold tracked provider/remote policy; ignore all mutable `.owlbear/delivery/runtime/**` and `.owlbear/delivery/worktrees/**`; retain tracked package and legacy paths |
| Architecture/package manifests | Declare Delivery, Cockpit, and provider-adapter domains and permitted dependency direction |
| Delivery, MCP, and Cockpit READMEs | Document the new lifecycle, exact paths, and removed Integration/Assembly surfaces |

### 10.6 Agents, Skills, and Prompts

Orchestration dispatches at most one builder for a Change. Packet building commits directly onto the
Change branch in its worktree. Agent tools contain no Assembly, Integration, provider merge, target
mutation, workflow-risk approval, or alternate-completion operation.

## 11. Verification Strategy

### 11.1 Structural Gates

- Add symbol-scoped gates under `tests/` for forbidden target-ref writes, checked-out-target reset,
  provider merge operations, merge-method fields in Delivery/provider response models, obsolete
  Delivery Assembly/Integration carriers, and extra-worktree factories.
  Historical fixtures, generated `serve/cockpit/dist/**`, `assemble_target_app`, `semble`, and unrelated
  prose uses of assembly/integration are excluded.
- Assert one `git worktree add` implementation exists and is reachable only through
  `ensure_change_worktree`.
- Assert provider write clients contain fixed PR create/update/draft operations and no merge documents.
- Assert no completion transition exists without a merged-PR observation receipt.

### 11.2 Behavioral Gates

- Exercise one full sequential multi-Task Change.
- Exercise multiple Changes concurrently and shared-ref lock contention.
- Exercise worktree retention across claim release, deferral, attention, finalization, and awaiting
  merge.
- Exercise missing worktree recovery from the exact Change branch.
- Exercise first/Outcome/final checkpoints, explicit publication, offline queueing, stale remote head,
  lost responses, and supersession.
- Exercise target sync triggers and semantic conflict review.
- Exercise user and known-automation head adoption plus bounded quiescence.
- Exercise finalization, head drift, pending/failing/passing checks, translating and non-translating
  acceptance, merged-state regression, and exact completion receipts.

### 11.3 Incident Regression

For clean, modified, staged, untracked, conflicted, detached, mid-merge, and mid-rebase user checkouts,
run publication success/failure/timeout/retry, target synchronization, finalization, acceptance
observation, and cleanup. Prove only the owned ignored `.owlbear/delivery/runtime/**` and
`.owlbear/delivery/worktrees/**` paths change; user files, index, `HEAD`, untracked content outside those roots,
local target ref, stash, config, hooks, and unrelated refs remain unchanged.

## 12. Limits

- Linked worktrees share repository-wide Git state by design. Delivery constrains its own effects but
  does not isolate arbitrary host-terminal commands.
- One nonterminal Change consumes one checked-out worktree. Disk use grows linearly with open Changes.
- Tasks within a Change are sequential. Long-running independent work must be a separate Change.
- A repository without usable GitHub publication may build and finalize a Change, but it cannot
  complete until a PR can be created and merged.
- Publishing may trigger repository workflows, including automation modified by the published Change.
  Repository permissions, trigger/path filters, secrets, and environment protections own that risk.
- Mutable `.owlbear/delivery/runtime/**` receipts are ignored and are not backed up by pushing Git
  branches; tracked `.owlbear/delivery/config.json`, `.owlbear/delivery/packages/**`, and legacy
  history are.
- With user GitHub credentials, merge-actor evidence cannot distinguish a user browser call from a
  hypothetical OwlBear API call; absence of merge routes is the enforcement boundary.
- A merged pull-request payload does not prove that its reported merge commit is reachable from the
  configured target ref. Delivery performs no reachability check; acceptance is the user's merged-PR
  event, not target-ancestry proof. Translating acceptance may not preserve the finalized Change
  commit as target ancestry.

---

# Appendix A — Decision Records

Appendices are non-normative. They explain the authority but do not override Sections 1-12.

## ADR-01 — One Change Worktree

- **Status:** Accepted
- **Context:** Delivery needs reliable workspace ownership with minimal Git machinery.
- **Decision:** One linked managed worktree exists per nonterminal Change. Tasks execute sequentially in
  that worktree. No Task, Outcome, assembly, proof, or temporary worktree exists.
- **Consequences:** Simpler execution and no intra-Change integration; no intra-Change parallelism;
  linear disk use across open Changes.

## ADR-02 — PR-Only Acceptance

- **Status:** Accepted
- **Context:** Completion needs one explicit user-owned acceptance event.
- **Decision:** Only read-only observation of a merged finalized GitHub PR completes a Change.
- **Consequences:** Offline work continues, but completion waits for GitHub. No target-ref inference or
  alternate local completion protocol exists.

## ADR-03 — Repository-Owned Actions

- **Status:** Accepted
- **Context:** Push/PR events already control Actions behavior and cost.
- **Decision:** Delivery publishes workflow/composite-action changes normally and only observes Actions.
- **Consequences:** No approval gate, risk taxonomy, dispatcher, or budget engine; repository owners
  configure permissions, triggers, filters, and protections.

## ADR-04 — Change Head Is the Offered Identity

- **Status:** Accepted
- **Context:** Review, validation, PR publication, and acceptance already bind an exact commit.
- **Decision:** The finalized Change head is the offered identity.
- **Consequences:** No synthetic Proposal commit, manifest, or record ref exists.

## ADR-05 — Worktree-Native Safety

- **Status:** Accepted
- **Context:** The destructive incident came from target mutation and checked-out-target refresh.
- **Decision:** Delivery removes those effects and keeps Git's shared worktree model.
- **Consequences:** Safety is effect- and ownership-based, not an isolation claim.

# Appendix B — Evidence and Research Index

| Evidence | Supported finding |
|---|---|
| `delivery-worktree-native-redesign.md` | Worktree-native alternative, incident analysis, dual independent reviews, and reconciled safeguards |
| `delivery-draft-pr-checkpoint-redesign.md` | Superseded clone-based alternative and review record |
| `delivery-proposal-acceptance-redesign.md` | Superseded security-first alternative and review record |
| Current `change_workspace.py` | One warm worktree per Change already exists; target CAS and checkout refresh are the destructive path |
| Current Delivery runtime/work-item modules | Assembly is represented as stage, role, scope, and job kind and must be removed for sequential Tasks |
| Current completed-history modules | Completion history currently depends on in-target packages and needs receipt-store projection |
| Current Delivery MCP/Cockpit surfaces | Integration operations and UI are externally exposed and require replacement |
| GitHub API evidence in `.owlbear/sources/overview.md` | PR write permission breadth; merged timestamp, actor, and reported commit fields; test-merge SHA semantics; and absence of a completed historical merge-method field |

# Appendix C — Rejected Alternatives

| Alternative | Decision | Reason | ADR |
|---|---|---|---|
| Worktree per Task or Outcome | Rejected | Couples authority units to workspace resources and creates integration machinery | ADR-01 |
| Separate assembly worktree/stage | Rejected | The Change branch/worktree already is the integration surface | ADR-01 |
| Managed clone per Change | Rejected | Duplicates repository administration without containing arbitrary host access | ADR-05 |
| Automated target publication | Rejected | Reintroduces the authority that caused destructive checkout refresh | ADR-02, ADR-05 |
| Local target movement as acceptance | Rejected | Creates a second ambiguous acceptance protocol | ADR-02 |
| User-created PR | Rejected | Adds ceremony without strengthening user-owned merge | ADR-02 |
| Workflow publication approval gate | Rejected | Contradicts unattended automation; repository policy owns execution | ADR-03 |
| CI risk/budget classification | Rejected | Adds generic policy machinery without repository-specific value | ADR-03 |
| Tests as the development loop | Rejected | Validation is Task-specific evidence, not the implementation method | ADR-04 |
| Synthetic Proposal object | Rejected | Exact finalized Change head already supplies identity | ADR-04 |
| Mandatory VM/sandbox | Rejected | Imports an unapproved threat model and breaks host/browser workflows | ADR-05 |
| Broad checkout fingerprint/snapshot | Rejected | Does not replace removal of the destructive route | ADR-05 |
| Mandatory post-merge rerun/confirmation | Rejected | Adds ceremony after exact user acceptance without changing the accepted fact | ADR-02 |
| Historical merge-method recording | Rejected | GitHub does not report the completed method on the merged-PR read path; commit shape cannot recover it reliably | ADR-02 |
| Accepted-commit parent or compare inference | Rejected | Test-merge and queued commits can mimic accepted topology; Delivery records exact identities without asserting ancestry | ADR-02, ADR-04 |
| Target reachability verification | Rejected | Adds target-observation authority to PR-only acceptance and can regress after legitimate target movement | ADR-02, ADR-05 |

# Appendix D — Migration and Cutover

## D.1 Safety and State Substrate

1. Quiesce Integration/Assembly claims without executing Integration, disable all Integration entry
  points, and remove target CAS/update plus `_refresh_checked_out_target` and
  `_require_clean_checked_out_target`.
2. Add the incident regression and forbidden-symbol gates. No later cutover step runs until they pass.
3. Add complete ignore rules for mutable `.owlbear/delivery/runtime/**` and
  `.owlbear/delivery/worktrees/**` to this repository and `seed/.gitignore`; retain tracked
  `.owlbear/delivery/config.json`, `.owlbear/delivery/packages/**`, and `.owlbear/legacy/**`.
4. Write the exact current tracked runtime-authority snapshot to
  `.owlbear/legacy/<cutover-id>/delivery-target/`, validate its inventory/digests, and commit it before
  changing tracking of `.owlbear/target/**`.
5. Copy the committed snapshot into the versioned `.owlbear/delivery/runtime/**` schema and validate
  all identities/digests against it. Only then remove migrated mutable `.owlbear/target/**` paths from
  the Git index and delete the obsolete source tree after exact-state verification. No artifact moves
  into Git administration.
6. Migrate admitted `CHANGE_ASSEMBLY` / `composition_claim` authority to sequential Task authority;
  irreconcilable active records block cutover for explicit disposition.
7. Move `.owlbear/briefs/**` to `.owlbear/legacy/briefs/**` and `.owlbear/completed/**` to
  `.owlbear/legacy/completed/**` without rewriting historical document content; readers map legacy
  locators explicitly. Write all new completion receipts to `.owlbear/delivery/runtime/completions/**`.
8. Remove `.owlbear/adapters/**`, target-cutover request/receipt/pending paths, and runtime adapter
  selection after migration verification. Retain historical cutover material only under
  `.owlbear/legacy/target-cutover/**`.

No new Change is admitted during D.1. Existing Changes become `building` or `finalized`; none completes
through local target observation.

## D.2 Sequential Change Execution

1. Make the existing Change worktree Change-scoped and idempotent across claims.
2. Replace the portfolio-global capacity of one with one fenced mutation claim per Change while
  retaining explicit configurable host-local cross-Change writer and execution limits.
3. Route Tasks directly onto the Change branch.
4. Remove Assembly stages, roles, scopes, jobs, agents, tools, projections, and tests.
5. Remove extra proof/verification worktree creation.
6. Add one-worktree structural and runtime gates.

## D.3 Publication and PR

1. Bump tracked `.owlbear/delivery/config.json` for remote name, target branch, and GitHub repository
  identity; update `setup/init.py` and remove startup dependence on a local target branch.
2. Add the `serve/delivery-github` fixed-operation adapter and in-memory test double.
3. Add Change-branch-only fast-forward publication from freshly fetched remote-tracking target state.
4. Add idempotent draft PR creation/reconciliation and generated summary ownership.
5. Add required checkpoint triggers and lost-response reconciliation.
6. Add fixed provider read/update/draft operations and check observation.

## D.4 Finalization, Acceptance, and History

1. Add exact-head finalization and head-drift invalidation.
2. Add ready/draft transitions.
3. Add read-only merged-PR acceptance observation, a monotonic merged-state latch, and completion
  receipts bound to content-addressed evidence identities.
4. After D.1.7 has moved and verified legacy packages, version completed-history records and cursors so
  one page can project legacy `.owlbear/legacy/completed/**` packages and new
  `.owlbear/delivery/runtime/completions/**` receipts without false ancestry. Atomically capture the
  non-authoritative display sidecar required for receipt-era title and search projection.
5. Replace Integration Cockpit/MCP/agent surfaces with publication and acceptance surfaces.

## D.5 Deletion and Proof

1. Retain `snapshot.py` for source-bound admission validation and delete `target_cutover.py` plus its
  setup/MCP/Cockpit adapter-activation surface after the one-way migration completes.
2. Delete `integration_verification.py`, `.owlbear/delivery/verification.json`, its `setup/init.py`
  scaffolding and documentation, plus obsolete Integration, Assembly, target mutation,
  completion-package write, and alternate-completion paths.
3. Run structural, focused, domain, adversarial, and end-to-end gates.

# Appendix E — Decision History

| Date | Decision | Authority |
|---|---|---|
| 2026-08-10 | Adopt exactly one linked worktree per Change and sequential Tasks | ADR-01 |
| 2026-08-10 | Make merged GitHub PR the sole acceptance event | ADR-02 |
| 2026-08-10 | Publish workflow changes normally and leave Actions policy to the repository | ADR-03 |
| 2026-08-10 | Use the exact finalized Change head as offered identity | ADR-04 |
| 2026-08-10 | Prevent the incident by removing target/cross-worktree effects rather than adding isolation | ADR-05 |
