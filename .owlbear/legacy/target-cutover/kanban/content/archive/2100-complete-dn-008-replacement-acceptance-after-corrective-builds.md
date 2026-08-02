---
id: 2100
title: Complete DN-008 replacement acceptance after corrective builds
status: archived
priority: high
created: 2026-07-28T05:20:51.823233+02:00
updated: 2026-07-28T06:09:44.164598+02:00
tags:
  - phase-17
  - scope:core
  - type:fix
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-008
  - proof:PROOF-007
parent: 1968
depends_on:
  - 1985
  - 2099
ac:
  - 'AC-1: Given public MCP `reject_accept` with one or more same-node `build-repair`
    routes and a positive unused replacement ID, rejection persists one new current-digest
    `accept` job whose predecessors are the corrective build IDs and leaves the original
    superseded; `pick_jobs` omits the replacement until those receipts are current,
    then exposes it as the sole current accept.'
  - 'AC-2: Plan-only correction or design re-entry forbids a replacement ID and persists
    no eager accept. Mixed plan/build or cross-node work, a missing/nonpositive required
    ID, an unexpected ID, or an active/archived collision returns public parameter,
    invalidation, or identity failure before persisting rejection state.'
  - 'AC-3: Replaying an all-build rejection returns the same replacement accept; changing
    its ID returns identity conflict without mutation. Injected rejection interruption
    leaves no finding, supersession receipt, corrective job, replacement accept, failed
    event, or partial archive.'
  - 'AC-4: In a temporary public MCP scenario, finishing only a strict subset of one
    or two corrective builds keeps the replacement out of `pick_jobs`; finishing the
    remainder exposes and starts it at the corrected commit. The proof never invokes
    final audit, DN-015, `setup/finalize.py`, or a live carrier path.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
A public delivery-node rejection with one or more same-node build-repair routes atomically publishes one immutable replacement `accept` job gated on the complete corrective-build closure, so corrected work can return to independent acceptance without reopening the rejected job.

## Scope
In scope: accept-only continuation identity at public MCP `reject_accept` and `NativeRuntime`; all-build route classification; atomic replacement publication; dependency readiness; replay, conflict, interruption; focused temporary-workspace proof. Out of scope: `reject_audit`, Cockpit mutation routes, plan-generated replacement acceptance, design re-entry continuation, DN-013 final audit, live carrier mutation, and compatibility/backfill behavior.

## Authority
DN-008, REQ-006, REQ-008, IF-009, DEC-009, PROOF-007, RISK-008, and RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`. Archived DN-008 #1985 and corrective packet-authority repair #2099 are lineage dependencies. Late discovery is #2097's resumed-dispatch failure after successful corrective finish.

## Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact |
|---|---|---|---|
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Validate and atomically publish accept rejection, replay, findings, invalidation, events, and cleanup. | Add accept-only replacement identity; classify all-build/plan-only/design/malformed closures; prepare, publish, replay, and expose one replacement accept for eligible all-build corrections. | `RejectAcceptRequest` gains `replacement_accept_job_id`; `RejectAuditRequest` must not expose it. |
| `serve/kanban/src/owlbear_kanban/invalidation.py` | Prepare immutable corrective routes/jobs and supersession participants. | Read-only corrective job-kind and identity authority consumed by rejection preparation. | None. |
| `serve/kanban/src/owlbear_kanban/jobs.py` | Define immutable job identity and readiness dependencies. | Reuse existing `accept` record with predecessor IDs and current node-plan digest. | No schema field addition. |
| `serve/kanban/src/owlbear_kanban/dispatch.py` | Select jobs whose authority and predecessor receipts are current. | Read-only eligibility boundary used by focused proof. | None. |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Validate public MCP reject parameters. | Expose replacement identity only for `reject_accept`; keep `reject_audit` unchanged. | Public reject-accept schema changes. |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Adapt public MCP reject operations to runtime requests. | Forward accept-only replacement identity without leaking it to reject-audit. | Public `reject_accept` gains one conditional field. |
| Focused Kanban/MCP tests | Protect rejection atomicity, replay, and public dispatch. | Add parameterized readiness and malformed-route controls; retain #2097 as downstream assembled proof. | Test-only. |

Complexity waiver: route classification, replacement identity, transaction atomicity, replay, and dispatch readiness are inseparable properties of one public rejection transaction. Splitting them would allow an under-gated or non-replayable continuation to pass component proof. Use parameterized existing harnesses rather than one test per criterion.

## Scenario Matrix
- One and multiple same-node build-repair routes.
- Replacement omitted before any corrective receipt and after partial completion; sole eligible accept after all corrective receipts are current.
- Exact replay, changed identity, active/archived collision, missing/nonpositive identity.
- Plan-only correction and design re-entry with no eager accept.
- Mixed plan/build and cross-node closure fail closed.
- Injected rejection interruption leaves no partial state.
- Focused temporary public MCP rejection-to-replacement-dispatch proof; downstream #2097 retains complete correction-to-audit ownership.

## Repair Closure Map
| Failure Key | Claimed Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof Or Negative Control | Executor Availability |
|---|---|---|---|---|---|
| `DN-013/resumed-dispatch-no-accept-job` | Public `reject_accept` preserves immutable failed acceptance while creating a dependency-gated path to re-acceptance for an all-build corrective closure. | `native_runtime.py::{RejectAcceptRequest,_prepare_accept_rejection,_commit_accept_rejection,_reject_accept_replay}`, `invalidation.py::{PreparedInvalidation,InvalidationRequest}`, `runtime_transaction.py::RuntimeTransaction`, MCP models/server, existing `JobRecord`/`DispatchRuntime.pick_waves`, and `test_complete_native_delivery.py`. | Reject an accept with two corrective builds and an explicit replacement ID. The replacement exists but is omitted immediately and after one corrective finish; after both receipts become current, `pick_jobs` exposes it alone. Current HEAD has no replacement and empty resumed waves. | Positive: same target/current digest, both corrective predecessors, sole eligibility after both receipts. Negative: malformed identity, mixed/cross-node route, plan-only/design no eager accept, replay mismatch, and interruption leave no partial continuation. | Existing NativeRuntime, MCP reject/start/finish/pick tools, JobStore, RuntimeTransaction hooks, and temporary acceptance/PROOF-013 harnesses are available; no new engine or route is required. |

## Proof Guidance
Use public MCP `reject_accept`, `pick_jobs`, `start_job`, and purpose-specific finish boundaries over a temporary workspace. Prove replacement existence through persisted `JobStore` and readiness through public dispatch. Do not complete #2097's final audit here and never pass the live carrier, live change root, or finalizer input.

[[2026-07-28T05:29:59+02:00]]
Interrupted builder recovery: coding subagent returned prematurely without tests, challenger, lifecycle note, or commit and incorrectly reported pytest unavailable. Effect check found one bounded candidate diff in `native_runtime.py`, MCP models/server, plus claim metadata. Existing reject-accept tests pass 16/16, but source review found contract gaps: reject-audit parameter leakage, missing required replacement identity for all-build closures, malformed mixed/cross-node closure acceptance when ID absent, archived collision omission, and an incorrect completion receipt on the pending replacement. Claim released so the candidate can be adopted and repaired in a clean build attempt.

[[2026-07-28T06:04:50+02:00]]
## Builder Notes
Adopted and repaired the interrupted same-task candidate within the shaped seven-file module map.

Implemented accept-only `replacement_accept_job_id` validation and MCP exposure, with strict reject-audit isolation. Native rejection now classifies prepared corrective closure independently of ID presence: same-node all-build requires a positive unused replacement identity; same-node plan-only or zero-job design re-entry forbids one; mixed and cross-node closures fail closed. The replacement is a current-digest pending accept with exact corrective predecessors, no packet or receipt, and is published in the same transaction as findings, supersession, corrective jobs, failed event, and original-job supersession. Typed result, query refresh, and exact replay expose and validate the replacement; active/archive collisions and changed IDs return identity conflict.

Durable proof covers one and two corrective builds, zero/partial/full readiness through public `pick_jobs`, start at the corrected commit in a disposable consumer, replay, missing/nonpositive/unexpected IDs, active/archive collisions, plan/design controls, mixed/cross-node closure rejection, and transaction interruption with byte-for-byte no mutation.

Evidence:
- Focused replacement/public lifecycle bundle: 36 passed, 62 deselected.
- Full Kanban package: 392 passed; four existing Python fork deprecation warnings.
- Builder challenger: pass; independent 33 focused tests and Ruff clean.
- Ruff check, Ruff format check, git diff check, and VS Code diagnostics: clean.
- MCP API/lifecycle suite excluding interaction modules returned exit 0. Full interaction modules remain independently incompatible with unrelated dirty `share/agents/builder.agent.md` and `share/prompts/ideate.prompt.md` exact-text expectations; no #2100-owned path touches those assets.

### AC Evidence
- AC-1 and AC-4: `test_replacement_accept_waits_for_every_corrective_build` plus `test_complete_native_delivery.py` prove persisted predecessor-gated continuation, zero/partial omission, sole full-closure eligibility, and start at corrected commit through public MCP tools.
- AC-2: native invalid-replacement matrix and MCP schema tests prove plan/design no eager accept, mixed/cross-node fail closed, positive parameter validation, accept-only schema, and active/archive collision handling before mutation.
- AC-3: exact replay returns the same typed replacement; changed identity conflicts; injected transaction failures preserve complete pre-rejection snapshots.

[[2026-07-28T06:08:58+02:00]]
## Verifier Notes
PASS at builder commit `4438f6e4ec9e2d5076e64eb35e4e2f27aa0d9f05`.

Direct verifier proof reran native replacement identity/atomicity, public two-build readiness, disposable-consumer corrected-commit start, and MCP accept/audit schema isolation: 33 passed, 54 deselected. The committed slice exactly matches the shaped module map and contains no uncommitted production/test changes.

AC review:
- AC-1: replacement is atomically persisted with current node-plan digest, exact corrective predecessors, no receipt, and original accept superseded; public dispatch gates on predecessor currentness.
- AC-2: positive accept-only public parameter, no audit leakage, plan/design no eager accept, malformed mixed/cross-node closures and active/archive collisions fail before mutation.
- AC-3: exact replay returns the stored replacement, changed identity conflicts, and interruption snapshots prove no partial finding, receipt, job, event, or archive.
- AC-4: one/two-build public scenarios prove zero/partial/full readiness and replacement start at the corrected commit without final audit or live carrier mutation.

Verifier challenger decision: pass. Memory preflight returned 20 entries and all were assessed; live adapter schema, exact replay, refined artifact-scope, and active-workspace guidance were applied. No new reusable memory candidate was identified.

Known full-MCP interaction failures remain unrelated dirty agent/prompt exact-text expectations outside this task; the MCP API/lifecycle subset and all focused public paths pass.

[[2026-07-28T06:09:44+02:00]]
## Collector Notes
ARCHIVED as completed.

Leaf archive readiness is satisfied: dependencies #1985 and #2099 are archived completed, builder implementation is committed at `4438f6e4ec9e2d5076e64eb35e4e2f27aa0d9f05`, verifier reran 33 direct public/native checks, both required challengers passed, full Kanban regression passed 392 tests, and all four ACs have named public or atomicity evidence. The task introduced no unresolved request, block, scratch artifact, or uncommitted code/test change.

The parent #1968 intentionally remains in collect and blocked on its other active descendants; archiving this completed leaf removes #2100 as a root blocker without claiming aggregate DN-013 or DN-015 closure.
