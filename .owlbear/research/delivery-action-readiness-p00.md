# P00: Delivery Action Readiness Preparation

> **Owning request:** Work on wave 00 of the Change-Scoped Continuation redesign.
> **Date:** 2026-09-12
> **Inspected baseline:** `5f978744ad356456ff9d198893690b508b6aa1be`, branch `dev`.
> **Status:** P00 baseline published and synchronized; WP1 approved, admitted, and natively planned. P01 stopped before editing because the named Builder host lacks callable tool discovery for its deferred context tool. Its claim was recovered; managed worktree is clean with no writer. See section 11.
> **Scope:** P00 design/context plus explicitly approved baseline and selected-launch prerequisite maintenance. No WP1/P01 implementation, task acquisition, repair of live B1/D1, or admission was performed.

## Current Handoff Summary

The user approved bringing launch prerequisites forward on 2026-09-12 and selected T3 `GPT-6 Astra (copilot)`, T2 `Claude Opus 5 (copilot)`, and T1 `GPT-5.6 Luna (copilot)`.

Implemented in the main development checkout as approved maintenance, not a managed WP1 task: selected `acquire_actions(selection=...)`, strict MCP input validation, atomic frontier and source fences, nonblocking Change checkpoint locking, retryable capacity/busy diagnostics, explicit already-active response, selected-only pending-publication replay, and retained recovery identities after post-claim launch failures. The original portfolio request remains supported. Existing transaction recovery can complete previously recorded transactions across the shared root; the promise is no new sibling actions, not zero sibling filesystem activity.

The baseline fixes preserve current contracts: disposition errors use `answer`; HTTP requests include the frontier digest; the current answer route restores bounded checkpoint contention; lost-acknowledgement replay respects the existing five-second backoff; admission responsiveness tests supply the required package identity. No failing tests were skipped.

Verification: **622 tests passed** in the expanded readiness/runtime/diagnostics/MCP/HTTP/application/transaction/package-boundary selection, then passed again on release commit `ffd71b158d448678b3f890b751298947da9c0e28` (111.28 seconds, one existing deprecation warning). Counts overlap and must not be added. Independent Claude Opus 5 exact-commit maintenance review reported `pass`, confirmed the parent and all eleven committed paths, and found no blocking defects. This is not a native Delivery task-result receipt. Pre-existing Ruff findings remain in the publication replay code and unrelated existing application tests; no clean whole-file lint pass is claimed.

The host accepted explicit model overrides for each chosen name in read-only probes. That proves the invocation option is accepted, not hidden model identity, Builder-hook execution, or nested reviewer availability. Critical production handoffs must preserve the configured role and its tools. Implementation/review pairings use different families: Astra -> Opus, Opus -> Astra, Luna -> Opus. Do not duplicate agent files or persist model routing in Delivery state solely for this programme.

The user explicitly authorized the bounded release steps: scoped prerequisite commit, exact-commit review, local Design checkpoint, and safe live schema activation. No push, WP1 admission, or P01 launch was authorized by that decision. The live `acquire_actions` schema now includes `selection` with Change/outcome, stage/task, frontier digest, and source head fields; `delivery_health` returned healthy with no diagnostics. No restart was needed and no acquisition call was made.

**Current gate:** restore callable tool discovery in the named Builder host before reacquiring P01. WP1 approval/admission, prerequisite publication, managed source synchronization, and independently reviewed native planning are complete. No agent may manufacture a task/claim from packet label P01 or substitute an unrestricted worker.

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

Later Design preparation owners remain those in programme section 12.8.4: P06 for continuation, P08 for provider/merge, P10 for recovery/retry, P12/P13 for revision/evidence, P15/P16 for assistance, and P19/P20 for maintenance/cutover. They are future gates, not completed designs.

## 7. Conditional P01 Handoff

**NEXT START: blocked.** The following is a preserved handoff draft, not a prompt to execute today. Once the prerequisite and approval gates pass, the P00 owner must refresh it with the actual approved package, task, model and baseline. The user should receive that complete version, not collect the missing identities.

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

**Resume action:** reload the VS Code window and start a fresh primary chat, then run the prompt below. Reload is a host recovery attempt, not proof of repair. The agent must verify discovery and named reviewer dispatch before acquiring a fresh TASK-001 claim. If discovery remains unavailable, report that exact host failure without another acquire/recover loop.

```text
Resume wave 01 for delivery-action-readiness only. Read section 11 of
.owlbear/research/delivery-action-readiness-p00.md. WP1 is approved, admitted,
and has a reviewed five-task native plan; do not reapprove, readmit, or replan.
First verify that the named builder host can actually load show_build_context
and submit_result through callable tool discovery, and can dispatch its named
build-reviewer. Preserve Astra implementation and Opus independent review.
If verified, read current engine fences, acquire TASK-001 only through selected
acquire_actions, and dispatch its unchanged launch to builder. Implement, test,
commit, independently review, and submit P01 in the managed Change worktree.
Stop before TASK-002/P02. Do not bypass missing tools, copy caller custody
evidence, edit Delivery state, or substitute an unrestricted worker.
```
