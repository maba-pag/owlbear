# Delivery N12 — Recoverable Builder Returns to Planning

> **Package:** N12 of the [execution plan](delivery-redesign-execution-plan.md#n12--recoverable-builder-returns-to-planning),
> added after programme completion (2026-10-08).
> **Planned on:** `redesign/n11-retry-grant-attempt` at `040a1fda9` (N11-A implemented, not yet merged).
> N12 builds on N11's attempt grant, retry-ledger version 2 and grant receipt, so its branch
> `redesign/n12-planning-return-recovery` is stacked on that head and is rebased onto `origin/dev`
> after N11 merges. Live Delivery is pinned to `92073c0ce` (`.owlbear/controller/pin.json`); live
> state was read only through Delivery's read tools.
> **Deviation (user-directed, 2026-10-08):** plan, plan gate, implementation and an implementation
> gate after every phase in one session; N12-P and the N12 phases share one branch and one PR.
> Reviews work in the execution plan's [operating context](delivery-redesign-execution-plan.md#19-operating-context).
> **Status:** N12-P plan gate closed 2026-10-08. A fresh Sol gate ran round 1 on `eb9478eb3`. Verdict:
> `revision-required`, four findings, all accepted fix-now and applied: F1 successive handoff
> settlements derive from their receipt-authenticated local predecessor (I8); F2 the grant receipt
> invariant and the Planner pause/answer baseline accept the legacy grant (I6); F3 Cockpit offers
> **Clear block** only when the card's action is `clear-block`; F4 revision activation carries the
> released Planning return's preserved commit. They refine the specification without changing its
> route; each phase's implementation gate covers them.

## 1. Contract

### 1.1 Result

Today a Builder that correctly hands its task back to Planning (`return`, target `planning`) is
charged as a failed attempt in the same three-attempt budget as crashes and lost chats. When that
charge exhausts the budget, settlement parks the outcome in Planning behind the requestless block
`builder-planning-route-<settlement_id>` and keeps the Builder handoff. Every exit is then refused:

- `revise_design_session` refuses `custody-retained` for a retained Planning-route handoff (D10);
- `unblock` refuses, pinned by `test_planner_return_exhaustion_block_stays_refused_for_unblock`;
- `administrative_move` refuses to orphan the handoff;
- even if the block were cleared, the next Builder reservation for the same task lineage lands in
  the same exhausted episode.

Only **Abandon** remains, which discards the reviewed candidate and the user's answered requests.
The live Change `macos-managed-browser-authentication` is in exactly this state (OUT-001,
TASK-004; two `worker-host-lost` failures and one charged `worker-returned`).

After N12:

1. A Builder return to Planning closes its reservation like a pause: it is recorded with failure
   code `worker-returned`, refunded, and never exhausts the Builder budget.
2. Returns are bounded separately: the third return of the same original Builder task under the
   same contract settles behind a requestless **return-limit** block. Its route is a Design
   revision. Revision first releases the retained handoff while preserving the Builder head under
   refs and keeping completed tasks, results and answered requests; the user then approves and
   admits the revision.
3. An already settled exhausted Planning-route block (the live case) gets N11's user-only
   **Grant one more attempt**: the Planner re-plans, and the Builder gets exactly one more attempt.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | A Builder return to Planning is not charged against the Builder's mechanical budget; crashes, lost hosts and retries still are | User decision 2026-10-08 (plan route, RC1) |
| R2 | Returns of the same original Builder task under the same contract are bounded at 3; the bound's exit is a Design revision that preserves the Builder head and keeps completed tasks, results and answered requests | User decision 2026-10-08 (option A) |
| R3 | No reachable state from a Builder return to Planning leaves Abandon as the only exit | Incident 2026-10-08; N10 route table (`retry-exhausted` → revise or Abandon) |
| R4 | The live Change's settled exhausted Planning-route block can continue after `/upgrade-delivery` with one user action and no record rewriting | User intent (minimal interaction); Sol pre-plan finding F7 (receipt-consistent recovery) |
| R5 | Crash-safe, replayable, fenced and loader-recognized like N04-B and N11 | Execution plan §1.9 |
| R6 | User-only actions stay user-only; agent tools cannot grant | Execution plan §1.9 |
| R7 | Planner guidance binds person-only evidence semantically, never by request identity | Incident trigger (RC4) |

### 1.3 Invariants

- **I1 History kept.** No phase rewrites an attempt, outcome, owner result, settlement receipt or
  grant receipt. Refunds and counts derive from new records only.
- **I2 Return accounting.** A Builder `ReturnDelivery` settlement to Planning writes its owner
  result with `paused=True`, `accepted=False`, `accepted_progress=False` and
  `failure_code="worker-returned"`. Reconciliation records a `paused` outcome carrying that code
  and decrements `total_attempts` (and `repair_attempts` for a repair) exactly as a pause does.
  `exhausted` is never computed for such a settlement. Returns to Design are unchanged (their
  outcome leaves Implementation; the Design route already has its N04-B exit).
- **I3 Return bound.** At settlement, `returns = 1 + |{attempts in the episode's current budget whose
  outcome carries failure code worker-returned}|`, where the current budget starts after the last
  accepted attempt (the window `attempt_history` uses, but never truncated to its display length)
  and a `failed` legacy outcome with that code also counts. The episode identity already fixes contract digest, outcome, procedure and
  task lineage, and Planning promotion with a retained handoff keeps the original task ID
  (`_validate_planner_return_plan`). When `returns >= 3` the settled binding carries block
  `builder-return-limit-<settlement_id>`; otherwise no block.
- **I4 Frozen until released.** A return-limit block is cleared only by the revision release. `unblock`,
  `answer` and the grant refuse it. The loader admits it only unchanged (the existing exhausted-row
  rule).
- **I5 Preserving release.** Revision on a paused Change whose single retained handoff is
  `same-outcome-planner` with an unresolved return-limit block runs the existing N04-B capture and
  reset (`ChangeWorkspaceManager.release_design_return`, route-agnostic) and then clears the
  binding's `builder_handoff_context` and block in the same transaction as the coordination
  release. It keeps `stage`, `tasks`, `results`, `requests` and `return_context`. Revision
  activation carries that `return_context.preserved_commit` into a replanned Planning outcome as it
  already does for a Design-stage predecessor (`_replanned_binding`, plan-gate F4); N04 D8/D13 still
  decide which completed tasks and answered requests survive the revision.
- **I6 Legacy grant.** N11's grant also accepts the exact legacy shape: stage Planning, route
  `same-outcome-planner`, unresolved requestless block `builder-planning-route-<settlement_id>`, the
  settlement receipt's `ReturnDelivery` result equal to the binding, and the episode MECHANICAL and
  EXHAUSTED with the return attempt as its latest settled failure. It writes the same receipt kind
  and resolution note; the binding keeps its `return_context`. The receipt's model invariant
  accepts exactly this second shape, and `_planner_handoff_pause_return_context` accepts the
  receipt-backed granted row as the Planner pause/answer baseline (plan-gate F2).
- **I7 One budget unit.** After a legacy grant the Planner runs under its own episode; the next
  Builder reservation for the original task matches the granted episode, and the grant funds exactly
  one more charged attempt (`mechanical_repairs + granted_attempts`). Refunded returns and pauses may
  still permit further invocations.
- **I8 Successive handoffs** (plan-gate F1). While a handoff is retained the frontier is not
  published, so a later Builder settlement of the same outcome (retry, pause or return after a
  Planner-promoted correction) starts from a local binding the remote snapshot does not hold. The
  loader derives each settlement's source binding from the remote binding or, failing that, from
  the immediately preceding settlement's receipt-authenticated plan promotion, and validates that
  predecessor's chain the same way. Today such a restart fails bootstrap; N12 makes it the normal
  path to the return limit.

### 1.4 Interfaces and error cases

- **Ledger** (`recovery.py`):
  - `record_pause(attempt_id, *, now, failure_code: str | None = None)`; the outcome stores the
    code. Replay by outcome identity is unchanged.
  - `reconcile_owner_results` passes `result.failure_code` to `record_pause` only when it is
    `worker-returned`, so ordinary pause outcomes keep their bytes.
  - New `RetryLedger.returned_attempts(episode) -> int` counts the current-budget attempts whose
    outcome record (`paused` or `failed`) carries `worker-returned`.
  - No model, schema or registry change.
- **Settlement** (`runtime_settlement.py`, `delivery_runtime.py`):
  - `_builder_invocation_settled_binding` treats a Planning return as refunded (I2) and computes the
    return bound (I3).
  - `_builder_return_settled_binding(..., exhausted, return_limited)` builds the return-limit block:
    reason "The Builder returned this task to Planning three times under the current Design.",
    unblock condition "Revise the Design; the revision preserves the retained Builder work first.",
    expected evidence "An approved Design revision for this outcome.", the return locators.
  - New `builder_return_limit_block_id(context)` and `builder_planning_route_block_id(context)` in
    `runtime_receipts.py` beside `builder_attempt_limit_block_id`.
- **Release** (`delivery_runtime.py`, `portfolio_application.py`):
  - `DeliveryRuntime.release_design_return()` also accepts the I5 shape and applies the I5 binding
    update. Its name stays (it releases a handoff into a portable revision-ready shape).
  - `_require_revision_allowed(..., allow_design_return=True)` accepts that shape as releasable.
    Every other retained handoff still refuses `custody-retained`.
- **Grant** (`delivery_runtime.grant_builder_attempt`): accepts the I6 shape in addition to N11's
  same-task shape. `DeliveryAnswerKind.GRANT_ATTEMPT`, the MCP refusal and the Cockpit route are
  unchanged.
- **Loader** (`delivery_application_loader.py`):
  - `_builder_handoff_settled_binding` admits the return-limit variant as a third expected result
    of a Planning return.
  - `_planner_handoff_pause_history` admits, for an exhausted Planning-route settlement, the granted
    row derived from the exact grant receipt (as `_builder_attempt_grant_successor` does for
    same-task), and continues the ordinary Planner history (claim, candidate, pauses, answers,
    promotion) from it.
  - `_planner_handoff_lifecycle_rank` ranks the granted row after the exhausted row, so lifecycle
    receipts anchored before the grant (the live Change's Pause and Resume) stay valid.
  - `_validate_local_builder_handoff_workspace` recognizes a captured return-limit release
    (`_design_return_captured`) for the planner route, as it does for the Design route.
  - `_builder_handoff_settled_binding` derives its source binding per I8.
- **Admission** (`delivery_admission.py` `_replanned_binding`): carries the preserved commit of a
  released Planning return (I5).
- **Cockpit** (`serve/cockpit/web/src/components/WorkItemDetail.tsx`): the requestless clearance form
  renders only when the card action is `clear-block`, so neither the legacy grant nor the
  return-limit card offers a control that is certain to be refused; component tests for both.
- **Readiness and work items** (`work_items.py`, `application_readiness.py`):
  - A shared predicate `builder_attempt_grant_block(binding)` (same-task attempt limit or legacy
    Planning-route exhaustion) replaces the three copies of N11's grant-eligibility test.
  - A return-limit block gives the card action `RESUME_DESIGN` ("Revise Design", `/design <id>`) and
    readiness `design-attention`, whose existing prompt already describes Pause, `/design` and the
    preserving release. No new reason, action kind or frontend mirror.
- **Skill** (`share/skills/w-frontier-planning/SKILL.md`): one rule: tasks never name a request
  identity; person-only evidence is bound by acceptance ID, version and procedure, which the
  Builder matches against the answered request's `applies_to`.

### 1.5 Existing owners to reuse

`record_pause` and owner-result reconciliation (I2); `attempt_history`'s budget window (I3); N04-B
`release_design_return` capture/reset/coordination release and its startup recognition (I5);
N11 `grant_builder_attempt`, `prepare_attempt_grant`, grant receipt and Cockpit route (I6); the
loader's exhausted-row and requestless-clearance derivations; `design-attention` readiness and
`RESUME_DESIGN` (Cockpit already renders both).

### 1.6 Exclusions

- The claim-held `transition_delivery` return path (`DeliveryRuntime._return`): Builders never use it
  (`w-packet-building`: no raw `transition_delivery` fallback). Its accounting is unchanged.
- Planner returns, Design returns, Finalizer and engine episodes.
- Rewriting or migrating persisted records; the live Change recovers through I6.
- Changing the default budget of three Builder attempts.
- Any live state change. Activation is the user's `/upgrade-delivery` after merge, then one
  **Grant one more attempt** in Cockpit for the live Change.

### 1.7 User decisions

| ID | Decision | Outcome |
| --- | --- | --- |
| U1 | Fix route for the incident | Fix Delivery first (2026-10-08) |
| U2 | Return bound and its exit | Option A: 3 returns per original Builder task under the same contract; at the limit `/design` revision preserves the Builder head and keeps completed work (2026-10-08) |
| U3 | Plan, gates and implementation in one session, challenger after every step, push at the end | Directed by the user 2026-10-08 |

**Lead decision L1 (2026-10-08, plan gate to confirm):** the earlier proposal's live recovery by a
registered record migration is replaced by I6. A migration would have to rewrite owner results,
settlement-derived bindings and the loader's exhausted-row evidence consistently (Sol pre-plan
finding F7); N11's grant already provides a receipt-backed, loader-recognized, user-only way to fund
one more attempt, and the legacy shape differs only in route and stage. Cost: one user click.

**Prior decisions amended (listed for the user):**

- N10 route table and `test_planner_return_exhaustion_block_stays_refused_for_unblock`: the
  exhausted Planning-route block is no longer read-only; its exit is the user grant (I6). `unblock`
  keeps refusing it, so the test is narrowed, not inverted.
- N04 D10 stands: revision never carries a handoff into a new version; the return-limit handoff is
  released first (I5).
- N04 D14 stands for Design returns; the I5 release keeps completed results because a Planning
  return does not declare the Design wrong.

## 2. Feasibility probes

| Probe | Result | Premise settled |
| --- | --- | --- |
| Owner-result validator | `RetryOwnerResult` with `paused=True` accepts any `failure_code` and requires `accepted=False`, `accepted_progress=False` | I2 needs no model change |
| Pause refund | `record_pause` decrements `total_attempts`/`repair_attempts` and keeps other stops | I2 refund semantics exist |
| Episode matching | `_matching_episode` for worker keys ignores `exact_head`/`original_candidate`; it needs `total_attempts > 0`, otherwise exact identity, which is stable for a re-planned original task (same reviewed head, `original_candidate` = outcome ID) | I3 and I7 count and fund the right episode |
| Planning promotion | `_validate_planner_return_plan` requires the original task ID, commitments and surfaces with a retained handoff | Task lineage is stable across re-plans (I3) |
| Release mechanics | `ChangeWorkspaceManager.release_design_return` and `_prepare_design_return_release` validate the coordination handoff only, not its route | I5 reuses capture, reset and coordination release |
| Loader shape | `_builder_handoff_settled_binding` returns the receipt result for a Planning return; `_exhausted_planner_handoff_row` admits only the unchanged block; the requestless-clearance derivation already reproduces `settled.copy(block=cleared)` | I4 holds unchanged; I6 needs one granted-row branch and a rank |
| Live episode | Builder episode for TASK-004: two `worker-host-lost`, one refunded pause, one `failed` `worker-returned` (latest attempt); binding and episode legacy counters 0 | `prepare_attempt_grant` accepts it (latest settled failure, EXHAUSTED) |

## 3. Phases

All phases edit `serve/delivery/src/owlbear_delivery/` and `serve/delivery/tests/` unless stated.
Each phase ends with its inner loop, a commit and a fresh Sol implementation challenge on the exact
head.

### 3.1 N12-A — Return accounting and bound

- **Editable:** `recovery.py`, `runtime_settlement.py`, `delivery_runtime.py`, `runtime_receipts.py`,
  `delivery_application_loader.py` (third expected Planning-return variant, I8), tests.
- **Positive:** P-A1 a Builder return after two failures settles without a block, refunds, and the
  next Builder reservation for the re-planned task is allowed; P-A2 owner-result reconciliation
  twice and a restart keep one `paused` outcome with `worker-returned` and the same counts, for an
  original and a repair attempt; P-A3 the third return of the same task under the same contract
  settles behind `builder-return-limit-<settlement_id>`, also with an ordinary pause and a legacy
  `failed` return in the window; P-A4 accepted progress resets the return count; P-A5 the loader
  bootstraps an unpublished return-limit handoff; P-A6 (I8) return → Planner corrects an allowed
  task field → promotion → Builder reacquires → second settlement → restart through the default
  loader.
- **Negative:** N-A1 `unblock` refuses the return-limit block; N-A2 a return to Design keeps its
  current accounting; N-A3 the loader refuses a return-limit block that differs from the receipt.
- **Size / risk:** small–medium / medium (settlement accounting, loader variant).

### 3.2 N12-B — Preserving release at the return limit

- **Editable:** `delivery_runtime.py`, `portfolio_application.py`, `delivery_application_loader.py`,
  `delivery_admission.py`, `work_items.py`, `application_readiness.py`,
  `serve/cockpit/web/src/components/WorkItemDetail.tsx` and its test, tests.
- **Positive:** P-B1 the return-limit card shows `RESUME_DESIGN` and readiness `design-attention`;
  P-B2 Pause → `revise_design_session` releases the handoff (attempt ref = Builder head; branch and
  worktree at the reviewed head; coordination writer and handoff cleared) and keeps tasks, results,
  requests and `return_context`, then revises; P-B3 dirty Builder work is captured under the
  quarantine refs; P-B4 startup recognizes the captured-but-unreleased state and the revision
  replays; P-B5 after activation and reload the replanned outcome keeps the preserved commit,
  surviving completed results and scoped answers, and the Planner can claim it; P-B6 Cockpit shows
  "Revise Design" and no clearance form for the return-limit block.
- **Negative:** N-B1 any other retained Planning-route handoff still refuses `custody-retained`;
  N-B2 a changed worktree refuses `design-return-workspace-changed`.
- **Size / risk:** medium / high (workspace reset, startup recognition).

### 3.3 N12-C — Grant for the legacy exhausted Planning-route block

- **Editable:** `delivery_runtime.py`, `runtime_receipts.py`, `runtime_settlement.py`,
  `delivery_application_loader.py`, `work_items.py`, `application_readiness.py`, the Cockpit block
  component and its test, tests (including the narrowed pinning test).
- **Positive:** P-C1 an incident-shaped fixture (two host-lost failures, one pause, one charged
  return, exhaustion block) shows **Grant one more attempt** with `next_actor=you`; P-C2 the grant
  resolves the block, writes receipt and ledger in one transaction and replays; P-C3 readiness then
  offers the Planner; the Planner claims, publishes and promotes a corrected plan; the Builder
  reservation for the original task is allowed exactly once; P-C4 the loader bootstraps the
  granted row, the Planner claim, the candidate and the promotion, including a lifecycle receipt
  anchored before the grant; P-C5 the assembled Cockpit HTTP route grants it; P-C6 legacy grant →
  request-bearing Planner pause → answer → restart → promotion, and a requestless Planner clearance
  after the grant; P-C7 Cockpit shows only the grant control for the legacy block.
- **Negative:** N-C1 `unblock` still refuses the legacy block; N-C2 the grant refuses a return-limit
  block, a Design-route handoff and a non-exhausted episode; N-C3 MCP `answer` still refuses
  `grant-attempt`.
- **Size / risk:** medium / high (loader history chain).

### 3.4 N12-D — Guidance and records

- **Editable:** `share/skills/w-frontier-planning/SKILL.md`, this plan, the execution plan (N12
  section and status rows).
- **Proof:** agent-ecosystem tests for `share/`.

### 3.5 Commands

- **Inner loop:** `uv run pytest serve/delivery/tests/test_retry_ledger*.py
  serve/delivery/tests/test_delivery_runtime.py serve/delivery/tests/test_delivery_state.py -q -k
  "<phase scenarios>"`.
- **Closeout:** `uv run test --changed`; scoped `uv run ruff check` and `uv run ruff format --check`;
  the agent-ecosystem tests for `share/`; the full `uv run test` once.
- **Closeout (frontend):** in `serve/cockpit/web`: `npm test`, `npm run build`, `npm run
  test:e2e:work`, Biome on the changed files.
- **LC:** load form. No persisted schema changes (I1; N11 already versions the ledger). Load an
  isolated live copy, prove every Change is available, grant on the copy's
  `macos-managed-browser-authentication` block, reload, acquire the Planner, promote a corrected
  plan, reload, acquire the funded Builder for TASK-004 with its preserved head and answered
  request, and confirm live hashes are unchanged.

## 4. Progress

| Phase | PR | Head | Proof | Challenge | Status |
| --- | --- | --- | --- | --- | --- |
| N12-P | shared | `eb9478eb3` + corrections | source probes (§2) | Sol round 1 `revision-required`; F1–F4 fix-now applied; gate closed | done |
| N12-A | shared | `0055ae06d` + gate fixes | focused Delivery selection 676 passed; new return-limit and grant files | Sol implementation round 1 (A–D together) `revision-required`: F1 Cockpit label, F2 LC unrun; F1 fixed | done |
| N12-B | shared | as N12-A | release, restart boundaries, publication wait, workspace-change refusal | as N12-A | done |
| N12-C | shared | as N12-A | legacy grant through Planner pause, promotion and one funded attempt; missing-receipt refusal | as N12-A | done; LC run (G3) |
| N12-D | shared | as N12-A | skill rule | as N12-A | done |

## 5. Verification gaps

| Gap | Claim | Reason unproven | Evidence | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | The live Change continues to merge after the grant | Live state is read-only for programme work | LC grant on the copy | User, after `/upgrade-delivery` | Nothing (post-merge activation) |
| G2 | Rollback to the pinned release while a return-limit or granted Planning-route handoff is local | The previous release does not know the shapes | Granted ledgers are version 2, which the pinned pre-N11 release refuses with a typed diagnostic; a return-limit handoff without a grant fails bootstrap for that Change only | User (switch forward) | Nothing |
| G3 | The live incident records load, grant and promote under this release | Load form run 2026-10-08 on an isolated Docker copy at `512499c8f`: launch provenance and in-container isolation proven, all 10 live Changes load available, records unchanged, live hashes unchanged (820 records). The tool reports `passed: false` only because the candidate-independent inspector stops at its 256-entry budget (`ENTRY_LIMIT_EXCEEDED`, 7 of 10 Changes even per Change; `serve/tools` is untouched by N12). The mutable rehearsal on the copy shows the real incident card as **Grant one more attempt** with next actor you, but the grant is refused as `remote-state-reconciliation-required`: the retained handoff's fingerprint hashes the worktree's Git index, whose stat data cannot survive a copy. The base `040a1fda9` refuses identically in the same container, so this is a copy artifact | Load form report and rehearsal reports in the LC stage `control/` | User: the first real grant is the post-merge activation (G1) | Nothing |
| G4 | The LC load form can pass on current live state | The inspector's 256-entry budget is smaller than one live Change | Raise or page the `delivery-diagnose` entry budget | Delivery tools owner | Future LC gates |
