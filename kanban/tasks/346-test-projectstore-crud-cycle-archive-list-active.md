---
id: 346
title: Test ProjectStore — CRUD cycle, archive, list_active, duplicate prevention
status: archived
priority: needed
created: 2026-03-01T11:19:44.6485555+01:00
updated: 2026-03-01T17:10:14.7464957+01:00
started: 2026-03-01T11:21:59.1331123+01:00
completed: 2026-03-01T17:10:14.7464957+01:00
tags:
    - phase-12
    - memory
    - daemon
    - test
depends_on:
    - 345
class: standard
---

## Acceptance Criteria
- [ ] Test create() writes {id}.json to config_dir/projects/
- [ ] Test get(id) reads and validates Project from JSON file
- [ ] Test get_by_name(name) finds project by display name
- [ ] Test list_active() returns only projects with status='active'
- [ ] Test update() rewrites project JSON with updated fields (e.g. last_active)
- [ ] Test archive(id) sets status='archived', does not delete file
- [ ] Test create() with duplicate name raises ValueError
- [ ] Test get() with nonexistent id raises FileNotFoundError
- [ ] Test list_active() on empty directory returns empty list
- [ ] Use tmp_path fixture for isolated test directory

See docs/multi-project-session-research.md S3.3
