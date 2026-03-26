---
id: 27
title: Clean up instruction files for v2
status: ideation
priority: critical
created: 2026-03-26T17:38:30.4685087+01:00
updated: 2026-03-26T17:38:30.4685087+01:00
tags:
    - phase-1
    - scope:docs
    - type:build
class: standard
---

## Objective
Carefully update copilot-instructions.md and agent-common.instructions.md to work for v2 without losing important content.

## Acceptance Criteria
- [ ] Review every section of .github/copilot-instructions.md
- [ ] Remove PydanticAI references (v2 uses Copilot CLI)
- [ ] Remove daemon/always-on references (v2 is on-demand)
- [ ] Remove bearclaw name references (everything is owlbear)
- [ ] Remove 25+ toolset references (v2 has 3-4 MCP servers)
- [ ] Remove 6-layer security model references (v2 uses git as safety net)
- [ ] Update tech stack table for v2 (Copilot CLI, MCP servers, ACP protocol)
- [ ] Update directory structure table for v2 layout
- [ ] Update file placement rules for v2
- [ ] Preserve: principles, coding discipline, process habits, kanban-md usage, formatting rules
- [ ] Preserve: attribution rules, confidence scores, tag taxonomy, priority scheme
- [ ] Review agent-common.instructions.md similarly
- [ ] Preserve: task discipline, commit discipline, evidence over claims, inter-agent comms
- [ ] Remove: references to PydanticAI AbstractToolset, daemon-specific hooks
- [ ] Update: task lifecycle to reflect v2 pipeline
- [ ] Test: agents still function correctly after changes

## IMPORTANT
Be careful not to delete general-purpose rules that apply to v2. When in doubt, keep the content. A lot of the workflow patterns (TDD, kanban lifecycle, agent communication protocol) carry over to v2.
