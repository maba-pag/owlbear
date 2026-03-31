---
id: 375
title: 'Unblock #210 and #211: remove depends_on #209'
status: backlog
priority: nice-to-have
created: 2026-03-30T20:46:37.5595232+02:00
updated: 2026-03-30T23:43:38.3932738+02:00
tags:
    - scope:agents
    - hooks
    - type:build
class: standard
---

## Context
See docs/research/stop-hook-multi-agent-viability.md section 3 Q4.
The chat.useCustomAgentHooks setting (the only real prerequisite from #209) is already present in .vscode/settings.json. #210 and #211 can proceed independently.

## Acceptance Criteria
- [ ] Remove depends_on: [209] from kanban/tasks/210-*.md frontmatter
- [ ] Remove depends_on: [209] from kanban/tasks/211-*.md frontmatter
- [ ] Verify both tasks are no longer blocked in kanban-md list --blocked

[[2026-03-30]] Mon 23:43
## Research\nN/A trivial change. Verified: chat.useCustomAgentHooks present at .vscode/settings.json line 70. Parent research: docs/research/stop-hook-multi-agent-viability.md section 3 Q4, section 4. No new research doc needed.
