# Delivery N11 — Grant One More Builder Attempt

> **Package:** N11 of the [execution plan](delivery-redesign-execution-plan.md#n11--grant-one-more-builder-attempt),
> added after programme completion (2026-10-06).
> **Planned on:** `origin/dev` `a22319bca`. Live Delivery is pinned to `d25349567` (format 3). Live
> state was read only through Delivery's read tools during diagnosis; probes were read-only source
> and test inventory.
> **Deviation (user-directed):** the user asked for plan, plan gate, implementation and
> implementation gate in one session. N11-P and N11-A share one branch and one PR; the plan commit
> precedes the code commits, and both gates run on their exact heads.
> **Status:** N11-P drafted; plan gate pending. Reviews work in the execution plan's
> [operating context](delivery-redesign-execution-plan.md#19-operating-context).

## 1. Contract

### 1.1 Result

When a same-task Builder retry episode is exhausted, Delivery parks the outcome behind the requestless
block `builder-attempt-limit-<settlement_id>` and keeps the Builder handoff. Today nothing can move
it: **Clear block** is offered but `unblock` refuses while a Builder handoff is retained, and no
operation adds budget without `RetryLedger.reset`, which requires accepted progress.

After N11 the user can press **Grant one more attempt** in Cockpit. One grant:

- resolves that exact block with a fixed, recorded resolution;
- raises the episode's mechanical limit by exactly one attempt and clears its `exhausted` stop,
  keeping every attempt, outcome and count;
- writes one immutable grant receipt;
- commits frontier, retry ledger and receipt in one runtime transaction.

The next `/continue-change` then acquires the same retained task through the existing same-task
handoff route. If that attempt fails again, settlement exhausts the episode again under a new
settlement ID and a new block; the user may grant again. Granting is a user action: agent tools
cannot perform it.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | An exhausted same-task Builder retry block has a user exit that keeps the episode history and does not reset counts | User decision 2026-10-06 (option C) |
| R2 | The exit is user-only: Cockpit offers it; the Delivery MCP `answer` tool refuses it with a typed error | Execution plan §1.9 (agent tools do not expose user-only actions) |
| R3 | One grant adds exactly one Builder attempt; every later exhaustion needs a new grant | User decision 2026-10-06 |
| R4 | The grant is crash-safe, idempotent on replay and fenced to the exact frontier digest, block, settlement and attempt | Execution plan §1.9 (guarded against crashes, honest mistakes) |
| R5 | A local unpublished handoff frontier carrying a grant reloads after restart, before and after the next claim | Existing loader contract for retained Builder handoffs |
| R6 | Format changes are versioned; an older controller refuses state that holds a grant with a typed version diagnostic | Execution plan §1.3 (LC), N02 format registry |
| R7 | The Work Item for the exhausted Builder block shows the new action instead of a failing **Clear block**, with matching guidance | D03 mandatory companions (§1.4) |

### 1.3 Invariants

- **I1 History kept.** A grant never changes `attempt_ids`, `outcome_ids`, `accepted_attempt_ids`,
  `aliases`, `total_attempts`, `repair_attempts`, `reset_count` or `legacy_failures`.
- **I2 Exact target.** The grant applies only when all of these hold:
  - the binding retains a same-task `builder_handoff_context`;
  - its unresolved, requestless block has `block_id == f"builder-attempt-limit-{context.settlement_id}"`;
  - no Change claim is active;
  - the settlement receipt for `context` holds the exhausted retry result equal to the binding;
  - the episode containing `context.attempt_id` is MECHANICAL with `stop_code == EXHAUSTED`.

  Any other state is a typed conflict.
- **I3 One budget unit per grant.** `granted_attempts` increases by one. Every mechanical threshold
  becomes `mechanical_repairs + granted_attempts`. That covers `reserve`, `record_failure`,
  `import_legacy_failures` and the Builder settlement exhaustion test. `RetryLedger.reset` clears it
  together with the other counts.
- **I4 Atomic.** Frontier replacement, ledger summary replacement (expected previous bytes) and grant
  receipt creation form one `RuntimeTransaction`, recovered by the existing `recover_all` paths.
- **I5 Rollback-safe by default.** A ledger with no grant is written as `schema_version` 1, byte-
  identical to today, so the previous release keeps reading it. A ledger with a grant is written
  as `schema_version` 2. The previous release refuses it with `state-newer-than-controller`.
- **I6 Mutability policy.** The new runtime operation `grant_builder_attempt` is registered in
  `_NORMAL_CHANGE_MUTATIONS` and is pause-gated (`_PAUSE_GATED_MUTATIONS`), like `unblock`.

### 1.4 Interfaces and error cases

- **Ledger** (`recovery.py`):
  - `RetryEpisodeSummary.granted_attempts: int = 0` (≥ 0), omitted from JSON when 0.
  - `RetryLedgerSummary.schema_version: Literal[1, 2]`. A validator refuses version 1 with any
    granted episode.
  - `_commit_summary` writes 2 when any episode has a grant and 1 otherwise.
  - New `RetryLedger.prepare_attempt_grant(attempt_id, *, now) -> tuple[ReplacementTransactionParticipant, RetryEpisodeSummary]`
    raises `RetryLedgerConflictError` unless the episode is MECHANICAL and EXHAUSTED. It clears
    `stop_code` and `next_eligible_at`, increments `granted_attempts` and bumps the summary version.
    It does not commit.
  - Registry: `retry_ledger` current 2, `read_upcasts=((1, "owlbear_delivery.recovery:parse_retry_ledger_summary"),)`.
- **Receipt** (`runtime_receipts.py`):
  - `_DeliveryBuilderAttemptGrantReceipt`, schema 1. Fields: `change_id`, `outcome_id`,
    `settlement_id`, `attempt_id`, `episode_id`, `granted_attempts`, `builder_handoff_context`,
    `granted_block`, `updated_block`.
  - Path: `runtime/changes/<change>/builder-attempt-grant-receipts/<settlement_id>.json`.
  - New registry kind `builder_attempt_grant_receipt` ("R", 1), plus diagnostics path, version and
    redaction entries.
- **Runtime** (`delivery_runtime.py`): `grant_builder_attempt(outcome_id, block_id) -> OutcomeAuthorityBinding`.
  - **Replay:** a resolved block that equals the receipt's `updated_block` returns the binding
    unchanged.
  - **Conflicts:** a resolved block without a matching receipt, a wrong block, a missing handoff, an
    active claim, a non-exhausted episode, a changed ledger and an unsafe receipt path each raise a
    typed conflict or reference error.
  - **Resolved block:** `resolution_note = "The user granted one more Builder attempt."`,
    `resolution_locators = (context.settlement_id,)`.
- **Loader** (`delivery_application_loader.py`):
  - For a retry settlement whose local binding differs from `receipt.result`,
    `_builder_handoff_settled_binding` derives the grant successor from the grant receipt, the way
    `_builder_request_resolution_successor` does for pauses. Anything else is a bootstrap failure.
  - `_builder_handoff_lifecycle_baselines` accepts the grant-resolved frontier as a second baseline.
- **Application:**
  - `DeliveryAnswerKind.GRANT_ATTEMPT = "grant-attempt"`. It requires `outcome_id` and `block_id`
    and forbids request, resolution, note, locators and disposition fields.
  - `PortfolioApplication.answer(..., allow_user_only=False)` refuses it with
    `DeliveryConfirmationError`. With `allow_user_only=True` it is fenced by the frontier digest,
    and it is idempotent when the digest has moved but the receipt matches.
  - `DeliveryAnswerResult` requires a binding for this kind.
- **MCP:** `AnswerParams` refuses `grant-attempt` at validation ("granting a Builder attempt is a user
  action in Cockpit").
- **Work items:**
  - New `WorkItemActionKind.GRANT_ATTEMPT` ("grant-attempt", label "Grant one more attempt") is
    returned instead of `CLEAR_BLOCK` for the exact attempt-limit block (I2 shape on the binding).
  - The Builder `retry-exhausted` guidance and the settled block's `unblock_condition` name the
    Cockpit action and keep `/inspect-change` as the read-only diagnosis route.
  - The non-Builder `retry-exhausted` text is unchanged.
- **Cockpit:**
  - Route `POST /api/changes/{change_id}/outcomes/{outcome_id}/blocks/{block_id}/grant-attempt`,
    body `{expected_frontier_digest}`, calls `answer(..., allow_user_only=True)`.
  - Frontend action kind mirror, API call and button in the Work Item detail, with confirmation copy
    that states one more attempt is added and history is kept.

### 1.5 Existing owners to reuse

- `resolve_request` / `_builder_request_resolution_receipt_participant` for the receipt participant.
- `_builder_request_resolution_successor` for loader derivation.
- `RetryLedger._read_with_bytes` and `ReplacementTransactionParticipant` for the CAS ledger write.
- `DeliveryRuntime._replace(..., additional_participants=...)` for the single transaction.
- `TargetCockpitService.clear_block` and its route for the Cockpit plumbing.
- `ClearBlock` UI flow for the button.

### 1.6 Exclusions

- Resetting episodes or granting more than one attempt per action.
- Grants for Planner, Finalizer, transient or acceptance episodes, and for Builder returns or pauses.
- Changing the default budget of three attempts.
- Any live state change. Activation is the user's `/upgrade-delivery` after merge; the blocked live
  Change `pr-feedback-replay-safe-resume` stays blocked until then.

### 1.7 User decisions

| ID | Decision | Outcome |
| --- | --- | --- |
| U1 | Exit for an exhausted Builder retry block | (C) Grant one more attempt as a user action, 2026-10-06 |
| U2 | Plan and implementation in one session | Directed by the user 2026-10-06 (header deviation) |

## 2. Feasibility probes

| Probe | Result | Premise settled |
| --- | --- | --- |
| Ledger and frontier roots | `DeliveryRuntime.retry_ledger()` returns `RetryLedger(self._target_root, change_id)`. The ledger summary is under the same runtime root as the frontier | One `RuntimeTransaction` can carry frontier, ledger and receipt (I4) |
| Format gate | `test_registered_owner_schemas_match_their_versioned_fingerprints` requires a version bump with a registered upcast for any owner schema change. Per-record versions do not move `SUPPORTED_FORMAT` (`classify_version`: an upcast version is `readable-legacy`, a higher version is `newer`) | No format-marker migration. `retry_ledger` goes to 2 with a v1 upcast |
| Golden round trip | `test_golden_d03_record_round_trips_byte_identically_through_its_strict_owner` re-serializes golden v1 ledgers compactly. Pydantic 2.13.5 supports `Field(exclude_if=...)` | Omitting `granted_attempts == 0` keeps v1 bytes identical (I5) |
| Acquisition after a resolved block | `claimable_outcome_ids` accepts `block.resolved`; `_validate_builder_handoff_activation` handles same-task acquisition; the Builder reservation calls `reserve(MECHANICAL)` with the `builder-claim` key | A grant needs no new acquisition path; only the thresholds change |
| Readiness after grant | `_with_retry_readiness` uses `handoff_attempt_id` only for an unresolved block. Otherwise it looks the episode up by key and reports `retry-exhausted` only from `stop_code` | A cleared stop makes the outcome ready without new readiness reasons |
| Re-exhaustion | `_builder_invocation_settled_binding` computes `exhausted` from `total_attempts`; the new block ID embeds the new settlement ID | A second failure produces a distinct block and a new grant target |

## 3. Phases

### 3.1 N11-A — Grant one more Builder attempt

- **Prerequisites:** N11-P plan gate closed.
- **Editable paths:**
  - `serve/delivery/src/owlbear_delivery/`: `recovery.py`, `runtime_receipts.py`,
    `runtime_support.py`, `runtime_settlement.py`, `delivery_runtime.py`, `runtime_models.py`,
    `delivery_application_loader.py`, `application_models.py`, `portfolio_application.py`,
    `work_items.py`, `application_readiness.py`, `state_formats.py`
  - `serve/delivery/tests/`, including `fixtures/state_formats.json`, `fixtures/module_surface.json`
    and golden `fixtures/state_formats/golden/**`
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py` and its tests
  - `serve/tools/src/owlbear_tools/delivery_diagnostics.py` and its tests
  - `serve/cockpit/src/owlbear_cockpit/routes/target_work.py` and its models
  - `serve/cockpit/web/src/**` (API mirror, presentation, detail action, tests)
  - `tests/test_cockpit_boundary.py`, `tests/test_delivery_worktree_authority.py`
  - `share/prompts/inspect-change.prompt.md` (guidance line only), this plan and the execution plan
- **Required companions:** the D03 mandatory companions for the new action, and the mutability
  policy and authority test for the new operation.
- **Positive scenarios:**
  - **P1** — ledger: an exhausted MECHANICAL episode can be granted once. Counts and history are
    unchanged, `stop_code` is cleared, the next `reserve` is allowed, and the following failure
    re-exhausts.
  - **P2** — a v1 ledger reads unchanged. A grant writes v2, a no-grant write stays v1, and `reset`
    clears `granted_attempts`.
  - **P3** — runtime: a grant on the exact handoff resolves the block, writes the receipt and ledger
    in one transaction, and replays idempotently.
  - **P4** — after a grant, acquisition re-claims the same task, and a failed granted attempt
    settles with a new `builder-attempt-limit-<new settlement>` block.
  - **P5** — the loader bootstraps the granted frontier before and after the new claim.
  - **P6** — the application, through the Cockpit HTTP route, grants with the digest and replays
    after the digest moved.
  - **P7** — Work Item: the exact block offers `grant-attempt`, not `clear-block`, and readiness is
    ready after the grant.
  - **P8** — Cockpit vitest: the button renders and posts.
- **Negative scenarios:**
  - **N1** — the grant is refused for: a non-exhausted episode, a wrong block ID, a request-bearing
    block, no handoff, an active claim, a stale digest without a receipt, and a resolved block
    without a receipt.
  - **N2** — the application refuses `grant-attempt` without `allow_user_only`, and MCP `answer`
    refuses it at validation.
  - **N3** — a v1 ledger containing a grant is refused by the validator.
  - **N4** — the format gate classifies a v2 ledger as `newer` under a registry where `retry_ledger`
    is current 1 (older controller).
  - **N5** — the loader refuses a grant receipt that differs from the settlement or the block.
  - **N6** — a crash injected after the transaction is prepared and before commit leaves either the
    old state or the full grant after `recover_all`.
- **Inner loop:**
  `uv run pytest serve/delivery/tests/test_retry_ledger*.py serve/delivery/tests/test_state_formats.py -q`
  plus the new runtime and loader tests.
- **Closeout:**
  - `uv run test --changed`
  - scoped `uv run ruff check` and `uv run ruff format --check`
  - in `serve/cockpit/web`: `npm test`, `npm run build`, `npm run test:e2e:work`, and Biome on the
    changed files
  - the full `uv run test` once (package closeout)
- **LC:** full form applies, because the `retry_ledger` version and the new receipt kind change the
  persisted format. Steps:
  1. Load an isolated live copy (recipe from N00-A).
  2. Prove that every Change is available.
  3. Grant on the copy's exhausted Builder block if present, and reload.
  4. Confirm that the previous release refuses the granted copy with `state-newer-than-controller`.
  5. Confirm that live hashes are unchanged.
- **Size and risk:** medium size, high risk (frontier writer, persisted format, loader bootstrap).

## 4. Progress

| Phase | PR | Head | Proof | Challenge | Status |
| --- | --- | --- | --- | --- | --- |
| N11-P | — | — | — | plan gate pending | drafted |
| N11-A | — | — | — | — | not started |

## 5. Verification gaps

| Gap | Claim | Reason unproven | Evidence | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | The live blocked Change continues after a grant | Live state is read-only for programme work | LC grant on the copy | User, after `/upgrade-delivery` | Nothing (post-merge activation) |
