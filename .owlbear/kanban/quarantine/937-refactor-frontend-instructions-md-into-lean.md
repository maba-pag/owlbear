---
id: 937
title: Refactor frontend.instructions.md into lean guardrails plus skill handoff
status: archived
priority: nice-to-have
created: 2026-03-22T04:41:31.5653176+01:00
updated: 2026-03-26T02:28:10.5886114+01:00
started: 2026-03-26T02:27:45.6553106+01:00
completed: 2026-03-26T02:27:45.6553106+01:00
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

Keep .github/instructions/frontend.instructions.md as the scoped, always-on baseline while moving deep design fluency into the frontend-design skill researched in docs/research/impeccable-design-skills.md.

## Acceptance Criteria

- [ ] Keep repo-level rules in .github/instructions/frontend.instructions.md: design-system choice, accessibility minimums, component hygiene, responsive/testing guardrails
- [ ] Add a short handoff telling Copilot to use the frontend-design skill for deeper typography, color, motion, interaction, responsive, and UX-writing guidance when relevant
- [ ] Avoid duplicating the seven reference files inside the instruction file
- [ ] Preserve the current applyTo scope

See docs/research/impeccable-design-skills.md.

[[2026-03-24]] Tue 02:56

## Research

- Scope: validate #937 AC against the completed frontend-design skill (#934) and VS Code docs.

- Finding: frontend.instructions.md is already lean (776 tokens). No content removal needed.

- Change: add a 2-3 line handoff section after the intro paragraph using the name+purpose pattern matching python.instructions.md precedent.

- Handoff pattern: 'For deeper design guidance ... use the frontend-design skill.'

- Overlap: a11y and responsive sections overlap with skill at surface level but serve different purposes (enforcement vs guidance). Keep both.

- Research doc: docs/research/frontend-instructions-skill-handoff.md

- Sources updated in docs/sources/overview.md.

- No new follow-up tasks needed - #937 AC already covers the recommended change.

[[2026-03-24]] Tue 13:18

## Architecture Review

**Verdict:** APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: Keep repo-level rules (design-system, a11y, component, responsive, testing) | Verifiable: reviewer checks all 5 sections remain post-edit. Research confirms no content removal needed (776 tokens already lean). | Keep as-is |
| AC2: Add short handoff to frontend-design skill | Verifiable: reviewer checks for handoff paragraph after intro. Research specifies name+purpose pattern and top placement. | Keep as-is |
| AC3: Avoid duplicating the 7 reference files | Verifiable: reviewer greps for content copied from references/. | Keep as-is |
| AC4: Preserve current applyTo scope | Verifiable: reviewer diffs YAML frontmatter applyTo value. | Keep as-is |

### Architecture Notes

- This is a docs-only task (type:docs) editing .github/instructions/frontend.instructions.md. No application code involved. TDD does not apply.
- Dependency #934 (frontend-design skill) is archived â€” the skill SKILL.md and 7 reference files exist at .github/skills/frontend-design/.
- Handoff pattern follows established precedent: python.instructions.md hands off to pytest-and-linting skill with name+purpose pattern.
- Research doc (docs/research/frontend-instructions-skill-handoff.md) is thorough â€” overlap analysis, placement rationale, and pattern comparison all documented.
- No module layering, security, or failure mode concerns â€” this is a markdown file edit.

### Changes Made

- Claimed #937 as copilot-architect
- Appended this architecture review
- Moved #937 from backlog to todo

### Dependencies

- Verified: #934 (frontend-design skill) â€” archived, skill exists at .github/skills/frontend-design/SKILL.md
- No missing dependencies

[[2026-03-24]] Tue 13:18

## Architecture Review

**Verdict:** APPROVE

### AC Assessment

- AC1 (keep repo-level rules): Verifiable. Reviewer checks 5 sections remain. Already lean at 776 tokens.
- AC2 (add handoff): Verifiable. Reviewer checks for handoff paragraph after intro. Name+purpose pattern.
- AC3 (no duplication): Verifiable. Reviewer greps for copied reference content.
- AC4 (preserve applyTo): Verifiable. Reviewer diffs YAML frontmatter.

### Architecture Notes

- Docs-only task (type:docs). No application code, TDD does not apply.
- Dependency #934 (frontend-design skill) archived. Skill exists at .github/skills/frontend-design/SKILL.md.
- Handoff pattern matches python.instructions.md precedent.
- Research doc thorough: overlap analysis, placement rationale, pattern comparison.

### Changes Made

- Claimed and approved #937.

### Dependencies

- Verified: #934 archived, skill files present.

[[2026-03-25]] Wed 22:09

## Test-Writer Notes

- Non-implementation task (tagged type:docs) - no tests applicable.
- Passing through to builder.

[[2026-03-26]] Thu 00:54

## Builder Notes

- Files changed: .github/instructions/frontend.instructions.md
- Tests: 55 passed in scoped frontend slices (3 plus 52).
- Lint: ruff check .github/instructions/frontend.instructions.md passed.
- Evidence: pytest tests/test_frontend_design_skill.py -k ScopeBoundary passed with 3 tests; pytest tests/test_944_frontend_audit_prompt.py tests/test_945_frontend_normalize_prompt.py passed with 52 tests; ruff check on frontend.instructions.md reported all checks passed.
- Fixes applied: added a top-placed Design guidance handoff to the frontend-design skill covering typography, color, spatial layout, motion, interaction, responsive patterns, and UX writing; existing guardrails retained; applyTo unchanged.
- TDD note: no task-specific TestFromAC tests exist for #937 instruction handoff wording, so nearest frontend prompt and skill boundary suites were used.

[[2026-03-26]] Thu 01:11

## Review Evidence

### Test Results

- pytest frontend skill scope boundary slice passed on rerun: 3 passed, 51 deselected, 1 warning.
- pytest frontend prompt regression slice passed: 52 passed.
- Initial scope-boundary run was interrupted by terminal-state KeyboardInterrupt, then reran cleanly with plugin autoload disabled.

### Lint Results

- ruff check on .github/instructions/frontend.instructions.md passed with no findings.

### Coverage

- Not applicable. This task changes one markdown instruction file and no Python module behavior.

### Test-Writer Audit

- No task-specific TestFromAC classes exist for #937. The test-writer correctly marked the task as docs-only and not suitable for new RED-phase tests.

### Security And Data Safety

- Reviewed the latest git diff for .github/instructions/frontend.instructions.md. The change is limited to a short Design guidance handoff section.
- No executable code, dependency, secret-handling, path, shell, serialization, or persistence changes were introduced.

### Test Quality

- Assertion specificity: STRONG. The prompt and skill boundary slices use concrete content and path assertions rather than loose existence checks.
- Negative and boundary coverage: ADEQUATE for this docs-only task. The skill boundary slice guards against scope bleed into the skill package, and prompt slices continue to validate related frontend command contracts.
- Manual mutation reasoning: ADEQUATE. Removing the new handoff text or moving scope into the skill package would be visible by direct file diff and boundary checks.
- Test independence: STRONG. The exercised tests read files directly and do not rely on shared mutable state.
- Test names: STRONG. The selected tests describe the contract they enforce.

### AC Compliance

- AC1 PASS: .github/instructions/frontend.instructions.md still contains the repo-level guardrail sections for Design system, Accessibility, Component structure, Responsive design, and Testing at lines 15, 27, 40, 48, and 55. The latest git diff for the file showed no removals outside the added handoff.
- AC2 PASS: The new Design guidance handoff is present at lines 10 to 13, including the explicit route to the frontend-design skill and the covered areas at lines 12 to 13.
- AC3 PASS: The latest git diff shows only the short handoff addition. Targeted review against the seven frontend-design reference files found none of their headings or sampled opening sentences copied into frontend.instructions.md.
- AC4 PASS: applyTo remains unchanged at line 2. The latest git diff for the file contains no frontmatter changes.

### Verdict

- PASS with confidence .95.

[[2026-03-26]] Thu 01:21

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Docs-internal refactor; copilot-instructions.md already lists frontend-design skill |
| 2 | Docstrings complete | No | N/A | No Python files changed |
| 3 | sources/overview.md | No | N/A | No new external patterns adopted into OwlBear code |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/frontend-instructions-skill-handoff.md exists, references task 937 |
| 6 | Scratch files | N/A | Pass | No docs/scratch/937-* files found |

### Files Updated

- None

### Scratch Files Cleaned

- None

[[2026-03-26]] Thu 02:28

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 97f5c0e | chore | kanban/tasks/937-*.md | #937 |
