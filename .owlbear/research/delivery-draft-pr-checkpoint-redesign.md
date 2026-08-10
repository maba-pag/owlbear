# Delivery Draft-PR and Checkpoint Redesign

> **Status:** Superseded for product direction by `delivery-change-worktree-authority.md`. Retained as
> the reviewed record of the rejected managed-clone, CI-selection, and post-merge-proof alternative.

> **Owning task:** Delivery safety redesign following destructive target-worktree publication
> **Date:** 2026-06-15
> **Question:** How should OwlBear preserve reviewed work remotely, collaborate through GitHub, test
> locally and in CI, and complete a Change without automated target mutation or destructive effects in
> user-owned worktrees?
> **Supersedes for product direction:** `delivery-proposal-acceptance-redesign.md`. That document remains
> the record of a security-first alternative whose user-created-PR, no-Git-agent, and mandatory-VM
> assumptions were rejected after product review.

## 1. Decision Markers

- **[LOCKED]** Binding product or safety requirement. Implementation may change only through an
  explicit design revision.
- **[REQUIRED]** Behavior needed to satisfy the locked model. Internal shape may vary while preserving
  the behavior and proof.
- **[DIRECTION]** Preferred implementation direction. Change is allowed when evidence supports a
  simpler or better implementation without weakening locked requirements.
- **[DEFERRED]** Deliberately outside the first redesign.
- **[REJECTED]** Considered and not selected.

## 2. Executive Decision

**[LOCKED] OwlBear creates one remote Change branch and one draft pull request early in active
Delivery.** The branch and PR provide collaboration, visibility, and remote durability. Reviewed Task
and Outcome checkpoints may advance the branch while work is active.

**[LOCKED] Local typed Delivery state remains canonical.** Git commits, the Change branch, the draft
PR, reviews, checks, and GitHub events are durable projections and evidence. They do not independently
advance the Change lifecycle.

**[LOCKED] Only a final sealed Proposal can be accepted.** Sealing binds the exact final PR head,
Proposal record manifest, authority, reviewed results, final local validation policy/evidence, and
independent Proposal review. Live repository/review/CI policy is re-evaluated without changing product
identity. Any acceptance-relevant branch or PR identity mutation after sealing invalidates that
Proposal and requires resealing.

**[LOCKED] The user alone merges.** OwlBear may create and update its draft PR, push its Change branch,
mark the PR ready, observe GitHub, and verify the result. It exposes no merge operation, never enables
auto-merge, never directly updates the target, and rejects an OwlBear-authored merge as valid
completion evidence.

**[LOCKED] Git and terminal access remain normal engineering capabilities.** Delivery agents may inspect
repository history and perform bounded writes in the exact OwlBear-owned managed clone and Change
refs assigned by an active claim. The safety boundary protects effects and ownership: no destructive
operation in a user-owned worktree and no automated target-ref mutation.

**[LOCKED] Local tests are the primary correctness loop.** They are fast, free, support browser and
host-integrated work, and run on exact reviewed/checkpoint/Proposal commits in OwlBear-managed
clones. Environment and credential sanitization are required, but a VM or sandbox is not.

**[LOCKED] GitHub Actions are selective corroboration, not lifecycle authority.** CI is used when
repository policy requires it or when changed-surface/risk routing justifies its cost. CI does not run
for every local iteration by default, does not replace local proof, and cannot complete a Task,
Outcome, Proposal, or Change by itself.

The lifecycle is:

```text
design
  -> active delivery
       -> create Change branch + draft PR
       -> implement/review/test
       -> publish durable Task/Outcome checkpoints
  -> proposal preparation
  -> seal exact PR head
  -> mark ready / await user merge
  -> observe + verify exact acceptance
   -> reuse equivalent proof or validate changed accepted tree (+ required selective CI evidence)
   -> policy-auto completion when exact evidence is green / protected exception decision otherwise
  -> completed receipt
```

## 3. Sources Studied

| Source | Relevant fact | Limit |
|---|---|---|
| Current Delivery implementation, especially `change_workspace.py` | Managed worktrees and target CAS exist; target publication can refresh a checked-out target destructively | Must be reread immediately before implementation because concurrent edits occurred |
| Current Delivery lifecycle, portfolio, and completed-history modules | Completion is coupled to Integration and target history | Describes current code, not desired authority |
| GitHub REST API documentation logged in `.owlbear/sources/overview.md` | GitHub App pull-request write permission covers both PR creation and merge endpoints | Permission scope alone cannot enforce user-only merge; application/API surface and accepted-actor checks must |
| GitHub branch/ruleset documentation logged in `.owlbear/sources/overview.md` | Protected targets and required checks provide remote defense in depth | Repository policy varies and may be changed by administrators |
| `.owlbear/scratch/turbo-spec-0.37.0.zip` inspection | Typed outcomes, bounded retries, checkpoints, deterministic gates, and credential isolation are useful patterns | No source copied; archive has no established license grant |
| Product discussion in this session | Early PRs, checkpoint pushes, normal Git use, local/browser tests, selective paid CI, and user-owned merge are required usability characteristics | Product authority, not external technical evidence |

## 4. Goals and Non-Goals

### 4.1 Goals

1. **[LOCKED] Make the original incident class structurally unreachable through Delivery.** No Delivery
   route may reset, clean, checkout, switch, rebase, merge into, or otherwise mutate a user-owned
   worktree. No automated Delivery route may update the configured target ref locally or remotely.
2. **[LOCKED] Preserve useful development workflows.** Agents can inspect Git, create commits, rebase
   private local work, resolve conflicts, run local tools, and use browser/E2E capabilities inside
   owned managed clones.
3. **[LOCKED] Preserve reviewed progress remotely without treating intermediate state as final.**
   Durable checkpoints are exact reviewed commits on one fast-forward Change branch.
4. **[LOCKED] Make acceptance an exact external fact.** Completion binds a sealed Proposal to the exact
   accepted target commit and verified Git topology/tree contract.
5. **[LOCKED] Keep user authority narrow and meaningful.** The user decides whether to merge. Routine
   PR creation/updates and evidence-complete happy-path completion are automated; only modeled
   exceptions require a second protected decision.
6. **[REQUIRED] Make crashes, retries, duplicate requests, stale GitHub reads, and partial remote writes
   recoverable through typed receipts and read-only reconciliation.**
7. **[REQUIRED] Keep CI cost visible and policy-driven while retaining local browser-capable proof.**

### 4.2 Non-Goals

1. **[REJECTED]** Removing terminal or Git from Delivery agents.
2. **[REJECTED]** Requiring the user to create or bind the PR manually.
3. **[REJECTED]** Keeping all work local until one immutable final publication.
4. **[REJECTED]** Requiring a `VZVirtualMachine`, container, or networkless sandbox for tests.
5. **[REJECTED]** Treating GitHub Actions as the task engine or sole correctness authority.
6. **[DEFERRED]** Automated merge, merge queues owned by OwlBear, cloud workers, multi-provider support,
   and distributed multi-writer Delivery authority.
7. **[DEFERRED]** Cryptographic signing beyond exact hashes, provider identities, and append-only local
   receipts.

## 5. Authority and Trust Model

### 5.1 Canonical Authority

**[LOCKED] One append-only event stream per Change is the lifecycle commit authority.** Each event has
`change_id`, monotonic sequence, kind, canonical payload, prior-event digest, and event digest. Append
uses compare-and-swap on expected sequence and prior digest. Change, Outcome, Task, Proposal,
publication, observation, attention, and completion states are deterministic folds over the stream.

**[REQUIRED] One repository clone has one configured authoritative Delivery state store.** Concurrent
processes share it and compete through CAS. A restored or second independent store is read-only until
explicit user promotion and remote reconciliation.

**[REQUIRED] The append-only state store has repository-identity-keyed snapshots/backups outside the
user checkout, with integrity digests and tested restore.** If the primary store is unavailable or
corrupt, Delivery stops mutation and enters `state-store-unavailable` attention. Proposal record refs,
remote branches/PRs, and provider evidence may bootstrap a read-only reconstruction candidate, but it
becomes authoritative only through explicit user promotion after reconciliation; projections alone
never silently replace lost authority.

**[LOCKED] The authoritative state store, managed-clone root, temporary proof artifacts, and recovery
snapshots live outside every user-owned worktree.** They are keyed by immutable repository identity in
an OwlBear-owned data root. Normal Delivery activity therefore cannot dirty a user checkout merely by
writing its own authority or scratch state.

### 5.2 Evidence and Projections

- Managed refs and worktrees project active local execution.
- The Change branch and draft PR project active collaboration and durable checkpoints.
- GitHub reviews/checks/merge events are external evidence.
- An immutable Proposal record binds final acceptance authority.
- A completion receipt binds verified external acceptance back into local authority.

**[LOCKED] No projection advances canonical state without a typed operation that validates current
state, exact identities, and expected prior values.** Webhooks are hints that trigger read-back, never
trusted transition commands.

### 5.3 Threat Boundary

The design structurally protects typed Delivery operations against:

- accidental or stale destructive commands;
- path/ref confusion;
- concurrent claims and stale expected heads;
- partial network success and lost responses;
- branch movement after review or seal;
- accidental use of provider merge endpoints;
- repository code reading ambient provider/push credentials during agent work or tests;
- false completion from prose, checks, PR state, or merge metadata alone.

The design detects but cannot structurally contain arbitrary commands issued through an unrestricted
host terminal. It also does not claim to contain:

- a malicious machine administrator or repository administrator;
- a user intentionally running arbitrary commands outside Delivery;
- a fully compromised agent host process with unrestricted OS authority;
- a malicious GitHub administrator rewriting policy/evidence.

These are evidence-integrity limits, not reasons to remove ordinary product capability.

## 6. Ownership and Mutation Invariants

### 6.1 Managed Workspace Identity

**[LOCKED] Managed execution uses isolated managed clones, never linked worktrees sharing the Git
common directory of a user-owned checkout.** Object reuse is allowed only from an OwlBear-owned mirror
with automatic GC disabled and precious-object retention, or through a clone dissociated before its
first commit/proof/push. Managed clones own separate refs, config, index, stash, reflogs, hooks, and
worktree administration. Loss or cleanup of a managed clone cannot mutate the user repository's
recovery surfaces, and user-repository GC cannot invalidate managed work.

**[LOCKED] Every filesystem or Git mutation first resolves a canonical `ManagedWorkspaceIdentity`:**

```text
change_id
claim_id
workspace_id
canonical_path
managed_git_dir
object_source_identity
managed_head_ref_or_detached_commit
allowed_local_refs
allowed_remote_change_branch
created_receipt_id
```

A mutation is admitted only when:

1. the claim is active and owns the managed clone;
2. `realpath` equals the stored canonical path;
3. the managed Git-dir identity matches the repository record and is not the user repository Git dir;
4. the path is under the configured managed-workspace root;
5. the root/user checkout and every registered user-owned worktree are excluded;
6. current `HEAD`, branch/ref, and clone registration match the receipt;
7. the requested effect targets only allowlisted paths/refs;
8. no submodule, symlink, nested repository, or writable object alternate escapes the owned root.

**[REQUIRED] OwlBear-owned hooks and cleanup use the same validator.** Repository-authored hooks are
disabled by default and may run only when an exact reviewed proof profile opts in. Cleanup can remove
only an exact owned clone/ref pair under a cleanup lease. Unknown, dirty, moved, or identity-mismatched
surfaces enter attention rather than being forced.

**[LOCKED] Every OwlBear Git invocation uses `git -C <canonical-path>` and starts with `GIT_DIR`,
`GIT_WORK_TREE`, `GIT_COMMON_DIR`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
`GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_CONFIG*`, and redirecting repository-discovery variables
removed.** Managed Git sets `core.hooksPath` to an empty OwlBear-owned directory unless the reviewed
profile explicitly enables hooks.

### 6.2 Git Capability Matrix

| Capability | User-owned worktree | Owned managed clone | Change branch | Target ref |
|---|---:|---:|---:|---:|
| `status`, `diff`, `log`, `show`, `blame`, materialized object/ancestry reads | allow | allow | read | read |
| edit files, stage, commit | deny | allow under active claim | n/a | n/a |
| private local amend/rebase/reset before publication | deny | allow under active claim and local-ref CAS | not published | deny |
| merge/rebase reviewed successor work locally | deny | allow under typed operation and review policy | later fast-forward publish | deny |
| push | n/a | only typed checkpoint/final publisher | create/fast-forward with expected old SHA | always deny |
| force-push/delete remote | n/a | deny | deny | deny |
| checkout/reset/clean affecting another worktree | deny | deny | n/a | n/a |
| provider create/update PR metadata/draft state | n/a | n/a | allow through typed client | n/a |
| provider merge/auto-merge/update-branch | n/a | n/a | deny/absent | deny/absent |

**[LOCKED] Typed Delivery routes check safety at their effect boundary, not only by command name.** Git
libraries, subprocesses, provider APIs, and MCP tools owned by Delivery receive only validated
destinations and exact expected values.

**[LOCKED] Agent processes receive no provider token, push-capable Git credential helper/config, SSH
agent socket, `gh` authentication, or Cockpit confirmation capability.** All remote Git/PR/CI writes
cross an out-of-process typed publisher boundary. Its authenticated IPC binds each request to an
active claim, operation ID, exact typed destination, and expected prior value. The guarantee is that
credentials are absent from agent environments and no route returns them, not that same-UID OS
credential theft is impossible.

**[REQUIRED] Private-remote reads use an out-of-process typed fetch service.** It accepts only explicit
allowlisted target/Change/Proposal-record refspecs, authenticates the active claim/operation, fetches
into the OwlBear mirror or exact managed clone, returns exact materialized object/ref identities, and
cannot push. Agent Git reads operate only on those already-materialized objects.

**[REQUIRED] Because a general host terminal is not an OS sandbox, OwlBear fingerprints every
user-owned repository/worktree before and after each claim.** The fingerprint covers files relevant to
the claim boundary, `HEAD`, all refs, index, stash list, repository/worktree config, hooks identity, and
worktree registrations. Unexpected change raises safety attention with attribution; the design does
not falsely claim an arbitrary shell command is impossible.

**[REQUIRED] Before granting a terminal-capable claim, OwlBear captures a recoverable snapshot of each
user-owned worktree's tracked, staged, and untracked state into the external OwlBear-owned store using
read-only access to the user surface and an OwlBear-owned temporary index/object store.** The snapshot
is bound to claim/fingerprint identity and retained until post-claim equality is proven. A mismatch
offers explicit user-controlled restoration; OwlBear never auto-overwrites the damaged checkout.
Ignored and configured high-volume generated paths are excluded by default, and the exact exclusion
policy/digest is part of snapshot identity so recovery limits are visible before claim admission.

### 6.3 Target Protection

1. **[LOCKED] Delete target CAS, checked-out-target refresh, and automated Integration publication.**
2. **[LOCKED] No Delivery API, MCP tool, agent assignment, provider client, or Cockpit command exposes
   merge or direct target update.**
3. **[REQUIRED]** The publisher's Git refspec allowlist accepts only the exact Change branch and immutable
   Proposal-record namespace; target-like destinations fail before process/network execution.
4. **[LOCKED]** Setup records one verified target-protection assurance tier:
   `provider-actor-restricted` when the repository supports push/merge actor restrictions excluding
   OwlBear; `provider-ruleset-restricted` when an equivalent user-owned-repository ruleset is proven;
   or `application-contained` when GitHub offers no such provider control. The last tier proceeds with
   endpoint/document allowlists, credential separation, target refspec denial, merge-actor rejection,
   and a visible reduced-assurance receipt. In that tier absence of provider actor/direct-push denial
   is recorded, not treated as validation failure. Setup fails closed only when the configured tier
   cannot be verified, not merely because the repository plan lacks stronger controls.
5. **[REQUIRED]** Acceptance verification rejects merges whose immutable actor identity belongs to an
   OwlBear App/bot/service account.
6. **[REQUIRED]** Static tests scan provider clients and tool registries for merge, auto-merge,
   update-branch, target-update, or generic arbitrary-ref operations.

GitHub App `pull_requests: write` is accepted because PR creation is a product requirement and GitHub
bundles broader endpoint permission. The residual capability is controlled by endpoint allowlisting,
fixed GraphQL operation documents, absence of merge code/tool routes, available target rules, audit
tests, and merge-actor rejection. This is a conscious trade-off, not a claim of least-privilege or
universal provider enforcement.

## 7. Lifecycle

### 7.1 Outcome and Task States

Outcome completion means internal readiness, not Change completion:

```text
design -> planning -> implementation -> assembly? -> verified
```

A Task result is publishable as a checkpoint only after:

- the exact completed commit is independently reviewed;
- the review binds task ID, task digest, authority digest, and commit;
- required local focused tests pass on that commit;
- all dependency checkpoints are ancestors;
- no active mutation claim can still change that result.

**[REQUIRED] Checkpoint publication is serialized by a per-Change publication lease and claim fence.**
Concurrent workers may build/review independently, but only one rebases/adopts and publishes against
the current remote head at a time. An independent review carries across a rebase only when canonical
stable patch identity (`git patch-id --stable` over canonical parent diff) before and after is
identical; the receipt records the carry digest. Patch identity is not semantic identity: local proof
always reruns on the rebased commit, and any patch change requires a new exact-commit review. Merge
commits are never review-carry eligible.

**[DIRECTION] Publish every Outcome checkpoint and publish Task checkpoints when the task is long-lived,
high-risk, independently useful for review, or needed for recovery.** Do not push every transient edit.
The exact routing threshold may be configured per repository.

### 7.2 Change States

| State | Meaning | Owner of next transition |
|---|---|---|
| `design` | Authored design is not admitted | design workflow/user |
| `active-delivery` | Work is executing; Change branch/draft PR may advance by reviewed checkpoint | workers/checkpoint publisher |
| `proposal-preparation` | All Outcomes verified; final exact commit and evidence are being assembled | Proposal builder/reviewer |
| `sealed` | Immutable Proposal binds exact PR head; PR remains draft until final publication | publisher |
| `awaiting-acceptance` | Existing PR is ready and still exactly matches the seal | user/GitHub observer |
| `acceptance-verification` | GitHub reports merge; exact graph/tree/actor are being verified | observer |
| `acceptance-validation` | Local accepted-commit tests and required CI evidence are being reconciled | validation service |
| `awaiting-confirmation` | Exception-only state: exact acceptance has modeled baseline/degraded evidence requiring a protected decision | user in protected Cockpit action |
| `completed` | Immutable completion receipt exists | terminal |
| `publication-attention` | Branch/PR/checkpoint/seal publication is ambiguous or unsafe | remediation/user |
| `acceptance-attention` | Merge, exactness, actor, validation, or evidence cannot be proven | remediation/user |
| `rejection-decision-pending` | PR closed unmerged; disposition required | user |
| `deferred` | User parked active work | user |
| `abandoned` | Never-merged Change intentionally terminated | terminal |
| `closed-unverified` | Merge occurred or may have occurred but exact completion cannot be proven and user closes without a false claim | terminal |

### 7.3 Proposal States

```text
prepared -> sealed | discarded | superseded
sealed -> published | invalidated | withdrawn | superseded
published -> accepted | rejected | invalidated | withdrawn | superseded | closed-unaccepted
accepted -> verified-complete | accepted-unconfirmed
```

- Draft PR and checkpoints predate the Proposal and belong to the Change.
- `sealed` binds the exact PR/base/head/repository identities and final Proposal commit.
- `published` means the PR is ready for user merge at exactly the sealed head.
- `invalidated` means the branch or acceptance-relevant PR metadata changed after seal.
- A Proposal is immutable and never returns to mutable state.
- The Change can continue under a successor Proposal after invalidation, rejection, withdrawal, or
  supersession.
- Seal invalidation returns the Change to `active-delivery` when code/head changed, otherwise to
   `proposal-preparation` for a successor seal.
- A merged Proposal can never be superseded away; it must be verified or closed unverified.

### 7.4 Seal Invalidators

After `ProposalPublicationReceipt`, while the PR is open and unmerged, any of the following atomically
invalidates the current seal or enters attention if the external state is ambiguous. Between local
seal and final publication, divergence is a publication-precondition failure, not seal invalidation:

- PR head differs from `proposal_commit`;
- PR base ref or repository identity changes;
- Change branch is force-updated, deleted, or no longer resolves to the sealed head;
- required final review no longer binds the exact head because the head changed;
- Proposal record is missing or mismatched;
- product-tree proof profile changes through a head mutation.

Returning the PR to draft and pushing a reviewed successor is allowed after invalidation. Resealing
creates a new `proposal_id`; old records remain audit evidence.

Review/check/actor/repository policy drift does not change the product commit and therefore does not
invalidate Proposal identity. It creates a new `SealValidityEvaluation`, blocks readiness/acceptance
when requirements are not met, and enters attention when a merge may already have occurred.

## 8. Canonical Records

### 8.1 `CheckpointReceipt`

```text
checkpoint_id              digest of canonical content excluding timestamp/operation ID
operation_id
change_id
checkpoint_kind            task | outcome
task_id                    nullable for outcome
outcome_id
authority_digest
task_or_outcome_digest
parent_checkpoint_id       nullable only for first checkpoint
dependency_checkpoint_ids
claim_fence_token
review_id
reviewer_id
reviewed_commit
review_carry_digest        nullable unless exact patch-equivalent rebase carries review
expected_remote_head       zero object for first push
published_head             equals reviewed_commit
change_branch
repository_identity
target_ref
local_proof_digest
created_at
```

`checkpoint_id` includes prior/dependency checkpoint identities so a semantically distinct
republication cannot collide. Checkpoint publication requires the reviewed commit to descend from
`expected_remote_head` and the claim fence to remain current through receipt CAS. The push uses exact
expected-old-value semantics and remote read-back. Force-push and deletion are forbidden. A lost
response is reconciled by reading the exact remote branch before retrying.

### 8.2 `DraftPublicationReceipt`

```text
draft_publication_id       digest of stable content
operation_id
change_id
repository_identity
target_ref
change_branch
external_number
external_node_id
external_url
initial_head
created_by_actor
rendered_change_marker
created_at
```

Creation is idempotent by repository identity, Change branch, and a machine-readable Change marker in
PR content. Before creating, reconciliation lists matching PRs but binds only one exact open match. A
closed match requires rejection/supersession disposition; multiple/conflicting matches enter
publication attention. Provider `already exists` responses trigger read-back and exact binding rather
than duplicate creation.

### 8.3 `DeliveryProposal`

```text
proposal_id                digest of canonical sealed payload
change_id
package_id
authority_digest
runtime_digest
result_history_digest
base_target_ref
base_target_commit
reviewed_change_commit
proposal_commit
proposal_tree
record_manifest_path
record_manifest_digest
final_local_proof_digest   recorded attribute; excluded from proposal_id
ci_policy_digest           recorded attribute; excluded from proposal_id
merge_contract_version
proposal_review_id
proposal_reviewer_id
reviewed_proposal_commit
created_at                  excluded from identity
schema_version
```

Proof digests are normalized to exclude host, timing, and ephemeral artifact locations before use in
validity evaluation. The canonical manifest is stored in the immutable Proposal record ref, not in the product tree. It
excludes containing Git object IDs and provider-generated identifiers to avoid identity cycles.
`proposal_id` is computed after deterministic product-commit construction and binds the resulting
commit/tree plus record-manifest digest. Merged product history contains no OwlBear metadata files.

**[REQUIRED] Proposal records use
`refs/owlbear/proposals/<change-id>/<proposal-id>`.** A deterministic record commit stores the canonical
manifest and has `proposal_commit` as a parent so the offered commit remains reachable after PR closure
or branch deletion. Publication verifies provider acceptance of this namespace, pushes create-only,
reads back, and fresh clones enumerate/fetch it through an explicit refspec. Unsupported namespaces
block setup before Delivery begins.

### 8.4 `SealValidityEvaluation`

```text
evaluation_id
proposal_id
observed_pr_head
ci_policy_digest
acceptance_actor_policy_digest
repository_policy_snapshot_digest
required_review_evidence_digest
required_ci_evidence_digest       nullable when current policy selects none
valid
reasons
observed_at
```

Policy, review, and CI evidence are re-evaluable observations rather than Proposal identity. Policy
drift can block readiness or acceptance without rebuilding an unchanged product commit. Only mutation
of commit/base/head/repository facts bound by the Proposal invalidates the seal.

### 8.5 `ProposalPublicationReceipt`

```text
publication_id             digest of proposal, draft publication, and exact ready PR head
operation_id
proposal_id
draft_publication_id
repository_identity
external_number
external_node_id
target_ref
change_branch
published_head             equals proposal_commit
proposal_record_ref
proposal_record_commit
final_rendered_intent_digest
observed_draft_state       false
created_at
```

Final publication first read-backs the immutable Proposal record and exact PR identities/head, then
updates final PR intent and ready state, reads back again, and appends the receipt by CAS. Any mismatch
invalidates or blocks; it never rewrites history to make evidence fit.

### 8.6 Acceptance and Completion

`AcceptanceObservation` records immutable provider/repository/PR identity, observed head, target ref,
target commit, actor ID/type, raw evidence digest, checks, review state, and provider cursor.
Observations are append-only; stale reads cannot regress terminal external state.

`DeliveryCompletionReceipt` binds:

```text
completion_id
change_id
proposal_id
publication_id
acceptance_observation_id
accepted_target_ref
accepted_target_commit
accepted_target_tree
accepted_by_actor_id
accepted_by_actor_type
merge_topology
verification_evidence_digest
accepted_validation_evidence_digest
required_ci_evidence_digest
confirmation_kind            policy-auto | protected-exception
confirmation_id              nullable for policy-auto
proposal_commit
proposal_tree
completed_at
```

The receipt is the sole `completed` authority. PR merge state, a green check, a target ref, or a user
statement alone is insufficient.

## 9. Draft PR and Checkpoint Workflow

### 9.1 Initial Publication

**[DIRECTION] Create the Change branch and draft PR after the first independently reviewed, locally
passing checkpoint.** This avoids empty/noisy PRs while making meaningful work visible early. A
repository may opt into PR creation immediately after design admission when early discussion is more
valuable.

The typed sequence is:

1. validate active claim/worktree identity and reviewed checkpoint eligibility;
2. fetch the remote Change branch with an explicit refspec;
3. reconcile a prior branch/PR side effect using stable identities;
4. push reviewed commit with exact expected old SHA;
5. read back remote branch and append `CheckpointReceipt` by event-stream CAS;
6. create the draft PR if absent using exact target/head repository identities and Change marker;
7. read back typed PR identity/head/draft state;
8. append `DraftPublicationReceipt` by CAS;
9. render status/checkpoint summaries from local typed records into PR metadata.

A failure between any external effect and local receipt never blindly repeats the write. Retry first
observes remote state and either records the already-matching result, safely performs the missing
step, or enters attention.

### 9.2 Subsequent Checkpoints

1. acquire the per-Change publication lease and freeze the exact Task/Outcome result claim/fence;
2. verify independent review and local focused proof on exact commit;
3. require ancestry from last published checkpoint;
4. require provider PR head equals last recorded branch head;
5. push fast-forward with expected old SHA;
6. read back branch and PR head;
7. append checkpoint receipt by CAS;
8. update generated PR summary without overwriting user-authored discussion.

**[REQUIRED] PR body rendering separates a machine-owned generated block from user-owned prose.** The
renderer replaces only the delimited generated block and preserves all other content. Labels,
reviewers, and draft state are changed only by explicit typed operations.

### 9.3 Corrections

- Unpublished private commits may be amended/rebased/reset inside the owned worktree.
- Published checkpoint history is never rewritten. Corrections use reviewed successor commits.
- A bad checkpoint can be marked superseded in typed state but remains in Git history.
- If preserving linearity would require rewriting published history, create a new Change branch/PR and
  explicitly supersede the old publication.
- Conflict resolution occurs in a managed clone, is independently reviewed, and is published as a
  normal successor; it never merges into or refreshes the target checkout.

When the target advances before seal, its exact commit is incorporated into the Change branch through
a reviewed merge checkpoint before Proposal preparation. Conflict detection returns to active
delivery; conflict resolution is committed, locally proven, independently reviewed, and published as
that normal successor checkpoint. The final Proposal commit's parent is always the last checkpoint
head, so the incorporated target is in branch ancestry and GitHub observes the same resolution.

An external/user-authored commit on the Change branch may be adopted through
`adopt_external_commit(change_id, expected_head, adopted_head, review_id, operation_id)`. Adoption
requires descent from the last checkpoint, a clean managed-clone materialization, independent
exact-commit review, the normal local proof route, and an `ExternalAdoptionReceipt`. A GitHub
update-branch merge is adoptable only before seal and only when its topology and resulting tree are
explicitly verified; it is never silently trusted.

## 10. Proposal Construction and Final Publication

### 10.1 Preconditions

1. every Outcome is `verified`;
2. no active mutation claim remains;
3. managed ref equals the last reviewed result boundary;
4. managed clone is clean and exact;
5. Change branch and draft PR head equal the expected last checkpoint;
6. exact target ref/commit are fetched without updating a local target branch;
7. final proof profile and CI-selection policy are resolved from the candidate tree;
8. required final local tests pass on the exact candidate commit;
9. current CI-selection policy is resolved; CI evidence is not a pre-seal identity input;
10. no active Proposal exists.

### 10.2 Deterministic Construction

Build in a fresh disposable managed clone or detached index, never in the root/user checkout:

1. resolve exact base target and reviewed Change commit;
2. require `base_target_commit` to be an ancestor through the reviewed checkpoint history without
   updating target refs;
3. detect any remaining conflict or target drift and return to active delivery for an explicit
   reviewed merge checkpoint; construction never resolves conflicts privately;
4. generate the canonical Proposal record manifest outside the product tree;
5. use the last reviewed checkpoint head directly when its tree is the final product tree; otherwise
   create a deterministic product commit whose parent is that checkpoint head;
6. run final local proof on exact Proposal commit;
7. obtain independent exact-commit Proposal review;
8. calculate Proposal identity;
9. append seal event and create local immutable Proposal ref atomically.

Canonical author/committer identity, message, encoding, parent, and timestamp policy make commit
construction reproducible. Signing is disabled in the first implementation.

### 10.3 Remote Finalization

1. verify exact local seal and no active claims;
2. verify PR/base/head/repository and Change branch match the sealed Proposal;
3. push the final Proposal commit by expected-old fast-forward when it is a successor checkpoint;
4. create immutable Proposal record ref with empty-expect create semantics;
5. read back branch and record;
6. update only the generated PR intent block;
7. mark the PR ready and read back exact head/base/draft state;
8. request/await required final reviews and checks according to current policy;
9. append current `SealValidityEvaluation` binding exact review/check/policy evidence;
10. append `ProposalPublicationReceipt` by CAS and enter `awaiting-acceptance`.

Lost responses are reconciled at every step. The publisher never force-pushes, updates the target,
enables auto-merge, or invokes merge.

## 11. Testing and Evidence Policy

### 11.1 Local Tests Are Primary

**[LOCKED] Every Task, checkpoint, Proposal, and accepted-commit validation policy has a deterministic
local route.** The existing changed-path test router is reused rather than inventing a second mapping.
For this repository that means `uv run test [PATH ...]` for routed Python/frontend tests and
`uv run test-e2e` for the maintained browser gate, with direct runner commands available for focused
diagnostics.

Local execution occurs in the exact claimed managed clone/commit and records:

```text
commit and tree
proof profile digest
resolved command IDs and canonical argv
changed-path/risk inputs
working-directory identity
environment policy digest
toolchain versions
start/end/exit status
timeout
normalized result digest
artifact locators
```

**[REQUIRED] Commands come from repository-owned typed proof profiles, not arbitrary model text.** A
human can revise profiles through normal reviewed source changes.

### 11.2 Environment and Credential Handling

The local runner:

- starts from a minimal allowlisted environment and isolated writable `HOME`, config, and temp roots;
- denies GitHub/App tokens, `GH_TOKEN`, `GITHUB_TOKEN`, SSH agent/socket, `.netrc`, `.ssh`,
   `.config/gh`, cloud/container credential directories, push-capable Git credential helpers, MCP
   secrets, Cockpit confirmation capabilities, and unrelated user environment variables;
- mounts or points only to explicit shared-cache allowlists such as `UV_CACHE_DIR`, npm cache, and
   `PLAYWRIGHT_BROWSERS_PATH`; cache identities/configuration are recorded in proof evidence;
- disables interactive credential helpers and prompts;
- sets explicit timeouts and process-group termination;
- records declared network and host-capability requirements;
- writes artifacts only to owned managed/scratch paths;
- validates worktree identity before and after execution.

**[LOCKED] This is hygiene and accidental-credential isolation, not a security sandbox claim.**
Repository code executes with the user's local OS authority. Tests that require browser, localhost,
filesystem watchers, macOS APIs, or other host integration may declare and receive those capabilities.
Network is allowed only when the proof profile declares why it is needed; offline-capable tests should
remain offline by default.

Shared writable caches are an accepted cross-claim/user-environment residual used for practical local
performance. Privileged proof profiles may require isolated or read-only caches; all profiles record
which cache policy was used.

### 11.3 Browser and E2E Work

**[LOCKED] Browser/E2E tests remain first-class local proof.** They may start local servers, launch the
integrated browser/Playwright Chromium, use loopback networking, capture screenshots/traces, and inspect
rendered pixels/accessibility state. They are not rejected merely because they cannot run inside a
networkless VM or generic sandbox.

Browser proof records server command/profile, bound commit, allocated port, browser/tool version,
viewport, test results, and artifact digests. Long-running servers are claim-owned and terminated on
completion, timeout, retry, or recovery.

### 11.4 Selective GitHub Actions

GitHub Actions are selected by a canonical `CiSelectionPolicy`:

```text
policy_version
repository_policy_inputs
changed_path_classes
risk_classes
required_workflow_check_ids
optional_corroborating_check_ids
budget_class
selection_reasons
selected_for_checkpoint      boolean
selected_for_final_proposal  boolean
```

**[LOCKED] CI selection rules:**

1. Repository-required checks always remain required for final user merge/Proposal evidence.
2. Local tests run first; known local failure never spends CI budget.
3. OwlBear does not explicitly trigger CI for routine private iterations. Checkpoint pushes may still
   trigger repository `push` or `pull_request` workflows; setup inventories those triggers, surfaces
   expected per-checkpoint spend, and uses checkpoint frequency as a cost lever.
4. Checkpoint CI is reserved for configured high-risk/cross-platform/CI-native boundaries.
5. Final Proposal CI runs when repository policy requires it or the risk router selects it.
6. CI-only secrets/deploy/integration checks may corroborate exact commits but cannot become Delivery
   lifecycle authority.
7. Browser/E2E tests may stay local when CI lacks host capability; the policy records that evidence
   source explicitly rather than pretending CI is universal.
8. CI evidence binds workflow definition identity, event type, head SHA, and evaluated base SHA. Head
   must equal the Proposal commit. Base must equal the accepted first parent only when strict
   up-to-date-branch policy is enabled; otherwise base drift is recorded and changed-tree
   accepted-commit validation supplies the final corroboration.
9. Budget exhaustion cannot silently downgrade a required check. It produces a user-visible decision
   or blocks final publication; optional checks may be skipped with a receipt and reason.
10. Re-running CI requires an explicit typed operation and expected workflow/SHA identities.

**[DIRECTION] Initial budget classes are `free-local`, `low`, `standard`, and `exceptional`.** Exact
currency accounting and provider billing APIs are deferred; first implementation records trigger
counts and selected class so cost remains visible and auditable.

**[LOCKED] Changes to `.github/workflows/**`, composite actions, or repository CI configuration are a
privileged risk class.** OwlBear requires explicit user approval before publishing such a checkpoint,
never automatically triggers its workflows, and records the approval/policy. This prevents
agent-authored workflow code from silently executing with repository Actions credentials.
`pull_request_target` and `ready_for_review` triggers are explicitly inventoried: the former is a
privileged secret-bearing execution class and the latter contributes to final-publication cost.

### 11.5 Accepted-Commit Validation

After exact merge verification, OwlBear creates a fresh managed clone detached at the accepted target
commit when revalidation is required. It runs the configured accepted-commit local profile, commonly
the changed-surface full route plus browser gate when relevant. This catches changed-tree merge/
environment effects without touching a user checkout. When accepted tree, proof profile, and
toolchain are identical to sealed proof inputs, an equivalence receipt avoids a redundant rerun.

Required CI evidence is read-only reconciled at the exact accepted/proposal SHA according to the merge
contract and repository policy. OwlBear does not trigger redundant paid CI when existing exact evidence
is sufficient.

A local failure, required CI failure, unavailable required evidence, or profile drift enters
`acceptance-attention`. The user may authorize only explicitly modeled pre-existing baseline failures
or close unverified; confirmation cannot waive an introduced failure through free text.

## 12. GitHub Contract

### 12.1 Provider Client Surface

The GitHub write client exposes only typed operations needed for:

- create draft PR;
- update title and generated body block;
- request reviewers/labels when configured;
- convert draft to ready or ready back to draft;
- close OwlBear-owned unmerged PR;
- trigger/re-run an allowlisted workflow only through an explicit CI operation, if enabled.

It has no generic request method reachable from agents and no methods for merge, auto-merge,
update-branch, arbitrary ref update, branch deletion, ruleset administration, or target mutation.
GraphQL transport accepts only a compiled code-owned set of named operation documents for draft/ready
and other listed operations; callers cannot supply query text. Structural tests prove the document set
contains no merge, auto-merge, or update-branch mutation.
Read clients retrieve exact repository, ref, PR, review, check, workflow, actor, and merge evidence.

### 12.2 Repository Policy

**[REQUIRED] Setup preflight records all items and validates those promised by the selected assurance
tier:**

- immutable repository/installation identities;
- exact target and Change namespace;
- target PR requirement and publisher direct-push denial when the selected provider tier promises
   them; their absence is explicit reduced-assurance evidence in `application-contained` mode;
- required review/check identities;
- whether update-branch/merge queues alter the supported graph contract;
- whether merge commits are allowed, linear history is disabled for this target, and merge queues do
   not make the initial two-parent contract unreachable;
- custom merge drivers/attributes that make local/server merge-tree equivalence unsupported;
- automatic head-branch deletion and whether acceptance evidence survives it;
- workflow trigger coverage for the Change namespace and estimated checkpoint-triggered spend;
- workflow/composite-action paths treated as privileged publication classes;
- App/bot identities excluded from accepted merge actors;
- configured immutable human merge-actor allowlist or validated non-App human actor policy;
- permission inventory and drift;
- exact App permissions: `pull_requests: write`, `contents: write` confined by publisher refspec,
  `checks: read`, `actions: read`, and `administration: read` when policy inspection is available;
  `workflows: write` is absent by default and obtained only through the protected workflow-change
  approval path for that exact checkpoint, then released/rotated after publication;
- webhook/read-back availability.

Policy drift before sealing blocks seal. Drift after sealing invalidates the Proposal when unmerged or
enters acceptance attention when merge may already have occurred.

### 12.3 Supported Initial Merge Contract

**[LOCKED] Support a normal two-parent GitHub merge commit under two exact verification cases:**

- accepted commit on configured target;
- second parent equal to `proposal_commit`;
- merge actor in the configured human allowlist and not an OwlBear identity.

Case A, target unchanged: first parent equals `base_target_commit` and accepted tree equals
`proposal_tree`.

Case B, target advanced: materialize the exact first parent and `proposal_commit` in an isolated
managed clone, compute the deterministic merge tree read-only, require zero conflicts, and require the
result to equal the accepted tree. Verification evidence records Git version, merge strategy,
renormalization/rename settings, and relevant attributes; repositories with custom merge drivers are
unsupported initially. The completion receipt records which case matched.

Squash, rebase, update-branch synthetic commits, merge queues, octopus merges, and manual equivalent-tree
reconstruction are unsupported initially and enter attention. They may be added later as separate
versioned graph contracts, never heuristic exceptions.

### 12.4 Acceptance Sequence

1. observe terminal external state through read-only provider client before evaluating open-PR branch
   invalidators; a merged PR remains verifiable after automatic head-branch deletion;
2. append raw `AcceptanceObservation` without claiming exactness;
3. fetch exact target/object refs without updating local branches/worktrees;
4. verify repository, PR, head, target, immutable actor, and sealed Proposal identities;
5. verify graph topology, parents, tree, and manifest;
6. enter `acceptance-validation`;
7. when Case A accepted tree/profile/toolchain equal the sealed local proof inputs, append a
   `ValidationEquivalenceReceipt`; otherwise run accepted-commit local validation and reconcile exact
   required CI evidence;
8. when merge actor is an allowed human and all exact required evidence is green, append completion
   automatically with `confirmation_kind = policy-auto`; present the immutable evidence summary in
   Cockpit;
9. require protected interactive confirmation only for explicitly modeled baseline/degraded evidence
   decisions; attention can never be waived through free text;
10. derive completed history from the completion receipt.

## 13. User Experience

### 13.1 Cockpit

Cockpit shows:

- active Change, current Outcome/Task, managed-clone identity;
- draft PR link and current branch/head;
- checkpoint timeline with review/local-test/optional-CI status;
- current CI budget class and why a CI run was or was not selected;
- seal validity and exact Proposal head;
- merge readiness blockers;
- acceptance graph, actor, local accepted-commit validation, and CI evidence;
- protected decisions for baseline authorization, closure, rejection disposition, and final confirmation.

There is no merge button. “Open PR” is navigation, not acceptance. “Ready for review” performs the
typed final-publication preflight; it never merges.

### 13.2 PR Presentation

The generated block summarizes:

- Change intent and Outcomes;
- completed reviewed checkpoints;
- exact final Proposal identity when sealed;
- local test evidence and selected CI rationale;
- unresolved blockers/attention;
- clear statement that the user owns merge.

Generated text never claims completion before a completion receipt exists.

## 14. Failure and Recovery

| Failure | Durable state | Recovery |
|---|---|---|
| State store unavailable/corrupt | Mutation stopped; `state-store-unavailable` attention | Restore verified backup or build read-only candidate from Proposal records/remote evidence and explicitly promote after reconciliation |
| Crash after branch push before checkpoint receipt | Remote head may be ahead of local event | Read exact branch; append matching receipt or enter attention; never push blindly |
| Crash after PR creation before receipt | Exact PR may exist | Reconcile by repository/branch/Change marker; bind one exact match or enter attention |
| Crash after marking ready before final publication receipt | Ready PR may be mergeable | Reconcile terminal state first; reconstruct the receipt from exact seal/PR read-back or continue acceptance observation if already merged |
| Stale expected remote head | No admitted push | Fetch/read and recompute successor; never force-push |
| User or external actor moves Change branch | Identity mismatch | Invalidate seal if present; require explicit adoption/successor decision; never overwrite |
| User edits generated PR block | Renderer mismatch | Preserve user prose; regenerate only delimited block after confirming exact PR identity |
| PR closed unmerged | Rejection decision pending | Resume with successor, defer, abandon, or close unverified |
| PR head changes after seal | Seal invalidated | Return PR to draft; review/test successor and reseal |
| Merge response/webhook lost | External state unknown | Read-only reconciliation; never call merge |
| OwlBear identity authored merge | Acceptance attention | Reject as completion evidence; user/remediation decides closure |
| Target history rewritten | Acceptance attention | Preserve evidence; never rewrite local authority to fit |
| Local test timeout/crash | Expired proof claim | Kill process group/server, clean only owned artifacts, reacquire and rerun exact commit |
| Required CI budget unavailable | Publication block/decision | User approves spend, changes policy through reviewed config, or defers; no silent downgrade |
| Optional CI unavailable | Recorded optional skip | Continue only when policy permits and local required evidence passes |
| Accepted commit fails local validation | Acceptance attention | Exact rerun or modeled baseline authorization; never complete on introduced failure |
| Required exact CI evidence missing/fails | Acceptance attention | Reconcile/rerun under policy or close unverified |
| Root/user worktree dirty, staged, untracked, conflicted, detached | Irrelevant to managed operation except read-only display | Continue without touching it; adversarial tests prove byte/ref/index stability |
| Managed clone identity mismatch | Mutation denied | Attention and explicit cleanup/recovery; no forced cleanup |
| Duplicate operation | Existing receipt or CAS loss | Return exact prior result or reconcile; no duplicate external effect |
| Network/provider offline during active delivery | Reviewed local result remains valid but unpublished | Continue local implementation/review/proof, queue deferred publication in order, and publish under lease when connectivity returns; no CI/PR evidence is fabricated |

Every claim has a bounded lease and heartbeat. Lease expiry ends mutation authority but does not
fabricate a lifecycle transition. Recovery first validates exact owned surfaces, terminates owned
processes, and reconciles external state.

## 15. Module Direction

| Module | Owns | Must not own |
|---|---|---|
| `DeliveryRuntime` | Event fold, lifecycle guards, claim/attempt state | Git/provider effects |
| `ManagedWorkspaceGuard` | Canonical clone ownership and mutation admission | Lifecycle decisions |
| `ChangeWorkspace` | Managed clone/ref operations and cleanup | Target publication/checkout refresh |
| `CheckpointPublisher` | Reviewed expected-head Change branch pushes | Arbitrary refs/force push |
| `GitHubPullRequestClient` | Typed create/update/draft/ready/read operations | Merge/auto-merge/update-branch/generic API |
| `CiEvidenceClient` | Typed workflow selection/trigger/read evidence | Task completion/lifecycle authority |
| `ProposalStore` | Candidate/seal/immutable Proposal records | GitHub observation |
| `ProposalBuilder` | Deterministic final commit/manifest construction | Target mutation/publication |
| `AcceptanceObserver` | Read-only external observation and graph verification | Provider writes |
| `LocalValidationRunner` | Exact-commit typed local proof and browser-capable execution | Lifecycle mutation/user confirmation |
| `CompletionService` | Validate evidence and append completion receipt | Merge/test execution |
| `CompletedHistory` | Receipt-backed immutable summaries | Inferring completion from target history alone |

**[DIRECTION] Split functions above 50 lines and keep provider, Git mutation, lifecycle, and test
execution dependencies one-way.** Concrete package placement follows existing `serve/delivery`
architecture rules during planning.

## 16. API and Tool Surface

### 16.1 Agent-Reachable and Mechanical Operations

```text
create_draft_publication(change_id, checkpoint_id, operation_id)
publish_checkpoint(change_id, checkpoint_id, expected_remote_head, operation_id)
adopt_external_commit(change_id, expected_head, adopted_head, review_id, operation_id)
supersede_checkpoint(change_id, checkpoint_id, successor_context, operation_id)
prepare_proposal(change_id, operation_id)
seal_proposal(change_id, candidate_id, expected_sequence, operation_id)
publish_final_proposal(change_id, proposal_id, operation_id)
return_to_draft(change_id, proposal_id, reason, operation_id)
observe_acceptance(change_id, proposal_id, publication_id)
validate_accepted_commit(change_id, observation_id, operation_id)
retry_local_validation(...)
request_ci_corroboration(...)
evaluate_seal_validity(...)
discard_proposal(...)
withdraw_proposal(...)
supersede_proposal(...)
resolve_rejection(...)
defer_change(...)
resume_change(...)
abandon_change(...)
close_unverified(...)
release_claim(...)
recover_claim(...)
cleanup_managed_clone(...)
resolve_publication_attention(...)
resolve_acceptance_attention(...)
```

### 16.2 Cockpit-Only Protected Decisions

```text
confirm_exception_completion(change_id, observation_id, validation_id, capability, operation_id)
authorize_preexisting_baseline(..., capability, operation_id)
authorize_workflow_change_publication(..., capability, operation_id)
promote_state_store(..., capability, operation_id)
```

These operations are absent from MCP/agent registries. Structural tests reject any protected decision
appearing in an agent tool assignment or callable without a live decision-specific UI capability.

### 16.3 Remove

- target CAS and checked-out-target refresh;
- direct Integration/integrate-ready operations;
- generic Git/ref/provider mutation tools;
- automated merge/auto-merge/update-branch routes;
- user-created-PR waiting/binding workflow;
- mandatory VM image/proof/evidence machinery;
- completion inferred from current target ancestry/tree alone.

### 16.4 Agent Assignment

Builders receive terminal, managed filesystem editing, local Git, typed local tests, and bounded
checkpoint publication for the active claim. Reviewers receive read-only repository/Git/test evidence
and no mutation of the candidate under review. Publishers receive only typed publication operations.
Observers are read-only. Protected exception decisions are local Cockpit capabilities never delegated
to agents or test subprocesses.

**[LOCKED] Every protected exception decision requires a server-minted, decision-specific, single-use,
short-lived capability rendered only into the interactive Cockpit UI and bound to Change, attention,
expected event sequence, exact evidence, and allowed decision.** Submission verifies the capability,
`Origin`, and fetch-site metadata before CAS and consumes it atomically. A bare loopback POST or replay
is rejected. This raises the boundary against agent/tool calls without claiming containment against a
malicious same-UID host process.

## 17. Cutover

No backwards compatibility or legacy migration layer is required.

### Phase 0: Freeze and Baseline

1. Disable current automated Integration target publication and checked-out-target refresh. Until
   Phase 5 lands, Changes use the existing external-completion preparation route followed by an
   explicitly human-performed merge and read-only acknowledgement; no automated target write remains.
2. Capture adversarial tests proving user-worktree and target-ref immutability.
3. Inventory Delivery/MCP/Cockpit/agent/prompt references to Integration and completion.

### Phase 1: Safety Kernel

1. Implement canonical managed-clone identity and mutation guard.
2. Add exact ref destination/expected-old publisher.
3. Remove target CAS/refresh code and tests that authorize it.
4. Add static provider/tool-surface denials for merge and arbitrary target/ref writes.

### Phase 2: Authority and Lifecycle

1. Add append-only Change event records and new state fold.
2. Rename Outcome `completed` to `verified`.
3. Add checkpoint/draft publication/Proposal/observation/completion records.
4. Replace Integration history with receipt-backed completion.

### Phase 3: Draft PR and Checkpoints

1. Add Change branch naming and idempotent early draft PR creation.
2. Add reviewed fast-forward checkpoint publication and reconciliation.
3. Add generated PR block ownership and Cockpit timeline.
4. Prove crash recovery at every branch/PR receipt boundary.

### Phase 4: Local and CI Evidence

1. Reuse changed-path test router for typed exact-commit local profiles.
2. Add environment/credential hygiene and browser-capable proof records.
3. Add CI selection policy, cost class, exact-SHA evidence, and optional trigger client.
4. Keep CI evidence subordinate to local lifecycle authority.

### Phase 5: Seal and Acceptance

1. Add deterministic Proposal construction and independent review.
2. Add exact final publication/ready transition and seal invalidation.
3. Add read-only merge observation, exact graph/tree/actor verification.
4. Add accepted-commit validation, protected confirmation, and completion receipt.

### Phase 6: Product Replacement

1. Replace MCP tools, agent assignments, prompts, and skills.
2. Replace Cockpit Integration UI with Change/PR/checkpoint/acceptance views.
3. Delete obsolete APIs, states, docs, tests, and the interim external-completion route after the new
   acceptance path proves end to end.
4. Run full domain and end-to-end regression gates.

## 18. Verification Strategy

### 18.1 Structural Safety

- No production symbol performs target CAS, target checkout refresh, provider merge, auto-merge,
  update-branch, or arbitrary ref push.
- Managed execution Git directories are distinct from every user-owned repository common directory;
   clone cleanup cannot mutate user refs, config, stash, hooks, reflogs, or worktree registrations.
- Tool registries and agent definitions expose no such operation.
- Publisher refspec parser rejects target, tag, notes, wildcard, deletion, and force destinations.
- GitHub client endpoint allowlist rejects merge URLs/methods even with a write-capable token.
- Test subprocess environments contain no provider/user-confirmation credentials.
- Agent subprocess environments contain no provider/push credentials, `gh` auth, SSH agent, or
   push-capable credential helper; only the out-of-process typed publisher can perform remote writes.
- Git invocation tests inject hostile `GIT_*` variables and repository hooks and prove they are
   scrubbed/disabled unless an exact reviewed profile opts in.

### 18.2 User-Worktree Adversarial Matrix

For clean, modified, staged, untracked, conflicted, detached-HEAD, in-progress rebase/merge, linked
user worktree, symlink, submodule, and nested-repository states, checkpoint publication, Proposal sealing,
acceptance verification, local testing, failure, timeout, retry, cleanup, and completion must leave the
user worktree's files, index, `HEAD`, refs, stash, config, hooks, and untracked content byte-identical.

### 18.3 Checkpoint and PR Transactions

Cover first push, subsequent push, lost push response, stale head, duplicate operation, PR create
response loss, duplicate/mismatched PRs, user metadata edits, generated block edits, closure, branch
deletion, automatic post-merge deletion, external branch movement/adoption, publication lease/fence,
patch-equivalent review carry, out-of-order workers, network timeout, provider cursor staleness, and
concurrent CAS.

### 18.4 Local and CI Proof

Cover changed-path routing, exact commit binding, dirty managed clone rejection, environment
allowlist, credential removal, timeout/process-tree cleanup, local server cleanup, browser screenshots/
traces, host-capability declarations, offline/default network behavior, CI selection by risk, required
versus optional CI, budget exhaustion, stale/wrong-SHA checks, workflow drift, and avoiding redundant CI.

### 18.5 Seal and Acceptance

Cover deterministic rebuild, identity-cycle avoidance, independent exact-commit review, post-seal
branch/PR/review/policy drift, normal merge acceptance, wrong parent/head/tree/manifest, squash/rebase/
queue/update-branch topology, unauthorized/OwlBear actor, stale observation, rewritten target, local
accepted-commit failure, baseline authorization, confirmation replay, and receipt idempotency.

### 18.6 End-to-End Acceptance Scenarios

1. First reviewed checkpoint creates one draft PR and survives a lost response without duplication.
2. Reviewed Task/Outcome successors publish fast-forward while private edits remain local.
3. A correction after a published checkpoint adds history rather than rewriting it.
4. Browser-required work runs locally with localhost/browser artifacts and no ambient credentials.
5. Low-risk work uses local proof without unnecessary Actions spend.
6. High-risk or repository-required work obtains exact-SHA Actions corroboration.
7. Final seal pins exact PR head; any later mutation invalidates it.
8. OwlBear marks ready but cannot merge through any tool/API path.
9. User merge is observed and exact merge commit/tree/actor are verified.
10. Changed accepted trees are tested in a fresh managed clone without touching the user checkout;
   equivalent trees reuse sealed proof through an equivalence receipt.
11. Exact green evidence creates one immutable completion receipt automatically after the authorized
   user merge; protected user action is reserved for modeled exceptions.
12. Every failure boundary recovers idempotently or enters typed attention without false completion.

## 19. Observability

Every external effect and proof attempt logs structured operation/change/claim/attempt IDs, exact
before/after SHAs, destination identities, policy/profile digests, selected CI reason/budget class,
provider request correlation, receipt ID, elapsed time, and redacted failure category. Secrets,
capabilities, raw environment values, and credential-bearing URLs are never logged.

Cockpit and CLI can explain from receipts:

- why a checkpoint was publishable;
- why CI was selected or skipped;
- which exact commit each test/check reviewed;
- why a seal is valid/invalid;
- why a merge is accepted/unsupported;
- why completion is available/blocked.

## 20. Directional Choices and Deferred Detail

The following are **[DIRECTION]**, not locked:

- create draft PR after first reviewed checkpoint rather than immediately after design admission;
- publish all Outcome and selected Task checkpoints;
- one remote branch per Change;
- generated PR body delimiter format;
- initial CI budget class names and thresholds;
- exact local proof record serialization and artifact retention;
- module/class names and Cockpit layout;
- deterministic unsigned Proposal commits in the first release.

The following require later explicit design if introduced:

- squash/rebase/merge-queue acceptance;
- automated merge in any form;
- distributed/cloud workers;
- multiple concurrent authoritative clones;
- providers other than GitHub;
- CI billing API integration or hard monetary quotas;
- cryptographic artifact signing;
- malicious-code sandboxing.

## 21. Rejected Alternatives

| Alternative | Decision | Reason |
|---|---|---|
| User manually creates PR after seal | **[REJECTED]** | Adds ceremony, hides active work, and solves App permission breadth by removing useful product behavior |
| Push only one immutable final Proposal | **[REJECTED]** | Loses remote durability and incremental review of meaningful progress |
| Push every transient edit | **[REJECTED]** | Produces noise, unstable review surfaces, and unnecessary CI triggers |
| No terminal/raw Git for agents | **[REJECTED]** | Removes core engineering capability instead of guarding dangerous destinations/effects |
| Mandatory networkless VZ VM | **[REJECTED]** | High complexity, poor browser/host compatibility, and a threat model not justified for the laptop product |
| GitHub Actions for every checkpoint | **[REJECTED]** | Spends money before local proof and makes CI a de facto execution loop |
| Never use GitHub Actions | **[REJECTED]** | Loses repository-required and cross-environment corroboration |
| CI green means complete | **[REJECTED]** | Check status does not prove local authority, exact acceptance, user merge, or completion receipt |
| Protect only with `git status --clean` | **[REJECTED]** | Cleanliness does not establish ownership and cannot guard atomic/ref/provider mutation paths |
| Give App write permission and trust prompts not to merge | **[REJECTED]** | Prompt policy is weaker than endpoint/tool absence, rules, actor rejection, and structural tests |

## 22. Definition of Done

The redesign is complete only when:

1. automated target mutation and checked-out-target refresh code paths are absent;
2. user-owned worktree adversarial tests prove byte/ref/index stability;
3. agents retain useful Git/terminal/browser workflows inside owned managed clones;
4. early draft PR creation and checkpoint pushes are typed, reviewed, fast-forward-only, idempotent,
   and crash-reconcilable;
5. post-publication corrections never rewrite remote checkpoint history;
6. final seal binds exact PR head, code-derived Proposal evidence, CI selection policy, and independent
   review while live policy/evidence remains re-evaluable;
7. post-seal identity drift invalidates seal before acceptance; live policy drift blocks without
   rebuilding an unchanged commit;
8. no Delivery API/tool/client can merge, auto-merge, update target, or invoke arbitrary provider/ref
   writes, and OwlBear-authored merges are rejected;
9. local exact-commit tests are primary and browser/host-capable;
10. environment hygiene removes ambient credentials without falsely claiming a sandbox;
11. selective CI is exact-SHA, policy/risk/cost routed, visible, and non-authoritative;
12. accepted merge graph/tree/actor and immutable Proposal record are verified read-only;
13. changed accepted trees are validated in a fresh managed clone; equivalent trees reuse exact sealed
   proof through a typed receipt;
14. an authorized human merge plus complete exact green evidence creates a completion receipt
   automatically; only modeled exceptions require protected confirmation;
15. every partial external effect has an idempotent reconciliation or typed attention path;
16. obsolete Integration, user-created-PR, no-Git-agent, and mandatory-VM surfaces are deleted;
17. focused, domain, end-to-end, and structural safety tests pass.

## 23. Recommendation, Confidence, and Limits

**Recommendation:** adopt this design as the new planning authority and challenge it independently
before implementation planning. Preserve exact identity, receipt, CAS, and completion strengths from
the prior design while replacing its disproportionate capability restrictions with ownership/effect
boundaries.

**Confidence:** high in the product direction and core safety boundary; medium in provider permission
containment because GitHub bundles PR creation and merge permission, making application surface,
repository rules, and accepted-actor verification jointly necessary; medium in exact CI policy details
until current repository workflows and billing preferences are inventoried during planning.

**Limits:** this design prevents Delivery from intentionally exposing dangerous operations and catches
accidental/stale effects at its boundaries. It is not an OS sandbox against malicious repository code
or a compromised unrestricted host process. That stronger threat model would require a separate,
explicit product decision rather than silently shaping the normal developer workflow.
