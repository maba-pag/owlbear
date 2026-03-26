---
id: 29
title: Clean up .github/ v1 prompts and residual files
status: ideation
priority: important
created: 2026-03-26T17:59:04.1808507+01:00
updated: 2026-03-26T17:59:04.1808507+01:00
tags:
    - phase-1
    - scope:docs
    - type:build
depends_on:
    - 8
    - 9
    - 10
class: standard
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
