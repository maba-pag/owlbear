---
id: 2040
title: 'P5-06: Complete and prove the native MCP control plane'
status: build
priority: high
created: 2026-07-25T09:11:58.219921+02:00
updated: 2026-07-25T13:44:40.266612+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - integration
  - removal
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-006
  - interface:IF-010
  - proof:PROOF-011
parent: 1981
depends_on:
  - 2028
  - 2029
  - 2030
  - 2031
  - 2042
ac:
  - 'AC-1: With tool exclusions unset, the live FastMCP registry is `list_changes
    | show_change | validate_change | admit_change | list_jobs | show_job | pick_jobs
    | start_job | finish_plan | finish_build | finish_accept | finish_audit | release_job
    | recover_expired_claims | create_request | list_requests | show_request | change_health
    | work_health | list_activity | list_attempts | show_receipt`; schemas and `ToolAnnotations`
    match read, mutation, and idempotency semantics.'
  - 'AC-2: Registry and source inspection prove `list_tasks | show_task | create_task
    | edit_task | move_task | start_work | end_work | pick_tasks | finish_shape` plus
    compatibility aliases are absent, while the eight IF-015 operations preserve their
    proved request, result, and proof-checkout cleanup contracts.'
  - 'AC-3: A maintained PROOF-011 scenario invokes public MCP tools over the real
    graph-aware engine from change inspection and validation through admission, native
    request creation, job query, pick, start, purpose-specific completion, receipt,
    attempt and activity reads, and health; only temporary authority, work, and repository
    stores replace lower persistence.'
  - 'AC-4: Given malformed parameters, unknown identities, stale authority, request
    conflicts, admission conflicts, or transaction failure, public tools return stable
    JSON domain codes and artifact snapshots show no partial mutation by the affected
    operation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-006`. Resolve normative behavior from `DN-009`, `IF-010`, retained `IF-015`, `MIG-003`, `PROOF-011`, and `PROOF-014`; this record is not specification authority.

## Outcome
Complete one strict native OwlBear Kanban MCP control plane, preserve the eight IF-015 job operations within IF-010, remove generic task and old lifecycle registrations, and prove the assembled public workflow.

## Envelope
In: final FastMCP registration, strict schemas and annotations, stable JSON domain-error mapping, removal or replacement of obsolete MCP adapters/tests, retained IF-015 contracts, and maintained PROOF-011 integration evidence.

Out: activating native orchestration as the default, setup and seed changes, agent/prompt migration, Cockpit HTTP/UI, OpenSpec removal, legacy history snapshot, consumer cutover, and request resolution. DN-012 owns those atomic cutover outcomes.

Proof guidance: exercise public MCP tools over the real graph-aware engine from change inspection through admission, native request creation, job lifecycle, evidence reads, and health; replacements are limited to temporary authority, work, and repository stores below the MCP boundary.

[[2026-07-25T12:43:49+02:00]]
## Builder Notes
REJECT to shape for `#2040-AC3/admission-work-store-handoff` after the first assembled PROOF-011 probe.

Registry work is locally implemented but not committed: the live FastMCP surface is now exactly the shaped 22 tools, with the eight generic task registrations and `finish_shape` absent. The exact registry/absence checks pass and the full MCP suite passed 421 tests before the integration probe. Admission JSON arrays also required transport-correct `model_validate_json` so strict tuple-backed evidence can be submitted through MCP.

The maintained public probe then invoked `list_changes`, `show_change`, `validate_change`, exact-replay `admit_change`, and `list_jobs` over copied admitted authority plus real `AdmissionTransaction`, `RuntimeTransaction`, `DispatchRuntime`, `NativeRuntime`, and `JobStore`. It fails at the causal handoff: admission returns its receipt/generation, but `list_jobs` returns 0 active records for 14 delivery nodes.

Current source explains the failure. `AdmissionTransaction` publishes only the immutable receipt and one `JobGeneration` document under the change package. `DispatchRuntime` and all job query/start/completion operations read numeric job records from `app_ctx.kanban_dir/jobs`. No public operation materializes admission generation into that work store. The admitted design explicitly requires admission to create one initially plan-ready `plan` job record per delivery node under `.owlbear/kanban/jobs/`.

This cannot be repaired solely inside #2040's MCP/test envelope without duplicating core transaction semantics or allowing partial cross-store mutation. `RuntimeTransaction` already supports participants with different roots; a core admission repair can use the work root as manifest root and include receipt, generation, and one `JobStore.create_participant` per plan job in one recoverable transaction. #2040 can then pass `app_ctx.kanban_dir` and retain public error mapping. Existing uncommitted #2040 registry, JSON normalization, and PROOF-011 probe changes are task-conforming candidate work for the retry and must be adopted rather than discarded.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | #2040-AC3/admission-work-store-handoff | shaper | Create one core admission child packet, dependent on #2028 and gating #2040, whose transaction accepts the native work root and atomically publishes the admission receipt, generation, and one numeric plan `JobRecord` per delivery node across authority/work roots; exact replay, conflict, injected failure, and retry must preserve all-or-none state. | `serve/kanban/src/owlbear_kanban/admission_transaction.py`; `serve/kanban/tests/test_admission_transaction.py` | Public PROOF-011 segment returns 0 jobs after successful admission; design section 6 requires one initial plan job per node. |
| 2 | #2040-AC3/admission-work-store-handoff | shaper | Keep #2040 scoped to MCP assembly: depend on the core packet, pass `app_ctx.kanban_dir` into the repaired transaction, and complete maintained PROOF-011 through request creation, job query/pick/start/completion, receipt/attempt/activity reads, and health without lower-boundary mutation shortcuts. | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`; `serve/mcp-kanban/tests/test_mcp_surface_contract.py`; `serve/mcp-kanban/tests/test_mcp_server.py` | Current first segment is a public failing test at the missing admission-to-work-store edge. |

[[2026-07-25T13:13:37+02:00]]
## Shape Notes
Repair classification: prescribed split for recurring failure key `#2040-AC3/admission-work-store-handoff`. The admitted design already requires globally monotonic numeric job identities and one initial plan job per delivery node, so this repair changes neither product behavior nor #2040 acceptance meaning.

The failure key is resolved by two ordered core packets. #2041 owns one `JobStore` reservation-participant API for contiguous globally monotonic identities in the flat work store. #2042 consumes that participant and owns one recoverable cross-root transaction that publishes the authority receipt and generation together with the work-store sequence and numeric plan jobs. #2040 depends on #2042 and remains limited to MCP assembly, error mapping, and public PROOF-011.

### Repair Closure Map
| Failure Key | Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof / Negative Control | Executor |
|---|---|---|---|---|---|
| `#2040-AC3/admission-work-store-handoff` | Public `admit_change` followed by `list_jobs` through the assembled MCP adapter and graph-aware engine | `AdmissionTransaction`, `RuntimeTransaction`, `JobStore`, `DispatchRuntime`, `server.admit_change`, and `server.list_jobs` | Fresh copied authority plus temporary work root: admit current evidence, then count queried jobs | With #2042, returned generation identities select the persisted numeric records and query returns one plan job per graph node; bypassing #2042 reproduces the observed 0 records for 14 nodes | Core pytest and MCP pytest are installed and runnable through `uv run` |

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owner |
|---|---|---|---|---|
| `serve/kanban/src/owlbear_kanban/jobs.py` | Flat active/archive numeric job storage and transactional job participants | Add reservation participant and native sequence validation | New core API; no MCP registration | #2041 |
| `serve/kanban/src/owlbear_kanban/admission_transaction.py` | Immutable admission receipt and generation publication | Accept work root, consume reservation, publish sequence and plan jobs in one cross-root transaction | Existing admission constructor/call contract changes | #2042 |
| `serve/kanban/src/owlbear_kanban/runtime_transaction.py` | Recoverable multi-root OCC publication | Reuse unchanged unless a concrete local defect is exposed | None expected | Current source authority |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | FastMCP transport and runtime assembly | Pass work root, retain JSON evidence normalization, expose only 22 native tools | Public registry narrowed to IF-010 | #2040 |
| `serve/mcp-kanban/tests/test_mcp_surface_contract.py` | Maintained assembled registry and IF-015 proof | Complete causal PROOF-011 through admission, request, lifecycle, evidence, and health | Durable public-boundary proof | #2040 |

### Product Invariant Map
| Product Invariant | Owner | Normal Boundary | Proof / Allowed Replacement |
|---|---|---|---|
| Native job identities remain globally monotonic across active and archived work | #2041 | `JobStore` reservation plus `RuntimeTransaction` commit | Temporary work root; no allocator mock |
| Admission publishes authority and initial work as one recoverable operation | #2042 | `AdmissionTransaction.validate_and_admit` | Copied authority and temporary work root; no publication shortcut |
| The deployed control plane is the exact 22-tool native IF-010 surface | #2040 | Live FastMCP registry | Lower persistence may be temporary |
| Public admission causally feeds request and job lifecycle operations | #2040 | Maintained PROOF-011 through exported MCP functions | Authority, work, and repository stores may be temporary; MCP functions and graph-aware engine remain real |

### Dependency Closure Map
| Task | Load-Bearing Input / Participant | Producer / Authority | Required Predecessor |
|---|---|---|---|
| #2041 | `JobStore`, active/archive records, `TransactionParticipant`, OCC replacement | Current `jobs.py` and `runtime_transaction.py` | #2028 |
| #2042 | Reservation IDs and sequence participant | #2041 AC-1 through AC-4 | #2041 |
| #2042 | Receipt/generation participants and multi-root recovery | #2028 plus current `AdmissionTransaction` / `RuntimeTransaction` | #2028 |
| #2040 | Atomic admission-created numeric jobs | #2042 AC-1 through AC-4 | #2042 |
| #2040 | Native query, request, receipt, history, health, and IF-015 operations | Archived #2029, #2030, #2031 and retained current source | #2029, #2030, #2031 |

### Scenario Closure Map
| Task | Risk Boundary | Input / State Classes | Failure / Recovery / Race Classes | AC |
|---|---|---|---|---|
| #2041 | Sequence reservation | Empty; active maximum; archive maximum; higher sequence | Malformed/non-positive sequence; unsafe path; stale competing reservation | AC-1 through AC-4 |
| #2042 | Cross-root admission | Admitted; non-admitted; exact replay; explicit IDs; automatic IDs | Changed evidence; explicit collision; one stale auto-allocation retry; failure before/after publication and before manifest cleanup | AC-1 through AC-4 |
| #2040 | Public control plane | Normal inspection/admission/request/lifecycle/evidence/health journey | Malformed parameter; unknown identity; stale authority; request/admission conflict; transaction failure | AC-1 through AC-4 |

Board audit: #2041 is build-ready behind archived #2028. #2042 is in build and dependency-blocked on #2041. #2040 now depends on #2042 and routes to dependency-blocked build; `dep_status` prevents dispatch until the core chain archives. The revised graph passed shaper challenge after the original reconsideration exposed the missing global allocator owner. A later lifecycle objection was reconsidered and passed under the board's dependency-blocked build semantics.

Existing uncommitted #2040 changes in `server.py`, `test_mcp_surface_contract.py`, and `test_mcp_server.py` are adopted as task-conforming candidate work: exact 22-tool registry removal, JSON-mode evidence normalization, and the causal PROOF-011 probe. They remain outside this shaping commit and must be revalidated against #2042 rather than discarded or treated as completed proof.

[[2026-07-25T13:43:00+02:00]]
Builder complete. The live FastMCP registry is exactly the 22 native IF-010 tools; generic task and finish_shape registrations are absent; all native tools explicitly declare correct read/mutation, idempotent, non-destructive annotations; retained IF-015 operations remain registered and covered. Admission evidence uses strict JSON-mode normalization and admit_change passes app_ctx.kanban_dir into the archived #2042 cross-root transaction. Maintained PROOF-011 now traverses public inspection, validation, admission, request create/list/show, job list/pick/start/finish_plan, completion receipt, attempts, activity, change health, and work health over real graph-aware runtime and temporary stores. Public malformed/admission-conflict/publication-error cases return stable codes and preserve complete artifact snapshots; existing suites cover unknown/stale/request and retained lifecycle negatives. Validation: complete MCP package 426 passed; core admission/allocator/transaction 54 passed with 2 existing fork warnings; focused lint and editor diagnostics clean. builder-challenger decision: pass with no findings.

[[2026-07-25T13:44:40+02:00]]
Verifier rejection on AC-2. Registry absence passed, but server.py still defines and exports obsolete compatibility APIs list_tasks, show_task, create_task, edit_task, move_task, start_work, end_work, and pick_tasks. Required repair: remove obsolete adapter definitions and exports, remove/replace tests importing those symbols, add source/module API absence proof for all obsolete names and aliases, rerun complete MCP suite, then re-challenge. Other AC evidence passed.
