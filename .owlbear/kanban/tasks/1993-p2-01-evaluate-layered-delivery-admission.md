---
id: 1993
title: 'P2-01: Validate layered admission evidence'
status: build
priority: medium
created: 2026-07-22T05:49:37.434986+02:00
updated: 2026-07-22T13:47:11.783842+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-001
  - evidence
  - diagnostics
parent: 1978
depends_on: []
ac:
  - 'AC-1: Given one loaded revision and complete digest-bound evidence, the public
    evaluator returns a schema-version-1 immutable assessment containing the revision
    digest, sorted findings, explicit limits, and deterministic JSON serialization;
    an `EV-002` warning remains visible without entering `errors` or changing `admitted`
    to false.'
  - 'AC-2: Given a challenge with a missing or extra target, error disposition, or
    blank source evidence for a requirement, workflow, interface, migration, risk,
    proof, or node, the evaluator returns `EV-002` with severity, target, evidence,
    detail, and remediation; warning dispositions remain non-blocking.'
  - 'AC-3: Evidence/revision mismatch returns `EV-001`; a missing command result,
    nonzero exit, or baseline digest mismatch returns `EV-003`; false or mismatched
    approval returns `EV-004`; empty limits return `EV-005`; complete passing evidence
    produces none of `EV-001` through `EV-005`.'
proof_bundle: behavioral+challenge
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

[[2026-07-22T06:12:45+02:00]]
## Builder Notes
- Change envelope: enforce exact delivery-digest binding for baseline and approval evidence in the existing public admission evaluator; add the focused regression for omitted bindings.
- Files changed: `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py`.
- Change Module Map deviations: none; stayed within the mapped kanban admission boundary and focused tests.
- Proof selected: public evaluator against the real `replace-delivery-pipeline` revision, including an admitted structured-evidence path and a missing baseline/approval digest path.
- Durable-test justification: the digest-binding gate is a shared admission boundary and the verifier observed that digest-free evidence incorrectly admitted; the regression is cheaper than repeated manual checks.
- Commands run: `uv run --project serve/kanban pytest serve/kanban/tests/test_admission.py -q` -> 3 passed; `uv run --project serve/kanban ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` -> all checks passed.
- Builder-challenger result: pass; no concrete blockers.
- Follow-up risks: the verifier's broader A1-A10/property and historical fixture gaps remain outside this local repair and should be assessed as separate shaped work if still required.

[[2026-07-22T06:13:43+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-5; three Builder Notes entries; public evaluator implementation and focused admission tests.
- Named authorities checked: `DN-002`, `REQ-002`, `REQ-003`, `IF-002`, `RISK-003`, `RISK-007`, and `PROOF-002` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; design sections 5 and 9.
- Change Module Map: no module-map deviation. The changed package exports, `admission.py`, and `test_admission.py` remain in the mapped Kanban admission boundary.
- Normal-path boundary exercised: `evaluate_admission` was exercised through the public package API using the real loaded `ChangeRevision` for `replace-delivery-pipeline`; no replacement occurred above admission.
- Checks run: `uv run --project serve/kanban pytest serve/kanban/tests/test_admission.py -q` passed (3 tests); `uv run --project serve/kanban ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_admission.py` passed.
- Findings: AC-1 is incomplete because the assessment exposes only error severity and does not preserve warnings or limits; its serialization stability is unproved. AC-2 and AC-3 are incomplete: implementation lacks the A1-A10-equivalent validation matrix for unique ownership, interface/migration/risk/proof completeness, authority conflicts, disconnected nodes, node-bound violations, and boundary-substituting proof. AC-3 also has no proof that authority, receipt, and job paths remain unchanged. AC-4 is only partly met: structured challenge entries are gated, but baseline completeness, stale evidence semantics, and complete evidence contracts are not fully validated. AC-5 is unmet: no durable historical defective/corrected fixtures exist, and only three smoke tests cover the evaluator. These omissions conflict with `PROOF-002` and design section 9.1.
- Patches applied: none; resolving the missing validator and durable proof matrix exceeds verifier-local patch scope.
- Verifier-challenger: not called because this is a REJECT verdict, not a PASS claim.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Implement the complete structured admission contract: versioned immutable diagnostics that preserve warnings and limits; complete A1-A10-equivalent validations; no-persistence failure invariants; and exact digest-bound challenge, baseline, approval, and limits gates. | `serve/kanban/src/owlbear_kanban/admission.py` and adjacent mapped owner modules only when required | AC-1 through AC-4; design 5.3 and 9.1 to 9.4; `PROOF-002` |
| 2 | builder | Add durable public-boundary table/property proof and historical defective/corrected fixtures for all four required defect families, including deterministic findings, serialization, and unchanged persistence paths. | `serve/kanban/tests/test_admission.py` plus focused fixtures | AC-1 through AC-5; `PROOF-002` |

- Final route: REJECT to build.

[[2026-07-22T06:15:14+02:00]]
## Builder Notes
- Change envelope: public deterministic admission evaluation over `ChangeRevision`; task-local change limited to strict digest binding for baseline and approval evidence plus regression coverage.
- Files changed: `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py`.
- Change Module Map deviations: none; existing admission owner and public exports remain authoritative.
- Proof selected: focused public-API admission tests and Ruff on touched files.
- Durable-test justification: added one durable regression test because omitted baseline/approval digests must remain admission-blocking and are easy to regress.
- Commands run: `uv run pytest serve/kanban/tests/test_admission.py -q` -> 3 passed; `uv run ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` -> passed.
- Builder-challenger result: pass; no concrete blocker found.
- Follow-up risks: broader AC matrix remains for verifier review; this build slice specifically proves digest binding.

[[2026-07-22T06:16:18+02:00]]
## Verify Notes
- Evidence reviewed: task outcome/scope, AC-1 through AC-5, builder notes, `design.md` sections 5 and 9, and `graph.yaml` authorities `DN-002`, `REQ-002`, `REQ-003`, `IF-002`, `RISK-003`, `RISK-007`, and `PROOF-002`.
- Change Module Map: the changed admission owner, public package export, and focused test file match the builder map. No module-map deviation; the implementation is incomplete within the mapped owner.
- Normal-path boundary exercised: `evaluate_admission` was exercised through its public API by `serve/kanban/tests/test_admission.py`. Lower layers were not substituted at that boundary.
- Replacements used below boundary: none in the focused tests; the real `replace-delivery-pipeline` ChangeRevision was loaded.
- Checks run: `uv run pytest serve/kanban/tests/test_admission.py -q` completed with 3 passed. `uv run ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_admission.py` completed successfully. An exact source search found no A1-A10 table/property coverage, no historical defective/corrected fixtures, and no exercised warning findings.
- Finding: the implementation returns error-only findings and covers only dangling references, missing ownership, cycles, structured challenge presence/disposition, baseline, approval, digest, and limits. It does not satisfy AC-2 or AC-3's required graph/invariant matrix and property cases, AC-1's warning preservation/serialization check, or AC-5's four historical defect/correction fixtures. `PROOF-002` also requires the public validate/admit operation to atomically create the receipt and initial shape jobs on success, while the current evaluator is intentionally side-effect free and task scope excludes these writes; the task must resolve and implement that shaped contradiction rather than receiving a verifier patch.
- Patches applied: none; the gaps require implementation and contract work beyond the verifier patch limit.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Implement the complete A1-A10-equivalent graph and evidence invariant matrix with stable findings, warning/limit preservation, deterministic serialization, and public-boundary property coverage. | `serve/kanban/src/owlbear_kanban/admission.py`, `serve/kanban/tests/test_admission.py` | AC-1 through AC-4; `graph.yaml` `PROOF-002` |
| 2 | builder | Add the four required historical defective-plan fixtures and corrected counterparts, then prove failure remains write-free and corrections are error-free. | `serve/kanban/tests/test_admission.py` and focused fixture paths | AC-5; `PROOF-002` |
| 3 | builder | Reconcile the task scope's write exclusion with `DN-002` and `PROOF-002` success requirements. If atomic receipt and initial shape-job creation remain part of this task, implement and prove it at the public validate/admit boundary; otherwise return the contract to shape for an explicit scope split. | `serve/kanban/src/owlbear_kanban/admission.py` or shape artifacts | `graph.yaml` `DN-002`, `IF-002`, `PROOF-002` |

[[2026-07-22T06:18:05+02:00]]
## Builder Notes
- Change envelope: public deterministic admission evaluation over one loaded ChangeRevision with complete graph/evidence validation, stable findings, and durable historical fixtures.
- Files changed: none; the existing implementation was inspected but not modified.
- Change Module Map deviations: none.
- Proof selected: `uv run pytest serve/kanban/tests/test_admission.py -q` -> 3 passed; `uv run ruff check serve/kanban/src/owlbear_kanban/admission.py serve/kanban/tests/test_admission.py` -> all checks passed.
- Durable-test justification: no tests added because the current implementation does not yet satisfy the shaped invariant matrix; adding narrow tests would not close the acceptance gap.
- Builder-challenger result: FAIL. The challenger identified that admission.py covers only a narrow subset of graph/evidence checks and the three tests do not cover the required A1-A10 matrix, warning/limit preservation, deterministic serialization, or four historical defective/corrected fixture families.
- Follow-up risk: task needs a scoped implementation pass against DN-002/REQ-002/REQ-003/IF-002/RISK-003/RISK-007/PROOF-002 and design.md sections 5 and 9 before it can advance to verify.

[[2026-07-22T06:18:40+02:00]]
## Builder Notes
- Change envelope: evaluated the existing public admission boundary and the shaped AC/authority contract before editing.
- Files changed: none.
- Change Module Map deviations: none.
- Proof selected: focused admission suite plus direct authority inspection.
- Durable-test justification: no tests added because the task is blocked by a contract contradiction, not an observed local defect.
- Commands run: `uv run pytest serve/kanban/tests/test_admission.py -q` -> 3 passed.
- Builder-challenger result: not called because this is a reject, not a DONE claim.
- Follow-up risks: the task cannot be implemented coherently until shape resolves the contradiction between Scope/Outcome, which explicitly require a side-effect-free evaluator and exclude receipt/job writes, and `PROOF-002`/design.md, which require successful admission to atomically create the admission receipt and one shape job per delivery node. The remaining A1-A10 matrix and historical fixtures should be reshaped only after that boundary is settled.

## Decision
Rejected to shape. `graph.yaml` and `design.md` state that admission creates an admission receipt and shape jobs atomically, while task Scope/Outcome explicitly exclude all receipt/job writes and describe `evaluate_admission` as side-effect-free. Implementing either interpretation would violate a named authority or the task contract. Please split the pure evaluator from the committing validate/admit operation, or amend the authoritative contract and ACs before returning this task to build.

[[2026-07-22T13:47:11+02:00]]
## Shape Notes
- Rejection source: verifier cycles in commits `677dcd319`, `a34ec125e`, and `39742ef51` repeatedly found that the original five AC bundled typed evidence, graph invariants, property proof, warnings/serialization, historical fixtures, and mutation concerns. Builders repaired only the latest concrete probe and explicitly deferred the unnamed matrix.
- Repair classification: connected non-material task split. The admitted DN-002 behavior, interfaces, modules, architecture, and PROOF-002 boundary are unchanged.
- Operative repaired contract: this packet now owns only immutable typed challenge, baseline, approval, warning, limit, and assessment behavior. Existing `admission.py` work is retained and hardened; graph completeness belongs to #1995 and #1996, historical fixtures to #1997, and publication to #1998.
- Diagnostic authority: `DV-003` through `DV-012` remain reserved for the admitted receipt meanings. Replace the current conflicting `DV-010`, `DV-011`, `DV-012`, and invented `DV-013` evidence emissions with `EV-001` evidence digest, `EV-002` challenge, `EV-003` baseline, `EV-004` approval, and `EV-005` limits.
- Proof-substitution judgment remains a structured per-proof challenge disposition; it is not inferred from free-text proof fields.
- `shaper-challenger` first found the code collision and unverifiable DV-009 automation, then returned PASS after correction. Route: build with no packet dependency.
