---
id: 2000
title: 'P3-01: Define native job and evidence contracts'
status: collect
priority: high
created: 2026-07-22T21:58:09.010514+02:00
updated: 2026-07-23T00:43:52.469260+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - contracts
  - jobs
  - evidence
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-001
parent: 1979
depends_on: []
ac:
  - 'AC-1: Given schema-version-1 mappings for `shape`, `build`, `accept`, and `audit`,
    the public parser returns immutable job records containing operational identity,
    target/digest/predecessor references, claim/block/evidence links, and disposition;
    unknown kinds, fields, or malformed target identity return stable diagnostics.'
  - 'AC-2: Given one parsed job plus its current `ChangeRevision` and optional node
    plan, the public projection resolves title, outcome, acceptance, modules, interfaces,
    and proof from authority; serializing the job record contains none of those normative
    fields.'
  - "AC-3: Given schema-version-1 `shape`, `build`, `accept`, `audit`, and `supersession`
    receipt mappings, the public parser enforces each kind's target, delivery/node-plan
    digest, predecessor, evidence, and code-revision contract and returns deterministic
    serialization or stable diagnostics."
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
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-001`

## Outcome
Versioned immutable contracts represent shape, build, accept, and audit jobs plus attempts, findings, claims, dispositions, kind-specific receipts, and authority-derived projections without copying normative graph truth into work records.

## Scope
In scope: public models, parsers, deterministic serializers, stable diagnostics, receipt payload contracts, and projection from `ChangeRevision` plus an optional node plan.

Out of scope: filesystem storage, lifecycle transitions, requests, invalidation, dispatch, agents, MCP, Cockpit, and bootstrap-carrier model changes.

## Current Foundation And Ownership
Deepen the native `jobs.py`, `receipt.py`, and package export boundary delivered by DN-001/DN-002. Do not extend legacy `models.py`, `engine.py`, `storage.py`, `request_models.py`, or `dispatch.py`; those remain the bootstrap carrier until later admitted nodes cut callers over and remove them.

## Authority
Resolve behavior from `DN-003`, `IF-003`, `REQ-009`, `NEG-001`, `NEG-002`, `NEG-010`, and receipt/job sections 3.5, 4, and 7 of the admitted design. Runtime records retain operational identity and references only; title, outcome, acceptance, modules, interfaces, risks, and proof come from authority projection.

Proof guidance: exercise public parsers, serializers, and authority projection with table-driven schema-version-1 mappings. Keep storage and lifecycle replacements outside this packet.

[[2026-07-22T23:43:16+02:00]]
## Builder Notes
- Change envelope: native job/evidence public contracts only; extended existing `jobs.py`, `receipt.py`, and package exports. No storage, lifecycle, dispatch, legacy carrier, MCP, Cockpit, or bootstrap changes.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/receipt.py`, `serve/kanban/src/owlbear_kanban/__init__.py`.
- Change Module Map deviations: none. Existing native module ownership supported the shaped boundary.
- Implementation: added immutable operational job references for node-plan, requests, attempts, findings, receipts, and supersession; added public `parse_receipt_mapping`, immutable parse result/diagnostic models, and stable diagnostics for invalid kind/field and missing target, predecessor, evidence, or code revision links. Existing `ReceiptStore` behavior remains unchanged.
- Proof selected: focused native job/receipt tests plus public parser smoke check.
- Durable-test justification: no durable tests added; existing focused coverage passed and the parser smoke check exercises the new public boundary without adding task-scoped test maintenance.
- Commands run: `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` -> `31 passed`; public parser import and missing-target diagnostic smoke -> `receipt parser smoke: ok`.
- Builder-challenger result: PASS. Challenger confirmed localized scope, typed public contracts, and preserved receipt-store behavior.
- Follow-up risks: receipt kind payloads remain intentionally represented as immutable JSON payloads at this packet boundary; deeper validity, digest, predecessor, code-revision, and lifecycle enforcement belongs to later shaped runtime packets.

[[2026-07-23T00:32:28+02:00]]
## Verify Notes
- Evidence reviewed: builder commit `4faba44e7` changed only `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/receipt.py`, and their public exports; its claimed module map has no ownership deviation. Existing focused suite passed: `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` produced `31 passed in 1.16s`.
- Named authorities checked: admitted design sections 3.5, 4, and 7.1; `REQ-009`, `IF-003`, `NEG-001`, `NEG-002`, and `NEG-010`. Job records retain only operational references and `project_job` sources title, outcome, acceptance, modules, interfaces, and proof from `ChangeRevision`, matching the authority-projection boundary.
- Change Module Map: no deviation. Changed modules remain `jobs.py`, `receipt.py`, and the package export boundary. No legacy carrier, storage, lifecycle, dispatch, MCP, or Cockpit path was changed.
- Normal-path boundary exercised: a public-API table probe parsed schema-version-1 shape/build/accept/audit jobs and shape/build/accept/audit/supersession receipts, then deterministically serialized the successful receipts. The existing tests did not exercise the new public parser or projection APIs, so they cannot prove the task AC by themselves.
- Finding: AC-3 is not satisfied. `parse_receipt_mapping` accepts a non-admission shape receipt lacking `node_plan_digest`, although the AC and design require enforcement of the delivery/node-plan digest contract. Reproduction command printed `BUG: shape receipt without node_plan_digest was accepted` after asserting `result.receipt is not None` for a shape receipt with target, predecessor, evidence, code revision, and no node-plan digest.
- Patches applied: none. This is an incomplete public receipt contract, not a verifier-local defect.
- Verifier-challenger: not called because the proposed route is rejection; challenger review is required only before PASS.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Implement kind-specific receipt payload validation for the required delivery/node-plan digest contract, including a stable missing-digest diagnostic, and add focused public parser coverage for all AC-3 receipt kinds. Preserve the existing receipt-store boundary. | `serve/kanban/src/owlbear_kanban/receipt.py`, focused existing receipt tests | The public parser accepts a shape receipt with no `node_plan_digest`; design section 3.5 and AC-3 require receipt-kind contracts. |

- Final route: REJECT to build.

[[2026-07-23T00:35:20+02:00]]
## Builder Notes
- Change envelope: repair the public native receipt parser contract and its focused parser tests only. Require `node_plan_digest` for node-scoped `shape`, `build`, and `accept` receipts; leave `audit` and `supersession` change-wide. No receipt-store, lifecycle, dispatch, legacy carrier, MCP, or Cockpit change.
- Files changed: `serve/kanban/src/owlbear_kanban/receipt.py`; `serve/kanban/tests/test_change_receipts.py`.
- Change Module Map deviations: none. The verifier-prescribed `receipt.py` owner and its existing focused test module directly contain the defect and proof boundary.
- Implementation: added stable `ERR_RECEIPT_NODE_PLAN_DIGEST_MISSING`; `parse_receipt_mapping` now requires `node_plan_digest` only for `shape`, `build`, and `accept`, in addition to the pre-existing non-admission references.
- Proof selected: public parser round-trip and deterministic serialization across admission, shape, build, accept, audit, and supersession; missing-digest diagnostics for each node-scoped kind.
- Durable-test justification: added focused durable coverage because this is an observed defect in a public versioned parser contract and a regression would otherwise be hard to detect through receipt-store tests.
- Commands run: `uv run --project . pytest serve/kanban/tests/test_change_receipts.py -q` -> `32 passed`; `uv run --project . ruff check serve/kanban/src/owlbear_kanban/receipt.py serve/kanban/tests/test_change_receipts.py` -> clean; `uv run --project . ruff format --check serve/kanban/src/owlbear_kanban/receipt.py serve/kanban/tests/test_change_receipts.py` -> clean; `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` -> `40 passed`.
- Builder-challenger result: PASS. It confirmed the scoped receipt-kind matrix and focused proof.
- Follow-up risks: validation intentionally checks payload-link presence rather than cross-record validity, which remains a later lifecycle/engine concern.

[[2026-07-23T00:37:38+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-3; Builder Notes; committed task changes at `469524efa`; and the admitted authority in `.owlbear/changes/replace-delivery-pipeline/design.md` sections 3.5, 4, and 7.1 plus graph `DN-003` / `IF-003`.
- Named authorities checked: design section 7.1 requires a job to retain only operational identity/references and project title, outcome, acceptance, modules, interfaces, and proof from authority. The implementation keeps the intended owner boundary in `serve/kanban/src/owlbear_kanban/jobs.py`, `receipt.py`, and package exports; there is no Change Module Map deviation.
- Normal-path boundary exercised: `parse_job_mapping` and `parse_receipt_mapping` were invoked through the public `owlbear_kanban` package exports. No replacement was used above the public parser boundary.
- Checks run:
  - `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` passed: 40 passed.
  - Public job parser smoke with `target_node_id=""` returned `job True` and `diagnostics []`.
  - Public audit receipt parser smoke without `node_plan_digest` returned `receipt True` and `diagnostics []`.
- Findings:
  - AC-1 fails: `JobRecord.target_node_id` has no identity validation, so a malformed empty target is accepted instead of producing a stable diagnostic.
  - AC-3 fails: the parser requires `node_plan_digest` only for shape/build/accept. The task requires kind-specific enforcement across the schema-version-1 receipt kinds, and the audit smoke accepted an omitted digest. Reconcile the exact per-kind target/digest/predecessor/evidence/code-revision matrix against the admitted receipt contract and enforce it with stable diagnostics.
  - Existing `test_jobs.py` exercises `ShapeJob` generation only, not the new public parser/projection API. It cannot prove AC-1 or AC-2. Add focused table-driven public-boundary coverage for all job kinds, malformed target identity/unknown fields, authority projection, and serialization excluding normative fields.
- Patches applied: none; the defects and missing proof require builder implementation and durable focused tests, outside verifier patch-pass limits.
- Memory assessment: all recalled entries were assessed; one recalled entry (`a7266466-8fb6-4af0-b7c1-7d350ebe0baf`) was no longer found by the assessment service.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Validate `JobRecord.target_node_id` as a delivery-node identity and return a stable parser diagnostic for malformed values. | `serve/kanban/src/owlbear_kanban/jobs.py`, focused tests | Public parser smoke accepted an empty target with no diagnostic. |
| 2 | builder | Define and enforce the authority-consistent schema-version-1 receipt requirement matrix for target, delivery/node-plan digests, predecessor links, evidence, and code revision across every receipt kind. | `serve/kanban/src/owlbear_kanban/receipt.py`, focused tests | Public audit parser smoke accepted a missing node-plan digest. |
| 3 | builder | Add focused public parser/projection tests covering AC-1 and AC-2, including serialization absence of normative fields. | `serve/kanban/tests/test_jobs.py` | Existing tests only cover legacy shape-generation behavior. |

- Final route: REJECT to build.


## Verify Correction
- The audit parser smoke recorded in the preceding Verify Notes is not a defect: admitted design section 3.5 defines `audit` as change-wide, and section 4.2 defines node-plan digests only for delivery-node plans. Therefore the prior receipt-specific finding and Required Follow-up row 2 are superseded and require no work.
- The REJECT remains required for the independent AC-1 defect (empty `target_node_id` accepted without a stable diagnostic) and the missing focused public parser/projection coverage needed to prove AC-1 and AC-2. The builder should retain the authority-consistent receipt matrix already implemented unless focused authority comparison finds a separate concrete violation.

[[2026-07-23T00:41:26+02:00]]
## Builder Notes
- Change envelope: repair the native public job parser and its focused public-boundary proof only. Validate delivery-node target identity and accept serialized operational reference arrays while retaining immutable records. No receipt-store, lifecycle, dispatch, legacy carrier, MCP, Cockpit, or bootstrap change.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`; `serve/kanban/tests/test_jobs.py`.
- Change Module Map deviations: none. The existing `jobs.py` owner and its focused test module directly contain the reported parser defect and AC-1/AC-2 proof boundary.
- Implementation: constrained `JobRecord.target_node_id` to the authority-defined `DN-###` identity format, preserving `ERR_JOB_TARGET_UNKNOWN` diagnostics; normalized serialized list reference fields to immutable tuples at the public parser boundary.
- Proof selected: table-driven public parsing for shape, build, accept, audit, and supersession; stable invalid-kind, malformed-target, and unknown-field diagnostics; authority projection and serialization exclusion of normative fields.
- Durable-test justification: added focused durable coverage because malformed public contract mappings and absent authority-projection boundary checks are concrete, repeatable regressions not covered by the legacy shape-generation tests.
- Commands run: `uv run --project . pytest serve/kanban/tests/test_jobs.py -q` -> `18 passed`; `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` -> `50 passed`; `uv run --project . ruff check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/tests/test_jobs.py` and `ruff format --check` -> clean.
- Builder-challenger result: PASS. It independently confirmed task alignment, scoped public-boundary coverage, and reran the 50-test suite and static checks.
- Follow-up risks: no additional risk identified; receipt kind matrix remains unchanged because the verifier correction confirmed audit is change-wide.

[[2026-07-23T00:43:52+02:00]]
## Verify Notes
- Evidence reviewed: all ACs; three Builder Notes entries; the scoped implementation commit `a6f6b72c8d2a854f266b3f7e29d2e799d2b823bb`; existing public-boundary tests in `serve/kanban/tests/test_jobs.py` and `serve/kanban/tests/test_change_receipts.py`.
- Named authorities checked: `.owlbear/changes/replace-delivery-pipeline/design.md` sections 4.2 and 4.3 define the delivery and node-plan digest relationship and receipt validity; `graph.yaml` REQ-009 confirms job kinds are transformations while claim/block/evidence state remains orthogonal. The task's authority-projection rule is satisfied: `JobRecord` serializes operational references only, while `project_job` sources title, outcome, acceptance, modules, interfaces, and proof from `ChangeRevision`.
- Change Module Map: changed owners are `jobs.py`, `receipt.py`, and package exports, plus their existing focused tests. No deviation found; no legacy carrier, storage, lifecycle, dispatch, MCP, or Cockpit surface was changed.
- Normal-path boundary exercised: exported `parse_job_mapping`, `project_job`, and `parse_receipt_mapping` are called directly. The job test loads the actual admitted `ChangeRevision`; no replacement occurs above the public parser/projection boundary. Parser tests cover schema-v1 mappings and deterministic round trips for shape, build, accept, audit, and supersession.
- Checks run: `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` passed 50 tests; Ruff lint passed for the two native modules and focused tests; Ruff format check passed for the same four files.
- Findings: none. The kind-specific receipt matrix matches authority: shape, build, and accept require `node_plan_digest`; audit and supersession remain change-wide. No verifier patch applied.
- Memory: assessed recalled entries. Nineteen assessments succeeded; one recalled deep-freezing entry reported not found by memory storage during assessment, with no impact on this task's verification.
- Verifier-challenger result: pass. It confirmed AC coverage, direct public-boundary proof, authority-derived projections, immutable operational records, and scoped changes.
- Final route: PASS; task advanced to collect.
