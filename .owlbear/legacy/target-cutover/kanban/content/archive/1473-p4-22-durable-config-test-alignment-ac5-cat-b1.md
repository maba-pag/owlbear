---
id: 1473
title: 'P4-22: Durable config test alignment (AC5 Cat-B1)'
status: archived
priority: medium
created: 2026-05-09T08:46:53.927445+00:00
updated: 2026-05-09T15:25:16.842553+00:00
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
[[2026-05-09]]
## Builder Notes
- Implementation: aligned durable test expectations in `tests/test_config_loader.py`, `tests/test_config_authority.py`, and `tests/test_config_schema.py` to the current topology-constant contract (`load_config` uses product topology; `save_config` persists `next_id` only).
- Tests: 91 passed, 0 failed, 0 skipped (scoped run over the 4 AC files).
- Coverage: quality-runner reported overall 24% for requested modules (`config_loader` 100%, `storage` 24%, `migrate` 30%, `models` 86%). This is a test-only alignment task; no production module behavior changes were introduced.
- Ruff: clean (no violations in scoped lint run).
- Evidence summary: RED baseline showed 23 failing assertions tied to legacy expectations (vendor-field preservation, schema/detection assumptions, grouped persistence). GREEN run after updates passed all scoped tests and lint.
- Fixes applied: updated assertions/docstrings to reflect product topology constants, `next_id`-only persistence, and non-preservation of YAML vendor fields in load/save path.

### Post-task Reflection
- Initial RED signal was highly actionable because failures clustered around two contract shifts; this sped up surgical patching.
- A patch-introduced indentation syntax error in one test file was caught immediately by quality-runner and corrected before final verification.
- Keeping changes confined to assertion updates in existing durable tests avoided production churn and matched the task scope exactly.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped run: 91 passed, 0 failed, 0 skipped across tests/test_config_loader.py, tests/test_config_authority.py, tests/test_config_schema.py, and tests/test_config_grouped.py.

### Lint Results
- quality-runner scoped ruff run: clean.

### Coverage
- quality-runner reported overall 24% across requested modules: config_loader 100%, storage 24%, migrate 30%, models 86%.
- Informational only for this review because task 1473 changed durable tests, not production modules.

### Git Scope
- Builder commit was reconstructed from reflog as f8637c652fb79535f79006e4f7c1ddaafb257580 with message: test: align durable config tests to topology constants (#1473, builder).
- Exact dirty-tree contamination check could not be completed because terminal/git status access was unavailable in this review environment. Confidence deduction applied.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| All tests in the scoped config test files pass after aligning with the topology-constant refactor. | Scoped suite is green, but the current durable assertions no longer prove two live branches: (1) load_config still reads persisted integer next_id at serve/kanban/src/owlbear_kanban/config_loader.py:45-47, yet the scoped suite only proves the missing-file default at tests/test_config_loader.py:226-230; (2) tests/test_config_schema.py:339-345 now asserts successful load for mixed flat-plus-grouped YAML without schema even though BoardConfig still rejects that shape in serve/kanban/src/owlbear_kanban/models.py:232-249. | FAIL |

### Critical Findings
1. Missing proof for the remaining disk-owned loader branch. The implementation still reads a persisted integer next_id from config.yml at serve/kanban/src/owlbear_kanban/config_loader.py:45-47, but the scoped suite has no non-default load assertion. The only loader next_id check is the missing-file default at tests/test_config_loader.py:226-230, so a regression that hardcodes next_id to 1 would stay green.
2. A durable negative-path test was converted into a green-path assertion without preserving the live rejection branch. tests/test_config_schema.py:339 still names test_mixed_flat_and_grouped_without_schema_raises_config_error, but the body at tests/test_config_schema.py:342-345 now asserts successful load. The mixed flat-plus-grouped rejection still exists in serve/kanban/src/owlbear_kanban/models.py:232-249, so this change removed meaningful proof rather than replacing it.

### Additional Notes
- Save-path assertions do correctly match the current writer contract: serve/kanban/src/owlbear_kanban/storage.py:224-236 persists next_id only, and the scoped save tests assert next_id-only output at tests/test_config_authority.py:303-343 and tests/test_config_schema.py:410-446.
- Several durable headers/docstrings are now stale relative to the asserted contract, especially tests/test_config_schema.py:9-15 and tests/test_config_authority.py:12-17. This supports the proof-quality concern but is not the primary blocker.

### Deductions
- 0.08 missing discriminating proof for persisted next_id load branch.
- 0.09 lost proof for mixed flat-plus-grouped rejection path.
- 0.03 dirty-tree contamination check unavailable because git status could not be executed.
- 0.02 no direct commit diff available; file ownership reconstructed from task body plus reflog.

### Verdict
- Confidence: 0.78
- FAIL. Implementation appears stable, but the durable test contract is not strong enough to approve.
- Action: reject to todo for test-writer strengthening.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a discriminating loader test that writes a non-default integer next_id to config.yml and proves load_config returns that persisted value. | tests/test_config_loader.py | Live branch remains at serve/kanban/src/owlbear_kanban/config_loader.py:45-47; current scoped proof only covers default path at tests/test_config_loader.py:226-230. |
| 2 | test-writer | Restore coverage for mixed flat-plus-grouped input without schema by directly exercising the rejection path, or split/rename the durable tests so both the success case and the rejection case are explicitly proven. | tests/test_config_schema.py, serve/kanban/src/owlbear_kanban/models.py | Current test name still claims raises_config_error at tests/test_config_schema.py:339, but body now asserts success at tests/test_config_schema.py:342-345 while rejection logic still exists at serve/kanban/src/owlbear_kanban/models.py:232-249. |
| 3 | test-writer | Update stale durable test headers/docstrings so each TestFromAC section describes the contract it now enforces. | tests/test_config_authority.py, tests/test_config_schema.py | Current file-level AC text still describes grouped save output and root statuses/priorities at tests/test_config_schema.py:9-15 and tests/test_config_authority.py:12-17, but bodies assert next_id-only persistence. |
[[2026-05-09]]
## Test-Writer Notes
- Retry: Step 1b — reviewer cited 2 proof gaps + 1 docstring concern. All addressed.

### Changes made
- **tests/test_config_loader.py**: Added `test_load_config_reads_persisted_next_id` to `TestFromAC_LoadConfigRegression` — writes `next_id: 42` to config.yml, proves `load_config` returns `config.next_id == 42` (closes gap 1: only the missing-file default was previously proven).
- **tests/test_config_schema.py**: Renamed `test_mixed_flat_and_grouped_without_schema_raises_config_error` → `test_load_config_mixed_flat_and_grouped_without_schema_returns_product_topology` (name now matches the body's success assertion); added `test_model_validate_mixed_flat_and_grouped_without_schema_raises_config_error` that directly calls `BoardConfig.model_validate` on mixed YAML and asserts `ConfigError(code="ERR_INVALID_STATUS")` (closes gap 2: rejection path in models.py:232-249 now explicitly proven). Updated file-header AC5 and AC8 comments to reflect current topology-constant behavior.
- **tests/test_config_authority.py**: Updated file-header AC4/AC5 descriptions and `TestFromAC_SaveConfigRootOnly` class docstring to reflect that `save_config` writes only `next_id`, not `statuses/priorities` (closes gap 3).

### Verdict: Step 1b.1 — all new tests PASS
- Both new tests pass against current code: `load_config` at config_loader.py:45-47 already reads `next_id`; `BoardConfig._normalise_legacy` at models.py:248-254 already raises `ConfigError` for mixed flat+grouped.
- No implementation work needed. Advancing directly to `review`.

### Quality evidence
- Scoped run: 93 passed, 0 failed (up from 91). Ruff: clean.
- Commit: 3a7c9519 — test: add proof-gap tests for persisted next_id and mixed-shape rejection (#1473, test-writer)
[[2026-05-09]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified task body indicates test-writer pass-through context for builder.
- Passing through to review.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped run: 93 passed, 0 failed, 0 skipped across [tests/test_config_loader.py](tests/test_config_loader.py), [tests/test_config_authority.py](tests/test_config_authority.py), [tests/test_config_schema.py](tests/test_config_schema.py), and [tests/test_config_grouped.py](tests/test_config_grouped.py).

### Lint Results
- quality-runner scoped ruff run: clean.

### Coverage
- quality-runner reported overall 24% across requested modules: [serve/kanban/src/owlbear_kanban/config_loader.py](serve/kanban/src/owlbear_kanban/config_loader.py) 100%, [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py) 86%, [serve/kanban/src/owlbear_kanban/migrate.py](serve/kanban/src/owlbear_kanban/migrate.py) 30%, [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py) 24%.
- Informational only for this review because task 1473 changed durable tests, not production modules.

### Git Scope
- Task-related commits were confirmed in reflog: builder `f8637c652fb79535f79006e4f7c1ddaafb257580` (`test: align durable config tests to topology constants (#1473, builder)`) and test-writer `3a7c9519e41a271108c30253cf4e34e2a38bd110` (`test: add proof-gap tests for persisted next_id and mixed-shape rejection (#1473, test-writer)`).
- Exact dirty-tree contamination check could not be completed in this review environment because terminal/git status access is unavailable. Confidence deduction applied.
- No direct commit diff was available; changed-file scope was reconstructed from task notes, reflog confirmation, and current file inspection.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All tests in the scoped config test files pass after aligning with the topology-constant refactor. | quality-runner proved the scoped command is green (93 passed, 0 failed, 0 skipped, ruff clean). The prior proof gaps are now closed by a persisted `next_id` load proof at [tests/test_config_loader.py](tests/test_config_loader.py#L232) and [tests/test_config_loader.py](tests/test_config_loader.py#L240) against the live loader branch at [serve/kanban/src/owlbear_kanban/config_loader.py](serve/kanban/src/owlbear_kanban/config_loader.py#L45) and [serve/kanban/src/owlbear_kanban/config_loader.py](serve/kanban/src/owlbear_kanban/config_loader.py#L46); mixed flat-plus-grouped behavior is now proven on both paths by the load path at [tests/test_config_schema.py](tests/test_config_schema.py#L343) and [tests/test_config_schema.py](tests/test_config_schema.py#L349) plus the direct rejection path at [tests/test_config_schema.py](tests/test_config_schema.py#L351) and [tests/test_config_schema.py](tests/test_config_schema.py#L362) against the live rejection branch at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L255); next_id-only save behavior is still pinned by [tests/test_config_authority.py](tests/test_config_authority.py#L304), [tests/test_config_authority.py](tests/test_config_authority.py#L312), [tests/test_config_authority.py](tests/test_config_authority.py#L314), and [tests/test_config_authority.py](tests/test_config_authority.py#L322) against [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L236). | [tests/test_config_loader.py](tests/test_config_loader.py#L232), [tests/test_config_schema.py](tests/test_config_schema.py#L343), [tests/test_config_schema.py](tests/test_config_schema.py#L351), [tests/test_config_authority.py](tests/test_config_authority.py#L304) | PASS |

### Critical Checks
- Test-writer audit: PASS. The retry closed the persisted-`next_id` and mixed-shape proof gaps with discriminating assertions.
- Test integrity: PASS with minor confidence deduction. No weakening is visible in the current `TestFromAC_*` bodies, but exact immutability versus the original revision could not be proven without a direct diff.
- Security review: PASS. No shell, traversal, secret, or unsafe-deserialization issue appears in scope.
- Data safety: PASS. Test state is local to temp board directories and bounded YAML fixtures.
- Test quality: PASS with deduction. Executable assertions are discriminating and branch-complete for task scope. Remaining stale pytest-visible identifiers are traceability debt rather than a blocking proof gap.

### Additional Notes
- Stale identifiers/headings remain in [tests/test_config_loader.py](tests/test_config_loader.py#L132), [tests/test_config_loader.py](tests/test_config_loader.py#L145), [tests/test_config_loader.py](tests/test_config_loader.py#L226), [tests/test_config_authority.py](tests/test_config_authority.py#L304), [tests/test_config_authority.py](tests/test_config_authority.py#L314), [tests/test_config_schema.py](tests/test_config_schema.py#L420), [tests/test_config_schema.py](tests/test_config_schema.py#L427), [tests/test_config_schema.py](tests/test_config_schema.py#L435), [tests/test_config_schema.py](tests/test_config_schema.py#L444), and [tests/test_config_schema.py](tests/test_config_schema.py#L453). These names still describe legacy semantics even though the bodies now assert the topology-constant contract.
- This residual traceability issue is tracked as follow-up task `#1477` (`Normalize stale durable config test identifiers`) and is not treated as a blocking AC failure because the executable assertions themselves are now aligned and discriminating.

### Deductions
- 0.03 exact dirty-tree contamination check unavailable because terminal/git status access was not available in this review environment.
- 0.02 no direct commit diff available; file ownership was reconstructed from task notes plus reflog confirmation.
- 0.03 stale pytest-visible identifiers/headings remain in the durable suites; cleanup is tracked separately in `#1477`.

### Verdict
- Confidence: 0.91
- PASS. The retry closed the two substantive proof gaps from the prior review, the scoped suite is green, and the remaining identifier drift is non-blocking cleanup debt.
- Action: advance to docs; follow-up cleanup tracked in `#1477`.
[[2026-05-09]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only alignment task; no API, CLI, config, or package structure changes. |
| 2 | Module docstrings | No | N/A | No production modules modified. Both builder passes confirm no code changes. Docstring edits mentioned in builder notes are in test file headers, not production .py modules. |
| 3 | External attribution | No | N/A | No external patterns used. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | No | N/A | No production file changes; no diagram describes-match possible. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_config_loader.py | OUT | N/A (test file) |
| tests/test_config_authority.py | OUT | N/A (test file) |
| tests/test_config_schema.py | OUT | N/A (test file) |
| tests/test_config_grouped.py | OUT | N/A (test file) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1473-* scratch files found)
[[2026-05-09]]
## Audit\n### Regression Detection\n- quality-runner mode full: 2975 passed, 400 failed, 4 skipped. All 400 failures are pre-existing from parent topology refactor (#1439) — sampled failures in test_engine_validation_push, test_cockpit_cache_populate, test_cockpit_cache_sse_1346 are all outside task scope. Task #1473 modified only test expectations in 3 config test files — no production code changed, no cross-domain regression possible.\n- Scoped run: 93 passed, 0 failed across all 4 AC test files.\n- Lint: 12 violations, all outside task scope (knowledge/, tools/ packages).\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (changed files: tests/test_config_loader.py, tests/test_config_authority.py, tests/test_config_schema.py — all within kanban config test domain; test_config_grouped.py correctly left unchanged as already passing)\n- purpose match: PASS (test expectations aligned to topology-constant contract; proof gaps from first review closed by test-writer retry)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nSingle verifiable AC with concrete pytest command. Detailed file-specific guidance and 4 breaking-change items provided substantial builder context. Reviewer's first rejection was about test proof quality (test-writer territory), not AC ambiguity. Minor gap: AC could have specified discriminating test requirements explicitly.\n\n### Commit Integrity\n- upstream commit presence: PASS (f8637c6 builder, 3a7c951 test-writer — both confirmed via git log --grep, both scoped to task test files only)\n- dirty-tree contamination: PASS (git status verified ~30 modified files, none overlapping with task's 3 changed test files)\n- kanban commit packaging: pending (auditor commits kanban state post-archive)\n\n### Deduction Breakdown\nNo deductions applied.\n- Pre-existing failures (400): not caused by task — parent topology refactor; no regression deduction.\n- Lint violations (12): outside task scope; no deduction.\n- AC quality 4/5 (>3): no deduction.\n- Reviewer evidence: detailed with PASS verdict; no deduction.\n- Commit integrity: both commits present and scoped; no deduction.\n\n### Confidence: 1.00\n### Action: archive