---
id: 941
title: Add RED tests for frontend-design skill discovery and reference pack
status: archived
priority: nice-to-have
created: 2026-03-22T17:20:27.0012273+01:00
updated: 2026-03-22T22:55:50.2709588+01:00
started: 2026-03-22T22:54:57.8050124+01:00
completed: 2026-03-22T22:54:57.8050124+01:00
tags:
    - ui
    - agent
    - test
    - scope:copilot
    - type:test
parent: 934
class: standard
---

## Context

Adding `.github/skills/frontend-design/` in #934 changes OwlBear's discovered skill surface. `tests/test_skills.py` owns the live real-skill discovery contract, `tests/test_project_definition_skill.py` shows the existing repo-path skill test pattern, and `src/owlbear/skills/registry.py` is the frontmatter-loading seam this RED task should verify.

## Acceptance Criteria

- [ ] Add `tests/test_frontend_design_skill.py` as a repo-path verification file for the checked-in `.github/skills/frontend-design/` package, following the pattern in `tests/test_project_definition_skill.py`.
- [ ] In `tests/test_frontend_design_skill.py`, assert `.github/skills/frontend-design/SKILL.md` exists and its YAML frontmatter is loadable by `SkillRegistry`.
- [ ] In `tests/test_frontend_design_skill.py`, assert the parsed frontmatter has `name == frontend-design` and a non-empty `description`.
- [ ] In `tests/test_frontend_design_skill.py`, assert these seven files exist under `.github/skills/frontend-design/references/`: `typography.md`, `color-and-contrast.md`, `spatial-design.md`, `motion-design.md`, `interaction-design.md`, `responsive-design.md`, and `ux-writing.md`.
- [ ] Update the three live real-skill discovery assertions in `tests/test_skills.py` from 19 to 20 and update the stale human-facing wording in that section so the prose matches the new count.
- [ ] Keep the task RED-only: limit changes to verification coverage for the `frontend-design` skill package and do not add or edit `.github/skills/frontend-design/**` content in this task.

See `docs/research/frontend-design-skill-implementation-gate.md` and `docs/research/frontend-design-skill-red-test-gate.md`.

[[2026-03-22]] Sun 17:38

## Research

- Recommendation (.95): keep the RED seam at the checked-in repo surface by adding tests/test_frontend_design_skill.py and updating the three real-skill count assertions in tests/test_skills.py from 19 to 20.
- Mirror tests/test_project_definition_skill.py: use repo-relative path assertions and SkillRegistry._parse_frontmatter(...) so the missing .github/skills/frontend-design/ package fails immediately until #934 lands.
- In the new file, assert only the task-scoped contract: SKILL.md exists, frontmatter name is frontend-design, description is non-empty, and the seven named references/*.md files exist.
- Do not over-constrain optional attribution or future sibling resources; #934 allows attribution in SKILL.md or NOTICE.md, and #938 may add more frontend-design resources later.
- Update the stale human-facing wording in tests/test_skills.py alongside the count bump so the suite does not claim 18 skills while asserting 20.
- No new kanban task created: #941 already captures the RED change and #934 is the paired GREEN consumer.
- Source ledger updated in docs/sources/overview.md.
- Evidence: docs/research/frontend-design-skill-red-test-gate.md

[[2026-03-22]] Sun 17:43

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add a skill-specific test file for `.github/skills/frontend-design/SKILL.md` | Too vague on file path and test seam | Rewrote to require `tests/test_frontend_design_skill.py` using the existing repo-path skill test pattern |
| Update real-skill discovery expectations in `tests/test_skills.py` from 19 to 20 when the skill is present | `when the skill is present` weakens the intended RED failure and omits stale prose updates | Rewrote to require the three live count assertions to move to 20 and the stale human-facing wording to match |
| Assert the skill frontmatter name is `frontend-design` and the description is non-empty | Missing the frontmatter-loading seam | Rewrote to require loadability by `SkillRegistry` plus `name` and `description` assertions |
| Assert the seven adapted reference files under `.github/skills/frontend-design/references/` exist | Missing the exact required file set | Rewrote to enumerate all seven required reference filenames |
| Keep scope limited to RED or verification coverage for the skill package | Good boundary, but not mechanically checkable | Rewrote to forbid `.github/skills/frontend-design/**` content edits in this task |

### Architecture Notes

- Single domain: RED verification for an `agent-config` skill package. The task changes only test coverage around skill discovery and package presence; it does not absorb #934's docs work or #938's later taxonomy work.
- Pattern to follow: `tests/test_project_definition_skill.py` already shows the repo-path skill test style, and `src/owlbear/skills/registry.py` confirms `SkillRegistry` discovers checked-in `*/SKILL.md` packages via frontmatter parsing.
- Integration seam: `tests/test_skills.py` owns the live `.github/skills` discovery count and `list_skills()` coverage. Those assertions must intentionally go RED from 19 to 20 until #934 creates the package.
- Failure-mode map skipped: RED-only test coverage, no application codepath change.

### Changes Made

- Claimed #941 as `architect-941`
- Rewrote the acceptance criteria with exact test files, assertions, and scope boundaries
- Advanced #941 to `todo`

### Dependencies

- Verified: #934 already depends on #941 as the paired GREEN consumer
- Verified: repo-path skill test pattern exists in `tests/test_project_definition_skill.py`
- Verified: live skill discovery count assertions live in `tests/test_skills.py`

[[2026-03-22]] Sun 18:04

## Test-Writer Notes

- Test file: tests/test_frontend_design_skill.py
- Classes: TestFromAC_FrontendDesignSkillPackage
- Tests per category: happy 2, edge 1, error 0, boundary 9
- Total: 12 tests, all FAIL âœ“
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC1: SKILL.md exists | test_skill_file_exists | happy |
| AC2: frontmatter loadable by SkillRegistry | test_frontmatter_parses_without_error | happy |
| AC3: name == frontend-design | test_frontmatter_name_is_frontend_design | boundary |
| AC3: description non-empty | test_frontmatter_description_is_nonempty | boundary |
| AC4: typography.md | test_typography_reference_exists | boundary |
| AC4: color-and-contrast.md | test_color_and_contrast_reference_exists | boundary |
| AC4: spatial-design.md | test_spatial_design_reference_exists | boundary |
| AC4: motion-design.md | test_motion_design_reference_exists | boundary |
| AC4: interaction-design.md | test_interaction_design_reference_exists | boundary |
| AC4: responsive-design.md | test_responsive_design_reference_exists | boundary |
| AC4: ux-writing.md | test_ux_writing_reference_exists | boundary |
| AC4: all 7 files | test_all_seven_reference_files_exist | edge |
| AC5: count assertions 19->20 | tests/test_skills.py TestFromAC_RealSkillsDiscovery (3 tests renamed+updated) | boundary |

[[2026-03-22]] Sun 18:04

## Test-Writer Notes

- Test file: tests/test_frontend_design_skill.py
- Classes: TestFromAC_FrontendDesignSkillPackage
- Tests per category: happy 2, edge 1, error 0, boundary 9
- Total: 12 tests, all FAIL`n- ruff: clean
- AC coverage: all 5 AC lines covered (see task body)

[[2026-03-22]] Sun 18:21

## Builder Notes

- Files changed: tests/test_frontend_design_skill.py (new), tests/test_skills.py (updated), pyproject.toml (N801 per-file-ignore added)
- Tests: 12 failing RED (test_frontend_design_skill.py - intentional seam for #934); 33 passed in test_skills.py (no regressions)
- Lint: ruff clean
- Evidence: 12 failing = all TestFromAC_FrontendDesignSkillPackage tests (SKILL.md missing), 33 passing = full test_skills.py suite
- Fixes applied: Removed 3 redundant # noqa: N801 inline comments from TestFromAC_* class definitions in test_skills.py (made redundant when test-writer added N801 to pyproject.toml per-file-ignores; RUF100 lint fix)
- Count note: At HEAD, .github/skills already has 20 skills (not 19 as assumed when task was written). The test-writer updated test_skills.py 19->20 which fixed a stale assertion (GREEN). The primary RED seam for #934 is the 12 tests in test_frontend_design_skill.py. When #934 creates the frontend-design package, test_skills.py will need a further update from 20->21.

[[2026-03-22]] Sun 18:47

## Review Evidence

## Review: #941 - Add RED tests for frontend-design skill discovery and reference pack

### Test Results

- Command: uv run pytest tests/test_frontend_design_skill.py tests/test_skills.py -q --tb=short
- Result: 12 failed, 33 passed, 2 warnings.
- Failure set is exactly the 12 tests in tests/test_frontend_design_skill.py; all failures are expected missing-package assertions for .github/skills/frontend-design/**.
- Real-skill discovery checks in tests/test_skills.py passed (33 passing tests in the scoped run).

### Lint Results

- Command: uv run ruff check tests/test_frontend_design_skill.py tests/test_skills.py
- Result: All checks passed.

### Coverage

- Command: uv run pytest tests/test_frontend_design_skill.py tests/test_skills.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: same 12 failed, 33 passed outcome; coverage report generated but not meaningful for gate decisions while RED assertions intentionally fail.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage (TestFromAC)

- AC1 mapped test: tests/test_frontend_design_skill.py:36 test_skill_file_exists. Would fail if SKILL.md missing. Verdict: COVERED.
- AC2 mapped test: tests/test_frontend_design_skill.py:40 test_frontmatter_parses_without_error. Would fail if SkillRegistry cannot load frontmatter. Verdict: COVERED.
- AC3 mapped tests: tests/test_frontend_design_skill.py:49 and tests/test_frontend_design_skill.py:57 for name and description. Would fail on wrong name/empty description. Verdict: COVERED.
- AC4 mapped tests: per-file checks plus aggregate check in tests/test_frontend_design_skill.py:95. Would fail if any required references/*.md file missing. Verdict: COVERED.
- AC5 mapped tests: tests/test_skills.py:375, tests/test_skills.py:386, tests/test_skills.py:398 with count/assertion prose updated to 20. Would fail if count/wording not updated. Verdict: COVERED.
- AC6 scope check: commit 8b6fb76 touches pyproject.toml, tests/test_frontend_design_skill.py, tests/test_skills.py and does not edit .github/skills/frontend-design/**. Verdict: COVERED.

#### Security Review

- No security issues found. Change set is test/lint configuration only (no new execution surfaces, no secrets, no deserialization or shell injection paths).

#### Test Integrity (TestFromAC comparison)

- git log 8b6fb76..HEAD -- tests/test_frontend_design_skill.py tests/test_skills.py pyproject.toml returned no entries.
- No post-test-writer modifications were made to the TestFromAC assertions for this task.
- Assessment: PRESERVED.

#### Test Quality

- Assertion specificity: STRONG (exact file existence and exact frontmatter/count assertions).
- Negative/error paths: ADEQUATE (task AC is positive contract verification; RED behavior comes from missing package seam).
- Mutation reasoning: STRONG (removing any required file/name/count assertion fails directly).
- Test independence: STRONG (pure filesystem reads, no shared mutable fixtures).
- Descriptive names: STRONG.

#### Data Safety

- No data safety issues found.

#### Implementation-aware test gaps

- No significant untested implementation complexity introduced by this task; scope is test-only verification for a skill package seam.

### Pass 2 - INFORMATIONAL

- pyproject.toml now ignores N801 for all tests (pyproject.toml:75). Behavior is unchanged, but this broadens test-style lint tolerance beyond just #941 classes.

### AC Compliance

- AC1 PASS: new repo-path verification file exists at tests/test_frontend_design_skill.py.
- AC2 PASS: frontmatter loadability assertion present at tests/test_frontend_design_skill.py:40.
- AC3 PASS: name/description assertions present at tests/test_frontend_design_skill.py:49 and tests/test_frontend_design_skill.py:57.
- AC4 PASS: seven required references checks present (individual checks plus aggregate at tests/test_frontend_design_skill.py:95).
- AC5 PASS: three live real-skill discovery assertions updated to 20 at tests/test_skills.py:378, tests/test_skills.py:389, tests/test_skills.py:401 and wording updated in adjacent docstrings.
- AC6 PASS: no edits to .github/skills/frontend-design/**; task remains verification-focused.

### Verdict: PASS

- Confidence: .93

### Action Taken

- Move review -> docs.

[[2026-03-22]] Sun 19:14

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | RED test-only task; no behavior/API/convention change |
| 2 | Docstrings complete | No | N/A | Only test files changed (tests/test_frontend_design_skill.py, tests/test_skills.py); no public API modules modified |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'Frontend-Design Skill RED Test Gate (Task #941)' already present with correct attributions |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research docs | Yes | Pass | docs/research/frontend-design-skill-red-test-gate.md and docs/research/frontend-design-skill-implementation-gate.md both exist and are referenced in task body |
| 6 | No impact | N/A | N/A | Items 1-5 fully evaluated above |

### Files Updated

- None (sources/overview.md was already updated during research phase)

### Scratch Files Cleaned

- None (no docs/scratch/941-* files found)

[[2026-03-22]] Sun 19:14

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | RED test-only task; no behavior/API/convention change |
| 2 | Docstrings complete | No | N/A | Only test files changed (tests/test_frontend_design_skill.py, tests/test_skills.py); no public API modules modified |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'Frontend-Design Skill RED Test Gate (Task #941)' already present with correct attributions |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research docs | Yes | Pass | docs/research/frontend-design-skill-red-test-gate.md and docs/research/frontend-design-skill-implementation-gate.md both exist and are referenced in task body |
| 6 | No impact | N/A | N/A | Items 1-5 fully evaluated above |

### Files Updated

- None (sources/overview.md was already updated during research phase)

### Scratch Files Cleaned

- None (no docs/scratch/941-* files found)

[[2026-03-22]] Sun 22:54

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: test_frontend_design_skill.py exists | File present at tests/test_frontend_design_skill.py, 102 lines | PASS |
| AC2: SKILL.md exists + frontmatter loadable | test_skill_file_exists + test_frontmatter_parses_without_error â€” both RED (expected) | PASS |
| AC3: name == frontend-design, description non-empty | test_frontmatter_name_is_frontend_design + test_frontmatter_description_is_nonempty â€” both RED | PASS |
| AC4: 7 reference files asserted | 7 individual tests + test_all_seven_reference_files_exist â€” all RED | PASS |
| AC5: count assertions 19->20, prose updated | test_skills.py L378/389/401 all assert == 20, docstrings/names say '20', 33 passed | PASS |
| AC6: no edits to .github/skills/frontend-design/** | Test-Path returns False, commit 8b6fb76 touches only tests + pyproject.toml | PASS |

### Test Results

- pytest (scoped): 12 failed (expected RED), 33 passed in test_skills.py
- pytest (full suite): 108 failed (12 task-RED + 96 pre-existing), 3754 passed â€” no regressions from #941
- ruff: clean on task files

### Architect Quality

- AC specificity: specific file names, exact counts, enumerated reference files
- Edge case coverage: aggregate + individual reference checks
- Design direction: correct pattern reference (test_project_definition_skill.py)
- AC quality score: 4/5 (minor gap: count assumption 19->20 was stale; builder adapted)

### Upstream Commit

- 8b6fb76 test: add RED tests for frontend-design skill package (#941, test-writer)
- Files: pyproject.toml, tests/test_frontend_design_skill.py, tests/test_skills.py
- Uncommitted diff on test_frontend_design_skill.py is CRLF/LF normalization only (no content change)

### Confidence: .96

### Action: archive

[[2026-03-22]] Sun 22:54

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: test_frontend_design_skill.py exists | File present at tests/test_frontend_design_skill.py, 102 lines | PASS |
| AC2: SKILL.md exists + frontmatter loadable | test_skill_file_exists + test_frontmatter_parses_without_error â€” both RED (expected) | PASS |
| AC3: name == frontend-design, description non-empty | test_frontmatter_name_is_frontend_design + test_frontmatter_description_is_nonempty â€” both RED | PASS |
| AC4: 7 reference files asserted | 7 individual tests + test_all_seven_reference_files_exist â€” all RED | PASS |
| AC5: count assertions 19->20, prose updated | test_skills.py L378/389/401 all assert == 20, docstrings/names say '20', 33 passed | PASS |
| AC6: no edits to .github/skills/frontend-design/** | Test-Path returns False, commit 8b6fb76 touches only tests + pyproject.toml | PASS |

### Test Results

- pytest (scoped): 12 failed (expected RED), 33 passed in test_skills.py
- pytest (full suite): 108 failed (12 task-RED + 96 pre-existing), 3754 passed â€” no regressions from #941
- ruff: clean on task files

### Architect Quality

- AC specificity: specific file names, exact counts, enumerated reference files
- Edge case coverage: aggregate + individual reference checks
- Design direction: correct pattern reference (test_project_definition_skill.py)
- AC quality score: 4/5 (minor gap: count assumption 19->20 was stale; builder adapted)

### Upstream Commit

- 8b6fb76 test: add RED tests for frontend-design skill package (#941, test-writer)
- Files: pyproject.toml, tests/test_frontend_design_skill.py, tests/test_skills.py
- Uncommitted diff on test_frontend_design_skill.py is CRLF/LF normalization only (no content change)

### Confidence: .96

### Action: archive

[[2026-03-22]] Sun 22:55

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8b6fb76 | test | pyproject.toml, tests/test_frontend_design_skill.py, tests/test_skills.py | #941 |
| e11caa3 | chore | kanban/tasks/941-*.md, kanban/activity.jsonl | #941 |
