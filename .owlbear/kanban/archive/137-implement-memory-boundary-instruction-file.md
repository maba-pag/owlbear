---
id: 137
title: Implement memory boundary instruction file
status: archived
priority: medium
created: 2026-03-29 13:00:01.081171+02:00
updated: 2026-03-30 15:36:01.262467+02:00
started: 2026-03-30 15:18:48.537351+02:00
completed: 2026-03-30 15:18:48.537351+02:00
tags:
- phase-1
- scope:knowledge
- type:docs
class: standard
archival_reason: completed
archival_refs: []
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

## Audit (manual archival 2026-03-30) Redundant with #11 (archived). Memory governance added to copilot-instructions.md. Confidence 1.0.
