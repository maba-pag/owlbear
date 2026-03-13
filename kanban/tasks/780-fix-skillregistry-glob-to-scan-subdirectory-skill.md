---
id: 780
title: Fix SkillRegistry glob to scan subdirectory SKILL.md files
status: in-progress
priority: needed
created: 2026-03-13T14:31:09.6044709+01:00
updated: 2026-03-13T20:44:08.964848+01:00
tags:
    - tooling
    - scope:core
class: standard
---

## Acceptance Criteria
- [ ] _scan() uses glob('*/SKILL.md') instead of glob('*.md')
- [ ] Class docstring and _scan docstring updated to reference subdirectory layout
- [ ] test_skills.py fixtures restructured from flat alpha.md to alpha/SKILL.md layout
- [ ] All existing tests pass (test_skills.py, test_pipeline_e2e.py)
- [ ] list_skills discovers 17 skills when pointed at real .github/skills dir

See docs/research/skillregistry-glob-fix.md for details.

[[2026-03-13]] Fri 20:04
## Research
Recommendation (.95): Change glob('*.md') to glob('*/SKILL.md').
Doc: docs/research/skillregistry-glob-fix.md
Sources: Python pathlib docs, VS Code Agent Skills docs.
Fix is one-line in _scan() + docstring updates + test fixture restructure.

[[2026-03-13]] Fri 20:13
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| _scan() uses glob('*/SKILL.md') | Precise, matches research rec (.95). Verified: 17 subdirs. | Keep |
| Class + _scan docstring updated | Verifiable by inspection. Current docstrings say '*.md'. | Keep |
| test_skills.py fixtures restructured | Clear. Covers all fixtures incl edge cases. | Keep |
| All existing tests pass | Verifiable. test_pipeline_e2e.py already uses subdir layout. | Keep |
| list_skills discovers 17 skills | Verified: 17 SKILL.md files exist. Integration check. | Keep |

### Architecture Notes
- Single domain: skills registry only
- KISS/YAGNI: */SKILL.md most precise pattern
- TDD within task: fixture restructure = RED, glob fix = GREEN
- Downstream unblocks: #774, #775, #781

### Dependencies
- Upstream: none
- Downstream: #774, #775, #781 benefit

[[2026-03-13]] Fri 20:44
## Test-Writer Notes
- Test file: tests/test_skills.py
- Classes: TestFromAC_SubdirGlob, TestFromAC_DocstringsUpdated, TestFromAC_RealSkillsDiscovery
- Tests per category: happy 5, edge 3, error 0, boundary 1, docstring 2
- Total: 11 tests, all FAIL
- ruff: clean
