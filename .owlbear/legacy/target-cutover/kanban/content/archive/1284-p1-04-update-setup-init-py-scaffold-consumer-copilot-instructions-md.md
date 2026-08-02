---
id: 1284
title: 'P1-04: Update setup/init.py — scaffold consumer copilot-instructions.md'
status: archived
priority: medium
created: 2026-05-02T16:01:10.625508+00:00
updated: 2026-05-03T14:09:44.613465+00:00
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
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped run: 41 passed, 0 failed, 0 skipped
- Scope: `tests/test_init_scaffold_1284.py`, `tests/test_neutral_shared_1281.py`, `tests/test_setup_init_settings.py`, `tests/test_setup_init_hook_conflicts.py`, `tests/test_core_removal_1297.py`

### Lint
- quality-runner lint: clean for `setup/init.py`, `tests/test_init_scaffold_1284.py`, `tests/test_neutral_shared_1281.py`

### Coverage
- quality-runner coverage: `setup.init` 89% overall (156 statements, 17 missed)
- Non-blocking: changed behavior is directly exercised at `setup/init.py:53` and `setup/init.py:356` by `tests/test_init_scaffold_1284.py:231` and `tests/test_init_scaffold_1284.py:264`; template content at `seed/.github/copilot-instructions.md:11-22` is exercised by `tests/test_neutral_shared_1281.py:104`, `tests/test_neutral_shared_1281.py:149`, `tests/test_neutral_shared_1281.py:214`, `tests/test_init_scaffold_1284.py:91`, `tests/test_init_scaffold_1284.py:108`, `tests/test_init_scaffold_1284.py:126`, `tests/test_init_scaffold_1284.py:144`, `tests/test_init_scaffold_1284.py:173`, and `tests/test_init_scaffold_1284.py:201`

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — `setup/init.py` generates a `.github/copilot-instructions.md` for new consumer projects | `tests/test_neutral_shared_1281.py:149` (`test_generates_copilot_instructions`), `tests/test_init_scaffold_1284.py:56` (`test_generated_file_is_consumer_generic`) | Yes — missing generation or retained OwlBear-dev branding would fail | COVERED |
| AC2 — generated file contains a commented path-mapping section covering project layout, source packages, frontend root, and test paths | `tests/test_neutral_shared_1281.py:104` (`test_has_directory_structure_heading`), `tests/test_neutral_shared_1281.py:214` (`test_path_entry_within_directory_section`), `tests/test_init_scaffold_1284.py:91`, `:108`, `:126`, `:144` | Yes — removing the section, section-local path rows, HTML comments, `src/`, frontend entry, or test-path entry would fail. This closes the prior AC2 proof gap. | COVERED |
| AC3 — template uses concrete illustrative examples with comments indicating customization needed | `tests/test_init_scaffold_1284.py:173` (`test_has_customization_instruction_comment`), `tests/test_init_scaffold_1284.py:201` (`test_directory_section_uses_generic_example_paths`) | Yes — removing customization comments or reverting to OwlBear-specific examples would fail | COVERED |
| AC4 — re-running init() preserves an existing customized file | `tests/test_init_scaffold_1284.py:231`, `tests/test_init_scaffold_1284.py:264` | Yes — overwrite behavior or missing skip-set membership would fail | COVERED |
| AC5 — existing `init.py` functionality preserved | quality-runner regression slice on `tests/test_setup_init_settings.py`, `tests/test_setup_init_hook_conflicts.py`, `tests/test_core_removal_1297.py` | Yes — targeted init/scaffold regressions would fail | PASS |
| AC6 — tests from #1281 pass for the init.py scaffold assertions | quality-runner scoped run includes `tests/test_neutral_shared_1281.py` | Yes — the inherited scaffold suite was green | PASS |

#### Security Review
- No issues found. Builder diff (`git diff --name-only f30454af~1 f30454af`) touched only `seed/.github/copilot-instructions.md` and `setup/init.py`; no new input surface, secrets, shell execution, traversal, or deserialization was added.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` in `tests/test_init_scaffold_1284.py` | Builder commit `f30454af` touched only `seed/.github/copilot-instructions.md` and `setup/init.py`; retry added one new test-path assertion via test-writer | PRESERVED |

#### Test Quality
- AC2 is now STRONG/ADEQUATE for td:1 scope: section heading + section-local path-row proof from `tests/test_neutral_shared_1281.py:104` / `:214`, plus dimension-specific assertions in `tests/test_init_scaffold_1284.py:91`, `:108`, `:126`, and `:144`.
- AC1, AC3, and AC4 use discriminating assertions: absence of generation, retained OwlBear branding, missing customization comments, or overwrite behavior would fail the suite.

#### Data Safety
- No issues found. Change is static scaffold content plus an existing skip-if-exists control path.

#### Implementation-Aware Test Gap Analysis
- No significant untested path remains in the diff.
- `_SKIP_IF_EXISTS_REL` membership at `setup/init.py:53` and the skip-if-exists branch at `setup/init.py:356` are directly exercised.
- The generated template’s Directory Structure section and customization comments are directly asserted at `seed/.github/copilot-instructions.md:9`, `:11`, `:13`, `:14`, `:18`, `:20`, `:21`, `:22`, `:27`, `:38`, and `:46`.

#### Necessity Check
- Not applicable. No new dependency, tool, or integration added.

#### Builder Process Quality
- CLEAN: one implementation pass (`f30454af`) followed by a test-only retry that used the builder-skip path correctly; no redundant source churn.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `setup/init.py:356` still seeds missing files; generated file existence is proven by `tests/test_neutral_shared_1281.py:149`; consumer-generic output is enforced by `tests/test_init_scaffold_1284.py:56` | `test_generates_copilot_instructions`, `test_generated_file_is_consumer_generic` | PASS |
| AC2 | `seed/.github/copilot-instructions.md:11-22` contains the Directory Structure section, HTML comments, source/frontend/test-path rows; section-local proof comes from `tests/test_neutral_shared_1281.py:104` / `:214` and dimension checks from `tests/test_init_scaffold_1284.py:91`, `:108`, `:126`, `:144` | `test_has_directory_structure_heading`, `test_path_entry_within_directory_section`, `test_has_html_comments_in_template`, `test_directory_section_has_source_package_entry`, `test_directory_section_has_frontend_entry`, `test_directory_section_has_test_path_entry` | PASS |
| AC3 | Customization comments exist at `seed/.github/copilot-instructions.md:9`, `:27`, `:38`, `:46`; generic illustrative paths remain at `seed/.github/copilot-instructions.md:18-22` | `test_has_customization_instruction_comment`, `test_directory_section_uses_generic_example_paths` | PASS |
| AC4 | `_SKIP_IF_EXISTS_REL` includes the path at `setup/init.py:53`, and `init()` skips overwrite at `setup/init.py:356` when the destination already exists | `test_preserves_customized_file_on_reinit`, `test_skip_if_exists_constant_includes_copilot_instructions` | PASS |
| AC5 | Fresh regression slice was green on `tests/test_setup_init_settings.py`, `tests/test_setup_init_hook_conflicts.py`, `tests/test_core_removal_1297.py` | quality-runner regression slice | PASS |
| AC6 | Fresh scoped run was green on `tests/test_neutral_shared_1281.py` | quality-runner scoped run | PASS |

### Deductions
- -0.02: `setup.init` reports 89% overall module coverage, below the generic 90% module-level heuristic, but the changed lines and template contract are directly exercised. Treated as informational/diff-scoped non-blocking.

### Verdict
- PASS -> docs
- Confidence: 0.96

### Action
- Advance to docs.

### Reflection
- Compound AC lines are only reviewer-safe when each named dimension has either a dedicated assertion or an equivalent exact-match proof.
- Section-local assertions matter for markdown scaffolds; file-global string presence can hide false greens.
- For narrow setup/init changes, targeted regression slices are a better signal than broad workspace baselines when unrelated suites are active.
[[2026-05-03]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `setup/setup-guide.md` "What Setup Creates" table missing `.github/copilot-instructions.md` row — added with purpose + idempotency columns |
| 2 | Module docstrings | Yes | N/A | `setup/init.py` `init()` docstring is accurate; no new public functions/classes added |
| 3 | External attribution | Yes | N/A | `sources/overview.md` already contains `## Init.py Consumer Scaffold (Task #1284)` section with 4 entries (GitHub Blog, VS Code docs, Graham Knapp, brief notation convention) |
| 4 | Research doc | Yes | Verified | `.owlbear/research/init-scaffold-copilot-instructions.md` exists; linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` describes `setup/**` — footer updated from `8e442bdc` → `7cca18fa` (2026-05-03) |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; `seed/.github/copilot-instructions.md` was replaced/updated, not deleted |

### Scope Classification

- `setup/init.py` — Python source (docstrings IN scope); `seed/.github/copilot-instructions.md` — seed template (OUT scope for doc-writer edits); `tests/test_init_scaffold_1284.py` — test file (OUT scope)
- IN-scope docs affected: `setup/setup-guide.md` (Item 1), `share/diagrams/project-overview.excalidraw` (Item 5)

### Files Updated

- `setup/setup-guide.md` — added `.github/copilot-instructions.md` row to "What Setup Creates" table
- `share/diagrams/project-overview.excalidraw` — footer updated to `2026-05-03 (7cca18fa)`

### Commit

`58d58ced` — docs: update setup-guide and diagram for copilot-instructions scaffold (#1284, doc-writer)

### Child Tasks

None.

### Scratch Files

None found for `1284-*`.
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — generates copilot-instructions.md | `seed/.github/copilot-instructions.md` exists, consumer-generic content confirmed; `setup/init.py:356` seeds it | PASS |
| AC2 — commented path-mapping section | HTML comments at `seed/.github/copilot-instructions.md:13-14`, Directory Structure heading at `:12`, table rows for `src/`, `frontend/`/`web/`, `tests/`, `tests/e2e/` | PASS |
| AC3 — illustrative examples + customization comments | HTML comments throughout template, generic paths (no OwlBear-specific content) | PASS |
| AC4 — skip-if-exists preserves customized file | `_SKIP_IF_EXISTS_REL` includes `.github/copilot-instructions.md` at `setup/init.py:53` | PASS |
| AC5 — no regressions | Reviewer regression slice green (22 passed); full suite 3797 passed, 130 failed — all failures in unrelated modules (config migration, storage, SSE) | PASS |
| AC6 — #1281 tests pass | Reviewer scoped run included `tests/test_neutral_shared_1281.py` green | PASS |

### Test Results
- pytest (full suite): 3797 passed, 130 failed, 4 skipped — 0 failures in task scope
- ruff: clean for `setup/init.py`, `tests/test_init_scaffold_1284.py`
- vitest (frontend): 80 passed, 814 failed — all failures in unrelated components (ActivityTab, hooks)

### Architect Quality: 4/5
AC was specific enough for the reviewer to identify a sub-dimension gap (AC2 test-paths) and reject. Challenger caught missing skip-if-exists at 0.68 — architect refined by adding AC4 and test-depth annotations. Solid but required one iteration.

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 verified) → 0
- Lint violations: 0 → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (present, detailed, two cycles) → 0
- Task-scope test failures: 0 → 0

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 03ff6de4 | test | tests/test_init_scaffold_1284.py | #1284 |
| f30454af | feat | setup/init.py, seed/.github/copilot-instructions.md | #1284 |
| 58d58ced | docs | setup/setup-guide.md, share/diagrams/project-overview.excalidraw | #1284 |