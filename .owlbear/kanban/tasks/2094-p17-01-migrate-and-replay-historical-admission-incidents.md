---
id: 2094
title: 'P17-01: Migrate and replay historical admission incidents'
status: verify
priority: high
created: 2026-07-27T19:45:12.424338+02:00
updated: 2026-07-27T20:07:04.762454+02:00
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
archival_reason:
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
