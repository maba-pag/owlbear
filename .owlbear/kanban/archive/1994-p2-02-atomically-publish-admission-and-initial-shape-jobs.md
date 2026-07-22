---
id: 1994
title: 'P2-02: Define initial shape-job generations'
status: archived
priority: medium
created: 2026-07-22T05:49:48.187184+02:00
updated: 2026-07-22T15:49:09.593895+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-002
  - jobs
  - schema
parent: 1978
depends_on:
  - 1999
ac:
  - 'AC-1: Given a revision, admission receipt identity, and allocated numeric IDs,
    the public planner returns one immutable kind=`shape` job per authored delivery
    node in authored order; records bind change ID, digest, target node, receipt prerequisite,
    priority, and timestamps.'
  - 'AC-2: Serialized generation readback preserves those operational fields and rejects
    duplicate numeric IDs, duplicate or missing node targets, non-shape kinds, digest
    or receipt mismatch, and targets outside the revision with structured diagnostics.'
  - 'AC-3: Job mappings omit authority-owned title, outcome, acceptance, module, interface,
    risk, and proof prose; inspection confirms claims, attempts, transitions, invalidation,
    supersession, requests, MCP, HTTP, and UI remain absent.'
proof_bundle: behavioral+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-002`

## Outcome
A public side-effect-free planner creates one immutable initial shape-job generation from a loaded revision, receipt identity, and allocated numeric job IDs for later publication by #1998.

## Scope
In scope: the minimal native shape-job record; generation identity; deterministic authored-node ordering; receipt prerequisite binding; priority and timestamps; immutable serialization/readback; duplicate, missing, wrong-kind, wrong-digest, wrong-receipt, and unknown-target diagnostics; public exports and focused tests.

Out of scope: live receipt or job publication; validate/admit composition; concurrency, replay, rollback, cleanup, durability, and complete-generation visibility owned by #1998; shape execution; claims, attempts, transitions, requests, activity, invalidation, supersession, generalized recovery/health, MCP, HTTP, and UI.

## Authority
Resolve job fields and authority projection rules from sections 6 and 7 of `design.md`. Job files contain operational identity/state only; titles, outcomes, acceptance, modules, interfaces, risks, and proofs remain projected from change authority.

## Boundary Ownership
This packet proves the planner and serialized generation only. It does not satisfy the atomic-success part of `PROOF-002`; #1998 owns storage and all-or-none publication.

## Repair Provenance
This body replaces the stale pre-repair Outcome and Scope that assigned atomic publication to #1994. The six-packet repair moved that responsibility to #1998; no later note is needed to reinterpret this contract.

Proof guidance: exercise the public planner and generation readback without filesystem writes. Run focused job-generation and admission model tests plus Ruff on touched files.

[[2026-07-22T14:10:35+02:00]]
## Shape Notes
- Replaced the stale body in full. The operative task now assigns only side-effect-free initial shape-job generation planning and serialization to #1994; #1998 owns storage and atomic publication.
- Dependency rewired from deprecated #1993 to clean replacement #1999. Route remains build after #1999.

[[2026-07-22T15:26:03+02:00]]
## Builder Notes
- Change envelope: add only side-effect-free initial shape-job planning, immutable generation models, serialized readback diagnostics, and public exports; no persistence/publication or execution workflow.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/__init__.py`.
- Change Module Map deviations: none; implemented at the native kanban model/export boundary.
- Proof selected: focused Ruff plus public import/model and JSON-list normalization smoke checks.
- Durable-test justification: no durable tests added; builder-challenger confirmed the focused public boundary and no concrete blocker. Existing repository test fixtures do not yet expose a minimal revision helper for this new boundary; follow-up risk is that verifier should add or run focused planner/readback behavioral coverage if required by the broader suite.
- Commands run: `uv run --project serve/kanban ruff check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/src/owlbear_kanban/__init__.py`; `PYTHONPATH=serve/kanban/src uv run --project serve/kanban python -c '...'` public export smoke; serialization normalization smoke.
- Builder-challenger result: pass.
- Follow-up risks: persistence and atomic publication remain explicitly owned by #1998; this task does not implement them.

[[2026-07-22T15:33:43+02:00]]
## Verify Notes
- Evidence reviewed: task AC and Builder Notes; builder commit `3a5fcbf44a3764e0f847a2c02f4a2bd9543774d0`; admitted authority `.owlbear/changes/replace-delivery-pipeline/{design.md,graph.yaml}` for DN-002, IF-002, and PROOF-002.
- Named authorities checked: design section 7.1 limits job records to operational identity/state; graph DN-002 assigns admission and initial shape jobs; PROOF-002 owns atomic receipt-plus-job success. The implementation stays in the repaired packet boundary: planner/readback only, with no persistence or atomic publication claimed.
- Change Module Map: no deviation. The change is limited to `serve/kanban/src/owlbear_kanban/jobs.py` and the package export boundary in `__init__.py`.
- Normal-path boundary exercised without filesystem writes: public `load_change`, `plan_shape_jobs`, and `read_job_generation` ran against the admitted `replace-delivery-pipeline` revision. It produced 14 authored-node jobs in order, confirmed immutable records and authority-prose omission, and observed all six required rejection categories: duplicate ID, missing target, wrong kind, digest mismatch, receipt mismatch, and unknown target.
- Checks run: public behavioral probe passed; Ruff on both touched modules passed; `uv run --project serve/kanban pytest serve/kanban/tests/test_admission.py` passed (3 tests); commit diff whitespace check passed.
- Finding: no durable test covers the new public planner or serialized readback APIs. `rg` found no `plan_shape_jobs`, `read_job_generation`, `JobGeneration`, or `ShapeJob` coverage in either test tree. The shaped Scope explicitly includes focused tests, and the builder's initial command used `tests/test_admission.py` from the package project and collected zero tests. This is not safely repairable under verifier patch limits because it needs a new regression test module/fixtures.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Add focused durable tests for the public `plan_shape_jobs` and `read_job_generation` boundary. Cover authored order/operational fields/immutability/authority-prose omission plus each AC-2 diagnostic. Run the test module from `serve/kanban` and Ruff on the touched implementation and test file. | `serve/kanban/tests/` (new or existing job-generation test), `serve/kanban/src/owlbear_kanban/jobs.py` only if a test exposes a defect | Test output that collects and passes the new cases; do not substitute an inline smoke script. |

- Final route: REJECT to build for focused regression-proof implementation.

[[2026-07-22T15:37:49+02:00]]
## Builder Notes
- Change envelope: add focused durable regression coverage for the existing side-effect-free initial shape-job planner and serialized generation readback; no product implementation, persistence, publication, or execution changes.
- Files changed: `serve/kanban/tests/test_jobs.py` only.
- Change Module Map deviations: none; tests exercise the native public job-generation boundary.
- Proof selected: focused pytest plus Ruff on the new test module.
- Durable-test justification: the shaped Scope explicitly requires focused tests, and the public planner/readback behavior had no durable coverage. The tests protect easy-to-regress ordering, immutable operational identity, authority-projection omission, and structured malformed-generation diagnostics.
- Commands run: `uv run --project serve/kanban pytest serve/kanban/tests/test_jobs.py` -> 8 passed; `uv run --project serve/kanban ruff check serve/kanban/tests/test_jobs.py` -> all checks passed.
- Builder-challenger result: pass; confirmed scope, Rent Test, and evidence with no concrete blocker.
- Follow-up risks: atomic persistence and publication remain explicitly owned by #1998; this task does not implement them.

[[2026-07-22T15:44:14+02:00]]
## Verify Notes
- Evidence reviewed: AC-1 through AC-3, Builder Notes, and authority `.owlbear/changes/replace-delivery-pipeline/design.md` section 7.1 plus `graph.yaml` DN-002 and PROOF-002.
- Named authorities checked: section 7.1 limits job records to operational identity/state; DN-002 owns admission and initial shape jobs; PROOF-002 assigns atomic receipt-plus-job publication outside this packet. The implementation stays within the repaired planner/readback-only boundary.
- Change Module Map: no deviation. Product code is limited to `serve/kanban/src/owlbear_kanban/jobs.py` and its package export in `serve/kanban/src/owlbear_kanban/__init__.py`; the durable proof is `serve/kanban/tests/test_jobs.py`.
- Normal-path boundary exercised without filesystem writes: public `load_change`, `plan_shape_jobs`, and `read_job_generation` read the admitted revision successfully, producing and restoring 14 immutable shape jobs in authored order with no diagnostics.
- Replacements used below boundary: none. The public loader, planner, and reader were exercised against the real admitted change revision.
- Checks run: `uv run --project serve/kanban pytest serve/kanban/tests/test_jobs.py` passed (8 tests); Ruff on both implementation modules and `test_jobs.py` passed; public successful readback probe passed; whitespace diff check passed.
- AC coverage: tests cover operational bindings, authored order, immutability, authority-prose omission, and each required diagnostic: duplicate numeric ID, duplicate/missing/unknown target, wrong kind, digest mismatch, and receipt mismatch.
- Patches applied: none.
- Verifier-challenger: pass. It confirmed task scope, evidence sufficiency, all diagnostic categories, and that PROOF-002 atomic publication is owned by #1998.
- Final route: PASS to collect.

[[2026-07-22T15:49:09+02:00]]
## Collect Notes
- Classification: leaf. Task #1994 has no child tasks and carries a packet implementation contract rather than parent or EPIC aggregate intent.
- Leaf verification evidence: the final `## Verify Notes` records PASS to collect after `uv run --project serve/kanban pytest serve/kanban/tests/test_jobs.py` passed 8 tests, Ruff passed on the implementation and test modules, the public successful readback probe passed, and verifier-challenger returned pass.
- Invariant coverage: final verification maps AC-1 through AC-3 to authored-order immutable shape-job generation, operational-field serialization/readback, authority-prose omission, and every required malformed-generation diagnostic.
- Dependency gate: dependency #1999 is archived with reason `completed`; task dependency state is `ok`.
- Follow-up closure: the earlier Required Follow-up for durable planner/readback tests was discharged by the later builder cycle adding `serve/kanban/tests/test_jobs.py`, followed by the final verifier PASS.
- Structured requests: no pending or resolved request records exist for #1994.
- Residual decisions: none. Atomic persistence and publication remain explicitly assigned to #1998 and are outside this leaf contract.
- Archive rationale: verifier completion evidence is present, the prior follow-up is resolved, the dependency gate is satisfied, and no request or decision state remains.
