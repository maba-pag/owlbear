---
id: 11
title: Write Copilot Memory boundary instructions
status: ideation
priority: important
created: 2026-03-26T17:20:13.9642078+01:00
updated: 2026-03-26T17:20:13.9642078+01:00
tags:
    - phase-1
    - scope:knowledge
    - type:docs
depends_on:
    - 5
class: standard
---

## Objective
Create the instruction file that constrains what Copilot Memory stores, ensuring clean separation between the three knowledge layers.

## Acceptance Criteria
- [ ] Write memory boundary instruction in copilot-instructions.md or dedicated instructions file
- [ ] Instruction constrains Memory to: tool usage patterns, CLI flags, agent behavior, what worked/failed
- [ ] Instruction explicitly excludes: architecture decisions, research findings, project-specific patterns, domain knowledge
- [ ] Test by running several agent sessions and verifying Memory contents stay in scope
- [ ] Document how to view and manage Copilot Memory entries

## Context
Depends on R5 (Copilot Memory boundary testing) for understanding what instructions are effective. The boundary instruction prevents Copilot Memory from duplicating knowledge that belongs in the general or project KB layers.
