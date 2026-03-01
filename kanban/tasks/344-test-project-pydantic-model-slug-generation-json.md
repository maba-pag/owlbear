---
id: 344
title: Test Project Pydantic model — slug generation, JSON round-trip, defaults
status: archived
priority: needed
created: 2026-03-01T11:19:24.0057783+01:00
updated: 2026-03-01T17:10:12.7969905+01:00
started: 2026-03-01T11:21:20.7333076+01:00
completed: 2026-03-01T17:10:12.7969905+01:00
tags:
    - phase-12
    - memory
    - daemon
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test Project model has fields: id, name, workspace_path, created_at, last_active, status
- [ ] Test id auto-derived from name via slugify: 'My Project' -> 'my-project'
- [ ] Test status defaults to 'active'
- [ ] Test created_at and last_active default to current time
- [ ] Test workspace_path stored as absolute Path
- [ ] Test JSON round-trip: model_dump_json() -> model_validate_json() preserves all fields
- [ ] Test invalid status value raises ValidationError
- [ ] Test duplicate slug generation from different names: 'My Project' and 'my project' produce same slug

See docs/multi-project-session-research.md S3.2
