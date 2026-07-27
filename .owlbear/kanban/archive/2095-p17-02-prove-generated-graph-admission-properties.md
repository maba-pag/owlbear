---
id: 2095
title: 'P17-02: Prove generated graph admission properties'
status: archived
priority: high
created: 2026-07-27T19:45:12.509746+02:00
updated: 2026-07-27T21:30:01.081125+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T2
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on: []
ac:
  - 'AC-1: Given deterministic generated acyclic graph families spanning single-node,
    branching, joining, and hundreds-of-node topologies whose delivery nodes are serialized
    in dependency-first and scrambled authored orders, public admission succeeds,
    creates one plan job per delivery node in authored YAML order, `DispatchRuntime.pick_waves`
    returns eligible plan jobs in stable dependency-topology order, and replay preserves
    digest, finding, and job identities.'
  - 'AC-2: Given YAML-backed generated mutations, the canonical loader rejects `dangling
    reference` with `ERR_CHANGE_REFERENCE_MISSING`; public validation rejects `dependency
    cycle`, `disconnected obligation`, `duplicate owner`, `interface omission`, `migration
    gap`, `risk disposition`, and `proof authorization` with `DV-008`, `DV-003`, `DV-003`,
    `DV-004`, `DV-005`, `DV-006`, and `DV-007`, respectively, before a receipt or
    job exists.'
  - 'AC-3: Given the same seed and generated authority, repeated loading and validation
    produce the same canonical delivery digest and sorted findings; YAML key order
    and document wrapping do not change semantic identity.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Deterministically generated graph families demonstrate that native admission is general rather than tailored to bootstrap fixtures.

## Scope
In scope: MOD-008 generators and tests over canonical models, hashing, admission, and plan-job publication. Out of scope: receipt lifecycle, browser behavior, and product changes.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, IF-002, RISK-006/RISK-011 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a deterministic seeded generator/property matrix through the canonical loader and admission boundary; add no property-test dependency solely for naming.

[[2026-07-27T20:28:55+02:00]]
## Builder Notes

DONE

- Added `serve/kanban/tests/test_generated_graph_admission.py`; no production behavior or dependency changes.
- AC-1: deterministic public `load_change` plus `validate_and_admit` coverage admits single-node, branching, joining, and 240-node families; asserts dependency-before-node publication order, persisted `JobStore` identities, exact receipt/generation/assessment replay, and one receipt/generation artifact.
- AC-2: generated mutations assert exact singleton codes `DV-002`, `DV-008`, `DV-003`, `DV-003`, `DV-004`, `DV-005`, `DV-006`, and `DV-007`; each public admission returns no receipt/generation and creates no authority or work publication.
- AC-3: seed 2095 authority with `DV-006`/`DV-007` defects is reloaded through the modular loader after recursive YAML key reversal, explicit document wrapping, and narrow line wrapping; digest and sorted findings remain identical across repeated loads.
- Focused proof: `uv run pytest serve/kanban/tests/test_generated_graph_admission.py -q --tb=short -n 0` passed 13 tests.
- Proportional proof: `uv run pytest serve/kanban/tests -q --tb=short` passed 364 tests with four existing Python multiprocessing fork deprecation warnings.
- Focused `uv run lint serve/kanban/tests/test_generated_graph_admission.py` passed all hooks; VS Code diagnostics reported no errors.
- Builder challenger decision: `pass`; it independently reran the focused test and lint.
- Assessed all 20 recalled memory entries in one batch: 19 succeeded; one concurrently absent entry (`b6c53f34-8a9d-4700-9350-9469ee81684a`) returned `Entry not found`.

[[2026-07-27T20:41:05+02:00]]
## Verify Notes

RESHAPE

- Builder commit reviewed: `b91c027b8d79b963c171898cb43eaaa3a77a0d07`; it adds only `serve/kanban/tests/test_generated_graph_admission.py`.
- AC-1 fails independent public-boundary proof. `plan_jobs` zips job IDs to authored `revision.graph.nodes` order. A transient verifier probe serialized a valid seven-node joining graph in reverse order, loaded it with `load_change`, and admitted it with `validate_and_admit`; published and stored targets were `DN-007` through `DN-001`, `topological=False`, while replay remained equal. The committed helper always authors dependency-first IDs and asserts that same order, so it is self-fulfilling. The hundreds family is genuinely 240 nodes.
- AC-2 is incompatible with the stated canonical-loader proof for dangling references. A YAML-backed `DN-999` dependency is rejected by `load_change` as `ERR_CHANGE_REFERENCE_MISSING` before a `ChangeRevision` reaches admission. The committed test instead uses unchecked `model_copy` mutation after a valid load to obtain `DV-002`. Independent YAML-backed probes confirmed the other seven exact singleton codes and no receipt, generation, jobs, or work root.
- AC-3 passes inspection: repeated modular loads after recursive YAML key reversal, explicit document start, and wrapping preserve digest and sorted findings.
- Fresh focused proof passed: 13 tests. Focused repository lint passed; source/test diagnostics were clean. Fresh package proof could not be trusted: shared terminal runs were replaced by unrelated concurrent output, and two effect-checked capture attempts created no artifact. Builder package evidence remains 364 passed but is not claimed as fresh verifier proof.
- Verifier challenger: `reconsider`; route to shape to reconcile topology and loader-boundary contracts.
- Memory: every one of 20 recalled entries was submitted in one assessment batch; 19 succeeded and one concurrently stale entry rejected assessment. Saved pending verifier lesson `ad11e1ab-f373-4c2b-9785-76edf59caace`.
- Changed paths: task record only; transient scratch probe deleted; no product or test patch.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC-1/topology-order | shaper via `/shape` | Define stable delivery-topology ordering independently of authored YAML order and require a scrambled-order generated family; include builder-owned planner correction if authored order is not the contract. | `serve/kanban/src/owlbear_kanban/jobs.py`; `serve/kanban/tests/test_generated_graph_admission.py` | Reversed loaded graph published dependents before dependencies. |
| 2 | AC-2/dangling-loader-boundary | shaper via `/shape` | Reconcile exact `DV-002` admission expectation with canonical loader rejection, explicitly choosing the owning boundary and valid generated input path. | `serve/kanban/src/owlbear_kanban/change.py`; `serve/kanban/src/owlbear_kanban/admission.py`; `serve/kanban/tests/test_generated_graph_admission.py` | Loader returns `ERR_CHANGE_REFERENCE_MISSING` before admission; current test bypasses loader invariants. |

[[2026-07-27T20:55:29+02:00]]
## Shape Notes

Local task repair of verifier follow-up keys `AC-1/topology-order` and `AC-2/dangling-loader-boundary`; approved intent, parent, dependencies, scope, authority, proof bundle, and AC-3 are unchanged.

### Repair Closure Map
| Failure Key | Claimed Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof Or Negative Control | Executor Availability |
|---|---|---|---|---|---|
| AC-1/topology-order | Canonical admission publishes authored-order plan jobs; `DispatchRuntime.pick_waves` consumes eligible jobs in stable dependency-topology order. | `change.py`, `admission.py`, `jobs.py::plan_jobs`, `dispatch.py::pick_waves/_delivery_topology_key`, generated admission proof. | Serialize a joining graph in scrambled order; compare persisted targets with authored order and flattened picked waves with dependency order. | Scrambling must alter publication order without altering dispatch topology; dependency-first-only fixtures cannot prove the distinction. | Installed pytest through `uv`. |
| AC-2/dangling-loader-boundary | Modular load owns undeclared-reference rejection; admission owns the seven semantic mutation findings that can reach a loaded revision. | `change.py` identity validation, `admission.py` DV findings, generated admission proof. | Write `DN-999` into YAML and require `ERR_CHANGE_REFERENCE_MISSING` with no revision; require each other YAML-backed mutation to load and return its declared DV code with no publication. | Post-load `model_copy` is excluded because it bypasses the canonical loader invariant. | Installed pytest through `uv`. |

- AC-1 now distinguishes authored publication order from dependency-topology dispatch order and requires a scrambled-order family.
- AC-2 now assigns dangling references to the canonical loader and the seven reachable semantic classes to public admission, with canonical diagnostics.
- Shaper challenger: `pass`; it confirmed live owners, literal authority, test-only scope, and closure-map causality.
- Board audit before release: task remains child of #1990, has no dependencies, retains `existing+challenge`, and routes to `build`.

[[2026-07-27T21:05:06+02:00]]
## Builder Notes

DONE

- Changed files: `serve/kanban/tests/test_generated_graph_admission.py` only; no production behavior or dependencies changed.
- Resolved `AC-1/topology-order`: added a valid seven-node joining family serialized in reverse authored order. The proof crosses canonical `load_change` and public `validate_and_admit`, asserts one persisted plan job per node in authored YAML order, then uses real `NativeRuntime` and `DispatchRuntime.pick_waves` to assert stable dependency-topology order. Exact admission replay and stored `JobRecord` identities remain stable. Existing single-node, branching, joining, and 240-node families remain covered.
- Resolved `AC-2/dangling-loader-boundary`: removed the dangling-reference `model_copy` bypass. A YAML-backed `DN-999` dependency now reaches canonical `load_change` and asserts no revision plus exact singleton `ERR_CHANGE_REFERENCE_MISSING`, with no receipt or job publication. The other seven mutations are YAML-backed, reload through canonical loading, and public admission returns exact singleton `DV-008`, `DV-003`, `DV-003`, `DV-004`, `DV-005`, `DV-006`, and `DV-007`, each with no receipt, generation, authority job artifact, or work job.
- AC-3 remains substantive and unchanged: repeated canonical loading after recursive YAML key reversal, explicit document wrapping, and narrow line wrapping preserves digest and sorted findings.
- Focused proof: `uv run pytest serve/kanban/tests/test_generated_graph_admission.py -q` with short tracebacks and xdist disabled passed 14 tests in 5.03 seconds. Builder challenger independently reran it and passed 14 tests in 4.58 seconds.
- Proportional package proof: `uv run pytest serve/kanban/tests -q` with short tracebacks passed 365 tests in 79.48 seconds; four existing Python multiprocessing fork deprecation warnings only.
- Lint and diagnostics: `uv run lint serve/kanban/tests/test_generated_graph_admission.py` passed all applicable hooks; VS Code diagnostics reported no errors; scoped `git diff --check` was clean.
- Builder challenger decision: `pass`; it confirmed the one-file test-only diff and independently reran focused test and lint.
- Memory assessment: all 20 recalled builder memories were assessed successfully. Four informed artifact-to-repaired-scope review, active-workspace selection, replay proof, or separation of replay identity from mutation eligibility; 16 were not applicable. No new non-obvious reusable institutional lesson was identified.

[[2026-07-27T21:12:30+02:00]]
## Verify Notes

INTERRUPTED

- The verifier subagent returned no response after claiming this task. Effect checks found no verifier commit and no status change.
- A recovery verifier could not adopt the live claim (`ERR_ALREADY_CLAIMED`), so the orchestrator released the interrupted claim through the public lifecycle operation before clean redispatch.
- No product or test mutation is attributed to the interrupted verifier.

[[2026-07-27T21:24:42+02:00]]
## Verify Notes

PASS

- Verified builder commit `a0ee4be65140b9454665dc4d6f5e288e99cfec2e`; current HEAD is its descendant and had no later committed `serve/kanban` drift. The builder diff was limited to the task record and `serve/kanban/tests/test_generated_graph_admission.py`.
- Closed `AC-1/topology-order`: source review confirmed `plan_jobs` persists authored node order while real `DispatchRuntime.pick_waves` independently derives dependency-ready order from the loaded graph and persisted `JobStore`. Challenger found the repaired fixture's ascending topology could still false-green lexical sorting, so verifier locally strengthened it to a non-lexical dependency chain distinct from reverse-authored YAML and added an explicit dependency-before-dependent assertion. Publication order, real runtime topology, replay tuple, stored `JobRecord` identities, and singleton receipt/generation artifacts are asserted.
- Closed `AC-2/dangling-loader-boundary`: dangling YAML crosses canonical `load_change`, returns no revision with exact `ERR_CHANGE_REFERENCE_MISSING`, and creates no authority publication. The seven other YAML mutations reload canonically and now assert exact singleton tuples `DV-008`, `DV-003`, `DV-003`, `DV-004`, `DV-005`, `DV-006`, and `DV-007`; public admission returns no receipt/generation and creates no authority or work publication. No `model_copy` bypass remains.
- AC-3 passes: repeated canonical loads after recursive key reversal, explicit document wrapping, and narrow line wrapping preserve digest, exact sorted findings, and semantic identity.
- Final focused proof: `uv run pytest serve/kanban/tests/test_generated_graph_admission.py -q` with short tracebacks and xdist disabled passed 14 tests in 5.06 seconds.
- Proportional package proof after verifier repair: `uv run pytest serve/kanban/tests -q` with short tracebacks passed 365 tests in 79.31 seconds; four existing Python multiprocessing fork deprecation warnings only.
- Repository lint passed all applicable hooks for the test file; VS Code diagnostics were clean; scoped diff check passed.
- Verifier challenger initially failed the lexical-topology and set-cardinality assertions. After the local repair and rerun, the required challenger decision was `pass`, explicitly closing both defects and supporting AC-1 through AC-3.
- All 20 recalled verifier memories were assessed successfully. No new non-obvious reusable institutional lesson was identified.
- Verifier-owned changed file: `serve/kanban/tests/test_generated_graph_admission.py`; final task record is included in the scoped closure commit.

[[2026-07-27T21:30:01+02:00]]
## Collect Notes

**Verdict:** ARCHIVED

### Closure Evidence
- Builder commit `a0ee4be65140b9454665dc4d6f5e288e99cfec2e` repaired the generated graph admission proof; verifier commit `95b198bf0e25052bce8ff6747de43ccf4bd7047d` is its current-HEAD descendant and independently accepted the repair.
- **AC-1:** Deterministic single, branching, joining, scrambled, and 240-node families cross canonical loading and public admission. Authored plan-job order, real `DispatchRuntime.pick_waves` dependency order, replay values, stored job identities, and singleton receipt/generation artifacts are asserted. The repaired scrambled chain is non-lexical and distinct from reverse-authored YAML.
- **AC-2:** YAML-backed dangling-reference loading returns exact singleton `ERR_CHANGE_REFERENCE_MISSING`; seven canonical YAML mutations return exact singleton `DV-008`, `DV-003`, `DV-003`, `DV-004`, `DV-005`, `DV-006`, and `DV-007`, with no receipt, generation, authority job artifact, or work publication.
- **AC-3:** Repeated canonical loads after recursive key reversal, explicit document wrapping, and line wrapping preserve digest and exact sorted findings.
- Repaired failure keys `AC-1/topology-order` and `AC-2/dangling-loader-boundary` are explicitly closed by the latest builder and verifier notes. Builder challenger: `pass`. Verifier challenger after local repair: `pass`. No collector challenger is defined for this role, so the collector ran direct closure proof.
- Fresh collector check at verifier commit: generated graph admission suite passed 14 tests. VS Code diagnostics are clean and the supplied commit range passes diff checking.
- Scope audit: both supplied commits touch only this task record and `serve/kanban/tests/test_generated_graph_admission.py`; no production, dependency, receipt-lifecycle, browser, or other product scope leaked.
- Parent `#1990` remains the unclaimed `collect` aggregate owner with other active descendants; archiving this leaf satisfies only its `#2095` dependency.
- No resolved requests exist. All six recalled collector memories were assessed successfully.

### Unresolved Follow-up
None.
