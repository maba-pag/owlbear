---
id: 2094
title: 'P17-01: Migrate and replay historical admission incidents'
status: archived
priority: high
created: 2026-07-27T19:45:12.424338+02:00
updated: 2026-07-27T20:20:10.549539+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T1
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on: []
ac:
  - 'AC-1: Given modular defective fixtures for browser, workspace, memory purge,
    and memory lifecycle incidents with complete evidence, public validation returns
    respectively `DV-004`; `DV-004` and `DV-006`; `DV-007`; and `DV-004` and `DV-007`,
    creates no admission receipt, and materializes no job.'
  - 'AC-2: Given each corrected counterpart and complete evidence, public validation
    has zero findings and public admission publishes one digest-bound admission receipt
    plus initial plan jobs; replay returns the stored identities without duplication.'
  - 'AC-3: Given the eight durable fixture directories, canonical loading joins intent,
    design, decisions, modular obligations/contracts/nodes, and isolated plans; `graph.yaml`
    is absent and each pair preserves only its named semantic defect/correction delta.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Eight historical incident fixtures use current modular authority and expose their intended semantic findings instead of a physical-layout failure.

## Scope
In scope: MOD-008 fixture migration and public validation/admission replay. Out of scope: production loader compatibility, runtime correction, assembled workflow, and live carrier mutation.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, IF-002, RISK-005 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a focused public validation/admission fixture matrix; add no production compatibility path.

[[2026-07-27T20:07:04+02:00]]
## Builder Notes

**Verdict:** DONE

### Change
- Migrated all eight `serve/kanban/tests/fixtures/historical-admission/*` packages from retired `graph.yaml` authority to `delivery/obligations.yaml`, `delivery/contracts.yaml`, and `delivery/nodes.yaml`.
- Added no plan files because every legacy `execution.node_plans` mapping was empty.
- Preserved all pre-task semantic authority except two stale extra defects that contradicted the shaped exact finding sets: restored `r1-browser-defective` `PROOF-001.boundary` so its blank `IF-001.contract` remains the sole defect, and restored `r2-workspace-defective` `MIG-001.ordered_steps` so its blank interface contract and empty risk scenarios remain the sole defects. Rebound those two admission digests.
- Added durable public-boundary proof in `serve/kanban/tests/test_historical_admission.py`. No production loader or compatibility code changed.

### Acceptance Evidence
- **AC-1:** Public `load_change`, `evaluate_admission`, and `validate_and_admit` matrix returns exact defective sets: browser `{DV-004}`; workspace `{DV-004, DV-006}`; memory purge `{DV-007}`; memory lifecycle `{DV-004, DV-007}`. Admission returns no receipt or generation and creates no source receipt/job directories or work root.
- **AC-2:** Every corrected fixture has zero public findings. First admission publishes one digest-bound receipt, one generation manifest, and one initial plan job per delivery node. Same-identity replay returns equal stored receipt/generation/assessment values; receipt, manifest, and `JobStore` counts remain unchanged.
- **AC-3:** All eight packages contain exactly the three modular delivery documents and no `graph.yaml`. Public loading joins nonempty intent, design, decisions, obligations, contracts, and nodes. A ruamel comparison against pre-task `HEAD` authority proved all eight semantic migrations equal after accounting only for the two shaped stale-defect normalizations and admission digest fields.

### Validation
- Focused historical matrix: 16 passed, including post-lint rerun.
- Full `serve/kanban/tests/` regression suite: 351 passed; four existing Python multiprocessing fork deprecation warnings.
- Focused workspace lint: clean for the test and all 24 YAML files, including Ruff, Ruff format, YAML parse, yamllint, and EditorConfig; only four unrelated pre-existing TODO scan warnings.
- `git diff --check`: clean. VS Code diagnostics: no errors.
- Builder challenger: `pass`; independently reran the focused matrix with 16 passed.
- Assessed all 20 recalled builder memories. Saved pending builder-scoped ruamel YAML normalization lesson `9d9767fe-bd12-4941-883a-c4d88f64abb6`.

### Files
- Deleted eight `serve/kanban/tests/fixtures/historical-admission/*/graph.yaml` files.
- Added 24 `serve/kanban/tests/fixtures/historical-admission/*/delivery/{obligations,contracts,nodes}.yaml` files.
- Added `serve/kanban/tests/test_historical_admission.py`.

### Unresolved Follow-up
None.

[[2026-07-27T20:16:09+02:00]]
## Verify Notes

**Verdict:** PASS

### Independent Verification
- Verified exact builder commit `ff220a3a9ce76226f71596584d6e342da65274fa` at current `HEAD`; its scope is the task record, 24 modular fixture YAML additions, eight `graph.yaml` deletions, and one public-boundary test. No production or compatibility code changed.
- **AC-1:** Fresh public `load_change`, `evaluate_admission`, and `validate_and_admit` matrix returned exact defective code sets: browser `{DV-004}`; workspace `{DV-004, DV-006}`; memory purge `{DV-007}`; memory lifecycle `{DV-004, DV-007}`. The transaction returns before recovery/publication on findings; tests observed `None` receipt/generation and no receipt, generation, work-root, or job publication.
- **AC-2:** Corrected fixtures had zero findings. Admission produced a digest-bound receipt, one generation manifest, and one stored initial plan job per node. Same-identity replay returned equal receipt, generation, and assessment values with one receipt, one manifest, and unchanged exact `JobStore` contents.
- **AC-3:** Public loading joined all eight fixture packages. Each contains only `delivery/{obligations,contracts,nodes}.yaml` and no `graph.yaml`. Recursive pair comparison showed only identity/digest plus the intended defects: R1 blank `IF-001.contract`; R2 blank contract and empty `RISK-001.scenarios`; R3 blank `PROOF-001.boundary`; R4 blank contract and blank proof boundary. Canonical comparison with `ff220a3^` proved semantic preservation `8/8` after asserting the retired execution envelope was exactly empty and accounting only for digest rebinding plus the documented R1 proof-boundary and R2 migration-step stale-defect repairs.

### Fresh Checks
- `uv run pytest serve/kanban/tests/test_historical_admission.py -q --tb=short`: 16 passed.
- `uv run pytest serve/kanban/tests/ -q --tb=short`: 351 passed, four Python 3.14 multiprocessing fork deprecation warnings.
- Focused `uv run lint` over all added/modified builder paths: passed; four unrelated repository TODO warnings only.
- `git diff --check ff220a3^ ff220a3`: clean.
- Assertion-based migration proof: semantic preservation `8/8`, modular layout `8/8`, rebound digests exactly R1 browser defective and R2 workspace defective.
- Verifier-challenger: `pass`; evidence directly covers all ACs and remains within minimum scope.
- Assessed all 20 recalled verifier memories. No verifier patch or unresolved follow-up.

[[2026-07-27T20:20:10+02:00]]
## Collect Notes

**Verdict:** ARCHIVED

### Closure Evidence
- Builder commit `ff220a3a9ce76226f71596584d6e342da65274fa` migrated all eight historical incident pairs to modular delivery authority and added the public-boundary fixture matrix; verifier commit `821ac18fa45d807666eb1f4835e52959fa2dcb40` is its current-HEAD descendant and independently confirmed the change.
- **AC-1:** Exact defective finding sets and absence of receipt, generation, work root, and jobs are covered by the public validation/admission matrix.
- **AC-2:** Corrected fixtures produce zero findings, one digest-bound receipt and initial jobs, while same-identity replay preserves stored identities and counts.
- **AC-3:** All eight packages load joined modular authority, omit `graph.yaml`, and preserve only the named semantic pair deltas.
- Fresh collector check: focused historical admission matrix passed 16 tests.
- Builder challenger: `pass`. Verifier challenger: `pass`.
- Leaf has no dependencies or requests. Parent `#1990` remains in `collect` with other active descendants; archiving this leaf satisfies its `#2094` dependency only.
- Assessed all six recalled collector memories.

### Unresolved Follow-up
None.
