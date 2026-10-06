# Delivery N10 — Regression Matrix, Host Journey and Live Migration

> **Package:** N10 of the
> [execution plan](delivery-redesign-execution-plan.md#n10--regression-matrix-host-journey-and-live-migration),
> reduced 2026-10-04.
> **Planned on:** `origin/dev` `66871ee92` (N09-P2 and N05-B1 merged; N03-C, N04-A–C, N05-B2–D, N08-C,
> N09-B and N09-C not merged). Live Delivery is pinned to release `841b1cffb` (format 2); N05-B2 adds the
> next format step. Live state was not read; probes were read-only source and test inventory. Rebased on
> `origin/dev` `9b77ddadd` (N03-C #373 and N08-C #370 merged); their planned citations resolve at N10-A start (D4).
> **Status:** N10-P plan gate closed 2026-10-05. Sol plan gate round 1 on `eb185eb3f`: revision-required,
> three documentation-level findings, all accepted fix-now and applied (U3 option (c) removed, D7 regression gate,
> V08 proof); the gate ends with these corrections. Plan decisions U1 and U2 settled (D13, D14). Product code is unchanged by
> this phase. Reviews work in the execution plan's
> [operating context](delivery-redesign-execution-plan.md#19-operating-context).

## 1. Contract

### 1.1 Result

- **N10-A:** every remaining V-scenario (V01–V24 without V17, V22 and V23), U1–U8 and programme §14.5 has
  named proof on the exact candidate (P23). Existing maintained tests carry almost all of it (§1.7); the one
  new durable test is an assembled V01 journey. The full suites pass on the candidate, and the candidate
  passes the upgrade rehearsal from the live release.
- **N10-H:** one real VS Code / Copilot journey with the user on a disposable project, from design through
  completion (P24, host half), recorded in a docs-only PR.
- **N10-M:** the live controller is upgraded to the final release through `/upgrade-delivery`, the three
  live Changes are disposed of (§3.3), B1 continues, the programme issues are closed with evidence, and the
  programme and execution plan are marked complete in a docs-only PR.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | The remaining V-matrix passes as regression on the exact candidate | Execution plan §5 N10, §6; programme §13; P23 |
| R2 | U1–U8 and programme §14.5 have proof or a recorded, accepted limit | Programme §1.1, §14.5; execution plan §6 |
| R3 | One host journey, design through completion, on a disposable project on macOS | Execution plan §5 N10, §1.1; P24; V01 "separate actual Copilot smoke" |
| R4 | Every verification gap of N01–N09 owned by N10 is closed or recorded (§1.9) | Execution plan §1.7 item 5 |
| R5 | The live controller is upgraded to the final release through the rehearsed procedure | Execution plan §1.3, §5 N10; [N02 plan](delivery-n02-plan.md) §3.5 |
| R6 | `delivery-action-readiness` completes or is observed; `frontier-serialization-contract` is abandoned through the supported route and PR #314 closed after the user confirms; B1 is reconciled once and continues | Execution plan §2.6, §5 N10, §7 |
| R7 | Issues #213, #215, #216 and #218–#222 (and #225 if N05-D is built) are closed with evidence | Execution plan §6 |
| R8 | Programme section 0 and the execution plan are marked complete | Execution plan §5 N10 |

### 1.3 Invariants

- **I1 No new mechanism.** N10 adds one test and documentation. A product defect found in any N10 phase is
  fixed by a normal fix PR with proof and the implementation gate, never inside an evidence PR.
- **I2 Disposable until N10-M.** N10-A and N10-H use disposable state and repositories only. Live writes
  happen only in N10-M, with the user present and authorizing each step (execution plan §1.3).
- **I3 Supported routes only.** Live state changes only through `/upgrade-delivery`, Cockpit controls,
  Delivery tools and `delivery-repair` proposals; never by editing records, refs, the pin or launchers.
- **I4 Evidence proves its own boundary.** An automated test is not host evidence; a host observation is
  not regression proof ([challenger protocol](../../share/skills/r-challenger-protocol/SKILL.md)). A host gap is
  recorded only to the boundary actually observed (an alive-window interruption is not unknown-issuer evidence).

### 1.4 Existing owners to reuse

- Assembled tests: the default loader; `Client(assemble_target_server(...))` (Delivery MCP tests); the Cockpit
  HTTP test client (`tests/test_cockpit_work_items.py`); the memory publication and merge provider of
  `owlbear_delivery_github` (N05-A); N05-B2's `approve_merge` and N05-C's HTTP approve route.
- Upgrade: `share/prompts/upgrade-delivery.prompt.md`, `delivery-controller`, `delivery-migrate`,
  `delivery-lc run --form upgrade` and the N02-D H-step runbook, including its checkout-collisions check
  ([N02 plan](delivery-n02-plan.md) §3.5).
- Repair: `/repair-delivery`, `delivery-diagnose`, `delivery-repair` (N08-A).
- Dispositions: Cockpit **Abandon Change** (`set_change_intent` abandon) and **Clean abandoned worktree**;
  `get_change`, `show_operator_context` and the evidence projection (N03-C); Pause and `/design` revision (N04).
- Disposable project: `setup/setup-guide.md` and `setup/init.py` (consumer default, unpinned).

### 1.5 Exclusions

- A test per V-scenario or per criterion; a second Cockpit journey E2E beside N05-C's approve E2E; real-GitHub
  scenarios beyond N05-C's smoke test (N05 plan G1, documented limit).
- B1's TASK-004 managed-device pilot (V23, B1's own acceptance) and B1's work after its reconciliation.
- Host runs on Ubuntu (host acceptance is macOS; Ubuntu is proven by CI, execution plan §1.1).
- Broader automatic recovery and physical worker exclusion (D03 bounded recovery).

### 1.6 Decisions

Settled by the planner (2026-10-05), each with one defensible answer in the operating context:

- **D1 Cite, do not duplicate.** Each V-scenario cites the maintained tests that already exercise it (§1.7);
  N10-A runs the full suites on the exact candidate, which is the regression (P23). No per-V test files.
- **D2 One new durable test: the assembled V01 journey.** The engine journey exists in two halves that do not
  meet: `test_continuation_plans_builds_and_finalizes_via_existing_result_routes` stops at
  `engine-owner-unavailable` (no publisher attached) and `test_continuation_publishes_syncs_finalizes_and_observes_acceptance`
  starts from a Completed outcome with a fixture checkpoint and a manual merge (P3). No test runs one Change
  across every stage handoff through the registered MCP and HTTP surfaces with the approval. A seam between
  phases is shared, easy to regress and hard to notice, so this is the one place a durable test earns its cost.
- **D3 Route audit, not a test.** Programme §14.5 requires every supported failure to resume automatically or
  expose one working prompt or control. N10-A records, for every `DeliveryReadinessReason` on the candidate,
  its route; existing tests already pin the progress mapping and prompt applicability. Only a reason without
  a route is a defect and gets a fix with one test.
- **D4 Planned citations resolve at N10-A start.** Rows that cite a scenario of an unmerged phase (marked
  *planned*) are replaced by that phase's merged node IDs. A phase that merged without its planned scenario is
  a gap of that phase, repaired by a fix PR of its package, not rebuilt in N10-A.
- **D5 macOS host only.** N10-H runs on macOS (execution plan §1.1); Ubuntu is covered by CI on the exact heads.
- **D6 N10-A carries the upgrade rehearsal.** N10-A is the last product phase, so its closeout runs
  `delivery-lc run --form upgrade --previous 841b1cffb…` on its candidate. N10-M reuses it when only
  documentation changed since (N02 runbook rule), otherwise reruns it.
- **D7 N10-H defects.** A defect found in the host journey stops that step. It is fixed in a fix PR
  (`redesign/n10-h-fix-<slug>`, `N10-H: fix <defect>`, normal proof and implementation gate). After merge the
  affected host steps are rerun, and the N10-A regression gate (full suites on the exact head, §3.1 closeout) runs
  again on the final product-code head; a docs-only change needs no repeat. D6 refreshes the upgrade rehearsal
  when code changed. The evidence PR follows.
  Applied 2026-10-05 to defect H1 (§3.2.1, PR #383; branch and title as named by the lead:
  `redesign/n10h-fix-contract-digest`, `N10-H fix: non-ASCII contract authority digest`).
- **D8 `/upgrade-delivery` unchanged.** N10-M runs the shipped prompt; this plan adds only the preconditions,
  the checkout alignment and the dispositions around it.
- **D9 Abandonment by the user.** `frontier-serialization-contract` is abandoned by the user in Cockpit
  (**Abandon Change**, reason naming N02-A #348 and #215). Abandonment does not close the PR (no provider
  close exists, P5); the agent closes PR #314 with a comment after the user confirms.
- **D10 B1 through supported routes.** The reconciliation is diagnosis plus existing routes (§3.3 step 5).
  A blocker without a route stops N10-M's B1 step and becomes a fix PR; nothing is edited by hand.
- **D11 U8 is a process requirement.** "Three model-capability tiers" is satisfied by execution plan §1.6
  (Opus leads, Luna for bounded slices, Sol challenges); it has no product proof.
- **D12 Issue closure.** The agent posts closure comments and closes issues only with the user's
  authorization at N10-M step 6; #218 was already authorized (N09 plan U1 (b)).

Settled by the lead with the user (2026-10-05):

- **D13 Host journey scope (was U1, option (a)).** The single N10-H journey also covers an interruption, a
  person-only check answered in Cockpit and one requirement change before completion (§3.2 steps 3–5).
  Requirement revision has no other host proof.
- **D14 Disposable repository (was U2, option (a)).** The agent creates a private repository
  (`<user>/owlbear-n10h-<date>`) before N10-H; the user deletes it afterwards (precedent N05 U2 (b)).
- **D15 `delivery-action-readiness` is observed, not continued (Sol gate finding 1).** The default N10-M
  outcome is a recorded observation of the migrated unfinished record (R6 "completes or is observed"). No
  Planner, Builder or Finalizer is acquired for it and no evidence is added: never use Delivery to implement
  Delivery (execution plan §1.1). Abandonment stays an optional user decision at the step (U3).
- **D16 V08 boundary (Sol gate finding 3).** Maintained tests prove the V08 parts on real owners (§1.7); none
  reports a `proof-mutation` diagnostic through the application. N10-A runs one disposable negative check for the
  complete boundary (§3.1) and records it; no durable test.

### 1.7 Acceptance map: V-scenarios

Prefixes: `D:` `serve/delivery/tests/`, `M:` `serve/delivery-mcp/tests/`, `G:` `serve/delivery-github/tests/`,
`T:` `serve/tools/tests/`, `C:` `serve/cockpit/tests/`, `R:` `tests/`, `E:` `serve/cockpit/web/e2e/`.
*Planned* named a scenario of an unmerged phase's plan (D4); N10-A replaced each with merged node IDs.

| V | Required result (programme §13) | Delivered by | Existing proof (node IDs) | N10-A | N10-H |
| --- | --- | --- | --- | --- | --- |
| V01 | One Change through plan, build, review, finalize, publish, approve merge, completion with only prompt, form and approval user actions | D02, N05, N09 | `D:test_portfolio_application.py::test_continuation_plans_builds_and_finalizes_via_existing_result_routes`, `::test_continuation_publishes_syncs_finalizes_and_observes_acceptance`; `E:work-portfolio.spec.ts` "copies the continuation prompt and pauses then resumes a quiescent Change"; N05-B2 `D:test_merge_approval.py::test_one_approval_sends_one_fenced_request_and_completes_once`; N05-C `R:test_cockpit_work_items.py::test_http_approve_merge_sends_one_request_and_refuses_stale_busy_and_unverifiable_offers`, `E:work-portfolio.spec.ts` "approves the exact offer once in the dialog and Delivery records completion"; N10-A `R:test_delivery_journey.py::test_v01_one_change_runs_from_admission_to_completion_through_mcp_and_cockpit` | Assembled journey test (D2, §3.1) | Required: the host journey (§3.2) |
| V02 | Dirty completed-task worktree: card and acquisition agree on recovery, not finalization | D01, D03 | `D:test_portfolio_application.py::test_captured_readiness_agrees_across_public_reads`, `::test_loader_composed_engine_preflight_contains_workspace_variants`, `::test_settled_dirty_finalizer_attention_stays_blocked_after_workspace_cleanup` | — | — |
| V03 | Finalizer fails before tests: checks not run, repair or containment, never blind refinalization | D03, N03-A | `M:test_target_server.py::test_registered_default_loader_contains_failed_finalizer_before_checks`; `R:test_cockpit_work_items.py::test_http_finalizer_handoff_contains_failure_before_checks`; `D:test_portfolio_application.py::test_finalization_attention_replays_only_its_report_and_rejects_new_diagnostics`; `D:test_evidence_runtime.py::test_uncovered_criterion_refuses_finalization_even_when_every_task_check_passed` | — | Observed (nested Finalizer, N03 G4) |
| V04 | Two sessions on one Change: one owner, the second is busy | D02 | `D:test_portfolio_application.py::test_continuation_concurrent_sessions_grant_one_owner`; `R:test_cockpit_work_items.py::test_continuation_execution_preserves_typed_busy_failure`; `D:test_change_workspace.py::test_publication_lease_rejects_concurrent_owner_and_allows_expired_takeover` | — | — |
| V05 | Two Changes, limited capacity, shared target | D02, D03, N02-C, N05-B1 | `D:test_portfolio_application.py::test_execution_capacity_allows_independent_builders_and_planners`, `::test_selected_acquisition_leaves_sibling_claims_unchanged`, `::test_selected_acquisition_honors_capacity_and_returns_source_failure`, `::test_application_binds_target_sync_receipt_and_invalidates_finalization`; `D:test_change_publication.py::test_slow_target_fetch_of_one_change_does_not_block_another_changes_merge` | — | — |
| V06 | Formatting drift: preserve with proven ownership, otherwise contain unchanged | D03 | `D:test_change_workspace.py::test_preservation_restores_only_proven_disposable_paths`, `::test_preservation_requires_trusted_exact_path_provenance_before_copying`; `D:test_portfolio_application.py::test_dirty_build_recovery_exclusion_required_preserves_bytes_and_custody` | — | — |
| V07 | Drift after proposal, foreign, staged or private files: no overwrite or publication | D03 | `D:test_change_workspace.py::test_preservation_rejects_foreign_dirty_path_before_private_capture`, `::test_private_path_policy_remains_conservative_for_dirty_paths`, `::test_quarantine_replay_rejects_changed_bytes_after_preservation`, `::test_recovery_workspace_rejects_path_drift_before_content_read` | — | — |
| V08 | Proof command mutates files: no pass, bounded diagnostic, no repeat | D03 | Parts on real owners: `D:test_finalization_reports.py::test_proof_attempt_store_binds_registered_owner_observation_and_replays` (owner-observed attempt with distinct before/after fingerprints persists; replay and restart never re-observe); `D:test_portfolio_application.py::test_proof_procedure_repair_accepts_only_exact_owner_attempt` (proof-procedure repair binds only the exact owner attempt); `D:test_recovery.py::test_completed_outcome_repair_replays_with_retry_authority_and_preserves_result` (proof-procedure repair refused without a `proof-mutation` diagnostic); `D:test_portfolio_application.py::test_continuation_failure_retains_custody_and_blocks_success_and_mutations` (a failed attempt cannot finalize, across restart; maintained-check category); `D:test_portfolio_application.py::test_settled_finalizer_retries_stop_at_three_attempts_without_recovery` (retries across sessions are bounded). Uncovered by maintained tests: a `proof-mutation` report through `report_finalization_failure` and the `application_lifecycle` fingerprint checks; covered by the N10-A disposable check (§3.1.1) | Disposable check (D16, §3.1) | — |
| V09 | Repeated failure across sessions exhausts a durable budget; siblings stay runnable | D03 | `D:test_portfolio_application.py::test_settled_planner_retries_exhaust_after_three_exact_attempts`, `::test_ended_without_result_builder_attempts_share_one_exhausting_budget`, `::test_worker_budget_survives_resolved_blocks_and_leaves_sibling_runnable`; `D:test_retry_ledger.py::test_semantic_identity_aliases_and_restart_persistence` | — | — |
| V10 | Worker past its lease may still write: contained, no cleanup or replacement | D03 | `D:test_recovery.py::test_absent_host_still_writing_descendant_stays_contained_across_restarts` and its MCP (`M:test_target_server.py::test_registered_absent_host_still_writing_descendant_stays_contained_across_restarts`) and HTTP (`R:test_cockpit_work_items.py::test_http_absent_host_still_writing_descendant_stays_contained_across_restarts`) twins; `D:test_worker_stall.py::test_leftover_process_blocks_confirmed_release_without_a_retry_time` | — | Observed (interruption, N09 G1; G9 only if unknown-issuer evidence occurs, I4) |
| V11 | Target advances during final verification: old proof not reused, fresh review and approval | D03, N05-B1, N05-B2 | `D:test_portfolio_application.py::test_continuation_finalizer_rejects_target_drift_without_releasing_custody`, `::test_application_binds_target_sync_receipt_and_invalidates_finalization`; `D:test_merge_offer.py::test_newer_provider_target_routes_a_finalized_change_through_sync_and_fresh_proof`; `G:test_merge_provider.py::test_memory_rules_failure_and_strict_target_advance_fail_without_merging`; N05-B2 `D:test_merge_approval.py::test_an_offer_invalid_at_execution_sends_nothing_and_writes_no_attempt`, `::test_a_raced_merge_is_attention_never_completion` | Resolved (D4) | — |
| V12 | Push or merge applied but response lost: readback, no duplicate | D02, D03, N02-C, N05-A, N05-B2 | `D:test_change_publication.py::test_adopts_exact_reviewed_remote_head_after_lost_push_response`; `D:test_delivery_state.py::test_state_push_accepted_after_its_lost_response_reads_back_success_without_a_second_push`; `D:test_draft_pull_request.py::test_reconciles_lost_create_response_without_creating_second_pr`; `D:test_portfolio_application.py::test_engine_mark_ready_replays_lost_response_and_acceptance_waits_without_merge`; `G:test_merge_provider.py::test_memory_lost_response_applies_the_effect_and_readback_finds_it`; N05-B2 `D:test_merge_approval.py::test_a_crash_at_each_outcome_changing_boundary_replays_to_one_outcome` (boundary (b)), `::test_every_acceptance_path_settles_the_attempt_after_a_restart`, `::test_an_unknown_merge_waits_for_the_user_and_check_again_reads_once` (assembled); N05-C `E:work-portfolio.spec.ts` "shows an unknown merge with its PR link and checks again only when asked" | Resolved (D4) | — |
| V13 | Quarantine or restore fails midway: no false success, evidence kept | D03 | `D:test_change_workspace.py::test_nonterminal_recovery_restore_fsync_failure_cannot_publish_success`, `::test_quarantine_replays_after_receipt_persistence_failure`, `::test_cleanup_replays_persisted_intent_after_receipt_write_failure`, `::test_nonterminal_recovery_capture_failure_keeps_bytes_and_replays` | — | — |
| V14 | Requirement change with old code and proof: prior authority kept, coherent activation, only affected work replanned | N04-A, N04-B | N04-A `D:test_source_bound_admission.py::test_revision_replans_changed_outcomes_and_keeps_change_state` (replaced the earlier `test_revision_preserves_unchanged_binding_and_invalidates_changed_dependents`), `::test_replanned_outcome_keeps_completed_work_whose_commitments_survive`, `D:test_portfolio_application.py::test_paused_change_revision_replans_changed_outcome_and_replays`; N04-B `D:test_delivery_state.py::test_design_return_readmission_preserves_builder_work_across_restart`; N04-C `D:test_portfolio_application.py::test_revision_replan_publishes_from_plan_context_alone` | Resolved (D4) | Observed: requirement change (D13, N04 G4) |
| V15 | New request ID, unchanged proven claim: evidence reused, no new human exercise | N03-A, N04-A, N03-C | `D:test_evidence.py::test_stale_versions_and_unknown_ids_never_cover_and_are_admissibility_gaps`; `D:test_acceptance_criteria.py::test_identity_survives_revision_while_the_version_changes_with_the_statement`; `D:test_evidence_runtime.py::test_full_carried_coverage_finalizes_with_zero_new_observations`; N04-A `D:test_source_bound_admission.py::test_revision_keeps_unchanged_criterion_evidence_and_scoped_confirmation`; N03-C `D:test_evidence.py::test_projection_shows_each_evaluator_status_with_its_latest_records_first`, `R:test_cockpit_work_items.py::test_http_work_item_detail_carries_its_evidence_projection`, `WorkItemDetail.evidence.test.tsx` "shows each criterion's evaluator status and its records, with locators as text" | Resolved (D4) | Observed: retained confirmation (D13, N04 G5) |
| V16 | Revised target not covered: exact missing claim shown, no silent waiver | N03-A, N03-C, N04-A | `D:test_evidence_runtime.py::test_uncovered_criterion_refuses_finalization_even_when_every_task_check_passed`; `M:test_confirmation_boundary.py::test_registered_finalize_refusal_carries_the_exact_bounded_gaps`, `::test_mcp_answer_refuses_a_waiver_or_person_only_request`; N03-C `D:test_evidence.py::test_projection_shows_each_evaluator_status_with_its_latest_records_first`, `M:test_target_server.py::test_registered_evidence_projection_agrees_across_reads_and_names_waivers`; N04-A `D:test_source_bound_admission.py::test_revision_keeps_unchanged_criterion_evidence_and_scoped_confirmation` (changed `AC-002` uncovered) | Resolved (D4) | — |
| V18 | Invalid state while the UI loads: Change visible, maintenance entry works (reduced: N08-B cut) | D03, N08-A | `D:test_portfolio_application.py::test_known_corrupt_change_remains_visible_without_relaxing_parser`; `R:test_cockpit_work_items.py::test_list_and_detail_preserve_known_unavailable_change_projection`, `::test_http_and_offline_diagnostics_bound_an_unknown_change_without_mutation`; `T:test_delivery_diagnostics.py::test_standalone_cli_degraded_and_unsupported_exit_one`; `D:test_state_repair.py::test_c02_restores_a_tampered_admitted_package_and_the_portfolio_lists_again` | — | Observed: refused start visible (N08 G1) |
| V19 | Approve merge, then head change or protection failure: no unapproved merge, reason shown | N05-A, N05-B1, N05-B2, N05-C | `G:test_merge_provider.py::test_memory_head_fence_fails_a_request_after_a_push`, `::test_memory_draft_or_closed_pull_request_is_refused`; `D:test_merge_offer.py::test_known_unmergeable_pull_request_never_yields_an_offer`; `R:test_delivery_worktree_authority.py::test_frozen_merge_body_is_direct_and_never_bypasses_rules`; N05-B2 `D:test_merge_approval.py::test_an_offer_invalid_at_execution_sends_nothing_and_writes_no_attempt`; N05-C `E:work-portfolio.spec.ts` "refuses an offer that changed while the dialog was open and sends no merge request", `WorkPortfolio.part5.test.tsx` "keeps the dialog open on a stale offer, merges nothing and blocks re-approval of the old offer" | Resolved (D4) | — |
| V20 | Unknown corruption or missing provenance: preserved, diagnosed, never blessed | D03, N02-B, N03-A, N08-A | `D:test_state_migration.py::test_frontier_invalid_at_its_declared_version_is_corruption_and_never_synthesized`, `::test_third_digest_stops_resume_and_abort_as_corruption_preserving_both_copies`; `D:test_state_repair.py::test_no_repair_path_writes_request_provenance`; `D:test_delivery_runtime.py::test_repair_missing_request_provenance_rejects_wrong_or_multiple_defects`; `D:test_recovery.py::test_recovery_caller_cannot_supply_forged_evidence` | — | — |
| V21 | Crash after each revision or migration step: old version or replayed new one | N02-B, N08-A, N04-A, N04-B | `D:test_state_migration.py::test_crash_at_each_apply_boundary_refuses_start_and_resume_converges`; `D:test_state_repair.py::test_c03_crash_then_fresh_process_resume_reaches_the_exact_after_state`; `D:test_change_workspace.py::test_snapshot_design_package_replays_after_commit_before_receipt`; N04-A `D:test_delivery_state.py::test_revision_activation_crash_reloads_and_replays_to_one_snapshot` (eight boundaries), `D:test_portfolio_application.py::test_cancel_interrupted_after_contract_publication_is_completed_by_resume`; N04-B `D:test_delivery_state.py::test_design_return_readmission_preserves_builder_work_across_restart` (capture, reset and release boundaries), `::test_design_return_replay_refuses_an_index_restaged_after_capture` | Resolved (D4) | — |
| V24 | Upgrade with active work or unsupported downgrade: drained or fenced, refused or safely reverted | N02-A–D, N05-B2 | `T:test_delivery_controller.py::test_preflight_blocks_exactly_the_d6_custody_shapes_and_changes_nothing`, `::test_switch_records_previous_rolls_back_and_prune_keeps_current_and_previous`; `D:test_state_migration.py::test_n02a_refuses_the_migrated_format_1_workspace_with_unchanged_hashes`; `T:test_delivery_lc.py::test_full_form_downgrade_refuses_exactly_the_records_of_a_family_version_the_previous_release_lacks`; `C:test_target_context_startup.py::test_cockpit_refuses_newer_state_with_the_typed_loader_detail`; live: N02-D H step (#362, #367); N05-B2 `D:test_state_formats.py::test_a_format_2_controller_refuses_state_with_merge_attempts`, `D:test_state_migration.py::test_marker_only_format_steps_change_only_the_marker_and_keep_every_change_available` | Upgrade rehearsal (D6) | — (live in N10-M) |

**Count (21 scenarios).** Proven on `dev` today: 12 (V02–V07, V09, V10, V13, V18, V20, V24). Proven once a
planned phase merges, N10-A only resolves the citations: 7 (V11, V12, V14, V15, V16, V19, V21). N10-A adds proof:
2 (V01 durable journey; V08 disposable check, D16). Needs N10-H host evidence: 1 (V01); N10-H also observes V03,
V10, V14, V15 and V18 (D13). N10-A result (2026-10-05): all 21 proven on the candidate, V08 with one gap fixed
(§3.1.1).

### 1.8 Acceptance map: U1–U8, programme §14.5 and execution plan §6

| Criterion | Proof | N10 phase |
| --- | --- | --- |
| U1 Actions through a Cockpit control or a complete chat prompt | N09-A1 progress and **Copy continuation prompt** (#354); `D:test_portfolio_application.py::test_engine_action_prompt_is_applicable_to_final_readiness_state`; `D:test_delivery_progress.py::test_every_readiness_reason_has_an_explicit_progress_mapping`; N09-B (#379) removed `/orchestrate` and `/release-stuck-worker`, `WorkPortfolio.part5.test.tsx` "offers the continuation prompt only while engine readiness is executable" | N10-A route audit (D3): 43 of 43 reasons routed after R1 (b) (§3.1.1); N10-H uses only prompts and controls |
| U2 User never runs tests, edits files, repairs JSON or operates Git | By construction (agents prove, Delivery owns custody); N09-B capability inventory | N10-H records every user action and checks that each is a prompt, form, control or approval |
| U3 Agents prepare; humans decide, authenticate, confirm | N03 scoped requests answered in Cockpit: `R:test_cockpit_work_items.py::test_http_answer_resolves_a_waiver_request_that_a_finalization_waiver_then_cites`, `M:test_confirmation_boundary.py::test_mcp_answer_refuses_a_waiver_or_person_only_request` | N10-H person-only check (D13) |
| U4 Resume from persisted evidence | `D:test_portfolio_application.py::test_continuation_finalizer_survives_restart_and_completes_exactly_once`, `::test_builder_ended_without_result_reacquires_same_task_with_preserved_work_and_history`; `D:test_worker_stall.py::test_host_lost_quiet_builder_settles_and_resumes_same_task_with_preserved_work` | N10-A journey restarts once (fresh loader between Builder and Finalizer, passed); N10-H interruption |
| U5 Responsible handler and bounded path for every failure | Retry exhaustion and containment tests (V09, V10); progress mapping test | N10-A route audit (D3): R1 resolved by (b) (§3.1.1) |
| U6 Repeated evidence only for an uncovered or invalidated claim | V15 row | N10-H step 5 (D13) |
| U7 Approval is not certification; nothing dropped to pass | `D:test_evidence_runtime.py::test_uncovered_criterion_refuses_finalization_even_when_every_task_check_passed`; waivers only through a user-resolved request (`D:test_evidence.py::test_waiver_citing_an_inapplicable_request_does_not_satisfy`) | — |
| U8 Three model tiers | Execution plan §1.6 (D11) | — |
| §14.5 Start, resume, answer, approve, see completion without tests or file edits | V01 row | N10-A journey (passed); N10-H |
| §14.5 / §6 Every supported failure resumes or exposes one working prompt or control | Route audit over readiness reasons (D3) | N10-A: every reason routed after R1 (b); dirty finished worktree is an accepted limit (§1.10) |
| §6 Live Changes migrated or disposed of; B1 continues; final release pinned | — | N10-M |
| §6 Issues closed with evidence | #216, #221 drafts (N00-A); #218 (N09 U1 (b)); #213 (N04); #215, #220 (N02); #219, #222 (N03); #225 (N05-D, if built) | N10-M step 6 |
| §6 Documentation matches shipped behavior | N09-C (P22) | N10-H follows the shipped setup guide and prompts |
| §6 No `fix-now` finding open | Each phase's gate | Each N10 phase |

### 1.9 Verification gaps of N01–N09 owned by N10

| Gap | Claim | Closed by |
| --- | --- | --- |
| N03 G4 (= N09 G11) | A real host dispatches the nested Finalizer and `build-reviewer` under `/continue-change` and finalizes | N10-H step 6 |
| N03 G7 | Live `delivery-action-readiness` can finalize (17 criteria need typed evidence) | N10-M step 4: recorded observation (D15) or user abandonment (U3); never finalized through Delivery |
| N04 G4 | A real Designer chat follows the revised `w-design-session` route | N10-H step 5 (D13) |
| N04 G5 | A Builder of a replanned outcome cites a retained confirmation instead of asking again | N10-H step 5 (D13) |
| N08 G1 | VS Code shows a refused Delivery MCP start clearly enough to run `/repair-delivery` | N10-H step 8 |
| N09 G1 | An `alive` issuer with a held claim may have no running worker; Cockpit never shows it as working | N10-H step 3 |
| N09 G2 | The copied `/continue-change <id>` prompt binds the right Change in Copilot Chat | N10-H steps 2 and 3 |
| N09 G5 | #218 closed with evidence | N10-M step 6 (agent, N09 U1 (b)) |
| N09 G9 | `needs-decision` for unknown issuer evidence does not lead the user to release a live worker | N10-H step 3 only if `needs-decision` for unknown issuer evidence appears; otherwise recorded open with engine proof only (I4) |
| N02 G3 | VS Code restart and autostart with the launcher | Closed by the N02-D H step 0 (2026-10-04); nothing in N10 |
| N06 G11 | LC exercises interaction records | Void: N06 cut 2026-10-04 |

N01 and N05 name no gap owned by N10; N05's real-GitHub evidence is N05-C's smoke test (N05 plan §3.3).

### 1.10 Accepted limits carried to completion

Documented limits, not N10 work: no physical worker exclusion, so unknown or live workers stay contained and may
hold capacity (D03); N05 G1 (real GitHub beyond one merge), G2 (base or stack change after the final read is
detected after the merge), G14 (supersession of a moved or merged predecessor) and G15 (ignored files in a
completed worktree are not preserved by cleanup); N08 §3.3 (package corruption makes `list_changes` raise, a
garbage transaction manifest stops Cockpit untyped, a malformed coordination record shows no diagnostic; each is
routed by `/repair-delivery`); N09 G3 (**Working**, **Checking** and **Repairing** are never emitted); N02 G6 and
N08 G6 (memory-store versioning is outside the programme); N10-A R1 (lead decision 2026-10-05, option (c) not
built): a dirty finished worktree has no automatic preservation-and-resume route, since one would be a new
mechanism (I1); `/repair-delivery` diagnoses the state read-only and the user cleans the worktree or abandons the
Change.

### 1.11 User decisions

Plan decisions U1 and U2 (not the programme criteria of §1.8) were settled on 2026-10-05 as D13 and D14.

Decided at the N10-M step (execution plan §7); recommendations for the lead to present then:

- **U3 — `delivery-action-readiness`.** Its product merged via PR #316 (`364daf61`); the record is unfinished
  (Implementation, 4 of 5 results, schema-1 evidence). *Default (D15):* after the upgrade the agent records its
  readiness and evidence projection and leaves the record as observed. *Option:* the user abandons it in Cockpit
  with the reason "product merged via PR #316 (`364daf61`); record unfinished". Continuing it through Delivery is
  not an option (execution plan §1.1). *Recommendation:* the default unless the user wants the record terminal.
- **U4 — `frontier-serialization-contract`.** Abandon (its scope shipped with N02-A, #348) and close PR #314:
  the user confirms at the step (D9).
- **U5 — B1.** The user confirms each user-only action of the reconciliation (§3.3 step 5).

## 2. Feasibility Probes

Read-only, on `origin/dev` `66871ee92` in lane D; logs in `.owlbear/scratch/n10p-*.log` (unversioned).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | `git grep` of test functions in the Delivery, Delivery MCP, GitHub provider, tools and Cockpit suites and the root Delivery tests; keyword grouping per V-scenario | 1,912 test functions; every V-scenario except V01 has direct maintained tests (§1.7); no test names a V-scenario | D1 |
| P2 | Package plans N01–N09: every verification gap and decision naming N10 | 11 items (§1.9); none in N01 or N05 | R4 |
| P3 | Bodies of `test_continuation_plans_builds_and_finalizes_via_existing_result_routes` and `test_continuation_publishes_syncs_finalizes_and_observes_acceptance` | The first ends at `waiting/engine-owner-unavailable` without a publisher; the second starts at stage Completed with a fixture checkpoint and simulates a manual merge; neither runs through MCP or HTTP | D2 |
| P4 | `test_every_readiness_reason_has_an_explicit_progress_mapping`, `test_engine_action_prompt_is_applicable_to_final_readiness_state` | Progress mapping and prompt applicability are pinned; no test asserts that every non-executable reason has a route | D3 |
| P5 | Source read of abandonment (`WorkItemDetail.tsx` **Abandon Change**, provider modules) | Abandonment is a Delivery intent; no provider call closes a PR; **Clean abandoned worktree** refuses a dirty worktree without discarding content | D9; §3.3 step 3 |
| P6 | `share/prompts/upgrade-delivery.prompt.md` | Steps 1–10 cover install, online and offline preflight, backup, migration, switch, verify, prune, restart and failure; no format-specific step | D8 |

## 3. Phases

### 3.1 N10-A — Matrix and gap fixes

- **Prerequisites:** N10-P, N09-C, the last N04 phase (execution plan §4.2).
- **Editable paths:** new `tests/test_delivery_journey.py` (re-resolve: root tests already combine Delivery MCP
  and Cockpit HTTP); this plan (planned citations, route audit, progress); execution plan status row. Only if the
  route audit finds a reason without a route: its owning module and one test, or a fix PR in the owning package.
- **Companions:** none (no readiness reason, action, status or frontier writer is added).
- **First step:** resolve every *planned* citation of §1.7 to merged node IDs (D4).
- **Positive scenario (the journey, one test):** a disposable repository with a local bare remote, the memory
  provider and the default loader. Agent side through `Client(assemble_target_server(...))`: `admit_change` of an
  approved package, `acquire_change_action` → Planner, `publish_delivery_plan` and `transition_delivery` advance,
  `acquire_change_action` → Builder, a commit and `submit_result`; then a fresh loader (restart, U4);
  `acquire_change_action` → Finalizer, `finalize_change`; `execute_change_action` for each engine action until
  readiness is `merge-approval-required`. User side through the Cockpit HTTP client: the detail shows the offer;
  approve merge; the provider merges at the exact head; acceptance completes; the detail shows **Completed**; a
  further `acquire_change_action` is `terminal`. The only user-side calls are reads and the approval.
- **Negative scenarios:** none durable; V04, V11, V12 and V19 negatives are cited in §1.7.
- **V08 disposable check (D16; record only, not committed):** a scratch script in the lane over a disposable
  repository and the real application: acquire the Finalizer, note the workspace fingerprint, change a tracked
  file as a mutating proof command would, then `report_finalization_failure` with `category=proof-mutation`,
  `code=proof-mutated-worktree`, a registered `procedure_id`, the before and after fingerprints and the path.
  Expected: the report persists and replays; a stale `proof_fingerprint_after` is `diagnostic-conflict`; readiness
  is not passed and `finalize_change` is refused; after `settle_worker_invocation` and a fresh application,
  `acquire_change_action` acquires no new Finalizer while the mutated workspace stands. Record the commands and
  results in this plan; a failure is a D03 defect fixed by a fix PR (I1).
- **Route audit (D3):** for every `DeliveryReadinessReason` (the `_EXPECTED` table of
  `D:test_delivery_progress.py` is the list), record its route: automatic (system actor), continuation prompt,
  engine-authored exceptional prompt, Cockpit control or genuine user request. Record the table in this plan.
- **Inner loop:** `env -u PYTHONPATH uv --directory <lane> run pytest tests/test_delivery_journey.py -q -n0`.
- **Closeout:** every §1.7 node ID collected (`pytest --collect-only -q` over the expanded IDs; none missing);
  the V08 disposable check recorded; full `uv run test` once; `npm --prefix serve/cockpit/web run build` and
  `run test:e2e:work`; scoped Ruff; triggered CI on the exact head; Sol implementation gate. This closeout's full
  suites are the regression gate that D7 repeats after an N10-H product fix.
- **LC:** upgrade form on a fresh copy, `--previous 841b1cffb…` (full SHA from the live `pin.json`) and the
  candidate (D6); the proposal's (path, before digest) set is recorded on the PR for N10-M.
- **Size / risk:** S / medium.

#### 3.1.1 N10-A results (2026-10-05)

Candidate code head `97f694ab2` on `origin/dev` `353cd788e` (every N01–N09 phase merged; N05-D not built); the R1
fix `fddb6d02f` (route table below) is the final code head, its proof in §4. The
cited node IDs of §1.7 and §1.8 (105 Python IDs, 228 collected items) collect with exit 0; the one stale citation
(`test_revision_preserves_unchanged_binding_and_invalidates_changed_dependents`, replaced by N04-A) was re-cited.
Frontend and E2E titles cited in §1.7 exist verbatim.

**V-matrix.** "Proven" means the cited maintained tests pass in the full suite on the candidate.

| V | Result | New proof in N10-A |
| --- | --- | --- |
| V01 | Proven (regression half); host half is N10-H | `tests/test_delivery_journey.py`: one Change from `create_design_session` and `admit_change` through Planner, Builder, a fresh loader (U4), `sync-target`, Finalizer, `reconcile-checkpoint` and `mark-ready` over registered MCP, then Cockpit HTTP detail with the offer, **Approve merge**, the provider's merge at the exact head, the page's automatic acceptance reconciliation, the completed record, and `terminal` |
| V02–V07, V09, V10, V13, V18, V20 | Proven | — |
| V08 | Proven, gap fixed | Disposable check below; it found that `report_finalization_failure` refusals (`diagnostic-conflict`) reached MCP callers as an untyped tool error. Fixed in `diagnostics.py` (typed `CONFLICT`, `retry_safe` only for `*-unavailable` codes), one assertion added to `M:test_target_server.py::test_registered_default_loader_contains_failed_finalizer_before_checks`; the programme's adapter exception mapping names this error (programme "D02 Critical Core") |
| V11, V12, V14–V16, V19, V21 | Proven (planned citations resolved, D4) | — |
| V24 | Proven; upgrade rehearsal below | — |

The journey's memory GitHub follows branch pushes and reports clean mergeability (`_FollowingMemoryProvider`),
as GitHub does; the plain memory provider keeps a pull request's creation head, which the publication identity
check correctly refuses. No product defect was found in the journey.

**V08 disposable check (D16; recorded, not committed).** Script `.owlbear/scratch/n10a_v08_check.py` (lane D,
unversioned) over the journey's disposable repository and the default loader, registered MCP for every agent call:

| Step | Observed |
| --- | --- |
| Finalizer acquired, tracked `product.txt` rewritten | Engine fingerprints before `475e6417…` and after `078cdfc4…` differ |
| Report with a stale `proof_fingerprint_after` | Typed refusal `diagnostic-conflict`, `retry_safe: false` (before the fix: untyped "Error executing tool") |
| Report `proof-mutation` / `proof-mutated-worktree`, `procedure_id` `pytest-maintained`, both fingerprints, path | Persisted; the identical request replays the same report |
| Readiness after the report | `waiting` `retry-backoff`, `checks_state` `failed`, not executable |
| `finalize_change` with a well-formed proof for the attempt | Refused `ERR_DELIVERY_ACTION_BUSY` ("failed finalization attempt cannot submit success after retirement") |
| `settle_worker_invocation` (`proof-failed`), fresh application, three acquisitions | `unsupported` `workspace-dirty` each time; no Finalizer acquired; the mutated bytes stand |

The application accepts any well-formed `procedure_id`; procedure registration is an observation-level digest
(`procedure_registration_digest`), not a report precondition. Recorded, not a defect.

**Route audit (D3).** Every `DeliveryReadinessReason` on the candidate (43). Routes: **A** automatic (Delivery or
the page re-reads), **C** continuation prompt (`/continue-change`, Cockpit **Copy continuation prompt**), **E**
engine-authored exceptional prompt in `readiness.prompt`, **K** Cockpit control, **U** genuine user request.
**Pause** and **Abandon** stay available under every custody (`D:test_delivery_progress.py::test_pause_is_available_under_any_custody_and_drains_or_converts`).

| Reason | Route |
| --- | --- |
| `ready`, `report-store-unavailable` | C |
| `target-sync-required` | C (executable `sync-target`); otherwise the workspace reason's route |
| `checkpoint-pending` | C (executable `reconcile-checkpoint`) or A |
| `engine-action-pending` | C (resume the exact operation) |
| `engine-action-interrupted` | C after the owner verifies closure (D03 limit, §1.10) |
| `engine-action-failed`, `engine-action-incomplete`, `engine-action-blocked`, `claim-activation-failed`, `claim-custody-unreconciled`, `coordination-unavailable`, `active-custody` | E `/repair-delivery` read-only diagnosis; `active-custody` also resolves when the owning chat finishes, or K **Release stuck worker** for a stopped chat |
| `builder-transition-contained`, `retry-transition-contained` | E `/repair-delivery` (diagnosis; resume needs host exclusion, D03 limit) |
| `retry-exhausted`, `settled-attention-target-drift` | E `/inspect-change`; a new attempt needs revised authority (`/design`) or **Abandon** |
| `design-attention` | E `/design` (or `/inspect-change` for a retained Builder handoff) |
| `review-repair` | K card command `/address-pr-feedback` |
| `request-action` | U answer form (or **Clear block**) |
| `change-paused` | K **Resume** |
| `change-terminal` | none needed |
| `dependency-wait`, `publication-wait`, `retry-backoff`, `merge-checking`, `checks-running`, `provider-unavailable`, `merge-in-progress` | A |
| `worker-stall-wait` | A (engine settles `worker-host-lost`); its readiness prompt is `/continue-change` |
| `acceptance-wait` | A (page reconciliation) and K **Check again** |
| `merge-approval-required` | K **Approve merge** (or merge in GitHub) |
| `merge-blocked` | The card names one step per block: conflicts or behind → synchronize the target (C, a sync conflict offers `/resolve-target-conflict`); protection, draft, queue, stack, base or method → act in GitHub; failed checks → "fix them, then merge in GitHub" (no prompt names the fixing agent; `/address-pr-feedback` is the nearest route) |
| `merge-response-unknown` | K **Check again**, **Pause**, **Abandon** |
| `finalization-failed` | Settled by the dispatching `/continue-change` (`settle_worker_invocation`), K **Release stuck worker** for a stopped chat; an unmatched settlement stays contained (D03) |
| `runtime-unavailable` | Health panel `/resolve-delivery-attention`; `/repair-delivery` (N08-A) |
| `execution-occupancy-unavailable` | Acquisition-only refusal; rerun C |
| `task-incomplete` | Never emitted on the candidate (listed type only) |
| `workspace-dirty`, `workspace-preflight-failed` (no settled Finalizer attention), `workspace-inspection-failed`, `retry-containment`, `retry-ledger-unavailable` | E `/repair-delivery` read-only diagnosis (R1 (b), lead decision 2026-10-05; pinned by `D:test_portfolio_application.py::test_captured_readiness_agrees_across_public_reads` and `::test_engine_action_prompt_is_applicable_to_final_readiness_state`), plus **Pause**/**Abandon**. No automatic preservation-and-resume route for a dirty finished worktree: accepted limit (§1.10), the user cleans the worktree or abandons. Under settled Finalizer attention `readiness.prompt` stays null and the card names `/inspect-change` and Pause or Abandon (`::test_settled_dirty_finalizer_attention_stays_blocked_after_workspace_cleanup`) |

`DeliveryReadinessReason` and the `_EXPECTED` table agree (`test_every_readiness_reason_has_an_explicit_progress_mapping`).

### 3.2 N10-H — Host journey

- **Prerequisites:** N10-A; D13 and D14; the agent has created the private disposable repository (D14); the user
  present.
- **Setup:** macOS; a disposable project with a tiny Python module (`slugify` with pytest) in the D14 repository;
  OwlBear from a clone at the N10-A merge commit outside every checkout; `setup/init.py` per
  `setup/setup-guide.md` (consumer default, unpinned); one VS Code window for the project. The main checkout's
  live Delivery is not touched. The Change has two criteria: `AC-001` slug rules (automated) and `AC-002` a README
  usage note confirmed by the user (person-only).
- **Editable paths:** this plan (journey record, progress, gaps); execution plan status row. Kit and logs in the
  lane scratch directory.

| Step | User does | Expected | Closes |
| --- | --- | --- | --- |
| 1 Design | `/design`, answers, approves | Admission output names `/continue-change <id>` | J01, J02; N09 R15 |
| 2 Start | **Copy continuation prompt** in Cockpit, pastes it into a new chat | Planner (with challenger), then Builder of the same Change; Cockpit shows progress | V01; N09 G2 |
| 3 Interrupt | Stops the chat while the Builder holds its claim; later **Release stuck worker** (or closes the window); pastes the same prompt | Cockpit shows neutral custody, never working; release refused while the worktree changes, accepted when quiet; the same task resumes with preserved work | U4, J08; N09 G1; V10. N09 G9 only if `needs-decision` for unknown issuer evidence appears (I4) |
| 4 Confirm | Answers the `AC-002` request in Cockpit | Recorded with provenance; the agent never answers it | U3 |
| 5 Revise | **Change requirements**, pastes `/design <id> Change requirements:` with a change to `AC-001`, approves the delta | Pause, revision, delta, activation; only the `AC-001` work is replanned; `AC-002` is not asked again | V14, V15, U6; N04 G4, G5 |
| 6 Finalize | Nothing | Nested Finalizer and `build-reviewer` under `/continue-change`; finalization covers both criteria | N03 G4, N09 G11 |
| 7 Merge | **Approve merge** in Cockpit | One merge at the exact head; **Completed**; worktree cleaned | V01, J05–J07 |
| 8 Refused start | Stops `owlbear-delivery`; the agent backs up and writes a newer format marker to the disposable state; the user starts the server, then runs `/repair-delivery` | VS Code shows the typed refusal; `/repair-delivery` names the upgrade route; marker restored, start healthy | N08 G1 |

- **Evidence:** per step the observed result, the list of user actions (U2: each a prompt, form, control or
  approval), the disposable PR link and the final Cockpit state; recorded in this plan and the docs-only PR. Each
  gap is closed only to the boundary the step actually observed (I4).
- **Failure:** stop the step; D7 (fix PR, rerun the affected steps, repeat the N10-A regression gate on the final
  product-code head).
- **LC:** not applicable. **Size / risk:** M / medium (one session with the user).

#### 3.2.1 N10-H journey record

Disposable project `~/owlbear-n10h/project` (repository `boecht/owlbear-n10h-20261005`), OwlBear clone
`~/owlbear-n10h/owlbear` at `6815cd714`.

| Step | Observed | Status |
| --- | --- | --- |
| 1 Design | First `admit_change` of Change `slug-rules` refused with `ERR_DELIVERY_PORTFOLIO: active package authority does not match the Delivery runtime` (`retry_safe` false). The contract contains `é`, `ß` and `→`. | Stopped; defect H1 (D7) |

**Defect H1: non-ASCII contract digest (fix PR #383).**

- *Cause:* the contract digest is the SHA-256 of the canonical UTF-8 bytes (`target_contract._canonical_json`,
  `ensure_ascii=False`). Admission writes these bytes as `contract.json` and `authority.json` and records their digest
  in the receipt. Four readers serialized the same contract again with `ensure_ascii` left on, which escapes
  non-ASCII text: `DeliveryRuntime.authority_digest`, the snapshot admission check in `delivery_state`, and the
  loader's local-versus-remote comparison and restore of `contract.json`. For `slug-rules` the bytes are 3,766
  against 3,875 and the digests `ecf7aafb…` against `62c7ca7a…`. ASCII-only contracts produce identical bytes either
  way, so the defect showed only with non-ASCII text.
- *Effect:* `_validate_package_authority` refused after admission had already written the receipt, contract,
  frontier, coordination, Change branch record and package authority (`refs/owlbear/packages/slug-rules` at
  `79c734ce`); the Design package snapshot never ran. A retry on the old code is routed to revision activation
  (`_revision_pending` compares the same mismatched digests) and refused with `change-not-paused`, without writes.
  Startup does not complete the admission on either code version. Read-only views show the partial Change as
  planning with an agent next; `/continue-change` must not be started before the admission completes.
- *Fix:* `target_contract.contract_canonical_bytes` is the one contract serialization; the runtime, the snapshot
  check and the loader use it. Persisted formats are unchanged. All live contracts and packages are ASCII
  (read-only scan of 3 runtime contracts and 9 packages), so their digests and bytes are identical before and after.
  The order of admission writes is kept: with the fix, a retried `admit_change` replays the recorded admission and
  completes the snapshot.
- *Recovery rehearsal* (copy of the project in `ubuntu:24.04` mounted at its absolute path, `origin` redirected by
  `url.<mirror>.insteadOf` to a local bare mirror, no provider, the original unchanged): on `6815cd714` startup and a
  supervisor tick change nothing and `admit_change` is refused `change-not-paused` with no record change; on the fix
  `admit_change` replays (receipt `4a3619c3…`, contract digest and runtime digest both `ecf7aafb…`, package
  `98b6f744…` unchanged), creates the Design package snapshot, publishes the Change branch and Delivery state to
  the mirror, and a reload is healthy.
- *Recovery route for the project:* after merge, run `/upgrade-delivery <merge commit>` from the project (the user
  stops and restarts `owlbear-delivery` when asked; no migration is expected, both releases read format 3), then
  the Designer retries `admit_change` for `slug-rules` with the same approved package. Resetting the disposable
  state is not needed.
- *Rerun after merge (D7):* step 1 from the admission retry, then the remaining steps; the N10-A regression gate on
  the final product-code head.

**Defect H7: revision refused by a retained same-task handoff, without a visible way on (fix PR #384).**

- *Observed* (clone at `9faf73796`): Change `slug-rules`, OUT-001 (AC-001) complete. The OUT-002 Builder committed
  the README (`f5e4bc3`), passed review and returned a typed `block` with a person-only confirmation request; the
  orchestrator settled it and the user answered `passed` in Cockpit. Coordination holds a `builder_handoff` for
  TASK-002-01 (route `same-task`, writer `handoff`, branch head `f5e4bc3`, reviewed head `63856f3`) waiting for the
  next continuation. The user then asked to change AC-001 only. The Designer paused the Change (deferred, no claim);
  `revise_design_session` was refused `ERR_DELIVERY_REVISION custody-retained` ("the Change retains worker, handoff
  or snapshot custody"), and `get_change` did not show the handoff, so the Designer could not explain it.
- *Decision (option B, refusal made actionable).* The refusal is specified: N04 §3.2 lists a same-task or
  Planning-route handoff as a `custody-retained` refusal, and D10 rejects carrying a handoff into a revision.
  Allowing it for an unchanged outcome (option A) is not small or safe: activation snapshots the revised package on
  the reviewed head (D7), and `_replace_design_package_snapshot` requires the branch at `last_reviewed_commit` and no
  writer, while the handoff holds the branch at the Builder's head one commit ahead. Snapshotting on that head would
  mark the Builder commit reviewed without a submitted result and move the branch away from the handoff fence
  (`branch_head`, metadata fingerprint), so the Builder could not resume; snapshotting on the reviewed head would
  rewrite the Builder commit and void its exact-commit review. The startup predicate for step 3 (only snapshot
  commits between the snapshot's and the local reviewed head) would also reject either state.
- *Fix:* `custody-retained` caused by a retained non-Design handoff names its outcome, task and route and the way
  on: "OUT-002 retains a same-task Builder handoff for TASK-002-01; Resume the Change, let the waiting worker finish
  that task, then Pause and revise". `get_change` lists each outcome with a retained handoff in
  `unresolved_outcomes[].builder_handoff` (the frontier's `DeliveryBuilderHandoffContext`).
  `w-design-session` tells the Designer to relay that route. Nothing persisted changes; the limit is N04 G9.
- *Recovery route for the project:* after merge, `/upgrade-delivery <merge commit>` from the project (the user
  restarts `owlbear-delivery` and Cockpit when asked; no migration). The Change is still paused and nothing was
  written by the refusal. The user resumes `slug-rules` in Cockpit and runs `/continue-change slug-rules`: the
  OUT-002 Builder resumes TASK-002-01 with its answered confirmation, submits its result and OUT-002 completes. Then
  the Designer reruns the revision with the same AC-001 text (`.owlbear/scratch/slug-rules-revision-1.md`): Pause,
  wait for the deferral, revise, approve, activate. If the Change has reached finalization meanwhile, the refusal
  is `change-finalized` (run `prepare_review_repair`, then Pause).
- *Rerun after merge (D7):* the revision step from Resume; the N10-A regression gate on the final product-code
  head.

**Defect H12: finalization preflight required frontier listing order to be build order.**

- *Observed:* Change `slug-rules`, build order `63856f3` (OUT-001 T1) → `f5e4bc3` (OUT-002) → design snapshot
  `2f78a5e` (revision reopened OUT-001) → `f65f788` (OUT-001 T2, head). The worktree was clean and every result
  reviewed, but readiness stayed `workspace-preflight-failed` ("Managed workspace preflight did not pass.").
- *Cause:* callers pass the promoted result commits in frontier binding order (per outcome:
  `63856f3, f65f788, f5e4bc3`). `_captured_finalization_guard` and `validate_finalization_head` checked
  `pairwise` ancestry in that order, so `f65f788 → f5e4bc3` failed. Any multi-outcome Change where an
  earlier-listed outcome gets a task after a later-listed one hits this.
- *Fix:* one helper `_promoted_chain_is_linear` orders the commits by `git rev-list --count` before the pairwise
  ancestry check; both checks use it. Divergent (sibling) results, a result not below the head and a reviewed head
  not below the head are still refused. No other consumer depends on the order. Nothing persisted changes.
- *Recovery route for the project:* after merge, `/upgrade-delivery <merge commit>` from the project (no
  migration), then `/continue-change slug-rules`; readiness proceeds to finalization.

### 3.3 N10-M — Live migration and programme closure

- **Prerequisites:** N10-H; the user present and authorizing each step.
- **Preconditions:** `F` is `origin/dev` after the N10-H merge; the N10-A regression gate passed on the final
  product-code head (D7); the upgrade rehearsal passed for `F` or for its code head when later commits change only
  documentation (D6); its proposal set is at hand; the user confirms no
  Delivery work runs; `git -C $LIVE fetch origin`. `LIVE=/Users/GGN7H9Q/Projects/owlbear-dev`.
- **Editable paths:** this plan; execution plan §1.2, §2.6, §4.4 and header status; programme section 0 status.

| Step | Action | Expected | On failure |
| --- | --- | --- | --- |
| 0 Facts (read-only) | `delivery_health`, `list_changes`, `get_change` for the three Changes through the running `841b1cffb` controller; GitHub reads of PRs #312, #314, #316 and the issues of R7 | Healthy; three Changes available; no running claim, started action, pending checkpoint or publication | Let work settle; never settle it from this procedure |
| 1 Upgrade | `/upgrade-delivery F` in the main checkout chat (its steps 1–9); the N02 runbook `collisions` check before its step 4 | Proposal equals the rehearsed set: the format 2 → 3 marker of N05-B2 plus only registered rewrites; `verified`; `switch` records `previous` `841b1cffb`; restart healthy; three Changes available and equal to step 0 | Different proposal: stop before `apply`, rehearse again. After the marker: prompt step 10; `switch 841b1cffb` is refused (it reads format ≤ 2, N02 D3); fix forward or restoring the backup is the user's decision (N02 runbook rollback) |
| 2 Align the checkout | `collisions` prints nothing, then `git -C $LIVE merge --ff-only origin/dev` | Prompts and skills in the checkout match `F` (agents read them from the checkout); no live effect | A collision: move it aside with the user (runbook step 1a) |
| 3 `frontier-serialization-contract` | The agent shows its state and N02-A's delivery of its scope (#348, #215); the user confirms (U4) and abandons it in Cockpit; the agent closes PR #314 with a comment; optionally **Clean abandoned worktree** | `get_change`: abandoned; PR #314 closed; a dirty worktree is refused and stays retained | The user declines: stop; §6 completion stays open |
| 4 `delivery-action-readiness` | The agent reads `get_change` and the evidence projection after the upgrade and records them (D15). The user may instead choose abandonment in Cockpit (U3) | Recorded observation of the migrated unfinished record, or abandoned with the reason naming PR #316 (`364daf61`); no Planner, Builder or Finalizer acquired for it | Unreadable after the upgrade: stop and report; repair only through `/repair-delivery` |
| 5 B1 reconciliation | The agent reads `get_change`, `show_operator_context` and the evidence projection and maps each blocker to an existing route: an open request answered in Cockpit; Pause and `/design` revision then activation (N04) for revised requirements; a `delivery-repair` proposal for a recognized state defect; **Release stuck worker** for a stale claim. The user confirms each user-only action (U5) | B1 shows an executable next action for `/continue-change macos-managed-browser-authentication`, or one genuine user request in Cockpit; B1 continues as its own work | A blocker without a route: stop; fix PR (D10); never edit state |
| 6 Issues | The agent verifies each issue's evidence and, with the user's authorization (D12), posts closure comments and closes them | R7 issues closed; #225 open with its reason if N05-D was not built | — |
| 7 Record | Docs-only PR: this plan, execution plan §1.2 (pinned to `F`), §2.6, §4.4 rows and header status, programme section 0: complete | Programme closed (R8) | — |

- **LC:** the step-1 migration is the rehearsed upgrade (D6). **Size / risk:** S / high (live state).

## 4. Progress

| Phase | PR | Head | Proof | Challenge | Status |
| --- | --- | --- | --- | --- | --- |
| N10-P | #374 | gate on `eb185eb3f` | Probes P1–P6; docs only; markdownlint on temporary copies | Sol plan gate round 1: revision-required, 3 findings fix-now, applied 2026-10-05; gate closed | merged |
| N10-A | #382 | code `fddb6d02f` (R1 fix; before it `97f694ab2`); docs after | R1 delta `35160cca2..fddb6d02f`, own runs on `fddb6d02f`: the two updated prompt tests plus the settled-attention and workspace-reason tests (`-k`, 35 passed); the eight affected test files (`test_portfolio_application.py`, `test_delivery_progress.py`, `test_change_workspace.py`, `test_retry_ledger.py`, `test_recovery.py`, `test_worker_stall.py`, `test_target_server.py`, `tests/test_cockpit_work_items.py`) 1398 passed; scoped Ruff check and format clean; agent-ecosystem tests 70 passed; one `uv run test --changed --base origin/dev` (unsharded, 659 s): 3439 passed, 1 skipped, exit 0; Cockpit frontend not rerun (readiness shape unchanged); LC on `fddb6d02f` (live copy, `ubuntu:24.04`, volume `n00a-uv-cache`, 139 live records): upgrade form from `841b1cffb` passed with the same proposal (`runtime/format.json` `format-marker` `fbee38db…` → `f2a27400…`, step `format-2-to-3`), only that record changed, two healthy starts with 3 of 3 available, Cockpit 200 and bundle equal, `verify` true, rollback refused `state-newer-than-controller`; full form passed; `compare` after each `live_unchanged: true`; stages and bundles removed. Own runs on `97f694ab2`: cited node IDs collect (105, exit 0); journey test passed; V08 disposable check recorded (§3.1.1); `uv run test` (full): Python 2 failed, 4707 passed, 1 skipped in 883 s, the 2 failures are 30-s load timeouts of `test_delivery_state.py::test_change_intents_on_planner_pause_of_builder_planning_return_survive_default_loader_restart[historical-*]`, rerun alone 6 of 6 passed (7.3 s each); `npm test` 31 files, 373 passed; scoped Ruff clean on the three changed Python files; `npm run build` ok; `npm run test:e2e:work` 31 passed; agent-ecosystem tests 70 passed; no frontend file changed (Biome not applicable); LC on `56366028d` (code equal to `97f694ab2`; live copy, user authorization 2026-10-05; `ubuntu:24.04`, volume `n00a-uv-cache`; 139 live records): `run --form upgrade --previous 841b1cffb` passed (previous release healthy with 3 of 3 Changes available; preflight `migration-required`; proposal one entry `runtime/format.json` `format-marker` `fbee38db…` → `f2a27400…`, step `format-2-to-3`; applied and verified; only that record changed; switch pinned the candidate, previous `841b1cffb`; two MCP starts healthy with 3 of 3 available and an unchanged round trip; Cockpit 200 and bundle equal; checkout code `controller-not-pinned`; `verify` true; step-9 rollback `switch 841b1cffb` refused `release-refuses-state` / `state-newer-than-controller`); `run --form full --previous 841b1cffb` passed (unmigrated copy refused `state-migration-required` with hashes unchanged; migrated copy loads 3 of 3; previous release's gate hashes unchanged, synthetic newer state refused); `compare` after each: `live_unchanged: true`; stages and bundles removed | Sol implementation gate: pending (lead) | merged |
| N10-H | fix #383 (defect H1); fix #384 (defect H7) | H1 code `4d126f887`; H7 code `1ec148a15`; docs after | Own runs on `4d126f887`: new default-loader test (fails on `origin/dev` with `change-not-paused`, and without either the snapshot or the loader part), `test_delivery_state.py` and `test_target_contract.py` 125 passed, scoped Ruff clean, one `uv run test --changed --base origin/dev` (unsharded, 651.65 s) 3440 passed, 1 skipped, exit 0; live scan read-only: all 3 runtime contracts and 9 packages ASCII; recovery rehearsal on copies of the disposable project (§3.2.1); LC on `4d126f887` (live copy, user authorization 2026-10-05; `ubuntu:24.04`, volume `n00a-uv-cache`; 139 live records): upgrade form from `841b1cffb` passed with the N10-A proposal (`runtime/format.json` `format-marker` `fbee38db…` → `f2a27400…`, step `format-2-to-3`), only that record changed, two healthy starts with 3 of 3 available, Cockpit 200 and bundle equal, `verify` true, rollback refused `state-newer-than-controller`; full form passed; `compare` after each `live_unchanged: true`; stages removed. H7, own runs on `1ec148a15`: `test_design_return_release_refusal_changes_nothing` 6 passed, its new `same-task` case fails with the `origin/dev` sources (message does not match); scoped Ruff check and format clean; agent-ecosystem tests 70 passed; one `uv run test --changed --base origin/dev` (unsharded, 578.77 s) 3441 passed, 1 skipped, exit 0; journey frontier read-only: OUT-002 holds the `same-task` handoff for TASK-002-01 and the Change is deferred, the state the new case covers; LC not applicable (no persisted or loading change); no journey-copy run | — | step 1 stopped; fix in review, then step 1 reruns from the admission retry (D7); H7 fix #384 in review, then the revision step reruns from Resume (§3.2.1) |
| N10-M | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence now | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | Every *planned* citation of §1.7 exists as a merged test | Closed by N10-A: resolved to merged node IDs; 105 cited IDs collect (§3.1.1) | — | N10-A (D4) | Nothing |
| G2 | Every readiness reason has a route (§14.5) | Closed by N10-A R1 (b): the five reasons without a route now expose the `/repair-delivery` read-only diagnosis prompt (43 of 43 routed); the dirty finished worktree without automatic resume is an accepted limit (§1.10) | Route table (§3.1.1); the two updated prompt tests | N10-A | Nothing |
| G3 | The live dispositions match the live facts (PR states, B1 blockers) | Live state not read in P | Execution plan §2.6; N03 plan P1 | N10-M step 0 | N10-M |
| G4 | The rehearsed upgrade matches `F` | `F` does not exist yet; N10-A rehearsed `841b1cffb` → `56366028d` and, after R1, → `fddb6d02f` (same proposal: `runtime/format.json` `format-marker` `fbee38db…` → `f2a27400…`, step `format-2-to-3`; §4 N10-A row) | N02-D rehearsals; N10-A LC | N10-A LC, rerun in N10-M if code changed (D6) | N10-M step 1 |
| G5 | The host journey generalizes beyond one Change, one project and macOS | One session by design | CI on Ubuntu; automated matrix | Documented limit | Nothing |
| G6 | B1 completes after reconciliation | B1's own acceptance (V23, its pilot) | — | B1 | Nothing |
| G7 | V08 complete boundary: a mutating proof yields a persisted `proof-mutation` diagnostic, no finalization and no repeat in a fresh session | Closed by the N10-A disposable check (§3.1.1); its typed-refusal defect fixed | Recorded run; no durable test (D16) | N10-A | Nothing |
