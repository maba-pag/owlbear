---
id: 2018
title: 'P3-19: Release or fail owning attempts'
status: verify
priority: high
created: 2026-07-23T14:41:48.715516+02:00
updated: 2026-07-24T12:42:10.991507+02:00
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
  - packet:DN-003-PK-004-I
parent: 2003
depends_on:
  - 2017
ac:
  - 'AC-1: Given schema-version-one attempt data with nonempty `claim_id`, `parse_attempt_event_mapping`
    returns an `AttemptEvent` and serialization preserves the claim; missing or empty
    `claim_id` returns `ERR_ATTEMPT_EVENT_IDENTITY_INVALID` and no event.'
  - 'AC-2: Given the owning active attempt, `NativeRuntime.release_job` atomically
    appends one sequence-2 `released` event carrying request `claim_id`, clears only
    matching job pointers, leaves disposition `pending`, and leaves graph and receipts
    unchanged.'
  - 'AC-3: Given the owning active attempt, `NativeRuntime.fail_job` atomically appends
    one sequence-2 `failed` event carrying request `claim_id`, detail, and evidence
    IDs, clears only matching job pointers, and preserves sequence-1 history.'
  - 'AC-4: Given a committed released or failed outcome and a replay matching job,
    attempt, claim, kind, actor, process, timestamp, detail, and evidence, the operation
    returns the existing job/event and `AttemptStore.list` retains one sequence-2
    event.'
  - 'AC-5: Given a sequence-2 outcome for the requested job and attempt, a release/fail
    request differing in claim, kind, actor, process, timestamp, detail, or evidence
    returns the operation-specific `NON_OWNER` diagnostic, leaves job bytes unchanged,
    and appends no event.'
  - 'AC-6: Given active pointers whose claim, attempt, actor, or process does not
    own the active attempt, release/fail returns the operation-specific `NON_OWNER`
    diagnostic without mutation. Given cleared pointers and no sequence-2 outcome
    for the requested job and attempt, it returns the operation-specific `NO_ACTIVE_CLAIM`
    diagnostic without mutation.'
  - 'AC-7: Given a committed sequence-2 outcome whose `job_id` differs from the replay
    request `job_id`, release/fail does not return that event, returns the operation-specific
    diagnostic for the requested job state, leaves both job records unchanged, and
    appends no event.'
  - 'AC-8: Given an eligible `NativeRuntime.start_job` request, its sequence-1 started
    event carries request `claim_id` and exact replay returns it without duplication;
    changed claim or attempt pointers retain `ERR_START_ACTIVE_CLAIM`, while matching
    pointers with changed actor, process, or claim timestamp retain `ERR_START_IDENTITY_CONFLICT`.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The native runtime lets only the owning attempt release or fail its active claim while preserving immutable history and job purpose.

## Scope
In scope: owner identity; released and failed events; supplied failure detail and evidence references; atomic matching-claim clear; open-job preservation; idempotent replay; non-owner and no-active-claim diagnostics; graph and receipt immutability.

Out of scope: start eligibility, expiry recovery, successful completion, receipt creation, corrective routing, dispatch, MCP, and Cockpit.

## Current Foundation And Ownership
Deepen the native runtime facade from task #2017. Reuse its claim identity and mixed transaction boundary. This task owns release and failed-finalization semantics only.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, design sections 2.2, 2.3, 7.2, 8.6, 13, and 14, and accepted `DEC-007` and `DEC-009`.

## Proof Guidance
Exercise public release and fail operations over owner, non-owner, no-active-claim, and replay states. Do not repeat start guards or transaction failure injection.

[[2026-07-24T03:20:42+02:00]]
## Builder Notes
- Change envelope: deepen `NativeRuntime` only with owner-bound release and failed-finalization operations. Preserve job openness, immutable attempt history, graph, and receipt ownership; no dispatch, MCP, Cockpit, or start-eligibility changes.
- Files changed: `serve/kanban/src/owlbear_kanban/native_runtime.py`; `serve/kanban/src/owlbear_kanban/__init__.py`; `serve/kanban/tests/test_native_runtime.py`.
- Change Module Map deviations: none. Source confirmed task #2017's facade, `AttemptStore`, `JobStore`, and `RuntimeTransaction` are the mapped owners.
- Implementation: added public `release_job` and `fail_job` request/result/diagnostic contracts. Both validate claim and starter identity, append immutable sequence-2 outcome events, clear only matching pointers in one runtime transaction, preserve pending disposition, and return matching committed outcomes on replay.
- Proof selected: one durable public-facade regression test. It earns its maintenance cost because owner isolation, atomic release/failure, immutable history, and replay are shared lifecycle invariants that are hard to verify manually and easy to regress.
- Commands run: `uv run pytest serve/kanban/tests/test_native_runtime.py` passed 10 tests. `uv run ruff check serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_native_runtime.py` and `uv run ruff format --check` for those same files passed.
- AC evidence: AC-1 is exercised by release event, pointer clear, pending disposition, and replay assertions. AC-2 is exercised by failed event detail/evidence assertions, pointer clear, and preserved sequence-1 started event assertions. AC-3 is exercised by matching replay, active non-owner, and post-finalization no-active diagnostics with no mutation branch.
- Current failure-key resolutions: none returned from verify.
- Builder challenger: pass; no concrete blockers.
- Follow-up risks: none identified.

[[2026-07-24T03:23:54+02:00]]
## Verify Notes
- Evidence reviewed: Builder Notes; committed task change `44206943a`; public `NativeRuntime` release/fail contracts; `AttemptStore` immutable event model; `RuntimeTransaction` participant boundary.
- Named authorities checked: `.owlbear/changes/replace-delivery-pipeline/design.md` sections 7.2, 8.6, 13, and 14; `graph.yaml` `REQ-008`, `REQ-009`, `REQ-016`, and `IF-003`; accepted `DEC-007` and `DEC-009`.
- Change Module Map: changed modules remain within `DN-003` runtime ownership. No map deviation.
- Normal-path boundary exercised: `uv run pytest serve/kanban/tests/test_native_runtime.py` passed 10 tests; this calls public `NativeRuntime.start_job`, `release_job`, and `fail_job` against real job/attempt stores. Replacements are limited to the lower-level repository-history stub needed for start eligibility.
- Checks run: `uv run ruff check serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_native_runtime.py` passed. `uv run ruff format --check` on the same files passed. `git diff --check 44206943a^ 44206943a` for the task files passed.
- Finding: verifier-challenger found that `_finalize` replay accepted a sequence-2 event without confirming `completed.job_id == request.job_id`. A later request for another job could receive that event and bypass ownership validation.
- Patch applied: `serve/kanban/src/owlbear_kanban/native_runtime.py` now requires the replay event's `job_id` to match the request before returning it. The focused suite and static checks passed after the repair.
- AC-to-evidence: AC-1 release behavior, AC-2 failed-event detail/evidence and preserved started event, and AC-3 ordinary owner replay/non-owner/no-active cases pass in the public-facade suite. The discovered cross-job replay branch is not covered by the durable test.
- Prior same-failure-key rejection check: none; this is the first verify rejection for `cross-job-finalization-replay`.
- Verifier-challenger: fail. It identified the cross-job replay ownership gap; source repair is applied, but requested regression proof remains absent.
- Final route: reject to build because verifier patch-pass cannot add a durable test.

### Required Follow-up
- Add a public `NativeRuntime` regression test with two materialized jobs: finalize an attempt for one job, then call the same finalization request identity with the other job ID. Assert it does not return the other job's completed event, returns the stable ownership/no-active diagnostic expected by the contract, and does not mutate either job or append a duplicate event.
- Rerun `uv run pytest serve/kanban/tests/test_native_runtime.py` and the existing Ruff checks.

[[2026-07-24T03:26:27+02:00]]
## Builder Notes
- Change envelope: resolve verifier failure key `cross-job-finalization-replay` through the existing public `NativeRuntime` test boundary only. No product behavior, runtime contract, or other lifecycle path changed.
- Files changed: `serve/kanban/tests/test_native_runtime.py`; task record `2018-p3-19-release-or-fail-owning-attempts.md`.
- Change Module Map deviations: none. The existing package-local native runtime test suite owns this public facade regression.
- Implementation: added a two-job public-facade regression. It releases job 1, replays the same request identity against job 2, requires `ERR_RELEASE_NO_ACTIVE_CLAIM`, and confirms neither job changes nor a duplicate attempt event appears.
- Proof selected: durable regression test. It earns its maintenance cost because it protects a previously observed, shared cross-job ownership regression that is hard to detect manually and easy to reintroduce.
- Commands run: `uv run pytest serve/kanban/tests/test_native_runtime.py` passed 11 tests. `uv run ruff check serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_native_runtime.py` passed. `uv run ruff format --check` for the same files passed. `git diff --check -- serve/kanban/tests/test_native_runtime.py` passed.
- AC-to-evidence: AC-1 and AC-2 remain covered by the existing public release/fail assertions in the focused suite. AC-3 is directly covered by the new cross-job replay test: it asserts the stable no-active-claim diagnostic, unchanged job records, and the original single sequence-2 event.
- Current failure-key resolution: `cross-job-finalization-replay` is resolved by the new two-job regression, which would fail if a finalization event from job 1 were returned or applied to job 2.
- Builder challenger: pass; it independently verified the focused suite and Ruff checks with no concrete blockers.
- Follow-up risks: none identified.

[[2026-07-24T03:29:35+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-3; Builder Notes; the committed release/fail implementation in `serve/kanban/src/owlbear_kanban/native_runtime.py`; package exports; focused public-facade tests; and commits `39b2b59dc` (prior verifier cross-job replay repair) and `ef7428219` (cross-job regression proof).
- Named authorities checked: `REQ-008`, `REQ-009`, `REQ-016`, and `IF-003` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; design sections 2.2, 2.3, 7.2, 8.6, 13, and 14; accepted `DEC-007` and `DEC-009`. Design section 7.2 requires replay only for the same active attempt, claim, actor, process, and timestamp identity.
- Change Module Map: no unrelated module deviation. `native_runtime.py`, the public package exports, and the focused test remain the mapped slice. The missing replay identity must be retained in the immutable attempt contract or an explicit idempotency record, which is outside this task's existing owner boundary.
- Normal-path boundary exercised: public `NativeRuntime.release_job` over a real temporary work root after a public start and release. Replacements were only fixture history and temporary filesystem beneath the public boundary.
- Checks run: `uv run --project /Users/markus/Projects/owlbear-dev pytest serve/kanban/tests/test_native_runtime.py` (11 passed); `uv run --project /Users/markus/Projects/owlbear-dev ruff check serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_native_runtime.py` (passed); `uv run --project /Users/markus/Projects/owlbear-dev ruff format --check serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_native_runtime.py` (3 files already formatted); VS Code diagnostics (none); `git diff --check` (clean).
- Finding: after a successful release, repeating the otherwise identical request with `claim_id="other-claim"` returns the committed job/event pair with no diagnostic. `_finalize` matches the completed event by job, kind, actor, process, timestamp, detail, and evidence, but the immutable event does not retain `claim_id`. This violates the authority's same-claim replay identity and makes a local verifier patch impossible without expanding the attempt-event public contract or selecting a separate idempotency-record owner.
- Patches applied: none. The prior verifier patch addressed a distinct failure key: cross-job replay ownership.
- AC-to-evidence map: AC-1 and AC-2 normal owner behavior passed the focused suite; AC-3 fails for claim-identity-mutated replay, demonstrated by the public-facade probe above.
- Prior same-failure-key check: no prior rejection for claim-identity replay found. The previous verifier repair was cross-job replay isolation, a distinct key.
- Verifier-challenger result: not invoked; a PASS verdict is not proposed.
- Final route: RESHAPE. Shape must decide the canonical durable owner for claim identity used in finalization replay, update the contract/module map, and specify the stable diagnostic for a request that differs only by `claim_id`.

[[2026-07-24T12:32:34+02:00]]
## Shape Notes
- Material repair source: verifier proved that a finalized request differing only by `claim_id` returned the existing successful event because active pointers were cleared and sequence-2 `AttemptEvent` did not retain claim identity.
- User decision: required nonempty `claim_id` on every schema-version-one `AttemptEvent`; no separate idempotency store, no claim-insensitive replay, and no compatibility fallback.
- Authority reconciliation: accepted DEC-023, added design section 7.4, extended IF-003, and narrowed design section 7.3 to the archived #2017 start diagnostic split. Missing/empty event claim returns `ERR_ATTEMPT_EVENT_IDENTITY_INVALID`. Exact finalization replay returns the existing outcome; any same-job/attempt sequence-2 mismatch returns operation-specific NON_OWNER before cleared-pointer handling; cleared pointers without that outcome return NO_ACTIVE_CLAIM; cross-job events are never returned.
- Validation: public `load_change` returns a revision with no diagnostics at digest `5d7cf64e0317707ea78015e818f9e3a328b0c4239871edb5bf66014d71ae2552`; authority diffs pass `git diff --check`. Global re-admission remains DN-013/DN-014 bootstrap debt.
- Approved graph: connected set #2003/#2018, no edge changes. #2018 owns a bounded repair of archived #2010 event contract/parser and archived #2017 started-event claim propagation; #2011 persistence/path safety and #2019 expiry remain unchanged. Eight AC cover strict claim parsing, release/fail writes, exact and mismatched completed replay, active/non-active diagnostics, cross-job isolation, and preserved start replay diagnostics.
- Challenger iterations resolved diagnostic overlap, parser literal ambiguity, cross-job preservation, reopened #2010/#2017 ownership, same-job non-claim mismatch, and archived #2017 start-diagnostic fidelity. Final complete challenge passed.
- User graph approval: approved the hardened #2003/#2018 delta.
- Lifecycle: release #2018 without movement. Commit reconciled authority and this review history, then restart the connected mutation set by claiming #2003 and #2018 in ID order.

[[2026-07-24T12:34:17+02:00]]
## Operative Finalization Replay Identity Contract

This amendment supersedes earlier Scope, Authority, ownership, and proof wording where they conflict with the contract below.

### Scope And Authority Amendment

In scope: required `AttemptEvent.claim_id`; stable parser diagnostics for missing or empty claim identity; claim propagation on started, released, and failed events; exact finalization replay; same-job completed mismatch; active-owner and no-active diagnostics; cross-job isolation; and preservation of start replay diagnostics. Expiry remains #2019. Successful completion, receipts, dispatch, MCP, and Cockpit remain outside this task.

Controlling authority is `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, design sections 2.2, 2.3, 7.2, 7.3, 7.4, 8.6, 13, and 14, and accepted `DEC-007`, `DEC-009`, `DEC-022`, and `DEC-023`. `DEC-023` and design section 7.4 control durable finalization replay identity and check precedence.

### Public Contract And Check Order

Every schema-version-one `AttemptEvent` has required nonempty `claim_id`. Missing or empty values return `ERR_ATTEMPT_EVENT_IDENTITY_INVALID`; no default, alias, backfill, or compatibility path is added. Start, release, and fail events copy the request claim.

For a sequence-two outcome belonging to the requested job and attempt, release/fail compares claim, kind, actor, process, timestamp, detail, and evidence before inspecting cleared pointers. An exact match returns the existing outcome. Any mismatch returns the operation-specific `NON_OWNER` diagnostic without mutation. A sequence-two event for another job is not returned. Cleared pointers with no sequence-two outcome for the requested job and attempt return the operation-specific `NO_ACTIVE_CLAIM` diagnostic.

Start behavior is preserved: exact replay returns the existing started event; changed claim or attempt pointers, or one populated pointer, return `ERR_START_ACTIVE_CLAIM`; matching pointers with changed actor, process, or claim timestamp return `ERR_START_IDENTITY_CONFLICT`.

### Change Module Map

- `serve/kanban/src/owlbear_kanban/attempts.py`: add required claim identity and map missing/empty values to the existing identity diagnostic while preserving strict parser, serializer, and store behavior.
- `serve/kanban/src/owlbear_kanban/native_runtime.py`: populate claim identity on both event constructors and enforce the completed-outcome replay partition before cleared-pointer handling.
- `serve/kanban/tests/test_attempts.py`: prove public claim round-trip and missing/empty rejection.
- `serve/kanban/tests/test_native_runtime.py`: prove started claim propagation, preserved start replay branches, exact and mismatched finalization replay, active/no-active diagnostics, and cross-job isolation.
- `serve/kanban/tests/test_runtime_transaction.py`: update the direct event fixture only; transaction behavior does not change.
- `serve/kanban/src/owlbear_kanban/__init__.py`: no change; `AttemptEvent` is already public.

This is a bounded repair of archived #2010's event contract/parser and archived #2017's event construction. Archived #2011's persistence/path-safety behavior is not reopened.

### Validation And Bootstrap Admission

The revised native package loads with no diagnostics at digest `5d7cf64e0317707ea78015e818f9e3a328b0c4239871edb5bf66014d71ae2552`. Global `DV-010` re-admission remains delegated to DN-013/DN-014 under the bootstrap policy; it is not a local #2018 branch.

[[2026-07-24T12:34:17+02:00]]

[[2026-07-24T12:36:59+02:00]]
## Approved Shape Handoff
- User approved required nonempty `AttemptEvent.claim_id`, strict no-compatibility migration, and completed-event ownership before cleared-pointer handling.
- Operative amendment names the public parser diagnostic, start/release/fail event propagation, exact replay, same-job mismatch, active/no-active, cross-job isolation, and preserved start diagnostics.
- Eight AC cover the complete finite scenario set at public parser/serializer and `NativeRuntime` boundaries.
- Bounded ownership: #2018 repairs archived #2010 event contract/parser and archived #2017 event construction; archived #2011 persistence/path safety and #2019 expiry remain unchanged. Dependencies do not change.
- Authority commit: 956e6c29dc5e9cef4f7379ef785e6fd63d59eb73. Parent map commit: a9ae3bb46f84a61d2b1b0c64018afb1554a9c464.
- Validation: public authority loader returned no diagnostics at digest 5d7cf64e0317707ea78015e818f9e3a328b0c4239871edb5bf66014d71ae2552; edit-contract tests passed 2; task diffs pass `git diff --check`; one operative amendment per task and exactly eight AC confirmed.
- Shaper challenger: final complete graph pass after resolving diagnostic partition, parser literal, cross-job preservation, archived invariant ownership, non-claim completed mismatch, and #2017 start-diagnostic fidelity.
- Route to builder using the operative amendment as controlling task text.

[[2026-07-24T12:42:10+02:00]]
## Builder Notes
- Change envelope: repair the shaped native attempt-event identity and finalization replay contract only. Required a nonempty `AttemptEvent.claim_id`, lifecycle propagation from start/release/fail requests, exact completed replay identity, and stable mismatch precedence. No expiry, completion, receipts, dispatch, MCP, Cockpit, or transaction behavior changes.
- Files changed: `serve/kanban/src/owlbear_kanban/attempts.py`; `serve/kanban/src/owlbear_kanban/native_runtime.py`; `serve/kanban/tests/test_attempts.py`; `serve/kanban/tests/test_native_runtime.py`; `serve/kanban/tests/test_runtime_transaction.py`.
- Change Module Map deviations: none. The transaction test changed only its direct `AttemptEvent` fixture to satisfy the strict required field.
- Implementation: `AttemptEvent.claim_id` is required and validates as identity. Start/release/fail events copy their request claim. Finalization returns a completed event only for an exact same-job identity; same-job completed mismatches return the operation-specific `NON_OWNER` before cleared-pointer handling, while cross-job events remain isolated.
- Proof selected: durable parser and public native-runtime regressions. They earn their maintenance cost because immutable claim identity and idempotent finalization replay are shared lifecycle invariants that are easy to regress and difficult to detect manually.
- Commands run: `uv run pytest serve/kanban/tests/test_attempts.py serve/kanban/tests/test_native_runtime.py` passed 32 tests. `uv run ruff check` and `uv run ruff format --check` for the five changed files passed. `git diff --check` for the five changed files passed. VS Code diagnostics found none.
- Additional check: `uv run pytest serve/kanban/tests/test_attempts.py serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_runtime_transaction.py` had 42 passing and 4 pre-existing failures in `test_runtime_transaction.py`; its fixtures use invalid `JobDisposition` literals `updated` and `transaction`. This task changed only the required direct event fixture and did not alter transaction behavior.
- AC-to-evidence: AC-1 parser/serializer round-trip plus missing and empty claim diagnostics are directly covered in `test_attempts.py`. AC-2 release claim propagation, pointer clear, and pending disposition are covered through public `release_job`. AC-3 fail claim/detail/evidence propagation and preserved sequence-one history are covered through public `fail_job`. AC-4 exact release/fail replay is covered by existing public assertions. AC-5 same-job release/fail claim mismatches return their respective `NON_OWNER` diagnostics without job mutation. AC-6 active non-owner and cleared no-active release/fail diagnostics are covered. AC-7 cross-job finalization replay remains covered without returning or mutating either job. AC-8 started-event claim propagation, exact replay, changed claim active-claim, and changed timestamp identity-conflict branches are covered.
- Current failure-key resolutions: `claim-identity-finalization-replay` is resolved by durable release and fail mismatch regressions; the former cross-job finalization replay regression remains passing.
- Builder challenger: pass. It confirmed focused proof, scope, and that the broader transaction failures arise from unrelated invalid disposition fixtures.
- Follow-up risks: the known transaction fixture failures remain outside this task scope.
