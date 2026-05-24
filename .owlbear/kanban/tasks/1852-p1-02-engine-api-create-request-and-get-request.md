---
id: 1852
title: 'P1-02: Engine API — create_request and get_request'
status: backlog
priority: needed
created: 2026-05-24T20:58:06.152479+02:00
updated: 2026-05-24T21:00:29.405957+02:00
tags:
  - phase-1
  - scope:kanban
  - api
parent: 1850
depends_on:
  - 1851
ac:
  - create_request(task_id, kind, title, summary, agent, options, body) writes 
    decisions/pending/{uuid4}.md atomically (O_EXCL) with YAML frontmatter 
    matching the Pydantic model schema, and returns the created request model.
  - create_request sets task.blocked=True with block_reason="DR pending" on the 
    parent task after successful file creation; rolls back the file on blocking 
    failure.
  - get_request(request_id) returns the full request model when the file exists 
    in either pending/ or resolved/; raises NotFoundError when absent from both.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- `create_request` engine function with atomic file creation
- UUID4 generation for request_id
- YAML frontmatter serialization from Pydantic model
- Task blocking on DR creation
- `get_request` engine function searching both directories
- Rollback (delete file) if task blocking fails

**Out of scope:**
- Resolution logic (P1-03)
- List/filter operations (P1-04)
- Sweep (P1-04)
- MCP/Cockpit layers

## Test scope
`serve/kanban/tests/`