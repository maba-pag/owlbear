---
id: 110
title: 'Implement: update instructions/README.md for v2'
status: archived
priority: medium
created: 2026-03-28 22:23:30.253662+01:00
updated: 2026-03-29 01:19:04.539245+01:00
started: 2026-03-29 01:19:04.539245+01:00
completed: 2026-03-29 01:19:04.539245+01:00
tags:
- phase-1
- scope:docs
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Update instructions/README.md to accurately describe the directory.

## AC
- [ ] Remove 'transition placeholder' text and .github/instructions/ reference
- [ ] Describe instructions/ as the primary location for VS Code instruction files
- [ ] List all 4 files with applyTo scopes:
  - agent-common.instructions.md (applyTo: **) -- Cross-agent rules
  - python.instructions.md (applyTo: **/*.py) -- Python conventions
  - frontend.instructions.md (applyTo: src/**/ui/**,...) -- Frontend conventions
  - research-docs.instructions.md (applyTo: docs/research/*.md) -- Research guardrails
- [ ] Keep it under 20 lines

## Context
Research: docs/research/instructions-readme-update.md
Parent: #109
