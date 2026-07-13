---
id: 376
title: 'Unblock #210 and #211: remove depends_on 209'
status: archived
priority: medium
created: 2026-03-30 20:46:43.140211+02:00
updated: 2026-04-01 08:14:10.136660+02:00
started: 2026-03-30 23:39:05.559775+02:00
completed: 2026-04-01 08:14:10.136660+02:00
tags:
- scope:agents
- hooks
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Context
See docs/research/stop-hook-multi-agent-viability.md section 3 Q4.
The chat.useCustomAgentHooks setting (the only prerequisite from 209) is already present. Tasks 210 and 211 can proceed independently.

## Acceptance Criteria
- [ ] Remove depends_on from task 210 frontmatter
- [ ] Remove depends_on from task 211 frontmatter
- [ ] Verify both tasks are no longer blocked
