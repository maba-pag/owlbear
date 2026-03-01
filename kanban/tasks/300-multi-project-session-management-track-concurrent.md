---
id: 300
title: Multi-project session management — track concurrent projects
status: archived
priority: needed
created: 2026-03-01T02:53:26.5173871+01:00
updated: 2026-03-01T17:09:25.5249078+01:00
started: 2026-03-01T10:06:08.1762828+01:00
completed: 2026-03-01T17:09:25.5249078+01:00
tags:
    - phase-12
    - memory
    - daemon
class: standard
---

## Context
Currently sessions are flat JSONL files with no project association. When OwlBear handles multiple projects, it needs to know which project context to load, which workspace to operate in, and maintain separate conversation histories.

## Acceptance Criteria
- [ ] Project model: name, workspace_path, created_at, last_active, status (active/archived)
- [ ] ProjectStore: CRUD for projects, stored in config_dir/projects/
- [ ] bearclaw project create/list/switch/archive CLI commands
- [ ] Session linked to project (session.project_id field)
- [ ] Context manager auto-loads project-specific context.md and MEMORY.md
- [ ] Agent can switch projects mid-conversation via tool ('switch to project X')
- [ ] Project listing shows active projects with last activity timestamp
- [ ] Unit tests for ProjectStore CRUD and session-project linking
