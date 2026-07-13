---
id: 131
title: Sync drifted skill content before .github/skills/ deletion
status: archived
priority: medium
created: 2026-03-29 08:06:55.313257+02:00
updated: 2026-03-29 11:57:58.029304+02:00
started: 2026-03-29 08:29:09.204196+02:00
completed: 2026-03-29 11:57:53.311544+02:00
tags:
- phase-1
- scope:skills
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Sync 3 skills where content drifted between .github/skills/ and skills/ after the copy (#115).

## Acceptance Criteria
- [ ] Copy vscode_listCodeUsages guidance from .github/skills/code-review/SKILL.md to skills/code-review/SKILL.md (added by #103 post-copy)
- [ ] Copy vscode_listCodeUsages guidance from .github/skills/tdd-workflow/SKILL.md to skills/tdd-workflow/SKILL.md (added by #103 post-copy)
- [ ] Verify skills/kanban-md/SKILL.md already has 3 extra pitfall lines (no action needed, skills/ is authoritative)
- [ ] Verify skills/research-workflow/SKILL.md cross-ref already updated to skills/ path (#116)
- [ ] All 4 drifted skills have identical or skills/-authoritative content
- [ ] Tests pass

## Context
After #115 copied skills to skills/, task #103 modified .github/skills/code-review and .github/skills/tdd-workflow without updating skills/ copies. This created content drift. Must resolve before #117 can delete .github/skills/.
See docs/research/port-skills-to-v2.md sec 3g for drift analysis.

[[2026-03-29]] Sun 08:29
## Research
N/A -- trivial sync. Drift verified via `fc.exe` diffs:

- **code-review**: `.github/` L36-37 has `vscode_listCodeUsages` guidance missing from `skills/` (2 lines)
- **tdd-workflow**: `.github/` L55-56 has `vscode_listCodeUsages` guidance missing from `skills/` (1 paragraph)
- **kanban-md**: `skills/` has 3 extra pitfall lines -- `skills/` is authoritative, no action
- **research-workflow**: `skills/` cross-ref already correct (#116) -- no action

Implementation: 2 text insertions. No code files touched. No new dependencies.
Sources: `docs/research/port-skills-to-v2.md` sec 3g, `fc.exe` diff output.

[[2026-03-29]] Sun 08:48
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Copy vscode_listCodeUsages to skills/code-review | Verified: .github/ L35 has paragraph, skills/ L33 missing it | Pass |
| Copy vscode_listCodeUsages to skills/tdd-workflow | Verified: .github/ L53 has bullet, skills/ L52 missing it | Pass |
| Verify kanban-md (skills/ authoritative) | Verified: skills/ has 3 extra pitfall lines | Pass |
| Verify research-workflow cross-ref | Verified: skills/ L99 already has skills/ path | Pass |
| All 4 drifted skills identical or skills/-authoritative | Testable via fc.exe diff | Pass |
| Tests pass | Standard regression check | Pass |

### Architecture Notes
Pure markdown content sync. No code files, no interfaces, no failure modes. TDD not applicable (no Python).
Insertion points are unambiguous: mirror the .github/ file structure in corresponding skills/ files.

Note: #117 (delete .github/skills/) currently depends on [116] only. It should also depend on [131] to prevent premature deletion.

### Changes Made
- No changes needed; AC is precise as-is

### Dependencies
- Verified: no formal depends_on on #131 (correct, it has none)
- Note: #117 should add #131 to its depends_on (not edited here per cross-task rule)

[[2026-03-29]] Sun 09:41
## Test-Writer Notes
- Test file: tests/test_skill_sync_131.py
- Classes: TestFromAC_CodeReviewSync, TestFromAC_TddWorkflowSync, TestFromAC_KanbanMdPitfalls, TestFromAC_ResearchWorkflowCrossRef
- Tests per category: happy 6, edge 0, error 0, boundary 0, verify-baseline 5
- Total: 11 tests written; 6 FAIL, 5 PASS by design
- ruff: clean
- Note: 5 tests (kanban-md pitfalls x3, research-workflow cross-ref x2) PASS immediately — they guard already-correct baseline state for AC lines 3 and 4, which explicitly say "verify, no action needed". Cannot make these fail without testing wrong state.
- AC coverage:
  - AC line 1 (copy to code-review): test_code_review_contains_vscode_list_code_usages, test_code_review_contains_trace_all_callers, test_code_review_vscode_line_matches_github_source_exactly — all FAIL
  - AC line 2 (copy to tdd-workflow): test_tdd_workflow_contains_vscode_list_code_usages, test_tdd_workflow_contains_before_modifying_signatures, test_tdd_workflow_vscode_line_matches_github_source_exactly — all FAIL
  - AC line 3 (verify kanban-md pitfalls): test_kanban_md_has_claim_release_separate_pitfall, test_kanban_md_has_body_append_claim_pitfall, test_kanban_md_has_lf_line_endings_pitfall — PASS (baseline guards)
  - AC line 4 (verify research-workflow cross-ref): test_research_workflow_cross_ref_uses_skills_path, test_research_workflow_cross_ref_not_github_path — PASS (baseline guards)
  - AC line 5 (content parity): covered by the 3 _matches_github_source_exactly tests — FAIL
  - AC line 6 (tests pass): meta-AC, satisfied when builder completes lines 1 and 2

[[2026-03-29]] Sun 10:04
## Builder Notes
- Files changed: skills/code-review/SKILL.md (+2 lines), skills/tdd-workflow/SKILL.md (+1 line)
- Tests: 11 passed (6 previously FAIL now GREEN, 5 baseline PASS unchanged)
- Lint: ruff clean (no Python files touched)
- Evidence: 11 passed in 0.07s
- Fixes applied: Inserted vscode_listCodeUsages paragraph into code-review (after Step 2 intro), inserted Before-modifying-signatures bullet into tdd-workflow Step 2 list

[[2026-03-29]] Sun 10:43
## Review Evidence
### Test Results
- pytest: 11 passed, 0 failed (tests/test_skill_sync_131.py -v)
- Evidence: 11 passed in 0.05s

### Lint Results
- ruff: All checks passed! (tests/test_skill_sync_131.py)

### Coverage
- No Python source files changed; markdown-only insertions. N/A.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Copy vscode_listCodeUsages to code-review | TestFromAC_CodeReviewSync x3 | Yes - asserts specific strings absent before sync | COVERED |
| Copy vscode_listCodeUsages to tdd-workflow | TestFromAC_TddWorkflowSync x3 | Yes - asserts specific strings absent before sync | COVERED |
| Verify kanban-md pitfalls (3 lines) | TestFromAC_KanbanMdPitfalls x3 | Yes - asserts presence of specific pitfall strings | COVERED |
| Verify research-workflow cross-ref | TestFromAC_ResearchWorkflowCrossRef x2 | Yes - asserts skills/ path present, .github/ path absent | COVERED |
| Content parity (_matches_github_source_exactly) | x2 exact-match tests | Yes - fails if line text differs by one char | COVERED |
| Tests pass (meta-AC) | All 11 tests PASS | Satisfied by completion of AC lines 1-2 | COVERED |

#### Security Review
- No security issues. Task is pure read-only markdown insertions; tests do Path.read_text on repo files only. No external input, no dynamic execution.

#### Test Integrity (TestFromAC comparison)
- Test file is new (created by test-writer, no prior version). Builder notes confirm only skills/code-review/SKILL.md and skills/tdd-workflow/SKILL.md were modified. No TestFromAC_* methods modified.
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 11 TestFromAC_* methods | No change | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact string matching, one test uses exact line comparison across files |
| Negative/error paths | ADEQUATE | AC lines 3-4 are verification-only (no negative path applicable); lines 1-2 covered by absence-before-sync design |
| Mutation reasoning | STRONG | Flipping the insertion would break 3 presence tests + 1 exact-match test per skill |
| Test independence | STRONG | Each test reads file independently, no shared mutable state |
| Descriptive names | STRONG | Names describe scenario and expected behavior clearly |

#### Data Safety
- No data safety issues. Tests are read-only; implementation is static markdown text insertion.

#### Implementation-Aware Test Gaps
- No implementation complexity. The builder made 2 targeted text insertions in markdown files. No branching, retry logic, or state machines to audit.

### Pass 2 - INFORMATIONAL
- No informational findings.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Copy vscode_listCodeUsages to skills/code-review | skills/code-review/SKILL.md L35 matches .github/ L35 exactly (grep confirmed) | test_code_review_vscode_line_matches_github_source_exactly PASS | PASS |
| Copy vscode_listCodeUsages to skills/tdd-workflow | skills/tdd-workflow/SKILL.md L53 matches .github/ L53 exactly (grep confirmed) | test_tdd_workflow_vscode_line_matches_github_source_exactly PASS | PASS |
| Verify kanban-md pitfalls (no action needed) | skills/kanban-md/SKILL.md has all 3 pitfall strings | TestFromAC_KanbanMdPitfalls x3 PASS | PASS |
| Verify research-workflow cross-ref (no action needed) | skills/research-workflow/SKILL.md contains skills/ path, not .github/ path | TestFromAC_ResearchWorkflowCrossRef x2 PASS | PASS |
| All 4 drifted skills identical or skills/-authoritative | Exact-match tests pass for code-review + tdd-workflow; baseline guards pass for kanban-md + research-workflow | 2x _matches_github_source_exactly PASS | PASS |
| Tests pass | 11 passed, 0 failed in 0.05s | All tests | PASS |

### Verdict: PASS (confidence .97)

[[2026-03-29]] Sun 11:03
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure markdown content sync; no behavior, API, or convention change |
| 2 | Docstrings complete | No | N/A | No Python files touched |
| 3 | docs/sources/overview.md | No | N/A | No external patterns; sync from internal .github/skills/ copy |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/port-skills-to-v2.md exists and linked in task body |
| 6 | Scratch files cleaned | N/A | Pass | No docs/scratch/131-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-29]] Sun 11:57
## Audit
All 6 AC lines PASS. 11/11 tests pass. Full suite: 784 pass, 81 pre-existing failures (none from #131). ruff clean. AC Quality: 5/5. Confidence: .97. Action: archive.

Quality gap: test-writer did not commit test file. Committed by auditor (294e827).
Builder commit: 9ee92ef.
