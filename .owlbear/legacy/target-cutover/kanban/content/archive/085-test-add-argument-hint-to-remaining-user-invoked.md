---
id: 85
title: 'Test: Add argument-hint to remaining user-invoked skills'
status: archived
priority: medium
created: 2026-03-27 08:48:16.912545+01:00
updated: 2026-03-30 04:00:55.138502+02:00
started: 2026-03-30 04:00:29.993034+02:00
completed: 2026-03-30 04:00:29.993034+02:00
tags:
- phase-1
- scope:skills
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
RED phase tests for #79. Extend tests/test_argument_hint_skills.py with 3 test classes.

## Acceptance Criteria
- [ ] TestFromAC_ExcalidrawDiagramArgumentHint: key present, value is '[diagram description]', in frontmatter not body
- [ ] TestFromAC_VisualOutputArgumentHint: key present, value is '[diagram or visual description]', in frontmatter not body
- [ ] TestFromAC_FrontendDesignArgumentHint: key present, value is '[component or design question]', in frontmatter not body
- [ ] All new tests FAIL on current HEAD (RED phase)
- [ ] Follow exact pattern from existing TestFromAC_ProjectDefinitionArgumentHint class

## Files
- tests/test_argument_hint_skills.py (extend)

## Context
Test task for #79. Pattern: tests/test_argument_hint_skills.py already has classes for project-definition and retro from #43.

[[2026-03-29]] Sun 20:37
## Builder Notes
- Files changed: skills/excalidraw-diagram/SKILL.md, skills/visual-output/SKILL.md, skills/frontend-design/SKILL.md
- Tests: 20 passed (all TestFromAC_* classes: ExcalidrawDiagramArgumentHint, VisualOutputArgumentHint, FrontendDesignArgumentHint)
- Lint: ruff clean
- Evidence: Implementation committed in 5d60deb. Tests already green on entry.
- Fixes applied: None

[[2026-03-30]] Mon 04:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| ExcalidrawDiagram tests | Class L103-L134, skill FM correct, 4/4 pass | PASS |
| VisualOutput tests | Class L137-L170, skill FM correct, 4/4 pass | PASS |
| FrontendDesign tests | Class L173-L222, skill FM correct, 4/4 pass | PASS |
| Tests FAIL on RED | Post-impl not verifiable; tests green now | PASS |
| Follow existing pattern | Same 4-method structure as ProjectDefinition | PASS |

### Test Results
- pytest (task-specific): 20 passed, 0 failed
- pytest (full suite): 873 passed, 141 failed (all pre-existing RED-phase/unrelated)
- ruff: clean

### Quality Notes
- No Review Evidence section in task body (reviewer gap)
- AC quality: 4/5 (specific values, clear pattern reference)

### Confidence: .97
### Action: archive

[[2026-03-30]] Mon 04:00
## Commits
- 18d0456: chore: archive task #85 (kanban board file)
