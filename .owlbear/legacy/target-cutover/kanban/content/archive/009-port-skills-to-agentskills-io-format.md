---
id: 9
title: Port skills to agentskills.io format
status: archived
priority: medium
created: 2026-03-26 17:19:53.993489+01:00
updated: 2026-03-30 15:35:58.748967+02:00
started: 2026-03-30 15:18:45.992803+02:00
completed: 2026-03-30 15:18:45.992803+02:00
tags:
- phase-1
- scope:skills
- type:build
depends_on:
- 3
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Port v1 skills from .github/skills/ to v2 skills/ directory using the agentskills.io open standard format.

## Acceptance Criteria
- [ ] Port tdd-workflow skill
- [ ] Port tdd-red skill
- [ ] Port code-review skill
- [ ] Port research-workflow skill
- [ ] Port kanban-md skill
- [ ] Port architecture-standards skill
- [ ] Port arch-review skill
- [ ] Port docs-gate skill
- [ ] Port task-verification skill
- [ ] Port task-decomposition skill
- [ ] Port dispatch-planning skill
- [ ] Port pytest-and-linting skill
- [ ] Port remaining skills (visual-output, excalidraw, etc.)
- [ ] Each skill follows agentskills.io directory structure
- [ ] Skills auto-load by relevance in VS Code
- [ ] Test at least 3 skills in VS Code Copilot Chat

## Context
Depends on R3 (agentskills.io spec validation) for format requirements. V1 has 15+ skills. Some may need restructuring.

[[2026-03-26]] Thu 17:56
## Additional AC
- [ ] Write v2 skills to skills/ at repo root (not .github/skills/)
- [ ] Update .vscode/settings.json chat.agentSkillsLocations to include skills/
- [ ] After v2 skills verified working, delete .github/skills/

[[2026-03-29]] Sun 14:26
## Architecture Review
**Verdict:** BLOCK (superseded)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Port tdd-workflow skill | Already in skills/tdd-workflow/ | Superseded |
| Port tdd-red skill | Already in skills/tdd-red/ | Superseded |
| Port code-review skill | Already in skills/code-review/ | Superseded |
| Port research-workflow skill | Already in skills/research-workflow/ | Superseded |
| Port kanban-md skill | Already in skills/kanban-md/ | Superseded |
| Port architecture-standards skill | Already in skills/architecture-standards/ | Superseded |
| Port arch-review skill | Already in skills/arch-review/ | Superseded |
| Port docs-gate skill | Already in skills/docs-gate/ | Superseded |
| Port task-verification skill | Already in skills/task-verification/ | Superseded |
| Port task-decomposition skill | Already in skills/task-decomposition/ | Superseded |
| Port dispatch-planning skill | Already in skills/dispatch-planning/ | Superseded |
| Port pytest-and-linting skill | Already in skills/pytest-and-linting/ | Superseded |
| Port remaining skills | 22 skills in skills/ (21 ported + mcp-kanban) | Superseded |
| Each skill follows agentskills.io format | Verified by research #3: 100% frontmatter compliance | Superseded |
| Skills auto-load by relevance | chat.agentSkillsLocations: {skills: true} already set | Superseded |
| Test 3 skills in VS Code | Skills actively used by all pipeline agents since porting | Superseded |
| Write v2 skills to skills/ | 22 directories exist | Superseded |
| Update .vscode/settings.json | Already updated; #117 cleaned dual-path | Superseded |
| Delete .github/skills/ | Completed by #117 (commit b5377c6) | Superseded |

### Architecture Notes
Task #9 is fully superseded. All 22 skills exist in skills/ with valid agentskills.io frontmatter (verified by research #3). The porting was done organically during v2 development. Remaining cleanup (delete .github/skills/, remove dual-path config, update references) was handled by task #117 (currently in review, builder committed b5377c6 with 44 files changed).

Related tasks that consumed #9's scope:
- #3 (archived): Research validated all 21 skills are agentskills.io compliant
- #42 (in-progress): user-invocable flags for pipeline-only skills
- #79 (todo): argument-hint for remaining user-invocable skills
- #44 (in-progress): skills-ref validation in CI
- #117 (review): Delete .github/skills/ and clean up dual-path config

No remaining actionable work exists for a builder. Recommend closing as superseded.

### Changes Made
- Blocked to ideation: task scope fully consumed by organic work and tasks #3, #42, #44, #79, #117

### Dependencies
- Depends-on #3: archived (satisfied)
- No downstream tasks depend on #9

## Audit (manual archival 2026-03-30) Superseded: all 22 skills ported organically. Superseding tasks #3, #42, #79, #117 all archived. Confidence 1.0.
