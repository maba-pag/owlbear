---
id: 3
title: agentskills.io spec validation
status: ideation
priority: needed
created: 2026-03-26T17:18:26.7722859+01:00
updated: 2026-03-26T17:18:26.7722859+01:00
tags:
    - research
    - phase-1
    - scope:skills
class: standard
---

## Objective
Research the agentskills.io open standard and validate whether v1 skills can be ported with minimal changes.

## Acceptance Criteria
- [ ] Read agentskills.io specification
- [ ] Map v1 SKILL.md format to agentskills.io format - identify gaps
- [ ] Document required changes per skill (scripts/, references/, assets/ structure)
- [ ] Test skill auto-loading in VS Code (relevance-based activation)
- [ ] Test skill loading in Copilot CLI
- [ ] Document progressive disclosure pattern (metadata -> instructions -> resources)
- [ ] Write findings to docs/research/agentskills-io.md
- [ ] Create follow-up tasks for any gaps discovered

## Context
OwlBear v1 has 15+ skills in .github/skills/. The agentskills.io standard may require restructuring. Need to know the delta before porting.
