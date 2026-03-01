---
id: 352
title: Bootstrap project-awareness — workspace_root from active project
status: archived
priority: important
created: 2026-03-01T11:20:48.9132236+01:00
updated: 2026-03-01T17:10:20.8906036+01:00
started: 2026-03-01T11:22:04.6231177+01:00
completed: 2026-03-01T17:10:20.8906036+01:00
tags:
    - phase-12
    - memory
    - daemon
depends_on:
    - 347
    - 349
class: standard
---

## Acceptance Criteria
- [ ] bootstrap() reads active project id from config_dir/active_project file
- [ ] When active project exists: workspace_root = project.workspace_path
- [ ] ContextManager, KanbanToolset, FileToolset, TerminalToolset all receive project workspace path
- [ ] SessionStore path = config_dir/projects/{id}/sessions/session.jsonl
- [ ] Knowledge queries include scope='project:{id}' in addition to 'global'
- [ ] Fallback: no active_project file or empty = current behavior (CWD as workspace)
- [ ] ProjectToolset added to toolsets list when ProjectStore is available
- [ ] Integration test: bootstrap with active project vs without

See docs/multi-project-session-research.md S3.8, S4
