# Delivery Action Readiness and Failure Visibility Design

> Status: P00 candidate; prerequisite release/activation, final challenge, checkpoint, user approval, and admission remain gates.
> Source and gate record: .owlbear/research/delivery-action-readiness-p00.md.

## Ownership and Snapshot Capture

portfolio_application.py owns coherent views and finalization readiness. work_items.py owns projection from captured inputs, not filesystem inspection. DeliveryRuntime owns lifecycle/proof; ChangeWorkspaceManager owns workspace facts and Git effects. MCP and HTTP adapt the application. Finalizer owns read-only checks and diagnostic reporting, not worktree repair.

Deepen a private application-owned readiness function taking runtime/contract state, managed workspace facts, applicable reports, and supported action metadata. Inspect each needed workspace at most once per response. Extract the existing WorkItemProjector._publication_phase body without semantic changes into one pure internal resolve_publication_phase(frontier) function in work_items.py; both projector and capture consume it. Do not duplicate phase ordering or call a projector that recursively requests readiness. Card/detail/finalization context consume one decision for their captured basis. Independently timed reads may differ when state changes; this is not a global atomic filesystem snapshot.

Consult persisted discovery before constructing the selected runtime so known-unavailable Changes can be displayed. Existing previously recorded transactions may recover through their current rules; new readiness inspection creates no claim, attempt, repair, or publication.

## Strict Public Read Contract

Add one strict immutable readiness DTO to the existing Change, card/detail, and finalization context views:

- status: ready | running | waiting | blocked | unavailable | complete.
- operation: an existing WorkItemActionKind value or null, reusing its schema owner.
- executable: true only for a supported operation whose observed prerequisites pass.
- next_actor: existing WorkItemNextActor; provider/dependency waiting uses its existing projection plus a reason code rather than invented enum aliases.
- reason_code: stable code for the observed condition, including workspace-dirty, workspace-inspection-failed, active-custody, runtime-unavailable, dependency-wait and current publication waits. Engine templates render safe reason text.
- checks_state: not-run | failed | passed | unknown for the displayed finalization observation, not unrelated task proof.
- basis: trusted contract/frontier digests, observed candidate/reviewed heads, workspace fingerprint when observed, and diagnostic sequence. Unknown values are null, never synthetic hashes.
- action: existing executable descriptor when supported. A read-only inspection prompt is separate from mutation actions.
- last_attempt: optional bounded report with current/historical applicability.

Known runtime plus failed Git/filesystem/workspace inspection yields readiness status unavailable, executable false, reason_code workspace-inspection-failed, and a null workspace fingerprint. Preserve trusted semantic detail and last proof, and distinguish a new not-run preflight from an unknown prior execution. Do not infer cleanliness, propagate raw exception text, or fail unrelated list entries. Skip workspace inspection when it is not a prerequisite for the displayed action. Apply a bounded fixed Git inspection timeout at the owning workspace adapter and show the same typed unavailable reason on timeout; reuse an existing bound where adequate.

get_change exposes a discriminated available/unavailable result. The available variant means semantic runtime data could be read, not that execution is ready. It includes readiness, which may be unavailable for workspace inspection. The unavailable variant means trusted runtime composition failed and contains only Change identity, trusted discovered title if present, typed diagnostics, nullable basis, and no mutable action. List views retain both variants. Unknown Change remains distinct from known-unavailable. Strict canonical parsing is unchanged.

## Readiness and Effect Rules

Precedence: unavailable authority -> unavailable; active/uncertain operation -> existing wait/reconciliation; paused/terminal -> existing lifecycle controls; current request/dependency -> existing bounded action/wait; unobservable required workspace -> unavailable; failed workspace preflight -> blocked; otherwise supported action -> ready. Apply current finalization guards.

A report is not a retry veto. When current preconditions allow retry at the same head, expose the existing command labelled Retry verification and show the previous result. Reporting clears no review, claim, or publication guard. A changed head/contract makes old reports historical.

finalize_change re-runs managed-head/worktree validation at the effect boundary. A fixture edits the workspace after the readiness read and before finalization; the latter rejects without writing a receipt. Read-time readiness is not a lease.

## Finalization Diagnostic Report Contract

Add application and registered MCP report_finalization_failure. No new observation-context token or successful-proof input. Bind expected contract/frontier digests, candidate/reviewed heads, expected diagnostic sequence, and caller attempt idempotency key.

Input fields: change_id; expected_contract_digest; expected_frontier_digest; expected_change_head; expected_reviewed_head; expected_diagnostic_sequence (nonnegative integer); attempt_key (1..128 ASCII characters from A-Za-z0-9._-); category custody-preflight | maintained-check | independent-review; fixed registered code enum; checks_state not-run | failed | unknown; optional engine-resolved check_id; optional integer exit_status; expected_workspace_fingerprint for custody reports; up to 32 contained relative paths verified against engine-observed dirty paths. Normalize and bound identifiers and path lengths using the owning path contract; final serialized size must also pass before write.

Reject caller fields for free-text summary, raw command, logs, URLs, environment, exception text, arbitrary artifact paths, observer names, and successful-proof payloads. The engine supplies timestamp, report identity, safe summary, and a diagnostic producer label that is not authenticated proof. check_id refers to an existing resolved proof/context descriptor; if none is resolvable, keep it null and display unavailable detail instead of inventing a command registry. Structural minimization is not a promise to detect arbitrary secrets encoded in permitted identifiers.

Unavailable runtime or unobservable workspace provides no trustworthy writable custody report basis; return its read-only diagnostic instead. A crashed finalizer may leave no report; WP1 does not promise unattended attempt-start evidence or new finalizer writer custody. Report writes never certify worker termination or release claims.

## Host-Local Report Persistence and Containment

Use the trusted configured runtime root plus finalization-reports/<change-id>/, containing reports/<engine-report-id>.json and current.json. This root is owned by a focused finalization_reports module, not the unrelated diagnostics.py failure classifier. It is outside existing portable snapshots' enumerated contract/frontier/admission participants. No frontier schema change or remote backup of reports is introduced. Explicit tests must prove the snapshot exporter ignores these reports.

Derive the report root from the existing injected runtime root, not a caller path or environment variable. The storage owner rejects symlink/non-directory components for finalization-reports, the Change directory and reports directory; reject unsafe file targets and escaped transaction participants using the existing no-follow/contained-root primitives. A symlink swap or invalid root must fail without writing outside the configured root. Use explicit allowed roots during transaction recovery. Root/path failure yields report-store-unavailable, never fallback to a product worktree, primary checkout, or temporary path with looser policy.

Under a dedicated per-Change report lock, recover pending report transactions, check sequence and authoritative basis, and compare workspace facts for custody reports. Store immutable reports and pointer changes with RuntimeTransaction. Identical attempt-key/payload replay returns its original record without moving a newer pointer, including after candidate change; a conflicting payload is rejected. New reports require the current sequence. Changes in authority during reporting leave evidence attached only to its original candidate, not a new one.

Bounds: maximum report JSON 16 KiB, maximum 256 reports per Change. Check encoded size before persistence. At capacity return diagnostic-capacity without silently evicting idempotency records; old-key replay remains available. Automatic compaction is out of scope.

Successful same-candidate finalization retires only its matching pointer/sequence, preserving immutable reports. A pointer-retirement failure cannot undo a successful finalization or show it as failed: read projection prioritizes the exact current success receipt. Deterministic finalization replay may reconcile the pointer; ordinary reads do not write new reports or clear them. Report-transaction recovery may complete previously persisted operations under existing recovery rules.

Missing report store means no previous report. Corruption means report-store-unavailable without invalidating existing product proof, deleting bytes, or recomputing hashes to bless data. Raw bytes remain available for later maintenance. No live B1/D1 conversion is part of this Change.

## Read-Only Inspection Entry

P02-W introduces /inspect-change <change-id> as a narrow diagnosis prompt, not an automatic fixer. It uses built-in read-only Ask mode and an explicit tools allowlist containing get_change and delivery_health only; no agent dispatch, terminal, edit, answer, repair, acquire, or transition tools. Verify the effective host prompt/tool surface. If runtime narrowing is not enforced, do not label it a hard read-only entry; fail the release gate or use an explicitly restricted existing read-only role.

The prompt explains what finished, whether checks ran, the current blocker, and supported next interactions from the returned state. It never emits raw Git repair instructions. Unknown/unavailable state remains evidence, not permission to fix it. Do not overload the temporary resolve-delivery-attention prompt or change its mutation authority/retirement rules. Cockpit copies the complete inspection prompt and labels that as copying, not launch. This small diagnosis entry can later be consumed by continuation, but WP1 does not advertise /continue-change.

## Packet and Native Planning Scope

Compiler derives SCOPE-001 for OUT-001. This authored section owns implementation/proof paths, not generated scope metadata or native task IDs.

P01 / delivery: portfolio_application.py, work_items.py and existing snapshot/inspection owners, a focused finalization_reports.py module and tests if needed; test_work_items.py, test_portfolio_application.py, test_runtime_transaction.py or a focused report-store companion. Add root-safety, encoded-size, corruption and exporter-exclusion tests alongside the store. Do not refactor unrelated retries, admission, provider effects, or diagnostics.py merely to house persistence.

P02 / delivery-mcp: target_models.py, target_server.py, exports/registry and test_delivery_adapter.py/test_target_server.py. P02-W is a separate agent-config task executed serially inside the P02 primary session: finalizer.agent.md, w-change-finalization/SKILL.md, inspect-change.prompt.md with its restricted effective tools, relevant prompt/schema/grant validation and WIRING.md when required. Finalizer gains only failure-report write authority, never repair rights. P02-W is not an extra user-launched packet or a delivery-mcp domain task.

P03 / cockpit: routes/target_work.py, target_models.py and tests/test_cockpit_work_items.py. P04 / cockpit: api/workItems.ts, existing card/detail/presentation components and tests, minimal maintained E2E for real controls. UI displays engine selection rather than computing policy. Documentation follows its owning behavior. No dependency change is expected; if one is justified, own the lockfile in the same task.

The assembled boundary crosses Delivery -> registered MCP and Cockpit HTTP -> rendered control/inspection handoff. P01/P02/P02-W/P03/P04 are sequential domain-local tasks in one WP1 Change worktree. Planner/acquisition generates native identities. P05 remains a separate later outcome. No second task board or per-packet worktree is introduced.

## Execution Prerequisite and Models

Before P01, release and activate the independently user-approved selected-launch prerequisite. Its code/tests are a dependency, not WP1 task scope. It adds a complete selection to acquire_actions: Change/outcome, expected stage/task, expected frontier and source head. At most one next eligible action is claimed; frontier is checked at activation. Current busy/stale/capacity/active cases remain distinct. Selected publication replay touches only the chosen Change; root transaction recovery may complete prior shared-root operations, not new unrelated claims.

The user selected Astra/Opus/Luna for T3/T2/T1 respectively. P01 uses Builder with GPT-6 Astra (copilot) override and independent Claude Opus 5 (copilot) review; Opus implementation is reviewed by Astra, Luna by Opus. Read-only host probes accepted the override names but do not prove actual underlying model identity, worker hooks, or nested review. Verify the effective role/tool/model route before acquisition; do not silently use a pinned default when override is unavailable.

No P00 action acquires planning or P01 work. After approval/admission, the authorized handoff obtains a selected Planning claim, publishes the independently reviewed domain-local task plan through existing tools, and then obtains only the exact next Builder task when the user starts its packet. Do not pause B1/D1, manipulate capacity, or call private activation to force selection.

## Baselines and Limits

The approved prerequisite working tree passed 622 tests across Delivery work items, runtime, diagnostics, application, transaction; registered MCP/adapter; Cockpit routes; and package boundaries using uv run --locked pytest -q --tb=short -n 0. Later focused checks cover cleanup. These are baseline observations, not proof of WP1 implementation or an immutable release. Existing unrelated Ruff findings remain documented; no skip or arbitrary permissive parser is used to pass baseline tests.

P00 must obtain an exact prerequisite release and verify live selected MCP schema before enabling P01. This candidate requires its own challenge, checkpoint, approval/admission and native task planning. Report storage is host-local, bounded and non-authoritative. The read-only inspector explains supported current operations and gaps without claiming WP3 repair has shipped.

```yaml target-contract
kind: outcome
id: OUT-001
title: Truthful Change readiness and retained finalization failures
promise: Cockpit and agents receive one snapshot-consistent executable action decision and can inspect failed or unstarted finalization after restart without manual worktree repair or weakened authority.
acceptance:
  - "AC-001: Given a completed-task Change whose managed worktree is dirty, application list/detail and registered get_change report blocked readiness, checks not-run for that preflight, and no executable finalization; their captured basis fields match."
  - "AC-002: Given a clean completed-task Change, show_finalization_context and displayed Finalize agree on candidate/readiness; editing the workspace after the read but before finalize_change causes managed validation to reject without a finalization receipt."
  - "AC-003: Given a failed maintained check or preflight submitted through registered report_finalization_failure with current basis, restart returns its retained category, candidate and checks state while branch, claims, frontier stage and proof receipts remain unchanged."
  - "AC-004: Given the same attempt key and payload twice, submission returns one record; changed payload, stale new basis or mismatched report sequence conflicts without overwriting current evidence."
  - "AC-005: Given a newer candidate/contract, prior reports remain historical and cannot block that candidate; a same-head report alone cannot veto a currently eligible retry or clear an existing lifecycle guard."
  - "AC-006: Given malformed frontier bytes for a known Change, registered MCP output, HTTP list/detail and Cockpit emit the tagged unavailable variant with no mutation action; unrelated entries remain visible and strict parsing still rejects the malformed bytes."
  - "AC-007: Given interruption between report/pointer publication or an injected store write error, restart replays the bounded transaction or shows report-store-unavailable without changing product authority or claiming report success."
  - "AC-008: Given unknown raw-summary, command, URL, log, environment or proof fields, or encoded report size above 16 KiB, validation rejects before persistence; stored fields follow the declared structured report contract."
  - "AC-009: Given a finalizer with trusted context and failed preflight, its registered failure-report handoff retains an identity and says checks did not run; no checkout mutation, claim recovery, or successful finalization occurs."
  - "AC-010: Given ready, blocked, unavailable, running, waiting and complete readiness fixtures, Cockpit renders the engine-selected action/explanation and labels copied prompts as copying, not agent launch."
  - "AC-011: Given successful same-candidate finalization after a failed attempt, the success receipt is current and report history survives pointer retirement; retirement failure cannot replace successful status, and an ordinary read creates or retires no report."
  - "AC-012: Given the P01/P02/P02-W/P03/P04 surfaces in this Design's Packet and Native Planning Scope section, routed core/adapter/HTTP/component checks and registered finalizer handoff pass; known-unavailable remains distinct from unknown Change."
  - "AC-013: Given custody reporting with a changed workspace fingerprint or paths escaping/mismatching engine-observed dirt, reporting rejects without checkout edits or pointer advancement."
  - "AC-014: Given 256 retained reports, the next new attempt returns diagnostic-capacity without deleting history; replay of an existing key returns its original record."
  - "AC-015: Given a per-Change Git inspection timeout, missing workspace, or permission error during list/detail capture, readiness is unavailable with workspace-inspection-failed and no executable finalization; unrelated entries remain usable and mutation rechecks do not assume cleanliness."
  - "AC-016: Given symlinked/non-directory report-root components or an escaped transaction target, report persistence rejects without touching an outside sentinel; authoritative portable snapshot export excludes host-local reports."
  - "AC-017: Given the effective inspect-change prompt configuration, only read-only get_change and delivery_health are available; no terminal, edit, dispatch or Delivery mutation tools are exposed, and fixture outputs explain blockers without raw Git repair instructions."
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005]
dependencies: []
```
