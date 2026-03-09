---
id: 685
title: 'Task decomposition rules: enforce single-domain tasks at planning level'
status: archived
priority: needed
created: 2026-03-08T15:45:45.4842319+01:00
updated: 2026-03-09T10:44:37.9330853+01:00
started: 2026-03-08T16:26:27.8858251+01:00
completed: 2026-03-09T10:44:37.9330853+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context
Instead of specializing the builder per domain (frontend/backend/database), ensure the planner decomposes tasks so each task is single-domain. The builder stays domain-agnostic -- domain knowledge comes from reading existing code and following patterns. The planner enforces the boundary.

## Acceptance Criteria
- [ ] kanban-planner.agent.md updated: atomicity gate explicitly checks single-domain (one of: backend logic, frontend UI, database schema, CLI, config, test infrastructure, docs)
- [ ] Architect gate (backlog->todo) validates single-domain as part of review
- [ ] agent-common.instructions.md has minimum task quality rules for follow-up task creation by any agent (AC required, single-responsibility, affected files listed)
- [ ] Follow-up tasks created by non-planner agents (reviewer rejections, researcher findings) must target backlog status so architect gate still applies
- [ ] No specialized builder agents needed -- the builder reads the codebase for domain patterns

## Notes
- The architect gate (backlog->todo) is the quality control for tasks created outside the planner. This already exists in the pipeline. The key rule is: follow-up tasks always go to backlog, never straight to todo, so the architect reviews them.

[[2026-03-08]] Sun 17:26
See docs/task-decomposition-rules-research.md for details. Follow-up tasks: #694, #695, #697.

[[2026-03-08]] Sun 23:51
Wave 4, agent: auditor

[[2026-03-09]] Mon 04:57
Wave 2, agent: auditor

[[2026-03-09]] Mon 10:44
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| kanban-planner.agent.md: single-domain atomicity gate | Lines 39-57: 'Single domain per task' rule + 11-domain table with module path scopes | PASS |
| Architect gate validates single-domain | arch-review/SKILL.md lines 51-53: item 9 single-domain check; line 83: checklist item; architect.agent.md red flags + rationalizations rows added | PASS |
| agent-common.instructions.md: follow-up task quality rules | Lines 78-82: 3 rules (AC required, single-responsibility with affected files, target backlog) | PASS |
| Follow-up tasks target backlog | Line 82: 'Non-planner agents always create follow-up tasks at backlog status so the architect gate applies' | PASS |
| No specialized builder agents needed | Only one builder.agent.md exists in .github/agents/ -- no domain-specific builders | PASS |

### Test Results
- pytest: 404 passed, 20 skipped, 1 failed (pre-existing: test_slack_channel_created -- slack_sdk not installed, unrelated to #685)
- ruff: 3 pre-existing errors in unrelated files (screenshot.py, test_bootstrap_structure.py)

### Notes
- AC1 domain list improved from generic (backend, frontend, database) to OwlBear-specific 11-domain list aligned with architecture layers. Intent exceeded.
- Implementation decomposed into subtasks #694, #695, #697 -- all in done with full pipeline evidence (builder/reviewer/writer gates passed).

### Confidence: .97
### Action: archive
