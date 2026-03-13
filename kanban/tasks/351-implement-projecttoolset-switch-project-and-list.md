---
id: 351
title: Implement ProjectToolset — switch_project and list_projects for agents
status: archived
priority: important
created: 2026-03-01T11:20:36.6028017+01:00
updated: 2026-03-01T17:10:19.9994031+01:00
started: 2026-03-01T11:22:03.6088639+01:00
completed: 2026-03-01T17:10:19.9994031+01:00
tags:
    - phase-12
    - memory
    - daemon
    - agent
depends_on:
    - 350
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/tools/project.py with ProjectToolset(FunctionToolset)
- [ ] switch_project(project_name: str) -> str: loads project, rebuilds session path, updates context, returns confirmation
- [ ] list_projects() -> str: returns formatted list of active projects with name and last_active
- [ ] Injects 'You are now working on project: {name}' into agent instructions after switch
- [ ] Updates project.last_active on switch
- [ ] Handles nonexistent project gracefully (returns error string, no exception)
- [ ] ~60 LOC

See docs/research/multi-project-session.md S3.10
