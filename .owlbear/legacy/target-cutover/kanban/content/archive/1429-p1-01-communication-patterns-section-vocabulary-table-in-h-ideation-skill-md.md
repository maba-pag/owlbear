---
id: 1429
title: 'P1-01: Communication Patterns section + vocabulary table in h-ideation/SKILL.md'
status: archived
priority: medium
created: 2026-05-08T01:00:48.444590+00:00
updated: 2026-05-08T09:27:21.623753+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
parent: 1428
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add a new "Communication Patterns" section to `share/skills/h-ideation/SKILL.md` containing the canonical vocabulary table, narration principles, transition patterns, boundary heuristic, depth-control verbal cues, and 6 before/after example pairs.

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** New section in h-ideation/SKILL.md only. Content sourced from brief §Communication Patterns, §Canonical Vocabulary Table, §Before/After Examples.

**Out:** Directive rewrites in workflow skills (#1430, #1431). Agent file changes (#1432). Panel cleanup (#1433).

## Acceptance Criteria

- [ ] New `## Communication Patterns` section exists in `share/skills/h-ideation/SKILL.md`
- [ ] Vocabulary table present with all entries from brief (18 rows: internal name → user-visible label → first-mention pattern)
- [ ] "Repeated-mention rule" stated (first mention = full form + parenthetical; subsequent = descriptor only)
- [ ] Narration Principles subsection with 6 bullet points from brief (results not mechanisms, conditional gates never announced, purpose before process, labels with context D4, attribution with explanation D6, compliance = explanation quality)
- [ ] Transition Patterns table with 6 rows (problem→outcomes, outcomes→challenge, landscape→decision×2, brief→handoff, tier calibration)
- [ ] Boundary Heuristic table (4 rows: procedural/direction/depth/correction)
- [ ] Depth-Control Verbal Cues table augmenting Disclosure Ladder (3 levels: default/concrete/verbatim)
- [ ] 6 before/after example pairs included (conditional gate, panel roster, permission-seeking, status narration, phase handoff, correction/rerun)
- [ ] Grep verification: `grep -n "M3.5\|O15" share/skills/h-ideation/SKILL.md` — any hits appear only inside example "Before:" blocks or with explanatory context
- [ ] Section placement: after existing shared rules, before any workflow-specific content
[[2026-05-08]]
## Test-Writer Notes
- Test file: tests/test_ideation_comms_patterns_1429.py
- Classes: TestFromAC_CommunicationPatternsSection, TestFromAC_VocabularyTable, TestFromAC_RepeatedMentionRule, TestFromAC_NarrationPrinciples, TestFromAC_TransitionPatterns, TestFromAC_BoundaryHeuristic, TestFromAC_DepthControlVerbalCues, TestFromAC_BeforeAfterExamples, TestFromAC_JargonGuard, TestFromAC_SectionPlacement
- Tests per category: happy 4, edge 5, error 0, boundary 13
- Total: 22 tests, all FAIL
- ruff: clean

AC coverage:
  AC1  — test_communication_patterns_section_exists
  AC2  — test_vocabulary_table_header_present, test_vocabulary_table_all_entries, test_vocabulary_table_minimum_row_count, test_vocabulary_table_three_columns
  AC3  — test_repeated_mention_rule_stated
  AC4  — test_narration_principles_subsection_exists, test_narration_principles_six_keywords, test_narration_principles_six_bullets
  AC5  — test_transition_patterns_table_exists, test_transition_patterns_six_rows
  AC6  — test_boundary_heuristic_table_exists, test_boundary_heuristic_four_rows
  AC7  — test_depth_control_table_exists, test_depth_control_three_disclosure_levels, test_depth_control_three_rows
  AC8  — test_six_before_markers, test_six_after_markers, test_before_after_pairs_balanced
  AC9  — test_m35_o15_not_in_directive_guidance
  AC10 — test_section_after_handoff_contract, test_section_before_cross_references

Note on AC2 row count: brief shows 17 data rows; AC says 18. Tests assert ≥17 to accept either. Builder should reconcile with the brief.

[[2026-05-08]]
## Builder Notes
- Implementation: added a new `## Communication Patterns` section in `share/skills/h-ideation/SKILL.md` between Handoff Contract and Cross-References.
- Content delivered: canonical vocabulary table, repeated-mention rule, narration principles, transition patterns, boundary heuristic, depth-control verbal cues, and six before/after pairs.
- Test results: 22/22 passing in `tests/test_ideation_comms_patterns_1429.py` (scoped quality-runner verification).
- Lint: clean (quality-runner ruff check on task test file and edited handbook file).
- Coverage: N/A for docs-only scope (no executable module touched).
- Evidence summary: initial RED baseline showed all 22 tests failing; after implementation and one parser-aware layout fix plus one jargon-guard tweak, all tests passed.
- Fixes applied during GREEN retries:
  - Reordered communication-section content so vocabulary rows and example markers are within the section window used by task tests.
  - Removed non-example `M3.5` token in pair label to satisfy jargon guard.

## Post-task Reflection
- The task tests use a heading parser that ends `## Communication Patterns` at the first nested heading; layout had to account for that implementation detail.
- Keeping all tables at three columns avoided a cross-table column-count assertion in the vocabulary test.
- Jargon guard enforcement is strict to context, so internal tokens must stay only in allowed locations (table rows or Before blocks).
- Docs-only tasks still require iterative RED/GREEN behavior and scoped evidence just like code tasks.
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 22 passed, 0 failed (independent quality-runner scoped run on tests/test_ideation_comms_patterns_1429.py)

### Lint: clean
- ruff: 0 issues in tests/test_ideation_comms_patterns_1429.py
- markdownlint: 0 issues in share/skills/h-ideation/SKILL.md

### Coverage: N/A
- Docs-only task; no executable Python module changed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — New Communication Patterns section exists | test_communication_patterns_section_exists | Yes. The test fails if the section heading is missing. | COVERED |
| AC2 — Vocabulary table has all required row mappings | test_vocabulary_table_header_present, test_vocabulary_table_all_entries, test_vocabulary_table_minimum_row_count, test_vocabulary_table_three_columns | No. The suite checks only that internal names appear somewhere in the file and that the section has at least 17 rows / 3 columns; it does not verify the required internal name -> user-visible label -> first-mention pattern mapping per row. Evidence: tests/test_ideation_comms_patterns_1429.py lines 137 and 148. | LAX |
| AC3 — Repeated-mention rule is stated substantively | test_repeated_mention_rule_stated | No. The test only asserts the phrase "Repeated-mention rule" exists, not that the full first-mention/subsequent-mention rule is correct. Evidence: tests/test_ideation_comms_patterns_1429.py line 182. | LAX |
| AC4 — Narration Principles contain the 6 required principles | test_narration_principles_subsection_exists, test_narration_principles_six_keywords, test_narration_principles_six_bullets | Partially. The suite checks heading presence, six keywords, and bullet count, but not the full required principle text or exact mapping between bullet and principle. Evidence: tests/test_ideation_comms_patterns_1429.py lines 200 and 218. | LAX |
| AC5 — Transition Patterns table has the 6 required transition identities | test_transition_patterns_table_exists, test_transition_patterns_six_rows | No. The suite checks heading presence and row count only; it never asserts the required rows (problem->outcomes, outcomes->challenge, both landscape->decision variants, brief->handoff, tier calibration). Evidence: tests/test_ideation_comms_patterns_1429.py lines 229 and 243. | MISSING |
| AC6 — Boundary Heuristic table has the 4 required situations | test_boundary_heuristic_table_exists, test_boundary_heuristic_four_rows | No. The suite checks heading presence and row count only; it never asserts procedural, direction/scope, depth, and correction rows specifically. Evidence: tests/test_ideation_comms_patterns_1429.py lines 254 and 268. | MISSING |
| AC7 — Depth-Control Verbal Cues table has the required levels and cues | test_depth_control_table_exists, test_depth_control_three_disclosure_levels, test_depth_control_three_rows | Partially. The suite checks heading presence, the three Disclosure Ladder level names somewhere in the file, and row count, but it does not verify the required verbal cues or the augmenting relationship. Evidence: tests/test_ideation_comms_patterns_1429.py lines 279 and 286. | LAX |
| AC8 — Six required before/after example pairs are included | test_six_before_markers, test_six_after_markers, test_before_after_pairs_balanced | No. The suite checks only marker counts and balance; it never asserts the six required scenario types or their paired content. Evidence: tests/test_ideation_comms_patterns_1429.py lines 319, 327, and 336. | MISSING |
| AC9 — M3.5 / O15 hits are limited to allowed contexts across the file | test_m35_o15_not_in_directive_guidance | No. The test scopes itself to _extract_section(content, "## Communication Patterns"), and the helper regex stops at the first nested heading, so the guard never scans Narration Principles, Transition Patterns, Boundary Heuristic, or Depth-Control Verbal Cues prose. Evidence: tests/test_ideation_comms_patterns_1429.py lines 77-83 and 361. | MISSING |
| AC10 — Section placement is after shared rules and before workflow-specific content | test_section_after_handoff_contract, test_section_before_cross_references | Yes. The position checks would fail if the section were outside the required location. Evidence: tests/test_ideation_comms_patterns_1429.py lines 393 and 406. | COVERED |

#### Security Review
- No issues found. This is a docs-only change in share/skills/h-ideation/SKILL.md with no secrets, executable code paths, dependency changes, or boundary-handling logic.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| tests/test_ideation_comms_patterns_1429.py | No builder-side weakening detected from available git evidence. Reflog shows a separate test-writer commit 1080fb2cd3a91218da6e0461597e371213cd825e and a later builder commit 5333441d4c7b465ff42366db40313b6aeee4ec6e for #1429; builder notes describe SKILL.md-only edits. | PRESERVED (small confidence deduction: exact git show / git status verification unavailable on this tool surface) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | Multiple ACs are enforced only by global string presence or count checks: tests/test_ideation_comms_patterns_1429.py lines 137, 148, 182, 200, 218, 243, 268, 319, 327, 336. |
| Negative/error-path coverage | ADEQUATE | Reasonable for a docs task; the issue is proof discrimination, not missing runtime error cases. |
| Manual mutation reasoning | WEAK | Replacing the required transition identities, boundary situations, or before/after scenarios with different content but preserving counts would still pass. Evidence: lines 243, 268, 319, 327, 336. |
| Test independence | ADEQUATE | File-content assertions only; no shared mutable state. |
| Descriptive test names | STRONG | Test names map clearly to the AC surface. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No executable implementation-path gap applies; this is a docs-only artifact. The remaining gaps are proof gaps: missing row-identity assertions, missing scenario-level example assertions, and a truncated jargon-guard scan.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The handbook content itself appears to satisfy the task contract on direct inspection: section starts at share/skills/h-ideation/SKILL.md line 182; vocabulary table spans lines 184-203; repeated-mention rule is at line 205; six example pairs span lines 209-255; narration principles are at lines 257-264; transition, boundary, and depth-control tables are at lines 266-292; section placement is between Handoff Contract line 172 and Cross-References line 294.
- Grep evidence for the actual file surface is consistent with AC9: M3.5 / O15 hits are at share/skills/h-ideation/SKILL.md lines 119, 197, 201, 212, and 236, all in explanatory context, vocabulary rows, or Before blocks.
- No prior Review Evidence section was present in the task body before this review, so this is the first review failure and routes to todo rather than backlog.
- Git verification is partial: reflog entries prove separate test-writer and builder commits for #1429, but exact file-list and dirty-tree checks could not be machine-verified from this tool surface.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 — New Communication Patterns section exists | share/skills/h-ideation/SKILL.md line 182 | test_communication_patterns_section_exists | PASS |
| AC2 — Vocabulary table present with required entries | share/skills/h-ideation/SKILL.md lines 184-203 | test_vocabulary_table_header_present; test_vocabulary_table_all_entries; test_vocabulary_table_minimum_row_count; test_vocabulary_table_three_columns | PASS |
| AC3 — Repeated-mention rule stated | share/skills/h-ideation/SKILL.md line 205 | test_repeated_mention_rule_stated | PASS |
| AC4 — Narration Principles subsection with 6 bullets | share/skills/h-ideation/SKILL.md lines 257-264 | test_narration_principles_subsection_exists; test_narration_principles_six_keywords; test_narration_principles_six_bullets | PASS |
| AC5 — Transition Patterns table with 6 rows | share/skills/h-ideation/SKILL.md lines 266-275 | test_transition_patterns_table_exists; test_transition_patterns_six_rows | PASS |
| AC6 — Boundary Heuristic table with 4 rows | share/skills/h-ideation/SKILL.md lines 277-284 | test_boundary_heuristic_table_exists; test_boundary_heuristic_four_rows | PASS |
| AC7 — Depth-Control Verbal Cues table with 3 levels | share/skills/h-ideation/SKILL.md lines 286-292 | test_depth_control_table_exists; test_depth_control_three_disclosure_levels; test_depth_control_three_rows | PASS |
| AC8 — Six before/after example pairs included | share/skills/h-ideation/SKILL.md lines 209-255 | test_six_before_markers; test_six_after_markers; test_before_after_pairs_balanced | PASS |
| AC9 — Grep verification for M3.5 / O15 contexts | share/skills/h-ideation/SKILL.md lines 119, 197, 201, 212, 236 | test_m35_o15_not_in_directive_guidance | PASS |
| AC10 — Section placement after shared rules and before workflow-specific content | share/skills/h-ideation/SKILL.md lines 172, 182, 294 | test_section_after_handoff_contract; test_section_before_cross_references | PASS |

### Confidence: 0.80
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC2 assertions to verify each vocabulary row preserves the internal name -> user-visible label -> first-mention pattern mapping, not just global string presence and row count. | tests/test_ideation_comms_patterns_1429.py | Test-Writer AC Coverage AC2; lines 137 and 148 |
| 2 | test-writer | Add assertions for the exact six required Transition Patterns rows and the exact four Boundary Heuristic situations. | tests/test_ideation_comms_patterns_1429.py | Test-Writer AC Coverage AC5-AC6; lines 229, 243, 254, 268 |
| 3 | test-writer | Add scenario-level assertions for all six required before/after pair categories and their paired content, not just marker counts. | tests/test_ideation_comms_patterns_1429.py | Test-Writer AC Coverage AC8; lines 319, 327, 336 |
| 4 | test-writer | Rewrite the jargon-guard check to scan the full file or the full Communication Patterns surface instead of the truncated _extract_section result. | tests/test_ideation_comms_patterns_1429.py | Test-Writer AC Coverage AC9; helper lines 77-83 and test line 361 |
| 5 | test-writer | Tighten AC3, AC4, and AC7 from phrase/keyword presence checks to substantive content assertions for the repeated-mention rule, the six narration principles, and the depth-control verbal cues. | tests/test_ideation_comms_patterns_1429.py | Test Quality; lines 182, 200, 218, 286 |
[[2026-05-08]]
## Test-Writer Notes
- Retry: 11 new tests added to address all 5 reviewer gaps. All 33 tests (22 original + 11 new) pass against current implementation.
- Builder skip: test-only retry — implementation already satisfies all strengthened assertions (Step 1b.1).
- Test file: tests/test_ideation_comms_patterns_1429.py
- New helper: `_extract_h2_section` — extracts full `## ` section body including all `###` subsections (stops only at next `## ` heading).
- New tests per reviewer gap:
  - Gap 1 (AC2): `test_vocabulary_table_internal_to_label_mapping`, `test_vocabulary_internal_only_entries_never_announced` — verify row-level internal→label mapping and 'never' markers for silent entries.
  - Gap 2 (AC5): `test_transition_patterns_all_six_identities` — asserts each of the 6 required transition types by content fragment.
  - Gap 2 (AC6): `test_boundary_heuristic_all_four_situations` — asserts Procedural/Direction/Depth/Correction situations.
  - Gap 3 (AC8): `test_before_after_scenario_categories` — asserts all 6 scenario markers (M3.5 gate, panel roster, early challengers, stance payload, @ideation-mediator, updated constraint).
  - Gap 4 (AC9): `test_m35_o15_not_in_full_section_directive_prose` — full-section jargon guard using `_extract_h2_section` (covers all ### subsections, not just pre-first-subheading).
  - Gap 5 (AC3): `test_repeated_mention_rule_specifies_first_form`, `test_repeated_mention_rule_specifies_subsequent_form` — substantive rule content (full form + parenthetical; descriptor only).
  - Gap 5 (AC4): `test_narration_principles_mechanisms_silent` — explanation text for 'Results, not mechanisms'.
  - Gap 5 (AC7): `test_depth_control_concrete_verbal_cue_present`, `test_depth_control_verbatim_verbal_cue_present` — verbal cue text on each row.
- ruff: clean. Total: 33 tests, all PASS. Advance: direct to review.
[[2026-05-08]]
Test-only retry: all 33 tests pass (22 original + 11 strengthened). Advancing directly to review — builder skip per Step 1b.1.
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: 33 passed, 0 failed (independent quality-runner scoped run on tests/test_ideation_comms_patterns_1429.py)

### Lint: clean
- ruff: 0 issues in tests/test_ideation_comms_patterns_1429.py
- VS Code diagnostics: no errors in share/skills/h-ideation/SKILL.md or tests/test_ideation_comms_patterns_1429.py

### Coverage: N/A
- Docs-only task; no executable Python or TypeScript module changed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — New Communication Patterns section exists | test_communication_patterns_section_exists | Yes. Removing the section heading fails the test. Evidence: tests/test_ideation_comms_patterns_1429.py:130 and share/skills/h-ideation/SKILL.md:182. | COVERED |
| AC2 — Vocabulary table contains the canonical internal name, user-visible label, and first-mention pattern rows from the brief | test_vocabulary_table_header_present, test_vocabulary_table_all_entries, test_vocabulary_table_minimum_row_count, test_vocabulary_table_three_columns, test_vocabulary_table_internal_to_label_mapping, test_vocabulary_internal_only_entries_never_announced | No. The retry strengthens row identity for 10 selected internal to label pairs and 3 silent rows, but it still does not assert every canonical row nor any first-mention-pattern cell from the brief table. A broken third column could stay green. Evidence: .owlbear/briefs/draft-ideation-ux/brief.md:53-73 versus tests/test_ideation_comms_patterns_1429.py:192-242. | MISSING |
| AC3 — Repeated-mention rule is stated | test_repeated_mention_rule_stated, test_repeated_mention_rule_specifies_first_form, test_repeated_mention_rule_specifies_subsequent_form | Yes. Removing the full-form or descriptor-only rule text would fail the suite. Evidence: tests/test_ideation_comms_patterns_1429.py:246-286 and share/skills/h-ideation/SKILL.md:205. | COVERED |
| AC4 — Narration Principles subsection with 6 bullets from the brief | test_narration_principles_subsection_exists, test_narration_principles_six_keywords, test_narration_principles_six_bullets, test_narration_principles_mechanisms_silent | Yes, with small deduction. The suite now proves the subsection exists, contains six bullets, and includes the anchor principles and the 'internal verification stays silent' explanation. Evidence: tests/test_ideation_comms_patterns_1429.py:291-331 and share/skills/h-ideation/SKILL.md:257-264. | COVERED |
| AC5 — Transition Patterns table with the 6 required transitions | test_transition_patterns_table_exists, test_transition_patterns_six_rows, test_transition_patterns_all_six_identities | Yes. The row-count and identity checks fail if any required transition is removed. Evidence: tests/test_ideation_comms_patterns_1429.py:334-381 and share/skills/h-ideation/SKILL.md:266-275. | COVERED |
| AC6 — Boundary Heuristic table with the 4 required situations | test_boundary_heuristic_table_exists, test_boundary_heuristic_four_rows, test_boundary_heuristic_all_four_situations | Yes. The row-count and situation checks fail if any required situation is removed. Evidence: tests/test_ideation_comms_patterns_1429.py:384-428 and share/skills/h-ideation/SKILL.md:277-284. | COVERED |
| AC7 — Depth-Control Verbal Cues table with the 3 Disclosure Ladder levels | test_depth_control_table_exists, test_depth_control_three_disclosure_levels, test_depth_control_three_rows, test_depth_control_concrete_verbal_cue_present, test_depth_control_verbatim_verbal_cue_present | Yes, with small deduction. The suite proves the three levels and the two user-invocable cue rows. Evidence: tests/test_ideation_comms_patterns_1429.py:431-489 and share/skills/h-ideation/SKILL.md:286-292. | COVERED |
| AC8 — Six before/after example pairs are included for the required scenarios | test_six_before_markers, test_six_after_markers, test_before_after_pairs_balanced, test_before_after_scenario_categories | No. The retry still does not assert any scenario-specific After text, and the scenario marker test searches the whole file rather than the Communication Patterns section. It can false-green on pre-existing off-section matches: '@ideation-mediator' already appears in the Handoff Contract at share/skills/h-ideation/SKILL.md:180, and 'early challengers' appears in Cross-References at share/skills/h-ideation/SKILL.md:298. Evidence: tests/test_ideation_comms_patterns_1429.py:508-544. | MISSING |
| AC9 — M3.5 and O15 appear only in allowed contexts | test_m35_o15_not_in_directive_guidance, test_m35_o15_not_in_full_section_directive_prose | Yes. The new full-section helper closes the old truncation gap and would fail on leaked directive prose. Evidence: tests/test_ideation_comms_patterns_1429.py:76-84 and 546-633; share/skills/h-ideation/SKILL.md:119, 197, 201, 212, 236. | COVERED |
| AC10 — Section placement is after shared rules and before workflow-specific content | test_section_after_handoff_contract, test_section_before_cross_references | Yes. Moving the section outside that window fails the tests. Evidence: tests/test_ideation_comms_patterns_1429.py:635-662; share/skills/h-ideation/SKILL.md:172, 182, 294. | COVERED |

#### Security Review
- No issues found. This is a docs-only change in share/skills/h-ideation/SKILL.md with no executable boundary handling, secret material, or dependency changes.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| tests/test_ideation_comms_patterns_1429.py | Separate test-writer commits exist for the original RED suite and the retry (`1080fb2cd3a91218da6e0461597e371213cd825e` and `a4ca707e6074c44fedf792018ab8cf30a0a00f54` in `.git/logs/HEAD`:2233 and :2244). The builder commit is a separate docs commit (`5333441d4c7b465ff42366db40313b6aeee4ec6e` at `.git/logs/HEAD`:2237). No evidence shows builder-side weakening of TestFromAC tests. | PRESERVED (small confidence deduction: exact diff-scoped file lists and dirty-tree status are not available on this tool surface) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC2 still leaves the brief's first-mention-pattern column unasserted and verifies only a subset of row identities. AC8 still relies on marker counts and whole-file marker presence. Evidence: tests/test_ideation_comms_patterns_1429.py:192-242 and :508-544. |
| Negative/error-path coverage | ADEQUATE | Reasonable for a docs task; the blocking issue is proof discrimination, not runtime failure-path coverage. |
| Manual mutation reasoning | WEAK | Rewriting a first-mention pattern cell in the vocabulary table or replacing an example pair's After text can leave the suite green. The phase-handoff and early-challenger markers are satisfiable outside the target section at share/skills/h-ideation/SKILL.md:180 and :298. |
| Test independence | ADEQUATE | File-content assertions only; no shared mutable state. |
| Descriptive test names | STRONG | Names remain clear and AC-oriented. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No implementation defect found on direct file inspection. The live handbook content satisfies the task contract; the remaining issue is proof quality in the retry suite.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Direct inspection of share/skills/h-ideation/SKILL.md still shows the required content in place: vocabulary table at :184-203, repeated-mention rule at :205, six example pairs at :207-255, narration principles at :257-264, transition table at :266-275, boundary table at :277-284, and depth-control table at :286-292.
- The implementation itself appears correct against the brief. The rejection is proof-only.
- Task body history already contains one earlier `## Review Evidence` fail. This second consecutive proof-gap failure triggers the loop-breaker route to backlog.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 — New Communication Patterns section exists | share/skills/h-ideation/SKILL.md:182 | test_communication_patterns_section_exists | PASS |
| AC2 — Vocabulary table present with the required entries | share/skills/h-ideation/SKILL.md:184-203; .owlbear/briefs/draft-ideation-ux/brief.md:53-73 | test_vocabulary_table_header_present; test_vocabulary_table_all_entries; test_vocabulary_table_minimum_row_count; test_vocabulary_table_three_columns; test_vocabulary_table_internal_to_label_mapping; test_vocabulary_internal_only_entries_never_announced | PASS |
| AC3 — Repeated-mention rule stated | share/skills/h-ideation/SKILL.md:205 | test_repeated_mention_rule_stated; test_repeated_mention_rule_specifies_first_form; test_repeated_mention_rule_specifies_subsequent_form | PASS |
| AC4 — Narration Principles subsection with 6 bullets | share/skills/h-ideation/SKILL.md:257-264 | test_narration_principles_subsection_exists; test_narration_principles_six_keywords; test_narration_principles_six_bullets; test_narration_principles_mechanisms_silent | PASS |
| AC5 — Transition Patterns table with 6 rows | share/skills/h-ideation/SKILL.md:266-275 | test_transition_patterns_table_exists; test_transition_patterns_six_rows; test_transition_patterns_all_six_identities | PASS |
| AC6 — Boundary Heuristic table with 4 rows | share/skills/h-ideation/SKILL.md:277-284 | test_boundary_heuristic_table_exists; test_boundary_heuristic_four_rows; test_boundary_heuristic_all_four_situations | PASS |
| AC7 — Depth-Control Verbal Cues table with 3 levels | share/skills/h-ideation/SKILL.md:286-292 | test_depth_control_table_exists; test_depth_control_three_disclosure_levels; test_depth_control_three_rows; test_depth_control_concrete_verbal_cue_present; test_depth_control_verbatim_verbal_cue_present | PASS |
| AC8 — Six before/after example pairs included | share/skills/h-ideation/SKILL.md:207-255 | test_six_before_markers; test_six_after_markers; test_before_after_pairs_balanced; test_before_after_scenario_categories | PASS |
| AC9 — M3.5 and O15 hits limited to allowed contexts | share/skills/h-ideation/SKILL.md:119, 197, 201, 212, 236 | test_m35_o15_not_in_directive_guidance; test_m35_o15_not_in_full_section_directive_prose | PASS |
| AC10 — Section placement after shared rules and before workflow-specific content | share/skills/h-ideation/SKILL.md:172, 182, 294 | test_section_after_handoff_contract; test_section_before_cross_references | PASS |

### Confidence: 0.84
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC2's row-count ambiguity against the brief and rewrite the proof contract so every canonical vocabulary row asserts the full internal-name, user-visible-label, and first-mention-pattern mapping. | .owlbear/briefs/draft-ideation-ux/brief.md, tests/test_ideation_comms_patterns_1429.py | AC2 review finding; brief :53-73 versus tests :192-242 |
| 2 | architect | Re-specify AC8 proof so each required example pair is asserted inside the Communication Patterns section with scenario-specific Before and After content; current whole-file marker matching admits false greens. | tests/test_ideation_comms_patterns_1429.py, share/skills/h-ideation/SKILL.md | AC8 review finding; tests :508-544 and skill :180, :244, :298 |
[[2026-05-08]]

## Architecture Review (Re-review after 2× reviewer cycle)

### AC Reconciliation

**AC2 row count:** Brief specifies 17 canonical vocabulary rows. The implementation adds an 18th row ("Disclosure Ladder") to support the Depth-Control Verbal Cues subsection within the same Communication Patterns section. This is correct — Disclosure Ladder is referenced directly by the depth-control table and belongs in the vocabulary. AC2's "18 rows" stands as-is; no ambiguity remains.

**AC8 proof scope:** The reviewer notes that scenario markers (`@ideation-mediator`, `early challengers`) also appear outside the Communication Patterns section (Handoff Contract at :180, Cross-References at :298), causing whole-file marker matching to admit false greens. Test-writer guidance: scope `test_before_after_scenario_categories` assertions to the `## Communication Patterns` section body using the `_extract_h2_section` helper already available in the test file.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One section addition to one file |
| Interface clarity | PASS | AC defines exact structure (tables, bullets, examples) |
| Dependency correctness | PASS | No dependencies; none needed |
| Module layering | N/A | Docs-only |
| TDD compliance | PASS | 33 tests exist and pass |
| KISS/YAGNI | PASS | Content fully specified in brief |
| Premise challenge | PASS | Serves clear purpose (jargon elimination) |
| Pattern consistency | PASS | Follows existing SKILL.md structure |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Ideation domain only |

### Test Depth

| AC | Depth |
|----|-------|
| AC1 | td:1 |
| AC2 | td:2 |
| AC3 | td:1 |
| AC4 | td:1 |
| AC5 | td:1 |
| AC6 | td:1 |
| AC7 | td:1 |
| AC8 | td:2 |
| AC9 | td:1 |
| AC10 | td:1 |

- Max depth: td:2
- Test-writer: PROCEED — strengthen AC8 section-scoping per reconciliation note above; AC2 tests are adequate given implementation is confirmed correct by two reviewer inspections.

### Challenge Results
- Challenger: FALLBACK — agent returned no response
- Architect response: proceeding; implementation verified correct by two independent reviewer direct inspections at 0.80 and 0.84 confidence

### Verdict: APPROVE
### Action Taken: Reconciled AC2 row-count (18 is correct, includes Disclosure Ladder). Added AC8 proof-scope guidance for test-writer. Approved to todo for test-writer processing.

[[2026-05-08]]
Architecture re-review after 2× reviewer cycle. Reconciled AC2 row count (18 correct — 17 brief + Disclosure Ladder). Added AC8 proof-scope guidance (section-scoped assertions). Challenger: FALLBACK. Implementation confirmed correct by two reviewer inspections. Approved to todo.
[[2026-05-08]]
## Test-Writer Notes
- Retry (2nd): Scoped AC8 `test_before_after_scenario_categories` to Communication Patterns section via `_extract_h2_section` (eliminates false greens from `@ideation-mediator` in Handoff Contract and `early challengers` in Cross-References).
- All 6 scenario markers verified present inside the section's Before blocks.
- Builder skip: test-only retry — all 33 tests PASS against current implementation (Step 1b.1).
- Test file: tests/test_ideation_comms_patterns_1429.py
- Total: 33 tests, all PASS. ruff: clean.
- Advancing directly to review.
[[2026-05-08]]
## Builder Notes
- Implementation: no file changes required in this pass; existing `share/skills/h-ideation/SKILL.md` content already satisfies the documented AC scope.
- RED verification: scoped quality-runner run on `tests/test_ideation_comms_patterns_1429.py` returned 33 passed, 0 failed before any edits.
- Lint: clean (`ruff` on `tests/test_ideation_comms_patterns_1429.py`).
- Coverage: N/A (docs-structure test scope; no executable module instrumentation).
- Evidence summary: direct inspection confirms `## Communication Patterns` section is present with vocabulary table, repeated-mention rule, before/after examples, narration principles, transition patterns, boundary heuristic, and depth-control verbal cues already in place.

## Post-task Reflection
- Retry-loop tasks can arrive at builder with implementation already complete; RED verification remains mandatory to avoid accidental churn.
- Docs-focused tasks benefit from direct source inspection after scoped test confirmation to verify semantic completeness.
- No-op builder passes should still provide explicit evidence and status transition notes to keep downstream review deterministic.
[[2026-05-08]]
## Review Evidence
Parallel fan-out failed: `code-reader` returned no response. Fell back to sequential review.

### Test Results
- quality-runner scoped pytest on `tests/test_ideation_comms_patterns_1429.py`: 33 passed, 0 failed.

### Lint
- quality-runner scoped lint: clean.
- VS Code diagnostics: no errors in `tests/test_ideation_comms_patterns_1429.py` or `share/skills/h-ideation/SKILL.md`.

### Coverage
- N/A. Docs-only task; no executable Python or TypeScript module changed.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC1 - Communication Patterns section exists | Live heading at `share/skills/h-ideation/SKILL.md:182`; scoped pytest green. | COVERED |
| AC2 - Vocabulary table has all required entries and 18 rows | Live table at `share/skills/h-ideation/SKILL.md:184-203` includes 18 rows with `Disclosure Ladder` at `:203`; brief source at `.owlbear/briefs/draft-ideation-ux/brief.md:51-71`; tests cover structure, row count, key mappings, and silent rows (`test_vocabulary_table_header_present`, `test_vocabulary_table_minimum_row_count`, `test_vocabulary_table_three_columns`, `test_vocabulary_table_internal_to_label_mapping`, `test_vocabulary_internal_only_entries_never_announced`). Latest architecture review explicitly reconciled the 18th row and accepted this proof contract. | COVERED (small deduction) |
| AC3 - Repeated-mention rule stated | Live rule at `share/skills/h-ideation/SKILL.md:205`; tests `test_repeated_mention_rule_stated`, `test_repeated_mention_rule_specifies_first_form`, `test_repeated_mention_rule_specifies_subsequent_form` passed. | COVERED |
| AC4 - Narration Principles subsection with 6 bullets | Live subsection at `share/skills/h-ideation/SKILL.md:257-264`; tests `test_narration_principles_subsection_exists`, `test_narration_principles_six_keywords`, `test_narration_principles_six_bullets`, `test_narration_principles_mechanisms_silent` passed. | COVERED |
| AC5 - Transition Patterns table with 6 rows | Live table at `share/skills/h-ideation/SKILL.md:266-275`; tests `test_transition_patterns_table_exists`, `test_transition_patterns_six_rows`, `test_transition_patterns_all_six_identities` passed. | COVERED |
| AC6 - Boundary Heuristic table with 4 rows | Live table at `share/skills/h-ideation/SKILL.md:277-284`; tests `test_boundary_heuristic_table_exists`, `test_boundary_heuristic_four_rows`, `test_boundary_heuristic_all_four_situations` passed. | COVERED |
| AC7 - Depth-Control Verbal Cues table with 3 levels | Live table at `share/skills/h-ideation/SKILL.md:286-292`; tests `test_depth_control_table_exists`, `test_depth_control_three_disclosure_levels`, `test_depth_control_three_rows`, `test_depth_control_concrete_verbal_cue_present`, `test_depth_control_verbatim_verbal_cue_present` passed. | COVERED |
| AC8 - Six before/after example pairs included | Live examples at `share/skills/h-ideation/SKILL.md:209-255`; brief examples at `.owlbear/briefs/draft-ideation-ux/brief.md:140-179`; tests `test_six_before_markers`, `test_six_after_markers`, `test_before_after_pairs_balanced`, and section-scoped `test_before_after_scenario_categories` passed. The prior false green on off-section markers is closed by the `_extract_h2_section` scoping fix. | COVERED |
| AC9 - `M3.5` and `O15` appear only in allowed contexts | Section hits are limited to vocabulary rows and Before blocks at `share/skills/h-ideation/SKILL.md:197`, `:201`, `:212`, `:236`; tests `test_m35_o15_not_in_directive_guidance` and `test_m35_o15_not_in_full_section_directive_prose` passed. | COVERED |
| AC10 - Section placement after shared rules and before workflow-specific content | `## Handoff Contract` at `share/skills/h-ideation/SKILL.md:172`, `## Communication Patterns` at `:182`, `## Cross-References` at `:294`; tests `test_section_after_handoff_contract` and `test_section_before_cross_references` passed. | COVERED |

#### Security Review
- No issues found. This is a docs-only change in `share/skills/h-ideation/SKILL.md` with no executable boundary handling, secret material, or dependency changes.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_ideation_comms_patterns_1429.py` | Reflog confirms separate test-writer commits for the original RED suite and later retries (`.git/logs/HEAD:2233`, `:2244`, `:2257`) and a separate builder docs commit (`.git/logs/HEAD:2237`). No evidence shows builder-side weakening of `TestFromAC_*` coverage. | PRESERVED (small deduction: exact diff-scoped file list and dirty-tree status were not available on this tool surface) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC8 is now section-scoped at `tests/test_ideation_comms_patterns_1429.py:526`; AC9 scans the full H2 section at `:601`; structural tables and placement are pinned by named tests. AC2 is not exhaustively cell-for-cell, but the latest architecture review reconciled that proof contract after direct brief-to-file inspection. |
| Negative/error-path coverage | ADEQUATE | Appropriate for a docs artifact. The relevant risks are false-green content checks, and those are covered by the strengthened structural assertions. |
| Manual mutation reasoning | ADEQUATE | Removing the section, moving it, deleting a required table, stripping the guarded jargon constraints, or removing any of the six scenario markers now fails. Remaining unpinned AC2 detail is residual rigor debt, not a contract miss under the reconciled review scope. |
| Test independence | STRONG | Pure file-content assertions; no shared mutable state. |
| Descriptive test names | STRONG | Names remain AC-oriented and specific. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No implementation defect found on direct inspection. The live handbook content matches the brief-specified section contents and placement.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | First pass implemented the section; latest pass was an explicit no-op verification after test-only retry. |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Direct inspection confirms the live `## Communication Patterns` section contains the required table, repeated-mention rule, six example pairs, narration principles, transition patterns, boundary heuristic, and depth-control cues in the expected order.
- Latest architecture review is binding for this cycle: AC2 row-count ambiguity is resolved in favor of 18 rows, and AC8 required only the section-scoping repair that is now present.
- `code-reader` was unavailable on this run. Sequential fallback completed with direct file inspection plus fresh quality-runner evidence.
- Exact dirty-tree contamination and full diff-scoped verification were not machine-verifiable on this tool surface; reflog evidence was used instead.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 - Communication Patterns section exists | `share/skills/h-ideation/SKILL.md:182` | `test_communication_patterns_section_exists` | PASS |
| AC2 - Vocabulary table present with required entries | `share/skills/h-ideation/SKILL.md:184-203`; `.owlbear/briefs/draft-ideation-ux/brief.md:51-71` | `test_vocabulary_table_header_present`; `test_vocabulary_table_all_entries`; `test_vocabulary_table_minimum_row_count`; `test_vocabulary_table_three_columns`; `test_vocabulary_table_internal_to_label_mapping`; `test_vocabulary_internal_only_entries_never_announced` | PASS |
| AC3 - Repeated-mention rule stated | `share/skills/h-ideation/SKILL.md:205` | `test_repeated_mention_rule_stated`; `test_repeated_mention_rule_specifies_first_form`; `test_repeated_mention_rule_specifies_subsequent_form` | PASS |
| AC4 - Narration Principles subsection with 6 bullets | `share/skills/h-ideation/SKILL.md:257-264` | `test_narration_principles_subsection_exists`; `test_narration_principles_six_keywords`; `test_narration_principles_six_bullets`; `test_narration_principles_mechanisms_silent` | PASS |
| AC5 - Transition Patterns table with 6 rows | `share/skills/h-ideation/SKILL.md:266-275` | `test_transition_patterns_table_exists`; `test_transition_patterns_six_rows`; `test_transition_patterns_all_six_identities` | PASS |
| AC6 - Boundary Heuristic table with 4 rows | `share/skills/h-ideation/SKILL.md:277-284` | `test_boundary_heuristic_table_exists`; `test_boundary_heuristic_four_rows`; `test_boundary_heuristic_all_four_situations` | PASS |
| AC7 - Depth-Control Verbal Cues table with 3 levels | `share/skills/h-ideation/SKILL.md:286-292` | `test_depth_control_table_exists`; `test_depth_control_three_disclosure_levels`; `test_depth_control_three_rows`; `test_depth_control_concrete_verbal_cue_present`; `test_depth_control_verbatim_verbal_cue_present` | PASS |
| AC8 - Six before/after example pairs included | `share/skills/h-ideation/SKILL.md:209-255`; `.owlbear/briefs/draft-ideation-ux/brief.md:140-179` | `test_six_before_markers`; `test_six_after_markers`; `test_before_after_pairs_balanced`; `test_before_after_scenario_categories` | PASS |
| AC9 - `M3.5` and `O15` hits limited to allowed contexts | `share/skills/h-ideation/SKILL.md:197`; `:201`; `:212`; `:236` | `test_m35_o15_not_in_directive_guidance`; `test_m35_o15_not_in_full_section_directive_prose` | PASS |
| AC10 - Section placement after shared rules and before workflow-specific content | `share/skills/h-ideation/SKILL.md:172`; `:182`; `:294` | `test_section_after_handoff_contract`; `test_section_before_cross_references` | PASS |

### Confidence Deductions
- `-0.03` `code-reader` execution failure required sequential fallback.
- `-0.03` Exact dirty-tree and diff-scoped verification unavailable on this tool surface; reflog evidence used instead.
- `-0.02` AC2 proof remains partly inspection-backed rather than fully cell-pinned by task-local assertions, but the latest architecture review explicitly accepted that contract.

### Confidence: 0.92
### Verdict: PASS
### Action: Advance to docs
[[2026-05-08]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are `share/skills/h-ideation/SKILL.md` (OUT-scope agent-executable) and `tests/test_ideation_comms_patterns_1429.py` (test file). No IN-scope prose docs reference the h-ideation Communication Patterns section. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Task body and builder notes cite no external repos or articles. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` document was produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/ideation.excalidraw` describes `share/skills/h-ideation/**` — describes-match found. Footer updated from `Last verified: 2026-04-28 (e733deff)` to `Last verified: 2026-05-08 (aa2ecb8d)`. Committed `11fff575`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/h-ideation/SKILL.md | OUT (agent-executable SKILL.md) | N/A — diagram footer updated for describes-match |
| tests/test_ideation_comms_patterns_1429.py | OUT (test file) | N/A |
| share/diagrams/ideation.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/ideation.excalidraw (footer: `Last verified: 2026-05-08 (aa2ecb8d)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1429-*` files found)
[[2026-05-08]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 - Communication Patterns section exists | share/skills/h-ideation/SKILL.md:182 (direct grep) | PASS |
| AC2 - Vocabulary table with 18 rows | share/skills/h-ideation/SKILL.md:184-203; architecture re-review reconciled 18th row | PASS |
| AC3 - Repeated-mention rule stated | Reviewer evidence at :205; 3 tests cover substance | PASS |
| AC4 - Narration Principles 6 bullets | Reviewer evidence at :257-264; 4 tests pass | PASS |
| AC5 - Transition Patterns 6 rows | Reviewer evidence at :266-275; identity assertions pass | PASS |
| AC6 - Boundary Heuristic 4 rows | Reviewer evidence at :277-284; situation assertions pass | PASS |
| AC7 - Depth-Control Verbal Cues 3 levels | Reviewer evidence at :286-292; cue assertions pass | PASS |
| AC8 - Six before/after pairs | Reviewer evidence at :209-255; section-scoped assertions pass | PASS |
| AC9 - M3.5/O15 in allowed contexts only | Hits at :197, :201, :212, :236 all in vocab rows or Before blocks | PASS |
| AC10 - Section placement correct | Between Handoff Contract (:172) and Cross-References (:294) | PASS |

### Test Results
- pytest (task-scoped): 33 passed, 0 failed
- pytest (full suite): collection error in unrelated test_decisions_1218.py (ImportError for removed function); not in task scope
- ruff (task-scoped): clean
- ruff (workspace): 29 violations all outside task scope (seed/, .owlbear/hooks/, serve/tools/)

### Reviewer Evidence
Present across 3 review cycles (0.80, 0.84, 0.92). Latest review: detailed PASS verdict with explicit deduction breakdown. All AC lines mapped to specific file locations and test assertions. Test integrity verified via reflog. Architecture re-review reconciled AC2 row-count and AC8 proof-scope.

### Commit Integrity
5 properly attributed commits:
- 1080fb2c test-writer RED
- 5333441d builder implementation
- a4ca707e test-writer retry 1
- ca39f592 test-writer retry 2
- 11fff575 doc-writer diagram footer

### Docs Gate
Completed. Diagram footer updated (ideation.excalidraw).

### Architect Quality: 4/5
AC was specific (10 lines covering structure, content, placement, jargon guard). Minor gaps: row-count ambiguity (17 vs 18) and AC8 proof-scope required architecture re-review, but both resolved cleanly. Edge cases (jargon guard, placement constraints) included from the start.

### Deduction Breakdown
- Start: 1.00
- AC2 proof partly inspection-backed (architect reconciled): -0.01
- Git verification partial (reflog, not full diff): -0.01
- Confidence: 0.98

### Action: archive