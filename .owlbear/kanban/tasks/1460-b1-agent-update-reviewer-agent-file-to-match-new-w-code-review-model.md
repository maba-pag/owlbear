---
id: 1460
title: 'B1-agent: Update reviewer agent file to match new w-code-review model'
status: backlog
priority: needed
created: 2026-05-08T19:47:16.726901+00:00
updated: 2026-05-08T19:47:45.952893+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
parent: 1403
depends_on:
- 1458
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Update `share/agents/reviewer.agent.md` to align with rewritten w-code-review skill. Changes: remove quality-runner from default dispatch (read from task body instead), update persona to remove "run tests yourself" language, update critical_rules to remove "Never trust builder self-reports", remove TestFromAC enforcement from boundaries, update examples to new output format (Review Evidence + Observations).