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
> PR #360 (rounds 1–4) added a user-only confirmation boundary over MCP elicitation, a confirmation
> ledger and single-use consent generations, and opened U2. **Simplification 2026-10-04** (lead
> decision, [execution plan §7](delivery-redesign-execution-plan.md#7-decisions)): that machinery is
> removed. A waiver or human confirmation cites a scoped request that the user resolved in Cockpit,
> by `request_id`, as before #360; MCP `answer` refuses such requests (D13); U2 is resolved. Reviews
> work in the execution plan's [operating context](delivery-redesign-execution-plan.md#19-operating-context).

## 1. Contract

### 1.1 Result

- Every new proof observation carries a typed result whose verdict is derived, never asserted: `passed`,
  `expected-negative`, `failed`, `missing` (with an owner) or `waived` (owner user, citing the user's
  affirmative Cockpit answer to a request bound to the criterion version (D13); it satisfies
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
| R14 | Waivers and `human-confirmed` evidence cite a scoped request that the user resolved in Cockpit with the affirmative option; agents' MCP `answer` cannot resolve such a request; a negative answer confirms nothing | U7; V16; execution plan §7 (2026-10-04) |

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
- **I6 Applicable confirmation.** `human-confirmed` provenance and `waived` results cite a
  `request_id` that the engine resolves to a request of the same Change and outcome
  (§1.5): resolved with `provenance: user-confirmed` and the affirmative option for its use (`waive` for
  `waived`; the observation's assessment for `human-confirmed`), and with an `applies_to` scope naming
  every criterion version the observation covers and its exact `procedure`. Existence of some confirmed
  request is not enough; a `keep-required` answer waives nothing. Nothing synthesizes one (V20). A
  `waived` record with an applicable confirmation satisfies finalization for that criterion version,
  from a task result or the finalization request, and stays shown as `waived` (U1(b)); agents and
  reviewers never waive.
- **I7 One evaluator.** One pure function computes coverage for `finalize_change`, the finalization context
  and the projection; identical inputs give identical statuses.
- **I8 Bounded and non-sensitive.** Locators use an allowlisted `scheme:value` form, never URLs; free text is
  length-bounded; projections cap evidence per criterion. The finalization context is all-or-nothing within one
  byte budget (§1.8); obligations are never truncated.
- **I9 Gate first.** N02 I1 and I5 unchanged; N03 adds format marker 2 and the widened versions to the registry.

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
| Survival across revision (consumed by N04) | Same `acceptance_id` and same version: the same criterion; its evidence still covers it. Same ID, new version: the same criterion revised; prior evidence does not cover it and it is replanned. New ID: a new criterion with no evidence. Removed ID: retired; never reused for another obligation. Legacy → authored: matched by version only |
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
| `procedure_registration_digest` | sha256 or null | Registered procedure identity (`MaintainedProofProcedure.registration_digest`) |
| `result` | union on `kind` (below) | Typed result |
| `covers` | ≤ 32 unique `DeliveryAcceptanceRef{acceptance_id, acceptance_version}` | Criteria this observation is evidence for; may be empty (supporting check) |
| `environment` | `platform`: `macos`, `linux` or null; `labels`: ≤ 8, each matching `^[a-z0-9][a-z0-9.+_-]{0,63}(:[A-Za-z0-9.+_-]{1,64})?$` | Environment constraints that bound applicability |
| `target_class` | null or `^[a-z0-9][a-z0-9-]{0,63}$` | Class of external target (`sharepoint`, `confluence`), never a hostname |
| `provenance` | `machine-observed` or `human-confirmed` | Who established the result |
| `request_id` | null or request ID | Required for `human-confirmed` and for `waived`; resolved and scope-checked by the engine (I6) |
| `locator` | null or ≤ 256 chars of `scheme:value`; scheme `path`, `ci-run`, `check-run`, `request` or `report`; no whitespace, no `://`, no `..` segment | Retained non-sensitive locator |
| `summary` | null or ≤ 240 chars | Non-authoritative note (`171 passed`) |
| `observation_id` (receipt) | sha256 | `_receipt_digest` over all other fields; `create` copies fields by attribute (P3 finding) |

| `result.kind` | Kind fields | Verdict |
| --- | --- | --- |
| `command` | `exit_status` −255…255; `expectation` `success` or `expected-failure`; `expected_exit_status` nonzero, required iff expected-failure | `passed` iff success and 0; `expected-negative` iff expected-failure and exit = expected; otherwise `failed` |
| `manual-procedure` | `assessment` `passed` or `failed` | The assessment; `human-confirmed` allowed |
| `artifact` | `assessment` `passed` or `failed`; `artifact_digest` sha256 or null; `locator` required | The assessment; `human-confirmed` allowed |
| `missing` | `owner` `agent`, `user`, `provider` or `assisted-check`; `reason` 1–240 chars | `missing` |
| `waived` | `owner: user`; `reason` 1–240 chars; observation `request_id` required | `waived`; with an applicable confirmation (I6) it satisfies finalization coverage and stays shown as `waived` ([U1](#u1--may-a-user-waive-a-required-acceptance-criterion)(b)) |

**Proof and admissible waivers.** Proof verdicts: `passed`, `expected-negative`. A satisfying record is a
proof verdict or a `waived` record with an applicable confirmation (I6). Both complete a criterion's coverage
wherever they appear, in a task result or in the finalization request (U1(b), §1.6); proof is shown as
`covered`, a waiver as `waived`. `missing` and `failed` never satisfy.

**Confirmation scope.** `DeliveryRequest` gains optional `applies_to: DeliveryConfirmationScope{kind:
"waive" | "confirm-check", acceptance: 1–32 unique DeliveryAcceptanceRef, procedure: 1–512 chars}`
(`exclude_if` None); its options are `waive` and `keep-required`, or `passed` and `failed`. The
requesting worker sets it on the existing request-bearing block route; a scoped request cannot carry a
`resolution` when it is created. The user answers it in Cockpit (D13), and the resolution is recorded
with provenance as today. A request without scope confirms nothing. The engine checks structure, not
the worker's honesty (R12).

**Retention.** A resolved request with `applies_to` is a scoped confirmation. Planning and
Implementation promotion (`_advance`) keep scoped confirmations in `binding.requests` and clear only the
rest (today all are cleared). The evaluator, `semantics` and the projection read them from the frontier
through one pure function, `confirmation_applies(frontier, observation, outcome_id)` in `evidence.py`,
which returns the I6 gap reason or None. `_DeliveryBuilderPlanPromotionReceipt` schema 2 expects the
same retained set (schema 1 keeps `()`); loader successor reconstruction and recovery's block-successor
check (`_is_repairable_frontier_successor`) treat retained confirmations as prior state. `_reset_binding`
still clears them with the results they supported.

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
| nested `DeliveryRequest` | `applies_to` (`exclude_if` None) | Covered by the frontier, snapshot and receipt widening | Unchanged | — |
| `planning_*`, `builder_*` receipts embedding bindings, frontiers or requests | `_DeliveryPlanningRetrySettlementReceipt`, `_DeliveryBuilderInvocationSettlementReceipt`, `_DeliveryBuilderPlanPromotionReceipt`, `_DeliveryBuilderHandoffChangeIntentReceipt`, `_DeliveryPlanningPauseReplay` (P8), `_DeliveryBuilderRequestResolutionReceipt` (P10) | 1 → widen 1, 2 | Unchanged; embedded frontiers keep 18 | none |
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
| Binding comparisons: `_planner_handoff_lifecycle_rank`, `_planner_handoff_pause_history`, `_planner_handoff_receipt_pause`, `_builder_handoff_settled_binding`, `_builder_request_resolution_successor`, `_validate_local_builder_plan_promotion`, `_promoted_builder_return_successor`, `_is_repairable_frontier_successor` (`application_recovery`), `_DeliveryBuilderPlanPromotionReceipt._validate_successor` (`runtime_receipts`) | loader, `application_recovery.py`, `runtime_receipts.py` | `OutcomeAuthorityBinding` equality | U (confirmation retention, §1.5) |
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

### 1.8 Interfaces and error cases

| Interface | Behavior |
| --- | --- |
| `owlbear_delivery.acceptance_criteria` (new leaf; imports `target_contract` only) | `acceptance_criteria(contract) -> tuple[DeliveryAcceptanceCriterion, …]`; `parse_acceptance_item(text)` returning the optional `acceptance_id` and the statement; `acceptance_version(statement)`; `DeliveryAcceptanceRef` |
| `owlbear_delivery.evidence` (new; imports models and `acceptance_criteria`, imported by runtime and application, never by `runtime_models`) | `evaluate_acceptance_evidence(contract, frontier, request_observations=()) -> DeliveryAcceptanceCoverage`; `confirmation_applies` (§1.5); `finalization_basis_digest(...)`; projection builder (N03-C) |
| `compile_delivery_contract` | Adds the three identity diagnostics; output bytes unchanged for valid input |
| `DeliveryAuthorityRegistry.admit` | First admission requires authored identities |
| `DeliveryRuntime.publish_result`, `DeliveryRuntime.finalize_change` | Enforce §1.6; on violation raise `DeliveryAcceptanceEvidenceError` (subclass of `DeliveryRuntimeConflictError`), code `ERR_DELIVERY_ACCEPTANCE_EVIDENCE`, `gaps` ≤ 64 × `{acceptance_id?, observation_id?, reason}`; reasons `uncovered`, `unknown-legacy-only`, `missing`, `failed`, `legacy-observation`, `unknown-acceptance`, `stale-acceptance-version`, `request-unresolved` (no such resolved scoped request), `request-not-applicable` (outcome, scope, procedure or option), `review-basis-missing`, `review-basis-stale`, `review-observations-mismatch`, `finalization-basis-unavailable`, `finalization-context-oversized` |
| MCP `answer` (N03-A) | For a request with `applies_to` (a waiver or person-only confirmation): refuses `ERR_DELIVERY_CONFIRMATION` before any write and says the user answers it in Cockpit (D13). Unscoped requests behave as today |
| Cockpit HTTP `answer_request` | Unchanged route; the user's answer to a scoped request is recorded with `provenance: user-confirmed` as today. N03-C shows the scope beside the answer controls |
| `show_finalization_context` | Adds `semantics: DeliveryFinalizationSemantics` and `semantics_refusal: DeliveryContextRefusal` (each `exclude_if` None; exactly one set whenever the context is otherwise available). `semantics` holds: contract digest and title; outcomes with promise, commitment and dependency IDs and criteria; commitments; task results (ID, title, commit, result digest, observation IDs); per promoted task its bound authority (`task_id`, `task_digest`, `result`, `constraints`, `exclusions`, `proof_boundaries`, `acceptance_observations`); confirmations cited by task evidence with their `applies_to` (retained, §1.5); `diff_base`; `change_head`; per-criterion coverage from task evidence; `basis_digest`. Task authority is bound by the result digests, which hold `task_digest`; the Design package is not included. Size: see the context budget below |
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

- **N04** consumes §1.4 identities and the evaluator, without applicability records (simplified
  2026-10-04): an observation still covers a criterion whose ID and version are unchanged; a changed
  criterion is uncovered and replanned. `_carry_forward_unresolved_binding` is untouched by N03.
  N04 keeps resolved scoped requests whose criterion versions are unchanged, so their confirmations still
  apply. For `(id, old version)` → `(id, new version)` a `waived` or `human-confirmed` record is
  `stale-acceptance-version`; person-only evidence for the changed criterion is asked again through a new
  scoped request answered in Cockpit.
- **N05** may show the projection counts in **Approve merge**; it adds no evidence semantics.
- **N08** renders N02 `CapabilityReport` rows for format 2 and the widened families.

### 1.10 Existing owners to reuse

`_receipt_digest` and the attribute-copy `create` pattern (`delivery_runtime.py:557-561`); `_omit_when_none`
(`delivery_runtime.py:158`); `DeliveryRequestResolution.provenance`; `validate_finalization_head` ancestry
(`change_workspace.py:5033-5036`); `FinalizationReportStore` and its existing codes; the N02 registry, gate,
`delivery-migrate` and `delivery-lc`; `Client(assemble_target_server(...))`, the Cockpit HTTP client and the
E2E stack.

### 1.11 Exclusions

Revision activation and evidence reuse after revision (N04); prepared interactions and private input (dropped
2026-10-04); a waiver path beyond [U1](#u1--may-a-user-waive-a-required-acceptance-criterion)(b) (no agent,
reviewer or unconfirmed waiver); claim IDs on
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
  frontier, snapshot and receipt widening already version. The user answers a scoped request in Cockpit
  (D13); its resolution is the confirmation, retained in the binding (§1.5).
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

Engineering decision by the lead (2026-10-04; replaces PR #360's D13, execution plan §7):

- **D13 Cockpit is where the user says yes.** In the execution plan's operating context agents are trusted
  but fallible, so the guard is against an honest mistake, not forgery. Agents' MCP tools do not offer
  user-only actions: MCP `answer` refuses a request with `applies_to` (a waiver or person-only
  confirmation) before any write, with `ERR_DELIVERY_CONFIRMATION` and the guidance to answer it in
  Cockpit; a scoped request cannot carry a `resolution` when it is created. The user answers in Cockpit,
  recorded with provenance as today. I6 then checks scope, criterion version, procedure and the affirmative
  option, which also catches an agent citing the wrong request. There is no elicitation, ledger, consent
  generation, Origin or cookie hardening or presence check. Digests prove content integrity only (R12).
  N05 merge approval follows the same rule (N05 D14).
- **D13 history.** PR #360 replaced caller provenance with MCP elicitation (P15, P16), a frontier
  confirmation ledger and single-use consent generations; that text is on PR #360.

#### U1 — May a user waive a required acceptance criterion?

Decided 2026-10-03: (b), by the user in chat after a full status-quo, problem, options and pro/con briefing
(required before N03-A starts). The answer changes one validator rule, one projection label and the PR
evidence text; N04-P plans against (b).

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
  waive, so (c) stays excluded. The user gives the waiver in Cockpit (D13).

#### U2 — Where does the user say yes?

Resolved 2026-10-04 by the lead ([execution plan §7](delivery-redesign-execution-plan.md#7-decisions)):
in Cockpit, for waivers, person-only confirmations and N05 merge approval. There is no enforcement beyond
the agent tool surface (D13). PR #360's options and briefing remain on that PR as history.

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

P15 and P16 (PR #360) probed MCP elicitation and the SDK request-state boundary for the D13 design that was
removed on 2026-10-04; their results remain on PR #360.

## 3. Phases

### 3.1 Shared rules

- **Layout.** Plans name symbols; re-resolve files with `grep` at phase start. N03-A requires N02-B, whose
  chain (N02-A ← N01-C ← N01-A, N01-B) guarantees the post-N01 layout: application methods in
  `application_*` mixins, workspace methods in `workspace_*`, runtime models in `runtime_models.py`, runtime
  receipts in `runtime_receipts.py`, and the 43 frontier writers (including `finalize_change`,
  `publish_result`) in the `delivery_runtime.py` facade (N01 I6).
- **Version numbering.** N05-B also bumps the format marker. Whichever of N03-A and N05-B merges second
  renumbers its versions and migration on rebase and reruns LC.
- **Ownership** (execution plan §1.6). Opus keeps models, versioning, migration registration, evaluator,
  finalize validation and challenge reconciliation. Luna may take
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
  - new `serve/delivery/src/owlbear_delivery/acceptance_criteria.py`, `evidence.py`
  - `target_contract.py`: `DeliveryCompilationDiagnosticCode`, `_parse_outcome` (`:354`), `_validate_definitions`
  - `delivery_admission.py`: `DeliveryAuthorityRegistry.admit` (`:183`)
  - `runtime_models.py` [N01-C]: observation, result, confirmation, environment and reference models;
    `DeliveryRequest.applies_to`, `DeliveryConfirmationScope`;
    `DeliveryReview`/`Receipt`, `DeliveryTaskResult`, `DeliveryFinalization`/`Receipt`, `DeliveryFrontier`,
    `FinalizeDeliveryChange`, `DeliveryAcceptanceEvidenceError`
  - `runtime_receipts.py` [N01-C]: the five embedding receipts of P8 and `_DeliveryBuilderRequestResolutionReceipt`
  - `delivery_runtime.py` facade: `DeliveryRuntime.publish_result`, `DeliveryRuntime.finalize_change`,
    `_read`, `_replace`, `_replace_content` (stored-byte contract, §1.7); `complete_recovery` and
    `acknowledge_checkpoint_publication` (P rows, §1.7); `frontier_bytes` and
    `publication_base_digest` wherever N01-C placed them (`runtime_reads.py` per N01 plan §3.6);
    `parse_delivery_frontier` wherever N02-A placed it
  - `runtime_reads.py` [N01-C]: `_advance` (confirmation retention, §1.5); `runtime_settlement.py` [N01-C]:
    handoff intent receipt construction (§1.7)
  - `delivery_state.py`: `DeliveryStateSnapshot`, `parse_delivery_state_snapshot`, snapshot version constants,
    `_same_snapshot_inputs`, `_portable_frontier`, `_snapshot_digest`
  - `delivery_application_loader.py`: snapshot restoration bytes and the S and N rows of the §1.7 inventory
  - `application_publication.py`: `_pending_publication_remote_head`, `_reconcile_pending_state_publication`
  - `application_recovery.py`: `_is_repairable_frontier_successor` (retained confirmations),
    `repair_stranded_frontier`; `repair_missing_request_provenance` beside `parse_delivery_frontier` (W row)
  - `state_formats.py` [N02-A/B]: §1.7 entries and migration `format-1-to-2`
  - `application_models.py`: `DeliveryFinalizationContext.semantics`, `.semantics_refusal`,
    `DeliveryFinalizationSemantics`, `DeliveryContextRefusal`,
    `DeliveryBuildContext.acceptance`, `DeliveryPlanContext.acceptance`
  - `application_lifecycle.py`: `show_finalization_context`, `_finalize_change_locked` (basis re-check under
    the checkpoint lock); `application_acquisition.py`: `show_plan_context`, `show_build_context`
  - `owlbear_delivery/__init__.py`; `serve/delivery/tests/fixtures/module_surface.json`; N02 fingerprint fixture
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py` (error code mapping, `_raise` carries `gaps`;
    `answer` refuses scoped requests with `ERR_DELIVERY_CONFIRMATION`, D13); `target_models.py`
    (`TargetDiagnostic.gaps`, ≤ 64, `exclude_if` None)
  - `serve/tools/src/owlbear_tools/delivery_diagnostics.py` (frontier 19, snapshot 3, receipts 2, marker 2)
  - tests: new `serve/delivery/tests/test_acceptance_criteria.py`, `test_evidence.py`; schema-2 fixtures in
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
  - A `human-confirmed` manual observation whose `request_id` names a request in the same
    outcome resolved through Cockpit HTTP `answer_request` with option `passed`, scoped to the covered
    criterion version and the observation's procedure, is accepted.
  - A task result with a `waived` record (owner user) whose `request_id` names a request
    resolved in Cockpit with option `waive`, scoped to that criterion version and the record's procedure,
    promotes; finalization with every other criterion covered succeeds and the evaluator shows that
    criterion `waived` (U1(b)).
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
  - Block with a request scoped to one criterion version and procedure (kind `confirm-check`); the user
    answers `passed` through Cockpit HTTP `answer_request`; reacquire; submit a `human-confirmed` result
    citing it; promote; reload: the confirmation stays in `binding.requests` and appears in `semantics`;
    finalization with carried evidence and no new observation succeeds.
  - Retention: after that confirmation, a restart before publication and a published snapshot restored on a
    fresh host keep the retained request byte-identical; `_reset_binding` of that outcome clears it with
    the results it supported.
  - An unscoped `answer` through MCP behaves as today.
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
    `request_id` naming an unresolved, unanswered or non-`user-confirmed` request →
    `ERR_DELIVERY_ACCEPTANCE_EVIDENCE` with the named reason; frontier bytes unchanged.
  - A confirmation citing a resolved request without scope, for another outcome, another criterion or
    version, or another procedure, or a `confirm-check` answered `failed` cited by a `passed` observation →
    `request-not-applicable`; frontier bytes unchanged.
  - Agent tool surface (D13): MCP `answer` on a scoped `waive` or `confirm-check` request, with or without a
    caller `resolution` → `ERR_DELIVERY_CONFIRMATION`, request unresolved, frontier bytes unchanged. A
    block request created with `applies_to` and a pre-filled `resolution` → rejected at validation.
  - Declined waiver: the user answers a `waive` request with `keep-required` in Cockpit → the request is
    resolved with that option; a `waived` record citing it → `request-not-applicable`, both in a task
    result and in the finalization request; finalization with that criterion otherwise uncovered →
    refused `uncovered`; no receipt.
  - Keep a valid finalization review and replace one otherwise-valid observation (or add, drop or reorder
    one) → `review-observations-mismatch`; no receipt, no report, frontier bytes unchanged.
  - Finalization with one criterion uncovered (all task checks pass: the #222 mechanical case), one whose last
    record is `missing`, one only legacy-evidenced, a failed or schema-1 request observation, an
    expected-failure observation whose exit differs, a review without basis, a stale basis (a task result, the
    target sync or the head changed between context and finalize), no diff base, or zero observations while a
    criterion is uncovered → refused with typed gaps; no
    receipt, no retry-ledger success, no checkpoint.
  - A `waived` record whose `request_id` names no resolved scoped request, or whose request is
    scoped to another outcome, criterion, version or procedure → `request-unresolved` or
    `request-not-applicable`; frontier bytes unchanged (U1(b)). The same record in a finalization
    request → refused with the same reason; no receipt.
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
  versus block; `applies_to` with kind `confirm-check` or `waive` on a request that asks the user, which
  the user answers in Cockpit; the agent never answers a scoped request);
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
  citing that exclusion; (5) all criteria covered by carried evidence → finalization with no new observation.
- **Negative scenarios:** ecosystem tests fail when a skill reintroduces schema-1 construction, asserts a
  verdict for a command, lets an agent author `waived` or `human-confirmed` without a scoped confirmation or
  tells it to answer a scoped request itself, or
  omits the basis or observation echo; the reviewer refuses a request without `semantics`; the Finalizer
  procedure continues after `finalization-context-oversized` or asks for a partial context.
- **Inner loop:** `uv run pytest tests/test_agent_ecosystem_validation.py -q`.
- **Closeout:** `uv run test --changed`; host rehearsal evidence on the PR.
- **LC:** not applicable (no loader, format or startup change).
- **Size / risk:** M / medium.

### 3.4 N03-C — Evidence projection

- **Prerequisites:** N03-B.
- **Editable paths:** `evidence.py` (projection); `work_items.py` (`WorkItemDetailView.evidence`,
  `WorkItemProjector`); `application_models.py` (`DeliveryChangeView.evidence`, `DeliveryOperatorContext.evidence`);
  `portfolio_application.py` (`get_change`, `:1162`); `application_readiness.py` (`show_work_item_view`,
  `show_operator_context`); `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py`
  (`DeliveryOperatorContextResponse.evidence` and its `from_context` copy);
  `serve/delivery-mcp/tests/test_target_server.py`; `serve/cockpit/src/owlbear_cockpit/target_models.py`
  and `serve/cockpit/tests`; `serve/cockpit/web/src/api/workItems.ts`; `WorkItemDetail.tsx` (technical summary;
  a scoped request's kind, criteria and procedure shown beside its answer controls)
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
6. §4.4: N03-P row on merge. No §4.2 change (PR #360's N05-B dependency on N03-A was removed on
   2026-10-04).

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N03-P | #349 | — | Probes P1–P16 | Sol round 1: revision-required (observation binding, stored-byte upcast contract, confirmation applicability, bounded exclusions context, all-carried path) → revised; Sol round 2: revision-required (snapshot consumer serialization, confirmation retention through promotion, upgraded handoff receipt contract, MCP output owners) → revised; Sol round 3: revision-required (Planner lifecycle normalization, context budget) → consolidated comparison inventory; Sol round 4: revision-required (representation-only write publication) → revised; Sol round 5: revision-required (drained acknowledgment base) → revised; Sol round 6: `plan-sound`; user-decision revision #360 (history): Sol rounds 1–4 added a user-only confirmation boundary over MCP elicitation, a frontier confirmation ledger and single-use consent records, and opened U2; all removed on 2026-10-04 (simplification, header) | approved (D11 confirmed 2026-10-03; U1 decided (b) 2026-10-03; U2 resolved 2026-10-04) |
| N03-A | — | — | — | — | — |
| N03-B | — | — | — | — | — |
| N03-C | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | N02-B's registry, gate and `delivery-migrate` accept identity `readable-legacy` entries for a mutable family and a marker-only migration | N02-A/B are not implemented | N02 plan §1.4–1.5, D3, D5 | N03-A (re-check at start; a divergence stops for a plan revision) | N03-A start |
| G2 | Widening validators reject N03 content in every old-version instance | Prototype covered observation and review only | P3, P6 | N03-A tests | N03-A merge |
| G3 | P8 lists every family whose fingerprint changes | Static scan; N02-A's fingerprint test is the authority | P8 | N03-A | N03-A merge |
| G4 | A real reviewer detects an assembled-but-wrong Change from the shared basis | Semantic judgment; not provable by fixtures | Mechanical uncovered case automated in N03-A | N03-B host rehearsal | N03-B merge |
| G6 | Evidence reuse after revision | Reuse is N04 | §1.4 survival rules | N04 | Nothing in N03 |
| G7 | Live `delivery-action-readiness` can finalize | Its product merged via PR #316 (`364daf61`), but the record is unfinished: 10 schema-1 observations are `unknown`; 17 criteria need typed evidence | P1 | N10-M disposition | N10-M |
| G8 | LC runs in CI | Needs Docker and a live copy | `delivery-lc` unit tests (N02-B) | Each phase | Nothing (recorded per phase) |
| G9 | The unadmitted live draft `interactive-browser-tools` (23 unprefixed criteria) can be admitted | First admission now requires `AC-NNN:` prefixes, a package change the user re-approves | P4 | Its Designer session after the programme | Nothing in N03 |
