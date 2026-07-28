---
id: 2097
title: 'P17-04: Execute the fresh-consumer native delivery workflow'
status: shape
priority: high
created: 2026-07-27T19:45:12.576115+02:00
updated: 2026-07-28T05:19:28.656377+02:00
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
ac:
  - 'AC-1: Given a temporary consumer initialized by public setup and a representative
    admitted two-node/two-module change, installed design contracts plus public MCP
    `show_change`, `validate_change`, and `admit_change` publish digest-bound frontier
    plan jobs while a plan outside admitted authority fails without a plan receipt
    or packet job.'
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

Complexity waiver: PROOF-013 requires one assembled design-to-audit boundary; splitting lifecycle phases would bypass it. A two-node fixture keeps the matrix bounded.

Proof guidance: reuse the current assembled MCP harness over a temporary Git consumer; replace only repository location, never public setup, MCP, engine, writer, or checkout boundaries.

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
