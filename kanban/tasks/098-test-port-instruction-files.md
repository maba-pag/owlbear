---
id: 98
title: 'Test: Port instruction files'
status: backlog
priority: important
created: 2026-03-28T03:53:35.1978065+01:00
updated: 2026-03-28T03:54:15.965388+01:00
tags:
    - phase-1
    - scope:docs
    - type:test
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test that instructions/ contains python.instructions.md, agent-common.instructions.md, research-docs.instructions.md, frontend.instructions.md
- [ ] Test each file has valid YAML frontmatter with applyTo and description fields
- [ ] Test python.instructions.md does NOT contain 'PydanticAI', 'BearClaw', or 'src/owlbear/' references
- [ ] Test .github/instructions/ directory does NOT exist
- [ ] Test .vscode/settings.json chat.instructionsFilesLocations does NOT include .github/instructions
- [ ] Test .github/copilot-instructions.md still exists
- [ ] Update or remove test_vscode_settings_instructions_files_locations_github in test_monorepo_skeleton.py

## Context
Test task for #10 (Port instruction files). Verifies the migration from .github/instructions/ to instructions/ completed correctly.
