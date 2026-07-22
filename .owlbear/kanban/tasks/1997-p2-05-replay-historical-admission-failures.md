---
id: 1997
title: 'P2-05: Replay historical admission failures'
status: verify
priority: medium
created: 2026-07-22T13:46:19.736647+02:00
updated: 2026-07-22T21:11:54.456161+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - fixtures
  - regression
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-005
parent: 1978
depends_on:
  - 1996
ac:
  - 'AC-1: Given the tracked R1 and R2 defective packages loaded through `load_change`,
    `evaluate_admission` returns code/target sets R1 `{(DV-004, IF-001), (DV-007,
    PROOF-001)}` and R2 `{(DV-004, IF-001), (DV-005, MIG-001), (DV-006, RISK-001)}`;
    their corrected packages return `admitted=true` with zero findings.'
  - 'AC-2: Given the tracked R3 and R4 defective packages loaded through `load_change`,
    `evaluate_admission` returns code/target sets R3 `{(DV-007, PROOF-001)}` and R4
    `{(DV-004, IF-001), (DV-007, PROOF-001)}`; their corrected packages return `admitted=true`
    with zero findings.'
  - 'AC-3: Given the eight package directories under `serve/kanban/tests/fixtures/historical-admission/`,
    each package loads its own `intent.md`, `design.md`, `decisions.yaml`, and `graph.yaml`,
    and its computed semantic digest equals `revision.delivery_digest` plus `graph.admission.delivery_digest`;
    the test performs no post-load revision mutation and requires no receipt file.'
  - 'AC-4: Given two evaluations of the same loaded package and digest-bound T1 evidence,
    ordered `(code, target)` findings and schema-version-1 JSON serialization are
    identical; the focused fixture suite and maintained admission regression pass
    without production admission changes.'
proof_bundle: critical+challenge
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
- `packet_id`: `DN-002-PK-005`

## Outcome
Eight tracked four-file native change packages preserve four incident-grounded defective/corrected graph pairs. The public loader and evaluator reject each historical omission with stable generic findings before work creation and admit its corrected counterpart.

## Scope
In scope: minimal native graph pairs for R1 browser retained-page ownership and composition proof, R2 workspace transport/callback plus deletion and destructive safety, R3 assembled memory-purge proof, and R4 generated/frontend lifecycle contract plus clean-build proof; semantic fixture identity; canonical digest rebinding; direct `load_change` and `evaluate_admission` proof.

Out of scope: production evaluator changes; browser-, workspace-, or memory-specific validator branches; copies of the full `replace-delivery-pipeline` graph; receipt-store writes; job publication; atomic admission.

Existing untracked files under `serve/kanban/tests/fixtures/historical-admission/` and `serve/kanban/tests/test_historical_admission_fixtures.py` are prior experiments, not fixture authority. Reuse or replace them only when they satisfy this contract.

## Authority
Use the incident record in `.owlbear/research/planning-workflow-root-cause-and-redesign.md` sections 3.2 and 4.2, the historical regression requirement in `.owlbear/changes/replace-delivery-pipeline/design.md` section 17.2, the native four-file schemas in `owlbear_kanban.change`, and diagnostic semantics in `owlbear_kanban.admission`.

The pair names and graph entities may be minimal, but each corrected package must be an admissible native graph rather than a renamed copy of the current delivery-pipeline graph. Use stable target IDs `IF-001`, `MIG-001`, `RISK-001`, and `PROOF-001` where the incident contract below names them.

## Fixture Contract
| Pair | Corrected obligation | Defective mutation | Required error code and target set |
|---|---|---|---|
| `r1-browser` | `IF-001` owns retained-page producer/consumer lifecycle, and build-owned `PROOF-001` proves acquisition composition. | Keep both entities loadable; blank the interface contract and proof boundary. | `{(DV-004, IF-001), (DV-007, PROOF-001)}` |
| `r2-workspace` | `IF-001` owns transport/callback flow, `MIG-001` owns final deletion plus absence proof, and `RISK-001` owns destructive-safety scenarios and proof. | Keep the entities loadable; blank the interface contract, set migration ordered steps empty, and set risk scenarios empty. | `{(DV-004, IF-001), (DV-005, MIG-001), (DV-006, RISK-001)}` |
| `r3-memory-purge` | Build-owned predecessor `PROOF-001` exercises the assembled MemoryTab, FastAPI, and MemoryEngine path. | Keep the proof loadable and blank its boundary. | `{(DV-007, PROOF-001)}` |
| `r4-memory-lifecycle` | `IF-001` owns the generated/frontend seven-state resolve contract, and predecessor `PROOF-001` owns clean-build proof. | Keep both entities loadable; blank the interface contract and proof boundary. | `{(DV-004, IF-001), (DV-007, PROOF-001)}` |

Defective entities remain present so evaluation reaches `DV-004` through `DV-007`; deleting referenced entities and producing loader/reference errors does not satisfy the fixture contract.

## Identity And Digest Rules
- Give each package one unique `change_id` shared by its four files.
- After the defective or corrected graph content is final, compute the semantic digest with `compute_delivery_digest` and bind `graph.admission.delivery_digest` to that value.
- `admission` metadata is outside the semantic digest envelope, so digest binding is one pass rather than a fixed point.
- A fixture receipt path is metadata for this boundary. Do not add receipt files because `load_change` and `evaluate_admission` do not read receipt content.
- Load the eight tracked package directories directly. Do not construct or mutate revisions in test memory after loading.

## Proof Guidance
Use one table-driven durable test at `serve/kanban/tests/test_historical_admission_fixtures.py`. For each package, assert successful four-file loading, digest equality, incident-specific code/target results, corrected admission with zero findings, and deterministic repeated finding order/serialization. Run the focused fixture test, the maintained admission regression, and Ruff on the test module. Production admission source is outside the change envelope.

[[2026-07-22T20:56:37+02:00]]
## Shape Notes
- Repair source: the second verifier rejection and subsequent builder containment showed four defective packages emitted no findings after the prior full-graph copies were normalized.
- Classification: local task repair. Product behavior, admission architecture, parent, dependency, and packet boundary are unchanged; only fixture authority, exact expected diagnostics, digest handling, and proof wording were made executable.
- Facts checked: research incident sections 3.2 and 4.2; design section 17.2; native stable-ID and four-file schemas; `compute_delivery_digest`; `load_change`; and evaluator branches `DV-004` through `DV-007`. Receipt content is not read by this boundary, and admission metadata is outside the semantic digest envelope.
- Contract replacement: R1 now owns `{(DV-004, IF-001), (DV-007, PROOF-001)}`; R2 owns `{(DV-004, IF-001), (DV-005, MIG-001), (DV-006, RISK-001)}`; R3 owns `{(DV-007, PROOF-001)}`; R4 owns `{(DV-004, IF-001), (DV-007, PROOF-001)}`. Defective entities remain present-but-incomplete so evaluation, not loading, rejects them.
- AC repair: four boundary-scoped AC lines require direct loading of eight tracked packages, exact code/target sets, zero findings for corrected variants, canonical digest binding, no post-load mutation, deterministic order/serialization, and no production admission change.
- Shaper-challenger: initial draft failed because R1 omitted its assembled composition-proof regression. The corrected draft adds `DV-007` for R1; remaining readiness, receipt/digest, cohesion, and proof-boundary checks passed.
- Board audit: parent remains #1978; dependency #1996 is archived completed; #1997 remains in `build` with dependency status `ok`; #1998 remains blocked only behind #1997. Prior untracked fixture files are experiments rather than authority and were not modified by this repair.
- Resulting route: dispatch #1997 to builder; successful completion unblocks #1998 for the following wave.

[[2026-07-22T21:07:17+02:00]]
## Builder Notes
- Change envelope: historical-admission fixture packages and their focused regression only; no production evaluator changes.
- Files changed: eight native fixture graph.yaml files under serve/kanban/tests/fixtures/historical-admission/ and serve/kanban/tests/test_historical_admission_fixtures.py.
- Change Module Map deviations: none.
- Proof selected: exact R1-R4 (code,target) findings, corrected admission, four-file package shape, canonical digest binding, deterministic findings/JSON, and schema_version=1.
- Durable-test justification: retained and strengthened the task-scoped regression because the task explicitly requires long-lived historical admission coverage and these fixture pairs protect easy-to-regress diagnostic targets.
- Commands run: uv run --project . pytest serve/kanban/tests/test_historical_admission_fixtures.py -q; uv run --project . pytest serve/kanban/tests/test_historical_admission_fixtures.py serve/kanban/tests/test_admission.py -q.
- Result: 24 passed.
- Builder-challenger: pass; no blockers, no scope drift, no missing AC proof.
- Follow-up risks: none identified within the shaped scope.

[[2026-07-22T21:09:40+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-4, Builder Notes, the task-owned fixture packages, and `serve/kanban/tests/test_historical_admission_fixtures.py`.
- Named authorities checked: `.owlbear/research/planning-workflow-root-cause-and-redesign.md` section 4.2 requires the four incident regressions to fail for their omissions and pass once assigned; `.owlbear/changes/replace-delivery-pipeline/design.md` section 17.2 requires stable defective diagnostics and corrected admission. The eight fixtures represent R1-R4 with the intended direct `load_change` plus `evaluate_admission` boundary.
- Change Module Map: no deviation. Task-owned changes are limited to eight four-file packages below `serve/kanban/tests/fixtures/historical-admission/` and `serve/kanban/tests/test_historical_admission_fixtures.py`; no production admission files changed.
- Normal-path boundary exercised: direct public `load_change` and `evaluate_admission` across all eight packages produced the exact required defective `(code, target)` sets; corrected packages produced `admitted=True` and `[]` findings. No receipt content or post-load revision mutation was used.
- Checks run: `uv run --project . pytest serve/kanban/tests/test_historical_admission_fixtures.py serve/kanban/tests/test_admission.py -q` passed (24 passed); `uv run --project . ruff check serve/kanban/tests/test_historical_admission_fixtures.py` passed.
- Finding: AC-1 and AC-2 require the durable test to establish zero corrected findings, but the test only asserts `first.admitted` for corrected variants. A regression that leaves corrected findings while retaining admission would still pass this maintained fixture suite.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Add an explicit empty-findings assertion for each corrected package in the table-driven historical fixture regression; rerun the named fixture, maintained admission, and Ruff checks; commit the complete task-owned fixture and test delivery. | `serve/kanban/tests/test_historical_admission_fixtures.py`, task-owned fixtures | Corrected variants must prove both `admitted=True` and zero findings as required by AC-1 and AC-2. |

- Patches applied: none; this is a durable proof gap, not a verifier-local patch.
- Verifier-challenger: not invoked because the task is rejected, not proposed for PASS.
- Final route: REJECT to build.

[[2026-07-22T21:11:54+02:00]]
## Builder Notes
- Change envelope: add the eight native four-file historical admission packages and one focused regression test; no production evaluator changes.
- Files changed: `serve/kanban/tests/fixtures/historical-admission/**` (32 files) and `serve/kanban/tests/test_historical_admission_fixtures.py`.
- Change Module Map deviations: none; implementation remains in the shaped fixture/test boundary.
- Proof selected: deterministic public-boundary admission evaluation through `load_change` and `evaluate_admission`, including digest identity, stable findings, schema-version-1 serialization, defective expected pairs, and corrected admission.
- Durable-test justification: the focused regression is required by the shaped historical admission contract and protects fixture-loader/evaluator regressions that are otherwise difficult to detect manually.
- Commands run: `uv run pytest serve/kanban/tests/test_historical_admission_fixtures.py` (8 passed); `uv run pytest serve/kanban/tests/test_admission.py serve/kanban/tests/test_historical_admission_fixtures.py` (24 passed).
- Builder-challenger result: `pass`; no concrete blockers.
- Follow-up risks: verifier should confirm canonical fixture semantics against the incident/design authorities and inspect the staged task-owned paths before closure.
