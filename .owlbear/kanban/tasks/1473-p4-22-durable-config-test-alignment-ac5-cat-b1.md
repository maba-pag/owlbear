---
id: 1473
title: 'P4-22: Durable config test alignment (AC5 Cat-B1)'
status: in-progress
priority: critical
created: 2026-05-09T08:46:53.927445+00:00
updated: 2026-05-09T10:12:39.061451+00:00
tags:
- phase-4
- type:refactor
- scope:tests
- topology
- type:test
parent: 1439
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Context
Parent #1439 collapsed configurable kanban topology into product constants. AC1-4 implementation is committed and working. This subtask remediates failures in the 4 durable config test modules in `tests/`.

## Scope
In scope: tests/test_config_loader.py, tests/test_config_authority.py, tests/test_config_schema.py, tests/test_config_grouped.py.
Out of scope: task-scoped tests (test_*_NNNN.py), cockpit tests, kanban package tests, consumer tests.

## Acceptance Criteria
1. All tests in the scoped config test files pass after aligning with the topology-constant refactor. Verify: `uv run pytest tests/test_config_loader.py tests/test_config_authority.py tests/test_config_schema.py tests/test_config_grouped.py` exits 0. (td:2)

## Breaking Changes to Align With
1. `load_config(kanban_dir)` no longer raises `FileNotFoundError` when config.yml is absent — returns product-topology defaults. Only reads `next_id`.
2. `save_config(config, kanban_dir)` persists only `next_id`, not topology fields.
3. `BoardConfig` topology values are product-fixed constants from `PRODUCT_TOPOLOGY`.

## File-Specific Guidance
- **test_config_loader.py** (~11 tests): Remove/update `FileNotFoundError` expectations — `load_config` now returns product-topology defaults when config.yml is absent. Update any assertions that verify topology fields are read from config.yml.
- **test_config_authority.py** (~19 tests): Update save_config behavior expectations — only `next_id` is persisted. Remove assertions that verify topology fields round-trip through save_config.
- **test_config_schema.py**: Update save_config round-trip assertions (e.g. AC8-AC9 tests) to expect next_id-only persistence.
- **test_config_grouped.py**: Update grouped schema format expectations for topology-constant world — grouped output now reflects product-owned topology.

## Pipeline Note
Tests already exist and fail (RED). Builder updates test expectations to match the new API contract (GREEN). No separate test-writer step needed.

[[2026-05-09]]


## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: align 4 durable config test files with topology-constant refactor |
| Interface clarity | PASS | AC verifiable via single pytest command. Breaking changes documented (expanded below). |
| Dependency correctness | PASS | No deps needed. Parent #1439 AC1-4 committed. Layer 1 siblings (#1472, #1474, #1475) are independent. |
| Module layering | N/A | Test-only changes. |
| TDD compliance | PASS | Tests already exist and fail (RED). Builder aligns expectations (GREEN). `type:test` tag added for test-writer pass-through. |
| KISS/YAGNI | PASS | Minimal scope — update expectations to match committed API contract. |
| Premise challenge | PASS | Failing durable tests are real problem; parent auditor confirmed 427 failures in `tests/`. |
| Pattern consistency | PASS | Standard test alignment work. |
| Security surface | N/A | No new system boundaries. |
| Single domain | PASS | kanban test alignment only. |
| Failure Mode Map | N/A | Test-only changes, no new codepaths. |
| Decision-request verification | N/A | No research doc referenced. |
| User-action detection | SKIP | Counter-signals C1 (assertion targets), C2 (expected test outcomes). |

### Refinements Applied
1. **Added breaking change #4**: Vendor/unknown fields in config.yml are no longer read by `load_config`; `BoardConfig.extra='allow'` remains for direct model construction but the product-topology load path builds from constants only. Builder should update/remove vendor field preservation tests.
2. **Added `type:test` tag** for test-writer pass-through (tests already exist and fail).
3. **Expanded file-specific guidance** (see below).

### File-Specific Guidance Corrections
- **test_config_loader.py** (11 tests, not ~11): (a) Update `test_load_config_raises_on_missing_file` — `load_config` now returns defaults on absent config.yml, no `FileNotFoundError`. (b) Update/remove vendor field preservation tests (`test_load_config_preserves_grouped_vendor_field_at_root`, `test_load_config_preserves_grouped_tui_section_at_root`) — `load_config` no longer reads arbitrary YAML content. (c) `test_load_config_statuses_parsed` should pass (product topology includes "todo" and "done").
- **test_config_authority.py** (~22 tests): (a) Update `TestFromAC_SaveConfigRootOnly` — `save_config` now writes only `{"next_id": N}`, not root-level statuses/priorities. (b) Update `TestFromAC_RoundTrip` — round-trip now returns product-topology values, not custom `_STATUSES`/`_PRIORITIES`. (c) `TestFromAC_ConflictValidation` and `TestFromAC_BackwardCompat` test `BoardConfig.model_validate()` directly — should pass unchanged.
- **test_config_schema.py**: (a) Detection cascade tests (AC3-5) — `load_config` no longer distinguishes grouped/flat/legacy YAML; all formats return product-topology defaults. Tests asserting custom `tasks_dir`, `archive_dir`, `statuses` from YAML will fail. (b) Defaults migration tests (AC7) — `load_config` returns product defaults regardless of YAML content. (c) Save_config format tests (AC8) — `save_config` writes only `next_id`; tests expecting `schema: grouped`, nested sections, or full topology output will fail. (d) Round-trip tests (AC9) — tests comparing `reloaded == original` via `model_dump` should pass (both loads return product topology). (e) Vendor field round-trip `test_vendor_field_survives_save_reload_round_trip` — will fail (save_config writes only next_id). (f) `_migrate_config` tests — verify first; `_migrate_config` has been cleaned up and may already produce correct grouped output.
- **test_config_grouped.py**: Likely already passes — `_migrate_config` was cleaned up (no flat duplicates) and seed template is already grouped. Builder should verify with `uv run pytest tests/test_config_grouped.py` first. If already green, no changes needed.

### Challenge Results
- Challenger: reconsider (confidence 0.66) — raised: (1) file count misread in initial analysis (ACCEPTED — verified 11 tests, guidance was correct), (2) schema file guidance incomplete (ACCEPTED — expanded above), (3) vendor field contract ambiguity (ACCEPTED — added breaking change #4), (4) test_config_grouped.py may already pass (ACCEPTED — noted in guidance), (5) no per-file guard against production edits (REBUTTED — task scope is explicit, `deny-non-doc-writes.py` hook enforces).
- Architect response: accepted 4 of 5 concerns, incorporated into refinements. Verdict unchanged after correction.

### Test Depth
- AC1: td:2 (multiple files, multiple test patterns to update/remove/rewrite)
- Max depth: td:2
- Test-writer: SKIP (type:test tag — tests already exist and fail)

### Design Diverge
- Skipped — single approach (update test expectations to match committed API). No competing alternatives.

### Verdict: APPROVE
### Action Taken: Added `type:test` tag, added breaking change #4 (vendor field behavior), expanded file-specific guidance with corrections from challenger feedback. Advanced to todo.

[[2026-05-09]]
Architecture review complete. Refined task: (1) added `type:test` tag for test-writer pass-through, (2) added breaking change #4 (vendor/unknown fields no longer read by load_config), (3) expanded file-specific guidance with per-test correction detail for all 4 files. Challenger raised 5 concerns at 0.66 confidence — accepted 4 (file count correction, guidance expansion, vendor field contract, test_config_grouped.py may already pass), rebutted 1 (production edit guard). All 13 Step 2 criteria evaluated — all PASS/N/A.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no new tests to write.
- Pipeline Note from architect: "Tests already exist and fail (RED). Builder updates test expectations to match the new API contract (GREEN). No separate test-writer step needed."
- Passing through to builder.