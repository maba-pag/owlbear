---
id: 2037
title: 'P1-C6: Replace IF-015 shape completion with plan completion'
status: collect
priority: high
created: 2026-07-25T02:46:59.817987+02:00
updated: 2026-07-25T08:29:04.775960+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-004
  - corrective
  - scope:mcp-kanban
  - mcp
  - interface:IF-015
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2039
ac:
  - 'AC1: The assembled MCP server registers `pick_jobs`, `start_job`, `finish_plan`,
    `finish_build`, `finish_accept`, `finish_audit`, `release_job`, and `recover_expired_claims`;
    its tool inventory contains no `finish_shape` registration or alias.'
  - 'AC2: Given strict `finish_plan` parameters, the adapter constructs `FinishPlanRequest`
    and returns `DispatchRuntime.finish_plan` success or its stable domain diagnostic
    without alternate file or task mutation.'
  - 'AC3: Given accept or audit start and completion through the assembled server,
    checkout setup precedes claim and cleanup follows finish, release, or recovery;
    setup or residual-cleanup failure returns the declared diagnostic without a current
    receipt.'
  - 'AC4: Given strict `finish_accept` parameters including `reconciliation_plan_job_ids`,
    the adapter constructs `FinishAcceptRequest` and returns `DispatchRuntime.finish_accept`
    success or its stable domain diagnostic; it never substitutes generic `FinishJobRequest`
    or alternate mutation.'
  - 'AC5: Given a lifecycle-tool invocation across the assembled MCP server using
    `start_job`, `finish_plan`, `finish_build`, `finish_accept`, `finish_audit`, `release_job`,
    or `recover_expired_claims`, the adapter performs only lifecycle delegation; it
    does not select a job, profile, dependency route, or subsequent invocation outside
    `pick_jobs`.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Expose the corrected purpose-specific native completion bridge through MCP without a shape alias or duplicate scheduling authority.

## Scope
In scope: MCP parameter models, registrations, strict adapters, response/error mapping, proof-checkout composition for accept/audit, exports, and focused bridge tests.

Out of scope: DN-009 change/admission/history/request APIs, Cockpit, planner policy, and scheduling decisions.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-033; MIG-004; DN-004; IF-005; IF-015; PROOF-014.

Proof guidance: run assembled FastMCP inventory and invocation checks over real `DispatchRuntime` with contained stores and proof-checkout dependency below the bridge.

## Shape Notes
- Connected local repair after #2036's assembled scenario exposed two ordered prerequisites: #2039 owns core completion participant composition, then this task owns strict MCP request construction and delegation.
- Removed the false dependency on #2036 and added #2039. This task remains build-ready but dependency-gated until #2039 archives.
- Added explicit `FinishAcceptRequest` ownership so a builder cannot satisfy the bridge while leaving the generic `FinishJobRequest` defect in place.
- Replaced the old forward-reference AC with an assembled invocation boundary that proves MCP adapters do not select or chain work.
- Active chain: `#2039 -> #2037 -> #2036 -> #1983`.
- Shaper challenge validated AC quality, authority, ownership, dependency closure, scenario closure, and boundary proof after the prerequisite task received a stable ID.

[[2026-07-25T08:09:00+02:00]]
## Shape Notes
- Connected local repair removed the false dependency on #2036 and added prerequisite #2039, which owns the core completion callback composition required by this task's assembled bridge proof.
- Added explicit AC4 ownership for strict `FinishAcceptRequest` construction with `reconciliation_plan_job_ids`; added AC5 for delegation-only lifecycle adapters with no scheduling authority.
- Preserved objective, scope, authority, AC1-AC3, and build status. Task remains dependency-gated until #2039 archives.
- Shaper-challenger passed the materialized `#2039 -> #2037 -> #2036 -> #1983` graph after direct Python 3.14.6 proof established the actual #2039 boundary.

[[2026-07-25T08:25:38+02:00]]
## Builder Notes

- Change envelope: `serve/mcp-kanban` strict MCP models, lifecycle adapters, native request/result/error delegation, proof-checkout composition proof, exports/inventory, and focused bridge tests. No picker profile, orchestration, core runtime, planner, Cockpit, or DN-009 changes.
- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`, `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, and `serve/mcp-kanban/tests/test_mcp_surface_contract.py`.
- Change Module Map deviations: none. `server._dispatch_runtime` already composes `ProofCheckoutManager` into both `NativeRuntime` and `DispatchRuntime`; this task only used that composition through the lifecycle adapters.
- Implementation: added strict `FinishAcceptParams.reconciliation_plan_job_ids`; `finish_accept` now requires that MCP parameter, constructs native `FinishAcceptRequest`, preserves `impact_closure` conversion, and delegates directly to `DispatchRuntime.finish_accept`. The generic `FinishJobRequest` helper remains limited to build/audit.
- Durable-test justification: the added live FastMCP schema assertion guards the public accept completion contract, which is easy to regress through function-default or generated-schema drift. PROOF-014 now supplies actual reconciliation-plan IDs to exercise the real runtime bridge.
- Commands run:
  - `uv run pytest serve/mcp-kanban/tests/test_mcp_surface_contract.py::TestFinishAcceptSchema::test_finish_accept_requires_reconciliation_plan_job_ids -q` -> 1 passed.
  - `uv run pytest serve/mcp-kanban/tests/test_mcp_surface_contract.py -q -k 'not TestProof014NativeMcpScenario'` -> 4 passed.
  - `uv run pytest serve/mcp-kanban/tests -q -k 'not TestProof014NativeMcpScenario'` -> 438 passed.
  - `uv run ruff check ... && uv run ruff format --check ...` -> passed.
  - `git diff --check` -> passed; editor diagnostics clean.
  - Exact `TestProof014NativeMcpScenario` now reaches and completes `finish_accept`; it then fails at the pre-existing downstream audit fixture collision with native reconciliation plan job `5`. No `shaper`/`planner` profile expectation or orchestration was patched here; that belongs to `#2036`.
- AC-to-evidence:
  - AC1: live registry snapshot includes all eight lifecycle tools and no `finish_shape`; focused surface suite passed.
  - AC2: assembled PROOF-014 invokes strict `finish_plan` over a real `DispatchRuntime`; adapter delegates directly.
  - AC3: assembled runtime composes proof checkout; PROOF-014 invokes start, finish, release, and recovery. The accept bridge passes completion before the downstream `#2036` fixture boundary.
  - AC4: live FastMCP schema requires `reconciliation_plan_job_ids`; adapter builds `FinishAcceptRequest` and delegates to `finish_accept`; direct schema test passed.
  - AC5: lifecycle adapter code delegates only. `pick_jobs` alone calls `pick_waves`; 438 focused MCP package tests passed.
- Current failure-key resolution: `#2036-AC3/accept-completion-prerequisite` MCP portion repaired. The earlier `FinishJobRequest` assertion is gone; the exact scenario completes accept and exposes only the explicitly out-of-scope downstream reconciliation/profile path.
- Builder-challenger: pass. It independently confirmed the 4 surface checks, 438 focused package checks, and ruff/diff hygiene.
- Follow-up risk: exact PROOF-014 remains red only after this task's accept-completion boundary because its next audit fixture assumes no reconciliation plan jobs; `#2036` owns the subsequent profile/orchestration expectation.

[[2026-07-25T08:29:04+02:00]]
## Verify Notes

- Authoritative task and dependency checked: #2037 was claimed in `verify`; prerequisite #2039 is archived at `5906afac1` after implementation `3599b9376`. No resolved requests. Candidate is `1a5e03004`.
- Named authorities checked: admitted digest, DEC-033, MIG-004, DN-004, IF-005, IF-015, and PROOF-014 were checked against the task's shaped boundary. Change Module Map matched exactly: candidate changes only MCP parameter models, FastMCP registrations/adapters, and focused MCP surface proof. No core picker/profile/orchestrator (`#2036`), planner, Cockpit, or DN-009 changes.
- Candidate/source review: `FinishAcceptParams` requires `reconciliation_plan_job_ids`; `finish_accept` validates it, converts `impact_closure`, constructs `FinishAcceptRequest`, and delegates to `DispatchRuntime.finish_accept`. The generic `FinishJobRequest` helper remains build/audit-only. `finish_plan` constructs `FinishPlanRequest` directly. Only `pick_jobs` calls `pick_waves`; start/finish/release/recovery adapters only delegate.
- AC1: post-lifespan live FastMCP inventory assertion passed. It contains `pick_jobs`, `start_job`, `finish_plan`, `finish_build`, `finish_accept`, `finish_audit`, `release_job`, and `recover_expired_claims`; no `finish_shape` alias/registration.
- AC2: strict assembled `finish_plan` constructs `FinishPlanRequest` and delegates to real `DispatchRuntime.finish_plan`; PROOF-014 invokes that path.
- AC3: assembled `_dispatch_runtime` composes `ProofCheckoutManager` below real `DispatchRuntime`. Source plus `14` focused checkout/dispatch tests prove setup before reader claim, cleanup after failed claim, finish cleanup before publication, release/recovery cleanup afterward, and stable setup/residual-cleanup diagnostics.
- AC4: live FastMCP schema requires `reconciliation_plan_job_ids`; focused schema test passed. The exact PROOF-014 bridge invokes `finish_accept` with those IDs and completes accept through `FinishAcceptRequest`.
- AC5: adapter source confirms lifecycle-only delegation and no picker/profile/dependency/next-operation selection outside `pick_jobs`; focused MCP suite passed.
- Normal-path boundary: exact `TestProof014NativeMcpScenario::test_profiles_release_recovery_and_replanning_use_native_tools` exercises the assembled FastMCP adapters over a real `DispatchRuntime` with contained stores. `finish_accept` succeeds. Its only failure follows that completion when the scenario manually creates audit job `5`, colliding with reconciliation plan job `5` created by accept: `TransactionConflictError`. This is the declared later #2036-owned reconciliation/audit fixture/profile expectation; no #2036 code or fixture was patched here. The repaired MCP portion of `#2036-AC3/accept-completion-prerequisite` is therefore cleared.
- Checks run:
  - `uv run pytest serve/mcp-kanban/tests -q -k 'not TestProof014NativeMcpScenario'` -> `438 passed`.
  - live inventory/schema checks -> `2 passed`.
  - `uv run pytest serve/kanban/tests/test_proof_checkout.py serve/kanban/tests/test_dispatch_runtime.py -q` -> `14 passed`.
  - `uv run ruff check ...` and `uv run ruff format --check ...` -> clean.
  - `git show --check 1a5e03004` -> clean; touched-file editor diagnostics -> none.
- Replacements remained below the claimed boundary: PROOF-014 replaces only `_dispatch_runtime` with a real contained `DispatchRuntime`; it does not mock the MCP command, workflow, generated tool visibility, or lifecycle path.
- No verifier patch applied: no local defect remained within the one-owner, one-validation-cycle patch budget.
- Prior same-failure-key rejection check: no earlier #2037 Verify Notes or verifier rejection exists. The current downstream fixture collision is separately owned by #2036, so no repeated verifier repair cycle applies.
- Memory recall assessed: all 20 returned entries were assessed; live-signature and task-boundary guidance was applied.
- Verifier-challenger: `pass`. It confirmed AC1-AC5 direct evidence, no scope drift, and #2036 ownership for the post-accept fixture collision.
- Final route: PASS to `collect`.

