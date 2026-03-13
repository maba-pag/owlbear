---
id: 347
title: Implement ProjectStore — CRUD for project persistence as JSON files
status: archived
priority: needed
created: 2026-03-01T11:19:57.4304321+01:00
updated: 2026-03-01T17:10:16.1503333+01:00
started: 2026-03-01T11:21:59.7662098+01:00
completed: 2026-03-01T17:10:16.1503333+01:00
tags:
    - phase-12
    - memory
    - daemon
depends_on:
    - 346
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/projects/store.py
- [ ] ProjectStore(projects_dir: Path): creates dir if not exists
- [ ] create(name, workspace_path) -> Project: slugifies name, writes {id}.json, raises ValueError on duplicate
- [ ] get(id) -> Project: reads {id}.json, raises FileNotFoundError if missing
- [ ] get_by_name(name) -> Project: scans all files, matches by name field
- [ ] list_active() -> list[Project]: returns all projects with status='active', sorted by last_active desc
- [ ] update(project: Project) -> None: overwrites {id}.json with updated model
- [ ] archive(id) -> None: reads project, sets status='archived', writes back
- [ ] ~60 LOC total

See docs/research/multi-project-session.md S3.3
