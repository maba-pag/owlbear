---
id: 938
title: Add OwlBear frontend anti-pattern taxonomy
status: archived
priority: nice-to-have
created: 2026-03-22T04:41:32.4213438+01:00
updated: 2026-03-25T06:39:05.0717402+01:00
started: 2026-03-25T06:38:14.3946758+01:00
completed: 2026-03-25T06:38:14.3946758+01:00
tags:
    - ui
    - agent
    - scope:copilot
    - docs
    - type:docs
parent: 929
depends_on:
    - 934
class: standard
---

## Context

Curate a reusable anti-pattern reference derived from docs/research/impeccable-design-skills.md that separates universal blockers from taste-specific heuristics, so OwlBear can avoid AI-slop without turning taste into hard law.

## Acceptance Criteria

1. Create .github/skills/frontend-design/references/anti-patterns.md with two top-level sections:
   - **Universal Blockers**: expand each of the 9 existing items from SKILL.md's quick-check list with a WCAG SC citation (or documented usability source) and a one-line rationale
   - **Taste Heuristics**: illustrative AI-slop signature examples across at least 5 categories (typography, color, layout, visual, motion); frame as warnings, not bans

2. Add a row to the SKILL.md reference table (after the ux-writing row) linking references/anti-patterns.md for anti-pattern classification: universal blockers vs. taste heuristics

3. Include an attribution header in anti-patterns.md that references NOTICE.md and credits Impeccable and Anthropic where structure or content is adapted

4. Update _EXPECTED_REFERENCE_FILES in tests/test_frontend_design_skill.py to include anti-patterns.md

5. Update TestFromAC_ScopeBoundary::test_skill_package_has_no_anti_pattern_taxonomy: this was a #934 scope boundary guard that #938 legitimately supersedes; either remove or rewrite to reflect the new scope

6. anti-patterns.md must have at least 20 non-empty lines (existing test_reference_files_have_substantial_content applies automatically)

7. All tests/test_frontend_design_skill.py tests pass after updates

8. Ruff clean on all changed files

### Files touched

- .github/skills/frontend-design/references/anti-patterns.md (new)
- .github/skills/frontend-design/SKILL.md (add reference table row)
- tests/test_frontend_design_skill.py (update expected files + scope test)

### Patterns to follow

- Match existing reference file style (headers, bullet points, concrete examples)
- The 9 universal blockers already live in SKILL.md Universal Blockers section; the reference file expands them with citations but does not replace the quick-check list
- Research: docs/research/frontend-anti-pattern-taxonomy.md section 4 (Content Design)

### Dependencies

- #934 (archived): skill package exists

## Research

Research complete. See docs/research/frontend-anti-pattern-taxonomy.md.

[[2026-03-24]] Tue 00:35

## Architecture Review

**Verdict:** APPROVED (after refine + merge)

### AC Assessment

[[2026-03-24]] Tue 01:46

## Test-Writer Notes

- Test file: tests/test_frontend_design_skill.py

- Classes modified/added: _EXPECTED_REFERENCE_FILES (updated), TestFromAC_ScopeBoundary (1 test rewritten), TestFromAC_AntiPatternTaxonomy (new, 17 tests)

- Tests per category: happy 4, edge 2, error 0, boundary 3, content-contract 11

- Total: 20 FAIL, 31 PASS (31 existing tests preserved) FAIL count = 20

- ruff: clean

- AC coverage:

  AC1 file+structure: test_anti_patterns_file_exists, test_anti_patterns_has_universal_blockers_section, test_anti_patterns_has_taste_heuristics_section, test_universal_blockers_section_precedes_taste_heuristics

  AC1 blockers: test_universal_blockers_have_wcag_or_source_citations, test_universal_blockers_covers_all_9_items

  AC1 heuristics: test_taste_heuristics_covers_typography_category, test_taste_heuristics_covers_color_category, test_taste_heuristics_covers_layout_category, test_taste_heuristics_covers_visual_category, test_taste_heuristics_covers_motion_category

  AC2: test_skill_md_links_to_anti_patterns, test_skill_md_anti_patterns_row_after_ux_writing_row

  AC3: test_anti_patterns_attribution_references_notice, test_anti_patterns_attribution_credits_impeccable, test_anti_patterns_attribution_credits_anthropic

  AC4: _EXPECTED_REFERENCE_FILES now includes anti-patterns.md (triggers existing test_all_seven_reference_files_exist + test_skill_links_to_all_seven_reference_files to FAIL)

  AC5: test_skill_package_has_no_anti_pattern_taxonomy -> rewritten as test_skill_package_includes_anti_pattern_taxonomy (FAIL)

  AC6: test_anti_patterns_has_at_least_20_non_empty_lines

  AC7: all 31 pre-existing tests still PASS

[[2026-03-24]] Tue 03:35

## Builder Notes

- Files changed: .github/skills/frontend-design/SKILL.md; .github/skills/frontend-design/references/anti-patterns.md
- Tests: 51 passed (`uv run pytest tests/test_frontend_design_skill.py -q --tb=short`).
- Coverage: bare `--cov` scoped run passed (51 passed); repo-wide aggregate showed 2% because the run targeted a single test module.
- Lint: `uv run ruff check tests/test_frontend_design_skill.py` -> All checks passed.
- Evidence: Added a new anti-pattern taxonomy reference with Universal Blockers expanded using WCAG/NNGroup citations and Taste Heuristics examples across typography, color, layout, visual, and motion.
- Fixes applied: Added references/anti-patterns.md and inserted the reference table row in SKILL.md after ux-writing.md.

[[2026-03-24]] Tue 04:13

## Review Evidence

### Review: #938 - Add OwlBear frontend anti-pattern taxonomy

### Test Results

- `uv run pytest tests/test_frontend_design_skill.py -q --tb=short` -> 51 passed, 2 warnings (`qdrant_client` optional-dependency skips from `tests/conftest.py`).

### Lint Results

- `uv run ruff check .github/skills/frontend-design tests/test_frontend_design_skill.py` -> All checks passed.

### Coverage

- `uv run pytest tests/test_frontend_design_skill.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> 51 passed. Bare `--cov` reports repo-wide source totals, so the aggregate percentages are not meaningful for this docs-only task.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |

| --- | --- | --- | --- |

| AC1 sections, order, and 5 heuristic categories exist | `TestFromAC_AntiPatternTaxonomy` section/category tests at `tests/test_frontend_design_skill.py:421`, `:428`, `:435`, `:494`, `:502`, `:510`, `:518`, `:526` | Yes for missing sections/categories | COVERED |

| AC1 all 9 blockers have citations | `test_universal_blockers_have_wcag_or_source_citations` at `tests/test_frontend_design_skill.py:458` and `test_universal_blockers_covers_all_9_items` at `:469` | No. `:458` only checks for any `sc` or `wcag` or `nngroup` string anywhere in the file, and `:469` only checks for broad keywords anywhere in the file. A taxonomy with one citation and nine unlabeled bullets still passes. | LAX |

| AC1 all 9 blockers have one-line rationales | none | No. Search for `rationale` in `tests/test_frontend_design_skill.py` returns no matches, even though the implementation carries `Rationale:` lines at `.github/skills/frontend-design/references/anti-patterns.md:13`, `:16`, `:18`, `:21`, `:23`, `:26`, `:28`, `:32`, `:35`. | MISSING |

| AC1 Taste Heuristics are framed as warnings, not bans | none | No. Search for `warning|ban|prompts for review|automatic rejection` in `tests/test_frontend_design_skill.py` returns no matches. Rewriting `.github/skills/frontend-design/references/anti-patterns.md:39` and `:67` as hard bans would still leave the suite green. | MISSING |

| AC2 SKILL.md row links `references/anti-patterns.md` after `ux-writing.md` | `tests/test_frontend_design_skill.py:544` and `:551`; implementation at `.github/skills/frontend-design/SKILL.md:37-38` | Yes | COVERED |

| AC3 attribution header references NOTICE and credits Impeccable plus Anthropic | `tests/test_frontend_design_skill.py:566`, `:574`, `:581`; implementation at `.github/skills/frontend-design/references/anti-patterns.md:2-4` | Yes | COVERED |

| AC4 and AC5 test-file updates exist in current tree | `_EXPECTED_REFERENCE_FILES` at `tests/test_frontend_design_skill.py:22-30` and rewritten scope test at `:383-386` | Yes for the current working tree. Note: these changes are not part of committed builder diff `096ab45`. | COVERED |

| AC6 at least 20 non-empty lines | `tests/test_frontend_design_skill.py:447`; implementation spans `.github/skills/frontend-design/references/anti-patterns.md:1-67` | Yes | COVERED |

| AC7 frontend-design skill tests pass | scoped pytest command above | Yes | COVERED |

| AC8 ruff clean on changed files | scoped ruff command above | Yes | COVERED |

#### Security Review

- No security issues found in the reviewed docs/test scope.

#### Test Integrity

| Original Test | Change Made | Assessment |

| --- | --- | --- |

| Pre-existing `TestFromAC_*` coverage outside #938 scope | `git diff --ignore-all-space HEAD -- tests/test_frontend_design_skill.py` shows formatting-only churn plus the #938 additions; committed builder diff `096ab45` touched only `.github/skills/frontend-design/SKILL.md` and `.github/skills/frontend-design/references/anti-patterns.md` | PRESERVED |

| `TestFromAC_ScopeBoundary::test_skill_package_has_no_anti_pattern_taxonomy` | Rewritten in the current working tree to `test_skill_package_includes_anti_pattern_taxonomy` at `tests/test_frontend_design_skill.py:383-386`, which is the task-authorized replacement for the superseded #934 guard | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |

| --- | --- | --- |

| Assertion specificity | WEAK | `tests/test_frontend_design_skill.py:458` accepts any single WCAG or NNGroup mention in the file; `:469` only checks for nine broad keywords. |

| Negative or error paths | ADEQUATE | For a markdown-reference task, file existence, structure, order, attribution, and category coverage are checked. |

| Mutation reasoning | WEAK | Removing every `Rationale:` line from `.github/skills/frontend-design/references/anti-patterns.md:11-35` or converting `.github/skills/frontend-design/references/anti-patterns.md:39` and `:67` from warnings into bans would still leave all 51 tests green. |

| Test independence | STRONG | Tests are pure file reads with no shared mutable state. |

| Descriptive names | STRONG | New test names are scenario-specific and readable. |

#### Data Safety

- No data safety issues found in the reviewed docs/test scope.

#### Implementation-Aware Test Gaps

- The implementation contains explicit per-item `Citation:` and `Rationale:` pairs at `.github/skills/frontend-design/references/anti-patterns.md:11-35` plus warning-not-ban framing at `:39` and `:67`. The suite never asserts those semantics directly, so a materially weaker taxonomy can pass unchanged.

### Pass 2 - INFORMATIONAL

- The required `tests/test_frontend_design_skill.py` updates for AC4 and AC5 exist only in the current working tree; `git show --stat --name-only --format=fuller 096ab45` confirms the committed builder diff touched only `SKILL.md` and `references/anti-patterns.md`.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |

| --- | --- | --- | --- |

| AC1 file structure and category coverage | `.github/skills/frontend-design/references/anti-patterns.md:6-67` | section/category tests in `TestFromAC_AntiPatternTaxonomy` | PASS |

| AC1 per-item citations, rationales, and warning framing are meaningfully enforced | implementation present at `.github/skills/frontend-design/references/anti-patterns.md:11-35`, `:39`, `:67`, but the mapped tests at `tests/test_frontend_design_skill.py:458-526` do not pin those clauses | insufficient | FAIL |

| AC2 reference-table row after ux-writing row | `.github/skills/frontend-design/SKILL.md:37-38` | `tests/test_frontend_design_skill.py:544-558` | PASS |

| AC3 attribution header | `.github/skills/frontend-design/references/anti-patterns.md:2-4` | `tests/test_frontend_design_skill.py:566-581` | PASS |

| AC4 expected reference file list updated | `tests/test_frontend_design_skill.py:22-30` | existing file-list tests | PASS (current tree) |

| AC5 scope-boundary test rewritten for #938 | `tests/test_frontend_design_skill.py:383-386` | `test_skill_package_includes_anti_pattern_taxonomy` | PASS (current tree) |

| AC6 at least 20 non-empty lines | `.github/skills/frontend-design/references/anti-patterns.md:1-67` | `tests/test_frontend_design_skill.py:447-451` | PASS |

| AC7 all `tests/test_frontend_design_skill.py` tests pass | scoped pytest output: 51 passed | scoped pytest command above | PASS |

| AC8 ruff clean | scoped ruff output: All checks passed | scoped ruff command above | PASS |

### Verdict: FAIL

- The taxonomy content is close, but the task does not clear review because AC1 is not meaningfully enforced by the new tests. The suite currently allows removal of per-item rationales and warning-not-ban framing without failing.

### Action Taken

- `kanban\kanban-md.exe edit 938 --status todo --release`

[[2026-03-24]] Tue 13:06

## Test-Writer Notes (retry)

- Retry reason: reviewer cited MISSING tests — per-item Citation/Rationale labels and warning-not-ban framing had no test coverage.
- Added 3 new tests to TestFromAC_AntiPatternTaxonomy:
  1. test_universal_blockers_each_item_has_citation_label — counts Citation: in UB section, requires >=9
  2. test_universal_blockers_each_item_has_rationale_label — counts Rationale: in UB section, requires >=9
  3. test_taste_heuristics_framed_as_warnings_not_bans — checks TH section contains explicit warning framing
- New tests all PASS because builder implementation already satisfies the criteria (retry cycle with complete implementation).
- Preserved: 51 existing tests (all PASS)
- Total: 54 passed, ruff clean

[[2026-03-25]] Wed 02:50

## Builder Notes

- Files changed: None. Green-on-arrival no-op; existing implementation already satisfies the acceptance criteria.
- Tests: 54 passed in tests/test_frontend_design_skill.py.
- Coverage: Scoped bare coverage run completed with 54 passed; repo aggregate percent is not meaningful for this docs-focused task.
- Lint: ruff clean on .github/skills/frontend-design and tests/test_frontend_design_skill.py.
- Evidence: Baseline task test module was already green before any edits. Coverage retry in an isolated terminal completed after one interrupted foreground run.
- Fixes applied: None.

[[2026-03-25]] Wed 05:31

## Review Evidence

### Review: #938 - Add OwlBear frontend anti-pattern taxonomy

### Test Results

- Scoped pytest on tests/test_frontend_design_skill.py completed with 54 passed in 0.60s.

### Lint Results

- Task-scoped ruff on .github/skills/frontend-design and tests/test_frontend_design_skill.py reported All checks passed.

### Coverage

- Scoped coverage run also completed with 54 passed. The aggregate 2% repo source figure is not meaningful for this task because the touched deliverables are markdown and tests, while bare coverage reports whole-repo source totals.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1 sections, order, and five heuristic categories: covered by TestFromAC_AntiPatternTaxonomy methods at tests/test_frontend_design_skill.py:416, 423, 430, 438, 494, 502, 510, 518, and 526. These fail if the section structure or any category disappears. Verdict: COVERED.
- AC1 per-item Citation labels: covered by tests/test_frontend_design_skill.py:588. This counts Citation labels against the blocker item count and fails if a blocker loses its citation label. Verdict: COVERED.
- AC1 per-item Rationale labels: covered by tests/test_frontend_design_skill.py:611. This counts Rationale labels against the blocker item count and fails if a blocker loses its rationale label. Verdict: COVERED.
- AC1 warning framing: covered by tests/test_frontend_design_skill.py:634. This fails if the Taste Heuristics section loses explicit warning framing. Verdict: COVERED.
- AC2 reference-table row and position: covered by tests/test_frontend_design_skill.py:539 and 546. Verdict: COVERED.
- AC3 attribution header: covered by tests/test_frontend_design_skill.py:561, 569, and 576. Verdict: COVERED.
- AC4 expected reference file list update: anti-patterns.md is present in _EXPECTED_REFERENCE_FILES at tests/test_frontend_design_skill.py:22 and is consumed by the file-list assertions at 101 and 234. Verdict: COVERED.
- AC5 scope-boundary rewrite: covered by tests/test_frontend_design_skill.py:383. Verdict: COVERED.
- AC6 line-count floor: covered by tests/test_frontend_design_skill.py:446 plus direct file count of 67 lines in .github/skills/frontend-design/references/anti-patterns.md. Verdict: COVERED.
- AC7 task test module green: scoped pytest result above. Verdict: COVERED.
- AC8 lint clean: scoped ruff result above. Verdict: COVERED.

#### Security Review

- No security issues found in the reviewed docs and test surface.

#### Test Integrity

- Pre-existing TestFromAC coverage outside #938 scope: current diff shows formatting churn plus #938-specific additions only. No weakening observed. Assessment: PRESERVED.
- TestFromAC_ScopeBoundary::test_skill_package_includes_anti_pattern_taxonomy at tests/test_frontend_design_skill.py:383 is the task-authorized replacement for the old negative guard. Assessment: STRENGTHENED.
- The retry-cycle additions at tests/test_frontend_design_skill.py:588, 611, and 634 strengthen the prior gap called out by the first review. Assessment: STRENGTHENED.

#### Test Quality

- Assertion specificity: ADEQUATE. The retry tests now pin Citation, Rationale, and warning-framing semantics instead of relying only on broad file-level keyword matches.
- Negative or error paths: ADEQUATE. This is a static markdown contract task; the suite checks presence, order, attribution, category coverage, and scope boundaries rather than runtime failures.
- Mutation reasoning: ADEQUATE. Removing a Citation label, Rationale label, or warning framing now breaks the suite; the prior surviving mutants are closed.
- Test independence: STRONG. These tests are pure file reads with no shared mutable state.
- Descriptive names: STRONG. The test names state the contract being enforced.

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- No significant untested behavior remains for this docs-focused task. Manual file review confirms the anti-pattern reference contains the attribution header at .github/skills/frontend-design/references/anti-patterns.md:3-4, the Universal Blockers section at line 6 with cited and rationalized entries across lines 11-35, the Taste Heuristics section at line 37 with five categories at lines 42, 47, 52, 57, and 62, and the warning framing at line 67.
- The SKILL reference table row is present immediately after ux-writing at .github/skills/frontend-design/SKILL.md:37-38.

### Pass 2 - INFORMATIONAL

- Current worktree diff still shows uncommitted changes in tests/test_frontend_design_skill.py and .github/skills/frontend-design/references/anti-patterns.md relative to HEAD. Review evaluated the current tree because that is what reached the review column.

### AC Compliance

- AC1 PASS: .github/skills/frontend-design/references/anti-patterns.md:6-67 contains the two top-level sections, nine cited blocker expansions with rationales at 11-35, and five heuristic categories at 42, 47, 52, 57, and 62; mapped tests at tests/test_frontend_design_skill.py:416-634.
- AC2 PASS: .github/skills/frontend-design/SKILL.md:37-38 places anti-patterns.md directly after ux-writing.md; mapped tests at tests/test_frontend_design_skill.py:539 and 546.
- AC3 PASS: .github/skills/frontend-design/references/anti-patterns.md:3-4 references NOTICE.md and credits Impeccable and Anthropic; mapped tests at tests/test_frontend_design_skill.py:561, 569, and 576.
- AC4 PASS: tests/test_frontend_design_skill.py:22 includes anti-patterns.md in_EXPECTED_REFERENCE_FILES.
- AC5 PASS: tests/test_frontend_design_skill.py:383 rewrites the scope boundary to assert the taxonomy is included.
- AC6 PASS: .github/skills/frontend-design/references/anti-patterns.md has 67 lines; mapped test at tests/test_frontend_design_skill.py:446.
- AC7 PASS: scoped pytest completed with 54 passed.
- AC8 PASS: task-scoped ruff reported All checks passed.

### Verdict: PASS

- Confidence: .93

### Action Taken

- Appended review evidence.
- Moving task #938 to docs.

[[2026-03-25]] Wed 06:38

## Audit

### AC Verification

All 8 AC items verified with evidence:

- AC1 PASS: anti-patterns.md has 9 cited blockers with Citation/Rationale labels, 5 heuristic categories, warning framing. Retry tests (L588, L611, L634) pin semantics.
- AC2 PASS: SKILL.md L38 places anti-patterns.md row after ux-writing.md L37.
- AC3 PASS: anti-patterns.md L3-4 credits NOTICE.md, Impeccable, Anthropic.
- AC4 PASS: _EXPECTED_REFERENCE_FILES includes anti-patterns.md at test L30.
- AC5 PASS: Scope boundary test rewritten at test L383.
- AC6 PASS: anti-patterns.md has 67 lines (>= 20).
- AC7 PASS: 54 passed in scoped run.
- AC8 PASS: ruff All checks passed.

### Test Results

- pytest (scoped): 54 passed
- pytest (full suite): 4339 passed, 38 failed (pre-existing RED-phase), 2 skipped. No task-related regressions.
- ruff: All checks passed

### Architect Quality

- AC quality score: 4/5. AC was measurable and complete. Minor gap: AC1 could have explicitly required per-item Citation/Rationale labels; reviewer caught this and retry cycle resolved it.

### Commits Verified

- 096ab45 docs: add frontend anti-pattern taxonomy reference (#938, builder)
- 1a73fb3 docs: add frontend anti-pattern taxonomy (#938, writer)
All deliverables committed, no uncommitted task files.

### Confidence: .96

### Action: archive

[[2026-03-25]] Wed 06:38

## Audit

### AC Verification

All 8 AC items verified with evidence:

- AC1 PASS: anti-patterns.md has 9 cited blockers with Citation/Rationale labels, 5 heuristic categories, warning framing. Retry tests (L588, L611, L634) pin semantics.
- AC2 PASS: SKILL.md L38 places anti-patterns.md row after ux-writing.md L37.
- AC3 PASS: anti-patterns.md L3-4 credits NOTICE.md, Impeccable, Anthropic.
- AC4 PASS: _EXPECTED_REFERENCE_FILES includes anti-patterns.md at test L30.
- AC5 PASS: Scope boundary test rewritten at test L383.
- AC6 PASS: anti-patterns.md has 67 lines (>= 20).
- AC7 PASS: 54 passed in scoped run.
- AC8 PASS: ruff All checks passed.

### Test Results

- pytest (scoped): 54 passed
- pytest (full suite): 4339 passed, 38 failed (pre-existing RED-phase), 2 skipped. No task-related regressions.
- ruff: All checks passed

### Architect Quality

- AC quality score: 4/5. AC was measurable and complete. Minor gap: AC1 could have explicitly required per-item Citation/Rationale labels; reviewer caught this and retry cycle resolved it.

### Commits Verified

- 096ab45 docs: add frontend anti-pattern taxonomy reference (#938, builder)
- 1a73fb3 docs: add frontend anti-pattern taxonomy (#938, writer)
All deliverables committed, no uncommitted task files.

### Confidence: .96

### Action: archive

[[2026-03-25]] Wed 06:39

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 794a754 | chore | kanban/tasks/938-*.md, activity.jsonl | #938 |
