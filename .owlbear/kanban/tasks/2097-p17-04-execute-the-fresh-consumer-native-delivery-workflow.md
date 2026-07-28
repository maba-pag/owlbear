---
id: 2097
title: 'P17-04: Execute the fresh-consumer native delivery workflow'
status: build
priority: high
created: 2026-07-27T19:45:12.576115+02:00
updated: 2026-07-28T06:21:19.238510+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T4
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on:
  - 2099
  - 2100
ac:
  - 'AC-1: Given a temporary consumer initialized by public setup and a representative
    admitted fixture with two delivery-work nodes/two modules plus mandatory DN-014
    audit authority, installed design contracts plus public MCP `show_change`, `validate_change`,
    and `admit_change` publish digest-bound frontier plan jobs while a plan outside
    admitted authority fails without a plan receipt or packet job.'
  - 'AC-2: Given engine-selected jobs, public MCP pick, start, and purpose-specific
    finish operations run plan and reviewed build work under shared writer coordination;
    a read-only proof checkout rejects one implementation defect, publishes the minimum
    corrective build job, then the corrected commit is independently accepted while
    stale or superseded receipts release no work.'
  - 'AC-3: Given accepted nodes at the corrected commit, public audit starts in a
    disposable read-only checkout and publishes one final audit receipt whose predecessor
    IDs, delivery/node-plan digests, code revision, impact closure, evidence IDs,
    and corrective history match persisted stores; native health reports no unresolved
    claim, writer, request, finding, or active legacy execution path.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
One temporary fresh consumer runs a representative two-module change from installed design contracts through public admission and engine-selected plan, reviewed build, independent acceptance, one corrective cycle, and final audit.

## Scope
In scope: MOD-008 assembled Python proof using public setup and real MCP, engine, writer, Git, and proof-checkout boundaries. Out of scope: live OwlBear carrier mutation, production fixes, and mocked lifecycle completion.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, IF-002/003/005/009/010/013/014, RISK-003/RISK-005/RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Complexity waiver: PROOF-013 requires one assembled design-to-audit boundary; splitting lifecycle phases would bypass it. A bounded fixture contains two delivery-work nodes/two modules plus the mandatory DN-014 audit-authority node.

Proof guidance: reuse the current assembled MCP harness over a temporary Git consumer and generate the reduced admitted fixture through structured change authority; replace only repository location and fixture authority, never public setup, MCP, engine, writer, Git, or checkout boundaries.

[[2026-07-27T22:10:18+02:00]]
## Builder Notes
REJECT: the assembled public corrective cycle exposes a production runtime defect, and the task contract explicitly forbids patching production here.

- Added `serve/mcp-kanban/tests/test_complete_native_delivery.py`, a task-scoped PROOF-013 red proof. Public `setup/init.py` initializes a Git consumer under pytest `tmp_path`; all setup, change, runtime, writer, Git, and proof-checkout roots are disposable.
- Safety binding: the proof asserts its work root is not under `/Users/markus/Projects/owlbear-dev/.owlbear/kanban`, its change root is not under the live change source, and no legacy root exists. It never invokes DN-015 or `setup/finalize.py`, and never passes the live carrier or active legacy carrier to setup, finalization, runtime, or checkout mutation.
- Causal flow: public `reject_accept` independently rejects the defective checkout and publishes exactly one corrective `build` job; a corrected disposable Git commit is created; public `start_job` accepts that corrective job at the corrected SHA; public `finish_build` then returns `ERR_FINISH_AUTHORITY_STALE` with lower code `ERR_RECEIPT_NODE_PLAN_DIGEST_STALE`.
- Root cause: `serve/kanban/src/owlbear_kanban/invalidation.py::_corrective_jobs` creates corrective build jobs without `node_plan_digest`, while `serve/kanban/src/owlbear_kanban/native_runtime.py::_finish` requires every non-plan job digest to equal current node-plan authority. The red proof confirms no corrected receipt is published and the owning active claim remains for diagnosis/retry.
- Exact proof: `uv run pytest serve/mcp-kanban/tests/test_complete_native_delivery.py -q --tb=short -n 0` reaches the expected final success assertion and fails only with the stale node-plan diagnostic after all negative controls pass.
- Regression: `uv run pytest serve/kanban/tests -q --tb=short -n 0` passed 378 tests. `uv run pytest serve/mcp-kanban/tests -q --tb=short -n 0` reproduced this red proof; it also had seven unrelated dirty-worktree contract failures in builder/designer agent prompt assertions and reached the configured 300-second session timeout (52 passed before timeout).
- Quality: `uv run lint serve/mcp-kanban/tests/test_complete_native_delivery.py` passed; VS Code diagnostics and `git diff --check` are clean.
- Builder-challenger: pass. It reproduced the causal failure, confirmed the disposable/live-carrier exclusion and fail-closed no-publication controls, and approved reject-to-shape rather than a production patch.
- Memory: all recalled entries were assessed; the returned pairwise-precedence entry ID was not found by the memory service and is recorded as an entry-level assessment failure.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC-2/corrective-build-node-plan-digest | shaper via `/shape` | Assign the owning production node a fix so engine-created corrective build jobs carry current node-plan authority and can complete through public `finish_build`; retain this assembled red proof for closure. | `serve/kanban/src/owlbear_kanban/invalidation.py`, `serve/kanban/src/owlbear_kanban/native_runtime.py`, `serve/mcp-kanban/tests/test_complete_native_delivery.py` | Exact serial test returns `ERR_FINISH_AUTHORITY_STALE` / `ERR_RECEIPT_NODE_PLAN_DIGEST_STALE`; challenger decision `pass`. |

[[2026-07-28T02:35:36+02:00]]
## Shape Notes

Material graph repair for failure key `AC-2/corrective-build-node-plan-digest` was challenged and user-approved.

- The production fix is assigned to new owning task #2099 under root #1968 with archived DN-008 #1985 as lineage; this task now depends on #2099.
- The committed red assembled proof remains the causal closure check and continues to exclude the live carrier, live change root, DN-015, and `setup/finalize.py`.
- No AC, scope, authority, or proof guidance changed. This task stays in `shape` while #2099 is active; after #2099 archives, a local repair may record closure of this failure key and route #2097 back to `build`.
- Final shaper-challenger: `pass`; user approved the graph.

[[2026-07-28T05:19:28+02:00]]
Shaping claim normalization: resumed PROOF-013 confirmed #2099 closes corrective finish, then exposed failure key `DN-013/resumed-dispatch-no-accept-job`. Current-source diagnosis, three challenger rounds, the completed Repair Closure Map, and user approval establish a material late DN-008 repair leaf. This claim is released without status change so the complete connected mutation set (#1968, #1990, #2097) can be claimed in deterministic ID order before graph writes.

[[2026-07-28T05:21:16+02:00]]
## Shape Notes
Connected repair update after #2099 closure and resumed PROOF-013 diagnosis.

- Failure key `AC-2/corrective-build-node-plan-digest` is closed by archived #2099: corrective build now completes through public `finish_build` with current packet and node-plan authority.
- New failure key `DN-013/resumed-dispatch-no-accept-job` is proven after that finish: public `pick_jobs` returns no accept work because all-build rejection supersedes the original accept and publishes no immutable replacement.
- Current-source owners, cheapest partial-versus-complete corrective-receipt dispatch check, negative controls, executor availability, and causality are recorded in #2100's Repair Closure Map.
- User approved and shaper-challenger passed new root repair #2100. #2097 now depends on #2100 and remains in `shape`; after #2100 archives, it returns to `build` without AC, scope, authority, or proof-guidance changes and completes the full correction-to-audit proof.
- The disposable/live-carrier exclusions remain binding. #2097 does not patch production or invoke DN-015.

[[2026-07-28T05:22:07+02:00]]
Connected graph mutation complete: earlier node-plan-digest failure is closed by archived #2099; resumed-dispatch failure is assigned to build-ready #2100 with complete Repair Closure Map. #2097 stays in shape and blocked on #2100, preserving its ACs and disposable full-workflow proof boundary. Claim released.

[[2026-07-28T06:11:51+02:00]]
## Shape Notes
Mechanical reroute after completion of the approved repair graph; no AC, scope, authority, dependency, or proof-guidance change.

- Failure key `AC-2/corrective-build-node-plan-digest` remains closed by archived completed #2099; public corrective build completion is now proven with packet and current node-plan authority.
- Failure key `DN-013/resumed-dispatch-no-accept-job` is closed by archived completed #2100 at builder commit `4438f6e4ec9e2d5076e64eb35e4e2f27aa0d9f05`; public one/two-build proofs show replacement acceptance omitted through partial correction and selected/started after the full current receipt closure.
- The actual proof artifact `serve/mcp-kanban/tests/test_complete_native_delivery.py` now resumes replacement acceptance instead of preserving the stale empty-dispatch xfail. It remains disposable and retains the live-carrier, live change root, DN-015, and `setup/finalize.py` exclusions.
- The previously approved Repair Closure Map and shaper-challenger pass in #2100 establish the production owner, causal public check, negative controls, and executor availability. #2100's archived completion satisfies the prior explicit route: #2097 returns to build and completes its unchanged full correction-to-audit AC boundary.

Board audit: #2097 `dep_status=ok`; #2099 and #2100 are archived completed; downstream #2098 remains blocked on #2097. All 18 recalled shaper memories were assessed.

[[2026-07-28T06:16:00+02:00]]
## Builder Notes
REJECT to shape for a newly demonstrated proof-contract contradiction; no code or test edit was made in this build attempt.

The current proof artifact copies the full admitted 15-node change and shortcuts into `_active_accept`; after corrected DN-001 replacement acceptance, production correctly emits dependent reconciliation plans and cannot create final audit until every admitted node has a current accept. The operative AC/guidance instead requires a literal two-node fixture through real final audit.

Current source makes literal two-node audit impossible without bypass or production change:
- `NativeRuntime._terminal_audit_authority` resolves mandatory `DN-014` and its plan.
- Receipt audit validation requires `PROOF-008`.
- `_terminal_accept_jobs` requires a current accept for every admitted node before creating audit.
- Existing task scope forbids mocked lifecycle completion or production fixes.

Smallest faithful fixture: two delivery-work nodes/two modules plus the mandatory DN-014 audit-authority node (three graph nodes total). This preserves public setup, admission, engine selection, writer, Git, checkout, correction, independent acceptance, audit, and health boundaries.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|---|
| 1 | `PROOF-013/literal-two-node-audit-impossible` | shaper via task repair | Correct AC-1 and proof guidance to a three-graph-node fixture consisting of two delivery-work nodes/two modules plus mandatory DN-014 audit authority; preserve unchanged assembled lifecycle and safety exclusions. Challenge the repaired proof contract before returning to build. | task #2097; `serve/mcp-kanban/tests/test_complete_native_delivery.py` | `native_runtime.py::{_terminal_audit_authority,_terminal_accept_jobs}` and `receipt.py` audit evidence require DN-014/PROOF-008 and accepts for every admitted node; read-only exploration found no missing executor or production premise beyond fixture wording. |

### Repair Closure Map
| Failure Key | Claimed Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof Or Negative Control | Executor Availability |
|---|---|---|---|---|---|
| `PROOF-013/literal-two-node-audit-impossible` | One disposable public setup-to-audit workflow | `native_runtime.py::{_prepare_terminal_audit,_terminal_audit_authority,_terminal_accept_jobs}`, `receipt.py` audit validation, `test_complete_native_delivery.py` | Load a reduced graph without DN-014: terminal acceptance creates no audit; include DN-014 and current accepts for all fixture nodes: audit is eligible | Public returned jobs must select every plan/build/accept/audit action; missing work-node accept or DN-014 authority prevents audit, detecting bypass | Public MCP tools, real Git/checkouts, structured change loader, and temporary consumer are available; a three-node fixture needs no production change. |

[[2026-07-28T06:17:00+02:00]]
## Shape Notes
Local proof-contract repair for `PROOF-013/literal-two-node-audit-impossible`.

- AC-1 and the operative fixture guidance now require three graph nodes: two delivery-work nodes representing exactly two modules, plus mandatory DN-014 audit authority. DN-014 is the third graph node, not a third represented delivery module.
- Outcome, assembled public lifecycle, AC-2/AC-3, production behavior, dependencies, and all live-carrier/DN-015/finalization safety exclusions are unchanged.
- The builder must generate this reduced fixture through structured change authority and select every plan/build/accept/audit action from public returned jobs. Missing DN-014 or any node's current accept remains the fail-closed negative control.
- Shaper-challenger: `pass`. It independently confirmed terminal authority and all-node accept requirements, found existing arbitrary-node structured fixture precedent in `serve/kanban/tests/test_generated_graph_admission.py`, and classified this as a complete non-material fixture-sizing correction requiring no production change.

[[2026-07-28T06:21:19+02:00]]
Proof-contract repair complete and challenged: AC-1, complexity waiver, and proof guidance now require two delivery-work nodes/two modules plus the mandatory DN-014 audit-authority node. AC-2/AC-3, Outcome, dependencies, public assembled lifecycle, and safety exclusions are unchanged. Shaper-challenger passed; task returns to build.
