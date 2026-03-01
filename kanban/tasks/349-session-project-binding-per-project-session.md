---
id: 349
title: Session-project binding — per-project session directories
status: archived
priority: needed
created: 2026-03-01T11:20:18.9600756+01:00
updated: 2026-03-01T17:10:18.0434234+01:00
started: 2026-03-01T11:22:01.5988803+01:00
completed: 2026-03-01T17:10:18.0434234+01:00
tags:
    - phase-12
    - memory
    - daemon
depends_on:
    - 347
class: standard
---

## Acceptance Criteria
- [ ] Sessions stored at config_dir/projects/{id}/sessions/{name}.jsonl when project is active
- [ ] _build_chat_session in bootstrap respects active project path for SessionStore
- [ ] Backward compat: existing sessions at config_dir/sessions/ still work when no project active
- [ ] bearclaw chat --project NAME uses project-scoped session dir
- [ ] Unit tests: session creation in project dir, session isolation between two projects
- [ ] SessionStore constructor receives project-aware path from bootstrap

See docs/multi-project-session-research.md S3.4
