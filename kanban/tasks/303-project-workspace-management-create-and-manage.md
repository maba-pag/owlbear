---
id: 303
title: Project workspace management — create and manage project repos
status: archived
priority: needed
created: 2026-03-01T02:53:58.0773901+01:00
updated: 2026-03-03T15:03:02.3622443+01:00
started: 2026-03-01T18:42:33.1027862+01:00
completed: 2026-03-03T15:03:02.3622443+01:00
tags:
    - phase-13
    - tools
    - git
class: standard
---

## Context
When OwlBear starts a new project, it needs to create a git repo, set up project structure, initialize kanban board, and manage workspace switching.

## Acceptance Criteria
- [ ] ProjectWorkspace class: create_project(name, template) -> Path
- [ ] Templates: python-uv, python-pip, node, bare (just git init + README)
- [ ] Git repo initialization with .gitignore, README, basic structure
- [ ] Kanban board initialization via kanban-md init
- [ ] Configurable project root directory (default: ~/projects/)
- [ ] bearclaw project new <name> --template <t> CLI command
- [ ] Agent can create projects via tool (workspace_create_project)
- [ ] Workspace switching: update CWD, reload context, swap session
- [ ] Unit tests for each template and workspace operations
