---
id: 345
title: Implement Project Pydantic model — id, name, workspace_path, status
status: archived
priority: needed
created: 2026-03-01T11:19:32.4854829+01:00
updated: 2026-03-01T17:10:13.6786488+01:00
started: 2026-03-01T11:21:58.4852862+01:00
completed: 2026-03-01T17:10:13.6786488+01:00
tags:
    - phase-12
    - memory
    - daemon
depends_on:
    - 344
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/projects/__init__.py and src/owlbear/projects/models.py
- [ ] Project(BaseModel): id (str), name (str), workspace_path (Path), created_at (datetime), last_active (datetime), status (Literal['active', 'archived'])
- [ ] id auto-derived from name via model_validator: slugify (lowercase, replace spaces with hyphens, strip special chars)
- [ ] status defaults to 'active'
- [ ] created_at and last_active default to datetime.now(UTC)
- [ ] JSON serialization works for Path and datetime fields
- [ ] Frozen model (immutable once created, use model_copy for updates)

See docs/research/multi-project-session.md S3.2
