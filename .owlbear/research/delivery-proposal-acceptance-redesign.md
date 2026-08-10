# Delivery Proposal and Acceptance Redesign

> **Status:** Superseded for product direction by
> `delivery-change-worktree-authority.md`. Retained as the reviewed record of the rejected
> user-created-PR, no-Git-agent, and mandatory-VM alternative.

> **Owning request:** User-directed redesign following the destructive Integration incident; no
> matching Delivery change exists because this document defines the replacement Delivery model
> **Date:** 2026-08-10
> **Question:** How should OwlBear replace direct Integration with a safe, exact, user-overseen
> proposal and acceptance lifecycle while preserving coherent planning, execution, proof, recovery,
> history, Cockpit, and optional future cloud dispatch?

## 1. Status and Decision Markers

This is a proposed canonical redesign, not a description of current behavior. It deliberately ignores
backward compatibility and migration compatibility. The implementation may delete current schemas,
commands, persisted state, tests, and terminology where they conflict with this design.

Every material statement uses one of these markers:

| Marker | Meaning |
|---|---|
| **[LOCKED]** | Must be delivered exactly as described. Changing it requires revising and re-challenging this design before implementation continues. |
| **[REQUIRED]** | The observable guarantee is mandatory; implementation details may change if the guarantee remains demonstrably equivalent. |
| **[DIRECTION]** | Preferred architecture or sequencing, but implementation evidence may justify a better route without reopening the whole design. |
| **[DEFERRED]** | Intentionally outside the first coherent redesign. The contract may reserve space for it, but no speculative implementation is required. |
| **[REJECTED]** | Explicitly excluded because it violates the authority, safety, or proportionality model. |

The distinction is important: **[LOCKED]** and **[REQUIRED]** define the system that must come back
together after the break. **[DIRECTION]** items guide implementation but are not promises of exact
internal structure.

## 2. Executive Decision

**[LOCKED] OwlBear Delivery ends automated work by producing one immutable, verified proposal for one
Change. No automated OwlBear Delivery actor updates the configured target ref or mutates a user-owned
worktree.**

**[LOCKED] A user-owned acceptance action is the only event allowed to place the proposal into the
target. For the first implementation, acceptance evidence consists of a human merge of a GitHub pull
request plus explicit local user confirmation bound to the observed Proposal and target commit.**

**[LOCKED] Pull-request creation is publication, not acceptance and not completion. A Change becomes
completed only after OwlBear observes the accepted target commit and verifies that the exact sealed
proposal was accepted under the supported Git graph contract.**

**[LOCKED] The Change remains the specification, atomic acceptance, and completion unit. Outcomes are
promises within that Change. Tasks are replannable execution details. GitHub objects do not replace
those local typed entities.**

The resulting high-level lifecycle is:

```text
design -> active delivery -> proposal preparation -> sealed
   -> awaiting PR creation -> awaiting acceptance -> acceptance verification -> acceptance proof
   -> awaiting confirmation -> completed

sealed -> sealed-unpublishable
awaiting PR creation / acceptance -> publication attention -> proposal preparation / closed-unverified
awaiting acceptance -> rejection decision pending -> active delivery / proposal preparation
acceptance verification / proof -> acceptance attention -> closed-unverified / remediation
proof-profile-changed attention -- protected exact authorization --> acceptance proof
target-preexisting-failure -- protected exact authorization --> awaiting confirmation
rejection decision pending -> deferred / abandoned / active delivery / proposal preparation
sealed-unpublishable -- protected preflight retry or supersession --> sealed / proposal preparation
deferred -- protected resume --> named active delivery / proposal preparation stage
awaiting confirmation -- decline --> acceptance attention
```

This is not “replace `git update-ref` with create-PR.” It replaces the authority model, terminal
states, history model, Git ownership boundary, tools, Cockpit actions, MCP contracts, and recovery
semantics together.

## 3. Goals and Non-Goals

### 3.1 Goals

1. **[LOCKED] Eliminate the incident class structurally inside Delivery.** No Delivery application,
   assigned agent tool, bounded mutation service, proof subprocess, or publication credential can
   write the target ref or mutate a user checkout. A general-purpose user chat outside Delivery acts
   with the user's own workstation authority and is not falsely claimed to be contained by Delivery.
2. **[LOCKED] Preserve exact identity.** The authority, reviewed commits, proof, proposal commit,
   published PR head, and accepted target commit remain cryptographically bound.
3. **[LOCKED] Preserve local correction freedom before publication.** Intermediate commits and
   managed change refs are local, private, and rewritable until sealing.
4. **[REQUIRED] Make failure and re-entry explicit.** Every external or local failure has a typed,
   resumable state and a single owner.
5. **[REQUIRED] Keep one source of truth for Delivery semantics.** GitHub contributes acceptance facts;
   it does not become a mutable copy of Change, Outcome, or Task authority.
6. **[REQUIRED] Restore the whole product.** CLI/MCP, Cockpit, orchestration, completed history,
   cleanup, recovery, tests, and documentation must agree with the new lifecycle before cutover.
7. **[DIRECTION] Leave a narrow future path for cloud execution without importing a second control
   plane into OwlBear.**

### 3.2 Non-Goals

1. **[REJECTED] Backward compatibility** for current Delivery state, Integration APIs, persisted
   runtime schemas, completed-history packages, or MCP tool names.
2. **[REJECTED] A GitHub-native mirror** of every Change, Outcome, Task, claim, or attempt.
3. **[REJECTED] Automated merge**, whether through an MCP merge tool, `gh pr merge`, GitHub API,
   direct push, local CAS, or a hidden fallback.
4. **[REJECTED] Preservation of direct local Integration** as an optional or emergency path.
5. **[REJECTED] Importing Turbo Spec source, schemas, prompts, or text.** The supplied archive has no
   license grant. Its ideas may inform an independent implementation.
6. **[DEFERRED] General cloud worker execution, GitHub Projects, non-GitHub publication adapters,
   merge queues, squash/rebase acceptance, and arbitrary evaluator plugins.**

## 4. Evidence and Constraints

| Source | Material evidence | Limit |
|---|---|---|
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | Current atomic publication updates the target ref and refreshes a checked-out target through `git reset --hard`; target mutation and checkout mutation share one owner | Static analysis and incident evidence; this document does not preserve that design |
| [`delivery_runtime.py`](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) | Current completion is coupled to `DeliveryIntegrationCompletion`; outcomes reach `COMPLETED` before Integration completes | Current schema is evidence of affected contracts, not future authority |
| [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | Current application assembles product and completed package, publishes through one target CAS, then records completion | Call sites must be replaced together |
| [`completed_history.py`](../../serve/delivery/src/owlbear_delivery/completed_history.py) | Current history assumes completed packages already exist in configured target history | Cannot survive unchanged when completion occurs after external acceptance |
| [Turbo Spec 0.37.0 assessment](turbo-spec-0.37.0-assessment.md) | Typed stage outcomes, deterministic gates, bounded retries, checkpoints, credential isolation, and structured reports are useful; its GitHub control plane should not replace OwlBear | Static inspection only; no source execution or license grant |
| User-supplied Turbo Spec 0.37.0 archive | Actual source confirms typed `StageResult`, bounded jump/retry, Kahn dependency validation, resumable sessions, fail-closed gates, credential scrubbing, and sentinel-based idempotent reporting | Archive is temporary evidence and has no established upstream URL or reuse license |

The offline argument is intentionally absent. Local authority is justified by type integrity,
transaction boundaries, correction freedom, and avoiding cross-store partial authority, not by a
claim that LLM-assisted work is offline.

## 5. Canonical Vocabulary

| Term | Definition |
|---|---|
| **Change** | The complete user-approved promise set and the only atomic acceptance unit. |
| **Outcome** | A user-visible promise within a Change. It may depend on other Outcomes but is not independently accepted. |
| **Task** | Replannable executable authority that produces one bounded reviewed result for an Outcome. |
| **Managed change ref** | OwlBear-owned local Git ref containing mutable, pre-publication work. It is never a user branch or target ref. |
| **Proposal** | An immutable exact commit plus authority and proof bindings offered for acceptance. |
| **Seal** | The irreversible local transition that freezes a proposal identity. It does not publish anything. |
| **Exposure** | Create-only remote proposal/record refs plus rendered PR intent; no PR write occurs. |
| **Publication** | Read-only binding of one exact user-created GitHub PR to an Exposure. |
| **Publication slot** | Per-target ordering projection that permits one current eligibility epoch to expose or await resolution. |
| **Eligibility epoch** | One monotone request for a Change to enter the publication slot; skipped epochs never reactivate. |
| **Acceptance** | A user-owned action that places a proposal into the configured target, initially a human PR merge. |
| **Acceptance observation** | Read-only evidence that an external acceptance action occurred. |
| **Acceptance verification** | Deterministic proof that the accepted target commit corresponds to the exact sealed proposal under a supported merge contract. |
| **Completion receipt** | Immutable local record binding Change, Proposal, acceptance evidence, and accepted target commit after verification. |
| **Publication attention** | Typed fail-closed state before any external merge fact; it permits correction or terminal forensic closure. |
| **Acceptance attention** | Typed fail-closed state when an external action occurred but cannot be verified as exact completion. |
| **Closed-unaccepted Proposal** | Terminal Proposal whose Change closed unverified without an external merge fact. |
| **Accepted-unconfirmed Proposal** | Terminal Proposal whose external merge occurred but whose Change closed without completion. |

**[LOCKED] “Integration” is removed as a lifecycle stage, worker role, API family, and conceptual
permission.** The term may remain only in incident history or migration notes.

## 6. Authority Model

### 6.1 Local Authority

**[LOCKED] OwlBear locally owns and validates:**

- Change identity and design package;
- commitment and Outcome definitions;
- task plans, dependencies, constraints, and proof boundaries;
- claims, attempts, custody, retries, returns, blocks, and requests;
- reviewed task-result commits and assembly result;
- proposal identity, exact source/base commits, manifest, and proof bundle;
- proposal supersession and local lifecycle state;
- completion receipts and typed acceptance attentions.

Local records use OwlBear IDs as primary keys. External identifiers are nullable references and never
participate in identity equality.

### 6.2 GitHub Authority

**[LOCKED] GitHub owns only facts that occur on GitHub:**

- repository and PR identity;
- exact published head observed by GitHub;
- PR open, closed, or merged state;
- review decisions and check conclusions;
- target commit produced by a merge;
- timestamps and actor identities reported by GitHub.

These facts are observations. A PR body edit cannot alter Change authority, tasks, proposal identity,
proof, or lifecycle mechanically.

### 6.3 Synchronization Direction

**[LOCKED] There is no bidirectional semantic synchronization.**

```text
OwlBear authority --render--> GitHub PR
GitHub acceptance facts --observe--> OwlBear verification
```

OwlBear renders the exact user-facing PR title/body and a GitHub compare URL, but the user owns the
GitHub PR-creation action. PR text remains presentation only: OwlBear binds publication by typed
repository, base, head branch, and head commit fields and never imports PR prose into local authority.

## 7. Safety and Capability Invariants

These are the irreducible incident-prevention rules.

1. **[LOCKED] No OwlBear-initiated Delivery actor may cause a write to the configured target ref**,
   locally or remotely. The invariant is defined by effect, not by which module or command performs
   it. Prohibited mechanisms include raw Git, Git libraries, shell indirection, provider APIs, MCP
   tools, hooks, proof commands, and subprocesses.
2. **[LOCKED] No OwlBear-initiated Delivery actor may mutate any path, index, `HEAD`, stash, config,
   hook, local branch, or untracked content in a user-owned worktree.**
3. **[LOCKED] Worktree cleanliness is not authorization.** A clean user checkout remains outside
   Delivery custody.
4. **[LOCKED] Delivery agents receive no general-purpose terminal, raw Git tool, raw GitHub write
   tool, or unrestricted filesystem mutation tool.** They mutate only through bounded application
   operations whose inputs are typed, whose roots and ref destinations are allowlisted, and whose
   effects are independently checked. Proof commands execute below the agent boundary in the
   restricted proof runner described in §17.3.
5. **[LOCKED] Every writable managed worktree lives in the reserved, gitignored
   `.owlbear/worktrees/` subtree and is validated before mutation or cleanup.** This subtree is
   OwlBear-owned state, not user project content, only after setup proves it is ignored and contains no
   unrecognized entries. Mutation requires an active task, proposal, or post-acceptance-proof claim.
   Cleanup requires a durable completion,
   withdrawal, or supersession receipt and does not require an active claim.
6. **[LOCKED] Publication may create exactly two remote refs: one proposal branch at the exact sealed
   proposal commit and one sibling record branch at the exact publication-record commit.** It may never push
   the managed mutable ref or an intermediate commit stream.
7. **[LOCKED] Remote proposal and record refs are create-only and permanently retained.** The preferred
   and only publication primitive is `git push --force-with-lease=<dest>:`; the empty-expect lease is
   client defense in depth. Server-side namespace
   rulesets permit creation but deny subsequent update, force-update, and deletion. Corrections use a
   new candidate ID and new refs.
8. **[LOCKED] Publisher capability is restricted by destination, operation, and expected old value.**
   The target ruleset has no publisher bypass. A proposal-namespace ruleset permits creation but
   rejects update, force-update, and deletion without bypass. Both are revalidated before publication.
   The acceptance observer is read-only with respect to local Git refs, remote Git refs, worktrees,
   and GitHub mutations.
9. **[REQUIRED] Cleanup is fail-closed.** Uncertain ownership, a dirty managed worktree, ref mismatch,
   or retained recovery evidence prevents deletion and raises typed attention.
10. **[LOCKED] Every Git ref write performed by Delivery passes one bounded ref service.** Its only
    local destinations are `refs/heads/owlbear/**`, `refs/owlbear/**`, and the exact configured remote
   target-tracking ref during an explicit non-pruning `git fetch --no-write-fetch-head`, plus
   per-worktree `HEAD`/`ORIG_HEAD` only inside a validated managed worktree under
   `.owlbear/worktrees/`. One
   user-authorized forced rebaseline is admitted after durable old/new-tip and divergence evidence.
   These pseudo-refs are forbidden in the root checkout and every user-owned worktree. The local target
   branch is never a base source or write destination.
11. **[REQUIRED] Setup installs repository hooks as defense in depth.** Ref policy has four classes:
   immutable create-only/delete-denied `refs/owlbear/proposals/**`,
   `refs/owlbear/observations/**`; mutable-under-claim
   `refs/heads/owlbear/changes/**` and `refs/owlbear/recovery/**`; managed-worktree pseudo-refs allowed
   only with exact custody evidence; and denied-for-OwlBear every other
   destination, including the target. The `reference-transaction` hook enforces immutable OwlBear
   local namespaces regardless of caller and is fail-open, bounded, and nonblocking for every ref
   outside OwlBear namespaces. A `pre-push` hook always rejects a delete or non-create update inside
   `refs/heads/owlbear/**` unless it is the exact admitted proposal/record create. For an invocation
   marked by the Delivery ref service using a dedicated non-secret environment sentinel plus matching
   active operation/claim record, it additionally rejects every destination outside exact
   `refs/heads/owlbear/proposals/**` or `refs/heads/owlbear/records/**`, including the target. Unmarked
   ordinary human pushes outside OwlBear namespaces are untouched. The Delivery marker is advisory;
   remote immutability and target protection are authoritative only through server rulesets.
   Publication preflight verifies hook content digests. Hooks supplement
   capability confinement and do not prohibit ordinary human target updates outside Delivery.
12. **[REQUIRED] Repository-wide static, configuration, and behavioral tests prove that target and
   user-worktree mutation effects are unreachable from every Delivery role, including indirect shell
   and proof-code attempts.**

### 7.1 Threat Actors and Trust Boundary

| Actor | Trust and capability decision |
|---|---|
| Delivery application code | Trusted only through typed bounded interfaces; no raw target or root-worktree primitive exists |
| Delivery agent | Untrusted planner of actions; no terminal/raw Git/raw provider capability and no path outside assigned managed surfaces |
| Repository-authored proof code | Untrusted executable input; isolated filesystem, credential-free environment, bounded resources, and no provider write channel |
| Human user | Owns acceptance and may use their workstation outside Delivery; concurrent actions are detected through exact identity checks |
| Second OwlBear process | Concurrent adversary for correctness; operation IDs, compare-and-swap records, and provider reconciliation prevent duplicate effects |
| GitHub/provider | Authoritative for typed external facts, untrusted for free text, availability, ordering, and policy stability |

**[LOCKED] Only typed provider fields participate in automation.** PR bodies, comments, check logs,
review text, and other free text are stored as redacted evidence and never enter agent instruction
context or derive a lifecycle transition without explicit user action.

**[LOCKED] User attestation is an informed-intent record and an anti-automation control, not a defense
against an arbitrary process already running with the user's full workstation authority.** That outer
trust boundary belongs to the user and operating system. `Origin`/`Host` validation and the one-time
nonce are browser-CSRF controls only; process isolation prevents Delivery agents, services, and
repository-authored proof code from reaching the confirmation capability.

### 7.2 Managed Worktree Identity and Cleanup

**[LOCKED] A managed worktree is writable or removable only while all applicable predicates hold:**

1. `git worktree list --porcelain` binds the recorded path to this repository and expected `HEAD`;
2. its Git administrative directory is the expected entry below the repository common Git directory;
3. its canonical real path equals the recorded path, its device/inode identity matches the ownership
   record, and no traversed component is a symbolic link;
4. the ownership record is stored in Delivery state outside the managed worktree and binds repository,
   Change, worktree, ref, expected commit, and active claim or cleanup receipt;
5. mutation stays within the task-maintained surface allowlist;
6. cleanup sees an exact clean worktree at the recorded head and no retained recovery evidence.

Deletion is directory-descriptor-relative to a validated managed root. It never uses `worktree remove
--force`, broad `rmtree`, ignored errors, or a path obtained solely from mutable state inside the
worktree.

VS Code editing and search continue to reach managed worktrees because they remain below the workspace
root. Claim-aware chat hooks confine editing tools to the exact active worktree and maintained
surfaces. The authoritative event/receipt store and proof evidence remain untracked OwlBear state and
are excluded from project-content assertions.

### 7.3 Committed and Machine-Local State

**[LOCKED] The state split is explicit:**

- committed inside the Proposal/target tree: admitted design authority and the Proposal manifest;
- untracked, machine-local, and gitignored: authoritative event streams, publications, observations,
  confirmations, completion receipts, attentions, proof evidence, claims, attempts, coordination,
  managed worktrees, and derived projections.

Runtime state never enters a Proposal tree. A second clone has no Delivery history until state import
or reindex; this is an accepted consequence, not compatibility debt.

### 7.4 Git Namespace and Target Identity

**[LOCKED] `base_target_ref` means exactly the remote-tracking ref for the configured remote target,
`refs/remotes/<remote>/<target>`.** OwlBear never selects a base from the local target branch. A base
refresh uses `git fetch --no-write-fetch-head` with one explicit non-pruning refspec that updates only
that remote-tracking ref. Delivery never writes root-checkout `FETCH_HEAD`.

**[DIRECTION] Use these local namespaces:**

```text
refs/heads/owlbear/changes/<change-id>
refs/owlbear/proposals/<change-id>/<proposal-id>
refs/owlbear/recovery/<change-id>/<attempt-id>
refs/owlbear/observations/<change-id>/<observation-id>
refs/heads/owlbear/dispatch/<change-id>/<task-id>/<dispatch-id>   # deferred cloud use
```

**[DIRECTION] Publish a sealed commit without creating a local user branch:**

```text
<proposal-commit>:refs/heads/owlbear/proposals/<change-id>/<proposal-id>
```

The exact names may change, but namespace separation, immutability, and absence of local target writes
are mandatory.

## 8. Lifecycle Model

### 8.1 Outcome Lifecycle

**[LOCKED] Outcome completion no longer means Change completion.** Outcome states describe internal
delivery readiness only:

```text
design -> planning -> implementation -> assembly? -> verified
```

`verified` means every required task result and optional assembly result is exact, independently
reviewed, and ready for proposal construction. Rename current Outcome `COMPLETED` to `VERIFIED` so the
word “completed” has one meaning at Change level.

### 8.2 Change Lifecycle

**[LOCKED] The canonical Change states are:**

| State | Entry condition | Exit owner |
|---|---|---|
| `design` | Authored design exists but is not admitted | Design workflow/user |
| `active-delivery` | Design is admitted and at least one Outcome is not verified | Delivery workers |
| `proposal-preparation` | Every Outcome is verified and no active proposal exists | Proposal builder |
| `sealed` | Exact proposal record and commit are persisted; no remote exposure exists | Publisher |
| `sealed-unpublishable` | Proposal is sealed but repository prerequisites cannot support verified publication | Protected preflight retry only under sealed policy equality; otherwise supersede |
| `awaiting-pr-creation` | Immutable proposal ref is exposed and exact PR content/compare URL is rendered; no PR is yet bound | User creates the PR in GitHub; observer binds it |
| `awaiting-acceptance` | Publication receipt binds the proposal to an open PR at the exact head | User/GitHub observation |
| `acceptance-verification` | GitHub reports merged; exact graph landing is not yet verified | Acceptance observer |
| `acceptance-proof` | Exact graph is verified; isolated guest proof on the accepted target commit is active | Post-acceptance proof service |
| `awaiting-confirmation` | Exact graph is verified and proof passed, or immutable preexisting-baseline authorization binds exact evidence; all is presented for user attestation | User through local Cockpit only |
| `completed` | Immutable completion receipt binds verified landing and user attestation | Terminal |
| `rejection-decision-pending` | Published PR closed unmerged; user disposition is required | User through local Cockpit only |
| `deferred` | User parks the Change with no active work or claim | User through local Cockpit may resume to named prior stage |
| `abandoned` | User terminates an unaccepted Change and preserves audit/recovery evidence | Terminal |
| `publication-attention` | Publication or pre-merge PR binding cannot be proven exact or safe | User/remediation workflow |
| `acceptance-attention` | External acceptance cannot be proven exact, supported, or sound on the accepted commit | User/remediation workflow |
| `closed-unverified` | User explicitly closes a publication or acceptance attention without forging completion | Terminal |

`discarded`, `rejected`, `withdrawn`, `superseded`, `closed-unaccepted`, and
`accepted-unconfirmed` are Proposal terminal states, not terminal Change states. Rejection,
withdrawal, and supersession return the Change to `active-delivery` or `proposal-preparation` with
explicit successor context. `closed-unaccepted` records forensic closure without an external merge;
`accepted-unconfirmed` records that accepted content remains on target after the Change is closed
without a completion claim.

Every nonterminal row has exactly one mechanical owner. The acceptance observer owns external state
observation and graph verification; the post-acceptance proof service owns the bounded proof claim;
the user owns acceptance itself and every transition out of `acceptance-attention`.
`closed-unverified` preserves that accepted content may exist on target while exact OwlBear completion
was never proven.

### 8.3 Proposal Lifecycle

**[LOCKED] Proposal state is event-derived and monotonic:**

```text
prepared  -> sealed | discarded | superseded
sealed    -> exposed | withdrawn | superseded
exposed   -> published | withdrawn | superseded | closed-unaccepted
published -> accepted | rejected | withdrawn | superseded | closed-unaccepted
accepted  -> verified-complete | accepted-unconfirmed
```

- `discarded` records a candidate abandoned before sealing and has no Git or provider effect.
- `sealed` is immutable but still private.
- `exposed` binds the exact immutable remote proposal ref but no PR identity.
- `published` binds one exact proposal commit to one user-created external PR identity and observed PR head.
- `accepted` records the external merge fact without claiming exactness.
- `verified-complete` exists only with a completion receipt.
- `withdrawn` is legal from `sealed`, `exposed`, or `published`; from `published` it requires an
   unmerged observation at CAS time. Delivery preserves immutable refs and never closes or mutates the
   user-owned PR.
- `closed-unaccepted` exists only with a terminal `closed-unverified` Change event and no external
   merge fact; it never claims acceptance.
- `accepted-unconfirmed` exists only with a terminal `closed-unverified` Change event after the
   external merge fact; it never claims verification or completion.
- A published proposal can never return to mutable state.

### 8.4 Attempts, Retries, and Pauses

**[REQUIRED] Every operation has a stable operation ID and bounded attempt counter.** Repeating a
request with the same ID is idempotent or returns the existing result.

**[REQUIRED] Retry is allowed only when the previous attempt produced no irreversible external side
effect, or after read-only reconciliation proves the side effect already matches the requested
identity.** This applies especially to push and PR creation.

**[LOCKED] A post-acceptance-proof claim has a configured bounded lease and heartbeat.** Lease expiry
ends mutation authority but does not change `acceptance-proof`. Recovery CASes the expired claim,
destroys the guest disk/VM and revalidates/removes bounded host transfer staging under the exclusive
cleanup lease, acquires a successor
claim, and reruns proof idempotently against the same immutable accepted commit and authorized profile.
Proof-result persistence CASes on the exact current claim ID; a superseded claim's eventual result is
discarded as evidence-only and cannot advance lifecycle state. Cockpit detects/surfaces expired claims
and offers `recover_acceptance_proof` as the single safe next action.

**[DIRECTION] Adopt Turbo’s useful distinction between typed outcomes:** success, retryable failure,
return to prior stage, escalation, and awaiting human action. Do not adopt generic free-form jump
targets; OwlBear’s existing typed transitions remain the authority.

## 9. Canonical Data Contracts

The exact field spelling is **[DIRECTION]**. The identities and bindings below are **[LOCKED]**.

### 9.1 `DeliveryProposalCandidate`

**[LOCKED] Proposal identity is two-stage so no object contains its own digest.**

```text
candidate_id                sha256 of the canonical candidate payload below
change_id
package_id
authority_digest
runtime_digest
result_history_digest
base_target_ref
base_target_commit
reviewed_change_commit
proof_bundle_digest
proof_profile_digest
merge_contract_version      exact versioned Git/config/attribute contract
acceptance_actor_allowlist_digest   immutable numeric user IDs plus node IDs; login excluded
policy_blocking_mode
effective_rule_snapshot_digest
bypass_actors_digest
manifest_schema_version
```

`candidate_id` is computed over canonical candidate payload bytes with the `candidate_id` field
omitted. `proposal_id` is computed over canonical sealed Proposal payload bytes with the `proposal_id`
field omitted. No identity payload includes its own digest field.

The candidate payload contains only values knowable before the proposal tree exists. It excludes
proof-bundle identity, timestamps, Git objects created from the manifest, provider object identifiers
(PR number, URL, node IDs, observed head), and all
future acceptance data. `proof_bundle_digest` is a sealed-Proposal field only; it is never part of the
candidate payload or manifest.

### 9.2 Authoritative Event Stream

**[LOCKED] One append-only stream per Change is the sole lifecycle commit authority.**

- each event carries `change_id`, monotonic sequence, event kind, canonical payload, prior-event
   digest, and event digest;
- append is compare-and-swap on the exact expected sequence and prior-event digest;
- every Change, Outcome, Proposal, publication, observation, attention, and completion state is a
   deterministic fold over that stream;
- projections, indexes, Cockpit views, and derived Git refs are rebuildable from the stream;
- one repository clone has exactly one configured authoritative Delivery state store;
- a second process shares that store and competes through stream CAS; a second independent store or
   restored clone is not a writer and must reconcile or be explicitly promoted by the user;
- cross-machine safety additionally checks the provider for any open OwlBear Proposal PR against the
   target before publication and fails closed on unknown competing authority.

### 9.3 `DeliveryProposal`

```text
proposal_id                 sha256 of canonical sealed proposal payload
candidate_id                stable pre-commit candidate identity
change_id                   stable OwlBear Change ID
package_id                  admitted design/contract package identity
authority_digest            canonical Change authority digest
runtime_digest              verified Outcome/task runtime digest
result_history_digest       exact reviewed result-history digest
base_target_ref             configured target ref name
base_target_commit          exact target commit used to build proposal
reviewed_change_commit      exact final managed Change commit
proposal_commit             exact immutable commit offered for acceptance
proposal_tree               exact Git tree of proposal_commit
manifest_path               canonical manifest path included in proposal tree
manifest_digest             canonical manifest digest
proof_bundle_digest         canonical verification evidence digest
proof_profile_digest        exact proof profile resolved from the proposal tree
merge_contract_version      sealed merge/Git contract used for verification
acceptance_actor_allowlist_digest   immutable numeric user IDs plus node IDs; login excluded
policy_blocking_mode
effective_rule_snapshot_digest
bypass_actors_digest
proposal_review_id          independent exact-commit review identity
proposal_reviewer_id        reviewer identity distinct from proposal builder
reviewed_proposal_commit    must equal proposal_commit
created_at                  timestamp, always excluded from content identity
schema_version              exact supported proposal schema
```

**[LOCKED] `proposal_id` binds every semantic and Git identity required to decide exact acceptance.**
It is the digest of a canonical payload that excludes timestamps and all provider identifiers. No
field that can change after sealing is part of a Proposal.

### 9.4 Proposal Manifest

**[LOCKED] The proposal commit contains a canonical machine-readable manifest that never references
its own containing Git objects.** It contains the candidate payload, including its
`manifest_schema_version`, and no duplicate schema field. It
must not contain `proposal_id`, `proposal_commit`, `proposal_tree`, `manifest_digest`, a changed-entry
digest, any provider/PR identifier, any timestamp, or any accepted target commit.

**[DIRECTION] Store it at:**

```text
.owlbear/proposals/<change-id>/<candidate-id>/manifest.json
```

After the manifest and deterministic proposal commit exist, `proposal_id` binds `candidate_id`,
manifest path and digest, proposal tree, and proposal commit without creating a hash cycle.

### 9.5 `ProposalExposureReceipt` and `ProposalPublicationReceipt`

```text
exposure_id                  digest of proposal_id, repository identity, target ref,
                             remote branch, exposed head, and rendered intent digest
operation_id
proposal_id
repository_identity          immutable owner/repository identity
target_ref
remote_branch
exposed_head                 exact remote proposal commit
renderer_schema_version
rendered_intent_digest       title/body/base/head/compare-URL intent including renderer schema
record_branch                immutable exposure-record branch
record_commit                deterministic commit containing Proposal plus typed exposure binding
record_tree
record_digest
created_at
```

`exposure_id` includes `renderer_schema_version` and excludes record branch/commit/tree/digest,
timestamp, and operation ID. The exposure
record commit is byte-deterministic: canonical serialization, fixed author/committer/message/encoding,
parentlessness, timestamp derived from `proposal_commit`, and signing disabled. Retry reproduces the
exact record commit.

```text
publication_id               digest of exposure_id, external_number, and published_head
operation_id
exposure_id
proposal_id
provider                     initially github
repository_identity          immutable owner/repository identity
external_number              PR number
external_url
target_ref
published_head               exact observed GitHub PR head
remote_branch
created_at
```

`publication_id` excludes timestamps, operation ID, and receipt metadata. It binds the exact
user-created PR observed by the read-only provider role to the immutable exposure receipt.

**[LOCKED] Exposure succeeds only after remote proposal and record read-back. Publication succeeds
only when read-only observation sees the same proposal commit as the user-created PR head and exact
base/head repository identities.** Network success, prose identity, or a PR number alone is insufficient.

### 9.6 `AcceptanceObservation`

```text
observation_id
publication_id
proposal_id
external_state               open, closed, merged
observed_head
target_ref
target_commit                nullable until merged
derived_merge_topology       computed from the accepted Git commit graph
review_state
check_summary
actor
observed_at
raw_evidence_digest
provider_cursor              provider updated-at plus ETag/node identity
```

Observations are append-only evidence. A newer observation supersedes current display state but does
not rewrite prior evidence.

Observation order uses the provider cursor first and local receipt sequence second. A stale provider
read cannot regress a merged/closed state to open.

Provider `updated_at` is only a reconciliation hint and is not assumed to advance for every
state-relevant field. Monotonicity comes from rejecting any transition from observed merged/closed
back to open and retaining every observation by local receipt sequence.

Provider-reported merge method, when present, is advisory raw evidence only. It never participates in
acceptance verification.

### 9.7 `DeliveryCompletionReceipt`

```text
completion_id                digest of canonical verified completion payload
change_id
proposal_id
publication_id
acceptance_observation_id
accepted_target_ref
accepted_target_commit
accepted_target_tree
accepted_by_actor
accepted_by_actor_type
confirmation_id
proposal_commit
proposal_tree
merge_contract_version
verification_evidence_digest
proof_profile_digest_used
profile_authorization_id     nullable only when used profile equals sealed profile
baseline_authorization_id    nullable unless preexisting baseline failure is authorized
completed_at
```

**[LOCKED] Completion binds both sides of the boundary: the exact sealed proposal and the exact target
commit introduced by user acceptance.**

`completion_id` is derived only from `change_id`, `proposal_id`, accepted target ref/commit/tree,
proposal commit/tree, and merge-contract version. Observation ID, actor, timestamp, verification
evidence digest, confirmation ID, proof profile used, and profile authorization ID are non-identity
receipt fields; baseline authorization ID is also non-identity. Retry therefore
recomputes the same completion identity.

### 9.8 `UserAcceptanceConfirmation`

```text
confirmation_id             digest excluding confirmed_at
change_id
proposal_id
publication_id
observation_id
accepted_target_commit
merge_actor
confirmed_at                non-identity field
```

The confirmation is an informed acceptance attestation, not proof that the merge mechanism was human-
initiated. Cockpit presents the Proposal commit, accepted target commit, merge actor, and topology
verdict before the user confirms or declines.

### 9.9 `PublicationAttention` and `AcceptanceAttention`

Every attention binds immutable `merge_fact_observed` at entry. False means `publication-attention`;
true means `acceptance-attention`. At minimum, typed codes cover:

- `publication-identity-collision`;
- `publication-head-mismatch`;
- `proposal-branch-mutated`;
- `pr-target-mismatch`;
- `unsupported-merge-method`;
- `base-ancestry-broken`;
- `proposal-parent-missing`;
- `target-tree-mismatch`;
- `merge-recomputation-mismatch`;
- `merge-contract-divergence`;
- `merge-driver-mismatch`;
- `unsupported-merge-base-topology`;
- `proof-profile-changed`;
- `post-acceptance-proof-failed`;
- `target-preexisting-failure`;
- `baseline-inconclusive`;
- `manifest-missing-or-mutated`;
- `publication-record-missing-or-mismatched`;
- `required-check-identity-mismatch`;
- `accepted-target-unreachable`;
- `provider-evidence-unavailable`;
- `proof-isolation-unavailable`;
- `proof-runner-timeout`;
- `evidence-incomplete`;
- `acceptance-actor-unauthorized-or-missing`;
- `confirmation-capability-rejected`;
- `proposal-branch-deleted`;
- `policy-evidence-unavailable-or-bypassed`;
- `sealed-policy-configuration-drift`;
- `target-history-rewritten`;
- `publication-slot-inconsistent`;
- `competing-delivery-authority`.

Each attention names the exact retry condition, immutable evidence locators, and whether remediation
requires a successor Change because the target has already changed. A code that can arise in either
phase uses `merge_fact_observed`, not its name, to select legal transitions.

## 10. Proposal Construction and Sealing

### 10.1 Preconditions

**[LOCKED] Proposal preparation begins only when:**

1. every Outcome is `verified`;
2. no active claims remain;
3. all task results bind the current authority and task digests;
4. the managed Change ref equals the last independently reviewed boundary;
5. the managed worktree is exact and clean;
6. the remote target is fetched through the single explicit refspec and its exact commit is recorded;
7. no active sealed/published proposal exists for the Change;
8. the complete proof profile is resolved from the candidate result tree before commit creation and
   its canonical digest is known. The entire generated `.owlbear/proposals/**` subtree is excluded from
   profile discovery; seal explicitly resolves both candidate-result and final-proposal trees and
   requires identical discovered profile sets and canonical digests.

### 10.2 Construction

**[REQUIRED] Build the proposal in a new managed, disposable worktree or detached index owned solely by
the proposal attempt.** Do not build in the mutable Change worktree and never in the root checkout.

Construction performs:

1. exact base and reviewed Change commit resolution;
2. deterministic result-tree preparation against `base_target_commit`;
3. conflict detection without touching the target ref;
4. package/manifest generation inside the candidate tree;
5. canonical proposal commit creation with exactly one parent, `base_target_commit`, and the reviewed
   result tree;
6. focused and full proof on the exact proposal commit;
7. independent review of the exact proposal commit and proof summary;
8. canonical identity calculation and atomic local seal publication under `refs/owlbear/proposals/...`.

**[LOCKED] Proposal commit construction is byte-deterministic.** Author and committer identities,
message template, encoding, parent order, and timestamps are canonical; timestamps derive from the
reviewed Change commit; signing is disabled. The same candidate inputs therefore reproduce the same
manifest, tree, and proposal commit. Proposal identity is attempt-scoped because it also binds proof
and independent review identity; publication reads it from the sealed Proposal in `ProposalStore`.
Fresh-clone reindex later re-verifies it from the exposure-record branch.

The proof runner reads the proof profile from the exact proposal tree, not from the target or ambient
checkout. The sealed Proposal binds the profile digest, proof-bundle digest, independent review ID,
reviewer identity, and reviewed commit. Seal fails unless the review binds `proposal_commit` and the
reviewer is independent of the Proposal builder.

**[LOCKED] A conflict returns to controlled repair before sealing.** There is no post-seal conflict
repair, no mutation of the proposal branch, and no hidden merge resolution during acceptance.

### 10.3 Seal Transaction

**[LOCKED] Sealing has exactly one commit point: durable compare-and-swap publication of the canonical
Proposal record and its lifecycle event in the authoritative Delivery event store.** Proposal Git
objects, the immutable local Proposal ref, and the proof bundle are content-addressed derivations.
They are created before the commit point when possible and recreated idempotently from the committed
record afterward. A crash before the commit point leaves inert unreferenced objects; a crash after it
leaves a sealed Proposal whose missing derivations are replayed. There is no partial-seal lifecycle
state and no claim of atomicity across Git and filesystem media.

**[REQUIRED] Sealing does not push, create a PR, alter a target, or clean the mutable Change workspace.**

## 11. GitHub Publication Contract

### 11.0 Required Repository and Client Configuration

**[LOCKED] The first coherent redesign supports only repositories with:**

- a configured GitHub remote name and immutable owner/repository identity;
- runtime GitHub App material consisting of App ID, installation ID, and private key stored in macOS
   Keychain; OwlBear mints a short-lived role token per operation. Publisher requests exactly
   `contents: write`, `metadata: read`, `administration: read`; observer requests
   exactly `contents: read`, `pull_requests: read`, `checks: read`, `metadata: read`,
   `administration: read`. `pull_requests: write` and `administration: write` are prohibited for every
   runtime role;
- a separate user-interactive setup credential with repository administration sufficient to install
   required target/proposal/record rulesets; when enumeration finds organization- or enterprise-sourced
   rulesets, setup additionally requires explicitly configured org/enterprise administration read for
   those sources. These credentials are never persisted in Delivery configuration or made available to
   any Delivery runtime process;
- no direct target-writing workflow, app, bot, deploy key, or bypass identity;
- Git hooks and VS Code chat hooks installed and verified by setup.

Private repositories require a GitHub plan that supports rulesets. Setup checks this prerequisite and
routes unsupported repositories to `sealed-unpublishable` rather than weakening enforcement.

Publication and observation are application code, not agent/MCP-mediated GitHub calls. Agents never
receive the provider credential. Configuration records remote name, provider repository identity,
credential key reference, App/installation IDs, target branch, required ruleset identities, a
user-attested allowlist of authorized immutable numeric user IDs plus node IDs, and policy-blocking
mode. Login is advisory display only. The publication App/installation identity is forbidden
from that allowlist. The private key and minted tokens never enter files, Delivery state, logs, event
streams, or subprocess environments. Missing or
insufficient configuration is a setup/preflight error with exact remediation; Delivery cannot enter
proposal publication until it passes.

Local-only and non-GitHub completion are explicitly unsupported until the deferred local acceptance
surface is separately designed. This is a deliberate first-version product prerequisite, not an
offline argument. When prerequisites cannot be met, Delivery may seal the Proposal and terminate at
`sealed-unpublishable`, exposing the exact commit and a manual export procedure but creating no
completion receipt. Setup and product documentation state this limitation before work begins.

**[LOCKED] The exact supported Git version for merge-contract v1 is Git 2.55.0, pinned in setup,
recorded in the Proposal/receipt, and verified before publication and recomputation.** Merge
recomputation uses that exact version, canonical merge configuration, and stable attribute inputs.
Setup may install it at a dedicated absolute path outside package-manager replacement, records the
binary digest, and uses only that verified path for merge-contract operations.
Any mismatch fails closed with remediation to install the exact version. Moving versions requires a
new merge-contract version, renewed architecture challenge, and live-suite revalidation; old receipts
remain valid because their exact merge-contract version participates in `completion_id`.
The credential is read from its configured source at call time and is never persisted in Delivery
state, logs, proof evidence, event streams, or inherited subprocess environments.

### 11.1 Initial Supported Surface

**[LOCKED] The first acceptance surface is one GitHub PR per sealed Proposal, at most one active PR per
Change, and at most one Proposal in published/accepted-but-unverified states per configured target.** Other
Verified Changes queue at `proposal-preparation`. Each eligibility epoch appends exactly one ordering
request to a store-level publication-slot stream with its own CAS sequence. This stream orders work
but never commits lifecycle, grant, or release state. The slot-holding Change states are exactly
`sealed`, `awaiting-pr-creation`, `awaiting-acceptance`, `acceptance-verification`,
`acceptance-proof`, and a `publication-attention` or `acceptance-attention` entered before the Change
ever reached `awaiting-confirmation`. A request is eligible only when its Change fold is
`proposal-preparation` under exactly that request's current epoch and holding only when its Change fold
is slot-holding for that epoch. The holder is the lowest-sequence request that is eligible or holding.
Every other Change fold permanently skips the request, including `design`, `active-delivery`,
`proposal-preparation` under a later epoch, `deferred`, `abandoned`, `sealed-unpublishable`,
`rejection-decision-pending`, `awaiting-confirmation` or any later state, and every terminal state.
Classification is total over all Change states; `publication-slot-inconsistent` is reserved for an
unreadable Change stream or invalid event fold. Once skipped, that request can never become eligible
or holding again. First entry into `proposal-preparation` appends epoch 1. Every later re-entry into
eligibility appends a new higher-sequence request, including protected preflight retry, resume,
rejection revision, withdrawal/supersession successor, and remediation; `retry_publication_preflight`
appends that request as part of its Change transition. `defer_change`, `abandon_change`,
`discard_candidate`, rejection disposition, and supersession also append a
`publication-slot-request-withdrawn` audit event to the ordering stream, but occupancy correctness
does not depend on that append: the authoritative Change fold already excludes the request.
No cross-stream snapshot isolation is claimed or required. `PortfolioApplication` reads the ordering
stream at one fixed sequence, then reads each lower-sequence request's Change head. A lower request
observed as skipped is durably skipped; one observed as eligible or holding blocks publication. It
then CASes publication intent against the publishing Change head. An unreadable stream or invalid fold
raises `publication-slot-inconsistent`. Monotone skipping prevents a lower request from becoming
eligible behind an already-published higher request, and there is no separately committed
grant/release that can leak or double-grant a slot.
Other human/bot PRs may merge while one OwlBear
Proposal is open; acceptance verification recomputes the exact resulting tree against the actual
target parent rather than requiring exclusive target access. The single OwlBear slot is retained to
bound user attention, collision handling, and deterministic loss of publication eligibility, not for
merge correctness.

**[REQUIRED] Publication preflight validates exact typed rules/settings:**

- configured remote resolves to the expected GitHub repository;
- token permissions plus exact namespace rules prove create-only ref and read-only PR capability
   without a trial push;
- each token-mint response's typed `permissions` map exactly matches its role-specific allowlist and contains
   no `administration: write`; an opaque pre-minted token is unsupported;
- target branch equals the Proposal target;
- proposal branch does not already exist with another commit;
- the target ruleset has the exact closed rule-type set `pull_request`, `required_status_checks`,
   `deletion`, and `non_fast_forward`; `pull_request.parameters.allowed_merge_methods == ["merge"]`,
   `required_approving_review_count == <sealed configured integer >= 0>`,
   `dismiss_stale_reviews_on_push == <sealed configured boolean>`,
   `require_last_push_approval == <sealed configured boolean>`, and
   `required_review_thread_resolution == <sealed configured boolean>`; an approval count above zero
   is admitted only when setup attests at least one authorized reviewer identity disjoint from every
   configured PR-author/acceptance actor because GitHub rejects self-approval. Approval count zero
   requires `require_last_push_approval == false`. `require_code_owner_review == <sealed configured
   boolean>` with every other documented `pull_request` parameter present at its sealed configured
   value; direct-push prevention and merge-method restriction derive from the `pull_request` rule and
   do not require a nonzero approval count; and
   `required_status_checks` with each expected source App pinned and up-to-date disabled, plus
   `required_status_checks.parameters.strict_required_status_checks_policy == false`,
   `required_status_checks.parameters.do_not_enforce_on_create == false`, the closed parameter set
   `required_status_checks`, `strict_required_status_checks_policy`, and
   `do_not_enforce_on_create`, and each
   `required_status_checks.parameters.required_status_checks[]` binding exact `context` and
   `integration_id`; the array is nonempty; `enforcement == "active"`. It has no other rule type, including `creation`,
   `update`, `required_linear_history`, or `merge_queue`; setup-attested `bypass_actors == []`. Direct
   push prevention derives from `pull_request`, not `update`;
- target ruleset conditions are exactly `ref_name.include == ["refs/heads/<target>"]`, or
   `["~DEFAULT_BRANCH"]` only when the configured target is the default branch, with
   `ref_name.exclude == []`; effective branch rules expose the identical closed rule-type set;
- proposal/record namespace rulesets have exact `ref_name.include` patterns
   `refs/heads/owlbear/proposals/**` and `refs/heads/owlbear/records/**`, plus the
   exact closed rule-type set `update`, `deletion`, and `non_fast_forward`, with no other rule including
   `creation`, `required_signatures`, `file_path_restriction`, `max_file_size`,
   `max_file_path_length`, `file_extension_restriction`, or `workflows`; both have
   `enforcement == "active"` and setup-attested `bypass_actors == []`;
- repository settings enable merge commits, disable squash/rebase merge, and disable automatic head
   branch deletion after merge;
- repository workflow inventory digest matches a user-attested allowlist stored in configuration;
- authorized immutable numeric user ID/node-ID pairs are nonempty; `merged_by.id` and `node_id` must
   be present and listed, while the publisher App/installation IDs are explicitly excluded;
- runtime `GET /repos/{owner}/{repo}/rulesets?includes_parents=true` enumerates all targeting
   repository/organization/enterprise rulesets and source types; runtime effective branch rules are
   read separately. `GET .../rules/branches/{branch}` is never treated as enumeration because it omits
   evaluate/disabled rulesets. Runtime compares every field readable by its installation token against
   the setup projection. Parent-rule bypass/details that runtime cannot read are covered by a
   configured bounded-age setup attestation; expiration blocks publication pending protected
   re-attestation;
- repository settings `allow_merge_commit`, `allow_squash_merge`, `allow_rebase_merge`, and
   `delete_branch_on_merge` are present and readable; absent fields fail closed rather than implying an
   acceptable default;
- no existing PR already binds another proposal under the same idempotency key.

**[LOCKED] Every target write still uses the repository's PR acceptance boundary.** Direct writers are
converted during cutover. Competing accepted PRs do not invalidate the sealed Proposal; they change the
actual target parent against which merge equivalence and post-acceptance proof are verified.

**[LOCKED] Bypass actors are attested only during user-interactive setup with the administration
credential that can read them.** Setup persists canonical `effective_rule_snapshot_digest` and
`bypass_actors_digest`, then seals both into the candidate and Proposal. An absent `bypass_actors` key
means unknown, never empty. Runtime drift, an unreadable parent ruleset, or inability to compare exact
runtime-readable fields blocks publication/verification with `policy-evidence-unavailable-or-bypassed`.
Setup reads full detail at `/repos/{owner}/{repo}/rulesets/{id}`, `/orgs/{org}/rulesets/{id}`, or the
configured enterprise ruleset-detail endpoint using source-appropriate administration read. Missing
source credentials make the repository unsupported at setup with exact remediation. Re-attestation
never gives Cockpit an administration credential. A separate user-invoked, out-of-process interactive
setup command reads the source-appropriate user credential directly from the terminal at call time,
enumerates policy, displays repository identity, ruleset IDs/source types, canonical policy-projection
digest, and issued-at time, and requires an explicit terminal confirmation. The credential never
enters files, arguments, environment, Cockpit, or Delivery runtime configuration. After confirmation,
the command appends the attestation directly to the authoritative state store by CAS against the exact
expected policy-attestation sequence and digest. The event binds the canonical projection plus the
interactive command's verified distribution binary digest. A stale CAS, unreadable policy field,
credential failure, command binary mismatch, or declined confirmation appends nothing and blocks
publication. Cockpit is read-only for this action: it displays expiration and the exact command to
run, then observes the appended event. Re-attestation cannot change a sealed Proposal; changed policy
requires supersession.

The canonical policy projection is closed and sorted: ruleset ID, source type, enforcement, ref
conditions, rule type, only the exact known parameters enumerated in §11.1, and normalized bypass
entries keyed by actor type/immutable ID/bypass mode. Unknown rule types fail closed. Unknown fields
inside a known rule type are retained as raw evidence but excluded from the digest, so provider field
additions do not invalidate otherwise identical policy.

### 11.2 Publication Sequence

**[LOCKED] Remote exposure and PR binding use this failure-safe order:**

1. append a publication-intent event by CAS, binding Proposal ID, operation ID, repository, target, and
   intended remote ref before any external effect;
2. read remote branch and existing PR state;
3. if exact exposure or a user-created PR already exists, reconcile and continue from its exact commit point;
4. transfer the exact sealed object and request proposal-ref creation using
   `git push <remote> <proposal-commit>:<proposal-ref> --force-with-lease=<proposal-ref>:`; the empty expected value is client-side
   defense-in-depth requiring the advertised ref to be absent. The server-side proposal namespace
   ruleset proven by §11.1 is the authoritative create-only enforcement and publication is blocked
   without it;
5. read the remote branch back and verify its object ID;
6. render the exact PR title/body, expected base/head identities, and GitHub compare URL. The rendered
   body contains the machine identity block; OwlBear does not call a PR create/update/close/merge endpoint;
7. construct a deterministic exposure-record commit whose single-entry tree contains the canonical
   sealed Proposal plus `exposure_id`, target, remote proposal branch, exact exposed head, and digest
   of the rendered PR intent; publish
   it create-only at `refs/heads/owlbear/records/<change-id>/<proposal-id>`, then read back the branch,
   commit, tree, and record digest. The proposal branch remains
   `refs/heads/owlbear/proposals/<change-id>/<proposal-id>` and there is no directory/file ref overlap;
8. append the exposure receipt by CAS on `proposal_id`, expecting the publication intent and no
   exposure receipt and requiring the verified record branch/commit/tree/digest. This is remote
   exposure's single effect-binding commit point and enters `awaiting-pr-creation`. A losing caller
   returns the committed receipt after exact reconciliation;
9. the user opens the rendered compare URL and creates the PR through GitHub's normal authenticated UI;
10. `observe_publication` lists PRs in every state by exact head branch within the base repository,
   requires exactly one open or merged PR whose base repository, head repository, target, source
   branch, and head commit equal the exposure record, and reads it back without trusting prose;
   closed-unmerged PRs on the same head remain append-only evidence and never block binding;
11. append the publication receipt by CAS expecting the exact exposure receipt and no prior PR binding;
   the receipt binds typed `external_number`, PR identity, and observed head to the immutable exposure
   record. This is PR binding's single commit point;
12. route from the reconciled PR state: open to `awaiting-acceptance`, merged to
    `acceptance-verification`, closed unmerged to the rejection decision;
13. any later additional PR on the same proposal head is an append-only observation and raises
    publication-identity-collision attention; the receipt is never mutated;
14. on an existing-ref or existing-PR response, reconcile by exact object ID and head/base identity:
   exact match returns the existing result; mismatch raises identity-collision attention;
15. on failure after ref creation but before exposure receipt, retain the branch and reconcile on retry; never
   blindly push again.

If a record ref exists without an exposure receipt, retry reads it back, deterministically
recomputes the expected record commit/tree/digest, and continues only on exact equality. Inequality
raises `publication-record-missing-or-mismatched`; create-only evidence is never overwritten.
If a user-created PR exists without a publication receipt, observation binds it only after every
typed repository/base/head identity matches the exposure record.

A publication intent without a receipt is not a lifecycle state. The same operation ID reconciles it;
a superseded operation ID appends an abandoned-intent event and never deletes history.

### 11.3 PR Intent Rendering

**[REQUIRED] OwlBear renders user-reviewable PR intent that makes the human creation and later merge
decisions legible.** It includes:

- Change title and intended value;
- Outcomes and acceptance observations;
- material exclusions and risks;
- proof summary with exact commands/checks and evidence links;
- proposal/base commit identities;
- explicit statement that merging accepts the complete Change;
- a machine-managed block carrying schema, Change ID, Proposal ID, and exact head.

**[LOCKED] Rendered PR intent is a pure deterministic function of the sealed Proposal, repository
identity, target ref, remote proposal branch, and `renderer_schema_version`.** It contains no
timestamps, attempt/operation IDs, absolute paths, machine-local evidence locators, or environment
values; evidence is referenced by content digest only. The compare URL uses GitHub's supported prefill
parameters when practical. Intent beyond the configured practical URL limit uses title-only prefill
plus a copyable deterministic body. Prefill success and body text never participate in binding.

### 11.4 Publication Drift

**[LOCKED] Any external mutation of the PR head, source branch, or target branch selection invalidates
publication exactness and raises attention.** OwlBear does not adopt the mutation. The machine
identity block is display-only provenance: absence, edit, or removal is retained as evidence and never
participates in binding, verification, or completion. A code correction creates a successor Proposal.

Proposal-branch absence before verified completion raises `proposal-branch-deleted` attention and
blocks completion. After a completion receipt, reachability through the accepted target commit is
sufficient for history, although repository policy still retains proposal refs for auditability.

**[REQUIRED] While acceptance is pending, a cheap read-only check tracks target advance and PR-head
identity.** Target advance is informational and does not supersede the Proposal. External mutation of
the Proposal head still raises attention. Supersession first reads PR state and CASes only on an
unmerged observation; a merged observation routes to acceptance verification.

## 12. Acceptance and Exact Completion

### 12.1 User-Owned Acceptance

**[LOCKED] OwlBear agents and Delivery services cannot merge.** The user merges in GitHub through the
normal repository-controlled surface. A repository policy may mediate the action only if the final
accepted graph still satisfies the supported exact merge contract.

The merge tool may remain globally exposed by an approved toolset, but it is not assigned to any
OwlBear agent. This is configuration-based least privilege, not a fictional runtime interception.

### 12.2 Initial Exact Merge Contract

To make the first redesign watertight, support one narrow merge topology before adding convenience.

**[LOCKED] Initial completion supports a deterministic recomputed two-parent merge where, in this
order:**

1. `merged == true` and `merged_at` is present in one provider read;
2. the candidate accepted commit is reachable from the freshly fetched configured remote target;
3. parent 1 is the actual target tip at merge and `base_target_commit` is its ancestor;
4. parent 2 is exactly `proposal_commit`;
5. the merge commit targets the configured target ref;
6. the merge tree equals a locally recomputed merge tree for parent 1 and `proposal_commit`, using
   exactly one merge base (`git merge-base --all` returning zero or multiple bases raises
   `unsupported-merge-base-topology`) and merge-contract v1: exact Git 2.55.0 with
   `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `GIT_ATTR_NOSYSTEM=1`, and a
   disposable `GIT_DIR` whose local config is empty except the contract's explicit `-c` values and
   whose `info/attributes` is absent; invoke
   `git merge-tree --write-tree <parent-1> <proposal-commit>` with calibrated contract values for
   `merge.renames`, `merge.renameLimit`, `merge.directoryRenames`, `diff.renames`, `diff.renameLimit`,
   and `diff.algorithm`, plus fixed
   `core.autocrlf=false`, `core.eol=lf`, `core.ignorecase=false`, `core.precomposeunicode=false`,
   `core.symlinks=true`, and `merge.conflictStyle=merge`;
7. the PR observed head equals `proposal_commit`;
8. every recorded review and check identity binds `proposal_commit` rather than another commit;
9. provider `merged_by.id` and `node_id` are present, match the sealed immutable actor allowlist, and
   are not the OwlBear publication App/installation identity; login is persisted only for display;
10. focused and full post-acceptance proof passes on the exact accepted target commit in the restricted
   proof runner.

This preserves immutable proposal review while permitting unrelated accepted target changes. The
accepted result is trusted only after deterministic tree equivalence and proof on the exact merged
commit; a conflict, merge-driver mismatch, or proof failure yields acceptance attention.

**[LOCKED] Merge-contract v1 admits only Git built-in merge behavior.** Before recomputation, form the
union of paths differing between merge-base, parent 1, and `proposal_commit`. Run
`git check-attr --source=<tree> --all --stdin` separately against all three exact trees in the
same sanitized environment. For `merge`, admitted `check-attr` states are `unspecified`, `set`,
`unset`, and literal built-in driver names `text` and `binary`; `union` and every unknown literal are
unsupported. For `filter`, `working-tree-encoding`, and `conflict-marker-size`, only `unspecified` or
`unset` are admitted. The latter scan is defensive even though `merge-tree` performs no working-tree
conversion. Any other value raises `merge-driver-mismatch`. A configured external merge driver or any
unreproducible attribute/config input is unsupported. Repository settings permit only merge commits;
tree equality, not provider method prose, is authoritative.

Before merge-contract v1 is admitted for first production publication, the rename/directory-rename/
diff values are calibrated by the live GitHub fixture and frozen into the contract digest. Environment
sanitization and exact Git version are locked now; calibrated values become locked with admission. The
release gate empirically proves which tree Git 2.55.0 consults for attributes and that the three-tree
scan covers it.

**[LOCKED] Required checks bind the PR head SHA for policy identity.** A default `pull_request` workflow may execute
an ephemeral provider merge tree that OwlBear never fetches; green checks are therefore policy
evidence, not correctness evidence for the accepted tree. Post-acceptance proof is the correctness gate.

**[DEFERRED] Merge queues, squash, and rebase.**
Each requires its own challenged equivalence and proof contract. They must never silently fall through
to “PR says merged, therefore completed.”

Tree equality makes manifest integrity at acceptance implicit. The receipt catalog still validates
the manifest digest independently when reconstructing history.

### 12.3 Observation and Verification

**[LOCKED] The acceptance observer is read-only.** It may fetch remote objects into remote-tracking or
temporary refs, query GitHub, inspect commits/trees, and write local Delivery receipts. It cannot
update a local target branch, push, merge, or touch a user worktree.

Verification proceeds:

1. read PR and typed provider evidence; never use free text for a transition;
2. bind observation to the stored publication receipt;
3. require `merged == true` and `merged_at` in the same read; `merge_commit_sha` is never acceptance
   evidence and `refs/pull/**` is never fetched, resolved, or admitted;
4. fetch the configured remote target with the explicit non-forced, non-pruning refspec and resolve the
   candidate accepted commit from that graph, not from a PR field;
5. retain the candidate under `refs/owlbear/observations/<change-id>/<observation-id>` for verification
   and receipt revalidation; a non-fast-forward target rewrite is an error, never silently adopted;
6. verify target reachability before every other graph property;
7. verify parent identities, merge topology, recomputed target tree, proposal tree, and manifest binding;
8. verify the acceptance actor matches the sealed allowlist and is not the publisher; otherwise raise
   `acceptance-actor-unauthorized-or-missing`. Then persist deterministic
   review/check identity evidence and a separate effective-rule/rule-suite snapshot including
   repository/organization provenance and bypass readability. Actor authorization,
   merge contract, and policy blocking use the sealed Proposal values; live configuration divergence
   raises `sealed-policy-configuration-drift` and never substitutes new policy silently;
9. resolve the canonical proof profile from the exact accepted target tree and compare it with the
   sealed `proof_profile_digest`; inequality raises `proof-profile-changed` attention and cannot
   silently adopt either profile. The user may explicitly authorize the accepted-tree profile through
   protected Cockpit action, producing an immutable authorization ID bound to `(observation_id,
   accepted_target_tree, accepted_profile_digest)`;
10. transition by CAS from `acceptance-verification` to `acceptance-proof`, acquire a bounded
   post-acceptance-proof claim, transfer and materialize the exact accepted target commit in a
   guest-only disposable proof workspace, and run focused plus full proof in the restricted runner.
   When accepted proof fails, resolve the profile from parent 1 and require its digest to equal the
   profile digest used for the accepted-commit run -- the sealed digest, or the authorized
   accepted-tree digest when a profile authorization exists -- before baseline execution; mismatch is
   `baseline-inconclusive`. “Fails
   identically” means equality of normalized failing-check identifier sets, never exit-code equality or
   output-byte similarity;
11. persist the verified graph and proof result, release the proof workspace, and transition to
    `awaiting-confirmation`;
12. after presenting Proposal, PR, merge actor, accepted target commit/tree, proof profile, and proof
   evidence, Cockpit accepts the explicit user-only confirmation that cannot be synthesized from
   provider data or assigned to an agent; it appends one `acceptance-confirmed` event carrying the user confirmation and completion
    receipt, transitions directly to `completed`, and releases eligible managed execution resources.

**[LOCKED] Candidate commit discovery is a bounded first-parent walk from the fetched target tip.** It selects the
unique commit whose second parent equals `proposal_commit`. No match within the configured bound or
more than one match raises `accepted-target-unreachable`; changing the configured bound is a protected
`set_candidate_discovery_bound` action and triggers a fresh observation. Discovery never guesses.

**[LOCKED] Completion has one commit point:** Cockpit appends the `acceptance-confirmed` event by
compare-and-swap on `(change_id, proposal_id)` expecting `awaiting-confirmation` and no completion. The
operation computes `confirmation_id` and retry-stable `completion_id` inside the event from immutable
inputs; its payload carries both `UserAcceptanceConfirmation` and the completion receipt and its
post-state is `completed`. A losing caller returns the existing receipt after exact identity
reconciliation. Completion evidence refs are not released.

**[REQUIRED] Policy compliance and graph exactness are distinct.** A ruleset snapshot is mandatory at
publication. Any available provider rule-suite result is retained at acceptance. Missing or bypassed
policy evidence raises typed governance attention, but does not change whether the exact sealed Git
proposal landed. By default it does not block a graph-exact completion receipt; repository operators
may configure it as blocking before publication. This setting is captured in the Proposal and cannot
change retroactively.

### 12.4 Accepted but Unverifiable

**[LOCKED] If GitHub reports merged but exact verification fails, OwlBear does not claim completion and
does not attempt to undo or repair the target.** It records `acceptance-attention` with the observed
target commit and requires a user-directed remediation Change or explicit forensic resolution.

This distinction is essential: external acceptance is an irreversible fact, while OwlBear completion
is a verified semantic claim.

## 13. Rejection, Correction, and Supersession

### 13.1 Before Sealing

**[LOCKED] Mutable work remains private.** Builders may amend, reorder, reset, or replace commits only
inside the managed Change ref and under active custody. None of those commits are pushed by default.

### 13.2 After Sealing but Before Publication

The sealed Proposal is immutable. If correction is needed:

1. mark it withdrawn or superseded;
2. return the Change to the owning earlier stage with exact reason and preserved boundary;
3. create and review new work;
4. construct a new Proposal with a new identity.

### 13.3 After Publication

**[LOCKED] Never mutate the published branch or user-owned PR.** Observe the PR as unmerged, append the
withdrawn/superseded state locally, preserve its evidence, expose the successor Proposal on a new
branch, and render the relationship for the user. The user may close the old PR in GitHub. This makes
review identity and forensics unambiguous without giving Delivery PR-write capability.

### 13.4 User Rejection

Closing without merge records a rejected/closed Proposal event and returns the Change through a typed
user decision:

- revise from a named stage;
- abandon the Change;
- defer without active work;
- supersede with a separately admitted Change.

No rejection path mutates target state or discards recovery refs before the decision is durable.

## 14. Completed History Redesign

The current catalog assumes a completion record is manufactured during target publication. That is no
longer possible because acceptance happens externally.

**[LOCKED] Separate three records:**

1. **Proposal package in the proposal/accepted tree:** what OwlBear offered and the user accepted.
2. **External acceptance evidence:** what GitHub reports happened.
3. **Local completion receipt:** OwlBear’s verified binding between the first two.

**[REQUIRED] Completed-history queries read completion receipts, then independently validate referenced
proposal package bytes and Git objects on demand.** They do not infer completion from package presence
alone and do not trust mutable GitHub text.

**[LOCKED] Local Proposal refs and observation refs are completion evidence, not managed execution
resources.** They are retained for the life of every referencing receipt and excluded from worktree,
mutable Change-ref, and attempt cleanup. Retention pruning requires a separately designed archival
contract and is not part of this redesign.

**[REQUIRED] Preserve bounded list/search/show behavior through a receipt catalog and provide a
deterministic reindex operation for a fresh clone.** Reindex scans committed Proposal manifests on the
target, lists PRs across all states by exact retained head branch in the base repository (including
non-default configured targets), and uses commit-to-PR association only as corroboration. It then
enumerates remote record branches under each Change namespace and matches exactly one record whose
`candidate_id` equals the target manifest, whose `proposal_commit` equals parent 2 of the accepted
merge, and whose target/remote branch/exposed head equal the typed provider PR facts. Record content,
not PR prose, is authoritative; zero or multiple exposure records matching the same typed PR identity
are `evidence-incomplete`. The first-parent target walk uses the configured protected discovery bound;
exceeding it is `evidence-incomplete`, never an unbounded scan. Reindex fetches that record commit,
recomputes and verifies `proposal_id` and `exposure_id`, reads immutable
proposal refs and PR/merge evidence from GitHub, re-runs exact graph checks, and recreates only receipts
whose user confirmation evidence is available in exported/imported Delivery state. A missing or
digest-mismatched record is never a guess or verified history. Without user confirmation, reindex records `awaiting-confirmation` or unresolved
accepted evidence rather than inventing intent.

Completion receipts are machine-local authority unless exported with the Delivery state store. The
committed manifest and GitHub/Git evidence make exact landing reconstructable on a fresh clone; user
attestation is not reconstructable from GitHub and must be imported or repeated by the user.

**[LOCKED] A package present on target without a valid completion receipt is surfaced as unresolved
accepted evidence, not silently included in completed history.**

## 15. GitHub Object Mapping

### 15.1 Normal Local Delivery

| OwlBear entity | GitHub representation | Decision |
|---|---|---|
| Change | One PR for each sealed Proposal; only one active Proposal at a time | **[LOCKED]** |
| Outcome | Rendered promise/checklist inside the Change PR | **[LOCKED]** |
| Task | No GitHub object | **[LOCKED]** |
| Attempt/claim | No GitHub object | **[LOCKED]** |
| Portfolio | Cockpit/Delivery remains canonical | **[LOCKED]** |
| Incoming idea/bug | GitHub Issue may become an intake source | **[DEFERRED]** |
| Cross-Change portfolio view | GitHub Project may display selected Changes | **[DEFERRED]** |

**[REJECTED] Project = Change, PR = Outcome, Issue = Task.** It breaks Change atomicity, externalizes
replannable detail, multiplies partial writes, and makes a mutable view look like typed authority.

### 15.2 When an Outcome Should Become a Change

**[REQUIRED] Split an Outcome into its own Change when it:**

- provides standalone value and can ship alone;
- can be independently accepted or rejected;
- has a materially different risk, reviewer, or release boundary;
- has independent dependencies;
- would keep a larger Change open long enough to create avoidable conflict risk.

If an Outcome needs its own target-merging PR, it is a Change.

## 16. Cloud Execution Boundary

Cloud execution is valuable prior art from Turbo, but it is not required to repair Delivery.

### 16.1 First Redesign

**[DEFERRED] Do not implement cloud dispatch during the proposal/acceptance replacement.** The initial
cutover must first prove local authority, safe proposal publication, exact acceptance, recovery, and
history end to end.

### 16.2 Reserved Future Contract

When implemented, cloud work is allowed only for eligible leaf Tasks:

- complete typed task authority and deterministic proof plan;
- exact base commit and bounded writable surfaces;
- no unresolved user request or interactive browser dependency;
- no credential, workflow, setup, or security-sensitive surfaces unless separately authorized;
- no dependency on mutable local-only state.

**[DEFERRED, RESERVED CONSTRAINT] A cloud worker returns a commit; it never merges.** It
may push only to a dispatch branch. Local OwlBear verifies the exact returned commit, independently
reviews it, admits it under normal custody, and may rerun proof before it becomes a task result.

**[DIRECTION] A temporary Issue or PR may serve as the externally addressable dispatch handle.** That
is the one justified task-level GitHub object because a genuinely separate worker needs coordination.
It is not a mirror of all Tasks.

### 16.3 Turbo Concepts to Adopt Independently

| Concept | Decision | OwlBear use |
|---|---|---|
| Typed stage/worker outcomes | **[REQUIRED]** | Machine-routable worker returns and proof summaries |
| Dependency/cycle validation | **[REQUIRED]** | Reject invalid task graphs before claims |
| Bounded per-operation attempts | **[REQUIRED]** | Deterministic retry and correction limits |
| Durable resume checkpoints | **[REQUIRED]** | Recover without chat-history inference |
| Fail-closed gate verdicts | **[REQUIRED]** | Separate deterministic proof truth from narrative |
| Credential scrubbing and audit | **[DEFERRED]** with reserved constraint | Prevent worker access to merge/elevated credentials |
| Container sandbox and model relay | **[DEFERRED]** | Consider only with unattended/cloud workers |
| Arbitrary evaluator registry | **[REJECTED]** | Too much privileged extensibility; explicit gates first |
| GitHub Actions as task authority | **[REJECTED]** | Would create a second control plane |
| New Relic/OTLP, Jira/Figma, second UI | **[REJECTED]** | Not part of Delivery correctness |

## 17. Tools, Credentials, and Role Boundaries

### 17.1 Tool Assignment

**[LOCKED] Least privilege is enforced through three layers:**

1. global MCP toolset allowlisting;
2. exact per-agent tool assignment;
3. claim-aware VS Code chat hooks that confine editing tools to the active managed worktree and task
   surfaces.

No OwlBear agent receives `merge_pull_request` or provider credentials. Publisher and observer are
application services, not agent roles. Builder retains workspace editing tools, but hooks confine each
write to its claimed managed surface. Builder does not receive terminal or raw Git.

**[DIRECTION] Extend agent-ecosystem validation so tool assignments that violate the role matrix fail
CI.** This hardens configuration drift; it is not a runtime security theater layer.

### 17.2 Server-Side Protection

**[REQUIRED] Configure the target branch so ordinary acceptance follows the supported merge contract:**

- `pull_request` rule with required merge method `merge`;
- required review/check policy;
- `non_fast_forward` and `deletion` rules;
- “require branches to be up to date” disabled: it is incompatible with immutable proposal refs and
   §11.4 target-advance handling; exact ancestry and tree equality are verified after acceptance.

Branch rules are defense in depth and exactness prerequisites. They do not replace OwlBear’s read-only
verification, because repository configuration can drift or privileged users can bypass it.

### 17.3 Credentials

**[LOCKED] The publication identity's inability to update the target is established jointly by an
enforced ruleset it cannot administer, a runtime credential with no `pull_requests: write` or
`administration: write`, and a bounded Git publisher that admits only create-only proposal/record
destinations.** GitHub contents-write permission does not provide ref-level granularity. Exposure is
forbidden when preflight cannot prove credential permissions, ruleset enforcement, and bypass
exclusions.

**[LOCKED] Every subprocess that executes repository-authored code runs in a direct
`VZVirtualMachine` proof runner on macOS owned by a separate `owlbear-proofvm` executable.** Setup
builds and locally code-signs that helper with `com.apple.security.virtualization`, records its binary
digest and embedded entitlement, verifies signature validity with `codesign --verify --strict`, reads
entitlements with `codesign -d --entitlements :-`, and compares the recorded binary digest before
every run. Merge-contract v1 supports Apple silicon `arm64` hosts only; unsupported architecture, absent/
unsigned/unentitled helper, or digest drift routes to `proof-isolation-unavailable` and setup/
publication fail closed. Setup pins and verifies separate Linux kernel, initramfs,
and rootfs SHA-256 digests.

**[LOCKED] Guest images have an explicit provenance and distribution contract.** A committed
reproducible build recipe produces the Linux kernel, initramfs, and rootfs from a pinned upstream
distribution snapshot. Every upstream input appears in a setup-attested
`{url, sha256, kind, arch}` allowlist. The rootfs contains the complete shared-library dependency
closure required by every allowlisted browser artifact because neither the guest nor the runtime host
fetcher may resolve system packages. Images are distributed as digest-pinned downloads outside the
Git clone; setup states disk and bandwidth prerequisites before Delivery work begins. A missing image,
digest mismatch, unbuildable recipe, or unsatisfied library closure routes to
`proof-isolation-unavailable` and Delivery terminates at `sealed-unpublishable` rather than degrading
isolation. The release gate runs every maintained proof profile, including actual Playwright browser
execution, to completion inside the guest with no network device attached.

Guest images are published as one versioned release artifact set at a setup-attested origin recorded
as `{origin_url, scheme=https, kernel_sha256, initramfs_sha256, rootfs_sha256, arch=arm64,
recipe_commit}`. Setup rejects another origin, scheme, or redirect target and verifies each digest.
The recipe is reproducible-by-verification, not build-on-install: the release gate runs it on a native
arm64 Linux builder pinned by image/toolchain digest and requires exact equality with all published
digests; divergence blocks release. Consumer
setup only downloads and verifies the set after stating origin, size, bandwidth, and disk
requirements. Unreachable origin or digest mismatch raises `proof-isolation-unavailable`.

The VM configuration has an empty network-device array and no
`VZVirtioSocketDeviceConfiguration`; guest-root code cannot add a device or route. Linux guest init
boots directly into the admitted proof profile from the read-only input image and writes completion/
evidence to the fixed-size raw evidence block. Guest init writes payload then header, calls `fdatasync`,
and powers off. Every guest-writable image is attached with `VZDiskImageCachingMode.uncached` and
`VZDiskImageSynchronizationMode.full`. The host detects completion only through
`VZVirtualMachineDelegate` stop callbacks, then opens the stopped evidence block with a fresh
`F_NOCACHE` descriptor and validates it. A bounded wall-clock deadline invokes stop/force-stop,
discards partial evidence, and records `proof-runner-timeout`; the host never reads a running guest's
block. Guest namespace and nftables deny rules are defense in depth only, never
load-bearing. Lima/SSH control planes are not used. No
host socket, home, credential store, Git config, or Cockpit path is
mounted. The profile/image/network-policy digests are verified before each run. Repository code
receives no Git credential helper, provider token, SSH agent socket, `gh` configuration, model
credential, or provider-reachable network. It can write only its disposable workspace, declared
dependency roots, and bounded temporary storage. Maintained test servers bind only inside that private
loopback namespace.

**[LOCKED] Dependency provisioning has two trust tiers and never executes repository-authored code
with egress.** A host fetcher reads committed digest-pinned lockfiles and downloads only exact wheel,
npm tarball, and Playwright/browser artifacts into a content-addressed staging store. Browser artifacts
must appear in a setup-attested configuration allowlist of
`{url, sha256, playwright_version, platform, arch}` compatible with the pinned Linux arm64 rootfs because
package lockfiles do not carry their archive digests; artifacts absent from both lockfile digests and
that allowlist fail closed. The fetcher builds a separate read-only content-addressed artifact image
containing every resolved wheel, npm tarball, and browser archive. The digest-pinned rootfs contains
exact pinned CPython 3.14 and Node 24.15.0 runtimes. The fetcher does not run
build backends, npm lifecycle scripts, package executables, or repository hooks. Source distributions,
dependencies requiring install/build scripts, and missing digests fail closed unless separately
user-authorized as a new challenged proof contract. All downloads finish before VM start. The guest
has no network device at any point, verifies every artifact digest from the read-only artifact image,
materializes writable disposable virtualenv/`node_modules` roots with scripts disabled, and has no
resolution path for an artifact or runtime absent from the image/rootfs.

The fetcher accepts only `https` URLs whose host is in a setup-attested registry allowlist. Before any
request it resolves the host and rejects loopback, link-local, unique-local, private, and reserved
address literals/resolutions; it follows at most one redirect to the same allowlisted host and rejects
`file`, `ftp`, `data`, and every other scheme. Any violation raises `proof-isolation-unavailable`.
The source-distribution/build-script prohibition applies to fetched third-party artifacts. First-party
packages from the exact repository commit may build only inside the network-device-free guest.

Guest init has a distinct provisioning phase before proof commands. It verifies all artifact digests
and the dynamic shared-library closure of every executable artifact. A browser allowlist entry is
accepted only when its version/platform/architecture triple appears in the pinned rootfs closure
record. Provisioning evidence is typed separately; any provisioning failure raises
`proof-isolation-unavailable`, never `post-acceptance-proof-failed`.

**[LOCKED] Repository content enters the guest only as a verified immutable transfer artifact.** The
host exports the retained exact observation/proposal ref as a Git bundle plus declared lock/artifact
manifest onto a host-built read-only raw input image; byte determinism of the bundle is unnecessary
because the guest verifies commit/tree/object identities. The guest materializes them on guest-only
disposable storage. No host repository, `.git` administrative directory, `.owlbear/` state, managed
worktree, or cache is mounted.

Evidence uses a second fixed-size raw block device. Its first block contains a fixed magic/version,
bounded payload length, and SHA-256; OwlBear reads it as raw bytes, rejects over-limit/trailing data,
verifies the digest, then schema-validates the payload. The host never mounts, `fsck`s, or invokes a
filesystem driver on any guest-writable image. The evidence schema cannot carry executable commands,
host paths, symlinks, device nodes, or nested archives.

The exact guest block inventory is: digest-pinned read-only rootfs, read-only input image, read-only
artifact image, per-run writable scratch image, and per-run writable fixed-size evidence block. Scratch
and evidence are discarded after validated extraction or any failure; no other block/share device is
attached.

Task proof and bounded diagnostics use the same channel before any Proposal exists. They run only on
an exact commit produced by `commit_task_result` and retained at
`refs/heads/owlbear/changes/<change-id>`; the guest verifies that exact commit/tree. Proof never reads
uncommitted managed-worktree state.

If the VM, kernel/initramfs/rootfs digest, evidence channel, namespace, nftables policy, or mount policy is unavailable or unverifiable,
proof fails closed. Delivery refuses to enter or continue `acceptance-proof` and refuses confirmation
while any proof-isolation prerequisite is degraded. Proof runner escape is a release-blocking security
failure.

**[LOCKED] Cockpit user actions remain on the macOS host outside the proof VM and every guest network/
mount namespace.** The per-launch secret exists only in Cockpit process memory and the trusted
browser session; it is absent from proof-visible files, environment, caches, ports, logs, and HTTP
responses obtainable from the proof namespace.

No builder/reviewer subprocess receives credentials capable of target writes or PR writes. Provider
credentials are held only by the bounded ref publisher and read-only observer and are never inherited by
build, proof, review, hook, or cleanup subprocesses.

**[DIRECTION] Independently implement environment scrubbing, credential-store neutralization, token
audits, and narrowly mediated model access based on the useful Turbo security pattern. Containers are
one possible proof-runner implementation, not a reason to weaken the locked isolation contract.**

## 18. Module and Ownership Redesign

Names are **[DIRECTION]**; responsibilities and capability separation are **[LOCKED]**.

| Module | Owns | Must not own |
|---|---|---|
| `TaskWorkspaceService` | Claim-bound workspace creation, path confinement, task-result commits, cleanup leases | Target ref writes, user content, GitHub |
| `ProofRunner` | Credential-free execution of admitted proof plans and typed evidence | Agent shell, provider credentials, lifecycle transitions |
| `PostAcceptanceProofService` | Claim-bound immutable transfer and guest-only proof workspace for the exact accepted commit, focused/full proof, typed result | Host worktree mutation, graph verdict, confirmation, target repair, provider credentials |
| `ProposalBuilder` | Candidate construction, manifest, proof binding, proposal commit, local seal | Push, PR creation, target writes |
| `ProposalStore` | Atomic proposal/event/receipt persistence and idempotency | Git mutation |
| `GitHubReadClient` | Read-only typed GitHub API evidence required by observer | Provider writes, agent exposure, lifecycle decisions |
| `GitHubRefPublisher` | Create-only remote proposal/record refs through the bounded ref service | Any PR API write, target update, local lifecycle decisions |
| `AcceptanceObserver` | Read-only GitHub/Git evidence and exact merge verification | Push, branch update, worktree mutation |
| `CockpitAcceptanceService` | Protected local confirmation/decline and atomic confirmation/completion append | MCP export, agent invocation, GitHub mutation |
| `CompletionCatalog` | Receipt-backed list/search/show, deterministic reindex, and integrity validation | Inferring completion from mutable PR prose |
| `PortfolioApplication` | Orchestrates capabilities and typed transitions | Direct Git subprocess calls or provider details |

**[REQUIRED] Apply the deletion test:** each module must hide a real capability boundary or substantial
complexity. Do not introduce generic provider interfaces until a second concrete acceptance surface
exists. Core models remain provider-neutral; the first concrete publisher/observer may be GitHub-
specific without a speculative adapter hierarchy.

## 19. API, MCP, Agent, and Cockpit Changes

### 19.1 Remove

**[LOCKED] Delete:**

- `integrate_ready_change` and direct Integration APIs;
- Integration repair claims and repair admission;
- target CAS and checked-out-target refresh operations;
- Integration worker/repairer role and attention taxonomy;
- `DeliveryIntegrationCandidate`, `DeliveryIntegrationCompletion`, and target-publication models;
- current completed-history assumptions tied to `.owlbear/completed` target snapshots;
- any UI action that implies an agent can merge or directly integrate.

### 19.2 Add

**[REQUIRED] Provide application/MCP operations equivalent to:**

```text
open_task_workspace(change_id, outcome_id, task_id, claim_id)
commit_task_result(change_id, outcome_id, task_id, claim_id, expected_head)
run_task_proof(change_id, outcome_id, task_id, claim_id, expected_commit, proof_plan_digest)
run_bounded_diagnostic(change_id, outcome_id, task_id, claim_id, expected_commit, profile_command_id, selector, args_allowlist)
prepare_proposal(change_id)
show_proposal(change_id, proposal_id?)
seal_proposal(change_id, candidate_id, claim/evidence binding)
expose_proposal(change_id, proposal_id)
observe_publication(change_id, proposal_id, exposure_id)
observe_acceptance(change_id, proposal_id)
verify_acceptance(change_id, proposal_id, observation_id)
recover_acceptance_proof(change_id, proposal_id, expired_claim_id)
supersede_proposal(change_id, proposal_id, reason)
withdraw_proposal(change_id, proposal_id, reason)
reindex_completed_history(repository_identity)
list_completed_changes(...)
search_completed_changes(...)
show_completed_change(...)
```

Mutating operations use exact expected identities and idempotency keys. Read operations expose typed
attention and never trigger hidden mutation.

The legacy MCP disposition is exact: remove Integration and repair operations; retain bounded
`list_completed_changes`, `search_completed_changes`, and `show_completed_change` with receipt-backed
implementations; replace lifecycle reads/mutations only where the new state model requires it.

`observe_publication`, `observe_acceptance`, and `verify_acceptance` are explicit mutations because
they append evidence and state events. `observe_publication` is invoked by Cockpit after the user
creates the PR; acceptance observation/verification are invoked by an orchestrator MCP operation or
the Cockpit “Check acceptance” write action. None occurs as a hidden side effect of a read. No
always-running scheduler is needed for first operation.

**[LOCKED] `confirm_acceptance` and `decline_acceptance` exist only on a loopback Cockpit HTTP endpoint protected
by a per-launch confirmation secret injected into the served SPA, exact loopback `Origin`/`Host`
validation, and a single-use nonce issued by the immediately preceding confirmation-view request.**
The confirmation view also issues a stable client operation ID; retries reconcile that ID before nonce
consumption, making lost responses idempotent.
They are not MCP tools, are absent from every agent tool list, and cannot be called through Delivery
orchestration. Confirmation appends one `acceptance-confirmed` event by CAS expecting
`awaiting-confirmation` and no completion; that event carries both `UserAcceptanceConfirmation` and
the retry-stable completion receipt and transitions directly to `completed`. Decline routes to
`acceptance-attention` without claiming completion; the request permanently lost slot eligibility on
entry to `awaiting-confirmation` after graph and proof success.

`authorize_accepted_proof_profile`, `resolve_rejection`, `close_unverified`,
`authorize_preexisting_baseline`, `rerun_acceptance_proof`, `rebaseline_target_history`,
`defer_change`, `abandon_change`,
`resume_change`, `discard_candidate`, `retry_publication_preflight`,
`set_candidate_discovery_bound`, `recalibrate_merge_contract`, `import_delivery_state`, and
`promote_state_store` are Cockpit-only user
or maintenance actions protected by the same launch secret,
exact loopback `Origin`/`Host`, immediately preceding one-time view nonce, process isolation, and
absence from MCP/agent tool lists. `resolve_rejection` resolves the `rejection-decision-pending` block/request;
`close_unverified` appends the terminal forensic disposition; `rebaseline_target_history` records the
old/new tips and authorizes the one bounded forced remote-tracking update. Reindex is an explicit
application/MCP maintenance operation that never creates user attestation or completion by inference.
`recover_acceptance_proof` is a mechanical orchestrator operation admitted only for an expired claim
and the same immutable observation/commit/profile; `rerun_acceptance_proof` is the protected
Cockpit-only user action after a completed failed attempt. Neither can alter proof inputs.

State import and store promotion are protected maintenance operations, not agent tools. Import verifies
repository identity, stream hash chains, receipt/object identities, and absence of a competing writer;
promotion requires the exact current authority digest plus user confirmation. Any divergent stream,
active lease, provider publication conflict, or unknown provenance fails closed without merging stores.

Builder and independent reviewer both receive proof and bounded-diagnostic operations against exact
commits. Diagnostic commands must be declared in the admitted proof profile; callers may supply only
validated selectors/filter arguments. Each operation CASes `expected_commit` against the change-ref
tip immediately before transfer and binds it into the proof evidence digest; a moved tip rejects the
operation. A reviewer who consumes only the builder's proof bundle does not
satisfy independent review.

### 19.3 Agent Workflow

**[DIRECTION] Replace Integration repair with one bounded proposal role and mechanical services:**

- **proposal builder/reviewer:** local exact candidate construction and independent review;
- **publisher/observer:** application services, not agents;
- **acceptance confirmer:** user through Cockpit only.

Publication is sufficiently deterministic that it should prefer application code over an LLM agent.
Agents explain or repair typed findings; they do not manually improvise Git/GitHub operations.

### 19.4 Cockpit

**[REQUIRED] Cockpit shows:**

- Change versus Outcome readiness distinctly;
- active Proposal identity and exact commit;
- publication state and PR link;
- review/check/merge observations with freshness;
- acceptance verification state;
- rejection/supersession history;
- typed attention with evidence and the one safe next action;
- completed receipt and accepted target commit.

**[LOCKED] Cockpit has no automated PR-create or merge button.** In `awaiting-pr-creation`, “Create PR”
navigates to the rendered GitHub compare URL; after the user creates it, “Bind PR” invokes
`observe_publication` and accepts only the exact typed base/head identity. “Open PR” remains navigation
only. The explicit “Check acceptance” write action appends an observation. When graph verification
succeeds, Cockpit presents an informed Confirm/Decline dialog for the Proposal commit, accepted target
commit, merge actor, topology verdict, proof profile used, and any profile-substitution authorization.
Any remediation action creates a typed local transition or
successor work.

### 19.5 Agent Ecosystem Replacement Inventory

**[REQUIRED] Delete or replace every active Integration reference in one cutover:**

| Existing surface | Required disposition |
|---|---|
| Integration repairer agent and repair review contracts | Delete |
| `w-integration-repair` | Delete |
| `w-delivery-attention-resolution` | Replace with Proposal/acceptance attention resolution |
| `w-orchestration` | Replace Integration dispatch with Proposal readiness/publication/observation routing |
| `w-packet-building` | Replace terminal/commit-owned flow with bounded workspace, commit, and proof operations |
| `r-workspace-governance` Integration repair exception | Delete; document new bounded commit operation |
| orchestration and attention-resolution prompts | Replace tool names, stages, transitions, and outputs |
| orchestrator, builder, and reviewer agent tool lists | Remove terminal/raw Git/provider tools; add only bounded Delivery operations and path-confined editing |
| instruction stubs and validation tests | Remove dangling Integration references and enforce the new capability matrix |

Agent-ecosystem validation must pass with no legacy symbol, skill link, prompt call, or tool assignment.

## 20. Failure and Recovery Matrix

| Failure | Durable state | Safe retry/recovery |
|---|---|---|
| Proposal proof fails | No seal; proof finding bound to candidate | Return to owning stage; preserve candidate evidence |
| Crash during seal | No committed Proposal or committed sealed Proposal | Discard inert pre-commit objects or replay content-addressed derivations from the single commit point |
| Remote branch push times out | Sealed, publication pending | Read remote branch; accept exact match or raise collision |
| User has not created the PR | `awaiting-pr-creation` with immutable exposure receipt | Keep rendered compare URL available; no timeout fabricates or creates a PR |
| User-created PR exists but binding response is lost | Either `awaiting-pr-creation` or atomically bound publication receipt | Re-run read-only `observe_publication`; exact typed identity returns the same receipt idempotently |
| Record ref exists, exposure receipt absent | Publication intent pending | Read back and require exact deterministic record commit/tree/digest, then continue to exposure-receipt CAS; mismatch raises attention |
| PR exists with wrong head | Publication attention | Never overwrite; create successor after user decision |
| PR checks fail | Awaiting acceptance | Repair locally and publish successor Proposal |
| Target advances | Awaiting acceptance, unchanged | Verify by recomputing against actual parent 1; supersede only on user decision or ancestry break |
| PR closed unmerged | `rejection-decision-pending` block/request | User chooses revise, abandon, defer, or supersede; no automatic terminal inference |
| PR merged by unsupported method | Acceptance attention | Record target fact; no completion; user-directed forensic/remediation path |
| Merged commit does not bind exact parents/tree | Acceptance attention | Never “fix” target automatically |
| Accepted target changes the sealed proof profile | `proof-profile-changed` attention | User inspects and explicitly authorizes the accepted-tree profile, then proof runs under that exact digest; no automatic adoption |
| Accepted commit fails post-acceptance proof | `post-acceptance-proof-failed` attention, or `target-preexisting-failure` when exact parent-1 baseline fails identically | Protected rerun CASes on exact evidence. `authorize_preexisting_baseline` CASes attention to `awaiting-confirmation` only when it binds observation ID, accepted commit/tree, authorized profile digest, normalized failure-set digest, and expected attempt; introduced failure routes to remediation or `closed-unverified` |
| Parent-1 baseline profile differs or failure identity cannot be compared | `baseline-inconclusive` attention | User may rerun after deterministic evidence repair, create remediation, or close unverified; never classify as preexisting automatically |
| Observer/GitHub unavailable | Awaiting acceptance or verification pending | Bounded read retry; no authority mutation |
| Proof VM exceeds wall-clock deadline | `proof-runner-timeout` attention | Force-terminate VM, discard raw evidence/staging, and allow bounded protected rerun under a successor claim |
| Crash during `acceptance-proof` | `acceptance-proof` with eventually expired claim | Reclaim expired claim, destroy guest disk/VM, validate/remove host transfer staging under cleanup lease, and rerun proof idempotently on the same accepted commit/profile |
| Queued Change is deferred, abandoned, discarded, or superseded before publication | Change fold leaves that eligibility epoch; ordering request remains auditable but ineligible | Recompute slot projection and select the next eligible sequence; a missing withdrawal audit event cannot block progress |
| Crash between a Change transition and publication-slot audit append | Change stream contains the authoritative lifecycle transition; ordering audit may lag | Rebuild occupancy from ordering requests plus Change folds and append missing audit evidence idempotently; never retain a separate grant |
| Acceptance not checked for configured interval | Awaiting acceptance | Cockpit shows stale observation; user or orchestrator invokes explicit check |
| Exact graph verified but user has not confirmed | Awaiting confirmation | Does not occupy publication slot; user confirms, declines, or leaves durable pending attestation |
| Cockpit confirmation response is lost | Either awaiting confirmation or atomically completed | Reconcile by operation ID first: return an existing receipt idempotently; only when no event exists does a consumed/invalid nonce reject the request |
| Cleanup finds dirty/unknown managed workspace | Recovery attention | Retain workspace/ref until explicit recovery |
| Target history rewrites non-fast-forward | `target-history-rewritten` attention | User-authorized rebaseline records old/new tips, marks affected receipts `evidence-divergent`, then permits one forced remote-tracking update |

 A `publication-attention` exits only through `withdraw_proposal` or `supersede_proposal` to
`proposal-preparation` with a new higher-sequence eligibility epoch, `retry_publication_preflight`
under unchanged sealed identity, or `close_unverified`. Closed-unmerged PR evidence remains retained;
no transition mutates a PR or target.

An `acceptance-attention` exits only through these exact protected re-entries, each CASing immutable
evidence: `authorize_accepted_proof_profile` to `acceptance-proof`, bound to observation ID, accepted
target tree, and accepted profile digest; `rerun_acceptance_proof` to `acceptance-proof`, bound to
observation ID, accepted commit, authorized profile digest, and expected attempt;
`authorize_preexisting_baseline` to `awaiting-confirmation`, bound to observation ID, accepted
commit/tree, authorized profile digest, and normalized failure-set digest;
`rebaseline_target_history` to a fresh observation after divergence evidence is appended; and
`close_unverified` to the terminal Change state. Any other exit does not exist, no attention times out
into completion, and no post-merge attention is superseded.

An `acceptance-attention` raised before `awaiting-confirmation` retains the per-target publication slot
until `closed-unverified` or another explicit terminal disposition. An attention entered by decline
holds no slot and never reacquires one. Because its Proposal is already `accepted`, no post-merge
attention can be superseded; it exits only through `close_unverified`, which appends the terminal
`accepted-unconfirmed` Proposal state, plus an optional separately admitted remediation Change for any
required correction.

Cleanup acquires an exclusive cleanup lease mutually exclusive with every mutation claim. Under that
lease it revalidates path, inode, Git worktree registration, clean state, expected head, and recovery
evidence immediately before deletion. Completion releases only managed worktrees and mutable Change
refs; it never releases Proposal, observation, receipt, or audit evidence.

Target rebaseline is also user-only. It never rewrites or deletes prior receipts; it appends divergence
evidence and restores future Delivery ability after privileged target-history repair.

`recalibrate_merge_contract` reruns the isolated live merge fixtures and proposes a new contract
version. It requires renewed architecture challenge and explicit admission, applies only to Proposals
sealed afterwards, and never changes existing receipts. Systemic provider/local divergence records
`merge-contract-divergence`; per-Change mismatch remains `merge-recomputation-mismatch`.

## 21. Destructive Cutover Strategy

There is no compatibility migration. There is still a safety-conscious implementation sequence.

### Phase 0 — Freeze and Baseline

1. **[LOCKED] Disable direct Integration before other redesign work.** A temporary fail-closed error is
   preferable to leaving destructive authority callable.
2. Capture current dirty-worktree and active-change inventory without mutation.
3. Record full existing tests and current failures.
4. Prevent new legacy Integration claims during the redesign.

### Phase 0.5 — Setup and Repository Prerequisites

1. Add Delivery configuration for GitHub remote, immutable repository identity, target branch,
   runtime GitHub App credential source, user-interactive setup credential source, ruleset IDs,
   authorized acceptance actors, policy mode, and state-store identity. Only the runtime source is
   retained after setup, and it cannot issue credentials with `administration: write`.
2. Install/repair VS Code chat hooks and Git hooks without overwriting a user-owned `core.hooksPath`;
   compose through an OwlBear hook dispatcher or fail with exact remediation when composition is not
   possible.
3. Validate GitHub permissions, repository settings, target/proposal rulesets, bypass lists, merge
   strategy, direct writers, and automatic branch deletion. The enforced target ruleset has an empty
   bypass list. Workflow inventory is recorded as a user-attested digest for drift visibility, not as
   semantic proof that no external writer exists.
4. Install and verify the distributed interactive policy-attestation command, then prove terminal-only
   credential input, explicit canonical-digest confirmation, exact state-store CAS, and fail-closed
   behavior without exposing credentials to Cockpit or another Delivery runtime process.
5. Build the separate `owlbear-proofvm` helper with Xcode Command Line Tools; verify `swiftc` can link
   `Virtualization.framework`, record the toolchain version, code-sign and verify the helper, then
   download the versioned guest image set only from its attested release origin and verify its recipe
   commit/digests. Absence or mismatch routes to `proof-isolation-unavailable`.
6. Add per-child local-state ignores to project and seed `.gitignore` files; never ignore the whole
   `.owlbear/` parent. Setup asserts `.owlbear/proposals/**` is trackable while event stores,
   worktrees, credentials, and scratch roots remain ignored.
7. Convert OwlBear's own direct target-writing workflows to PR-shaped publication before dogfooding.
8. Update sync-to-main and consumer setup so provider configuration and hooks are installed without
   shipping secrets or local state. Proposal manifests under `.owlbear/proposals/` are product evidence
   and ship through sync-to-main when reachable from accepted product history; machine-local receipts do
   not.

### Phase 1 — Safety Kernel

1. Add static deny, capability-assignment, hook, proof-isolation, and adversarial user-worktree tests;
   they must fail against current production behavior.
2. Delete target ref/update/reset/refresh capabilities from Delivery production code and remove raw
   terminal/Git/provider tools from Delivery roles until those tests pass.
3. Establish managed-ref/worktree ownership validation and the bounded mutation services.
4. Prove no Delivery actor can update target or user checkout, including indirect shell and
   repository-authored proof attempts.

### Phase 2 — New Canonical State

1. Replace lifecycle enums and models.
2. Add Proposal, Publication, Observation, Completion, and Attention stores.
3. Implement atomic transactions, idempotency, and schema validation.
4. Delete legacy Integration persistence and transitions rather than translating them.

### Phase 3 — Proposal Pipeline

1. Build candidate against exact target base in managed isolation.
2. Generate canonical package and manifest.
3. Execute proof and independent exact-commit review.
4. Seal atomically under immutable local ref.

### Phase 4 — GitHub Publication

1. Preflight repository and policy.
2. Push exact immutable proposal/record branches and persist the exposure receipt.
3. Render the exact compare URL and PR intent; bind the user-created PR by read-only observation.
4. Implement drift, retry, supersession, and rejection without any PR-write credential.

### Phase 5 — Acceptance and History

1. Implement read-only observation.
2. Verify the narrow exact merge contract.
3. Persist completion receipts.
4. Replace completed-history catalog and reindex behavior.

### Phase 6 — Product Surfaces

1. Replace MCP operations and schemas.
2. Update agents, skills, prompts, instructions, and tool assignment validation.
3. Replace Cockpit stages, actions, sidecar details, filters, and activity/update events.
4. Update setup, repository prerequisites, and operator documentation.

### Phase 7 — Delete and Prove

1. Delete all legacy Integration code, tests, fixtures, docs, and exported names.
2. Search for forbidden terminology and mutation primitives.
3. Run all Delivery, MCP, Cockpit backend/frontend, setup, and ecosystem tests.
4. Run an isolated end-to-end GitHub test repository through seal, publish, human merge fixture,
   observe, verify, complete, reject, supersede, stale-base, and unsupported-merge cases.
5. Only then re-enable Delivery execution.

**[LOCKED] The system is not considered restored while any production surface mixes old Integration
semantics with new Proposal semantics.**

## 22. Verification Strategy

### 22.1 Structural Safety Tests

**[LOCKED] Tests must fail if Delivery production code:**

- invokes `reset --hard`, checkout, restore, clean, stash, or merge in a user/root checkout;
- calls `update-ref` or equivalent for configured target refs;
- constructs a push refspec whose destination is the target;
- invokes GitHub merge APIs/tools;
- issues any provider HTTP method other than GET from a Delivery role, except the single admitted
   `POST /app/installations/{installation_id}/access_tokens` whose body contains only the exact
   role-permission map and repository selector; tests assert that URL template, method, and closed body
   key set. Repository merge, Git ref, Git commit, contents, and every pull-request write endpoint
   remain forbidden; the publisher's only remote write primitive is bounded `git push` creating exact
   proposal and record refs;
- configures any runtime credential source other than the exact GitHub App ID/private-key reference/
   installation-ID form or permits requesting `pull_requests: write` or `administration: write`;
   runtime preflight separately
   verifies each token-mint permission map;
- exposes any user-interactive repository/organization/enterprise administration credential source
   to Cockpit or another Delivery runtime process;
- removes a worktree without exact OwlBear ownership/custody evidence;
- treats a clean checkout as writable authority.

### 22.2 Model and Transaction Tests

Cover canonical serialization, digest stability, unknown-field rejection, identity collisions,
partial transaction recovery, duplicate requests, stale expected identities, and event replay.

### 22.3 Proposal Tests

Cover exact base binding, conflicts, package mutation, proof failure, independent review mismatch,
manifest mutation, dirty managed worktree, concurrent proposal attempts, moved change-ref tip between
proof request and transfer, seal crash, and supersession.

### 22.4 Publication Contract Tests

Use a fake provider below the concrete publisher interface and live tests in an isolated repository.
Cover timeout after push, exposure-record crash recovery, no user-created PR, lost PR-binding response,
read-after-write mismatch, branch collision, duplicate operation, changed PR head, changed target,
manual PR edits, closure, permissions failure, record-branch create-only collision, record read-back
mismatch, and exposure/publication receipt binding.

Fake-provider contract tests are the default deterministic gate. Live GitHub tests run only with an
explicit `github_live` marker against a disposable isolated repository and credential. The release
gate requires the live suite for ref-create CAS/ruleset interaction, PR lifecycle, merge topology,
ruleset evidence including a successful human merge under the exact target rule types, exact-pinned-
Git behavior, proposal and record branch retention, and rename/
directory-rename fixtures that measure provider/local merge-tree equality; ordinary local tests never contact
GitHub. A provider-algorithm divergence raises `merge-recomputation-mismatch`; user remediation is a
successor Proposal on the new target base, never target repair. Immutable proposal branches and record refs are retained indefinitely in first operation; the
repository-wide storage and ref-listing cost is accepted until a separate archival contract exists.
Accepted `.owlbear/proposals/**` manifest directories likewise accumulate in product history; that
committed-history cost is accepted and is not silently pruned.

### 22.5 Acceptance Tests

Cover exact two-parent merge, wrong parent order, base ancestry broken by rewritten target, squash, rebase, merge queue output,
unreachable target commit, mutated manifest, wrong target, missing checks, bypassed rules, duplicate
observation, publisher or non-allowlisted identity reported as merge actor, custom `merge=`/filter/
working-tree-encoding attributes, merge recomputation mismatch, proof-profile change and explicit
authorization, post-acceptance proof failure, crash/lease recovery during `acceptance-proof`, record
digest mismatch, preexisting-baseline authorization and inconclusive baseline, decline without slot
reacquisition, `accepted-unconfirmed` terminal projection, queued-Change abandonment and slot
projection rebuild after a transition/audit crash, two Verified Changes racing for one slot,
sealed-unpublishable, protected authorization for `close_unverified` and
`rebaseline_target_history`, and receipt replay. Only the exact supported topology completes.

### 22.6 User-Worktree Adversarial Matrix

For root checkout states including clean, unstaged, staged, untracked, conflicted, detached HEAD,
target checked out, another branch checked out, and no branch checked out:

- run every automated Delivery operation;
- assert an explicit allowlist diff: every path outside the Delivery state root and every ref outside
   the managed ref allowlist is byte-identical afterward, including index, `HEAD`, local user branches,
   stash, and untracked content;
- allow only the exact managed-state, managed-ref, remote target-tracking fetch, and remote proposal
   effects declared by the operation. Internal Git storage may legitimately change `.git/objects`,
   remote-tracking reflogs, and packed-ref representation; root `FETCH_HEAD` must remain byte-identical.
   Tests compare user ref values, checkout/index
   content, stash identity, and worktree bytes rather than requiring internal storage bytes to freeze.

### 22.7 End-to-End Acceptance Scenarios

**[LOCKED] Release requires at least these durable scenarios:**

1. A complete Change seals and exposes immutable refs, the user creates the PR through GitHub,
   read-only observation binds it, and the user merges by the supported method; verification completes
   without any Delivery credential capable of invoking a PR-write endpoint.
   The release gate runs this both with an independent required reviewer and as a solo operator with
   sealed approval count zero and no self-approval requirement.
2. A dirty root checkout on the target survives the entire lifecycle byte-for-byte.
3. An unrelated target advance still completes through recomputed merge equality; a broken
   `base_target_commit` ancestry raises attention and never completes.
4. A rejected PR returns through an explicit user decision without target mutation.
5. A publication timeout reconciles to exactly one branch, PR, and receipt.
6. A squash/rebase/unsupported merge records acceptance attention but never completion.
7. A malicious or accidental remote branch mutation is detected.
8. A crash at every transaction boundary resumes without duplicate irreversible effects.
9. Completed history verifies from receipts and detects package/Git/provider drift.
10. No configured OwlBear agent can invoke merge authority.
11. Builder edits, task commit creation, and proof succeed end to end without terminal or raw Git.
12. Cockpit-only acceptance confirmation cannot be invoked through MCP or an agent tool list.
13. A fresh clone reindexes exact accepted evidence without fabricating missing user attestation.
14. A raw confirmation POST without the launch secret, exact loopback origin/host, and immediately
   preceding one-time view nonce is rejected without appending an event.
15. Repository-authored code running inside the proof runner cannot connect to the Cockpit user-action
   listener/socket, obtain its secret, or append a confirmation event.
16. A post-acceptance proof failure records attention and never completion; an expired proof claim is
   reclaimed and rerun without touching target or user worktrees.
17. Record-branch mutation/digest mismatch and custom merge-driver attributes fail closed before
   completion.
18. Dependency provisioning executes no repository-authored code while egress exists; source/build-
   script-only third-party dependencies fail closed without a separately challenged authorization;
   malicious lockfile URLs cannot reach loopback/private/link-local targets, while first-party builds
   occur only inside the network-device-free guest.
19. Guest proof receives only the verified commit/artifact bundle, cannot reach host repository,
   `.owlbear/`, other worktrees, caches, or Cockpit, and can return only bounded typed evidence;
   even guest-root observes no network interface except `lo` and cannot obtain egress.
   Setup and each run verify the signed entitled `owlbear-proofvm` helper, arm64 host, pinned kernel/
   initramfs/rootfs, exact block inventory, stop-before-read callback, uncached/full-sync writable
   disks, and timeout force-stop behavior. Setup also proves the image recipe/allowlist provenance and
   complete browser shared-library closure; an actual allowlisted Playwright browser runs successfully
   in the network-device-free guest. Provisioning failures produce `proof-isolation-unavailable`, not
   a repository proof failure.
20. Token mint permissions are exact and administration-write is rejected; unreadable effective
   repository/org rules or repository settings block publication.
21. Every Cockpit-only action rejects a raw or proof-originated call lacking its immediately preceding
   nonce and protection set, including profile authorization, rerun, rejection resolution, forensic
   close, rebaseline, defer/abandon/resume, candidate discard, preflight retry,
   merge-contract recalibration, state import, and state-store promotion, without appending an event.
22. Target ruleset `ref_name` conditions and exact rule parameters apply to the configured target, a
   human merge succeeds, and parent-policy attestation expiration blocks publication until the
   separate interactive terminal command re-reads policy, receives explicit user confirmation, and
   appends the exact CAS-bound attestation without exposing an administration credential to Cockpit.

## 23. Observability and Audit

**[REQUIRED] Emit structured local events for proposal construction, proof, review, seal, push,
publication reconciliation, PR observation, acceptance verification, attention, supersession, receipt,
and cleanup.** Each event carries Change, Proposal, operation, attempt, actor/role, and exact commit IDs.

**[DIRECTION] Keep telemetry local and expose it through Cockpit SSE/history.** External OTLP or vendor
telemetry is unnecessary for correctness and remains a separate product decision.

Secrets, tokens, PR body content outside OwlBear’s managed block, and raw command output with possible
credentials are redacted before persistence.

## 24. Directional Decisions That May Change

These choices do not weaken the locked guarantees if implementation evidence suggests alternatives:

1. Exact Python module names and package boundaries.
2. Filesystem versus dedicated Git ref storage for local receipts, provided transactions and recovery
   are equally strong.
3. Exact managed ref and remote branch naming.
4. PR body formatting and sentinel syntax.
5. Whether publication is application-only or invoked by a narrowly tooled mechanical agent.
6. Cockpit layout and visual hierarchy.
7. Whether proof bundles store full output, digests plus locators, or tiered retention.
8. Whether completed-history reindex requires GitHub online or persists enough signed/raw provider
   evidence for later verification.

## 25. Explicitly Deferred Decisions

1. Non-GitHub acceptance surfaces and whether a public adapter abstraction is justified.
2. Local Cockpit acceptance that updates a target ref under an explicit user capability.
3. Automated policy acceptance for unattended Changes.
4. Squash/rebase equivalence and post-merge proof semantics.
5. Merge queues and synthetic merge-group identities.
6. Off-machine backup refs for mutable pre-seal work.
7. GitHub Issues as inbound idea intake.
8. GitHub Projects as a portfolio projection.
9. Cloud/Copilot/GitHub Actions task dispatch.
10. Container sandbox, model relay, and network egress policy.

None may be smuggled into the first redesign through a “generic” abstraction.

## 26. Rejected Alternatives

| Alternative | Reason rejected |
|---|---|
| Keep direct Integration with a cleanliness check | Racy and still mutates a checked-out target ref; cleanliness is not authority |
| Keep direct Integration as fallback | Preserves the catastrophic capability and creates two completion models |
| Mark completed when PR opens | Confuses publication with acceptance; target does not contain the Change |
| Mark completed when GitHub says merged | Does not prove the exact sealed proposal landed under a supported topology |
| Push every task/intermediate commit | Destroys the private correction window and triggers noise/cost for unreviewable states |
| Force-push a draft PR until ready | Makes reviewed identity mutable and complicates recovery/audit |
| One Issue per Task | Exports replannable detail, creates partial network transactions, and has no local coordination value |
| One PR per Outcome | Breaks Change atomicity; independently shippable Outcomes should be Changes |
| One Project per Change | A Project is a mutable portfolio view, not typed/versioned authority |
| GitHub as lifecycle source of truth | Cannot express OwlBear invariants and creates cross-store partial authority |
| Runtime code ban for MCP merge tool | OwlBear is not on the VS Code MCP call path; per-agent assignment and server policy are real controls |
| Copy Turbo’s engine/resources | No license grant and wrong control-plane ownership |
| Build cloud execution simultaneously | Multiplies trust and failure surfaces before the local safety model is proven |

## 27. Definition of Done

The redesign is complete only when all conditions hold:

1. **[LOCKED] No Delivery production code can mutate target refs or user worktrees.**
2. **[LOCKED] No agent can merge through assigned tools or credentials.**
3. **[LOCKED] Every Git-backed Change ends in an immutable Proposal, not direct publication.**
4. **[LOCKED] GitHub publication binds one exact Proposal to one PR head with read-after-write proof.**
5. **[LOCKED] Completion requires verified exact acceptance, not PR creation or an unverified merged flag.**
6. **[LOCKED] Rejection, staleness, correction, supersession, and unsupported merges are typed and safe.**
7. **[REQUIRED] Completed history is receipt-backed and integrity-checked.**
8. **[REQUIRED] Cockpit, MCP, agents, setup, docs, and tests expose only the new lifecycle.**
9. **[REQUIRED] Legacy Integration code and terminology are absent from active production surfaces.**
10. **[REQUIRED] Adversarial and end-to-end validation passes with an unrelated dirty user checkout.**
11. **[REQUIRED] Crash/retry testing proves exactly-once external effects through reconciliation.**
12. **[REQUIRED] The complete implementation receives independent architecture, security, and exact-
    commit review before Delivery is re-enabled.**

## 28. Current Recommendation and Confidence

Implement the narrow exact system first: local typed authority, immutable sealed Proposal, one GitHub
PR, human merge, exact two-parent/base-bound verification, local completion receipt, and no target or
user-worktree write capability anywhere in Delivery.

Do not dilute this with compatibility paths or expand it with Projects, task Issues, merge queues,
cloud runners, or multiple providers until the new lifecycle is operational and adversarially proven.

**Confidence:** high in the authority and safety model; medium-high in the initial merge topology until
it is validated against a live isolated GitHub repository and repository rules. The narrow topology is
deliberately fail-closed: unsupported real behavior produces attention rather than false completion.