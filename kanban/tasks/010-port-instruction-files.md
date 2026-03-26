---
id: 10
title: Port instruction files
status: ideation
priority: important
created: 2026-03-26T17:20:03.836269+01:00
updated: 2026-03-26T17:56:20.4019369+01:00
tags:
    - phase-1
    - scope:docs
    - type:build
depends_on:
    - 7
class: standard
---

## Objective
Copy and adapt v1 instruction files to v2 instructions/ directory.

## Acceptance Criteria
- [ ] Copy python.instructions.md - remove v1-specific PydanticAI references
- [ ] Copy agent-common.instructions.md - update for v2 workflow (no daemon, no PydanticAI)
- [ ] Copy research-docs.instructions.md
- [ ] Copy frontend.instructions.md (if applicable)
- [ ] Create copilot-instructions.md for v2 root (.github/copilot-instructions.md)
- [ ] All instructions reference v2 directory structure
- [ ] Remove references to dropped components (daemon, approval gates, bearclaw)
- [ ] Test that instructions auto-apply in VS Code via applyTo patterns

## Context
Depends on F1 (monorepo skeleton) for directory structure. Instruction files are mostly compatible but contain v1-specific references that need updating.

[[2026-03-26]] Thu 17:56
## Additional AC
- [ ] Write v2 instructions to instructions/ at repo root (not .github/instructions/)
- [ ] After v2 instructions verified working, delete .github/instructions/
