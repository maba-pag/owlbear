---
id: 823
title: 'Close #813 as won''t-do per re-export research'
status: archived
priority: nice-to-have
created: 2026-03-15T09:11:29.009987+01:00
updated: 2026-03-26T06:24:19.140217+01:00
started: 2026-03-16T05:15:28.5689751+01:00
completed: 2026-03-26T06:24:05.6771957+01:00
tags:
    - audit
    - scope:core
class: standard
---

Task #813 (add re-exports to 5 packages) is blocked by architect and contradicted by empirical evidence (0/64 consumers use short-path imports). Mark #813 as archived/won't-do. Update #549 description to reflect the resolved decision. See docs/research/core-init-reexport-removal.md section 3.2.

[[2026-03-16]] Mon 05:15
## Research Closure
#813 archived as won't-do (2026-03-16). Decision A resolved. This meta-task is complete.

[[2026-03-26]] Thu 06:24
## Audit
### AC Verification
This is a meta/housekeeping task (no code changes). AC items:

| AC Item | Evidence | Status |
|---------|----------|--------|
| Mark #813 as archived/won't-do | #813 status=archived, audit section present, decision trail complete | PASS |
| Update #549 description | #549 archived with Architecture Review section referencing resolved decision | PASS |
| Reference docs/research/core-init-reexport-removal.md section 3.2 | File exists, section 3.2 present (line 34), committed (0444ded) | PASS |
| Decision request resolved | docs/decisions/resolved/813-re-export-feature-gate.md exists | PASS |

### Test Results
- pytest: 91 failed, 4515 passed, 2 skipped (pre-existing failures per repo memory, no code changes in this task)
- ruff: 163 pre-existing issues (160 unused-noqa, 2 line-too-long, 1 blind-except), no new issues

### AC Quality Score: 4/5
AC was clear and specific for a meta-task: three concrete deliverables. Minor: could have explicitly stated decision request resolution as an AC item.

### Confidence: .95
### Action: archive

[[2026-03-26]] Thu 06:24
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8064154 | chore | kanban/tasks/823-*.md | #823 |
