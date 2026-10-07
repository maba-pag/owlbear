# Delivery N05 — Exact-Head Merge Approval, Completion and Publication Continuity

> **Package:** N05 of the [execution plan](delivery-redesign-execution-plan.md#n05--exact-head-merge-approval-completion-and-publication-continuity).
> **Planned on:** `origin/dev` `ef622c354` (N01-A and N02-P merged; N01-B in review; N01-C and N02-A
> not started; Python 3.14.8). Lane C worktree, branch `redesign/n05-p-merge-approval-plan`.
> **Round 3:** lock, runtime and transport locators rechecked at `origin/dev` `58c4d928b` (N01 merged).
> **Status:** approved: plan gate `plan-sound` in round 12 of fresh GPT-6.1 Sol challenges (2026-10-03).
> Product code is unchanged by this phase. U1–U4 decided 2026-10-03 ([1.9](#19-user-decisions)):
> U1 (a), U2 (b), U3 part 1 (a) and part 2 (e), U4 (b). PR #360 then moved merge approval, retirement
> and reply decisions onto N03's user-only confirmation boundary with single-use consent records (D14).
> **Simplification 2026-10-04** (lead decision,
> [execution plan §7](delivery-redesign-execution-plan.md#7-decisions)): that boundary is removed; the user
> approves a merge in Cockpit and no MCP tool approves (D14); U4 (b) retirement is removed (1.9); the
> multi-scenario real-GitHub rehearsal A-R is replaced by one smoke test (3.3); N05-B no longer needs N03-A.
> **N05-B amendment 2026-10-04** (lead decisions A1–A7 and Q1–Q5 in [1.8](#18-decisions)): one approval
> sends one merge request, recorded in one `merge_attempt` record; settlement S1–S8 (1.11) runs inside the
> acceptance owner; an owner-level fence (1.12) replaces guard threading; revocation, re-requests, the
> engine merge action and the held-state machinery are cut. N05-B is split into N05-B1 (3.4, read side)
> and N05-B2 (3.5, effect side).
> Reviews work in the execution plan's
> [operating context](delivery-redesign-execution-plan.md#19-operating-context).

## 1. Contract

### 1.1 Result

- A Change whose exact reviewed head is published, ready and mergeable offers **Approve merge** in
  Cockpit. The offer shows repository, PR,
  exact reviewed head, target branch and head, proof and required-check summary, and merge method.
  The user approves in Cockpit (D14); the continuation chat shows the offer and points to Cockpit.
- One approval authorizes one exact merge offer and sends at most one merge request. Immediately
  before it, Delivery recomputes the offer from a fresh provider read of PR state, head, stack,
  target branch head, rules, mergeability and required checks; any difference refuses as stale with
  no request. A target change before the offer is shown keeps an offer bound to the new target and
  reports the proof target beside it (U3 amended 2026-10-07 to (b)); a change after it is shown
  refuses the approval as stale. A
  target advance or scope change during GitHub's background execution is detected after the merge
  and reported as acceptance attention, never completion attributed to the proof (I4, I10, U3(e);
  programme §10.2 as revised 2026-10-03).
- An unknown merge response is settled only by readback, never by another request (Q1). While it
  stays unknown after the automatic reads, the Change shows one attention with the PR link; the user
  merges in GitHub, checks again, or abandons or defers the Change (1.13). A PR is never merged twice
  or merged without a matching approval.
- Completion is still observed exactly once by the existing acceptance owner when the finalized
  head merges, by the engine or manually in GitHub. A merge at any other head settles a merge
  attempt (S2) but yields acceptance attention, never completion or cleanup (programme §10.1).
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
| R1 | **Approve merge** in Cockpit with repository, PR, exact head, target, proof and required-check summary, merge method; the chat shows the offer and points to Cockpit; no MCP tool approves (D14) | Execution plan §5 N05; programme §4.2, §10.2, J05–J06; R3; execution plan §7 (2026-10-04) |
| R2 | Approval binds exact head and target; pre-merge provider re-read of PR state, head, stack, target, rules and checks; head change invalidates; target change per U3 (b, amended 2026-10-07: fresh approval against the current target, proof target shown); execution-time target and scope race detected and reported per U3(e) | §10.2 (revised 2026-10-03); V19; V11 (approval part) |
| R3 | Unknown merge response is read back, never re-sent; no duplicate or unapproved merge | §6.1 unknown write; §10.2; V12 |
| R4 | Completion observed exactly once when the finalized head merges, including manually in GitHub; a merge at another head is acceptance attention, never completion | §10.1; §10.2; J06 |
| R5 | Automatic cleanup of an eligible completed worktree; unexpected contents preserved; cleanup status distinct from completion | §10.3; J07 |
| R6 | Distinct waits: checks running, provider outage, pending user approval | §10.3; §4.3 progress copy |
| R7 | L1: readiness uses a fresh provider observation in every publication phase; acting owners re-read the provider (D8) | Programme D02 deferred findings (L1); execution plan §2.2 |
| R8 | L2: a known-unmergeable PR shows its real reason, not `merge-approval-required` | Programme L2; execution plan §2.2 |
| R9 | Governance: engine/provider publication is system work; agents never push arbitrarily | §10.2 last paragraph |
| R10 | #225: durable handoff and replay-safe replies for PR-feedback repair | Issue #225 acceptance criteria |
| R11 | WP2 step 4 (sync, proof, publication, checks, acceptance in the continuation loop) and step 5 (exact-head merge approval) | WP2; P08, P09; R2 |
| R12 | N05-A editable paths disjoint from every N01 phase; mandatory companions; LC full form from N05-B2 | Execution plan §4.2, §1.4, §5 N05 |
| R13 | Support baseline: macOS and Ubuntu, Chromium-only Cockpit E2E, Python 3.14 | Execution plan §1.1 |

### 1.3 Invariants

- **I1 Exact offer.** No merge request is sent unless the approval's `offer_id` equals the offer
  recomputed from a fresh provider read immediately before the request: same repository, PR number
  and node ID, head SHA, base branch, target branch head, finalization ID, ready receipt ID, the
  required checks' names and conclusions at that head, merge method and stack facts (I10). Check
  observation IDs are not bound: they digest `observed_at`, so every fresh read mints a new one
  (A7). The proof target is `frontier.target_sync_receipt.target_head` (the finalization has no
  target field; from N05-B1 any later sync to a new target invalidates finalization, 3.4). The offer
  binds the provider's current target branch head (`read_branch_head`), not the local remote-tracking
  ref the readiness basis reads without a fetch (A7). Since the 2026-10-07 U3 amendment (b), a proof
  target that differs from that head keeps the offer and is reported beside it; only a finalized
  Change without a recorded proof target routes to target sync.
- **I2 Fenced request.** Every merge request carries the approved head as GitHub's `sha` fence,
  `merge_action: "direct_merge"` and `bypass_rules: false`. Delivery never enables auto-merge,
  updates a PR branch through the provider, enqueues into a merge queue or bypasses rules.
- **I3 One request, readback only.** One approval sends at most one merge request. After a lost
  response, timeout, crash or unknown outcome, the attempt is settled only by readback
  ([1.11](#111-effect-settlement-contract)); no request is sent again for that approval (Q1).
  Terminal states come only from independently sufficient evidence; missing or expired readback
  evidence keeps an attempt or reply nonterminal. A pending request is adopted only when its
  reported head, method, action and bypass flag equal the approval's (D2).
- **I4 Completion owner unchanged.** `PortfolioApplication._observe_acceptance_once` stays the only
  caller of `DeliveryRuntime.complete_change`, guarded by the merged-PR latch
  (`tests/test_delivery_worktree_authority.py:81`, `:1252-1287`). A merge result is never a
  completion receipt; `CompletionEvidence` gains no field (it records no merge method, AC-13 of
  [worktree authority](delivery-change-worktree-authority.md)). Attempt settlement is not Change
  acceptance: a merge at another head (S2) settles only the attempt, and `_observe_acceptance_once`
  refuses it (`snapshot.head_sha != finalization.exact_head`) with `identity-mismatch` attention.
  1.11 runs right after the provider read on every acceptance path, before anything can return: in
  `_reconcile_awaiting_acceptance_locked` before `_classify_acceptance_observation` (Cockpit's
  reconciliation, also after a restart) and in `_observe_acceptance_once` before its identity check
  and latch (explicit `observe_acceptance`, the `observe-acceptance` engine action). It applies once
  per read and leaves a terminal attempt unchanged. Under U3(e), when the attempt settled `merged` records parent 1 ≠
  approved target head or merged base ≠ approved target, it calls `capture_acceptance_attention`
  with `identity-mismatch` and diagnostic `target-advanced-during-merge:<approval_id>` or
  `scope-changed-during-merge:<approval_id>` (no enum or frontier change), never completion; this
  also applies to a manual merge while the engine attempt is nonterminal, which that merge settles
  (Q4). After a terminal attempt the approval has ended, and a later manual merge is outside any
  approval, like a manual merge without an attempt. Detection reads only the merge
  commit, parent 1 and merged base persisted on the attempt record, so a raced attempt never
  latches, completes or cleans up, and a repeated observation returns the recorded attention.
- **I5 No inferred approval.** Only the user's Cockpit approval (HTTP `approve-merge`) creates an approval
  (D14). No MCP tool approves. Proposal approval, readiness, the engine, the supervisor and workers never
  approve.
- **I6 Cleanup never forces.** Automatic cleanup uses the existing `ChangeWorkspaceManager.cleanup`
  path; computed attention (dirty, untracked, ownership, branch mismatch) stops before any
  mutation and is preserved and reported.
- **I7 Formats.** N05-A and N05-B1 change no persisted model. N05-B2 and N05-D register every new or changed
  persisted family in N02's registry, ship its registered migration and pass the LC full form.
- **I8 Locks.** Provider calls hold only the per-Change checkpoint lock, never a portfolio-wide lock
  (programme §5.2).
- **I9 One decision.** Readiness never offers **Approve merge** where acquisition or the merge owner
  would refuse for a known reason; both use the same offer computation (programme §5.4).
- **I10 Single-PR scope.** GitHub's async merge of a stacked PR includes all open downstack PRs,
  and a PR's `base` can change without a head change; the request fences only the head (P4). The
  offer and merge owner refuse a fresh read with `stack.size` > 1 (`merge-blocked/stacked`) or a
  base other than the approved target. A fresh read cannot exclude a later retarget or stack join;
  under U3(e) Delivery accepts that residual window (G2), sends the request without a
  scope-enforcing provider fact and detects a changed scope after the merge (D9, I4).
- **I11 Merge fence.** While a `MergeAttemptRecord` is nonterminal (`intent`, `released`,
  `pending`), readiness reports `merge-in-progress` or `merge-response-unknown` before any other
  reason, so acquisition selects no target sync, mark ready, finalization or worker; the owners of
  target sync, mark ready, review-repair preparation, the external-head tools and the public
  finalization reconciliation refuse with
  `merge-in-progress` under the checkpoint lock they already hold, before any effect
  ([1.12](#112-owner-fence)). Acceptance observation is exempt and settles the attempt first (I4).
  Abandon and defer stay allowed (Q3); neither settles the attempt.

### 1.4 Persisted record families

New persisted state. Each new family gets an entry in N02-A's registry module (`state_formats.py`,
`FAMILIES`). N05-B2 adds a marker-only format step 2 → 3 after N03-A's format 2 (A1): an older
controller treats an unregistered file as `unrecognized`, not a refusal, so without the step it would
act on a Change with a live attempt. If another step merges first, N05-B2 renumbers (F6, G5). N05-D
adds its own step. Paths are relative to `.owlbear/delivery/runtime/changes/<change>/`.

| Family (proposed registry ID) | Path | Owner model (module) | Class | Identity over bytes | Phase |
| --- | --- | --- | --- | --- | --- |
| `merge_attempt` | `merge-attempts/<approval_id>.json` | `MergeAttemptRecord` (new `merge_approval`): `approval_id`; provenance (`submission_id`, host, session, `approved_at`, D14); the approved offer facts (repository, PR number and node ID, head, base, target head, finalization ID, ready receipt ID, method); `state` `intent → released → pending`, terminal `merged`, `refused`, `not-sent`, `head-changed`, `closed` (1.11); `released_at` with group ID and start time (diagnostic); `request_id` (UUID, or the adopted `409` UUID); refusal reason; on `merged`: merge commit, parent 1, merged base and `race` (`none`, `target-advanced`, `scope-changed`) | M (CAS rewrite under the checkpoint lock) | `approval_id` = SHA-256 of `offer_id` and `submission_id` (D4) | N05-B2 |
| `review_feedback_handoff` | `review-feedback/<handoff_id>/handoff.json`, `revisions/<digest>.json` | `ReviewFeedbackHandoff` (new `review_feedback`; kind `repair` or `no-repair`) | M (CAS revisions, R history) | `handoff_id` | N05-D |
| `review_reply` | `review-feedback/<handoff_id>/replies/<reply_id>.json`; frozen bodies `review-feedback/<handoff_id>/reply-bodies/<sha256>.json` (read-only) | `ReviewReplyReceipt`: frozen body digest (file written before spawn, D16); `intent → released` (release recorded) `→ posted` or `not-posted`; `unknown` until a marker hit (Y2); a CAS revision records the one automatic repost (Y4, D13); 1.11 | M (CAS revisions) | `reply_id` | N05-D |

The merge request body is transient: written right before spawn outside the scanned state tree and
removed after the request finishes (D16, A1). `coordination`, `action_result`, `retry_*` and
`recovery_*` are unchanged (A1). Attempts live outside the frontier (D4), so frontier v19 and its
pinned writers stay unchanged.
Completion receipts, latches and observation receipts keep their bytes (I2 of N02).

### 1.5 Interfaces and error cases

| Interface | Phase | Behavior and errors |
| --- | --- | --- |
| `PublicationMergeProvider` (new runtime-checkable Protocol in `publication_provider.py`) | A | `read_merge_settings(repository, branch)`, `read_branch_head(repository, branch)`, `request_merge(RequestPublicationMerge, *, body_path, release)` (D16), `read_merge_request(repository, number, request_id)`, `read_merge_evidence(repository, number)`. Separate from `PublicationProvider` so existing fakes stay valid (D1) |
| `RequestPublicationMerge` | A | `repository`, `number`, `node_id`, `expected_head_sha`, `merge_method` (`merge`, `squash`, `rebase`); no bypass, queue or auto-merge field exists |
| `PublicationMergeRequestResult` | A | `status`: `pending` (`PendingMergeRequest`: UUID and the reported expected head, method, action, bypass flag), `merged` (merge commit), `refused` (`PublicationMergeRefusal`: `head-changed`, `not-mergeable`, `closed-or-draft`, `rules-failed`, `forbidden`, `queue-required`, `validation`), `unavailable` (UUID result `404`: expired or not found; readback evidence absent, never a refusal); bounded provider message |
| `PublicationMergeEvidence` | A | merged flag, head, base, stack (`size`, `position`, base ref and SHA; absent when not stacked), merge commit, merge-commit parents, merged-at; used for the offer (I10) and post-merge target verification (D9) |
| `PublicationMergeSettings` | A | allowed methods, viewer push permission, target rule types, merge-queue and up-to-date requirements (ruleset `strict_required_status_checks_policy`; unreadable classic protection counts as not enforced, F1); `execution_scope_enforced` (GitHub: `false`; memory provider configurable; informational only: under U3(e) it gates no merge) |
| Effect launcher (`effect_launcher.py`, new) | A | `freeze_body(request) -> bytes` (canonical JSON); `request_merge` refuses a `body_path` whose bytes differ, spawns the launcher, calls `release(group_id, start_time)` and writes the token only after it returns; a raised `release` closes the pipe (no request). Launcher: EOF, short token, digest mismatch or missing file → exit with no request (D16) |
| Transport errors | A | Existing `PublicationProviderError`; write timeout or unreadable write response → `RESPONSE_UNKNOWN`, `retry_safe=False`; GitHub `409` on merge-async → `pending` with the existing request's UUID and reported options (not an error); options missing → unknown, never matching |
| `MergeOffer` (projection on `DeliveryReadiness.merge_offer`) | B1 | Fields of I1 plus title, proof summary (finalization observation count, review ID, proof target), check summary (required passed/pending/failed, optional failed); `offer_id` excludes the title. One computation serves readiness and `approve_merge` (I9) |
| `PortfolioApplication.approve_merge(ApproveChangeMerge)` | B2 | Inputs `change_id`, `offer_id`, `submission_id` (generated by the Cockpit dialog; a retried POST repeats it), `host_id`, `session_id`. Called only by the Cockpit HTTP route (D14). Under the checkpoint lock: a retry with the same `submission_id` returns the same attempt; another nonterminal attempt → `ERR_DELIVERY_MERGE_IN_PROGRESS`; otherwise recomputes the offer from a fresh read, writes the attempt `intent`, sends one request through the launcher (`released` written before the token, D16), records the response and applies 1.11, then on `merged` the acceptance observation. Errors `ERR_DELIVERY_MERGE_OFFER_STALE` (carries the fresh offer or block; no attempt written), `ERR_DELIVERY_MERGE_UNAVAILABLE` (typed block), provider errors (the attempt stays `released` and settles by readback) |
| New readiness reasons | B1, B2 | B1: `merge-approval-required` (with `merge_offer`), `merge-checking`, `merge-blocked` (with `merge_block`: `conflicts`, `behind`, `protection`, `draft`, `closed`, `checks-failed`, `queue-required`, `stacked`, `capability-unavailable`, `method-not-allowed`), `target-sync-required` (a finalized Change without a recorded proof target; U3 amended 2026-10-07), `checks-running`, `provider-unavailable`. B2: `merge-in-progress` and `merge-response-unknown` with the `merge_attempt` summary (`approval_id`, `state`, `approved_head`, `pr_url`; 1.13) |
| MCP | C | No new tool; no MCP tool approves a merge (D14). Check again in the chat is the existing `observe_acceptance` (1.13) |
| HTTP `POST …/changes/{change_id}/approve-merge` | C | Called after the visible **Approve merge** dialog with the dialog's `submission_id`; runs `approve_merge`, which sends the request, settles and observes acceptance in the same call; `409` stale offer with the fresh offer, `409` in progress, `503` provider unavailable. Check again uses the existing observe-acceptance route |
| MCP `record_review_feedback_handoff`, `show_review_feedback_handoff`, `post_review_feedback_replies` | D | Handoff CAS revisions bound to PR and head, and to the repair invalidation (`repair`) or the current finalization (`no-repair`); replies posted by the engine under D13 custody and settled by 1.11 rows Y1–Y4; an `unknown` reply is reposted once automatically (Y4); errors `ERR_DELIVERY_REVIEW_HANDOFF_STALE`, `…_MISSING`, `…_INCOMPLETE` |

### 1.6 Existing owners to reuse

Source locators refreshed by symbol at `origin/dev` `d0223e0a1` (N05-B amendment); re-resolve by name
at implementation. Paths under `owlbear_delivery/` unless stated.

| Owner | Locator | Use |
| --- | --- | --- |
| Merge provider (N05-A) | `publication_provider.py` `PublicationMergeProvider` (`read_branch_head` `:456`, `request_merge` `:460`, `read_merge_evidence` `:474`); `owlbear_delivery_github/github.py` `request_merge` `:688-724` → `_rest_effect` `:1252`; `memory.py` `request_merge` `:320` | Offer reads, the single request, settlement reads |
| Forbidden-effect gate (N05-A allowlist) | `tests/test_delivery_worktree_authority.py` | Add B2 files (D11) |
| Acceptance owner | `portfolio_application.py`: `reconcile_awaiting_acceptance` `:296`, `_reconcile_awaiting_acceptance_locked` `:502` (classifies before `_observe_acceptance_once`), `_classify_acceptance_observation` `:563`, `observe_acceptance` `:661`, `_observe_acceptance_once` `:718` (sole `complete_change` caller `:804`, then the latch) | Settlement first, race check, cleanup after completion (D6, D10) |
| Acceptance retry episode | `portfolio_application.py:692-716` (`RetryFailureClass.ACCEPTANCE`, `ACCEPTANCE_WAIT` stop); `recovery.py` `RetryLedger.reserve` (one explicit read per episode: `explicit_observations == 0` `:1328`, `>= 1` `:1400`); readiness `acceptance-wait` `application_readiness.py:1411-1420` | Bounded automatic reads; one explicit read per Check again (D6) |
| Engine result reason | `application_acquisition.py:800` (waiting → `merge-approval-required`), `_record_engine_attempt_result` `:695`, `_invoke_engine_owner` `:954`; `application_models.py:1192` (persisted reason literal) | L2: chat shows the readiness reason; persisted bytes unchanged (D5) |
| Readiness | `application_readiness.py`: `_capture_action_basis` `:1459`, `_supports_finalization` `:1744` (target sync only before finalization), `_action_prerequisites` `:1787`, `_engine_action_prompt` `:1801`, `_delivery_snapshot` `:2207`, `_publication_observation` `:2222` (L1 short-circuit `:2233-2235`, `None` on failure `:2240-2243`; cache `application_support.py:143`, 15 s); `work_items.py` basis, reasons, cards | L1, L2, offer, distinct waits, U3(a) route |
| Proof target | `runtime_models.py:716` `DeliveryFinalization` (no target field), `:1473` `target_sync_receipt`; `change_workspace.py:170-182` (basis target head: local ref, no fetch) | I1 strict-proof comparison against `read_branch_head` |
| Target sync and external heads | `application_publication.py`: `sync_change_with_target` `:155` (lock `:168`; draft return only before a head change), `adopt_external_head` `:254`, `promote_external_head` `:395`; `application_acquisition.py` `_engine_action_preflight` `:880` (compares the action target with the unfetched local ref `:902`); `delivery_runtime.py` `_target_sync_update` `:1650` (invalidates finalization only on a head change); `workspace_target_sync.py` exact-fetch check (`ChangeTargetSyncStaleError`) | U3(a) route; owner fence (1.12) |
| Mark ready and review repair | `application_publication.py`: `mark_change_ready` `:838`, `prepare_review_repair` `:977`; `share/skills/w-address-pr-feedback/SKILL.md` | Required-check semantics; owner fence; #225 handoff |
| Cleanup | `application_lifecycle.py:173` `_cleanup_change_worktree_locked`; `change_workspace.py:739` `ChangeWorkspaceManager.cleanup` (attention before mutation) | Automatic cleanup (D10) |
| Supervisor sweep | `checkpoint_supervisor.py:68` → `application_publication.py:1254` `reconcile_pending_checkpoints` | Host the cleanup sweep |
| Checkpoint lock | `portfolio_application.py:1942` `_checkpoint_lock_root`; `storage_io.py:122` `locked_roots`; `application_acquisition.py:993` `_engine_checkpoint_lock` | Owner fence (1.12) |
| N02 registry, migration, LC | `state_formats.py:62-65` (`FORMAT_MIGRATIONS`, format 2 after N03-A); [N02 plan](delivery-n02-plan.md) §1.4, §1.5, §3.3 (`state_migration`, `delivery-lc`) | Register `merge_attempt`; step 2 → 3 |
| Assembled proof | Default loader, `Client(assemble_target_server(...))`, Cockpit HTTP client, `start-work-portfolio-stack.mjs` | Fakes only below the provider (fake `gh`, P10) |

### 1.7 Exclusions

Merge queues and auto-merge (queue-required targets fall back to manual merge, D7); provider update
of a PR branch; squash and rebase (U1(a)); any provider other than GitHub.com through
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
  pending request's UUID and options on a repeated request (`409`) and `200` when already merged
  (P4). A `409` request is adopted only
  when its `expected_head_sha`, `merge_method`, `merge_action` and `bypass_rules` equal the approved
  head, U1 method, `direct_merge` and `false`; a `409` whose successfully parsed options differ
  settles the single request `refused/foreign-request` (S4); an option-less or incomplete `409` is
  the adapter's `RESPONSE_UNKNOWN` (1.5) and settles only by readback (S8): Delivery's request had no effect, and a foreign merge is
  observed like a manual one. Rejected: synchronous `PUT …/merge` (no
  request identity; `405`/`409` only) and GraphQL `mergePullRequest` (synchronous, same head fence,
  no request identity). Neither API fences the base (P2, P4).
- **D3 N05-A changes no persisted bytes.** New models are transport-only; existing models are not
  edited; new names are imported from `owlbear_delivery.publication_provider`, not the package root,
  so `owlbear_delivery/__init__.py` and N01's surface fixture stay untouched.
- **D4 One attempt record per approval, outside the frontier.** `approval_id` = SHA-256 of
  `offer_id` and the dialog's `submission_id`: a retried POST returns the same attempt; a new dialog
  submission of the same offer is accepted once the earlier attempt is terminal (D14). At most one
  attempt per Change is nonterminal. Validity is computed at use (I1), so head, target,
  finalization or check changes refuse without a frontier write. There is no revocation: approval
  and request happen in one Cockpit request (A1). The frontier, its writers and
  `_require_change_mutable` stay unchanged (1.12).
- **D5 Merge in the approve owner, not an engine action.** `approve_merge` sends the request in the
  Cockpit request that approves it; the attempt record is its journal (`intent` before spawn,
  `released` before the token (D16), the response after). `ChangeContinuationAction`,
  `DeliveryEngineActionResult`, the retry ledger and the recovery models are unchanged (A1). The L2
  label defect (waiting mapped to `merge-approval-required`, `application_acquisition.py:800`) is
  fixed by showing the chat the readiness reason, not by a persisted result change.
- **D6 Settlement inside the acceptance owner.** 1.11 runs right after the acceptance read, before
  any classification or check can return (I4, A4): Cockpit's `reconcile_awaiting_acceptance` settles
  before `_classify_acceptance_observation` returns for an open, closed or moved-head PR, and
  `_observe_acceptance_once` (explicit `observe_acceptance`, the `observe-acceptance` engine action)
  before its identity check. Automatic reads stay bounded by the existing acceptance retry episode
  (`RetryFailureClass.ACCEPTANCE`, `ACCEPTANCE_WAIT` stop). After the stop, each explicit
  `observe_acceptance` performs one read (Check again, 1.13): N05-B1 removes the one-explicit-read cap
  in `RetryLedger.reserve`; the automatic budget is never reset and the record shape is unchanged.
  No new retry episode, predicate or successor action exists.
- **D7 Capability boundary.** Merge is offered only when the provider implements D1, the viewer
  can push, the U1 method is allowed, the target requires no merge queue and the PR is not stacked
  (I10). Neither an up-to-date rule nor a scope-enforcing provider fact is required (U3(e)).
  Otherwise readiness shows `merge-blocked` with its block (`capability-unavailable`,
  `queue-required`, `stacked`) and "merge in GitHub" guidance; a manual merge is still observed
  (R4). `delivery_health` does not report the capability (it would need network reads); the
  readiness block explains the limit where it matters (A7).
- **D8 L1 refresh.** Readiness refreshes an expired cached observation in every publication phase,
  not only before ready (P8). Provider failure yields `provider-unavailable`, never stale data or
  `None`. The readiness basis gains no observation field: every acting owner re-reads the provider
  itself (mark ready reads checks, acceptance reads the PR, `approve_merge` recomputes the offer).
- **D9 L2 classification.** Mergeability `UNKNOWN` → `merge-checking` (bounded re-read; GitHub
  computes it lazily, P3); `CONFLICTING`/`DIRTY` → `merge-blocked/conflicts` → target sync route;
  `BEHIND` → `merge-blocked/behind` → target sync route; `BLOCKED` →
  `merge-blocked/protection` (act in GitHub); draft or closed → their block; failed required
  checks → `checks-failed`; pending required checks → `checks-running`.
  Only `CLEAN`, `HAS_HOOKS`, or `UNSTABLE` with no failed required check are offerable. After a
  merge, parent 1 of the merge commit is compared with the approved target head and the merged
  PR's base with the approved target; a difference is reported as `target-advanced-during-merge`
  or `scope-changed-during-merge` acceptance attention, never completion (I4; the race that no API
  fences, P2, G2; U3(e)).
- **D10 Automatic cleanup.** Immediately after a completion is recorded, under the same checkpoint
  lock, call the locked cleanup variant (`_cleanup_change_worktree_locked`; re-taking the flock in
  one process would deadlock). The supervisor sweep (`reconcile_pending_checkpoints`) retries each
  completed Change with a retained worktree at most once per controller process. Attention stays
  computed and is shown in the retained-worktree and completed views; nothing is forced. Inside
  continuation custody (the `observe-acceptance` engine action) cleanup may report active custody
  as attention; it is best effort there and the sweep retries.
- **D11 Gate becomes an allowlist.** The forbidden-effect tests keep forbidding auto-merge,
  `enablePullRequestAutoMerge`, update-branch, `enqueuePullRequest`, `merge_queue`,
  `bypass_rules: true` and any merge call outside allowlisted provider functions. `merge_method` is
  allowed only in an enumerated set of files (provider, N05-B2 and N05-C modules declared here);
  acceptance, latch, completion and observation models keep no merge-method field.
- **D12 Governance text.** Delivery publishes Change branches, draft PRs and state, and merges only
  after an exact-head user approval; agents never run `git push`, `gh pr merge` or provider
  mutations directly (the programme-specific `redesign/*` push exception of execution plan §1.2
  stays).
- **D13 #225 in Delivery.** The handoff is a Delivery record, not chat output; replies are posted by
  an engine operation through the provider with a hidden per-reply marker. Reply writes are
  serialized per handoff under the per-Change checkpoint lock and run through the release-gated
  launcher (D16): frozen body before spawn, group record, then release record. Settlement follows rows
  Y1–Y4 of [1.11](#111-effect-settlement-contract). An `unknown` reply (Y4) is reposted once with the
  same marker after transport closure and a marker-negative read; the worst case is one duplicate
  comment, which is visible and harmless in the operating context. No user decision is involved.
  External comments stay evidence, never Design or Delivery authority.
- **D14 Merge approval in Cockpit** (2026-10-04; replaces PR #360's elicitation and consent records).
  In the execution plan's operating context agents are trusted but fallible, so the guard is that their
  tools do not offer user-only actions: no MCP tool approves a merge, and the continuation chat shows the
  offer and points to Cockpit. The user approves in Cockpit's **Approve merge** dialog; the approval is
  recorded with the dialog's `submission_id` and provenance as today. Under the checkpoint lock the
  owner re-verifies the fresh offer's `offer_id` the user saw (else `ERR_DELIVERY_MERGE_OFFER_STALE`). No
  Origin or cookie hardening and no OS presence check.
- **D15 No time expiry.** Approvals do not expire by time; I1 re-verifies every fact at execution.
- **D16 EOF-safe effect entry.** `gh api --input -` passes stdin to `client.Do` unbuffered
  (v2.65.0 `api.go` `openUserFile`, `http.go`), so a dead controller's closed stdin can send an
  empty `PUT`; merge-async then defaults `sha` to the current head and the action to `default`.
  Merge and reply writes therefore enter through a release-gated launcher (option b, using a's file):
  1. Before spawn the owner durably writes (write, `fsync`, rename, directory `fsync`) the frozen
     body, the canonical JSON of the approved request with every field (`sha`, `merge_method`,
     `merge_action`, `bypass_rules`), and records its digest. A merge body is a transient file
     outside the scanned state tree, removed after the request finishes (A1); a reply body is the
     read-only content-addressed file of 1.4.
  2. The runner spawns new `owlbear_delivery_github/effect_launcher.py` in a new session. It opens
     no connection and blocks on a fixed-size release token (operation ID and body digest) on stdin.
  3. The owner durably records the group's ID and start time, then a release record, then writes
     the token. For a merge, the `release(group_id, start_time)` callback writes the attempt
     `released` (with the group) before it returns. Only the runner holds the pipe's write end
     (`close_fds`), so controller death is EOF.
  4. The launcher reads the whole token, re-hashes the file, sets stdin to `/dev/null` and, only on
     an exact match, `exec`s `gh api … --input <file>` in the same group; `gh` sends the file with
     `Content-Length` from its size. EOF, a short token, a mismatch or a missing file exit unsent.
  - Possible submission starts at the durable release record (1.11). Absence of a group record
    proves nothing; absence of a release record proves `gh` never ran (rows S3, Y1).
  - The launcher is kept as merged in N05-A (A5); N05-A's EOF falsifier proves it on macOS and
    Ubuntu, so N05-B adds no controller-death subprocess test.
  - Rejected: (a) alone leaves `gh` effect-capable before its group is recorded, so an unrecorded
    live child can never be shown closed; (c) adds a second transport with token, proxy and TLS
    handling, larger than one launcher module.
  - Other existing provider writes keep `--input -`; they are not 1.11 effects.

Lead decisions 2026-10-04 (N05-B amendment, under the user's authorization to simplify to the
operating context; [execution plan §7](delivery-redesign-execution-plan.md#7-decisions)). Each
line gives its reason; later reviews do not reopen them.

- **A1 Persisted state** (lead decision 2026-10-04): one `merge_attempt` record per approval;
  transient frozen body; no `coordination`, `action_result`, `retry_*` or `recovery_*` widening;
  a marker-only format step after N03-A's format 2. Reason: approval and request happen in one
  Cockpit request, so nothing waits to be revoked, replayed or journaled as an engine action, and
  only a marker makes an older controller refuse a state it cannot read.
- **A2 Settlement S1–S8 replaces M1–M9** (lead decision 2026-10-04): M6 consent withdrawal, M8
  re-request and per-submission series are cut; M9 is split into S6–S8. Reason: one `sha`-fenced
  request per approval leaves them no trigger, and GitHub merges a PR at most once.
- **A3 Owner fence** (lead decision 2026-10-04): a helper in target sync, mark ready, review-repair
  preparation and the external-head tools, plus the readiness fence (1.12); no `mutation_fence.py`,
  guard threading or lock-entry rework. Reason: those owners are the paths honest agents and own
  processes reach; a runtime mutation without an application owner is outside the operating context.
- **A4 Settlement in the acceptance owner** (lead decision 2026-10-04): settlement right after the
  acceptance read on every path (D6) with the existing acceptance retry budget; one
  `merge-response-unknown` attention with the PR link; Check again = explicit `observe_acceptance`.
  Both D6 retry episodes, `merge_reads_exhausted`, `MergeHold`, the guidance codes,
  `check_merge_status`, revocation and the `merge-approved` reason are cut. Reason: that owner
  already polls on every path, bounds automatic reads and allows explicit reads after exhaustion.
- **A5 D16 launcher as merged** (lead decision 2026-10-04): no N05-B controller-death or
  delayed-transport subprocess test. Reason: N05-A's EOF falsifier proved the launcher on both
  platforms; N05-B2 only orders the `released` write before the token, which a unit test shows.
- **A6 Proportionate negative scenarios** (lead decision 2026-10-04): the sets of 3.4 and 3.5,
  with crash proofs at the four outcome-changing boundaries. Reason: every other boundary collapses
  into "before" or "after" the release record.
- **A7 False premises fixed** (lead decision 2026-10-04): the offer binds the required checks'
  conclusions, not check observation IDs (they digest `observed_at`); the proof target is the sync
  receipt's target head (the finalization has none); strict proof compares against the provider's
  branch head, not the readiness basis's local ref read without a fetch; the frontier is v19; 1.6
  locators are refreshed by symbol; the L1 basis fence and the `delivery_health` capability line are
  dropped. Reason: source reads at `d0223e0a1`.
- **Q1 One request per approval** (lead decision 2026-10-04): no automatic re-request after an
  unknown merge; the user merges in GitHub (observed), abandons or defers. Reason: the rare dead end
  has a user exit, and a re-request adds a state for it.
- **Q2 Head moved or PR closed settles terminally** (lead decision 2026-10-04): S6 and S7, which
  win over a still-pending UUID (S5) because the request is `sha`-fenced to the approved head.
  Reason: a return to the old head inside GitHub's pending window is a coincidence of independent
  timing events; acceptance's identity check still flags any merge at another head.
- **Q3 Abandon and defer stay allowed during an attempt** (lead decision 2026-10-04); a later merge
  of an abandoned Change is not attributed to its proof (documented limit). Reason: they are the
  user's exits and take the checkpoint lock, so they never interleave with the request.
- **Q4 Post-merge parent-1 and base check stays** (lead decision 2026-10-04) as `identity-mismatch`
  acceptance attention, also for a manual merge while the engine attempt is nonterminal (the merge
  then settles that attempt). After a terminal attempt (for example an S4 refusal) the approval has
  ended; a later manual merge is the developer's own decision outside any approval, the same as a
  manual merge without an attempt (plan challenge round 2, 2). Reason: strict proof,
  U3(e). A manual merge without an attempt is not checked against the proof target: it is the
  developer's or a collaborator's explicit decision outside any Delivery offer; strict proof (U3 part
  1 (a)) governs the offer and the engine merge, completion identity is the finalized head (programme
  §10.1), and the execution plan observes manual merges as completion (plan challenge round 1, 4).
- **Q5 N05-B splits into N05-B1 and N05-B2** (lead decision 2026-10-04): B1 is the read side (3.4,
  no format change), B2 the effect side (3.5); N05-C follows B2; N05-D is unchanged. Reason: B1
  carries no effect or format change and merges independently.

### 1.9 User decisions

All four were decided on 2026-10-03; each records its basis. N05-A depends on none of them;
nothing in N05-P depends on them.

**Execution-plan amendment.** The deltas F1–F8 of [1.10](#110-premise-findings-and-execution-plan-deltas)
amend the execution plan's rules and schedule notes (its §1.1): merged under the user's overnight
authorization of 2026-10-03; confirmed 2026-10-03 (listed to the user without objection).

**U1 — Merge method and authority scope** (decided 2026-10-03: (a); required before N05-B starts).
Status quo: Delivery cannot merge. The older design locked this
([acceptance redesign](delivery-proposal-acceptance-redesign.md) line 1050: "OwlBear agents and
Delivery services cannot merge"), enforced by gates added in `09b98bfc9` and stated in
`setup/operating-owlbear.md:306`. The approved execution plan supersedes it for N05 (§5 N05 result).
The repository allows merge, squash and rebase (P1). Problem: the engine must send a method; squash
and rebase create new commits, so the exact reviewed head is not in target history and the
parent-1 target check (D9) does not apply. Options:
(a) merge commit only, direct merge, never bypass, auto-merge, update-branch or queue; one approval
per merge in Cockpit; targets that disallow merge commits show `method-not-allowed`;
(b) the user picks a method in each approval among those the repository allows;
(c) a per-repository method in Delivery config (config family v3 with a registered migration).
**Decision (2026-10-03): (a)**, an engineering decision with one defensible answer, listed to the
user without objection. It keeps the reviewed head in history, matches this repository's
existing "Merge pull request #N" history and keeps every check exact.

**U2 — Real merge test on a disposable repository** (decided 2026-10-03: (b); scope reduced on
2026-10-04 to one smoke test, 3.3). Status quo: probes are read-only; execution plan §1.3
requires a disposable repository and the user's permission for provider mutation tests. Problem:
GitHub's async merge semantics (UUID on `409`, `400` for drafts, rules failures, readback, head
fence) are documented but unexecuted (G1). The token has scopes `gist, read:org, repo, workflow`
and no `delete_repo` (P1). Options: (a) the user creates a disposable private repository and
permits the agent to push branches, open PRs and merge there; (b) the agent creates the
repository (deletion stays the user's); (c) no real test; fakes only.
**Decision (2026-10-03): (b)**, an engineering decision listed to the user without objection: the
agent creates a disposable private repository and the user deletes it afterwards (the token
lacks `delete_repo`). On 2026-10-04 the lead replaced the multi-scenario rehearsal by one smoke test.

**U3 — Target freshness and the execution-time target race** (decided 2026-10-03 by the user:
part 1 (a), part 2 (e); required before N05-B starts). Status quo: readiness offers target sync
only before finalization
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
post-merge detection (D9) cannot undo that. Programme §10.2 (before its 2026-10-03 revision)
required enforced protection or queue semantics where the target cannot be fenced. Options:
(d) enforced: engine merge only where the fresh rules read shows the target requires up-to-date
branches (merge queues stay excluded, D7); otherwise `merge-blocked/target-unenforced` and the
user merges in GitHub. On `dev` this needs the user to add that rule; agents never change settings;
(e) detection-only: the user accepts, as a dated requirement revision of programme §10.2 that
passes the plan gate, that the target may advance during execution; Delivery reports
`target-advanced-during-merge` and claims no stronger guarantee.
Part 2 also covers the execution scope (I10): the request fences only the head, and a `base`
retarget or stack join after the final read changes what merges (P4); the (d) rule binds only the
branches it targets, and no provider fact that enforces the scope is known at N05-P.
**Decision (2026-10-03), by the user in chat after a full status-quo, problem, options and
pro/con briefing: part 1 (a); part 2 (e), applied to both the execution-time target race and the
execution-scope race of I10.** Consequences:

- Engine merge is not blocked by the absence of a GitHub up-to-date rule or of a scope-enforcing
  provider fact. `merge-blocked/scope-unenforced` and `merge-blocked/target-unenforced` are
  retired; no GitHub setting changes.
- The fresh pre-request read still refuses `stack.size` > 1 (`merge-blocked/stacked`) and a base
  other than the approved target (I10).
- After the merge, Delivery compares parent 1 of the merge commit with the approved target head
  and the merged PR's base with the approved target (D9), and reports `target-advanced-during-merge`
  or `scope-changed-during-merge` as acceptance attention, never completion attributed to the proof
  (I4). Delivery claims no stronger guarantee. The interval between the final read and GitHub's
  execution is not bounded by Delivery (a request can stay pending, 1.11 rows S5 and S8); unintended
  merges can occur in it, and detection cannot undo them.
- G2 becomes a recorded, accepted residual risk with detection evidence. A stack join or retarget in
  the seconds after the final read is a coincidence of independent timing events, outside the
  operating context; the parent-1 and base comparison is the cheap detection, and a stacked execution it
  does not expose is a documented limit.
- This revises programme §10.2, recorded with the old text, revision and reason in the
  [programme](change-continuation-delivery-redesign.md#102-merge-approval-is-a-bounded-user-action)
  and approved by the user on 2026-10-03.

**Amendment (2026-10-07), by the user in chat after a status-quo, problem, options and pro/con
briefing: part 1 changes from (a) to (b); part 2 (e) is unchanged.** Reason: (a) assumed re-proof
runs automatically, but since automatic dispatch was removed every re-proof needs a user-started
chat (sync, finalize with independent review, mark ready). `dev` advances many times a day and has
no up-to-date rule, so the offer expired before the user saw it and merges moved to GitHub without
any Delivery offer. Under (b) a moved target keeps the offer: `offer_id` binds the current target,
the offer reports the finalized proof target separately, and Cockpit states that the proof does not
cover the newer target commits. Conflicts, `BEHIND`, failed or pending required checks and the D9
post-merge comparison are unchanged; a finalized Change without a recorded proof target still
syncs. Path-scoped carry-forward (c) was rejected because a target commit outside the Change's
paths can still break it.

**U4 — Exit from an unsettled merge** (decided 2026-10-03: (b); reversed 2026-10-04 by the lead,
[execution plan §7](delivery-redesign-execution-plan.md#7-decisions)). The 2026-10-03 contract (b), a
user-confirmed non-merging retirement with its own record and terminal disposition, is removed. A merge
response still unknown after the automatic reads shows the 1.13 attention with the PR link. The user
checks GitHub and resolves it through existing routes: a merge is observed (S1 → completion; S2 →
acceptance attention); **Check again** is the existing explicit `observe_acceptance` (one read per
invocation, D6); otherwise the user abandons or defers the Change (always allowed, Q3). Delivery claims no
cancellation; a request sent earlier may still execute, and a later merge of an abandoned Change is not
attributed to its proof (documented limit).

### 1.10 Premise findings and execution-plan deltas

Findings against the execution plan and programme, with evidence. The N05-P PR applies these
deltas to the execution plan (amendment recorded in [1.9](#19-user-decisions)).

| # | Finding | Evidence | Execution-plan delta (applied) |
| --- | --- | --- | --- |
| F1 | The provider cannot re-read classic branch protection with WRITE permission; protections are visible only as rules and `mergeStateStatus` | `GET branches/dev/protection` → 404; `viewerCanAdminister: false`; `rules/branches/dev` readable (P1) | §5 N05: "re-reads PR state, head, target, rules, mergeability and checks" |
| F2 | No GitHub merge API fences the target; this repository has no up-to-date rule or merge queue, so the target fence is pre-read plus post-merge detection only | P2, P4; ruleset 14785182 = `deletion`, `non_fast_forward` | §5 N05: no provider-side target fence; enforced rules or U3 decide (G2) |
| F3 | The forbidden-effect gates assert that Delivery cannot merge anywhere; N05-A must revise them | `tests/test_delivery_worktree_authority.py:1417-1430`, `:1603-1629`; P6 | §5 N05-A: revises the no-merge gates to an allowlist (N01 §3.7 allows the file) |
| F4 | `merge-approval-required` is an engine-result reason, not a readiness reason; Cockpit has no mirror | `application_models.py:1169-1176`; `work_items.py:274-311`; `workItems.ts:67-120` | §5 N05: N05-B owns it as a readiness reason, with companions |
| F5 | N05-B and N03 phases list shared core modules (`application_readiness.py`, `application_acquisition.py`, `work_items.py`, `workspace_models.py`), so §4.3's ready rule serializes them despite the stage-3 lane split | §4.3 ready rule bullet 4; N05-B paths ([3.4](#34-n05-b1--merge-offer-readiness-and-cleanup), [3.5](#35-n05-b2--merge-attempt-settlement-and-fence)) | §4.3 schedule note: stage 3 runs N03 and N05-B1…D sequentially where paths overlap |
| F6 | N05-B and N03-A both bump N02's format marker; whichever merges second renumbers its migration onto the other's and reruns LC full form | N02 plan D3 | §4.2 note |
| F7 | Reason text renders from `workItemPresentation.ts`, not only `WorkItemDetail.tsx`/`WorkPortfolioPage.tsx` | `workItemPresentation.ts:58-64` | §1.4 companion list: add `workItemPresentation.ts` |
| F8 | New N05 decision U3 (target freshness and execution-time target race) | §1.9 | §7 "Decided later": add U3 to N05 |
| F9 | Package-plan prerequisites added: N05-B needs U1 and U3 answered (decided 2026-10-03); N05-C merge needs the smoke test (3.3); engine merge needs no scope-enforcing fact (U3(e); G2 is an accepted residual risk) | §1.9 | None (§4.2 allows package-added prerequisites) |
| F10, F11 | PR #360 made N05-B and N05-C depend on N03-A's user-only boundary and consent records; removed on 2026-10-04 (D14) | Execution plan §7 | §4.2: N05-B and N05-C no longer need N03-A |

No phase was re-split at N05-P; the 2026-10-04 amendment splits N05-B into N05-B1 and N05-B2 (Q5).

### 1.11 Effect settlement contract

**Merge (N05-B2).** One function settles a merge attempt from one fresh read (PR state and head,
merge evidence, and the recorded UUID result if any); rows are listed in match order and the first
matching row wins (S6 and S7 precede S5, Q2). `approve_merge` applies it right after its request, and
every acceptance path applies it right after its read, before any classification (D6). Acceptance
attention, latch, completion and cleanup run only after it.

- Possible submission starts at the durable `released` record (D16); without it `gh` never ran.
- After possible submission, a terminal state needs provider evidence of merge, refusal, a head
  change or closure. Expiry, absence, timeouts and elapsed time are never refusal evidence; a UUID
  `404` is never `refused`.
- One approval sends one request (Q1); no row sends another.
- Attempt settlement is not Change acceptance: only S1 can lead to completion, through
  `_observe_acceptance_once` at the finalized head, and only when `race` is `none` (I4).

| Row | Evidence (fresh read; first match wins) | Settlement | Next step |
| --- | --- | --- | --- |
| S1 | PR merged at the approved head (released or not) | `merged`; merge commit, parent 1 and merged base persisted; `race` `target-advanced` when parent 1 ≠ approved target head, `scope-changed` when base ≠ approved target, else `none` | Acceptance completes once when `race` is `none`; otherwise `identity-mismatch` attention, no latch, completion or cleanup (I4, Q4) |
| S2 | PR merged at another head | `head-changed` | Existing acceptance identity check records `identity-mismatch` attention; no completion or cleanup |
| S3 | No `released` record | `not-sent` | The offer reappears; a new approval is needed |
| S4 | The request's complete refusal (`400`, `403`, `405`, `422`), UUID result `failed` or `enqueued`, or a `409` whose parsed options differ from the approval's | `refused` with reason (`queue-required` for `enqueued`, `foreign-request` for the `409`) | Readiness shows the block; a new approval is needed |
| S6 | PR closed unmerged (also with a pending UUID) | `closed` | Existing `CLOSED_UNMERGED` acceptance attention (Q2) |
| S7 | PR open at another head (also with a pending UUID) | `head-changed` | Existing `HEAD_MOVED` finalization invalidation (Q2) |
| S5 | UUID result `pending` with the approval's options | `pending` | Polled by the acceptance owner within its budget (D6) |
| S8 | Anything else after release (UUID absent or `404`, read failed, an option-less or incomplete `409` that the adapter reports as `RESPONSE_UNKNOWN`, PR open at the approved head) | stays `released` (unknown) | Automatic reads within the acceptance budget; then `merge-response-unknown` attention (1.13) |

**Reply (N05-D).** The same entry rules apply to replies (D13, D16). A reply has no provider
de-duplication; an unknown reply is reposted once (Y4), accepting a possible duplicate comment.
"Transport closed" means the reply's recorded process group is confirmed gone (G12); a release record
without a group record is a defect and settles Y4, never Y1.

| Row | Effect | Evidence (fresh read; first match wins) | Settlement | Next step |
| --- | --- | --- | --- | --- |
| Y1 | Reply | No release record (a group may be recorded; D16) | No possible submission; stays `intent` | Post after a marker read |
| Y2 | Reply | Hidden marker found in a viewer reply on the thread | `posted` | Thread may be resolved |
| Y3 | Reply | Complete provider rejection of this write: HTTP `4xx` error body, or GraphQL `errors` with null `data` (G13) | `not-posted` | Post again with the same marker after a marker read |
| Y4 | Reply | Anything else after the release record: timeout, signal, `5xx`, unreadable output, controller death | `unknown` | After transport closure and one marker-negative read, post once more with the same marker; a later marker hit settles Y2. At most one automatic repost per reply |

A repost may produce a duplicate comment when the first write landed late. That is visible, harmless
and accepted under the operating context; it needs no user decision.

Falsifiers (N05-D): a reply effect delayed past transport closure and a marker-negative read is
reposted exactly once and never again; crash after the repost, replay → marker read, no third post.

EOF falsifier (G12): real `gh` against a local HTTP recorder, on macOS and Ubuntu. Controller death
before the durable release record sends no request (S3, Y1); death after it sends at most one
request, byte-equal to the frozen body, and settlement stays nonterminal until evidence (S8, Y4).
N05-A proved the launcher half on both platforms (#356); N05-D adds the reply controller case.

### 1.12 Owner fence

`_require_no_merge_in_flight(change_id)` reads the attempt store and raises `merge-in-progress`
while an attempt is nonterminal (A3). The application owners of target sync
(`sync_change_with_target`), mark ready (`mark_change_ready`), review-repair preparation
(`prepare_review_repair`), the external-head tools (`adopt_external_head`,
`promote_external_head`) and the public finalization reconciliation
(`reconcile_finalization_head`) call it first under the per-Change checkpoint lock they already hold,
before any provider, Git or frontier effect. Acceptance's internal head reconciliation
(`_reconcile_finalization_head_locked` from the acceptance owner) stays exempt: it runs after
settlement, which has already made a moved-head attempt terminal (S7). `approve_merge` writes `intent`, `released` and the
response under the same lock, so a concurrent own process either sees the attempt and refuses, or
finishes first and makes the approval's fresh offer stale. Readiness reports `merge-in-progress` or
`merge-response-unknown` before any other reason, so acquisition never reaches these owners as
engine actions while an attempt is open (where an owner refusal would become a `blocked` engine
result). `_require_change_mutable` and its call sites stay unchanged; a runtime mutation called
without an application owner is outside the operating context.

### 1.13 Unknown merge and user exit

While an attempt is `released` or `pending` and the acceptance episode has not stopped, readiness is
`merge-in-progress` (actor system). Once the episode stops (`ACCEPTANCE_WAIT`), readiness is
`merge-response-unknown` (actor you, `human` acquisition) with the `merge_attempt` summary
(`approval_id`, `state`, `approved_head`, `pr_url`). Card, Cockpit and chat show one attention with
the PR link: "GitHub has not confirmed this merge. It may still run. Check the PR in GitHub: merge
it there, Check again, or Pause or Abandon the Change." Approve merge, mark ready, target sync,
review repair and worker controls are not offered; Abandon and Pause stay enabled (Q3). **Check
again** is the existing explicit `observe_acceptance` (MCP tool and Cockpit route): one read per
invocation that settles the attempt first (D6), without a budget reset. A merge in GitHub settles on the next read
(S1 or S2). Delivery offers no cancel; a request may still execute after abandon or defer, and such
a merge is not attributed to the Change's proof (documented limit, Q3).

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
| P11 | `p_disjoint.py`: N05-A paths against N01-A/B/C maps and N01 §3.7 exclusions | No clash; the only shared file is the execution plan status table (a companion) | R12; [3.8](#38-n01-disjointness-check-for-n05-a) |
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
  merge owner, settlement, L1/L2, registry and migration (B1, B2); route semantics and prompt rules (C);
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
    fails the gate run); `test_merge_rehearsal.py` was listed here but not created by N05-A; the
    smoke test of 3.3 replaces it
  - `tests/test_delivery_worktree_authority.py` (provider and forbidden-effect gates, D11);
    `tests/fixtures/delivery-authority/forbidden-fields.py`, new `forbidden-provider-merge.py`
  - this plan's N05-A progress row; the execution plan's N05-A status row
- **Must not edit** while any N01 phase is unmerged: the N01 list in [3.8](#38-n01-disjointness-check-for-n05-a).
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
    `release(group_id, start_time)` and writes the token only after it returns (D16).
    `gh` reads the file (`--input <file>`), never stdin.
  - Merge-specific failure parsing reads stdout JSON and the stderr status: `409` with a UUID →
    `pending` carrying the reported options; `409` without them → `RESPONSE_UNKNOWN` (never
    matching); `400` → `refused/closed-or-draft`; `403` → `refused/forbidden`; `405`/`422` →
    `refused/not-mergeable` or `validation`; result `failed` → `refused/rules-failed` with bounded
    message; `enqueued` → `refused/queue-required`; `GET` UUID `404` → `unavailable` (never a
    refusal); write timeout or unreadable write response → `RESPONSE_UNKNOWN`.
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

### 3.3 Smoke test on a disposable repository (step, not a phase)

Replaces the multi-scenario real-GitHub rehearsal A-R (2026-10-04).

- **When:** on the N05-C candidate head, before N05-C merges. The agent creates the disposable
  private repository (U2(b)); the user deletes it later.
- **Owner:** N05-C implements `serve/delivery-github/tests/test_merge_smoke.py` (marker `api`, runs only
  with `OWLBEAR_MERGE_SMOKE_REPO` set).
- **Steps:** create a PR; approve it through the Cockpit HTTP route; the engine merges it at the exact
  head; Delivery observes completion once.
- **Evidence:** command, repository, PR number and observed statuses on the N05-C PR. No other repository
  is mutated.

### 3.4 N05-B1 — Merge offer, readiness and cleanup

Read side; no persisted format, effect or request (Q5).

- **Prerequisites:** N05-A, N01-C, N02-B (execution plan §4.2); U1 and U3 decided (2026-10-03). G2
  is an accepted residual risk (U3(e)) and gates nothing.
- **Editable paths** (N01 phase in brackets):
  - new `owlbear_delivery/merge_offer.py` (`MergeOffer`, `MergeBlock`, and the one offer computation
    from fresh merge evidence, the cached PR observation, required checks, merge settings and the
    provider's target branch head; L2 classification)
  - `application_readiness.py` [A]: `_publication_observation`, `_delivery_snapshot` (D8);
    `_capture_action_basis` and `_supports_finalization` (U3(a) `target-sync-required` for a
    finalized Change, compared against `read_branch_head`; since the 2026-10-07 U3 amendment only
    without a recorded proof target); awaiting-merge readiness with the offer
    and the B1 reasons; `_action_prerequisites`; `_engine_action_prompt`
  - `application_acquisition.py` [A]: the chat-facing reason comes from readiness, not the persisted
    `merge-approval-required` label (L2, D5); replay mapping; `_engine_action_preflight` does not
    compare a `sync-target` action's provider-derived target with the unfetched
    `observed_target_head()`, so it reaches `sync_change_with_target` and its exact-fetch check
  - `application_publication.py` [A]: the sync route's expected target is the provider's branch
    head; a sync of a finalized Change to a new target returns the PR to draft through the existing
    draft-return owner also when the head is unchanged; `reconcile_pending_checkpoints` runs the
    cleanup sweep (D10)
  - `delivery_runtime.py` [C]: `_target_sync_update` invalidates finalization and ready when the
    receipt's target head differs from the proof target (strict proof, U3(a)), not only on a head
    change
  - `recovery.py`: `RetryLedger.reserve` allows one explicit acceptance read per invocation while the
    episode is stopped at `ACCEPTANCE_WAIT` (the `explicit_observations` caps go; the counter still
    counts; automatic budget and record shape unchanged; D6)
  - `portfolio_application.py`, `application_lifecycle.py` [A]: `_observe_acceptance_once` calls
    best-effort cleanup after completion (D10)
  - `application_support.py` [A]: PR body text (`:341` "merge this pull request in GitHub")
  - `application_models.py` [A]: non-persisted readiness reason literals only
  - `work_items.py`: readiness reasons, `merge_offer`, `merge_block`, awaiting-merge card text
    ("merge in GitHub"; the approve action is named only once N05-C ships the dialog)
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py` (readiness schema only)
  - frontend companions: `serve/cockpit/web/src/api/workItems.ts`,
    `components/workItemPresentation.ts`, `WorkItemDetail.tsx` (offer summary, block and wait text,
    no control), component tests; `tests/test_cockpit_boundary.py`
  - tests: new `serve/delivery/tests/test_merge_offer.py`; `serve/delivery/tests/test_portfolio_application.py`
    (`test_background_and_explicit_acceptance_share_durable_budget`: a second explicit observation
    reads once more; automatic reads stay stopped)
  - this plan's progress row; the execution plan's status row
- **Positive scenarios:**
  - Awaiting merge, `CLEAN`, required checks green, proof target equal to the provider's target
    branch head → `waiting/merge-approval-required`, actor you, card guidance "merge in GitHub", offer
    fields equal provider facts; a
    second read with a new check observation (new `observed_at`) yields the same `offer_id`.
  - Finalized Change, local remote-tracking ref stale, provider target head newer →
    `waiting/merge-approval-required` with the offer bound to the newer target and the proof target
    reported beside it; finalization and ready stay recorded and acquisition waits (U3 amended
    2026-10-07; the earlier sync, refinalize and re-review route applies only without a recorded
    proof target). Parametrized over a changed and an unchanged candidate head.
  - Automatic acceptance reads exhausted with the PR open → Check again reads once and waits;
    restart; manual merge at the finalized head; Check again → one read, completion once; automatic
    reconciliation makes no read throughout.
  - Manual merge in GitHub at the finalized head → acceptance completes once and cleanup removes the
    clean worktree in the same call; completed views show completion and cleanup separately.
  - A completed Change with a retained clean worktree → the sweep cleans it once per process.
  - A provider without D1 → `merge-blocked/capability-unavailable`; the card says to merge in GitHub.
- **Negative scenarios:**
  - Offer classification, one parametrized test: `CONFLICTING`/`DIRTY` → `conflicts` with the sync
    route; `BEHIND` → `behind`; `UNKNOWN` → `merge-checking`; `BLOCKED` → `protection`; draft,
    closed, stacked (`stack.size` 2), wrong base, `method-not-allowed`, `queue-required`; a failed
    required check → `checks-failed`; a pending one → `checks-running`. None yields
    `merge-approval-required` in readiness or in the chat-facing acquisition result (L2).
  - L1: expired cache with a ready receipt → readiness re-reads; provider down →
    `provider-unavailable`, not an offer.
  - Unexpected file in the completed worktree → cleanup preserved with attention; completion intact;
    the sweep does not force it.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_merge_offer.py -q -n0`.
- **Closeout:** `uv run test --changed`; scoped Ruff; `npm --prefix serve/cockpit/web test`;
  `npm --prefix serve/cockpit/web run build`; Biome on changed frontend files; `uv run pytest
  tests/test_cockpit_boundary.py tests/test_delivery_worktree_authority.py -q`.
- **LC:** not applicable (no persisted format, loading or startup change).
- **Size / risk:** M / medium (estimate: 450–600 product lines plus about 150 frontend, 400–600 test
  lines).
- **Implementation notes (2026-10-04, N05-B1 build):**
  - An open awaiting-merge PR at the finalized head is a readiness wait or block, never an executable
    `observe-acceptance`; the engine reads acceptance once readiness sees the PR merged, closed or moved.
    The card keeps **Check merge status**, so Cockpit's reconciliation and the explicit read stay reachable.
  - `merge_block` adds `wrong-base`: I10 refuses a base other than the target, and 1.5 listed no value for it.
  - `DeliveryContinuationResult` reports the readiness reason for a waiting engine result (D5); the
    persisted engine label is unchanged.
  - `DraftPullRequestPublisher.provider` (read-only property, outside the path list) serves the offer reads.
  - The D11 `merge_method` allowlist in `tests/test_delivery_worktree_authority.py` gains `merge_offer.py`,
    `workItems.ts` and `WorkItemDetail.tsx`, which show the offer's method (no acceptance or completion model).
  - With an unchanged head, a sync to a new target clears finalization and ready without an invalidation
    receipt (the receipt requires head drift and I7 forbids a new reason); a finalization without a
    target-sync receipt counts as unproven against any target.
  - Cleanup is skipped inside engine custody (the `observe-acceptance` engine action); the sweep cleans it.
  - Progress: blocks only Delivery's merge has (capability, queue, stack, method) stay `ready-to-merge`;
    `checks-running` maps to `waiting-for-service` because `checking` is a reserved key.

### 3.5 N05-B2 — Merge attempt, settlement and fence

Effect side (Q5).

- **Prerequisites:** N05-B1.
- **Editable paths** (N01 phase in brackets):
  - new `owlbear_delivery/merge_approval.py` (`MergeAttemptRecord`, store with CAS rewrite, the S1–S8
    settlement function, errors)
  - new `owlbear_delivery/application_merge.py` (`_MergeMixin`: `approve_merge`,
    `_require_no_merge_in_flight`, transient body)
  - `portfolio_application.py` [A]: facade base; the settlement call right after the read in
    `_reconcile_awaiting_acceptance_locked` (before `_classify_acceptance_observation`) and in
    `_observe_acceptance_once` (before its identity check); the race attention (I4)
  - `application_readiness.py` [A]: `merge-in-progress` and `merge-response-unknown` before other
    reasons, `merge_attempt` summary (1.13)
  - `application_publication.py` [A]: fence call in `sync_change_with_target`, `mark_change_ready`,
    `prepare_review_repair`, `adopt_external_head`, `promote_external_head`,
    `reconcile_finalization_head` (1.12)
  - `work_items.py`: the two reasons, the summary and the attention text (1.13); `merge-approval-required`
    guidance still names only merge in GitHub
  - `state_formats.py`, `state_migration.py` [N02]: `merge_attempt` registration, marker-only format
    step 2 → 3; `serve/tools/src/owlbear_tools/delivery_diagnostics.py` mirror
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py` (readiness schema only)
  - frontend companions: `workItems.ts`, `workItemPresentation.ts`, `WorkItemDetail.tsx` (attention
    text with the PR link, no control), component tests; `tests/test_cockpit_boundary.py`
  - `tests/test_delivery_worktree_authority.py` (allowlist entries for B2 files only)
  - tests: new `serve/delivery/tests/test_merge_approval.py`; `serve/delivery/tests/test_state_formats.py`
    fixture; `serve/tools/tests/test_delivery_diagnostics.py`
  - this plan's progress row; the execution plan's status row
- **Positive scenarios:**
  - Happy path (memory provider): offer → `approve_merge` → one request with `sha` = approved head,
    `merge_method` `merge`, `merge_action` `direct_merge`, `bypass_rules` false → `merged` → one
    completion → cleanup; a retried call with the same `submission_id` returns the same attempt and
    sends nothing.
  - `pending` → readiness `merge-in-progress`, actor system → acceptance reads poll the UUID →
    `merged` → one completion, no second request.
  - When the provider writes the release token, the stored attempt is already `released` (unit, D16).
- **Negative scenarios** (each asserts the provider request log):
  - Offer invalid at execution, one parametrized test: head changed, target branch head changed,
    check failed or pending, stale `offer_id` (`ERR_DELIVERY_MERGE_OFFER_STALE` with the fresh
    offer), stacked, wrong base, draft or closed → no request, no attempt written.
  - Two concurrent approvals (threads) → one attempt, one request; an approval while another attempt
    is nonterminal → `ERR_DELIVERY_MERGE_IN_PROGRESS`.
  - Lone request refused (S4) → `refused`, readiness shows the block; a new approval is accepted.
  - Settlement table, one parametrized test over S1–S8, including S1 from `intent` (manual merge
    after a crash), UUID `404` → stays `released` (never `refused`), and a foreign `409` →
    `refused/foreign-request`, not adopted.
  - Settlement on every acceptance path, one parametrized test: restart with a `released` attempt,
    then background reconciliation of a PR with a pending UUID at the approved head (→ `pending`),
    closed unmerged (→ `closed`, then `CLOSED_UNMERGED`), open at another head (→ `head-changed`,
    then `HEAD_MOVED`) and a pending UUID with a moved head (→ `head-changed`, S7 over S5); each
    terminal case lifts the owner fence.
  - Post-merge race, parametrized target advance (parent 1) and retarget (base), including a manual
    merge while an engine attempt is nonterminal (Q4) → `identity-mismatch` attention with its diagnostic; no latch,
    completion receipt or cleanup; a second observation returns the same attention and writes nothing.
  - Unknown beyond the budget, assembled (default loader, `Client(assemble_target_server(...))`):
    lost response and failing reads until `ACCEPTANCE_WAIT` → `merge-response-unknown`, actor you,
    summary with the PR URL, no further automatic read; Check again → one read, still unknown;
    restart; the fake merges; Check again → one read → S1 → one completion.
  - Fence, one parametrized test over the six owners of 1.12 with a nonterminal attempt →
    `merge-in-progress`, empty provider, Git and frontier effect logs.
  - Abandon while unknown → succeeds, no request, the attempt stays `released`.
  - Crash proofs at the four outcome-changing boundaries: (a) before the `released` record →
    `not-sent`, empty request log; (b) after it → unknown, readback converges (merged → one
    completion); (c) after `merged` settlement, before completion → replay completes once;
    (d) after completion, before cleanup → the sweep cleans.
  - Downgrade: a format-2 release refuses format-3 state with `state-newer-than-controller`
    (one `test_state_formats` fixture; LC full form).
- **Inner loop:** `uv run pytest serve/delivery/tests/test_merge_approval.py -q -n0`.
- **Closeout:** `uv run test --changed`; scoped Ruff; frontend test, build and Biome on changed
  frontend files; `uv run pytest tests/test_cockpit_boundary.py tests/test_delivery_worktree_authority.py
  tests/test_package_boundary.py -q`.
- **LC:** full form through `delivery-lc`: unmigrated copy refused, migrated copy loads with every
  Change available, the previous release refuses (N02 D3 oracle), live hashes unchanged.
- **Size / risk:** M / high (estimate: 650–800 product lines, 700–900 test lines; external effect,
  crash replay, format step).
- **Implementation notes (2026-10-05, N05-B2 build):**
  - Settlement makes its own fresh merge-evidence read (plus the UUID read while the PR is open at the
    approved head) right before the acceptance PR read; the race check runs right after that read. A
    retargeted PR no longer matches its bound publication, so the acceptance read refuses it: the attempt
    still settles `merged`/`scope-changed`, but no observation exists to carry the `scope-changed`
    attention; the existing publication-identity refusal shows instead (never completion, latch or
    cleanup). Check again is one read set (evidence, UUID when pending, acceptance read).
  - Sol implementation round 1 (fixed): GitHub's asynchronous merge can finish between the settlement read
    and the acceptance read, so the acceptance read could complete (or raise attention) while the attempt
    stayed `pending` and the parent-1/base check never ran. When the acceptance read no longer shows the
    attempt's PR open at the approved head, settlement now reads again before the race check and any
    classification, latch, completion or cleanup; if the attempt is still open, acceptance waits.
  - `approve_merge` observes acceptance after releasing the approval's checkpoint lock (re-taking the
    flock in one process deadlocks, D10); a later read completes when that one cannot.
  - The fence raises `DeliveryMergeError` (a `PortfolioApplicationError`) with `ERR_DELIVERY_MERGE_IN_PROGRESS`.
    A moved head at approval is `ERR_DELIVERY_MERGE_OFFER_STALE`; a provider outage or a retargeted PR
    whose bound publication read refuses is `ERR_DELIVERY_MERGE_UNAVAILABLE`.
  - Readiness skips the fence for abandoned and completed Changes; the attempt summary carries the PR URL.
  - Crash (c) is the approval's own `merged` settlement before its acceptance observation. A crash inside
    an acceptance observation leaves that acceptance retry attempt reserved, so later reads stop at
    `retry-containment` (D03 behavior, independent of N05-B2; reported to the lead).
  - The unknown-merge test checks again through `Client(assemble_target_server(...))` with the memory
    provider injected below the application; the default loader builds the `gh` provider, which N05-C
    fakes. Companions outside the listed paths: `test_delivery_progress.py` (reason table),
    `test_state_migration.py` (steps), the golden attempt record and owner fingerprint.
  - LC finding: the offline inspector flagged a migration-required format only at format 0, while the
    gate refuses any older format with runtime records; the first full form from a non-zero format (2)
    failed on that mismatch. The inspector now mirrors the gate (`delivery_diagnostics.py`, one case).
    The full form also counted the journal of the earlier (N03-A) migration as a changed record, since
    it compared a tree with journals against one without; it now compares both without (`delivery_lc.py`).

### 3.6 N05-C — Adapters, Cockpit approval, continuation path and governance

- **Prerequisites:** N05-B2.
- **Editable paths:**
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py` (`observe_acceptance` description
    only, if needed); `serve/delivery-mcp/tests/test_target_server.py`
  - `serve/cockpit/src/owlbear_cockpit/routes/target_work.py`, `target_models.py`;
    `tests/test_cockpit_work_items.py`, `tests/test_cockpit_boundary.py`
  - `serve/delivery/src/owlbear_delivery/work_items.py` (awaiting-merge guidance names the Cockpit
    approval)
  - frontend: `src/api/workItems.ts`, new `src/components/MergeApprovalDialog.tsx`,
    `WorkItemDetail.tsx`, `workItemPresentation.ts`, the work-items mutation hook, component tests
  - E2E: `e2e/work-portfolio.spec.ts`, `e2e/support/seed-work-portfolio-delivery.py`
    (awaiting-merge and unknown-merge fixtures), `e2e/support/start-work-portfolio-stack.mjs` (fake `gh` on `PATH`),
    new `e2e/support/fake-gh.mjs`
  - `share/prompts/continue-change.prompt.md`, `share/skills/w-orchestration/SKILL.md`,
    `share/agents/orchestrator.agent.md` (only if its text names merge ownership),
    `share/skills/r-workspace-governance/SKILL.md:66`, `share/skills/w-change-finalization/SKILL.md`
    (merge ownership text, if any)
  - `setup/operating-owlbear.md:300-345`, `README.md` Delivery section, `serve/delivery/README.md`,
    `serve/delivery-github/README.md`
  - `tests/test_delivery_worktree_authority.py` (allowlist entries for C files only)
  - new `serve/delivery-github/tests/test_merge_smoke.py` (3.3)
  - this plan's progress row; the execution plan's status row
- **Contract:** Cockpit shows the offer only for `merge-approval-required` with an offer, with every R1
  field and the consequence ("merges into `<target>` in GitHub; Delivery cannot undo it"), as the
  **Approve merge** dialog with **Approve merge** and **Cancel** (D14). States: submitting, merged then
  completing, refused with reason, stale (re-review the new offer), provider unavailable, and the
  1.13 unknown-merge attention with the PR link and **Check again** (the existing observe-acceptance
  route; never shown as checking; Abandon and Pause enabled). The
  continuation workflow, on a `human` result with `merge-approval-required`, shows the offer and says to
  approve it in Cockpit or merge in GitHub, and stops; it never claims an approval itself (D14). On
  `human` with `merge-response-unknown` it shows the 1.13 attention and PR link, asks one question
  (Check again / Not now) and makes one `observe_acceptance` call per Check answer; it never loops.
- **Positive scenarios:** HTTP `approve-merge` through the Cockpit client → one attempt, merge and
  completion on a disposable portfolio with the memory provider; a retried POST with the same
  `submission_id` returns the same attempt. E2E: approve in the dialog → the fake `gh` records exactly one
  merge request → **Completed**. Agent-ecosystem tests accept the revised skills
  and prompts. The smoke test (3.3) passes on the disposable repository.
- **Negative scenarios:** the assembled MCP server registers no tool that approves a merge; the
  continuation prompt contains no approve call and no approve question of its own.
  Offer changed between showing and submitting the dialog → `ERR_DELIVERY_MERGE_OFFER_STALE`, no approval.
  Stale-offer E2E (fake head changes while the offer is shown or the dialog is open →
  stale message, no merge request in the fake log); cancel sends nothing; HTTP `409` stale and in
  progress, `503` provider unavailable; no control
  appears for `merge-blocked`, `checks-running`, `merge-checking`; the capability gate still rejects
  auto-merge and update-branch strings in Cockpit and agent files.
- **Unknown-merge E2E (1.13):** fixture with an unknown attempt (fake `gh` reports nothing). Reload →
  attention with the PR link and **Check again**; no **Approve merge**. Click → exactly one read set
  in the fake log, no merge-async `PUT`, still unknown. The fake merges the PR at the approved head →
  click → **Completed**. **Abandon** → no merge request in the fake log. Continuation test:
  acquisition returns `human` with `merge-response-unknown`; the prompt asks Check again / Not now and
  makes one `observe_acceptance` call per answer.
- **Inner loop:** `uv run pytest tests/test_cockpit_work_items.py -q -n0 -k merge`; then
  `uv run pytest serve/delivery-mcp/tests/test_target_server.py -q -n0`.
- **Closeout:** `uv run test --changed`; scoped Ruff; `npm test`, `npm run build`, Biome;
  `npm --prefix serve/cockpit/web run test:e2e:work` (Chromium);
  `uv run pytest tests/test_agent_ecosystem_validation.py -q`.
- **LC:** full form (execution plan §5 N05: full form from N05-B2 on); no format change expected.
- **Size / risk:** M / medium.
- **Implementation notes (2026-10-05, N05-C build):**
  - `POST /api/changes/{change_id}/approve-merge` takes `offer_id` and the dialog's `submission_id`; the
    approval's host is the Cockpit machine name and its session `cockpit`. `DeliveryMergeError` maps to `409`
    (stale, in progress) or `503` (unavailable), each with the fresh readiness; a provider error keeps the
    existing `502` mapping (the attempt stays `released` and settles by readback).
  - The dialog keeps the offer under review. Each opening mints `cockpit-merge-<uuid>`, repeated on a retried
    POST; a stale refusal disables re-approval of that offer. The detail reports the attempt state.
  - An unknown merge's acceptance control is labelled **Check again** (`work_items.py`).
  - The continuation skill shows a merge offer and stops; on `merge-response-unknown` it asks Check again /
    Not now and calls `observe_acceptance` once per Check again answer. Orchestrator gains the
    `observe_acceptance` tool; `tests/test_agent_ecosystem_validation.py` pins its tool map (companion outside
    the listed paths), and `WorkPortfolioPage.tsx` wires the new prop.
  - Default-loader proof of the unknown merge (deferred from B2): the work E2E stack starts a third Cockpit
    (port 4177) on a merge fixture seeded through `load_delivery_application` with `e2e/support/fake-gh.mjs`
    first on `PATH`. Its four Changes cover the stale offer, Check again then a manual merge, Abandon while
    unknown, and Cancel then approve. Tests drive the fake with `__move-head`, `__merge` and
    `__restore-target` (the fixtures share one target branch, so a merge would otherwise make later offers
    stale). The smoke test reuses the fixture's public-owner lifecycle helpers.
  - Smoke finding, fixed here (`github.py`, outside the listed paths): GitHub Free refuses
    `rules/branches/{branch}` on a private repository with `403` ("Upgrade to GitHub Pro"), so the merge facts
    were unreadable and readiness stayed `provider-unavailable`; no merge was ever offered. A `403` on that
    read now means no rules (none can apply on that plan; GitHub still enforces any rule at merge time, S4).
    The first smoke repository stopped there with its PR open and no merge request.
  - The portfolio E2E describe releases its `/api/work-items` route after each test: with the third Cockpit
    running, a poll in flight at test end failed an existing completed-history test (`route.fetch: Test ended`).
  - Found, not changed here: after `mark_change_ready`, readiness keeps the pre-ready (draft) PR observation
    for its 15-second cache lifetime, so the offer shows `merge-blocked/draft` until it expires (B1 cache). The
    generated PR body still says "merge this pull request in GitHub" (`application_support.py`); changing it
    rewrites every published PR summary. The awaiting-merge publication card headline still reads "Merge pull
    request in GitHub" (`work_items.py` `_awaiting_merge_state`); the readiness detail carries the control.

### 3.7 N05-D — PR-feedback continuity (#225)

Built only if it stays small (execution plan §5 N05); otherwise it is cut at its start and #225 stays
open.

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
    response it reads the thread's comments by the viewer and settles by 1.11 rows Y1–Y4; an `unknown`
    reply is reposted once with its marker (Y4). It resolves a thread
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
  closure and a marker-negative read → `unknown`, one repost, then the delayed reply → `posted`;
  timeout or `5xx` → `unknown`, never `not-posted`; GraphQL `errors` with null `data` → `not-posted`,
  one later post; `unknown` after transport closure and a marker-negative read → exactly one repost with
  the same marker, then a late original → both comments visible, reply `posted`, no further post;
  repaired thread not repaired
  twice after restart (repair commit already recorded); reply response lost → marker found →
  no duplicate; reply posted but resolve fails → thread unresolved, repair evidence intact; external
  comment text never changes Delivery authority.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_review_feedback.py -q -n0`.
- **Closeout:** `uv run test --changed`; scoped Ruff; agent-ecosystem tests; package closeout: full
  `uv run test` once and a cumulative Sol challenge of the N05 diff against this plan.
- **LC:** full form.
- **Size / risk:** M / medium-high (external comments; replay).

### 3.8 N01 disjointness check for N05-A

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
| N05-P | #353 | — | Probes P1–P16 | Sol round 1: revision-required (stack scope, execution-time target race in U3, pending/unknown reconciliation, renewable consent, no-repair handoff, 409 option validation) → revised; Sol round 2: revision-required (execution scope policy, successor ledger accounting, outstanding-reply reconciliation, complete repair map, fence owner/ordering) → revised; Sol round 3: revision-required (reply non-execution authority, expiry ≠ refusal, fence lock-entry contract) → consolidated settlement contract; Sol round 4: revision-required (request-series settlement, repost decision replay, guard helper scope) → revised; consistency pass (D6/§1.4/§1.5 aligned with §1.11–§1.12); Sol round 5: revision-required (EOF-safe effect entry) → revised; Sol round 6: revision-required (EOF oracle vs release record) → revised; Sol round 7: revision-required (head drift vs pending series) → revised; Sol round 8: revision-required (held-state user exit) → revised; Sol round 9: blocked (U4 non-merging retirement) + 3 fix-now → revised; U4 pending; Sol round 10: revision-required (exhausted M7 hold) → revised; Sol round 11: revision-required (M1 vs observed manual merge) → revised; Sol round 12: `plan-sound`; user-decision revision #360 (history; its D14 boundary, consent records and U4 (b) retirement were removed on 2026-10-04): Sol round 1: revision-required (raced M2 completion, A-R rehearsal split and ownership, unbounded execution interval) → revised; Sol round 2: revision-required (A-R does not discriminate execution-time rules) → ordered pending-then-change step with stop-and-ask; lead's deferred item: D14 moves approval, retirement and reply decisions onto N03 D13 (F10); Sol round 3: revision-required (renewed merge consent replayable within the request-state TTL) → single-use consent generation (D14, D4, `merge_consent`); Sol round 4 (N03 finding, cross-plan): a declined or cancelled question stayed replayable with an affirmative answer → D14 moves onto N03's shared `consent_generation` family (N03 D13 *Single use*), `merge_consent` removed, N05-B needs N03-A (F11) | approved (execution-plan amendments confirmed 2026-10-03; U1–U4 decided 2026-10-03; N03 U2 open before N05-C) |
| N05-A | #356 | `a4951b044` | Ubuntu CI run 37147328711 exact head: 3953 passed, 3 skipped (no launcher skips); macOS focused launcher/provider/authority 149 passed; `test --changed --py` 3955 passed; real-gh recorder 409 formats captured; parser mutation fails 7 tests | Sol implementation round 1: repair-required (real-gh 409 parsing, merge-call ownership gate, typed pre-release failures) → repaired; round 2: `implementation-sound` | merged |
| Smoke (3.3) | N05-C | `ee74f72ad` | Run 1 `boecht/owlbear-merge-smoke-20261005030104` at `0c94abdf9`: no offer (`provider-unavailable`, rules read `403` on GitHub Free; fixed in N05-C), no merge request, PR #1 open. Run 2 `boecht/owlbear-merge-smoke-20261005030543`: `OWLBEAR_MERGE_SMOKE_REPO=… uv run pytest serve/delivery-github/tests/test_merge_smoke.py -q -n0 -s -p no:cacheprovider` passed (89 s); PR #1; `approve-merge` `200` `pending`; acceptance `200`, completion `71056e46…`; merge `1f3162bde` parents `[eaddc3892, 9830ca4b1]` (target, approved head); GitHub `merged: true` | — | done; both repositories left for the user to delete |
| N05-B1 | #371 | `651afebcd` | `uv run test --changed` 3310 passed (580 s), Cockpit 364 passed; earlier at `ffbe5a62c`: build, Biome, ruff clean; `test:e2e:work` 27 passed | Sol implementation round 1 on `2353ca7d3`: repair-required. (1) Rejected, documented limit G15: cleanup does not preserve ignored files. (2) Fixed: a failed PR read in the draft phase projected an executable `mark-ready`; now `waiting/provider-unavailable`, acquisition agrees | merged |
| N05-B2 | #375 | `b79f01eb6` | `uv run test --changed` at `644a923cf`: 3680 passed, 3 companion expectations failed → fixed in `b10076c79`, rerun passed; Cockpit 367 passed; diagnostics/LC/migration 316 passed at `19ccc28d9`; build, Biome, ruff clean; `test:e2e:work` 27 passed; LC full form (Docker, previous `841b1cffb`) passed at `19ccc28d9` after two LC-tool findings fixed here; round-1 repair at `b79f01eb6`: merge/offer tests 81 passed (new inter-read test fails all 8 cases with the fix disabled), `test --changed` 3693 passed (574 s), Cockpit 367 passed, ruff clean; LC not rerun (no format or loader change) | Sol implementation round 1 on `b92536267`: repair-required. (1) Fixed: an asynchronous merge finishing between the settlement read and the acceptance read completed (or raised attention) while the attempt stayed `pending` and skipped the parent-1/base check; the acceptance read now re-settles first and waits while the attempt stays open | in review |
| N05-C | #377 | `5c299b2be` | At code head `ee74f72ad`: `uv run test --changed --base origin/dev` hit the 900 s session limit after 3102 passed (Cockpit Vitest 372 passed); sharded union of the same 64 files 1029 + 1 skipped (smoke) / 1169 / 1363 passed = all 3562 items; build, Biome, Ruff clean; boundary/authority/package 78 passed; `test:e2e:work` failed twice in an existing completed-history test (route callback in flight at test end) → `5c299b2be` releases the route after each test → 31 passed; smoke (3.3) passed on the second repository; LC not applicable (no format or loader change). Package closeout (last N05 phase) at `2e7eed979`: full `uv run test` in one detached run (764 s): Python 4663 passed, 1 skipped (smoke, no env var), 2 failed = all 4666 collected, in 724 s under the 900 s session limit; both failures were 30 s load timeouts in `test_delivery_state.py::test_change_intents_on_planner_pause_of_builder_planning_return_survive_default_loader_restart[historical-True/False]`, rerun alone: 6 passed; Cockpit Vitest 30 files, 372 passed | Sol N05-C implementation challenge: `implementation-sound`, no material findings. Cumulative N05 package challenge (A+B1+B2+C): no material implementation findings; its only `blocked` item, the package-closeout full suite, is satisfied by the run in Proof | in review; the user deletes the smoke repositories `boecht/owlbear-merge-smoke-20261005030104` and `boecht/owlbear-merge-smoke-20261005030543` |
| N05-D | — | — | — | — | not built (lead decision 2026-10-05): 3.7 is not small (M, medium-high risk; two persisted families with a format step and LC full form, three MCP tools, reply custody Y1–Y4, G12/G13 proof). #225 stays open. N05-C is N05's last phase and carries the package closeout |

Plan challenge round 1 (2026-10-04), Sol on `3936d4f8d`: revision-required; lead dispositions:

1. Fixed: settlement runs right after the read on every acceptance path, before
   `_classify_acceptance_observation` returns for open, closed or moved-head PRs; S6 and S7 precede S5
   (I4, D6, 1.11, Q2; 3.5 scenario).
2. Rejected: checking a manual merge without an attempt against the proof target (reason in Q4).
3. Fixed: Check again reads once per invocation after the automatic stop; N05-B1 removes the
   one-explicit-read cap in `RetryLedger.reserve` and updates its test contract (D6, 1.13, 3.4).
4. Fixed: the `sync-target` preflight no longer compares the provider target with the unfetched local
   ref; a sync to a new target invalidates finalization and returns the PR to draft also when the head
   is unchanged (I1, 1.6, 3.4).
5. Fixed: the obsolete reply-decision contract left 1.4 and 1.5 (D13, Y4); N05-B1 and N05-B2 guidance
   names only merge in GitHub until N05-C ships the dialog (3.4, 3.5, 3.6).

Plan challenge round 2 on the N05-B2 part (2026-10-04), Sol on `4a270e807`: revision-required; lead
dispositions, applied as N05-B2's first commit:

1. Fixed: public `reconcile_finalization_head` joins the owner fence (I11, 1.12, 3.5); acceptance's
   internal reconciliation stays exempt after settlement.
2. Fixed as a wording narrowing: Q4's post-merge check covers a manual merge only while the engine
   attempt is nonterminal; after a terminal attempt a manual merge is outside any approval (I4, Q4, 3.5).
   The proposed acceptance-time check for terminal attempts is rejected (round 1, finding 2).
3. Fixed: an option-less or incomplete `409` is the adapter's `RESPONSE_UNKNOWN` and settles by S8;
   only parsed foreign options settle S4 (D2, 1.11).

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | GitHub's async merge behaves as documented beyond the exact-head merge (UUID and options on `409`, `400` drafts, rules at execution, lost-response readback) | The smoke test (3.3) exercises only one exact-head merge; P phase ran read-only | P4 reference; P2 schema; fake tests (A); smoke test | Documented limit | Nothing |
| G2 | The target, the PR's `base` or its stack cannot change between the final read and background execution | No GitHub merge API fences the base or the stack; `base` is editable without a head change; `dev` has no up-to-date rule (P1, P2, P4) | Accepted residual risk (U3(e), programme §10.2 revised 2026-10-03): post-merge parent-1 and base check (D9, I4); a stack join in that window is outside the operating context, and a stacked execution the check does not expose is a documented limit | N05-B2 (detection) | Nothing |
| G4 | Merge-queue and up-to-date-required targets behave as designed | This repository has neither (P1) | Memory-provider scenarios | N05-B1 | Nothing |
| G5 | N05-B2's marker-only step 2 → 3 composes with any other format step | N03-A's step (format 2) is merged; N05-B2's does not exist yet | N02 D3 linear chain; whichever step merges later renumbers (F6) and reruns the LC full form | N05-B2 | N05-B2 merge |
| G6 | The fake `gh` used in E2E matches real GitHub responses | Fake fidelity | P10; smoke test (3.3): one real exact-head merge passed; it did not compare the fake's `409`/unknown paths with GitHub, and it found the rules-read `403` the fake never returned | N05-C (partial; rest documented limit) | Nothing |
| G7 | Marker-based reply dedupe survives edited or deleted replies | Not exercised | Read-back design (D13) | N05-D | Nothing |
| G8 | A 15-second observation cache is fresh enough under rate limits | Not measured | P8; existing constant `application_support.py:143` | N05-B1 | Nothing |
| G9 | The cleanup sweep stays cheap with many completed Changes | Not measured | Bounded supervisor `limit` | N05-B1 | Nothing |
| G10 | `deleteBranchOnMerge` does not disturb completion or later reads | Only manual merges observed so far; the smoke repository had `delete_branch_on_merge: false` | Existing completions after manual merges | Documented limit | Nothing |
| G11 | The per-Change checkpoint lock excludes a concurrent approval or fenced owner and is released when its process dies | Not exercised for merge; no subprocess test is planned (A3, A5) | `locked_roots` uses `flock` (`storage_io.py:122`), relied on by every checkpoint owner; N05-B2 thread concurrency test | Documented limit | Nothing |
| G12 | No `gh` request precedes a durable release record, and every sent request is the complete frozen body (D16; rows S3, Y1); a recorded group identifies live reply transport after controller death (row Y4) | Upstream `--input -` sends stdin EOF as an empty body (v2.65.0 `api.go`, `http.go`) | N05-A launcher EOF falsifier passed on macOS and Ubuntu (#356); `openUserFile` sends a regular file with `Content-Length` | N05-D controller-death test (macOS and Ubuntu, local HTTP recorder) | N05-D engine replies (else replies stay manual) |
| G13 | A complete GitHub `4xx` error or GraphQL `errors` with null `data` for a reply mutation means it did not execute (row Y3) | Provider semantics, not a documented guarantee | `_execute` already treats write timeouts as response-unknown (`github.py:859-866`) | N05-D | Nothing: without proof, row Y3 is dropped and such replies stay `unknown` |
| G14 | `supersede_publication` works for a predecessor that moved, was deleted or was merged | It passes the immutable publication receipt's creation `head_sha` to `_validate_supersession_predecessor`, and `draft_pull_request.py` refuses every merged predecessor (found during N04-P, 2026-10-04) | Source reads only | Documented limit; abandonment plus a successor Change is the route | Nothing |
| G15 | Completed-worktree cleanup preserves every file | Ignored files in a completed Change worktree are not preserved by cleanup: the guard's status omits them and non-forced `git worktree remove` ignores them (N05-B1 challenge round 1) | Same guard as manual cleanup; ignored paths are disposable by convention | Documented limit | Nothing |
