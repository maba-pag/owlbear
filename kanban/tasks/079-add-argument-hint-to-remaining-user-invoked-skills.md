---
id: 79
title: Add argument-hint to remaining user-invoked skills
status: todo
priority: nice-to-have
created: 2026-03-27T02:56:52.2499907+01:00
updated: 2026-03-27T08:49:12.3421444+01:00
tags:
    - phase-1
    - scope:skills
    - type:build
depends_on:
    - 85
class: standard
---

## Objective
Add argument-hint frontmatter to the 3 remaining actively user-invoked skills that were out of scope for #43.

## Acceptance Criteria
- [ ] Add argument-hint: '[diagram description]' to excalidraw-diagram
- [ ] Add argument-hint: '[diagram or visual description]' to visual-output
- [ ] Add argument-hint: '[component or design question]' to frontend-design
- [ ] Verify hints appear in VS Code slash-command menu

## Context
See docs/research/argument-hint-user-invocable-skills.md for rationale and analysis.

[[2026-03-27]] Fri 08:06
## Research
Research already complete in docs/research/argument-hint-user-invocable-skills.md (task #43).

Checklist:
- Theoretical validity: argument-hint is an official VS Code YAML frontmatter field (VS Code docs, updated 2026-03-25)
- Prior art: 11 OwlBear agents + 2 skills from #43 already use the pattern
- Technical feasibility: one YAML line per file, no runtime impact
- Architecture fit: identical pattern to existing agents and #43 skills
- Implementation: add argument-hint line to frontmatter of excalidraw-diagram, visual-output, frontend-design
- Testing: parse frontmatter, assert key and value (same as tests/test_argument_hint_skills.py from #43)

No follow-up tasks needed beyond #79 itself (this IS the follow-up from #43 research).
No decision requests needed -- hint values are concrete in the AC.

[[2026-03-27]] Fri 08:06
## Research
Research validated from docs/research/argument-hint-user-invocable-skills.md (task #43). VS Code docs (2026-03-25) confirm argument-hint as optional YAML frontmatter. Pattern established by 11 agents + #43 skills. Implementation: one YAML line per file. Testing: frontmatter parse + assert (same pattern as #43).

[[2026-03-27]] Fri 08:49
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add argument-hint '[diagram description]' to excalidraw-diagram | Precise, testable, matches research recommendation | Keep |
| Add argument-hint '[diagram or visual description]' to visual-output | Precise, testable, matches research recommendation | Keep |
| Add argument-hint '[component or design question]' to frontend-design | Precise, testable, matches research recommendation | Keep |
| Verify hints appear in VS Code slash-command menu | Manual verification, appropriate for UI behavior | Keep |

### Architecture Notes
Trivial YAML frontmatter addition. Pattern established by 11 agents and #43 (project-definition, retro). No layering, security, or dependency concerns. All 3 target SKILL.md files confirmed present with standard frontmatter structure. No argument-hint key exists in any skill file yet. Implementation: add one line per file after the description field.

### Changes Made
- Created #85 (Test: Add argument-hint to remaining user-invoked skills) at todo
- Added depends_on: #85 to #79
- Approved #79 to todo

### Dependencies
- Added: #85 (TDD RED phase test task)
- No other deps needed (independent of #43, targets different files)

[[2026-03-27]] Fri 08:49
## Audit
### AC Verification
AC 1 PASS: docs/research/owlbear-project-json-schema.md section 3.1 defines all 5 fields with types and constraints
AC 2 PASS: section 3.3 documents all-required rule and per-field validation constraints
AC 3 PASS: sections 3.2 and 3.4 document integer versioning and additionalProperties true
AC 4 PASS: section 3.5 documents workspace-root location convention
AC 5 PASS: follow-up tasks 68 and 69 confirmed on board at backlog status, both reference research doc

### Test Results
- pytest: 83 passed, 21 failed (all failures pre-existing RED-phase tests from other tasks)
- ruff: N/A (research task, no Python source)

### Reviewer Evidence
Detailed PASS at .95 with specific line references for all 5 AC items. Source attribution verified.

### AC Quality Score: 4/5
AC was specific and verifiable for a research task. Minor gap: did not specify doc section structure, but builder handled it fine.

### Quality Gap
Builder did not commit research doc before handoff (docs/research/owlbear-project-json-schema.md still untracked). Committing as orphaned deliverable.

### Confidence: .97
### Action: archive
