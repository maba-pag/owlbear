---
id: 29
title: Clean up .github/ v1 prompts and residual files
status: archived
priority: medium
created: 2026-03-26 17:59:04.180851+01:00
updated: 2026-04-04 06:39:36.919679+02:00
started: 2026-04-04 06:39:36.919679+02:00
completed: 2026-04-04 06:39:36.919679+02:00
tags:
- phase-1
- scope:docs
- type:build
depends_on:
- 8
- 9
- 10
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
After agents, skills, and instructions are ported to root dirs, clean up remaining v1 content in .github/.

## Acceptance Criteria
- [ ] Review .github/prompts/ - port or delete each prompt file
  - orchestrate.prompt.md - likely v1-specific, delete or rewrite for v2
  - agent-audit.prompt.md - review if still useful
  - design-context.prompt.md - review if still useful
  - frontend-*.prompt.md - review if still useful
- [ ] Delete .github/agents/ after v2 agents/ at root confirmed working
- [ ] Delete .github/skills/ after v2 skills/ at root confirmed working
- [ ] Delete .github/instructions/ after v2 instructions/ at root confirmed working
- [ ] Review .github/copilot-instructions.md - should point to v2 structure
- [ ] Keep .github/ itself (GitHub platform directory)

## Context
Depends on porting tasks #8, #9, #10 completing successfully. This is the final cleanup of v1 artifacts in .github/.

[[2026-03-30]] Mon 15:52
## Architecture Review
**Verdict:** BLOCK (superseded)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Review .github/prompts/ - port or delete | All 6 prompts are v2 content (reference v2 agents, skills, docs). Not v1. No porting or deletion needed. | Superseded |
| Delete .github/agents/ | Already deleted by task #8 (archived). Directory does not exist. | Superseded |
| Delete .github/skills/ | Already deleted by task #9/#117 (both archived). Directory does not exist. | Superseded |
| Delete .github/instructions/ | Already deleted by task #10 (archived). Directory does not exist. | Superseded |
| Review .github/copilot-instructions.md | Already points to v2 structure. Verified in #10 audit. No v1 references remain. | Superseded |
| Keep .github/ itself | .github/ contains only copilot-instructions.md, dependabot.yml, and prompts/ -- all v2. Satisfied. | Superseded |

### Architecture Notes
Task #29 is fully superseded. Its original premise was to clean up v1 content in .github/ after porting tasks #8, #9, #10 completed. Those tasks (and #117) already cleaned up all v1 artifacts:

- .github/agents/ removed by #8
- .github/skills/ removed by #9/#117
- .github/instructions/ removed by #10
- copilot-instructions.md rewritten for v2 during #10

The 6 prompt files in .github/prompts/ are v2 content in the standard VS Code location. They reference v2 agents (orchestrator), v2 skills (frontend-design), and v2 docs. No PydanticAI, BearClaw, or src/owlbear/ references found. .github/prompts/ is the correct VS Code default location for user-invocable slash commands per the Command Surface Selection table in copilot-instructions.md.

No remaining actionable work exists for a builder. Recommend closing as superseded.

### Changes Made
- Blocked to ideation: task scope fully consumed by completed tasks #8, #9, #10, #117

### Dependencies
- Depends-on #8: archived (satisfied)
- Depends-on #9: archived (satisfied)
- Depends-on #10: archived (satisfied)
- No downstream tasks depend on #29
