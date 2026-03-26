---
id: 350
title: Test ProjectToolset — switch_project and list_projects agent tools
status: archived
priority: important
created: 2026-03-01T11:20:28.0067807+01:00
updated: 2026-03-01T17:10:18.9323233+01:00
started: 2026-03-01T11:22:02.5858537+01:00
completed: 2026-03-01T17:10:18.9323233+01:00
tags:
    - phase-12
    - memory
    - daemon
    - agent
    - test
depends_on:
    - 347
class: standard
---

## Acceptance Criteria
- [ ] Test switch_project(name) updates agent session path to project's session dir
- [ ] Test switch_project(name) returns confirmation message with project name
- [ ] Test switch_project with nonexistent project returns error message (not exception)
- [ ] Test list_projects() returns active projects with name and last_active
- [ ] Test switch_project updates project.last_active timestamp
- [ ] Mock ProjectStore and OwlBearAgent for isolation

See docs/research/multi-project-session.md S3.10
