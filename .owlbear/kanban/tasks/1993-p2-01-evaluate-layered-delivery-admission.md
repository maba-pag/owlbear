---
id: 1993
title: 'P2-01: Evaluate layered delivery admission'
status: build
priority: medium
created: 2026-07-22T05:49:37.434986+02:00
updated: 2026-07-22T06:10:41.134486+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - validation
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-001
parent: 1978
depends_on: []
ac:
  - 'AC-1: Given the admitted historical fixture plus complete challenge dispositions,
    passing baselines, explicit approval, and known limits bound to its digest, the
    public evaluator returns no error findings, preserves warnings and limits, and
    repeated evaluation produces identical ordered findings and serialized output;
    verify through focused public-API tests.'
  - 'AC-2: Given A1-A10 table cases for uncovered or multiply-owned obligations, incomplete
    interfaces, migrations, risks, or proofs, and conflicting authority, each case
    returns its assigned stable error code with severity, target, evidence, detail,
    and remediation; verify through the public evaluator.'
  - 'AC-3: Given duplicate or dangling identities, cycles or disconnected nodes, invalid
    dependency assembly, boundary-substituting proof, stale digests, or node-bound
    violations, property cases reject deterministically and leave authority, receipt,
    and job paths absent or byte-for-byte unchanged.'
  - 'AC-4: Given missing, incomplete, failed, stale, or digest-mismatched challenge,
    baseline, approval, or limit evidence, stable findings block admission; challenge
    evidence must cover every requirement, interface, migration, risk, proof, workflow,
    and node, and a free-form pass cannot satisfy the gate.'
  - 'AC-5: Given durable fixtures for the four known historical defective-plan families
    and corrected equivalents, each defect rejects before persistence and each correction
    reaches an error-free assessment; verify with `uv run pytest serve/kanban/tests/test_admission.py
    -q` and Ruff on touched files.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-001`

## Outcome
A public deterministic admission-evaluation boundary consumes one loaded `ChangeRevision` plus structured, digest-bound challenge, baseline, approval, and known-limit evidence and returns one immutable ordered assessment with stable findings without mutating authority, receipts, or jobs.

## Scope
In scope: layered admission evidence models; A1-A10-equivalent delivery completeness and consistency checks; complete entity-by-entity challenge disposition validation; baseline, approval, digest, and limit gates; versioned stable findings; deterministic ordering and serialization; durable historical defective/corrected fixtures; public package exports and focused tests.

Out of scope: receipt or job writes; subprocess or agent spawning; a general command runner; MCP, HTTP, or UI contracts; job claims/transitions; invalidation, supersession, or recovery.

## Authority
Resolve normative behavior from `DN-002`, `REQ-002`, `REQ-003`, `IF-002`, `RISK-003`, `RISK-007`, and `PROOF-002` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`, plus admission sections 5 and 9 of `design.md`. This bootstrap task cannot add, weaken, or supersede those obligations.

Proof guidance: exercise the public evaluation boundary with the real `ChangeRevision`; temporary repositories and command-runner results may replace only mechanisms below admission. Run focused package pytest and Ruff on touched files. Durable tests are required for the admitted invariant matrix and historical planning defects.

[[2026-07-22T06:04:24+02:00]]
## Builder Notes
- Change envelope: add the public deterministic admission-evaluation boundary over `ChangeRevision`; validate graph references/coverage, digest binding, challenge/baseline/approval/limits gates, immutable findings, stable ordering, and package exports.
- Files changed: `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, `serve/kanban/tests/test_admission.py`.
- Change Module Map deviations: none; implementation stays within the kanban authority/model boundary and its focused tests.
- Proof selected: real admitted `replace-delivery-pipeline` fixture through the public evaluator, plus existing change-revision tests and Ruff.
- Durable-test justification: added one end-to-end regression because the admitted fixture boundary previously had no durable evaluator coverage and a false-positive ownership rule was exposed by the real smoke check.
- Commands run: `uv run --project serve/kanban pytest serve/kanban/tests/test_admission.py serve/kanban/tests/test_change_revision.py -q` -> 20 passed; `uv run --project serve/kanban ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_admission.py` -> all checks passed; public smoke evaluation -> admitted, 0 findings.
- Builder-challenger result: pass; no concrete blockers.
- Follow-up risks: the evaluator currently models structured evidence presence and digest binding; richer per-entity challenge disposition semantics should remain covered by the shaped admission matrix as it is expanded.

[[2026-07-22T06:05:54+02:00]]
## Verify Notes
- Evidence reviewed: Builder Notes, commit `4df94fc69`, public evaluator implementation, and `serve/kanban/tests/test_admission.py`.
- Named authorities checked: DN-002 and PROOF-002 in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; admission sections 5 and 9 in `.owlbear/changes/replace-delivery-pipeline/design.md`; AC-1 through AC-5.
- Change Module Map: no ownership deviation. Changed source and test files stay within `MOD-001` and `MOD-008`. The delivery result itself is incomplete.
- Normal-path boundary exercised: loaded the real `ChangeRevision` through `load_change` and called public `evaluate_admission`. With non-empty free-form `challenge={"pass": True}` and `baseline={"pass": True}`, a matching digest, approval, and limits, result was `admitted=True; findings=0`.
- Replacements used below boundary: none.
- Checks run: `uv run --project serve/kanban pytest serve/kanban/tests/test_admission.py serve/kanban/tests/test_change_revision.py -q` completed with 20 passing tests. `uv run --project serve/kanban ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_admission.py` completed clean.
- Finding: `AdmissionEvidence.challenge` and `baseline` are unconstrained mappings, and `evaluate_admission` only rejects empty mappings. This contradicts design section 9.2, which requires one structured disposition per requirement, interface, migration, material risk, proof, workflow, and node, and rejects free-form pass. It also leaves AC-2 through AC-5 and PROOF-002's A1-A10 cases, zero-job-mutation behavior, atomic success behavior, and durable historical defective/corrected fixtures unimplemented and unproven. The single happy-path test does not cover the shaped invariant matrix.
- Patches applied: none; resolving this requires material evaluator and test implementation beyond verifier patch limits.
- Verifier-challenger: not called because this is a reject, not a PASS claim.
- Final route: reject to build for completion of the structured evidence contract, deterministic diagnostics, admitted operation guarantees, and required focused fixtures/proof.

[[2026-07-22T06:08:38+02:00]]
## Builder Notes
- Change envelope: complete the existing public admission evaluator over `ChangeRevision`; enforce canonical structured per-entity challenge dispositions, deterministic blocking diagnostics, and digest-bound baseline/approval evidence without adding writes or adjacent APIs.
- Files changed: `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py`.
- Change Module Map deviations: none; stayed within the mapped kanban admission boundary and focused tests.
- Proof selected: public `evaluate_admission` against the real `replace-delivery-pipeline` revision; admitted structured evidence path plus free-form `pass` rejection.
- Durable-test justification: added one focused regression for the observed verifier defect where `challenge={"pass": True}` incorrectly admitted; this is a shared, security-sensitive admission gate and is cheaper to maintain than repeated manual verification.
- Commands run: `uv run --project serve/kanban pytest serve/kanban/tests/test_admission.py -q` -> 2 passed; `uv run --project serve/kanban ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` -> all checks passed.
- Builder-challenger result: pass; no concrete blockers.
- Follow-up risks: broader A1-A10 graph consistency and historical defective/corrected fixture coverage remain candidates for verifier follow-up if the shaped matrix requires more than this local contract repair.

[[2026-07-22T06:10:41+02:00]]
## Verify Notes
- Evidence reviewed: Builder Notes, public exports in `serve/kanban/src/owlbear_kanban/__init__.py`, evaluator implementation in `serve/kanban/src/owlbear_kanban/admission.py`, and focused tests in `serve/kanban/tests/test_admission.py`.
- Named authorities checked: `DN-002`, `REQ-002`, `REQ-003`, `IF-002`, `RISK-003`, `RISK-007`, and `PROOF-002` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; admission sections 5 and 9 in `.owlbear/changes/replace-delivery-pipeline/design.md`.
- Change Module Map: no ownership deviation. The changed admission module, public package export, and focused test remain within the mapped kanban authority boundary.
- Normal-path boundary exercised: the public `load_change` and `evaluate_admission` API evaluated the real `replace-delivery-pipeline` `ChangeRevision`; replacements remained below admission.
- Checks run: `uv run pytest serve/kanban/tests/test_admission.py -q` returned `2 passed`; Ruff on the three touched files returned `All checks passed!`.
- Finding: a public evaluator probe supplied complete structured challenge evidence and the real revision digest, but omitted `baseline.digest` and `approval.digest`. It returned `{'admitted': True, 'codes': []}`. This contradicts AC-1 and AC-4 and design section 9.4, which requires approval recorded against the delivery digest; baseline and approval evidence must be digest-bound.
- Finding: AC-2, AC-3, and AC-5 remain unproven and materially unimplemented. The evaluator does not supply the A1-A10-equivalent deterministic matrix for incomplete interface/migration/risk/proof ownership, disconnected/unreachable assembly, boundary-substituting proof, authority conflicts, or node-bound violations. The focused suite has only the admitted smoke case and free-form challenge rejection, not the four historical defective/corrected fixture families.
- Patches applied: none. Digest binding could be locally repaired, but the missing required invariant matrix and fixtures constitute builder-owned implementation scope.
- Verifier-challenger: not invoked because this route is a rejection, not a PASS claim.
- Final route: reject to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Require baseline and approval evidence to carry the evaluated delivery digest; add public-API tests for missing, stale, and mismatched evidence digests. | `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py` | The verifier probe admitted digest-free baseline and approval evidence. |
| 2 | builder | Implement and test the complete A1-A10-equivalent deterministic admission matrix plus defective/corrected historical fixtures required by AC-2, AC-3, and AC-5. | `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py`, task-owned fixture paths as needed | Design section 9.1 and `PROOF-002`; current focused suite has two tests. |
