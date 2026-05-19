---
id: 934
title: Create OwlBear frontend-design skill from curated Impeccable references
status: archived
priority: nice-to-have
created: 2026-03-22T04:41:06.5563725+01:00
updated: 2026-03-23T08:38:08.3268336+01:00
started: 2026-03-23T08:36:54.7902681+01:00
completed: 2026-03-23T08:36:54.7902681+01:00
tags:
    - ui
    - agent
    - scope:copilot
    - docs
    - type:docs
parent: 929
depends_on:
    - 941
class: standard
---

## Context

Create `.github/skills/frontend-design/` as an OwlBear-owned skill package that adapts the curated guidance from `docs/research/impeccable-design-skills.md` without copying Impeccable verbatim into always-on instructions. This task owns only the skill package itself; the `frontend.instructions.md` handoff remains in #937 and the anti-pattern taxonomy remains in #938.

## Acceptance Criteria

- [ ] Create `.github/skills/frontend-design/SKILL.md` with YAML frontmatter loadable by `SkillRegistry`, `name: frontend-design`, a non-empty description, and a top-of-body design-context section that asks for target audience, primary use cases/jobs, and brand personality or tone.
- [ ] Create exactly seven OwlBear-authored reference files under `.github/skills/frontend-design/references/`: `typography.md`, `color-and-contrast.md`, `spatial-design.md`, `motion-design.md`, `interaction-design.md`, `responsive-design.md`, and `ux-writing.md`.
- [ ] The skill body links to the seven local `references/*.md` files using OwlBear's `references/` directory naming and does not use Impeccable's singular `reference/` layout.
- [ ] No file under `.github/skills/frontend-design/` mentions `.impeccable.md`, `/teach-impeccable`, or provider-specific slash-command/setup instructions.
- [ ] `SKILL.md` and the seven reference files are OwlBear adaptations, not verbatim copies of Impeccable or Anthropic source text.
- [ ] Attribution inside `.github/skills/frontend-design/` credits both Impeccable and Anthropic, either in `NOTICE.md` or in a clearly marked attribution section in `SKILL.md`.
- [ ] Scope is limited to `.github/skills/frontend-design/**` for the skill package; `frontend.instructions.md` handoff work stays in #937 and anti-pattern taxonomy work stays in #938.

See `docs/research/impeccable-design-skills.md` and `docs/research/frontend-design-skill-implementation-gate.md`.

[[2026-03-22]] Sun 17:22

## Research

- Docs-only scope: add `.github/skills/frontend-design/SKILL.md`, seven adapted references, and an attribution notice.
- Keep the `frontend.instructions.md` handoff in #937 and the anti-pattern taxonomy in #938; do not duplicate either scope inside #934.
- Replace Impeccable-specific `.impeccable.md`, `/teach-impeccable`, and provider command references with upfront audience, use-case, and tone questions.
- Use OwlBear's `references/` directory naming rather than Impeccable's singular `reference/`.
- Verification impact: the discovered skill set shifts from 19 to 20; see `tests/test_skills.py` and `tests/test_project_definition_skill.py`.
- Follow-up created: #941 Add RED tests for frontend-design skill discovery and reference pack.
- Source ledger updated in `docs/sources/overview.md`.
- Evidence: `docs/research/frontend-design-skill-implementation-gate.md`

[[2026-03-22]] Sun 17:27

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add `.github/skills/frontend-design/SKILL.md` | Too vague on frontmatter and the design-context contract | Rewrote to require loadable frontmatter, a non-empty description, and three explicit context questions |
| Add adapted reference files for typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, and ux-writing | Missing exact file paths and enforceable count | Rewrote to require seven named files under `.github/skills/frontend-design/references/` |
| Add upfront design-context questions for audience, use cases, and tone | Good intent, but placement and scope were not verifiable | Folded into the `SKILL.md` contract as top-of-body audience, use-case, and tone prompts |
| Remove Impeccable-specific command references and teach-impeccable dependency | Needed concrete forbidden strings | Rewrote to ban `.impeccable.md`, `/teach-impeccable`, and provider-specific slash-command/setup text inside the skill package |
| Preserve attribution to Impeccable and Anthropic in the skill or a notice file | Acceptable direction, but storage location was ambiguous | Rewrote to allow `NOTICE.md` or a clearly marked attribution section in `SKILL.md` |

### Architecture Notes

- Single domain: `agent-config`/docs only. The task targets `.github/skills/frontend-design/**` and does not absorb the `frontend.instructions.md` handoff from #937 or the anti-pattern taxonomy from #938.
- Pattern to follow: `.github/skills/excalidraw-diagram/SKILL.md` already uses a resource-backed skill with relative `references/` links, which matches the proposed packaging.
- Verification seam: `tests/test_skills.py` currently asserts 19 discovered skills, and `tests/test_project_definition_skill.py` shows the skill-specific frontmatter/content test style. Adding this skill changes that contract, so #934 now depends on RED task #941 before it becomes dispatchable.
- Failure-mode map skipped: this task changes agent configuration content, not application code paths.

### Changes Made

- Claimed #934 as `architect-934`
- Rewrote task body with precise file-level AC and scope boundaries
- Added dependency on #941
- Advanced #934 to `todo` with dependency gating intact

### Dependencies

- Added: #941 as the RED predecessor for skill-discovery and reference-pack verification
- Verified: resource-backed skill pattern exists in `.github/skills/excalidraw-diagram/SKILL.md`
- Verified: real-skill discovery assertions live in `tests/test_skills.py`; skill-specific content assertions live in `tests/test_project_definition_skill.py`

[[2026-03-22]] Sun 22:18

## Test-Writer Notes

- Non-implementation task (tagged docs, type:docs) — no tests applicable.
- Task creates .github/skills/frontend-design/ skill package files (SKILL.md, 7 reference files, attribution).
- Passing through to builder.

[[2026-03-23]] Mon 00:18

## Review Evidence - AC4 FAIL: .github/skills/frontend-design/NOTICE.md line 14 contains forbidden strings .impeccable.md and /teach-impeccable. pytest: 45 passed. ruff: clean

[[2026-03-23]] Mon 00:18

- pytest: uv run pytest tests/test_frontend_design_skill.py tests/test_skills.py -q --tb=short => 45 passed, 0 failed, 2 warnings.

[[2026-03-23]] Mon 00:18

- ruff: uv run ruff check tests/test_frontend_design_skill.py tests/test_skills.py => All checks passed.

[[2026-03-23]] Mon 00:18

- Commit scope check: git show --name-only 0311f39 touches only .github/skills/frontend-design/** (SKILL.md, NOTICE.md, and 7 references).

[[2026-03-23]] Mon 00:18

- AC mapping: AC1 PASS, AC2 PASS, AC3 PASS, AC4 FAIL, AC5 PASS (manual spot-check), AC6 PASS, AC7 PASS.

[[2026-03-23]] Mon 00:18

- FAIL reason: .github/skills/frontend-design/NOTICE.md line 14 explicitly mentions forbidden strings .impeccable.md and /teach-impeccable. Confidence .96.

[[2026-03-23]] Mon 00:47

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about missing test — AC4 forbidden-strings violation in NOTICE.md not caught by existing tests
- Added: 3 new failing tests in TestFromAC_ForbiddenStrings (tests/test_frontend_design_skill.py)
  - test_no_file_mentions_dotimpeccable_md
  - test_no_file_mentions_teach_impeccable
  - test_forbidden_strings_not_present_together
- Preserved: 12 existing tests (all PASS)
- ruff: clean
- AC coverage: AC4 forbidden-strings gap now covered
| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC4: no .impeccable.md in any file | test_no_file_mentions_dotimpeccable_md | error |
| AC4: no /teach-impeccable in any file | test_no_file_mentions_teach_impeccable | error |
| AC4: neither forbidden string anywhere | test_forbidden_strings_not_present_together | boundary |

[[2026-03-23]] Mon 02:51

## Builder Notes

- Files changed: .github/skills/frontend-design/NOTICE.md (1 line)
- Tests: 48 passed (15 frontend-design + 33 test_skills), 0 failed
- Lint: ruff clean
- Evidence: 3 previously-failing TestFromAC_ForbiddenStrings tests now pass
- Fixes applied: Rewrote NOTICE.md line 14 without forbidden strings

[[2026-03-23]] Mon 04:29

## Review Evidence

## Review: #934 - frontend-design skill package

### Test Results

- `uv run pytest tests/test_frontend_design_skill.py tests/test_skills.py -q --tb=short` => 48 passed, 0 failed, 2 warnings.
- Broader sanity run (`... + tests/test_project_definition_skill.py`) showed 1 failure in `test_user_invokable_false_in_frontmatter`; treated as out-of-scope for #934.

### Lint Results

- `uv run ruff check tests/test_frontend_design_skill.py tests/test_skills.py` => All checks passed.

### Coverage

- Scoped run with bare `--cov` passed; `src/owlbear/skills/registry.py` reported 100% in that run.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| SKILL frontmatter + design-context prompts | Frontmatter tests in `TestFromAC_FrontendDesignSkillPackage` | No (design-context prompt contract not asserted) | LAX |
| Exactly seven reference files | `test_*_reference_exists`, `test_all_seven_reference_files_exist` | Yes | COVERED |
| SKILL links use `references/*.md` and avoid `reference/` | none | - | MISSING |
| Forbidden strings + provider slash-command/setup clause | `TestFromAC_ForbiddenStrings` | Partial only (literal strings only) | LAX |
| Adaptation (not verbatim copy) | none | - | MISSING |
| Attribution includes Impeccable + Anthropic | none | - | MISSING |
| Scope limited to `.github/skills/frontend-design/**` | none | - | MISSING |

Critical result: FAIL (MISSING AC coverage present; no `TestBuilderDiscovered` compensating tests).

#### Security Review

- No security issues found (markdown-only change scope).

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_frontend_design_skill.py::TestFromAC_*` | Builder retry commit `3b387bb` changed only `.github/skills/frontend-design/NOTICE.md` | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact frontmatter/file assertions. |
| Negative/error paths | ADEQUATE | Forbidden-string negatives covered; other AC negatives absent. |
| Mutation reasoning | WEAK | Removing link/attribution/prompt requirements still passes tests. |
| Test independence | STRONG | File-read assertions, no shared mutable state. |
| Descriptive names | STRONG | Scenario-specific naming. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- Missing tests for design-context prompt contract.
- Missing tests for SKILL link layout (`references/*.md` and no `reference/`).
- Missing tests for attribution requirement.
- Missing tests for provider-specific slash-command/setup-instruction clause.
- Missing tests for scope-boundary AC.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| SKILL frontmatter + prompts | `SKILL.md` has name/description + Design Context prompts | Prompt checks missing | FAIL |
| Seven reference files | references dir count=7 with required names | Yes | PASS |
| `references/*.md` links and no singular `reference/` in SKILL | links present in `SKILL.md`; no `reference/` match in SKILL | none | FAIL |
| Forbidden strings / slash-command clause | no `.impeccable.md` or `/teach-impeccable` matches in package scan | partial | FAIL |
| Adaptation (not verbatim) | adaptation headers + NOTICE statement | none | FAIL |
| Attribution to both sources | NOTICE source table includes both | none | FAIL |
| Scope limited to package files | `git show --name-only 0311f39` and `git show --name-only 3b387bb` only list package files | none | FAIL |

### Verdict: FAIL

### Action Taken

- Moved #934 to `todo`.

[[2026-03-23]] Mon 05:32

## Test-Writer Notes (retry #2)

- Retry reason: reviewer FAIL cited MISSING test coverage for AC1 prompts, AC3 link layout, AC4 setup clause, AC5 adaptation, AC6 attribution, AC7 scope
- Added: 19 new tests in 6 new classes (tests/test_frontend_design_skill.py)
  - TestFromAC_DesignContextPrompts (5 tests) -- AC1 design-context questions
  - TestFromAC_SkillLinkLayout (3 tests) -- AC3 references/ link format
  - TestFromAC_ProviderSetupInstructions (2 tests) -- AC4 setup clause extension
  - TestFromAC_OwlBearAdaptation (3 tests) -- AC5 no-verbatim / substantive content
  - TestFromAC_Attribution (3 tests) -- AC6 Impeccable + Anthropic credit
  - TestFromAC_ScopeBoundary (3 tests) -- AC7 only expected files in package
- Preserved: 15 original tests + 3 first-retry tests, all PASS
- Total: 34 tests, 34 PASS; all new tests PASS (implementation was already correct)
- Note: new tests act as regression net; they PASS because the builder's code already satisfies all AC lines
- ruff: clean

[[2026-03-23]] Mon 06:14

## Builder Notes (retry #3 — verification pass)

- Files changed: None — implementation already complete from prior builder commits (0311f39, 3b387bb)
- Tests: 67 passed (34 frontend-design + 33 test_skills), 0 failed; exit 0
- Coverage: skills/registry.py 100%
- Lint: ruff clean on tests/test_frontend_design_skill.py and tests/test_skills.py
- Evidence: all 34 TestFromAC_* tests pass including 19 from test-writer retry #2
- Fixes applied: None — prior builder fix (3b387bb) and test-writer retry #2 (b06e7ab) already satisfy all AC lines

[[2026-03-23]] Mon 07:11

## Review Evidence

## Review: #934 - frontend-design skill package

### Test Results

- pytest scoped: uv run pytest tests/test_frontend_design_skill.py tests/test_skills.py -q --tb=short => 67 passed, 0 failed, 2 warnings.
- broader sanity run including tests/test_project_definition_skill.py => 1 failure at tests/test_project_definition_skill.py:47 (out of scope for #934).

### Lint Results

- ruff: uv run ruff check tests/test_frontend_design_skill.py tests/test_skills.py => All checks passed.

### Coverage

- scoped bare --cov run passed; src/owlbear/skills/registry.py reported 100%.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| SKILL frontmatter + design-context prompts | TestFromAC_FrontendDesignSkillPackage plus TestFromAC_DesignContextPrompts | Yes | COVERED |
| Exactly seven reference files with required names | test_*_reference_exists, test_all_seven_reference_files_exist, test_skill_package_contains_only_expected_files | Yes | COVERED |
| SKILL links to references/*.md and not reference/ | TestFromAC_SkillLinkLayout::* | Yes | COVERED |
| Forbidden strings and provider slash-command/setup instruction bans | TestFromAC_ForbiddenStrings::*, TestFromAC_ProviderSetupInstructions::* | Yes | COVERED |
| OwlBear adaptation and no verbatim copy contract | TestFromAC_OwlBearAdaptation::* | Yes | COVERED |
| Attribution credits Impeccable and Anthropic | TestFromAC_Attribution::* | Yes | COVERED |
| Scope remains frontend-design package; #937 and #938 scopes not absorbed | TestFromAC_ScopeBoundary::* plus commit file-scope checks | Yes | COVERED |

#### Security Review

- No security issues found in scope (markdown content and tests only).

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| tests/test_frontend_design_skill.py TestFromAC classes | Builder commits 0311f39 and 3b387bb did not modify test file | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact frontmatter fields, exact filenames, exact forbidden-pattern checks. |
| Negative/error paths | STRONG | Explicit negatives for singular reference/, forbidden strings, slash-command lines, setup headings, and scope drift. |
| Mutation reasoning | ADEQUATE | Deleting required links/prompts/attribution or adding forbidden patterns fails targeted tests. |
| Test independence | STRONG | Filesystem read assertions only; no shared mutable state. |
| Descriptive names | STRONG | Names map directly to AC scenarios. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- No significant untested behavioral paths for #934 scope.

### Pass 2 - INFORMATIONAL

- Out-of-scope baseline failure remains in tests/test_project_definition_skill.py::TestProjectDefinitionSkillFrontmatter::test_user_invokable_false_in_frontmatter.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| SKILL.md loadable frontmatter (name + non-empty description) and top-of-body design context prompts | .github/skills/frontend-design/SKILL.md lines 2, 3, 11, 15, 16, 17 | TestFromAC_FrontendDesignSkillPackage::*, TestFromAC_DesignContextPrompts::* | PASS |
| Exactly seven required reference files under references/ | .github/skills/frontend-design/references directory contains required 7 files only | test_all_seven_reference_files_exist, test_skill_package_contains_only_expected_files | PASS |
| SKILL links use references/*.md and avoid singular reference/ | .github/skills/frontend-design/SKILL.md lines 31-37; no (reference/...) link matches in SKILL | TestFromAC_SkillLinkLayout::* | PASS |
| No .impeccable.md, no /teach-impeccable, no provider slash-command/setup instructions in package | Search across .github/skills/frontend-design/** returned no matches for forbidden patterns | TestFromAC_ForbiddenStrings::*, TestFromAC_ProviderSetupInstructions::* | PASS |
| SKILL + references are OwlBear adaptations, not verbatim copy | .github/skills/frontend-design/NOTICE.md lines 3, 11, 18 and adaptation markers in each reference file line 3 | TestFromAC_OwlBearAdaptation::* | PASS |
| Attribution credits Impeccable and Anthropic | .github/skills/frontend-design/NOTICE.md lines 8-9 | TestFromAC_Attribution::* | PASS |
| Scope stays in frontend-design package; #937/#938 work not absorbed | git show --name-only 0311f39 and 3b387bb touch only .github/skills/frontend-design/** | TestFromAC_ScopeBoundary::* | PASS |

### Verdict: PASS

### Action Taken

- Moving #934 to docs
- Confidence: .93

[[2026-03-23]] Mon 08:05

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Skill file addition; copilot-instructions.md has no skill registry table â€” directory listing at line 139 needs no change |
| 2 | Docstrings | No | N/A | type:docs task â€” no Python modules created or modified |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'Frontend-Design Skill Implementation Gate (Task #934)' present with pbakaus/impeccable and Impeccable website rows |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research docs linked | Yes | Pass | docs/research/impeccable-design-skills.md and docs/research/frontend-design-skill-implementation-gate.md both exist and linked from task body |
| 6 | Scratch files | N/A | Pass | No docs/scratch/934-* files found |

### Files Updated

- None

### Scratch Files Cleaned

- None

[[2026-03-23]] Mon 08:36

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md frontmatter + design-context prompts | SKILL.md L1-17: name: frontend-design, non-empty description, 3 context questions | PASS |
| Seven reference files under references/ | 7 files confirmed: typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, ux-writing | PASS |
| SKILL links use references/*.md, not reference/ | SKILL.md L31-37 all use references/ path | PASS |
| No .impeccable.md or /teach-impeccable in package | grep across package: no matches | PASS |
| OwlBear adaptations, not verbatim copies | NOTICE.md L18 explicit statement + adaptation markers | PASS |
| Attribution credits Impeccable + Anthropic | NOTICE.md L8-9 source table with both | PASS |
| Scope limited to .github/skills/frontend-design/** | git log commits 0311f39, 3b387bb touch only package files | PASS |

### Test Results

- pytest scoped: 67 passed, 0 failed (test_frontend_design_skill.py + test_skills.py)
- pytest full suite: 3871 passed, 121 failed (all failures pre-existing, none in task files)
- ruff (task files): clean

### Architect Quality

- AC specificity: strong (exact file names, forbidden strings, directory layout)
- Edge case gap: forbidden-string-in-attribution context missed, caught by reviewer
- Design direction: correct (excalidraw-diagram pattern, scope boundaries)
- AC quality score: 4/5

### Confidence: .96

### Action: archive

[[2026-03-23]] Mon 08:38

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2513ae8 | chore | kanban/tasks/934-...md | #934 |
