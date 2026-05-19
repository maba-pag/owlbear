---
id: 946
title: Add frontend-polish prompt built on frontend-design skill
status: archived
priority: nice-to-have
created: 2026-03-22T19:01:48.51761+01:00
updated: 2026-03-25T05:24:33.7432142+01:00
started: 2026-03-25T05:24:12.8720739+01:00
completed: 2026-03-25T05:24:12.8720739+01:00
tags:
    - ui
    - agent
    - scope:copilot
    - docs
    - type:docs
parent: 930
depends_on:
    - 934
    - 943
class: standard
---

## Context

Pilot the finishing step in the Impeccable-style workflow for OwlBear: a prompt that performs a final frontend detail pass after the main work is done.

See docs/research/impeccable-command-patterns.md.

## Acceptance Criteria

- [ ] Add `.github/prompts/frontend-polish.prompt.md` with description-only frontmatter and an optional scope input.
- [ ] Prompt reads `docs/design-context.md` and references the frontend-design skill by relative path.
- [ ] Prompt focuses on final-detail checks for spacing, interaction states, copy consistency, focus treatment, loading or empty states, and mobile readiness.
- [ ] Prompt treats polish as a last pass, not a redesign, and includes final verification steps before completion.

[[2026-03-24]] Tue 17:22

## Research

- Doc: docs/research/frontend-polish-prompt.md
- Dependencies satisfied: #934 (archived), #943 (design-context prompt exists)
- Key findings:
  - Impeccable /polish has 11 categories; OwlBear AC scopes to 6 (spacing, interaction states, copy consistency, focus treatment, loading/empty states, mobile readiness). KISS/YAGNI: keep AC scope.
  - Implementation is a single .prompt.md file with description-only frontmatter and optional scope input, matching design-context.prompt.md format.
  - Prompt should reference frontend-design skill and 4 specific reference files (interaction-design, spatial-design, responsive-design, ux-writing) for on-demand depth.
  - Must include redesign guardrails and final verification steps (adapted from Impeccable).
- No new follow-up tasks needed; #946 and siblings (#944, #945) already created by #930.
- Confidence: .92
- Source ledger updated: docs/sources/overview.md

[[2026-03-24]] Tue 17:48

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: Add .github/prompts/frontend-polish.prompt.md with description-only frontmatter and optional scope input | Clear, verifiable. File location, frontmatter format, and input syntax all specified. Matches existing design-context.prompt.md pattern. | Keep |
| AC2: Prompt reads docs/design-context.md and references frontend-design skill by relative path | Clear. The design-context.prompt.md creates docs/design-context.md as its output; polish prompt should reference it conditionally (may not exist yet). Skill reference matches existing pattern. | Keep |
| AC3: Prompt focuses on final-detail checks for spacing, interaction states, copy consistency, focus treatment, loading or empty states, and mobile readiness | 6 specific categories named. Verifiable by file inspection. Research doc maps these to 4 skill reference files (interaction-design, spatial-design, responsive-design, ux-writing). | Keep |
| AC4: Prompt treats polish as a last pass, not a redesign, and includes final verification steps | Clear intent with verifiable guardrails. Research doc provides Impeccable-sourced verification steps to adapt. | Keep |

### Architecture Notes

- This is a type:docs task producing a single .prompt.md file. No source code, no automated tests, no module layering concerns.
- Existing pattern: design-context.prompt.md uses description-only frontmatter and optional input syntax. The builder should follow the same structure.
- The 6 focus areas in AC3 map to frontend-design skill references: spatial-design.md (spacing), interaction-design.md (interaction states, focus treatment), ux-writing.md (copy consistency, loading/empty states), responsive-design.md (mobile readiness).
- docs/design-context.md does not exist yet; it is generated on first run of the design-context prompt. The builder should treat the reference as conditional (when present).
- Research doc at docs/research/frontend-polish-prompt.md is thorough and implementation-ready with .92 confidence.
- TDD not applicable for prompt files; verification is by file inspection per research section 3.6.

### Changes Made

- Approved task, moved to todo

### Dependencies

- Verified: #934 (frontend-design skill) archived
- Verified: #943 (design-context prompt) archived
- No new dependencies needed

[[2026-03-24]] Tue 19:53

## Test-Writer Notes

- Non-implementation task (tagged type:docs) -- no tests applicable.
- Passing through to builder.

[[2026-03-25]] Wed 02:52

## Builder Notes

- Files changed: .github/prompts/frontend-polish.prompt.md
- Tests: No task-specific tests were provided; sanity pytest run reported 22 passed in tests/test_945_frontend_normalize_prompt.py.
- Coverage: Not applicable for markdown prompt-only change.
- Lint: Ruff sanity check passed on tests/test_945_frontend_normalize_prompt.py.
- Evidence: Prompt includes description-only frontmatter, optional scope input, docs/design-context.md reference, relative frontend-design skill links, six polish categories, redesign guardrails, and final verification steps.
- Fixes applied: Added frontend-polish prompt as last-pass finishing workflow.

[[2026-03-25]] Wed 03:33

## Review Evidence

### Review: #946 - Add frontend-polish prompt built on frontend-design skill

### Test Results

- pytest: 22 passed, 0 failed on tests/test_945_frontend_normalize_prompt.py.
- Evidence: isolated rerun with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and PYDANTIC_DISABLE_PLUGINS=**all** completed in 0.19s. This is a sanity slice for adjacent prompt-contract coverage; #946 itself has no task-owned tests because it is a prompt-only docs task.

### Lint Results

- ruff: All checks passed on tests/test_945_frontend_normalize_prompt.py.

### Coverage

- N/A for this prompt-only docs task. No Python module or task-owned test surface was added.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- N/A for #946. The task is a single .prompt.md artifact and the task body positioned verification as file inspection, not TDD. No TestFromAC classes or task-owned tests exist.

#### Security Review

- No security issues found. The change is a static markdown prompt file with relative workspace references only; no secret handling, shell execution, path construction, or deserialization logic is introduced.

#### Test Integrity

- N/A for #946. No TestFromAC classes exist for this task.

#### Test Quality

- N/A for #946. There are no task-owned tests to assess; review is based on direct prompt inspection plus adjacent prompt-sanity pytest.

#### Data Safety

- No data safety issues found. The prompt adds no persistence, concurrency, or unbounded-input behavior.

#### Implementation-Aware Test Gaps

- No significant untested paths. The deliverable is static prompt content, and all acceptance criteria are directly verifiable by file inspection.

### Pass 2 - INFORMATIONAL

- The initial shared-shell pytest attempt ended with a spurious KeyboardInterrupt during startup. An isolated rerun passed cleanly, so that first interruption was terminal noise rather than task risk.
- No other informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Add .github/prompts/frontend-polish.prompt.md with description-only frontmatter and an optional scope input | .github/prompts/frontend-polish.prompt.md lines 1-3 contain only YAML fences plus description, line 10 defines Optional scope input using ${input:scope...}, and git blame shows the file was introduced entirely by commit 6572e76. | N/A (file inspection) | PASS |
| Prompt reads docs/design-context.md and references the frontend-design skill by relative path | .github/prompts/frontend-polish.prompt.md lines 14-21 read docs/design-context.md if present and reference ../skills/frontend-design/SKILL.md plus spatial-design, interaction-design, responsive-design, and ux-writing relative references. file_search confirmed those skill files exist under .github/skills/frontend-design/. | N/A (file inspection) | PASS |
| Prompt focuses on final-detail checks for spacing, interaction states, copy consistency, focus treatment, loading or empty states, and mobile readiness | .github/prompts/frontend-polish.prompt.md lines 39-57 enumerate exactly those six categories with concrete polish checks for each. | N/A (file inspection) | PASS |
| Prompt treats polish as a last pass, not a redesign, and includes final verification steps before completion | .github/prompts/frontend-polish.prompt.md lines 7-8 frame polish as the last frontend detail pass, lines 59-68 define verification steps before completion, and lines 72-77 explicitly forbid redesign and broader structural changes. | N/A (file inspection) | PASS |

### Verdict: PASS

### Action Taken

- Claimed task #946 as reviewer-github-copilot-946.
- Appended review evidence.
- Moving task to docs.

[[2026-03-25]] Wed 03:57

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Task adds a .prompt.md file. The Command Surface Selection table is illustrative, not an exhaustive inventory. No behavior, API, or convention change. |
| 2 | Docstrings | No | N/A | No Python modules created or modified. Pure .prompt.md addition. |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'Frontend-Polish Prompt Research (Task #946)' present with two rows: Impeccable /polish skill (Apache-2.0) and VS Code Prompt Files docs (CC-BY-4.0). Confirmed by reading file. |
| 4 | README.md | No | N/A | No CLI commands added or changed. |
| 5 | Research doc | Yes | Pass | docs/research/frontend-polish-prompt.md exists and is linked from task body. Follow-up tasks not needed per research notes (#946 and siblings already created by #930). |

### Files Updated

- None

### Scratch Files Cleaned

- None found (docs/scratch/946-* search returned no results)

[[2026-03-25]] Wed 05:24

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7805f1b | chore | kanban/tasks/946-*.md | #946 |
