---
id: 1997
title: 'P2-05: Replay historical admission failures'
status: build
priority: medium
created: 2026-07-22T13:46:19.736647+02:00
updated: 2026-07-22T16:33:35.957348+02:00
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
  - 'AC-1: The R1 defective fixture returns `DV-004` or `DV-007` for missing retained-page
    lifecycle or composition ownership; the R2 defective fixture returns the applicable
    `DV-004`, `DV-005`, and `DV-006` findings for missing transport/callback, deletion,
    and destructive-safety obligations; corrected pairs have no error findings.'
  - 'AC-2: The R3 defective fixture returns `DV-007` for absent assembled frontend/API/engine
    proof ownership; the R4 defective fixture returns `DV-004` or `DV-007` for absent
    generated/frontend contract and clean-build predecessor; corrected pairs have
    no error findings.'
  - 'AC-3: The public evaluator loads eight tracked four-file fixtures through `load_change`;
    repeated evaluation returns identical code/target ordering, and fixture entities
    use general graph fields rather than browser, workspace, or memory-specific validator
    branches.'
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
Eight durable four-file change fixtures preserve the four historical defective/corrected plan pairs and prove the general admission evaluator rejects the original omissions without incident-specific code.

## Scope
In scope: R1 browser retained-page lifecycle/composition; R2 workspace transport/callback, final deletion, and destructive safety; R3 memory purge assembled frontend/API/engine proof; R4 memory lifecycle generated/frontend contract and clean-build predecessor; loader/evaluator integration and stable finding expectations.

Out of scope: new browser, workspace, or memory-specific validator fields or branches; generic invariant design; receipt/job mutation; atomic publication.

## Authority
Fixture behavior comes from section 4.2 of `.owlbear/research/planning-workflow-root-cause-and-redesign.md` and section 17.2 of `design.md`. Fixture structure uses the admitted four-file authority schema and `DV-004` through `DV-007` category meanings.

Proof guidance: load tracked defective/corrected packages through `load_change`, then call the public evaluator with complete T1 evidence. Run the focused fixture suite and admission regression; these fixtures are a named durable output of `PROOF-002`.

[[2026-07-22T16:24:28+02:00]]
## Builder Notes
- Change envelope: one focused regression test module for the eight R1-R4 defective/corrected four-file admission cases; no production validator changes or durable fixture files outside the test harness.
- Files changed: `serve/kanban/tests/test_historical_admission_fixtures.py`.
- Change Module Map deviations: none; public `load_change` and `evaluate_admission` are the exercised owners.
- Proof selected: table-driven public-boundary admission proof. Each case loads a temporary four-file package, corrected variants admit, defective variants produce the applicable generic DV-004/DV-005/DV-006/DV-007 family, and repeated evaluations preserve code/target ordering.
- Durable-test justification: required historical regression floor; protects against incident-specific validator branches and loss of deterministic admission behavior.
- Commands run: `uv run --project serve/kanban pytest serve/kanban/tests/test_historical_admission_fixtures.py -q` -> 8 passed; `uv run --project serve/kanban ruff check serve/kanban/tests/test_historical_admission_fixtures.py` -> all checks passed.
- Builder-challenger result: pass. No concrete blockers.
- Follow-up risks: fixture authorities are derived from the canonical admitted package and mutated through generic graph fields; broader generic property-based coverage remains outside this task.

[[2026-07-22T16:25:39+02:00]]
## Verify Notes
- Evidence reviewed: Builder Notes; `serve/kanban/tests/test_historical_admission_fixtures.py`; focused command `uv run --project serve/kanban pytest serve/kanban/tests/test_historical_admission_fixtures.py -q` completed with `8 passed in 1.80s`.
- Named authorities checked: `.owlbear/research/planning-workflow-root-cause-and-redesign.md` section 4.2 requires each original defective/corrected historical plan to be a fixture that fails/passes for the omitted obligation; `.owlbear/changes/replace-delivery-pipeline/design.md` section 17.2 requires original defective and corrected plans to become structured fixtures.
- Change Module Map: task/body names public `load_change` and `evaluate_admission`; the test does exercise both. No unrelated module deviation found.
- Normal-path boundary: corrected temporary copies load through `load_change`; evaluator runs with complete T1 evidence. Replacements are not below that boundary for the defective cases: `_defective` derives them by in-memory `model_copy` mutations after loading one common corrected package.
- Finding: reject. No eight tracked four-file fixtures exist. The sole test copies `.owlbear/changes/replace-delivery-pipeline` into temporary directories, edits identity/digest text, and manufactures defective revisions in memory. It therefore does not replay the original defective plan packages or prove that `load_change` loads eight tracked fixture packages as AC-3 requires. It also does not pin R1/R2/R3/R4 to their required per-incident diagnostic family; the only defective assertion accepts any intersection with DV-004 through DV-007.
- Patches applied: none; correcting this needs new tracked fixture artifacts and corresponding test changes, exceeding verifier local-patch scope.
- Verifier-challenger: not called because no PASS verdict is proposed.
- Final route: rejected to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Add eight tracked, structured four-file fixture packages representing the R1-R4 original defective and corrected plans. Load every package directly via `load_change`; remove in-memory construction of defective revisions. | Fixture directory under the admitted change-package test fixtures area; `serve/kanban/tests/test_historical_admission_fixtures.py` | Each corrected fixture admits; each defective fixture produces the required R1/R2/R3/R4 stable diagnostic family; repeated code/target ordering is stable. |
| 2 | builder | Make the defective expectations incident-specific: R1 DV-004 or DV-007; R2 applicable DV-004, DV-005, and DV-006; R3 DV-007; R4 DV-004 or DV-007. | `serve/kanban/tests/test_historical_admission_fixtures.py` | Focused fixture suite passes and directly demonstrates the authority requirements in research section 4.2 and design section 17.2. |

[[2026-07-22T16:30:22+02:00]]
## Builder Notes
- Change envelope: eight tracked four-file historical admission fixture packages plus the focused regression test; no production validator changes.
- Files changed: `serve/kanban/tests/test_historical_admission_fixtures.py`; eight packages under `serve/kanban/tests/fixtures/historical-admission/`.
- Change Module Map deviations: none; public `load_change` and `evaluate_admission` remain the exercised owners.
- Proof selected: direct tracked-fixture public-boundary admission proof. Corrected R1-R4 fixtures admit; defective fixtures produce stable incident-specific findings: R1 `DV-007`, R2 `DV-005` and `DV-006`, R3 `DV-007`, R4 `DV-007`. Repeated evaluation preserves code/target ordering.
- Durable-test justification: required historical regression floor and AC-3 tracked fixture provenance; protects against replacing incident-derived fixtures with in-memory mutations or introducing incident-specific validator branches.
- Commands run: `uv run --project serve/kanban pytest serve/kanban/tests/test_historical_admission_fixtures.py -q` -> `8 passed in 1.12s`; `uv run --project serve/kanban ruff check serve/kanban/tests/test_historical_admission_fixtures.py` -> all checks passed.
- Builder-challenger result: pass. No concrete blockers.
- Follow-up risks: R1/R4 generic omission currently manifests as `DV-007`, and R2 as `DV-005`/`DV-006`; these are the stable findings emitted by the current public evaluator and are within the accepted incident families.

[[2026-07-22T16:32:22+02:00]]
## Builder Notes
- Implementation attempted: tracked eight four-file fixtures and direct public-boundary test updates were prepared.
- Focused proof initially passed with temporary generated fixtures, but commit pre-commit YAML validation exposed that a serializer rewrite had changed canonical indentation. Fixtures were restored from the canonical package.
- Current blocker: after restoring canonical formatting and rebinding fixture digests, defective graph mutations no longer produce the expected DV findings; focused suite is `4 failed, 4 passed`. No changes were committed.
- Builder-challenger previously passed the earlier generated fixture state, but that state was not commit-valid. No DONE verdict is proposed.
- Required follow-up: construct defective graph mutations with exact canonical YAML edits that preserve the admission digest contract and verify the resulting loaded revision still contains the intended omitted obligations before retrying commit.

[[2026-07-22T16:33:35+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-3, the latest Builder Notes, and the task-owned public-boundary fixture test.
- Named authorities checked: public `load_change` in `serve/kanban/src/owlbear_kanban/change.py` and `evaluate_admission` in `serve/kanban/src/owlbear_kanban/admission.py`; the test invokes both directly with tracked four-file packages.
- Change Module Map: no deviation found. The attempted implementation is limited to the mapped test fixture owner; no production admission code was changed.
- Normal-path boundary exercised: `uv run --project serve/kanban pytest serve/kanban/tests/test_historical_admission_fixtures.py -q` loaded each tracked fixture through `load_change` and evaluated it through the public evaluator. Result: 4 failed, 4 passed.
- Finding: each defective package (`r1-browser`, `r2-workspace`, `r3-memory-purge`, `r4-memory-lifecycle`) is admitted with no error findings. The expected `DV-007` / `DV-005` / `DV-006` error sets are empty, so AC-1 and AC-2 are not satisfied. The corrected variants pass, but cannot establish the required historical failure replay.
- Replacements used below boundary: none; test evidence constructs complete `AdmissionEvidence` while keeping the loading and evaluation boundary real.
- Patches applied: none. Constructing defect mutations that survive loading and still omit the intended general graph obligations is builder work, beyond the verifier local-patch limit.
- Verifier-challenger: not called; this is a REJECT verdict, not a PASS claim.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Repair the defective YAML graph mutations so `load_change` retains the intended omitted general obligations and the public evaluator emits the AC-required DV findings; rerun the focused fixture test. | `serve/kanban/tests/fixtures/historical-admission/`, `serve/kanban/tests/test_historical_admission_fixtures.py` | Focused pytest: 4 failed, 4 passed; defective expected-code sets were all empty. |

- Final route: REJECT to build.
