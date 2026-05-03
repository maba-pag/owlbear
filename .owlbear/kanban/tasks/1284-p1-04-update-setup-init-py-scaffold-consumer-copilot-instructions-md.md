---
id: 1284
title: 'P1-04: Update setup/init.py — scaffold consumer copilot-instructions.md'
status: review
priority: needed
created: 2026-05-02T16:01:10.625508+00:00
updated: 2026-05-03T13:22:16.552195+00:00
tags:
- phase-1
- scope:tools
- shared-layer
parent: 1280
depends_on:
- 1282
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] setup/init.py generates a `.github/copilot-instructions.md` for new consumer projects (td:1)
- [ ] Generated file contains a commented path-mapping section (project layout, source packages, frontend root, test paths) (td:1)
- [ ] Template uses concrete illustrative examples with comments indicating customization needed (td:1)
- [ ] Re-running init() on a project with a customized copilot-instructions.md preserves the existing file (td:1)
- [ ] Existing init.py functionality preserved — no regressions in other scaffolded files (td:0)
- [ ] Tests from #1281 pass for the init.py scaffold assertions (td:0)

## Scope

- IN: setup/init.py modification (add to `_SKIP_IF_EXISTS_REL`), seed/.github/copilot-instructions.md replacement
- OUT: Editing the OwlBear-dev copilot-instructions.md (#1282), cross-refs (#1283)

[[2026-05-03]]
## Research
- Research doc: .owlbear/research/init-scaffold-copilot-instructions.md
- Sources: 6 studied, 4 high-relevance (GitHub Blog 5 Tips, VS Code custom instructions docs, Graham Knapp real-world example, brief notation convention)
- Recommendation: Approach A — consumer scaffold template + skip-if-exists (confidence: 0.85)
- Follow-up tasks created: none (implementation is self-contained in #1284)
- Decision requests: none — T1 Autonomous

## Implementation Summary
Two changes needed:
1. Replace `seed/.github/copilot-instructions.md` with consumer-generic scaffold (Project Identity placeholder, Directory Structure table with illustrative examples and HTML comments, Tech Stack placeholder, Resources section)
2. Add `".github/copilot-instructions.md"` to `_SKIP_IF_EXISTS_REL` in `setup/init.py` (1 line — preserves consumer customizations on re-init, follows existing pattern for .editorconfig etc.)

No placeholder replacement needed (template is generic). All #1281 AC4 tests pass with any template that has `## Directory Structure` heading + table rows.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One change: scaffold consumer copilot-instructions.md + skip-if-exists |
| Interface clarity | PASS | AC specifies file content requirements and preservation behavior |
| Dependency correctness | PASS | #1282 archived (done); #1281 tests exist |
| Module layering | PASS | No new imports; 1 line in frozenset + seed file replacement |
| TDD compliance | PASS | #1281 tests cover scaffold assertions; AC4 (new) adds skip-if-exists coverage gap |
| KISS/YAGNI | PASS | Minimal: 1 seed file + 1 line in `_SKIP_IF_EXISTS_REL` |
| Premise challenge | PASS | Current seed is OwlBear-specific; consumers need generic scaffold |
| Pattern consistency | PASS | Follows existing `_SKIP_IF_EXISTS_REL` pattern (`.editorconfig`, `.gitattributes`, etc.) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:tools only |

### Challenge Results
- Challenger: reconsider (0.68)
- Challenges: (1) AC2/AC3 test coverage gap — existing #1281 tests check heading+rows not comments/examples; (2) skip-if-exists had no explicit AC line; (3) regression surface broader than cited evidence
- Architect response: accepted concerns (1) and (2) — added AC4 for skip-if-exists preservation, annotated test depths so test-writer adds deeper assertions for AC2/AC3. Concern (3) is handled by td:0 on AC5 (full suite run). Architecture itself is sound.

### Test Depth
- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC — added explicit skip-if-exists AC line (AC4), annotated all lines with test depth. Advancing to todo.
[[2026-05-03]]
## Architecture Review

Refined AC: added explicit skip-if-exists AC line (AC4: "Re-running init() on a project with a customized copilot-instructions.md preserves the existing file"), annotated all AC lines with test depth (4×td:1, 2×td:0). Challenger returned reconsider at 0.68 on test-coverage gaps — accepted concerns (1) and (2), addressed by AC refinement and test-depth routing. Architecture sound: follows existing `_SKIP_IF_EXISTS_REL` pattern, single domain, minimal scope (1 seed file + 1 line).

Verdict: APPROVE → todo
[[2026-05-03]]
## Test-Writer Notes
- Test file: tests/test_init_scaffold_1284.py
- Classes: TestFromAC_ConsumerScaffoldGeneration, TestFromAC_CommentedPathMappingSection, TestFromAC_IllustrativeExamples, TestFromAC_SkipIfExistsPreservation
- Tests per category: happy 0, edge 0, error 0, boundary 0 (all are smoke/contract tests per td:1 depth)
- Total: 8 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (td:1) — consumer-generic scaffold | test_generated_file_is_consumer_generic | FAIL ✓ |
| AC2 (td:1) — HTML commented path-mapping section | test_has_html_comments_in_template, test_directory_section_has_source_package_entry, test_directory_section_has_frontend_entry | FAIL ✓ |
| AC3 (td:1) — illustrative examples + customization comments | test_has_customization_instruction_comment, test_directory_section_uses_generic_example_paths | FAIL ✓ |
| AC4 (td:1) — skip-if-exists preserves customized file | test_preserves_customized_file_on_reinit, test_skip_if_exists_constant_includes_copilot_instructions | FAIL ✓ |
| AC5 (td:0) — no regressions | skipped per td:0 | — |
| AC6 (td:0) — #1281 tests pass | skipped per td:0 | — |

Failure modes: all 8 fail against current seed (OwlBear-dev-specific template, no HTML comments, no `src/`/`frontend/` entries, `.github/copilot-instructions.md` not in `_SKIP_IF_EXISTS_REL`).
[[2026-05-03]]
## Builder Notes
- Implementation: updated setup/init.py and seed/.github/copilot-instructions.md
- Fixes applied:
  - Added `.github/copilot-instructions.md` to `_SKIP_IF_EXISTS_REL` so re-init preserves existing customized consumer instructions.
  - Replaced seed copilot instructions template with a consumer-generic scaffold including HTML customization comments and path-mapping examples (`src/`, `frontend/`/`web/`, `tests/`).
- Tests: 8/8 TestFromAC tests passed in tests/test_init_scaffold_1284.py
- Coverage: N/A (task tests dynamically load setup/init.py via importlib exec_module; pytest-cov reports no data for this execution path)
- Lint: ruff clean for setup/init.py and tests/test_init_scaffold_1284.py
- Module-level durable test file: none found for this module pattern (`tests/test_init.py` not present)
- Commit: f30454af (`feat: scaffold consumer copilot instructions (#1284, builder)`)

### Reflection
- Dynamic import test architecture can block coverage instrumentation despite green tests.
- Keeping scaffold content generic in seed templates avoids leaking OwlBear-internal assumptions into consumer repos.
- Skip-if-exists lists are a reliable way to preserve user-customized project files on re-init.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped run (`tests/test_init_scaffold_1284.py`, `tests/test_neutral_shared_1281.py`): 18 passed, 0 failed, 0 skipped
- quality-runner regression run (`tests/test_setup_init_settings.py`, `tests/test_setup_init_hook_conflicts.py`, `tests/test_core_removal_1297.py`): 22 passed, 0 failed, 0 skipped

### Lint
- quality-runner scoped lint (`setup/init.py`, `tests/test_init_scaffold_1284.py`, `tests/test_neutral_shared_1281.py`): clean

### Coverage
- quality-runner reported `setup` at 71% overall and noted dynamic-import/no-data limitations for `setup/init.py`
- Diff-scoped changed behavior is still directly exercised: `_SKIP_IF_EXISTS_REL` membership and the skip-if-exists branch both run under `test_preserves_customized_file_on_reinit` / `test_skip_if_exists_constant_includes_copilot_instructions`

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — setup/init.py generates a `.github/copilot-instructions.md` for new consumer projects | `test_generated_file_is_consumer_generic`; inherited `test_generates_copilot_instructions` | Yes — missing file or OwlBear-dev branding would fail | COVERED |
| AC2 — generated file contains a commented path-mapping section covering project layout, source packages, frontend root, test paths | `test_has_html_comments_in_template`, `test_directory_section_has_source_package_entry`, `test_directory_section_has_frontend_entry`, inherited directory-section/table-row checks | No — if `tests/` and `tests/e2e/` entries were removed while comments, `src/`, and frontend rows remained, all mapped tests would still pass | MISSING |
| AC3 — template uses concrete illustrative examples with comments indicating customization needed | `test_has_customization_instruction_comment`, `test_directory_section_uses_generic_example_paths`, plus AC2 source/frontend assertions | Yes — removing customization comments or reverting to OwlBear-specific directory examples would fail | COVERED |
| AC4 — re-running init() preserves an existing customized file | `test_preserves_customized_file_on_reinit`, `test_skip_if_exists_constant_includes_copilot_instructions` | Yes — overwrite or missing skip-set entry would fail | COVERED |
| AC5 — existing init.py functionality preserved | Regression suites `tests/test_setup_init_settings.py`, `tests/test_setup_init_hook_conflicts.py`, `tests/test_core_removal_1297.py` | Yes — existing scaffold/settings/hook behavior regressions would fail | PASS |
| AC6 — tests from #1281 pass for the init.py scaffold assertions | `tests/test_neutral_shared_1281.py` in scoped quality-runner run | Yes — scoped run was green | PASS |

#### Security Review
- No issues found in the builder diff (`setup/init.py`, `seed/.github/copilot-instructions.md`): no new inputs, no secrets, no shelling out, no deserialization, no path-traversal surface added.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` in `tests/test_init_scaffold_1284.py` | No builder changes detected; builder commit `f30454af` touched only `seed/.github/copilot-instructions.md` and `setup/init.py` | PRESERVED |

#### Test Quality
- Assertion specificity is ADEQUATE for AC1, AC3, and AC4.
- AC2 is WEAK/MISSING at the named `test paths` dimension: the suite proves comments, `src/`, and frontend examples, but not explicit test-path entries.

#### Data Safety
- No issues found. Change is static template content plus an existing skip-if-exists pattern.

#### Implementation-Aware Test Gap Analysis
- Current implementation does include test-path examples in `seed/.github/copilot-instructions.md` (`tests/`, `tests/e2e/`).
- The gap is proof, not code: no task-scoped or inherited test asserts those entries are present in the directory section.

#### Necessity Check
- Not applicable. No new dependency, tool, or integration added.

#### Builder Process Quality
- CLEAN: one builder pass, one commit, scoped diff only.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `setup/init.py` writes seed files during `init()`; generated scaffold is exercised by the scoped run; template is consumer-generic in `seed/.github/copilot-instructions.md` | `test_generated_file_is_consumer_generic`; inherited `test_generates_copilot_instructions` | PASS |
| AC2 | Template directory section contains comments and rows for `src/`, frontend/web, and test paths in `seed/.github/copilot-instructions.md`, but mapped tests only assert comments/source/frontend plus generic table rows | `test_has_html_comments_in_template`, `test_directory_section_has_source_package_entry`, `test_directory_section_has_frontend_entry`, inherited directory-row tests | FAIL |
| AC3 | HTML customization comments and generic illustrative examples are present in `seed/.github/copilot-instructions.md`; scoped tests enforce comment/customization and generic-path expectations | `test_has_customization_instruction_comment`, `test_directory_section_uses_generic_example_paths` | PASS |
| AC4 | `_SKIP_IF_EXISTS_REL` contains `.github/copilot-instructions.md` and `init()` skips existing files at the generic skip-if-exists branch in `setup/init.py` | `test_preserves_customized_file_on_reinit`, `test_skip_if_exists_constant_includes_copilot_instructions` | PASS |
| AC5 | Existing init-related regression suites remained green in reviewer-run quality evidence | `tests/test_setup_init_settings.py`, `tests/test_setup_init_hook_conflicts.py`, `tests/test_core_removal_1297.py` | PASS |
| AC6 | Reviewer-run scoped quality pass on `tests/test_neutral_shared_1281.py` was green | `tests/test_neutral_shared_1281.py` | PASS |

### Deductions
- -0.12: AC2 proof gap. The named `test paths` requirement is not covered by a discriminating assertion.

### Verdict
- FAIL -> todo
- Confidence: 0.88

### Action
- Return to test-writer to add a discriminating AC2 assertion for explicit test-path entries in the generated directory section (for example `tests/` and/or `tests/e2e/`).
- Builder changes appear correct; no source-code fix required at this stage.

### Reflection
- Compound AC lines with named dimensions need at least one assertion per named dimension or an equivalent exact-match assertion.
- Inherited “directory section exists” tests are useful regression coverage but do not prove newly added named dimensions like test paths.
- Scoped init regression suites are a better AC5 signal than a repo-wide red baseline when unrelated tasks are active.
[[2026-05-03]]
## Test-Writer Notes
- Retry: added 1 test for reviewer gap (AC2 test-path dimension).
- Builder skip: test-only retry — new test passes against current implementation.

### Change
- Added `test_directory_section_has_test_path_entry` to `TestFromAC_CommentedPathMappingSection` in `tests/test_init_scaffold_1284.py`.
- Asserts `tests/` appears in the directory section of the generated copilot-instructions.md (AC2 fourth dimension: test paths).

### Evidence
- pytest `tests/test_init_scaffold_1284.py`: **9 passed, 0 failed** (1 new test included)
- ruff `tests/test_init_scaffold_1284.py`: clean
- Implementation already contains `tests/` and `tests/e2e/` in `seed/.github/copilot-instructions.md` — proof gap only, no code fix needed.

### AC Coverage
| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (td:1) | test_generated_file_is_consumer_generic | PASS ✓ |
| AC2 (td:1) — all 4 dimensions | test_has_html_comments_in_template, test_directory_section_has_source_package_entry, test_directory_section_has_frontend_entry, **test_directory_section_has_test_path_entry (new)** | PASS ✓ |
| AC3 (td:1) | test_has_customization_instruction_comment, test_directory_section_uses_generic_example_paths | PASS ✓ |
| AC4 (td:1) | test_preserves_customized_file_on_reinit, test_skip_if_exists_constant_includes_copilot_instructions | PASS ✓ |
| AC5 (td:0) | skipped per td:0 | — |
| AC6 (td:0) | skipped per td:0 | — |
[[2026-05-03]]
## Builder Notes
- Implementation: no additional builder code changes required in this retry pass.
- Files changed in this pass: none.
- Test evidence (quality-runner scoped): 19 passed, 0 failed, 0 skipped (`tests/test_init_scaffold_1284.py`, `tests/test_neutral_shared_1281.py`).
- Regression evidence (quality-runner scoped): 22 passed, 0 failed, 0 skipped (`tests/test_setup_init_settings.py`, `tests/test_setup_init_hook_conflicts.py`, `tests/test_core_removal_1297.py`).
- Lint: ruff clean for `setup/init.py` and scoped test files.
- Coverage: `setup` reported 71% in scoped run; regression slice reported no-data for setup import path. No new implementation changes in this pass.
- Evidence summary: AC2 test-path proof gap is now covered by test-writer retry and all scoped checks are green.

### Reflection
- Test-only retry flow worked as intended: no builder code churn, only evidence re-validation.
- Keeping verification scoped avoided unrelated-suite noise while still proving AC5 with targeted init regressions.
- Coverage signals for dynamically loaded setup paths remain context-dependent; pass/fail confidence came from explicit functional assertions and green regression slice.