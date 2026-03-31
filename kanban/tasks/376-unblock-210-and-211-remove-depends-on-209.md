---
id: 376
title: 'Unblock #210 and #211: remove depends_on 209'
status: backlog
priority: nice-to-have
created: 2026-03-30T20:46:43.1402112+02:00
updated: 2026-03-30T23:39:10.5805569+02:00
started: 2026-03-30T23:39:05.5597753+02:00
tags:
    - scope:agents
    - hooks
    - type:build
class: standard
---

## Context
See docs/research/stop-hook-multi-agent-viability.md section 3 Q4.
The chat.useCustomAgentHooks setting (the only prerequisite from 209) is already present. Tasks 210 and 211 can proceed independently.

## Acceptance Criteria
- [ ] Remove depends_on from task 210 frontmatter
- [ ] Remove depends_on from task 211 frontmatter
- [ ] Verify both tasks are no longer blocked
