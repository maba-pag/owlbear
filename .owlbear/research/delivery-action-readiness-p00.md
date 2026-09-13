# P00/P01 Historical Evidence and Consolidation

> **Owning request:** Work on wave 00 of the Change-Scoped Continuation redesign.
> **Date:** 2026-09-12
> **Inspected baseline:** `5f978744ad356456ff9d198893690b508b6aa1be`, branch `dev`.
> **Status:** Historical record. The user replaced Delivery-managed programme execution with direct development on `dev` on 2026-09-13. P01/P02/P02-W/P03 code is consolidated; P04 UI is next. Earlier status and launch instructions below describe past events, not current authority.
> **Current plan:** [Direct implementation decision and D00-D08 schedule](change-continuation-delivery-redesign.md#0-direct-implementation-decision).

## Direct-Dev Consolidation

Readiness Change head `7580a8caacbd6f849081adf9f61bf28165b4851c` was merged into `dev`
at `364daf61c`. This preserves the reviewed core, MCP, finalizer/inspection and HTTP work
without rewriting the original commits. The four overlapping local edits and all four
local package files were accounted for; the temporary preservation stash was removed only
after comparison. Product source matches the reviewed Change head.

Unused controller bootstrap additions from `89b6912fa` and `54e43e9c3` were removed in
`c6bf0d82b`: script, dedicated tests, setup guide section and ignore rule. Their Git history
remains available. Selected acquisition and direct-tool fixes remain because they are useful
product/host behavior; direct development does not need to invoke them.

Live Delivery MCP and Cockpit were stopped after verifying no active claims. The local
Delivery MCP registration is intentionally removed for development; other MCP servers,
seed configuration and live state are unchanged. Do not restart against live state as a
test. Existing Delivery records and the merged worktree are retained recovery history,
not an active task board. D1/B1/B5 and unrelated issue worktrees were not merged or deleted.

The next step is **D01 in the active plan**, not a new admission, task acquisition, P00
restart or the historical P02 prompt below. Full WP1 completion still requires readiness
UI and assembled proof. The pre-existing checkpoint replay test remains explicitly open;
no full-suite pass is claimed by consolidation.

Consolidated regression verification: **739 passed** across the core, workspace, report store,
MCP/HTTP, package-boundary, ecosystem and setup selection. Earlier 38- and 234-test runs
overlap this selection and must not be added. No live state migration or product activation
was performed; the known baseline replay failure remains outside this passing selection.

## Historical Handoff Summary

The user approved bringing launch prerequisites forward on 2026-09-12 and selected T3 `GPT-6 Astra (copilot)`, T2 `Claude Opus 5 (copilot)`, and T1 `GPT-5.6 Luna (copilot)`.

Implemented in the main development checkout as approved maintenance, not a managed WP1 task: selected `acquire_actions(selection=...)`, strict MCP input validation, atomic frontier and source fences, nonblocking Change checkpoint locking, retryable capacity/busy diagnostics, explicit already-active response, selected-only pending-publication replay, and retained recovery identities after post-claim launch failures. The original portfolio request remains supported. Existing transaction recovery can complete previously recorded transactions across the shared root; the promise is no new sibling actions, not zero sibling filesystem activity.

The baseline fixes preserve current contracts: disposition errors use `answer`; HTTP requests include the frontier digest; the current answer route restores bounded checkpoint contention; lost-acknowledgement replay respects the existing five-second backoff; admission responsiveness tests supply the required package identity. No failing tests were skipped.

Verification: **622 tests passed** in the expanded readiness/runtime/diagnostics/MCP/HTTP/application/transaction/package-boundary selection, then passed again on release commit `ffd71b158d448678b3f890b751298947da9c0e28` (111.28 seconds, one existing deprecation warning). Counts overlap and must not be added. Independent Claude Opus 5 exact-commit maintenance review reported `pass`, confirmed the parent and all eleven committed paths, and found no blocking defects. This is not a native Delivery task-result receipt. Pre-existing Ruff findings remain in the publication replay code and unrelated existing application tests; no clean whole-file lint pass is claimed.

The host accepted explicit model overrides for each chosen name in read-only probes. That proves the invocation option is accepted, not hidden model identity, Builder-hook execution, or nested reviewer availability. Critical production handoffs must preserve the configured role and its tools. Implementation/review pairings use different families: Astra -> Opus, Opus -> Astra, Luna -> Opus. Do not duplicate agent files or persist model routing in Delivery state solely for this programme.

The user explicitly authorized the bounded release steps: scoped prerequisite commit, exact-commit review, local Design checkpoint, and safe live schema activation. No push, WP1 admission, or P01 launch was authorized by that decision. The live `acquire_actions` schema now includes `selection` with Change/outcome, stage/task, frontier digest, and source head fields; `delivery_health` returned healthy with no diagnostics. No restart was needed and no acquisition call was made.

**Superseded handoff:** the native P02 start below was used before consolidation. Do not execute it now; the active plan starts D01 directly on `dev` and retains the completed backend/wiring implementation.

## 1. Result and Source Authority

The programme is [Change-Scoped Continuation and Recoverable Delivery](change-continuation-delivery-redesign.md). P00 prepares WP1, a single coherent Change named `delivery-action-readiness` covering P01-P04 and the required finalizer-reporting companion task. P05 remains a separate later offline-diagnostics outcome. No one-Change-per-packet split is proposed.

The draft was created and revised through Delivery tools, not direct filesystem edits:

- [Intent](../delivery/packages/delivery-action-readiness/intent.md).
- [Design](../delivery/packages/delivery-action-readiness/design.md).
- Current package ID: `01a0b26301058f483de5a001d60705809e753b78ddfd3dba45b2f2e7ff319a26`.
- Derived contract digest: `6bdd20a63da9ac9386014364b503f8a9adb45f419f2ef5751dfaa725915b8c1a`.
- Compilation: no diagnostics; five commitments, one outcome `OUT-001`, seventeen acceptance scenarios, compiler-derived `SCOPE-001`.
- Local Design checkpoint: `1713c65bd20ed2cc1385c09a67df79a39c60c6b0`, under `refs/owlbear/packages/delivery-action-readiness`; returned package identity unchanged.
- Post-checkpoint derivation: complete result exactly equals the reviewed pre-checkpoint result, including contract, digest, and empty diagnostics.
- No admission, task plan, implementation claim, or new managed worktree exists for this Change from P00.

`derive_delivery_contract` is non-publishing. Empty generated authority before checkpoint is expected; it is not evidence that the compiler failed. The identities above describe the current candidate, not user approval or a runtime launch token.

## 2. What WP1 Will Deliver

One application-owned readiness decision will feed cards, detail, MCP/HTTP responses, and finalization preflight. A dirty worktree cannot advertise executable finalization while a hidden detail field says it is blocked. Verification failures will remain inspectable after restart, with an explicit distinction between checks not run, failed checks, and independent-review findings.

Failure reports are bounded diagnostic observations, not proof receipts or new lifecycle gates. Current engine checks still decide whether retry is possible. Known-unavailable Changes remain visible without making malformed runtime data permissive or pretending an empty portfolio is healthy.

The draft explicitly excludes automatic worktree repair, a continuation controller, new writer fencing, merge mutation, revised B1 acceptance, and tiered dispatch implementation. Those remain later programme work or the proposed bootstrap prerequisite below. This first slice does not claim `/continue-change` already exists.

The final candidate also contains per-Change workspace-inspection failure handling, contained host-local report storage under the configured runtime root, and a proposed `/inspect-change` prompt restricted to two read-only tools. Effective host restrictions are a release gate; the prompt and report store have not been implemented during P00.

### Initial controlling source anchors

| Source | Verified fact |
| --- | --- |
| [Work-item projection](../../serve/delivery/src/owlbear_delivery/work_items.py) | `_finalization_action_available` checks stage/claims, not workspace cleanliness. |
| [Application](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | `show_work_item_view` enriches publication readiness separately; `show_finalization_context` invokes workspace validation; `get_change` first requires a runtime. |
| [MCP adapter](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py) | `acquire_actions` takes an empty request and calls portfolio-wide acquisition. |
| [Contract compiler](../../serve/delivery/src/owlbear_delivery/target_contract.py) | Planning scopes are derived from outcomes, not hand-authored task surface lists. |
| [Runtime transactions](../../serve/delivery/src/owlbear_delivery/runtime_transaction.py) | Existing replayable immutable/replacement participants are suitable candidates for bounded diagnostic persistence. |
| [Builder role](../../share/agents/builder.agent.md) | Builder is pinned to `GPT-5.6 Luna (copilot)` at inspection time. Top-level model selection does not establish a different worker model. |
| [Designer role](../../share/agents/designer.agent.md) | Design runs through manifest-bound tools and independent challenge. |
| [Cockpit attention route](../../serve/cockpit/src/owlbear_cockpit/routes/target_work.py) | Current route delegates to `answer`, not the removed adapter operation assumed by some tests. |
| [Cockpit request models](../../serve/cockpit/src/owlbear_cockpit/target_models.py) | Attention resolution requires `expected_frontier_digest`. |

Live read-only observations during preparation: Delivery health reported healthy; B1 remained at Planning with a user request, and D1 had completed task work with finalization outstanding. Neither was acquired, paused, revised, or otherwise manipulated to force a desired scheduling order.

## 3. Independent Review and Adjudication

Successive read-only `designer-challenger` reviews were obtained. Their results are advisory; no review substitutes for user approval or a clean baseline.

### First review

The first candidate compiled but had unresolved token/persistence details and overbroad privacy wording. Findings accepted and addressed in the current candidate:

- Remove a redundant observation-context token; use existing expected identity/head fences and a diagnostic sequence.
- Restrict persisted report input structurally; do not promise arbitrary-secret detection.
- Define diagnostic persistence location, bounds, idempotency, and restart behavior.
- Specify retirement of a same-candidate failure pointer after successful finalization while retaining immutable history.
- Include the tagged unavailable variant in the registered MCP contract and list/detail proof.
- Name the agent-config reporting companion explicitly as P02-W, a native domain-local task within the P02 session rather than another primary user launch.

Two claims were not accepted as stated: empty `authority.json` before checkpoint is not a failed non-publishing derivation, and absence of authored SCOPE prose does not mean the compiler omitted a scope. The second reviewer was supplied the compiler output and confirmed both corrections.

### Earlier review and corrections

Pass: Change identity, COM-002, COM-003, COM-004, SCOPE-001.
Warnings: COM-001, COM-005, OUT-001. No error dispositions.

Warnings subsequently corrected through Design tools:

1. **Single phase owner:** explicitly name one internal pure phase resolver reused by the readiness capture and projector. Do not create another lifecycle implementation merely to avoid recursion.
2. **Selected acquisition prerequisite:** declare the missing scoped launch route as an actual prerequisite rather than implying the current commitment is enforceable today. Do not weaken the no-unrelated-acquisition requirement.
3. **Acceptance locator:** AC-012 should reference the Design's named implementation/proof surface section, not imply that generated `SCOPE-001` itself contains editable paths.

Subsequent review also identified workspace-inspection failure semantics, report-root containment, and a read-only prompt boundary. The current candidate resolves those with AC-015, AC-016, and AC-017 respectively; it explicitly includes P02-W in COM-005 and uses the readiness status `complete` consistently.

### Final review of the current candidate

Claude Opus 5 reviewed the package and compiler output identified in section 1. The Change identity, COM-001 through COM-004, OUT-001, and SCOPE-001 received `pass`. COM-005 received `warning`; no entity received `error`.

The remaining warning is that prerequisite release/activation, effective model and independent-review dispatch, and selected-only acquisition are process gates, not additional WP1 acceptance scenarios. Release commit review and live schema inspection now satisfy the first gates. Model-name probes do not prove hidden model identity or the effective nested native worker route; that remains a launch-time gate. No further Design revision is required for this warning.

Checkpoint and post-checkpoint derivation completed after explicit authorization. The checkpoint implementation in [design_package.py](../../serve/delivery/src/owlbear_delivery/design_package.py) writes a Git commit and local package ref without changing the product branch or index; it is not remote backup and is not Design approval.

### Exact prerequisite release review

Release commit `ffd71b158d448678b3f890b751298947da9c0e28` has parent `5f978744ad356456ff9d198893690b508b6aa1be`. Independent Opus review resolved the commit, inspected the full eleven-file diff, and matched inspected files to committed blobs. It confirmed selected-only acquisition/replay, capacity enforcement, frontier CAS, nonblocking checkpoint locking, stale/busy retry classification, strict MCP validation, post-activation recovery identity, and the bounded attention/backoff fixes.

An initial Explore review lacked terminal access and withheld a disposition; it is not counted as review evidence. A fresh Opus reviewer with read-only Git access returned `pass`. Known nonblocking limits: selected acquisition does not automatically recover expired claims, which can retain capacity occupancy; a selected runtime reconciliation failure may return the generic no-claimable-action diagnostic. Neither permits a new claim or redispatch.

## 4. Initial Baselines and Their Resolution

Commands were executed against the existing checkout with disposable test fixtures. They made no product-code changes. Counts are per command; the focused rerun overlaps the core run and is not additional coverage.

### Transport and projection baseline

```shell
uv run pytest serve/delivery/tests/test_work_items.py serve/delivery-mcp/tests/test_delivery_adapter.py tests/test_cockpit_work_items.py -q --tb=short -n 0
```

Result: **178 passed, 4 failed**, one existing deprecation warning.

| Failure | Evidence and classification |
| --- | --- |
| `test_named_runtime_catalog_and_integration_failures_preserve_diagnostics` | Calls absent `TargetMCPAdapter.resolve_change_disposition`; current adapter uses the newer public interface. |
| `test_stale_attention_resolution_route_is_not_retry_safe` | Sends no required frontier digest; gets 422 before the expected conflict behavior. |
| `test_busy_attention_resolution_route_is_retryable_conflict` | Also omits required frontier digest; gets 422 rather than the asserted 409. |
| `test_real_attention_resolution_route_fails_fast_on_held_checkpoint_lock` | `_LockOnlyPortfolioApplication` lacks `_coordinator`, which the route's current `answer` path requires. |

The first three exhibit test/contract drift. The fourth also raises an unresolved question about preserved busy/lock behavior. Updating fixtures is not automatically sufficient: a repair must exercise current stale/busy semantics instead of deleting those checks or restoring retired interfaces just for tests.

### Core application and transaction baseline

```shell
uv run pytest serve/delivery/tests/test_portfolio_application.py serve/delivery/tests/test_runtime_transaction.py -q --tb=short -n 0
```

Result: **287 passed, 1 failed**.

```shell
uv run pytest serve/delivery/tests/test_portfolio_application.py::test_reconcile_checkpoint_replays_pr_after_lost_local_acknowledgment -q --tb=short -n 0
```

Initial result: **1 failed**, reproduced independently. Replay returned `reconciled=False` with `ERR_DELIVERY_RUNTIME_CONFLICT` and `interrupted acknowledgment`. Subsequent investigation established that the fixture retried at a fixed time before the current backoff expired. The approved correction asserts no provider retry before eligibility, advances the fixture clock five seconds, then verifies replay. The backoff implementation was not weakened.

The current Design workflow requires passing baselines before checkpoint/approval/admission. These initial failures were resolved through the expressly approved maintenance work, with the expanded 622-pass selection recorded above. The historical failures remain here to explain the changes, not as current test failures.

## 5. Launch Prerequisite: Initial Gap and Implemented Contract

Initial acquisition iterated eligible portfolio candidates and could return multiple launches. An exploratory suggestion that its lock guaranteed one packet per session was rejected against the controlling source. The approved maintenance adds a separate selected branch to the existing public operation; the live registered schema now exposes that selection.

The requested schedule therefore has a bootstrap dependency: it asks P01 to use selected-packet execution before P06 introduces Change-scoped acquisition. Current role pins also prevent assuming that a T3 primary chat becomes a T3 Builder.

### Approved bounded preparation before P01

The user explicitly approved bringing forward these prerequisites:

1. An agent reconciles the five baseline failures with current contracts, adds or preserves discriminating stale/busy/replay proof, and obtains independent review. This is bounded platform maintenance, not a WP1 implementation hidden inside P00.
2. Provide selected Change and expected stage/task acquisition that validates readiness and custody through the existing engine before claiming anything. It must reject a different next task rather than acquire and later discard unrelated work. Planner-stage selection has no invented task ID; Builder selection binds the actual published task identity.
3. Establish an explicit worker model binding for the approved tier profiles and verify the actual dispatch route. Model prose alone is insufficient. Preserve existing tool restrictions and independent review.

Do not move the whole continuation controller, automatic finalization, repair engine, or merge flow forward. The later P06 work reuses this narrow selected-launch capability. Do not create a worktree per packet, call private claim activation, edit Delivery JSON, change capacity to manipulate candidate selection, or pause B1/D1 to make the desired launch happen.

The maintenance was performed in the shared development checkout after checking for tracked edits, not in a new isolated workspace. No managed Change worktree was edited. Concurrent edits to the existing publication-replay area were preserved. The authorized commit contains only the eleven inspected prerequisite source/test files; its replay-region delta is the selected-Change filter. An independent exact-commit maintenance review followed the earlier working-tree review.

### Selected acquisition payload and operator contract

```json
{
	"selection": {
		"change_id": "delivery-action-readiness",
		"outcome_id": "OUT-001",
		"expected_stage": "planning",
		"expected_task_id": null,
		"expected_frontier_digest": "<current engine-projected digest>",
		"expected_source_head": "<current reviewed managed source head>"
	}
}
```

For Builder acquisition use `expected_stage=implementation` and the actual engine-published next task ID. The agent loads those values; the user does not supply them. A wrong next outcome/stage/task or stale frontier/head is rejected before claim activation. Capacity and checkpoint contention are retryable waits. An already-active claim returns no launch and explicitly forbids redispatch; inspection and confirmed-termination recovery remain separate. Pending publication replay operates only on the selected Change and may require a refresh if its frontier moves.

The operation returns at most one launch. Its role/worker identity remains engine-selected. A permitted host invocation can call `runSubagent` with that role's `agentName`, the complete serialized launch, and the explicit approved `model` override. It must not substitute a general-purpose worker or override tools/hooks. Planner needs an actual planning claim and returns a plan only; each later Builder launch binds the native task. If the host lacks model override or reviewer nesting, stop before claim acquisition and expose that precise capability gap.

Before using this payload live, the agent must inspect the registered `acquire_actions` schema and see `selection`, not assume the running process reloaded source. P00 observed that live schema and healthy Delivery after committing the prerequisite source. No restart or acquisition was necessary. Recheck the schema in the later launching session; an MCP restart, if needed there, is not permission to acquire B1/D1.

## 6. Packet-to-Task and Worktree Mapping

| Primary packet | Planned task boundary | Model requirement | Start condition |
| --- | --- | --- | --- |
| P01 | Delivery core readiness/diagnostic owner and tests | Astra implementation, independent Opus review | Approved WP1 Design, passing baseline, published task plan, exact selected acquisition/model route |
| P02 | MCP schema/adapter task, then P02-W agent-config reporting task serially | T2; T3 reviews consequential finalizer-boundary changes | P01 result present in this Change's managed baseline |
| P03 | Cockpit HTTP adaptation and tests | T2 | P01/P02 contract and earlier reviewed tasks available |
| P04 | Cockpit display of engine-selected readiness and supplied fixtures | T1, independent T2 review | P03 contract ready; no unresolved policy logic assigned to the UI |
| P05 | Separate offline read-only diagnostics outcome | T2, independent T3 boundary review | P01 diagnostic contract and its own approved task/custody context |

The first four primary sessions use the same future WP1 Change worktree, serially. Its concrete path is engine-assigned after approved admission; no path or claim is granted by this table. P02-W is internal task sequencing, not a new user-launched wave. Planner publishes native task IDs from the approved contract; P00 does not fabricate those records.

Parallel is **not authorized now**. P05 may overlap P02/P03 only after distinct coherent Change custody, source inputs, file reservations, and capacity are verified by the outgoing owner. No new P05 package was created in this pass.

The original Design preparation owners are retained in programme section 12.4: P06 for continuation, P08 for provider/merge, P10 for recovery/retry, P12/P13 for revision/evidence, P15/P16 for assistance, and P19/P20 for maintenance/cutover. This is historical scope mapping, not the active schedule or evidence of completed designs.

## 7. Conditional P01 Handoff

**Historical P01 draft, superseded by section 14.** This preserved text records the original gated handoff and must not be used to reacquire the completed TASK-001.

```text
Implement P01 for delivery-action-readiness only after P00 marks NEXT START ready.
Read .owlbear/research/delivery-action-readiness-p00.md and the verified Design
package through read_design_session. Require its current approved contract and
the exact engine-acquired Planner/Builder context for this task; do not infer a
claim from this research or call portfolio-wide acquisition to find the task.

Implement the application-owned readiness capture/decision and bounded host-local
diagnostic persistence described in the approved Design. Reuse the pure phase
owner and current managed-workspace validation. Reads create no claims or reports.
Keep diagnostic reports non-authoritative and leave current proof/custody guards
unchanged. Test dirty/clean readiness, degraded state, stale report basis, replay,
transaction interruption and same-candidate success retirement at their owners.

Own Delivery-domain paths and tests only. Do not implement P02/P03/P04, automatic
repair, continuation, model routing, provider merge, or changes to live B1/D1.
Use builder with explicit GPT-6 Astra (copilot) override and independent
build-reviewer with Claude Opus 5 (copilot), preserving both role boundaries.
Verify the live selected schema and host reviewer capability before acquisition. Resolve current test
commands from manifests, preserve existing user changes, and submit only the
reviewed exact result through the approved task route.

Return the exact result/evidence and complete P02/P03/P05 handoffs, including
which starts are actually ready and whether isolation permits parallel work.
Do not start the next primary packet session automatically.
```

## 8. Closeout and Release Gates

- Completed: WP1 candidate, compiler output, independent Design review, local checkpoint and deterministic re-derivation, source-grounded packet/domain mapping, conditional P01 handoff, approved model profiles, committed/tested/independently reviewed selected-launch prerequisites, and live schema/health verification.
- Implemented only under the additional user approval: prerequisite baseline corrections and selected acquisition. WP1 readiness/failure-report product work has not started.
- Still gated: explicit Design approval/admission, native task planning, effective nested worker dispatch verification, and a verified exact P01 launch.
- No live Change was acquired, no existing B1/D1 acceptance was changed, no managed worktree was repaired, no GitHub mutation or push occurred, and no server restart was performed by this session.
- Task-specific findings remain in this research, not institutional memory. Review warnings and remaining approval gates are not implementation permission.

The preceding closeout records P00's state. The later wave 01 request and explicit admission approval supersede its approval gate; the current state and remaining prerequisite are below.

## 9. Wave 01 Admission and Target Baseline Blocker

On 2026-09-12 the user selected **Approve WP1 and proceed with wave 01** after presentation of the complete scope, exclusions, limits, reviewed package, and contract digest. The verified complete package and derivation were unchanged before and after approval. Approval authorizes managed admission, native planning, and P01 implementation/review only, with no P02 launch or merge.

Delivery admitted `delivery-action-readiness` with the approved contract digest `6bdd20a63da9ac9386014364b503f8a9adb45f419f2ef5751dfaa725915b8c1a`:

- Admission receipt: `b205b2e362aea0b78042ced71faf87da5902c5f2a6e181e5d596f8b8a6ca7f9a`.
- Admission checkpoint: `e1ff5eea6e441c9049c87f3438b7025b68840822`.
- Outcome/scope: `OUT-001` / `SCOPE-001`, Planning, no tasks or active claim.
- Managed branch: `owlbear/change/delivery-action-readiness`.
- Managed worktree: `.owlbear/delivery/worktrees/delivery-action-readiness`.
- Draft publication: [PR #316](https://github.com/maba-pag/owlbear/pull/316).
- Managed source/reviewed head: `52ff53fc983b60440942ced2f3ecf3e760b141b8`.
- Admission-generated package snapshot identity: `553f95f0087a7f1279052e1e1c68750d9a7ef27da053d90124605176661377c7`. This is the generated admitted package, not a new authored approval.

Read-only named Planner and Builder preflights ran. Builder successfully dispatched its permitted `build-reviewer` with the approved Opus override, and that reviewer reported callable read-only Git/terminal access. Required Delivery tools were advertised but deferred activation inside those workers was not fully verified; do not confuse this with successful execution of a native claim or hidden model attestation.

**Observed blocker:** the managed source is based on `bf244faa59f3cc994b59f7ced88211babd033b33`, the current `origin/dev`. Local `dev` remains `ffd71b158d448678b3f890b751298947da9c0e28`, 61 commits ahead, with the reviewed P00 prerequisite changes. Read-only Git showed that the managed source does not contain those changes. The 622-pass local baseline therefore does not prove this managed baseline. Earlier P00 release wording omitted this remote-target prerequisite; live engine schema activation is not managed worktree source activation.

[Delivery configuration](../delivery/config.json) selects `origin` / `dev`. [Target synchronization](../../serve/delivery/src/owlbear_delivery/change_workspace.py) fetches that remote target before merging it in the managed worktree; it cannot import the unpublished local `dev` head by changing the request's expected hash. [Workspace governance](../../share/skills/r-workspace-governance/SKILL.md) reserves pushes to the user. Publishing local `dev` would publish all 61 ahead commits, not just P00, so it is not a routine implicit side effect of this packet.

**Resume route:** once the intended local baseline is published to `origin/dev`, the agent verifies the remote head, invokes the existing Delivery target-sync operation with its exact expected target, verifies the managed source includes the prerequisites, and refreshes selected Planning inputs. Then dispatch Planner for the reviewed native chain and Builder for P01 only. Do not repeat Design approval for unchanged meaning. Do not copy or cherry-pick prerequisite files, retarget the remote, acquire against the stale baseline, or broaden P01 to reimplement maintenance.

No wave 01 source edits, claim acquisition, manual worktree mutation, target sync, push, or P02 launch occurred. B1/D1 were unchanged. The admitted Change and draft PR remain available; no rollback or abandonment is needed.

## 10. Authorized Publication and Planning Retry

The user subsequently authorized whatever is necessary to finalize wave 00 and work on wave 01. This explicitly superseded the earlier no-agent-push constraint for the required prerequisite publication. A normal, non-force `git push origin dev:dev` published the reviewed `ffd71b158d448678b3f890b751298947da9c0e28` baseline; remote readback matched. No unrelated untracked files were staged.

Delivery target sync `p01-prerequisite-sync-ffd71b158` returned receipt `48292900f688662f10ae7c3dfeb596069d9bb8d486b72c3c1988ce25df84cd9e`, managed head `63f52914f8e1e16c8436b51277e49ffc4885c647`, and `review_required=false`. Read-only Git confirmed a clean managed worktree and exact equivalence to the 622-test baseline for `serve/`, `tests/`, `share/`, `pyproject.toml`, and `uv.lock`.

The first selected Planning claim was `28df05f2-6774-4702-8d16-a3cf8925f083`, attempt `ac12ab65-f6dc-4e3a-99c9-a3f6c5f6b523`. Planner obtained three candidate reviews but published no plan. It returned `retry` with `failure_code=plan-source-owner-mismatch` and an `attempt_id`. Delivery rejected that transition because Planning retry does not accept attempt commit identity. The completed invocation was recovered through exact `recover_claim`; result `recovered`, no preservation/quarantine/attention, and the outcome returned to unclaimed Planning with no tasks.

Persisted reviewer evidence identifies local Planning corrections for the next candidate, not new Design requirements:

- Portable snapshot/export ownership is [delivery_state.py](../../serve/delivery/src/owlbear_delivery/delivery_state.py), covered by [test_delivery_state.py](../../serve/delivery/tests/test_delivery_state.py). P01's AC-016 export-exclusion observation must name that real owner and authorize its test surface. Do not name nonexistent `state_store.py`.
- A new registered MCP tool requires the P02 task to own the canonical inventory in [serve/delivery-mcp/README.md](../../serve/delivery-mcp/README.md), as well as actual registry/grant tests. The Knowledge persistence-wiring test is not a Delivery proof owner.
- The read-only inspection task must explicitly own [validate_prompts.py](../scripts/validate_prompts.py) and its tests for the built-in Ask agent name. Its current built-in allowlist does not include Ask; this is a concrete requirement, not conditional frontmatter-shape work.
- A Planning retry must omit `attempt_id` and `abandoned_commit`, which belong to Implementation retry. This is engine validation, not permission for the caller to rewrite a returned worker transition.

These notes are discovery evidence only. A fresh Planner must validate the current launch/context, form the complete corrected native chain, obtain its configured independent review, and publish through the existing tool. P01 remains unimplemented; B1/D1 remain untouched.

## 11. Published Plan and Builder Host Blocker

The second selected Planner claim `2ca853b7-6ba0-4c72-9879-340a2cbaedb7`, attempt `1022120b-53dc-4722-9853-0f2ba1f5a395`, published an independently reviewed plan and returned `advance`. Delivery accepted that unchanged transition. Plan output `plan-68d25ea2cbdfb3bb1e756971655a36ffe24c228ba008657b05c3cba5ef6c519e` has digest `68d25ea2cbdfb3bb1e756971655a36ffe24c228ba008657b05c3cba5ef6c519e`.

| Native task | Packet | Scope |
| --- | --- | --- |
| TASK-001 | P01 | Delivery readiness capture and bounded finalization reports |
| TASK-002 | P02 | Registered MCP reads and diagnostic reporting |
| TASK-003 | P02-W | Finalizer reporting and read-only inspection prompt |
| TASK-004 | P03 | Cockpit HTTP readiness and degraded projections |
| TASK-005 | P04 | Cockpit controls and inspection handoff |

These are sequential tasks in the same Change worktree. Read fresh engine task authority before execution; the table is not a replacement task definition. Only P01 execution is authorized in this session.

P01 acquisition bound TASK-001 to claim `5242e241-0035-485c-bf3a-8df0d04855bf`, attempt `657e0950-5aeb-43dd-b2d7-f86d507cca1e`, source/reviewed head `63f52914f8e1e16c8436b51277e49ffc4885c647`. Named Builder with the approved Astra override returned `dispatch_failure` at `show_build_context`: that operation was deferred, but the child exposed no `tool_search` to load it. It made no edits. Exact recovery returned `recovered`, preserved the existing source head at `refs/owlbear/attempts/delivery-action-readiness/657e0950-5aeb-43dd-b2d7-f86d507cca1e`, and required no quarantine or attention. This preserved head is not an implementation result.

**Host evidence:** [builder.agent.md](../../share/agents/builder.agent.md) already grants `vscode/toolSearch`. The installed Copilot extension's structured `languageModelToolSets` metadata includes `toolSearch` in the `vscode` set, so no permission-name correction is established. A fresh claim-free Builder probe again exposed only `functions` and `multi_tool_use`, with no callable discovery function; `show_build_context` and `submit_result` remained advertised but deferred. The parent could load these operations, but its capabilities do not establish the child's direct custody check. No agent grants, hooks, or workflow safeguards were changed.

**Safe retained state:** outcome Implementation, all five tasks retained, zero results, no active claim or writer, clean managed worktree at the reviewed head above. P01 product implementation and P02 have not started. Do not repeat admission or Planning merely because the host session is new.

**Superseded recovery advice:** the user reloaded and retried; Builder still reported missing discovery. Do not repeat the reload-only advice. Section 12 records the tested repair; the historical prompt below was revised to accept either directly bound tools or successful discovery.

**Retired launch prompt: do not execute.** Use D01 in the active plan instead.

```text
Resume wave 01 for delivery-action-readiness only. Read section 11 of
.owlbear/research/delivery-action-readiness-p00.md. WP1 is approved, admitted,
and has a reviewed five-task native plan; do not reapprove, readmit, or replan.
First verify that the named builder host has directly callable show_build_context
and submit_result, or can load them through discovery, and can dispatch its named
build-reviewer. Preserve Astra implementation and Opus independent review.
If verified, read current engine fences, acquire TASK-001 only through selected
acquire_actions, and dispatch its unchanged launch to builder. Implement, test,
commit, independently review, and submit P01 in the managed Change worktree.
Stop before TASK-002/P02. Do not bypass missing tools, copy caller custody
evidence, edit Delivery state, or substitute an unrestricted worker.
```

## 12. Tested Host Deferral Repair

After the reload failed, installed VS Code/Copilot 0.65.0 metadata confirmed that
`chat.agentHost.copilot.toolSearch.enabled` defers MCP and non-core tools behind
discovery. The workspace had explicitly enabled it. Setting it to `false` in
[workspace settings](../../.vscode/settings.json) exposed Builder's existing allowed
`show_build_context` and `submit_result` bindings directly. This increases upfront
tool-schema context; it does not widen the agent allowlist, disable hooks, or waive
custody. It is a workspace workaround, not proof that VS Code's discovery defect is fixed.

A claim-free named Builder probe actually invoked `show_build_context` with a
recovered claim and received the engine's expected inactive-identity error. This
proves reachability, not custody. A subsequent launch still stopped because it
treated the separate deferred-tool inventory as overriding actual bindings. Claim
`33a71b47-16b9-483e-a250-e9e4dd0a1f0f`, attempt
`640096c7-b856-4418-80cc-c7a136b61d55`, was recovered with no edits or quarantine.

[Packet Building Step 0](../../share/skills/w-packet-building/SKILL.md) now makes
actual callable definitions decisive for its mandatory custody read: call an
already-bound tool; otherwise load it through discovery; if neither exists,
return `dispatch_failure`. A name in prose alone never grants a callable tool.
A fresh named Builder following this rule reached the engine's inactive-claim
error and confirmed `submit_result` directly bound without invoking it.

Focused validation: `uv run --locked pytest tests/test_agent_ecosystem_validation.py
-q --tb=short -n 0` passed all 30 tests; edited settings and workflow have no editor
diagnostics. Actual P01 execution remains a separate gate and must use a fresh
engine-acquired claim after the repair reaches the managed source.

## 13. Released Workaround and Dispatch Evidence Handoff

The workaround is commit `4ef59274098ed036c1cdc3f837a9746b1acbb6bc`, independently
reviewed by Opus with `pass`, and all 30 ecosystem tests rerun on that commit passed.
It was pushed normally to `origin/dev`. Delivery target sync
`p01-direct-tools-sync-4ef592740` returned receipt
`9441387c279f3eb8e10eba0aeddd4df443b44569716824167e48e0bd2f78dd15` and managed reviewed
head `f41ae7c4897a54ea48e3cfb5ff5c23d737a0cc05`, with `review_required=false`.
The original tested prerequisite `ffd71b158` is an ancestor of that source.

The current installed versions are VS Code 1.137.0 and bundled Copilot 0.65.0. No
version or rollout history establishes the exact cause/date of discovery disappearance.
Keep `chat.agentHost.copilot.toolSearch.enabled=false` temporarily in this workspace;
its cost is more upfront schemas, not wider permissions. Do not change seed defaults
or remove the agent's discovery grant based on this workspace-specific observation.

Caller-observed evidence available to the next Planner:

- The named Builder was invoked using `runSubagent(agentName="builder",
	model="GPT-6 Astra (copilot)")`. The host accepted that invocation and returned a
	role-bound result. This records the explicit requested route, not hidden model identity.
- A fresh claim-free Builder directly called `show_build_context` on recovered claim
	`33a71b47-16b9-483e-a250-e9e4dd0a1f0f`; Delivery returned the expected inactive-identity
	error. Builder also reported the directly callable `submit_result` schema without
	invoking it. No discovery was needed. Earlier named Builder-to-`build-reviewer`
	dispatch with explicit Opus override succeeded with read-only Git access.
- Selected acquisition returned only TASK-001, with attempt
	`d9237edb-bc48-4ed3-b487-b137eb9ba1de`, claim
	`bf088c78-a48b-4a99-96b7-a6b708c0669b`, and source `f41ae7c4` above. The actual Builder
	obtained fresh context and reported passed custody checks, with no file changes.
- Builder returned to Planning on `TASK-001.constraints[0]` / `COM-005`: its fresh Build
	context did not contain prerequisite or effective-model evidence, and the default
	Builder frontmatter names Luna. The caller forwarded that return unchanged. Delivery
	accepted it, released the claim, and cleared the old plan while retaining return context.

The default `model:` value is not evidence that an explicit host override was ignored.
Conversely, accepted dispatch arguments are not hidden model attestation. The approved
Design already distinguishes these. Planning owns a concrete, source-grounded evidence
handoff that preserves the approved Astra/Opus route and independent review without
demanding an unavailable hidden identity. This document supplies observations, not
permission to rewrite task authority or bypass direct Build custody. Validate these
sources and incorporate needed evidence in the corrected native task before review.

## 14. P01 Submitted Result and Wave 02 Handoff

The user confirmed submission of existing evidence through
`AR-OUT-001-LAUNCH-PREREQUISITE`, with explicit limits: authorization to submit agent
observations is not user technical attestation, hidden-model proof, or an acceptance
waiver. The resolved request now carries release, live-schema, direct-call and named
reviewer-route evidence into native Planning and Build context.

Planner published reviewed plan `plan-098350cf614c0eefbbd80315597c4e13ea34c8341638f3544652098a9da90f11`
under claim `d08193ea-21dd-4d85-9926-17dfcc0623b9`. The corrected TASK-001 reuses
the resolved caller evidence rather than requiring Builder to recreate absent
pre-acquisition evidence. Delivery accepted the unchanged advance transition.

Named Astra Builder acquired TASK-001 with claim
`07a602a5-e671-457d-9865-a90c324f467b`, attempt
`ccc0e3b7-1102-4dff-9156-87e0d5ff1ed1`, and source
`513a72b471e77d411c46fe0139d3dcddff922768`. It implemented readiness capture, degraded
Change views and bounded host-local finalization reports, then repaired two concrete
independent-review findings concerning cleanup/recovery projections. Preserved commits:

- `4600af1fc`: initial P01 implementation.
- `a5a2af180`: preserve publication cleanup and recovery detail.
- `4bf2365180c2851723fa09d91fa48a209220eb33`: suppress recovery after recorded cleanup;
	final independently reviewed and submitted candidate.

Delivery retained result `result-task-001-4bf2365180c2` with task digest
`d2721b2f0de8dbe0f5f0065d09b989433db84b8dd335233b0abf8d712681f91e`, observation
`70de62a863b012e3fe412819411e28709ccbd2e3e0fbb923126fdee5e06f1cfb`, and independent
`build-reviewer` pass `9c466f8187d762773f06547f45760ded661aed1e90fe977af687d5cc75589bc1`.
The parent verified these identities against persisted engine state and did not apply
a duplicate transition. The candidate is published on the managed Change branch in
[PR #316](https://github.com/maba-pag/owlbear/pull/316), not merged into `dev`.

**Proof:** 465 maintained core tests passed on the exact submitted candidate, covering
application, Work Items, workspace, transactions, portable Delivery state and the new
report-store suite. The broader changed-scope run reported **1195 passed, 1 failed**:
[test_checkpoint_publication_regressions.py](../../serve/delivery/tests/test_checkpoint_publication_regressions.py)
`test_checkpoint_snapshot_replays_after_publication_failure`. Independent review found
the relevant checkpoint/backoff implementation unchanged. The parent also reproduced
that exact failure on the primary checkout without P01, confirming it is pre-existing.
The broader suite is not green; no test was skipped or weakened to accept P01.

**State at P01 submission:** one submitted task result; four later tasks retained; no active claim
or writer; clean managed worktree and reviewed head `4bf2365180c2851723fa09d91fa48a209220eb33`;
Delivery health returned `healthy` with no diagnostics. P02, HTTP/UI integration,
finalizer wiring and whole-Change acceptance remain unimplemented. These are later
tasks, not features claimed by the P01 core result.

**Setting decision:** keep `chat.agentHost.copilot.toolSearch.enabled=false` for now.
The workaround succeeded through a real Builder context read, implementation, nested
review and submission, not only a claim-free probe. It loads permitted schemas upfront
without changing tool grants or hooks. The cause of the earlier menu disappearance
and its exact version/rollout timing remain unverified. No further reload is requested.

### Superseded Next Packet

The original P02 prompt is retired. P02, P02-W and P03 have since been implemented
and merged into `dev`. Use D01 from the active plan for the remaining UI and assembled
proof; do not acquire another Delivery claim for this programme.

P05 remains a separate unadmitted offline-diagnostics outcome. No P05 launch or parallel
work is authorized by the retired WP1 task plan. Core DTOs and report-store behavior
at the reviewed P01 commit are its future source inputs, not admission authority.
