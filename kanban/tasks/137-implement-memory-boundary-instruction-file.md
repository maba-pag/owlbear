---
id: 137
title: Implement memory boundary instruction file
status: ideation
priority: important
created: 2026-03-29T13:00:01.081171+02:00
updated: 2026-03-29T15:36:56.9848865+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:docs
blocked: true
block_reason: 'Redundant with #11 (in-progress, same scope). Delete after #11 completes.'
class: standard
---

## Objective
Create instructions/memory.instructions.md with applyTo ** to constrain built-in memory tool usage.

## Acceptance Criteria
- [ ] Create instructions/memory.instructions.md with YAML frontmatter (applyTo: **, description)
- [ ] Boundary text constrains user memory to: tool usage patterns, CLI flags, agent behavior, what worked/failed
- [ ] Boundary text explicitly excludes: architecture decisions, research findings, project-specific patterns, domain knowledge
- [ ] Include management section: Chat: Show Memory Files command, memory view/delete operations
- [ ] Manual test: run agent session, verify /memories/ contents stay in scope, document result in PR
- [ ] Add instructions listing entry to copilot-instructions.md if applicable

## Content Source
Boundary text from docs/research/copilot-memory.md section 4. Management commands from section 5.
See docs/research/memory-boundary-instructions.md for implementation rationale.
