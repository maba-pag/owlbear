---
id: 115
title: Copy 21 skills from .github/skills/ to skills/
status: archived
priority: medium
created: 2026-03-29 01:40:43.470987+01:00
updated: 2026-03-29 06:15:15.659306+02:00
started: 2026-03-29 06:14:48.124690+02:00
completed: 2026-03-29 06:14:48.124690+02:00
tags:
- phase-1
- scope:skills
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Copy all 21 skill directories from .github/skills/ to skills/ at repo root.

## Acceptance Criteria
- [ ] All 21 skill directories copied to skills/ (alongside existing mcp-kanban)
- [ ] Each copied skill passes validate_skills.py
- [ ] No modifications to skill content during copy
- [ ] .github/skills/ remains intact (deleted in a later task)

## Context
See docs/research/port-skills-to-v2.md. Pure file operation task -- no content changes.
Depends on #9 research.

[[2026-03-29]] Sun 03:03
## Research
N/A - trivial mechanical copy. Validated by parent research docs/research/port-skills-to-v2.md.

**Verification (2026-03-29):**
- 21 skill dirs confirmed in .github/skills/
- All 21 pass validate_skills.py
- skills/ exists with mcp-kanban already present
- VS Code settings already map both paths (scripts/setup.py L34-37)
- Sibling tasks #116 (update refs) and #117 (delete old) already on board
- No new follow-up tasks needed

Research checklist: items 1-5 trivial-path (pure file copy, no design decisions).

[[2026-03-29]] Sun 03:39
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| All 21 skill directories copied to skills/ (alongside existing mcp-kanban) | Verifiable: count dirs in skills/, expect 22 (21 + mcp-kanban). 21 confirmed in .github/skills/. No naming conflict with existing mcp-kanban. | Keep |
| Each copied skill passes validate_skills.py | Verifiable: run `uv run python scripts/validate_skills.py skills/*`. Existing validation mechanism. | Keep |
| No modifications to skill content during copy | Verifiable: diff .github/skills/{name} vs skills/{name} for each. | Keep |
| .github/skills/ remains intact (deleted in a later task) | Verifiable: check directory exists post-copy. Downstream #117 handles deletion. | Keep |

### Architecture Notes
Pure mechanical file-copy task. No application code, no interfaces, no layering concerns.

Existing patterns verified:
- skills/ already exists with mcp-kanban/ and README.md
- validate_skills.py accepts skill dirs as positional args
- VS Code settings already discover both .github/skills/ and skills/ paths (scripts/setup.py L34-37)

TDD exemption: no application code is written. validate_skills.py serves as the existing verification mechanism (AC2).

Dependency chain verified in YAML frontmatter:
- #116 (update refs) depends_on: [115]
- #117 (delete old) depends_on: [116]

### Changes Made
- No AC changes needed -- AC is precise and verifiable as-is.

### Dependencies
- Verified: docs/research/port-skills-to-v2.md exists and is complete
- Verified: #116 depends_on [115], #117 depends_on [116]
- No missing dependencies

[[2026-03-29]] Sun 04:23
## Test-Writer Notes
- Test file: tests/test_copy_skills_to_root.py
- Classes: TestFromAC_AllSkillsCopied, TestFromAC_ValidateSkills, TestFromAC_ContentUnmodified
- Tests per category: happy 4, edge 2, error 0, boundary 0 + 21 parametrized per class = 108 total
- Total: 108 tests, all FAIL
- ruff: clean
- AC4 note: .github/skills/ intact verified implicitly by TestFromAC_ContentUnmodified (reads source files; fails if source deleted)
- AC coverage:
  AC1 (21 dirs in skills/) maps to: test_skills_dir_contains_exactly_22_dirs, test_all_21_expected_skills_present, test_each_skill_directory_exists x21
  AC2 (each passes validate_skills.py) maps to: test_validate_skill_returns_no_errors x21, test_validate_all_skills_together
  AC3 (no content modification) maps to: test_skill_md_content_matches_source x21, test_all_files_in_skill_dir_match_source x21
  AC4 (.github/skills/ intact) maps to: content tests read source (implicit coverage)

[[2026-03-29]] Sun 05:29
## Builder Notes
- Files changed: skills/ (37 files added — 21 skill dirs with SKILL.md + co-located resources)
- Tests: 108 passed, no coverage target (pure file-copy, no application code)
- Lint: ruff clean on tests/test_copy_skills_to_root.py
- Evidence: 108 passed in 0.26s, all TestFromAC_* classes green
- Fixes applied: None

[[2026-03-29]] Sun 05:33
## Review Evidence

### Test Results
- pytest tests/test_copy_skills_to_root.py: 108 passed in 0.27s, 0 failed

### Lint Results
- ruff tests/test_copy_skills_to_root.py: All checks passed!

### Coverage
- No coverage target (pure file-copy, no application code written)

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| All 21 skill directories copied to skills/ (alongside existing mcp-kanban) | Get-ChildItem skills/ shows 22 dirs; test_skills_dir_contains_exactly_22_dirs + 21 parametrized tests pass | PASS |
| Each copied skill passes validate_skills.py | uv run python scripts/validate_skills.py spot-check: no output (clean); test_validate_skill_returns_no_errors x21 + test_validate_all_skills_together pass | PASS |
| No modifications to skill content during copy | Compare-Object .github/skills/arch-review vs skills/arch-review: no diff; test_skill_md_content_matches_source x21 + test_all_files_in_skill_dir_match_source x21 pass | PASS |
| .github/skills/ remains intact | Test-Path .github/skills: True; count: 21 dirs; implicit via 42 content tests reading source | PASS |

### Test-Writer Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 21 dirs in skills/ | test_skills_dir_contains_exactly_22_dirs, test_each_skill_directory_exists x21 | Yes - exact count + per-skill existence check | COVERED |
| validate_skills.py passes | test_validate_skill_returns_no_errors x21, test_validate_all_skills_together | Yes - asserts errors == [] | COVERED |
| No content modification | test_skill_md_content_matches_source x21, test_all_files_in_skill_dir_match_source x21 | Yes - byte-for-byte comparison | COVERED |
| .github/skills/ intact | Implicit via 42 content tests reading source | Yes - any deletion breaks content tests | COVERED |

### TestFromAC Comparison
Builder notes: Fixes applied: None. Test file is new (added by test-writer). Builder added no files to the test suite. All 108 tests PRESERVED as written by test-writer.

### Test Quality
| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | STRONG | Exact counts, byte-for-byte content, parametrized per skill |
| Negative/error paths | ADEQUATE | No invalid-state tests, but task is pure file copy with no error paths in AC |
| Test independence | STRONG | Each test reads filesystem independently, no shared mutable state |
| Test names | STRONG | Descriptive names conveying scenario and condition |

### Security Review
Pure mechanical file copy. No user input, no new dependencies added, no subprocess/SQL/template rendering. No security concerns.

### Verdict: PASS
- Confidence: .95

[[2026-03-29]] Sun 05:54
## Docs Gate
### Checklist

No docs impact. Pure file-copy task.

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure file-copy, no behavior change. Stale .github/skills/ ref is #116 scope. |
| 2 | Docstrings | No | N/A | No Python modules created or modified. |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used. |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research doc | Yes | PASS | docs/research/port-skills-to-v2.md exists, linked in task body. Follow-up tasks #116 and #117 on board. |
| 6 | Scratch files | N/A | PASS | No docs/scratch/115-* files found. |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-29]] Sun 06:15
## Audit
### AC Verification
AC1 (21 dirs in skills/): 22 dirs confirmed (21 copied + mcp-kanban). Commit 91865e4 adds 37 files across 21 skill dirs. PASS
AC2 (validate_skills.py): 108 tests pass including 21 parametrized validate checks. PASS
AC3 (no content modification): Spot-check task-verification/SKILL.md identical. 42 parametrized byte-for-byte tests pass. PASS
AC4 (.github/skills/ intact): 21 dirs confirmed present via list_dir. Content tests read source (would fail if deleted). PASS

### Test Results
- pytest (full suite, ignore voice import): 647 passed, 71 pre-existing failures (voice, mcp-project RED, rename, infra). Zero regressions from #115.
- pytest (task-specific): 108/108 passed in 0.38s
- ruff: All checks passed

### Architect Quality: 5/5
AC was specific, complete, and verifiable. No builder improvisation needed.

### Quality Gap
Test file tests/test_copy_skills_to_root.py was not committed by test-writer. Committed by auditor as orphaned deliverable.

### Confidence: .97
### Action: archived

## Commits
Commit 99a4e3f: test: add copy-skills verification tests (#115, test-writer) - orphaned test file
