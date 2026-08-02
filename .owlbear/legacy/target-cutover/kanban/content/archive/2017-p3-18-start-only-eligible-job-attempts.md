---
id: 2017
title: 'P3-18: Start only eligible job attempts'
status: archived
priority: high
created: 2026-07-23T14:41:39.975443+02:00
updated: 2026-07-24T03:15:05.451390+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - claims
  - attempts
  - lifecycle
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-H
parent: 2003
depends_on:
  - 2013
  - 2016
ac:
  - 'AC-1: Given schema-version-one job data with disposition `pending`, `cancelled`,
    or `superseded`, `parse_job_mapping` returns that `JobRecord`; any other disposition
    returns `ERR_JOB_SCHEMA_INVALID` and no job.'
  - 'AC-2: Given matching loaded authority and target, every authored predecessor
    with a `CURRENT` receipt, no pending request, disposition `pending`, and no active
    claim, `start_job` atomically stores the request claim, attempt, and timestamp
    on the job plus one sequence-1 `started` event with the request actor, process,
    and timestamp; public store reads return both records.'
  - 'AC-3: Given a job whose change ID or digest differs from loaded authority, or
    whose target cannot be projected, `start_job` returns `ERR_START_AUTHORITY_STALE`
    with the target and leaves job and attempt bytes unchanged.'
  - 'AC-4: Given an authored predecessor whose job is missing, receipt ID is absent,
    or receipt is not `CURRENT`, `start_job` returns `ERR_START_PREDECESSOR_INVALID`
    with the blocking job or receipt target; when evaluation ran, `lower_code` is
    its result code. Job and attempt bytes remain unchanged.'
  - 'AC-5: Given an otherwise eligible job with pending requests, `start_job` returns
    `ERR_START_REQUEST_PENDING` with the first request ID as target and leaves job
    and attempt bytes unchanged.'
  - 'AC-6: Given disposition `cancelled` or `superseded`, `start_job` returns `ERR_START_TERMINAL`
    with that disposition as target and leaves job and attempt bytes unchanged.'
  - 'AC-7: Given stored claim and attempt IDs equal the request and event 1 has the
    same actor, process, and claim timestamp, `start_job` returns the existing job
    and event while the attempt retains one event. A differing actor, process, or
    timestamp returns `ERR_START_IDENTITY_CONFLICT` without mutation.'
  - 'AC-8: Given a stored claim or attempt ID differs from the request, or only one
    stored pointer is populated, `start_job` returns `ERR_START_ACTIVE_CLAIM` and
    leaves job and attempt bytes unchanged.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
A transport-free native runtime starts one eligible job attempt by atomically persisting the active claim pointers and one immutable `started` event.

## Scope
In scope: loaded-authority match; complete predecessor validity; pending-request and terminal-disposition guards; active-claim exclusion; caller-supplied attempt identity; claim and process identity; supplied claim timestamp on the started event; idempotent same-identity replay; stable rejection reasons.

Out of scope: transaction failure matrices, receipt evaluator internals, release/failure, expiry recovery, successful completion, dispatch waves, global writer leases, MCP, and Cockpit.

## Current Foundation And Ownership
Compose the mixed job/event transaction from task #2013 with complete receipt currentness from task #2016. Add the `start_job` operation to the transport-free native runtime facade; callers do not mutate `JobStore` directly.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `PROOF-003`, design sections 4.3, 7.2, 8.6, 13, and 14, and accepted `DEC-007` and `DEC-009`.

## Proof Guidance
Exercise public `start_job` with the finite readiness classes eligible, active claim, stale authority, invalid predecessor, pending request, terminal disposition, same-identity replay, and different identity. Lower transaction and validity failure matrices remain in their owners.

[[2026-07-23T23:49:54+02:00]]
## Builder Notes
- Change envelope: add the transport-free native runtime facade and its public `start_job` contract, composing `JobStore`, `AttemptStore`, `RuntimeTransaction`, and complete receipt currentness. The contract must define constructor inputs, request/result models, stable reason codes, loaded-authority source, terminal dispositions, and claim/process identity semantics.
- Files changed: none; task metadata only.
- Change Module Map deviations: source confirms no existing runtime facade or state/request projection owner. The shaped map names the facade outcome but does not name its module or contract boundary.
- Proof selected: source inspection plus exact searches for `start_job`, native runtime facade, active-claim/terminal-disposition contract, and tests. This disproved the availability of a local owner and a public callable to exercise.
- Durable-test justification: no test added because no stable public contract exists to protect.
- Commands run: `git status --short && git diff -- .owlbear/kanban/tasks/2017-p3-18-start-only-eligible-job-attempts.md` (only expected claim metadata on this task; unrelated worktree changes preserved).
- AC-to-evidence map: AC-1 cannot be implemented without an authoritative `start_job` request/result and authority-loading contract. AC-2 cannot select stable reasons without a terminal-disposition vocabulary and readiness projection. AC-3 cannot define same-identity replay without the caller identity and outcome shape.
- Current failure-key resolutions: none; no Verify Notes or Required Follow-up section.
- Builder-challenger result: not invoked; no DONE verdict is proposed.
- Follow-up risk: shape must define the facade module, public callable signature/models, loaded-authority and candidate-revision inputs, request/terminal state ownership, exact stable rejection codes, and same-identity outcome semantics. Implementing these choices here would invent an unadmitted cross-module interface.

[[2026-07-24T03:01:51+02:00]]
## Shape Notes
- Material repair review completed. The builder correctly found that the original task lacked a public facade, request/result models, exact diagnostics, terminal vocabulary, and replay contract.
- User decision: approved Option A, strict `JobDisposition = pending | cancelled | superseded` plus a dedicated `NativeRuntime.start_job` result. Unknown dispositions fail schema validation; lower-layer code/target remain optional diagnostic evidence rather than public control flow.
- Authority reconciliation: added accepted DEC-022, design section 7.3, and extended IF-003 with strict disposition, six stable `ERR_START_*` diagnostics, ordered eligibility checks, atomic start, and exact replay identity including claimed_at.
- Validation: revised package loads. Standard focused authority tests produced 31 passes and four existing DV-010 failures because global admission metadata is null/old. With an in-memory current-digest admission marker, admission evaluation returned no findings at digest `ce87d37e9935c7dfbb07a52ad485a8ce4b3641d3b054ba72417b0d80577f1a82`. Archived #2021 records this live-change admission limitation as delegated to DN-013/DN-014 rather than a leaf blocker.
- Draft graph: #2017 owns jobs.py strict disposition migration, new native_runtime.py start facade/models, package exports, and public start tests. Dependencies remain #2017 after archived #2013/#2016, then #2018 and #2019.
- Draft AC: eight independently verifiable cases cover schema literals, eligible atomic start, stale authority, predecessor invalidity, pending request, terminal states, exact/conflicting replay identity, and different/inconsistent active claims.
- Challenger: final complete graph challenge passed after adding explicit DEC-022/design 7.3 task authority, schema-migration ownership, and complete eligible preconditions.
- User graph approval: approved the presented #2003/#2017 graph delta.
- Lifecycle: release #2017 without movement. Commit reconciled authority and this task history, then restart the approved connected mutation set by claiming #2003 and #2017 in ID order.

[[2026-07-24T03:05:18+02:00]]
## Operative Native Job Start Contract

This amendment supersedes earlier Scope, Authority, ownership, and proof wording where they conflict with the contract below.

### Scope And Authority Amendment

In scope: the strict `JobDisposition` schema migration; correction of incidental fixtures using unsupported disposition strings; public start request, result, and diagnostic models; the assembled transport-free start operation; and public-boundary proof. Release/failure remains task #2018, expiry recovery remains task #2019, and successful finish/receipt issuance, dispatch, MCP, and Cockpit remain outside this task.

Controlling authority is `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `PROOF-003`, design sections 4.3, 7.2, 7.3, 8.6, 13, and 14, and accepted `DEC-007`, `DEC-009`, and `DEC-022`. `DEC-022` and design section 7.3 control disposition literals, start diagnostic codes, check order, and replay identity.

### Public Contract

- `JobDisposition` is a `StrEnum` with `pending`, `cancelled`, and `superseded`; `JobRecord.disposition` defaults to `pending`. Unsupported persisted values fail through existing `ERR_JOB_SCHEMA_INVALID`; no compatibility aliases are added.
- `StartJobRequest` contains `job_id`, `attempt_id`, `claim_id`, `actor_id`, `process_id`, `claimed_at`, and `candidate_revision`.
- `StartJobDiagnosticCode` contains `ERR_START_AUTHORITY_STALE`, `ERR_START_PREDECESSOR_INVALID`, `ERR_START_REQUEST_PENDING`, `ERR_START_TERMINAL`, `ERR_START_ACTIVE_CLAIM`, and `ERR_START_IDENTITY_CONFLICT`.
- `StartJobDiagnostic` contains `code`, `detail`, optional `lower_code`, and optional `target`.
- `StartJobResult` contains either one `StoredJob` plus one `AttemptEvent`, or one diagnostic.
- `NativeRuntime(revision, work_root, history)` assembles `JobStore`, `AttemptStore`, and `ReceiptStore`; `start_job(request)` is the public mutation boundary.

### Ordered Eligibility And Mutation

`start_job` checks, in order: job authority and target projection; predecessor jobs and their receipt currentness in authored `predecessor_job_ids` order; pending requests; terminal disposition; active claim and replay identity. Exact replay identity includes attempt, claim, actor, process, and claim timestamp.

An eligible start uses task #2013's `JobStore.replacement_participant` and `AttemptStore.create_participant`, then commits one `RuntimeTransaction` rooted at the work root. The job replacement sets `claim_id`, `attempt_id`, and `updated_at` to the request values; the immutable event uses sequence 1, kind `started`, and the request actor, process, and timestamp. Callers do not mutate stores directly.

### Change Module Map

- `serve/kanban/src/owlbear_kanban/jobs.py`: own strict disposition schema migration and parsing while preserving job serialization and OCC ownership.
- `serve/kanban/src/owlbear_kanban/native_runtime.py`: own start request/result/diagnostic models and the assembled `NativeRuntime.start_job` operation.
- `serve/kanban/src/owlbear_kanban/__init__.py`: export the disposition enum and public start contract.
- `serve/kanban/tests/test_native_runtime.py`: prove the public assembled start scenarios; tasks #2018 and #2019 deepen this facade later.
- Existing job and transaction fixtures using unsupported incidental disposition strings move to canonical literals; no compatibility path is introduced.

### Validation And Bootstrap Admission

The revised native package loads and reports no admission findings under a current-digest marker at `ce87d37e9935c7dfbb07a52ad485a8ce4b3641d3b054ba72417b0d80577f1a82`. The live `DV-010` remains the existing global re-admission obligation delegated to DN-013/DN-014, consistent with archived task #2021; it is not a local #2017 acceptance branch.

[[2026-07-24T03:06:41+02:00]]
## Approved Shape Handoff
- User approved strict `JobDisposition = pending | cancelled | superseded` plus the dedicated `NativeRuntime.start_job` request/result/diagnostic contract.
- Operative amendment names schema, facade, exports, tests, constructor inputs, six `ERR_START_*` codes, ordered checks, exact replay identity, and task #2013 participant composition.
- Eight AC independently cover strict schema parsing, eligible atomic start, stale authority, predecessor invalidity, pending requests, both terminal dispositions, exact/conflicting replay, and different/inconsistent active claims.
- Dependencies are unchanged and satisfied: archived #2013 and #2016. #2018 still owns release/fail; #2019 still owns expiry recovery.
- Validation: `uv run pytest -q tests/test_edit_task_contract.py` passed 2 tests; both task diffs pass `git diff --check`; mechanical audit found one operative amendment per task and exactly eight #2017 AC.
- Authority commit: e8de7f92df9847a004613898e2171c3239365e29. Parent map commit: 8e1032fa8adfb3ae62758b91597e3b0f498e5e41.
- Shaper challenger: pass on the complete graph. Route to builder using the operative amendment as controlling task text.

[[2026-07-24T03:11:44+02:00]]
## Builder Notes
- Change envelope: strict native job disposition parsing plus the transport-free `NativeRuntime.start_job` boundary that composes existing job, attempt, receipt-currentness, and mixed transaction owners.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/native_runtime.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, `serve/kanban/tests/test_jobs.py`, and `serve/kanban/tests/test_native_runtime.py`.
- Change Module Map deviations: none. The shaped `jobs.py`, native runtime, package export, and public proof owners were used exactly as mapped. Incidental unsupported `claimed` test fixtures were migrated to the strict canonical disposition.
- Proof selected: public-boundary pytest coverage for parser, eligible atomic start, rejection classes, and replay identity; Ruff lint for all touched source and tests.
- Durable-test justification: added `test_native_runtime.py` because the assembled public mutation contract crosses stores and transaction ownership, making regressions hard to detect through lower-layer tests.
- Commands run: `uv run pytest -q serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_jobs.py` passed 31; `uv run ruff check` on all five touched files passed.
- AC-to-evidence map: AC-1 strict parser test; AC-2 start persists claim, attempt, timestamp, and sequence-one `started` event; AC-3 stale authority parameterized case; AC-4 missing predecessor case; AC-5 pending request case; AC-6 cancelled and superseded parameterized cases; AC-7 exact replay plus changed actor conflict; AC-8 partial and different active claim pointer cases. Rejection cases assert the stored job is unchanged.
- Current failure-key resolutions: none; no Verify Notes Required Follow-up was present.
- Builder-challenger result: pass. The challenger reviewed the diff and reran the focused suite: 31 passed.
- Follow-up risks: receipt-currentness detail paths are delegated to the existing receipt owner; no transaction-failure matrices were added because they remain outside this task scope.

[[2026-07-24T03:14:05+02:00]]
## Verify Notes
- Evidence reviewed: current Shape Notes, newest Builder Notes, all eight AC lines, and no prior Verify Notes or resolved requests. The named authorities are reflected in the approved runtime contract; `jobs.py` owns strict disposition parsing and `native_runtime.py` owns the public start boundary.
- Change Module Map: no deviations. Builder changed exactly `jobs.py`, `native_runtime.py`, package exports, and their focused tests. Task-owned mapped files were clean; unrelated workspace changes were preserved.
- Normal-path boundary: `NativeRuntime.start_job` was exercised directly. The test substitutes only repository-history behavior below the receipt-currentness boundary; it does not replace the runtime operation, store mutation, transaction, or emitted event.
- Checks run: `uv run pytest -q serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_jobs.py` passed 31; `uv run ruff check` on the five mapped files passed; `uv run pytest -q serve/kanban/tests/test_native_runtime.py -vv` passed 9 cases. `git diff --check HEAD` found no task-owned file defects.
- Findings: `start_job` evaluates loaded authority, predecessor currentness, pending requests, terminal disposition, and active claim before committing a `RuntimeTransaction` that persists updated job pointers and exactly one started event. Exact replay returns that persisted pair; actor, process, or timestamp mismatch returns identity conflict. Source confirms the AC-3 digest/unknown-target and AC-4 missing-receipt/non-current receipt variants that are not separately parameterized by the focused tests.
- AC-to-evidence: AC-1 strict parser test plus `JobDisposition`; AC-2 public start/replay mutation case; AC-3 stale authority public case plus `project_job`; AC-4 missing predecessor public case plus predecessor owner; AC-5 pending-request public case; AC-6 both terminal dispositions; AC-7 exact replay and conflicting actor public case plus process/timestamp condition; AC-8 partial and different active-pointer public cases. All rejection tests read the job again and confirm it is unchanged.
- Prior same-failure-key rejection check: none. No Required Follow-up is open.
- Memory: assessed all ten recalled entries; artifact-to-scope and live-public-contract guidance materially informed this review.
- Verifier-challenger: pass, no concrete blocker. It confirmed public coverage of the start boundary, source closure of remaining branch variants, mapped scope, and focused proof.
- Final route: PASS to collect.

[[2026-07-24T03:15:05+02:00]]
## Collect Notes
- Classification: leaf. No child tasks; parent `#2003` is aggregate context only.
- Latest verification evidence: newest `## Verify Notes` records PASS after `uv run pytest -q serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_jobs.py` (31 passed), focused verbose runtime tests (9 passed), and ruff on the five mapped files. It maps AC-1 through AC-8 to the public `NativeRuntime.start_job` boundary and source-closed branch variants.
- Intent source: `## Outcome` and `## Scope` require an eligible runtime attempt start with atomic claim pointers and one immutable `started` event.
- Invariant coverage: verifier confirms authority, predecessor, pending request, terminal, active-claim, exact replay, identity-conflict, and unchanged-state rejection coverage across AC-1 through AC-8.
- Dependency gate: `#2013` and `#2016` are archived with `completed`; task dependency status is `ok`.
- Child coverage: none.
- Aggregate normal-path proof: not applicable to this leaf; latest verification contains focused public normal-path proof.
- Residual decisions: no pending or resolved structured requests; no Required Follow-up.
- Archive rationale: current verifier PASS and clean closure state satisfy leaf archival requirements.
