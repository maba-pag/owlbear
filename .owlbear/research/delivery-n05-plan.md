# Delivery N05 — Exact-Head Merge Approval, Completion and Publication Continuity

> **Package:** N05 of the [execution plan](delivery-redesign-execution-plan.md#n05--exact-head-merge-approval-completion-and-publication-continuity).
> **Planned on:** `origin/dev` `ef622c354` (N01-A and N02-P merged; N01-B in review; N01-C and N02-A
> not started; Python 3.14.8). Lane C worktree, branch `redesign/n05-p-merge-approval-plan`.
> **Round 3:** lock, runtime and transport locators rechecked at `origin/dev` `58c4d928b` (N01 merged).
> **Status:** approved: plan gate `plan-sound` in round 12 of fresh GPT-6.1 Sol challenges (2026-10-03). Product code is unchanged by this phase. U1–U4 are pending user
> confirmation ([1.9](#19-user-decisions)); U4 is required before N05-B.

## 1. Contract

### 1.1 Result

- A Change whose exact reviewed head is published, ready and mergeable offers **Approve merge** in
  Cockpit and the same bounded approval in the continuation chat. The offer shows repository, PR,
  exact reviewed head, target branch and head, proof and required-check summary, and merge method.
- One approval authorizes one exact merge offer. Delivery's engine executes it through the provider
  adapter after a fresh re-read of PR state, head, stack, target, rules, mergeability and required
  checks. A head change invalidates the approval for any further request; a sent request stays
  fenced until provider evidence settles it (1.11). A target change follows the U3 policy. Delivery
  sends a merge only where the provider enforces the single-PR, approved-target scope (I10, U3).
- An unknown merge response is read back before any further request; a PR is never merged twice or
  merged without a matching approval.
- Completion is still observed exactly once by the existing acceptance owner when the finalized
  head merges, by the engine or manually in GitHub. A merge at any other head settles a merge
  attempt (M3) but yields acceptance attention, never completion or cleanup (programme §10.1).
  The completed worktree is cleaned automatically when eligible; unexpected contents are preserved
  and reported without reversing completion.
- Waits are distinct: required checks running, mergeability being computed, provider unavailable,
  merge in progress, and pending user approval (L1, L2 fixed).
- Governance states that engine/provider publication and an approved merge are system work and
  that agents never push or merge directly.
- PR-feedback repair has a durable, exact-head handoff and replay-safe thread replies (#225).

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | **Approve merge** in Cockpit and chat with repository, PR, exact head, target, proof and required-check summary, merge method | Execution plan §5 N05; programme §4.2, §10.2, J05–J06; R3 |
| R2 | Approval binds exact head and target; pre-merge provider re-read of PR state, head, stack, target, rules and checks; head change invalidates; target change and execution-time target race per U3 | §10.2; V19; V11 (approval part) |
| R3 | Unknown merge response is read back before any retry; no duplicate or unapproved merge | §6.1 unknown write; §10.2; V12 |
| R4 | Completion observed exactly once when the finalized head merges, including manually in GitHub; a merge at another head is acceptance attention, never completion | §10.1; §10.2; J06 |
| R5 | Automatic cleanup of an eligible completed worktree; unexpected contents preserved; cleanup status distinct from completion | §10.3; J07 |
| R6 | Distinct waits: checks running, provider outage, pending user approval | §10.3; §4.3 progress copy |
| R7 | L1: fresh provider observations are fenced into the readiness basis | Programme D02 deferred findings (L1); execution plan §2.2 |
| R8 | L2: a known-unmergeable PR shows its real reason, not `merge-approval-required` | Programme L2; execution plan §2.2 |
| R9 | Governance: engine/provider publication is system work; agents never push arbitrarily | §10.2 last paragraph |
| R10 | #225: durable handoff and replay-safe replies for PR-feedback repair | Issue #225 acceptance criteria |
| R11 | WP2 step 4 (sync, proof, publication, checks, acceptance in the continuation loop) and step 5 (exact-head merge approval) | WP2; P08, P09; R2 |
| R12 | N05-A editable paths disjoint from every N01 phase; mandatory companions; LC full form from N05-B | Execution plan §4.2, §1.4, §5 N05 |
| R13 | Support baseline: macOS and Ubuntu, Chromium-only Cockpit E2E, Python 3.14 | Execution plan §1.1 |

### 1.3 Invariants

- **I1 Exact offer.** No merge request is sent unless a recorded approval's `offer_id` equals the
  offer recomputed from a fresh provider observation immediately before the request: same
  repository, PR number and node ID, head SHA, base branch, target head, finalization ID, ready
  receipt ID, check observations, merge method and stack facts (I10).
  A merged PR fails I1; a series that released nothing then settles M2 or M3, never M1 (1.11).
- **I2 Fenced request.** Every merge request carries the approved head as GitHub's `sha` fence,
  `merge_action: "direct_merge"` and `bypass_rules: false`. Delivery never enables auto-merge,
  updates a PR branch through the provider, enqueues into a merge queue or bypasses rules.
- **I3 Readback first.** After a lost response, timeout, crash or unknown outcome, the owner applies
  the settlement contract ([1.11](#111-effect-settlement-contract)) before any further request.
  Terminal states come only from independently sufficient evidence; missing or expired readback
  evidence keeps an attempt or reply nonterminal. A submission's result settles only that
  submission; rows M1–M9 settle the request series. A pending request is adopted only when its
  reported head, method, action and bypass flag equal the approval's (D2).
- **I4 Completion owner unchanged.** `PortfolioApplication._observe_acceptance_once` stays the only
  caller of `DeliveryRuntime.complete_change`, guarded by the merged-PR latch
  (`tests/test_delivery_worktree_authority.py:81`, `:1252-1287`). A merge result is never a
  completion receipt; `CompletionEvidence` gains no field (it records no merge method, AC-13 of
  [worktree authority](delivery-change-worktree-authority.md)). Attempt settlement is not Change
  acceptance: a merge at another head (M3) settles only the attempt, and `_observe_acceptance_once`
  refuses it (`snapshot.head_sha != finalization.exact_head`) with `identity-mismatch` attention.
- **I5 No inferred approval.** Only the two adapters (Cockpit HTTP after a visible confirmation,
  MCP `approve_merge` with `confirmation="user-confirmed"`) create approvals. Proposal approval,
  readiness, the engine, the supervisor and workers never approve.
- **I6 Cleanup never forces.** Automatic cleanup uses the existing `ChangeWorkspaceManager.cleanup`
  path; computed attention (dirty, untracked, ownership, branch mismatch) stops before any
  mutation and is preserved and reported.
- **I7 Formats.** N05-A changes no persisted model. N05-B and N05-D register every new or changed
  persisted family in N02's registry, ship its registered migration and pass the LC full form.
- **I8 Locks.** Provider calls hold only the per-Change checkpoint lock, never a portfolio-wide lock
  (programme §5.2).
- **I9 One decision.** Readiness never offers **Approve merge** where acquisition or the merge owner
  would refuse for a known reason; both use the same offer computation (programme §5.4).
- **I10 Single-PR scope.** GitHub's async merge of a stacked PR includes all open downstack PRs,
  and a PR's `base` can change without a head change; the request fences only the head (P4). The
  offer and merge owner refuse a fresh read with `stack.size` > 1 (`merge-blocked/stacked`) or a
  base other than the approved target. A fresh read cannot exclude a later retarget or stack join,
  so a request is sent only where fresh provider facts enforce that scope until execution (U3
  part 2, G2); otherwise `merge-blocked/scope-unenforced` and the user merges in GitHub.
- **I11 Merge fence.** While a `MergeAttemptRecord` (one request series, 1.11) is not terminal,
  every other mutation of the Change (target sync, mark ready, review-repair preparation, worker
  acquisition) is refused with `merge-in-progress`; revocation follows its interface rule (1.5).
  Only series settlement releases the fence; D6 ledger settlement and head movement never do. The
  fence is read under the per-Change checkpoint lock through one lock-aware entry, checked before
  any effect and held through the mutation ([1.12](#112-mutation-fence-lock-entry)). Acceptance observation is
  exempt and runs only after the attempt is settled ([1.11](#111-effect-settlement-contract)); an unreleased
  series settles M2 or M3 on merged evidence, so a manual merge needs no revocation.

### 1.4 Persisted record families

New or changed persisted state. Each new family gets a new entry in N02-A's registry module
(`state_formats.py`, `FAMILIES`); each widened family (`coordination`, `action_result`, `retry_*`,
`recovery_*`) gets a version step with its registered migration (N02 plan §1.4, D2, D3). Per-Change
paths are relative to `.owlbear/delivery/runtime/changes/<change>/`; the coordination path is
relative to `.owlbear/delivery/`. Version numbers and the format-marker step are assigned at
implementation against the registry then on `origin/dev`.

| Family (proposed registry ID) | Path | Owner model (module) | Class | Identity over bytes | Phase |
| --- | --- | --- | --- | --- | --- |
| `merge_approval` | `merge-approvals/<approval_id>/approval.json` | `MergeApprovalRecord` (new `merge_approval`) | R | `approval_id` = SHA-256 of `offer_id` and `confirmation_id` (D4) | N05-B |
| `merge_approval_revocation` | `merge-approvals/<approval_id>/revocation.json` | `MergeApprovalRevocation` | R | `revocation_id` | N05-B |
| `merge_attempt` | `merge-approvals/<approval_id>/attempts/<operation_id>.json`; frozen bodies `merge-approvals/<approval_id>/request-bodies/<sha256>.json` (read-only, never rewritten) | `MergeAttemptRecord`: one request series per approval (1.11); per submission (first request and each M8 re-request): frozen body digest (file written before spawn, D16), process group ID and start time (after spawn), release record (before the release token), response, UUID or adopted `409` UUID; per series: a head-drift record (first drifted head; blocks M8, 1.11); series state `intent → released` (first release recorded) `→ pending` or `unknown →` terminal `merged`, `refused`, `head-changed` (M3 only) or `revoked-unsent`; an unreleased series reaches `merged` or `head-changed` directly on merged evidence (1.11) | M (bodies R) | file name = engine operation ID of the creating action; body file name = SHA-256 of its bytes | N05-B |
| `coordination` (changed) | `runtime/coordination/changes/<change>.json` | nested `ChangeContinuationAction`: kind `merge-pull-request`, `merge_approval_id`, `publication_observation_id`, `reconciles_operation_id` | M | nested | N05-B |
| `action_result` (changed) | `action-receipts/<op>/result.json` | `DeliveryEngineActionResult`: `merge` receipt, merge reasons | R | operation ID | N05-B |
| `retry_*`, `recovery_*` (changed) | `retry-ledger/**`, `invocations/*.json` | `RetryEpisodeKey` kinds `merge-pull-request` (effect: one reservation per submission; closing it counts budget only, 1.11) and `merge-readback` (D6); `RecoveryInvocationRequest.kind` (`recovery.py:53`) | M/R | unchanged | N05-B |
| `merge_retirement` (U4(b) only) | `merge-approvals/<approval_id>/retirement.json` | `MergeRetirementRecord` (`merge_approval`): hold snapshot, `confirmation_id`, provenance, time (U4) | R | `retirement_id` = SHA-256 of `approval_id` and `confirmation_id` | N05-B |
| `review_feedback_handoff` | `review-feedback/<handoff_id>/handoff.json`, `revisions/<digest>.json` | `ReviewFeedbackHandoff` (new `review_feedback`; kind `repair` or `no-repair`) | M (CAS revisions, R history) | `handoff_id` | N05-D |
| `review_reply` | `review-feedback/<handoff_id>/replies/<reply_id>.json`; frozen bodies `review-feedback/<handoff_id>/reply-bodies/<sha256>.json` (read-only) | `ReviewReplyReceipt`: frozen body digest (file written before spawn, D16); `intent → released` (release recorded) `→ posted` or `not-posted`; `unknown` until a marker hit (Y2); a CAS revision records a Y4 user decision before any transport: decision identity, `confirmation_id`, and `repost` with its replacement `reply_id` or `leave-unposted` (a user choice, never evidence; state stays `unknown`); 1.11 | M (CAS revisions) | `reply_id`; a replacement's `reply_id` = SHA-256 of the decision identity | N05-D |

Approvals live outside the frontier (D4), so frontier v18 and its 43 pinned writers stay unchanged.
Completion receipts, latches and observation receipts keep their bytes (I2 of N02).

### 1.5 Interfaces and error cases

| Interface | Phase | Behavior and errors |
| --- | --- | --- |
| `PublicationMergeProvider` (new runtime-checkable Protocol in `publication_provider.py`) | A | `read_merge_settings(repository, branch)`, `read_branch_head(repository, branch)`, `request_merge(RequestPublicationMerge, *, body_path, release)` (D16), `read_merge_request(repository, number, request_id)`, `read_merge_evidence(repository, number)`. Separate from `PublicationProvider` so existing fakes stay valid (D1) |
| `RequestPublicationMerge` | A | `repository`, `number`, `node_id`, `expected_head_sha`, `merge_method` (`merge`, `squash`, `rebase`); no bypass, queue or auto-merge field exists |
| `PublicationMergeRequestResult` | A | `status`: `pending` (`PendingMergeRequest`: UUID and the reported expected head, method, action, bypass flag), `merged` (merge commit), `refused` (`PublicationMergeRefusal`: `head-changed`, `not-mergeable`, `closed-or-draft`, `rules-failed`, `forbidden`, `queue-required`, `validation`), `unavailable` (UUID result `404`: expired or not found; readback evidence absent, never a refusal); bounded provider message |
| `PublicationMergeEvidence` | A | merged flag, head, base, stack (`size`, `position`, base ref and SHA; absent when not stacked), merge commit, merge-commit parents, merged-at; used for the offer (I10) and post-merge target verification (D9) |
| `PublicationMergeSettings` | A | allowed methods, viewer push permission, target rule types, merge-queue and up-to-date requirements (ruleset `strict_required_status_checks_policy`; unreadable classic protection counts as not enforced, F1); `execution_scope_enforced` (GitHub: `false` until A-R names an enforcing fact, G2; memory provider configurable) |
| Effect launcher (`effect_launcher.py`, new) | A | `freeze_body(request) -> bytes` (canonical JSON); `request_merge` refuses a `body_path` whose bytes differ, spawns the launcher, calls `release(group_id, start_time)` and writes the token only after it returns; a raised `release` closes the pipe (no request). Launcher: EOF, short token, digest mismatch or missing file → exit with no request (D16) |
| Transport errors | A | Existing `PublicationProviderError`; write timeout or unreadable write response → `RESPONSE_UNKNOWN`, `retry_safe=False`; GitHub `409` on merge-async → `pending` with the existing request's UUID and reported options (not an error); options missing → unknown, never matching |
| `MergeOffer` (projection on `DeliveryReadiness.merge_offer`) | B | Fields of I1 plus title, proof summary (finalization observation count, review ID), check summary (required passed/pending/failed, optional failed); `offer_id` excludes the title |
| `MergeHold` (projection on `DeliveryReadiness.merge_hold`) | B | Fields of [1.13](#113-held-merge-state-and-user-exit): `row` M6, M8, M9, or M7 only when `merge_reads_exhausted`; `cause` includes `pending-provider-request` (M7); null while not held, including M7 before exhaustion; computed from the attempt record, D6 ledger and fresh read; no persisted field, no N02 registry change |
| `PortfolioApplication.check_merge_status(change_id, approval_id)` | B | One 1.11 read per call; no request, reservation or budget reset (1.13); returns the settlement (on M3 with the acceptance attention it records) or the refreshed `MergeHold` (a matching `pending` under exhaustion: row `M7`, cause `pending-provider-request`); `ERR_DELIVERY_MERGE_NOT_HELD` when no nonterminal attempt matches `approval_id`; a failed read keeps the hold (`read-failed`) |
| `PortfolioApplication.retire_held_merge(RetireHeldMerge)` (U4(b) only) | B | Inputs `change_id`, `approval_id`, `confirmation_id`, `provenance`; contract of U4(b) (1.9): one fresh 1.11 read first (M2–M5 wins, no record); else writes the retirement record; no provider write; `ERR_DELIVERY_MERGE_NOT_HELD` unless held with `merge_reads_exhausted` |
| `PortfolioApplication.approve_merge(ApproveChangeMerge)` | B | Inputs `change_id`, `offer_id`, `confirmation_id` (one per visible confirmation), `provenance` (`cockpit` or `chat-user-confirmed`), `host_id`, `session_id`. Recomputes the offer from a fresh observation; idempotent per offer and confirmation; while an approval is live, returns it. Errors `ERR_DELIVERY_MERGE_OFFER_STALE` (carries the fresh offer or block), `ERR_DELIVERY_MERGE_UNAVAILABLE` (typed block), provider errors |
| `PortfolioApplication.revoke_merge_approval(change_id, approval_id)` | B | Allowed when no attempt exists or no submission has a release record (row M1; a recorded unreleased group is confirmed gone or killed first; settled `revoked-unsent`, fence released); a fresh read showing the PR merged settles M2 or M3 instead and returns it; else `ERR_DELIVERY_MERGE_IN_PROGRESS` |
| Engine action `merge-pull-request` | B | Acquired through `acquire_change_action` when a live approval exists; executed by `execute_change_action`. Results: `completed` (row M2, `PullRequestMergeReceipt`), `waiting/merge-in-progress` (M7), `stale/readiness-changed` (no request sent), terminal `head-changed` or `refused` (rows M3–M5: series and approval end, custody and fence released; M3 then yields acceptance attention, not completion), `merge-response-unknown` (M6: head drift, consent withdrawn; M8 without a permitted re-request; M9: read failed, transport open, foreign pending request). One submission's refusal is terminal only when it completes M4 or M5; otherwise the series stays in M6, M8 or M9. Head drift never ends a released series. `waiting/merge-in-progress` and `merge-response-unknown` are non-terminal: the next acquisition yields a reconciliation successor (D6) |
| New readiness reasons | B | `merge-approval-required`, `merge-approved`, `merge-in-progress`, `merge-checking`, `merge-blocked` (with `merge_block`: `conflicts`, `behind`, `protection`, `draft`, `closed`, `checks-failed`, `queue-required`, `stacked`, `scope-unenforced`, `target-unenforced`, `capability-unavailable`, `method-not-allowed`), `checks-running`, `provider-unavailable`, `merge-response-unknown` (with `merge_hold`, 1.13); `merge-retired-unsettled` (U4(b) only) |
| `DeliveryReadinessBasis` | B | Adds `publication_observation_id` and `merge_approval_id`; acquisition of `mark-ready`, `observe-acceptance` and `merge-pull-request` returns `stale` when a fresh observation differs (L1) |
| MCP `approve_merge`, `revoke_merge_approval`, `check_merge_status` | C | Strict models; `approve_merge` annotated destructive and requires `confirmation: "user-confirmed"` and a `confirmation_id`; `check_merge_status` is not destructive; the continuation calls it once per user Check answer (1.13); under U4(b) `retire_held_merge` is annotated destructive and requires `confirmation: "user-confirmed"` and a `confirmation_id` |
| HTTP `POST …/changes/{change_id}/approve-merge`, `…/approve-merge/revoke`, `…/merge-status/check` | C | Approve, then run the merge engine action and the single-Change acceptance reconciliation in one request; `409` stale offer with the fresh offer, `409` in progress, `503` provider unavailable; `merge-status/check` runs one `check_merge_status` (`409` not held); under U4(b) `…/merge-status/retire` runs one `retire_held_merge` (`409` not held) |
| MCP `record_review_feedback_handoff`, `show_review_feedback_handoff`, `post_review_feedback_replies` | D | Handoff CAS revisions bound to PR and head, and to the repair invalidation (`repair`) or the current finalization (`no-repair`); replies posted by the engine under D13 custody and settled by 1.11 rows Y1–Y4; `post_review_feedback_replies` takes optional `unknown_reply_decisions` (`repost` or `leave-unposted` per reply, each with its answer's `confirmation_id`) only with `confirmation: "user-confirmed"`; a decision persists before any transport and replays per 1.11; errors `ERR_DELIVERY_REVIEW_HANDOFF_STALE`, `…_MISSING`, `…_INCOMPLETE`, `ERR_DELIVERY_REVIEW_REPLY_DECIDED` (a different decision for a decided reply; returns the accepted one) |

### 1.6 Existing owners to reuse

Source locators at `ef622c354`. Symbols moved by N01 are re-resolved by name at implementation.

| Owner | Locator | Use |
| --- | --- | --- |
| Provider contract | `publication_provider.py:225-257` (`PublicationProvider`), `:55-90` (`PublicationPullRequest`, `mergeable`/`merge_state_status` excluded from dumps at `:69-70`) | Extend beside, not inside (D1) |
| GitHub CLI transport | `owlbear_delivery_github/github.py:806-910` (`_rest`, `_graphql`, `_execute`, `_raise_command_failure`), `:716-796` (merged readback), `:31` (API version `2026-03-10`) | Add fixed merge operations and operation-specific status parsing |
| In-memory provider | `owlbear_delivery_github/memory.py:21-184` | Deterministic merge fake with fault injection |
| Provider and forbidden-effect gates | `tests/test_delivery_worktree_authority.py:83-129`, `:1080-1095`, `:1417-1430`, `:1603-1629` | Revise to an allowlist (D11) |
| Acceptance owner | `portfolio_application.py:288-345` (`reconcile_awaiting_acceptance`), `:547-624`, `:645-788` (`observe_acceptance`, `_observe_acceptance_once`), `:784-` (latch) | Unchanged completion path; cleanup hook after completion |
| Engine actions | `application_acquisition.py:263` (`acquire_change_action`), `:519` (`_acquire_engine_action`), `:758-801` (execute; `:797-798` maps waiting to `merge-approval-required`), `:862-931` (preflight), `:936-971` (owners); `application_models.py:1164-1258` (`DeliveryEngineActionResult`); `change_workspace.py:498-519` (`ChangeContinuationAction`), `:2096-2205` (journal) | Add `merge-pull-request` |
| Readiness | `application_readiness.py:1962-2016` (snapshot and observation cache), `:1203-1256` (action basis, target sync only before finalization), `:1546-1557` (`publication-wait`), `:1086-1095` (failure classes); `work_items.py:261-311` (basis, reasons), `:1020-1080` (awaiting-merge and draft cards) | L1, L2, offer, distinct waits |
| Target sync after finalization | `application_publication.py:118-170` (returns PR to draft before head change), `delivery_runtime.py:3923-3975` (conflict invalidates finalization) | U3 strict route |
| Mark ready and checks | `application_publication.py:743-799`; `publication_provider.py:193-222` (check classification) | Required-check semantics for the offer |
| Cleanup | `application_lifecycle.py:130-168`, `:242-248`; `change_workspace.py:3816-3866` (`cleanup`, attention before mutation) | Automatic cleanup (D10) |
| Supervisor sweep | `checkpoint_supervisor.py:65-69` calls `reconcile_pending_checkpoints` (`application_publication.py:1121`) | Host the cleanup sweep |
| Mutability policy and locks (at `58c4d928b`) | `runtime_support.py:59` (`_require_change_mutable`, pure, frontier only); `portfolio_application.py:1738` (`_runtime`, before the lock), `:1798` (`_checkpoint_lock_root`); `storage_io.py:43` (`locked_roots`, fresh descriptor); `application_acquisition.py:975` (`_engine_checkpoint_lock`); `application_lifecycle.py:765` (bounded attention lock); `workspace_coordination.py:83-92`, `:604` (`PublicationLock` token) | I11 fence and lock entry (1.12) |
| Review repair | `application_publication.py:853-980` (`prepare_review_repair`); `share/skills/w-address-pr-feedback/SKILL.md:24-262` | #225 handoff |
| N02 registry, migration, LC | [N02 plan](delivery-n02-plan.md) §1.4, §1.5, §3.3 (`state_formats`, `state_migration`, `delivery-lc`) | Register N05 families |
| Assembled proof | Default loader, `Client(assemble_target_server(...))`, Cockpit HTTP client, `start-work-portfolio-stack.mjs` | Fakes only below the provider (fake `gh`, P10) |

### 1.7 Exclusions

Merge queues and auto-merge (queue-required targets fall back to manual merge, D7); provider update
of a PR branch; squash or rebase unless U1 selects them; any provider other than GitHub.com through
`gh`; deployment or post-merge verification; Cockpit **Open in Copilot**; retiring
`/address-pr-feedback` (N09-B); live activation of N05 (N10-M); changing `CompletionEvidence`.

### 1.8 Decisions

Agent-settled with probe evidence:

- **D1 Separate merge protocol.** `PublicationMergeProvider` sits beside `PublicationProvider`.
  Existing fakes in `serve/delivery/tests/test_draft_pull_request.py` and the `isinstance` checks in
  `serve/delivery-github/tests` stay valid (P12); the application detects merge capability with
  `isinstance` and reports `capability-unavailable` otherwise.
- **D2 Asynchronous merge API.** `PUT repos/{o}/{r}/pulls/{n}/merge-async` with `sha`, `merge_method`,
  `merge_action: "direct_merge"`, `bypass_rules: false`; poll `GET …/merge-async/{uuid}`; read back
  with the PR read and a merge-commit query. GitHub recommends it over `PUT …/merge`; it returns the
  pending request's UUID and options on a repeated request (`409`) and `200` when already merged,
  which makes the readback-then-request rule of I3 idempotent (P4). A `409` request is adopted only
  when its `expected_head_sha`, `merge_method`, `merge_action` and `bypass_rules` equal the approved
  head, U1 method, `direct_merge` and `false`; otherwise the attempt stays `merge-response-unknown`
  and no request is sent. Rejected: synchronous `PUT …/merge` (no
  request identity; `405`/`409` only) and GraphQL `mergePullRequest` (synchronous, same head fence,
  no request identity). Neither API fences the base (P2, P4).
- **D3 N05-A changes no persisted bytes.** New models are transport-only; existing models are not
  edited; new names are imported from `owlbear_delivery.publication_provider`, not the package root,
  so `owlbear_delivery/__init__.py` and N01's surface fixture stay untouched.
- **D4 Approvals outside the frontier, one per confirmation.** `approval_id` = SHA-256 of
  `offer_id` and `confirmation_id`: a retried submission of one confirmation is idempotent; a new
  confirmation of the same offer is accepted once the earlier approval is terminal (revoked,
  refused, head-changed or invalid at use). At most one approval per Change is live. Validity is computed
  at use (I1), so head, target, finalization or check changes invalidate without a frontier write.
  After a release, invalidation stops only further submissions; the series settles by 1.11.
  The frontier and its writers stay unchanged; the central mutability policy gains only the I11
  fence, read from the attempt store (no frontier field).
- **D5 Merge as an engine continuation action.** `merge-pull-request` binds `merge_approval_id` and
  `publication_observation_id` in `ChangeContinuationAction` and reuses the D02 journal
  (`intent`, `started`, `result`). A per-approval `MergeAttemptRecord` persists the request series:
  per submission its frozen body before spawn, its group after spawn, its release record before the
  release token (D16), and its response and async UUID after.
- **D6 Interrupted or pending merge reconciles by readback.** D02 turns any started-without-result
  action into `engine-action-interrupted` containment (`application_acquisition.py:779-801`), and
  `execute_change_action` returns a persisted result as-is and releases custody for `waiting`
  (`:758-776`). The approved bounded-recovery boundary (programme §1.1, 2026-09-25) allows automatic
  reconciliation of engine-owned effects whose owner can establish exact identity, completion and
  exclusion. For `merge-pull-request` only (every other kind keeps D02 containment):
  - *Immutable results, successor records.* A persisted result is never rewritten; its replay stays
    exact. A non-terminal result or a started action without result leaves the attempt non-terminal;
    the next acquisition yields a successor action with a new operation ID and
    `reconciles_operation_id`. A successor reconciles the original external effect; it is not a
    new effect attempt.
  - *Readback precedence.* The successor takes a fresh provider read and applies rows M1–M9 of
    [1.11](#111-effect-settlement-contract) in order; it sends a request only under row M8.
  - *Ledger accounting.* `RetryEpisodeKey.engine` excludes operation IDs, `reserve` contains an
    episode with an outstanding attempt, and `_record_engine_attempt_result` counts `waiting` as
    failure (`recovery.py:434-440`, `:1295`; `application_acquisition.py:711`). For merge kinds:
    the effect episode `merge-pull-request` reserves one attempt per submission, before the
    transport starts. Series settlement closes the outstanding reservation (row M2 → progress;
    M3–M5 → failure); an M8 re-request first closes it as a failure count. Closing a reservation
    counts budget only: it settles no submission or series and never releases the fence (1.11).
    Successors reserve in a separate `merge-readback` episode, so an outstanding effect
    reservation never blocks them. A row M7 (`pending`) read is a non-consuming backoff wait;
    every M8 or M9 read consumes one attempt. A readback reservation left by a crash settles as a
    failed read (reads have no effect).
  - *Bounded resumption.* One predicate, `merge_reads_exhausted`, is true when either episode
    (`merge-readback` or `merge-pull-request`) has a stop code. It alone decides automatic-read
    eligibility, `merge_hold.automatic_reads`, the actor, `human` acquisition and background
    suppression (1.13). Once true, readiness keeps `merge-response-unknown` with `merge_hold` and
    the **Check merge status** route: one read per user check, applying 1.11. Neither episode
    resets; a user check that reads M7 keeps the hold (row M7, 1.13) and restores no automatic
    polling; no request is sent;
    background reconciliation reads nothing.
  - *Settlement order.* Defined once in [1.11](#111-effect-settlement-contract) and shared by the
    merge owner, readiness and `_observe_acceptance_once`. Revocation settles row M1
    `revoked-unsent`. Head drift is recorded on the series and withdraws consent for further
    submissions (no M8, even if the head returns); it settles nothing. Only M2–M5 end a series.
  - *Mutation exclusion.* I11 holds while the attempt is non-terminal, even after continuation
    custody is released.
  - *Controller exclusion is not transport closure.* The checkpoint lock (G11) only excludes a
    second executor. Each submission runs through the release-gated launcher (D16) in its own
    process group (N02 plan D8 runner: `start_new_session`, `killpg` on timeout), so a released
    `gh` can outlive a killed controller. A group is recorded before its release, so every released
    submission has a recorded group. Transport closure (every released submission's group gone,
    1.11) is necessary for row M8, never sufficient for a terminal state.

  N05-B proves the lock and transport premises first (subprocess tests); if either fails, D6 falls
  back to D02 containment.
- **D7 Capability boundary.** Merge is offered only when the provider implements D1, the viewer
  can push, the U1 method is allowed, the target requires no merge queue, the PR is not stacked,
  the execution scope is enforced (I10) and, under U3(d), the target enforces up-to-date branches.
  Otherwise readiness shows `merge-blocked` with its block (`capability-unavailable`,
  `queue-required`, `stacked`, `scope-unenforced`, `target-unenforced`) and "merge in GitHub"
  guidance; a manual merge is still observed (R4).
  `delivery_health` reports the capability, so setup explains the limit before the last step
  (programme §4.2).
- **D8 L1 fence.** Readiness refreshes an expired cached observation in every publication phase,
  not only before ready (P8). Provider failure yields `provider-unavailable`, never stale data. The
  basis carries `publication_observation_id`; acquisition of a publication action takes a fresh
  observation under the checkpoint lock and returns `stale` when it differs.
- **D9 L2 classification.** Mergeability `UNKNOWN` → `merge-checking` (bounded re-read; GitHub
  computes it lazily, P3); `CONFLICTING`/`DIRTY` → `merge-blocked/conflicts` → target sync route;
  `BEHIND` → per U3; `BLOCKED` → `merge-blocked/protection` (act in GitHub); draft or closed → their
  block; failed required checks → `checks-failed`; pending required checks → `checks-running`.
  Only `CLEAN`, `HAS_HOOKS`, or `UNSTABLE` with no failed required check are offerable. After a
  merge, parent 1 of the merge commit is compared with the approved target head; a difference is
  reported as `target-advanced-during-merge` evidence (the race that no API fences, P2, G2; under
  U3(d) the enforced rule refuses it instead).
- **D10 Automatic cleanup.** Immediately after a completion is recorded, under the same checkpoint
  lock, call the locked cleanup variant (`_cleanup_change_worktree_locked`; re-taking the flock in
  one process would deadlock). The supervisor sweep (`reconcile_pending_checkpoints`) retries each
  completed Change with a retained worktree at most once per controller process. Attention stays
  computed and is shown in the retained-worktree and completed views; nothing is forced.
- **D11 Gate becomes an allowlist.** The forbidden-effect tests keep forbidding auto-merge,
  `enablePullRequestAutoMerge`, update-branch, `enqueuePullRequest`, `merge_queue`,
  `bypass_rules: true` and any merge call outside allowlisted provider functions. `merge_method` is
  allowed only in an enumerated set of files (provider, N05-B and N05-C modules declared here);
  acceptance, latch, completion and observation models keep no merge-method field.
- **D12 Governance text.** Delivery publishes Change branches, draft PRs and state, and merges only
  after an exact-head user approval; agents never run `git push`, `gh pr merge` or provider
  mutations directly (the programme-specific `redesign/*` push exception of execution plan §1.2
  stays).
- **D13 #225 in Delivery.** The handoff is a Delivery record, not chat output; replies are posted by
  an engine operation through the provider with a hidden per-reply marker. Reply writes are
  serialized per handoff under one mutation-fence entry (1.12) and run through the release-gated
  launcher (D16): frozen body before spawn, group record, then release record. Settlement follows rows
  Y1–Y4 of [1.11](#111-effect-settlement-contract): transport closure and marker-negative reads
  never prove non-execution, so an `unknown` reply is never reposted automatically (G12, G13). A
  user `repost` persists its replacement `reply_id` before any transport; a replay resumes it.
  External comments stay evidence, never Design or Delivery authority.
- **D14 Chat approval trust.** The MCP tool cannot verify that the user answered. The continuation
  workflow must obtain an explicit answer in the same session, the tool is annotated destructive so
  VS Code prompts unless the user auto-approved it, and the record keeps `chat-user-confirmed`
  provenance and that answer's `confirmation_id` (G3). Y4 reply decisions follow the same rule.
- **D15 No time expiry.** Approvals do not expire by time; I1 re-verifies every fact at execution.
- **D16 EOF-safe effect entry.** `gh api --input -` passes stdin to `client.Do` unbuffered
  (v2.65.0 `api.go` `openUserFile`, `http.go`), so a dead controller's closed stdin can send an
  empty `PUT`; merge-async then defaults `sha` to the current head and the action to `default`.
  Merge and reply writes therefore enter through a release-gated launcher (option b, using a's file):
  1. Before spawn the owner durably writes (write, `fsync`, rename, directory `fsync`) the frozen
     body, the canonical JSON of the approved request with every field (`sha`, `merge_method`,
     `merge_action`, `bypass_rules`), to a read-only content-addressed file and records its digest.
  2. The runner spawns new `owlbear_delivery_github/effect_launcher.py` in a new session. It opens
     no connection and blocks on a fixed-size release token (operation ID and body digest) on stdin.
  3. The owner durably records the group's ID and start time, then a release record, then writes
     the token. Only the runner holds the pipe's write end (`close_fds`), so controller death is EOF.
  4. The launcher reads the whole token, re-hashes the file, sets stdin to `/dev/null` and, only on
     an exact match, `exec`s `gh api … --input <file>` in the same group; `gh` sends the file with
     `Content-Length` from its size. EOF, a short token, a mismatch or a missing file exit unsent.
  - Possible submission starts at the durable release record (1.11). Absence of a group record
    proves nothing; absence of a release record proves `gh` never ran (rows M1, Y1).
  - Rejected: (a) alone leaves `gh` effect-capable before its group is recorded, so an unrecorded
    live child can never be shown closed; (c) adds a second transport with token, proxy and TLS
    handling, larger than one launcher module.
  - Other existing provider writes keep `--input -`; they are not 1.11 effects.

### 1.9 User decisions

Each is **pending user confirmation**; the recommendations are defaults, not decisions. N05-A
depends on none of them; nothing in N05-P depends on them.

**Execution-plan amendment.** The deltas F1–F8 of [1.10](#110-premise-findings-and-execution-plan-deltas)
amend the execution plan's rules and schedule notes (its §1.1): merged under the user's overnight
authorization of 2026-10-03; explicit confirmation pending.

**U1 — Merge method and authority scope** (pending user confirmation — required before N05-B starts).
Status quo: Delivery cannot merge. The older design locked this
([acceptance redesign](delivery-proposal-acceptance-redesign.md) line 1050: "OwlBear agents and
Delivery services cannot merge"), enforced by gates added in `09b98bfc9` and stated in
`setup/operating-owlbear.md:306`. The approved execution plan supersedes it for N05 (§5 N05 result).
The repository allows merge, squash and rebase (P1). Problem: the engine must send a method; squash
and rebase create new commits, so the exact reviewed head is not in target history and the
parent-1 target check (D9) does not apply. Options:
(a) merge commit only, direct merge, never bypass, auto-merge, update-branch or queue; one approval
per merge in Cockpit or chat; targets that disallow merge commits show `method-not-allowed`;
(b) the user picks a method in each approval among those the repository allows;
(c) a per-repository method in Delivery config (config family v3 with a registered migration).
**Recommended default: (a).** It keeps the reviewed head in history, matches this repository's
existing "Merge pull request #N" history and keeps every check exact.

**U2 — Real merge rehearsal on a disposable repository** (pending user confirmation — required
before step A-R; A-R gates N05-B's merge). Status quo: probes are read-only; execution plan §1.3
requires a disposable repository and the user's permission for provider mutation tests. Problem:
GitHub's async merge semantics (UUID on `409`, `400` for drafts, rules failures, readback, head
fence) are documented but unexecuted (G1). The token has scopes `gist, read:org, repo, workflow`
and no `delete_repo` (P1). Options: (a) the user creates a disposable private repository and
permits the agent to push branches, open PRs and merge there during A-R; (b) the agent creates the
repository (deletion stays the user's); (c) no rehearsal; fakes only; G1 then blocks N10-H and
engine merge stays `scope-unenforced` (G2).
**Recommended default: (a).**

**U3 — Target freshness and the execution-time target race** (pending user confirmation — required
before N05-B starts). Status quo: readiness offers target sync only before finalization
(`application_readiness.py:1242-1256`); after finalization a moving target is not re-proved. The
target ruleset of `dev` has only deletion and non-fast-forward rules, so GitHub does not require an
up-to-date branch (P1). Problem, part 1 (proof): the programme requires "sync, revalidation and
fresh review where the proof depends on it", which Delivery cannot judge per change. Options:
(a) strict: offer approval only when the finalized proof's target equals the current target head;
otherwise sync, refinalize and re-review automatically through existing owners (P13);
(b) informed: the offer shows proof target and current target; the user may approve; conflicts
and `BEHIND` still sync; (c) repository-driven: strict only where the target requires up-to-date
branches, otherwise (b). **Recommended default: (a).** It never attributes old proof to a new merge
result (V11). Its cost is agent proof time when the target moves often; the user acts once per
proven state.
Problem, part 2 (execution): GitHub merges in the background after Delivery's final read, and no
merge API fences the target (P2, P4). Even under (a) the target can advance before execution;
post-merge detection (D9) cannot undo that. Programme §10.2 requires enforced protection or queue
semantics where the target cannot be fenced. Options:
(d) enforced: engine merge only where the fresh rules read shows the target requires up-to-date
branches (merge queues stay excluded, D7); otherwise `merge-blocked/target-unenforced` and the
user merges in GitHub. On `dev` this needs the user to add that rule; agents never change settings;
(e) detection-only: the user accepts, as a dated requirement revision of programme §10.2 that
passes the plan gate, that the target may advance during execution; Delivery reports
`target-advanced-during-merge` and claims no stronger guarantee.
Under (d) and (e) alike, engine merge also needs an enforced execution scope (I10): the request
fences only the head, a `base` retarget or stack join after the final read changes what merges
(P4), and the (d) rule binds only the branches it targets. Engine merge runs only where fresh
provider facts make a merge outside the approved PR and target impossible until execution, shown
by A-R evidence (G2); otherwise `merge-blocked/scope-unenforced` and the user merges in GitHub. No
such fact is known at N05-P.
**Recommended default: (d).** It is the only option that meets §10.2 as written.

**U4 — Exit from an unsettled merge** (pending user confirmation — required before N05-B starts;
N05-A and A-R do not depend on it). Question: "When an issued merge remains unknown after readback
expiry, should Delivery require indefinite containment until provider settlement, or permit
explicit retirement without merging, while retaining the unresolved attempt, prohibiting further
submissions and preserving later status checks?"
Status quo (1.11, 1.13): a released series ends only by M2–M5. Once a submission is `unavailable`
(response lost, UUID expired after 24 h, P4), no refusal can arrive, so only a merge in GitHub
ends the hold; a user who does not want the merge keeps a held Change in active work for good.
Problem: GitHub offers no cancellation of a pending async merge (P4), and closing the PR excludes
nothing (it can reopen). Any exit without a merge leaves a request that may still execute, so
Delivery must not claim cancellation or settlement, nor attribute a later merge to reviewed proof
(programme §10.1–10.2). Options:

(a) **Indefinite containment** (current text of 1.11 and 1.13). Exits only by provider settlement
evidence on a check (M4, M5) or the user merging in GitHub (M2 → completion; M3 → acceptance
attention). N05-B adds nothing. Cost: actor you and a `human` continuation result until then.

(b) **User-confirmed non-merging retirement.** N05-B and N05-C implement this contract:

- *Entry.* `retire_held_merge(change_id, approval_id, confirmation_id, provenance)`: Cockpit
  after a visible confirmation; MCP with `confirmation="user-confirmed"` (D14, destructive);
  HTTP `POST …/merge-status/retire`. Allowed only while held with `merge_reads_exhausted`;
  otherwise `ERR_DELIVERY_MERGE_NOT_HELD`.
- *Order.* Under one fence entry (1.12) it first takes one 1.11 read. A match of M2–M5 wins: that
  settlement is returned and nothing is retired. Otherwise it writes `MergeRetirementRecord`
  (family `merge_retirement`, 1.4) with the hold snapshot (row, cause, per-submission states).
  First write wins; a replay or a later confirmation returns the existing record. The write is an
  attempt-store write, exempt from I11 like the attempt record (1.12).
- *Disposition.* A distinct terminal Change disposition `retired-unsettled`, derived from the
  record: neither `abandoned` nor `completed`; no frontier field (v18 and its writers unchanged).
  Readiness `merge-retired-unsettled`, actor none; the work list shows it as retired; ordinary and
  batch continuation skip it (no `human`, no loop); background reconciliation never reads it.
- *Kept.* Attempt record bytes and state `unknown`, visible in detail and diagnostics. The I11
  fence: every Change mutation, including abandonment, deferral, target sync, mark ready, repair
  and worker acquisition, is still refused with `merge-in-progress`. The approval never becomes
  terminal, so D4 accepts no further approval and no submission is ever sent for this Change.
  D6 ledgers, the worktree and the branch (no cleanup: neither completed nor abandoned; D10 sweep
  skips it). The PR: Delivery never closes it; closing it in GitHub still settles nothing.
- *Released.* Active-work membership and prompts only. No lock is held after the write; checks
  take the per-Change checkpoint entry as before.
- *Later checks.* **Check merge status** stays available: read-only, one 1.11 read, no request or
  reservation, never automatic. A merge (M2 or M3) settles the series as in 1.11 and releases the
  fence, but the acceptance owner records acceptance attention, never completion:
  `_observe_acceptance_once` reads the retirement record before the latch and calls
  `capture_acceptance_attention` with the existing `identity-mismatch` reason and diagnostic
  `retired-unsettled:<retirement_id>` (no enum or frontier change). M4 or M5 settles `refused` and
  releases the fence; the Change stays retired. After either, the existing attention route and
  abandonment intent apply.
- *Text.* "Delivery will not merge this Change. A request sent earlier was not cancelled and may
  still merge in GitHub; if it does, Delivery reports it for attention." Never "cancelled",
  "settled" or "closed".

(c) **Defer under hold** (existing owners). The `defer` intent (`set_change_intent`,
`DeliveryRuntime.defer_change`) and `resume_change` become I11-exempt for a held Change only. It
leaves active work, keeps attempt, fence, approval and worktree, and is reversible; no new
family. But deferral writes the frontier and moves the stage to `deferred`, and
`capture_acceptance_attention` requires `entered_from` = current stage (`awaiting-merge`): a check
while deferred settles the series (M2–M5) but runs acceptance only after `resume`. The Change
stays nonterminal for good.

**Recommended default: (b)** under this explicitly approved contract. It ends active work without
claiming any provider fact, never sends again and keeps every later observation.

### 1.10 Premise findings and execution-plan deltas

Findings against the execution plan and programme, with evidence. The N05-P PR applies these
deltas to the execution plan (amendment recorded in [1.9](#19-user-decisions)).

| # | Finding | Evidence | Execution-plan delta (applied) |
| --- | --- | --- | --- |
| F1 | The provider cannot re-read classic branch protection with WRITE permission; protections are visible only as rules and `mergeStateStatus` | `GET branches/dev/protection` → 404; `viewerCanAdminister: false`; `rules/branches/dev` readable (P1) | §5 N05: "re-reads PR state, head, target, rules, mergeability and checks" |
| F2 | No GitHub merge API fences the target; this repository has no up-to-date rule or merge queue, so the target fence is pre-read plus post-merge detection only | P2, P4; ruleset 14785182 = `deletion`, `non_fast_forward` | §5 N05: no provider-side target fence; enforced rules or U3 decide (G2) |
| F3 | The forbidden-effect gates assert that Delivery cannot merge anywhere; N05-A must revise them | `tests/test_delivery_worktree_authority.py:1417-1430`, `:1603-1629`; P6 | §5 N05-A: revises the no-merge gates to an allowlist (N01 §3.7 allows the file) |
| F4 | `merge-approval-required` is an engine-result reason, not a readiness reason; Cockpit has no mirror | `application_models.py:1169-1176`; `work_items.py:274-311`; `workItems.ts:67-120` | §5 N05: N05-B owns it as a readiness reason, with companions |
| F5 | N05-B and N03 phases list shared core modules (`application_readiness.py`, `application_acquisition.py`, `work_items.py`, `workspace_models.py`), so §4.3's ready rule serializes them despite the stage-3 lane split | §4.3 ready rule bullet 4; N05-B paths ([3.4](#34-n05-b--approval-merge-action-readiness-and-cleanup)) | §4.3 schedule note: stage 3 runs N03 and N05-B…D sequentially where paths overlap |
| F6 | N05-B and N03-A both bump N02's format marker; the second to merge must renumber its migration and rerun LC full form | N02 plan D3 | §4.2 note (adds no prerequisite) |
| F7 | Reason text renders from `workItemPresentation.ts`, not only `WorkItemDetail.tsx`/`WorkPortfolioPage.tsx` | `workItemPresentation.ts:58-64` | §1.4 companion list: add `workItemPresentation.ts` |
| F8 | New N05 decision U3 (target freshness and execution-time target race) | §1.9 | §7 "Decided later": add U3 to N05 |
| F9 | Package-plan prerequisites added: N05-B needs U1, U3 and U4 answered; N05-B merge needs A-R evidence or U2(c); engine merge needs A-R scope evidence (G2), else `scope-unenforced` | §1.9 | None (§4.2 allows package-added prerequisites) |

No phase is re-split; §4.2 dependencies are unchanged.

### 1.11 Effect settlement contract

One procedure settles both external effects. Under one mutation-fence entry (1.12) the owner takes
a fresh provider read and applies its effect's rows in order; the first match wins, and M1 excludes a
merged PR (below). Readiness, acquisition, the merge owner, `_observe_acceptance_once` and the reply
owner share it. Acceptance attention, latch, completion and publication-state writes run only after
it (exempt from I11).

- Effect entry follows D16: frozen body before spawn, group record, release record, then token.
- Merged evidence precedes M1. M1 needs a read that does not show the PR merged; an unreleased
  series whose PR merged outside Delivery settles M2 or M3 with zero requests, no revocation.
- Before that settlement, a recorded unreleased group is confirmed gone or killed, as for
  revocation (1.5). It could not send anyway: the entry excludes any owner that could release it,
  and without a token it exits on EOF (D16).
- Possible submission starts at the durable release record; `gh` cannot run before the token.
- An ambiguous spawn (death before, during or after spawn) with no release record has no possible
  submission; one with a release record is possibly submitted and stays nonterminal.
- After possible submission, a terminal state needs independently sufficient provider evidence of
  merge, refusal or cancellation. Expiry, absence, timeouts and transport closure are not evidence.
- Merge may re-request (M8): GitHub returns the live pending request on `409` and a PR merges at
  most once. A reply has no provider de-duplication, so a re-post needs a user decision (Y4).
- A merge attempt is one request series: its first request and every M8 re-request are
  submissions under one approval, each with its own group record, response and UUID, if any. A
  submission answered `409` and adopted shares the adopted UUID's result.
- A submission result settles only that submission; rows M1–M9 settle the series. A refusal of
  one submission never excludes an earlier one's effect: GitHub documents independent failures
  (`403`; `422` "validation failed, or the endpoint has been spammed") and no cancellation of a
  pending request by a later one (P4 reference, rechecked in round 4).
- D6 ledger settlement of an effect reservation counts budget only. It settles no submission or
  series and never releases the fence.
- Attempt settlement is not Change acceptance. M2–M5 release the fence; only M2 can lead to
  completion, through `_observe_acceptance_once` at the finalized head. M3 content is unreviewed:
  no completion receipt, no D10 cleanup (programme §10.1–10.2).
- "Transport closed" means every released submission's recorded process group is confirmed gone
  (G12). A release record without a group record is a defect and settles M9 or Y4, never M1 or Y1.
- Head drift (PR unmerged, head ≠ approved head) withdraws consent for further submissions. An
  evaluation that reads it first records it durably on the series; M8 never applies again, even if
  the head returns. Drift settles nothing: a released request keeps its `sha` and may execute once
  the head returns (P4), so the execution-time fence proves no cancellation or exclusion.
- A released series ends only by M2–M5: every possible submission needs its own refusal or UUID
  result, or the PR is merged. Otherwise pending submissions stay in M7, the rest in M6 or M9.
  An unmerged or closed PR excludes nothing (it can return to the approved head or reopen).

| Row | Effect | Evidence (fresh read; first match wins) | Settlement | Fence and next step |
| --- | --- | --- | --- | --- |
| M1 | Merge | No submission has a release record (a group may be recorded; D16); the read does not show the PR merged (a failed read qualifies) | No possible submission: no token was written; stays `intent` | Revoke → recorded unreleased group gone or killed, then `revoked-unsent`; else send under I1 |
| M2 | Merge | PR merged; merge evidence head = approved head (series released or not) | `merged`; from `intent` with zero requests when unreleased | Unreleased: recorded group gone or killed first. Receipt with D9 parent-1 check (zero submissions when unreleased); fence released; acceptance completes |
| M3 | Merge | PR merged at another head (series released or not) | `head-changed`: the `sha` fence shows no submission of the series merged it; settles the attempt, not the Change; from `intent` with zero requests when unreleased | Unreleased: recorded group gone or killed first. Fence released; `_observe_acceptance_once` refuses the head and records `identity-mismatch` acceptance attention (existing owner); no completion receipt; no D10 cleanup; worktree retained |
| M4 | Merge | Every possible submission of the series has its own complete refusal: `400`, `403`, `405` or `422` response, or UUID result `failed` (a lone first request qualifies) | `refused` with reason | Fence released; approval ends; a new confirmation is needed |
| M5 | Merge | As M4, with at least one response or UUID result `enqueued` | `refused/queue-required` | As M4; a later queue merge is still observed (R4) |
| M6 | Merge | PR unmerged, head ≠ approved head (drift recorded), no submission `pending` | `unknown` (contained): consent withdrawn; the `sha` fence excludes nothing while the head can return | Fence held; no request; `merge-response-unknown` hold (1.13): **Check merge status** or a merge in GitHub; a new offer only after M2–M5 |
| M7 | Merge | A submission's UUID result `pending` with options equal to the approval's (at any current head) | `pending` | Fence held; non-consuming backoff poll (D6) until `merge_reads_exhausted`, then a `pending-provider-request` hold (1.13), user checks only; no request |
| M8 | Merge | PR open and unmerged at the approved head; no recorded head drift; no submission `pending`; one or more without own refusal (UUID absent or `404`); transport closed; I1 holds | `unknown`: readback evidence unavailable, never a refusal | Fence held; one I3 re-request per evaluation within the effect budget (`409` adopts; `200` → M2); its refusal leaves the series in M8 or M9 |
| M9 | Merge | Anything else: read failed, transport open, PR closed unmerged at the approved head, I1 fails, foreign or optionless `409` | `unknown` (contained) | Fence held; `merge-response-unknown` hold (1.13); no request; **Check merge status** or a merge in GitHub |
| Y1 | Reply | No release record (a group may be recorded; D16) | No possible submission; stays `intent` | Post after a marker read |
| Y2 | Reply | Hidden marker found in a viewer reply on the thread | `posted` | Thread may be resolved |
| Y3 | Reply | Complete provider rejection of this write: HTTP `4xx` error body, or GraphQL `errors` with null `data` (G13) | `not-posted` | Post again with the same marker after a marker read |
| Y4 | Reply | Anything else after the release record: timeout, signal, `5xx`, unreadable output, controller death; transport open or closed; any number of marker-negative reads | `unknown` (contained) | Never reposted automatically; thread stays unresolved; a recorded user decision (below; duplicate risk shown); a later marker hit settles Y2 |

Y4 user decisions are durable and replay-safe:

- Each `unknown_reply_decisions` entry carries the `confirmation_id` of one user answer. The
  decision identity is SHA-256 of handoff ID, original `reply_id`, decision and `confirmation_id`.
- `repost`: before any transport, a CAS revision of the original's receipt records the decision
  and its replacement `reply_id` (SHA-256 of the decision identity). The replacement starts at Y1.
- Replaying an accepted decision resumes that replacement through Y1–Y4, marker read first; it
  never mints another. A different decision for an already decided reply is refused with the
  accepted one.
- `leave-unposted` is a user disposition, not evidence: the original stays `unknown`, never
  `not-posted` (Y3 only); posting stops for it; a later marker hit still settles Y2.

Falsifiers: UUID `404` with the PR open and the request merging later stays nonterminal until M2
(N05-B); original pending, its UUID unavailable, re-request `422`, original merges later →
nonterminal and fenced until M2 (N05-B); original pending at head A, transport closed, head A→B →
nonterminal and fenced; head back to A, original executes → M2, fence never released before
(N05-B); a reply effect delayed past transport closure and two marker-negative reads is never
reposted (N05-D); `repost` accepted, replacement sent, crash before return, identical decision
replayed → one replacement identity, settled by marker read (N05-D).

EOF falsifier (G12; N05-A launcher, N05-B and N05-D controller): real `gh` against a local HTTP
recorder, on macOS and Ubuntu. Controller death right after spawn or after the group record, with no
release record → no request recorded; M1 or Y1. Death after the durable release record, including
before or during token delivery (empty or truncated token) or with a truncated body file → at most
one request, byte-equal to the frozen body (`sha`, `merge_method`, `merge_action`, `bypass_rules`),
and settlement stays nonterminal: merge M6–M9 until M2–M5 evidence, reply Y4 without automatic
repost, even when the recorder log is empty. Only the absence of a release record permits M1 or Y1.
Engine merge and engine replies are offered only after it passes on both platforms.

### 1.12 Mutation-fence lock entry

The fence is only as strong as the exclusion around it. One entry, new `mutation_fence.py` (N05-B),
owns both.

- **Lock.** The per-Change checkpoint lock (`_checkpoint_lock_root`). Attempt creation and every
  attempt settlement need a live guard and update `guard.fence`, so the fence cannot change under
  a holder.
- **Entry.** `change_mutation(target_root, change_id, *, guard=None, blocking=True)` takes the flock
  once, reads the attempt store and yields `ChangeMutationGuard(change_id, fence)`; `fence` is the
  nonterminal attempt identity or none. The guard dies when its entry exits.
- **Already-locked caller.** Passes its guard; the entry checks Change and liveness and yields it
  without opening a descriptor (a second `flock` on a fresh descriptor blocks in one process,
  `storage_io.py:43-62`). This generalizes the `PublicationLock` token
  (`workspace_coordination.py:83-92`, `:604`) and replaces the implicit `executing_continuation`
  skip of `_engine_checkpoint_lock` (`application_acquisition.py:975-980`).
- **Standalone runtime entry.** A public `DeliveryRuntime` mutation called without a guard enters
  once at its top and passes the guard to internal calls; helpers below it require a guard.
- **Helpers.** A private helper that reaches `_require_change_mutable` takes its caller's guard.
  At lane B `c9d4a15b7` (post-N01) all 41 calls in `owlbear_delivery` sit in `delivery_runtime.py`:
  40 in public mutations, one in `_retry` (`:2299-2310`). `_retry` is reached only from
  `transition` (`:1930-1947`) through `_SettlementReplayMixin._transitioned_binding`
  (`runtime_settlement.py:91-99`); both carry the guard. No `runtime_*` or `application_*`
  module has another call.
- **Order.** Acquisition lock → checkpoint entry → publication or recovery lock. Owners already
  publish inside the checkpoint lock (`portfolio_application.py:1275` →
  `application_publication.py:1351` → `change_publication.py:325`); `settle_builder_invocation`
  takes the publication lock before runtime writes (`delivery_runtime.py:2095`), so it enters
  first. Entering while this thread holds the Change's publication or recovery lock raises; the
  coordinator records holders per thread.
- **Check.** `_require_change_mutable(frontier, operation, *, guard, allow_attention=False)` stays
  pure and refuses `merge-in-progress` when `guard.fence` is set and `operation` is not in
  `_MERGE_FENCE_EXEMPT` (`runtime_models.py`, beside `_NORMAL_CHANGE_MUTATIONS`). Application
  owners check `guard.fence` right after entry, before any provider, Git or frontier effect, and
  hold the guard through the mutation. The `_runtime(for_mutation=True)` check runs before the lock
  (`portfolio_application.py:1216-1218`), so it is an early refusal only, never authority.
- **Exempt.** Attempt-store writes, the merge owner, `latch_merged_pull_request`, `complete_change`
  and acceptance writes, each only in the 1.11 order. The bounded attention lock
  (`application_lifecycle.py:765-775`) uses the non-blocking entry with its existing deadline.

### 1.13 Held merge state and user exit

A Change is *held* while readiness is `merge-response-unknown`: a released series is nonterminal
and no automatic step may send or settle it (rows M6, M9, M8 without a permitted re-request, or
M7 once `merge_reads_exhausted`).

- **M7 before and after exhaustion.** While `merge_reads_exhausted` is false, an M7 read is D6's
  non-consuming poll: readiness `waiting/merge-in-progress`, actor `system`, `merge_hold` null (not
  held, no hold text). Once true, M7 is a hold: `row` `M7`, `cause` `pending-provider-request`,
  actor `you`, `human` acquisition. The check records series state `pending` (1.4; attempt-store
  write, 1.12), so later readiness derives the same hold without a read; polling stays off.
- **Projection.** `DeliveryReadiness.merge_hold` (`MergeHold`, N05-B) is computed from the attempt
  record, the D6 ledger and the fresh read. It adds no persisted field; head drift is already on
  the series (1.4), so the N02 registry is unchanged.
- **Fields.** `approval_id`; `row` (`M6`, `M8`, `M9`, or `M7` only when `merge_reads_exhausted`);
  `cause` (`head-drift`, `readback-unavailable`, `transport-open`, `read-failed`, `pr-closed`,
  `foreign-request`, `offer-invalid`, `pending-provider-request` for M7);
  `consent_withdrawn` (drift recorded); `approved_head`, `drift_head`, `current_head`, `pr_state`;
  per submission `pending`, `unavailable` (UUID absent or expired, no own refusal), `refused` or
  `none`; `outstanding` (every possible submission without its own refusal); `automatic_reads`
  (`active`, or `exhausted` when D6's `merge_reads_exhausted` holds); `check_action` =
  `check-merge-status`; `pr_url`; `settles` and `does_not_settle` guidance codes (below).
- **Actor and continuation.** One predicate, D6's `merge_reads_exhausted` (either episode
  exhausted): actor `system` while false, `you` once true. Ordinary continuation then yields
  `human` with `merge-response-unknown`; it never falls back to raw `observe_acceptance` and never
  loops.
- **Both surfaces** (N05-B card and detail; N05-C Cockpit control and chat) show: consent withdrawn
  when drift is recorded; that a sent request's outcome is unknown (for `pending-provider-request`:
  that GitHub still reports it pending) and that it may still execute;
  Approve merge, revoke, mark ready, target sync, review repair and worker controls disabled with
  that reason; one **Check merge status** action; the PR link and the guidance below. Neither
  shows "checking" or implies automatic polling or a way to cancel the request.
- **Pending copy** (`pending-provider-request`): "GitHub reports the merge request is still
  pending. Delivery will not check it automatically. Check merge status again, or act in GitHub
  as described below."
- **Check merge status.** One user check is one `check_merge_status` call: one 1.11 fresh read
  (PR, merge evidence, each recorded UUID result) under one fence entry. It sends no request (not
  even under M8), reserves nothing in either D6 episode, resets no budget and restores no
  automatic polling. It releases the fence only when the read matches M2–M5. On M2 the same call
  runs the acceptance observation (completion); on M3 it runs it too and returns the acceptance
  attention recorded. Otherwise it returns the refreshed hold; a matching `pending` returns row
  `M7`, cause `pending-provider-request`, with the fence and both D6 budgets unchanged.
- **No background reads.** While `merge_reads_exhausted`, acquisition and
  `reconcile_awaiting_acceptance` (Cockpit's 30-second reconciliation hook) read nothing for a
  held Change; they report `merge-response-unknown` from persisted state.
- **GitHub guidance** derives only from the complete M2–M5 predicates of 1.11. Both surfaces
  render it from the codes and `outstanding`, so they cannot disagree:
  - `merge-approved-head` (M2): merging the PR in GitHub at the approved head; completion is
    then observed once (R4).
  - `merge-other-head-attention` (M3): merging at any other head ends the attempt
    (`head-changed`), but the content is unreviewed: acceptance attention, no completion, no
    cleanup.
  - `all-submissions-refused` (M4, M5): seen on a check when every possible submission has its
    own refusal response or `failed`/`enqueued` UUID result. Omitted while any submission is
    `unavailable`, since an expired or absent UUID can never yield a refusal.
  - Does not settle (`does_not_settle`): `single-refusal` (one submission's refusal while another
    is outstanding), `uuid-expiry`, `pr-closed-or-reopened`, `branch-deleted`,
    `push-or-head-restore`, `elapsed-time`, `new-approval` (none is offered while held).
  - Restoring the approved head can let the outstanding request execute (P4); that merge is M2.
  - Once any submission is `unavailable`, only a merge in GitHub (M2 or M3) ends the hold. A user
    who does not want the merge keeps a held Change; Delivery offers no cancel. Whether an
    explicit non-merging retirement is added is U4 (1.9).

## 2. Feasibility Probes

All probes ran on `ef622c354` in the lane C worktree or in `.owlbear/scratch/n05p/` (helpers and
outputs, unversioned). GitHub probes were read-only GETs and GraphQL queries against
`maba-pag/owlbear`. No live Delivery state, MCP server or Cockpit was touched.

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | `gh api` GETs: `repos/maba-pag/owlbear`, `rules/branches/{dev,main}`, `rulesets`, `branches/dev/protection`, `branches/dev`; GraphQL repository fields (`gh1.txt`) | Merge, squash and rebase allowed; auto-merge disallowed; `mergeQueue(branch:"dev")` null; `deleteBranchOnMerge: true`; `viewerPermission: WRITE`, `viewerCanAdminister: false`; `dev` ruleset has only `deletion` and `non_fast_forward`; classic protection 404; PR #345 merge commit `ef622c35` has parents `[d8072409 (base), 91e6545d (head)]`; token scopes `gist, read:org, repo, workflow` | U1, U3, D7, D9, F1, F2 |
| P2 | GraphQL introspection (`gh2.txt`) | `MergePullRequestInput`: `pullRequestId`, `expectedHeadOid`, `mergeMethod`, `commitHeadline`, `commitBody`, `authorEmail` (no base fence); methods `MERGE`, `SQUASH`, `REBASE`; `MergeStateStatus`: `DIRTY`, `UNKNOWN`, `BLOCKED`, `BEHIND`, `UNSTABLE`, `HAS_HOOKS`, `CLEAN`; `MergeableState`: `MERGEABLE`, `CONFLICTING`, `UNKNOWN`; `EnqueuePullRequestInput` has `expectedHeadOid`, `jump` | D2, D9 |
| P3 | Mergeability computation: GraphQL on open PRs, then three REST GETs of #312 and a GraphQL re-read (`gh2.txt`, `gh3.txt`) | GraphQL first returned `UNKNOWN` for #312, #314, #335; REST then returned `mergeable: false`, `mergeable_state: "dirty"` and GraphQL `CONFLICTING`/`DIRTY`. B1's PR #312 currently conflicts with `dev` | `UNKNOWN` is a real transient state (D9); live L2 example |
| P4 | GitHub REST reference for pull requests (API version 2026-03-10) and `GET …/pulls/{345,326}/merge` | `PUT …/merge`: `sha` fence; `405` cannot merge; `409` head mismatch; doc recommends the async API. `PUT …/merge-async`: `sha`, `merge_method`, `merge_action` (`default`, `direct_merge`, `merge_queue`), `bypass_rules` (default false); `202` with UUID; `200` already merged or enqueued; `409` returns the pending request's UUID and merge options (`merge_method`, `merge_action`, `expected_head_sha`, `bypass_rules`); a stacked PR's merge includes all open downstack PRs; the PR object reports `stack` (`size`, `position`, base); `400` not ready (closed, draft); rules evaluated in the background; `GET …/merge-async/{uuid}` retained 24 h; `GET …/merge` → `204` (observed for #345, #326) or `404` | D2, I2, I3 |
| P5 | `gh api` error transport on a 404 (`gh_err_*.txt`) | Non-zero exit; JSON error body on stdout; `gh: <message> (HTTP <code>)` on stderr. Today `_execute` discards stdout on failure (`github.py:841-883`) and `_raise_command_failure` maps an unmatched write status such as `405` or `400` to `RESPONSE_UNKNOWN` (`github.py:885-910`) | N05-A needs operation-specific status and body parsing |
| P6 | `p_gate.py`: provider and capability gates on the real `github.py` and on copies with a merge-async REST call and a `mergePullRequest` document | Baseline clean. Copies: `unexpected REST operation in request_merge`, merge-method field hit, capability hit, `unexpected GraphQL document _MERGE_MUTATION`; 279 production files are scanned | F3, D11 |
| P7 | Focused baseline: `pytest serve/delivery-github/tests tests/test_delivery_worktree_authority.py -k "provider or merge or completion or capability or automation or github or memory"` (`t_base.txt`) | 77 passed, 28 deselected, 1.09 s | Harness and gates green before N05-A |
| P8 | `p_l1.py`: `_ReadinessViewsMixin._publication_observation` with a one-hour-expired cache entry | With a ready receipt: expired observation returned, 0 provider reads. Before ready: refreshed, 1 read. Acquisition also reads the cache regardless of age (`application_acquisition.py:349`, `:847`; `application_readiness.py:1967-1968`, `:1989-1990`) | L1 root cause (D8) |
| P9 | Source read of L2 | Card shows "Pull request has merge conflicts" from a cached observation (`work_items.py:1020-1036`) while acquisition still offers `observe-acceptance` and maps `DeliveryAcceptanceWaitingError` to `merge-approval-required` (`application_acquisition.py:797-798`) | L2 root cause (D9) |
| P10 | `p_fakegh.py`: `GitHubCliPublicationProvider().read_repository` with a fake `gh` first on `PATH` | Fake answered; argv recorded (`api --method GET … repos/example/repo`). The work E2E stack passes `...process.env` to Cockpit (`start-work-portfolio-stack.mjs:54-59`) | E2E can fake GitHub below the provider owner without a production seam |
| P11 | `p_disjoint.py`: N05-A paths against N01-A/B/C maps and N01 §3.7 exclusions | No clash; the only shared file is the execution plan status table (a companion) | R12; [3.7](#37-n01-disjointness-check-for-n05-a) |
| P12 | `isinstance` and fake-provider inventory | `isinstance(..., PublicationProvider)` only in `serve/delivery-github/tests` (`test_memory_provider.py:50`, `test_github_provider.py:213`); a custom provider fake in `serve/delivery/tests/test_draft_pull_request.py` | D1 |
| P13 | Source read of target sync after finalization | Sync returns the PR to draft before any head change (`application_publication.py:118-170`, hook at `:139`); a conflict invalidates finalization and ready (`delivery_runtime.py:3923-3975`); readiness offers sync only before finalization (`application_readiness.py:1242-1256`) | U3(a) is feasible with existing owners |
| P14 | Completion and cleanup source read | Single completion caller and latch guard pinned by tests; `cleanup` raises computed attention before any mutation (`change_workspace.py:3816-3866`); no automatic cleanup caller exists; supervisor runs only checkpoint reconciliation | I4, I6, D10 |
| P15 | N02 state on `ef622c354` | No `state_formats.py` or `state_migration.py` in `owlbear_delivery` | N05-B must follow N02-B (as §4.2 states) |
| P16 | Issue #225 (GitHub read) and `w-address-pr-feedback` | Replies are posted by the agent with `gh api graphql` (`SKILL.md:204-219`); classifications live only in chat output; no reload contract | D13, R10 |

## 3. Phases

### 3.1 Shared rules

- Plans name symbols; after N01-C, re-resolve files by symbol (`application_*`, `workspace_*`,
  `runtime_*`). Writers pinned by N01 I6 stay where they are.
- Risky code stays with Opus: provider status mapping and gate revision (A); offer, approval,
  merge owner, readback, L1/L2, registry and migration (B); route semantics and prompt rules (C);
  handoff and reply replay (D). Luna may take fake-provider fixtures and scenarios, TS mirrors,
  presentation text, dialog component and tests, docs and skill text, each with an exact contract
  (execution plan §1.6).
- Every new readiness reason, action or status ships with its `workItems.ts` mirror, rendering
  (`workItemPresentation.ts`, `WorkItemDetail.tsx` / `WorkPortfolioPage.tsx`) with a component
  test, and the parity assertion in `tests/test_cockpit_boundary.py` (execution plan §1.4).
- Assembled claims use the default loader, `Client(assemble_target_server(...))`, the Cockpit HTTP
  client and the work E2E stack on disposable repositories with local bare remotes. Provider fakes
  sit at `PublicationMergeProvider` (memory provider) or below `gh` (fake executable on `PATH`).
- Proof commands run from the lane worktree with `env -u PYTHONPATH`; tests use `-n0` in the inner
  loop. Under machine load, run one test file or `-k` selection at a time.

### 3.2 N05-A — Provider merge and readback adapter

- **Prerequisites:** N05-P, N01-P, N00-C (execution plan §4.2). Runs while N01-B and N01-C are open.
- **Editable paths:**
  - `serve/delivery/src/owlbear_delivery/publication_provider.py` — additions only (D1, D3)
  - `serve/delivery-github/src/owlbear_delivery_github/github.py`, `memory.py`, new
    `effect_launcher.py` (D16), `serve/delivery-github/README.md`
  - `serve/delivery-github/tests/test_github_provider.py`, `test_memory_provider.py`, new
    `test_merge_provider.py`, new `test_effect_launcher.py` (EOF falsifier; requires `gh`, a skip
    fails the gate run), new `test_merge_rehearsal.py` (marker `api`, runs only with
    `OWLBEAR_MERGE_REHEARSAL_REPO` set; A-R)
  - `tests/test_delivery_worktree_authority.py` (provider and forbidden-effect gates, D11);
    `tests/fixtures/delivery-authority/forbidden-fields.py`, new `forbidden-provider-merge.py`
  - this plan's N05-A progress row; the execution plan's N05-A status row
- **Must not edit** while any N01 phase is unmerged: the N01 list in [3.7](#37-n01-disjointness-check-for-n05-a).
- **Contract:**
  - New REST calls, one per allowlisted function: `GET repos/{o}/{r}/branches/{branch}` (URL-encoded
    branch), `GET repos/{o}/{r}/rules/branches/{branch}`, `PUT …/pulls/{n}/merge-async`,
    `GET …/pulls/{n}/merge-async/{uuid}`; repository settings come from the existing
    `GET repos/{o}/{r}` shape with added fields. One new GraphQL query `_READ_MERGE_COMMIT_QUERY`
    (merge commit and its first two parents).
  - The merge body is built only from `RequestPublicationMerge`; `merge_action` and `bypass_rules`
    are constants (`"direct_merge"`, `false`).
  - The `PUT` enters through the launcher (D16): `request_merge` checks `body_path` bytes equal
    `freeze_body(request)`, spawns the launcher through the bounded runner (N02 plan D8), calls
    `release(group_id, start_time)` and writes the token only after it returns (1.11 row M1, D6).
    `gh` reads the file (`--input <file>`), never stdin.
  - Merge-specific failure parsing reads stdout JSON and the stderr status: `409` with a UUID →
    `pending` carrying the reported options; `409` without them → `RESPONSE_UNKNOWN` (never
    matching); `400` → `refused/closed-or-draft`; `403` → `refused/forbidden`; `405`/`422` →
    `refused/not-mergeable` or `validation`; result `failed` → `refused/rules-failed` with bounded
    message; `enqueued` → `refused/queue-required`; `GET` UUID `404` → `unavailable` (never a
    refusal; row M8); write timeout or unreadable write response → `RESPONSE_UNKNOWN`.
  - The memory provider models: pending → merged transitions, lost response (effect applied,
    exception raised), repeated request returning the pending ID and options, a foreign pending
    request, a stacked PR, head fence, draft or closed, rules failure (including an up-to-date rule
    after a target advance), manual merge by a "user", target advance between read and merge, base
    retarget or stack join after the final read (with and without configured scope enforcement).
- **Positive scenarios:** exact argv and body for every new call (runner fake); `202` → `pending`
  with UUID; `GET` UUID → `merged` with SHA; repeated request after a pending one returns the same
  UUID and its options; already-merged PR → `merged` without a new request; merge evidence parses
  `stack` and its absence; `release` is called with the launcher's group before the token is written
  and the runner fake sees `--input <file>`, never `--input -`; merge-commit query returns parents;
  settings report allowed methods, push permission, `merge_queue` and strict up-to-date rules;
  `isinstance(provider, PublicationMergeProvider)` holds for both providers and
  `isinstance(provider, PublicationProvider)` still holds; the revised gate passes on the real
  provider.
- **Negative scenarios:** each failure mapping above; a `PUT` timeout is `RESPONSE_UNKNOWN` with
  `retry_safe=False`; a `409` body without options yields unknown options, never the request's
  own; `GET` UUID `404` yields `unavailable`, never `refused`; a `body_path` differing from
  `freeze_body(request)` is refused before spawn; a raised `release` sends nothing; the 1.11 EOF
  falsifier at the launcher; no model accepts a bypass, queue or
  auto-merge field; gate fixtures fail for
  `bypass_rules: true`, `enablePullRequestAutoMerge`, `update-branch`, `enqueuePullRequest`, a merge
  call in a non-allowlisted function, and a `merge_method` field on an acceptance, latch,
  completion or observation model; golden bytes of an existing `PublicationPullRequest` observation
  dump are unchanged.
- **Inner loop:** `uv run pytest serve/delivery-github/tests/test_merge_provider.py -q -n0`,
  `uv run pytest serve/delivery-github/tests/test_effect_launcher.py -q -n0`, then
  `uv run pytest tests/test_delivery_worktree_authority.py -q -n0 -k "provider or merge or capability or field"`.
- **Closeout:** `uv run test --changed`; scoped `uv run ruff check` and `ruff format --check`; the
  full `uv run pytest serve/delivery-github/tests tests/test_delivery_worktree_authority.py -q`.
- **LC:** not applicable (no persisted format, loading or startup change).
- **Size / risk:** M / high (relaxes a security gate; provider mutation transport).

### 3.3 A-R — Real-provider merge rehearsal (step, not a phase)

- **When:** after N05-A merges and U2 is answered (a) or (b); before N05-B merges. Under U2(c) it is
  skipped and G1 blocks N10-H.
- **Procedure:** with `OWLBEAR_MERGE_REHEARSAL_REPO` set, `test_merge_rehearsal.py` creates branches
  and draft PRs through the provider, then exercises: wrong `sha` (expect refusal, PR unmerged);
  draft (expect `400`); exact head (expect `202` or `200`, then `merged` by UUID); repeated request
  (no second merge); lost response (send, discard the response, read back, repeat request → same
  UUID or `merged`); merge commit parents; `deleteBranchOnMerge` effect on later PR reads; under
  U3(d), with a disposable ruleset requiring up-to-date branches, a target advanced after the final
  read and before the request (expect `failed`, PR unmerged); for a candidate scope-enforcing
  fact, a `base` retarget or stack join after the final read with the same head (expect no merge
  outside the approved PR and target). Without such a fact N05-B keeps `scope-unenforced`.
- **Evidence:** command, repository, PR numbers, observed statuses and messages, on the N05-B PR.
  No other repository is mutated.

### 3.4 N05-B — Approval, merge action, readiness and cleanup

- **Prerequisites:** N05-A, N01-C, N02-B (execution plan §4.2); U1, U3 and U4 answered; A-R evidence
  or U2(c) before merge; G2 resolved (U3 part 2 and A-R scope evidence) and the G12 EOF falsifier
  green on macOS and Ubuntu before engine merge is offered, else only `scope-unenforced`.
- **Editable paths** (N01 phase in brackets):
  - new `owlbear_delivery/merge_approval.py` (`MergeOffer`, `MergeHold`, `MergeApprovalRecord`,
    `MergeApprovalRevocation`, `MergeAttemptRecord`, `PullRequestMergeReceipt`, store, errors;
    `MergeRetirementRecord` under U4(b))
  - new `owlbear_delivery/application_merge.py` (`_MergeMixin`: offer, approve, revoke, merge
    owner, `check_merge_status` (1.13), capability, cleanup best effort and sweep;
    `retire_held_merge` under U4(b); held-Change defer and resume exemption under U4(c))
  - `portfolio_application.py` [A]: facade bases; `_observe_acceptance_once` settles a live
    attempt first (1.11) and calls cleanup after completion (D10); `reconcile_awaiting_acceptance`
    reads nothing for a held, exhausted Change (1.13); `_classify_acceptance_observation`
    keeps manual-merge detection; `_runtime` advisory pre-check; checkpoint `locked_roots` uses
    become `change_mutation` entries (1.12)
  - `application_readiness.py` [A]: `_publication_observation`, `_delivery_snapshot` (D8);
    `_capture_action_basis` (U3 route for finalized Changes); awaiting-merge readiness, offer and
    new reasons; `_action_prerequisites`; `_engine_action_prompt`; retry failure classes
  - `application_acquisition.py` [A]: engine-action selection, fresh-observation fence,
    `_execute_engine_action` (D6), `_invoke_engine_owner`, waiting-reason mapping (L2),
    `_record_engine_attempt_result` (D6 ledger accounting), `_engine_checkpoint_lock` → entry
  - `application_lifecycle.py`, `application_recovery.py` [A]: checkpoint, attention and recovery
    owners take the entry first and pass the guard (1.12)
  - new `owlbear_delivery/mutation_fence.py` (`change_mutation`, `ChangeMutationGuard`);
    `workspace_coordination.py` [B]: per-thread holder record for the order check
  - `runtime_support.py` [C]: `_require_change_mutable(..., guard=)` (I11); `runtime_models.py`
    [C]: `_MERGE_FENCE_EXEMPT` beside `_NORMAL_CHANGE_MUTATIONS`; `delivery_runtime.py` [C]: public
    mutations accept a guard or enter once; `_retry` takes the guard; `settle_builder_invocation`
    enters before its publication lock; `runtime_settlement.py` [C]: `_transitioned_binding`
    passes the guard to `_retry` (1.12 helpers)
  - `application_models.py` [A]: `DeliveryEngineActionResult` kinds, reasons, `merge` receipt
  - `application_publication.py` [A]: `reconcile_pending_checkpoints` runs the cleanup sweep
  - `application_support.py` [A]: PR body text (`:341` "merge this pull request in GitHub")
  - `work_items.py`: basis fields, readiness reasons, `merge_offer`, `merge_hold`, awaiting-merge
    and held card text (1.13)
  - `workspace_models.py` [B]: `ChangeContinuationAction` kind and fields
  - `recovery.py`: `RecoveryInvocationRequest.kind`, retry episode kinds and failure classes
  - `state_formats.py` and `state_migration.py` [N02]: family registration, format step, rewrite of
    `coordination`; `serve/tools/src/owlbear_tools/delivery_diagnostics.py` mirror
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py` (basis and result schemas only)
  - frontend companions: `serve/cockpit/web/src/api/workItems.ts`,
    `components/workItemPresentation.ts`, `WorkItemDetail.tsx` (offer summary, wait and hold
    text, no control), component tests; `tests/test_cockpit_boundary.py`
  - `tests/test_delivery_worktree_authority.py` (allowlist entries for B files only)
  - tests: new `serve/delivery/tests/test_merge_approval.py`, `test_merge_continuation.py`;
    `serve/delivery/tests/test_state_formats.py` fixtures; `serve/tools/tests/test_delivery_diagnostics.py`
  - this plan's progress row; the execution plan's status row
- **Positive scenarios:**
  - Awaiting-merge, `CLEAN`, checks green, U3 satisfied → readiness `waiting/merge-approval-required`,
    actor you, with an offer whose fields equal provider facts; `approve_merge` records one approval;
    a retried submission of the same confirmation returns the same record.
  - Acquisition yields `merge-pull-request` bound to the approval and fresh observation; execution
    sends one request with `sha` = approved head and `merge_method` per U1; `merged` → receipt with
    parents; next acquisition observes acceptance and completes once; cleanup removes the clean
    worktree in the same call; completed history shows completion and cleanup separately.
  - `pending` beyond the poll bound → `waiting/merge-in-progress`; the next acquisition yields a
    reconciliation successor that polls the recorded UUID and completes without a new request; the
    first operation's result replays unchanged.
  - Several successful `pending` polls (more than the `merge-readback` budget), then `merged` → no
    readback failure recorded, no budget exhausted, one request, one completion; while polling,
    readiness `waiting/merge-in-progress`, actor system, `merge_hold` null.
  - Revoke, then a new confirmation of the identical offer → a new approval and one request.
    Provider refusal, then a new confirmation → a new approval and attempt.
  - Manual merge in GitHub at the finalized head, with or without an approval → acceptance
    completes once; a pending approval is moot (no request sent).
  - Target moved after finalization under U3(a) → `target-sync-required` → sync returns PR to
    draft, invalidates finalization; after refinalize and ready, a new offer appears.
  - `delivery_health` reports merge capability; a provider without D1 shows
    `capability-unavailable` and the card says to merge in GitHub.
- **Negative scenarios (each asserts the provider request log):**
  - Head changed after approval → `stale`, no request; readiness offers nothing until republished.
  - Target head changed after approval → no request; U3 route.
  - Required check failed or pending after approval → `checks-failed` or `checks-running`, no request.
  - Stale `offer_id` → `ERR_DELIVERY_MERGE_OFFER_STALE` with the fresh offer, no approval written.
  - Revoke before submission → no request; revoke after submission → `ERR_DELIVERY_MERGE_IN_PROGRESS`.
  - Provider refusal of a lone first request (rules, protection, draft, closed; row M4) → no merge
    observed, approval terminated, custody and fence released, typed `merge-blocked` reason; a new
    confirmation is required.
  - Stacked PR (fresh read `stack.size` 2) → `merge-blocked/stacked`, no offer; an approval
    recorded before the stack formed → no merge request under that single-PR approval.
  - `base` retarget or stack join after the final read, same head: GitHub provider →
    `scope-unenforced`, no offer, no request; fake with scope enforcement → no out-of-scope merge.
  - Restart with the original effect reservation outstanding → the successor reserves
    `merge-readback` and reads; no second request. Failed reads exhaust `merge-readback` before
    `merged` → `check_merge_status` route remains, no episode reset, no second merge. Then three
    successive user checks: each performs exactly one read. The one reading matching `pending`
    returns `merge_hold` row `M7`, cause `pending-provider-request`, the same fence (attempt
    identity), both episode budgets unchanged, actor you and acquisition `human` with
    `merge-response-unknown`; afterwards acquisition and batch acceptance reconciliation make zero
    provider reads. The check that reads `merged` settles M2.
  - Exhaustion predicate (D6): exhaust `merge-readback` alone (effect episode open); in a fresh
    fixture, exhaust the effect episode alone (`merge-readback` open). Each →
    `merge_reads_exhausted`, actor you, acquisition `human` with `merge-response-unknown`,
    `automatic_reads` `exhausted`, zero provider reads from acquisition and batch acceptance
    reconciliation; one user check = one read set, no `PUT`, no reservation.
  - Guidance falsifier (1.13): original UUID `404` (expired), re-request refused `422` → still
    held; `outstanding` lists the original as `unavailable`; `settles` omits
    `all-submissions-refused`; `does_not_settle` has `single-refusal` and `uuid-expiry`; card and
    detail say the hold remains and only a merge in GitHub ends it.
  - Held-state falsifier (1.13), assembled (default loader, `Client(assemble_target_server(...))`):
    drift recorded, UUID `404`, both episodes exhausted. Reload readiness and the card →
    `merge-response-unknown`, actor you, `merge_hold` with `consent_withdrawn`, cause
    `head-drift`, `automatic_reads` `exhausted`, PR URL and guidance codes; acquisition and batch
    acceptance reconciliation make no provider read. `check_merge_status` → exactly one read set,
    no `PUT`, no reservation, budgets and fence unchanged, hold returned. PR closed, then head
    restored to A, a check after each → still held. Fake merges the original → check → M2,
    fence released, one completion. Variant: user merges at head B → check → M3 settlement,
    fence released, `identity-mismatch` acceptance attention, no completion receipt, no cleanup,
    worktree retained.
  - U4 branch (the confirmed one only): (a) a held Change with an `unavailable` submission stays
    held across checks until a merge; no retirement route exists. (b) Retire with UUID `404` →
    record written, attempt bytes unchanged, fence held, no provider write, readiness
    `merge-retired-unsettled`, no offer after head or target changes, abandonment refused
    `merge-in-progress`, no cleanup, continuation skips it; replay → same record; read shows
    merged during retire → settlement wins, no record; not exhausted → `…_NOT_HELD`; fake later
    merges at the approved head → check → series `merged`, acceptance attention
    `retired-unsettled:<id>`, no completion, no cleanup; downgrade refuses the new family. (c)
    Defer and resume of a held Change succeed under the fence, other mutations still refused; a
    check while deferred settles M2 without acceptance; `resume` → acceptance completes once.
  - Settlement table: each row M1–M9 driven by the memory provider yields its 1.11 settlement and
    fence effect; order holds (a merged PR with a `failed` UUID result settles `merged`).
  - Request series: a first request refused `422` with no predecessor → `refused`, fence released.
    Original pending, its UUID `404`, re-request `422`, original merges later → series nonterminal
    and fenced, D6 effect reservation closed as a failure count only, no second merge; settles M2
    on merge.
  - Expiry falsifier: UUID `404`, PR open at the approved head, the fake's request merges later →
    attempt stays nonterminal and fenced; with transport closed and I1 valid, one re-request →
    `409` adoption or `200` → `merged`; never `refused`, never two merges. PR closed unmerged with
    UUID `404` → `merge-response-unknown`, no request, fence held.
  - Head-drift falsifier: original request held pending at head A, transport closed, head A→B →
    settlement stays nonterminal (M7), drift recorded, fence held, no offer, no request; head
    restored to A, original executes → custody and fence never released before M2, which then
    settles it. Variant with its UUID `404`: A→B→A → no re-request (drift blocks M8), contained
    (M9) until the merge → M2. Drift with every submission refused (M4) → `refused`, fence released.
  - Pending attempt, then merged evidence → settled in 1.11 order, acceptance observed; head moved
    → stays nonterminal (M6 or M7); other mutations refused while nonterminal; revocation of an
    unsent `intent` → `revoked-unsent`, no request.
  - Lock entry (1.12): application entry and direct runtime entry, each with and without a pending
    attempt, and attempt creation racing each (two processes; two threads) → no deadlock within a
    bounded harness timeout; when the attempt wins, the mutation refuses `merge-in-progress` with
    empty provider, Git and frontier effect logs; when the mutation wins, approval execution sees
    a stale offer. A guard-passing caller opens no second descriptor (`locked_roots` spy). Entry
    while holding the Change's publication lock raises. Every `_require_change_mutable` call passes
    `guard=`, and each private helper on its path receives its caller's guard (AST inventory).
  - `RetryDelivery` through application entry and direct runtime entry, with and without a pending
    attempt → typed disposition (`DeliveryWorkerExclusionRequiredError` after the diagnostic, or
    `merge-in-progress` with no frontier write); `_retry` sees the entry's live guard; the
    `locked_roots` spy shows no second checkpoint descriptor.
  - Target advanced between preflight and provider execution (fake advances it after the final
    read): U3(d) with the rule → `failed`, no merge, attempt terminal; U3(d) without the rule →
    `target-unenforced`, no offer, no request; U3(e) → merge with `target-advanced-during-merge`.
  - `409` pending request with another head, `merge_queue` or `bypass_rules: true` → not adopted,
    `merge-response-unknown` kept, no request; no receipt claims that request matches the approval.
  - While an attempt is pending or unknown, target sync, mark ready, repair preparation, worker
    acquisition and revocation are refused with `merge-in-progress` (I11).
  - L1: expired cache with a ready receipt → readiness re-reads; provider down →
    `provider-unavailable`, not an offer; acquisition with a different observation ID → `stale`.
  - L2: `CONFLICTING` → `merge-blocked/conflicts` and sync route, never `merge-approval-required`;
    `UNKNOWN` → `merge-checking`; `BLOCKED` → `merge-blocked/protection`.
  - Crash injection at every durable boundary: after approval write; after attempt intent; after the
    frozen body; after spawn before the group record; after the group record before release; after
    release before the token; after the request before the UUID is recorded; after `merged` before
    the attempt is terminal; after the
    engine result before completion; after completion before cleanup. Each restart converges to one
    request series, at most one merge, exactly one completion, and cleanup or preserved attention;
    every boundary before release settles M1 with an empty HTTP recorder log (1.11 EOF falsifier).
  - Intervening manual merge (1.11, merged evidence before M1): crash after attempt intent, and in a
    variant after the group record before release; the user merges in GitHub at the approved head;
    reload and acquire → recorded group gone or killed, series `merged` from `intent`, exactly one
    completion, zero merge requests, no revocation; a revoke instead of the reload settles M2, never
    `revoked-unsent`. Variant at another head → M3 `head-changed`, fence released,
    `identity-mismatch` attention, no completion receipt, no cleanup, worktree retained, zero requests.
  - Response lost and readback fails → `merge-response-unknown`, no new request. Restart, restore
    provider reads → the successor converges to at most one merge and exactly one completion; the
    persisted unknown result replays unchanged.
  - Transport delayed across controller death: fake `gh` sleeps before merging; the controller is
    killed and restarted; readback while that process group lives → unknown, no request; after the
    fake merges → converge.
  - D6 premise: while one process executes the merge action, a second executor on the same Change
    is refused; after the executing process is killed (subprocess), the lock is free and the next
    execution performs readback before any request.
  - Two controllers (MCP and Cockpit applications on one portfolio) approve and execute concurrently
    → one live approval, one request series, one completion.
  - Unexpected file in the completed worktree → cleanup preserved with attention; completion intact.
  - Merge commit parent 1 differs from the approved target → receipt flag
    `target-advanced-during-merge`, shown as evidence; completion still observed.
  - Downgrade: the N02-B release refuses a state with N05 families (typed version diagnostic,
    unchanged hashes).
- **Inner loop:** `uv run pytest serve/delivery/tests/test_merge_approval.py -q -n0`, then
  `uv run pytest serve/delivery/tests/test_merge_continuation.py -q -n0`.
- **Closeout:** `uv run test --changed`; scoped Ruff; `npm --prefix serve/cockpit/web test`;
  `npm --prefix serve/cockpit/web run build`; Biome on changed frontend files; `uv run pytest
  tests/test_cockpit_boundary.py tests/test_delivery_worktree_authority.py tests/test_package_boundary.py -q`.
- **LC:** full form through `delivery-lc` (N02-B): unmigrated copy refused, migrated copy loads with
  every Change available, previous release meets the N02 D3 oracle, live hashes unchanged.
- **Size / risk:** L / high (external effect, crash replay, persisted formats).

### 3.5 N05-C — Adapters, Cockpit confirmation, continuation path and governance

- **Prerequisites:** N05-B.
- **Editable paths:**
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py` (tool names, annotations,
    handlers) and `target_models.py`; `serve/delivery-mcp/tests/test_target_server.py`
  - `serve/cockpit/src/owlbear_cockpit/routes/target_work.py`, `target_models.py`;
    `tests/test_cockpit_work_items.py`, `tests/test_cockpit_boundary.py`
  - frontend: `src/api/workItems.ts`, new `src/components/MergeApprovalDialog.tsx`, new
    `src/components/MergeHoldPanel.tsx`, `WorkItemDetail.tsx`, `workItemPresentation.ts`, the
    work-items mutation hook, component tests
  - E2E: `e2e/work-portfolio.spec.ts`, `e2e/support/seed-work-portfolio-delivery.py`
    (awaiting-merge and held fixtures), `e2e/support/start-work-portfolio-stack.mjs` (fake `gh` on `PATH`),
    new `e2e/support/fake-gh.mjs`
  - `share/prompts/continue-change.prompt.md`, `share/skills/w-orchestration/SKILL.md`,
    `share/agents/orchestrator.agent.md` (only if its text names merge ownership),
    `share/skills/r-workspace-governance/SKILL.md:66`, `share/skills/w-change-finalization/SKILL.md`
    (merge ownership text, if any)
  - `setup/operating-owlbear.md:300-345`, `README.md` Delivery section, `serve/delivery/README.md`,
    `serve/delivery-github/README.md`
  - `tests/test_delivery_worktree_authority.py` (allowlist entries for C files only)
  - this plan's progress row; the execution plan's status row
- **Contract:** Cockpit shows **Approve merge** only for `merge-approval-required` with an offer.
  The dialog shows every R1 field and the consequence ("merges into `<target>` in GitHub; Delivery
  cannot undo it"), with **Approve merge** and **Cancel**; each opening carries one
  `confirmation_id`. States: submitting, merged then
  completing, refused with reason, stale (re-review the new offer), provider unavailable, held
  (`MergeHoldPanel`, 1.13; never shown as checking; cause `pending-provider-request` renders the
  1.13 pending copy in panel and chat). The continuation workflow, on a `human`
  result with `merge-approval-required`, shows the offer, asks one question (Approve / Not now),
  and on Approve calls `approve_merge` with `confirmation="user-confirmed"` and a
  `confirmation_id` for that answer, then continues acquisition; it never approves without that
  answer (D14). On `human` with `merge-response-unknown` it shows the 1.13 hold and guidance,
  asks one question (Check merge status / Not now) and makes one `check_merge_status` call per
  Check answer; it never calls `observe_acceptance` as a fallback and never loops. Under U4(b) the
  panel adds **Retire without merging** (dialog with the outstanding submissions and the U4 text,
  one `confirmation_id` per opening) and chat asks Check / Retire / Not now; under U4(c) the panel
  offers Defer.
- **Positive scenarios:** MCP and HTTP approve, merge and complete on a disposable portfolio with
  the memory provider; E2E: approve in the dialog → fake `gh` records exactly one merge request →
  card shows **Completed**; revoke before execution; agent-ecosystem tests accept the revised
  skills and prompts.
- **Negative scenarios:** stale-confirmation E2E (fake head changes while the dialog is open →
  stale message, no merge request in the fake log); cancel sends nothing; HTTP `409` stale and in
  progress, `503` provider unavailable; MCP rejects a missing or wrong `confirmation`; no control
  appears for `merge-blocked`, `checks-running`, `merge-checking`; the capability gate still rejects
  auto-merge and update-branch strings in Cockpit and agent files.
- **Held-state falsifier (1.13):** E2E on the held fixture (drift recorded, UUID `404`, both
  episodes exhausted, fake `gh` at head B). Reload → panel shows consent withdrawn, outstanding
  uncertainty, disabled controls, PR link, settle and no-settle guidance, one **Check merge
  status**; no **Approve merge**; one reconciliation tick → no merge read in the fake log. Click →
  exactly one read set, no merge-async `PUT`, still held. Fake merges the PR at head B → click →
  hold cleared, acceptance attention (merged at an unreviewed head), not **Completed**, no
  cleanup. Variant: fake restores head A and merges the original → click → **Completed**.
  Variant: fake UUID result `pending` (matching options) → click → panel shows the 1.13 pending
  copy (row M7), still held, **Check merge status** remains, no **Approve merge**; next
  reconciliation tick → no read in the fake log.
  Expired original plus refused re-request → panel and chat say the hold remains; neither says
  the refusal settled it. Under U4(b): retire in the dialog → card shows retired, Check merge
  status remains, no merge request in the fake log. HTTP `merge-status/check` on a non-held
  Change → `409`. Continuation test:
  acquisition returns `human` with `merge_hold`; prompt asks Check / Not now, one call per
  answer, no `observe_acceptance` fallback.
- **Inner loop:** `uv run pytest serve/delivery-mcp/tests/test_target_server.py -q -n0 -k merge`;
  `uv run pytest tests/test_cockpit_work_items.py -q -n0 -k merge`.
- **Closeout:** `uv run test --changed`; scoped Ruff; `npm test`, `npm run build`, Biome;
  `npm --prefix serve/cockpit/web run test:e2e:work` (Chromium);
  `uv run pytest tests/test_agent_ecosystem_validation.py -q`.
- **LC:** full form (execution plan §5 N05: full form from N05-B on); no format change expected.
- **Size / risk:** M / medium.

### 3.6 N05-D — PR-feedback continuity (#225)

- **Prerequisites:** N05-C.
- **Editable paths:**
  - `publication_provider.py` (new `PublicationReviewProvider` protocol: list unresolved threads
    with comments, reply, resolve), `owlbear_delivery_github/github.py`, `memory.py`, their tests
  - new `owlbear_delivery/review_feedback.py` (handoff, revisions, reply receipts, store) and
    `application_review_feedback.py` (mixin); `portfolio_application.py` bases
  - `state_formats.py`, `state_migration.py` (families, format step); diagnostics mirror and tests
  - MCP `target_server.py`, `target_models.py` and tests (three tools)
  - `share/skills/w-address-pr-feedback/SKILL.md`, `share/prompts/address-pr-feedback.prompt.md`
  - `tests/test_delivery_worktree_authority.py` (allowlisted GraphQL documents)
  - new `serve/delivery/tests/test_review_feedback.py`; this plan; the execution plan status row
- **Contract:**
  - `start` records the handoff after triage (PR identity, base head, per thread: classification,
    bounded evidence, reply body). A `repair` handoff (at least one `fix`) also binds the
    review-repair invalidation ID and is revised by CAS after each repair commit (commit SHA, proof
    locator). A `no-repair` handoff (only `no-change`, `duplicate`, `stale`) binds the current
    finalization ID and PR head; it calls no `prepare_review_repair` and invalidates nothing.
  - `resume` reloads it. For `repair`: same PR, current finalization newer than the invalidation,
    PR head = finalized head, and a complete repair map: every `fix` thread has a recorded repair
    commit that is an ancestor of that head and a proof locator, or a later revision reclassifies
    it with evidence. Otherwise `ERR_DELIVERY_REVIEW_HANDOFF_INCOMPLETE` names the unmapped threads;
    the route is a CAS revision that maps or reclassifies them, or `start` again; no reply is posted. For
    `no-repair`: same PR, the bound finalization still current, PR head unchanged. Otherwise
    `ERR_DELIVERY_REVIEW_HANDOFF_STALE`; a missing handoff is `…_MISSING` with the bounded route
    "run `start` again at the current head" (already fixed findings become `stale` with evidence).
  - `post_review_feedback_replies` requires `resume`'s checks and posts each reply under D13 custody
    with a hidden marker `<!-- owlbear-reply:<reply_id> -->`; before posting and after any unknown
    response it reads the thread's comments by the viewer and settles by 1.11 rows Y1–Y4. An
    `unknown` reply blocks posting on its thread until a marker hit or a user decision in
    `unknown_reply_decisions`, recorded and replayed under the 1.11 Y4 decision rules. It resolves a thread
    only after its reply is recorded; failures leave the thread unresolved with the exact provider
    code.
- **Positive scenarios:** fresh-session `resume` recovers classifications and repair map without chat
  output; replies and resolutions posted once; handoff revisions replay exactly; only non-repair
  classifications, restart, `resume` → each reply posted once, finalization ID and ready state
  unchanged.
- **Negative scenarios:** stale PR or head → refused before any reply; controller death after spawn
  and before the release record → no reply sent, stays `intent` (Y1), one later post (1.11 EOF
  falsifier); fresh finalization with one
  unmapped `fix` thread → `…_INCOMPLETE` before any reply; provider effect delayed past transport
  closure and two marker-negative reads → `unknown`, no repost, then the delayed reply → `posted`;
  timeout or `5xx` → `unknown`, never `not-posted`; GraphQL `errors` with null `data` → `not-posted`,
  one later post; user `repost` → one replacement with a new marker; `repost` accepted,
  replacement sent, crash before return, identical decision replayed → one replacement identity,
  marker read, no second post; a different decision for that reply → refused with the accepted
  one (`ERR_DELIVERY_REVIEW_REPLY_DECIDED`); `leave-unposted` → disposition recorded, evidence
  stays `unknown`, never `not-posted`, a later marker hit → `posted`; repaired thread not repaired
  twice after restart (repair commit already recorded); reply response lost → marker found →
  no duplicate; reply posted but resolve fails → thread unresolved, repair evidence intact; external
  comment text never changes Delivery authority.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_review_feedback.py -q -n0`.
- **Closeout:** `uv run test --changed`; scoped Ruff; agent-ecosystem tests; package closeout: full
  `uv run test` once and a cumulative Sol challenge of the N05 diff against this plan.
- **LC:** full form.
- **Size / risk:** M / medium-high (external comments; replay).

### 3.7 N01 disjointness check for N05-A

N01 module maps from the [N01 plan](delivery-n01-plan.md): N01-A §3.4 (merged #344), N01-B §3.5
(in review), N01-C §3.6 (pending), and the "N05-A must not edit" list of §3.7.

| N01 phase | N01 editable paths | Overlap with N05-A |
| --- | --- | --- |
| N01-A | `portfolio_application.py`, `application_{support,models,readiness,acquisition,publication,lifecycle,recovery}.py`, `test_portfolio_application.py`, `tests/test_cockpit_work_items.py`, `test_module_structure.py`, `fixtures/module_surface.json` | none |
| N01-B | `change_workspace.py`, `workspace_{models,coordination,worktree_state,preservation,snapshots,target_sync}.py`, `test_change_workspace.py` | none |
| N01-C (in review, `1ba931191`; its six changed files rechecked) | `delivery_runtime.py`, `runtime_{models,receipts,support,settlement,reads}.py` | none |
| N01 §3.7 extras | `owlbear_delivery/__init__.py`, `test_delivery_runtime.py`, `test_worker_stall.py` | none |

Result (P11): disjoint. N05-A's core edit is `publication_provider.py`, which N01 §3.7 explicitly
permits; it removes and renames nothing that the split modules import (D3). N05-A adds no module
with an `application_`, `workspace_` or `runtime_` prefix. The only shared file is the execution
plan's status table, a companion that the ready rule does not block.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N05-P | — | — | Probes P1–P16 | Sol round 1: revision-required (stack scope, execution-time target race in U3, pending/unknown reconciliation, renewable consent, no-repair handoff, 409 option validation) → revised; Sol round 2: revision-required (execution scope policy, successor ledger accounting, outstanding-reply reconciliation, complete repair map, fence owner/ordering) → revised; Sol round 3: revision-required (reply non-execution authority, expiry ≠ refusal, fence lock-entry contract) → consolidated settlement contract; Sol round 4: revision-required (request-series settlement, repost decision replay, guard helper scope) → revised; consistency pass (D6/§1.4/§1.5 aligned with §1.11–§1.12); Sol round 5: revision-required (EOF-safe effect entry) → revised; Sol round 6: revision-required (EOF oracle vs release record) → revised; Sol round 7: revision-required (head drift vs pending series) → revised; Sol round 8: revision-required (held-state user exit) → revised; Sol round 9: blocked (U4 non-merging retirement) + 3 fix-now → revised; U4 pending; Sol round 10: revision-required (exhausted M7 hold) → revised; Sol round 11: revision-required (M1 vs observed manual merge) → revised; Sol round 12: `plan-sound` | approved (execution-plan amendments confirmation pending; U1, U3, U4 before N05-B; U2 before A-R) |
| N05-A | — | — | — | — | — |
| A-R | — | — | — | — | — |
| N05-B | — | — | — | — | — |
| N05-C | — | — | — | — | — |
| N05-D | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | GitHub's async merge behaves as documented (UUID and options on `409`, `400` drafts, rules run at execution, readback, head fence) | Provider mutations need U2; P phase ran read-only | P4 reference; P2 schema; fake tests (A) | A-R under U2(a)/(b) | N05-B merge; N10-H under U2(c) |
| G2 | The target, the PR's `base` or its stack cannot change between the final read and background execution | No GitHub merge API fences the base or the stack; `base` is editable without a head change; `dev` has no up-to-date rule (P1, P2, P4) | U3(d) rule refusal (A-R); A-R scope falsifier (retarget or stack join, same head); post-merge parent-1 check (D9) | U3 part 2; N05-B (enforce, else `scope-unenforced`) | N05-B start until U3 part 2 is answered; under U3(e) a recorded requirement revision; engine merge until A-R shows an enforcing fact |
| G3 | A chat approval reflects a real user answer | MCP cannot verify host dialogs | D14 rules; destructive annotation | N05-C; N10-H host rehearsal | N10-H evidence |
| G4 | Merge-queue and up-to-date-required targets behave as designed | This repository has neither (P1) | Memory-provider scenarios | N05-B | Nothing |
| G5 | Format-marker steps of N03-A and N05-B compose | Neither exists yet (P15) | N02 D3 linear chain | Second of N03-A/N05-B to merge | That phase's merge |
| G6 | The fake `gh` used in E2E matches real GitHub responses | Fake fidelity | P10; A-R real evidence | N05-C | Nothing |
| G7 | Marker-based reply dedupe survives edited or deleted replies | Not exercised | Read-back design (D13) | N05-D | Nothing |
| G8 | A 15-second observation cache is fresh enough under rate limits | Not measured | P8; existing constant `application_support.py:143` | N05-B | Nothing |
| G9 | The cleanup sweep stays cheap with many completed Changes | Not measured | Bounded supervisor `limit` | N05-B | Nothing |
| G10 | `deleteBranchOnMerge` does not disturb completion or later reads | Only manual merges observed so far | Existing completions after manual merges; A-R step | A-R | Nothing |
| G11 | The per-Change checkpoint lock excludes a second merge executor and is released when its process dies (D6 premise) | Implementation of `_selected_action_checkpoint_lock` not exercised for this purpose in P | `locked_roots` uses `flock` (N02 plan, `storage_io.py:33`) | N05-B subprocess test | N05-B merge (else D6 falls back to containment) |
| G12 | No `gh` request precedes a durable release record, and every sent request is the complete frozen body (D16; rows M1, Y1); recorded groups identify live transport after controller death (rows M8, M9; closed = every released submission's group gone) | Not exercised in P; upstream `--input -` sends stdin EOF as an empty body (v2.65.0 `api.go`, `http.go`) | `openUserFile` sends a regular file with `Content-Length` (v2.65.0); N02 plan D8 and P6 (`killpg` closes the group) | N05-A launcher EOF falsifier; N05-B and N05-D controller-death tests (macOS and Ubuntu, local HTTP recorder) | Engine merge (N05-B: else D6 falls back to containment and no merge is offered); N05-D engine replies (else replies stay manual) |
| G13 | A complete GitHub `4xx` error or GraphQL `errors` with null `data` for a reply mutation means it did not execute (row Y3) | Provider semantics, not a documented guarantee | `_execute` already treats write timeouts as response-unknown (`github.py:859-866`) | N05-D | Nothing: without proof, row Y3 is dropped and such replies stay `unknown` |
