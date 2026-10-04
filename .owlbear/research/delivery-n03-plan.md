# Delivery N03 — Evidence Model and Finalization Assurance

> **Package:** N03 of the
> [execution plan](delivery-redesign-execution-plan.md#n03--evidence-model-and-finalization-assurance).
> **Planned on:** `origin/dev` `ef622c354` (N02-P and N01-A merged; N01-B in review; N01-C and N02-A…D not
> started; Python 3.14.8). Live state observed read-only: main checkout on `delivery-live` (D03).
> **Status:** approved: plan gate `plan-sound` in round 6 of fresh GPT-6.1 Sol challenges (2026-10-03).
> Product code is unchanged by this phase.
> The §1.7 comparison inventory was re-scanned on post-N01 `origin/dev` `58c4d928b` (P11) and its publication
> gates on `58c4d928b` + N02-A (P13); the acknowledgment base on lane-b `e6ed5bb31` (P14).
> D11 amends the execution plan, merged under the user's overnight authorization of 2026-10-03 and
> confirmed 2026-10-03 (listed to the user without objection). U1 decided 2026-10-03 by the user: (b).
> PR #360 plan gate round 1 adds the confirmation boundary (D13), the Change confirmation ledger and
> the open user decision [U2](#u2--which-clicks-and-answers-count-as-the-user-said-yes) (before N03-C
> and N05-C). Round 2 defines D13's legacy and modern elicitation routes on the SDK's request-state
> boundary (P16), binds the ledger append into request-resolution receipts for restart replay, and
> widens U2 to Cockpit merge approval and retirement. Round 3 makes every boundary answer single-use (D13
> *Single use*), restates U2's applicability and cost, and drops the expectation that N06 adds a channel
> or locator scheme (N06 D3). Round 4 replaces the frontier-as-generation rule with one shared single-use
> consent generation (`consent_generation`, D13 *Single use*, I11): decline, cancel and a failed re-check
> consume the question too. N04, N05 and N06 use the same family; N05-B therefore also needs N03-A.

## 1. Contract

### 1.1 Result

- Every new proof observation carries a typed result whose verdict is derived, never asserted: `passed`,
  `expected-negative`, `failed`, `missing` (with an owner) or `waived` (owner user, with an affirmative user
  waiver captured through the confirmation boundary (D13) and bound to the criterion version; it satisfies
  finalization, [U1](#u1--may-a-user-waive-a-required-acceptance-criterion)(b)). Command, manual-procedure and
  artifact evidence have distinct shapes.
- Every new observation records the acceptance criteria and criterion versions it covers, the exact commit,
  procedure, environment and target class, its time, machine-observed versus human-confirmed provenance, and a
  bounded non-sensitive locator.
- Acceptance criteria have stable identities (`AC-NNN`) authored in the Design package and a content version.
  Identities survive revision; versions change when the statement changes.
- `finalize_change` loads the admitted acceptance authority and fails closed unless every acceptance criterion
  is covered by proof or waived by an applicable user waiver (U1(b)), whether that record is carried from a
  task result or submitted by the Finalizer. The finalization context gives the
  Finalizer and the independent reviewer the same semantic projection and diff baseline, bound by one basis
  digest the engine re-checks; the review also binds the exact ordered set of submitted observations.
- Existing observations are never relabeled: their coverage is `unknown`. No stored receipt byte or identity
  changes.
- One evidence projection (acceptance criterion → evidence → status) is readable through `get_change`, MCP, HTTP
  and a Cockpit technical summary.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | Typed, unambiguous proof result; expected-negative tests pass only with a recorded expectation; failed or unmet required proof cannot support finalization | #219; execution plan §5 N03 |
| R2 | Minimum coverage metadata: criterion IDs and versions, exact code/procedure/environment, target class, time, confirmation provenance, bounded locator | Programme §8.4; §5 N03 |
| R3 | Stable acceptance identities with versions in semantic authority, defined so N04 can map them across a revision | §8.4; WP4 step 3; P13; §5 N03 "P must settle" |
| R4 | Finalization loads the admitted acceptance authority and fails closed on failed, unmet or uncovered evidence | #222; #219; §10.1 |
| R5 | The reviewer receives the same semantic context and exact diff boundary as the Finalizer | #222; §10.1 |
| R6 | Existing observations: unknown coverage unless attributable; never relabeled; original receipts never rewritten | §5 N03; §8.4 |
| R7 | Evidence projection through `get_change`, MCP, HTTP and a Cockpit technical summary | §5 N03 result |
| R8 | Proof submission guidance for Builder and Finalizer | §5 N03 "P must settle" |
| R9 | Repeated evidence collection needs a specific uncovered or invalidated criterion, not a new request ID (groundwork for V15) | U6; V15 |
| R10 | No requirement is dropped to pass; agents never waive acceptance | U7; programme §5.1 role table; V16 |
| R11 | Every changed persisted family registers a version owner; migrations run through the N02-B core; LC full form | Execution plan §1.3; N02 plan I2, I3, D3 |
| R12 | Trust boundary documented: digests prove content integrity, not execution authenticity | #219 scope |
| R13 | Support baseline (Python 3.14; macOS and Ubuntu); §1.4 mandatory companions for new statuses | Execution plan §1.1, §1.4 |
| R14 | Waivers and `human-confirmed` evidence count only through a user confirmation captured on a channel the agent's tool surface cannot satisfy; caller-asserted provenance confers nothing; a declined or negative answer confirms nothing; an answer counts once, and re-sending it never records another confirmation; a declined or cancelled question is consumed and never later yields a confirmation | PR #360 plan gate rounds 1, 3 and 4; U7; V16 |

### 1.3 Invariants

- **I1 Immutable history.** No stored observation, review, task result, finalization, settlement receipt or
  snapshot changes bytes or identity. Old-version instances validate unchanged under the new models (P3, P6).
- **I2 Version widening.** A family whose JSON schema changes widens its version literal (`Literal[old, new]`);
  writers emit only the new version; a validator rejects N03-only content inside an old-version instance. This
  satisfies N02 I2 (version bump for every schema change) without rewriting stored bytes (N02 I3).
- **I3 No relabel.** Schema-1 observations never acquire a verdict or covered criteria. They count as evidence
  for nothing and make otherwise uncovered criteria `unknown`, not `uncovered`.
- **I4 Derived verdict.** A command verdict is computed from exit status and expectation; it cannot contradict
  them. Manual and artifact evidence carry an explicit assessment.
- **I5 Fail closed.** `finalize_change` writes nothing unless every criterion is covered or waived (U1(b)),
  every request observation is typed and either a proof verdict or an applicable waiver (I6), the review's
  basis digest equals the engine's current basis, and the review's `observation_ids` equal the request's
  observation IDs in order.
- **I6 Applicable confirmation.** `human-confirmed` provenance and `waived` results cite a `confirmation_id`
  that the engine resolves in the Change's confirmation ledger (§1.5): a `DeliveryUserConfirmation` captured
  through the confirmation boundary (D13), in the same Change and outcome, whose scope names every criterion
  version the observation covers and its exact `procedure`, and whose recorded decision is the affirmative one
  for its use (`waive` for `waived`; the observation's assessment for `human-confirmed`). Caller-supplied
  `provenance` never creates or substitutes for one; a declined or cancelled elicitation records no
  confirmation (it only consumes its consent generation, I11); a `keep-required` answer waives nothing.
  Nothing synthesizes one (V20). A `waived` record with an applicable
  confirmation satisfies finalization for that criterion version, from a task result or the finalization
  request, and stays shown as `waived` (U1(b)); agents and reviewers never waive.
- **I7 One evaluator.** One pure function computes coverage for `finalize_change`, the finalization context
  and the projection; identical inputs give identical statuses.
- **I8 Bounded and non-sensitive.** Locators use an allowlisted `scheme:value` form, never URLs; free text is
  length-bounded; projections cap evidence per criterion. The finalization context is all-or-nothing within one
  byte budget (§1.8); obligations are never truncated.
- **I9 Gate first.** N02 I1 and I5 unchanged; N03 adds format marker 2 and the widened versions to the registry.
- **I10 Append-only confirmations.** Every frontier successor's `confirmations` extends its predecessor's
  unchanged; the facade writer refuses any other write before touching bytes. `_reset_binding`, request
  history moves and N04 revision activation leave the ledger as it is.
- **I11 Single-use consent.** Every question asked through the confirmation boundary (D13) renders one
  server-owned consent generation that exists before it is asked. The first answer the handler receives
  for it, affirmative or not, consumes it under the owning lock, atomically with every write that answer
  causes; every later answer to it returns the recorded disposition and writes nothing. Only a new call,
  which renders a new generation, can ask again.

### 1.4 Acceptance identities

Delivery already uses "claim" for worker custody (`claim_id`). This plan calls acceptance claims **acceptance
criteria** and names their fields `acceptance_id` and `acceptance_version`.

| Rule | Definition |
| --- | --- |
| Authored identity | An outcome `acceptance` item of the form `AC-NNN: <statement>` (regex `^AC-[0-9]{3}: \S`) declares `acceptance_id = AC-NNN`. The text stays one YAML string, so `DeliveryContract` v2 and its digest are unchanged (D1) |
| Version | `acceptance_version = sha256(statement as UTF-8)`, where `statement` excludes the `AC-NNN:` prefix and its space |
| Legacy identity | A contract with no prefixed item gets `acceptance_id = <outcome_id>.<NN>` (1-based position). It is valid only within that contract digest; across contracts, legacy criteria match only by version (P4) |
| Uniqueness | `AC-NNN` is unique per Change across outcomes. A contract is all-prefixed or all-legacy |
| Compiler diagnostics | `acceptance-identity-mixed`, `acceptance-identity-duplicate`, `acceptance-identity-invalid` (an item starting with `AC-<digit>` that does not match). No live package triggers any of them (P4) |
| First admission | A Change with no current admitted authority must be all-prefixed (`DeliveryAdmissionValidationError`, diagnostic `acceptance-identity-required`). Replay and revision of an admitted legacy contract stay valid |
| Survival across revision (consumed by N04) | Same `acceptance_id` and same version: the same criterion, a mechanical reuse candidate. Same ID, new version: the same criterion revised; prior evidence needs a reviewed applicability decision. New ID: a new criterion with no evidence. Removed ID: retired; never reused for another obligation. Legacy → authored: a version match is a mechanical candidate only; a reviewer confirms |
| Projection | `DeliveryAcceptanceCriterion{acceptance_id, acceptance_version, outcome_id, statement, identity_source}`; `identity_source` is `authored` or `legacy-position` |

### 1.5 Evidence record (observation schema 2)

`DeliveryObservation` / `DeliveryObservationReceipt` become schema 2. The schema-1 classes stay, renamed
`DeliveryLegacyObservation` / `DeliveryLegacyObservationReceipt`, read-only (no `create`). Nested fields are a
union discriminated by `schema_version`.

| Field | Type and bound | Meaning |
| --- | --- | --- |
| `schema_version` | `Literal[2]` | Discriminator |
| `change_id`, `task_or_finalization_id`, `step_id`, `exact_commit`, `observer_or_runner_identity`, `observed_at` | As schema 1 | Unchanged meaning |
| `observation_kind` | 1–64 chars | Free label (`pytest`, `ruff`, `manual-browser-check`) |
| `procedure` | 1–512 chars | Exact command line or procedure name; replaces `command_or_procedure` |
| `procedure_registration_digest` | sha256 or null | Registered procedure identity (`MaintainedProofProcedure.registration_digest`; N06 handler digest) |
| `result` | union on `kind` (below) | Typed result |
| `covers` | ≤ 32 unique `DeliveryAcceptanceRef{acceptance_id, acceptance_version}` | Criteria this observation is evidence for; may be empty (supporting check) |
| `environment` | `platform`: `macos`, `linux` or null; `labels`: ≤ 8, each matching `^[a-z0-9][a-z0-9.+_-]{0,63}(:[A-Za-z0-9.+_-]{1,64})?$` | Environment constraints that bound applicability |
| `target_class` | null or `^[a-z0-9][a-z0-9-]{0,63}$` | Class of external target (`sharepoint`, `confluence`), never a hostname |
| `provenance` | `machine-observed` or `human-confirmed` | Who established the result |
| `confirmation_id` | null or sha256 | Required for `human-confirmed` and for `waived`; resolved in the Change's confirmation ledger and checked by the engine (I6) |
| `locator` | null or ≤ 256 chars of `scheme:value`; scheme `path`, `ci-run`, `check-run`, `request` or `report`; no whitespace, no `://`, no `..` segment | Retained non-sensitive locator |
| `summary` | null or ≤ 240 chars | Non-authoritative note (`171 passed`) |
| `observation_id` (receipt) | sha256 | `_receipt_digest` over all other fields; `create` copies fields by attribute (P3 finding) |

| `result.kind` | Kind fields | Verdict |
| --- | --- | --- |
| `command` | `exit_status` −255…255; `expectation` `success` or `expected-failure`; `expected_exit_status` nonzero, required iff expected-failure | `passed` iff success and 0; `expected-negative` iff expected-failure and exit = expected; otherwise `failed` |
| `manual-procedure` | `assessment` `passed` or `failed` | The assessment; `human-confirmed` allowed |
| `artifact` | `assessment` `passed` or `failed`; `artifact_digest` sha256 or null; `locator` required | The assessment; `human-confirmed` allowed |
| `missing` | `owner` `agent`, `user`, `provider` or `assisted-check`; `reason` 1–240 chars | `missing` |
| `waived` | `owner: user`; `reason` 1–240 chars; `confirmation_id` required | `waived`; with an applicable confirmation (I6) it satisfies finalization coverage and stays shown as `waived` ([U1](#u1--may-a-user-waive-a-required-acceptance-criterion)(b)) |

**Proof and admissible waivers.** Proof verdicts: `passed`, `expected-negative`. A satisfying record is a
proof verdict or a `waived` record with an applicable confirmation (I6). Both complete a criterion's coverage
wherever they appear, in a task result or in the finalization request (U1(b), §1.6); proof is shown as
`covered`, a waiver as `waived`. `missing` and `failed` never satisfy.

**Confirmation scope.** `DeliveryRequest` gains optional `applies_to: DeliveryConfirmationScope{kind:
"waive" | "confirm-check", acceptance: 1–32 unique DeliveryAcceptanceRef, procedure: 1–512 chars}`
(`exclude_if` None). The requesting worker sets it on the existing request-bearing block route; a scoped
request cannot carry a `resolution` when it is created. The user answers only through the confirmation
boundary (D13): the engine resolves the request with `provenance: user-confirmed` and the new
`DeliveryRequestResolution.confirmation_id` (`exclude_if` None) and appends the confirmation to the ledger in
one transaction. A request without scope confirms nothing. The engine checks structure and the channel, not
the worker's honesty (R12).

**Confirmation ledger** (portable representation, consumed by N04 and N06). `DeliveryUserConfirmation`
(schema 1): `change_id`, `outcome_id`, `request_id`, `scope` (the request's `applies_to`), `decision`
(`waive` or `keep-required` for kind `waive`; `passed` or `failed` for `confirm-check`), `channel`
(`mcp-elicitation`; U2 may add `cockpit`; N06 adds none, N06 D3), `question_digest` (sha256 of the
canonical JSON of the exact rendered `ElicitRequestFormParams`, the rendering the SDK pins its answer to,
P16), `generation_id` (the consent generation it consumed, I11), `confirmed_at`, and `confirmation_id`
(`_receipt_digest` over the rest).
`DeliveryFrontier.confirmations` holds them for the whole Change, ≤ 256 entries (I8), `exclude_if` None,
append-only (I10). It travels in every snapshot that embeds the frontier, so the ledger is as portable as
the frontier. Two pure functions in `evidence.py` are the only readers: `resolve_confirmation(frontier,
confirmation_id)` and `confirmation_applies(confirmation, observation, outcome_id)`, which returns the I6
gap reason or None. The evaluator, `semantics`, the projection and N04 use only these.

**Requests stay unchanged.** `_advance` and `_reset_binding` keep clearing requests as today; confirmation
authority lives only in the ledger, so promotion, reset and revision cannot drop it. This replaces the
round-2 retention of resolved requests in `binding.requests`.

### 1.6 Admissibility and coverage

| Surface | Rule |
| --- | --- |
| `publish_result` / `submit_result` | Every observation schema 2; verdict in {passed, expected-negative, missing, waived} (a failing check blocks or retries, it is not a result); `covers` names current criteria of the admitted contract; confirmations resolve and apply (I6); existing exact-commit checks unchanged |
| `finalize_change` request | Zero or more observations, each schema 2 and satisfying (a proof verdict, or `waived` with an applicable confirmation, I6), at the exact head; review schema 2 with `review_mode: finalization`, `basis_digest` equal to the current basis and `observation_ids` equal to the request's IDs in order; coverage complete (every criterion `covered` or `waived`) |
| Review binding | Review schema 2 adds `observation_ids` (ordered, may be empty) inside `review_id`. Coverage assignment is a pure function (I7) of the basis inputs and those receipts, whose `covers` lie inside each `observation_id`, so the review binds it. Same review with one observation replaced, added, dropped or reordered → `review-observations-mismatch`, no write |
| Coverage evaluation | Records in order: task results in authority order (their commits are ancestry-ordered, P7), observations in result order, then the finalization request. For each current criterion, the **last** record covering it decides: proof verdict → `covered`; `waived` (admitted only with an applicable confirmation) → `waived`; `missing` → `missing`. No typed record → `unknown` if the Change has any schema-1 observation, else `uncovered`. Finalization accepts `covered` and `waived` (U1(b)); `missing`, `uncovered` and `unknown` are gaps |
| Carried evidence | A task-result observation at an ancestor commit counts for finalization (U6: no repetition without a specific uncovered or invalidated criterion). The reviewer judges its applicability to the assembled head under the shared basis (§8.4). When carried evidence covers every criterion, finalization needs no new observation; the exact-head finalization review stays required. A reviewer finding that carried evidence does not apply is the invalidation that permits a fresh exercise (R9) |
| Basis digest | `sha256` of canonical JSON `{schema: 1, contract_digest, change_head, diff_base, result_digests, acceptance: [[id, version], …]}`; `diff_base` = latest `target_sync_receipt.target_head`, else `ChangeCoordination.publication_base_head`; null → finalization refused (`finalization-basis-unavailable`) |
| Finalization receipt | Schema 3: zero or more observations, all schema 2; review schema 2 in finalization mode with matching `observation_ids`. Schema 2 keeps `min_length=1`. Coverage is recomputed from immutable inputs, not stored twice |
| Stored history | Schema-2 finalizations (legacy observations) and completed Changes stay valid and are never reopened; their projection is `finalization_rules: legacy` |

### 1.7 Persisted families, versions and migration

Every change below is registered in the N02 registry (`state_formats.FAMILIES`) by N03-A. "Widen" means
`Literal[old, new]`, old instances validated unchanged and constrained to old content (I2).

| Family (N02 ID) | Model | Before → after | Old records | Live |
| --- | --- | --- | --- | --- |
| `frontier` (M) | `DeliveryFrontier` and nested `OutcomeAuthorityBinding`, `DeliveryTaskResult`, observations, `DeliveryReviewReceipt`, `DeliveryFinalizationReceipt`, `DeliveryRequest` | 18 → 19 (widen 18, 19) under the stored-byte contract below. No rewrite migration (D3) | 18 = `readable-legacy`; reads never write; file bytes and digests unchanged until the next mutation | 3 × v18 |
| nested `DeliveryObservationReceipt` | schema 1 / 2 union | 1 → 1 ∪ 2 | Unchanged | 12 × v1 (P1) |
| nested `DeliveryReviewReceipt` | `DeliveryReview` | 1 → widen 1, 2 (`review_mode`, `basis_digest`, `observation_ids`, each with `exclude_if` None) | Bytes and `review_id` identical (P6) | 5 in results |
| nested `DeliveryFinalizationReceipt` | `DeliveryFinalization` | 2 → widen 2, 3 | Unchanged | none local |
| nested `DeliveryRequest` | `applies_to` (`exclude_if` None); `DeliveryRequestResolution.confirmation_id` (`exclude_if` None) | Covered by the frontier, snapshot and receipt widening | Unchanged | — |
| nested `DeliveryUserConfirmation` (new) | `DeliveryFrontier.confirmations` (`exclude_if` None) | New, schema 1; only in frontier 19, snapshot 3 and receipts 2 through their embedded frontiers | None exist; I2 rejects a ledger in an old-version instance | — |
| `consent_generation` (new, local; not in snapshots) | `DeliveryConsentGeneration` (new `consent_generation.py`) at `runtime/changes/<change>/consent-generations/<sequence>.json` (per-Change sequence, zero-padded, exclusive create) | New, schema 1; mutable by one CAS transition `open` → `answered` (D13 *Single use*, I11); identity `generation_id` | None exist | — |
| `planning_*`, `builder_*` receipts embedding bindings, frontiers or requests | `_DeliveryPlanningRetrySettlementReceipt`, `_DeliveryBuilderInvocationSettlementReceipt`, `_DeliveryBuilderPlanPromotionReceipt`, `_DeliveryBuilderHandoffChangeIntentReceipt`, `_DeliveryPlanningPauseReplay` (P8), `_DeliveryBuilderRequestResolutionReceipt` (P10; schema 2 also binds the ledger append, below) | 1 → widen 1, 2 | Unchanged; embedded frontiers keep 18 | none |
| `snapshot` (remote R) | `DeliveryStateSnapshot` | 2 → widen 2, 3; v1 keeps its read-upcast, now to 3 | v2 parse natively (no forced republish); v1 upcast as today | 2 × v2, 1 × v1 (N02 P3) |
| `result_receipt` (R, unversioned) | `DeliveryResultCandidate` | Content may now hold schema-2 observations | Unchanged | none |
| any other family the N02-A fingerprint test flags | — | Widen if versioned; covered by the marker if unversioned | Unchanged | — |
| `format` marker | `runtime/format.json` | 1 → 2 by registered migration `format-1-to-2` (marker only, after classifying every record as registered). A copy below format 1 runs N02-B's 0 → 1 first | — | absent today (format 0); format 1 after the N02-D H step |
| `contract`, `package`, `admission`, finalization reports, proof attempts, finalizer settlements, completions | — | Unchanged (identity lives in authored text, D1; acceptance failures reuse existing report codes, D7) | — | — |

Downgrade (N02 D3): an N02 release refuses format 2, frontier 19, snapshot 3 and the widened receipts before
parsing. Supported rollback after migration is not offered: no N02 release accepts format 2.

**Stored-byte contract (frontier 18).** The verified stored record and the writable model are separate (P10).
`parse_delivery_frontier` returns the writable v19 model, the stored bytes and the stored version: for 19 the
canonical bytes (N02-B keeps the current-version rewrite), for 18 the verified file bytes, never re-serialized.
N03-A registers `normalize_frontier` for the frontier family in `state_formats`: 18 → 19 sets `schema_version`
only (I2 keeps 18 free of 19 content). New fields are `exclude_if` None, so an 18 model dumps to its stored bytes.

**Comparison inventory.** Every frontier comparison, hash and identity site on `58c4d928b` (P11), by treatment:

- **S stored-version:** stored bytes, or the model serialized at its own `schema_version`; an 18 stays 18.
- **N normalized:** `normalize_frontier` on both sides before equality, limited to the registered version
  transformation; receipt IDs, byte digests and every non-version field compare unchanged.
- **W writable:** the v19 writable model from `parse_delivery_frontier`; version-uniform by construction.
- **U unchanged:** byte digests of stored bytes, or field- and binding-level equality (`OutcomeAuthorityBinding`
  has no `schema_version`).
- **P publication:** a portable write records pending publication on the S base when its written bytes differ
  from its stored bytes for a reason the remote snapshot does not hold: a model change or the 18 → 19
  representation change. Writable-model equality alone never suppresses it (P13).
- **L ledger replay:** an expected frontier rebuilt from `snapshot.frontier` takes `confirmations` = the
  snapshot ledger unchanged (I10) followed by the confirmations bound in the schema-2 request-resolution
  receipts of exactly the answers that this expected frontier includes, in answer order. Nothing else adds
  an entry; the local ledger must equal it byte for byte.

| Site | Owner module | Compares or derives | Treatment |
| --- | --- | --- | --- |
| `parse_delivery_frontier` | `runtime_support.py` today; wherever N02-A places it | Writable model, stored bytes, stored version | S bytes, W model |
| `DeliveryRuntime._read`, `frontier_bytes()` | `delivery_runtime.py` facade | Returns stored bytes; never writes an 18 (N02-B rule) | S |
| `_replace`, `_replace_content` | `delivery_runtime.py` facade | `previous` = stored bytes (expected prior content); writes `_model_content(v19)`: the first mutation is one 18 → 19 transaction | S prior, W write |
| Byte CAS and version digests over `frontier_bytes()` or file bytes | facade expected-frontier checks; `runtime_reads` pending match and `snapshot_version`; `application_acquisition`; `application_lifecycle`; `workspace_coordination`; `workspace_preservation`; `application_publication` replay; `portfolio_application` answers and intents; `application_recovery` repairs and receipts; `delivery_admission` expected frontier; loader `_read_local_pending_publication`; `DeliveryPortfolioSnapshot.capture` (`work_items`) | sha256 of stored bytes | U |
| `publication_base_digest` | `runtime_reads.py` | Portable projection digest; today re-serializes the writable model | S (project at stored version) |
| `snapshot_id`, `_snapshot_digest`, `_publication_digest` | `delivery_state.py` | Snapshot and publication identity | S |
| `_portable_frontier`, `_same_snapshot_inputs` | `delivery_state.py` | Publish-skip equality, snapshot frontier vs local | S (unchanged 18 equals its snapshot; the first 19 write republishes once) |
| `parse_delivery_state_snapshot` | `delivery_state.py` | Embedded frontier | S: v2/v3 embeds validate natively; v1 upcast keeps the 17 → 18 step, never the writable model |
| `_validate_local_snapshot` expected bytes; `_restore_runtime_snapshot` | `delivery_application_loader.py` | `_canonical_model(snapshot.frontier)` vs `frontier.json`; restore write | S |
| `_read_local_snapshot_frontier` | `delivery_application_loader.py` | Local model for successor checks | S model, fed to N rows |
| `_reconcile_pending_state_publication`, `_pending_publication_remote_head` | `application_publication.py` | Remote snapshot frontier digest vs pending base or current digest | S |
| `_is_unpublished_claim_successor`, `_is_unpublished_checkpoint_successor`, `_is_unpublished_acceptance_attention_successor`, `_is_unpublished_target_sync_attention_successor` | `delivery_application_loader.py` | Whole-frontier equality, snapshot vs local | N |
| `_validate_local_builder_handoff_frontier`, `_validate_local_builder_return_frontier` | `delivery_application_loader.py` | Expected (from `snapshot.frontier`) vs local frontier | N |
| `_builder_handoff_lifecycle_successor_frontier` | `delivery_application_loader.py` | Baseline (from `snapshot.frontier`) vs receipt `before_frontier` and `after_frontier`; chain continuity | N |
| `_planner_handoff_lifecycle_successor_frontier` | `delivery_application_loader.py` | Baseline (from `snapshot.frontier`) vs receipt `before_frontier` and `after_frontier`; chain continuity | N |
| `_builder_handoff_lifecycle_baselines`, `_local_builder_return_successor_frontier`, `_builder_handoff_frontier_with_lifecycle_fields` | `delivery_application_loader.py` | Both sides from `snapshot.frontier`; lifecycle-field copy | U (outputs feed N rows) |
| Binding comparisons: `_planner_handoff_lifecycle_rank`, `_planner_handoff_pause_history`, `_planner_handoff_receipt_pause`, `_builder_handoff_settled_binding`, `_builder_request_resolution_successor`, `_validate_local_builder_plan_promotion`, `_promoted_builder_return_successor`, `_is_repairable_frontier_successor` (`application_recovery`), `_DeliveryBuilderPlanPromotionReceipt._validate_successor` (`runtime_receipts`) | loader, `application_recovery.py`, `runtime_receipts.py` | `OutcomeAuthorityBinding` equality | U (requests unchanged; the ledger is frontier-level and replays by the L row) |
| Ledger suffix of retained-handoff replays: `_validate_local_builder_handoff_frontier` (expected frontier from `snapshot.frontier`, loader `:1037-1044`), `_builder_request_resolution_successor` (`:1831-1889`; returns the binding and its receipt's confirmation), `_builder_handoff_lifecycle_baselines` (`:1755-1778`; the resolved baseline carries the entry, the settlement baseline does not), `_local_builder_return_successor_frontier` (`:1169-1198`), `_planner_handoff_answered_request` (`:1434-1461`; a scoped answer requires its schema-2 receipt) and the baselines of `_planner_handoff_lifecycle_successor_frontier` (`:1730-1736`; entries of answers up to the row's rank) | loader | `confirmations` of every expected frontier built from `snapshot.frontier` | L |
| `_DeliveryBuilderHandoffChangeIntentReceipt` digests and `_changed_frontier_fields` | `runtime_receipts.py` | Schema 1: unchanged. Schema 2: below | S digests, N delta |
| `_require_recorded_builder_handoff_change_intent`, `_builder_handoff_change_intent_chain` | `runtime_settlement.py` | Lifecycle fields of the latest receipt vs current frontier | U |
| `_is_delivery_replay` | `delivery_admission.py` | `parse_delivery_frontier` model vs derived frontier | W |
| `repair_missing_request_provenance`, `repair_stranded_frontier` | `runtime_support.py`, `application_recovery.py` | History bytes by digest; repaired bytes written and replay-compared | U history; W: write `_model_content(writable)`, not parse's stored bytes |
| Read-only parses: `application_readiness`, `application_acquisition`, `application_recovery` readers, `completed_history`, `delivery_contract_discovery`, `work_items`, `portfolio_application` admission result | as named | No comparison or identity | U |
| `DeliveryRuntime.complete_recovery` (`:1723-1766`) | `delivery_runtime.py` facade; caller `_complete_recovery` (`application_recovery.py:1949-1990`) publishes nothing after it | Gate `replacement != frontier and portable` (`:1764`); `clean-finalizer` and `ready-readback` keep the model, so an 18 → 19 write gets no marker | P: `portable and (replacement != frontier or _model_content(replacement) != previous)`; transaction, custody release, exclusion checks and the `intent.frontier_digest` CAS on stored bytes unchanged |
| `acknowledge_checkpoint_publication` (`:754-783`) | facade; callers `application_publication.py:1340, 1392`, `application_recovery.py:1160` | `record_pending_publication=False` (`:782`): the drain equals the already published `_portable_frontier` (`delivery_state.py:790-796`); `_publish_delivery_state` has already acknowledged the preceding marker (`portfolio_application.py:1725`) | P: stored 19 keeps `False` (semantics unchanged). Stored 18 and portable records, because a full drain is no `_is_unpublished_checkpoint_successor` (loader `:1965-1979`), with an acknowledgment-specific `base_frontier_digest` (`_replace_content` `:2366`): the already published projection, i.e. the stored pre-acknowledgment model with `publication_base_digest`'s claim-field removal and `_portable_frontier`'s drain (a `pending_checkpoint` whose head equals `published_head` removed), serialized at 18. The default base (`:2384`) keeps that checkpoint, so its marker matches neither the remote nor the current digest and replay refuses (`application_publication.py:1633`). Trigger retention and `publication_base_digest` stay unchanged everywhere else |
| `_read` canonical rewrite (`:2328-2329`) | facade | `record_pending_publication=False` | U: fires only for a non-canonical 19 with an unchanged model; never writes an 18 (S) |
| `_replace` (`:2351-2357`); Builder invocation settlement (`:2151-2157`) | facade | `record_pending_publication=portable`; no model-equality gate | U: every portable write records; a non-portable 18 → 19 write is recognized by the N successor rows |
| `record_checkpoint_branch_publication` (`:664-674`), `complete_change` (`:1103-1106`), `finalize_change` (`:1215`), `prepare_completed_outcome_repair` (`:1389-1393`), `repair_stranded_frontier` (`application_recovery.py:908-935`) | as named | Record pending publication unconditionally | U |
| Byte guards `ReplacementTransactionParticipant(frontier, frontier)` | `workspace_coordination.py:136, 343-345, 552-555` | Write the stored bytes back unchanged | U: an 18 stays 18; no marker |

N03-A re-runs the P11 scan and the P13 publication-gate scan at phase start; a frontier equality, hash, identity
or publication-gate site outside this table stops for a plan revision.

- **Upgraded handoff intent receipts.** `_DeliveryBuilderHandoffChangeIntentReceipt` schema 2 binds
  `before_frontier` as the stored model at its stored version (`runtime_settlement` passes it from `_read`) and
  `before_frontier_digest` as the sha256 of the committed prior bytes; `after_frontier` is 19. Its field delta is
  computed on `normalize_frontier(before_frontier)`, so it permits only the registered 18 → 19 representation
  change plus the action's authorized fields; any other change still fails `_validate_action`. Schema-1 receipts
  keep 18 → 18 with today's validation and identity. Both loader replays, same-task Builder
  (`_builder_handoff_lifecycle_successor_frontier`) and same-outcome Planner
  (`_planner_handoff_lifecycle_successor_frontier`), compare these receipts through the N rows above.
- **Request-resolution receipts bind the ledger append.** A scoped answer during a retained handoff writes no
  pending publication, and the loader rebuilds that frontier from `snapshot.frontier` by substituting
  bindings, so the ledger entry needs receipt authority. `_DeliveryBuilderRequestResolutionReceipt` schema 2
  adds `confirmation: DeliveryUserConfirmation | None` (`exclude_if` None). The validator requires it
  exactly when `resolved_request.applies_to` is set: same `change_id`, `outcome_id` and `request_id`, `scope`
  equal to `applies_to`, `confirmation_id` equal to `resolution.confirmation_id`, and a verifying digest.
  Schema 2 also accepts route `same-outcome-planner` for scoped answers. `resolve_request` writes it in
  the answer's transaction for a scoped Builder answer and for a scoped Planner pause answer, which today
  writes no receipt (`delivery_runtime.py:2238-2250`). An unscoped Planner answer keeps that receipt-free
  path; schema-1 receipts stay unscoped. Replay follows the L row: Builder same-task through
  `_builder_request_resolution_successor`, Planner same-outcome through `_planner_handoff_answered_request`,
  and every lifecycle baseline by rank. A local entry no receipt binds, a bound entry absent locally, a byte
  difference or another order fails the existing bootstrap check; the Change is unavailable (V20).

### 1.8 Interfaces and error cases

| Interface | Behavior |
| --- | --- |
| `owlbear_delivery.acceptance_criteria` (new leaf; imports `target_contract` only) | `acceptance_criteria(contract) -> tuple[DeliveryAcceptanceCriterion, …]`; `parse_acceptance_item(text)` returning the optional `acceptance_id` and the statement; `acceptance_version(statement)`; `DeliveryAcceptanceRef` |
| `owlbear_delivery.evidence` (new; imports models and `acceptance_criteria`, imported by runtime and application, never by `runtime_models`) | `evaluate_acceptance_evidence(contract, frontier, request_observations=()) -> DeliveryAcceptanceCoverage`; `resolve_confirmation`, `confirmation_applies` (§1.5); `finalization_basis_digest(...)`; projection builder (N03-C) |
| `compile_delivery_contract` | Adds the three identity diagnostics; output bytes unchanged for valid input |
| `DeliveryAuthorityRegistry.admit` | First admission requires authored identities |
| `DeliveryRuntime.publish_result`, `DeliveryRuntime.finalize_change` | Enforce §1.6; on violation raise `DeliveryAcceptanceEvidenceError` (subclass of `DeliveryRuntimeConflictError`), code `ERR_DELIVERY_ACCEPTANCE_EVIDENCE`, `gaps` ≤ 64 × `{acceptance_id?, observation_id?, reason}`; reasons `uncovered`, `unknown-legacy-only`, `missing`, `failed`, `legacy-observation`, `unknown-acceptance`, `stale-acceptance-version`, `confirmation-unresolved` (no such ledger entry), `confirmation-not-applicable` (outcome, scope, procedure or decision), `review-basis-missing`, `review-basis-stale`, `review-observations-mismatch`, `finalization-basis-unavailable`, `finalization-context-oversized` |
| `DeliveryRuntime.resolve_request`, `PortfolioApplication.answer` | For a scoped request, accept only a `DeliveryUserConfirmation` built by a boundary adapter (D13) and write the request resolution, the ledger entry and, during a retained Builder or Planner handoff, the schema-2 request-resolution receipt binding that entry (§1.7) in one transaction under the existing `expected_frontier_digest` CAS, together with consuming the request's consent generation (I11); a scoped request without one, a caller `resolution` on a scoped request or a full ledger raise `DeliveryConfirmationError`, code `ERR_DELIVERY_CONFIRMATION`, reasons `confirmation-required`, `declined`, `channel-unavailable`, `ledger-full`, `question-closed`; nothing is written except the generation's recorded disposition (D13 *Single use*). Unscoped requests behave as today |
| MCP `answer` (N03-A) | The adapter method declares the server-injected `confirmation` parameter of D13, which `_flatten_tool` registers and keeps out of the input schema. For a scoped request the resolver checks the channel (form elicitation declared; on the legacy route also a back-channel), else the handler refuses `channel-unavailable`; otherwise one question is asked on the negotiated route (legacy `elicitation/create` mid-call, modern `InputRequiredResult` round trip) and the handler builds the confirmation from an `accept` only; `decline` or `cancel` → `declined`, consuming the question's consent generation (I11); a re-sent answer to a consumed generation returns its recorded disposition. A `request_state` the SDK boundary rejects fails with JSON-RPC `INVALID_PARAMS` before the resolver or handler runs (P16). Caller `resolution` and `provenance` are ignored for confirmation purposes. No lock is held while the user answers |
| Cockpit HTTP `answer_request` (N03-A) | For a scoped request: `409` `ERR_DELIVERY_CONFIRMATION` reason `channel-unavailable` with chat guidance; caller `provenance` never counts. [U2](#u2--which-clicks-and-answers-count-as-the-user-said-yes) may add a Cockpit channel in N03-C |
| `show_finalization_context` | Adds `semantics: DeliveryFinalizationSemantics` and `semantics_refusal: DeliveryContextRefusal` (each `exclude_if` None; exactly one set whenever the context is otherwise available). `semantics` holds: contract digest and title; outcomes with promise, commitment and dependency IDs and criteria; commitments; task results (ID, title, commit, result digest, observation IDs); per promoted task its bound authority (`task_id`, `task_digest`, `result`, `constraints`, `exclusions`, `proof_boundaries`, `acceptance_observations`); ledger confirmations cited by task evidence (scope, decision, channel; §1.5); `diff_base`; `change_head`; per-criterion coverage from task evidence; `basis_digest`. Task authority is bound by the result digests, which hold `task_digest`; the Design package is not included. Size: see the context budget below |
| `show_build_context`, `show_plan_context` | Add `acceptance: tuple[DeliveryAcceptanceCriterion, …]` for the outcome |
| MCP | `finalize_change`, `submit_result` and the request-bearing `transition_delivery` and `settle_worker_invocation` schemas (`applies_to`) follow the core models (strict); the error maps to its code with bounded `gaps` in `TargetDiagnostic` (N03-A); `DeliveryOperatorContextResponse` copies `evidence` (N03-C); no new tool |
| Projection (N03-C) | `DeliveryEvidenceProjection{change_id, contract_digest, frontier_digest, finalization_id, finalization_rules, criteria, unattributed, counts}`: `finalization_rules` is `typed`, `legacy` or `none`; `criteria` holds one `DeliveryAcceptanceEvidenceView` per criterion with status `covered`, `missing`, `waived`, `uncovered` or `unknown` and ≤ 16 evidence items, latest first; `unattributed` holds ≤ 64 legacy or non-covering observations plus a truncated count |
| Surfaces (N03-C) | `DeliveryChangeView.evidence` (whole Change); `WorkItemDetailView.evidence` (outcome item: its criteria; publication item: all); `DeliveryOperatorContext.evidence` (outcome); HTTP work-item detail; Cockpit technical summary |

**Finalization context budget** (D12). `DeliveryContract` and `DeliveryTaskDefinition` bound none of their
collections, so one byte budget bounds `semantics`:

- **Budget:** `FINALIZATION_SEMANTICS_MAX_BYTES = 262_144` in `evidence.py`; the live maximum is 34,560 bytes (P12).
- **Measure:** UTF-8 length of `json.dumps(semantics.model_dump(mode="json"), sort_keys=True,
  separators=(",", ":"))` over the complete value before emission. Identical inputs give the identical size (I7).
- **Within budget** (≤, boundary inclusive): `semantics` is returned complete; `semantics_refusal` is None.
- **Over budget:** `semantics` and its `basis_digest` are withheld; `semantics_refusal` is
  `{code: "finalization-context-oversized", measured_bytes, budget_bytes}`. No obligation, criterion, task
  authority or confirmation is truncated, sampled or partially emitted.
- **Finalize:** `finalize_change` re-measures under the checkpoint lock and refuses an oversized Change with gap
  reason `finalization-context-oversized` before any write, even when the review carries a recomputed basis.
- **Consequence:** an oversized Change cannot finalize under N03 rules. The Finalizer reports
  `independent-review-unavailable` (D7) and stops; the remedy is a requirement change or split (N04) or a
  later plan raising the budget. No stored format changes; the N03-C projection keeps its own caps.

### 1.9 Contracts for successors

- **N04** consumes §1.4 survival rules and the evaluator. Its applicability report adds reviewed records that
  map evidence for `(id, old version)` to `(id, new version)`; the evaluator stays a pure ordered fold, so those
  records join the sequence without changing N03 rules. `_carry_forward_unresolved_binding` is untouched by N03.
  **Confirmation contract for N04:** revision activation carries `DeliveryFrontier.confirmations` unchanged
  (I10). Applicability evaluation resolves a reused record's confirmation with `resolve_confirmation` by
  `confirmation_id`, never from active requests, so a request that N04 moves to history keeps its
  confirmation authority. `confirmation_applies` checks the exact criterion version: for `(id, old version)`
  → `(id, new version)` a `waived` or `human-confirmed` record stays `stale-acceptance-version` until the
  user confirms the new version through the boundary (D13): N04's `confirm_revision_criterion` asks with
  use `confirm-revision-criterion` and its own binding, one consent generation per question (I11); no
  reviewed applicability record transfers it.
  Same ID and version: the original confirmation still applies.
- **N06** adds no confirmation channel and no locator scheme (N06 D3). An interaction-linked request is an
  ordinary scoped `confirm-check` request (§1.5) answered through N03's `answer` and the D13 boundary,
  including its consent generation (use `confirm-check`, the N03 binding; I11); its ledger entry has
  channel `mcp-elicitation` (`cockpit` only if U2 adds
  it), and the link lives in its scope, question digest and `confirmation_id`. Whether a Cockpit-hosted
  confirmation counts as user-only follows [U2](#u2--which-clicks-and-answers-count-as-the-user-said-yes);
  assisted checks record `manual-procedure` or `command` results with `procedure_registration_digest` = handler
  digest, `target_class` and `environment`. `missing` with owner `assisted-check` is the gap N06 resolves.
- **N05** may show the projection counts in **Approve merge**; it adds no evidence semantics. N05-C reuses
  D13's registration and both elicitation routes for merge approval, retirement and reply decisions
  (N05 D14), with its own confirmation record; N05-B uses the `consent_generation` family with its own
  uses and bindings and adds no generation family of its own. Whether Cockpit counts follows U2.
- **N08** renders N02 `CapabilityReport` rows for format 2 and the widened families.

### 1.10 Existing owners to reuse

`_receipt_digest` and the attribute-copy `create` pattern (`delivery_runtime.py:557-561`); `_omit_when_none`
(`delivery_runtime.py:158`); `DeliveryRequestResolution.provenance` (kept for unscoped answers);
`validate_finalization_head` ancestry
(`change_workspace.py:5033-5036`); `FinalizationReportStore` and its existing codes; the N02 registry, gate,
`delivery-migrate` and `delivery-lc`; the MCP SDK's `Resolve`/`Elicit` resolver transport and its default
`RequestStateBoundary` (P16); `Client(assemble_target_server(...))` with `mode` and `elicitation_callback`,
the Cockpit HTTP client and the E2E stack.

### 1.11 Exclusions

Revision activation and applicability after revision (N04); prepared interactions and private input (N06); a
waiver path beyond [U1](#u1--may-a-user-waive-a-required-acceptance-criterion)(b) (no agent, reviewer or
unconfirmed waiver); a Cockpit confirmation channel (pending
[U2](#u2--which-clicks-and-answers-count-as-the-user-said-yes)); claim IDs on
`DeliveryTaskDefinition` (task digest churn for no engine use; Planner guidance cites IDs in text instead);
evidence projection for archived completed history; execution attestation; contract schema change.

### 1.12 Decisions

Agent-settled with probe evidence:

- **D1 Identity in authored text, contract v2 unchanged** (P4). Two live packages already prefix every item
  with `AC-NNN:`; all admitted authorities recompile byte-identically. A typed contract v3 would change
  `DeliveryContract` and every consumer schema, and a v2 package re-admitted under a v3-emitting compiler would
  look like a revision that invalidates all outcomes (replay equality at `delivery_admission.py:197`, then
  `_delivery_frontier` → `_invalidated_outcomes`).
- **D2 Content version, positional legacy IDs scoped to one contract** (P4: B1's revision moved 7 of its 9
  unchanged texts; 9 match by version, 2 by position).
- **D3 Version widening, no frontier rewrite** (P2, P3). Rewriting frontiers changes their digests, which nine
  persisted record types hold, including the Finalizer reservation and report basis that N02 D6 lets an
  upgrade carry. Widening keeps every stored digest valid. This deliberately uses N02's `readable-legacy`
  class for a mutable family; N02 D5 lists rewrite for 17 → 18 only because the old reader already rewrote.
- **D4 Results keep only non-failing records; finalization only satisfying ones.** Failures go to block,
  retry or `report_finalization_failure`; gaps (`missing`) and user waivers (`waived`, U1(b)) stay durable
  and visible. A satisfying record is proof or an applicable waiver (§1.5), so a Finalizer may submit an
  exact-head waiver just as a Builder may carry one.
- **D5 Last record wins**, in ancestry order (P7), so later evidence can close or reopen a gap
  deterministically.
- **D6 Basis digest and observation set in the review.** The reviewer attests the semantic basis it saw and
  the exact ordered observations it reviewed; the engine re-derives and compares both, which proves R5
  without trusting free text. Observation IDs sit in the review, not the context digest, because the
  context precedes the exact-head checks.
- **D7 No new finalization report code.** Uncovered criteria are reported as `maintained-check-unavailable`,
  failed checks as `maintained-check-failed`, assembled-outcome findings as `independent-review-failed`; the
  projection names the criteria. This avoids versioning the unversioned report family.
- **D8 Re-split.** Persisted shapes and the context the engine validates against all land in N03-A, together
  with the receipt-construction text of the skills (companion rule, execution plan §1.4); N03-B keeps the
  semantic procedures and host rehearsal; N03-C the projection. See [3.5](#35-required-execution-plan-deltas).
- **D9 Confirmation scope on the existing request route** (P10). Requests bind no criterion or procedure
  today, so applicability needs one optional request field. It changes nested request shapes, which the
  frontier, snapshot and receipt widening already version. The user's answer to a scoped request arrives
  only through the D13 boundary, and its authority lives in the ledger, not in the request.
- **D10 No new observation when carried evidence covers all** (P10). Today's request and receipt require
  one observation; requiring an exact-head check with nothing uncovered would contradict R9. Complete
  coverage plus the exact-head finalization review is the proof; maintained supporting checks stay optional.
- **D11 Execution-plan amendment.** This P revision amends execution plan §4.1, §5 N03 (phases, size, LC,
  frontier note), §2.6 and §7 ([3.5](#35-required-execution-plan-deltas)): changes that §1.1 reserves for
  user approval. Merged under the user's overnight authorization of 2026-10-03; confirmed 2026-10-03
  (listed to the user without objection).
- **D12 All-or-nothing context budget** (P12). A truncated context would let the reviewer attest a basis that
  omits obligations (R5, R10). One deterministic byte budget with a typed refusal keeps the context complete or
  absent; 256 KiB is 7.5× the largest live upper bound, and finalization refuses rather than degrades.

Engineering decision by the lead (PR #360 plan gate round 1):

- **D13 Confirmation boundary: MCP elicitation** (P15, P16).
  - *Threat model.* An agent can call every Delivery MCP tool with any arguments. MCP `answer` forwards a
    caller-supplied `resolution` with `provenance: user-confirmed` unchanged (`target_server.py:442-453`), so
    an agent could manufacture a waiver or a human confirmation, and a scoped answer that declines a waiver
    would still pass a provenance check. A user confirmation therefore has to arrive on a channel that the
    agent's normal tool surface cannot satisfy. The agent also runs as the same OS user and could in
    principle forge state files or call the Python API from a terminal. The boundary targets the agent's
    tool surface, not a hostile local process; existing Delivery state integrity checks (receipt digests,
    frontier CAS, snapshot identity) detect tampering only where they apply (R12).
  - *Channel.* When MCP `answer` targets a scoped request, the Delivery MCP server asks the user through MCP
    form elicitation inside that tool call. VS Code renders the form to the user; the model neither sees a
    way to answer it nor supplies the response. The form shows the Change, outcome, request ID, kind, each
    criterion ID, version and statement, the procedure and the expected frontier digest; its one required
    field is the enum `decision` (§1.5). N05 D14 uses the same boundary for merge approval and retirement.
  - *One declaration, two routes* (P16). The adapter method declares one server-injected parameter,
    `confirmation: Annotated[DeliveryConfirmationOutcome, Resolve(confirmation_question)]`. The SDK
    resolver picks the transport from the negotiated protocol (`resolve.py:96`, `:664-670`):
    - *Legacy* (up to `2025-11-25`): the resolver's `Elicit` marker runs `Context.elicit`, which sends a
      server-initiated `elicitation/create` mid-call (`resolve.py:572-587`, `context.py:196-227`,
      `session.py:351-380`). Without a back-channel the send raises `NoBackChannelError`
      (`connection.py:132-147`).
    - *Modern* (`2026-07-28` and later): the protocol forbids server-initiated requests
      (`connection.py:156-167`), so `Context.elicit` cannot work. The resolver's marker is recorded as
      pending and the tool returns `InputRequiredResult` (`input_requests` and `request_state`) without
      running the handler body (`resolve.py:600-613`, `:512`; `mcpserver/tools/base.py:172-176`). The
      client retries the same `tools/call` with `input_responses` and the echoed state; the SDK accepts an
      answer only for the exact rendered question it recorded (`resolve.py:607`).
    - *Channel check first.* `confirmation_question` takes the `Context` and tool arguments by name
      (`resolve.py:383-395`). It returns a plain value, not a marker, for an unscoped request (nothing is
      asked) and when the channel is missing: no form elicitation in `ctx.client_capabilities`, or a legacy
      session whose `can_send_request` is false (`session.py:80`). The handler then refuses
      `channel-unavailable`. Without this check the SDK would raise `MISSING_REQUIRED_CLIENT_CAPABILITY` or
      `NoBackChannelError` (`resolve.py:575-576`, `:611`, `:673-708`): a protocol error before the body
      that writes nothing but is not Delivery's typed refusal.
  - *Registration.* `_flatten_tool` builds each tool's signature only from the request model's fields and
    forwards only that model (`target_server.py:1325-1381`, `:1347-1370`), so a `Context` or `Resolve`
    parameter would never reach MCP registration today. N03-A makes it copy every adapter-method parameter
    other than `request` whose annotation is `Context` or `Annotated[_, Resolve(...)]` into the flat
    signature and annotations, and `flat_tool` passes those keys to the method beside the validated model.
    The SDK leaves such parameters out of the input schema (`mcpserver/tools/base.py:88-100`), and
    `_install_strict_argument_model` (`target_server.py:1272-1290`) derives its strict model from that
    schema with `extra="forbid"`, so no caller can supply them. No other tool's schema changes.
  - *Outcomes.* An `accept` records one `DeliveryUserConfirmation` with channel `mcp-elicitation` and the
    digest of the exact rendered question. `decline` or `cancel` records no confirmation; it consumes the
    question's consent generation and leaves the request open and the frontier unchanged (*Single use*).
    A `keep-required` or `failed` answer is recorded as the user's decision but is not affirmative for a
    waiver or a passed check (I6). Caller `resolution` and `provenance` are ignored for confirmation purposes.
  - *No fallback.* A client without form elicitation, or a legacy session without a back-channel, is
    refused with `channel-unavailable`; nothing falls back to caller provenance.
  - *Request-state boundary* (replaces the round-1 MAC, whose premise was wrong). `MCPServer` installs
    `RequestStateBoundary` by default under a process-local AES-256-GCM key (`mcpserver/server.py:237-245`,
    `request_state.py:140-149`); `assemble_target_server` passes no policy (`target_server.py:1260`). The
    boundary seals every outgoing `request_state` and verifies every inbound one before any resolver or
    handler runs. A malformed, forged, foreign-key, expired (TTL 600 s), wrong-method, wrong-tool,
    wrong-arguments or wrong-audience state is refused with JSON-RPC `INVALID_PARAMS` "Invalid or expired
    requestState" (`request_state.py:261-268`, `:353-406`). Delivery adds no MAC of its own.
    - *Key custody.* The key exists only in the Delivery MCP process's memory; it is never written, logged
      or shared. Each VS Code window runs its own stdio process, so another window's or server's state
      fails as an unknown key (`request_state.py:244`).
    - *Restart and expiry.* A state minted before a restart or older than its TTL is refused; nothing is
      written and the request stays open. The next `answer` call starts a fresh round, so the user is asked
      again.
    - *Binding.* The sealed state binds the method, the tool name and a digest of all tool arguments
      (`request_state.py:271-285`, `:424-449`): here `change_id`, `request_id` and
      `expected_frontier_digest`, so a state minted for another request or frontier version is refused.
      Within one argument set the SDK accepts an answer only for the identical rendered question
      (`resolve.py:607`, `:806-825`), and the question renders every criterion ID, version and statement and
      the procedure. The resolver renders only while the current frontier digest equals
      `expected_frontier_digest`, the handler applies the answer under that CAS, and it re-checks the
      decision against the request kind. An answer therefore applies only to the request, criteria,
      versions and frontier it was asked for. Stdio carries no authentication, so no principal is bound
      (`request_state.py:394-405`); the per-process key stands in for it.
  - *Single use* (PR #360 rounds 3 and 4; I11). The boundary authenticates `request_state` but does not
    consume it: its checks hold no one-time identity (`request_state.py:327-406`), so within the TTL the
    same state can be sent again with any `input_responses`, and `_fulfil` accepts them while the rendered
    question still matches (`resolve.py:607`). Round 3 let the frontier stand in for that identity, but a
    decline or cancel leaves the frontier unchanged, so a refused question could be replayed with an
    affirmative answer. One shared mechanism, built by N03-A, therefore fences every boundary question:
    - *Record.* `DeliveryConsentGeneration` (family `consent_generation`, §1.7; `consent_generation.py`):
      `change_id`, `use`, `subject_id`, `binding_digest`, per-Change `sequence`, `generation_id` (256-bit
      nonce from `secrets`), `created_at`, and state `open` or `answered` with a disposition: `outcome`
      (`accepted`, `declined`, `cancelled` or `refused`), a bounded `code` and, when accepted,
      `confirmation_id` and the owner's record ID. `use` is a bounded slug and `binding_digest` the sha256
      of the use's canonical binding, so successors add uses without a schema change; each owner
      validates its own binding. Generations are local replay protection, not confirmation authority, and
      are not in snapshots: the ledger stays the authority (I6, I10), and a sealed state never outlives
      the process key that minted it, so a fresh host restored from a snapshot needs none.
    - *Uses.* N03: `waive` and `confirm-check` (the scope kind), subject `request_id`, binding
      `{outcome_id, request_id, applies_to, expected_frontier_digest}`; N06 interaction confirmations are
      `confirm-check` requests with this binding (§1.9). N04: `confirm-revision-criterion`, with the
      binding N04 defines. N05 (D14): `approve-merge` (subject `offer_id`), `retire-held-merge` (subject
      `approval_id`, binding the hold snapshot) and `reply-decision` (subject reply ID), each with its
      `change_id`.
    - *Before asking.* A round without input responses (every legacy call; each modern first round) first
      returns a disposition already in force (a resolved request's resolution; for N05 a live approval, a
      decided reply or a retirement) and asks nothing. Otherwise, under the owning lock, which it releases
      before asking, it renders the subject's latest generation if that is `open` with the call's binding,
      else durably creates one (exclusive create of the next sequence). The rendered question includes
      `generation_id`, and the ledger entry or owner record names it.
    - *Answer-bearing rounds never create.* A modern round with input responses renders the subject's
      latest generation only while it is `open` with the call's binding; otherwise it asks nothing and
      passes that generation, or none, to the handler. An older generation is never rendered again, so
      an answer to it is re-asked by the SDK, never applied.
    - *Consumption.* Under the owning lock (N03: the Change's frontier writer; N05: its mutation-fence
      entry), the handler applies an answer only to the subject's latest generation while it is `open`,
      and in one replacement transaction writes it `answered` with its disposition together with every
      write the answer causes. Accept, decline, cancel and a failed re-check all consume it. For a scoped
      request: an accepted answer resolves the request and appends the ledger entry (`accepted`); decline
      or cancel writes only the generation (`declined`, `cancelled`), so the request stays unresolved and
      the frontier bytes unchanged; a frontier other than `expected_frontier_digest`, a request no longer
      open or a full ledger writes only the generation (`refused`, code `frontier-changed`,
      `request-closed` or `ledger-full`) and raises the existing conflict or `ledger-full`.
    - *Replay.* An answer that reaches an `answered` generation, whatever `input_responses` it carries,
      returns the recorded disposition (the resolution and ledger entry; `declined` for a decline or
      cancel; the same typed refusal) and writes nothing. A continuation round whose subject has no
      generation, or whose latest generation has another binding, refuses `ERR_DELIVERY_CONFIRMATION`
      `question-closed`. Only a new call renders a new generation, i.e. a new question the user answers.
    - *Never applied.* An accepted answer whose transaction did not commit (crash, I/O failure) consumed
      nothing; it can apply at most once, only while its generation stays `open`, its request and
      frontier still match and validation succeeds. `ledger-full` is a recorded refusal and keeps refusing.
    - *A resolved request still rejects a second answer.* `DeliveryRuntime.resolve_request` returns the
      request for an identical resolution and raises `request is already resolved` for any other.
  - *Concurrency.* No lock is held while the user answers, on either route; between modern rounds nothing
    is held at all. Competing answers to one `open` generation serialize on the owning lock: the first
    consumes it, the others return its disposition. A changed frontier consumes the generation as
    `frontier-changed`; a new call asks again.
  - *Scope.* The same boundary covers `human-confirmed` evidence, which has the same fabrication route, and
    N05 merge approval, retirement and reply decisions (N05 D14). Whether a Cockpit confirmation also counts
    is [U2](#u2--which-clicks-and-answers-count-as-the-user-said-yes); until it is decided, Cockpit refuses
    these actions and points to the chat. The SDK notes that an agent-type client may answer an
    elicitation itself (`elicitation.py:114-116`); that VS Code always asks the user, on the route it
    negotiates, is G10.

#### U1 — May a user waive a required acceptance criterion?

Decided 2026-10-03: (b), by the user in chat after a full status-quo, problem, options and pro/con briefing
(required before N03-A starts). The answer changes one validator rule, one projection label and the PR
evidence text; N04-P and N06-P plan against (b).

- **Status quo:** `finalize_change` accepts any observation strings. The programme forbids agent waivers
  (§5.1 role table) and silent waivers (V16), and routes changed requirements to explicit agreement (§8.4).
- **Problem:** the execution plan lists `waived with an owner` as a result, but no source says whether an
  explicit user waiver may let finalization pass.
- **Options:** (a) `waived` records the user's explicit decision but never satisfies a criterion; dropping a
  criterion is a requirement change (N04 **Change requirements**). (b) A `waived` record with a resolved
  user-confirmed request bound to that criterion and version satisfies finalization and is shown as waived in
  the projection and PR. (c) Agents or reviewers may waive.
- **Decision: (b).** The agents had recommended (a), which keeps one route for changing what "done" means
  (U7, §8.4); the user chose an explicit, recorded and visible waiver instead. Agents and reviewers never
  waive, so (c) stays excluded. The waiver is captured through the D13 boundary, so an agent cannot
  manufacture it.

#### U2 — Which clicks and answers count as "the user said yes"?

Open user decision, required before N03-C and N05-C start. N03-A, N03-B and N05-B do not depend on it.

- **What this is about.** Some Delivery steps happen only because you agreed to them. The AI agents that
  do the work must never be able to give that agreement for you. This decision is about where your
  agreement may be given: only by answering a question in the chat, or also by clicking a button in
  Cockpit, the local Delivery web page.
- **When it applies, and how often:**
  - *Approving a merge that Delivery carries out: every Change that Delivery merges, sometimes more than
    once.* Before Delivery merges a finished Change's pull request into its target branch, you approve that
    exact merge. You are asked again, with a new question, if you withdraw your approval, if GitHub refuses
    the merge, or if the Change or its target branch moved and the Change had to be proved again. This is
    the path you meet most often.
  - *Merging the pull request yourself in GitHub: not covered.* You can always do this instead, under every
    option. It needs no Delivery approval; Delivery notices the merge and completes the Change (N05 R4).
  - *Retiring a held merge: rare.* Only when a merge request that Delivery already sent is stuck and
    Delivery's automatic checks have run out: either GitHub's answer was lost, or GitHub still reports the
    request as pending (N05 U4 and N05 §1.13). Retiring means Delivery stops pursuing that merge; it cannot
    cancel the request in GitHub.
  - *Waiving an acceptance criterion: whenever you choose to.* Under
    [U1](#u1--may-a-user-waive-a-required-acceptance-criterion)(b) you may waive any criterion with an
    explicit answer, including one that a machine could check; it then shows as waived, not as proved.
    Agents may ask; only your answer waives. How often depends on you.
  - *Confirming a check that only a person can do: occasional.* Only for criteria whose proof needs a
    person, for example looking at a page in a browser and saying that it works (N06's prepared checks
    ask this way too).
  - *Deciding about a pull-request reply that may or may not have been posted: rare* (N05 Y4). Chat only
    under every option, because Cockpit has no control for it.
- **Status quo (as planned so far).** Agents can call every Delivery tool with any arguments, and today's
  tools accept an argument that simply says "the user confirmed". D13 replaces that: Delivery itself asks
  you a question inside the chat (an MCP elicitation, which VS Code shows as a small form), and only your
  answer to that form counts; the agent cannot fill it in through its tools. Each answer counts once:
  sending the same answer again never approves or waives a second time, and a new approval always needs a
  new question that you answer (D13 *Single use*, N05 D14). D13 covers every case above. The approved N05
  plan also puts an **Approve merge** button in Cockpit, and Cockpit's answer route today forwards
  whatever `provenance` the caller sends (`routes/target_work.py:133-138`); N03-A refuses these answers
  in Cockpit until this decision.
- **Problem.** Agents in this workspace also have browser tools: they can open Cockpit and click its
  buttons, and they run as the same macOS or Ubuntu user as you. Cockpit's planned protections, a check
  that the request comes from Cockpit's own page (Origin) and a same-site session cookie, stop other
  websites, not a browser that an agent drives. A Cockpit click therefore does not show that you clicked.
- **Options:**
  - (a) *Cockpit clicks count, as well as chat answers.* Pro: one click where you already look; no chat
    needed; Cockpit keeps its **Approve merge** button. Con: an agent driving a browser can click it, so
    the rule "agents never approve" rests on agents following instructions. Risk: an unwanted merge into
    the shared target branch, which Delivery cannot undo. Confidence that it keeps agents out: low.
  - (b) *Only the chat answer counts.* Cockpit shows what is waiting (the merge offer with repository, PR,
    head, target and checks; the waiver's criteria) and says to answer in the chat. Pro: one rule that no
    agent tool can satisfy; Cockpit gains no new authority. Con: every approval of a merge that Delivery
    carries out happens in chat, not Cockpit, including each renewed approval; you need a chat running the
    Change at the moment you approve, and a Change waits while no chat is open (merging yourself in GitHub
    stays possible). Risk: it relies on VS Code showing the form to you instead of letting the model
    answer it (G10, checked in N03-B's rehearsal); if that check fails, Delivery cannot take approvals at
    all and you merge in GitHub, which Delivery still observes and completes (N05 R4). Confidence that it
    keeps agents out: medium-high; that the chat cost is acceptable: medium.
  - (c) *Cockpit clicks count only with an operating-system presence check* (Touch ID or your password on
    macOS). Pro: the Cockpit button stays, and a click needs a person at the machine. Con: no Ubuntu
    equivalent, so Ubuntu falls back to (b); a native helper to build and maintain; needs a plan revision
    first. Risk: the safety rule differs by platform. Confidence: medium.
  - (d) *Split:* Cockpit counts for merge approval and retirement, chat only for waivers and human checks.
    Pro: the frequent action stays one click. Con: the weaker rule guards the action with the largest and
    least reversible effect. Risk: as (a) for every merge. Confidence: low.
- **Recommendation: (b)**, confidence medium. It is the only option where "agents cannot approve for you"
  is enforced rather than requested, and a merge is the least reversible step Delivery takes. The honest
  cost is that every merge Delivery carries out is approved in the chat, not in Cockpit, and approved
  again after each withdrawal, refusal or re-proof; merging yourself in GitHub is unaffected. If N03-B's
  rehearsal shows that VS Code does not show the form reliably or that the chat round trip is too costly,
  (c) on macOS is the next step; (a) only with its residual risk accepted explicitly.
- **Effect.** N03-A builds the chat question under every option, and N05-C uses it for merge approval and
  retirement. (b): N03-C and N05-C keep Cockpit read-only for these actions (what is waiting, plus "answer
  in the chat"); this changes the approved Cockpit **Approve merge** button (execution plan §5 N05 result,
  N05 R1) to a display, and choosing (b) approves that change. (a): N03-C and N05-C add Cockpit controls
  behind the Origin and SameSite checks with channel `cockpit`, each with its negative scenarios.
  (c): a plan revision for the native presence helper first. (d): N05-C as (a), N03-C as (b). N06's
  interaction confirmations are ordinary scoped requests and follow the same answer. Under every option
  each answer counts once (D13 *Single use*).

## 2. Feasibility Probes

Ran on `ef622c354` in the lane worktree (read-only) with `uv run --no-sync`; live state only read. Scripts and
outputs: `/Users/GGN7H9Q/Projects/owlbear-dev-lane-d/.owlbear/scratch/n03p/` (unversioned).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | `p1_live_inventory.py` on live `runtime/changes` | 3 Changes: frontier v18, contract v2. 12 task observations, all schema 1, free text (`0; 171 passed`, `exit:0; …`), 10 kinds. No local finalization receipt. B1 in Planning with 0 tasks and 12 criteria; `delivery-action-readiness` in Implementation with 4 of 5 results and 17 criteria; `frontier-serialization-contract` outcome completed, not finalized | Migration never needs to relabel; `unknown` is the honest status; no live finalization needs reinterpretation |
| P2 | Static scan for persisted frontier-digest fields | Persisted holders: `ChangeFinalizationAttempt` (`change_workspace.py:453`), `ChangeContinuationAction` (505), `WorktreePreservationReceipt` (1273), pending state publication (`delivery_runtime.py:350-351`), completed-outcome repair request and receipt (1404, 1445), Builder handoff change-intent receipt (1929-1930), `ReportFinalizationFailure` and `ProofAttempt` (`finalization_reports.py:93, 213, 244`), `RecoveryIntent` (`recovery.py:119`) | A frontier rewrite would stale custody N02 D6 allows across upgrades → D3 |
| P3 | `p3_union_bytes.py`: prototype schema-2 observation, union nested in a task result and a frontier-19 prototype | (a) Schema-1 receipt validates in a `schema_version`-discriminated union under strict JSON with the same `observation_id`; (b) task-result bytes and digest identical; (c) verdicts: exit 0 → passed, exit 1 → failed, expected 1 / exit 1 → expected-negative, expected 1 / exit 2 → failed, missing → missing; expected-failure without a status is rejected; mixed v1 + v2 results parse; (d) frontier 18 read as 19 keeps nested bytes; (e) string exit status rejected (`int_type`). The `model_dump()`-based `create` pattern emits serializer warnings for nested models | D3, I1, I4; schema-2 `create` copies fields by attribute |
| P4 | `p4_acceptance_identity.py`, `p4b_out.txt`: every live package compiled with the current compiler | 137 criteria in 9 packages; `delivery-action-readiness` and `delivery-offline-diagnostics` prefix all 17 items each with `AC-NNN:`, unique per Change; 0 mixed, 0 duplicate, 0 near-miss; all 7 admitted authorities recompile byte-identically. B1 revision `216a787…`: 12 criteria, 9 match an old one by version digest, 2 by position | D1, D2; the new diagnostics break no live package |
| P5 | `p5_out.txt`: schema probe on `FinalizeDeliveryChange` | Accepts an observation with `exit_status_or_artifact_locator="1"` | #219 premise holds on current `dev` |
| P6 | `p6_exclude_if.py`: widened review prototype | Schema-1 review bytes and `review_id` identical; new fields serialize only when set | D6 without identity change |
| P7 | Source read of `validate_finalization_head` | Requires pairwise ancestry of promoted task commits and each one an ancestor of the head (`change_workspace.py:5033-5036`) | Carried evidence lies on the head's history; record order is deterministic (D5) |
| P8 | Static scan for persisted models embedding bindings, results or frontiers | Versioned: `_DeliveryPlanningRetrySettlementReceipt` (`delivery_runtime.py:1693`), `_DeliveryBuilderInvocationSettlementReceipt` (1712), `_DeliveryBuilderPlanPromotionReceipt` (1750), `_DeliveryBuilderHandoffChangeIntentReceipt` (1917; frontiers at 1931-1932), `_DeliveryPlanningPauseReplay` (2106), `DeliveryStateSnapshot` (`delivery_state.py:72, 89`). Unversioned: `DeliveryResultCandidate` (`delivery_runtime.py:830`). `_DeliveryBuilderRequestResolutionReceipt` (1875) embeds no binding, result or frontier but embeds `DeliveryRequest` (1884; P10) | Nested change ripples to these families under N02 I2 → widening per family (§1.7) |
| P9 | Source read of the finalization context, Builder context and skills | `DeliveryFinalizationContext` (`application_models.py:747`) has no semantic authority or diff base; `DeliveryBuildContext` (733) has no acceptance; skills build schema-1 receipts (`w-change-finalization` Step 4; `w-packet-building` Step 2, lines 155-160); `test_agent_ecosystem_validation.py:967, 1031, 1161-1166` pin their text | #222 gap confirmed; skill text is a companion of N03-A |
| P10 | Round-1 source read (`delivery_runtime.py` unless named) | `_read` (6071-6083) returns `parse_delivery_frontier`'s canonical bytes (6266-6279) and rewrites when they differ; `_replace_content` (6121) passes `previous` as the expected prior content; `frontier_bytes()` (2332) returns `_read()[1]`; hashed at 3556, 4166, 4399, 5693, 2395, `application_acquisition.py:882, 1290`, `application_lifecycle.py:405`, `change_workspace.py:2350`, `application_publication.py:1548-1604`, `portfolio_application.py:1220-1449, 1727`, `application_recovery.py:859, 1042, 1353`, `delivery_application_loader.py:625`, `work_items.py:221`; `publication_base_digest` (2348) re-serializes the parsed model. `DeliveryRequest` (869) and `DeliveryRequestResolution` (851) bind no criterion or procedure. `FinalizeDeliveryChange.observations` (1526) and `DeliveryFinalization.observations` (548) require ≥ 1. `DeliveryTaskDefinition` (374) holds `constraints`, `exclusions`, `proof_boundaries` | Stored-byte contract (§1.7); I6 scope (D9); zero-observation finalization (D10); bounded task authority in `semantics` |

N02-A and N02-B are not implemented yet (`state_formats.py` absent at `ef622c354`); N03-A uses their planned
interfaces ([G1](#5-verification-gaps)).

Round-3 and round-4 probes ran on post-N01 `origin/dev` `58c4d928b` (source via `git show`, live state read only);
P13 read the same base plus N02-A (`c9d4a15b7`); P14 read lane-b `e6ed5bb31` (cited files unmodified):

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P11 | `grep` over every `owlbear_delivery` module: `_*successor*`, `_*lifecycle*`, `_validate_local_*`, frontier `==`/`!=`, `model_copy`, `frontier_digest`, `parse_delivery_frontier`, `model_validate_json` of frontiers (`scan_comparisons.txt`, `scan_frontier_digest.txt`) | Whole-frontier equalities only in the loader successor, handoff and lifecycle validators; `_planner_handoff_lifecycle_successor_frontier` compares a `snapshot.frontier` baseline with receipt frontiers (loader `:1683-1692`); `_is_repairable_frontier_successor` and promotion `_validate_successor` are binding-level; `repair_missing_request_provenance` writes parse's canonical bytes (`runtime_support.py:129-158`); every other site is a byte digest or read | §1.7 comparison inventory |
| P12 | `p12_semantics_size.py` on live `runtime/changes` | Upper bound of canonical `semantics` bytes: `delivery-action-readiness` 34,560 (17 criteria, 5 tasks); `frontier-serialization-contract` 15,840; `macos-managed-browser-authentication` 7,475 | D12 budget headroom |
| P13 | Round-4 source read on lane-b `c9d4a15b7` (`58c4d928b` + N02-A): every `_replace_content`, frontier `ReplacementTransactionParticipant` and `record_pending_publication` site | Model-equality gate only in `complete_recovery` (`delivery_runtime.py:1764`); `False` only in `acknowledge_checkpoint_publication` (`:782`) and the `_read` rewrite (`:2329`); `_portable_frontier` drops a published pending checkpoint (`delivery_state.py:790-796`) | P rows of §1.7 |
| P14 | Round-5 source read on lane-b `e6ed5bb31` | `acknowledge_checkpoint_publication` calls `_replace_content` (`delivery_runtime.py:782`), whose default base is `publication_base_digest(previous)` (`:2384`); that helper drops claim fields but keeps `pending_checkpoint` (`runtime_reads.py:78-95`). Snapshots embed `_portable_frontier` (`delivery_state.py:124`), which drops a checkpoint at `published_head` (`:790-796`). `_publish_delivery_state` acknowledges the prior marker (`portfolio_application.py:1725`) before checkpoint acknowledgment (`application_publication.py:1340`, `:170`). Replay refuses a remote digest outside {base, current} (`:1633`) | Acknowledgment-specific base (§1.7 P row) |

P15 ran for the PR #360 gate on lane-c `4839b1fc8` (`origin/dev` `634a77be7`) with the lane venv
(`env -u PYTHONPATH uv --directory <lane-c> run --no-sync`); scripts and outputs in
`/Users/GGN7H9Q/Projects/owlbear-dev-lane-c/.owlbear/scratch/gate1/` (unversioned). P16 is the round-2 source read
of the same venv on lane-c `9c06c97cd`. Bare SDK paths in P16 and D13 are relative to
`.venv/lib/python3.14/site-packages/mcp/server/`; there `context.py` and `resolve.py` mean the `mcpserver/`
modules; paths starting with `mcp/` are relative to `site-packages/`.

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P15 | `p_elicit.py`, `p_elicit2.py`: installed MCP SDK and Delivery adapters | `mcp` 2.3.0, no `fastmcp` (FastMCP is `MCPServer` in 2.x; `target_server.py:14` imports it). `Context.elicit(message, schema)` (`mcp/server/mcpserver/context.py:196`) → `elicit_with_validation` (`mcp/server/elicitation.py:103`) → `ServerSession.elicit_form` sends `elicitation/create` (`mcp/server/session.py:351`, `mcp/shared/peer.py:198`). `ElicitResult.action` is `accept`, `decline` or `cancel`; `decline` and `cancel` carry no data. Capability: `ClientCapabilities.elicitation`, `ServerSession.check_client_capability` (`session.py:137`); the marker path raises `MISSING_REQUIRED_CLIENT_CAPABILITY` without form elicitation (`mcp/server/mcpserver/resolve.py:678-690`). From protocol `2026-07-28` (`resolve.py:96`) elicitation rides `InputRequiredResult` with a client-round-tripped `request_state`; the resolver's own `_encode_state` adds no MAC (`resolve.py:664-669` and `_encode_state`), but P16 shows the server boundary seals it. The SDK docstring warns that an agent client may answer an elicitation itself (`elicitation.py:103`). MCP `answer` forwards the caller's `resolution` unchanged (`target_server.py:442-453`); Cockpit forwards `body.provenance` (`routes/target_work.py:133-138`); `DeliveryRequestResolution.provenance` (`runtime_models.py:826`); the writer is `DeliveryRuntime.resolve_request` (`delivery_runtime.py:2198`) via `PortfolioApplication.answer` (`portfolio_application.py:1340`) | D13 is feasible in the installed SDK; capability refusal is typed; host behavior is G10. Its round-1 conclusions that `Context.elicit` serves every protocol and that `request_state` needs a Delivery MAC are superseded by P16 |
| P16 | Round-2 source read of the same installed SDK and of `target_server.py` on lane-c `9c06c97cd` (no script; file:line below) | `Context.elicit` always calls `elicit_with_validation` → `session.elicit_form` → `send_request` (`context.py:196-227`, `elicitation.py:103-130`, `session.py:351-380`): a server-initiated request. Modern connections refuse those by construction (`connection.py:132-147` `_NoChannelOutbound`, `:156-167` `NotifyOnlyOutbound`; `NoBackChannelError`, `mcp/shared/exceptions.py:55`). `InputRequiredResult` comes only from `Resolve`/`Elicit`: `_uses_input_required` (`resolve.py:664-670`) selects `_fulfil`'s legacy branch (`:572-592`, `Context.elicit`, capability checked only when `can_send_request`) or the pending branch (`:600-613`), and `resolve_arguments` returns `InputRequiredResult` (`:475-512`) that `Tool.run` returns without the body (`mcpserver/tools/base.py:172-176`). An answer counts only for the recorded question digest (`resolve.py:607`, `:743-760`, `:806-825`). Resolvers take `Context`, other resolvers or tool arguments by name (`:383-395`); resolved and context parameters are left out of the input schema (`mcpserver/tools/base.py:88-100`). `MCPServer` installs `RequestStateBoundary` under `RequestStateSecurity.ephemeral()` when no policy is given (`mcpserver/server.py:237-245`; `request_state.py:140-149`, TTL 600 s): inbound state is unsealed and checked for expiry, method, tool name, argument digest, audience and principal before any handler (`request_state.py:327-406`, identity `:271-285`, claims `:424-449`); every failure is `INVALID_PARAMS` "Invalid or expired requestState" (`:261-268`). Delivery passes no policy (`target_server.py:1260`). `_flatten_tool` forwards only the request model (`target_server.py:1325-1381`). The client pins a route with `Client(mode="legacy" \| "2026-07-28")` and answers through `elicitation_callback` (`mcp/client/client.py:335`, `:348`) | D13's two routes, registration change and reuse of the SDK boundary instead of a MAC; boundary-level scenarios replace the forged-MAC scenario |

## 3. Phases

### 3.1 Shared rules

- **Layout.** Plans name symbols; re-resolve files with `grep` at phase start. N03-A requires N02-B, whose
  chain (N02-A ← N01-C ← N01-A, N01-B) guarantees the post-N01 layout: application methods in
  `application_*` mixins, workspace methods in `workspace_*`, runtime models in `runtime_models.py`, runtime
  receipts in `runtime_receipts.py`, and the 43 frontier writers (including `finalize_change`,
  `publish_result`) in the `delivery_runtime.py` facade (N01 I6).
- **Version numbering.** N05-B also bumps the format marker and follows N03-A (execution plan §4.2, since
  PR #360 round 4), so N05-B renumbers its versions and migration onto N03-A's and reruns LC.
- **Ownership** (execution plan §1.6). Opus keeps models, versioning, migration registration, evaluator,
  finalize validation, the confirmation boundary and ledger, and challenge reconciliation. Luna may take
  fixture conversion to schema-2 observations,
  frontend mirrors and rendering, parity assertions and skill text once Opus fixes the contract.
- **Assembled proof** uses the default loader, `Client(assemble_target_server(...))`, the Cockpit HTTP client
  and the E2E stack on disposable portfolios with local bare remotes.
- **Exports.** A phase that changes `owlbear_delivery.__all__` updates
  `serve/delivery/tests/fixtures/module_surface.json`
  (N01 D9) and the N02 fingerprint fixture in the same PR.

### 3.2 N03-A — Evidence model, identities and finalization validation

- **Prerequisites:** N03-P, N02-B; [U1](#u1--may-a-user-waive-a-required-acceptance-criterion) answered
  ((b), 2026-10-03).
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/acceptance_criteria.py`, `evidence.py`, `consent_generation.py`
    (`DeliveryConsentGeneration`, its store and replacement-transaction participant; D13 *Single use*)
  - `target_contract.py`: `DeliveryCompilationDiagnosticCode`, `_parse_outcome` (`:354`), `_validate_definitions`
  - `delivery_admission.py`: `DeliveryAuthorityRegistry.admit` (`:183`)
  - `runtime_models.py` [N01-C]: observation, result, confirmation, environment and reference models;
    `DeliveryRequest.applies_to`, `DeliveryConfirmationScope`, `DeliveryRequestResolution.confirmation_id`,
    `DeliveryUserConfirmation`, `DeliveryFrontier.confirmations`, `DeliveryConfirmationError`;
    `DeliveryReview`/`Receipt`, `DeliveryTaskResult`, `DeliveryFinalization`/`Receipt`, `DeliveryFrontier`,
    `FinalizeDeliveryChange`, `DeliveryAcceptanceEvidenceError`
  - `runtime_receipts.py` [N01-C]: the five embedding receipts of P8 and `_DeliveryBuilderRequestResolutionReceipt`
    (schema 2 binds the ledger confirmation and admits scoped `same-outcome-planner` answers, §1.7)
  - `delivery_runtime.py` facade: `DeliveryRuntime.publish_result`, `DeliveryRuntime.finalize_change`,
    `DeliveryRuntime.resolve_request` (ledger append; schema-2 resolution receipt for scoped Builder and
    Planner handoff answers), `_read`, `_replace`, `_replace_content` (stored-byte
    contract, §1.7; I10 guard); `complete_recovery` and
    `acknowledge_checkpoint_publication` (P rows, §1.7); `frontier_bytes` and
    `publication_base_digest` wherever N01-C placed them (`runtime_reads.py` per N01 plan §3.6);
    `parse_delivery_frontier` wherever N02-A placed it
  - `runtime_settlement.py` [N01-C]: handoff intent receipt construction (§1.7) and
    `_builder_request_resolution_receipt_participant` (schema 2); `portfolio_application.py`:
    `answer` (passes the boundary confirmation; refuses scoped requests without one)
  - `delivery_state.py`: `DeliveryStateSnapshot`, `parse_delivery_state_snapshot`, snapshot version constants,
    `_same_snapshot_inputs`, `_portable_frontier`, `_snapshot_digest`
  - `delivery_application_loader.py`: snapshot restoration bytes and the S, N and L rows of the §1.7 inventory
  - `application_publication.py`: `_pending_publication_remote_head`, `_reconcile_pending_state_publication`
  - `application_recovery.py`: `repair_stranded_frontier`; `repair_missing_request_provenance` beside
    `parse_delivery_frontier` (W row)
  - `state_formats.py` [N02-A/B]: §1.7 entries and migration `format-1-to-2`
  - `application_models.py`: `DeliveryFinalizationContext.semantics`, `.semantics_refusal`,
    `DeliveryFinalizationSemantics`, `DeliveryContextRefusal`,
    `DeliveryBuildContext.acceptance`, `DeliveryPlanContext.acceptance`
  - `application_lifecycle.py`: `show_finalization_context`, `_finalize_change_locked` (basis re-check under
    the checkpoint lock); `application_acquisition.py`: `show_plan_context`, `show_build_context`
  - `owlbear_delivery/__init__.py`; `serve/delivery/tests/fixtures/module_surface.json`; N02 fingerprint fixture
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py` (error code mapping, `_raise` carries `gaps`;
    `_flatten_tool` keeps server-injected `Context` and `Resolve` parameters through registration (D13);
    `answer` declares the D13 `confirmation` parameter and its resolver, with no Delivery MAC, on the shared
    consent-generation resolver helper that N04, N05 and N06 reuse; the default
    `RequestStateBoundary` stays installed); `target_models.py` (`TargetDiagnostic.gaps`, ≤ 64, `exclude_if` None)
  - `serve/cockpit/src/owlbear_cockpit/routes/target_work.py` (`answer_request` refuses scoped requests,
    U2 default) and `serve/cockpit/tests`
  - `serve/tools/src/owlbear_tools/delivery_diagnostics.py` (frontier 19, snapshot 3, receipts 2, marker 2)
  - tests: new `serve/delivery/tests/test_acceptance_criteria.py`, `test_evidence.py`,
    `test_consent_generation.py`; schema-2 fixtures in
    `test_delivery_runtime.py`, `test_portfolio_application.py`, `test_target_contract.py`,
    `test_source_bound_admission.py`, `test_delivery_state.py`, `test_work_items.py`,
    `test_completed_history.py`, `test_state_formats.py`, `test_state_migration.py`,
    `test_checkpoint_publication_regressions.py`;
    `serve/delivery-mcp/tests/test_delivery_adapter.py`, `test_target_server.py`;
    `serve/tools/tests/test_delivery_diagnostics.py`; `serve/cockpit/web/e2e/support/seed-work-portfolio-delivery.py`
  - companion skill text (receipt construction only): `w-change-finalization` Steps 2 and 4,
    `w-packet-building` Step 2, `w-design-session` Step 8 (`AC-NNN:` prefixes), `build-reviewer` output
    (`basis_digest` and `observation_ids` echo); `tests/test_agent_ecosystem_validation.py`
  - this plan's N03-A progress row; execution plan N03-A status row
- **Positive scenarios:**
  - Authored and legacy criteria derive as §1.4; every live package compiles unchanged; prefixed first
    admission succeeds; replay of an admitted legacy contract (B1 shape) succeeds.
  - A Builder result with schema-2 `passed`, `expected-negative` and `missing` (owner `assisted-check`)
    records promotes; the pending `missing` criterion shows `missing` in the evaluator.
  - Finalization where carried task evidence covers some criteria and exact-head observations cover the rest,
    with a matching review basis and `observation_ids`, writes a schema-3 receipt and frontier 19; an exact
    replay returns it.
  - Finalization of a Change whose carried task evidence covers every criterion, with zero new observations
    and an exact-head finalization review with empty `observation_ids`, writes a schema-3 receipt; no
    criterion is exercised again.
  - A `human-confirmed` manual observation whose `confirmation_id` names a ledger confirmation in the same
    outcome with decision `passed`, scoped to the covered criterion version and the observation's procedure,
    is accepted.
  - A task result with a `waived` record (owner user) whose `confirmation_id` names a ledger confirmation with
    decision `waive`, scoped to that criterion version and the record's procedure, promotes; finalization with
    every other criterion covered succeeds and the evaluator shows that criterion `waived` (U1(b)).
  - The Finalizer submits an exact-head `waived` record with an applicable `waive` confirmation (no task
    result covers that criterion), with a matching review: finalization writes a schema-3 receipt and the
    evaluator shows `waived`; the same record cited by a task result gives the same status.
  - Every golden D03 record and every schema-1 observation, review, result, finalization and embedding receipt
    round-trips byte-identically with unchanged identity; a v2 snapshot parses natively; a v1 snapshot upcasts
    to 3 with `migrated_from_snapshot_id`.
  - A v18 frontier: `get_change`, `list_changes`, `frontier_bytes` and `publication_base_digest` leave its
    file bytes, digest and base digest unchanged with no write; then one existing mutation (`set_change_intent`
    defer with the v18 `expected_frontier_digest`) commits one transaction whose prior content is the v18
    bytes, stores 19, records one pending publication on the v18 base and keeps every nested receipt identity.
  - Disposable checkpoint fixture, snapshot 2 / frontier 18: the first local mutation writes 19 with a pending
    publication on the 18 base; reload recognizes the local successor; publication replay matches the remote 18
    digest and publishes snapshot 3; snapshot 2's `snapshot_id`, the 18 file digest and the base are unchanged.
  - Finalizer-recovery fixture, snapshot 2 / frontier 18, parameterized for `clean-finalizer` and
    `ready-readback`: complete recovery writes 19 with one pending publication whose base is the exact v18
    publication base; reload through the default loader before publication keeps the Change available;
    publication replay publishes snapshot 3; snapshot 2's `snapshot_id`, the 18 file digest and every recovery,
    custody and nested receipt identity are unchanged. With frontier 19, recovery records no marker.
  - Drained acknowledgment: remote snapshot 2 holds the v18 frontier without the published checkpoint; local
    v18 retains it. `acknowledge_checkpoint_publication` writes 19 with one marker whose base equals the remote
    frontier digest; reload through the default loader keeps the Change available; replay with the real
    local-bare-remote publisher publishes snapshot 3 once; a second replay adds no snapshot commit and leaves
    no pending marker. A stored-19 acknowledgment records no marker.
  - Block with a request scoped to one criterion version and procedure (kind `confirm-check`); MCP `answer`
    through `Client(assemble_target_server(...))` with an `elicitation_callback` that accepts `passed`,
    parameterized for both routes (P16): `mode="legacy"` (the callback receives a mid-call
    `elicitation/create`) and `mode="2026-07-28"` (the first round returns `InputRequiredResult`, the
    client retries with the answer and the sealed state). Each → one ledger entry (channel `mcp-elicitation`,
    naming the request's consent generation, whose rendering its question digest covers) and the resolved
    request with its `confirmation_id`, and the generation `answered` `accepted`, in one transaction;
    reacquire; submit a `human-confirmed` result citing it; promote
    (requests cleared as today); reload: the ledger entry is byte-identical and appears in `semantics`;
    finalization with carried evidence and no new observation succeeds.
  - Registration (D13): the assembled server's `answer` input schema holds no injected parameter name, the
    registered tool has a context or resolved parameter for it, and every other tool's input schema equals
    its pre-N03 golden; an unscoped `answer` on either route asks nothing and behaves as today.
  - Restart before publication with an unpublished scoped answer, parameterized for a same-task Builder
    pause and a same-outcome Planner pause (retained handoff; the snapshot holds neither the answer nor the
    entry): the accepted answer writes the ledger entry and a schema-2 request-resolution receipt binding
    it in one transaction; restart through the default loader before any publication → the Change is
    available and its ledger byte-identical. Variants with lifecycle receipts around the answer: defer and
    resume before the answer (their frontiers lack the entry), defer after it (its frontiers hold it), and
    both; each reloads, and the after-answer receipt anchors to the resolved baseline. Then a fresh claim
    acquires and a restart still reloads. Then publication writes snapshot 3 with the entry, and a fresh
    host (empty runtime, only the published snapshot and the remote) restores frontier and ledger
    byte-identically; `resolve_confirmation` returns the entry and a `human-confirmed` result citing it
    promotes.
  - Ledger survival: after the confirmation above, `_reset_binding` of that outcome and a request moved out of
    the active binding leave `confirmations` byte-identical; `resolve_confirmation` still returns the entry;
    the frontier restored from its published snapshot carries it.
  - Defer a passive v18 handoff over a v18 snapshot, parameterized for a same-task Builder handoff and a
    same-outcome Planner handoff (Builder return to Planning, no Planner claim): the schema-2 intent receipt's
    `before_frontier_digest` equals the sha256 of the v18 file bytes and `after_frontier` is 19; reload accepts
    the local successor; a following resume (19 → 19) also reloads; receipt IDs are unchanged on replay.
  - `show_finalization_context` with `semantics` at exactly `FINALIZATION_SEMANTICS_MAX_BYTES` (budget patched to
    the fixture's measured size) returns it complete with `basis_digest`; finalization succeeds.
  - A registered MCP `finalize_change` refusal returns `ERR_DELIVERY_ACCEPTANCE_EVIDENCE` with the exact
    bounded `gaps` of the core error.
  - `delivery-migrate` `format-1-to-2` on a disposable D03-format portfolio with passive Builder handoff,
    Planner pause, report-backed Finalizer attention and a completed Change: only the marker changes; every
    Change is available afterwards and every stored digest is unchanged.
- **Negative scenarios:**
  - Unprefixed first admission → `acceptance-identity-required`; mixed, duplicate and near-miss items → their
    compiler diagnostics.
  - Result with a `failed` command, a schema-1 observation, an unknown `AC-` ID, a stale version, or a
    `confirmation_id` absent from the ledger → `ERR_DELIVERY_ACCEPTANCE_EVIDENCE` with the named reason;
    frontier bytes unchanged.
  - A ledger confirmation for another outcome, another criterion or version, or another procedure, or a
    `confirm-check` decision `failed` cited by a `passed` observation → `confirmation-not-applicable`;
    frontier bytes unchanged.
  - Fabricated confirmation (R14), on both routes: the agent calls MCP `answer` on a scoped request with
    `resolution.provenance: user-confirmed` and a selected option, through a client that declares no
    elicitation → `ERR_DELIVERY_CONFIRMATION` `channel-unavailable`; through a legacy session without a
    back-channel → `channel-unavailable`; through a client that declares it but declines, and again
    cancels → `declined`. A caller argument named like the injected parameter → `ERR_TARGET_PARAM_VALIDATION`.
    Each: no ledger entry, request unresolved, frontier bytes unchanged; after a decline or cancel the
    request's consent generation is `answered` `declined` or `cancelled`, otherwise none exists. Cockpit
    HTTP `answer_request` with
    `provenance: user-confirmed` on a scoped request → `409`,
    nothing written. A block request created with `applies_to` and a pre-filled `resolution` → rejected at
    validation. `submit_result` with a `waived` or `human-confirmed` record citing a request resolved
    through the old caller-provenance route (fixture written directly) → `confirmation-unresolved`.
  - Request-state boundary (modern route, P16), each through the assembled server with the client driving
    rounds manually (`allow_input_required=True`): a forged or bit-flipped `request_state`; a state minted
    for request A replayed on request B, or with another `expected_frontier_digest`; a state from a second
    assembled server (foreign key); a state past its TTL (clock advanced); a state minted before the server
    was re-assembled (restart) → JSON-RPC `INVALID_PARAMS` "Invalid or expired requestState" before the
    resolver or handler runs: no ledger entry, request unresolved, frontier bytes and any generation
    unchanged. A following
    fresh call asks the user again, and accepting then records exactly one entry. A valid state whose
    answer was given for a different rendering (the frontier advanced between rounds) → the existing
    frontier conflict; only the generation is written (`refused` `frontier-changed`), and re-sending the
    round returns the same refusal.
  - Single use (D13 *Single use*, I11), modern route through the assembled server; each re-send is a raw
    `tools/call` within the TTL carrying a captured round's `request_state`:
    (1) the accepted round's state and responses right after the answer applied, and (2) after a later
    unrelated frontier write → no elicitation; the original resolution and ledger entry returned; ledger
    length and frontier bytes unchanged.
    (3) Decline → affirmative: after a declined round, re-send its state with substituted `input_responses`
    that accept (`waive` on a `waive` request; `passed` on a `confirm-check` request) → `declined`; no
    ledger entry, request unresolved, frontier bytes unchanged, generation still `declined`.
    (4) Cancel → affirmative: the same after a cancelled round → `declined`, generation still `cancelled`,
    nothing else written.
    (5) After (3) or (4), a new `answer` call renders a fresh generation (new `generation_id` and question
    digest); the old state re-sent with an accept is re-asked by the SDK and never applied; accepting the
    new question records exactly one entry naming the new generation.
    (6) Concurrent competing responses on one `open` generation: a declining and an accepting
    continuation round, both orders forced through a barrier on the owning lock → exactly one
    disposition; the loser returns it; a ledger entry exists only when the accept won; a later re-send of
    either round returns the same disposition.
    (7) Two concurrent rounds carrying the same accepted answer → one ledger entry; the other returns it.
    (8) A fresh call on the resolved request → no question, the original resolution returned, no second
    entry.
    (9) A continuation round whose subject has no generation (fixture), or whose latest generation has
    another binding → `question-closed`; nothing written.
    (10) Crash injected before the accepting transaction commits → the generation stays `open`; re-sending
    that answer applies it once while request and frontier still match, and a further re-send returns it.
    Legacy route: a decline, then the same call again → a new generation and a new question; the
    declined one stays `declined`.
  - Replay tamper (§1.7 L row): a local ledger entry no schema-2 receipt binds, a receipt-bound entry
    absent locally or differing in one byte, a schema-1 receipt for a scoped answer, two entries reordered,
    or a lifecycle receipt anchored before the answer whose frontier holds the entry → the existing
    bootstrap failure; the Change is unavailable and nothing is rehashed.
  - Declined waiver: the user answers a `waive` request with `keep-required` → the request is resolved with
    that recorded decision; a `waived` record citing it → `confirmation-not-applicable`, both in a task
    result and in the finalization request; finalization with that criterion otherwise uncovered →
    refused `uncovered`; no receipt.
  - Append-only ledger (I10): a frontier write that drops, reorders or alters a ledger entry → refused before
    any byte write; a stored frontier whose ledger entry fails its digest → the Change is unavailable (V20);
    the 257th confirmation → `ledger-full`; only the generation is written (`refused` `ledger-full`), and
    re-sending that answer refuses `ledger-full` again.
  - Keep a valid finalization review and replace one otherwise-valid observation (or add, drop or reorder
    one) → `review-observations-mismatch`; no receipt, no report, frontier bytes unchanged.
  - Finalization with one criterion uncovered (all task checks pass: the #222 mechanical case), one whose last
    record is `missing`, one only legacy-evidenced, a failed or schema-1 request observation, an
    expected-failure observation whose exit differs, a review without basis, a stale basis (a task result, the
    target sync or the head changed between context and finalize), no diff base, or zero observations while a
    criterion is uncovered → refused with typed gaps; no
    receipt, no retry-ledger success, no checkpoint.
  - A `waived` record whose `confirmation_id` is not in the ledger, or whose confirmation is scoped to another
    outcome, criterion, version or procedure → `confirmation-unresolved` or `confirmation-not-applicable`;
    frontier bytes unchanged (U1(b)). The same record in a finalization request → refused with the same
    reason; no receipt.
  - A schema-2 handoff intent receipt whose frontiers also differ in a field outside the action's set → rejected;
    a schema-1 intent receipt embedding a 19 frontier → rejected. On reload, for both the Builder and the Planner
    handoff parameter, a receipt whose normalized `before_frontier` or `after_frontier` differs from its baseline
    in any non-version field → the existing lifecycle bootstrap failure; the Change is unavailable.
  - Oversized context: the same fixture at budget + 1 byte, and one unpatched synthetic Change whose task
    `constraints` exceed 256 KiB → `show_finalization_context` returns `semantics_refusal`
    `finalization-context-oversized` with exact `measured_bytes` and no `semantics` or `basis_digest`; then
    `finalize_change` with a recomputed basis → refused with that gap; no receipt, no report, frontier bytes
    unchanged.
  - Corruption (V20): a schema-2 observation whose `observation_id` does not match; a frontier 18 containing a
    schema-2 observation; a schema-1 embedding receipt containing N03 content; a schema-2 finalization holding
    a schema-2 observation → rejected at parse; the Change is unavailable with its existing diagnostic and is
    never rehashed.
  - Downgrade: the predecessor release refuses format 2, frontier 19, snapshot 3 with typed version
    diagnostics and unchanged tree hashes; a remote snapshot 4 → `remote-state-version-unsupported`.
  - Crash (V21, through N02-B's parameterized harness): after backup, before and after the marker, before
    `verified` → restart refuses `state-migration-incomplete`; `resume` converges; `abort` before the marker
    restores; finalize crash after transaction commit → exact replay returns the stored receipt; replay with a
    different observation set → conflict.
- **Inner loop:**
  `uv run pytest serve/delivery/tests/test_acceptance_criteria.py serve/delivery/tests/test_evidence.py -q`,
  then `uv run pytest serve/delivery/tests/test_delivery_runtime.py -q -k "finaliz or observation or result"`.
- **Closeout:** `uv run test --changed`; scoped `uv run ruff check` / `ruff format --check`;
  `uv run pytest tests/test_agent_ecosystem_validation.py tests/test_package_boundary.py -q` and
  `uv run pytest tests/test_cockpit_boundary.py tests/test_delivery_worktree_authority.py -q`;
  `npm run test:e2e:work` (seed changed).
- **LC:** full form with `delivery-lc`: the unmigrated copy is refused with `state-migration-required`; the copy
  migrates through every registered step from its observed format; the migrated copy lists and reads every
  Change as available; `acceptance_criteria` of each live contract and the classification of all 12 live
  observations as schema 1 are recorded; the predecessor release refuses the migrated copy; the candidate
  refuses a synthetic format 3; live record hashes unchanged.
- **Size / risk:** L / high. Persisted shapes in six versioned families, a migration, finalize semantics and
  fixture churn in about ten test files; the risk is an identity change in stored receipts, which I1 tests and
  the LC catch.

### 3.3 N03-B — Finalization semantics and proof procedures

- **Prerequisites:** N03-A.
- **Editable paths:** `share/skills/w-change-finalization/SKILL.md` (coverage plan from `semantics`; exact-head
  evidence only for criteria not covered by carried evidence, none when carried evidence covers all; stop and
  report `maintained-check-unavailable` for an uncovered criterion; on `semantics_refusal`
  `finalization-context-oversized`, stop before any proof and report `independent-review-unavailable`;
  dispatch the reviewer with `semantics`,
  `basis_digest`, `diff_base` and the final ordered observations); `share/agents/build-reviewer.agent.md`
  (finalization mode: assess the assembled promise, the task `exclusions`, `constraints` and
  `proof_boundaries` in `semantics`, preserved behavior and carried-evidence applicability, reading cited
  source at `change_head` only; finding boundary for an unmet promise or a violated exclusion);
  `share/agents/finalizer.agent.md`; `share/skills/w-packet-building/SKILL.md` and
  `share/agents/builder.agent.md` (`covers` from build context, expected-negative, when to record `missing`
  versus block; `applies_to` with kind `confirm-check` or `waive` on a request that asks the user, answered
  only through the chat elicitation; never set `provenance: user-confirmed` to confirm anything);
  `share/skills/w-frontier-planning/SKILL.md` and `share/agents/planner-challenger.agent.md`
  (tasks cite `AC-NNN` in `acceptance_observations`; plan covers every criterion);
  `share/agents/designer-challenger.agent.md` (identity check); `serve/delivery/README.md` (evidence model and
  trust boundary, R12); `tests/test_agent_ecosystem_validation.py`; this plan's row; execution plan status row.
- **Positive scenarios:** ecosystem tests pin each new procedure step; host rehearsal on a disposable portfolio
  with a real Finalizer and `build-reviewer`: (1) all criteria covered → schema-3 finalization; (2) one
  criterion without a procedure → engine refusal, then `maintained-check-unavailable` report and
  `proof-failed` settlement; (3) a seeded assembled defect where every criterion has passing evidence but the
  promise is unmet → reviewer `finding`, `independent-review-failed` report, `review-failed` settlement;
  (4) a candidate that passes every criterion but violates one explicit task exclusion → reviewer `finding`
  citing that exclusion; (5) all criteria covered by carried evidence → finalization with no new observation;
  (6) in real VS Code, a scoped `answer` shows the elicitation to the user; the model's transcript holds no
  answer control; accept records one ledger entry, decline records none; the evidence records the protocol
  VS Code negotiated and therefore which D13 route ran (G10).
- **Negative scenarios:** ecosystem tests fail when a skill reintroduces schema-1 construction, asserts a
  verdict for a command, lets an agent author `waived` or `human-confirmed` without a ledger confirmation or
  tells it to supply `provenance: user-confirmed` itself, or
  omits the basis or observation echo; the reviewer refuses a request without `semantics`; the Finalizer
  procedure continues after `finalization-context-oversized` or asks for a partial context.
- **Inner loop:** `uv run pytest tests/test_agent_ecosystem_validation.py -q`.
- **Closeout:** `uv run test --changed`; host rehearsal evidence on the PR.
- **LC:** not applicable (no loader, format or startup change).
- **Size / risk:** M / medium.

### 3.4 N03-C — Evidence projection

- **Prerequisites:** N03-B; [U2](#u2--which-clicks-and-answers-count-as-the-user-said-yes) answered. Under
  U2(b) or (d) N03-C keeps N03-A's Cockpit refusal. Under U2(a) it also edits `routes/target_work.py` to record
  a Cockpit channel confirmation behind the Origin and SameSite checks, with its negative scenarios; U2(c)
  first needs a plan revision for the native presence helper.
- **Editable paths:** `evidence.py` (projection); `work_items.py` (`WorkItemDetailView.evidence`,
  `WorkItemProjector`); `application_models.py` (`DeliveryChangeView.evidence`, `DeliveryOperatorContext.evidence`);
  `portfolio_application.py` (`get_change`, `:1162`); `application_readiness.py` (`show_work_item_view`,
  `show_operator_context`); `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py`
  (`DeliveryOperatorContextResponse.evidence` and its `from_context` copy);
  `serve/delivery-mcp/tests/test_target_server.py`; `serve/cockpit/src/owlbear_cockpit/target_models.py`
  and `serve/cockpit/tests`; `serve/cockpit/web/src/api/workItems.ts`; `WorkItemDetail.tsx` (technical summary;
  a scoped request's kind, criteria and procedure: under U2(b) or (d) read-only with a link to the chat that
  asks it, under U2(a) or (c) beside a Cockpit confirmation control)
  with its component test; E2E seed and the work-portfolio spec; `tests/test_cockpit_boundary.py` (parity for
  status, verdict, identity source and finalization rules); `application_support.py` (`_checkpoint_summary`:
  the PR body names each `waived` criterion, U1(b)); this plan's row; execution plan status row.
- **Positive scenarios:** one disposable Change shows the same statuses through `get_change`, MCP `get_change`,
  registered MCP `show_operator_context` (`evidence`), HTTP detail and the Cockpit summary (covered, missing with
  owner, waived, uncovered), and the PR body names the waived criterion (U1(b)); a legacy Change shows
  `unknown` and its schema-1 observations as unattributed; a finalized
  Change derives statuses from its schema-3 receipt; outcome items show only their criteria.
- **Negative scenarios:** an unavailable Change keeps its existing unavailable view; more than 16 records per
  criterion truncate with a count; locators render as text, never as links; a projection read leaves the tree
  hash unchanged; TypeScript and Python unions disagree → parity test fails.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_evidence.py serve/delivery/tests/test_work_items.py -q`;
  `npm test -- WorkItemDetail`.
- **Closeout:** `uv run test --changed`; `npm test`; `npm run build`; Biome on changed files;
  `npm run test:e2e:work`; package closeout: full `uv run test` once and a cumulative Sol challenge of the N03
  diff against this plan.
- **LC:** full form (live stays below format 2 until N10-M); also record the projection for every live Change.
- **Size / risk:** M / medium.

### 3.5 Required execution-plan deltas

Applied in this PR's execution-plan edits (D11).

1. §5 N03 phases: N03-A also owns the finalization semantic context (including bounded task authority),
   basis digest, review observation binding and receipt-construction skill text; N03-B keeps the semantic
   procedures, proof guidance and host rehearsal (D8).
2. §5 N03 LC line: A full form; B not applicable; C full form.
3. §4.1 and §5 N03 size: L / high (version widening in six families, P8), not M / high.
4. §5 N03: existing frontiers stay `readable-legacy` 18 until their next normal mutation writes 19; no
   frontier rewrite migration (D3).
5. §2.6 and §7: PR #316 was merged (merge commit `364daf61`), so "product merged via PR #316" stays. Separately,
   the live record `delivery-action-readiness` is unfinished (Implementation, 4 of 5 results, schema-1
   evidence, no finalization; P1); add its disposition to N10-M beside `frontier-serialization-contract`.
6. §4.4: N03-P row on merge. §4.2 (PR #360 round 4, from N05 plan F11): N05-B also needs N03-A for the
   shared `consent_generation` family (D13 *Single use*); the format-marker note orders N05-B after N03-A.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N03-P | #349 | — | Probes P1–P16 | Sol round 1: revision-required (observation binding, stored-byte upcast contract, confirmation applicability, bounded exclusions context, all-carried path) → revised; Sol round 2: revision-required (snapshot consumer serialization, confirmation retention through promotion, upgraded handoff receipt contract, MCP output owners) → revised; Sol round 3: revision-required (Planner lifecycle normalization, context budget) → consolidated comparison inventory; Sol round 4: revision-required (representation-only write publication) → revised; Sol round 5: revision-required (drained acknowledgment base) → revised; Sol round 6: `plan-sound`; user-decision revision #360: Sol round 1: revision-required (fabricated confirmation, Finalizer waiver admissibility, confirmation authority across revision) → confirmation boundary D13, ledger, U2 opened; Sol round 2: revision-required (elicitation route across protocols, ledger append missing from handoff replay, request-state premise) → D13 legacy and modern routes with registration (P16), receipt-bound ledger replay (L row), SDK boundary instead of a MAC; U2 widened to merge approval and retirement; Sol round 3: revision-required (renewed consent replayable within the request-state TTL, U2 applicability and cost) → D13 *Single use* (frontier as generation for scoped requests; N05 D14 generation record), U2 restated; N06 D3 cross-plan note applied (no `interaction` channel or locator); Sol round 4: revision-required (a declined or cancelled question stayed replayable with an affirmative answer) → one shared single-use consent generation (`consent_generation`, D13 *Single use*, I11) consumed by every answer, used by N03, N04, N05 and N06; N05-B now needs N03-A | approved (D11 confirmed 2026-10-03; U1 decided (b) 2026-10-03; U2 open before N03-C and N05-C) |
| N03-A | #363 | `8e2faf3cd` | Own runs (macOS, Python 3.14.8, mcp 2.3.0): new `test_acceptance_criteria`, `test_evidence`, `test_consent_generation` 49 passed; `test_evidence_runtime` 18 passed (inadmissible results refused byte-unchanged; #222 uncovered refusal; carried + exact-head finalization and replay; zero-observation finalization with full carried coverage; review mode/basis/observation-ID, missing and failed gaps; no diff base; v18 reads keep bytes and the first mutation stores 19; I10 prefix guard); MCP `test_confirmation_boundary` 14 passed through `Client(assemble_target_server(...))` on `legacy` and `2026-07-28` (accept records one ledger entry and an `accepted` generation, replay asks nothing; decline/cancel write only the generation; no elicitation capability → `channel-unavailable`; injected `confirmation` argument → `ERR_TARGET_PARAM_VALIDATION`, absent from the input schema; `keep-required` recorded and non-affirmative; a declined question is never reopened, a new call asks a new generation; a registered `finalize_change` refusal returns `ERR_DELIVERY_ACCEPTANCE_EVIDENCE` with the exact bounded `gaps`); Cockpit scoped answer → 409, nothing written; `test_state_migration` adds format 1 → 2 marker-only with every Change available; diagnostics 141 passed; ecosystem/package/cockpit-boundary/worktree-authority/module-structure 170 passed; `test --changed --base origin/dev` (one run, on `b152c5b9e`): 3513 collected, 3509 passed, 4 failed on stale version or fixture expectations (`test_target_server` newer-state frontier 19 → 20; `test_delivery_lc` pretty frontier now 19 because a stored 18 is never rewritten by reads, and the previous-gate format; work-item acceptance text with its `AC-001:` prefix), fixed in the head and rerun alone: 95 passed; Vitest 25 files, 361 passed. `npm run test:e2e:work` (seed changed): 18 passed, 1 failed, 8 not run (serial) twice; the failure is a Playwright teardown race (`route.fetch: Test ended` in the `/api/work-items` route) on `completed history detail closes with its Close button`, which passes alone, as do the 8 tests it skipped. LC full form (`delivery-lc`, `ubuntu:24.04`, candidate `c9faf5200`, previous `bff93d73e`): pass — unmigrated copy refused `state-migration-required`; migration 0 → 2 (3 `coordination_1_to_2` rewrites + marker); all 3 Changes load; predecessor refuses the migrated copy `state-newer-than-controller`; synthetic format 3 refused; `compare`: 132 live records unchanged. Live facts on the copy: `delivery-action-readiness` 17 authored `AC-` criteria, `frontier-serialization-contract` 7 and `macos-managed-browser-authentication` 12 legacy-position; all 12 live observations schema 1; frontiers stay 18. Fixes found by these runs: application clock passed as a string to consent records; schema-1 handoff-intent receipts compared a normalized before-frontier with an un-normalized after-frontier (golden D03 receipt); inspector locator for `consent_generation`. Completion round (code head `c97a0eb1f`, same toolchain; real owners, no mocks above the behavior): MCP `test_confirmation_single_use` 28 passed on the assembled server (SDK request-state boundary: forged, other request, other frontier, foreign key, expired by clock and pre-restart states → `INVALID_PARAMS` before any resolver or handler, generations and frontier unchanged, a fresh call then records one entry; frontier advanced between rounds → `refused` `frontier-changed`, re-send refuses again; single use (1)–(10): accepted round re-sent immediately and after an unrelated write, with a substituted answer and as a fresh call, returns the original resolution and writes nothing; decline/cancel → affirmative replay on `waive` and `confirm-check` stays `declined`/`cancelled`, the stale state is re-asked by the SDK, a new call renders a new generation that alone applies; competing decline/accept forced through a barrier on the owning lock, both orders, and two identical acceptances record exactly one disposition; no generation or a foreign binding → `question-closed`; a crash after the generation write re-asks the same open generation; an accepted answer whose transaction never committed applies once while request and frontier match and is refused `frontier-changed` after a write; 256-entry ledger → the 257th answer is `refused` `ledger-full` on both routes, re-sent and newly asked it refuses again); MCP `test_confirmation_restart` 17 passed through the default loader (scoped Builder same-task and Planner same-outcome answers with no, before, after and both defer/resume receipts: restart before publication keeps the ledger byte-identical, a fresh claim acquires, `submit_result` with a `human-confirmed` record citing the entry promotes and publishes snapshot 3 holding it, a fresh host restores it and `resolve_confirmation` returns it; tamper: an unbound entry, a missing entry, an altered entry, a schema-1 receipt and two reordered Planner entries leave the Change unavailable with files unchanged); stored-byte rows: v18 first mutation records one marker on the v18 base, reloads and replays snapshot 3 once with snapshot 2 as parent; drained acknowledgment records a marker on the published projection for 18 and none for 19; clean-finalizer recovery of a stored 18 records one marker on its published base and replays once (19: none), reopened in process; deferring a passive v18 Builder or Planner handoff over a snapshot 2 binds the stored bytes and reloads, as does the 19 → 19 resume; stranded-frontier repair writes 19 from a stored 17 or 18; a real 256 KiB task-constraint Change refuses `semantics` whole with exact `measured_bytes` and `finalize_change` with a recomputed basis refuses `finalization-context-oversized`. Defect fixed with a failing test first: the confirmation resolver turned any application exception into `confirmation-required`; typed Delivery failures now keep their own code and unexpected ones propagate as MCP internal errors, logged by the SDK. Focused 182 passed; `test --changed --base origin/dev` (one run, on `c97a0eb1f`): 3570 passed in 10 min 12 s, Vitest 25 files, 361 passed; ruff check and format clean. `test:e2e:work`: the same `route.fetch: Test ended` failure occurs on a clean `origin/dev` `bff93d73e` worktree (1 of 3 full runs there, 3 of 3 here; same test, same in-flight `/api/work-items` route at test end), so it is a pre-existing teardown race, not an N03-A defect; `/api/work-items` payload shape and latency (≈75 ms) match dev. Not assembled: the ready-readback recovery variant (a pre-N03 finalized Change needs a schema-2 finalization the current owners cannot write) and a lifecycle receipt anchored before the answer whose frontier holds the entry. Round 1 repair (code head `8e2faf3cd`), each fix with a test failing on `727f73df1` first (temporary worktree): (1) an accepted answer that the lifecycle or custody re-check refuses (Change deferred, completed, abandoned or under attention, an active claim, Finalizer custody or a pending Pause) now consumes its generation as `refused` with code `change-deferred`, `change-completed`, `change-abandoned`, `change-attention`, `claim-active`, `custody-conflict` or `request-invalid` under the owning lock, and a re-sent answer returns the same typed refusal; transaction conflicts and I/O failures still leave it `open` (`test_an_accepted_answer_the_lifecycle_recheck_refuses_consumes_its_generation` on both routes, `test_resending_an_answer_the_lifecycle_recheck_refused_returns_the_same_refusal`); this widens the D13 *Consumption* refusal codes beyond `frontier-changed`, `request-closed` and `ledger-full`; (2) `FORMAT_MIGRATIONS` registers `format-0-to-1` (N02-B) and `format-1-to-2`, proposals bind their ordered `steps` in the migration identity, a format-0 copy lists both, a format-1 copy lists `format-1-to-2`, and the CLI and LC report show them; (3) finalization `semantics.confirmations` also lists every ledger confirmation that `confirmation_applies` admits for an exact-head record (current criterion versions of its outcome, its procedure, an affirmative decision), and `w-change-finalization` Step 2 says so (`test_finalizer_waiver_cites_an_applicable_ledger_confirmation_that_no_task_result_cites`; a `keep-required` entry stays unlisted). Gate proofs: `test_v18_finalizer_recovery_reloads_through_the_default_loader_and_republishes_once[clean-finalizer, ready-readback]` (loader workspace; the D03 frontier holds results and a schema-2 finalization rebuilt from the retained legacy models and is validated as schema 18, the ready receipt model is unchanged by N03; recovery writes 19 with one marker on the snapshot-2 base, `load_delivery_application` reloads it available, replay publishes snapshot 3 once with snapshot 2 as parent, a second load converges; recovery records and nested receipt IDs unchanged) and `test_lifecycle_receipts_anchored_before_the_answer_that_hold_its_entry_leave_the_change_unavailable[builder, planner]` (an identity-valid rebuild of the lifecycle chain reproduces it byte for byte; adding the entry leaves the Change unavailable and unrehashed). Focused 545 passed; `test --changed --base origin/dev` (one run, on `8e2faf3cd`): 3578 passed in 705.9 s, Vitest 25 files, 361 passed; ruff check and format clean. LC full form on `8e2faf3cd`, previous `bff93d73e`: passed; the unmigrated copy refuses `state-migration-required` with hashes unchanged; the proposal from format 0 lists `format-0-to-1`, `format-1-to-2` and migrates the marker and three coordination records; applied, verified; the migrated copy loads all three Changes available; the previous release refuses the format-2 marker; the synthetic format 3 is refused; `compare` reports all 132 live records unchanged; 12 live observations, all schema 1; live frontiers 18 | Sol implementation round 1: `repair-required` (refused answers left the generation open; format 0 skipped the registered step sequence; uncited ledger confirmations unusable by the Finalizer) → repaired | implemented; awaiting review |
| N03-B | — | — | — | — | — |
| N03-C | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | N02-B's registry, gate and `delivery-migrate` accept identity `readable-legacy` entries for a mutable family and a marker-only migration | N02-A/B are not implemented | N02 plan §1.4–1.5, D3, D5 | N03-A (re-check at start; a divergence stops for a plan revision) | N03-A start |
| G2 | Widening validators reject N03 content in every old-version instance | Prototype covered observation and review only | P3, P6 | N03-A tests | N03-A merge |
| G3 | P8 lists every family whose fingerprint changes | Static scan; N02-A's fingerprint test is the authority | P8 | N03-A | N03-A merge |
| G4 | A real reviewer detects an assembled-but-wrong Change from the shared basis | Semantic judgment; not provable by fixtures | Mechanical uncovered case automated in N03-A | N03-B host rehearsal | N03-B merge |
| G5 | Human confirmation beyond MCP elicitation | A Cockpit channel needs U2 | N06 links prepared interactions to ordinary scoped `confirm-check` requests answered through `answer`, with no new channel or locator (N06 D3); `channel` gains `cockpit` only under U2 | U2 | Nothing in N03-A or N03-B |
| G6 | Evidence reuse after revision | Applicability is N04 | §1.4 survival rules | N04 | Nothing in N03 |
| G7 | Live `delivery-action-readiness` can finalize | Its product merged via PR #316 (`364daf61`), but the record is unfinished: 10 schema-1 observations are `unknown`; 17 criteria need typed evidence | P1 | N10-M disposition | N10-M |
| G8 | LC runs in CI | Needs Docker and a live copy | `delivery-lc` unit tests (N02-B) | Each phase | Nothing (recorded per phase) |
| G9 | The unadmitted live draft `interactive-browser-tools` (23 unprefixed criteria) can be admitted | First admission now requires `AC-NNN:` prefixes, a package change the user re-approves | P4 | Its Designer session after the programme | Nothing in N03 |
| G10 | VS Code renders Delivery's elicitation to the user and never answers it automatically or through the model, on the route it negotiates (legacy `elicitation/create` or modern `InputRequiredResult`) | Host behavior; the SDK warns an agent client may answer itself (P15); no host run in P | P15, P16; D13 typed refusal without the capability; both routes covered by in-process client tests (N03-A) | N03-B host rehearsal step (6) | N03-B merge; without it waivers, human-confirmed evidence and N05 merge approval through chat stay unavailable (merges then happen in GitHub, N05 R4) |
| G11 | Whether a Cockpit click counts as user-only for waivers, human-confirmed checks, merge approval and retirement | Open user decision | [U2](#u2--which-clicks-and-answers-count-as-the-user-said-yes) | User | N03-C start; N05-C start |
